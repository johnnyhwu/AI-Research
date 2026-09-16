# AI Coding Agent 到底把你的錢花在哪裡？一篇 16,000 條軌跡的實證拆解

## 前言

如果你把一張 SWE-bench 的 issue 丟給 coding agent，按下 Enter 的那一刻，你其實不知道自己要付多少錢。可能是零點幾美金，也可能是好幾塊。這篇文章要談的論文《How Do AI Agents Spend Your Money? Analyzing and Predicting Token Consumption in Agentic Coding Tasks》，就是在回答這件事。

它不提新模型、不提新演算法，而是把 8 款前沿模型在 500 個真實修 bug 任務上的 16,000 條執行軌跡攤開來，逐回合拆解 token 花在哪。文章分成兩半：前半是這份帳單長什麼樣子，後半是論文提出的一個新問題，也就是 agent 能不能在動手前先幫自己估價。最後我會把這些發現整理成幾個能直接用在系統設計上的做法。

## 實驗是怎麼做的

先把實驗設定講清楚，後面的數字才有意義。

**資料集用 SWE-bench-Verified**，也就是經過人類專家篩過的 500 個開源 GitHub 任務。選 Verified 而不是原始版的 SWE-bench，是為了把測試腳本本身有瑕疵的題目剔除掉。這樣一來，agent 沒修好就是它自己的問題，不是環境在扯後腿。

**Agent 框架用 OpenHands**，給模型一個可互動的 Linux 環境，能下 bash 指令、讀檔、跑單元測試。這裡有個關鍵細節：所有歷史對話與環境回饋，每一回合都原封不動往後累積傳遞。這個「只增不減」的設計，是後面所有成本現象的源頭。

**模型陣容有 8 款**：Claude Sonnet 3.7 / 4 / 4.5、GPT-5、GPT-5.2、Qwen3-Coder-480B-A35B-Instruct、Kimi-K2、Gemini-3-Pro。為了壓下 agent 本身的隨機性，每個模型在每題都跑 4 次獨立實驗，500 × 8 × 4 就是那 16,000 條軌跡。

資料萃取的粒度也拉得很細：

- **Token 分四類記**：output、non-cached input、cache creation、cache read（每一輪重新讀取已被快取的歷史，單價最便宜的一種）。
- **動作分四類記**：view file、modify file、execute terminal、call finish。
- **逐回合折算成美金**：依各家 API 的官方定價，含 prompt caching 折扣。

這種拆法是整篇研究能講出東西的基礎，只看總帳是看不出下面這些現象的。

## 第一件事：Agentic 任務的量級完全不同

Agentic coding 的 token 消耗是單輪程式推理問答（丟一題、回一個答案）的 **3500 倍**，是多輪程式對話（來回討論但不實際動手執行）的 **1200 倍**。這不是「比較貴」，是差了三個數量級。

![三類程式任務的 input/output 比例、平均 token 用量與平均成本對照，agentic 任務在三項上都遠高於另外兩類。](img-001)
*圖 1 — Agentic coding 與單輪推理、多輪對話的成本量級對照。差距主要來自 input token 的膨脹。（來源：原始論文）*

更重要的是錢花在哪一邊。一般人的直覺是模型寫愈多程式碼愈貴，但 agent 的成本幾乎完全由 input token 驅動，跟 output 沒什麼關係。

為什麼會這樣？說白了就是滾雪球。想像你在開一場會，每討論一個新議題，主席都要求全體「從第一頁會議紀錄開始重讀一遍」。OpenHands 就是這樣運作的：每一回合的工具回饋、每一次程式碼變更，全部疊進下一輪的 prompt。回合數線性成長，input token 卻是滾出來的。

## 第二件事：成本的隨機性大到不像話

同一件事做兩次，帳單可以差很多。論文量到的數字是這樣：

- **跨任務**：最貴的任務比最便宜的任務，平均多消耗約 700 萬個 token。
- **同一個模型、同一個任務**：4 次獨立執行中，最貴的一次平均是最便宜那次的 2 倍，極端情況可以差到 30 倍。

![左圖為 500 題依平均成本排序的每題成本與標準差，右尾很重；右圖為各模型在同一題上的最貴／最便宜成本比值。](img-002)
*圖 2 — 成本的兩種變異：題目之間（左）與同一題重複執行之間（右）。高成本的題目同時也是跨次變異最大的題目。（來源：原始論文）*

第二個數字才是真正麻煩的地方。跨任務的差異還可以解釋成「題目本來就有難有易」，但同一題同一個模型差 30 倍，就純粹是 agent 自主試錯路徑的不確定性。使用者按下執行的時候，等於在轉扭蛋，做完之前不知道自己要付 0.1 美金還是 10 美金。任何想做前置固定報價（upfront pricing）的商業模式，都會在這個數字面前碰壁。

## 第三件事：花愈多錢，結果不會愈好

這是整篇論文最反直覺的發現。研究團隊把同一題的 4 次執行依 token 消耗由低到高分成四組（MinCost、LowerCost、UpperCost、MaxCost），然後看各組的成功率。

如果「多花 token = 多想一下 = 比較容易做對」成立，成功率應該隨成本單調上升。實際結果是成功率在 LowerCost 這組達到高點，接著在 UpperCost 與 MaxCost 停滯、甚至往下掉。

![左圖為各難度／模型分組的準確率對平均 input token，附整體趨勢線；右圖為四個成本分組相對於最低成本組的準確率變化，中段最高而後走平。](img-003)
*圖 3 — 準確率與成本的關係。同一題之內，表現在中等成本的那次執行達到高點，成本再往上就不再有回報。（來源：原始論文）*

成本暴增的那些軌跡有一個共同特徵：agent 對同一個檔案重複 view 與重複 modify 的頻率，在 MaxCost 組急劇竄高。

![兩張長條圖，分別為重複修改與重複查看同一檔案的相對頻率，皆隨成本分組上升而明顯增加。](img-004)
*圖 4 — 重複修改（左）與重複查看（右）同一個檔案的頻率，隨成本分組一路走高。高成本買到的是重複，不是進展。（來源：原始論文）*

換句話說，這些高成本軌跡並不是模型在深思熟慮，而是它在鬼打牆：反覆讀同一個檔案、反覆改同一段程式碼、被自己製造出來的錯誤 log 帶著跑。這個現象學界稱為 **inverse test-time scaling**，也就是推論期算力投入超過某個點之後，效果反而反轉。

對工程上的意義很直接：**異常高的 token 消耗是一個故障訊號，不是一個努力訊號**。它值得被監控、被中斷，而不是被容忍。

## 第四件事：人類覺得難的，agent 不一定覺得難

SWE-bench-Verified 的每一題都有人類專家標註的預估難度（少於 15 分鐘、15 分鐘到 1 小時、超過 1 小時）。把這個標註跟 agent 實際消耗的 token 做關聯，Kendall 相關係數只有 0.32，屬於很弱的相關。

![左圖為 500 題依實際 token 消耗排序的色條，人類難度標籤的顏色散亂分布；右圖為三個難度組的 token 密度曲線，彼此大幅重疊。](img-005)
*圖 5 — 把題目依實際 token 消耗排序後，人類難度標籤的顏色完全沒有形成梯度。上方參考條是「完全吻合」時該有的樣子。（來源：原始論文）*

三個難度組的 token 分布重疊得非常嚴重，細看兩端更有意思：

- **6.7%** 被人類評為「15 分鐘內搞定」的超簡單題，agent 實際燒掉的 token 超過了「超過 1 小時」那組的平均值。
- **11.1%** 的「超過 1 小時」難題，agent 反而用了低於簡單題平均的 token 就解掉了。

原因在於兩邊的「難」根本不是同一件事。人類覺得難，難在邏輯繞、要想很久；agent 覺得難，難在程式碼結構定位、搜尋路徑長短、工具調用效率。一個改名字的小需求，只要它藏在很深的呼叫鏈裡、散落在十幾個檔案，對 agent 來說就是一場高成本災難。

這件事直接否定了一個很常見的產品設計偷懶做法：拿人類的難度標籤去估 agent 的成本。估不準。

## 不同模型的「花錢性格」

把準確率與 token 消耗畫成散佈圖，8 款模型的位置差異很大，大致分成三群：

| 類型 | 代表模型 | 特徵 |
|---|---|---|
| 高效率 | GPT-5、GPT-5.2 | 成本低但成功率維持在高檔 |
| 高成本高準確 | Claude Sonnet 4.5、Sonnet 4、Qwen3-Coder-480B | 準確率好看，但 token 燒得兇 |
| 離群值 | Kimi-K2 | 成本高，準確率卻不高 |

![左圖為各模型的平均 token 用量對平均準確率散佈圖；右圖為共同成功與共同失敗子集上各模型的 token 用量，排名一致。](img-006)
*圖 6 — 模型的 token 效率與準確率分布（左），以及在共同成功／共同失敗子集上的用量對照（右）。（來源：原始論文）*

比較值得一提的是研究團隊怎麼排除「題目難度不同」這個變因。他們挑出所有模型都成功的子集（n=230）與所有模型都失敗的子集（n=100），在這兩組裡各模型的相對成本排名完全一致。也就是說，token 效率是模型的先天行為慣性，不是被它剛好遇到的題目難度決定的。

### 冗餘動作與不知道停損

細看檔案操作的頻率，性格差異更明顯。GPT-5 / GPT-5.2 屬於精準型，查看與修改的次數都少，幾乎不重複動作。Qwen3-Coder、Kimi-K2、Claude Sonnet 4 屬於冗餘型，檔案操作頻繁，而且其中高達 **50% 的動作是對同一個檔案重複查看或修改**，看起來就是缺乏組織的盲目試錯。

![兩張長條圖，分別為各模型的檔案查看與檔案修改次數，並區分總次數與重複次數。](img-007)
*圖 7 — 共同成功子集上各模型的檔案查看（左）與修改（右）次數，深色部分為重複操作。（來源：原始論文）*

失敗的時候差距會被放大。在共同失敗的子集裡，GPT-5.2 的成本只微幅上升（不到 50 萬 token），Kimi-K2 卻暴增了將近 200 萬 token。差別不在誰比較聰明，而在於**有沒有「這題我做不出來」的自覺**。沒有這個自覺的模型，只會不斷重讀 context、重試、重寫，把失敗的成本推到天上去。

## 帳單的時間軸：Cache Read 才是主角

研究團隊以 Claude Sonnet 4.5 為對象，把一條軌跡切成五個階段：Setup（環境設定）、Explore（探索）、Fix（修復）、Validate（驗證）、Closeout（收尾）。回合數的分布上，Fix 佔 33.53%、Explore 佔 30.37%，兩者加起來接近三分之二。

![表格列出五個階段的名稱、定義說明與各自佔總回合數的百分比。](img-008)
*表 1 — 五個階段的定義與佔比（以 Sonnet 4.5 的所有回合統計）。（來源：原始論文）*

真正讓人意外的是成本組成。單價上，output token 最貴，大約是 cache read 的 80 倍。但在所有五個階段裡，**cache read 的總花費都絕對主導了帳單**。

用數字感受一下這個反差：假設「回顧一個字」1 元、「寫一個字」80 元。模型每一輪都要重看前面累積的 15 萬字歷史，回顧就是 15 萬元；而它這一輪只寫了 500 字程式碼，寫作成本 4 萬元。單價最便宜的那一項，因為被重複了太多次，變成帳單上最大的一塊。

![兩張堆疊長條圖，分別為五個階段的 token 數量與美金成本，cache read 在每個階段都佔最大面積。](img-009)
*圖 8 — 各階段的 token 用量（左）與實際成本（右）。不論哪個階段，input 側都主導了帳單。（來源：原始論文）*

### 尖峰從哪裡來

如果把成本畫成以回合為單位的時間序列，它不是平順上升的曲線，而是一條穩定基線加上幾根很高的尖峰。基線由 cache read 構成，尖峰則由「引入全新、還沒被快取的資訊」觸發，例如讀進一個大檔案，或是跑測試噴出一大坨單元測試 error log。

![折線／堆疊圖顯示單一軌跡中每一回合的成本，cache read 構成緩升的基線，數個回合出現明顯尖峰並標註觸發的工具。](img-010)
*圖 9 — 單一軌跡的回合級成本拆解。基線隨 context 累積而穩定上升，尖峰則對應到讀檔、跑測試等引入新內容的動作。（來源：原始論文）*

論文另外挑出六個代表性回合，依主導成本來源分類，可以看得更清楚：input 吃重的回合來自工具回傳的新內容，output 吃重的回合來自 agent 自己的推理與生成。

![表格列出六個代表性回合的編號、主導成本來源、使用的工具與該回合動作摘要。](img-011)
*表 2 — 從同一條軌跡挑出的六個代表性回合，依主導成本來源分組。（來源：原始論文）*

這個現象對系統設計有直接的意涵：**成本尖峰是可以預測、也可以主動迴避的**，因為它綁定在特定的動作類型上，而不是隨機發生。

## 核心實驗：Agent 能不能幫自己估價？

前面都是在解剖既成事實的帳單。論文接著問了一個新問題：agent 能不能在真正動手之前，先探勘一下環境，然後給出一張報價單？

### 任務怎麼設計

做法是不另外訓練預測模型，而是直接把同一個 agent 換個角色，讓它當估價員。Prompt 的約束相當明確（完整版本在論文附錄）：

- **允許**：用 `grep`、`find` 摸專案結構，用 `cat` 讀檔案，跑現有的單元測試評估損壞範圍。
- **禁止**：修改任何 source code、建立新的測試檔案、提交 git commit。
- **輸出**：必須呼叫 `finish` 工具回傳嚴格的 JSON，內容包含預估的 input / output / total token、信心水準，以及按階段拆解的 token 明細。

Prompt 裡還附了一份人類專家寫的完整估價推理示範，作為 in-context 的引導範例。

這個角色設定很像工程承包商的施工前估價：不能拆牆、不能動工，只能看藍圖、做局部檢測，然後給業主一張耗材與工時的預估單。

### 估得準嗎？不太準

評估指標是預測 token 數與實際 token 數的皮爾森相關係數。結果是所有模型都落在「弱到中等」的區間。

幾個值得記住的點：

- **世代是有進步的**：Claude 家族的預測能力隨世代穩定上升，Sonnet 4.5 在 output token 上拿到全場最高的 0.39 相關性。
- **input 比 output 難預測**：input token 的累積受環境回饋高度影響，測試會噴出多長的 log 不是模型自己能決定的；output token 講白了就是它自言自語的字數，相對好掌握。
- **Kimi-K2 是特例**：它在 input token 的預測上拿到 0.38 的最高值，看起來對 context 擴展比較敏感。

![左圖為各模型預測值與實際值的皮爾森相關係數長條圖，數值普遍偏低；右圖為各模型的預測成本佔實際任務成本的比例。](img-012)
*圖 10 — 自我預測的準確度（左）與額外開銷（右）。兩邊都還有很大的改善空間。（來源：原始論文）*

### 更嚴重的問題：系統性低估

把預測值與實際值畫成散佈圖，配上一條完美校準的對角線，幾乎所有模型的點都明顯落在線的下方。也就是說，模型不只是估不準，而是**穩定地估太低**。

![兩張散佈圖，分別為 input 與 output 的預測值對實際值，各模型的點群大多落在代表完美校準的對角線下方。](img-013)
*圖 11 — 預測值與實際值的對照。虛線為完美校準，點落在線下方即代表低估，input 與 output 皆然。（來源：原始論文）*

原因是 agent 在靜態規劃時，腦中跑的是理想路徑：讀 2 個檔案、改 2 行程式碼、測試通過、結束。實際執行時是另一回事：它會迷路、會被無關檔案吸引、會寫出有 bug 的 code、會印出巨大無比的 error log、會在同一個地方反覆讀寫。

兩邊的落差可以整理成這樣：

| | Agent 規劃時的假設 | 實際執行的樣子 |
|---|---|---|
| 探索 | 讀 2 個相關檔案 | 讀十幾個檔案，其中一半無關 |
| 修改 | 一次改對 | 改了又改，中間卡在自己寫出的 bug |
| 驗證 | 測試一次通過 | 反覆跑測試，吃進大量 error log |
| 收尾 | 乾淨結束 | 可能根本沒收斂，燒到上限為止 |

換句話說，模型缺的不是算術能力，而是**預測自己未來會犯錯、會困惑、會鬼打牆的能力**。這是一個自我建模的缺陷，不是估算技巧的問題。

這也不是 prompt 沒寫好造成的。論文另外試了拿掉那份專家示範範例的版本，低估的情況依然明顯。

![兩張散佈圖，為移除 in-context 範例後 Sonnet 4.5 與 GPT-5.2 的預測對實際值，點群仍普遍位於對角線下方。](img-015)
*圖 12 — 拿掉 in-context 示範後的自我預測行為。低估的程度沒有改善。（來源：原始論文）*

### 估價本身也要錢

別忘了預測本身也是一個 agent 任務，也在燒 token。論文用「預測成本 ÷ 實際任務成本」來衡量這筆額外開銷，結果差距大得驚人：

| 模型 | 預測開銷佔實際任務成本 | 評價 |
|---|---|---|
| GPT-5.2 | < 6% | 便宜，適合當前置探勘 |
| Claude Sonnet 4.5 | 32% | output 預測最準，開銷也還在可接受範圍 |
| Claude Sonnet 3.7 / Sonnet 4 | > 200% | 為了一個不準的估算，燒掉比做完任務還多的錢 |

最後那一列基本上宣告了這條路現階段的實用邊界：如果估價比施工還貴，那不如直接開工。

## 帶回工程現場：三個防禦性設計

論文的數據攤完，真正有用的是把它翻譯成系統設計。以下三個做法，是我認為從這些發現能直接推導出來的。

### 一、Context 垃圾回收

**問題**：cache read 主導帳單，而它之所以那麼大，是因為框架採用 append-only 的 prompt 設計，把歷史記錄無差別往後打包。

**做法**：把 prompt 當成需要管理的記憶體，而不是一本只能往後寫的日誌。具體有兩個切入點。

一是**無效 log 修剪**。Explore 階段跑的那些 `cat`、`grep`，吐出來的長程式碼與目錄樹，在進入 Fix 與 Validate 之後絕大多數已經沒用了。系統應該在階段轉換時主動把這些中介回饋從歷史裡刪掉。

二是**階段轉換壓縮**。當 agent 分析完、準備動手改 code 時，對前面的探勘對話做一次低成本的 summary，只留下關鍵錯誤原因與鎖定的目標檔案行數，其餘清空。

實際的體積差距大概是這樣：

```text
[探索階段] Prompt 堆疊：
(系統提示詞) + (問題描述) + (10 次 grep 結果) + (2 個檔案的完整程式碼)
  --> Context 體積約 150k

  觸發 Context GC（轉換至修復階段）

[修復階段] 壓縮後 Prompt：
(系統提示詞) + (目標問題總結) + (僅鎖定檔案的目標程式碼區段)
  --> Context 體積約 15k
```

省下來的就是後面每一回合都要再付一次的 cache read。

### 二、動作感知熔斷器

**問題**：高成本失敗軌跡的共同特徵是重複動作暴增，而模型自己不知道要停。指望模型自主退出是不可靠的。

**做法**：在 agent 框架外圍加一層狀態監控，用可量化的指標觸發熔斷。三個可以直接實作的檢測點：

1. **操作重複率**：開一個滑動視窗（例如最近 5 個回合），若 agent 對同一個檔案路徑呼叫 view 或 modify 的比例高於 80%，而期間單元測試仍未通過，觸發熔斷。
2. **同質報錯監控**：連續 3 回合跑測試，回傳的 traceback 文字相似度高於 90%，判定它卡在修復盲區。
3. **預算硬上限**：限制單次執行的最大可用預算（例如 8 美金），累計帳單觸頂就強制中斷。

熔斷之後不要直接回報失敗。比較好的做法是把當下的執行狀態保留住，將目前的執行紀錄與遭遇的瓶頸整理成一頁式總結，提示人類工程師介入。人給一句關鍵指引，往往能用極低的代價救回一個高價值任務。

### 三、預算感知的兩階段流程

**問題**：模型的自我估價只有弱到中等的相關性，又系統性低估，精確的前置定價現階段做不到。

**做法**：不要追求精準報價，改成粗粒度的風險分級加上動態預算控制。

第一階段先派一個估價開銷低的模型（以論文的數據來說是 GPT-5.2，開銷低於 6%）做快速探勘，輸出低／中／高風險的分級，而不是一個具體金額。

第二階段依風險分級決定互動方式：低風險就默默背景執行；高風險則跳出警示，請使用者自己設定止損金額。這樣做的好處是，你只需要模型的排序能力大致可用，不需要它的絕對值準確，而排序正是它相對不那麼糟的部分。

另外可以把剩餘預算百分比當成環境變數餵給 agent，讓它自己調整策略：剩餘預算大於 50% 時允許對整個程式碼庫做 grep 這類高成本搜尋；低於 20% 時就限制它只能做局部分析，逼它收斂。

## 這篇研究不能直接套用的地方

引用這些結論之前，有三個限制值得先放在心上。

**一、跟框架綁得很緊。** 16,000 條軌跡全部建立在 OpenHands 上，那是一個單線型、append-only 記憶的框架。如果你的系統用的是樹狀搜尋、RAG 式記憶檢索，或多代理協作架構，token 的累積動態與快取命中率會完全不同，這裡的數字沒辦法直接搬。

**二、完全沒有考慮延遲。** 論文談的成本只有錢。但為了做自我預測，有些模型（例如 Sonnet 4）在估價階段花掉超過實際任務 2 倍的 token，時間大概也跟著等比例拉長，但論文並沒有量測這一項。在真實產品裡，讓使用者為了一個估算多等 3 分鐘，在 UI/UX 上可能是不能接受的。錢的帳算完了，時間的帳還沒算。

**三、SWE-bench 是純 Python 的。** Python 的單元測試跑得快、環境也輕。換到 Java、C++ 這種需要繁重編譯的語言，或需要瀏覽器渲染的前端任務，工具回饋的時間與 error log 的體積都會膨脹得更厲害，成本動態只會比論文呈現的更極端，不會更溫和。

## 結論

這篇論文把 agent 的成本黑箱打開，留下三個值得記住的事實：帳單的主角是 cache read 而不是 output，因為 context 在滾雪球；異常高的花費通常代表 agent 迷路了，而不是它在深思；模型對自己的花費會系統性低估，最好的相關性也只有 0.39。

對做系統的人來說，結論是「context 愈大、重試愈多就愈聰明」這個假設該退場了。取而代之的是防禦性設計：主動修剪歷史來壓低 cache read、用動作監控在 agent 鬼打牆時及時熔斷、用粗粒度的風險分級搭配硬預算上限來管住尾部風險。準確的前置報價現在做不到，但可控的成本上限是做得到的，而後者才是產品真正需要的東西。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1: Agentic coding tasks cost significantly more tokens than Code Reasoning (single- turn problem solving without tool interaction) and Code Chat (multi-turn dialogue about a coding problem) tasks. Such a difference is largely driven by the increase of input tokens.",
    "why_used": "支撐開頭說明 agentic 任務與單輪推理、多輪對話成本量級差距的段落。",
    "agent_match_hint": "三組並排長條圖，比較三類程式任務的 input/output 比例、平均 token 用量與平均成本。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2: Token cost is highly variable both across problems and across repeated runs of the same problem. (a) Per-instance mean ±1 SD across the four runs and eight models, with instances sorted by mean cost; the heavy right tail indicates that high-cost problems also exhibit the largest cross-run variance. (b) Per-model max/min cost ratio, averaged across the 500 instances; error bars show ±1 SD across instances. Together, these results suggest that token cost is highly variable, making upfront cost prediction fundamentally difficult.",
    "why_used": "支撐成本隨機性那一節，同時呈現跨任務與同任務重複執行兩種變異。",
    "agent_match_hint": "左為每題成本與標準差的排序曲線，右為各模型最大／最小成本比值的長條圖。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 3: Task accuracy and token cost across models. (a) Group-level accuracy and mean input tokens for each difficulty/model bin; the dashed line shows the overall trend. (b) Relative agent accuracy across cost quartiles, compared to the minimum-cost setting and estimated via mixed-effects regression. When working on the same problem, agent performance peaks at the intermediate-cost run and then saturates with higher costs.",
    "why_used": "支撐「成本與成功率非單調」這個反直覺發現的主段落。",
    "agent_match_hint": "左為準確率對 input token 的散佈與趨勢線，右為四個成本分組的相對準確率長條圖。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Figure 4: When working on the same problem, high-cost runs are associated with repeated view and edits for the same file. Relative frequency of repeated file modifications (a) and repeated file views (b) across cost quartiles, compared to the minimum-cost setting and estimated via mixed-effects regression.",
    "why_used": "說明高成本軌跡的成因，接在成功率走平的發現之後。",
    "agent_match_hint": "兩張長條圖，重複修改與重複查看的相對頻率隨成本分組上升。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Figure 5: Expert-rated task difficulty is a weak predictor of agent token consumption. Left: each vertical bar represents one of the 500 SWE-bench tasks, sorted by actual token consumption (low →high) and colored by human difficulty rating. The top reference strip shows the expected coloring under perfect alignment (clean light-to-dark gradient); the actual coloring below it is scrambled throughout. Dashed lines mark the <15 min and >1 hour group means. Right: density of token consumption per difficulty group, with substantial overlap across the full range.",
    "why_used": "支撐人類難度標籤與 agent 實際成本脫鉤的段落。",
    "agent_match_hint": "左為依實際 token 排序的彩色長條帶與上方參考條，右為三組難度的密度曲線。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Figure 6: Token efficiency varies substantially across models and reflects model-specific behavior rather than task difficulty. (a) Mean total token usage vs. mean accuracy across all 500 SWE-bench instances; one point per model. (b) Model token usage on the shared success and failure tasks, blue dots show mean token usage on the shared success subset (n=230, solved by all models) and red diamonds show the shared failure subset (n=100, failed by all models). Models’ relative token usage remains consistent on both subsets, suggesting that token efficiency is an inherent characteristic of the model.",
    "why_used": "支撐模型之間 token 效率差異、以及效率屬於模型先天特性的論證。",
    "agent_match_hint": "左為 token 用量對準確率的散佈圖每模型一點，右為共同成功／失敗子集的用量對照。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Figure 7: Fine-grained file interaction patterns on the shared success subset. For each model, we report the average number of overall and repeated file view actions (a) and modification actions (b).",
    "why_used": "支撐冗餘動作那一段，呈現各模型重複操作的比例差異。",
    "agent_match_hint": "兩張分組長條圖，各模型的檔案查看與修改次數，含重複次數的區分。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Table 1: Phases of agent trajectories. Percentages are computed over all rounds across Sonnet-4.5 runs.",
    "why_used": "支撐五階段劃分與回合佔比的段落。",
    "agent_match_hint": "一張三欄表格：階段名稱、說明、佔總回合數的百分比。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Figure 8: Phase-level token usage and cost dynamics. Input tokens dominate both raw token usage and dollar cost across phases.",
    "why_used": "支撐 cache read 主導帳單的核心發現。",
    "agent_match_hint": "兩張堆疊長條圖，五個階段的 token 數量與美金成本組成。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "Figure 9: Round-level token-cost dynamics of the agent trajectory on astropy astropy- 7336. The cost of cache read stably increases with the accumulation of the input contexts. Cost spikes are driven by discrete actions that introduce new content (file views, test execution, script generation, final summary).",
    "why_used": "支撐成本尖峰由引入新內容的動作觸發的段落。",
    "agent_match_hint": "單一軌跡的回合級成本圖，緩升基線加上數個標註工具名稱的尖峰。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Table 2: Six representative rounds from the trajectory in Figure 9, grouped by their dominant cost source. Input-heavy rounds are driven by new content returned from tool calls; output- heavy rounds are driven by the agent’s own reasoning and generation.",
    "why_used": "補充說明尖峰與基線背後的實際動作類型。",
    "agent_match_hint": "一張表格：回合編號、主導成本來源、使用工具、動作摘要。"
  },
  {
    "id": "img-012",
    "references_manifest_caption": "Figure 10: Self-prediction performance and overhead across models. (a) Pearson correla- tion between predicted and actual token counts. (b) Overhead of self-prediction, measured as the ratio of prediction cost to actual task cost. Overall, predicting token usage before execution is challenging for all the tested models and there is much space for improving the prediction efficiency.",
    "why_used": "支撐自我預測準確度偏低、以及預測開銷差異極大的兩個段落。",
    "agent_match_hint": "左為各模型相關係數的長條圖，右為預測成本佔任務成本比例的長條圖。"
  },
  {
    "id": "img-013",
    "references_manifest_caption": "Figure 11: Predicted vs. real token usage across models. The dashed diagonal indicates perfect calibration. Agents systematically underestimate both input and output token usage.",
    "why_used": "支撐系統性低估這個核心缺陷的段落。",
    "agent_match_hint": "兩張散佈圖，預測對實際的點群與代表完美校準的對角虛線。"
  },
  {
    "id": "img-015",
    "references_manifest_caption": "Figure 13: Self-prediction behavior without in-context demonstration (Sonnet 4.5 and GPT-5.2). The dashed diagonal indicates perfect calibration. Underestimation remains pronounced.",
    "why_used": "佐證低估並非 prompt 範例造成，移除示範後依然存在。",
    "agent_match_hint": "兩張散佈圖，兩個模型在無 in-context 範例下的預測對實際值。"
  }
]
```
