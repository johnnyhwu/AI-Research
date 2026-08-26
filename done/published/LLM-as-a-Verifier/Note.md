# LLM-as-a-Verifier: A General-Purpose Verification Framework

> arXiv 2607.05391v2 · Stanford / UC Berkeley / NVIDIA Research
> 官方資源：llm-as-a-verifier.com

---

## 0. 三十秒版本

**這篇在做什麼**：把「LLM 當評分員」這件事，從「讀模型輸出的那個分數數字」改成「讀模型輸出分數時的機率分佈，算期望值」。一個解碼層面的改動，換來連續分數而非離散整數。

**為什麼有用**：離散分數會讓大量候選解「打平手」（Terminal-Bench 上平手率 27%），無法排序；連續分數的平手率是 0%。

**核心價值判斷**：
- **工程價值 > 研究新穎性**
- 期望值解碼、重複取樣、準則拆解都不是新發明；貢獻在於系統化打包 + 扎實 ablation + 一個真正新的排名演算法（PPT）
- 最強的實證是 RoboRewardBench：同一個模型，只改解碼方式，準確率從 70.8% → 87.4%
- 主實驗的「SOTA」宣稱有 harness 混雜問題，真正的 verifier 貢獻是 +2~3 個百分點

---

## Part 1｜問題定義

### 1.1 核心挑戰：離散評分把資訊壓扁了

傳統 LM judge 的形式化定義（論文 Section 2）：

```
R_LM(x, τ) ∈ {1, ..., G}     ← 分數就是「生成出來的那個 token」
```

模型在分數 token 的位置，內部其實產生了一個**完整的機率分佈**。但標準做法只取機率最高的那一個（argmax），其餘全部丟棄。

**關鍵認知**：資訊不是「模型沒產生」，而是**解碼策略把它丟掉的**。模型內部對「這條軌跡有多好」的信念一直是連續的，被壓扁的位置在 argmax 那一步。

**證據**：
- Terminal-Bench 上，粗粒度評分造成 **27%** 的比較結果是平手（Section 3.1）
- 更具體的案例見 Part 3 的 query-optimize

### 1.2 次要挑戰：訓練式 reward model 換領域會失靈

過去做法是訓練專用的 reward model：ORM、PRM、generative verifier，機器人領域則有 RoboReward-8B（約 4.5 萬 episode）、Robometer-4B（約 100 萬筆比較）。論文主張這些被訓練資料綁死、跨域泛化不佳。

> ⚠️ **論文的弱點**：這只是 Section 1 的一句話背景假設，**沒有提供任何跨域失效的實驗數據**。

### 1.3 為什麼這件事值得解決：Oracle 的巨大落差

**Figure 5**（caption: *"Oracle Pass@K reaches 98.9% on Terminal-Bench V2"*）

如果存在一個完美的 oracle verifier，光靠重複抽樣候選解、每次都挑中對的那條，Terminal-Bench V2 的解出率可以達到 **98.9%**。而實際的 Pass@1 只有 83.1%。

**這張圖的功能要正確理解**：它**不是**第三個獨立的挑戰，而是「挑戰 1.1 值得解決」的量化證據。Section 3.1 的行文順序是：Fig. 5 → 「要拿到這段潛力需要夠準的 verifier」→ 「但標準 LM judge 不夠細緻」→ 繞回挑戰 1.1。

```
Pass@1  83.1% ─────────── 落差 ~16pp ─────────── Oracle 98.9%
                    這段全靠 verifier 去兌現
```

### 1.4 Related work 定位上的模糊處

- 論文把 MT-Bench [4] 和 V1 [5] 並列成「standard LM judges」，但 V1 是相對新、本身就含 self-verification 的方法。**全文沒有解釋 V1 怎麼運作**，只在 Table 9 拿來當基準
- Generative Verifiers [6] 在概念上跟本篇很接近（都把 reward modeling 拉到 token 層次），卻被歸進「訓練資料受限」那一類，**沒有說明兩者差在哪**

---

## Part 2｜方法（本篇重點）

### 2.1 Judge vs Verifier 的定義區分

論文在 Section 3.2 開頭做了字典式的區分：
- **Judge**：形成整體意見、給出一個決定（像老師打總分）
- **Verifier**：確認真偽與正確性，需要更細緻的評估（像審計，逐項核對）

> ⚠️ **這是斷言（asserted），不是推導（derived）**。論文並沒有論證「verifier 的角色定義 → 所以必須用機率分佈期望值」。這段的實際功能是**修辭鋪墊**，用來合理化緊接著要推出的三個 scaling 維度，不是技術論證。

### 2.2 Scoring Prompt 的設計

```
You are an expert [domain] reviewer. You will see a
task description and two trajectories.

Evaluation Criteria: [domain specific criteria]
Task: {task prompt}
Trajectory A: {A}   Trajectory B: {B}

Carefully analyze each trajectory, then provide your
final scores:
<score_A> INTEGER_1_TO_20 </score_A>
<score_B> INTEGER_1_TO_20 </score_B>

Rating Rules: Rate correctness on a 1–20 scale
(1 = incorrect, 10 = borderline, 20 = correct)
```

三個設計要點：

1. **一次 prompt 塞兩個候選解**，對照著評，不是各自單獨評分
2. **`<score_A>` / `<score_B>` 標籤是機制關鍵**：真正要的不是輸出的文字，而是該 token 位置上整個 vocabulary 的機率分佈
3. **1–20 分制只給三個錨點**（1/10/20），中間值如何判斷論文沒說，靠模型自行內插

#### ❗ 為什麼 prompt 裡沒有 ground truth？

這是**刻意的 reference-free 設計**。verifier 只拿到「任務描述 + 軌跡內容」，必須自己從 log、工具呼叫結果、輸出格式等證據判斷對錯，不是拿去跟標準答案比對。

佐證：
- Section 4.3 的三個子準則（Specification / Output / Errors）全都是「拿軌跡對照任務要求」
- query-optimize 案例中，verifier 是**看出行為本身違反任務隱含限制**，而非比對答案

Fig. 4 / Fig. 7 caption 提到的 "ground-truth successful solution" 是**研究者事後評估 verifier 準不準**用的標籤，永遠不會進入 verifier 的 prompt。

#### ❗ 為什麼要兩條軌跡一起放？

Eq. 3.2 數學上只需要兩個獨立算出的純量相減，理論上可以分兩次 prompt 各自評分。但論文明講是**同一個 prompt 一次拿到兩個分數**。

> ⚠️ **論文完全沒有解釋原因**。合理的猜測是「相對比較比絕對評分校準更穩」，或「PPT 本來就需要成對比較，一次呼叫拿兩個分數更省」——但這些都不是論文的論述。

#### ❗ 一個字面上的矛盾

Prompt 裡寫的是 `INTEGER_1_TO_20`（數字），但緊接的註解卻說：*"We use a letter-based scale instead of digits to enable logprob extraction for granularity scaling."*（用字母而非數字，以利抽取 logprob）。**兩處對不上，論文沒有澄清。**

可能的解釋是 tokenization：兩位數在 tokenizer 裡常被切成兩個 token，改用單一字母（A=1…T=20）才能確保每個分數恰好一個 token。但論文沒有這樣說明。

---

### 2.3 核心公式 Eq. 3.1

```
R(x,τ) = (1/CK) · Σ_c Σ_k Σ_g  p_θ(v_g | x,c,τ) · φ(v_g)
                    C   K   G
```

| 符號 | 意義 |
|---|---|
| `x` | 任務描述 |
| `τ` | 被評分的軌跡 |
| `c` / `C` | 第 c 個評分準則 / 準則總數（主實驗 C=3） |
| `k` / `K` | 第 k 次重複評估 / 重複次數（主實驗 K=8） |
| `v_g` / `G` | 第 g 個分數 token / 取用的分數 token 數（主實驗 G=20） |
| `p_θ(v_g \| x,c,τ)` | 模型在該位置給 `v_g` 的機率 |
| `φ(v_g)` | 把分數 token 對應回實際數值（代表 3 分的 token → 3.0） |

#### 三層結構

```
【最內層 Σ_g】granularity
  一次 LLM 呼叫 → 分數 token 位置的機率分佈
  → G 個候選分數做機率加權 → 得 1 個期望值

【中層 Σ_k】repetition
  同一準則重複 K 次 → 得 K 個期望值 → 加總

【外層 Σ_c】criteria
  每個準則各自跑完中層 → 全部加總

【最後】÷ (C×K)
```

**注意**：分母沒有除以 G，因為最內層是機率加權（Σ_g p_θ = 1），本身已是平均。

**總 LLM 呼叫次數 = C × K**（主實驗每條軌跡 24 次）。**G 不影響呼叫次數。**

#### 數字實算（最內層，G=5 為例）

| v_g | φ(v_g) | p_θ(v_g) | 乘積 |
|---|---|---|---|
| v_1 | 1 | 0.02 | 0.02 |
| v_2 | 2 | 0.05 | 0.10 |
| v_3 | 3 | 0.13 | 0.39 |
| v_4 | 4 | 0.35 | 1.40 |
| v_5 | 5 | 0.45 | 2.25 |
| | | **合計** | **4.16** |

- 離散 judge（argmax）→ **5**
- 本篇 verifier（期望值）→ **4.16**

另一條軌跡若分佈是 p(v_5)=0.52、p(v_4)=0.30…，argmax 一樣是 5（**平手**），但期望值會是 4.3 之類的不同數字（**不平手**）。這就是平手率歸零的機制來源。

> ⚠️ 論文**從未公布任何一次評分的實際機率分佈數值**，上表數字為示意。

> ⚠️ **公式的瑕疵**：被加總項 `p_θ(v_g | x, c, τ)` 裡有 c 卻**沒有 k**。既然 Σ_k 在對 k 加總，被加總的東西理應隨 k 變化，否則等於把同一個數字加 K 次再除以 K。Section 4.2 內文寫的是 `R^(k)(x,τ)`（有標 k）才是對的，Eq. 3.1 本身寫得不嚴謹。

> ⚠️ **標號不一致**：這條公式編號 Eq. 3.1，但 Section 4.3 和 Fig. 2 都改稱它為「Eq. 1」。

#### 正規化

```
R ← (R − φ_min) / (φ_max − φ_min)     壓到 [0,1]
```

上例：(4.16 − 1) / (5 − 1) = **0.79**

**❗ 為什麼需要正規化？**（論文沒有解釋理由，以下是機制上的推敲）

正規化不改變單次比較的排序（線性單調變換），真正影響的是**下一步 Bradley–Terry 的 sigmoid 飽和**：

| 情境 | 差值 | σ(差值) |
|---|---|---|
| 1–20 原始量表，兩條差 8 分 | 8.0 | 0.9997 |
| 正規化後同樣差距 | 0.42 | 0.60 |

沒有正規化的話，sigmoid 會飽和，「好一點」和「好很多」都被壓成 1.0——**等於把剛剛辛苦保留下來的細緻度又丟掉**。

具體例子（量表 1–20）：

```
                沒正規化          有正規化
τ1 (19分) vs τ5 (5分)  → 0.999999      → 0.676
τ2 (14分) vs τ6 (4分)  → 0.999955      → 0.629
                       差距 0.00004     差距 0.047
                     「都是完勝」    「τ1 明顯更強」
```

這在 PPT 裡才真正出問題：PPT 是把多場比較的機率**累加**成 w_i 再取 argmax。一旦飽和，w_i/c_i 就幾乎只反映「你有沒有碰到弱對手」，而不是「你到底多強」。

---

### 2.4 Eq. 3.2：Bradley–Terry 轉成偏好機率

```
P(τi ≻ τj | x) = 1 / ( 1 + exp( −( R(x,τi) − R(x,τj) ) ) )
```

就是 sigmoid 套在分數差上。

**數字實算**：R(τi)=0.79、R(τj)=0.62 → 差值 0.17 → exp(−0.17)=0.8437 → **P = 0.542**（忠實反映「差不多但略勝」）。

#### ❗ Bradley–Terry 的正確理解

**O(N²) 不是 Bradley–Terry 造成的，是「循環賽這個比較排程」造成的。** 兩者是不同層次：

```
比較排程（要比哪些配對）      ← O(N²) 出在這裡
       ↓ 產生比較結果
Bradley–Terry（結果 → 機率）  ← 只是一個數學模型
```

BT 在統計學的原始用法是**從不完整的勝負紀錄反推潛在實力**（如運動排名），本身不要求比幾場。

**本篇的用法跟經典 BT 是反過來的**：

| | 經典 BT | 本篇 |
|---|---|---|
| 已知 | 勝負紀錄 | 分數 R(x,τ) |
| 求 | 潛在實力值 | 偏好機率 P(τi ≻ τj) |
| 方向 | 觀測 → 反推 | 實力 → 正推 |

論文直接把 R 當成 latent strength，**完全跳過了 BT 最麻煩的參數估計**。所以 PPT 要省的不是 BT 的計算成本（sigmoid 幾乎免費），而是**取得每個 R 所需的 LLM 呼叫成本**（每對 C×K = 24 次）。

**為什麼不直接比大小？** 那只會得到 0/1，資訊又被壓扁。轉成機率能保留「贏多少」，而 PPT 累加的正是機率而非勝負。

---

### 2.5 三個 Scaling 維度

**Figure 4**（caption: *"Verification Scaling. We find that verification accuracy consistently improves as we scale across multiple dimensions: (1) the granularity of score tokens, (2) the number of repeated evaluations, and (3) the decomposition of evaluation criteria. Verification accuracy is measured as the pairwise accuracy of the verifier in assigning a higher score to the ground-truth successful solution than to failed solutions for the same task on Terminal-Bench V2."*）

#### (A) Score Token Granularity（G）— 對付「解析度不足」

| G | 1 | 2 | 4 | 8 | 16 | 20 |
|---|---|---|---|---|---|---|
| 準確率 | 73.1% | 73.3% | 75.1% | 75.9% | 77.2% | 77.5% |

**反直覺之處**：擴大量表**並沒有給 verifier 任何新資訊**。論文的說法是，它給了 decoder 一個更細的空間去投射模型內部本來就有的信念——原本會被四捨五入到同一格的相近信念，現在落到不同的連續值上。

> ❗ **G 到底要不要重跑 LLM？論文自相矛盾，沒有澄清。**
>
> **讀法一（不用重跑）**：Section 1 說 "scaling the number of extracted token logits"；Section 4 說 Gemini 2.5 Flash "allows us to extract up to 20 top logprobs per scoring token"——聽起來 G 只是「事後從 API 回傳的候選清單取幾個」。
>
> **讀法二（要重跑）**：Section 3.2 定義 `V_score = {v_1,...,v_G}` 是分數等級的 token 集合；Table 2 把 G=5 標為 "the expectation over the same 1–5 scale"，1–5 和 1–20 是兩個不同的 prompt。
>
> **影響**：如果是讀法二，granularity 就**不是免費的**，成本評估要重算。

**SNR 分析**（Eq. 4.1）：

```
SNR(G) = E[s_c − s_i] / sqrt( Var(s_c − s_i) )
         ↑ 訊號：平均贏多少   ↑ 雜訊：贏得多不穩定
```

**Table 1**（caption: *"Signal-to-noise ratio (SNR). (Left) The SNR measures how reliably the verifier separates correct (s_c) from incorrect (s_i) trajectories (Eq. 4.1). (Right) As the number of scoring tokens G increases, the SNR grows, indicating better-calibrated score separation."*）

| G | 1 | 4 | 16 | 20 |
|---|---|---|---|---|
| SNR (k=16) | 0.775 | 0.786 | 0.797 | 0.799 |

這個式子與統計的 **effect size**（Cohen's d）同形式：平均差距 ÷ 標準差，標準化後才能跨情境比較。

**SNR 在論述中的定位**：它不是解釋 granularity 的**作用機制**（那是「更細的投射空間」在做的事），而是把「分得更開」和「最終更準」連起來的**橋樑指標**。

> ⚠️ 但這座橋是斷言出來的：論文只說「準確率是 SNR 的單調函數」，**沒給函數形式**，也沒解釋 SNR 僅漲 0.024（約 3%）為何能對應準確率漲 4.4pp。Table 1 四個裸數字、**無誤差範圍**，論述強度不足。

#### (B) Repeated Evaluation（K）— 對付「單次評估的隨機偏差」

```
(1/K) · Σ_k R^(k)(x,τ)      ← Monte Carlo estimator
```

| 性質 | 效果 |
|---|---|
| 變異數 | 以 O(1/K) 縮小 |
| **偏誤** | **完全不變** |

**關鍵區分**：平均只能消除隨機誤差。若 verifier 對某類軌跡有系統性誤判（每次都往同方向錯），跑一百次也還是錯。論文自己承認 K 變大時報酬遞減，因為困難樣本上的偏誤是**相關的（correlated biases）**。

**類比**：等同統計上「增加樣本數縮小標準誤」——但若儀器本身有系統偏差（秤永遠多 2 公斤），量再多次也修不了。

**兩者分工**：

```
Granularity  → 讓每一個估計值本身更銳利
Repetition   → 把 granularity 消不掉的雜訊平均掉
```

| K | 1 | 2 | 4 | 8 | 16 |
|---|---|---|---|---|---|
| 準確率 | 74.7% | 76.1% | 77.1% | 77.3% | 77.5% |

#### (C) Criteria Decomposition（C）— 對付「評分標準本身不合理」

前兩個維度都預設 rubric 是好的。但在長時序 agent 任務裡，「這條軌跡正確嗎？」把多個邏輯上獨立的因素混在一起，verifier 往往只抓住 **prompt 裡最顯眼的那個因素**。

論文對 code agent 的三個子準則：

```
Specification → 有沒有滿足任務的所有要求？   → 檢查完整性
Output        → 最終輸出格式是否符合預期？   → 檢查結果
Errors        → log/工具輸出有無失敗訊號？   → 檢查證據
```

| 準則 | 準確率 |
|---|---|
| Specification 單獨 | 75.2% |
| Errors 單獨 | 76.0% |
| Output 單獨 | 76.4% |
| **三者 ensemble** | **78.3%** |

**類比**：這就是 ML 的 **ensemble**——多個各有不同偏誤的弱分類器，只要錯誤不完全相關，平均起來就優於單一最強者。

> ⚠️ **這一節的四個問題**：
> 1. **三個準則怎麼來的，論文沒說**。沒有交代選擇過程，沒有「試過 4 個、5 個」的 ablation。論文自己在 Appendix A 承認未來應改為學習或動態生成
> 2. **C 沒有 scaling 曲線**。G 和 K 都有完整曲線，C 只有四根柱子。**沒有 C=2 的資料，也不知道 C=5、C=10 會如何**——嚴格說 C 根本沒被證明是可 scaling 的「軸」，只證明了「3 個比 1 個好」。但論文從摘要就把它跟另外兩個並列
> 3. **Fig. 4 右圖誤差棒重疊明顯**，1.9pp 的改善未做顯著性檢定，也沒說明誤差棒代表什麼
> 4. **跨領域準則完全沒交代**。這三個明說是 "for code-agent trajectories"，但機器人和醫療實驗也宣稱用同一組。「輸出格式是否符合預期」對一段機器手臂影片是什麼意思？論文從未給出

---

### 2.6 Probabilistic Pivot Tournament（PPT）

**這是全篇唯一算得上演算法新貢獻的部分**，也是工程價值最集中的地方。

**要解決的問題**：verifier 一次只能比兩條，但任務是「從 N 條選最好」。完整循環賽是 O(N²)：

```
N = 20  →  C(20,2) = 190 對  →  190 × 24 = 4,560 次 LLM 呼叫
```

**核心想法**：每條候選只跟一小群 pivot 比，成本降到 O(Nk)。但**真正的設計重點不是「用 pivot 省錢」（這很直觀），而是「怎麼用一個便宜的前置步驟找出值得當 pivot 的候選」**。

**Figure 6**（caption: *"Probabilistic Pivot Tournament. A five-stage pipeline for selecting the best of N candidates under a constrained verification budget. (1) Candidates: the pool {τ1,...,τN} to be ranked. (2) Ring pass: a random Hamiltonian cycle scores the N adjacent pairs so every candidate appears once in the "A" slot and once in "B", canceling the model's positional bias. (3) Pivot selection: candidates are ranked by their ring-pass scores w(i), and the top-k candidates form the pivot set P. (4) Pivot tournament: every non-pivot–vs–pivot and pivot–vs–pivot pair is scored via Eq. 3.2, concentrating the budget on uncertain top candidates and cutting cost from O(N²) to O(Nk). (5) Selection: comparisons are aggregated into win mass wi and count ci, and the candidate with the highest normalized wi/ci is returned."*）

> ⚠️ Fig. 6 說五階段，Section 3.2 正文說三步驟——差別只在正文把「候選生成」和「最終選出」併入，實質相同。

```
① Candidates    N 條候選
       ↓
② Ring pass     隨機環狀比較 N 場 → 粗略排名 + 消位置偏誤
       ↓
③ Pivot select  取前 k 名為 pivot 集合 P
       ↓
④ Pivot rounds  非pivot vs pivot + pivot 彼此互比
       ↓
⑤ Selection     累積 w_i / c_i，取最高者
```

#### 步驟 1：Ring pass

把 N 條候選**隨機排成一個環**，只比較環上相鄰的 N 對。

```
      τ4 ── τ1
     ╱          ╲
   τ2            τ5
     ╲          ╱
      τ6 ── τ3

比較：(τ4,τ1)(τ1,τ5)(τ5,τ3)(τ3,τ6)(τ6,τ2)(τ2,τ4)
共 6 對 = N 對，而非 C(6,2)=15 對
```

**同時達成兩件事**：

**(a) 便宜取得粗略排名** — 只花 N 場就能大致看出誰強誰弱。

**(b) 消除位置偏誤** — LLM 對 prompt 中「Trajectory A」「Trajectory B」兩個位置常有系統性偏好（已知問題，論文引 [58,59]）。環狀結構讓每條候選**恰好當一次 A、當一次 B**，偏好在期望值上互相抵消。

**類比**：等同實驗設計的**平衡設計（counterbalancing）**——讓每個條件在每個位置出現相同次數，順序效應就會在整體平均中抵銷。

> **關於 Hamiltonian cycle 這個詞**：這是圖論術語（每個節點恰好經過一次並回到起點），因「判斷任意圖是否存在 Hamiltonian cycle」是 NP-complete 而有名。**但這篇完全沒碰到那個難點**——這裡是完全圖（任兩條都可比較），隨便打亂順序就是合法的環。Algorithm 1 第 5 行的偽代碼寫的其實就是 `Sample random permutation γ`。用詞偏向華麗，實質就是「隨機排列成環」。

> ⚠️ 「在期望值上抵消」只在**偏誤是加性常數**時嚴格成立。若偏誤與內容有關（如「只在兩條差不多時才偏好 A」），環狀結構不保證抵消。論文沒討論這個前提，也**沒有「有 ring pass vs 無 ring pass」的對照實驗**。

#### 步驟 2：Pivot selection

每場比較兩邊都更新（Algorithm 1 第 10 行）：

```
p = σ(R_i − R_j)
w_i += p        c_i += 1      ← w_i 是 win mass
w_j += (1 − p)  c_j += 1      ← 兩者相加恰為 1
```

環狀結構讓跑完後每條的 c_i 都是 **2**。然後按 **w_i/c_i 排序取前 k 名**當 pivot——沒有額外規則，純粹 top-k。

**為什麼挑表現好的當 pivot？** 目標是選出最好的那條，需要細分的是頂端誰最好，不是墊底誰比較不爛。若 pivot 挑到明顯很差的候選，所有比較都得到「大家都比它好」這種無鑑別力的結果。

**類比**：如同 quickselect 的選 pivot 思路——不需完全排序，只要找最大者，資源就該集中在可能是答案的那一區。

> 🔴 **重要疑慮（論文完全沒分析）**：pivot 是根據 ring pass 的**僅僅兩場比較**選出的，樣本量極小。**如果某條真正最好的候選在 ring pass 中運氣不好、兩場都碰到強對手，它的 w_i/c_i 就會偏低，可能直接落榜、進不了 pivot 集合。** 論文沒有分析這個「好候選被誤篩掉」的機率。

#### 步驟 3：Pivot rounds + 最終選出

比兩類配對：非 pivot vs 每個 pivot（(N−k)×k 對）、pivot 彼此互比（C(k,2) 對）。後者是必要的，因為最後還要在 pivot 之間分高下。

**總比較次數**：

```
N + k(N−k) + C(k,2)

N=20, k=5 →  20 + 75 + 10 = 105 對
             對照循環賽 190 對，省約 45%
```

**最終選出**：`i* = argmax_i  w_i / c_i`

**為什麼除以 c_i？** pivot 參與的場次遠多於非 pivot（pivot 跟所有人比，非 pivot 只跟 k 個比）。只看 w_i 的話，pivot 光靠場次多就會累積出較大數字。除以 c_i 換算成「平均每場贏多少」才公平。

#### Table 9：預算 vs 準確率

**Table 9**（caption: *"Probabilistic Pivot Tournament (PPT) scales with the number of pivots, achieving higher accuracy as k increases while maintaining a low verification budget on Terminal-Bench V2."*）
（N=20 候選、89 題、Terminus-2 harness）

| 方法 | 查詢配對數 | 準確率 |
|---|---|---|
| pass@1 | — | 52.64% |
| V1 (1N) | 1,400 | 64.64% |
| V1 (3N) | 4,200 | 65.62% |
| V1 (5N) | 7,000 | 65.85% |
| V1 (7N) | 9,800 | 65.53% |
| PPT k=1 | 2,570 | 65.83% |
| PPT k=3 | 4,723 | 66.17% |
| PPT k=5 | 6,609 | 66.27% |
| PPT k=7 | 8,242 | 66.67% |
| PPT k=9 | 9,630 | 67.13% |
| Full Round-Robin | 13,111 | 67.42% |

**讀法**：
- k 愈大愈準但報酬遞減（k=1→9 只漲 1.3pp，預算多近 4 倍）
- k=9 已逼近完整循環賽（67.13% vs 67.42%），預算省 27%
- V1 在 5N 後不升反降，PPT 則單調上升

> ⚠️ **三個保留**：
> 1. **論文沒給選 k 的方法論**，只說「k 愈大愈好」——但那樣就退化回循環賽了
> 2. **省下的幅度沒有想像中大**：k=9 相對循環賽只省 27%。O(N²)→O(Nk) 的漸進優勢要 N 很大才明顯，N=20 還不到那個區間
> 3. **這張表的 N=20 是特別策展的**。主實驗（Section 5）的 N 只有 3~5，C(5,2)=10 對，PPT 幾乎省不了什麼——**所以主實驗那些 SOTA 數字裡，PPT 的貢獻其實很有限**

---

## Part 3｜實驗

### 3.1 統一協定

四個 benchmark 用完全相同的流程與設定：

```
① 生成策略 π_θ 對每題產生 N 條候選
② verifier 用 PPT 兩兩評分
③ 選出正規化分數最高者提交
```

- **G = 20、K = 8、C = 3**
- **Training-free**：不訓練任何東西
- **Plug-and-play**：四個 benchmark 用同一框架，無任何領域 fine-tuning

第二點是最重要的實務主張——若成立，代表可直接套到自己的領域，不需準備訓練資料。

### 3.2 Table 3：主結果（讀法是重點）

**Table 3**（caption: *"Per-benchmark performance and gains from verification. Baseline accuracies (left) are obtained under a fixed agent harness. On the same candidate pools, we report Pass@1, the oracle Pass@N upper bound, and the accuracy achieved by LLM-as-a-Verifier (right). Our method consistently improves over Pass@1 and recovers a large portion of the oracle headroom, achieving state-of-the-art performance on each."*）

| Benchmark | Baseline #1 | #2 | #3 | Pass@1 | Oracle | Ours |
|---|---|---|---|---|---|---|
| Terminal-Bench V2 | GPT-5.5 (84.7%) | Opus 4.7 (80.2%) | G3.1 Pro (80.2%) | 83.1% | 92.1% | 86.5% |
| SWE-Bench Verified | Opus 4.5 (76.8%) | G3 Flash (75.8%) | M2.5 (75.8%) | 76.1% | 84.4% | 78.2% |
| MedAgentBench | Opus 4.8 (70.2%) | G3.5 Flash (66.3%) | GPT-5.5 (65.1%) | 70.2% | 75.0% | 73.3% |

**❗ 這張表必須分兩半讀：**

```
┌─── 左半：其他模型成績 ───┐  ┌─── 右半：同一候選池 ───┐
│  不同 harness            │  │  Pass@1 → Oracle → Ours│
│  不同抽樣設定            │  │  完全可控的對照        │
│  ← 蘋果比橘子            │  │  ← 這才是 verifier 功勞│
└──────────────────────────┘  └────────────────────────┘
```

**右半才是誠實的證據**（同一批候選、同一生成器，唯一變因是「怎麼挑」）：

| Benchmark | Pass@1 → Ours | verifier 真正貢獻 | Oracle 落差 | 兌現比例 |
|---|---|---|---|---|
| Terminal-Bench V2 | 83.1% → 86.5% | **+3.4pp** | 9.0pp | 38% |
| SWE-Bench Verified | 76.1% → 78.2% | **+2.1pp** | 8.3pp | 25% |
| MedAgentBench | 70.2% → 73.3% | **+3.1pp** | 4.8pp | 65% |

**回頭對照動機**：Fig. 5 的 oracle 上限 98.9% 聽起來潛力巨大，但實際只兌現了 **25%~65%**。

> ⚠️ **三個問題**：
> 1. **「SOTA」宣稱混雜 harness 差異**。86.5% 是 GPT-5.5 + Capy harness + N=5 抽樣 + verifier；84.7% 是 GPT-5.5 + NexAU-AHE harness。三個變因不同，把差距全歸給 verifier 不成立。**乾淨的比較是 83.1% → 86.5%**
> 2. **RoboRewardBench 整列消失**。caption 說涵蓋四個 benchmark，表格只有三列（RoboRewardBench 因衡量 preference accuracy 而移至 Table 4，但 caption 未說明）
> 3. **SWE-Bench 的候選池是異質的**：N=3 從三個不同模型各抽一條，Pass@1 是三模型平均。verifier 的任務變成「跨模型家族挑最好」——這其實是更有價值的應用場景（**模型路由**），但也讓它與其他列不可直接比較

### 3.3 RoboRewardBench：本篇最強的結果

**Table 4**（caption: *"Preference accuracy on RoboRewardBench. LLM-as-a-Verifier outperforms trained robotics reward models."*）

| 方法 | 準確率 |
|---|---|
| **LLM-as-a-Verifier (ours)** | **87.4%** |
| RoboReward-8B（訓練過，~4.5萬 episode） | 81.4% |
| Robometer-4B（訓練過，~100萬比較） | 78.8% |
| TOPReward | 74.7% |
| LLM-as-a-Judge（同一 VLM，離散） | 70.8% |

**為什麼這比 Table 3 更有說服力**：

1. **同一個模型的乾淨對照**：87.4% vs 70.8% 是**同一個 Qwen 3.6 35B**，唯一差別是離散 argmax vs 連續期望值。**16.6pp 的差距是全篇最大、也最能歸因給方法本身的數字**，沒有 harness 混雜
2. **直接驗證「挑戰 1.2」**：零訓練框架打贏兩個專門訓練的機器人 reward model
3. **跨模態**：輸入從文字換成多幀影片，方法完全不用改

**Table 5** 的附帶結果：把 RoboReward-8B 的輸出改用連續公式解碼，與人類標註的 MAE 從 **1.11 降到 0.72**——代表這套解碼方式**可以直接加在既有 reward model 上**。

> ⚠️ **論文沒有解釋為什麼專門訓練的機器人 reward model 會在自己的領域輸掉。** Section 5.3 只列數字，沒有任何分析。

> ⚠️ **利益關係**：RoboRewardBench 是共同作者 Chelsea Finn 也掛名的 RoboReward 論文 [11] 提出的，被比較的 RoboReward-8B 正是那篇的模型。論文自己沒有揭露這層關係。

### 3.4 進度追蹤：VOC

**核心觀察**：連續分數不只能挑最好的，還能反映「agent 做到哪了」。

**Eq. 6.1**：
```
VOC = rank-correlation( argsort(s_t1,...,s_tK), (t1,...,tK) )
```

把「步驟時間順序」與「verifier 對該步驟**前綴**的分數」算 Spearman 等級相關。分數完美隨步驟遞增 → VOC → 1。

**類比**：等同 RL 的 **value function**——V(s) 估「從此狀態出發的預期回報」，在往目標推進的軌跡上應隨接近目標而上升。論文引 Ma et al. [22] 正是此脈絡。

**Figure 8**（caption: *"We observe a strong correlation between the chronological progression of code generation steps and the scores from LLM-as-a-Verifier. The example task above requires the agent to run MNIST inference..."*）

```
成功軌跡：Read model.py → Install g++ → Install CPU-only torch
          → Update hidden_dim → DONE          分數持續上升 → ~1.0
失敗軌跡：不必要地裝 torchvision → 磁碟空間耗盡 → 編譯錯誤
                                               分數一路偏低
```

**Table 6**（caption: *"Value-Order Correlation by trajectory outcome on Terminal-Bench V2. Mean Spearman rank correlation between step index and verifier progress score, computed over 500 randomly sampled trajectories from Terminal-Bench V2..."*）

| 軌跡結果 | Spearman VOC |
|---|---|
| 成功 | 0.848 ± 0.012 |
| 失敗 | 0.769 ± 0.016 |
| **落差** | **+0.079** |

**Table 7**（機器人，500 條 RoboRewardBench 軌跡）

| 方法 | VOC |
|---|---|
| **LLM-as-a-Verifier (Qwen 3.6 35B, K=5, G=20)** | **0.966** |
| RoboReward-8B | 0.877 |
| Robometer-4B | 0.780 |
| TOPReward | 0.565 |

> 🔴 **論文在此講得過頭**：論文主張 verifier 在停滯或走向失敗的軌跡上分數**大致持平**，因此同一個分數可兼作進度量測與早期預警。**但 Table 6 不支持這個說法**——失敗軌跡的 VOC 是 **0.769**，是相當高的正相關，代表**失敗軌跡的分數也在隨時間穩定上升**，離「持平」（VOC≈0）差得很遠。
>
> ```
> 論文的敘事          Table 6 實際數字
> 成功：上升 ↗        成功：0.848 ↗
> 失敗：持平 →        失敗：0.769 ↗（幾乎一樣在升）
>                     落差：僅 0.079
> ```
>
> Fig. 8 很有說服力，但那是**單一任務的單一案例**（pytorch-model-cli）；Table 6 是 500 條軌跡的統計。論文選擇用前者當敘事主軸，卻沒討論後者為何落差這麼小。**用 0.079 的落差做執行中即時預警，鑑別力很弱。**

### 3.5 TurboAgent（工程產物）

給 Claude Code 及 OpenAI-API 相容客戶端的擴充。以**推論時代理層（proxy）**形式夾在客戶端與 LLM 供應商之間，兩邊都不用改。每個請求平行送出 N 條候選，用 PPT 選最好的回傳；另提供網頁介面即時顯示 verifier 分數與進度。

> ⚠️ 論文對 TurboAgent **沒有任何量化評估**——無延遲數字、無成本分析、無使用者研究。屬概念驗證性質。

---

## Part 4｜案例研究：query-optimize（最能建立直覺的例子）

來自 Terminal-Bench V2，完整內容在 Appendix B.4。

**任務**：給定 SQLite 資料庫和一段未優化的 SQL 查詢，寫出效能更好、**輸出結果完全相同**的版本。

**兩條軌跡的差別**（都由 Claude Opus 4.5 在 OpenHands harness 產生）：

```
✅ 正確：等原始查詢在正規資料庫上跑完（等了 5分03秒）
        → 直接 diff 比對 → 通過

❌ 失敗：嘗試跑原始查詢，兩次都超時中斷（60秒、5分02秒）
        → 把資料庫複製到 /tmp
        → 在複製品上加索引，讓原始查詢跑得動
        → 拿「有索引副本上的原查詢」對比「無索引正規庫上的優化查詢」
        → 刪掉所有驗證產物
```

**失敗的關鍵**：它在**兩個不同的物理存取路徑**上比較結果。加索引後 ORDER BY 遇相同鍵值的排序可能不同，在 LIMIT 500 邊界上就可能切出不一樣的資料。所以它從未真正驗證等價性——但它自己回報「內部 diff 檢查通過」。

**verifier 有看出來嗎？有。** Appendix B.4 引用的 Gemini 2.5 Flash 推理過程明確指出：agent 修改了資料庫來取得參考輸出，違反了任務的隱含限制，因此並未正確驗證等價性。

**那問題出在哪？** verifier 抓到了，卻用**帶保留、程度性的措辭**表達（如「稍微乾淨一些」「略為直接一點」），講得像是無關緊要。**模型內部有正確判斷，但這個判斷在 argmax 時被壓扁了。**

**Table 2**（caption: *"Judges vs. Verifiers on query-optimize. Over 100 repeated evaluations, we count how often the correct trajectory is scored higher than (s_c>s_i), tied with (s_c=s_i), or lower than (s_c<s_i) the incorrect one..."*）

| 方法 | s_c > s_i ✓ | 平手 | s_c < s_i ✗ |
|---|---|---|---|
| Judge（離散, G=5） | 12/100 | **88/100** | 0/100 |
| Verifier（連續, G=5） | 69/100 | 0/100 | 31/100 |
| Verifier（連續, G=20） | **77/100** | 0/100 | 23/100 |

**對照設計很乾淨**：
- 第 1→2 列：同一 1–5 量表，**只換解碼方式**（argmax → 期望值）。88 次平手歸零，正確排序 12 → 69
- 第 2→3 列：同為期望值，**只換量表**（1–5 → 1–20）。正確排序 69 → 77

> ⚠️ **一個論文沒討論的 trade-off**：注意最右欄——離散 judge 的**排錯次數是 0/100**，它從不把錯的排在對的前面，只是不表態。連續 verifier 消除平手的代價是**被迫每次都表態，其中二三成表錯了**。
>
> 用「平手算半分」計分（即 Fig. 7 左圖標示的 "½-tie / Mann-Whitney"）：Judge = 12 + 88×0.5 = **56**；Verifier G=5 = **69**；G=20 = **77**。verifier 確實仍勝出，結論站得住腳。
>
> 但在「平手就交給人審」的下游流程中，judge 的行為反而更安全。論文沒有提這一層。

**Figure 7**（caption: *"Verifier (continuous) vs. Judge (discrete) on Terminal-Bench V2 across k ∈ {1, 4, 16} repeated evaluations. Left: Pairwise verification accuracy... Right: Tie rate. The judge produces ties in 26.7% of comparisons at k=1 due to coarse discrete scoring, decreasing to 5.5% at k=16 as averaging breaks ties. In contrast, the verifier yields zero ties."*）

| K | Judge 準確率 | Verifier 準確率 | Judge 平手率 | Verifier 平手率 |
|---|---|---|---|---|
| 1 | 71.8% | 74.7% | 26.7% | 0.0% |
| 4 | 74.4% | 77.1% | 11.7% | 0.0% |
| 16 | 74.7% | 77.5% | 5.5% | 0.0% |

**論文想說的話**：看對角線——**verifier 只跑 1 次（74.7%）就等於 judge 跑 16 次（74.7%）**。judge 靠重複評估的改善主要機制是**用平均打破平手**（26.7% → 5.5%），而非真的提升判斷力。

**類比**：judge 跑 16 次破平手，像用重複測量彌補一把刻度太粗的尺；verifier 則是直接換一把刻度細的尺。前者能改善，但上限受制於尺本身。

> ⚠️ **「16 倍運算」的對比有點誇大**：Judge 與 Verifier 在每個 K 下的差距都穩定在 2.8~2.9pp。那個對比成立的前提是只在乎「追平 74.7%」這個特定門檻。更實質的差別是**天花板不同**——judge 在 K=16 已飽和（74.4→74.7），verifier 仍在 77.5%。

---

## Part 5｜可帶走的東西

### 立刻能用、成本最低

**把現有 LLM-as-judge 的 argmax 換成讀 top-k logprobs 算期望值。**

- 這是全篇最高投資報酬率的一步
- 二元/離散判斷 → 連續分數，直接獲得排序能力與信心度
- **前提**：需確認 G 屬於「讀法一」（同一次呼叫）才是零成本；若屬「讀法二」則要重跑

### 次一步

**Criteria decomposition（C）**。輕量、可直接套進任何 prompt-based judge。但子準則要自行設計——論文的 Specification/Output/Errors 是為 reference-free 的 terminal 任務設計的，不見得適用其他情境，而論文也提供不了設計方法論。

**Repeated evaluation（K）**。概念最簡單，但成本是線性增加。記住它**只降變異數、不降偏誤**。

### 成本的真實樣貌

```
每條軌跡的 LLM 呼叫次數 = C × K
主實驗設定 C=3, K=8  →  每條軌跡 24 次
```

若再乘上 PPT 的比較對數，總量會很可觀。論文從未討論延遲與成本，這是套用前必須自己算清楚的。

### 套用在「有 ground truth」情境的注意事項

Eq. 3.1 的形式是 `R(x, c, τ)`——**本來就是單條評分**，成對比較是外加的（Eq. 3.2 + PPT），只在「從 N 條選最好」時才需要。若情境是「這一條對不對」，可以只用 Eq. 3.1，把 ground truth 放進 prompt。

- **理論上會更好校準**（判斷任務比 reference-free 簡單）
- **但論文從未驗證過這個用法**——所有實驗都是「選最好」或「兩兩比較」，沒有任何「單條對照 ground truth 判對錯」的實驗。**不能假設 73.1%→77.5% 那條曲線會重現，必須自己跑 ablation**
- 改成連續分數後，會被迫**提前決定「多少分算對」的閾值**

### 兩個最該記住的實證

1. **Table 4 的 87.4% vs 70.8%**：同一個模型、只改解碼方式、16.6pp 差距——這是全篇最乾淨的證據
2. **Table 5 的 MAE 1.11 → 0.72**：這套解碼方式**可以直接加在既有的 reward model 上**，不是非得從頭換掉

---

*（本筆記不涵蓋論文第 7 節「Dense Reward for Reinforcement Learning」。）*
