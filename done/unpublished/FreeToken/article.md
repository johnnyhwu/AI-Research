# FreeToken：把超大型 MoE 模型塞進一張消費級顯卡的工程手法

## 前言

如果你手上只有一張消費級顯卡，卻想跑一個上百億甚至上千億參數的 MoE（Mixture-of-Experts）模型，通常會卡在同一個地方：模型的專家（expert）權重太大，裝不進 GPU 的顯示記憶體（VRAM）。FreeToken 是 UC Berkeley、MIT、Databricks 等機構合作的一篇 2026 年 8 月論文，處理的正是這個問題——它讓單張 RTX PRO 6000 就能跑一個 753B 參數的 GLM-5.2，甚至連 8GB VRAM 的筆電顯卡也能服務中型 MoE 模型。

這篇文章會先說明 FreeToken 解決的三個痛點，再逐一拆解它在 prefill（讀 prompt）跟 decode（逐字生成）兩個階段各自用了什麼機制，最後看它的實驗數字，並誠實評估這篇論文的價值到底在哪裡。先講結論：**這篇論文的工程整合價值很高，但研究原創度不高**——用到的每一項底層技巧都是計算機系統裡的經典手法，真正屬於這篇論文自己的，是判斷怎麼把這些技巧組合起來、套用在「MoE + 消費級硬體限制」這個特定情境。

![FreeToken 在成本與能力的 Pareto frontier 上，用消費級硬體達到跟雲端 API 相近的服務水準；右側則是不同硬體等級下實測的 decode 速度。](img-001)
*圖 1 — FreeToken 服務的模型落在成本與能力的效率前緣上，且能在消費級硬體上做到互動等級的速度。*

## 一、背景知識：MoE 一層裡實際發生什麼事

現在的大型語言模型，一層（layer）通常是先過 self-attention，再過一個前饋網路（FFN）。MoE 架構把「一個 FFN」換成「一整組（可能上百個）FFN」，每一個都叫做一個 expert。一個 token 通過這一層時，不會用到全部 expert，而是先經過一個路由器（router），選出分數最高的 top-$k$ 個 expert（例如 $k=12$，總共 64 個可選），把這 $k$ 個 expert 各自的輸出做加權平均後合併輸出。

這代表：雖然每個 token 只碰一小部分 expert，運算是稀疏的，但完整模型仍然得把**所有**expert 的權重都存起來——這正是 MoE 在邊緣裝置上難以服務的根源：算得動，但裝不下。論文舉的例子是 DeepSeek-V4-Flash：每層 256 個 expert 選 6 個，總共 284B 參數，但單一 token 只用到 13B；問題是完整的 284B 參數（FP4 精度下約 140GB）還是得找地方放。

### PCIe：GPU 與主機之間的搬運通道

PCIe（PCI Express）是主機板上通用的高速匯流排標準，不是專為 CPU-GPU 設計的——SSD、網卡也走 PCIe。但在獨立顯卡的場景下，「GPU 記憶體」和「主機記憶體」之間交換資料走的就是這條通道，所以在 MoE serving 的脈絡下，「PCIe 頻寬」可以直接理解成「GPU 跟 CPU 之間搬資料的速度上限」。對照組：資料中心的 GPU 之間常用 NVLink 這種更快的專屬互聯，頻寬比消費級 PCIe 高一個數量級以上，這也是消費級硬體沒辦法像資料中心那樣輕鬆處理龐大模型的原因之一。

## 二、FreeToken 要解決的三個痛點

**痛點一：Prefill 階段的傳輸量是物理限制，搬不掉。** Prefill 是模型一次讀完一大段 prompt、產生 KV cache 的階段。因為 prompt 裡成千上萬個 token 各自路由到不同 expert，整體聯集幾乎會覆蓋這一層所有的 expert——所以 prefill 幾乎要把整個專家池搬過 PCIe 一次。以 DeepSeek-V4-Flash 為例，完整專家池（FP4）約 140GB，除以 RTX 5090 的 PCIe 理論頻寬（約 60GB/s；後面 Memory-bound 那段會看到，論文實測的頻寬其實更低，只有 49-53 GB/s），要花兩秒多——用理論頻寬算只是抓個數量級，實際搬運時間會比這裡算出來的更長。這是硬性的物理限制，沒辦法用排程技巧消除，只能設法別讓 GPU 空等。

**痛點二：Decode 階段每一步都可能要臨時搬 expert，且沒有分配原則。** Decode 一次只處理一個新 token，每一步只碰 top-$k$ 個 expert。GPU 上放不下全部 expert，常會遇到「這步要的 expert 不在 GPU 上」，也就是 cache miss。遇到 miss 有兩條路：把它搬過去 GPU 算，或直接在 CPU 上原地算。llama.cpp、KTransformers 等現有系統沒有原則性方法決定這兩條路該怎麼分配。

**痛點三：個人電腦的 GPU 資源不是穩定專屬的。** 跟資料中心整張卡專屬服務一個任務不同，一般人的電腦上，GPU 常常同時被遊戲、瀏覽器等其他程式佔用。這代表 serving 引擎能用的 VRAM 額度，運行過程中會浮動，不是啟動時分配好就固定不變。

## 三、Prefill 階段：把搬運跟計算重疊起來

![FreeToken 的整體運作示意：prefill 階段用跨層 double buffering，decode 階段靠 LRU expert cache 加上頻寬平衡分配 miss。](img-002)
*圖 2 — FreeToken 的系統概觀：prefill 靠雙緩衝隱藏搬運延遲，decode 靠 LRU 快取加上頻寬分配公式決定 miss 的 expert 怎麼處理。*

### Full-layer Double Buffering

做法很直觀：VRAM 裡任何時刻只保留「當前層 + 下一層」兩層份的 expert 緩衝區，不是把整個模型塞進去。GPU 正在計算第 $l$ 層的同時，第 $l+1$ 層的全部 expert 正透過 PCIe 搬過來；等第 $l$ 層算完，兩個緩衝區角色互換，GPU 開始算第 $l+1$ 層，原本算完的那塊緩衝區被清空，開始接收第 $l+2$ 層的資料。

以 DeepSeek-V4-Flash 為例，完整專家池 140GB 除以 43 層，每層約 3.3GB，兩層合計 6-7GB——即使 8GB VRAM 的筆電顯卡也放得下，這就是為什麼不需要把整個模型塞進 GPU 的原因。這個緩衝池跟 decode 用的 expert cache 是共用同一個 slot pool，不是分開的兩套系統：prefill 結束後留在 GPU 上的 expert，decode 可以直接沿用。如果 VRAM 連兩層份的空間都擠不出來（例如同時開著吃 VRAM 的遊戲），FreeToken 會退回按需載入模式，犧牲管線化的好處換取不爆記憶體。

> **容易搞混的地方：double buffering 解決的不是「傳輸量太大」，而是「傳輸時間能不能被藏起來」。** 傳輸的總資料量沒有變小，140GB 該花的時間還是要花。Double buffering 只是讓 GPU 在等資料的同時順便算前一層，把傳輸時間和計算時間重疊，而不是消除傳輸。論文自己的實驗數字也印證這件事：關掉 double buffering，吞吐量只掉 19-26%（後面第七節會看到），如果它真的解決了「傳輸量太大」這個根本問題，關掉應該是災難性下降，而不是兩三成的損失。

老實說，double buffering 本身是系統領域幾十年歷史的通用技巧，FlexGen 等系統早就用在一般 dense model 上了。這裡的貢獻是工程判斷：MoE 的 prefill 階段幾乎用到全部 expert，與其花力氣預測哪些會被用到，不如整層全搬更划算，而且讓這個緩衝跟 decode cache 共用記憶體池，不用另外配一塊。

### Semantic-Aware State Cache

前沿模型（Qwen3.6 用 gated DeltaNet、Kimi-K3 用 Kimi Delta Attention）混用了一種跟標準 attention 完全不同的層，統稱線性注意力（linear attention）。奠基論文是 Katharopoulos 等人 2020 年的《Transformers are RNNs》，核心洞察是把 attention 用線性化的方式改寫，數學上等價於一個 RNN。

標準 attention 的每個 token 的 K、V 向量是獨立存放的，這就是 KV cache，可以事後任意切片重用——這正是 SGLang 的 radix prefix tree 能做「跨請求共享 prefix」的原因。線性注意力層完全不同：它不存每個 token 的 KV，而是維護一個固定大小、會不斷演化的狀態矩陣 $S$，新 token 進來時用「舊狀態 + 新 token」算出新狀態，舊的被覆蓋：

$$S_{new} = S_{old} + k_t v_t^\top$$

外積把 key、value 兩個向量變成一個矩陣，疊加進狀態裡。這帶來的關鍵性質是：資訊被壓縮進同一個矩陣，無法事後單獨抽出某一段的貢獻，也無法從後面的狀態反推更早的狀態。

這件事很麻煩，因為 agent 每一輪對話幾乎都會修改 context（刪掉舊的 thinking、舊的工具輸出），導致之前存的 checkpoint 失效。如果沒有可用的 checkpoint，整段就得重算。論文提到一份 checkpoint 的成本大約等於幾百個 token 份量的 KV cache，所以只能存少數幾個名額——標準 KV 存的是向量，大小跟 head 維度成正比；線性注意力的狀態存的是矩陣，大小跟 head 維度的平方成正比，形狀從向量變矩陣，量級差距自然被拉開（這是論文沒給出的直覺推導，非原文，僅供理解量級參考）。

**論文的解法叫 Semantic Anchors（語意錨點）。** 判斷邏輯來自觀察真實 agent 框架怎麼砍 context：OpenClaw 只留最新的 thinking，OpenCode 用固定佔位符替換舊的工具輸出，SWE-agent 只留最後 $n$ 筆觀察結果。這些框架砍的永遠是「一整個語意區塊」（一段完整的 thinking、一次完整的工具呼叫），不會砍到區塊中間，而這些區塊在 token 序列裡是用特殊 token 標記邊界的（如 `<think>...</think>`、`</tool_call>`）。

於是解法就是：checkpoint 存在**每一個**語意區塊的邊界上，不是只存一個固定位置，也不是預測哪一段會被砍。因為每個邊界都存了 checkpoint，不管 agent 這一輪實際砍的是哪一段，「保留下來的 prefix 結尾」必然會落在某個曾經存過的邊界上——完全不需要預測會砍哪裡，只需要重算被砍掉、新加進來的那一小段。Checkpoint 名額用 LRU 回收，跟 KV cache 的 radix tree 是分開管理、獨立運作的兩套機制。

> 這裡論文有個沒交代清楚的地方：這些模型在原生（非 FreeToken）serving 方式下，線性注意力狀態原本是怎麼做 prefix reuse 或 checkpoint 的，論文完全沒有提到，值得之後獨立查證。

## 四、Decode 階段：每一步該怎麼分配資源

### LRU Expert Cache

核心觀察是：decode 時，相鄰步驟（同一層、不同 token）選中的 expert 有很高的重疊率——這是論文引用的「路由一致性」實證觀察（Liang et al., 2025）。FreeToken 用最普通的 LRU（Least Recently Used）策略管理 GPU 上的 expert cache，不做任何預測。

舉個例子：假設 cache 有 12 個 slot，上一步用到 E3、E7、E9、E12、E17、E24、E5、E22、E48、E51、E60、E33，這一步要用的 expert 裡有 8 個跟上一步重複（直接命中），剩下 4 個是新的（miss）。LRU 順便淘汰最久沒被用到的 4 個 slot，騰出空間。

要注意這裡「相鄰步驟」指的是**同一層、不同解碼步驟**，不是跨層。能不能像 prefill 那樣做跨層 double buffering，提前搬下一層要用的 expert？不行，原因是資料依賴：下一層要選哪個 expert，必須等這一層算出輸出、經過路由器才知道，這跟 prefill「反正幾乎全部都要用到，可以無腦全搬」完全不同。此外，cache 裡每個 slot 記錄的是一個「（層、expert）」配對，不是單純的 expert 編號，所以第 1 層的 E5 跟第 43 層的 E5 是兩筆完全獨立的記錄，不會互搶同一個 slot。

論文自己做了一個乾淨的驗證：拿同一組真實 routing 記錄，重播三種引擎的 placement 策略，在相同 cache 容量下比較 miss 率。

| Placement 策略 | 更新頻率 | Qwen3.6 miss 率 | DeepSeek-V4-Flash miss 率 |
|---|---|---|---|
| FreeToken（全域 LRU） | 每一步都更新 | 16% | 39% |
| KTransformers（prefill 時更新一次） | 只在 prefill 更新，之後固定 | 41% | 59% |
| llama.cpp（啟動時固定分配） | 從不更新 | 62% | 89% |

規律很清楚：策略跟現實的脫節程度越高，miss 率越高。因為相鄰 token 的路由高度重疊，「最近用過的 expert」是預測「下一步會不會再用到」最有效的線索，更新頻率越低，就越無法反映 decode 過程中實際發生的路由變化。值得追問的是：一個幾十年來就用在作業系統分頁替換、CPU 快取的老演算法，搬到 MoE serving 上為什麼管用？答案在於 MoE 路由剛好具備適合 LRU 發揮的時間局部性——這個觀察，才是這裡真正的貢獻。

### $q^*$ 頻寬分配公式

LRU cache 沒接住的 $m$ 個 miss，有兩條路：搬去 GPU 算（cache fill，以後留在 cache 裡），或留在 CPU 原地算（算完就算完，不留存）。關鍵洞察是：這兩條路徑其實在搶同一個資源——主機記憶體頻寬。搬去 GPU 要先從 DRAM 讀出來再送過 PCIe；CPU 原地算也要從 DRAM 讀出來才能算，兩者都得跟同一個主機頻寬池搶資料。全部走 PCIe 會把主機頻寬吃滿、CPU 反而讀不到資料；全部留 CPU 算，PCIe 又完全閒置浪費。

論文定義了幾個符號：$m$ 是這一步這一層總共 miss 的 expert 數量，$q$ 是決定走「搬去 GPU」這條路的數量，$m-q$ 是走「CPU 原地算」的數量，$S$ 是一個完整 expert 的權重大小，$B_{PCIe}$ 是實測 PCIe 傳輸頻寬，$B_{Host}$ 是實測 CPU 執行 expert 運算的等效頻寬。

搬 $q$ 個過 PCIe 要花的時間約為 $T_{fill}(q) \approx q S / B_{PCIe}$。PCIe 傳輸會佔走部分主機頻寬，CPU 只能用剩下的，所以 $T_{cpu}(m-q) \approx (m-q) S / (B_{Host} - B_{PCIe})$。兩條路徑同時進行，整體延遲取決於較慢的那條；最理想的狀態是兩條路徑花的時間一樣長，令 $T_{fill} = T_{cpu}$，可以解出：

$$q^* \approx m \times \frac{B_{PCIe}}{B_{Host}}$$

拿圖 2 的例子完整走一次：$m=4$，圖上標註實測 $B_{PCIe} : B_{Host} \approx 1:4$，代入得 $q^* = 4 \times (1/4) = 1$。驗證：圖 2 畫的正是 4 個 miss 裡「1 個走 fill」「3 個走 CPU 原地算」，跟公式算出的結果吻合。

這個公式在兩個極端下也說得通：$B_{Host}$ 趨近 $B_{PCIe}$（兩條路徑速度差不多）時，$q^*$ 趨近 $m$，全部搬去 GPU，退化成單純 cache fill；$B_{Host}$ 遠大於 $B_{PCIe}$（PCIe 是瓶頸）時，$q^*$ 趨近 0，幾乎都留 CPU 算。工程細節上，$q^*$ 算出來會取整數，且無論如何至少保留 1 個 fill，讓 cache 持續「暖身」，不會因為某一步算出 0 就完全停止更新。

#### Memory-bound vs Compute-bound：這次討論最重要的觀念修正

第一直覺可能是：GPU 運算能力遠勝 CPU，為什麼公式算出來反而是大部分 miss 留在 CPU 上算？

答案是：$q^*$ 這個公式從頭到尾比較的不是「誰算得快」（compute，FLOPS），而是「誰能把資料送到位」（memory bandwidth，頻寬）。GPU 的浮點運算能力確實遠超 CPU，這點沒有錯，但 decode 階段有一個關鍵性質：一個 token 對一個 expert 權重只用一次，不會重複利用來做很多次運算。這種「讀一次權重、只做一次矩陣運算」的模式，在電腦體系結構裡叫 memory-bound（記憶體頻寬受限）：運算單元大部分時間是在等資料從記憶體送過來，而不是在忙著算，運算能力再強，資料沒到位也只能空轉等。

![論文測試系統的實測頻寬數字：PCIe 頻寬與主機端頻寬處在同一個數量級。](img-003)
*表 1 — 六台測試機器的實測頻寬：PCIe 傳輸頻寬（$B_{PCIe}$）跟 CPU 端 expert 運算等效頻寬（$B_{Host}$）。*

拿論文表 1 的實測數字看差距有多小：RTX 5090 的顯存自身頻寬有 1-1.8 TB/s，非常快，但這是「顯存內部」頻寬，不是這裡的瓶頸；真正決定速度的是 PCIe 5.0 x16 實測頻寬，約 49-53 GB/s；而主機 DDR5 雙通道實測頻寬約 53.8-77.3 GB/s。$B_{PCIe}$ 跟 $B_{Host}$ 其實是同一個數量級，$B_{Host}$ 甚至常常略高。GPU 顯存本身 1-1.8TB/s 的高頻寬完全用不上，因為權重根本還沒送到顯存，就已經卡在 PCIe 這道窄門上了。

一句話總結：把一個 expert 搬進 GPU、再享受 GPU 高速運算，瓶頸出在「搬」這一步，不是「算」這一步。既然搬跟直接在 CPU 上算，用的是差不多速度的資源，不如省下 PCIe 這一趟，直接在 CPU 上就地算掉更划算。GPU 算力快，不等於「用 GPU 處理這個 miss」就快——決定速度的是資料能不能送到手上，不是手腳快不快。

## 五、CUDA Graph 相容的動態決策設計

這是論文工程含金量最高的部分，也是最值得花時間搞懂的地方。以下從最基礎的背景概念開始鋪陳。

### 為什麼 GPU 下指令有固定成本

GPU 自己不會主動做事，永遠是被動等指令的角色，CPU 才是指揮全局的角色。可以想像 CPU 像廚房主廚，GPU 像一台超級快的切菜機：主廚每一步都要開口下令「切菜機，把這把菜切一切」，切菜機才會動作；切完了，主廚要親自檢查、決定下一步，再下一個新指令。

GPU 世界的「kernel」跟作業系統核心是完全不同的兩個概念，只是借用了同一個英文單字——GPU 的 kernel 指的是一段會在 GPU 上由成千上萬個執行緒同時平行執行的函式。比如把兩個各有 100 萬個元素的陣列逐一相加，CPU 做法是寫一個迴圈依序算 100 萬次；GPU 做法是寫一個 kernel 描述「單一一個元素該怎麼算」，再由 CPU 端下指令「啟動 100 萬個執行緒，每個都跑這個 kernel」，這個啟動的動作就叫 kernel launch。

為什麼每次 kernel launch 本身要花固定的時間成本？大致的路徑是：CPU 先準備指令（打包參數、記憶體位置），驅動程式做核對跟排程，再透過 PCIe 把「要做什麼」的訊息送到 GPU（這裡搬的是很小的指令封包，跟搬 expert 權重那種 GB 等級的資料完全不同量級），GPU 收到後排進自己的執行佇列，才真正開始執行運算。

時間成本主要集中在前面幾段：準備、排程、傳遞，不是最後的「真正運算」。每次通訊都有一個固定的起步延遲，不管傳的資料是 1 byte 還是 1000 bytes，這個延遲都差不多存在（單次 kernel launch 的固定開銷量級大約在微秒等級，這是一般計算機系統知識，非論文提供的具體數字）。

這解釋了為什麼 decode 特別受傷：decode 每一步的實際運算量很小（一個 token，一層，只碰 top-$k$ 個 expert），運算本身花的時間可能跟這個固定起步延遲是同一個量級，「傳令」的固定成本佔比會被放得很大。相對地，prefill 一次處理幾千個 token，運算量本身很大，固定的傳令成本相對可以忽略。而且一個模型有 43 層，一次生成可能要跑幾百、幾千個 token，每層又不只一個 kernel（QKV 投影、softmax、輸出投影、FFN⋯⋯），零碎的啟動次數會非常可觀。

### CUDA Graph：錄製與重放

核心想法是：與其每次都重新一個一個 kernel 分別下令，不如把整串固定的 kernel 呼叫順序「錄」一次，之後要重複執行時直接「重放」，不用每個 kernel 都重新走一次完整的傳令流程。延續切菜機的比喻：主廚每天早上都要對切菜機喊同一套指令「切紅蘿蔔→切洋蔥→切馬鈴薯」，與其每天重新喊三次，不如先把這三句話錄成一捲錄音帶，之後每天早上按一次播放鍵，整捲自動依序播完。

底層具體發生的事（capture 階段）：不是錄「程式碼本身」，而是把一連串 kernel launch 各自變成一個節點（node），把它們之間的依賴關係變成邊（edge），組成一個有向無環圖（DAG）。圖裡記錄的內容包括每個節點對應哪個 kernel、要開多少執行緒、用到的記憶體位址，以及節點跟節點之間的先後順序關係。這張圖錄製完成後，會被編譯成 GPU 驅動程式看得懂的低階描述，存放在 GPU 那一側。

重放階段省下的是：沒有 Graph 時，每個 kernel launch 都要重新走一次「CPU 準備 → 驅動驗證/排程 → PCIe 傳遞 → GPU 排隊」的完整路徑；有了 Graph，CPU 只需要送出一個指令——「執行編號 X 的這張已編譯好的圖」，GPU 驅動程式直接按照圖裡記錄好的節點順序依序執行，這個排程過程發生在驅動程式那一側，不需要 CPU 每個節點都重新介入。

**為什麼「形狀不能變」是必要條件？** 沒有 Graph 時，驅動程式每次呼叫 kernel 都要重新做一次合法性驗證跟排程規劃（參數對不對、記憶體位置有沒有衝突、跟前一個 kernel 的依賴關係怎麼安排），這些驗證本身也要花時間。Graph 的做法是把這些工作提前在 capture 階段做一次，結果存起來重複使用；之後每次重放，因為圖的結構保證跟錄製時一模一樣，驅動程式不需要重新驗證，直接照抄之前算好的排程結果執行。一旦允許形狀改變（這次多插入一個 kernel，或某節點的執行緒數量變了），驅動程式就沒辦法安全地照抄之前的排程結果，等於失去了 Graph 想省下來的成本。

這也是為什麼 Graph 不能有分支：「如果發生 A 情況就做 X，如果發生 B 情況就做 Y」這種需要臨時判斷的邏輯，CUDA Graph 沒辦法錄，因為每次重放，實際會發生的 kernel 順序都可能不同，已經不是同一張固定的圖了。這正是 FreeToken 遇到的矛盾：decode 每一步，miss 的數量、要 fill 幾個、該淘汰哪個 expert，全部要等路由結果出來才知道。論文自己在相關工作也點名對照組的弱點在這裡——KTransformers 和 llama.cpp 都沒辦法在混合式（CPU+GPU）執行模式下維持 CUDA Graph 重放，因為排程決策留在 CPU 端做。

### 把動態決策塞進靜態圖的五個步驟

核心策略一句話：不管這一步 miss 幾個，永遠固定跑「同一組」kernel，只是這組 kernel 內部處理的資料量、內容不同——用固定大小緩衝區加一個「有效數量」標記，取代 if/else 分支。緩衝區永遠固定配置成「最多 12 個」（top-$k=12$）：如果這一步只 miss 4 個，前 4 格是真的資料，valid_count 標記為 4，剩下的格子空著也沒關係；下一步 miss 7 個，valid_count 就變成 7。

不管這一步 miss 幾個，緩衝區的形狀永遠一樣，對應的 kernel 呼叫也永遠是同一個、同樣的執行緒配置，圖的結構完全沒變，只是內部讀到的數字不同。論文原文的說法是「動態的控制邏輯，被表示成靜態圖裡流動的資料」：原本會寫成 if/else 分支的邏輯，改寫成「永遠執行、用一個數字欄位標記真正有效的部分是多少」。

每一層的決策具體拆成五步：

**步驟一：去重（deduplication）。** MoE 的路由是每個 attention head 各自獨立選 top-$k$，不同 head 選出的 expert 可能重複。如果不去重，同一個 expert 會被檢查好幾次，系統誤以為要處理好幾次，實際上只需要處理一次——因為不管幾個 head 用到它，這個 expert 的權重只有一份。

GPU 上怎麼平行做去重？標準解法是先排序：排序完之後重複的數字會自動變成相鄰，只需要拿每個元素跟前一個比較一次，就能平行判斷是否重複。最後用一次前綴和（prefix sum），算出每個保留元素該落在去重後陣列的第幾個位置。

這三個步驟——排序、相鄰比較、前綴和——都是「對固定大小的陣列套用同一種運算」，不管原始資料重複了幾次，要跑的動作都固定，只是處理的數值內容不同。這裡用的是 Hillis-Steele 平行 prefix sum（用倍增取代逐一累加，$\log n$ 輪解決）。

**步驟二：分類 hit/miss。** 去重後拿到一份不重複的 expert 清單，逐一比對「目前 cache 裡有什麼」的對照表，標記每個是 hit 還是 miss。如果對照表是雜湊表或直接定址陣列，每個執行緒可以完全獨立平行檢查自己負責的那個 expert 是否存在，不需要跟其他執行緒溝通。

**步驟三：算出 $q$。** 用前面的 $q^*$ 公式，是一個純量對純量的乘除法，不管 $m$ 是 2 還是 200，運算量都一樣小，這一步本身不需要平行。但即使不需要平行，這一步仍然必須留在 GPU 上做，不能丟給 CPU——原因不是效能（這一步耗時極短），而是圖形完整性：如果讓 CPU 算這個簡單的乘除法，會需要「GPU 算出 $m$ → 傳回 CPU → CPU 算 $q$ → 傳回 GPU」這個來回，中間會產生同步等待，打斷整條路徑被完整錄進同一張 CUDA Graph 的可能性。要不要平行是效能考量，要不要放在 GPU 上是圖形完整性的考量，這是兩個獨立的判斷維度。

**步驟四：選 LRU 淘汰候選。** 要淘汰的數量恆等於要 fill 的數量 $q$。如果做法是「淘汰一個 → 重新掃描找下一個最舊的 → 再淘汰」，這個「要掃幾遍」的次數會跟著 $q$ 變動，違反圖的形狀不能隨資料內容改變的原則。解法是一次排序，找出完整的淘汰候選名次表，之後不管 $q$ 是多少，永遠只需要讀取排序結果的前 $q$ 名，是 $O(1)$ 的讀取，不需要因為 $q$ 變大就重新掃描。

**步驟五：轉換成實體 slot 編號。** 前四步用的都是 expert 的邏輯編號，但 GPU 硬體實際執行運算需要的是「這個 expert 的資料放在 GPU 記憶體的哪個實際位址」。這一步把邏輯編號轉換成具體指令：hit 的 expert 直接標記各自對應的既有 slot；被選中要 fill 的 miss expert，標記「從主機搬進某個 slot」；剩下留 CPU 算的 miss expert，標記「不進 GPU cache，送去 CPU 執行」。這一步同樣完全平行，每個 expert 各自查一次自己該對應到哪個實體位置或標記，彼此獨立。

值得一提的是，CPU 那一路也被納入同一張圖：GPU 把需要的資料複製到 CPU、透過一個 host function 通知 CPU 開始算、CPU 算完再複製回來。這整條路徑跟 GPU 自己那條路一起被錄進圖裡同步重放，兩條路徑真正並行，而不是「GPU 做完才輪到通知 CPU」。

### 一個 Token 生成時實際發生的事

一整張 CUDA Graph 錄的不只是一層，而是「一個 token 要走完全部層（例如 43 層）」的完整流程：每一層都是 attention kernel → 五步驟決策 → 搬資料/GPU 算/CPU 算 → 合併輸出，43 層跑完才輸出這個 token 的機率分佈。每一個新 token 要生成時，都是重放同一張圖一次，不是每個 token 都重新錄一次——錄製只需要在引擎啟動、暖機時做一次，一個回應可能要生成幾百、幾千個 token，每個都重複利用同一張已錄好的圖。圖的結構保持不變，重放時真正變的只是緩衝區裡填的數字內容（這一步的 $m$、$q$、要搬哪個 expert）。

> 這整套五步驟決策機制完全是針對 MoE 架構的「expert 選擇」設計的，如果模型不是 MoE，這套機制不適用。這不是論文的疏漏，而是研究範圍本來就設定在這裡——標題就寫著「Edge-Native MoE Serving」。Dense 模型每層是固定的 FFN，沒有「選 expert」這回事，遇到模型太大裝不下的問題，要用完全不同的技巧（按層分布、量化等）解決。
>
> 論文另外一個沒交代的地方：prefill 階段的 double buffering kernel 呼叫，是否也被錄進 CUDA Graph，論文完全沒有明講，相關章節只聚焦在 decode 的五步驟機制上。

## 六、彈性記憶體管理

除了前面兩大塊機制，論文還簡短提到兩個資源管理手法，概念上都是系統工程裡常見的做法，沒有特別的巧思。

**Runtime cache reconfiguration：** GPU 記憶體要分給 KV cache 跟 expert cache 兩塊，這個劃分不是啟動時固定的。在排程器認定安全的時間點，FreeToken 可以重新計算兩塊的比例並重建 expert cache 大小，不需要重啟引擎、不需要重新讀取 CPU 端完整的 expert pool——因為 CPU 端那份才是正確答案的唯一來源，GPU 上的 cache 只是加速用的副本，重建只影響效能，不影響正確性。（論文沒有具體說明重新配置 VRAM 預算時 KV cache 那塊怎麼被同步調整，只提到兩者共享同一塊可調整的 VRAM 預算。）

**Fast engine bootstrap：** 讀取硬碟資料時直接讀進最終要用的記憶體格式，省掉一次多餘的搬運；完全不做 GPU 暖機，直接開始服務第一個請求，cache 在正常服務過程中自然「變熱」——用的就是 decode 階段本來就有的 miss 處理機制。

## 七、實驗結果怎麼說

實驗設置：六台機器，從 8GB 筆電顯卡到工作站級 RTX PRO 6000 都有，對照組是 llama.cpp、Ollama、KTransformers、MoE-Infinity，用四個真實 agent workload（數學推理、兩種 coding agent、email/calendar agent）測試——不是合成 benchmark，這點算是加分項。

### 整體效能

![四個真實 agent workload、兩個模型下，FreeToken 跟各對照組引擎的 decode TPS 與 mean TTFT 比較。](img-004)
*圖 3 — RTX 5090 上，跨四個 workload 與兩個模型的端到端服務表現，上排是 decode 速度、下排是首個 token 延遲（對數座標）。*

在 RTX 5090 上，FreeToken 的 decode 吞吐量比最強對照組快 1.5-2.3 倍（Qwen3.6 是 77-83 tok/s，DeepSeek-V4-Flash 是 22-25 tok/s）。多輪 agent 場景下吞吐量只比單輪掉 12% 以內，而 KTransformers 在 DeepSeek-V4-Flash 上從單輪到第二輪就已經掉了 31%，印證了前面提到的「context 被砍要重算」問題確實拖累對照組。

尾端延遲（TTFT）差距更大：FreeToken 最差情況控制在 44 秒內，對照組某些情境拉到 150 秒以上，KTransformers 最差甚至到 946 秒，長到會被真實 agent 客戶端的逾時機制直接中斷連線。

### 三個拆解實驗

論文另外做了三個拆解實驗，分別驗證各個機制的貢獻：

![關掉 double buffering 之後 prefill 吞吐量隨 prompt 長度變化，以及 decode-time expert miss 率隨 cache 大小變化的比較。](img-005)
*圖 4 —（a）有無 double buffering 的 prefill 吞吐量對比；（b）三種引擎 placement 策略下的 decode-time miss 率對比。*

- **Double buffering 的貢獻：** 關掉它，prefill 吞吐量在長 prompt 時掉 19-26%，符合前面「隱藏延遲、非消除延遲」的預期，不是災難性下降。
- **Cache locality 的貢獻：** 這是驗證得最乾淨的部分，就是第四節那張 miss 率表——LRU 在相同容量下 miss 率明顯低於對照組。

![五台不同等級的消費級 GPU 上，FreeToken 對比其他引擎的 coding-agent decode 速度。](img-006)
*圖 5 — 跨五台消費級 GPU 的 coding-agent decode 速度對比，優勢在不同硬體等級上維持穩定。*

- **跨硬體穩定性：** 五台不同等級消費機器上，優勢維持在 1.3-2.1 倍，不是只在特定硬體上調校出來的數字。

### 實驗驗證的缺口

誠實地說，這篇論文的實驗也有明顯的缺口。**$q^*$ 頻寬分配公式從未被單獨拆出來做消融實驗。** 所有端到端數字，永遠是「LRU cache + $q^*$ policy」綁在一起報的，沒辦法回答「如果只用 LRU cache、但 miss 全部走 CPU（不做頻寬分配），效能會差多少」——這是論文最像原創計算的部分，卻是驗證最薄弱的一環。另外，**論文沒有跟 vLLM 比較。** 對照組只有 llama.cpp、Ollama、KTransformers、MoE-Infinity 四個，論文也沒有交代原因；vLLM 在論文裡只被提到是 FreeToken 借用其架構理念的基礎，不是效能對照對象。

## 八、這篇論文教會我們的事

### 論文本身的貢獻，老實講有多少

核心手法——double buffering、LRU cache、頻寬平衡分配、CUDA Graph 動態化——全部是計算機系統裡的經典技巧，沒有一項是這篇論文發明的。這篇論文真正屬於自己的東西，是把這些技巧組合起來、套用在「MoE + 邊緣硬體限制」這個特定情境的工程判斷，特別是 $q^*$ 這個 closed-form 頻寬平衡公式（數學本身很簡單，但「用兩個實測頻寬算出最優分配比例，且輕量到能塞進 CUDA Graph」是有意義的設計選擇），以及把整套動態決策塞進 CUDA Graph 五步驟這件事，這是工程含金量最高的部分。

但如前面提到的驗證缺口，這部分的說服力仍打了折扣：工程整合的完整度，優於研究驗證的嚴謹度。

### 脫離這篇論文也成立的心法

這次讀下來，比 FreeToken 這個系統本身更值得留下的，其實是幾個可以遷移到其他場景的思維方式。

**Memory-bound vs. compute-bound 的區分。** GPU 算力遠勝 CPU，不代表「用 GPU 處理某個任務」一定比較快——當瓶頸在「資料能不能及時送到手上」而非「算得快不快」時，運算單元的強弱不是決定性因素。這是這次討論裡最顛覆直覺的觀念，適用範圍遠超過 MoE serving，任何牽涉到資料搬運跟運算並存的系統設計都用得上。

**Kernel launch 的固定開銷，以及用「錄製+重放」把它攤平。** 傳令的固定延遲跟資料量大小無關，這是理解 GPU 效能瓶頸的基礎概念；CUDA Graph 把它攤平的手法，本質上是任何「重複執行相同流程」場景都能借用的思路。

**用固定大小緩衝區 + valid_count 標記，取代 if/else 分支。** 這是 CUDA Graph 要求形狀固定、逼出來的設計模式，但它其實是一個可遷移到其他「需要平行化、又有動態行為」場景的通用思路，不限於 GPU 程式設計——任何需要批次處理、又想避免分支導致效能不可預期的系統，都可以借用這個「用資料表示控制邏輯」的想法。

**標準 KV cache 跟線性/遞迴注意力狀態的本質差異。** 前者可以事後任意切片重用，因為每個 token 獨立存；後者是不可逆壓縮，只能靠 checkpoint 補救。這解釋了為什麼「prefix reuse」問題在不同注意力機制下難度完全不同，也是理解現在「混合式注意力」架構設計取捨的一個好切入點。

**讀論文相關工作時，判斷「地基工具」跟「窄坑競品」的原則。** 有些系統（如 vLLM、SGLang）是整個領域共用的地基，值得單獨花時間深讀；同個 niche 裡的漸進式變體，通常讀相關工作摘要就夠了。這個判斷習慣本身，比記住任何一個具體系統的細節都更耐用。

## 結論

FreeToken 解決的是一個很實際的問題：消費級 GPU 記憶體裝不下超大型 MoE 模型的完整專家池。它的做法是把搬運（prefill 的 double buffering）、快取（decode 的 LRU expert cache）、資源分配（$q^*$ 頻寬平衡公式）這三個經典系統手法組合起來，再想辦法把整套動態決策塞進 CUDA Graph，讓 GPU 端的重放效率不被 CPU 端的判斷邏輯拖垮。實驗數字顯示這套組合在真實 agent workload 上確實有效，尤其是尾端延遲的改善相當可觀，但前面提到的驗證缺口，仍是這篇論文說服力上最大的短板。

如果只能記住一件事，那大概是：**這篇論文教會你的，與其說是「MoE serving 的新演算法」，不如說是「一套解決『動態決策 vs. 靜態圖執行』矛盾的工程思路」**——這個思路能遷移到很多跟 GPU 平行運算沾邊的場景，遠比 FreeToken 這個系統本身更有用。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1 FreeToken serves the models on the cost–capability Pareto frontier, at interactive speed on consumer hardware. (a) Blended API list price (9:1 input:output mix, following the token economics measured on real coding-agent traces (Zhu et al., 2026)) versus Code Arena Elo (LMArena, 2026) for representative hosted models. Blue squares mark models FreeToken serves, tagged with the consumer GPU class that serves them; the frontier segment from DeepSeek-V4-Flash to GLM-5.2 is exactly this set. Kimi-K3 releases open weights but exceeds consumer memory (594 GB); Qwen3.5-35B stands in for its successor Qwen3.6-35B, which has no arena rating yet. (b) Mean decode",
    "why_used": "作為前言的開場視覺，直接支撐『消費級硬體也能服務接近雲端 API 水準的模型』這個核心主張。",
    "agent_match_hint": "左側是成本對模型能力的散佈圖，標出效率前緣；右側是不同硬體等級的 decode 速度長條圖。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2 FreeToken overview. (1) Prefill: expert loading is double-buffered at full-layer granularity, streaming layer l+1 over PCIe while the GPU computes layer l; recurrent-state checkpoints are anchored at special-token boundaries, so a context edit resumes from the nearest surviving anchor and re-prefills only the new suffix. (2) Decode: most routed experts hit the shared LRU expert cache (here 8 of 12, following temporal locality). The m=4 misses are divided by q⋆= m BP/BH between cache fills over PCIe (one expert) and in-place CPU execution (three), using bandwidths profiled on the deployed machine; the GPU and CPU partial outputs merge exactly. The host-resident expert pool remains the source of truth throughout.",
    "why_used": "在介紹完 prefill 與 decode 兩階段機制的總覽段落插入，並在後面 q* 公式的具體例子（m=4, q*=1）中回頭引用圖中標註的數字。",
    "agent_match_hint": "系統架構示意圖，分成 Prefill 與 Decode 兩大區塊，畫出雙緩衝、context 編輯、LRU cache 命中/未命中、以及 CPU/GPU 分工的箭頭流程。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Table 1 Test systems. BP is the measured host-to-device expert-transfer bandwidth over PCIe; BH is the measured effective bandwidth of the CPU-side MoE expert kernel. On the three rented servers the CPU-thread and DRAM columns give container quotas.",
    "why_used": "支撐 memory-bound vs compute-bound 概念補充段落裡的實測頻寬數字，讓讀者看到 PCIe 頻寬跟主機頻寬確實在同一個量級。",
    "agent_match_hint": "一張表格，列出六台測試機器的 GPU 型號、VRAM 大小、PCIe 頻寬、CPU 型號與執行緒數、DRAM 大小與頻寬。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Figure 3 End-to-end serving on the RTX 5090 across four workloads (1. AIME, 2. OpenCode+SWE, 3. Claude Code+SWE, 4.OpenClaw+Email/Cal) and two models (Qwen3.6-35B-A3B BF16 and DeepSeek-V4-Flash MXFP4). Top: decode TPS; bottom: mean TTFT (log scale). × marks configurations an engine cannot serve (Ollama and MoE-Infinity lack DSV4 support; MoE-Infinity provides no usable server for multi-turn agents).",
    "why_used": "作為實驗結果一節的主要圖表，具體呈現 FreeToken 相對各對照組引擎在 decode 速度與首字延遲上的優勢幅度。",
    "agent_match_hint": "上下兩排長條圖，上排是 decode TPS、下排是 mean TTFT（對數座標），橫軸是四個 workload，分兩個模型、多個引擎比較，部分格子標了 × 代表無法服務。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Figure 4 (a) Prefill TPS versus prompt length (RTX 5090, Qwen3.6-35B BF16), with and without FreeToken’s pipelined full-layer loading. (b) Decode-time expert miss rate versus cache size (as a percentage of the expert pool) under the three engines’ placement policies, replayed on identical routing traces; lines are means over W1–W4, bands the min–max range.",
    "why_used": "支撐拆解實驗段落裡 double buffering 貢獻與 cache locality 貢獻兩項發現。",
    "agent_match_hint": "左圖是有無 double buffering 的 prefill 吞吐量折線圖（橫軸 prompt 長度）；右圖是三種引擎在不同 cache 大小下的 miss 率折線圖，兩個模型各一張。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Figure 5 Coding-agent decode TPS across consumer GPUs (SWE issues via the OpenCode harness), Qwen3.6-35B-A3B. 4060 laptop using NVFP4, the other Qwen3.6 columns BF16. The RTX PRO 6000 column is a separate demonstration: GLM-5.2 (753B-A40B, NVFP4) on the math workload; Ollama is not run there. × marks configurations an engine cannot serve.",
    "why_used": "支撐跨硬體穩定性這項拆解實驗發現，說明 FreeToken 的優勢不是只在特定硬體上調校出來的數字。",
    "agent_match_hint": "一張長條圖，橫軸是五種不同等級的消費級 GPU，比較 FreeToken 與其他引擎在 coding-agent workload 下的 decode 速度。"
  }
]
```
