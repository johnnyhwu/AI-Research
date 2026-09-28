這是一份為你——身為AI軟體工程師——量身打造的**《Generative Skill Composition for LLM Agents》深度學術與工程研讀筆記綱要**。

這份綱要旨在建立一條嚴謹、客觀且具備高度實務參考價值的學習路徑，將論文底層的數學形式、資料流設計，與我們在討論過程中提煉出的「工程實作細節（如 PyTorch 張量對齊、分類與迴歸的本質區別、手算字串去重演算法等）」進行深度結合。

以下為本篇研讀筆記的章節綱要：

---

# 📖 《Generative Skill Composition for LLM Agents》深度學術與工程研讀筆記

## 📌 前言
*   筆記撰寫目的與定位：AI 軟體工程師的實務落地指南
*   技能庫組合技術（Skill Composition）在 Agent 技術演進時間軸上的關鍵位置
*   閱讀本筆記預期獲得的工程直覺與數學素養

---

## ## Chapter 1: LLM Agent 技能庫時代的瓶頸與挑戰
### 1.1 技能（Skills）與傳統原子級 API 的本質差異
*   定義 3.1（Skills）與傳統 Tool-use 的分水嶺
*   為什麼 Skills 是「非型別（Non-typed）」且「高敏感度」的程序知識？
### 1.2 傳統方案的雙重失敗：純檢索與上下文洪水
*   純檢索（Flat Retrieval）在結構化任務中的天然缺陷
*   大模型「上下文淹沒（Context-Flooding）」與注意力稀釋的量化證明
*   *【對應圖表：Figure 1】*
### 1.3 結構化技能組合的三個維度：選哪些、選多少、什麼順序
*   如何將這三個耦合問題視為一個不可分割的聯合決策？
*   *【對應圖表：Figure 2】*

---

## ## Chapter 2: SkillComposer 核心問題定義 (Problem Formulation)
### 2.1 將「搜尋問題」重塑為「封閉詞表造句遊戲」
*   引入封閉詞彙表（Closed Vocabulary）與 $K$ 個技能 ID 的轉換邏輯
*   封閉詞表設計如何 100% 免疫大模型的技能幻覺（Hallucination）
### 2.2 漸進式揭露（Progressive Disclosure）的 Token 減負哲學
*   Inference 階段的「精簡 Metadata 檢索」與 Execution 階段的「完整 Policy 載入」
### 2.3 任務約束技能序列預測的數學形式
*   自迴歸序列生成的數學定義與 `STOP` Token 的動態終止機制
*   *【對應數學定義：Definition 3.2 & Definition 3.3】*

---

## ## Chapter 3: 模型架構拆解與張量資料流 (Core Architecture & Tensor Dimensions)
### 3.1 凍結的語言理解器：Task Encoder 與 256 維降維矩陣
*   為什麼選擇凍結大模型（Qwen3-Embedding）並僅訓練一個線性投影層 $W_{proj}$？
*   張量維度流轉：輸入文字 $\to$ $\mathbf{h}_x \in \mathbb{R}^{1024}$ $\to$ $W_{proj}$ 降維 $\to$ 任務向量 $\mathbf{h} \in \mathbb{R}^{256}$
*   *【對應圖表：Figure 3 (Part A)】*
### 3.2 技能記憶體（Skill Memory）矩陣的建構
*   196 個技能的 Metadata 編碼與對齊矩陣
*   張量維度流轉：$196$ 個技能文字 $\to$ $\mathbb{R}^{196 \times 1024}$ $\to$ $W_m$ 投影 $\to$ 技能記憶體 $\mathbb{R}^{196 \times 256}$
### 3.3 輕量級自迴歸解碼器：3 層 Transformer 解碼器規格
*   Decoder 內部工作規格與多頭注意力（4 Heads）設定
*   *【對應圖表：Figure 3 (Part B)】*
### 3.4 核心剖析：Decoder 層內 Masked Self-Attention 與 Cross-Attention 的交錯運作與數學推導
*   為什麼不能只有 Cross-Attention？前綴條件解碼（Prefix-conditioned decoding）的本質
*   **子層一：Masked Self-Attention** —— 揉合 Task Vector 與已生成技能歷史的張量流動（以第 $t$ 步輸入 $[\mathbf{h}, E(\text{START}), E(s_{104})]$ 為例）
*   **子層二：Cross-Attention** —— 拿著吸飽歷史的 Query 去與技能記憶體計算夾角分數的數學推導與 $QK^T$ 矩陣乘法維度對齊

---

## ## Chapter 4: 因式分解監督：雙重輔助預測頭 (Factorized Supervision via Auxiliary Heads)
### 4.1 序列監督訊號被稀釋與污染的學術痛點
*   自迴歸模型在預測「數量」與「位置無關相關性」時的梯度弱點
### 4.2 數量預測頭（Cardinality Head）：為什麼分類（CE）優於迴歸（MSE）？
*   數學思維對比：機率分佈（Soft-biasing）對 Beam Search 的價值 vs. MSE 連續空間的 rounding 偏見
*   張量與損失函數：$\mathbf{h} \in \mathbb{R}^{256} \to W_n \to \mathbb{R}^8$ 的 Cross-Entropy 計算
### 4.3 集合預測頭（Set Head）：四維特徵拼接的物理與幾何語意
*   拼接特徵 $[\mathbf{h} ; \mathbf{e}_i ; \mathbf{h} \odot \mathbf{e}_i ; |\mathbf{h} - \mathbf{e}_i|]$ 的逐項物理意義剖析（Hadamard 積與絕對差值的幾何直覺）
*   批次（Batch）特徵廣播計算與 $196$ 個技能的 BCE 損失函數
*   *【對應公式：式 4.3】*
### 4.4 多任務聯合訓練損失函數的權重分配
*   聯合 Loss 各項 Lambda 的實務配置
*   *【對應公式：式 4.1 與 Section 5.1 實作細節】*

---

## ## Chapter 5: 推論階段的對數機率融合與束搜索 (Retrieval-Augmented Decoding & Beam Search)
### 5.1 對數空間的向量疊加：三方分數融合公式
*   結合「上下文」、「無監督檢索先驗」與「全域相關性」的貝氏概率相加原理
*   *【對應公式：式 4.4】*
### 5.2 實務工程難題：196 維先驗與 199 維 Decoder Logits 的 PyTorch 拼接與補零對齊
*   真實 PyTorch 代碼切片（Slicing）與 199 維（含特殊 Token）對齊的工程實作
### 5.3 帶約束的束搜索演算法：重複技能遮罩（$-\infty$ Masking）與長度懲罰機制
*   束寬度 $W=4$ 與長度懲罰因子 $\gamma = 0.7$ 的實務作用
*   在 Beam Search 展開時，使用 $-\infty$ 遮罩實現「同路徑一票否決重複技能」的演算法細節
*   長度控制：如何結合 Cardinality Head 進行軟硬兼施的終止剪裁（Hard-clip）
### 5.4 超參數優化：驗證集座標上升法（Coordinate Ascent）與停止偏差（$\delta_{stop}$）的調校
*   如何修正合成資料與真實任務間的數量偏斜（Cardinality Skew）？
*   *【對應圖表：Figure 5 (Part a)】*

---

## ## Chapter 6: 訓練資料的煉金術：資料工程流水線 (Data Curation & Synthesis)
### 6.1 技能相依圖設計：資料流相依（Dependency Edges）與工作流共現（Workflow Edges）
*   924 條邊的比例與採樣機制：以硬性資料流為骨架，經驗工作流為血肉
*   *【對應圖表：Table 5】*
### 6.2 多層次大模型合成：單技能對齊與多技能依賴約束 Prompts
*   為什麼單技能合成對於「教導模型何時停止」至關重要？
*   Gemini 2.5 Flash / Pro 的合成工作分配
*   *【對應圖表：Figure 6 & Figure 7】*
### 6.3 三層過濾去重與格式驗證機制
*   字串精確匹配 $\to$ Trigram Jaccard 相似度 $\to$ 語意向量餘弦相似度 的漏斗式過濾架構
*   *【對應實作細節：Appendix B.3】*
### 6.4 深入實例計算：字元三元組傑卡德相似度（Trigram Jaccard）手算步驟與漏斗過濾原理
*   以 `"AI agent"` 與 `"AI agents"` 為例的手算全流程（交集與聯集之比值計算）
*   Trigram 算法抗語序顛倒與拼字錯誤的幾何原理

---

## ## Chapter 7: 關鍵實驗、消融分析與學術洞察 (Experimental Analysis & Insights)
### 7.1 跨域泛化能力測試：為什麼標準 SFT 崩盤而 SkillComposer 能優雅落地？
*   全參數微調（600M）對合成句型範本的 Overfitting 痛點分析
*   *【對應圖表：Table 1】*
### 7.2 下游編碼 Agent 實測：少即是多與注意力稀釋的量化證明
*   Context-Flooding 在 1.27M tokens 級別下的注意力渙散現象剖析
*   *【對應圖表：Table 2】*
### 7.3 檢索先驗消融：為什麼 TF-IDF Cosine 在微觀檢索中完勝 BM25 與 Dense Embedding？
*   微觀檢索（Micro-retrieval）下，BM25「長度歸一化」與「詞頻飽和」優勢失效的數學原因
*   *【對應圖表：Table 4】*
### 7.4 柏拉圖最優前沿：3.9M 小模型擊敗 Frontier 大模型裁判的成本延遲對比
*   在特定、封閉領域中，訓練專門小專家模型對比調用大模型裁判的巨大成本與延遲優勢
*   *【對應圖表：Figure 5 (Part b & c) & Table 3】*

---

## 📌 結論
*   `SkillComposer` 的核心工程啟示：結構化預測（Structured Prediction）在 Agent 架構設計中的復興
*   給 AI 軟體工程師的實務建議：如何將本論文的「資料合成 $\to$ 凍結 Backbone 投影 $\to$ 自迴歸解碼 $\to$ 推論 Logit 融合」全套方法論複製到企業內部的專有 API 路由系統中

---

這份綱要已經涵蓋了我們所討論的**全部細節**，並精確對齊了論文中的所有 Figure 和 Table。

你可以先確認一下這個結構。如果你對這份綱要的章節劃分與對齊方式感到滿意，我們接下來就可以從 **「Chapter 1」** 或 **「前言」** 開始，正式用嚴謹、客觀的工程師語言，一步步將這篇宏大的研讀筆記的細節內容撰寫出來！

本篇筆記旨在客觀、嚴謹地梳理 2026 年發表的論文《Generative Skill Composition for LLM Agents》之核心方法論與工程實作細節。

在大型語言模型代理（LLM Agents）的發展過程中，隨著代理能使用的「技能（Skills）」或「工具」庫體積急劇膨脹，如何精確、高效地在推論階段挑選、規劃並安排這些技能的執行順序，已成為決定 Agent 任務成功率與算力成本的核心瓶頸。

本篇論文提出的 `SkillComposer` 框架，提供了一個不同於傳統「無序檢索（RAG）」與「大模型直接規劃（End-to-end Planning）」的新思路。它將技能組合問題重新定義為**「受任務約束的封閉詞表序列預測問題」** [1, 2]。藉由一個凍結的語意編碼器（Encoder）、輕量化的自迴歸解碼器（Decoder） [2]，並在訓練階段引入輔助預測頭 [2]、在推論階段實施對數機率融合（Logit Fusion）與束搜索（Beam Search） [2, 3]，從而在極小的參數代價下，實現了兼具準確性、抗分佈偏移（Robustness）與低延遲的技能派發 [3, 4]。

本筆記將跳脫學術宣傳的修辭，以 AI 軟體工程師與研究員的視角，深度還原以下核心內容：
1. **技能組合問題的數學與邏輯定義**。
2. **模型內部的張量維度流動**，特別是 Masked Self-Attention 與 Cross-Attention 的交錯機制。
3. **輔助預測頭**的特徵工程與 Loss 設計。
4. **推論階段 PyTorch 級別的張量對齊、遮罩（$-\infty$ Masking）與融合演算法**。
5. **支撐該系統的資料工程**（圖採樣、Gemini 合成、多層過濾去重演算法）。

希望透過這份客觀、具體的技術記錄，能協助讀者在面對企業級的多工具 Agent 系統時，能有更清晰的架構設計直覺與複製此方案的工程實力。

以下是為你撰寫的筆記第一章與第二章合併內容，本章節著重於客觀陳述「技能（Skills）」在 LLM Agent 時代所面臨的組合瓶頸，以及論文如何建立數學模型將其重新定義為一個「序列生成問題」：

---

## ## Chapter 1 & 2: 技能庫組合的瓶頸挑戰與核心問題定義

在現代 LLM Agent 系統中，隨著功能性工具（Tools）逐漸演進為更高級、富含程序知識的「技能庫（Skill Libraries）」，如何精確地調度與執行這些技能，已成為限制 Agent 效能的核心瓶頸。

---

### 1. 技能（Skills）與傳統原子級 API 的本質差異

在深入挑戰之前，我們必須釐清「技能（Skill）」與常規「工具/API 呼叫（Tool/API Call）」在學術與工程上的本質區別。

根據論文 **Definition 3.1**，每一個技能 $s_i$ 被定義為一個多維度的元組（Tuple）：
$$ s_i = (m_i, C_i, \pi_i, T_i, R_i) $$

*   **$m_i$（Metadata）**：技能名稱與一句話的簡短描述。
*   **$C_i$（Applicability Condition）**：適用條件（例如輸入需包含特定格式的資料）。
*   **$\pi_i$（Procedural Policy）**：程序策略，即具體指引大模型逐步執行的自然語言指令或程式碼腳本。
*   **$T_i$（Termination Condition）**：終止條件（如特定檔案已被寫入）。
*   **$R_i$（Supporting Resource）**：支援資源（如輔助的 Python 腳本或 REST API 端點）。

與一般的 API 呼叫（如計算機、單一 SQL 查詢）相比，技能是**更粗粒度、涵蓋多個執行步驟且不具備硬性程式型別（Non-typed）的知識包**。由於缺乏型別約束，技能之間的依賴關係是「隱性的、任務邏輯上」的，這使得傳統基於型別匹配的自動 API 規劃器無法直接應用於技能派發。

---

### 2. 傳統組合方案的雙重失敗（對應 Figure 1）

當技能庫規模擴大（例如達到論文設定的 $K = 196$）時，傳統的技能選擇方案面臨雙重瓶頸：

1.  **扁平無序檢索（Flat Retrieval）的失敗**：
    傳統方法利用 Embedding 相似度（如 Qwen3-Embedding）或 LLM-as-a-judge，將技能與任務進行獨立比對。這種做法只能回傳一個**「無序的候選子集」**。然而，實際任務往往具有嚴格的先後順序（例如：必須先下載 USGS 數據，才能對比水位閾值，最後才能進行洪水檢測）。扁平檢索無法判斷需要多少個技能，也無法提供正確的執行順序。
2.  **直接推理與上下文洪水（Context-Flooding）的失敗**：
    另一種做法是直接將整個技能庫（All Skills）注入大模型的 Prompt 中，讓模型在執行任務時自己挑選。實驗表明（對應 **Table 2**），這種做法會導致巨大的 Token 浪費，並嚴重稀釋 LLM 的注意力（Attention），導致任務成功率（Pass Rate）反而大幅下降。

#### 核心 Insight：技能組合的三個不可分割維度（對應 Figure 2）
一個成功的技能計畫必須同時解決三個高度耦合的維度：
*   **選哪些（Subset）**：挑選出真正與任務相關的子集。
*   **選多少（Count）**：動態決定需要多少個工具，適時終止（STOP）。
*   **什麼順序（Ordering）**：按照任務邏輯依賴依序排兵佈陣。

這三個維度無法被拆開單獨解決，必須在一次決策中同時產生。

---

### 3. 問題重新塑形：受任務約束的封閉詞表序列預測

為了在一個步驟中同時決定「選哪些、選多少、什麼順序」，論文在 **Definition 3.2** 和 **Definition 3.3** 中，將技能組合重新表述為一個**「受任務條件約束的技能序列預測問題（Task-conditioned Skill Sequence Prediction）」**。

其核心工程哲學如下：

#### A. 封閉詞彙表（Closed Vocabulary）與 ID 化
在推論（Inference）階段，技能庫 $\mathcal{S}$ 的大小 $K$ 是固定的。因此，模型將 196 個技能直接對應到整數 ID $\{1, 2, \dots, K\}$，並引入特殊符號 `STOP`、`START` 與 `PAD`，構建出一個極小的**封閉詞彙表**：
$$ \mathcal{V} = \{1, 2, \dots, K\} \cup \{\text{STOP}, \text{START}, \text{PAD}\} $$

模型不再需要生成冗長的文字，而是直接在這個封閉詞表上進行「造句（Sequence Generation）」。這在物理上 100% 避免了大模型憑空捏造技能名稱的幻覺問題。

#### B. 漸進式揭露（Progressive Disclosure）
為了兼顧算力成本與準確性，`SkillComposer` 採用了漸進式揭露。在進行序列預測時，模型**只讀取技能庫的 Metadata $m_i$（名稱與單行描述）**。直到序列解碼完成（例如生成了 `104 -> 184 -> 55 -> STOP`）之後，系統才會去資料庫中調用這些 ID 對應的完整程序策略 $\pi_i$，並載入下游 Agent 的 Prompt 中。這大幅節省了推論階段的 Token 消耗量。

#### C. 問題的數學形式
給定任務 $x$、環境 context $c$、固定技能庫 $\mathcal{S}$，模型 $f_\theta$ 將直接預測一個變動長度的技能索引序列 $\hat{\mathbf{z}}$：
$$ \hat{\mathbf{z}} = (\hat{z}_1, \hat{z}_2, \dots, \hat{z}_n, \text{STOP}) = f_\theta(x, c, \mathcal{S}) $$

其中 $\hat{z}_t \in \{1, \dots, K\}$。當模型生成 `STOP` 時，序列自動終止。這個數學形式極為優雅地讓「子集選擇、數量預測、執行順序」在**單次的解碼前向傳播（Single decoding pass）**中同時自然湧現。

以下為你撰寫筆記第三章的完整內容，本章節將以極致的細節還原 `SkillComposer` 的模型架構、資料流、張量維度（Tensor Dimensions）以及解碼器層內部的數學運作機制：

---

## ## Chapter 3: 模型架構拆解與張量資料流

`SkillComposer` 的架構本質上是一個經過高度輕量化與特化的 **Encoder-Decoder（編碼器-解碼器）** 網路（對應 **Figure 3**）。本章將從資料流的維度流轉開始，深入剖析其底層矩陣運算。

---

### 3.1 凍結的語言理解器：Task Encoder 與 256 維降維矩陣

在系統的輸入端，模型必須對「用戶任務」、「環境上下文」以及「技能 Metadata」進行高質量的語意表徵。

*   **輸入字串**：序列化後的 Prompt $P(x, c, \mathcal{S})$。
*   **骨幹網路（Backbone $E_\phi$）**：採用預訓練的稠密向量模型 `Qwen3-Embedding-0.6B`。為了避免過度擬合與巨額算力開銷，**其模型參數 $\phi$ 在訓練過程中被完全凍結（Frozen）**。
*   **初始任務向量**：對 Qwen3 的輸出進行「最後一個 Token（Last-token pooled）」的池化操作，提取出初始高維任務特徵 $\mathbf{h}_x \in \mathbb{R}^{1024}$。
*   **降維投影層（Projection Layer $W_{proj}$）**：
    由於後續的自迴歸解碼器（Decoder）工作維度設定為 $d=256$，系統使用一個**可訓練**的線性投影矩陣 $W_{proj} \in \mathbb{R}^{1024 \times 256}$ 來對特徵進行壓縮與對齊：
    $$ \mathbf{h} = \mathbf{h}_x \cdot W_{proj} \quad \in \mathbb{R}^{256} $$

最終輸出最終任務向量 $\mathbf{h} \in \mathbb{R}^{256}$，作為後續解碼器（Decoder）的 **前綴條件（Prefix Condition）**。

---

### 3.2 技能記憶體（Skill Memory）矩陣的建構

為了解碼器能依據「自然語言語意」來認識並挑選技能，系統必須為技能庫中的 $K = 196$ 個技能建立語意表徵，這被稱為「技能記憶體（Skill Memory）」：

1.  **輸入**：196 個技能各自的自然語言 Metadata $m_i$（技能名稱與單行描述）。
2.  **編碼與投影**：同樣通過凍結的 $E_\phi$，並使用一個獨立的可訓練投影矩陣 $W_m \in \mathbb{R}^{1024 \times 256}$。
    $$ \mathbf{e}_i = E_\phi(m_i) \cdot W_m \quad \in \mathbb{R}^{256} $$
3.  **記憶體矩陣**：將 196 個技能的表徵向量堆疊，形成一個靜態的技能記憶體矩陣：
    $$ \mathbf{M}_{skill} = \begin{bmatrix} \mathbf{e}_1 \\ \mathbf{e}_2 \\ \vdots \\ \mathbf{e}_{196} \end{bmatrix} \quad \in \mathbb{R}^{196 \times 256} $$

這個 $\mathbf{M}_{skill}$ 在整個推論與解碼過程中保持不變，將作為 Decoder 的 Cross-Attention 鍵值（Keys & Values）來源。

---

### 3.3 輕量級自迴歸解碼器：3 層 Transformer 解碼器規格

自迴歸解碼器 $D_\theta$ 是一個微型且高效的 Transformer 網路（對應 **Figure 3 (Part B)**）。其工作配置如下：
*   **層數**：3 層（3-layer）Pre-norm Transformer。
*   **隱藏維度**：$d=256$。
*   **注意力頭數**：4 Heads。
*   **詞表空間大小**：$196$ 個真實技能 ID $+ 3$ 個特殊 Token（START, STOP, PAD）$= 199$。因此，頂部 LM Head 的輸出維度為 $\mathbb{R}^{199}$。

---

### 3.4 核心剖析：Decoder 層內 Masked Self-Attention 與 Cross-Attention 的交錯運作與數學推導

為了解決自迴歸解碼在沒有 explicit typed signatures 情況下的「順序依賴性」與「任務條件對齊」，每一層解碼器內部被嚴格拆解為三個子層（Sub-layers）進行交錯運作：

#### ⚙️ 運算子層一：遮罩自注意力機制（Masked Self-Attention）
自迴歸的本質是 $p_\theta(z_t \mid \mathbf{h}, \mathbf{z}_{<t})$。為了讓模型在第 $t$ 步時，能同時考慮「任務目標（前綴 $\mathbf{h}$）」與「已經選過的技能歷史（$\mathbf{z}_{<t}$）」，輸入序列在 Embedding 查表後會拼接成：
$$ \mathbf{X}_{in\_seq} = [\mathbf{h}, E(\text{START}), E(z_1), \dots, E(z_{t-1})] \quad \in \mathbb{R}^{(t+1) \times 256} $$

在 Self-Attention 中，模型計算 $Q_{self}, K_{self}, V_{self}$ 均來自 $\mathbf{X}_{in\_seq}$，並使用下三角遮罩（Causal Mask）阻止資訊向未來洩露。
*   **物理意義**：這一步驟讓序列中最後一個 Token 的輸出狀態 $\mathbf{h}_{self} \in \mathbb{R}^{256}$ 成功吸收了前面所有的歷史軌跡與任務前綴。這個 $\mathbf{h}_{self}$ 即代表**「在任務 $\mathbf{h}$ 的約束下，執行完歷史技能序列後，當下的系統狀態」**。

#### ⚙️ 運算子層二：交叉注意力機制（Cross-Attention）
這是模型「翻找技能庫」並與自然語言描述進行匹配的核心數學運算。
*   **Query ($Q$)** 來自上一步 Masked Self-Attention 在最後一個位置輸出的狀態向量 $\mathbf{h}_{self}$：
    $$ Q = \mathbf{h}_{self} \cdot W_Q \quad \in \mathbb{R}^{1 \times 256} $$
*   **Key ($K$) 與 Value ($V$)** 來自靜態的技能記憶體矩陣 $\mathbf{M}_{skill}$：
    $$ K = \mathbf{M}_{skill} \cdot W_K \quad \in \mathbb{R}^{196 \times 256} $$
    $$ V = \mathbf{M}_{skill} \cdot W_V \quad \in \mathbb{R}^{196 \times 256} $$

接著計算當前查詢與 196 個技能描述的內積，除以縮放因子 $\sqrt{d_k}$（其中 $d_k = 256 / 4 = 64$），得到注意力權重分數 $A$：
$$ \text{Scores} = \frac{Q \cdot K^T}{\sqrt{d_k}} \quad \in \mathbb{R}^{1 \times 196} $$
$$ A = \text{Softmax}(\text{Scores}) \quad \in \mathbb{R}^{1 \times 196} $$

最後，將權重乘上 $V$，得到對技能庫的加權特徵總和：
$$ \text{Context}_{skill} = A \cdot V \quad \in \mathbb{R}^{1 \times 256} $$

*   **物理意義**：這個 Cross-Attention 的核心優雅之處在於，模型在第 $t$ 步做決策時，它的 Query 向量是在與 196 個技能描述向量（$K^T$）算夾角投影。模型是在**語意空間**中尋找與目前上下文狀態最重合的技能描述，而非盲目預測一個抽象的 ID。

#### ⚙️ 運算子層三：前饋神經網路（Feed-Forward Network, FFN）
$$ \mathbf{h}_{out} = \text{LayerNorm}(\text{FFN}(\text{Context}_{skill}) + \mathbf{h}_{self}) \quad \in \mathbb{R}^{256} $$
經過殘差連接與 LayerNorm 後，資訊被送入兩層的線性對齊網路，並透過 GELU 進行非線性投射。

---

經過 3 層解碼器層重複上述三個子層的運作後，頂部 LM Head 將 $\mathbf{h}_{out}$ 投射至 199 維的對數機率空間，輸出原始的 Logit 向量 $\boldsymbol{\ell}_t \in \mathbb{R}^{199}$，為後續的 Logit Fusion 與束搜索做好準備。

以下為你撰寫筆記第四章的完整內容，本章節將著重於剖析輔助預測頭的數學公式、設計動機，以及多任務聯合訓練（Joint Training）的梯度學術原理：

---

## ## Chapter 4: 因式分解監督：雙重輔助預測頭

雖然上一章介紹的自迴歸（AR）主幹網路具備極佳的序列依存表達力，但在深度學習實務中，單純依靠序列生成的損失函數會面臨嚴重的監督訊號稀釋問題。本章將深度探討 `SkillComposer` 的**「因式分解監督（Factorized Supervision）」**機制。

---

### 4.1 序列監督訊號被稀釋與污染的學術痛點

在標準自迴歸訓練中，模型學習預測技能序列（如 `[A, B, C, STOP]`）時，面臨兩個主要的梯度困境：

1.  **「數量」訊號被隱式埋藏**：
    模型只有在最後一步預測 `STOP` Token 時，才能間接、被動地接收到關於「序列長度」的監督。在訓練早期，這種微弱的長度梯度很容易在反向傳播（Backpropagation）過程中流失，難以迫使編碼器（Encoder）主動產出具備「任務規模感（Task Scale）」的特徵。
2.  **「相關性」訊號與位置高度綁定**：
    如果技能 $C$ 被排在第三步，那麼模型只有在解碼至第三步、且前兩步都預測正確的前提下，才能有效地將「技能 $C$ 與任務相關」的梯度傳回給任務向量 $\mathbf{h}$。如果模型在前面步驟預測失誤，關於 $C$ 的正向監督訊號就會被嚴重污染。

為了解決這個問題，作者提出不應該把所有任務都壓在自迴歸 Decoder 身上，而應該對監督訊號進行「因式分解（Factorize）」，外掛兩個專門的輔助預測頭。

---

### 4.2 數量預測頭（Cardinality Head）：為什麼分類（CE）優於迴歸（MSE）？

數量預測頭專門回答 **"How many skills are needed?"** 的問題。它直接作用於任務向量 $\mathbf{h} \in \mathbb{R}^{256}$ 上：

$$ p_\psi(n \mid x, c) = \text{Softmax}(W_n \mathbf{h}) \quad \in \mathbb{R}^8 \quad (\text{對應公式 4.2}) $$

其中 $W_n \in \mathbb{R}^{8 \times 256}$ 是一個可訓練的線性分類矩陣（限制最大技能數 $N_{max} = 8$）。訓練時採用標準的交叉熵損失函數（Cross-Entropy Loss）。

#### 💡 學術與工程洞察：為什麼不將其視為 Regression Task 並用 MSE 訓練？
從直覺上看，數量預測似乎是一個連續數值問題，但使用**分類（CE）而非迴歸（MSE）**具有以下關鍵的底層邏輯：

1.  **幾何度量空間（Metric Space）的限制**：
    MSE 隱含假設了數值軸的連續性與等距性。在 MSE 眼裡，預測值與正確答案差距 $1$（如正確答案 $2$，預測成 $1$ 或 $3$）的懲罰是完全對等的。但在實務的 Agent 工作流中，「需要 1 個技能卻預測成 2 個（多呼叫一個無效工具導致崩潰）」與「需要 7 個技能卻預測成 8 個（微小的長尾偏差）」在系統風險上具有完全不同的非線性本質。分類模型不假設這種度量空間，允許網路為每個特定的數量狀態學出正交的特徵。
2.  **避免極端拉扯導致的保守預測**：
    真實任務的技能數量分布通常是偏態（Skewed）的。在 MSE 損失下，模型為了降低全局平方誤差的期望值，會表現出「均值回歸」，傾向於保守地預測中間值（如始終預測 2.5 個技能）。分類任務（Softmax）則能強迫模型在 8 個離散的工作流狀態中進行明確選擇，輸出更銳利（Sharp）的機率分佈。
3.  **為推論提供軟性先驗（Soft-biasing）**：
    分類輸出的 $\mathbb{R}^8$ 機率分佈，在後續解碼（Beam Search）時能提供一個豐富的先驗。這讓系統可以得知「模型對於要用 2 個還是 3 個技能的猶豫程度」，而迴歸輸出的單一純量（如 `2.6`）則完全喪失了這種不確定性表徵。

---

### 4.3 集合預測頭（Set Head）：四維特徵拼接的物理與幾何語意

集合預測頭專門回答 **"Which skills are relevant?"** 的問題。它是一個成對（Pairwise）匹配網路，拋開順序不談，只評估任務 $\mathbf{h}$ 與各個技能 $\mathbf{e}_i$ 的全域語意相關性：

$$ \sigma_i = g_\xi(\mathbf{h}, \mathbf{e}_i) = \text{MLP}_\xi([\mathbf{h} ; \mathbf{e}_i ; \mathbf{h} \odot \mathbf{e}_i ; |\mathbf{h} - \mathbf{e}_i|]) \quad \in \mathbb{R} \quad (\text{對應公式 4.3}) $$

其中 $\text{MLP}_\xi$ 是一個 2 層的 MLP，隱藏層維度為 256，輸出維度為 1（代表對應對數機率 Logit）。對 196 個技能獨立進行二元交叉熵損失（BCE Loss）訓練。

#### 💡 拼接特徵 $[\mathbf{h} ; \mathbf{e}_i ; \mathbf{h} \odot \mathbf{e}_i ; |\mathbf{h} - \mathbf{e}_i|]$ 的數學與幾何直覺
這個拼接設計借鑒了自然語言推論（NLI）領域的經典特徵工程。拼接後的維度為 $256 \times 4 = 1024$。其四個組成部分各自帶有明確的物理語意：

*   **$\mathbf{h}$ (Task Context)**：保留原始任務特徵，提供當前環境的全域背景知識。
*   **$\mathbf{e}_i$ (Skill Identity)**：保留原始技能嵌入，讓網路識別當前正在評估哪一個工具。
*   **$\mathbf{h} \odot \mathbf{e}_i$ (Hadamard Product / 元素級相乘)**：
    *   *幾何意義*：這是兩個向量在各個維度上的「互動投影」。如果任務與技能在某個語意特徵維度上同時具有高度激活，相乘後的結果就會被極度放大。它提供了最直接的**「共現與相似度」**特徵。
*   **$|\mathbf{h} - \mathbf{e}_i|$ (Element-wise Absolute Difference / 元素級絕對差值)**：
    *   *幾何意義*：這代表兩者在各個特徵維度上的「曼哈頓距離（Manhattan Distance）」。它能主動凸顯兩者之間的**「衝突與不匹配」**。如果某個特徵維度的絕對差值極大，代表該技能包含了任務根本不需要的操作，MLP 可以據此快速給出否定評分。

透過主動幫神經網路算出 $\odot$ 與 $|-|$，我們不需要強迫只有 2 層的微型 MLP 去「從頭學習如何做乘法與減法」，大幅降低了特徵提取的難度，這也是 Set Head 能保持極輕量且高準確度的關鍵。

---

### 4.4 多任務聯合訓練損失函數的權重分配

在訓練階段，`SkillComposer` 的參數更新並不是只看單一指標，而是將這三個任務進行多任務聯合學習（Joint Training）。其總損失函數定義如下：

$$ \mathcal{L}_{total} = \mathcal{L}_{AR} + \lambda_1 \mathcal{L}_{card} + \lambda_2 \mathcal{L}_{set} $$

根據論文 **Section 5.1 (Model implementation)** 提供的最佳工程實作細節，這兩個輔助預測頭的 Loss 權重（Lambda）設定為：
*   **$\lambda_1$ (Set Head Loss 權重)** = **$0.5$**
*   **$\lambda_2$ (Cardinality Head Loss 權重)** = **$0.25$**

#### 訓練動態（Training Dynamics）：
自迴歸序列損失（$\mathcal{L}_{AR}$）做為權重為 1 的絕對主導者，負責訓練自迴歸解碼器學會複雜的**「步驟順序」**。而兩個輔助損失則以較小的權重（0.5 與 0.25）作為強大的**「正則化（Regularization）約束」**。這確保了模型在學習順序的同時，其共享的 Encoder 表徵空間不會偏離「數量感知」與「位置無關相關性」的物理軌道，為推論階段的 Logit 融合打下完美的參數底子。

以下為你撰寫筆記第五章的完整內容，本章節將以極具工程實務性的視角，還原推論階段（Inference）的對數機率融合公式、PyTorch 維度對齊實作、帶有遮罩與懲罰機制的束搜索（Constrained Beam Search）演算法：

---

## ## Chapter 5: 推論階段的對數機率融合與束搜索

在推論（Inference）階段，`SkillComposer` 會將訓練階段所學得的各項獨立能力，與無監督的檢索先驗在對數空間（Log-space）中進行重新融合，並透過帶有約束條件的束搜索（Constrained Beam Search）為下游 Agent 規劃出最佳技能序列。

---

### 5.1 對數空間的向量疊加：三方分數融合公式

為了讓模型在每一步預測時都能同時兼顧「歷史順序」、「字面匹配」與「全域相關性」，系統引入了**對數機率融合（Logit Fusion）**機制（對應 **Figure 3 (Part C)** 與 **式 4.4**）：

$$ \tilde{\ell}_t(i) = \ell_t(i)_{\text{context}} + \alpha \cdot \bar{r}_i + \beta \cdot \sigma_i, \quad i \in \{1, \dots, 196\} $$

#### 💡 貝氏後期融合（Bayesian Late Fusion）的數學美感
如果我們將這三項分數轉回概率空間（Probability Space），由於 $\log(P) \propto \text{Logit}$，相加關係在機率上等同於：
$$ P(\text{Final}) \propto P(\text{Context}) \cdot P(\text{Retrieval})^\alpha \cdot P(\text{Set})^\beta $$

這種設計在數學上極為乾淨，它成功將一個原本極難優化的「多約束聯合機率問題」，轉換為對數空間中極低運算成本的**線性向量加法**。其中：
*   $\ell_t(i)_{\text{context}}$：Decoder 輸出的動態 Logits，決定**步驟順序與歷史**。
*   $\bar{r}_i$：預先算好並經過 Min-Max 校準的 TF-IDF 餘弦相似度向量，決定**字面關鍵字（長尾救援）**。
*   $\sigma_i$：Set Head 輸出的靜態 Logits，決定**全域無順序相關性**。

---

### 5.2 實務工程難題：196 維先驗與 199 維 Decoder Logits 的 PyTorch 拼接與補零對齊

在代碼實作中，我們必須解決一個工程難題：
*   檢索向量 $\bar{\mathbf{r}}$ 與 集合預測向量 $\boldsymbol{\sigma}$ 的維度均為 `[196]`。
*   Decoder 輸出的原始 Logit 向量 $\boldsymbol{\ell}_t$ 維度為 `[199]`（包含真實技能 + START + STOP + PAD）。

為了解決這個維度不對齊的問題，且避免先驗分數污染特殊 Token 的機率，系統採用了**選擇性切片（Selective Slicing）**與**補零（Padding）**的思想。以下為其在 PyTorch 實作中的邏輯：

```python
import torch

def fuse_logits(logits_199, r_bar_196, sigma_196, alpha=1.0, beta=0.5, delta_stop=0.0):
    """
    對解碼器第 t 步的 Logits 進行多方先驗融合
    張量維度對齊：
    - logits_199: [Batch_size, 199] (Decoder Raw Logits)
    - r_bar_196: [Batch_size, 196] (Calibrated TF-IDF Cosine Score)
    - sigma_196: [Batch_size, 196] (Set Head Raw Logits)
    """
    # 複製一份原始張量以進行 In-place 修改
    fused_logits = logits_199.clone()
    
    # 1. 僅對前 196 個維度（真實技能 ID）進行向量疊加
    fused_logits[:, :196] = logits_199[:, :196] + alpha * r_bar_196 + beta * sigma_196
    
    # 2. 對 STOP Token (Index 197) 加入停止偏差 delta_stop，以修正合成/真實資料的數量分佈偏斜
    fused_logits[:, 197] = logits_199[:, 197] + delta_stop
    
    # 3. 保持 START (Index 196) 與 PAD (Index 198) 不變
    return fused_logits # 輸出 [Batch_size, 199]
```

---

### 5.3 帶約束的束搜索演算法：重複技能遮罩與長度懲罰機制

得到融合後的 $\tilde{\boldsymbol{\ell}}_t \in \mathbb{R}^{199}$ 後，系統將其送入 **Softmax** 並執行**束寬度 $W=4$** 且帶有物理約束的束搜索（Constrained Beam Search）：

#### A. 重複技能遮罩（Duplicate-Skill $-\infty$ Masking）
在真實世界任務中，Agent 通常不需要重複載入同一個技能。因此，在解碼的第 $t$ 步，對於任何已經出現在目前路徑歷史 $\mathcal{Z}_{<t}$ 中的技能 ID $i$，系統會在進行 Softmax 之前，將其 Fused Logit 強制設為負無窮大：
$$ \tilde{\ell}_t(i) = -\infty \quad \forall i \in \mathcal{Z}_{<t} $$
這在數學上 100% 確保了在 Softmax 轉換後，已被選擇過的技能其機率降為 0，防止模型陷入無意義的自循環。

#### B. 序列長度懲罰與基於 Cardinality Head 的截斷
對於一條長度為 $T$（不含 START/STOP）的候選序列 $\mathbf{z}$，其評估得分會使用長度懲罰因子 $\gamma = 0.7$ 進行平滑：
$$ \text{Score}(\mathbf{z}) = \frac{\sum_{\tau=1}^{T} \log P(z_\tau \mid \mathbf{z}_{<\tau})}{T^{0.7}} $$

此外，數量預測頭輸出的 $n$ 會作為**硬限制（Hard-clip）**。一旦解碼步數達到預測上限 $n$，演算法會在第 $n+1$ 步強制封鎖除了 `STOP` 之外的所有 Token，強迫序列進入終止狀態。

---

### 5.4 超參數優化：驗證集座標上升法與停止偏差（$\delta_{stop}$）的調校

融合公式中的三個核心參數：檢索權重 $\alpha$、集合權重 $\beta$、以及停止偏差 $\delta_{stop}$，都不是透過反向傳播學習的。

由於**合成訓練資料**與**真實人類任務**在所需技能數量上存在分佈偏斜（Cardinality Skew），自迴歸模型在真實測試集上往往會面臨過早預測 `STOP` 的問題。

為了解決這個偏差，作者在驗證集（Validation Set）上使用**座標上升法（Coordinate Ascent）**進行网格尋優（對應 **Figure 5 (Part a)**）：
1.  **固定 $\beta$ 與 $\delta_{stop}$**，調整 $\alpha$ 使得驗證集上的 Set F1 分數最高。
2.  **固定 $\alpha$ 與 $\delta_{stop}$**，調整 $\beta$ 使其最佳化。
3.  **調整 $\delta_{stop}$（停止偏差）**：一個加在 `STOP` Token 上的常數偏置，用來吸收（absorb）合成與真實數據間的長度偏斜。
4.  重複上述步驟直到收斂。最終確定的最佳推論參數為：
    $$ \alpha = 1.0, \quad \beta = 0.5 \quad (\text{對應 Section 4.4 實務設定}) $$

以下為你撰寫筆記第六章的完整內容，本章節將以極致細緻且具備高度工程實用性的視角，拆解 `SkillComposer` 在資料工程上的「煉金術」，包含技能相依圖的建構、多層次 LLM 合成方法，以及包含手算範例的三層去重過濾流水線：

---

## ## Chapter 6: 訓練資料的煉金術：資料工程流水線

如果沒有高品質且結構多元的「任務-技能序列」對齊資料，任何精巧的模型設計都難以發揮實用價值。`SkillComposer` 透過建立技能相依圖、多層次的大模型（LLM）合成以及嚴格的三層去重過濾，設計了一套高度自動化且穩健的資料工程流水線。

---

### 6.1 相依圖設計：資料流相依（Dependency Edges）與工作流共現（Workflow Edges）

為了解鎖多技能組合的真實邏輯，作者並非讓大模型隨意拼接技能，而是基於 196 個技能（節點）建構了一張包含 **924 條邊** 的技能相依圖（對應 **Table 5**）：

1.  **資料流相依邊（Dependency Edges，共 658 條）**：
    *   *數學定義*：如果上游技能 $s_A$ 的輸出資料類型（Schema/Type）與下游技能 $s_B$ 的輸入資料類型存在交集，則建立一條有向邊 $s_A \to s_B$。
    *   *例如*：`s184: usgs-data-download` 會輸出 CSV 資料流，而 `s55: flood-detection` 需要讀入 CSV。
2.  **工作流共現邊（Workflow Edges，共 266 條）**：
    *   *定義*：這兩個技能在真實 Agent 的執行軌跡中經常先後共現，雖然沒有直接的資料型別重合，但存在經驗上的邏輯順序（如 `compile-code` 之後通常會接 `run-test`）。

#### 採樣機制（Sampling Strategy）：
在生成多技能任務時，系統會從此圖中隨機採樣長度為 2~5 的技能鏈。其中 **$65\%$ 的邊採樣自資料流相依邊，$35\%$ 來自工作流共現邊**。這個比例能夠精準模擬真實軟體工程與自動化任務中，硬性資料流與軟性工作流交織的分布特性。

---

### 6.2 多層次大模型合成：單技能對齊與多技能依賴約束 Prompts

作者組裝了共 **9,872 筆** 訓練資料，並採用「分層（Layered）」思想，使用不同規格的大模型進行合成（對應 Section 5.1）：

#### A. 真實任務錨點（Real Anchors, 65 筆）
*   來自 SkillsBench 的 65 個真實人類軟體工程任務。這是最珍貴的種子，其順序自真實 Agent 執行日誌提取，做為系統優化的黃金上限。

#### B. 單技能校準資料（Single-skill Synthetic, 2,880 筆）
*   *合成工具*：Gemini 2.5 Flash
*   *目的*：訓練模型**「在單一任務結束後立即預測 `STOP`（學會適時終止）」**。
*   *Prompt 約束（Figure 6）*：規定大模型在寫任務描述時，**絕對不能提及技能名稱**（例如 HR 技能 `query_leave` 的 Prompt 裡不能有 "query leave" 字眼），迫使模型只能透過用戶的日常口吻與業務語意進行對齊。

#### C. 多技能組合資料（Multi-skill Synthetic, 6,927 筆）
*   *合成工具*：Gemini 2.5 Pro
*   *運作方式*：從相依圖中隨機採樣 2 到 5 個相連技能，若技能間存在資料流相依有向邊，Prompt 會強制注入硬性約束（例如：`"sA" MUST come before "sB"`）。
*   *Prompt 約束（Figure 7）*：要求大模型設計一個必須同時動用這 2~5 個技能才能解決的複合任務，並輸出大模型自己建議的執行順序與合理解釋（Rationale）。

---

### 6.3 三層過濾去重與格式驗證機制

合成資料極易產生高度雷同的「語意垃圾（Semantic Clutter）」。系統在 **Appendix B.3** 中設計了三層遞進、由淺入深的漏斗式過濾架構（Funnel Filter）：

1.  **第一層：精確字串匹配（Exact String Match）**：直接過濾掉字面上 100% 一模一樣的任務描述。
2.  **第二層：字元三元組傑卡德相似度（Character-trigram Jaccard Similarity）**：
    *   *過濾門檻*：$> 0.6$。目的在於過濾掉換句話說（Paraphrasing）或僅微調標點符號的近乎重複件。
3.  **第三層：語意向量相似度（Sentence Embedding Cosine Similarity）**：
    *   *過濾門檻*：$> 0.92$。使用 Qwen3-Embedding 計算向量餘弦夾角，徹底拔除語意極度接近的重複資料。
4.  **格式與語法校驗**：任何大模型回傳的 JSON 裡，只要多加、漏掉、或是拼錯任何技能 ID，或者沒有遵守相依圖的有向邊約束，該筆資料直接被無情丟棄。

---

### 6.4 深入實例計算：字元三元組傑卡德相似度（Trigram Jaccard）手算步驟與漏斗過濾原理

為了直觀理解第二層過濾如何不透過神經網路，就能精準且高速地幹掉「近乎重複的文本」，我們來進行一次手算演示：

#### 📝 手算範例：
*   **字串 $S_1$** = `"ai agent"` (長度 8)
*   **字串 $S_2$** = `"ai agents"` (長度 9，僅多了一個複數 `s`)

#### 步驟一：前處理
轉為小寫，並保留空白字元。
*   $S_1 = \text{"ai agent"}$
*   $S_2 = \text{"ai agents"}$

#### 步驟二：提取字元三元組（Character-trigram）
我們用長度為 3 的滑動窗口，在字串上逐字滑動切片：
*   **對於 $S_1$ ("ai agent")**，切出的三元組集合 $A$ 為：
    $$ A = \text{\{"ai ", "i a", " ag", "age", "gen", "ent"\}} \quad (\text{大小 } |A| = 6) $$
*   **對於 $S_2$ ("ai agents")**，切出的三元組集合 $B$ 為：
    $$ B = \text{\{"ai ", "i a", " ag", "age", "gen", "ent", "nts"\}} \quad (\text{大小 } |B| = 7) $$

#### 步驟三：求交集（$A \cap B$）與聯集（$A \cup B$）
*   **交集**（兩個集合共同拥有的元素）：
    $$ A \cap B = \text{\{"ai ", "i a", " ag", "age", "gen", "ent"\}} \quad \implies \quad |A \cap B| = 6 $$
*   **聯集**（兩個集合合併去重後的總元素）：
    $$ A \cup B = \text{\{"ai ", "i a", " ag", "age", "gen", "ent", "nts"\}} \quad \implies \quad |A \cup B| = 7 $$

#### 步驟四：計算傑卡德相似度
$$ J(A, B) = \frac{|A \cap B|}{|A \cup B|} = \frac{6}{7} \approx \mathbf{0.857} \quad (85.7\%) $$

由於 $0.857 > 0.6$，這兩筆資料被系統判定為「極度雷同的複製品」，因此其中一筆會被直接刪除。

#### 💡 工程實務直覺：
字元級 Trigram Jaccard 僅需對字串進行雜湊（Hash）匹配，其運算複雜度極低。將其放在第二層，可以在進入昂貴、緩慢的第三層 Embedding 餘弦相似度（需要跑 0.6B 神經網路推理）之前，**先濾掉 80% 以上的字面雷同垃圾**。這是一個在資料工程中兼顧「運算吞吐量（Throughput）」與「資料多樣性（Diversity）」的標準漏斗式設計。

以下為你撰寫筆記第七章的完整內容，本章節將以高度量化的數據指標與嚴謹的學術視角，拆解 `SkillComposer` 在預測品質、下游 Agent 實測、先驗消融以及柏拉圖最優前沿（Pareto Frontier）上的關鍵實驗結果與底層洞察：

---

## ## Chapter 7: 關鍵實驗、消融分析與學術洞察

本章將透過論文中的核心實驗數據，客觀評估 `SkillComposer` 在預測品質、下游任務通過率以及算力成本上的表現，並剖析這些實驗背後的技術本質。

---

### 7.1 跨域泛化能力測試：為什麼標準 SFT 崩盤而 SkillComposer 能優雅落地？

在預測品質評估中，作者對比了模型在「同分佈合成測試集」與「跨域真實任務留出集」上的表現（對應 **Table 1**）：

#### 📊 核心數據（Set F1 指標）：
*   **同分佈合成測試（Synthetic test）**：
    *   全參數微調的 `SFT Qwen3-0.6B-Base` 拿到 **$71.1\%$**。
    *   `SkillComposer` 拿到 **$73.9\%$**（在參數少 154 倍的情況下仍略勝一籌）。
*   **跨域真實任務測試（Real-task holdout）**：
    *   SFT 模型發生災難性崩潰，分數暴跌至 **$43.6\%$**（**跌幅高達 -27.5 pp**）。
    *   `SkillComposer` 展現出極佳的抗偏移能力，僅輕微下滑至 **$62.9\%$**（**跌幅僅 -11.0 pp**），依然擊敗了 frontier API 級別的 `LLM-judge`（$59.9\%$）。

#### 💡 學術洞察：
標準 SFT（全參數微調）在訓練時，會將解碼器的注意力權重強力綁定在合成資料的特定語句模板與關鍵字排列上（過度擬合）。一旦面對真實人類寫法、未曾見過的任務描述時，其自迴歸預測便會失準。

相反地，`SkillComposer` 的 **Task Encoder 保持完全凍結**，語意空間由強大的 `Qwen3-Embedding` 預訓練權重保障。小解碼器無法在微調時去「扭曲」這個語意空間，被迫只能學會通用的「語意對齊邏輯」。這證明了**「凍結通用骨幹 + 輕量級特化解碼 + 推論先驗融合」**在跨域泛化任務中具有壓倒性的工程優勢。

---

### 7.2 下游編碼 Agent 實測：少即是多與注意力稀釋的量化證明

為了解鎖更好的技能計畫是否能真正轉化為下游 Agent 的成功率，作者在 SkillsBench 的 75 個編碼任務上，測試了 GPT-5.2-Codex 和 Gemini-3-Pro-Preview（對應 **Table 2**）：

#### 📊 核心數據：
1.  **GPT-5.2-Codex 任務通過率（Pass %）與平均輸入 Token 消耗**：
    *   *No Skills（不給技能）*：通過率 **$22.2\%$**，消耗 0.94M tokens。
    *   *All Skills（196個技能全塞）*：通過率僅提升至 **$29.3\%$**，但消耗膨脹至 **1.27M** tokens。
    *   *Retrieval top-3（前3名檢索）*：通過率 $44.0\%$，消耗 1.09M tokens。
    *   *`SkillComposer`（預測組合）*：通過率飆升至 **$45.3\%$**（**相較於無技能提升了 +23.1 pp**），且消耗僅 **1.03M** tokens。
2.  **Gemini-3-Pro-Preview 通過率**：
    *   從 $25.8\%$（No Skills）提升至 **$44.0\%$**（**提升了 +18.2 pp**）。

#### 💡 工程啟示：
*   **「Context-Flooding（上下文淹沒）」的代價**：直接把整個技能庫丟進 Prompt（All Skills），不僅會導致企業帳單暴增（1.27M tokens），更會因為 LLM 在 Self-Attention 中將注意力均勻分散到無效資訊上，導致推理精度急劇下滑。
*   **「前置 Composer」的必要性**：`SkillComposer` 透過輸出精準、無冗餘且排好順序的技能鏈，不僅以最少的 Token 成本（1.03M）達成了最高的通過率，更成功逼近了人類專家標註的 Gold Skills 上限（$51.1\%$ / $48.4\%$）。這證明在多工具/多技能的 Agent 架構中，配置一個專門的小型「前置規劃器」是降低營運成本並提升精準度的關鍵。

---

### 7.3 檢索先驗消融：為什麼 TF-IDF Cosine 在微觀檢索中完勝 BM25 與 Dense Embedding？

在推論階段的 Logit Fusion 中，作者對不同的解碼期先驗（Decode-time Prior）進行了消融實驗（對應 **Table 4**）：

#### 📊 核心數據（Set F1 指標）：
*   **No Prior（不加任何檢索先驗）**：$67.5\%$
*   **Qwen3-Embedding（稠密向量檢索）**：$68.8\%$（僅提升 1.3 pp）
*   **BM25（改良版檢索）**：$70.0\%$
*   **`TF-IDF Cosine`（傳統稀疏檢索）**：$\mathbf{73.9\%}$（**大幅提升 6.4 pp**）

#### 💡 數學與物理本質洞察：
為什麼理論上更完美的 BM25 與向量檢索，在此處反而輸給了最古老的 TF-IDF？
1.  **文件長度一致性**：技能 Metadata 全都是 10~20 字的單一極短句子。BM25 的「文件長度歸一化（$b$ 參數）」在這種高度均勻的資料庫中，無法提供正面效益，反而引入了長度計算的數學微擾（Noise）。
2.  **無詞頻飽和問題**：在極短描述中，特定的專業詞彙（如 `NWS`, `USGS`）只會出現 1 次。BM25 用於防止詞頻洗板的「TF 飽和度曲線（$k_1$ 參數）」在 $TF=1$ 的情況下完全失效。
3.  **邊界對齊**：TF-IDF 的 Cosine 相似度輸出嚴格受限於 $[0, 1]$ 之間，具有極佳的幾何邊界，這使得它在乘以 $\alpha=1.0$ 後能極其穩定地融入 Logit 空間。相反地，BM25 分數是無邊界的，隨著語料庫動態波動，極難在對數空間中與解碼 logits 進行穩定的線性疊加。

---

### 7.4 柏拉圖最優前沿：3.9M 小模型擊敗 Frontier 大模型裁判的成本延遲對比

最後，作者評估了 `SkillComposer` 在算力成本、延遲與參數規模上的消融與邊界（對應 **Figure 5** 與 **Table 3**）：

#### 📊 核心數據：
1.  **各組件消融貢獻（Table 3）**：
    *   *僅用自迴歸（AR-only）*：F1 分數為 $69.3\%$。
    *   *去掉推論時的 Set Head 融合（$\beta=0$）*：分數暴跌 **$7.1$ pp**（降至 $65.0\%$）。
    *   *去掉推論時的 TF-IDF 融合（$\alpha=0$）*：分數下跌 **$4.6$ pp**（降至 $67.5\%$）。
2.  **帕累托最優（Pareto Frontier）對比（Figure 5）**：
    *   `SkillComposer` 的可訓練參數僅有 **~3.9M**，相較於 SFT 模型（600M），參數規模縮小了 **154 倍**，訓練算力消耗節省了 **25 倍**。
    *   在**推論延遲（Latency）**上（對應 **Figure 5 (Part c)**），`SkillComposer` 與 SFT 處於同一個毫秒級別（在 A6000 上單步解碼僅需幾毫秒），比基於 API 呼叫、需要讀入全體技能資料的 `LLM-judge` **快了整整兩個數量級（100倍）**。

#### 💡 學術啟示：
這項消融與效能對比，打破了「大模型萬能論」的偏見。實驗證明，在一個「固定且有邊界的技能/工具調度問題」中，透過**「多任務聯合訓練（解開梯度綁定）+ 推論時 Logit 級別的 Late Fusion」**，僅僅 3.9M 的專屬小專家模型，不論在準確度、成本還是延遲上，都能徹底完勝高昂、緩慢且容易分心的通用大模型裁判。這在學術與商業架構設計上，都處於絕對的 Pareto 最優前沿。

## 📌 結論

《Generative Skill Composition for LLM Agents》這篇論文為我們提供了一個極具啟發性的工程範式轉移 [1, 2]。

當學術界與工業界普遍將工具或技能派發視為「RAG 檢索問題」或「大模型推理問題」時，`SkillComposer` 另闢蹊徑，證明了**「將技能組合定義為封閉詞彙表的受約束自迴歸生成問題」**在實務上的優勢 [2]。透過「凍結 Encoder + 3.9M 極小 Decoder + 雙重輔助預測頭」的簡潔架構，輔以推論階段的 Logit 級別貝氏後期融合（Logit Fusion）與重複約束 [2]，該框架成功克服了傳統 SFT 模型的跨域泛化崩潰問題 [3]，也徹底免除了大模型在面對龐大技能庫時的注意力稀釋與高昂成本 [3]。

對於 AI 軟體工程師而言，本篇論文提供了以下三個最具實用性的系統架構實務方針：

1.  **少即是多（Less is More）**：與其用超大的 Context Window 把所有工具或技能說明灌給 Agent，不如在系統前方架設一個專門的小型「序列規劃器（Composer）」。這項設計能直接讓下游 Agent 的任務成功率翻倍，並大幅縮減推論階段的 Token 營運成本 [3]。
2.  **幾何餘弦高於概率排名**：在短文本、長度均勻的 Metadata 檢索中，傳統的 TF-IDF 幾何餘弦相似度在數學上比 BM25 更穩定、比向量檢索更精準，且天然具備 $[0, 1]$ 的數值邊界，是與解碼 Logits 進行 Late Fusion 的首選 [3]。
3.  **封閉詞表與 $-\infty$ 遮罩**：將有限的 API 或技能庫 ID 化，並在束搜索中實施 $-\infty$ 遮罩（Masking），是從底層代碼層面解決 Agent 陷入工具調用死循環與幻覺問題，最穩健且成本最低的工程手段。

本篇論文的實踐表明，在 AI Agent 時代，我們不需要一味地追求更大的參數量與更長的上下文。透過對特定領域問題的「結構化重塑」與優雅的「多任務特化小模型」設計，我們依然能用極低的算力，建立起高精準度、低延遲且高度穩健的工業級 Agent 調度系統 [3]。

