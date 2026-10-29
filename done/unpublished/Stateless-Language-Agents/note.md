# SLA 論文筆記：Stateless Language Agents 與長時間自動研究

Oct 18, 2026 · @YHHW

## 三十秒版本

SLA（Stateless Language Agents，無狀態語言 agent；arXiv 2610.07625v1，Stanford、CMU、UW、SambaNova，2026 年 10 月）提出一個長時間自動研究系統的設計原則：研究狀態由外層控制程式（harness）保管，agent 本身不保留對話，每次被呼叫時由 harness 現場重建一份它需要的 context（agent 在一次呼叫中看得到的全部內容）。

- 做法：一個無狀態的 Advisor（負責規劃的 agent）讀 harness 整理好的證據，替多個平行的 Worker（負責實作的 agent）各指派一個具體實驗；Worker 在隔離環境裡實作，由獨立的 evaluator 評分。
- 主結果：在 Anthropic 的 VLIW SIMD kernel 優化題（Codex，每個方法跑 3 次），跑完 1B token 後 SLA 的 cycles 為 1112.0，最強對手 SwarmResearch 為 1275.7，少 12.8%（cycles 是程式的執行週期數，越低越好；分母是 SwarmResearch 的 1275.7）。
- 效率：SLA 只用 67.9M token 就達到最強對手的最終成績，對手用了 986.3M，少 93.1%（分母是對手自己的用量，接近整個 1B 預算）。
- Ablation：從同一份存檔出發，各拿掉 Advisor 的 context 重建（harness 整理的摘要）、Worker 隔離、Advisor 的指派，12 組比較的平均值全部比完整 SLA 差。
- 值得帶走：兩個脫離這篇論文也成立的做法。一、要讓 agent 具備某個性質（不接續對話、看不到別人的檔案），要用系統手段強制，不要靠 prompt 請它遵守。二、彼此看不到對方的平行 agent，沒有明確分工時會挑到同一個缺口。

## 索引

以下【概念】段落位於文末的「概念詳解」，各自獨立，不需要先讀主線就能看懂。

- 【概念】① 重置不是失憶：Advisor 每輪對話都清空，為什麼還記得實驗結果
- 【概念】② 姿態（分散或集中）怎麼選
- 【概念】③ REGIME 標籤是什麼
- 【概念】④ Worker 每個 epoch 從哪裡開始做
- 【概念】⑤ 一個 epoch 內 Advisor 會不會打斷 Worker
- 【概念】指派與任務規格的差別
- 【概念】「拿掉指派」的 ablation 是什麼意思

## 1. 問題與挑戰

**挑戰 1（保留經驗，又不讓 context 爆掉）：** 過往的候選解、評分結果與失敗紀錄之後可能還用得上，不能丟，但把一路增長的歷史反覆交給 agent 會多花 token 並讓表現變差，所以難點是留住證據、同時讓每個 agent 只看當下決策需要的部分。

**挑戰 2（把證據變成下一步實驗）：** 有紀錄不等於知道下一步該試什麼，平行的 agent 會重複做同樣的實驗，也可能提早停止實驗卻繼續消耗 token。

**重點：** 作者把這兩個問題歸因於兩個設計選擇。一是研究狀態放在哪裡（現有做法放在 agent 自己的對話裡），二是誰決定下一步試什麼（現有做法由每個 agent 自己決定）。SLA 把這兩件事都換掉。

## 2. 方法

### 2a. 狀態與 context

SLA 把「記憶」從 agent 的對話搬到 harness：agent 每次被呼叫都是全新的，所需資訊由 harness 現場組給它。

- 狀態（state）：跨越多次呼叫仍然存在的東西。SLA 裡只有 harness 持有，內容是候選解與量測結果。
- context：agent 在一次呼叫裡看得到的內容。
- 無狀態 agent：它累積的任何東西（包含對話）都不會帶到下一次呼叫。這不等於沒有 context，harness 會從研究狀態重建一份新的給它。
- 類比（我的類比，不是論文寫的）：無狀態的 web service 加資料庫。service 每次請求都不記得上一次，持久的資料都在 DB，每次請求時才查出需要的部分。底層上，agent 的「記憶」就是它的對話訊息列表，新開 session 列表就是空的，harness 再把挑選過的內容寫進第一則 prompt（這是一般知識，不是論文內容）。

harness 持有的研究狀態包含四項：

- 全域最佳：目前分數最高的程式碼與分數
- 各 Worker 的本地候選：每個 Worker 自己保留的程式碼、方向與回饋
- 結果紀錄：每次嘗試的分數與證據狀態（有沒有跑成）
- 完整時間序紀錄：每個實驗按時間排的完整記錄（harness 全存，但不直接給任何 agent）

**整體流程。** 請看 Figure 3（p.5），原 caption：「Figure 3: The SLA framework: stateful search with stateless agents. The harness owns candidates and outcomes and rebuilds a fresh and role-specific context for the Advisor each epoch and for each Worker each trial (§3.1). The Advisor turns global evidence into coordinated assignments (§3.2).」

1. harness 重建 Advisor 的 context
2. Advisor 指派實驗給各 Worker
3. 每個 Worker 在隔離空間做幾次試驗（trial）
4. 獨立的 evaluator 打分
5. harness 記錄結果，更新各 Worker 的最佳候選與全域最佳，回到第 1 步

- epoch 是 Advisor 的一輪（一次呼叫），trial 是 Worker 的一次嘗試（也是一次呼叫），每次都開新 session。
- 預設 3 個 Worker，每個 Worker 每個 epoch 做 3 次 trial（Appendix B.1）。

### 2b. Advisor 與 Worker 的 context

harness 手上有完整紀錄，但兩種角色各只拿到做決策所需的那一份。每項後面註明來源。

**Advisor 的 context（每個 epoch 重建）**

- 任務規格：來源是任務 adapter（每個任務各一份設定，寫明可改的檔案、可用資源與評分流程）
- 目前全域最佳的程式碼與分數：來源是研究狀態的「全域最佳」
- 證據摘要：由 harness 把結果紀錄與完整紀錄加工而成（論文 §3.1），包含下列幾項
  - 近期嘗試
  - 依搜尋方向分組的結果
  - 各 Worker 的目前狀態：來源是研究狀態的「本地候選」
  - 近期進展
  - 任務專屬診斷（有的話）：論文只說「有的話」，未明講來源。推論：由受信任的分析程式產生（Appendix E 的 Advisor prompt 提到 trusted aggregate analyzer）
  - 摘要會把「量測後沒進步」和「實作、執行或正確性出錯而無結論」分開標示，出錯不會被當成這個方向已經沒救
- 看不到：完整時間序紀錄（harness 有存但不給）。Appendix E 的 kernel Advisor prompt 另外明列看不到被拒絕的原始程式碼、evaluator 的測試案例、隨機種子與預期值、Worker 的對話、隱藏測試的細節

**Worker 的 context（每次 trial 重建）**

- 任務規格：來源同上
- 自己的指派：來源是這個 epoch 開頭 Advisor 的輸出。指派是什麼、和任務規格差在哪裡，見【概念】指派與任務規格的差別
- 自己保留的候選程式碼：來源是研究狀態的「本地候選」
- 上一次 trial 的狀態、分數與正確性診斷：來源是 evaluator 的結果，由 harness 整理成簡短回饋
- 看不到：其他 Worker 的工作區與完整研究歷史；其他方向的證據只能透過 Advisor 的指派傳到它手上

### 2c. Advisor 怎麼分派實驗：一個 epoch 的完整流程

Advisor 是一個 LLM agent（Codex 或 Claude Code），沒有演算法在決定怎麼分派。它每個 epoch 讀 harness 給的證據，照 prompt 裡各任務的規則，用判斷寫出一份分派單。下圖是一個 epoch 的流程，圖中① 到 ⑤ 對應文末的【概念】段落。

&#91;embedded content: 一個 epoch 的完整流程 · 8 個步驟，1 個分支，1 個回圈\]

淡色底的方框是 LLM 的判斷，無底色的是 harness 的固定規則；每個 epoch 結束後，Advisor 開新 session 重來。

三條補充觀念：

- 本地最佳只進不退：Worker 的新候選要贏過自己的最佳才保留，輸了或出錯就還原成原本的最佳（SOL-ExecBench 的 Worker prompt）。
- 全域最佳進步了，沒改派的 Worker 不會自動跟上：別的方向的發現只有兩條路傳過去，一是 Advisor 在指派（PROPOSAL）裡轉述這個技巧，二是改派重設。SOL-ExecBench 的 Advisor prompt 把這兩條列為技巧跨方向傳遞的正式管道。
- 哪些是 harness 的固定規則、哪些是 Advisor 的判斷：
  - harness 規則：比對標籤、評分、保留或還原
  - Advisor 判斷：盤點瓶頸、選姿態、寫指派、決定何時換標籤

### 2d. 強制無狀態與隔離的實作

| 對象 | 機制 | 做法 | 擋住什麼 |
| --- | --- | --- | --- |
| Advisor | 每個 epoch 開新 session | 每個 epoch 開頭，harness 啟動一個全新的 Advisor 對話，裡面只有 harness 組好的 context，沒有上一輪的任何對話 | Advisor 每輪都從當下的證據重新判斷，不會順著自己先前的推論走（§3.2） |
| Worker | 每次 trial 之後清掉已存的 session | harness 把 coding agent 存下來、可供接續的對話紀錄，連同暫存檔一起刪掉，下次 trial 開新對話 | Worker 接續不了上次 trial 的對話，只能靠 harness 給的 context |
| Worker | Landlock 檔案系統限制 | Worker 以無特權程序（沒有管理員權限的一般程序）執行，再用 Linux 核心的 Landlock 規定這個程序和它開出的子程序能讀寫哪些路徑 | 進不了其他 Worker 的目錄，也讀不到 context 之外的過往實驗檔案（B.1） |
| Worker | 限制網路存取 | harness 限制 Worker 的網路連線 | 論文沒說限制到什麼程度，也沒說防的是什麼風險 |
| Worker | 只能改指定檔案 | 每個任務的 task adapter（每個任務各一份設定，寫明可改的檔案、可用資源、評分流程）指定可改的檔案，其餘全部唯讀 | 候選解只能出現在指定的檔案裡 |
| Worker | evaluator 在 Worker 環境之外執行 | harness 在 Worker 之外的地方（本機或 Modal 遠端容器）跑評分，有時間與資源上限，評分程式與邏輯受保護 | Worker 改不了自己的候選解怎麼被評分（B.1） |
| Advisor 與 Worker | 關掉 Codex 內建的多 agent 功能 | 設定層面關閉 | 沒有任何 agent 自己再開 subagent（子 agent）。論文只在 Codex 的設定裡提到，Claude Code 沒說 |

## 3. 實驗

兩個實驗細看（Table 1 的主結果、Table 4 的 ablation），其餘實驗各用一個小標題帶過。重複實驗只有 Anthropic kernel（Codex）與 Table 4 的 ablation 跑 3 次，其餘設定每個方法只跑 1 次。三個對手框架：

- EvoX：同時演化候選解與搜尋策略
- CORAL：平行的 agent 自己選實驗，每個 agent 保有一個長 session
- SwarmResearch：一個 Shepherd（協調者）協調多個 search agent，被指示不指派具體想法

### 3.1 Table 1：Anthropic kernel 主結果

- 任務：Anthropic 公開的 VLIW SIMD kernel 優化題，預算 1B token。指標 cycles 是程式的執行週期數，越低越好。
- To match tokens：一個方法第一次追平「最強對手的最終成績」所需的累積 token（單位 M = 百萬），NR 表示沒追上。
- 原 caption：「Table 1: Anthropic VLIW SIMD kernel performance and token efficiency. Cycles at 25% (250M) and 100% (1B) of the token budget, and cumulative tokens needed to first match the strongest baseline’s full-budget cycles (NR: not reached). Codex entries are mean ± std over three runs (token counts use the mean curve); Claude Code uses one run per method. Bold: best per column; underline: second best. The last row gives SLA’s relative reduction over the strongest baseline in each column.」

**Codex（每個方法 3 次，平均 ± 標準差）**

| 方法 | 250M cycles ↓ | 1B cycles ↓ | To match tokens (M) ↓ |
| --- | --- | --- | --- |
| EvoX | 1478.3 ± 112.0 | 1343.3 ± 4.0 | NR |
| CORAL | 1524.0 ± 101.7 | 1350.0 ± 134.2 | NR |
| SwarmResearch | 1501.7 ± 185.7 | 1275.7 ± 133.9 | 986.3 |
| SLA | 1149.3 ± 18.9 | 1112.0 ± 8.9 | 67.9 |
| SLA 相對最強對手的減少 | −22.3% | −12.8% | −93.1% |

**Claude Code（每個方法 1 次）**

| 方法 | 250M cycles ↓ | 1B cycles ↓ | To match tokens (M) ↓ |
| --- | --- | --- | --- |
| EvoX | 1174 | 1153 | NR |
| CORAL | 1205 | 1130 | 888.3 |
| SwarmResearch | 1648 | 1243 | NR |
| SLA | 1079 | 1039 | 138.5 |
| SLA 相對最強對手的減少 | −8.1% | −8.1% | −84.4% |

結論：

- 同預算比較：Codex 設定下，250M token 時 SLA 比當時最好的對手（EvoX，1478.3）少 22.3% cycles，跑完 1B token 比最強對手（SwarmResearch，1275.7）少 12.8%。Claude Code 設定下兩個時點都少 8.1%（250M 對 EvoX 的 1174，1B 對 CORAL 的 1130）。
- 效率比較：追平最強對手的最終成績，Codex 設定的對手是 SwarmResearch，需要 986.3M token，SLA 只要 67.9M，少 93.1%；Claude Code 設定的對手是 CORAL，需要 888.3M，SLA 只要 138.5M，少 84.4%。百分比的分母是對手的用量。
- 穩定度：Codex 設定下，SLA 的 3 次全部贏過對手的 9 次。

### 3.2 Table 4：Ablation（各拿掉一個零件）

- 做法：從 SLA 跑到 10% 或 20% 預算時存下的研究狀態出發，每個設定再跑 100M token，3 次取平均 ± 標準差。kernel 預算 1B，存檔在 100M、200M；libexpat（FrontierSWE 的一題，用組合語言重寫 XML parser，預算 700M，分數乘 100，越高越好）存檔在 70M、140M。
- 三個變體，每個仍然是無狀態，只改「各 context 裡放什麼」或「有沒有指派」：
  - 拿掉 Advisor 重建（w/o Advisor reconstruction）：Advisor 沒有 harness 整理的摘要，改成自己透過唯讀介面去讀完整紀錄
  - 拿掉 Worker 隔離（w/o Worker isolation）：Worker 看得到完整紀錄和其他 Worker 的候選解
  - 拿掉指派（w/o Advisor assignments）：Worker 拿到的是「做一次獨立嘗試」的 prompt，不是 Advisor 的指派，細節見【概念】「拿掉指派」的 ablation 是什麼意思
- 原 caption：「Table 4: Ablations from shared SLA checkpoints. In each column, every configuration resumes from the same checkpoint (header: start → end cumulative tokens) and runs for 100M additional tokens; entries are mean ± std over three continuations. Grey values give full SLA’s progress from the checkpoint; red values give each variant’s relative drop in that progress. Bold: best per column.」

| 設定 | kernel 100M→200M cycles ↓ | kernel 200M→300M cycles ↓ | libexpat 70M→170M 分數 ↑ | libexpat 140M→240M 分數 ↑ |
| --- | --- | --- | --- | --- |
| 存檔起點 | 1218 | 1197 | 16.12 | 17.69 |
| 完整 SLA | 1192.3 ± 2.5 | 1170.0 ± 14.2 | 18.78 ± 0.92 | 20.13 ± 0.20 |
| 拿掉 Advisor 重建 | 1198.3 ± 2.3（−23.3%） | 1188.7 ± 6.8（−69.3%） | 16.86 ± 0.64（−72.2%） | 19.07 ± 0.31（−43.4%） |
| 拿掉 Worker 隔離 | 1203.3 ± 7.1（−42.8%） | 1174.7 ± 4.5（−17.4%） | 16.79 ± 0.47（−74.8%） | 19.77 ± 0.12（−14.8%） |
| 拿掉指派 | 1195.0 ± 2.6（−10.5%） | 1182.3 ± 8.1（−45.6%） | 16.54 ± 0.33（−84.2%） | 18.85 ± 0.12（−52.5%） |

括號裡的百分比是該變體的進步量比完整 SLA 少的比例。分母是完整 SLA 相對存檔的進步量，四欄依序是 25.7、27.0 cycles 與 2.66、2.44 分。例：kernel 第一欄，拿掉 Worker 隔離只從 1218 降到 1203.3，進步 14.7，(25.7 − 14.7) ÷ 25.7 = 42.8%。

結論：

- 12 格（3 個變體 × 4 欄）的平均值全部比完整 SLA 差，論文據此主張三個零件都有貢獻。
- 單格的證據強度：其中兩格的差距與標準差在同一量級（kernel 200M→300M 拿掉隔離，差 4.7 cycles，完整 SLA 的標準差 14.2；kernel 100M→200M 拿掉指派，差 2.7，兩邊標準差約 2.5 到 2.6）。每格只有 3 次，單格不能當證據，12 格方向一致才是比較有力的訊號。
- 完整 1B run：只拿掉 Worker 隔離，跑完整預算得 1336 cycles，比完整 SLA 三次平均（Table 1 的 1112.0）差 224 cycles；續跑 100M 時同一個變體只差 5 到 11 cycles。論文只描述了一次完整 run，並以此主張缺乏焦點 context 的代價會隨時間放大。

### 3.3 Table 2 與 Figure 1(b)：FrontierSWE 4 題（Codex，每個方法 1 次）

- 任務與指標：FrontierSWE 是長時間軟體工程基準，論文選 4 題（libexpat → x86-64 Assembly、Git → Zig、Dart → Haskell、Lua Native Compiler），官方分數乘 100，越高越好，預算 700M token。
- 證明什麼：方法的排名會隨預算改變，短預算的評估會誤判方法。
- 25% 預算（175M token）：SLA 在 4 題都落後最強對手，落後 0.85 到 11.27 分。
- 100% 預算（700M token）：SLA 在 4 題都領先，領先 0.86 到 6.75 分，平均 4.95 分，其中 Git→Zig 只領先 0.86 分。
- 各題差距（175M → 700M，分數差）：libexpat −0.85 → +6.75，Git→Zig −3.90 → +0.86，Dart→Haskell −11.27 → +6.68，Lua −2.75 → +5.49。

### 3.4 Table 3：SOL-ExecBench 3 題（Codex，500M token，每個方法 1 次）

- 任務與指標：SOL-ExecBench 是 GPU kernel 基準，論文選三題：#1（attention 的 softmax、dropout 與 value 矩陣乘法的反向傳播）、#58（MoE 的 token 排序與前綴和）、#210（殘差加法與 RMS 正規化的融合）。SOL 分數介於 0 到 1，越接近 1 表示 kernel 越接近硬體極限（SOL 是 speed-of-light），baseline 為 0.5，硬體極限為 1.0。
- 500M token 的分數（對同題最強對手 EvoX）：#1 為 0.763 對 0.710（+7.5%），#58 為 0.862 對 0.804（+7.2%），#210 為 0.393 對 0.386（+1.8%），三題平均 +5.5%。百分比的分母是 EvoX 的分數。
- 追平最強對手最終成績所需的 token：#58 為 SLA 14.5M 對 EvoX 354.1M（少 95.9%），#210 為 208.3M 對 283.0M（少 26.4%）；#1 為 SLA 152.7M 對 EvoX 46.1M，SLA 較慢，但終點分數較高。百分比的分母是 EvoX 的用量。
- \#210 幾乎沒差：25% 到 100% 預算間沒有任何方法進步超過 0.02。論文推測原因是所有方法最好的 kernel 都用 Triton，對 warp 層級歸約的控制不如 CUDA，可能限制了上限（論文用「may」表述，屬推測）。

### 3.5 Table 3：FrontierCS Structured-LWE（Codex，每個方法 1 次）

- 任務與指標：FrontierCS 是演算法設計基準，論文選 Structured-LWE，一個密碼學題目，要從公開的結構化 learning-with-errors 實例中恢復有效的秘密向量；分數越高越好。
- 分數：200M token 時 SLA 59.5 對 SwarmResearch 58.0（高 1.5 分，+2.6%）；50M token 時 48.5 對 44.0（+10.2%）。百分比的分母是 SwarmResearch 的分數。
- 追平最強對手最終成績所需的 token：SLA 169.6M 對 SwarmResearch 197.0M，少 13.9%（分母是 SwarmResearch 的用量）。

### 3.6 Table 5：協調成本

- 設定：成本以 GPT-5.5 費率估算（每百萬 token：未快取輸入 $5、快取輸入 $0.50、輸出 $30），不含執行與評估實驗的算力。
- 協調者佔該方法整個 run 的 token：SLA 的 Advisor 在 kernel（1B）為 0.24%，libexpat（700M）為 0.51%；SwarmResearch 的 Shepherd 分別為 8.39% 與 10.70%。
- 協調者佔成本：SLA 的 Advisor 為 1.20% 與 2.29%；Shepherd 為 6.14% 與 7.35%。
- 成本占比比 token 占比高：快取輸入佔兩個方法 token 的 90% 以上，所以 token 占比會低估快取少的角色（如 Advisor）的成本。Shepherd 的 context 長，kernel run 中每次呼叫平均讀入約 99K input token，新 session 開頭約 8K。

### 3.7 Table 6：Worker 數量 W（1、3、7、15）

- 設定：W 取 1、3、7、15，預算固定（kernel 1B，FrontierSWE 每題 700M）。預設 W=3。
- 時間：W 從 1 到 15，kernel 跑完時間從 98.1 小時降到 14.8 小時（6.6 倍）；FrontierSWE 每題平均從 62.1 小時降到 8.5 小時（7.3 倍）。
- kernel 的品質：25% 預算時 W=7、W=15 分別比 W=1 差 337、174 cycles（1488、1325 對 1151），跑完整預算後四種寬度都落在 1107 到 1113 cycles。
- FrontierSWE 100% 預算的最佳 W 因題而異：Dart 為 W=3（45.2），Git→Zig 與 libexpat 為 W=7（29.0、34.5），Lua 為 W=1（97.3）。
- 預設 W=3 的位置：kernel 距最佳 5 cycles 內，FrontierSWE 各題距最佳 3.2 分內，時間比 W=1 快 2.5 到 2.7 倍。
- 論文的結論：Worker 數要依任務、token 預算與時間限制選，沒有通用的最佳寬度。

### 3.8 Figure 4：Worker 模型（同成本比較）

- 設定：Advisor 固定為 GPT-5.5、Worker 3 個，比較 Worker 用 GPT-5.5 或 GPT-5.4 mini；成本含 Advisor 與 Worker，依各模型費率（GPT-5.4 mini 每百萬 token：未快取輸入 $0.75、快取輸入 $0.075、輸出 $4.50）。
- 結果（成本 $100）：FrontierSWE Git→Zig 上，GPT-5.4 mini 的 Worker 較高（20.88 對 19.68）；Anthropic kernel 上則是 GPT-5.5 的 Worker 領先。
- 論文的解釋：便宜的模型每塊錢消耗更多 token，可能抵銷單次品質較低，這在部分任務成立、部分不成立（論文用「may」表述，屬推測）。

## 4. 值得帶走的東西

讀這篇論文得到、脫離它也成立的兩件事。

### 4.1 無狀態與隔離要由系統強制，不是在 prompt 裡請 agent 遵守

**一句話：** 想讓 agent 具備某個性質（不接續上次、看不到別人、改不了評分），要用 agent 做不到的手段去擋，不要用文字請它不要做。

**為什麼成立：** 論文把它寫成設計選擇（§3.3：statelessness and isolation are enforced rather than requested）。理由是我的推論，屬一般工程推理，不是論文的實驗結果：prompt 只是輸入的一部分，模型可能不照做，系統層級的限制則是 agent 的行為改不了的。

| 想要的性質 | 請求式（靠 agent 自己遵守，自編例子） | 強制式（論文的做法） |
| --- | --- | --- |
| 不接續上次對話 | 「請忘記上次的內容」 | 每個 epoch 開新 session；Worker 的已存 session 在 trial 之間清掉 |
| 看不到其他 Worker 的檔案 | 「不要讀別人的目錄」 | Worker 以無特權程序執行，再用 Landlock 限制可讀寫的路徑 |
| 改不了自己怎麼被評分 | 「不要動評分程式」 | evaluator 在 Worker 環境之外執行 |
| 不自己開 subagent | 「不要啟動 subagent」 | 在設定層面關掉 Codex 的內建多 agent 功能 |

Landlock 是 Linux 核心的功能，讓程序限制自己能讀寫的路徑（一般知識，不是論文內容）。各機制的完整做法見 2d 的表。

**怎麼用：** 對每個你需要的性質問一句：「agent 想違反時，做得到嗎？」做得到，就是請求式，要換成強制式。

```
# 請求式：靠 agent 自己遵守（自編例子）
prompt += "不要讀其他 Worker 的目錄"

# 強制式：agent 想讀也讀不到（自編例子）
launch(agent, user="unprivileged", fs_allow=[my_workspace, public_task_files])
```

### 4.2 彼此看不到對方的平行 agent，沒有明確分工時會挑到同一個缺口

**一句話：** 平行的 agent 如果輸入相同、又互相看不到，沒有人分派方向，它們就會各自做同一件事。

**證據：** 請看 Figure 5(a)（p.22），原 caption：「Figure 5: Trace examples of experiment selection and refinement. (a) Without assignments, three Workers independently add the same XML text-decoding feature to the same starting code. None improves its score. (b) Full SLA assigns another Worker to build on a successful change, further improving the solution. Scores are multiplied by 100, as in the main results.」論文說另外兩次重複實驗也出現同樣的情形，但也說這些案例沒有量測發生的頻率（Appendix D.3）。

**為什麼成立（我的推論）：** 三個條件同時成立：起點程式碼相同、任務規格相同、彼此看不到。沒有指派時，沒有任何東西讓三個 Worker 的選擇不同，所以各自挑到最明顯的缺口。這跟集成（ensemble）需要多樣性是同一個道理：輸入相同的獨立決策者，結論會很像。

**怎麼用：**

```
if workers 彼此看不到:
    由一個能看全局的角色，替每個 Worker 派不同的方向   # SLA 的做法
    每份指派要宣告它動到哪一類東西           # 讓重疊可以被檢查（自編例子）
```

- 論文的 kernel Advisor prompt 要求每份提案寫明它會省掉哪一類運算（論文事實）。這個欄位讓重疊可以被檢查，是我的推論，論文沒說有用它來檢查。
- 例外：集中攻同一個瓶頸時，prompt 規定各 Worker 的做法要實質不同（論文事實）。所以去重的層級是「做法」，不是「瓶頸」。

## 概念詳解

以下各段各自獨立，可以單獨閱讀。① 到 ⑤ 對應 2c 流程圖上的標記。

### 【概念】① 重置不是失憶：Advisor 每輪對話清空，為什麼還記得實驗結果

- 一句話：Advisor 每個 epoch 開新 session（對話清空），但已知的實驗結果存在 harness 的帳本裡，每次都會再交給它。
- 出處與原句：Appendix E（p.24）Anthropic Kernel Advisor Prompt 的 Research policy 最後一條，原句是「Reset means fresh reasoning from measured state, not amnesia」。它前面還有一句：用整理過的帳本，避免重複已有強烈負面證據的機制。
- 中文意思：「重置」是指對話被清空，要從量測到的狀態重新推理；但這不是失憶，帳本還在，所以不該叫人去重試已有強烈負面證據的機制。
- 帳本的內容：sanitized scalar research ledger（淨化過的純數字研究帳本），只有數字，被拒絕的原始程式碼、evaluator 的測試案例、Worker 的對話都刻意不放（p.23 的 prompt）。
- 白話：Advisor 每輪腦袋是空的，但桌上有一本實驗紀錄，它不能假裝沒看到。

### 【概念】② 姿態（分散或集中）怎麼選

- 一句話：Advisor 是 LLM agent（Codex 或 Claude Code，§3.3），沒有演算法在算要分散還是集中，它照各任務 prompt 的規則判斷。
- 兩種姿態：分散（diversify）是好幾種機制都有可能時，各 Worker 去不同方向；集中（concentrate）是有一個明顯瓶頸時，多個 Worker 各用不同做法攻同一個瓶頸。
- kernel 任務的規則（Appendix E）：先做資源盤點，把目前分數和引擎容量下限比較，找出是哪類運算造成下限；選集中要說明為什麼比分散更值得，且各做法要實質不同；整批 Worker 最多一個做小修小補，其餘必須做機制層級的改動。輸出有一欄 SEARCH POSTURE 寫明姿態（確切格式由 runner 提供，論文沒給）。
- SOL-ExecBench 任務的規則：預設分散；某方向有強烈局部訊號時才集中，之後回到分散。
- FrontierSWE 任務的規則：紀錄顯示某個 build、export 或正確性關卡主導時才集中。
- 論文沒講清楚：Advisor 實際多常選哪一種，論文沒報告，也沒有實驗比較兩種姿態；Discussion（p.11）自己說，剩下的問題是 Advisor 的決策品質。
- 實例（推論）：Appendix D.3 與 Figure 5(b)（p.22）的 full SLA 例子中，Advisor 要 Worker 2 在 Worker 1 的改進上繼續，其餘 Worker 分去 parser 的其他部分，同一輪同時有一路集中在贏家上、其餘分散。論文沒說這算哪種姿態，我的推論是姿態不是嚴格二選一。

### 【概念】③ REGIME 標籤是什麼

- 一句話：REGIME 是 Advisor 給每個 Worker 的方向標籤，一個簡短名稱，代表一類做法。
- 完整的指派 = REGIME（標籤）+ PROPOSAL（具體做法的描述，Worker 讀它來動手）。
- 標籤的格式：SOL-ExecBench 的 prompt 要求用短的 kebab-case（小寫加連字號），自編例子：`fused-reduction`。
- 標籤的作用：讓 harness 判斷 Worker 是接續還是改派。標籤不變，Worker 接著自己的進度做；換新標籤，harness 把它重設為全域最佳（見【概念】④）。
- REGISTRY 表：SOL prompt 要求 Advisor 在輸出裡列出每個方向的狀態：maturing（還在進步）、mature-WIN（成熟且勝出）、pruned（已淘汰）。
- 適用範圍：論文只在 SOL-ExecBench 的 prompt 裡把標籤和規則寫清楚。kernel prompt 只說每個 Worker 要有一個 regime，FrontierSWE prompt 只提 proposal 沒提標籤；這兩類任務怎麼判斷改派，論文沒說明（§3.2 只說 redirect）。

### 【概念】④ Worker 每個 epoch 從哪裡開始做

- 一句話：沒改派，接著自己上個 epoch 的本地最佳做；被改派，才從全域最佳重新出發。

| 情況 | Worker 的起點 |
| --- | --- |
| 下個 epoch 沒改派（SOL-ExecBench 是標籤不變） | 自己的本地最佳，包含上個 epoch 累積的進步 |
| 被改派（標籤換了） | 全域最佳，第一個成功評分的候選成為新的本地基準 |

- 依據：§3.2（p.5）：harness 保留每個 Worker 的本地進步，即使它落後全域最佳，好讓其他方向有時間成熟；只有 Advisor 改派時，Worker 才從全域最佳重來。
- SOL-ExecBench Worker prompt 寫「Same REGIME continues the lane」，意思是標籤相同就延續這條 lane（lane 是 Worker 自己的獨立工作線，有自己的工作區與本地最佳），並規定 trial 的保留規則：贏過自己 lane 的最佳才保留，輸了或出錯就還原成 lane 最佳。
- 論文沒講清楚：「沒改派」在不同任務怎麼判定，只有 SOL-ExecBench 明寫是標籤相同。kernel 與 FrontierSWE 的 prompt 沒提標籤，§3.2 只說 redirect。我的推論是兩者的機制相同，但原文沒有逐項確認。

### 【概念】⑤ 一個 epoch 內 Advisor 會不會打斷 Worker

- 一句話：不會。Advisor 只在 epoch 開頭被呼叫一次，所以一個 epoch 內不會做到一半被換標籤；改派就是下個 epoch 的分派單換了新標籤。這是我從論文結構推出來的，論文沒有一句話明講（推論）。
- 依據：
  - 每個 Advisor epoch 是一次呼叫，每個 Worker trial 也是一次呼叫（§3）。
  - SOL-ExecBench Advisor prompt 說每個 Worker 每個 epoch 有固定次數的 trial，所以一份 proposal 要大到夠做好幾次修改；Worker prompt 也說同一份指派會重複用在好幾次 trial。
  - Appendix C.2：每 epoch 1 次 trial 時續跑 21 到 34 個 epoch，5 次時只有 6 到 8 個，吻合 epoch 數 = 預算 ÷ 每輪 trial 數，沒有中途插入 Advisor 的跡象。
- 例外：預算用完。外部計數器直接停掉整個 run（B.2），最後一輪可能做不滿 3 次，但那是整個 run 結束，不是被換標籤。
- 論文沒講清楚的三點：
  - 有沒有任何中途打斷的機制：沒明講，我的推論是沒有。
  - 失敗或被丟棄的 trial 算不算那 3 次：B.1 只說這類 trial 會把 Worker 還原成原本保留的本地候選，沒說算不算次數。
  - 3 個 Worker 是否同步等到全部做完才進入下一個 epoch：沒說。

### 【概念】指派與任務規格的差別

- 指派是什麼：Advisor 針對某個 Worker 寫的一段文字：這個 epoch 要試哪一個具體的改法。它是 Advisor 的輸出，harness 原封不動放進該 Worker 的 context。
- 指派管什麼：方向，也就是做哪一類改動以及為什麼值得做。kernel 的 Advisor prompt 規定每份指派要寫三件事：它預計省掉哪一類運算、預期省多少、依賴哪個正確性不變量（correctness invariant，改了之後輸出必須保持不變的條件）。
- 指派不管什麼：實作細節，怎麼實作與怎麼修正由 Worker 在接下來幾次 trial 自己決定（p.5）。
- 一份指派會用於同一個 epoch 的好幾次 trial（預設 3 次），下個 epoch 才由 Advisor 重新指派（B.1）。
- 和本地候選的關係：指派說「往哪走」，本地候選是「目前走到哪」。

|  | 任務規格 | 指派 |
| --- | --- | --- |
| 內容 | 要解什麼問題、怎麼算分、哪些檔案可改、哪些做法禁止 | 這個 epoch 要試的一個具體方向 |
| 誰寫的 | 人類事先定好（任務 adapter 與公開任務說明） | Advisor 每個 epoch 現寫 |
| 會變嗎 | 整個 run 都不變 | 每個 epoch 重寫，每個 Worker 各不相同 |
| 誰有 | Advisor 和所有 Worker 拿到同一份 | 只有被指派的那個 Worker |

推論：「任務規格」的具體內容是我的推論。正文 p.5 只寫 task specification 這個詞，沒有逐項列出；我對照 Appendix E 的 prompt 推出（Worker prompt 裡的 Valid candidate contract 和各任務的 {task\_target}，FrontierSWE 另外讀 PUBLIC\_TASK\_INSTRUCTION.md），論文沒有逐字對應。

### 【概念】「拿掉指派」的 ablation 是什麼意思

- 一句話：Worker 仍然知道要做什麼，只是不知道這一輪往哪個方向做。

|  | 完整 SLA | 拿掉指派 |
| --- | --- | --- |
| 任務規格（整個問題的定義） | 有 | 有 |
| 自己保留的候選解與上次回饋 | 有 | 有 |
| Advisor 寫的 PROPOSAL（這一輪的具體方向） | 有 | 沒有 |
| 取而代之的是 | 無 | 一個「做一次獨立嘗試」的 prompt |

- Worker 的目標沒變：任務規格已經說了要提高哪個分數，它手上也有目前的程式碼，所以知道要把分數做上去；缺的是方向，該先做哪個功能、攻哪個瓶頸，由每個 Worker 自己從程式碼挑。
- Advisor 照常運作：它還是每個 epoch 被叫起來、寫分派單，token 也照算（B.1），只是 Worker 看不到這份分派單；論文說它仍然可以把 Worker 的候選解重設為全域最佳。
- 這個實驗在測什麼：同一個 Advisor、同一份證據都在，唯一差別是 Worker 有沒有收到明確方向。如果 Worker 自己挑也一樣好，Advisor 的分派就沒價值。
- 論文未說明：「做一次獨立嘗試」的 prompt，論文原文只寫「a prompt for an independent trial」，prompt 的實際內容沒有附。
- 結果的例子：請看 Figure 5(a)（p.22），caption 的 (a) 部分是「Without assignments, three Workers independently add the same XML text-decoding feature to the same starting code. None improves its score.」論文說另外兩次重複實驗也出現同樣的情形，但這些案例沒有量測發生的頻率（Appendix D.3）。
