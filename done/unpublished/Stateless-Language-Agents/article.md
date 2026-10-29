# 讓 agent 每次都從零開始：SLA 如何撐起長時間自動研究

## 前言

讓 LLM agent 連續跑好幾天，自動做研究、改程式、刷分數，現在已經不稀奇。難的是怎麼讓它「跑越久越有用」，而不是燒了十億個 token 之後，後半段只是在原地空轉。

這篇整理的是 SLA（Stateless Language Agents，無狀態語言 agent；arXiv 2610.07625v1，Stanford、CMU、UW、SambaNova 的團隊，2026 年 10 月）。它的核心主張很單純：研究的「狀態」不要放在 agent 的對話裡，改由外層的控制程式（下文叫 harness）保管；agent 每次被呼叫都是全新的，harness 現場替它組出這一次需要的 context（agent 在單次呼叫裡看得到的全部內容）。

文章分成幾塊：先講論文要解的問題和方法，再看實驗數字，接著抽出兩個脫離這篇論文也成立的工程做法，接著在「概念詳解」補上幾個容易卡住的機制細節，最後交代證據的強度與還沒回答的問題。如果你只想拿走做法，可以直接跳到〈值得帶走的兩件事〉。

先給一個結果的輪廓：在 Anthropic 公開的 VLIW SIMD kernel 優化題上（Codex，每個方法跑 3 次），跑完 1B token 後，SLA 的 cycles（程式的執行週期數，越低越好）是 1112.0，最強對手 SwarmResearch 是 1275.7，少了 12.8%。想追平對手的最終成績，SLA 只用 67.9M token，對手用了 986.3M。

## 問題：長時間跑下去，為什麼會卡住

作者把長時間自動研究的困難歸成兩個挑戰。

**挑戰一：保留經驗，又不讓 context 爆掉。** 過去的候選解、評分結果、失敗紀錄之後可能還用得上，不能丟。但把一路增長的歷史反覆塞給 agent，會多花 token，表現也會變差。所以難點是留住證據的同時，讓每個 agent 只看當下決策需要的那一部分。

**挑戰二：把證據變成下一步實驗。** 有紀錄不等於知道下一步該試什麼。平行的 agent 會重複做同樣的實驗，也可能提早停止實驗，卻還在繼續消耗 token。

作者把這兩個問題歸因於兩個設計選擇：研究狀態放在哪裡（現有做法放在 agent 自己的對話裡），以及誰決定下一步試什麼（現有做法由每個 agent 自己決定）。SLA 把這兩件事都換掉了。

## 方法：狀態歸 harness，agent 只負責當下的判斷

### 狀態與 context 的分工

先把幾個詞對齊：

- **狀態（state）**：跨越多次呼叫仍然存在的東西。SLA 裡只有 harness 持有，內容是候選解與量測結果。
- **context**：agent 在一次呼叫裡看得到的內容。
- **無狀態 agent**：它累積的任何東西（包含對話）都不會帶到下一次呼叫。這不等於沒有 context，harness 會從研究狀態重建一份新的給它。

> 一個類比（這是我的類比，不是論文寫的）：無狀態的 web service 加資料庫。service 每次請求都不記得上一次，持久的資料都在資料庫裡，每次請求時才查出需要的部分。往底層看，agent 的「記憶」其實就是它的對話訊息列表，新開 session 列表就是空的，harness 再把挑選過的內容寫進第一則 prompt。這是一般常識，不是論文的內容。

harness 持有的研究狀態有四項：

- 全域最佳：目前分數最高的程式碼與分數。
- 各 Worker 的本地候選：每個 Worker 自己保留的程式碼、方向與回饋。
- 結果紀錄：每次嘗試的分數與證據狀態（有沒有跑成）。
- 完整時間序紀錄：每個實驗按時間排的完整記錄。harness 全存，但不直接給任何 agent。

### 一個 epoch 怎麼跑

整體流程如下圖。SLA 有兩種角色：Advisor（負責規劃的 agent）與 Worker（負責實作的 agent）。Advisor 每一輪被呼叫一次，這一輪叫一個 epoch；Worker 的一次嘗試叫一個 trial，每次 trial 也是一次新的呼叫。

![SLA 框架示意圖：harness 持有候選解與結果，並替 Advisor 與各 Worker 重建 context，Advisor 把全域證據轉成各 Worker 的指派。](img-003)
*圖 1 — SLA 的整體框架：以有狀態的搜尋搭配無狀態的 agent。（來源：原始論文 Figure 3。）*

一輪的大意是：harness 重建 Advisor 的 context，Advisor 替每個 Worker 指派一個實驗，Worker 在隔離空間裡做 trial，獨立的 evaluator 打分，harness 記錄結果後進入下一輪。

預設是 3 個 Worker，每個 Worker 每個 epoch 做 3 次 trial（Appendix B.1）。

Advisor 本身也是一個 LLM agent（Codex 或 Claude Code），沒有任何演算法在決定怎麼分派。它每個 epoch 讀 harness 給的證據，依各任務 prompt 裡的規則，用判斷寫出一份分派單。這份分派單裡每個 Worker 的「指派」由兩部分組成：REGIME（方向標籤，一個簡短名稱）與 PROPOSAL（具體做法的描述，Worker 讀它來動手）。把一輪拆開，大致是下面八步，哪些是 LLM 的判斷、哪些是 harness 的固定規則，分得很清楚：

| 步驟 | 誰做 | 內容 |
| --- | --- | --- |
| 1 | harness | 開一個全新的 Advisor session，放進重建好的 context |
| 2 | Advisor（判斷） | 盤點目前的瓶頸 |
| 3 | Advisor（判斷） | 選姿態：分散或集中（詳見〈姿態（分散或集中）怎麼選〉） |
| 4 | Advisor（判斷） | 替每個 Worker 寫指派，也決定要不要換方向標籤（詳見〈REGIME 標籤是什麼〉） |
| 5 | harness（固定規則） | 比對標籤。標籤沒變，Worker 接著自己的本地最佳做；標籤換了，Worker 重設為全域最佳 |
| 6 | Worker | 做幾次 trial，每次都開新 session |
| 7 | harness 與 evaluator | 評分，贏過自己最佳就保留，否則還原 |
| 8 | harness | 更新全域最佳，進入下一個 epoch（回圈） |

簡單講：比對標籤、評分、保留或還原是 harness 的規則；盤點瓶頸、選姿態、寫指派、決定何時換標籤是 Advisor 的判斷。每個 epoch 結束後，Advisor 都會開新 session 重來。

這個流程還有三條補充：

- **本地最佳只進不退。** Worker 的新候選要贏過自己的最佳才保留，輸了或出錯就還原成原本的最佳（出自 SOL-ExecBench 的 Worker prompt）。
- **全域最佳進步了，沒改派的 Worker 不會自動跟上。** 別的方向的發現只有兩條路傳過去：一是 Advisor 在指派的 PROPOSAL 裡轉述這個技巧，二是改派重設。SOL-ExecBench 的 Advisor prompt 把這兩條列為技巧跨方向傳遞的正式管道。
- **沒有 subagent。** 沒有任何 agent 會自己再開 subagent（細節見〈無狀態與隔離是怎麼「強制」的〉的表）。

### Advisor 與 Worker 各看到什麼

harness 手上有完整紀錄，但兩種角色各只拿到做決策所需的那一份。

**Advisor 的 context（每個 epoch 重建）**

- 任務規格：來源是任務 adapter（每個任務各一份設定，寫明可改的檔案、可用資源與評分流程）。
- 目前全域最佳的程式碼與分數：來源是研究狀態的「全域最佳」。
- 證據摘要：由 harness 把結果紀錄與完整紀錄加工而成（論文 §3.1），包含近期嘗試、依搜尋方向分組的結果、各 Worker 的目前狀態（來源是「本地候選」）、近期進展，以及任務專屬診斷（有的話）。
  - 任務專屬診斷論文只說「有的話」，沒講來源。我的推論是由受信任的分析程式產生，因為 Appendix E 的 Advisor prompt 提到 trusted aggregate analyzer。
  - 摘要會把「量測後沒進步」和「實作、執行或正確性出錯而無結論」分開標示，出錯不會被當成這個方向已經沒救。
- 看不到的：完整時間序紀錄（harness 有存但不給）。Appendix E 的 kernel Advisor prompt 另外明列看不到被拒絕的原始程式碼、evaluator 的測試案例、隨機種子與預期值、Worker 的對話、隱藏測試的細節。

**Worker 的 context（每次 trial 重建）**

- 任務規格：來源同上。
- 自己的指派：來源是這個 epoch 開頭 Advisor 的輸出。指派和任務規格差在哪裡，見〈指派與任務規格的差別〉。
- 自己保留的候選程式碼：來源是「本地候選」。
- 上一次 trial 的狀態、分數與正確性診斷：來源是 evaluator 的結果，由 harness 整理成簡短回饋。
- 看不到的：其他 Worker 的工作區與完整研究歷史。其他方向的證據只能透過 Advisor 的指派傳到它手上。

### 無狀態與隔離是怎麼「強制」的

這一塊是整套設計的地基，所以值得一次列清楚。論文的重點是這些性質都由系統手段實作，而不是在 prompt 裡請 agent 自己遵守。

| 對象 | 機制 | 做法 | 擋住什麼 |
| --- | --- | --- | --- |
| Advisor | 每個 epoch 開新 session | 每個 epoch 開頭，harness 啟動一個全新的 Advisor 對話，裡面只有 harness 組好的 context，沒有上一輪的任何對話 | Advisor 每輪都從當下的證據重新判斷，不會順著自己先前的推論走（§3.2） |
| Worker | 每次 trial 之後清掉已存的 session | harness 把 coding agent 存下來、可供接續的對話紀錄，連同暫存檔一起刪掉，下次 trial 開新對話 | Worker 接續不了上次 trial 的對話，只能靠 harness 給的 context |
| Worker | Landlock 檔案系統限制 | Worker 以無特權程序（沒有管理員權限的一般程序）執行，再用 Linux 核心的 Landlock 規定這個程序和它開出的子程序能讀寫哪些路徑 | 進不了其他 Worker 的目錄，也讀不到 context 之外的過往實驗檔案（B.1） |
| Worker | 限制網路存取 | harness 限制 Worker 的網路連線 | 論文沒說限制到什麼程度，也沒說防的是什麼風險 |
| Worker | 只能改指定檔案 | 每個任務的 task adapter 指定可改的檔案，其餘全部唯讀 | 候選解只能出現在指定的檔案裡 |
| Worker | evaluator 在 Worker 環境之外執行 | harness 在 Worker 之外的地方（本機或 Modal 遠端容器）跑評分，有時間與資源上限，評分程式與邏輯受保護 | Worker 改不了自己的候選解怎麼被評分（B.1） |
| Advisor 與 Worker | 關掉 Codex 內建的多 agent 功能 | 設定層面關閉 | 沒有任何 agent 自己再開 subagent。論文只在 Codex 的設定裡提到，Claude Code 沒說 |

## 實驗：數字怎麼看

實驗涵蓋好幾個基準，其中 Anthropic kernel 的主結果和 ablation（逐一拿掉零件的對照實驗）兩個最值得細看，其餘各用一小節帶過。先講一個閱讀數字時很重要的前提：重複實驗只有 Anthropic kernel（Codex）與 ablation 跑了 3 次，其餘設定每個方法只跑 1 次，所以單題的差距要保守看。

三個對手框架：

- **EvoX**：同時演化候選解與搜尋策略。
- **CORAL**：平行的 agent 自己選實驗，每個 agent 保有一個長 session。
- **SwarmResearch**：一個 Shepherd（協調者）協調多個 search agent，被指示不指派具體想法。

### Anthropic kernel 主結果

任務是 Anthropic 公開的 VLIW SIMD kernel 優化題，預算 1B token。指標 cycles 越低越好。表裡的「追平所需 token」指一個方法第一次追平「最強對手的最終成績」所需的累積 token（單位 M 是百萬），NR 代表沒追上。

**Codex（每個方法 3 次，平均 ± 標準差）**

| 方法 | 250M cycles ↓ | 1B cycles ↓ | 追平所需 token（M）↓ |
| --- | --- | --- | --- |
| EvoX | 1478.3 ± 112.0 | 1343.3 ± 4.0 | NR |
| CORAL | 1524.0 ± 101.7 | 1350.0 ± 134.2 | NR |
| SwarmResearch | 1501.7 ± 185.7 | 1275.7 ± 133.9 | 986.3 |
| SLA | 1149.3 ± 18.9 | 1112.0 ± 8.9 | 67.9 |
| SLA 相對最強對手的減少 | −22.3% | −12.8% | −93.1% |

**Claude Code（每個方法 1 次）**

| 方法 | 250M cycles ↓ | 1B cycles ↓ | 追平所需 token（M）↓ |
| --- | --- | --- | --- |
| EvoX | 1174 | 1153 | NR |
| CORAL | 1205 | 1130 | 888.3 |
| SwarmResearch | 1648 | 1243 | NR |
| SLA | 1079 | 1039 | 138.5 |
| SLA 相對最強對手的減少 | −8.1% | −8.1% | −84.4% |

幾個讀法：

- **同預算比較。** Codex 設定下，250M token 時 SLA 比當時最好的對手（EvoX，1478.3）少 22.3% cycles，跑完 1B token 比最強對手（SwarmResearch，1275.7）少 12.8%。Claude Code 設定下兩個時點都少 8.1%（250M 對 EvoX 的 1174，1B 對 CORAL 的 1130）。
- **效率比較。** 追平最強對手的最終成績，Codex 設定的對手是 SwarmResearch，需要 986.3M token，SLA 只要 67.9M，少 93.1%。Claude Code 設定的對手是 CORAL，需要 888.3M，SLA 只要 138.5M，少 84.4%。這些百分比的分母都是對手自己的用量。
- **穩定度。** Codex 設定下，SLA 的 3 次全部贏過對手的 9 次。

圖 2 把這件事畫成曲線：

![左圖為 Anthropic kernel 優化的加速倍率對累積 token 曲線，SLA 與三個對手各三次；右圖為 FrontierSWE 四題中 SLA 與最強對手在 175M 與 700M token 時的分數差。](img-001)
*圖 2 — SLA 在長時間跑下去之後持續進步。左半是 Anthropic kernel，右半是 FrontierSWE 四題，後者在下一小節討論。（來源：原始論文 Figure 1。）*

左半的訊息是：SLA 用 67.9M 對 986.3M，少用 14.5 倍的 token 就追平對手的最終成績，而且每一次 SLA 的 run 都贏過每一次對手的 run。

### Ablation：各拿掉一個零件

主結果只能說 SLA 整體比較好，沒法說是哪個零件貢獻的。Ablation 就是各拿掉一個，看掉多少。

做法是從 SLA 跑到 10% 或 20% 預算時存下的研究狀態（checkpoint）出發，每個設定再跑 100M token，3 次取平均 ± 標準差。kernel 預算 1B，存檔在 100M、200M；libexpat（FrontierSWE 的一題，用組合語言重寫 XML parser，預算 700M，分數乘 100，越高越好）存檔在 70M、140M。三個變體都仍然是無狀態，只改「各 context 裡放什麼」或「有沒有指派」：

- **拿掉 Advisor 重建**（w/o Advisor reconstruction）：Advisor 沒有 harness 整理的摘要，改成自己透過唯讀介面去讀完整紀錄。
- **拿掉 Worker 隔離**（w/o Worker isolation）：Worker 看得到完整紀錄和其他 Worker 的候選解。
- **拿掉指派**（w/o Advisor assignments）：Worker 拿到的是「做一次獨立嘗試」的 prompt，不是 Advisor 的指派。這個變體到底拿掉了什麼，見〈「拿掉指派」的 ablation 是什麼意思〉。

| 設定 | kernel 100M→200M cycles ↓ | kernel 200M→300M cycles ↓ | libexpat 70M→170M 分數 ↑ | libexpat 140M→240M 分數 ↑ |
| --- | --- | --- | --- | --- |
| 存檔起點 | 1218 | 1197 | 16.12 | 17.69 |
| 完整 SLA | 1192.3 ± 2.5 | 1170.0 ± 14.2 | 18.78 ± 0.92 | 20.13 ± 0.20 |
| 拿掉 Advisor 重建 | 1198.3 ± 2.3（−23.3%） | 1188.7 ± 6.8（−69.3%） | 16.86 ± 0.64（−72.2%） | 19.07 ± 0.31（−43.4%） |
| 拿掉 Worker 隔離 | 1203.3 ± 7.1（−42.8%） | 1174.7 ± 4.5（−17.4%） | 16.79 ± 0.47（−74.8%） | 19.77 ± 0.12（−14.8%） |
| 拿掉指派 | 1195.0 ± 2.6（−10.5%） | 1182.3 ± 8.1（−45.6%） | 16.54 ± 0.33（−84.2%） | 18.85 ± 0.12（−52.5%） |

括號裡的百分比，是該變體的進步量比完整 SLA 少的比例。分母是完整 SLA 相對存檔起點的進步量，四欄依序是 25.7、27.0 cycles 與 2.66、2.44 分。舉 kernel 第一欄為例：拿掉 Worker 隔離只從 1218 降到 1203.3，進步 14.7，(25.7 − 14.7) ÷ 25.7 = 42.8%。

結論與它的強度：

- 12 格（3 個變體 × 4 欄）的平均值全部比完整 SLA 差，論文據此主張三個零件都有貢獻。
- 單格的證據其實不強。其中兩格的差距和標準差在同一量級：kernel 200M→300M 拿掉隔離，差 4.7 cycles，完整 SLA 的標準差是 14.2；kernel 100M→200M 拿掉指派，差 2.7，兩邊標準差約 2.5 到 2.6。每格只有 3 次，單格不能當證據，12 格方向一致才是比較有力的訊號。
- 另有一次完整 1B run：只拿掉 Worker 隔離，跑完整預算得 1336 cycles，比完整 SLA 三次平均（1112.0）差 224 cycles；續跑 100M 時同一個變體只差 5 到 11 cycles。論文只描述了這一次完整 run，並以此主張缺乏焦點 context 的代價會隨時間放大。

### FrontierSWE 四題：排名會隨預算反轉

FrontierSWE 是長時間軟體工程基準，論文選了 4 題（libexpat → x86-64 Assembly、Git → Zig、Dart → Haskell、Lua Native Compiler），官方分數乘 100，越高越好，預算 700M token，Codex，每個方法只跑 1 次。這組實驗要證明的是：方法的排名會隨預算改變，短預算的評估會誤判方法。

![FrontierSWE 四題的成績表，分 libexpat 到 x86-64 組合語言、Git 到 Zig、Dart 到 Haskell、Lua Native Compiler 四個子表，列出各方法在 175M 與 700M token 時的分數與追平所需 token。](img-005)
*表 1 — FrontierSWE 四題在 25% 與 100% 預算下的分數與 token 效率。（來源：原始論文 Table 2。）*

- 25% 預算（175M token）：SLA 在 4 題都落後最強對手，落後 0.85 到 11.27 分。
- 100% 預算（700M token）：SLA 在 4 題都領先，領先 0.86 到 6.75 分，平均 4.95 分，其中 Git→Zig 只領先 0.86 分。

各題差距（175M → 700M，分數差）：

| 題目 | 175M | 700M |
| --- | --- | --- |
| libexpat | −0.85 | +6.75 |
| Git→Zig | −3.90 | +0.86 |
| Dart→Haskell | −11.27 | +6.68 |
| Lua Native Compiler | −2.75 | +5.49 |

這也是圖 2 右半在畫的東西：空心圓是 175M 的差距，實心圓是 700M 的差距。

### SOL-ExecBench 三題與 FrontierCS

SOL-ExecBench 是 GPU kernel 基準，論文選三題不同的 GPU kernel 優化：#1（attention 的反向傳播）、#58（MoE 的 token 排序與前綴和）、#210（殘差加法與 RMS 正規化的融合）。SOL 分數介於 0 到 1，越接近 1 表示 kernel 越接近硬體極限（SOL 是 speed-of-light），baseline 為 0.5，硬體極限為 1.0。預算 500M token，Codex，每個方法 1 次。

FrontierCS 是演算法設計基準，論文選 Structured-LWE，一個密碼學題目，要從公開的結構化 learning-with-errors 實例中恢復有效的秘密向量，分數越高越好。

![SOL-ExecBench 三題與 FrontierCS Structured-LWE 的成績表，列出各方法在 25% 與 100% 預算下的分數，以及追平最強對手所需 token。](img-006)
*表 2 — SOL-ExecBench 與 FrontierCS 在不同預算下的分數與 token 效率。（來源：原始論文 Table 3。）*

SOL-ExecBench 在 500M token 的分數（對同題最強對手 EvoX）：

- #1：0.763 對 0.710（+7.5%）
- #58：0.862 對 0.804（+7.2%）
- #210：0.393 對 0.386（+1.8%）
- 三題平均 +5.5%

百分比的分母都是 EvoX 的分數。

追平最強對手最終成績所需的 token：#58 是 SLA 14.5M 對 EvoX 354.1M（少 95.9%），#210 是 208.3M 對 283.0M（少 26.4%）。#1 是 SLA 152.7M 對 EvoX 46.1M，SLA 比較慢，但終點分數較高。

#210 幾乎沒差：25% 到 100% 預算間，沒有任何方法進步超過 0.02。論文推測原因是所有方法最好的 kernel 都用 Triton，對 warp 層級歸約的控制不如 CUDA，可能限制了上限。注意這是論文用「may」表述的推測。

FrontierCS Structured-LWE 的結果：200M token 時 SLA 59.5 對 SwarmResearch 58.0（高 1.5 分，+2.6%）；50M token 時 48.5 對 44.0（+10.2%）。追平最強對手最終成績所需的 token，SLA 是 169.6M，SwarmResearch 是 197.0M，少 13.9%。這幾個百分比的分母都是 SwarmResearch 的數字。

### 協調成本：Advisor 很便宜

SLA 多了一個 Advisor，自然要問它貴不貴。成本以 GPT-5.5 費率估算（每百萬 token：未快取輸入 5 美元、快取輸入 0.5 美元、輸出 30 美元），不含執行與評估實驗的算力。

![SLA 與 SwarmResearch 在 Anthropic kernel 與 FrontierSWE libexpat 上的 token 組成，以及協調者占總 token 與總成本的比例。](img-008)
*表 3 — token 組成與協調成本。（來源：原始論文 Table 5。）*

| 任務 | 方法（協調者） | 協調者占 token | 協調者占成本 |
| --- | --- | --- | --- |
| Anthropic kernel（1B） | SLA（Advisor） | 0.24% | 1.20% |
| Anthropic kernel（1B） | SwarmResearch（Shepherd） | 8.39% | 6.14% |
| FrontierSWE libexpat（700M） | SLA（Advisor） | 0.51% | 2.29% |
| FrontierSWE libexpat（700M） | SwarmResearch（Shepherd） | 10.70% | 7.35% |

Advisor 的成本占比比 token 占比高：快取輸入占兩個方法 token 的 90% 以上，而快取輸入便宜很多，所以 token 占比會低估快取少的角色（像 Advisor）的成本。即使換算成成本，Advisor 也只占 1% 到 2% 出頭。Shepherd 的 token 占比高，主因是它的 context 很長：kernel run 中每次呼叫平均讀入約 99K input token，新 session 開頭約 8K。

### Worker 數量：沒有通用的最佳寬度

預設的 Worker 數是 $W=3$。論文把 $W$ 取 $\{1, 3, 7, 15\}$，在固定預算下比較（kernel 1B，FrontierSWE 每題 700M）。

![不同 Worker 數量在 Anthropic kernel 與 FrontierSWE 四題上，於 25% 與 100% 預算時的表現與耗時。](img-009)
*表 4 — Worker 數量對表現與耗時的影響。（來源：原始論文 Table 6。）*

- **時間。** $W$ 從 1 到 15，kernel 跑完時間從 98.1 小時降到 14.8 小時（6.6 倍）；FrontierSWE 每題平均從 62.1 小時降到 8.5 小時（7.3 倍）。
- **kernel 的品質。** 25% 預算時 $W=7$、$W=15$ 分別比 $W=1$ 差 337、174 cycles（1488、1325 對 1151），但跑完整預算後，四種寬度都落在 1107 到 1113 cycles。
- **FrontierSWE 100% 預算的最佳寬度因題而異。** Dart 是 $W=3$（45.2），Git→Zig 與 libexpat 是 $W=7$（29.0、34.5），Lua 是 $W=1$（97.3）。
- **預設 $W=3$ 的位置。** kernel 距最佳 5 cycles 內，FrontierSWE 各題距最佳 3.2 分內，時間比 $W=1$ 快 2.5 到 2.7 倍。

論文的結論是：Worker 數要依任務、token 預算與時間限制選，沒有通用的最佳寬度。

### Worker 換成便宜的模型：同成本比較

Advisor 固定用 GPT-5.5、Worker 3 個，比較 Worker 用 GPT-5.5 或 GPT-5.4 mini。成本含 Advisor 與 Worker，依各模型費率計算（GPT-5.4 mini 每百萬 token：未快取輸入 0.75 美元、快取輸入 0.075 美元、輸出 4.5 美元）。

![兩張折線圖：左為 Anthropic kernel，右為 FrontierSWE Git 到 Zig，比較 GPT-5.5 與 GPT-5.4 mini 作為 Worker 時，最佳表現隨累積模型成本的變化。](img-010)
*圖 3 — Worker 模型選擇：以相同成本比較最佳表現。（來源：原始論文 Figure 4。）*

成本 100 美元時，FrontierSWE Git→Zig 上 GPT-5.4 mini 的 Worker 較高（20.88 對 19.68），Anthropic kernel 上則是 GPT-5.5 的 Worker 領先。論文的解釋是：便宜的模型每塊錢消耗更多 token，可能抵銷單次品質較低，這在部分任務成立、部分不成立。這句同樣是論文用「may」表述的推測。

## 值得帶走的兩件事

下面兩件事是讀這篇論文得到、但脫離它也成立的。想直接套用在自己的 agent 系統上，看這一段就夠了。

### 無狀態與隔離要由系統強制，不是在 prompt 裡請 agent 遵守

想讓 agent 具備某個性質（不接續上次、看不到別人、改不了評分），要用 agent 做不到的手段去擋，不要用文字請它不要做。

論文把它寫成設計選擇（§3.3：statelessness and isolation are enforced rather than requested）。為什麼成立，是我的推論，屬一般工程推理，不是論文的實驗結果：prompt 只是輸入的一部分，模型可能不照做，系統層級的限制則是 agent 的行為改不了的。

| 想要的性質 | 請求式（靠 agent 自己遵守，自編例子） | 強制式（論文的做法） |
| --- | --- | --- |
| 不接續上次對話 | 「請忘記上次的內容」 | 開新 session，並清掉已存的 session |
| 看不到其他 Worker 的檔案 | 「不要讀別人的目錄」 | 無特權程序加 Landlock 路徑限制 |
| 改不了自己怎麼被評分 | 「不要動評分程式」 | evaluator 在 Worker 環境之外執行 |
| 不自己開 subagent | 「不要啟動 subagent」 | 在設定層面關掉內建多 agent 功能 |

Landlock 是 Linux 核心的功能，讓程序限制自己能讀寫的路徑。這是一般知識，不是論文的內容。各機制的完整做法見〈無狀態與隔離是怎麼「強制」的〉那張表。

怎麼用？對每個你需要的性質問自己一句：「agent 想違反時，做得到嗎？」做得到，就是請求式，要換成強制式。下面兩段是自編的示意。

請求式是把規矩寫進 prompt，靠 agent 自己遵守：

```
prompt += "不要讀其他 Worker 的目錄"
```

強制式是 agent 想讀也讀不到，因為啟動它的時候就限定了它能碰的路徑：

```
launch(agent, user="unprivileged", fs_allow=[my_workspace, public_task_files])
```

### 彼此看不到對方的平行 agent，沒有明確分工時會挑到同一個缺口

平行的 agent 如果輸入相同、又互相看不到，沒有人分派方向，它們就會各自做同一件事。

證據來自論文的一個 trace 範例：

![兩個 trace 範例。左側是沒有指派時，三個 Worker 各自對同一份起始程式碼加上同一個 XML 文字解碼功能，分數都沒進步；右側是完整 SLA 中，Advisor 要另一個 Worker 接續一次成功的改動，使分數進一步提升。](img-014)
*圖 4 — 實驗選擇與接續改進的 trace 範例。（a）沒有指派時三個 Worker 做了同一件事；（b）完整 SLA 讓另一個 Worker 接在成功的改動上。（來源：原始論文 Figure 5。）*

（a）的情形是：沒有指派時，三個 Worker 獨立地對同一份起始程式碼加上同一個 XML 文字解碼功能，沒有一個分數進步。論文說另外兩次重複實驗也出現同樣的情形，但也坦白這些案例沒有量測發生的頻率（Appendix D.3）。

為什麼會這樣，是我的推論：起點程式碼相同、任務規格相同、彼此看不到，三個條件同時成立時，沒有任何東西讓三個 Worker 的選擇不同，所以各自挑到最明顯的缺口。這跟集成（ensemble）需要多樣性是同一個道理，輸入相同的獨立決策者，結論會很像。

怎麼用？用一段自編的示意：

```
if workers 彼此看不到:
    由一個能看全局的角色，替每個 Worker 派不同的方向
    每份指派要宣告它動到哪一類東西
```

第一行是 SLA 的做法。第二行的用意是讓重疊可以被檢查，這是我的推論。

- 論文的 kernel Advisor prompt 要求每份提案寫明它會省掉哪一類運算，這是論文事實。至於拿這個欄位來檢查重疊，論文沒說有這麼用。
- 有一個例外：集中攻同一個瓶頸時，prompt 規定各 Worker 的做法要實質不同。所以去重的層級是「做法」，不是「瓶頸」。

## 概念詳解

以下各段各自獨立，可以單獨閱讀。〈一個 epoch 怎麼跑〉的表格提到的名詞，都在這裡有展開。

### 重置不是失憶：Advisor 每輪對話清空，為什麼還記得實驗結果

Advisor 每個 epoch 開新 session（對話清空），但已知的實驗結果存在 harness 的帳本裡，每次都會再交給它。

出處是 Appendix E（p.24）Anthropic Kernel Advisor Prompt 的 Research policy 最後一條，原句是「Reset means fresh reasoning from measured state, not amnesia」。它前面還有一句：用整理過的帳本，避免重複已有強烈負面證據的機制。

意思是：「重置」是指對話被清空，要從量測到的狀態重新推理，但這不是失憶，帳本還在，所以不該叫人去重試已有強烈負面證據的機制。帳本的內容是 sanitized scalar research ledger（淨化過的純數字研究帳本），只有數字，被拒絕的原始程式碼、evaluator 的測試案例、Worker 的對話都刻意不放（p.23 的 prompt）。

白話一點：Advisor 每輪腦袋是空的，但桌上有一本實驗紀錄，它不能假裝沒看到。

### 姿態（分散或集中）怎麼選

Advisor 是 LLM agent（Codex 或 Claude Code，§3.3），沒有演算法在算要分散還是集中，它照各任務 prompt 的規則判斷。

兩種姿態：

- **分散（diversify）**：好幾種機制都有可能時，各 Worker 去不同方向。
- **集中（concentrate）**：有一個明顯瓶頸時，多個 Worker 各用不同做法攻同一個瓶頸。

各任務 prompt 的規則不太一樣：

| 任務 | 規則 |
| --- | --- |
| kernel（Appendix E） | 先做資源盤點，把目前分數和引擎容量下限比較，找出是哪類運算造成下限；選集中要說明為什麼比分散更值得，且各做法要實質不同；整批 Worker 最多一個做小修小補，其餘必須做機制層級的改動。輸出有一欄 SEARCH POSTURE 寫明姿態（確切格式由 runner 提供，論文沒給） |
| SOL-ExecBench | 預設分散；某方向有強烈局部訊號時才集中，之後回到分散 |
| FrontierSWE | 紀錄顯示某個 build、export 或正確性關卡主導時才集中 |

至於 Advisor 實際多常選哪一種，論文沒報告，也沒有實驗比較兩種姿態。

我從論文的實例推出一個觀察（推論）：Appendix D.3 與圖 4(b) 的完整 SLA 例子中，Advisor 要 Worker 2 在 Worker 1 的改進上繼續，其餘 Worker 分去 parser 的其他部分，同一輪同時有一路集中在贏家上、其餘分散。論文沒說這算哪種姿態，所以姿態大概不是嚴格二選一。

### REGIME 標籤是什麼

REGIME 是 Advisor 給每個 Worker 的方向標籤，一個簡短名稱，代表一類做法。完整的指派等於 REGIME（標籤）加 PROPOSAL（具體做法的描述，Worker 讀它來動手）。

- **格式。** SOL-ExecBench 的 prompt 要求用短的 kebab-case（小寫加連字號），自編例子：`fused-reduction`。
- **作用。** 讓 harness 判斷 Worker 是接續還是改派。標籤不變，Worker 接著自己的進度做；換新標籤，harness 把它重設為全域最佳（見〈Worker 每個 epoch 從哪裡開始做〉）。
- **REGISTRY 表。** SOL prompt 要求 Advisor 在輸出裡列出每個方向的狀態：maturing（還在進步）、mature-WIN（成熟且勝出）、pruned（已淘汰）。

適用範圍要小心：論文只在 SOL-ExecBench 的 prompt 裡把標籤和規則寫清楚，kernel 與 FrontierSWE 的 prompt 沒有，細節見〈Worker 每個 epoch 從哪裡開始做〉。

### Worker 每個 epoch 從哪裡開始做

沒改派，接著自己上個 epoch 的本地最佳做；被改派，才從全域最佳重新出發。

| 情況 | Worker 的起點 |
| --- | --- |
| 下個 epoch 沒改派（SOL-ExecBench 是標籤不變） | 自己的本地最佳，包含上個 epoch 累積的進步 |
| 被改派（標籤換了） | 全域最佳，第一個成功評分的候選成為新的本地基準 |

依據是 §3.2（p.5）：harness 保留每個 Worker 的本地進步，即使它落後全域最佳，好讓其他方向有時間成熟；只有 Advisor 改派時，Worker 才從全域最佳重來。

SOL-ExecBench Worker prompt 寫「Same REGIME continues the lane」，意思是標籤相同就延續這條 lane（lane 是 Worker 自己的獨立工作線，有自己的工作區與本地最佳），並規定 trial 的保留規則：贏過自己 lane 的最佳才保留，輸了或出錯就還原成 lane 最佳。

還有一個缺口：「沒改派」在不同任務怎麼判定，只有 SOL-ExecBench 明寫是標籤相同。kernel 與 FrontierSWE 的 prompt 沒提標籤，§3.2 只說 redirect。我的推論是兩者的機制相同，但原文沒有逐項確認。

### 一個 epoch 內 Advisor 會不會打斷 Worker

不會。Advisor 只在 epoch 開頭被呼叫一次，所以一個 epoch 內不會做到一半被換標籤；改派就是下個 epoch 的分派單換了新標籤。這是我從論文結構推出來的，論文沒有一句話明講。

依據有三條：

- 每個 Advisor epoch 是一次呼叫，每個 Worker trial 也是一次呼叫（§3）。
- SOL-ExecBench Advisor prompt 說每個 Worker 每個 epoch 有固定次數的 trial，所以一份 proposal 要大到夠做好幾次修改；Worker prompt 也說同一份指派會重複用在好幾次 trial。
- Appendix C.2：每 epoch 1 次 trial 時續跑 21 到 34 個 epoch，5 次時只有 6 到 8 個，吻合 epoch 數 = 預算 ÷ 每輪 trial 數，沒有中途插入 Advisor 的跡象。

唯一的例外是預算用完。外部計數器直接停掉整個 run（B.2），最後一輪可能做不滿 3 次，但那是整個 run 結束，不是被換標籤。

還有三點論文沒交代：

- 有沒有任何中途打斷的機制：沒明講，我的推論是沒有。
- 失敗或被丟棄的 trial 算不算那 3 次：B.1 只說這類 trial 會把 Worker 還原成原本保留的本地候選，沒說算不算次數。
- 3 個 Worker 是否同步等到全部做完才進入下一個 epoch：沒說。

### 指派與任務規格的差別

指派是 Advisor 針對某個 Worker 寫的一段文字：這個 epoch 要試哪一個具體的改法。它是 Advisor 的輸出，harness 原封不動放進該 Worker 的 context。

- **指派管什麼：** 方向，也就是做哪一類改動以及為什麼值得做。kernel 的 Advisor prompt 規定每份指派要寫三件事：它預計省掉哪一類運算、預期省多少、依賴哪個正確性不變量（correctness invariant，改了之後輸出必須保持不變的條件）。
- **指派不管什麼：** 實作細節。怎麼實作與怎麼修正，由 Worker 在接下來幾次 trial 自己決定（p.5）。
- **用幾次：** 一份指派會用於同一個 epoch 的好幾次 trial（預設 3 次），下個 epoch 才由 Advisor 重新指派（B.1）。
- **和本地候選的關係：** 指派說「往哪走」，本地候選是「目前走到哪」。

用一個自編的例子感受一下（不是論文裡的原文）：REGIME 寫 `fused-reduction`，PROPOSAL 寫「把兩段各自掃一遍記憶體的歸約合併成一段，省掉一次記憶體往返，預期省下一小部分 cycles；改完輸出必須和原本一致」。方向、預期收益、依賴的不變量都有，但怎麼改程式是 Worker 的事。

| | 任務規格 | 指派 |
| --- | --- | --- |
| 內容 | 要解什麼問題、怎麼算分、哪些檔案可改、哪些做法禁止 | 這個 epoch 要試的一個具體方向 |
| 誰寫的 | 人類事先定好（任務 adapter 與公開任務說明） | Advisor 每個 epoch 現寫 |
| 會變嗎 | 整個 run 都不變 | 每個 epoch 重寫，每個 Worker 各不相同 |
| 誰有 | Advisor 和所有 Worker 拿到同一份 | 只有被指派的那個 Worker |

要提醒的是，「任務規格」的具體內容是我的推論。正文 p.5 只寫 task specification 這個詞，沒有逐項列出；我對照 Appendix E 的 prompt 推出（Worker prompt 裡的 Valid candidate contract 和各任務的 `{task_target}`，FrontierSWE 另外讀 PUBLIC_TASK_INSTRUCTION.md），論文沒有逐字對應。

### 「拿掉指派」的 ablation 是什麼意思

Worker 仍然知道要做什麼，只是不知道這一輪往哪個方向做。

| | 完整 SLA | 拿掉指派 |
| --- | --- | --- |
| 任務規格（整個問題的定義） | 有 | 有 |
| 自己保留的候選解與上次回饋 | 有 | 有 |
| Advisor 寫的 PROPOSAL（這一輪的具體方向） | 有 | 沒有 |
| 取而代之的是 | 無 | 一個「做一次獨立嘗試」的 prompt |

- **Worker 的目標沒變。** 任務規格已經說了要提高哪個分數，它手上也有目前的程式碼，所以知道要把分數做上去；缺的是方向，該先做哪個功能、攻哪個瓶頸，由每個 Worker 自己從程式碼挑。
- **Advisor 照常運作。** 它還是每個 epoch 被叫起來、寫分派單，token 也照算（B.1），只是 Worker 看不到這份分派單；論文說它仍然可以把 Worker 的候選解重設為全域最佳。
- **這個實驗在測什麼。** 同一個 Advisor、同一份證據都在，唯一差別是 Worker 有沒有收到明確方向。如果 Worker 自己挑也一樣好，Advisor 的分派就沒價值。
- **論文未說明。** 「做一次獨立嘗試」的 prompt，論文原文只寫「a prompt for an independent trial」，prompt 的實際內容沒有附。

結果的例子就是〈彼此看不到對方的平行 agent，沒有明確分工時會挑到同一個缺口〉那一節的圖 4(a)。

## 證據強度與還沒回答的問題

這篇論文的結果方向一致，但有幾個地方要保守看：

- 多數設定每個方法只跑 1 次，FrontierSWE 四題的排名反轉就是 1 次 run 的結果。
- Ablation 的 12 格雖然全部比完整 SLA 差，但單格往往和標準差同一量級，拿掉隔離的完整 1B run 也只有一次。
- 「Worker 挑到同一個缺口」的案例，論文沒有量測發生頻率。
- Advisor 的決策品質還沒被獨立檢驗。論文自己在 Discussion（p.11）也說，這是剩下的問題。
- 部分機制細節論文沒講清楚，例如不同任務怎麼判定「沒改派」、網路限制到什麼程度，都已在〈概念詳解〉與前面的表裡逐項標出。

## 結論

SLA 的設計可以濃縮成兩句話：研究狀態由 harness 保管，agent 每次都從重建的 context 重新判斷；下一步試什麼由 Advisor 統一分派，而不是讓每個 agent 各自挑。

數字上，在 Anthropic kernel 的主結果、FrontierSWE 四題和 SOL-ExecBench 上，SLA 都在跑完整預算時領先；ablation 的 12 格方向一致，指向三個零件都有貢獻。Advisor 只占不到 0.6% 的 token，協調成本很低。

證據的強度前面已經交代過，要保守看。比起具體數字，更值得帶走的是兩個做法：agent 需要的性質要用系統手段強制，不要靠 prompt 請它遵守；彼此看不到的平行 agent，要有一個看得到全局的角色替它們分工。

```figure-map
[
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 3: The SLA framework: stateful search with stateless agents. The harness owns candidates and outcomes and rebuilds a fresh and role-specific context for the Advisor each epoch and for each Worker each trial (§3.1). The Advisor turns global evidence into coordinated assignments (§3.2).",
    "why_used": "支撐「一個 epoch 怎麼跑」：說明 harness、Advisor、Worker 的整體流程。",
    "agent_match_hint": "一張框架示意圖，harness 在中間，連到 Advisor 與多個 Worker 的流程。"
  },
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1: SLA sustains research progress over long horizons. (a) On Anthropic kernel optimization, SLA finds stronger solutions and reaches the strongest baseline’s mean final performance with 14.5× fewer tokens (a 93.1% reduction); every SLA run finishes ahead of every baseline run. Thick curves show means over three runs per method; thin curves show individual runs. (b) On all four FrontierSWE tasks, SLA trails the strongest per-task baseline at 175M tokens (25% of the budget, open circles) but leads at 700M (full budget, filled circles). All results use Codex with GPT-5.5.",
    "why_used": "呈現主結果：kernel 上 SLA 用更少 token 追平對手，以及 FrontierSWE 四題的排名反轉。",
    "agent_match_hint": "兩個子圖，左為折線圖（加速倍率對累積 token），右為各題 SLA 與最強對手分數差的圓點圖。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Table 2: FrontierSWE performance and token efficiency with Codex. Official scores (×100) at 25% (175M) and 100% (700M) of the token budget, and cumulative tokens needed to first match the strongest baseline’s full-budget score (NR: not reached). One run per method. Bold: best per column; underline: second best. The last row of each panel gives SLA’s score difference from the strongest baseline (points) and its relative token reduction: SLA trails on all four tasks at 175M but leads at 700M.",
    "why_used": "給出 FrontierSWE 四題在 25% 與 100% 預算下的完整數字，支撐排名反轉的說法。",
    "agent_match_hint": "一張含四個子表的表格，欄位是 175M 與 700M 的分數及追平所需 token。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 3: SOL-ExecBench and FrontierCS performance and token efficiency with Codex. SOL scores ([0, 1]) and FrontierCS task scores at 25% and 100% of each task’s token budget, and cumulative tokens needed to first match the strongest baseline’s full-budget score (NR: not reached). One run per method. Bold: best per column; underline: second best. The last row of each panel gives SLA’s relative difference from the strongest baseline.",
    "why_used": "給出 SOL-ExecBench 與 FrontierCS 的完整數字，支撐後面逐題的百分比。",
    "agent_match_hint": "一張含兩個子表的表格，上排 SOL-ExecBench 三題，下排含 FrontierCS Structured-LWE。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Table 5: Token usage and coordination overhead. Token composition and coordinator share (SLA Advisor or SwarmResearch Shepherd) of tokens and estimated cost at the full budget, using GPT-5.5 rates of $5/$0.50/$30 per million uncached-input, cached-input, and output tokens [26]. Bold: lower share.",
    "why_used": "支撐「協調成本」一節：Advisor 與 Shepherd 的 token 與成本占比。",
    "agent_match_hint": "一張小表格，列出 token 組成與協調者占比，兩個任務各兩列。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Table 6: Worker scaling at fixed token budgets. Best-so-far performance and time at 25% and 100% of the token budget (1B for Anthropic kernel; 700M per FrontierSWE task) as the number of Workers W varies. FrontierSWE scores are official scores (×100); mean time is the average time per FrontierSWE task. Colored values give the change from W=1 in the same block (green: better; red: worse), and wall-clock speedup for time. Shaded: default W=3 used in all other experiments. Bold: best per column within each block.",
    "why_used": "支撐 Worker 數量的比較：不同 W 下的表現與耗時。",
    "agent_match_hint": "一張分短期與長期兩個區塊的表格，列出 W 為 1、3、7、15 的表現與時間。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "Figure 4: Worker model selection at matched cost. Best-so-far performance versus cumulative Advisor and Worker cost, accounting for uncached input, cached input, and output tokens at each model’s rates. All runs use a GPT-5.5 Advisor and three Workers. (a) Anthropic kernel optimization. (b) FrontierSWE Git→Zig.",
    "why_used": "支撐 Worker 換成便宜模型的同成本比較。",
    "agent_match_hint": "兩張折線圖，標題為 Anthropic kernel 與 FrontierSWE Git→Zig，各有兩條不同模型的曲線。"
  },
  {
    "id": "img-014",
    "references_manifest_caption": "Figure 5: Trace examples of experiment selection and refinement. (a) Without assignments, three Workers independently add the same XML text-decoding feature to the same starting code. None improves its score. (b) Full SLA assigns another Worker to build on a successful change, further improving the solution. Scores are multiplied by 100, as in the main results.",
    "why_used": "以具體 trace 說明沒有指派時 Worker 會重複同一件事，以及有指派時如何接續改進。",
    "agent_match_hint": "兩個子圖，上方是三個 Worker 做同一個功能的示意，下方是三欄的接續改進流程。"
  }
]
```
