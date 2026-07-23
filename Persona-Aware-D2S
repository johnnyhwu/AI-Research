# 論文筆記：Persona-Aware-D2S

> **論文標題**：Presentations *by the Humans* and *For the Humans*: Harnessing LLMs for Generating Persona-Aware Slides from Documents
> **作者**：Ishani Mondal, Shwetha Somasundaram, Anandhavelu Natarajan, Aparna Garimella, Sambaran Bandyopadhyay, Jordan Boyd-Graber
> **單位**：University of Maryland, Adobe Research
> **發表**：EACL 2024 (Long Paper), pp. 2664–2684

---

## 0. 一句話總結

這篇論文提出「end-user specification-aware document-to-slides generation」任務——讓同一篇論文可以依照「受眾是不是專家」「簡報要長還是短」，生成四種不同版本的投影片大綱與內容。方法上用 SFT + 輕量版 preference fine-tuning（借用 Decision Transformer 的 reward-conditioning 技巧）訓練 LLM，但**產出僅止於文字大綱與內容，不含排版/視覺設計**，且訓練資料規模極小（80 筆），架構上需要為每種 persona 配置獨立訓練模型，泛化性與 scalability 都存在明顯疑慮。

---

## 1. 核心挑戰（Challenges）

論文在 §1 與 §7 (Related Work) 中定義的問題，可整理成以下 5 點。每點都附上「過去方法怎麼處理」「為什麼處理不好」，並標示原文出處。

| # | 挑戰 | 意義 | 過去方法 | 為什麼不好 |
|---|---|---|---|---|
| 1 | **單一輸出，無法因應不同受眾** | 同一篇論文給專家 vs 給業務主管看，理想內容完全不同（術語密度、細節深度） | Doc2PPT (Fu et al., 2021)、D2S (Sun et al., 2021) | 架構上是 document → 單一投影片的固定映射，完全沒有「受眾條件」這個輸入變數，無法擴充 |
| 2 | **無法因應時長限制** | 一小時技術報告 vs 五分鐘 overview，需要的投影片張數、資訊密度不同 | 同上 | 同挑戰1，duration 也沒被當作條件輸入 |
| 3 | **訓練目標與人類多元偏好不對齊** | 若只用「最大化跟單一 gold reference 的相似度（如 ROUGE）」訓練，模型學到的是逼近某個標註者的寫法，不是理解「不同受眾需要不同東西」 | 過去工作 mostly aligned with fine-tuning based on a single gold standard (maximizing ROUGE) | Single-gold-standard 的 MLE 訓練假設「只有一種正確答案」，跟「一對多」的 persona 問題本質衝突 |
| 4 | **抽取式方法內容不連貫** | 純抽取只能「複製貼上」原文句子，無法摘要、改寫、跨句整合，讀起來生硬 | Heuristic-based (Masum et al. 2005; Shibata & Kurohashi 2005 等)、ML-based extractive (Hu & Wan 2013; Li et al. 2021 等) | Heuristic 方法依賴 handcrafted features，泛化性差；ML extractive 方法「rely on extractive methods to fetch sentences from document as slide content」，沒有摘要能力 |
| 5 | **缺乏可訓練/評測的 benchmark 資料集** | 要做 persona-aware 生成，需要「同一篇論文對應多種 persona 版本投影片」的平行資料，此前不存在 | — | Prior research had predominantly addressed preparing technical conference slides, neglecting diverse presentation types, audiences, and durations |

**挑戰之間的依賴關係**：挑戰5（無資料）是前提 → 有了資料才能定義挑戰1+2的條件輸入 → 條件生成模型的訓練需要處理挑戰3（單一 reference 不夠用）→ 挑戰4則是獨立於 persona、但同樣需要解決的內容品質問題。

---

## 2. 方法拆解

### 2.0 問題形式化（符號系統）

| 符號 | 意義 |
|---|---|
| D | 整份文件（論文） |
| SE | D 的 sections（章節） |
| F | 文件中所有 multimodal content（圖表集合） |
| Fq = {Iq, Capq} | 第 q 個圖表，含圖片 Iq 與 caption Capq（**圖片本身不被理解，只用文字 caption 代表**） |
| C | Document content（論文正文內容） |
| H | Heading（論文標題） |
| A | Abstract（論文摘要） |
| B ∈ {e, ne} | 受眾背景：expert / non-expert |
| L ∈ {l, s} | 簡報長度：long / short |
| IN = {C, B, L} | 模型輸入 tuple |
| O | 最終投影片輸出 |
| t = {t1, ..., tj} | 投影片標題序列（outline） |
| Su | 從文件篩選出的候選內容片段（句子 + caption） |

**整體目標函數**：

```
p(O | C, B, L)
```

**（我的推論，非論文明寫）** 為了讓這個聯合機率可訓練，pipeline 實際上做了三段式分解：

```
p(O | C, B, L)  ≈  p(t | IN)          ← Stage 1：Outline Generation
                 × p(Su | t, IN)      ← Stage 2：Content Extraction
                 × p(O | Su, t, IN)   ← Stage 3：Summarization + Alignment
```

> ⚠️ **原文 notation 瑕疵**：§3.1 把 Outline Generation 的目標寫成 `P(t | IN)`，但 §3.2 描述 Content Extraction 時公式仍誤寫成 `P(t | IN)`，應該是 `P(Su | IN)`。讀原文公式時需注意，此為論文寫作疏漏。

---

### 2.1 Stage 1：Persona-aware Slide Outline Generation（§3.1）

**目標**：給定論文內容 + persona 條件，生成投影片標題序列 t。

#### 2.1a Supervised Fine-Tuning (SFT-F)（§3.1.1）

- 用 cross-entropy loss，最小化生成標題 T′ 與 ground-truth 標題 T 之間的差距
- **關鍵設計**：訓練 **4 個獨立模型**，對應 4 種 persona 配置：
  `π_SFT(B=ne,L=l)`、`π_SFT(B=ne,L=s)`、`π_SFT(B=e,L=l)`、`π_SFT(B=e,L=s)`
  （而非訓練單一模型、把 B, L 當作 prompt 條件）
- **訓練資料規模**：train split 只有 20 篇論文 × 4 configs = **80 筆訓練樣本**，fine-tune GPT-3.5-turbo（3 epochs, lr=0.2, batch size 256）

#### 2.1b Preference Fine-Tuning (P-F)（§3.1.2）

處理挑戰3（單一 gold standard 不夠用）。流程分三步：

**Step 1｜收集人類偏好資料**
- 用 4 個 π_SFT，各自以不同 temperature / top-K / top-p 生成 5 組候選 topic set
- 3 位專家對 Expert 的兩配置（E-L vs E-S）做 pairwise ranking，3 位非專家對 Non-expert 的兩配置做同樣的事
- 評分準則：comprehensibility to target audience、length-based satisfaction
- 只保留「多數決有共識」的樣本，無共識則丟棄

**Step 2｜訓練 Reward Model**（Bradley-Terry loss，詳見第3節背景知識）

```
loss = -E_{x~train}[ log(sigmoid(s_w - s_r)) ]
```
- s_w = chosen response 的 reward 分數；s_r = rejected response 的 reward 分數
- 最終得到 4 個 reward model：RM-C-E, RM-L-E（專家的 comprehensibility/length）、RM-C-NE, RM-L-NE（非專家）
- **⚠️ 我的觀察**：reward model 用的是 **distilbert-base-cased**（一個很小的 encoder，約 66M 參數），capacity 是否足以判斷 "comprehensibility" 這種語意複雜的東西，論文沒有做消融驗證

**Step 3｜Final Preference Fine-tune（借用 Decision Transformer 的技巧，詳見第3節）**
- 從 train set 抽 prompt，用 π_SFT 生成 5 組 topic-set
- 用 reward model 對每組打分，得到 (prompt, reward) → topic-set 的訓練 pair
- 用這個 pair 再次 fine-tune LLM（本質上仍是監督學習，只是多了 reward 當 condition）
- Inference 時：直接餵入「最大 reward 值」當條件，生成對應高分的 topic 序列

> ⚠️ **論文交代不清楚的細節**：(1) "maximum reward" 的具體數值怎麼決定（訓練資料觀察值？手動設定常數？）未說明；(2) reward 是合併成單一純量、還是兩個分數都塞進 prompt，實作細節缺失。

---

### 2.2 Stage 2：Persona-aware Content Extraction（§3.2）

**目標**：給定 t，為每個標題找出相關的句子/圖表 caption Su。

#### 2.2a Topic-wise High Recall Section Filter（非 LLM 檢索，省成本）

**為什麼需要**：直接把整篇論文丟給 LLM 挑句子，成本高，且原文提到目的是把 prompt 壓進 GPT-3.5-turbo 的 4096 token 限制內。

流程：
1. 每個投影片標題 ti 跟論文 section headings SH 做 **fuzzy match**（字面相似度），取相似度 > 門檻值 th 的 top-k
2. Fallback：若無 section 通過門檻，改用 **Sentence-BERT**（Reimers & Gurevych, 2019）算語意相似度，挑最像的 section
3. 選定 section 後，該 section 所有句子+caption 全部串接成 Su

> ⚠️ **我的觀察**：th 門檻值是在只有 **5 篇論文**的 dev split 上調出來的，樣本數極小，換到不同 domain（不同章節命名習慣）大概率需要重新調整；此外整套機制**高度依賴論文有標準化 section 結構**，對非結構化文件（會議記錄、PRD等）會失效。

#### 2.2b Persona-aware Content Extraction from Candidates

完全重用 Stage 1 的 SFT-F + P-F 機制（同樣的 cross-entropy loss、同樣的 Bradley-Terry reward model、同樣的 Decision-Transformer-style fine-tune），只是輸入輸出換成「(t, Su) → Su_relevant」。訓練出的 policy 記為 `π_SFT-CE`。

#### 檢索成本 vs Recall 的權衡（Table 10）

| 策略 | 平均 GPT calls | Recall |
|---|---|---|
| 論文提出的輕量 filter | ~1 次 | 78.89% |
| 中等範圍候選 | ~5.3 次 | 81.34% |
| 幾乎用整篇論文 | ~8.2 次 | 100% |

論文宣稱「省 GPT calls 8 倍」，代價是**永久漏掉約 21% 真正相關的內容**（這一步篩選不可逆，後續 Stage 沒機會再看到被漏掉的句子）。

> ⚠️ Table 10 的 precision 欄位數字（6.73, 5.93, 5.88）在 PDF 抽取後數值不合常理（precision 通常應為 0–1 或 0–100% 比例），懷疑是原文表格 OCR/欄位錯位問題，引用時建議回頭核對原始 PDF。Recall 數字看起來合理。

---

### 2.3 Stage 3：Summarization and Logical Alignment（§3.3）

**目標**：把 Stage 2 抽出的零散句子片段，整理成連貫、可讀的最終投影片 O。

**機制**：兩步驟 prompting，**完全沒有 fine-tuning**（跟 Stage 1、2 形成明顯對比）：
1. 把 Su 的內容摘要成 bullet points
2. 把摘要後的 bullet points 丟給 LLM，要求「在同一標題內部」或「跨標題之間」重新排列，讓內容更適合聽眾消化

> ⚠️ **方法論斷層（我的觀察，論文未解釋）**：Stage 1、2 都投入大量心力做 SFT+P-F，但對最終使用者體驗影響最大的 Stage 3 卻完全沒有客製化訓練，資源分配不對稱，論文沒有說明原因。

**Hallucination 處理方式**：沒有做自動化事實查核，而是讓標註者對「Relevance of content」評分，用這個分數間接代表有沒有幻覺（§6.1.3）。

> ⚠️ **我的批評**：用「相關性」proxy「幻覺」不夠嚴謹——內容可以「跟標題高度相關」但同時「捏造論文沒講過的細節」，這種類型的幻覺測不出來。

**消融實驗結果（Figure 5，10篇論文，Step 2 抽取版 vs Step 3 摘要+重排版對照）**：

| 指標 | 變化 |
|---|---|
| Coherence | +0.5 |
| Readability | +1.0 |
| Coverage | -0.05（幾乎不變） |
| Relevance | 0（不變） |

這是全篇論文中證據力相對紮實的實驗——直接 before/after 對照，證實摘要+重排確實提升可讀性與連貫性，且沒有明顯犧牲內容涵蓋度。但樣本數僅10篇，評分者也非獨立第三方。

> 📌 **附錄缺失**：附錄 D–G 提供了 Zero-shot/Few-shot 的 Topic Generation 與 Content Extraction 完整 prompt，但**沒有**提供 Stage 3（摘要+重排）用的 prompt template，是四個模組中唯一無法從附錄還原的一步。

---

## 3. 背景知識補充

> 這節整理我在討論過程中額外提問、之前不熟悉的兩個技術背景。

### 3.1 Decision Transformer（Chen et al., 2021, NeurIPS 2021）

**時間脈絡**：2021年6月掛上 arXiv，同年 NeurIPS 發表，時間點卡在 GPT-3（2020）之後、ChatGPT（2022）之前，是「Transformer 能否用於序列決策問題」這股研究風潮的代表作之一。

**要解決的問題**：傳統 RL（Q-learning、policy gradient）訓練不穩定、需要精細調參、常需要 online 跟環境互動。Decision Transformer 提出典範轉移：把 RL 問題重新包裝成「序列預測」問題，用 GPT 式的監督學習訓練，完全不用算價值函數（value function）、不用 bootstrapping。

**具體運作（以走迷宮為例）**：

- 一條軌跡（trajectory）由多個 (state, action, reward) 組成
- 訓練前先把 reward 轉換成 **return-to-go**（從現在這步到終點，總共還會拿到多少分）
- 模型輸入是交錯排列的三元組序列：`[return-to-go, state, action]`
- **訓練**：蓋住 action，讓模型根據前面的 (return-to-go, state) 去預測應該輸出的 action，用 cross-entropy/迴歸 loss 對答案
  - 學到的映射：`(我還想拿到10分, 我現在在位置A) → 往右走`
- **Inference**：使用者先「開口許願」設定一個目標 return（比如「我想拿10分」），模型根據這個目標 + 目前 state 吐出動作；每走一步，剩餘 return-to-go 依實際拿到的分數遞減；重複直到走完

**一句話**：訓練時是「觀察別人怎麼走 + 最後拿多少分 → 學會兩者關聯」；使用時是「你先設定想要的分數 → 模型回推該怎麼走」。

**有沒有變主流技術？**
- 研究圈內有明確影響力：同期有 Trajectory Transformer（Janner et al. 2021）提出類似想法；後續有 Online Decision Transformer；也被延伸應用到推薦系統、機器人、embodied AI、網頁導航 agent 等領域
- **但沒有成為 LLM alignment 的主流做法**——今天 RLHF 生態主流仍是 PPO（InstructGPT）或後來的 DPO，Decision Transformer 本身不是訓練 ChatGPT/Claude 這類模型對齊的主流框架。它比較像在「offline RL / 機器人控制」這個子領域持續有影響力，不是家喻戶曉的產品技術

**Persona-Aware-D2S 怎麼用它**：
- 只是借用「reward-conditioned generation」這個**訓練技巧**（把 reward 當 condition 塞進輸入，用監督學習訓練），繞開 PPO 的複雜度
- **⚠️ 這是不完整的挪用**：Decision Transformer 原本的威力在處理「多步驟、有前後因果關係」的序列決策問題（這步的選擇會影響下一步能拿多少分）。但這篇論文的應用場景是「單次生成」（一次把 prompt 丟進去，一次吐出完整 outline），**沒有真正的多步驟決策結構**，也沒有「軌跡」的概念。所以嚴格來說只是借了表層技巧，沒用到它真正被設計來解決的核心問題

**跟這篇論文的映射關係**：

| Decision Transformer 概念 | Persona-Aware-D2S 的對應 |
|---|---|
| return-to-go（還想拿多少分） | reward model 打的分數 |
| state（目前在哪） | prompt（論文內容 + persona 條件） |
| action（要往哪走） | 要生成的 topic-set |
| 一整條軌跡 | 不存在——只是單步生成 |

---

### 3.2 Bradley-Terry Model（Bradley & Terry, 1952）

**起源**：一個很老的統計模型，1952年提出，原本用來處理「兩兩比較 → 推算整體排名」的統計問題（比如球隊排名），完全不是為了 AI 而生。

**核心假設**：每個項目都有一個看不見的「實力值」，比較結果只是這個實力值的機率反映，不是絕對保證。

**公式（純文字版）**：

```
P(i 贏 j) = 實力_i / (實力_i + 實力_j)
```

**具體例子**：若 A 隊實力值=8，B 隊實力值=2，則 P(A贏B) = 8/(8+2) = 0.8——A 實力強4倍，贏面80%，但B仍有20%機率爆冷。這種容許不確定性的設計，正好適合套用在「人類偏好」這種有雜訊、不一定每次判斷都一致的場景。

**跟 RLHF 的關係**：
- 把 P(i>j) 重新參數化成指數形式（p_i = e^r_i），就會得到 reward model 訓練常見的 sigmoid(reward差) 形式
- 這是 **RLHF 領域最廣泛採用的偏好模型**——從 Christiano et al. 2017（RLHF 開山文獻）、OpenAI InstructGPT、到後續的 DPO，底層數學都是同一套 Bradley-Terry loss，只是應用方式不同
- Persona-Aware-D2S 論文的 reward modeling loss（見 2.1b）**不是原創**，是直接套用這套業界標準做法

**具體訓練例子**：reward model 對 chosen 版本打 3.5分、rejected 打 1.0分 → s_w - s_r = 2.5 → sigmoid(2.5) ≈ 0.92 → loss = -log(0.92) ≈ 0.08（很小，代表判斷準確）；若打分方向錯誤（chosen反而低分），loss 會飆到 2.53 左右，梯度會用力修正。

**為什麼用 pairwise 比較而非直接打分**：直接打分（如「1-10分」）標註者之間一致性低；成對比較（「A跟B哪個好」）人類直覺容易判斷、共識度較高。這也是為什麼 §3.1.2 的標註流程設計成 pairwise ranking。

**已知的方法論缺陷**：Bradley-Terry 依賴「傳遞性」假設（A>B, B>C ⟹ A>C），但人類偏好常不滿足這個假設。這篇論文的「只保留多數決有共識的樣本，丟棄無共識樣本」做法，某種程度是在迴避這個問題，而非真正解決。

---

## 4. 批判性評估

### 4.1 論文自己承認的限制（Limitations 章節原文）

1. Approach is limited to be faithful to document content（內容忠實度有限）
2. 大部分技術術語需要額外解釋才能讓非專家理解，但模型能力有限
3. 完全依賴人類撰寫的圖表 caption，不會生成原創圖表、不理解圖片本身內容
4. 只能產生 bullet-point 格式的文字摘要，**不涉及排版設計**（layout design）
5. 沒有多模態表徵能力，可能導致圖片相關資訊流失

### 4.2 我的批評（論文未提及、但分析後認為存在的問題）

| 面向 | 問題 |
|---|---|
| **訓練資料規模** | Topic Generation 訓練僅80筆樣本（20篇×4configs），dev split僅5篇；小樣本 fine-tuning 容易 overfit 到這批論文的寫作風格，泛化到不同 domain 的效果存疑 |
| **架構 Scalability** | 4種 persona 配置需要訓練4個獨立 SFT 模型+4組 reward model；若擴展 persona 維度（如加入角色：PM/工程師/主管），模型數量會乘法爆炸，完全不 scalable |
| **檢索機制的隱藏成本** | Section Filter 篩選不可逆，21%的相關內容會被永久漏掉；th 門檻值只在5篇論文上調過，泛化性存疑；高度依賴標準化 section 結構，對非結構化文件會失效 |
| **Reward model capacity** | 用 distilbert-base-cased（約66M參數）判斷「comprehensibility」這種語意複雜的任務，capacity 是否足夠未經驗證 |
| **P-F 訓練細節缺失** | "maximum reward" 數值怎麼決定、reward 是純量還是多維，論文均未交代清楚，難以複現 |
| **Stage 3 資源分配不對稱** | 對最終體驗影響最大的摘要+重排步驟，反而是唯一沒做任何客製化訓練的環節，論文未解釋原因，附錄也沒提供該步驟的 prompt |
| **Hallucination 評測方法薄弱** | 用「relevance 評分」proxy「有沒有幻覺」，測不出「內容相關但細節捏造」這類幻覺 |
| **實驗樣本數普遍偏小** | 質化分析僅10篇、認知負荷研究僅3位專家、消融實驗僅10篇，統計效力低（注意：這是「規模不足」而非「沒有做」——論文的實驗涵蓋面其實算完整：模組級評測+端到端評測+消融+質化分析都有涉及） |
| **產出物離「真正的投影片」有明顯落差** | 完全不含排版、顏色、字體等視覺設計，本質上輸出的是結構化文字大綱，不是可直接使用的簡報 |

---

## 5. Engineering / Production 落地價值評估

### 5.1 各模組 ROI 判斷

| 模組 | 落地可行性 | ROI 判斷 |
|---|---|---|
| Stage 1（SFT+P-F 的 4模型架構） | 低 | 訓練+維運成本隨 persona 維度乘法增長，不建議直接複現 |
| Stage 2（fuzzy match + SBERT 兩層檢索） | **高** | 成熟、可遷移、確實解決真實痛點（省API成本）。與 retrieve-then-rerank 的通用 RAG 設計思路一致，值得參考 |
| Stage 3（摘要+重排，無需訓練） | **最高** | 成本最低（僅2次額外LLM呼叫）、消融實驗證實有明確效果提升，是全篇論文中投入產出比最好的部分 |
| Decision-Transformer-style 訓練技巧 | 中（視情境） | 若你自己有需要做輕量版 preference alignment、又想避開 PPO 的 infra 複雜度，這個「reward 當 condition 塞進監督學習」的思路值得參考；但要清楚意識到它捨棄了 Decision Transformer 真正的多步驟決策優勢 |

### 5.2 若要在工作中導入，建議的取捨

- **可以直接借鑑**：Stage 2 的兩層檢索設計（先便宜的字面匹配，字面失敗才動用語意模型）；Stage 3 的「抽取後摘要重排」兩步驟 prompting 模式
- **不建議複現**：Stage 1/2 的「每種條件訓練一個獨立模型」架構；小樣本 SFT 的做法本身風險較高，除非你的任務也是「教模型輸出格式/風格」而非「教新知識」
- **這篇論文更適合當作「問題定義」的參考，而非「解決方案」的參考**——它的價值在於清楚描述了 persona-aware 生成這個任務該長什麼樣，而不是提供了一個可直接落地的系統

---

## 6. 整體結論

**研究價值**：中等偏低。核心貢獻是「定義新任務 + 建立新資料集」，方法論本身（SFT + RLHF-lite 組合）沒有原創性，都是直接沿用 Christiano et al. 2017（RLHF）、Chen et al. 2021（Decision Transformer）的現成技術拼裝。論文能中 EACL 2024 long paper，主要吃在任務定義的新穎性，而非方法創新。

**工程價值**：低，不建議整體複現進 production。訓練資料規模撐不起真實世界的 domain diversity；4倍模型數量的架構不 scalable；產出物離「可直接使用的投影片」還有一大段距離（無排版、無視覺設計）。

**唯一值得帶走的兩個東西**：
1. Stage 2 的 retrieve-then-rerank 檢索設計（fuzzy match + SBERT fallback）
2. Decision Transformer 的「reward-conditioning」訓練思路的基本概念（即便這篇論文只是不完整的借殼使用）


