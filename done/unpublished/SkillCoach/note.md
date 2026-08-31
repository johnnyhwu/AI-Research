# SkillCoach: Self-Evolving Rubrics for Evaluating and Enhancing Agentic Skill-Use

**來源**：arXiv:2607.01874v1（JD.COM + HKUST(GZ)，2026年7月）

---

## 30 秒版本

企業級 agent 系統常把「操作手冊」包裝成可重複使用的 SKILL.md 技能文件庫。但技能一多，agent 容易選錯技能、跳過步驟、順序亂做、不做結果檢查——即使**最後答案還是對的**。這篇論文的問題意識是：只看「最終答案對不對」（verifier pass/fail）沒辦法分辨 agent 是真的學會了用技能，還是純粹運氣好蒙對。

它提出 SkillCoach：把 agent 的執行軌跡拆成四個可觀測維度（選技能、照步驟做、組合順序、結果反思）分別打分，並設計一套機制讓評分規則（rubric）能透過真實 rollout 資料自動修正演化。這套 rubric 拿來做兩件事：診斷 agent 哪裡失敗、篩選訓練資料做 SFT。

**核心結論（實驗證實）**：用這套過程分數去篩選 SFT 訓練資料，比只看「verifier 有沒有過」去篩選訓練資料效果更好——甚至後者在小模型上是負向的（把模型教壞）。

**這篇論文真正的定位**：它不是在發明一個新的訓練哲學。「過程監督比結果監督更適合拿來篩訓練資料/當 reward」這件事，在 RLHF、數學推理 process reward model 的文獻裡早就是成熟共識，這篇論文自己在 Related Work 裡也承認站在這條研究線上。它真正的貢獻，是把這個已知原則**工程化、自動化**、並且**綁定到「企業技能庫」這個具體場景**：rubric 不需要大量人工逐步標註，而是能從真實 rollout 中自己演化出來。如果你已經熟悉 process reward 這條文獻，這篇論文對你的邊際價值主要集中在兩塊：① rubric 自動演化的工程機制設計 ② 技能選擇在大規模技能庫下的失效邊界分析（見下方「背景概念」章節）。

---

## 索引：本筆記最重要的兩段（背景概念補完）

這兩段不是論文的主結論，是閱讀過程中被追問、值得獨立記住的觀念，未來最容易忘記、也最值得重讀：

1. [誰在打分？——規則 / LLM judge / 外部 verifier 的分工](#誰在打分)
2. [Validation Gate 到底怎麼運作——不是「judge of judge」](#validation-gate-怎麼運作)
3. [Degradation boundary 與 Collapse boundary 是同一套機制，不是兩種測試方式](#degradation-vs-collapse)

---

## 一、問題設定：為什麼「答案對」不等於「用對技能」

企業裡的 agent 系統常見這樣的情境：技能庫裡有很多 SKILL.md 文件，記錄著標準作業流程（SOP）、工具呼叫方式、驗證規則。隨著技能庫變大，技能之間會互相重疊（例如不同部門的相似報表流程），agent 可能：漏看該用的技能、選錯技能、跳過關鍵步驟、順序做錯、提交前沒檢查。

論文用一個具體例子說明為什麼「只看最終答案對不對」不夠（原文 **Figure 1**，caption: *"Motivating example of agentic skill-use diagnosis"*）：一個防洪任務裡，兩條軌跡都算出了正確的淹水天數：

- **Trajectory A**：讀了技能文件，照著文件規定的步驟一步步做（下載官方閾值資料 → 計算門檻表 → 檢查結果）
- **Trajectory B**：完全沒看技能文件，靠自己瞎猜資料、反覆試錯，運氣好蒙對答案

用 verifier 去看，兩條軌跡的分數**一模一樣**。但只有 A 展現出「可重複、可信賴」的技能使用行為；B 是撞對的。

這帶來兩層問題：
- **評估層面**：只看 pass/fail 完全看不出 A、B 的差異，也就看不出 agent 到底學會了什麼
- **訓練層面**：如果把所有「verifier 通過」的軌跡都當成好示範去做 SFT，會把 B 這種「亂試一通、繞過流程」的行為也一起訓練進模型——實驗結果（見第四節）證實了這個擔憂是真的會發生。

---

## 二、四個評分維度：怎麼把「過程」變成可打分的東西

論文把 agentic skill-use 定義成軌跡層級的 meta-ability，拆成四個維度，各自有獨立公式和權重：

```
┌─────────────────────┬──────────────────────────────┬──────┐
│ 維度                  │ 在測什麼                       │ 預設權重│
├─────────────────────┼──────────────────────────────┼──────┤
│ skill_selection       │ 有沒有選對 gold skill、          │ 0.40 │
│ (技能選擇)             │ 有沒有誤用 distractor 技能        │      │
├─────────────────────┼──────────────────────────────┼──────┤
│ skill_following        │ 有沒有照著技能文件規定的           │ 0.30 │
│ (步驟遵循)             │ 關鍵步驟做（不是只是提到技能名稱）    │      │
├─────────────────────┼──────────────────────────────┼──────┤
│ skill_composition      │ 多個技能/步驟之間的順序、          │ 0.20 │
│ (組合順序)             │ 中間產物有沒有正確傳遞              │      │
│                       │ （單一技能任務時此項不適用）          │      │
├─────────────────────┼──────────────────────────────┼──────┤
│ skill_reflection       │ 提交答案前有沒有明確的            │ 0.10 │
│ (結果反思)             │ 自我檢查行為（不等於 verifier 通過） │      │
└─────────────────────┴──────────────────────────────┴──────┘
```

外加 **verifier**（外部結果訊號，獨立於這四個維度之外，不計入加權）。

**設計要點**：`skill_selection` 是「閘門」——如果選錯技能，下游維度的分數會被打折，邏輯是「技能都選錯了，後面做得再仔細也沒意義」。

### 公式細節

以下四條公式都是「加權平均」的變形，其中 selection 略特殊（用 F1 兼顧漏選跟濫選），其他三項是「規定好的事有沒有做到」，用加權平均就夠了：

**① Skill Selection**（`Sb` = agent 實際選用的技能集合，`Gt` = 該任務真正需要的 gold skill 集合）
```
情況一（需要用到 gold skill 時）：
ssel = 2 * |Sb ∩ Gt| / (|Sb| + |Gt| + ε)      ← 本質是 F1 score

情況二（本來就不需要任何 skill 時）：
ssel = I[Sb = ∅]     ← agent 有沒有正確地「什麼都不選」
```

**② Skill Following**（`wk` = 步驟權重，`ck` ∈ {0, 0.5, 1} 完成程度，`mk` ∈ {0,1} 有沒有可見證據）
```
sfol = Σ_k [ wk * ck * mk ] / Σ_k wk
```
關鍵設計：`mk` 是**乘法項**——就算 agent 聲稱自己做了某步驟（ck=1），只要軌跡裡沒有對應證據（mk=0），這步直接算 0 分。這是防止 agent 靠嘴巴宣稱就拿到分數的機制。

**③ Skill Composition**（`(u,v)` = 一組先後依賴，`quv` ∈ [0,1] 是否真的先做 u 再做 v 且中間產物正確傳遞）
```
scomp = Σ_(u,v) [ βuv * quv ] / Σ_(u,v) βuv
```

**④ Skill-Grounded Reflection**（`c` = 一項預期檢查，`rc` ∈ {0, 0.5, 1} 檢查品質）
```
sref = Σ_c [ ρc * rc ] / Σ_c ρc
```

四項分數最後依權重加總成一個總分 `Smeta`，用來做訓練資料篩選，但 **verifier 永遠獨立保留**，不會被這個加總分數蓋掉（原文附錄 B 定義）。

---

## 三、誰在打分？——規則 / LLM judge / 外部 verifier 的分工 {#誰在打分}

> 這是討論過程中最值得記住的一個誤解修正點：**不是四個維度全都靠 LLM 打分**。

| 維度 | 誰來判 | 為什麼這樣設計 |
|---|---|---|
| skill_selection | **規則為主**（機械式偵測，非 LLM） | 論文原文明講「current implementation is rule-dominant for skill_selection」——用「有沒有出現讀取 SKILL.md 這種事件」來判定，避免 LLM 幻覺出「選對了」的假證據 |
| skill_following | LLM judge，但**強制要求引用具體證據**（event_index） | 判斷步驟有沒有真的做需要理解語意，但要求證據引用防止空判斷 |
| skill_composition | 同上 | 同上 |
| skill_reflection | 同上 | 同上 |
| verifier（外部結果） | **完全不是 LLM**，是 code-level 的硬性檢查器 | 讀 benchmark 產生的結果檔案，跟 LLM 判斷完全獨立 |

訓練資料篩選規則：軌跡要**同時滿足** `Smeta ≥ 0.95` **且** verifier 通過，才會被收進 SFT 訓練集。兩個條件都要達標，缺一不可。

---

## 四、自我演化的 Rubric 機制：怎麼讓評分規則自己變好

### 4.1 整體迴圈

每個任務都有自己專屬的 rubric，透過反覆迴圈演化：

```
[初始 Rubric R⁰]（從 SKILL.md、任務指令、oracle 解法、verifier 資訊建構）
        │
        ▼
  Rollout（agent 在真實環境跑出一批軌跡）
        │
        ▼
  Judge（用目前版本的 rubric 對每條軌跡打四維度分數）
        │
        ▼
  Arbitration（另一個 LLM 提出一個「局部修改建議」patch）
        │
        ▼
  Validation Gate（用沒被拿去提案的保留軌跡驗證這個 patch 有沒有變好）
        │
     接受 ──→ 版本升級，重複迴圈（最多 6 輪）
     拒絕 ──→ 保留舊版，換下一輪再試（連續拒絕 3 次提早停止）
        │
        ▼
  從「所有曾被接受過的版本」裡挑驗證分數最高的當 R^best
  （不是直接取最後一輪的版本）
```

每輪軌跡切成「校準集」（10條，給 arbitration model 看去提案修改）和「驗證集」（5條，**對 arbitration model 隱藏**，只用來檢驗 patch），類似 train/validation split，防止 rubric 對少數校準軌跡過擬合。

**實際跑起來的規模**：28 個任務總共跑了 94 輪演化，平均每個任務 3.36 輪，最少 3 輪、最多觸頂 6 輪。這個數字說明多數任務初版 rubric 品質已經不差，只需要小修小補就收斂，不需要大改特改。

**Patch 的硬性限制**：不能動 `key_steps` 本身的定義、不能改 `score_weights`、不能繞過 verifier，只能修改判定標準（criteria、evidence_requirements、score_rules 這類）——確保每次修改都是局部、可控的。

⚠️ **論文沒講清楚的地方**：這 15 條軌跡（10校準+5驗證）具體是怎麼生成的——是「同一題用不同 temperature 重跑」還是「同任務家族下不同具體實例」還是「換不同 agent backend」，論文全文沒有明確交代。Table 5 顯示每個任務家族底下有多個 instance，這暗示軌跡池可能包含不同題目實例，但這只是推論，不是論文明講的事實。

### 4.2 Validation Gate 到底怎麼運作——不是「Judge of Judge」 {#validation-gate-怎麼運作}

> 這是討論過程中另一個關鍵的觀念釐清。

**直覺上的誤解**：既然要比較「舊版 rubric」和「候選版 rubric」誰比較好，是不是要再設計一個 LLM 去當「評審中的評審」？

**實際機制**：不是。流程是「**同一套 judge 機制，套用兩個不同版本的規則，跑在同一批驗證資料上，再用可計算的指標量化差異**」——概念上更接近 A/B test，而不是疊加一層新的評審：

```
驗證軌跡 Ut（5條）
    │
    ├──→ 用「舊版 rubric」跑 Judge Prompt（LLM）→ 結構化 JSON 輸出
    │      （每個 key step 的 completed/missing、引用哪個 event_index 當證據）
    │
    └──→ 用「候選版 rubric」跑同一套 Judge Prompt（同一個 LLM）→ 同樣的結構化輸出

           ↓
    程式碼（非 LLM）對這兩份 JSON 做機械式統計比對：
    - 有幾個 key step 引用了有效的證據？
    - process 分數的方向跟 verifier 的 pass/fail 一不一致？
    - 有沒有出現「沒證據卻判 completed」這種違規？
           ↓
    算出 ∆H（hard gate 差異）、∆Q（soft objective 差異）
```

接受候選版本需要**同時滿足四個條件**（原文附錄 D）：

1. **Hard gate H 不能退步**：候選版本不能出現破壞性行為（沒證據卻給 credit、忽略 distractor、刪除關鍵步驟、繞過 verifier）——這些可以機械化偵測
2. **Soft objective Q 要改善超過閾值 ε=0.2**：Q 由證據覆蓋率、證據品質、reflection 證據紮實度、process 分數與 verifier 一致性、規則精簡度組成
3. **材料性改善（∆mat ≠ ∅）**：不能只是「judge 更有信心」，必須有實際變化（證據覆蓋率提升門檻 0.02、維度分數提升門檻 0.01 等）
4. **Patch 本身沒有結構性違規**：沒有偷改 key_steps、score_weights，或刪掉整個維度

⚠️ **論文沒講清楚的地方**：Q 的精確計算公式論文沒有給出，只列出它包含哪些子項；其中「evidence quality」「reflection grounding」這類子項究竟是純機械統計（例如數證據引用次數）算出來的，還是背後也讓 LLM 給了品質分數，論文全文沒有交代。

**與此對照、容易搞混的另一個機制**：論文 **Table 2**（caption: *"Human-gold validation of rubrics before and after self-evolution"*）裡有一個**真正的 judge-of-judge**，但那是**離線的、一次性的驗證研究**，跟上面的 validation gate 是不同的東西：拿演化完成的 R⁰ 和 R^best 兩個版本，找一個獨立的 LLM（Gemini 3.1 Pro）跟人工標註的 gold reference 比對，打出 gold-keypoint coverage（71.56 → 83.70）、usability（81.53 → 94.33）、hallucination rate（2.00 → 0.00）、filtering consistency（82.00 → 96.00）這幾項指標，證明演化後的 rubric 品質確實變好。這個實驗**不是每輪演化都會跑**，只是拿最終結果去做一次外部驗證。

---

## 五、關鍵實驗結果

### 5.1 Rubric-filtered SFT vs Outcome-only SFT（全篇最重要的證據）

原文 **Table 4**（caption: *"SFT ablation under the Gold + Distractors setting. Results are final accuracy (%)"*），在 Gold + Distractors 設定下訓練 Qwen3.5-4B / 9B：

```
                    4B    9B
Base（沒訓練）        8.0   14.0
Outcome-only SFT     6.0   18.0   ← 只挑 verifier 過的軌跡去訓練
用 R⁰ 篩選訓練        16.0  28.0
用 R^best 篩選訓練    24.0  32.0   ← 最好
```

**重點解讀**：
- Outcome-only SFT 對 4B 模型是**負向**的（8.0 → 6.0）——直接驗證了「把 verifier 過但過程亂來的軌跡當訓練示範，會教壞模型」這個核心擔憂
- R⁰（未演化的初版 rubric）篩選已經比 outcome-only 好很多，R^best 又比 R⁰ 更好——證明 rubric 演化本身有增量價值

**Ablation（拿掉某個維度篩選的影響）**：拿掉 key-step following 傷害最大（4B: 24→10，9B: 32→16），拿掉 composition order 也有明顯傷害，拿掉 reflection 傷害較小但仍可見。意思是四個維度裡，**「有沒有照步驟做」是篩選訓練資料時信號量最強的一項**。

⚠️ **樣本規模提醒**：測試集只有 10 個任務家族、50 個 instance，論文沒有報告這些百分點差異的置信區間，引用時要保留一點保守態度。

### 5.2 Distractor-boundary 分析（工程參考價值最高的部分）

測的是：當技能庫規模變大、干擾項變多，模型還能不能選對技能。原文 **Figure 4**（caption: *"Distractor-boundary analysis under growing and semantically overlapping skill libraries"*），拆成兩個邊界：

**測試機制**（degradation 和 collapse 用的是**同一套機制**，只是技能庫規模不同——不是「一次塞給模型」vs「搜尋」兩種不同測法）：模型透過一個**類似瀏覽器的多輪互動介面**（`list` 列出候選、`search` 搜尋、`read` 讀取內容、`final` 輸出選定技能或放棄）去逐步探索技能庫，不是把所有候選技能一次塞進 context window。這個設計刻意把「技能選擇」這個能力單獨抽出來測，不跟工具呼叫失敗、環境錯誤混在一起。

⚠️ 論文沒講清楚 `search` 動作底層是關鍵字搜尋還是語意/embedding 檢索，如果是後者，代表模型在過程中其實有拿到輔助工具幫忙縮小範圍，這對「模型自己判斷力有多強」的解讀會打些折扣（這是我的推論，非論文明講）。

```
技能庫規模：  小 ──────────────────────────────→ 大
              1  5  20  50  500  5k  20k  50k
              │                    │              │
         （高分穩定）        degradation        collapse
                          （F1開始下滑        （80%樣本選不到
                           且回不去）           任何 gold skill）
```

- **Degradation boundary**（F1 第一次掉超過 0.10 且回不去）：Gemini 3.1 Pro 約 45-46 個干擾項、GPT-5.5 約 55-56 個、Opus 4.7 撐到 194-195 個
- **Collapse boundary**（80% 樣本選不到任何 gold skill）：DeepSeek V4 Flash 在 6.4k-6.5k 個干擾項崩潰、Kimi K2.6 在 20k-21.25k、Gemini 3.1 Pro 在 35k-35.5k；**GPT-5.5 和 Opus 4.7 測到 5 萬個干擾項都沒崩潰**

**另一個實務上更有用的發現**（同樣在 Figure 4，子圖 (b)，caption 對應 *"Distractor-type sensitivity"*）：干擾項的**語意相似度比數量更致命**。固定 50 個干擾項，比較三種類型：

```
              隨機無關      高相似度
GPT-5.5：      0.84    →    0.59
Opus 4.7：     0.87    →    0.71
DeepSeek V4：  0.70    →    0.46
```

最危險的干擾項不是明顯無關的東西，而是「長得很像但實際用不上」的技能（例如同類報表流程的不同版本、不同部門的相似合規檢查腳本）。

---

## 六、值得帶走的東西（按耐久度排序）

### 這篇論文本身的貢獻（時效性較短，脫離這篇論文本身不一定成立）
- SkillCoach 這套 rubric 自動演化的**具體工程機制**（validation gate 的四個接受條件、校準/驗證集切分方式）
- 在他們選定的 18+10 個任務家族上，rubric-filtered SFT 優於 outcome-only SFT 的具體數字（Table 4）——樣本量小，數字本身不必照單全收，但方向性的結論有參考價值

### 脫離這篇論文也成立的通用觀念（這才是真正耐久的收穫）

1. **「process supervision 優於 outcome supervision」這個原則本身不是這篇論文的發明**，在 RLHF / 數學推理 process reward model 的文獻裡早已是成熟共識。這篇論文的價值在於把這個原則**自動化、工程化**，並綁定到「企業技能庫」這個具體場景——讀論文時要能分辨「這是這篇獨創的」還是「這是站在已知結論上的應用」。

2. **驗證證據的乘法設計是一個可遷移的 pattern**：判斷「某件事有沒有完成」時，「宣稱完成」和「有可見證據支持完成」應該用**乘法**而不是加法結合（`ck * mk`）——只要有一項是零，分數就歸零。這防止任何靠自我宣稱就拿高分的評分機制，不限於 agent 技能評估，任何用 LLM 當 judge 的場景都適用。

3. **技能/工具庫的規模化風險，語意相似度比數量更致命**：如果你在設計技能檢索/路由系統，測試干擾項的抗性時，不能只測「數量夠不夠多」，更要測「有沒有語意上高度相似但功能不同的近鄰選項」——這類近鄰選項才是實際部署時最容易造成誤觸發、誤選的來源。

4. **Degradation 與 Collapse 是兩種不同的失效訊號，處理方式不同**：性能開始下滑（degradation）代表應該優化檢索/排序/候選過濾機制；性能幾乎完全失效（collapse）代表技能庫規模已經超出模型可靠判斷的範圍，光靠優化排序無法解決，需要換架構（例如先用檢索大幅縮小候選集，而不是讓模型直接面對整個庫）。

5. **驗證新舊版本評分規則好壞時，不一定需要疊加一層新的評審機制**：可以用「同一套 judge，跑在同一批資料上、套用不同版本的規則，再用可計算的機械指標比較輸出差異」，這比另外設計一個 judge-of-judge 更輕量、更可控（但論文裡也保留了一個真正的 judge-of-judge 機制當作離線的、獨立的最終驗證手段——兩者用途不同，不衝突）。
