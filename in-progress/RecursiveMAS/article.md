# RecursiveMAS：讓多個 AI Agent 別再打字，直接交換向量

## 前言

現在的 multi-agent system（MAS）幾乎都長同一個樣子：Agent A 生一段文字，丟給 Agent B，B 讀完再生一段文字丟給 C。這個設計很自然，因為 LLM 本來就是吐文字的東西。但它其實把一件很浪費的事情變成了預設值。

RecursiveMAS（UIUC、Stanford、NVIDIA、MIT 合作）的主張是：**Agent 之間根本不需要看懂人類的文字**。既然接收端也是模型，那就直接把最後一層的 hidden state 傳過去就好，中間那段「投影到十幾萬維詞表、逐字解碼、對方再重新 embedding 讀進來」的來回全部可以省掉。

省掉之後，還多送一個附加價值：向量是連續的，所以整條溝通路徑變成可微的。整個 Agent 團隊可以被當成一張大的計算圖來做端到端訓練——而且只需要訓練不到 0.31% 的參數。

這篇文章會把這套機制從頭拆一遍：溝通媒介怎麼換、跨模型的維度怎麼對齊、兩階段訓練怎麼設計、以及一個乍看反直覺的結果——明明多做了好幾輪推論，為什麼反而比文字版更快。

## 一、文字當溝通媒介，到底貴在哪裡

### 痛點一：每講一個字都要查一次巨大的字典

LLM 生文字是 auto-regressive 的。每生一個 token，都必須把隱藏層向量（維度 $d_h$，常見約 4096）投影到整個詞表空間（$|V|$，常見 10 萬到 15 萬）。因為 $|V| \gg d_h$，這一步在中間溝通上會產生 $O(m|V|d_h)$ 的成本。

換個比喻：兩個外星人明明有心電感應，卻被規定必須把腦中的想法用地球人的打字機一個字一個字敲出來，對方收到後再把文字翻譯回腦波。中間那兩層翻譯是純粹的損耗——因為接收端根本不是人類。

### 痛點二：離散文字切斷了反向傳播

文字是離散的，這件事直接把神經網路最依賴的反向傳播鏈條剪斷了。

就算你用一些數學技巧（例如 softmax 軟近似）硬把文字空間變得可導，論文的 Theorem 4.1 也證明了：只要經過多輪反覆溝通，梯度會無可避免地指數級衰減為 0。

拿企劃案傳閱來想比較好懂：如果 Agent A 印成紙本給 Agent B，最後老闆說企劃案很爛，這股「退件的怒氣」很難沿著紙本精準追溯到 A 到底哪一句話想錯了。但如果大家是在同一份雲端文件上工作（連續的潛在空間），就能一路追蹤回去修正。

結果就是：我們沒辦法把整個 Agent 團隊當成一個統一的個體來做系統級的聯合優化。Agent A 永遠不知道自己該怎麼改。

### 痛點三：想讓團隊變強，只剩兩條爛路

過去要讓 MAS 變強，選項大致只有兩個。改 prompt，治標不治本，模型本身沒有變聰明；或者把團隊裡每個模型（動輒 7B、70B）拆開來各自做 full fine-tuning，光是 VRAM 和運算成本就完全不切實際。

而且就算你把每個 Agent 都單獨練強了，也不代表他們組隊之後就會有默契。缺的是一種輕量的方法，專門用來訓練「團隊合作」這件事本身。

## 二、核心概念：把 hidden state 直接當成「想法」

![RecursiveMAS 的整體架構圖：Agent A1 透過 Inner Link 自我循環產生潛在思考向量，再經 Outer Link 轉換後拼接進 Agent A2 的輸入序列，最後一個 Agent 才解碼成文字，右側標示 Looping 表示整個流程會繞回起點。](img-002)
*圖一 — 整體架構。注意右下角那個 Looping 標記：資訊傳完一輪不是就結束了，最後一個 Agent 的思考會再餵回第一個。（來源：原始論文。）*

標準推論流程裡，模型最後一層產生的 hidden state $h$ 會被投影到詞表，變成「蘋果」這種具體的字。RecursiveMAS 的做法是把這一步整個拿掉，直接把 $h$ 當成 Agent 的**潛在思考（latent thought）**——一個高維向量，承載的語意比一個離散的 token 豐富得多。

這帶來的關鍵性質是可微。梯度可以穿透溝通媒介，從 Agent B 一路流回 Agent A。

第二個核心觀念是**把 Agent 當成一層網路**。不要把每個 Agent 看成獨立個體，把它看成一個超大號 Transformer 裡的一個 block：Agent A 是前幾層，Agent B 是中間層，整個 MAS 組成一張統一的運算圖。論文把這個過程形式化成 $S^{(0)} \to S^{(1)} \to \dots \to S^{(n)}$，系統狀態隨著遞迴圈數不斷精煉。

那為什麼要繞圈？就跟人遇到難題會「再想一遍」是同個道理。透過重複遞迴，系統可以在**不增加任何參數**的前提下，用時間換取更深的推理深度。

## 三、架構：RecursiveLink 怎麼搭

Agent 之間傳遞資訊靠的是 RecursiveLink，它有兩種形態。

![Inner 與 Outer RecursiveLink 的結構對照圖：兩者都是 Linear、GELU、Linear 的三層堆疊加上殘差連接，差別在於 Outer 版本的殘差路徑上多了一個線性投影層。](img-003)
*圖二 — Inner 與 Outer 的差別只有一處：Outer 的殘差路徑上多了一個投影矩陣，用來對齊不同模型的維度。（來源：原始論文。）*

### Inner RecursiveLink：大腦內部的電梯

當 Agent 處在「憋著不說話、繼續想」的模式時，它需要一個機制把深層的想法送回淺層的輸入。論文稱之為 dense-to-shallow transition。

$$\mathcal{R}_{in}(h) = h + W_2 \sigma(W_1 h)$$

$W_1$、$W_2$ 是輕量線性層，$\sigma$ 是 GELU。

拿電梯來想：模型頂層產生的 $h$ 是高度抽象的「結論」，$\mathcal{R}_{in}$ 這台電梯把它從頂樓運回一樓，翻譯成輸入層看得懂的特徵分佈，模型才能基於這個結論繼續往下想。

實際跑起來是這樣的循環：產生第 1 個向量 → 過 $\mathcal{R}_{in}$ → append 到輸入序列 → 產生第 2 個向量。整段過程**完全沒有文字產生**，輸入序列後方會慢慢累積 $m$ 個連續的潛在思考向量。

### Outer RecursiveLink：跨模型的翻譯官

當 Agent A 要交棒給架構完全不同的 Agent B，會撞到兩個障礙：維度可能不同（例如 2048 對 4096），語意空間也不一樣。Qwen 的腦波 Llama 聽不懂。

$$\mathcal{R}_{out}(h) = \mathbf{W_3} h + W_2 \sigma(W_1 h)$$

跟 Inner 版本比，多的就是那個 $W_3$，負責物理維度的線性投影。

比較容易被誤解的是接收端怎麼吃這些向量。**不是取代，是融合**：Agent B 仍然保有自己的 system prompt 和原始問題，系統把 B 的文字 prompt 轉成 embedding 之後，在預留的 slot 位置把 A 傳來的 $m$ 個向量拼接進去。論文的 prompt template 裡就有 `{Latent Thought Embeddings}` 這樣的佔位符。

### 殘差連接是定海神針

那個不起眼的 `+ h`，是整套系統能撐過多輪遞迴訓練的關鍵，理由有兩層。

**語意層面**：原本的 $h$ 已經帶有很強的語意。如果不加 $h$，一個隨機初始化的 $\mathcal{R}$ 網路會把這些資訊直接毀掉。加了之後，網路只需要學「分佈的微小偏移」，學習難度大幅下降。

**數學層面**：在遞迴系統裡，梯度要繞好幾圈、經過數十個 Agent。若沒有殘差，連鎖律的連乘效應會讓梯度迅速歸零。有了殘差，$\frac{\partial (h+F(h))}{\partial h} = 1 + F'(h)$，那個 **1** 保證了就算旁邊的轉導層完全沒反應，錯誤訊號仍能原封不動流回上一個 Agent。論文的 Theorem 4.1 就是在證明這件事。

這不是嘴上說說，作者有做對照：

![一張四列的表格，比較 1-Layer、Res+1-Layer、2-Layer、Res+2-Layer 四種 RecursiveLink 設計在三個基準上的準確率，帶殘差的兩層版本在三個基準上都最高。](img-010)
*圖三 — RecursiveLink 的設計消融。同樣層數之下，有沒有殘差的差距相當明顯。（來源：原始論文。）*

## 四、訓練：先練個人基本功，再練團隊默契

![兩階段訓練流程圖：上半部是每個 Agent 平行進行的 inner-loop 預熱，以回歸損失對齊潛在思考與真實分佈；下半部是整個 MAS 展開多輪遞迴的 outer-loop 協同訓練，藍色箭頭為前向傳遞、紅色為反向傳播。](img-004)
*圖四 — 兩階段訓練。上半部每個 Agent 各練各的，下半部整個系統展開一起練。（來源：原始論文。）*

如果 RecursiveLink 是硬體，訓練演算法就是賦予它靈魂的軟體。作者拆成兩階段。

### 第一階段：Inner-loop 預熱

在把 Agent 串起來之前，得先讓每個 Agent 學會「隱形寫字」——讓 Inner Link 輸出的向量，在語意上精準對齊真實的單字。

用的是 teacher forcing。就像教練在池邊扶著你的手練划水：預熱階段不會讓模型真的去吃自己產生的錯誤向量，而是給它讀標準答案，讓它在正常狀態下學習映射。

具體來說，當模型處理到第 $t$ 個字、產生隱藏狀態 $h_t$ 時，強迫 $\mathcal{R}_{in}(h_t)$ 要長得像**下一個字**的 embedding：

$$\mathcal{L}_{in} = 1 - \cos(\mathcal{R}_{in}(h_t), \text{Emb}(y_{t+1}))$$

用餘弦相似度而不是 L2，是因為在向量空間裡「方向」才代表核心語意。

這一階段跑完，模型就學會了憋氣思考：沒開口說話，但產出的每一粒向量都精準承載了下一個字的語意。

### 第二階段：Outer-loop 協同優化

基本功練完，接著是全系統實戰。這時候沒有教練扶著，A 產生的向量直接丟給 B，B 再丟給 C，甚至繞回 A。

流程是：系統依照預設圈數（例如 $r=3$）進行純向量的遞迴傳遞 → 直到最後一圈、最後一個 Agent 才吐出文字答案 → 與標準答案比對算 cross-entropy loss。這份 loss 代表整個團隊這三圈合作下來的總體誤差。

### 梯度累加與信用分配

這是工程和數學結合得最漂亮的一段。因為中間傳的全是連續向量，loss 產生的梯度可以沿著計算圖跨越不同 Agent、跨越不同遞迴圈數，一路倒流回起點——本質上就是 BPTT。

這裡有個實作細節值得單獨拎出來：在三圈的運算中，**同一個 OuterLink 被使用了很多次**，會產生好幾組梯度。根據多元連鎖律，框架會把各圈產生的梯度自動加總（`grad += new_grad`）。意義在於，這讓 OuterLink 被迫學成一個「全能翻譯官」：無論在討論初期（第 1 圈）還是收尾期（第 3 圈），都得提供夠精準的翻譯。

信用分配也是這套機制自動完成的。如果最後答錯了，梯度會告訴系統是第 1 圈 Agent A 的計畫寫太爛，還是第 2 圈 Agent B 審查太馬虎，然後精準修正那些扯後腿的連結參數。

### 成本：只訓練 0.31% 的參數

![一張三列的表格，比較 LoRA 訓練、Full-SFT 與 RecursiveMAS 的峰值 GPU 記憶體、可訓練參數量、估計成本與平均準確率，RecursiveMAS 在四項指標上都最好。](img-012)
*圖五 — 整個 LLM 主體全程凍結，訓練的只有 RecursiveLink 那 13.12M 個參數。（來源：原始論文。）*

整個訓練過程中，幾十億參數的 LLM 主體是**完全凍結**的。真正被訓練的只有 RecursiveLink，佔比 0.31%。峰值 GPU 記憶體 15.29 GB，估計成本 4.27 美元，而平均準確率反而比 LoRA 訓練和 full-SFT 都高。

這是很典型的四兩撥千斤：不動模型本身，只教它們怎麼互相講話。

## 五、推論：為什麼多做了那麼多次推論反而更快

這是整套設計最違反直覺的地方。系統在潛在空間裡繞了好幾圈、每圈每個 Agent 都要跑 $m$ 次推論，怎麼會比傳統 MAS 快？

原因有三個，而且都很具體。

| 傳統 text-based MAS | RecursiveMAS |
|---|---|
| 每走一步都要投影到 15 萬維的詞表矩陣，$O(\|V\|)$ | InnerLink 只是 $d_h \times d_h$（如 4096×4096）的小矩陣，計算量小上數十倍 |
| 要產生數百個 token 才能把一段推理講清楚 | 潛在步數 $m$ 設在 80 步左右就足以承載完整語意 |
| 下一個 Agent 收到文字後要重新 embedding、重新 prefill | 向量無縫插入，省掉重新編碼與預填充 |

第一點是最大宗的節省。傳統模型每產生一個 token 都要付一次巨大的 LM head 投影，RecursiveMAS 把這筆開銷整個換成小矩陣運算。

第二點的 80 步不是隨便挑的：

![一張折線圖，橫軸是潛在思考長度 m 從 0 到 128，三條曲線分別是 MATH500、GPQA-D、LiveCodeBench 的準確率，三者都在 m 約 64 到 80 之後趨於平緩。](img-013)
*圖六 — 潛在思考長度的消融。三個基準都在 64 到 80 步左右進入平原期，再加下去效益有限。（來源：原始論文。）*

### 不同協作拓樸怎麼接

**Mixture style（多對一的星狀拓樸）**：總結者的 prompt 裡設有數個 slot（像是 `{Math_Latent}`、`{Code_Latent}`），不同專家的向量各自過自己的 $\mathcal{R}_{out}$ 轉換後同時填進去，Summarizer 一次前向傳播就能讀完所有專家的腦波。而且是雙向的——下一圈開始時，Summarizer 的總結向量會廣播回所有專家，讓他們根據上一輪的集體共識修正自己的方向。

**Deliberation style（要呼叫外部工具）**：這裡有個根本矛盾——潛在空間不講話，但外部工具只看文字。解法叫**延遲解碼（late decoding）**：前面幾圈 Tool-Caller 和 Reflector 完全處在憋氣模式，只用向量把「要搜尋什麼、要寫什麼 code」的邏輯先對齊好；只有最後一圈，Tool-Caller 才切換模式、用 LM head 吐出真實文字（例如 `<search>...</search>`），這時外部工具才介入。

說白了就是三思而後行。它避免了模型在文字空間裡不斷嘗試、報錯、修正的 token 浪費，在腦中先校對過一遍，確保最後下筆時一擊必殺。

整個推論流程收攏起來是這樣：

```
① Input              問題轉為 embedding sequence
② Agent Internal     跑 m 次推論，經 R_in 產生 m 個潛在向量並 append
③ Cross-Agent        m 個向量經 R_out 翻譯，拼接進下一個 Agent 的指令序列
④ System Recursion   繞行 r 次大圈
⑤ Final Output       最後一圈、最後一個 Agent 改用 LM Head 逐字解碼成文字
```

## 六、實驗結果

### 效率與準確率不再是蹺蹺板

![一張大表格，比較 Recursive-TextMAS 與 RecursiveMAS 在三個遞迴圈數下、六類任務上的準確率、執行時間與 token 用量，RecursiveMAS 在每一組設定下都同時更準、更快、更省。](img-006)
*圖七 — 主結果表。三個區塊分別是遞迴 1、2、3 圈，最右欄是相對於文字版的改善幅度。（來源：原始論文。）*

以 $r=3$ 為例，跟文字版遞迴（Recursive-TextMAS）比：

| 指標 | Recursive-TextMAS | RecursiveMAS |
|---|---|---|
| MATH500 準確率 | 85.8% | **88.2%** |
| 執行時間 | 6,010 秒 | **2,320 秒**（2.4 倍加速） |
| Token 用量 | — | **少 75.6%** |

比單點數字更值得注意的是趨勢：**遞迴圈數愈多，RecursiveMAS 的成本優勢愈誇張**。文字版每多繞一圈就得多付一輪完整的解碼開銷，時間和 token 都是往上疊的；RecursiveMAS 把溝通壓力轉移到極輕量的向量空間，多繞一圈的邊際成本小得多。

![三張並排的長條圖，分別對應遞迴第 1、2、3 圈，比較 RecursiveMAS 與 Recursive-TextMAS 的 token 用量倍率，隨著圈數增加，差距從平均 34.6% 拉大到 75.6%。](img-009)
*圖八 — Token 節省率隨遞迴圈數放大：第 1 圈省 34.6%，第 3 圈省到 75.6%。（來源：原始論文。）*

### 遞迴系統也有自己的 scaling law

![上半部是四張熱力圖，橫軸為訓練遞迴圈數、縱軸為推論遞迴圈數，顏色愈深代表準確率愈高，右上角最深；下半部是三組長條圖，分別對應混合型、深思熟慮型、蒸餾型三種協作模式下各角色與 RecursiveMAS 的準確率比較。](img-001)
*圖九 — 上半：訓練與推論圈數的效能地形圖。下半：三種協作模式下的表現。（來源：原始論文。）*

熱力圖要橫著看也要豎著看。橫著看是 **test-time compute scaling**：同一個訓練好的模型，推論時多繞幾圈，準確率就穩定往上。豎著看則是訓練圈數的效果。兩者同步增加時，系統會落在圖的右上高地——代表訓練時經歷過深度遞迴洗禮的模型，更懂得怎麼利用推論時的遞迴步數去修正錯誤。

這跟現在追求「增加思考時間」的推理模型是同一個思路，差別在 RecursiveMAS 是在資源便宜得多的潛在空間裡完成的。

下半部則說明架構不挑陣型：

- **混合型（Mixture）**：數學、程式、科學專家平行協作，準確率比單一最強專家高出 6.2%。
- **蒸餾型（Distillation）**：大專家帶小學生，小模型準確率提升 8.0%，同時還保有 1.5 倍的速度優勢。
- **深思熟慮型（Deliberation）**：引入外部搜尋與程式執行，即使必須跟外部文字互動，仍能在搜尋前用向量互動減少無效嘗試。

### 那些向量真的不是雜訊嗎？

這是個很合理的疑問——中間傳的東西人看不懂，你怎麼知道模型不是在傳隨機噪音？作者用 PCA 把每一圈產生的潛在思考向量投影到 2D 平面來回答。

![三張並排的散佈圖，分別對應遞迴第 1、2、3 圈，橘色點是 RecursiveMAS 產生的語意分佈、藍紫色點是標準答案的分佈，兩組虛線橢圓從第一圈的明顯錯開逐漸靠攏到第三圈的幾乎重合。](img-011)
*圖十 — 三圈下來，生成答案的語意分佈逐步收斂到標準答案的分佈上。（來源：原始論文。）*

第一圈時，生成分佈和標準答案分佈明顯錯開（想法還很模糊）；第二圈開始重疊，偏移縮小；到第三圈幾乎完全重合。

這個結果的說服力在於，它把「遞迴」這個抽象操作跟一個看得見的過程對應起來了：遞迴就是**語意精煉**。模型透過每一圈的互動，在潛在空間中不斷修正自己的座標，直到鎖定正確答案的語意中心。

## 七、代價與尚未解決的問題

這套設計不是沒有代價，最直接的一個就是**可讀性**。傳統 text-based MAS 有個隱形的好處：中間過程是人看得懂的文字，出事的時候你可以直接讀 log 看是哪一步想歪了。RecursiveMAS 把這層可讀性換成了效率——中間全是向量，除非額外做投影分析（像上面那張 PCA 圖），否則你很難知道系統第 2 圈在想什麼。對於需要稽核、需要除錯的正式系統，這是要先想清楚的取捨。

另外兩個是論文自己留下的開放問題：

**遞迴深度是固定的。** 目前圈數是超參數（例如 $r=3$），系統不會自己判斷「這題我想懂了，不用再繞了」。理想上這應該是動態的，簡單題早停、難題多繞，但論文沒做到這一步。

**目前只驗證了語言模態。** 如果傳遞的潛在向量不只包含語言邏輯，還能帶上視覺特徵，這套框架理論上可以延伸成多模態團隊——但這還只是方向，不是結果。

## 結論

RecursiveMAS 的核心動作只有一個：**把 Agent 之間的溝通媒介從離散文字換成連續向量**。但這一換帶來三個連鎖效果。

省掉 LM head 投影和重新 prefill 的開銷，讓多輪遞迴反而比文字版更快、更省 token，而且圈數愈多優勢愈明顯。溝通路徑變成可微的，整個 MAS 可以當成一張計算圖做端到端訓練，梯度跨 Agent、跨圈數地累加，系統真的學得到「團隊默契」而不只是個別能力。而支撐這一切的只有那個帶殘差的小小 RecursiveLink——不到 0.31% 的可訓練參數，主體模型全程凍結。

代價是中間過程不再是人看得懂的文字。這在追求極致效率的場景值得換，在需要稽核與除錯的場景就得三思。
```figure-map
[
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2 | Overall Architecture of RecursiveMAS. Each agent first leverages the inner RecursiveLink to perform latent thoughts generation, and then transfers the generated information to the next agent through the outer RecursiveLink. After the last agent finishes generation, its latent thoughts are fed back to the first agent, thereby forming a recursive loop within the multi-agent system.",
    "why_used": "作為核心概念一節的開場圖，讓讀者先看到 Inner Link 自我循環、Outer Link 跨 Agent 傳遞、以及整體 looping 的關係。",
    "agent_match_hint": "一張架構示意圖，兩個灰色大方框標示 Agent A1 與 Agent A2，下方有標示 Inner Link 與 Outer Link 的橫向色塊，右側有一個 Looping 的循環箭頭圖示。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 3 | Illustration on the inner and outer RecursiveLink Design.",
    "why_used": "支撐 Inner 與 Outer RecursiveLink 的結構對照，讓讀者一眼看出兩者只差一個投影矩陣。",
    "agent_match_hint": "一張左右對照的小圖，兩側都是 Linear、GELU、Linear 三個堆疊方塊加上一條標示 Residual Connection 的箭頭，右側殘差路徑上多一個直立的 Linear 方塊。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "Table 4 | Efficacy on RecursiveLink Design. We com- pare accuracy across alternative architectural designs.",
    "why_used": "支撐「殘差連接是關鍵」這個論點的消融數據，避免該段只停留在理論推導。",
    "agent_match_hint": "一張窄長的四列表格，欄位是 RecursiveLink Design、Math500、GPQA-D、LiveCodeBench，最後一列 Res+2-Layer (ours) 以粗體標示。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Figure 4 | Two-Stage Training Pipeline of RecursiveMAS. We first perform inner-loop training for each agent in parallel to warm up the inner RecursiveLink for latent thoughts generation, and then conduct outer-loop training to recursively optimize the outer RecursiveLink over the entire system.",
    "why_used": "訓練一節有兩個階段且前後有依賴關係，用流程圖比純文字更容易讓讀者建立整體結構。",
    "agent_match_hint": "一張上下分成兩個虛線大框的流程圖，上框標題為 Preliminary Inner-Loop Training，下框標題為 Recursive Outer-Loop Training，內含多列 Agent 方塊與藍色前向、紅色反向箭頭。"
  },
  {
    "id": "img-012",
    "references_manifest_caption": "Table 5 | Cost analysis on RecursiveMAS. We report the peak GPU memory usage (GB), number of trainable parameters, estimated cost, and average accuracy (%) across all downstream tasks.",
    "why_used": "支撐「只訓練 0.31% 參數、主體全程凍結」這個訓練成本論點，並與 LoRA、full-SFT 直接對照。",
    "agent_match_hint": "一張三列的表格，欄位是 Methods、GPU Mem.、Trainable Param.、Cost、Avg. Acc.，最後一列 RecursiveMAS 全部粗體。"
  },
  {
    "id": "img-013",
    "references_manifest_caption": "Figure 8 | Effectiveness of RecursiveMAS’s latent thoughts with different step lengths.",
    "why_used": "支撐「潛在步數 m 設在 80 步左右就夠」這個具體設定，說明它是消融出來的而不是隨手挑的。",
    "agent_match_hint": "一張折線圖，橫軸是 Latent Thoughts Length m 從 0 到 128，三條帶不同標記的曲線分別是 MATH500（綠色三角）、GPQA-D（橘色圓）、LiveCodeBench（紫色方塊），縱軸有斷軸符號。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 2 | Main results of RecursiveMAS over Different Recursion Rounds. We report the accuracy (%, “Acc.”), end-to-end runtime (s, “Time”), and overall token usage (“Token”) across domains. For",
    "why_used": "主結果表，同時涵蓋準確率、時間、token 三個維度，是「效率與準確率不再是蹺蹺板」這一節的數據來源。",
    "agent_match_hint": "一張大表格，分成三個以灰底列分隔的區塊（Recursive Round r=1/2/3），每區塊兩組方法各三列指標，最右欄有綠底的改善幅度標示。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Figure 6 | Token Reduction of RecursiveMAS across Three Recursion Rounds. As recursion deepens, RecursiveMAS reduces substantially more tokens than Recursive-TextMAS.",
    "why_used": "支撐「遞迴圈數愈多、成本優勢愈誇張」這個趨勢論點，比單一數字更能說明邊際成本的差異。",
    "agent_match_hint": "三張並排的長條圖，每張都有灰色與藍色成對的柱子，橫軸是六個基準名稱，右上角以藍色大字標示平均節省百分比。"
  },
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1 | Performance Landscape of RecursiveMAS across Training/Inference Recursion Depths (Top): The lightweight RecursiveMAS with sub-1.5B agents shows a clean scaling trend as recursion",
    "why_used": "一張圖同時支撐兩個論點：遞迴系統的 scaling law，以及跨三種協作模式的泛化性。",
    "agent_match_hint": "上下兩部分：上半是四張階梯狀的方格熱力圖，格內標有準確率數字；下半是三組長條圖，標題分別為 Mixture-Style、Deliberation-Style、Distillation-Style。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Figure 7 | Semantic Representations of RecursiveMAS across Differnt Recursion Rounds. We visualize the semantic distribution of the final answers generated by RecursiveMAS and the corre- sponding ground-truth across 500 questions. Increasing recursion rounds progressively aligns the generated distribution of RecursiveMAS with the ground truth distribution.",
    "why_used": "回答「中間傳的向量到底是不是雜訊」這個讀者一定會有的疑問，把遞迴對應到看得見的語意收斂過程。",
    "agent_match_hint": "三張並排的散佈圖，橘色與藍紫色兩群點，每張各有一紅一黑兩個虛線橢圓，圖內左下角以紅字標示 Round 1、Round 2、Round 3。"
  }
]
```
