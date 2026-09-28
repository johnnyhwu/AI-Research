# 技能太多反而選不出來：SkillComposer 如何用「造句」邏輯解決 Agent 的工具編排難題

## 前言

當一個 LLM Agent 手上的技能庫從十幾個工具膨脹到兩百個「技能（Skill）」時，真正困難的已經不是單一技能寫得好不好，而是**在任務當下，要選哪幾個、選幾個、照什麼順序執行**。這三個問題彼此綁死，傳統的檢索式方案只能回答「哪些相關」，直接把整包技能塞進 Prompt 又會拖垮成本與準確率。

《Generative Skill Composition for LLM Agents》提出的 `SkillComposer`，把這個組合問題重新定義成「在一個封閉詞表上生成序列」——用一個只有 3.9M 參數的小型自迴歸解碼器，取代動輒 600M 參數的全參數微調模型，卻在準確度、跨域穩定性與推論延遲上全面勝出。這篇筆記會照著論文的邏輯，從問題定義、模型架構、訓練訊號設計、推論演算法，一路講到資料工程與實驗結果，盡量把每一段背後的工程直覺講清楚，而不是只丟公式。

---

## 1. 技能爆炸時代的組合瓶頸

### 1.1 技能不是工具：更粗粒度、沒有型別的知識包

要理解為什麼技能組合會變難，得先搞清楚「技能（Skill）」跟一般的工具呼叫（Tool/API Call）本質上不一樣。論文的 **Definition 3.1** 把每個技能 $s_i$ 定義成一個五元組：

$$ s_i = (m_i, C_i, \pi_i, T_i, R_i) $$

其中 $m_i$ 是名稱與一句話描述（Metadata），$C_i$ 是適用條件，$\pi_i$ 是實際指引大模型逐步執行的程序策略，$T_i$ 是終止條件，$R_i$ 則是輔助資源，例如一支 Python 腳本或一個 REST API 端點。

一般工具呼叫（像計算機、單一 SQL 查詢）通常是型別明確、單步驟完成的。技能則相反：它涵蓋多個執行步驟，而且**沒有硬性的程式型別約束**。這代表技能之間的依賴關係是隱性的、藏在任務邏輯裡的，傳統靠型別比對來自動規劃的 API planner，在這種場景下根本用不上力。

### 1.2 兩種傳統方案，兩種失敗

當技能庫規模衝到論文設定的 $K = 196$ 之後，兩種常見的因應方式都會撞牆。

第一種是**扁平無序檢索（Flat Retrieval）**：用 Embedding 相似度或 LLM-as-a-judge，把技能跟任務逐一比對，回傳一個候選子集。問題在於這個子集是無序的，而真實任務常常有嚴格的先後關係——像是「先下載 USGS 水位資料，才能比對閾值，最後才能判斷是否洪水」。檢索完全無法回答「要選幾個」跟「先後順序」。

第二種是**直接把整個技能庫塞進 Prompt**（All Skills），讓模型自己在執行時挑。這種做法會造成嚴重的「上下文淹沒（Context-Flooding）」：Token 消耗暴增，LLM 的注意力被稀釋到一堆無關資訊上，任務成功率不升反降（後面第 7.2 節的實測數字會很明顯地展示這件事）。

![SkillComposer 論文的總覽圖，分成三個部分：大型技能庫造成的選擇瓶頸、SkillComposer 與既有方案的架構對比，以及提升下游任務成功率的結果摘要。](img-001)
*圖 1 — SkillComposer 總覽：問題、方法與結果一次看完。（來源：原始論文 Figure 1）*

### 1.3 三個綁死在一起的決策

一個真正堪用的技能計畫，必須同時解決三個高度耦合的維度：**選哪些**（挑出跟任務相關的子集）、**選多少**（動態決定數量，適時終止）、**什麼順序**（照任務邏輯依序排列）。這三件事沒辦法分開處理——選了哪些技能會影響該選幾個，順序又反過來限制了哪些技能現在能選。

![一個具體範例，展示模型如何從技能庫中挑出正確的技能組合與順序來完成防洪相關任務。](img-002)
*圖 2 — 給定任務與環境，模型從技能庫中選出有序技能序列的實際範例。（來源：原始論文 Figure 2）*

以圖 2 這個例子來說：任務是「找出 2025 年 4 月 1 日到 7 日間曾經淹水的密西根 USGS 測站」，模型讀完任務描述跟環境資訊（一個本地的測站清單檔案）之後，直接輸出索引序列 `(104, 184, 55)`，對應到 `nws-flood-thresholds → usgs-data-download → flood-detection` 這條有先後邏輯的技能鏈。子集、數量、順序，在這一次解碼裡一起決定。

---

## 2. 把「組合」重新定義為「在封閉詞表上造句」

### 2.1 封閉詞彙表與 ID 化

`SkillComposer` 解決耦合問題的方式很直接：既然推論階段技能庫 $\mathcal{S}$ 的大小 $K$ 是固定的，那就把 196 個技能直接編號成整數 $\{1, 2, \dots, K\}$，再加上 `STOP`、`START`、`PAD` 三個特殊符號，組成一個極小的封閉詞彙表：

$$ \mathcal{V} = \{1, 2, \dots, K\} \cup \{\text{STOP}, \text{START}, \text{PAD}\} $$

模型不再需要生成冗長的技能名稱文字，而是直接在這個封閉詞表上「造句」。這個設計在物理上就徹底堵死了大模型憑空捏造技能名稱的幻覺問題——詞表裡沒有的技能，模型根本生成不出來。

### 2.2 漸進式揭露：先讀 metadata，再讀完整策略

為了兼顧成本與準確度，`SkillComposer` 採用漸進式揭露（Progressive Disclosure）：在序列預測階段，模型**只讀取技能的 metadata $m_i$**（名稱加一句話描述），完全不碰完整的程序策略 $\pi_i$。要等整條序列解碼完成（比如生成了 `104 → 184 → 55 → STOP`），系統才會去資料庫撈出這幾個 ID 對應的完整策略內容，塞進下游 Agent 的 Prompt。這個設計大幅壓低了推論階段的 Token 消耗——196 個技能的完整策略文件可能動輒上萬字，但一句話描述通常只有十幾個字。

### 2.3 問題的數學形式

給定任務 $x$、環境 context $c$、固定技能庫 $\mathcal{S}$，模型 $f_\theta$（論文 **Definition 3.2 與 3.3**）要直接預測一個變動長度的技能索引序列：

$$ \hat{\mathbf{z}} = (\hat{z}_1, \hat{z}_2, \dots, \hat{z}_n, \text{STOP}) = f_\theta(x, c, \mathcal{S}) $$

其中每個 $\hat{z}_t \in \{1, \dots, K\}$，模型生成 `STOP` 時序列自動終止。這個形式很優雅的地方在於：子集選擇、數量預測、執行順序，全部在**單次的解碼前向傳播**中自然湧現，不需要額外的後處理或多階段流程。

---

## 3. SkillComposer 的模型架構

`SkillComposer` 本質上是一個經過高度輕量化與特化的 Encoder-Decoder 網路，由三個元件組成：一個凍結的文字編碼器、一個帶輔助預測頭的自迴歸解碼器，以及推論階段的 logit 融合機制。

![SkillComposer 方法架構圖，分成任務與技能庫編碼、自迴歸解碼器搭配輔助預測頭，以及推論階段的 logit 融合三個部分。](img-003)
*圖 3 — SkillComposer 的完整架構：編碼、解碼與推論融合三段式流程。（來源：原始論文 Figure 3）*

### 3.1 凍結的 Task Encoder 與 256 維投影

輸入端要對「用戶任務」、「環境上下文」、「技能 metadata」做語意表徵。骨幹網路 $E_\phi$ 用的是預訓練的 `Qwen3-Embedding-0.6B`，而且**訓練過程中參數 $\phi$ 完全凍結**——這個決定後面在第 7.1 節會看到，是模型能扛住跨域偏移的關鍵。

把序列化後的 Prompt $P(x, c, \mathcal{S})$ 丟進去，取最後一個 token 的 pooled 輸出，得到初始任務特徵 $\mathbf{h}_x \in \mathbb{R}^{1024}$。由於解碼器的工作維度是 $d=256$，系統用一個**可訓練**的線性投影矩陣 $W_{proj} \in \mathbb{R}^{1024 \times 256}$ 把它壓下來：

$$ \mathbf{h} = \mathbf{h}_x \cdot W_{proj} \quad \in \mathbb{R}^{256} $$

這個 $\mathbf{h}$ 就是後面解碼器的前綴條件（Prefix Condition）。

### 3.2 Skill Memory 矩陣

同樣的道理，196 個技能各自的 metadata 也要透過凍結的 $E_\phi$，用另一個獨立的可訓練投影矩陣 $W_m \in \mathbb{R}^{1024 \times 256}$ 編碼：

$$ \mathbf{e}_i = E_\phi(m_i) \cdot W_m \quad \in \mathbb{R}^{256} $$

把 196 個技能的向量堆疊起來，就是靜態的**技能記憶體矩陣**：

$$ \mathbf{M}_{skill} = \begin{bmatrix} \mathbf{e}_1 \\ \mathbf{e}_2 \\ \vdots \\ \mathbf{e}_{196} \end{bmatrix} \quad \in \mathbb{R}^{196 \times 256} $$

這個矩陣在整個推論過程中保持不變，會作為解碼器 Cross-Attention 的 Key 與 Value 來源。

### 3.3 輕量自迴歸解碼器規格

解碼器 $D_\theta$ 是一個很小的 Transformer：3 層 pre-norm、隱藏維度 $d=256$、4 個注意力頭。詞表空間是 196 個真實技能 ID 加上 3 個特殊 token（START、STOP、PAD），總共 199 維，所以頂部 LM Head 輸出的是 $\mathbb{R}^{199}$。

### 3.4 Decoder 內部：Masked Self-Attention 與 Cross-Attention 如何交錯

每一層解碼器內部拆成三個子層依序運作，這是整個架構裡最值得細看的部分。

#### 子層一：Masked Self-Attention

模型要在第 $t$ 步同時考慮「任務目標（前綴 $\mathbf{h}$）」跟「已經選過的技能歷史」，所以 embedding 查表後會拼接成：

$$ \mathbf{X}_{in\_seq} = [\mathbf{h}, E(\text{START}), E(z_1), \dots, E(z_{t-1})] \quad \in \mathbb{R}^{(t+1) \times 256} $$

Self-Attention 的 $Q, K, V$ 都來自這個序列，並用下三角遮罩（Causal Mask）擋住未來資訊。物理意義是：序列最後一個位置的輸出 $\mathbf{h}_{self} \in \mathbb{R}^{256}$，會吸收前面所有歷史軌跡與任務前綴，代表「在任務 $\mathbf{h}$ 的約束下、執行完目前技能序列後的當下系統狀態」。

#### 子層二：Cross-Attention

這是模型「翻找技能庫」的核心運算。Query 來自剛剛的狀態向量：

$$ Q = \mathbf{h}_{self} \cdot W_Q \quad \in \mathbb{R}^{1 \times 256} $$

Key 跟 Value 則來自靜態的技能記憶體：

$$ K = \mathbf{M}_{skill} \cdot W_K \quad \in \mathbb{R}^{196 \times 256}, \qquad V = \mathbf{M}_{skill} \cdot W_V \quad \in \mathbb{R}^{196 \times 256} $$

查詢跟 196 個技能描述的內積，除以縮放因子 $\sqrt{d_k}$（其中 $d_k = 256 / 4 = 64$）：

$$ \text{Scores} = \frac{Q \cdot K^T}{\sqrt{d_k}} \quad \in \mathbb{R}^{1 \times 196}, \qquad A = \text{Softmax}(\text{Scores}) \quad \in \mathbb{R}^{1 \times 196} $$

再用權重加總 $V$，得到技能庫的加權特徵：

$$ \text{Context}_{skill} = A \cdot V \quad \in \mathbb{R}^{1 \times 256} $$

這一步的優雅之處在於：模型是在**語意空間**裡找跟目前上下文狀態最接近的技能描述，而不是盲目地去猜一個抽象的 ID 數字。

#### 子層三：Feed-Forward

最後經過殘差連接與 LayerNorm，送進兩層線性網路並用 GELU 做非線性轉換：

$$ \mathbf{h}_{out} = \text{LayerNorm}(\text{FFN}(\text{Context}_{skill}) + \mathbf{h}_{self}) \quad \in \mathbb{R}^{256} $$

三層解碼器重複這三個子層之後，頂部 LM Head 把 $\mathbf{h}_{out}$ 投射到 199 維的 logit 向量 $\boldsymbol{\ell}_t \in \mathbb{R}^{199}$，準備進入下一節的推論融合。

---

## 4. 因式分解監督：兩個輔助預測頭

### 4.1 為什麼單靠序列損失，監督訊號會稀釋

自迴歸主幹雖然表達力夠，但單純靠序列生成的損失函數，訓練訊號其實很容易被稀釋。兩個具體的痛點：一是「數量」訊號被隱式埋藏——模型只有在最後一步預測 `STOP` 時才間接接收到長度資訊，訓練早期這個微弱梯度很容易在反向傳播中流失；二是「相關性」訊號跟位置高度綁定——如果技能 C 排在第三步，模型只有前兩步都預測正確，才能有效把「C 跟任務相關」的梯度傳回任務向量 $\mathbf{h}$，一旦前面步驟出錯，C 的正向訊號就被污染了。

`SkillComposer` 的解法是不把所有任務都壓在自迴歸 Decoder 身上，額外外掛兩個專門的輔助預測頭，把監督訊號**因式分解**開來。

### 4.2 Cardinality Head：數量預測為什麼用分類，不用迴歸

數量預測頭只回答一個問題：這個任務需要幾個技能？它直接作用在任務向量 $\mathbf{h}$ 上：

$$ p_\psi(n \mid x, c) = \text{Softmax}(W_n \mathbf{h}) \quad \in \mathbb{R}^8 $$

其中 $W_n \in \mathbb{R}^{8 \times 256}$，訓練用標準交叉熵（Cross-Entropy）。乍看數量預測像是個連續數值問題，但論文選擇分類而不是迴歸（MSE），背後有三個站得住腳的理由。

第一，MSE 隱含假設數值軸連續等距——正確答案是 2、預測成 1 或 3，懲罰完全對等。但在真實 Agent 工作流裡，「該用 1 個技能卻預測成 2 個」跟「該用 7 個卻預測成 8 個」，風險本質完全不同，分類不假設這種度量空間，讓網路可以為每個數量狀態學出各自正交的特徵。

第二，真實任務的技能數量分布通常是偏態的。MSE 為了壓低全局平方誤差，會讓模型出現「均值回歸」，傾向保守地預測中間值；分類（Softmax）則強迫模型在 8 個離散狀態裡明確選邊站，輸出更銳利的機率分布。

第三，分類輸出的 8 維機率分布，能在後面的束搜索裡提供豐富的先驗——系統可以知道「模型對於要用 2 個還是 3 個技能有多猶豫」，而迴歸輸出的一個純量（比如 2.6）完全丟失了這種不確定性資訊。

### 4.3 Set Head：四維特徵拼接的幾何直覺

集合預測頭回答另一個問題：哪些技能相關？它是一個 pairwise 匹配網路，不管順序，只評估任務 $\mathbf{h}$ 跟每個技能 $\mathbf{e}_i$ 的全域語意相關性：

$$ \sigma_i = g_\xi(\mathbf{h}, \mathbf{e}_i) = \text{MLP}_\xi([\mathbf{h} ; \mathbf{e}_i ; \mathbf{h} \odot \mathbf{e}_i ; |\mathbf{h} - \mathbf{e}_i|]) \quad \in \mathbb{R} $$

$\text{MLP}_\xi$ 是一個兩層 MLP，隱藏層 256 維，輸出 1 維（代表 logit），對 196 個技能各自獨立做二元交叉熵（BCE）訓練。

這個拼接借鑒了自然語言推論（NLI）領域的經典特徵工程，拼接後維度是 $256 \times 4 = 1024$，四個組成部分各自有明確的物理意義：

- $\mathbf{h}$（任務特徵）：保留原始任務特徵，提供全域背景。
- $\mathbf{e}_i$（技能身分）：保留技能自身的嵌入，讓網路知道現在在評估哪個技能。
- $\mathbf{h} \odot \mathbf{e}_i$（Hadamard 積，逐維相乘）：如果任務跟技能在某個語意維度上同時被強烈激活，相乘結果會被放大，提供最直接的「共現與相似度」訊號。
- $|\mathbf{h} - \mathbf{e}_i|$（逐維絕對差值）：像是曼哈頓距離，主動凸顯兩者的「衝突與不匹配」——差值越大，代表這個技能包含了任務根本不需要的操作，MLP 可以據此快速給負分。

說白了，主動幫網路算好 $\odot$ 跟 $|-|$，是不想逼一個只有兩層的小 MLP 自己去「從頭學會乘法跟減法」。這大幅降低了特徵提取的難度，也是 Set Head 能保持輕量又準確的關鍵。

### 4.4 聯合訓練的 loss 權重怎麼分配

訓練時三個任務一起做多工聯合學習，總損失是自迴歸損失加上兩個輔助頭各自帶權重的損失：

$$ \mathcal{L}_{total} = \mathcal{L}_{AR} + \lambda_{set} \cdot \mathcal{L}_{set} + \lambda_{card} \cdot \mathcal{L}_{card} $$

根據論文 **Section 5.1** 的實作細節，Set Head 的權重是 $0.5$，Cardinality Head 的權重是 $0.25$。自迴歸損失本身權重固定為 1，是訓練的絕對主導者，負責讓解碼器學會複雜的步驟順序；兩個輔助損失用較小的權重扮演正則化角色，確保共享的 Encoder 表徵空間不會偏離「數量感知」跟「位置無關相關性」的軌道，也為推論階段的 logit 融合打好底子。

---

## 5. 推論階段：Logit Fusion 與帶約束的束搜索

### 5.1 三方分數在對數空間相加

推論時，`SkillComposer` 會把訓練學到的各項能力，跟無監督的檢索先驗在對數空間重新融合：

$$ \tilde{\ell}_t(i) = \ell_t(i)_{\text{context}} + \alpha \cdot \bar{r}_i + \beta \cdot \sigma_i, \quad i \in \{1, \dots, 196\} $$

$\ell_t(i)_{\text{context}}$ 是 decoder 輸出的動態 logits，決定步驟順序與歷史；$\bar{r}_i$ 是預先算好、經過 min-max 校準的 TF-IDF 餘弦相似度，負責字面關鍵字的長尾救援；$\sigma_i$ 是 Set Head 輸出的靜態 logits，負責全域無順序相關性。

由於 $\log(P) \propto \text{Logit}$，把這三項分數相加，換算回機率空間就等於：

$$ P(\text{Final}) \propto P(\text{Context}) \cdot P(\text{Retrieval})^\alpha \cdot P(\text{Set})^\beta $$

這其實是貝氏後期融合（Bayesian Late Fusion）：把一個原本很難優化的多約束聯合機率問題，轉換成對數空間裡成本極低的線性向量加法。

### 5.2 工程實作：196 維先驗要怎麼塞進 199 維 Logits

實作上有個維度不對齊的小麻煩要解：檢索向量 $\bar{\mathbf{r}}$ 跟 Set Head 輸出 $\boldsymbol{\sigma}$ 的維度都是 `[196]`，但 decoder 的原始 logits $\boldsymbol{\ell}_t$ 是 `[199]`（多了 START、STOP、PAD）。為了不讓先驗分數污染特殊 token 的機率，做法是**選擇性切片**：只對前 196 維（真實技能 ID）疊加先驗，STOP 位置（index 197）另外加一個停止偏差 $\delta_{stop}$，START 跟 PAD 維持不動：

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
    return fused_logits  # 輸出 [Batch_size, 199]
```

這幾行雖然簡單，但把「哪些維度該融合、哪些不該動」講得很清楚，是這種混合先驗系統實作時最容易出錯的地方。

### 5.3 束搜索的兩個約束：重複遮罩與長度懲罰

融合後的 $\tilde{\boldsymbol{\ell}}_t \in \mathbb{R}^{199}$ 送進 Softmax，接著跑束寬度 $W=4$ 的束搜索，並帶兩個物理約束。

第一個是**重複技能遮罩**：真實任務通常不需要重複載入同一個技能，所以在第 $t$ 步，只要某個技能 ID $i$ 已經出現在目前路徑歷史 $\mathcal{Z}_{<t}$ 裡，就在 Softmax 之前把它的 fused logit 強制設為負無窮：

$$ \tilde{\ell}_t(i) = -\infty \quad \forall i \in \mathcal{Z}_{<t} $$

這在數學上 100% 確保已選過的技能機率歸零，避免模型陷入無意義的自我循環。

第二個是**長度懲罰**：對於長度 $T$（不含 START/STOP）的候選序列 $\mathbf{z}$，用懲罰因子 $\gamma = 0.7$ 平滑評分：

$$ \text{Score}(\mathbf{z}) = \frac{\sum_{\tau=1}^{T} \log P(z_\tau \mid \mathbf{z}_{<\tau})}{T^{0.7}} $$

Cardinality Head 輸出的數量 $n$ 還會作為硬限制：一旦解碼步數到達預測上限，第 $n+1$ 步會強制封鎖除了 `STOP` 之外的所有 token，逼序列進入終止狀態。

### 5.4 $\alpha$、$\beta$、$\delta_{stop}$ 是怎麼調出來的

融合公式裡的三個核心參數——檢索權重 $\alpha$、集合權重 $\beta$、停止偏差 $\delta_{stop}$——都不是靠反向傳播學出來的。原因是合成訓練資料跟真實人類任務，在所需技能數量上存在分布偏斜（Cardinality Skew），自迴歸模型在真實測試集上容易過早預測 `STOP`。

作者在驗證集上用**座標上升法（Coordinate Ascent）**做網格尋優，步驟很直觀：

1. 固定 $\beta$ 跟 $\delta_{stop}$，調 $\alpha$ 讓驗證集 Set F1 最高。
2. 固定 $\alpha$ 跟 $\delta_{stop}$，調 $\beta$ 到最佳。
3. 再調 $\delta_{stop}$（一個加在 STOP token 上的常數偏置，用來吸收合成與真實資料間的長度偏斜）。
4. 重複上述步驟直到收斂。

最終選出來的推論參數是 $\alpha = 1.0$、$\beta = 0.5$。後面第 7.4 節會看到，這組參數對應的 F1 曲面是平滑的碗狀，選中的操作點跟鄰近點差距都在 2 個百分點以內，代表這不是脆弱的手調結果。

---

## 6. 資料是怎麼煉出來的

### 6.1 技能相依圖：924 條邊背後的取捨

高品質的「任務—技能序列」對齊資料，是整套系統能跑起來的地基。作者沒有讓大模型隨意拼接技能，而是先基於 196 個技能節點，建構一張技能相依圖。

![技能相依圖的邊型別統計表，列出資料流相依邊與工作流共現邊的數量與加總。](img-010)
*表 1 — 用來取樣多技能任務的技能相依圖，依邊的型別統計條數。（來源：原始論文 Table 5）*

這張圖總共有 924 條邊，分兩種類型：**資料流相依邊**（658 條）是如果上游技能 $s_A$ 的輸出資料型別跟下游技能 $s_B$ 的輸入型別有交集，就建一條有向邊 $s_A \to s_B$，例如 `usgs-data-download` 輸出 CSV，`flood-detection` 需要讀入 CSV；**工作流共現邊**（266 條）則是兩個技能在真實 Agent 執行軌跡裡經常先後出現，雖然沒有直接的資料型別重疊，但存在經驗上的邏輯順序，像是 `compile-code` 之後通常接 `run-test`。

生成多技能任務時，系統從這張圖隨機取樣長度 2 到 5 的技能鏈，其中 65% 的邊取自資料流相依邊，35% 取自工作流共現邊。這個比例是為了模擬真實軟體工程任務裡「硬性資料流」跟「軟性工作流」交織的分布特性——不能全靠資料型別硬邏輯，也不能全靠經驗式的共現統計。

### 6.2 分層 LLM 合成：9,872 筆資料的組成

作者總共組裝了 9,872 筆訓練資料，用「分層」思路，依資料類型指派不同規格的模型去合成。

**真實任務錨點**（65 筆）來自 SkillsBench 的真人軟體工程任務，順序取自真實 Agent 的執行日誌，是最珍貴的種子，做為系統優化的黃金上限。

**單技能校準資料**（2,880 筆）由 Gemini 2.5 Flash 合成，目的是訓練模型「在單一任務結束後立即預測 STOP」，也就是學會適時終止。

![單技能合成用的 Gemini 2.5 Flash prompt 截圖，規定每次呼叫產生五個任務，並且不能提及技能名稱。](img-011)
*圖 4 — 單技能任務合成用的 prompt 設計。（來源：原始論文 Figure 6）*

這裡有個很刻意的 prompt 約束：規定大模型寫任務描述時**絕對不能提及技能名稱**——比如某個 HR 技能叫 `query_leave`，合成出來的任務描述裡不能出現「query leave」這種字眼，逼模型只能透過使用者的日常口吻跟業務語意去對齊，而不是抄關鍵字。

**多技能組合資料**（6,927 筆）由 Gemini 2.5 Pro 合成，從相依圖隨機取樣 2 到 5 個相連技能，如果技能之間存在資料流相依的有向邊，prompt 會強制注入硬性約束（例如「sA 必須排在 sB 之前」）。

![多技能合成用的 Gemini 2.5 Pro prompt 截圖，展示如何注入相依圖的順序限制。](img-012)
*圖 5 — 多技能任務合成用的 prompt，含相依順序限制注入方式。（來源：原始論文 Figure 7）*

這個 prompt 要求大模型設計一個必須同時動用這 2 到 5 個技能才能解決的複合任務，並且自己輸出建議的執行順序跟理由（Rationale）。

### 6.3 三層去重過濾

合成資料很容易產生高度雷同的「語意垃圾」，作者在 **Appendix B.3** 設計了三層漏斗式的過濾架構，由淺入深：第一層是精確字串比對，直接濾掉字面上百分之百相同的描述；第二層是字元三元組傑卡德相似度，門檻設在 $0.6$，用來抓換句話說或只調過標點的近乎重複件；第三層是語意向量餘弦相似度，門檻設在 $0.92$，用 Qwen3-Embedding 算向量夾角，徹底拔掉語意極度接近的重複資料。除此之外還有一道格式跟語法校驗：只要 JSON 裡多加、漏掉、拼錯任何技能 ID，或者沒遵守相依圖的有向邊約束，這筆資料就會被直接丟棄。

### 6.4 手算一次 Trigram Jaccard，看漏斗怎麼運作

第二層的字元三元組過濾看起來抽象，但其實手算一次就懂。假設有兩個字串：$S_1 = \text{"ai agent"}$（長度 8）跟 $S_2 = \text{"ai agents"}$（長度 9，只多了一個複數 s）。

先統一轉小寫並保留空白，然後用長度為 3 的滑動窗口切出字元三元組。$S_1$ 切出的集合是：

$$ A = \{\text{"ai "}, \text{"i a"}, \text{" ag"}, \text{"age"}, \text{"gen"}, \text{"ent"}\}, \quad |A| = 6 $$

$S_2$ 多了一個字元，切出來多一個三元組：

$$ B = \{\text{"ai "}, \text{"i a"}, \text{" ag"}, \text{"age"}, \text{"gen"}, \text{"ent"}, \text{"nts"}\}, \quad |B| = 7 $$

交集是兩者共同擁有的元素，這裡剛好是 $A$ 的全部六個：$|A \cap B| = 6$；聯集是合併去重後的總數：$|A \cup B| = 7$。傑卡德相似度就是交集除以聯集：

$$ J(A, B) = \frac{|A \cap B|}{|A \cup B|} = \frac{6}{7} \approx 0.857 $$

$0.857$ 大於門檻 $0.6$，這兩筆資料會被判定為極度雷同的複製品，其中一筆直接刪除。

這個演算法只需要字串雜湊比對，運算成本極低，放在第二層剛好卡在「精確字串比對」跟「昂貴的向量餘弦相似度」之間——能在跑最貴的 embedding 推理之前，先濾掉八成以上字面雷同的垃圾。這是資料工程裡兼顧吞吐量跟多樣性的標準漏斗式設計，跟這篇論文本身其實沒有強綁定，換到任何需要大規模合成資料去重的場景都能直接套用。

---

## 7. 實驗結果：這套設計到底值不值得

### 7.1 同分佈打平，跨域完勝：SFT 為什麼會崩盤

先看預測品質。作者比較了同分佈合成測試集跟跨域真實任務留出集上的表現。

![技能預測品質比較表，涵蓋同分佈合成測試與跨域真實任務留出集，列出各方法的 Set F1、Recall@5、MRR、nDCG@5 與 SetEM。](img-005)
*表 2 — 技能預測品質：同分佈合成測試 vs. 跨域真實任務留出集。（來源：原始論文 Table 1）*

在同分佈合成測試上，全參數微調的 `SFT Qwen3-0.6B-Base` 拿到 71.1% Set F1，`SkillComposer` 拿到 73.9%，領先 2.8 個百分點——而且參數量只有對方的六百五十分之一左右。真正拉開差距的是跨域真實任務測試：SFT 模型直接崩潰到 43.6%（掉了 27.5 個百分點），`SkillComposer` 只小幅下滑到 62.9%（掉 11.0 個百分點），還贏過 frontier API 等級的 LLM-judge（59.9%）。

為什麼會這樣？標準 SFT 在訓練時，會把解碼器的注意力強力綁定在合成資料特有的語句模板跟關鍵字排列上，一旦碰到真人寫法、沒看過的任務描述，預測就會失準。`SkillComposer` 的 Task Encoder 是完全凍結的，語意空間由預訓練的 Qwen3-Embedding 權重保障，小小的解碼器沒辦法在微調過程中去扭曲這個語意空間，被迫只能學到通用的語意對齊邏輯。凍結骨幹加輕量特化解碼，在跨域泛化上有壓倒性的優勢。

### 7.2 下游 Agent 實測：少即是多

技能預測準不準，最終還是要看能不能轉化成下游任務的成功率。作者在 SkillsBench 的 75 個編碼任務上，用 GPT-5.2-Codex 跟 Gemini-3-Pro-Preview 兩個 production 等級的 coding agent 做實測。

![下游任務通過率與平均輸入 token 數的比較表，涵蓋 GPT-5.2-Codex 與 Gemini-3-Pro 兩個 agent。](img-006)
*表 3 — 不同技能載入策略對下游 Agent 任務通過率與 token 成本的影響。（來源：原始論文 Table 2）*

GPT-5.2-Codex 這邊，不給任何技能（No Skills）通過率只有 22.2%，消耗 0.94M tokens；把 196 個技能全塞進去（All Skills），通過率只提升到 29.3%，token 消耗卻膨脹到 1.27M；檢索 top-3 能到 44.0%，消耗 1.09M tokens；`SkillComposer` 通過率飆到 45.3%（比不給技能高了 23.1 個百分點），消耗卻只要 1.03M tokens，比 All Skills 還省。Gemini-3-Pro 那邊也是同樣的模式，從 25.8% 提升到 44.0%（+18.2 pp）。

這組數字很直白地印證了「上下文淹沒」的代價：把整個技能庫硬塞進 Prompt，不只帳單暴增，還會因為 self-attention 把注意力均勻分散到一堆無效資訊上，拖累推理精度。`SkillComposer` 用精準、無冗餘且排好順序的技能鏈，以最低的 token 成本拿到最高的通過率，而且已經逼近人類專家標註的 Gold Skills 上限（51.1% / 48.4%）。在多工具的 Agent 架構裡，配一個專門的小型「前置規劃器」，是同時降成本又提準度的關鍵一步。

### 7.3 檢索先驗消融：TF-IDF 為什麼贏 BM25

推論階段的 logit fusion 用了 TF-IDF 作為檢索先驗，作者也做了消融，對比不同先驗的效果。

![解碼期檢索先驗消融表，比較 No Prior、Qwen3-Embedding、BM25 與 TF-IDF 四種先驗的 Set F1。](img-009)
*表 4 — 解碼期檢索先驗消融實驗：TF-IDF 領先其他方法。（來源：原始論文 Table 4）*

不加任何先驗是 67.5%；換成 Qwen3-Embedding 的稠密向量檢索，只提升到 68.8%（+1.3 pp）；BM25 能到 70.0%；而看起來最傳統的 TF-IDF 餘弦相似度，反而拿到 73.9%，大幅領先 6.4 個百分點。

這個結果乍看反直覺——理論上更先進的 BM25 跟向量檢索，為什麼會輸給最古老的 TF-IDF？原因出在技能 metadata 的特性太特殊：

- **文件長度太均勻**：196 個技能的描述全部是 10 到 20 字的短句，長度高度一致。BM25 的文件長度歸一化參數在這種均勻資料庫裡完全發揮不了效果，反而引入計算上的雜訊。
- **沒有詞頻飽和問題**：在這麼短的描述裡，像 `NWS`、`USGS` 這種專業詞彙通常只出現一次。BM25 用來防止詞頻洗版的 TF 飽和度曲線，在詞頻恆等於 1 的情況下等於沒用。
- **數值邊界乾淨**：TF-IDF 的餘弦相似度輸出嚴格落在 $[0, 1]$ 之間，乘上權重 $\alpha=1.0$ 之後能穩定地疊進 log 空間；BM25 的分數則是無邊界的，會隨語料庫動態波動，很難跟解碼 logits 做穩定的線性疊加。

這個發現的實務意義是：先驗要跟主模型的 logit 做線性融合時，先驗本身的數值邊界比它理論上多精緻更重要。

### 7.4 元件消融與 Pareto 前沿

最後看模型各元件的貢獻，以及在算力成本、延遲、參數規模上的整體表現。

![模型元件消融表，比較僅用自迴歸主幹、加上不同輔助頭，以及移除推論期融合項目的 Set F1 差異。](img-008)
*表 5 — 模型元件與推論期融合項目的消融結果。（來源：原始論文 Table 3）*

單用自迴歸主幹（沒有輔助頭）是 69.3%；移除推論時的 Set Head 融合（$\beta=0$），分數暴跌 7.1 個百分點到 65.0%；移除推論時的 TF-IDF 融合（$\alpha=0$），分數下跌 4.6 個百分點到 67.5%。兩個推論期融合項目都是實打實的貢獻，不是錦上添花。

再看整體的成本效益權衡：

![三張並排子圖：(a) α、β 解碼權重網格搜尋的 F1 曲面，(b) 可訓練參數量與準確度的權衡，(c) 推論延遲與準確度的權衡。](img-007)
*圖 6 — 超參數網格、參數量與延遲的三個權衡視角。（來源：原始論文 Figure 5）*

圖 6(a) 就是前面第 5.4 節提到的 $\alpha$、$\beta$ 網格搜尋曲面，平滑碗狀，證明最終選定的操作點不是脆弱的手調結果。圖 6(b) 是可訓練參數量對準確度，`SkillComposer` 只有約 3.9M 可訓練參數，比 SFT 的 600M 少了 154 倍，訓練算力也省了 25 倍，而且落在 Pareto 最優前沿上。圖 6(c) 是推論延遲對準確度，`SkillComposer` 跟 SFT 在同一個延遲量級（A6000 上單步解碼只要幾毫秒），但比需要呼叫 API、讀入全體技能資料的 LLM-judge 快了整整兩個數量級，快了大約 100 倍。

這組消融跟效能對比，打破了「大模型萬能」的直覺。在一個固定且有邊界的技能調度問題裡，透過多任務聯合訓練解開梯度綁定，加上推論時 logit 級別的後期融合，一個 3.9M 的專屬小模型，不管在準確度、成本還是延遲上，都能全面壓過昂貴、緩慢又容易分心的通用大模型裁判。

---

## 結論

`SkillComposer` 給出的核心工程啟示是：當工具或技能派發的問題本身是「固定且有邊界」的，與其把它硬塞進 RAG 檢索或丟給大模型直接推理，不如把它重新定義成一個受任務約束的封閉詞表序列生成問題——用「凍結 Encoder + 極小 Decoder + 雙重輔助預測頭」的簡潔架構，搭配推論階段的 logit 級別貝氏後期融合與重複約束，就能同時解決 SFT 模型的跨域崩潰問題，也免除大模型面對龐大技能庫時的注意力稀釋與高昂成本。

對於正在設計企業內部多工具 Agent 系統的工程師，這篇論文留下三個值得直接複製的實務方針：

1. **少即是多**：與其把所有工具說明塞進超大 context window，不如在系統前方架一個專門的小型序列規劃器。這能直接翻倍下游任務成功率，同時大幅壓低推論階段的 token 成本。
2. **幾何餘弦贏過機率排名**：在短文本、長度均勻的 metadata 檢索場景，TF-IDF 餘弦相似度比 BM25 更穩定、比向量檢索更精準，而且天生具備 $[0,1]$ 的數值邊界，是跟解碼 logits 做後期融合的首選。
3. **封閉詞表配 $-\infty$ 遮罩**：把有限的工具庫 ID 化，並在束搜索裡實施硬性遮罩，是從底層代碼層面阻止 Agent 陷入工具調用死循環的成本最低的工程手段。

不需要一味追求更大的參數量跟更長的上下文——對一個結構清楚的子問題做結構化重塑，搭配一個小而專的模型，一樣能做出高準確度、低延遲、跨域穩健的工業級調度系統。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1: Structured skill composition with SkillComposer. (A) Large skill libraries create a composition bottleneck. To solve complex tasks, an agent must decide not only which skills to use, but also their exact count and execution order. (B) Existing paradigms: directly exposing the agent to all skill options leaves composition implicit within an unstructured execution trace, while retrieval methods only return an unordered subset of candidates. We propose SkillComposer, which explicitly predicts an ordered, executable skill sequence. (C) By structuring the composition process, SkillComposer improves both plan exact match and downstream task success rates on SkillsBench.",
    "why_used": "在第 1.2 節開場說明兩種傳統方案為何失敗，同時預告全文的結果摘要，讓讀者一開始就知道整篇文章要往哪裡走。",
    "agent_match_hint": "三格並排的總覽圖，分別是技能庫規模與瓶頸示意、既有方案與 SkillComposer 的架構比較、以及下游任務成功率的長條圖。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2: Example of selecting an ordered skill sequence from a large skill library given a task and environment.",
    "why_used": "具體呈現第 1.3 節「選哪些、選多少、什麼順序」三個維度如何在同一個例子裡同時被決定，比純文字描述更容易懂。",
    "agent_match_hint": "一個文字方塊範例，列出技能庫片段、任務描述、環境資訊，最後給出預測出的技能索引序列。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 3: SkillComposer method overview. (A) Given a task, environment context, and compact metadata from a fixed skill library, SkillComposer encodes the task–library context and predicts a variable-length ordered sequence of skill indexes. (B) The autoregressive decoder produces contextual skill logits, while auxiliary cardinality and set heads estimate how many",
    "why_used": "作為第 3 章的開場圖，讓讀者在讀進解碼器內部數學細節之前，先看過編碼、解碼、推論融合三段式的整體輪廓。",
    "agent_match_hint": "三格架構圖，分別畫出任務與技能庫的編碼流程、自迴歸解碼器搭配兩個輔助頭、以及推論時的 logit 融合示意。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Table 1: Skill prediction quality (%). Left: in-distribution synthetic test (n=494). Right: real-task holdout (n=65); trained models are retrained on the real-task-removed partition. Best non-oracle result in bold; second best underlined; oracle- cardinality retrievers (in italics) are reported as ceilings and excluded from the ranking.",
    "why_used": "第 7.1 節比較同分佈與跨域表現，這張表是唯一同時列出多種方法在兩個測試集上完整指標的資料來源。",
    "agent_match_hint": "一張數據表，左半部是同分佈合成測試指標，右半部是跨域真實任務留出集指標，列出多種檢索與訓練方法的 Set F1 等分數。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 2: Downstream task performance on SkillsBench. Pass rate follows the paper-binary protocol, Tok. is the average input prompt tokens per non-errored trial. Best non-oracle result in bold; second best underlined.",
    "why_used": "第 7.2 節論證「少即是多」需要具體的通過率與 token 成本數字，這張表把兩個 agent 在不同技能載入策略下的表現並列，最直觀。",
    "agent_match_hint": "一張表，欄位分成 GPT-5.2-Codex 與 Gemini-3-Pro 兩組，各自列出不同技能載入條件下的通過率百分比與平均 token 數。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Table 4: Decode-time retrieval prior ablation.",
    "why_used": "第 7.3 節解釋 TF-IDF 為何贏過 BM25 跟向量檢索，需要這張表列出四種先驗各自的 Set F1 供讀者對照。",
    "agent_match_hint": "一張簡短的表，四列分別是 No prior、BM25、Qwen3-Embedding、TF-IDF，對應各自的 Set F1 分數。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Table 3: Model component ablation.",
    "why_used": "第 7.4 節說明移除 Set Head 融合或 TF-IDF 融合各自造成多少分數下跌，這張表是原始的消融數據來源。",
    "agent_match_hint": "一張表，列出 AR-only、加上各輔助頭、完整 SkillComposer，以及移除推論期融合項目後的 Set F1 分數。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Figure 5: (a) Test Set F1 across the (α, β) decoding-weight grid; the surface is smooth and bowl-shaped around the val- selected operating point. (b) Compute–accuracy frontier on the synthetic test split: SkillComposer w/ Qwen3-Embedding is Pareto-optimal among predicted-k methods, sitting above SFT at ∼154× fewer trainable parameters and ∼25× less training compute. (c) Latency–accuracy frontier (1×A6000, fp16, batch 1): SkillComposer sits in the same latency class as SFT but with higher accuracy.",
    "why_used": "第 7.4 節總結超參數穩健性、參數效率、推論延遲三個面向，這張圖的三個子圖剛好對應這三個論證重點。",
    "agent_match_hint": "三張並排的子圖：左邊是 α、β 網格搜尋的碗狀曲面熱力圖，中間是可訓練參數量對準確度的散佈圖，右邊是推論延遲對準確度的散佈圖。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "Table 5: Skill dependency graph used for grounding multi-skill synthesis.",
    "why_used": "第 6.1 節說明技能相依圖的邊組成時，需要這張表提供資料流相依邊與工作流共現邊各自的實際條數。",
    "agent_match_hint": "一張簡短的表，列出邊的型別（資料流相依、工作流共現）與各自的條數，以及加總的 924 條。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Figure 6: Single-skill synthesis prompt (Gemini 2.5 Flash). Five tasks per call ensure scenario diversity at fixed cost; difficulty is balanced 2/2/1 across easy/medium/hard.",
    "why_used": "第 6.2 節說明單技能合成資料如何避免模型單純背關鍵字，需要實際的 prompt 內容來佐證「不能提及技能名稱」這個約束。",
    "agent_match_hint": "一段 prompt 文字截圖，開頭是任務說明，內容規定每次呼叫產生五個任務，並列出難度與情境多樣性的要求。"
  },
  {
    "id": "img-012",
    "references_manifest_caption": "Figure 7: Multi-skill synthesis prompt (Gemini 2.5 Pro). Ordering constraints from dependency edges are injected verbatim when present; otherwise, Gemini proposes an execution order with rationale.",
    "why_used": "第 6.2 節說明多技能合成如何把相依圖的順序限制注入 prompt，需要實際的 prompt 內容作為依據。",
    "agent_match_hint": "一段 prompt 文字截圖，內容包含多個技能清單、順序限制條件，以及要求輸出執行順序與理由的說明。"
  }
]
```
