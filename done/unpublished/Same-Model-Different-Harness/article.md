# 同一個模型，換一套 Harness：Coding Agent 的表現差距從哪裡來？

## 前言

如果你用同一顆模型跑兩次 coding agent，只是換了執行框架（harness）的設定，結果會差多少？這篇論文用一個嚴謹的配對實驗回答了這個問題：答案是「差很多，但原因不是你想的那樣」。

作者把自己開發的 harness（Yuj）設計成兩種模式，在完全相同的模型、任務、context 容量之下互相對照。結果顯示，當 context 空間吃緊時，改良版的表現大幅超前；但把 context window 開大到不再吃緊之後，這個優勢幾乎完全消失。更值得注意的是，改良版用的運算量是對照組的兩到四倍——表現提升，有很大一部分其實是「多做了工」換來的。

這篇文章除了拆解論文本身的實驗設計與結果，也會花不少篇幅整理幾個脫離這篇論文、單獨拿出來也成立的統計與評估心法——包括怎麼識破一個機制看起來很聰明、其實只是多花運算量的檢查框架，以及 p value 常被誤解的地方。這些心法比論文本身的結論更值得記住。

## 1. 一個問題：只換 Harness，結果會不同嗎？

一個 coding agent 的工作流程大致是：拿到一個 bug 或 issue，搜尋相關程式碼，讀檔案，改程式，跑測試，再依結果決定下一步。每一步都會留下文字紀錄——下的指令、拿到的輸出、錯誤訊息、模型自己的回覆——這些紀錄會不斷累積。在大型程式庫上，累積的文字量很快就會跟模型能看到的「context window（上下文視窗，也就是模型單次能讀進去的文字容量上限）」互相搶空間。

論文把一個 coding agent 系統拆成兩層來看：**model（模型）**負責決定下一步要做什麼——要搜什麼、要改什麼、要跑什麼測試；**harness（執行框架）**負責決定模型「看得到什麼」、「能用什麼工具」、「什麼時候該停」。這篇論文的核心提問就是：如果模型權重完全不動，只改變 harness 決定「模型看到什麼」的方式，結果會不會不一樣？

最傳統的做法（論文稱為 Control）很直覺：把完整對話依照發生的時間順序，原封不動地全部塞給模型；一旦這個對話塞不進 context window，任務就直接中止，就算程式還沒改完。論文開發的替代做法（Treatment）換了個思路：保留一份完整的執行記錄，但模型實際看到的「視窗畫面」是動態、精簡過的，另外再加上一個偵測卡關並介入提醒的機制。

## 2. Treatment Harness 怎麼設計

Treatment 由三個機制組成：**context 半衰期縮減規則**、**卡關偵測器**、**指令防護**。這三者是綁在一起測試的整包（package），論文沒有拆解實驗（ablation），所以沒辦法從這篇論文知道三者各自貢獻了多少——這點會在後面的限制段落再提一次。

### 2.1 機制一：context 半衰期縮減規則

Control 模式下，舊的工具呼叫結果——搜尋結果、測試 log、錯誤訊息——會一直佔著 context 空間，擠壓後面真正需要的資訊，大型早期輸出甚至可能吃光後面需要的空間。

Treatment 的解法是把「模型實際看到的畫面（working view）」跟「完整的執行記錄（in-memory conversation）」分開：完整記錄永遠留著、永遠可以事後查，但模型當下看到的東西可以被動態壓縮。

![一個閉迴路示意圖：完整執行記錄永遠保留，harness 每一步都重新組出模型當下看到的畫面，模型依此決定動作，工具執行結果再寫回完整記錄。](img-001)
*圖 1 — Treatment harness 的閉迴路運作方式：模型看到的畫面每一步都重新組裝，但底層的完整記錄不會被縮減。*

**啟動時機**：縮減規則不是一開始就啟動，只有當「預估的完整 prompt」達到設定 context window 的 **50%** 時才會開始運作。在跨過這條線之前，不管一筆結果多舊，都完整顯示、放著不管。

**age 的定義**：age 指的是「這筆工具結果之後，又出現了幾筆更新的工具結果」，age 越大代表越舊，寫成公式：

$$\text{age}(R) = k_{now} - k_R$$

其中 $k_R$ 是 R 這筆工具結果建立時是第幾次工具呼叫，$k_{now}$ 是目前累積到第幾次工具呼叫。

縮減規則本身是一張分級表：

| age 分級 | 字元上限 |
|---|---|
| 最新 4 筆 | 完整保留（verbatim） |
| age 4–7 | 最多 4,096 字元 |
| age 8–15 | 最多 2,048 字元 |
| age 16–31 | 最多 1,024 字元 |
| age 32–63 | 最多 512 字元 |
| age 64 以上 | 最多 256 字元 |

![working-view 規則的長條圖：橫軸是工具結果的年齡分級，縱軸是允許的字元上限，長條以對數尺度隨年齡遞減。](img-002)
*圖 2 — Treatment 的 working-view 縮減規則：age 每翻一倍，字元上限就砍半，這就是「半衰期」命名的由來。*

規律很清楚：age 每翻一倍（4→8→16→32→64），字元上限就砍半——這就是「半衰期（half-life）」命名的由來，借用「自變數翻倍、應變數呈指數遞減」這個數學形狀上的類比，沒有更深的物理意義。縮減後的結果保留開頭、保留結尾，中間用省略標記取代，讓模型還能看出這次工具呼叫大致在做什麼。

論文用一個真實任務（`django_django-11211`）完整走查了這套規則：

| $k_{now}$ | age | 落在哪一級 | 上限（字元） | 實際顯示長度 |
|---|---|---|---|---|
| 5 | 0 | 最新 4 筆內 | 完整 | 26,684（逐字，★真實資料點） |
| 9 | 4 | age 4–7 | 4,096 | 4,096 |
| 13 | 8 | age 8–15 | 2,048 | 2,048 |
| 21 | 16 | age 16–31 | 1,024 | 1,024 |
| 37 | 32 | age 32–63 | 512 | 512 |
| 60 | 55 | age 32–63 | 512 | 512（★真實資料點） |

表中 $k=5$（建立時，26,684 字元）跟 $k=60$（呈現時，512 字元）是論文真實公布的兩個快照數字，其餘節點是套用論文明講的分級規則、對這兩點之間做的機械式計算，用來讓遞減節奏更清楚，不是論文逐輪公布的資料。

![左下角是一段被縮減過的工具結果，顯示開頭幾行程式碼與結尾，中間標註已省略的字元數；右下角是一張折線圖，顯示第 45 到 60 個 turn 之間 prompt token 持續上升，直到第 60 turn 斷崖式下降。](img-004)
*圖 3 — 一次真實的 Treatment 執行紀錄：512 字元的顯示內容加上省略的 26,172 字元，等於原始的 26,684 字元；右側可以看到縮減規則在第 60 turn 一次性生效。*

在 $k_{now}=60$ 這個真實快照裡，實際顯示內容是開頭幾行程式碼（`from collections import defaultdict...`）加上「26,172 字元已省略，完整結果仍保留在存檔中」的提示，再加上結尾（`return GenericRelatedObjectManager`）。512（顯示）加 26,172（省略）等於 26,684（原始），數字對得上。

這裡有一個容易被誤會、但很重要的細節：縮減規則**不是每個 turn 都在跑漸進式的縮減**。圖 3 右下角那張圖顯示，turn 45 到 60 之間，prompt tokens 一路往上爬（約 22,500 到 30,500），完全沒有縮減痕跡；直到 turn 60 那一瞬間才斷崖式下降到約 20,500。

原因是縮減規則要等到「整體 prompt 佔用率跨過 50% 門檻」才會一次性地把當下所有舊結果依照各自的 age 套上對應上限——「要不要開始壓」是由整體佔用率決定的獨立開關，「壓到多短」才是由單筆結果自己的 age 決定，這是兩件分開的事。

### 2.2 機制二：卡關偵測器

Context 縮減只解決「空間不夠」，但還有另一種浪費：空間明明還夠，模型卻在原地打轉——重複下同一個會失敗的指令、連續拿到一樣的錯誤訊息、或反覆讀同一份資料卻遲遲不動手改程式碼。

偵測器的運作方式很單純：它**不會**重新理解或解讀對話內容，只比對「執行記錄裡已經存在的固定事實」，例如這個指令之前出現過嗎、上次結果跟這次一樣嗎。整套規則是寫死的，同樣的模式一定觸發同樣的反應，不會臨場判斷，也完全不耗用模型 token、不呼叫模型。

偵測到模式後，harness 會送出一段固定文字提醒模型換個做法（論文稱為 intervention，介入），然後繼續觀察下一步。這個「觀察、回應、再觀察」的迴圈，就是論文把整套 Treatment 稱為 closed-loop harness（閉迴路 harness）的原因。

論文只給了三種質性的症狀描述：模型重複下同一個會失敗的指令、連續拿到同樣的錯誤訊息、反覆讀同一份資料但沒有做任何原始碼變更。前面圖 3 提到的那個真實案例，就是這套機制實際觸發的樣子：第 32 個 model-call turn，偵測器記錄到「同樣的參數 7 個 turn 後又被重送一次，期間完全沒有寫入任何原始碼變更」；第 33 個 model-call turn，harness 送出固定回應：偵測到迴圈，停止重複，換個做法。

論文沒有講清楚具體的判定規則跟門檻值——例如重複幾次才算觸發、多少 turn 內算同一次重複、怎麼判定兩次錯誤訊息算「一樣」——只說這些規則是 harness 與 treatment 設定的一部分，實際定義藏在程式碼設定檔裡，正文完全沒有揭露。論文自己在後段也承認，「detector 各機制的個別貢獻」是未來工作，連作者自己都還沒做拆解實驗。

雖然論文沒揭露具體規則，這三種症狀分類——重複失敗指令、重複錯誤訊息、空轉重讀無編輯——本身是一個可以脫離這篇論文、直接套用到其他 agent harness 設計上的分類框架，這點會在後面的通用觀念一起整理。

### 2.3 機制三：指令防護

論文對這個機制的描述極為單薄，原文整段就只有一句話：Treatment 額外處理幾個可預期的指令問題，把測試指令改寫成預期格式、在禁止指令執行前先攔下來、防止過大的 setup 輸出佔滿 context。

也就是三件事：把測試指令重寫成預期格式、在禁止指令執行前先攔下來、防止過大的 setup 輸出佔滿 context。這裡論文完全沒有講清楚具體規則——沒有列出禁止指令清單、沒有解釋「預期格式」指的是什麼、也沒說明這個機制跟機制一的縮減邏輯是共用還是獨立。三個機制裡，這個揭露程度最低，這裡就不做任何推測性補充。

## 3. 怎麼公平比較：實驗設計與評分方式

### 3.1 配對比較設計

論文的核心設計是配對比較：同一個任務，同時跑兩次——一次 Control、一次 Treatment，兩次共用完全相同的模型權重、任務、context 容量、執行協定、評分器，唯一的差異只在 harness 設定這一個變因。

這樣做要解決的問題是：如果不做配對，直接把任務隨機分成兩組分別跑，就沒辦法排除「任務難度差異」這個干擾因素——萬一某一組剛好分到比較簡單的任務，你不知道進步是來自 harness 設計還是純粹運氣。配對設計把任務難度這個變因鎖死，能歸因的變數只剩下 harness 設定。

有一個容易被忽略但重要的前置檢查：在正式比較之前，作者先驗證了自己的 Control 版本是不是一個可信的基準，而不是刻意做弱的稻草人對照組。

做法是拿同一個模型、同一批 500 個 SWE-bench Verified 任務，分別跑在 Yuj（未開 Treatment）跟一個外部現成的 harness（mini-SWE-agent v2.2.8）上，結果兩邊在 87.6% 的任務判定上一致（一致性係數 $\kappa = 0.66$）。論文沒有進一步討論那 12.4% 不一致的任務屬於什麼類型，只用一句話帶過就接受了這個前測結果，算是交代得比較簡略的環節。

### 3.2 怎麼算分：Resolution 與 F2PF

論文同時報兩個指標。**Resolution（是否完全解決）**是二元的、是或否；**F2PF（Fail-to-Pass Fraction，部分修復比例）**是連續值，介於 0 到 1 之間。

要理解 F2PF，得先知道 F2P 測試是什麼。一個 coding 任務底下，evaluator 會挑出一批「修 patch 之前失敗、修完之後應該要通過」的測試，稱為 F2P（Fail-to-Pass）測試，專門用來檢查「有沒有真的把 bug 修好」。F2PF 就是從這堆測試裡算出來的比例：

$$F2PF = \frac{\text{F2P 測試中，修完後變成通過的數量}}{\text{F2P 測試的總數}}$$

![十個測試方塊排成一列，修 patch 之前全部標記失敗，修 patch 之後有七個變成通過、三個仍然失敗。](img-006)
*圖 4 — F2PF 的具體例子：十個目標測試裡修好七個，F2PF 是 0.70，但因為還有三個沒過，這個任務不算完全解決。*

圖 4 是論文給的具體例子：十個 F2P 測試裡，修 patch 之後有七個變成通過，$F2PF = 7/10 = 0.70$；但因為還有三個測試仍然失敗，這個任務的 Resolution 判定是「否」——F2PF 記錄的是全有全無終點線之下的漸進進展。

順帶一提，跟 F2P 相對的還有 P2P（Pass-to-Pass，修 patch 前後都應該通過的測試，用來檢查有沒有把別的地方改壞），這是 SWE-bench 系列 benchmark 的標準協定背景知識，論文正文完全沒有出現這個詞，也沒有討論或報告改壞其他測試的情況。

**為什麼需要兩把尺一起用**：如果只用二元的 Resolution 當指標，會有一個弱點——它的變化量通常很小、樣本又少，統計上容易看不出差異。

論文自己的數據就是最好的示範：FeatureBench 的 183 個任務裡，complete solutions（Resolution）只從 2 變成 3，幾乎看不出東西；但 mean per-task F2PF 從 10.5% 變成 19.6%，訊號清楚很多。F2PF 存在的意義，就是在 Resolution 判定為「失敗」的任務裡繼續榨出訊號，不把「改對七成」跟「一題都沒改對」的任務粗暴地歸成同一類「失敗」。

評分還有一條邊界規則：如果某筆記錄沒有 F2P 分母（這個任務本身沒有可用的目標測試），評分規則直接把 operational F2PF 設為 0——但這跟「有分母、測試全部沒過」的真實 0 分是兩種不同情況。

![多個長條圖，每個 benchmark 一組，長條依 context pressure 與 context 不受限兩種情境分開，長條內部用斜線紋路標示沒有 F2P 分母而被記為零的比例，灰色標示有分母但測試全掛的真實零分。](img-009)
*圖 5 — 論文用斜線與灰色兩種紋路，區分「沒有可用目標測試而被記為零」跟「有目標測試但全部沒過」這兩種不同性質的零分。*

論文在圖 5（原文 Figure 7）用不同紋路把這兩種零分分開標示，讓讀者不會把「這個任務根本沒有可評分的測試」跟「這個任務真的一題都沒修好」混為一談。

### 3.3 統計檢定：資料是二元還連續，決定你要用哪個檢定

Resolution 是二元配對資料，用 McNemar test；F2PF 是連續配對資料，用 Sign test。論文選 Sign test 而非 Wilcoxon signed-rank test 或配對 t-test 的原因，是研究問題本身只關心「哪個方向的題目比較多」，不關心贏多少，而且 sign test 對資料分布沒有假設要求。這兩個檢定的完整決策邏輯跟具體算法，留到後面的通用觀念一起整理會更清楚。

## 4. 主要結果

### 4.1 Context 壓力大時，Treatment 領先幅度很大

三個 benchmark 的核心結果整理如下：

| Benchmark | mean F2PF（C→T） | complete solutions（C→T） |
|---|---|---|
| SWE-bench Verified | 28% → 49% | 43 → 72 |
| SWE-bench Pro | 15% → 33% | 31 → 72 |
| FeatureBench | 11% → 20% | 2 → 3 |

![一張表格，三個 benchmark（SWE-bench Verified、SWE-bench Pro、FeatureBench）各自列出 control 與 treatment 兩欄的 mean per-task F2PF 與 complete solutions 數字。](img-007)
*表 1 — 三個主要 benchmark 在 context 壓力下的核心成果：mean per-task F2PF 與完全解決的任務數，control 對照 treatment。*

三個 benchmark 的 F2PF 差異都是 $p < 0.0001$（sign test）；Verified 跟 Pro 的 resolution 差異也都是 $p < 0.0001$（McNemar test）；FeatureBench 因樣本太小（2→3）沒測出顯著性。單看這組數字，會覺得 Treatment 像變魔法——但先別急著下結論。

### 4.2 隱藏的代價：這不是免費的午餐

這是整篇論文最關鍵、也最容易被忽略的一塊。表 2（原文 Table 9）揭露了代價：

| Benchmark | model turns（C/T） | prompt tokens 百萬（C/T） | wall time 小時（C/T） |
|---|---|---|---|
| Verified | 3,280 / 6,517 | 37.8 / 80.7 | 1.3 / 4.6 |
| Pro | 8,357 / 25,750 | 210.6 / 657.1 | 5.4 / 21.8 |
| FeatureBench | 5,281 / 15,178 | 140.3 / 412.8 | 2.5 / 14.7 |

![一張表格，列出三個 benchmark 在 control 與 treatment 下各自的 model turns、prompt tokens（百萬）與 wall time（小時）。](img-017)
*表 2 — Treatment 消耗的運算資源：Pro benchmark 上，Treatment 用了將近三倍的 model turns、三倍多的 prompt tokens、四倍的 wall time。*

以 Pro 這一行為例：Treatment 用了將近三倍的 model turns、3.1 倍的 prompt tokens、四倍的 wall time。表現提升（F2PF 15%→33%）有很大一部分可能就是「多做了三倍的工」換來的，不是「同樣的工作量、做得更聰明」。

論文自己也承認這一點：少做工可能只是代表提早停手，而不是真的比較有效率——在壓力情境下，control 常常撞到 context 上限，treatment 卻還能繼續做下去。換句話說，control 表現差，很大一部分原因是它被 context 塞滿、提早被迫收工，不是它真的能力比較差。這句話直接動搖了 4.1 那組數字表面上給人的「智慧型機制」印象。

### 4.3 Context 解除限制後，優勢幾乎消失

如果 Treatment 真的比較「聰明」，那把 context window 開大、讓兩邊都不再吃緊之後，優勢應該還在。論文用同一批 169 個任務，只改變 context window 大小，測了這件事：

| context window | mean F2PF（C/T） | 差距 | resolution（C/T） |
|---|---|---|---|
| 20,480（緊） | 28.0% / 49.1% | +21.1pp | 43/169 → 72/169 |
| 43,008（中） | 53.8% / 60.1% | +6.4pp | 76/169 → 87/169 |
| 262,144（寬鬆） | 69.0% / 68.7% | −0.3pp | 102/169 → 101/169 |

![折線圖，橫軸是三種 context window 大小，縱軸是 mean per-task F2PF，control 跟 treatment 兩條線在寬鬆 context 下幾乎重疊。](img-008)
*圖 6 — 三種 context window 下的表現變化：window 越寬鬆，control 跟 treatment 的差距越小，262,144 tokens 時幾乎完全重疊。*

262,144 tokens 時，每個 benchmark 每個 arm 裡低於 1% 的任務真的會撞到 context 上限，等於完全不受限。優勢在這裡直接歸零（95% 信賴區間 [−4.5, +3.9]，涵蓋 0）。Treatment 的優勢幾乎完全集中在「context 不夠用」這個特定情境下，一旦拿掉限制，兩者表現趨於一致。

> **統計嚴謹度註記**：附錄的 repository-level 敏感度分析（下一節會詳細解釋這個方法）顯示，Verified 的 resolution 差異 $p$ 值從 $<0.0001$ 跳到 $0.0625$（不再顯著，雖然方向仍是 `6:0:5` 一面倒偏向 treatment，只是樣本數太小加上多重比較校正，證據強度不夠）。
>
> FeatureBench 的 resolution 更明顯，22 個 repo 裡只有 1 個支持 treatment、21 個平手（$p_{Holm}=1$，完全沒訊號）。真正在兩個檢定層級都穩定顯著的，只有 SWE-bench Pro。

論文對這個現象有一個站得住腳的正面解讀：你事先不知道任務會不會撞到 context 上限，Treatment 在會撞時大賺、不會撞時打平不虧，所以從風險管理的角度，預設開啟是合理的，即使它平均而言不是什麼突破，更接近一張安全網。

### 4.4 FeatureBench 是唯一的例外

三個 benchmark 裡，只有 FeatureBench 在 context 完全不受限時依然保留差距。262,144-token、183 題的情境下，F2PF 從 23.9% 進步到 30.7%，task-level sign test 顯著（$p = 0.00022$），但 repository-level sign test 不顯著（$p = 0.0963$）；而完全解決的任務數，5 → 5，完全沒變。

也就是說，即使 context 不受限，Treatment 依然讓模型修好更多測試，但完全解決的任務數一個都沒多。論文沒有解釋為什麼 FeatureBench 跟另外兩個 benchmark 不一致，只是誠實地把這個矛盾攤出來。

## 5. 換模型，結論還成立嗎？

前面所有結果都只在單一模型（Qwen3.6-35B-A3B）上跑出來。作者把同一套凍結不變、完全沒重新調參的 Treatment 設定，套用到三個架構完全不同的模型上，驗證效果是不是 Qwen3.6 專屬的巧合，過程中沒有任何 harness 程式碼分支或重新調校。

| model | 設計 | F2PF（C→T，增益；倍數） | solutions（C→T，增益；倍數） |
|---|---|---|---|
| Qwen3.6 | DeltaNet / attention MoE | 28%→49%（+21pp；1.8×） | 43→72（+29；1.7×） |
| Devstral | dense transformer | 17%→37%（+20pp；2.1×） | 22→53（+31；2.4×） |
| Nemotron | Mamba-2 / attention MoE | 12%→18%（+6pp；1.5×） | 16→25（+9；1.6×） |
| Qwen3.8 | dense DeltaNet / attention | 20%→35%（+15pp；1.7×） | 32→54（+22；1.7×） |

![一張表格，四個模型各自列出 F2PF 與完全解決任務數在 control 跟 treatment 下的變化，附上增益幅度與倍數。](img-011)
*表 3 — 跨模型遷移結果：四個架構完全不同的模型上，Treatment 的效果方向一致，但幅度差異不小。*

四個模型的 F2PF 跟 solutions 都一致朝同一個方向進步，說明 Treatment 的效果方向性不是 Qwen3.6 專屬的巧合。但 Nemotron 的 resolution 差異（McNemar $p = 0.0636$）沒有達到 0.05 顯著門檻，是四個模型裡唯一一個 resolution 沒有顯著證據支持的案例。

這裡有一個重要的揭露缺口：遷移實驗完全沒有公布這四個模型各自的 model turns、prompt tokens、wall time。前面已經確認 Qwen3.6 的巨大提升裡，有很大一部分可能來自運算量差距（兩到四倍）——這個「運算量混淆」的疑慮，在遷移模型上完全沒辦法檢查，因為沒有對應的資源消耗數字可查證。

## 6. 這篇論文之外，更重要的六個通用觀念

論文本身的方法沒有太多新穎性，作者自己也承認這點。真正值得帶走的，是讀論文過程中釐清、但脫離這篇論文也成立的一批通用觀念——理解這些，比記住論文本身的結論更耐用。

### 6.1 看到「新機制帶來大幅提升」，先檢查運算量有沒有對齊

評估任何一個「新機制帶來大幅提升」的宣稱時，第一件要檢查的事是兩邊有沒有用一樣多的運算量。運算量沒對齊，提升就可能只是多做工，而不是做得聰明——這是這篇論文提供的最強懷疑框架，可以直接套用到任何 agent 或 harness 系統的評估上。

搭配的具體反事實檢查是：單純加大資源（例如把 context window 開大），能不能達到同樣效果？如果答案接近「能」，那所謂的智慧型機制，價值就要大打折扣。這篇論文的 4.3 節結果正好是這個檢查的活教材——Treatment 的優勢在 context 開大之後幾乎消失，代表它有相當一部分其實只是「context 不夠用時的救急手段」，不是普遍意義上的能力提升。

### 6.2 p value 到底是什麼意思

p value 的正確定義是：**假設虛無假設為真**（也就是兩個方法其實一樣強、沒有差異），觀察到現在這組資料、或比現在更極端的資料的機率。

最常見的誤解是「p 值很小，代表虛無假設不成立」。這句話是錯的，而且是全世界統計教學裡最常見的誤解之一。

可以拿反證法來類比，但要看清楚差在哪裡：反證法的邏輯是假設 P 為真，推導出邏輯矛盾，所以 P 不成立，這是確定性推論，矛盾就是矛盾。假設檢定的邏輯不一樣——假設虛無假設為真，算出「觀察到這組資料」的機率很低，所以虛無假設「可能」不成立，這只是機率上的傾向，不是邏輯上的鐵證。

機率很低的事情不代表不可能發生，只是比較少見。研究者拒絕虛無假設時，永遠帶著一個「萬一正好碰上小機率巧合」的風險，這個風險有名字，叫 **Type I error（第一型錯誤）**。

具體代入論文的數字會更清楚。Sign test 給出 `42:6:121`，$p < 0.0001$，正確的講法是：如果 treatment 跟 control 真的一樣強，那麼在 169 題裡隨機決定誰贏誰輸，出現「42 題 treatment 贏、只有 6 題 control 贏」這麼懸殊、或比這更懸殊的比例，機率低於萬分之一。因為這個機率低到不合理，研究者選擇拒絕「兩者一樣強」的假設，但這個決定本身永遠保留了一個判斷錯誤的可能性，不是邏輯上的鐵證。

顯著性還有一個更實用的延伸應用：換一個樣本定義方式（例如從「任務」換成「來源／群組」），同一組底層資料的顯著性可能會翻盤。看到任何顯著性宣稱，都該多問一句「用什麼單位算的」——下一節就是這個問題的具體示範。

### 6.3 Repository-level 敏感度分析：你的樣本真的互相獨立嗎？

Repository（程式碼庫）指的是任務來自哪一個開源專案。SWE-bench 系列 benchmark 的任務都是從真實 GitHub 專案的歷史 issue 挑出來的，論文的 169 個 Verified 任務集中在 11 個 repository 裡（平均一個 repository 貢獻約 15 題），Pro 也是 11 個，FeatureBench 是 22 個。

前面所有 sign test 跟 McNemar test 都把「每一個任務」當作獨立樣本，但同一個 repository 底下的多個任務可能共享相似的程式碼風格、bug 類型，不見得是統計上真正獨立的樣本。

如果 Treatment 剛好對某個 repository 的程式碼風格特別合拍，task-level 統計會把這個 repository 裡的每一題都算成一次獨立的「贏」，顯著性可能被少數幾個合拍的專案灌水撐起來。

具體做法是把同一個 repository 裡所有任務的差值先平均成一個數字，變成「以 repository 為單位」的一筆資料，再重新做 sign test。舉個說明用的簡化例子：假設某個 repository 底下有 5 題，F2PF 差值分別是 +0.40、+0.30、+0.20、+0.10、+0.00，repository-level 做法會先平均成 $(0.40+0.30+0.20+0.10+0.00)/5 = 0.20$，這個 repository 最終只貢獻一筆「正」的資料，而不是五筆。

論文附錄的真實結果，把 task-level 跟 repository-level 兩種算法擺在一起，落差看得很清楚：

| 比較項目 | task-level $p$ 值 | repository-level $p$ 值（Holm 校正） |
|---|---|---|
| Verified F2PF | < 0.0001 | 0.0469（勉強顯著） |
| Verified resolution | < 0.0001 | 0.0625（不顯著） |
| Pro F2PF | < 0.0001 | 0.00586（依然強顯著） |
| Pro resolution | < 0.0001 | 0.00586（依然強顯著） |
| FeatureBench F2PF | < 0.0001 | 0.00586（依然顯著） |
| FeatureBench resolution | 1 | 1（完全沒訊號） |

這組結果該怎麼解讀？除了 FeatureBench F2PF 那組有 2 個 repository 反過來偏向 control 之外，其餘所有比較裡「control 贏」的 repository 數量都是 0。也就是說，顯著性的消失主要不是因為方向出現分歧——不是有些 repo 撐 treatment、有些撐 control。

真正的原因是樣本數從 169 壓縮到 11 到 22 個之後，單純沒有足夠的樣本量把這個仍然一致的方向訊號推過統計顯著的門檻，加上 Holm 多重比較校正（一種讓多次檢定的顯著門檻變嚴格的統計修正）又進一步拉高了門檻。真正在兩個檢定層級都穩定顯著的，只有 SWE-bench Pro；Verified 跟 FeatureBench 的 resolution 提升，證據強度比 task-level 數字表面上看起來要弱得多。

遇到配對或分組資料要做顯著性檢定時，先問自己一句：「我的樣本真的互相獨立嗎？」不獨立就該用更保守的分組層級重新驗證一次。

### 6.4 McNemar test 與 Sign test：配對比較怎麼選檢定

遇到配對比較資料，先問結果是二元還是連續值，再選檢定方法：

- 結果是二元（是／否、成功／失敗）→ McNemar test。一句話記憶：兩邊都贏或都輸的配對不算數，只看誰單獨贏。
- 結果是連續值（比例、分數）→ Sign test。一句話記憶：只數正負號，完全不管贏多少。

McNemar test 具體怎麼算，可以用論文真實數字示範（Table 7，Verified 20,480-token window）：

| | control：是 | control：否 |
|---|---|---|
| **treatment：是** | 兩邊都過，不算 | 34（treatment 單獨救回來的） |
| **treatment：否** | 5（control 單獨救回來的） | 兩邊都沒過，不算 |

McNemar test 只看「一邊贏、一邊輸」的配對，也就是不一致配對，兩邊都成功或都失敗的配對直接丟掉不算，因為這些配對無法告訴你誰比較強。這裡是 34 贏 5，懸殊到 $p < 0.0001$。

Sign test 具體怎麼算，同樣用真實數字（Table 8，同一個 window）：169 題裡，42 題 treatment 的 F2PF 較高、6 題 control 較高、121 題平手（直接排除）。只比 42 跟 6 這兩個非平手數字，懸殊到 $p < 0.0001$。

論文選 Sign test 而非 Wilcoxon signed-rank test 或配對 t-test，原因是研究問題只關心方向、不關心贏多少，而且 sign test 對資料分布沒有假設要求，不需要常態或對稱分布。

### 6.5 Resolution + F2PF：雙尺度評分設計的可遷移價值

前面第 3 節提過，當終局指標是二元、樣本又少、容易看不出訊號時，補一個連續型的「部分完成度」指標，可以在不改變終局判定標準的情況下榨出更多訊號。這個設計模式不只適用於 coding agent 評分，可以直接遷移到任何「怎麼設計中間層評估指標」的情境——例如客服對話系統只看「有沒有解決問題」太粗，補一個「對話往解決方向推進了多少」的連續指標，也是同一個邏輯。

### 6.6 卡關偵測的三類症狀分類框架

第 2.2 節提到的三類卡關症狀——重複失敗指令、重複錯誤訊息、空轉重讀無編輯——雖然論文沒有揭露具體的判定規則跟門檻值，這個分類本身是一個可以直接套用到其他 agent harness 設計上的通用觀念。如果你正在設計自己的 agent 系統，這三類是一個現成的起點：先從偵測這三種模式開始，再依實際情況調整門檻。

## 7. 限制與保留

這篇論文有幾個值得放在心上的限制：

- **三個機制綁在一起測試，沒有拆解實驗**。你沒辦法從這篇論文知道 context 縮減、卡關偵測、指令防護三者各自貢獻了多少，論文自己也把這列為未來工作。
- **卡關偵測器跟指令防護的具體規則沒有揭露**。觸發門檻、指令清單、格式定義全部藏在程式碼設定檔裡，正文完全沒有交代，讀者沒辦法自行複製這套邏輯。
- **基準有效性驗證交代得比較簡略**。87.6% 的一致率、$\kappa = 0.66$ 看起來不錯，但那 12.4% 不一致的任務屬於什麼類型，論文完全沒有討論。
- **FeatureBench 在寬鬆 context 下的行為跟其他兩個 benchmark 矛盾**，論文沒有嘗試解釋，只是誠實地攤出來。
- **跨模型遷移實驗缺運算量數據**。少了 model turns、prompt tokens、wall time 這幾項，沒辦法檢查遷移模型的提升裡，有多少一樣是「多做工」換來的。
- **論文自己承認研究新穎性低**。這篇論文真正證明的東西，比表面上看起來的「智慧型機制」要單薄一些——比較接近「別讓模型因為 context 爆掉而提早陣亡」這種務實的工程修正，而不是什麼演算法突破。

## 結論

同一個模型，換一套 harness，表現確實可以差很多——但這篇論文最有價值的地方，不是「Treatment 比較強」這個表面結論，而是它示範了怎麼正確地拆解「表現提升」背後的成因。當 context 空間吃緊時，Treatment 大幅領先；但這個領先有很大一部分來自運算量差距，一旦拿掉 context 限制，優勢幾乎消失。跨模型遷移實驗確認了效果方向一致，但同樣缺運算量數據可以驗證。

比起論文本身的結論，更值得帶走的是一套思考工具：看到「新機制帶來大幅提升」先檢查運算量有沒有對齊，理解 p value 真正在講什麼，用 repository-level 分析檢查樣本是否真正獨立，以及怎麼依資料型態選對統計檢定。這些心法脫離這篇論文本身依然成立，也更適合帶進你自己下一次評估 agent 系統的場合。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1: The closed loop. The harness retains the in-memory conversation but rebuilds the model’s current view for each step. Recorded execution patterns can change a later step. Separate files preserve the complete run record.",
    "why_used": "視覺化 Treatment harness 的閉迴路運作方式，幫助讀者理解完整記錄與模型當下視野是分開的兩件事。",
    "agent_match_hint": "一個由四個方框組成的迴圈示意圖，箭頭連成一圈，下方有兩個小方框代表偵測器與指令防護。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2: The treatment’s working-view rule. The treatment starts shortening only after the estimated full prompt reaches half the configured window. The newest four tool results remain full. Older results keep their beginning and end within the printed caps, while the in-memory result remains complete. Capped bar lengths use a base-two logarithmic scale. The printed values are exact.",
    "why_used": "用長條圖具體呈現 age 分級與字元上限之間的半衰期關係，搭配正文的分級表一起理解。",
    "agent_match_hint": "一排橫向長條圖，長條長度隨著年齡分級遞減，標示各級距的字元上限數字。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Figure 4: A real Verified treatment trace. The lower-left panel shows an excerpt from the exact 512-character view of a 26,684-character tool result. The full result remained saved. The lower-right panel shows assembled prompt tokens before and after shortening began at turn 60. The top row reports the recorded detector fact and the reminder that followed.",
    "why_used": "用真實案例具體呈現縮減規則的斷崖式觸發現象，以及偵測器介入的實際文字內容。",
    "agent_match_hint": "上方一列文字說明偵測到的迴圈模式，左下是一段含省略標記的程式碼片段，右下是一張 prompt token 隨 turn 變化的折線圖，在某一點急遽下降。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Figure 5: The ten-test example. The patch fixes seven target tests, so its F2PF is 0.70. Three target tests still fail, so the task is not resolved. F2PF records useful movement below the all-or-nothing finish line.",
    "why_used": "用具體的十個測試方塊呈現 F2PF 的計算方式，讓抽象定義有一個可以馬上理解的例子。",
    "agent_match_hint": "一列十個方塊圖示，修補前全部標記失敗，修補後七個變成打勾、三個仍是叉號。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Table 2: Outcomes for the three primary Qwen3.6 pressure comparisons. Each row gives mean per-task F2PF and complete solutions for both arms. We round percentages to whole numbers. C and T denote control and treatment.",
    "why_used": "呈現三個主要 benchmark 在 context 壓力下的核心成果數字，是整篇論文最重要的一張成果表。",
    "agent_match_hint": "一張三列表格，欄位包含 benchmark 名稱、mean per-task F2PF 的 control 對 treatment 數字，以及 complete solutions 的 control 對 treatment 數字。"
  },
  {
    "id": "img-017",
    "references_manifest_caption": "Table 9: Recorded model work for the three primary Qwen3.6 pressure comparisons. Each total covers the complete fixed run protocol used for the final outcome. Model turns count unique recorded turns within each solver invocation, while prompt tokens count the assembled model inputs at those turns. C/T denotes control/treatment.",
    "why_used": "揭露 Treatment 表現提升背後的運算量代價，是理解整篇論文結論限制的關鍵證據。",
    "agent_match_hint": "一張三列表格，列出三個 benchmark 在 control 跟 treatment 下的 model turns、prompt tokens（百萬）與 wall time（小時）。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Figure 6: Qwen3.6 outcomes across the three Verified context windows at the completed-run endpoint under the fixed 480-second budget. Every point uses the same 169 tasks. The mean per-task F2PF label above each window gives the paired treatment-minus-control difference in percentage points.",
    "why_used": "呈現 context window 從緊到寬鬆時，control 與 treatment 表現差距逐漸收斂到幾乎重疊的過程。",
    "agent_match_hint": "一張折線圖，橫軸是三種 context window 大小，縱軸是 mean per-task F2PF，兩條線（control、treatment）之間的距離隨 context 變寬而縮小。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Figure 7: One operational F2PF state per task under context pressure and with context effectively unconstrained at 262,144 tokens. Hatched segments show selected records with no F2P denominator. The fixed scoring rule assigns those records zero. Gray segments show measured zeros with a positive denominator. We round segment percentages independently. Each panel uses the task outcomes for the matching benchmark",
    "why_used": "用視覺方式區分兩種容易混淆的零分情況，幫助讀者理解 F2PF 評分邊界規則的實際樣貌。",
    "agent_match_hint": "多組堆疊長條圖，每組代表一個 benchmark，長條內部以斜線紋路與純灰色區分兩種不同成因的零分。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Table 3: Paired outcomes on the same 169-task SWE-bench Verified cohort at 20,480 tokens and a fixed 480-second attempt budget. C and T denote control and treatment. The design column uses the term mixture of experts (MoE). Parentheses give the absolute gain and T/C multiplier; F2PF gains are percentage points.",
    "why_used": "呈現同一套 Treatment 設定套用到四個不同架構模型上的結果，用來驗證效果方向是否具有可遷移性。",
    "agent_match_hint": "一張四列表格，列出四個模型名稱、架構設計，以及各自的 F2PF 與完全解決任務數在 control 跟 treatment 下的變化。"
  }
]
```
