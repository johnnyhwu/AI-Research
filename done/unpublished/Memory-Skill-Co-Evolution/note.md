# MSCE 論文筆記
### From Memory to Skills: Evidence-Grounded Co-Evolution Governance for Long-Horizon LLM Agents

**筆記目的**：這份筆記是為了讓半年後、甚至更久之後的我，不用回頭翻原始 PDF，也能快速、完整地重建對這篇論文的理解。內容包含論文本身的方法拆解，也包含我們討論過程中釐清的重點提問，以及論文本身沒交代清楚的留白之處。

---

## 0. 論文資訊

| 項目 | 內容 |
|---|---|
| 標題 | From Memory to Skills: Evidence-Grounded Co-Evolution Governance for Long-Horizon LLM Agents |
| 方法簡稱 | MSCE（Memory–Skill Co-Evolution） |
| 主要單位 | MemTensor、中國科學技術大學、香港理工大學、福州大學、西安交通大學 |
| 日期 | 2026 年 7 月 21 日 |
| arXiv | 2607.16621v1 [cs.CL] |
| 通訊作者 | Yang Zhang（zynolo96@outlook.com） |
| Code | https://github.com/MemTensor/MemOS |

---

## 1. 一句話定調

**這是一篇「讓 agent 從『記得』進化到『會做』」的工程化記憶治理框架論文。**

Agent 執行任務累積下來的 trajectory（軌跡），怎麼被「安全地」蒸餾成可以直接呼叫的 skill？這篇論文的核心貢獻，不是「trajectory → skill」這件事本身，而是**在兩者之間插入一層完整的治理機制**，確保只有真正有證據、有效果、夠穩定的經驗才會被晉升成正式 skill，避免像其他 baseline 一樣直接從雜訊 trajectory 硬蒸餾出脆弱、over-specific 的 skill。

---

## 2. 核心問題意識（四個挑戰）

1. **記憶只是被動參考，沒有變成能力**：現有系統把 trajectory 當 context 丟回去，agent 每次都要重新推理一遍，浪費 token（例如反覆重新 list 目錄找測試檔案）
2. **原始 trajectory 太雜，直接蒸餾會產生脆弱的 skill**：混雜失敗嘗試、瞎摸索、環境雜訊，直接蒸餾容易 overfit 到單一情境（over-specific）
3. **終端回饋 sparse 且延遲，難做 step-level 的 credit assignment**：一個任務往往只在最後給一個分數，中間哪一步才是關鍵很難判斷
4. **一個能用的 skill 需要的東西遠不只是成功步驟**：還要有觸發條件、適用邊界、驗證規則、生命週期維護

這四個挑戰分別對應到論文的四個機制：分層記憶（解①②）、跨 episode 支持度門檻（解②）、reflection-weighted value backfilling（解③）、skill 的完整結構 + 生命週期管理（解④）。

---

## 3. 整體架構總覽

**建構階段（怎麼從 trajectory 長出 skill）：**

```
原始 trajectory（雜訊多）
    ↓ 正規化、保留證據
L1 Trace（step 級別，證據層）
    ↓ 跨 episode 找重複模式（≥2 個不同 episode）
L2 Policy（候選 → 誘發，泛化過的做法）
    ↓ 通過「gain>0 + 穩定」兩關
Skill（正式可呼叫，經 deterministic verifier 驗證）
    ↓ 持續監控實際使用表現
probationary → active → archived（生命週期）
```

同時，L2 Policy 之間如果在同個 domain 累積夠多，會再抽象出：

```
多個 L2 Policy（同 domain）
    ↓ Algorithm 1：分桶 + cohort 篩選
L3 環境認知（宣告式知識：這個環境長什麼樣）
```

**使用階段（agent 執行任務時怎麼查記憶）：**

```
當前 context
   ↓
① 優先匹配 active skill（trigger relevance + η + gain 排序）
   ↓（沒匹配到 or 匹配到但失敗）
② 退回 L1 trace 檢索（精確線索 + 語意相似度，高 V 優先）
   ↓（若 agent 表現出「結構性不確定」）
③ 條件式查 L3 環境認知（提供環境參數，不覆蓋 skill 程序）
```

對應圖示：**Figure 1**（原文 caption：*"Overview of MSCE with governed memory, skill crystallization, and dual-signal value backfilling."*）——整篇論文的架構總圖，左側是 Interaction（任務產生 step trace）、中間是 Three-level Governed Memory（L1/L2/L3）、右側是 Skill Library（Eligibility check → Skill card → 驗證 → 生命週期管理）、下方是 Dual-Signal Feedback & Value Backfilling。之後想快速回憶整個架構，看這張圖最快。

---

## 4. 三層記憶結構詳解

### 4.1 L1 Trace Memory（證據層）

每個 **step**（不是 episode）存成：

```
f(1) = (s, a, o, ρ, V)
```

| 欄位 | 意義 | 備註 |
|---|---|---|
| s | 精簡過的語意狀態（state） | **不是**完整原始 context；論文只說有「截斷、去重、規則式脫敏」，**沒給具體截斷演算法**（論文留白） |
| a | 動作 | 可以是純文字回應，也可以是 tool call |
| o | 觀察結果 | 對應 tool result；純文字 step 記為 `"(assistant-only step)"` |
| ρ | self-reflection | episode 結束時**整批**處理生成（詳見 §5） |
| V | 這個 step 的價值 | 初始為空，episode 結束後透過 value backfilling 回填 |

**Episode 的定義**：一個 episode 是「回饋與更新的單位」，包含多個 step。一個 task（使用者目標）在單輪情境下等於一個 episode，多輪情境下可能包含多個 episode。

**Episode 邊界怎麼判斷**：新訊息進來時，用一個分類器（lexical cues + 必要時用 LLM tie-breaker）判斷跟前一個 episode 的關係：
- **Correction**（修正）→ 延續同一 episode
- **Follow-up**（延續同目標）→ 關閉舊 episode、開新的
- **New task**（無關新目標）→ 開新 task context

此外也提到有 timeout 機制，但論文沒給出具體時長。

**儲存設計的隱私考量**：L1 不存無限制的 raw observation，會截斷、去重、規則式脫敏；上層記憶（L2/L3）只存「證據 ID」指向 L1，不重複存原始資料。

### 4.2 L2 Policy Memory（泛化層）

**⭐ 核心結論（最值得記住的一句話）：**
> **Policy 是「一群相似 trace 背後共同模式」的泛化表徵，不是任何單一 step 的翻版。**

結構：
```
f(2) = (φ, π, κ, B, {f(1)})
```
φ=觸發條件、π=自然語言程序、κ=驗證/fallback 規則、B=適用邊界、{f(1)}=支持的 L1 證據集合（複數）。

**誕生流程：**
1. L1 trace 的 V ≥ vmin（=0.1，門檻很低，只是過濾器）才有資格被考慮
2. 用 **embedding 相似度 + 結構化特徵**（domain tag、工具類型、normalized error signature）去匹配既有 policy
3. 匹配成功 → 併入該 policy，更新它
4. 匹配失敗 → 丟進「候選池」，用一個 **deterministic pattern signature** 分組（**論文沒給出這個 signature 具體怎麼算**，合理推測跟前面的結構化特徵欄位有關，但未明講——論文留白）
5. 候選池累積到 **至少 nmin(=2) 個不同 episode** 的證據，才誘發 LLM（Πpolicy prompt）真正歸納出一個新 policy

> 為什麼要求「不同 episode」而不是單純「多筆 trace」：避免同一個長 trajectory 裡的重複雜訊被誤判成通用規律。

**具體範例（來自附錄 C, 對應 Table 5）**：
- Task A：Alpine 容器裝 `lxml` 失敗（缺 C library）→ 裝系統依賴後成功
- Task B：Debian 容器裝 `psycopg2` 失敗（缺 `pg_config`）→ 裝系統依賴後成功

兩者情境完全不同（不同 OS、不同套件），但因為抽象模式相似（容器內 pip 因缺系統函式庫而失敗），累積到 2 個不同 episode 的證據後，誘發出**一個**泛化 policy：
- φ：pip install 因缺系統函式庫而失敗
- π：解析缺什麼 → 判斷套件管理工具（apk/apt-get）→ 裝對應 -dev 套件 → retry
- B：僅限容器環境

**Table 5**（原文 caption：*"L1 traces from two distinct tasks demonstrating cross-task L2 policy induction. Task-level feedback (RA = 0.8, RB = 0.9) is backpropagated using reflection weights (α) to compute step values (V)."*）——就是這個例子的原始數據表，之後想確認確切的 α、V 數值可以回頭查這張表。

### 4.3 L2 Policy 的 Gain 計算（怎麼判斷這個 policy 有沒有用）

**公式：**
```
G(f(2)) = V_with − V_blend(without)
```
白話：**「有用到這個 policy 的 step，平均表現多好」減去「同一情境下沒用到的 step，平均表現多好」**。

**With 側（有用到 policy 的 trace）：**
- 證據數 ≥ 3：用 **softmax 加權平均**（讓表現特別好的案例權重更大）
- 證據數 < 3：退化成普通算術平均
- τV（softmax 溫度）= 0.5

**Without 側（同池子裡沒用到的 trace）：**
- 用算術平均，但加上 **shrinkage（收縮）**：
```
V_blend(without) = (|without| × mean(without) + N0 × b) / (|without| + N0)
```
N0=5（偽計數）、b=0.5（保守基準值）。

**⭐ 值得記住的巧思：為什麼要收縮？**
如果對照組（without）樣本很少，直接算平均會很不可靠、容易被單一雜訊樣本綁架，導致 gain 被誤判為異常高或異常低。**收縮的精神是：樣本數越少，越把平均值拉回中性基準 0.5；樣本數越多，越相信真實算出來的平均值。** 這是貝氏統計裡 shrinkage estimator 的經典手法，論文裡至少有兩處用到同樣的精神：這裡的 gain 計算、以及後面 skill reliability η 的公式。

**⭐ 比較池 T 的精確範圍（容易搞混的地方）：**
T 只包含「**這次觸發重算的那個 episode**」的所有 trace + 「這個 policy 原本累積的誘發證據」，**不是這個 policy 涉及過的所有歷史 episode**。這樣才能回答一個當下、同情境的問題：「在這次剛發生的任務裡，用了這個 policy 的那一步，是不是真的比同一次任務裡沒用到它的其他步驟表現更好？」

```
簡圖：
┌─────────────────────────────────────────┐
│ Episode C（本次觸發重算）                  │
│  trace1  trace2  trace3  trace4  [trace5]│ ← 這次新匹配到 policy
│  without without without without  WITH  │
├─────────────────────────────────────────┤
│ Policy 原本的誘發證據（來自過去不同 episode）│
│  Episode A-trace3 ──────────→  WITH      │
│  Episode B-trace2 ──────────→  WITH      │
└─────────────────────────────────────────┘
```

**Gain 什麼時候重算？** 每次有新證據匹配進來、reward backfilling 跑完，就 **recompute（覆蓋掉舊值）**，不是累積或平均歷史 gain。這讓 policy 的表現可以隨時間漂移，持續負 gain 會導致 policy 被淘汰。

### 4.4 L3 環境認知記憶（宣告式知識層）

**跟 L2 最關鍵的差異**：L2 講「怎麼做」（程序性），L3 講「這個環境長什麼樣」（宣告式）。L3 的 prompt 明文禁止出現任何指令性動詞（do/don't/should/use/prefer/avoid/try/install/run）。

結構：
```
f(3) = (E, I, C, {f(2)})
```
E=實體/結構事實、I=action-response 規律、C=環境限制、{f(2)}=支持的 L2 policy 集合。

**同一事實的兩種寫法對照（論文原文舉的例子）：**
| 層級 | 寫法 |
|---|---|
| L3（宣告式，該寫的） | "Alpine 容器只內建 Python 的純 Python 套件層" |
| L2（程序式，L3 禁止） | "在 Alpine 遇到 pip 失敗時，執行 apk add 再重試" |

**怎麼被觸發生成（Algorithm 1，原文標題：*"Environmental cognition abstraction"*）：**
1. 活躍的 L2 policy 依 domain key 分桶
2. 桶內數量 ≥ m(=2) 才繼續
3. **Admit**：用 cohort 的 embedding centroid 跟每個 policy 的餘弦相似度篩選（θsim=0.62），embedding 發散時 fallback 用結構化 tag 比對
4. 呼叫 LLM（Πenv prompt）：輸入 cohort + 每個 policy 帶一筆代表性證據
5. 判斷合併還是新建：跟現有 L3 的餘弦相似度 ≥ θmerge → 合併；否則新建

**Confidence 機制（⚠️ 論文留白最多的地方之一）：**
- 新證據支持 → 增加；反駁 → 減少
- **論文完全沒有給出計算公式**，只有定性描述 + LLM 輸出時給的初始 [0,1] 分數
- 低信心不會被刪除，只是排除在**預設檢索**之外（保留供稽核，未來有新支持可以重新啟用）

**上線後怎麼用：** L3 不會覆蓋 skill 的程序骨架，只提供「環境參數」去實例化 skill——例如一個「安裝依賴」skill 的程序骨架固定（解析缺什麼 → 判斷套件管理工具 → 安裝 → 重試），但具體用 `apk` 還是 `apt-get` 還是 `brew`，由 L3 判斷當前是 Alpine/Debian/macOS 決定。

**觸發時機**：只有 agent 表現出「structural uncertainty」（例如不知道測試檔案、設定檔在哪）時才會查 L3，**不是每次 skill 執行都會查**。但「怎麼偵測 structural uncertainty」以及「cognition 內部哪個 item 該被選中」，論文都**沒有給出具體演算法**——這是使用階段的一個明顯留白。

---

## 5. Reflection-Weighted Value Backfilling（把終端分數攤回每個 step）

**背景問題**：一個 episode 結束只會拿到**一個**終端分數 Rᵢ，但裡面有多個 step，要怎麼分配？

**核心公式：**
```
V(f_t) = α_t · R_i + (1 - α_t) · γ · V(f_{t+1})
```
- 最後一步直接繼承終端分數：`V(最後一步) = R_i`
- 前面步驟的價值 = 「直接用終端分數」（權重 α_t）+「繼承下一步價值、打折 γ」（權重 1-α_t）的混合
- γ = 0.9（折扣因子）

**直覺**：反思寫得越有洞察力（α 高）→ 這一步越是關鍵轉折點，值得直接跟終端結果掛鉤；反思空洞（α 低）→ 這一步的價值主要靠「後面接的步驟好不好」去補。

**⭐ 類比**：結構上很像強化學習的 **TD(λ) / eligibility trace**（用折扣把未來價值往回傳），差別在於這裡的混合權重不是固定常數 λ，而是**每個 step 動態算出來、由反思品質決定的 α**。

**手算範例（附錄 C）**：episode A 最終 R_A=0.8，倒數第二步 α=0.7：
```
V = 0.7×0.8 + (1-0.7)×0.9×0.8 = 0.56 + 0.216 = 0.776
```

**α 怎麼算：** 由獨立的 LLM prompt（Πreflexion_score，用 GPT-4o）依四個維度評分：
1. **faithfulness**（忠實度）：反思內容是否對得起實際發生的 THINKING/ACTION/TOOL_CALLS/OUTCOME
2. **causal insight**（因果洞察）：有沒有講清楚為什麼成功/失敗
3. **transferability**（可遷移性）：對未來類似任務有沒有用
4. **concreteness**（具體程度）：是否具體（指令名稱、錯誤訊息）而非空泛廢話

規則：空洞或同義反覆的反思直接給 0 分且 `usable=false`；分數 ≥0.4 且非同義反覆才 `usable=true`。**短任務內的多個 step 會批次一起丟給 LLM 評分**，讓 judge 能做相對比較。若評分機制關閉，非空反思一律給中性值 α=0.5；judge 輸出格式錯誤則不更新，沿用舊值。

**⚠️ 本質提醒**：α 不是客觀公式算出來的，是 LLM-as-judge 的啟發式評分——這跟後面的 reward quantification（Rᵢ 的計算）是同一類機制，論文自己在 Limitations 裡也承認這些治理訊號是「heuristic」而非因果推論。

---

## 6. Skill Crystallization（Policy 怎麼晉升成 Skill）

### 6.1 Skill 結構

```
k = (φ, π, κ, B, A, D, η)
```
前四項繼承自 L2 policy，新增三項：
- **A（evidence anchors）**：明確的證據錨點
- **D（decision guidance）**：`(preferences, anti-patterns)` — 建議做什麼/避免什麼
- **η（reliability）**：可信度分數（見下）

**⭐ Policy vs Skill 的角色差異**：L2 policy 是內部用來聚合證據、可能還不穩定的抽象；skill 是有標準呼叫介面、生命週期狀態、可信度估計的**部署物件**。晉升不只是格式轉換，是一個需要驗證的正式步驟。

### 6.2 兩道晉升關卡

1. **正向 gain**：`G(policy) > θG`（θG=0，門檻很低，只要有正面貢獻就過）
2. **穩定性（stability）**：最近的新證據要能吻合現有 φ/π/B，不需要大幅改寫
   - **⚠️ 論文留白**：穩定性怎麼量化、判斷門檻是什麼，論文只有定性描述（"substantial rewrite"），沒給具體演算法或對應 prompt。合理推測可能隱含在 L2 update 環節由 LLM 順帶判斷，但論文未明講。
   - **⚠️ 晉升是否需要最小證據數量**：論文**沒有**給出明確門檻（跟 L2 誕生明確要求 nmin=2 不同），只間接透過 gain 計算裡的 softmax 樣本數規則（≥3 筆才用加權平均）隱含影響。

### 6.3 生成與驗證流程

1. 支持證據分成 **positive evidence**（成功案例，歸納通用程序）與 **counter-evidence**（失敗案例，限縮邊界、產生 anti-pattern）
2. 呼叫 Πskill prompt：輸入 policy、evidence anchors A、**證據中實際出現過的工具白名單**、既有 decision-guidance 種子
3. LLM 回傳結構化草稿：步驟、參數、前置條件、範例、初始 decision guidance

**Deterministic Verifier（非 LLM，規則式檢查）**：
- Schema 完整性（名稱、前置條件、有序步驟、範例、工具清單、guidance 欄位齊全）
- **Evidence grounding**：引用的證據 ID 必須真的存在於支持證據集
- **工具白名單**：宣稱要用的工具必須來自證據中實際出現過的工具，不能發明
- 兩個「輕量覆蓋率測試」（論文未給出具體演算法，只有名稱）

**任何一項沒通過，草稿直接丟棄，不會變成可呼叫的 skill。** 這個設計是為了防止「LLM 生成幻覺配上 LLM 驗證幻覺」的循環——用規則式邏輯把關，而非再找一個 LLM 去審查。

### 6.4 Reliability η

```
η = (n_pass + 1) / (n_trial + 2)
```
**⭐ 重要釐清**：n_trial / n_pass 是 skill **正式上線、部署之後**被實際呼叫的次數統計（"invocations"），**跟晉升前累積的誘發證據數量無關**——完全是兩個不同時間軸的東西：
- 晉升前：誘發 policy 誕生、通過晉升關卡的「誕生證據」
- 晉升後：skill 上線後每次被呼叫的「服役表現」，用來動態更新 η

`+1`、`+2` 的偽計數同樣是 shrinkage 精神：呼叫次數少時，η 被拉向 0.5，避免小樣本過度自信。使用者明確正/負回饋也可調整 η；邊界違規會縮小 B。

---

## 7. Skill 生命週期管理

三個狀態：**probationary（試用）→ active（正式啟用）→ archived（封存）**

**轉換門檻（Table 6 超參數）**：
- n_prob=1（至少 1 次試用呼叫後才評估）
- θ_active_η=0.6（η 超過此值才轉正）
- θ_archive_η=0.2（η 低於此值被封存）
- δ=0.1（使用者明確回饋時 η 的調整步幅）

**⭐ probationary 跟 active 的關鍵差異**：不是「agent 看不看得到」，而是**檢索優先序**——router 檢索時只匹配 **active** 狀態的 skill trigger，probationary 的 skill 不在預設檢索候選名單裡。（但 probationary skill 具體怎麼被觸發呼叫、怎麼累積 n_trial，論文未明講機制。）

**Table 4**（原文 caption：*"Lifecycle operations for crystallized skills."*）——完整事件對照表：

| 事件 | 操作 | 效果 |
|---|---|---|
| 呼叫成功 | reinforce | η 提高 |
| 執行失敗 | repair | 修正程序或驗證規則 |
| 使用者拒絕 | shrink | 縮小適用邊界 B |
| 新反例證據 | revise | 加入 guidance 或 anti-pattern |
| 源頭 policy 被大幅改寫 | rebuild | 用全新證據重新 crystallize（不是小修小補） |
| 長期沒被用 or 低可信度 | archive | 移出預設檢索範圍（不刪除，保留稽核） |

**⚠️ 事件偵測機制的留白**：「呼叫成功/失敗」相對明確（系統執行結果）；但「使用者拒絕」這種需要語意理解的事件怎麼被偵測、「policy 大幅改寫」的穩定性判斷怎麼量化，論文都沒給出對應的 prompt 或演算法（附錄 E 列的五個 prompt 裡沒有對應這件事的）。可以確定的是：Decision guidance 的**合成**（synthesize contrastive guidance）是由 LLM 做的，Πskill prompt 也接受一個叫 `REPAIR_HINTS` 的輸入欄位佐證這件事。

---

## 8. Hierarchical Retrieval（使用階段的檢索順序）

三層優先序（詳見 §3 的流程圖）：

1. **Skill Retrieval**：優先匹配 active skill trigger，用 trigger relevance + η + gain 排序
2. **Trace/Episode Retrieval**：skill 沒匹配到 or 匹配到但失敗時的退路 → 查 L1 trace（精確線索 + 語意相似度，高 V 優先，低 V 保留當反例）；同 episode 的多筆 trace 會被打包成 episode-level rollup
3. **Environmental Cognition Retrieval**：條件式，只在 agent 表現「結構性不確定」時觸發，提供環境參數但不覆蓋 skill 程序

這個順序直接對應解決挑戰①（記憶被動）：命中 skill 就直接拿到驗證過的程序，不需要重新從一堆 trace 裡自己歸納；只有 skill 這層「沒用」才退回成本最高的 L1 檢索。

---

## 9. Reward Quantification（附帶補充，附錄 B.3）

當沒有數值環境獎勵，只有使用者文字回饋時，怎麼轉成 scalar Rᵢ ∈ [-1,1]：
```
R_i = clip(0.45·g_i + 0.30·p_i + 0.25·u_i, -1, 1)
```
g=goal achievement（是否達成目標）、p=process quality（過程效率/安全）、u=user satisfaction（使用者滿意度語氣）。三者都由一個 LLM 評估器打分。若 LLM 評估器不可用，退回極性式的 heuristic 估計。

---

## 10. 實驗結果

### 10.1 實驗設置

- **Benchmark**：EvoAgentBench（五領域：IR/Math/SE/Code/KW）為主戰場；LoCoMo 測長對話記憶一致性
- **三類 baseline**：① 純記憶型（EverOS/Memento/MemSkill，不主動蒸餾 skill）② 軌跡→skill 型（EvoSkill/OpenSpace/SkillFlow-Evolve，MSCE 真正的對手）③ Vanilla Agent（無記憶下限對照）
- **共同設定**：全部方法同一 runtime（OpenClaw v2026.5.7）、同一 backbone（GPT-5.2 主體 + GPT-4o 輔助算子）、同樣工具權限與任務順序——比較相對公平

### 10.2 主結果（Table 1）

**Table 1**（原文 caption：*"Main results on EvoAgentBench. We report Pass@1 (%) and Cost across five domains. Cost is measured in chars for Math and turns for other domains..."*）

MSCE 在五個領域全部拿到最好或並列最好的 Pass@1：
- IR: 26.15（+4.61 vs 最強對手）
- Math: 47.00（+4.00）
- SE: 53.85（**+15.39，最大提升**，但 cost 也從 37.3→40.8 turns 上升）
- Code: 61.54（與 EvoSkill 打平，但 cost 從 3.9→2.0 turns，**準確率打平、成本砍半**）
- KW: 53.45（+5.17）

**⭐ 值得記住的觀察（我們討論中發現，論文未深入分析）**：贏過 MSCE 之外表現最好的 baseline，在 IR/Math/SE 這三個領域是**純記憶型**（EverOS/Memento），只有 **Code** 領域是軌跡→skill 型（EvoSkill）表現最好。論文完全沒有分析這個分裂模式。可能的解讀（我的推論，非論文明講）：未經治理的蒸餾 skill 可能主動誤導 agent 走錯方向、比單純不蒸餾還糟，但 Code 任務判準明確（跑測試案例、二元對錯），結構化程度高，即使未治理的蒸餾也相對不容易被誤用。

### 10.3 LoCoMo 結果（Table 2）

**Table 2**（原文 caption：*"Results on LoCoMo. We report LLM-judge (GPT-4o) scores for four question types, including single-hop, multi-hop, temporal reasoning, and open-domain questions, together with the overall judge score and overall F1 score."*）

MSCE 在 single-hop（75.98）、multi-hop（47.87）、temporal（44.24）、overall（61.23）、F1（49.89）都拿最高。**但 open-domain 這項 MSCE（28.13）沒贏**，EverOS（29.17）與 Vanilla Agent（39.58，全表最高）反而更好——暗示 open-domain 問題可能更依賴模型通用知識而非檢索出來的長期記憶，記憶系統在這類問題上幫助有限甚至可能是雜訊。論文對此未深入分析。

### 10.4 Ablation Study（Table 3）★ 最值得重視的實驗

**Table 3**（原文 caption：*"Ablation results on EvoAgentBench. The top row shows the full MSCE method, while the following rows evaluate non-hierarchical and component-level ablations."*）

五個消融版本：Flat Memory（完全拿掉分層）、w/o L3、w/o Value Calibration、w/o Reflection Weighting、w/o Skill Crystallization。

**掉分幅度排序**：
```
Flat Memory（掉最多，IR -15.38 / Math -16.00 / SE -19.23，Code cost 2.0→5.3 turns）
  > w/o Skill Crystallization（掉 6.15~11.54 分，且所有領域 cost 都上升）
  > w/o Reflection Weighting
  > w/o L3 ≈ w/o Value Calibration
```

**⭐ 這個實驗告訴我們的真相**：
- MSCE 真正的核心價值是**「治理」這件事本身**，不只是「分層」這個架構——Flat Memory 掉分最兇，證明單純多存記憶、多檢索是不夠的
- **Skill Crystallization 是組件級消融中貢獻最大的**——拿掉後準確率跟效率同時變差
- **Value Calibration 在每個領域都證實必要**：拿掉後 Pass@1 全面下降、cost 全面上升，印證了「未經治理的 skill 直接注入反而拖累表現」這個核心假設——不是空話，是有消融證據支撐的

### 10.5 其他實驗（性價比較低，僅摘要）

- **Cross-domain Transfer（Figure 2）**（原文 caption：*"Cross-domain transfer results. Bars show the absolute Pass@1 improvement from intra to cross in percentage points, and the orange line shows the relative cost change."*）：6 個跨領域配對全部正提升（+2.56~+5.13 分），佐證「學到的是可遷移結構，不是死記硬背」，但沒有新機制。
- **Lifelong Evolution（Figure 3）**（原文 caption：*"Long-horizon cumulative evolution under the lifelong learning protocol. The left panel shows Pass@1 across increasing accumulated training scales, and the right panel shows cost normalized by the corresponding p0 cost of each task category."*）：累積更多經驗，Pass@1 單調上升，cost 先升後降，支持「learning by using」敘事。
- **Simulated Human Feedback（附錄 D.2, Table 7）**：驗證 §9 的 reward quantification 機制確實有用，KW/SE 提升最多（+13.79/+7.69），Math 無變化。

---

## 11. 論文的明顯留白（整理成清單，方便之後評估工程落地可行性時查）

| 留白項目 | 論文交代程度 |
|---|---|
| L1 state 怎麼截斷 | 只說「truncated」，無具體演算法 |
| L2 候選池的 deterministic pattern signature 怎麼算 | 完全沒給公式，只有名稱 |
| Policy/Skill 的「穩定性」怎麼量化 | 只有定性描述（"substantial rewrite"），無演算法或 prompt |
| Skill 晉升要不要累積最小證據數 | 沒有明確門檻（跟 L2 的 nmin=2 對比明顯） |
| L3 confidence 怎麼計算 | 完全沒給公式，只有「支持增、反駁減」的定性描述 |
| L3 檢索觸發判斷（怎麼偵測 structural uncertainty） | 只有定性描述，無演算法 |
| L3 內部哪個 item 該被選中 | 完全未提及篩選機制 |
| Deterministic verifier 的「兩個輕量覆蓋率測試」 | 只有名稱，無定義 |
| 使用者拒絕/糾正的偵測機制 | 沒有對應 prompt（附錄 E 五個 prompt 裡沒有這個） |
| **Latency 數據（重要）** | **完全沒有任何真實時間量測**，Cost 指標只是 turns/chars 代理指標；Limitations 只有一句話帶過"introduce additional latency and cost"，沒有數字佐證 |
| Baseline 之間為何互有勝負（純記憶型 vs 軌跡→skill 型） | 論文未分析（見 §10.2） |
| Open-domain 問題上記憶系統為何反而不如 Vanilla Agent | 論文未分析（見 §10.3） |

**⭐ 整體觀察**：凡是牽涉到**數字計算**的部分（gain、η、value backfilling、reward quantification），論文都給得很仔細，有明確公式；但凡是牽涉到**「怎麼從自然語言/情境判斷出一個離散事件」**的部分（穩定性、拒絕偵測、pattern signature、L3 觸發），論文普遍只給概念，沒給演算法或 prompt。這是貫穿全文的一致模式。

---

## 12. 三個最值得帶走的可遷移設計模式

即使不做 agent skill 系統，這三個 pattern 在其他「從雜訊經驗裡篩選可靠訊號」的場景也用得上：

1. **用中介治理層防止直接蒸餾的脆弱性**：原始資料 → 泛化抽象（要求跨樣本/跨來源支持）→ 通過效果驗證後才正式部署，中間永遠隔著至少一層「治理」而非一步到位
2. **用信號品質做動態的 credit assignment**：不是均勻地把最終結果分攤到每個中間步驟，而是依照「這個步驟本身的可信度/資訊量」（這裡是反思品質 α）動態決定分攤比例——概念上是 TD(λ) 的一個資料驅動版本
3. **用 shrinkage estimator 處理小樣本的可信度估計**：樣本少時把估計值拉回保守的中性基準，樣本多時信任真實統計值——這個手法在論文裡至少重複用了兩次（policy gain 的 without 側、skill reliability η），是一個簡單但好用的統計工具

---

## 13. 整體評價

- **研究貢獻**：中等偏上。核心 idea（治理式的 memory→skill 晉升機制）問題意識明確，Ablation Study 確實支撐了設計選擇的必要性，不是空話包裝。
- **工程落地價值**：目前不足。**沒有 latency 數據是最大的硬傷**——疊了五、六層 LLM prompt（reflection scoring、reward quantification、L2 induction、L3 abstraction、skill drafting、verification）的治理管線，在真實 online 系統的延遲跟 API 成本完全沒被量化。雖然 online update 是非同步設計，一定程度緩解了使用者等待的問題，但「線上學習的時效性」（新 policy/skill 能不能來得及被下一個 episode 用上）論文完全沒討論。
- **最適合學的地方**：不是照抄整個系統架構，而是 §12 列的三個可遷移設計模式，以及「用消融實驗驗證每個組件是否真的在做事」這種嚴謹態度。

---

## 14. 符號/術語快查表

| 符號 | 意義 |
|---|---|
| f(1) | L1 trace，單一 step 的記錄單位 |
| f(2) | L2 policy，泛化過的做法 |
| f(3) | L3 環境認知 |
| s, a, o, ρ | state, action, observation, self-reflection |
| V | trace 的 backfill 後價值 |
| R_i | episode 的終端回饋分數 |
| α_t | reflection weight，決定 backfill 混合比例 |
| γ | value backfilling 的折扣因子（=0.9） |
| φ, π, κ, B | policy/skill 的觸發條件、程序、驗證規則、適用邊界 |
| G | policy 的 gain（有用度指標） |
| vmin | L2 association 的最小 V 門檻（=0.1） |
| nmin | L2 induction 要求的最小不同 episode 數（=2） |
| θG | skill 晉升的 gain 門檻（=0） |
| A, D, η | skill 的 evidence anchors、decision guidance、reliability |
| n_pass, n_trial | skill 上線後的成功/總呼叫次數 |
| E, I, C | L3 的實體事實、規律、限制 |
| m | L3 abstraction 最小 policy cohort 大小（=2） |
| θsim, θmerge | L3 cohort 准入 / 合併的相似度門檻（0.62 / 未列出精確值於正文，見 Table 6） |
| c | L3 認知的 confidence（無公式，只有定性描述） |
| Πreflexion_score, Πreward, Πpolicy, Πenv, Πskill | 五個 LLM 輔助算子的 prompt 名稱 |

**Table 6**（原文 caption：*"Principal MSCE hyperparameters."*）——所有超參數的完整列表，含 γ、reward 三權重、nmin、vmin、τV、N0、b、θG、m、θsim、θedge、K、k、nprob、θ_active_η、θ_archive_η、δ、τeval。之後要查任何超參數的確切數值，直接翻這張表最快。

---

*筆記完成日期對應討論當下。若之後要深入實作，優先補完 §11 列出的留白項目，並查看論文 GitHub repo（MemTensor/MemOS）確認實際實作細節。*
