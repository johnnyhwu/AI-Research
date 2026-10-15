# ParseBench 論文筆記

> **論文**：ParseBench: A Document Parsing Benchmark for AI Agents
> **出處**：arXiv 2604.08538v3 (cs.CV), 2026-04-13
> **作者單位**：runllama.ai（LlamaIndex / LlamaParse 團隊）

---

## 三十秒版本

這篇論文提出一套**文件解析（document parsing）的評測基準**——也就是評估「把 PDF 轉成結構化文字」這件事做得好不好。它不提出新的解析模型，只提出**新的評分方式**。

- **它的主張**：以前 parser 是給人讀的，現在是給 AI agent 拿去做決策的。標準必須從「看起來像不像」改成「意思對不對」。
- **它最有價值的東西**：`TableRecordMatch` —— 把表格從「格子的排列」重新理解成「以表頭為 key 的一袋記錄」。這是全篇唯一一個新的看事情的方式。
- **它最該打折的東西**：排行榜。這是廠商自家的 benchmark，自己出題、自己訂分、自己拿第一名。
- **結論**：**研究價值低，工程價值高**——但高在「metric 設計思路」，不在「排行榜數字」。值得讀的部分大約佔全文兩成。

**如果只有五分鐘**：跳到本文第 2.2 節（TableRecordMatch）和第 4 節（可帶走的價值）。

---

## 第一部分：這篇論文要解決什麼問題

### 1.1 背景：文件解析的下游消費者換人了

「文件解析」指的是把 PDF、掃描件這類文件，轉換成機器可用的結構化內容（Markdown、HTML 表格、bounding box 等）。

論文的核心觀察是：**這件事的服務對象變了。**

| | 過去 | 現在 |
|---|---|---|
| 目的 | 讓 PDF 可搜尋、給人讀 | 讓 AI agent 拿去自主決策 |
| 文件類型 | 熟悉的固定模板 | 多樣、沒見過的企業文件 |
| 容錯 | 高（人會自己判斷） | 低（沒有人在迴圈裡） |

論文用一句話概括這個轉變：標準從 *"good enough to read"* 變成 *"reliable enough to act on"*。

### 1.2 為什麼這個轉變會讓舊指標失效

因為在 agent 的情境下，**小的解析錯誤會直接變成決策錯誤**。論文舉的例子：

- 表頭錯位 → agent 核賠時抓到錯的數字
- 圖表被壓成純文字 → agent 沒有數字可以計算
- 刪除線被丟掉 → agent 把已作廢的舊價當成現價
- 上標被壓平 → 腳註編號「1」被當成數量

這些錯誤有一個共同點：**文字相似度指標完全看不到**。字幾乎都對，意思全錯了。

論文把「意思要對」這個要求命名為 **semantic correctness（語意正確性）**。這是全篇的核心概念。

### 1.3 論文對既有 benchmark 的兩點批評

**批評一：文件分佈不對。** 既有基準大多是學術論文或乾淨的截圖，不是真正驅動企業自動化的文件。

**批評二：指標不對。** 比的是表面文字相似度，抓不到結構性的失效。

論文用一張表來支撐這兩點：

> **Table 1** — caption: *"Comparison of document parsing benchmarks. Subtask benchmarks evaluate a single capability on a narrow corpus; end-to-end benchmarks target multiple capabilities jointly. ParseBench covers all five capability dimensions on enterprise documents. Scale reflects the primary annotation unit (table/chart images for subtask benchmarks, document pages for end-to-end benchmarks)."*

這張表的註腳最有殺傷力：
- OmniDocBench 只有 **6%** 是企業文件、**62% 是中文**
- olmOCR-Bench 有 **42% 是 arXiv 數學論文**
- DocLayNet 只做 bounding box 偵測，**不做內容抽取**

### 1.4 ParseBench 的答案：五個能力維度

它的解法是：**企業文件（保險、金融、政府）+ 語意指標**，並拆成五個維度。每個維度對應一種會弄壞 production agent workflow 的失效模式。

```
tables       合併儲存格、階層表頭、跨頁接續
charts       把圖表還原成精確的數值點（不是文字描述）
content      漏字、幻覺、閱讀順序
formatting   刪除線、上下標、粗體、超連結
grounding    每個抽出的元素能不能追回頁面上的原始位置
```

第五個（visual grounding）的動機是**稽核**：受監管的流程裡，抽出來的數字必須能指回原文哪一塊。

### 1.5 規模

> **Table 2** — caption: *"ParseBench dataset statistics. The Text dataset serves both the Content Faithfulness and Semantic Formatting dimensions with different evaluation rules. Tables uses GTRM, a continuous metric (no discrete rules)."*

| 資料集 | 頁數 | 文件數 | 規則數 |
|---|---|---|---|
| Tables | 503 | 284 | —（連續指標，無離散規則）|
| Charts | 568 | 99 | 4,864 |
| Text | 507 | 507 | 147,319 |
| Layout | 500 | 321 | 16,325 |
| **合計** | **2,078** | **1,180** | **169,011** |

兩個必須記住的細節：

1. **Content Faithfulness 和 Semantic Formatting 共用同一批 507 頁文件**，只是套不同的規則集。所以「五個維度」實際只有**四份資料集**。
2. **16.9 萬條規則有 87% 集中在 Text 那一份**。宣傳語裡的「169K test rules」主要是文字比對規則**自動展開**出來的量，不是 169K 個獨立設計的考點。

---

## 🔑 關鍵問答（一）：「規則」到底是什麼？它跟評分公式的關係是什麼？

> 這是整篇論文最容易讀不通的地方。因為論文從沒把這條鏈完整畫出來。

### 一條 rule = 一道「是非題」

論文不是拿 parser 的輸出跟正確答案整篇比對，而是**從正確答案自動生出一大堆小測驗**，一題一題判。每題產出 0 到 1 的分數（binary rule 給 0 或 1，percentage rule 給連續值）。

實際的規則長這樣：

```
missing_sentence      這句話有沒有掉？
unexpected_sentence   有沒有多出原文沒有的句子？
present / absent      某片段該在 / 不該在
bag_of_digit_percent  數字的出現頻率分佈對不對？
order rule            片段 A 有沒有出現在片段 B 前面？
is_strikeout          這段字有沒有標成刪除線？
is_not_strikeout      這段字有沒有「被誤加」刪除線？
is_title              這段字有沒有被判成標題？
```

Chart 那邊，**一條 rule 就是一個標註的資料點**：一組 label + 一個數值 + 一個容差。

### 為什麼會有 14.7 萬條：因為多數是自動展開的

最明顯的例子是閱讀順序規則：每份文件會產生 **N_sentences − 1** 條順序規則（每對相鄰句子一條）。再加上字級、句級、數字級各自的 recall / precision / 重複檢查，一頁密集排版的文件就能生出好幾百條。

### 規則與公式的關係：規則是原料，公式是聚合機器

**你在論文裡看到的每一個公式，都只是這條鏈上的某一層。**

以 Content Faithfulness 為例：

```
第 0 層  單條規則
         「這句話掉了嗎？」→ 0 或 1
              ↓  Equation 4：同型別內平均
第 1 層  文件 d 的 missing_sentence 得分
         （500 條漏字規則 → 壓成 1 個數）
              ↓  Equation 5：同 category 內、對「有出現的型別」平均
第 2 層  文件 d 的 text 得分、order 得分
              ↓  Equation 6：加權（text 1.0、order 0.5）
第 3 層  文件 d 的 CFS 分數
              ↓  跨 507 份文件取平均
第 4 層  Content Faithfulness = 89.7（主表那一格）
              ↓  五維未加權平均
第 5 層  Overall = 84.9
```

### 但 Tables 走的是完全不同的路

Tables 那一格的規則數是破折號——因為它用的是**連續指標**：直接拿整張表跟正確答案算一個 0~1 的相似度，不問是非題。

| 維度 | 底層單位 | 聚合方式 |
|---|---|---|
| Tables | 一張表 | 連續相似度 GTRM，直接平均 |
| Charts | 一個抽查資料點 | 通過比例 |
| Content Faithfulness | 一條文字 / 順序規則 | 兩層平均 + 1.0/0.5 加權 |
| Semantic Formatting | 一條格式 / 標題規則 | 調和平均 + 頻率調整加權 |
| Visual Grounding | 一個標註元素 | 三段相乘後取通過率 |

⚠️ **重要推論**：Tables 的分數是「相似度」，Content Faithfulness 的分數是「通過率」，**本質上不是同一種東西**。而 Overall 把五個維度直接未加權平均——這是 Overall 這個數字要打折的理由之一。

---

## 第二部分：這篇論文提出的方法

論文的「方法」是**評分方法**，不是解析方法。它沒有告訴你怎麼把 PDF 解得更好，只告訴你怎麼量測誰解得好。

### 2.1 先理解既有的兩個表格指標：TEDS 與 GriTS

> ⚠️ 這兩個指標的定義，**論文完全沒有解釋**，只給了引用編號。以下是背景補充。

#### 用同一張表當範例

```
Company     Revenue   YoY%
Acme Corp   $4.2B     12%
Beta Inc    $1.8B      8%
```

#### TEDS — Tree Edit Distance based Similarity

**來歷**：出自 PubTabNet 論文（ECCV 2020）。核心工具 **tree edit distance** 來自演算法／資料結構領域（1980 年代的 Zhang-Shasha 演算法），原本用於比對 XML、剖析樹、生物分類樹。在 AI 領域整體不常見，但在表格辨識這個小圈子是標準配備。

**世界觀：表格是一棵樹。**

```
                    table
        ┌─────────────┼─────────────┐
       tr            tr            tr
    ┌───┼───┐     ┌───┼───┐     ┌───┼───┐
   td  td  td    td  td  td    td  td  td
 "Company"       "Acme"         "Beta"
   "Revenue"       "$4.2B"        "$1.8B"
     "YoY%"          "12%"          "8%"
```

**它問的問題**：把預測的樹改成正確的樹，最少要付多少代價？

```
插入一個節點     代價 1
刪除一個節點     代價 1
替換一個節點     標籤不同 → 代價 1
                文字內容不同 → 代價 = 兩段文字的歸一化編輯距離（0~1）

TEDS = 1 - EditDistance / max(節點數_A, 節點數_B)
```

**替換的代價是「文字的編輯距離」——這是理解一切的鑰匙。**

#### GriTS — Grid Table Similarity

**來歷**：微軟 Table Transformer 團隊提出。概念來自序列比對（bioinformatics 比對 DNA 那種 alignment）的二維推廣。動機是 TEDS 只能吃 HTML，而表格辨識模型輸出的常常是「哪個格子佔哪幾行幾列」。

**世界觀：表格是一張矩陣。**

```
        c0          c1         c2
r0   "Company"   "Revenue"   "YoY%"
r1   "Acme"      "$4.2B"     "12%"
r2   "Beta"      "$1.8B"     "8%"
```

**它問的問題**：在兩個矩陣中，找出「**保持行順序、也保持列順序**」的最佳對應關係，然後比對對齊上的每一對格子。

```
正確答案矩陣          預測矩陣
┌───┬───┬───┐        ┌───┬───┬───┬───┐
│ A │ B │ C │        │ A │ X │ B │ C │   ← 預測多插了一欄 X
├───┼───┼───┤   →    ├───┼───┼───┼───┤
│ 1 │ 2 │ 3 │        │ 1 │ Y │ 2 │ 3 │
└───┴───┴───┘        └───┴───┴───┴───┘

對齊結果：A↔A, B↔B, C↔C, 1↔1, 2↔2, 3↔3
          X, Y 沒有對應 → 被罰
```

計分套一個類似 F-score 的公式，分母是兩邊格子數的**和**，所以任何一邊多出來的格子都會稀釋分數。

**注意「保持順序」這個約束**——這正是 GriTS 重罰欄位重排的原因。

*補充（把握度中等，非論文內容）*：GriTS 原論文定義了三個變體（`GriTS_Top` 只比結構、`GriTS_Con` 比內容、`GriTS_Loc` 比座標）。ParseBench 用的應該是內容版，但**論文沒有指明**。另外，二維對齊問題本身是 NP-hard，GriTS 實際用的是近似解法，**分數本身就帶有近似誤差**。

#### 兩者的共同盲點

**它們都把表頭格和資料格一視同仁——對它們來說，表頭只是「另一個格子」。**

沒有「表頭定義了整欄資料的意義」這個概念。

---

### 2.2 TableRecordMatch（TRM）：本篇最有價值的貢獻

#### 核心轉換：表格 → 一袋記錄

TRM 做的第一件事，是把表格從「格子的排列」改看成「**一袋記錄**（bag of records）」。

- **一列 = 一筆記錄（record）**
- 每筆記錄裡，每個值都由它**所在欄的表頭**當 key

```
原表格：
  Company     Revenue   YoY%
  Acme Corp   $4.2B     12%

轉成一筆記錄：
  { Company: "Acme Corp",
    Revenue: "$4.2B",
    YoY%:    "12%" }
```

**「一袋」的意思是無序**——不管列怎麼排、欄怎麼排，袋子裡的內容一樣。這就是 TRM 對欄列順序不敏感的原因。

反過來，**表頭掉了或錯位，每個 key 都變了，整袋記錄全部對不上**——這正是它想要的懲罰。

*來歷補充*：這個概念來自關聯式資料庫（一列 = 一筆有欄位名的記錄，正是 SQL 的世界觀），數學形式則是 Jaccard 相似度的變形。

#### 公式（論文 Equation 1、2）

```
                    Σ_(g,p)∈M  RecordSim(g, p)
TableRecordMatch = ───────────────────────────
                          max(|G|, |P|)


                Σ_k∈K(g)∩K(p)  1[ g[k] = p[k] ]
RecordSim(g,p) = ────────────────────────────────
                        |K(g) ∪ K(p)|
```

| 符號 | 意思 |
|---|---|
| G | 正確答案那一袋記錄 |
| P | parser 預測出來那一袋記錄 |
| M | G 與 P 之間的「最佳配對」 |
| g, p | 被配成一對的兩筆記錄 |
| K(r) | 記錄 r 的 key 集合（它有哪些欄位）|
| r[k] | 記錄 r 在 key k 上的值 |
| 1[...] | 括號內成立算 1，不成立算 0 |
| \|G\|, \|P\| | 各自的記錄筆數 |

**RecordSim 的白話**：分子數「兩邊都有這個欄位、而且值也一樣」的欄位有幾個；分母是「兩邊欄位的**聯集**」。

**為什麼說它是 Jaccard 的變形**：Jaccard 是「交集 / 聯集」，懲罰任何一邊多出來的元素。這裡分母用聯集，效果一樣——只要有一邊多了或少了欄位，分數就被稀釋。差別只在分子不是單純的交集，而是「交集之中值還要相等的部分」。

#### 完整算例

> **Figure 2** — caption: *"Illustration of the TABLERECORDMATCH metric. Predicted records and columns are matched to those in the ground truth. Each matched record is scored by binary cell-level agreement."*

**Ground truth G（3 筆，欄位 = Company / Revenue / YoY%）**

```
g1  Acme Corp   $4.2B   12%
g2  Beta Inc    $1.8B    8%
g3  Gamma Ltd   $3.1B   15%
```

**Prediction P（4 筆，多了一個 Region 欄）**

```
p1  Beta Inc    $1.8B    6%   —
p2  Gamma Ltd   $3.1B   15%   US
p3  Acme Corp   $4.2B   12%   —
p4  Delta Co    $0.9B    5%   —
```

P 有四個問題：列順序被打亂（無所謂）、多了一欄 Region、多了一筆 Delta Co（憑空冒出來）、Beta 的 YoY% 從 8% 錯成 6%。

**逐筆算 RecordSim**（聯集 |K(g) ∪ K(p)| 一律是 4）：

```
g1 ↔ p3   Company✓ Revenue✓ YoY%✓ Region(只有P有)
          = 3 / 4 = 0.75

g2 ↔ p1   Company✓ Revenue✓ YoY%✗ Region(只有P有)
          = 2 / 4 = 0.50

g3 ↔ p2   Company✓ Revenue✓ YoY%✓ Region(只有P有)
          = 3 / 4 = 0.75

p4        配不到任何 g → 分子貢獻 0
```

**代入主公式**：

```
分子 = 0.75 + 0.50 + 0.75 = 2.00
分母 = max(|G|, |P|) = max(3, 4) = 4

TableRecordMatch = 2.00 / 4 = 0.50
```

#### 兩種懲罰是從哪來的

這個例子同時示範了兩種懲罰，**理解它們的來源比記住公式更重要**：

1. **欄位層級的懲罰**——即使 Acme 三個值全對，也只有 0.75，因為分母的**聯集**被 Region 撐大了。
   注意這是**對稱的**：不只罰「多出來的欄位」，也罰「少掉的欄位」。表頭被丟掉（論文最在意的失效模式）走的正是「少了一欄」這條路。
2. **記錄層級的懲罰**——分母用 `max(3,4)=4` 而不是 3，多餘的 Delta Co 白白佔一個位置卻沒有分子貢獻。

論文原文：*"the overall metric averages these per-pair scores over the larger of the two record bags, so unmatched records are also penalized."*

#### ⚠️ 論文沒交代的三個洞

如果要自己實作 TRM，論文給的是**評分哲學，不是可複現的規格**。以下三點論文從頭到尾沒有說明：

1. **配對 M 的目標函數是什麼**——原文只有一句 *"let M be the optimal matching between them"*，之後再無說明。
2. **用什麼演算法求解**——完全沒提。（若是二分圖最大權匹配，標準解是 Hungarian algorithm，O(n³)——這是推論，非論文內容。）
3. **欄位 key 怎麼比對**——Figure 2 的 caption 明說 *"Predicted records **and columns** are matched"*，欄位本身也要先配對。但論文沒說表頭字串是**完全相符**才算同一個 key，還是允許模糊比對（大小寫、空白、`Revenue` vs `Revenue (USD)`）。

**第 3 點實作上最會咬人**：若是嚴格字串相等，parser 只要在表頭多帶一個單位符號，整張表就掛掉。

**這也代表：別人若獨立實作 TRM，不見得能複現論文表格裡的數字。**

---

### 2.3 GTRM：TRM 與 GriTS 的平均

主結果表「Tables」那一欄報的**不是純 TRM，而是 GTRM**（論文 Equation 3）：

```
        GriTS + TableRecordMatch
GTRM = ──────────────────────────
                  2
```

不加權，各 50%。

#### ⚠️ 這裡有一個論證上的矛盾

論文花了整段論證 GriTS / TEDS **不適合**現代生產環境，附錄還給了實例坐實這個批評——**然後把這個它認為會給出 0.998 錯誤高分的指標，以 50% 權重放進最終分數裡。**

論文對這個決定的全部說明只有一句：*"We combine both perspectives into a single score."*
**沒有解釋為什麼要合併、為什麼是 50/50、GriTS 補足了 TRM 的什麼。**

**實務影響**：附錄那個表頭對調的例子，TRM 給 0.480，但 GTRM = (0.998 + 0.480) / 2 ≈ **0.739**。論文最想抓的失效模式，在真正上榜的那個分數裡被稀釋掉一半。

---

### 2.4 附錄的兩個對照例子（本篇最有說服力的部分）

> **Figure 13** — caption: *"Two contrasting predictions where GriTS and TEDS disagree with the table's downstream usefulness. (a) A semantically wrong prediction that GriTS and TEDS round to ≈ 1.0. (b) A semantically equivalent rewrite that GriTS and TEDS heavily penalize. TRM ranks both correctly."*

| 情境 | GriTS | TEDS | TRM |
|---|---|---|---|
| (a) 表頭對調，所有數字掛錯年份 | 0.998 | 0.999 | **0.480** |
| (b) 欄位順序重排，語意完全等價 | 0.740 | 0.716 | **1.000** |

**這兩個例子讓「既有指標有問題」從主張變成事實**，是全篇最值得記住的證據。

#### 為什麼 (a) 可以拿 0.999？

被對調的兩個表頭是 `"Year ended December 31, 2003"` 和 `"Year ended December 31, 2004"`——**28 個字元只差 1 個**。

```
每個替換的代價 = 1/28 ≈ 0.036
兩個一起      ≈ 0.071
那張表約 60~70 個節點

TEDS ≈ 1 - 0.071 / 70 ≈ 0.999
```

*（這個拆解是推算，論文只給了 0.999 這個結果。但它能完美解釋為什麼分數那麼高。）*

**語意上，整張財報每個數字都掛到錯的年份。數學上，這只是 0.07 刀。**

#### 一個誠實的技術細節

論文說 TEDS 預設對 `<th>` 表頭儲存格的內容**根本不比對**，所以他們在算之前先把 `<thead>/<th>` 降級成一般資料格。也就是說「TEDS 0.999」是**已經對 TEDS 有利地調整過**的結果——不調整會更寬鬆。

---

## 🔑 關鍵問答（二）：TRM 什麼時候不可行？

TRM 的整個前提是這一句：**一列 = 一筆記錄，key 來自「上方」的欄表頭。** 前提破了就失效。論文點名兩種：

### 情況一：不連續的表頭列

```
Company     Revenue   YoY%
━━━ North America ━━━      ← 表格中間插入的分區標題列
Acme Corp   $4.2B     12%
Beta Inc    $1.8B      8%
━━━ Europe ━━━             ← 又一個
Gamma Ltd   $3.1B     15%
```

TRM 會把「North America」也當成一筆普通記錄，而 Acme 那筆變成：

```
{ Company: "Acme Corp", Revenue: "$4.2B", YoY%: "12%" }
```

**「它屬於北美」這個資訊完全消失了。** 更糟的是，如果歐洲區有一家公司數字剛好一樣，兩筆記錄會完全無法區分——因為 TRM 是「無序的一袋」，連誰前誰後都不看。

### 情況二：上方與左方同時有表頭

```
                  Q1     Q2     Q3
Revenue          100    110    120
Operating cost    60     65     70
Net               40     45     50
```

`100` 的意思是「**Q1 的 Revenue**」——需要**兩個表頭**才能定義。但 TRM 只認欄表頭，所以會產生：

```
{ (空白key): "Revenue", Q1: "100", Q2: "110", Q3: "120" }
```

`Revenue` 被降級成一個**值**，而不是 key。

**一個諷刺的後果（推論，論文未寫）**：這種表格轉置後語意完全等價，但轉置後 key 集合整組換掉（Q1/Q2/Q3 → Revenue/Cost/Net），TRM 會給接近 0 分。**TRM 最引以為傲的「對排列不敏感」，在這類表格上反而失效。**

### 論文的處理

這些案例經**人工審查**標記，在公開資料集裡註記為 `trm_unsupported`，**對所有 provider 一律改報 GriTS**。

處理方式一致、也算誠實。⚠️ 但**論文沒說這類表格佔多少比例**——所以主表「Tables」那一欄裡，有多少分數其實是純 GriTS 貢獻的，無從得知。

---

### 2.5 Charts：CHARTDATAPOINTMATCH

#### 核心設計：不比整張表，只抽查資料點

論文的理由：標註完整的 ground truth 表格「costly and brittle」——讀圖表本來就有主觀性（一條股價折線，該標日、週、還是月？）。

所以改成：**每張圖標最多 10 個抽查資料點**，每個點包含：

```
labels     要一起出現的標籤（系列名、x 軸類別、圖表標題...）
value      期望的數值
tolerance  容差
```

**指標定義**：成功驗證的資料點比例。沒有公式。

#### 容差怎麼定

| 圖表類型 | 容差 |
|---|---|
| 有明確標數字（例如長條上有標值）| 完全比對 |
| 沒標數字，要用眼睛估 | 相對容差，預設 1% |

實際上容差是**人工在驗證時逐點決定的**。

> **Table 12** — caption: *"Two representative test rules for the OECD chart example (Sweden / Below upper secondary). The wide 0.5 relative tolerance on the Unadjusted rule reflects that the bar is very short (≈3 score points) and difficult to read precisely from the 3D chart; any estimate between 1.5 and 4.5 is accepted."*

| Labels | Value | 相對容差 | 接受區間 |
|---|---|---|---|
| Below upper secondary, Sweden, Adjusted | 10 | 0.1 | [9, 11] |
| Below upper secondary, Sweden, Unadjusted | 3 | 0.5 | [1.5, 4.5] |

算法：`10 - 10×0.1 = 9`，`10 + 10×0.1 = 11`。

#### 驗證流程四步

```
1. Parse           從輸出裡抽出 Markdown / HTML 表格
2. Locate context  用周圍文字（粗體、標題、caption）找到相關的那張表
3. Match values    模糊比對 + 數值正規化，在容差內找到值
4. Verify labels   確認其餘 labels 有正確關聯到該值的行或列
```

**第 3 步的數值正規化很實用**：貨幣符號、k/M/B 後綴、千分位、小數點分隔符都會被吃掉。所以 `$1,234K`、`1234000`、`1.234M` 視為同一個數。

#### 這個設計聰明在哪

**它對輸出表格的格式完全不敏感。** 附錄用一個 OECD 3D 長條圖示範，四個 provider 輸出的表格結構完全不同（橫式、縱式、Markdown、HTML），但評分不受影響——它只找「label 和 value 有沒有共同出現」。

#### ⚠️ 兩個要打折的地方

1. **容差是人工逐點決定的**，論文只給了兩個範例，沒有公布整體容差分佈。容差鬆緊直接決定分數，這是一個**沒有被量化揭露的自由度**。
2. **抽查 10 點 ≠ 整張圖對**。一張有 40 個資料點的圖，抽 10 點全對只代表這 10 點對。論文對此沒有討論。

---

### 2.6 Content Faithfulness：兩層平均

論文說這是「最基礎、最 table-stakes」的維度——漏字、幻覺、順序錯，agent 的整個上下文就髒了。

#### 規則分兩大類

**text correctness（文字正確性）**：`missing_sentence`（漏字）、`unexpected_sentence`（幻覺）、`present / absent`、`bag_of_digit_percent`。

**reading order（閱讀順序）**：每條規則指定兩個文字片段 `before` 和 `after`，通過條件是：

```
before 的「第一次」出現  必須早於  after 的「最後一次」出現
```

**為什麼是 first / last 而不是 first / first？** 論文解釋：某些片段會重複出現（例如標題也出現在目錄裡）。用寬鬆的判準，才不會因為這種「parser 管不到的重複」而誤判正文順序錯誤。

#### 兩層平均：為什麼需要它

**要解決的問題**：一份密集排版的文件可能有 500 條 `missing_sentence`，但只有 3 條 `unexpected_sentence`。全部丟進去平均的話，**「漏字」會完全淹沒「幻覺」**。

**第一層（Equation 4）**——同一型別內部平均：

```
s_(d,t) = (1/|R_(d,t)|) · Σ_(r∈R_(d,t)) score(r)
```

| 符號 | 意思 |
|---|---|
| d | 某一份文件 |
| t | 某一種規則型別（如 missing_sentence）|
| R_(d,t) | 文件 d 中型別 t 的所有規則結果 |
| score(r) | 單條規則的分數，落在 [0,1] |

**第二層（Equation 5）**——同一 category 內，只對「有出現的型別」平均：

```
S_(d,C) = (1/|{t∈C : R_(d,t) ≠ ∅}|) · Σ_(t∈C, R_(d,t)≠∅) s_(d,t)
```

分母只數**這份文件裡實際有規則的型別**——沒出現的型別不會拉低分數。

**效果**：500 條漏字規則先自己壓縮成 1 個分數，3 條幻覺規則也壓縮成 1 個分數，然後這兩個分數**等權**。
**數量不再等於話語權。**

#### 合成總分（Equation 6）

```
          w_text · S_(d,text)  +  w_order · S_(d,order)
CFS_d = ────────────────────────────────────────────────
                     Σ_(C∈P_d)  w_C

其中  w_text = 1.0,  w_order = 0.5
```

`P_d` 是「這份文件實際有規則的 category 集合」，分母只加總有出現的那些權重。

**為什麼 order 只給 0.5**：論文說 text correctness 是更關鍵的失效模式。⚠️ 但這個比例**沒有任何依據或敏感度分析**。

#### 完整算例

用附錄實例的分數：

```
S_text  = 0.949
S_order = 1.000

CFS = (1.0×0.949 + 0.5×1.000) / (1.0 + 0.5)
    = 1.449 / 1.5
    = 0.966
```

再看一個對照，就能看出拆子分數的價值：

```
某模型  S_text = 0.876   ← 字幾乎都抓對了
        S_order = 0.225  ← 但欄位順序全亂

CFS = (0.876 + 0.1125) / 1.5 = 0.659
```

> **Table 14** — caption: *"Per-provider Content Faithfulness scores on the Federal Register example. Each competitor exhibits a distinct failure mode: Textract duplicates content, Haiku 4.5 hallucinates text and jumbles column order, and Extend reads across columns row-wise."*

**單一總分會掩蓋這種差異**：有的失效是「內容重複」（order 高但 text 低），有的是「順序崩壞」（text 高但 order 低）——兩種完全不同的病，總分不會告訴你是哪一種。

#### 資料來源

從網路上隨機抓 **500 份 PDF**，每份取一頁，**刻意移除有大量表格、圖表的頁面**。

> **Table 4** — caption: *"Content faithfulness and semantic formatting: shared document categories. The same corpus serves both dimensions, with different evaluation rules applied."*

分成 8 類：簡單文字 170、掃描件 129、多欄 117、多語言 47、雜項 33、密集 24、手寫 23、重排版 10。

⚠️ **類別分佈很不均**：`text_formatting` 只有 10 份，而這同一批文件也拿來評 Semantic Formatting——**用 10 份文件去評「重度排版」能力，樣本偏薄**。

---

## 🔑 關鍵問答（三）：bag_of_digit 為什麼「6 和 8 互換」會抓不到？

`bag_of_digit_percent` 專門抓 OCR 的數字誤認（6 看成 8）。做法是統計輸出裡每個數字出現幾次，跟正確答案的分佈比。

論文自己承認的限制原文是：

> frequency-based comparison cannot detect swaps between **equally frequent** digits

**「頻率相同」是前提條件。** 這個限定詞很容易被漏掉，漏掉之後整句話就不成立了。

**情況一：頻率不同 → 抓得到**

```
原文：6 出現 10 次，8 出現 3 次  →  分佈 { 6:10, 8:3 }
交換後：6 出現 3 次，8 出現 10 次 →  分佈 { 6:3, 8:10 }

兩者不同 ✅ 抓得到
```

**情況二：頻率剛好相同 → 抓不到**

```
原文：6 出現 5 次，8 出現 5 次   →  分佈 { 6:5, 8:5 }
交換後：6 出現 5 次，8 出現 5 次  →  分佈 { 6:5, 8:5 }

完全一樣 ❌ 失效
```

要同時滿足「雙向互換」且「兩個數字出現次數剛好相等」——條件相當苛刻，論文接受這個限制是合理的。

*（附帶一提，論文那句括號裡的舉例如果單獨抽出來看其實不成立，要接著前半句的 equally frequent 才對。它自己的例子寫得有點鬆。）*

### ⚠️ 但這個檢查有一個更大的洞（推論，論文未提）

`bag_of_digit` 是**袋**，本來就不看順序。所以真正危險的是這種：

```
原文：Revenue $2.0M, Cost $0.2M
輸出：Revenue $0.2M, Cost $2.0M

分佈完全一樣 → 通過
```

這特別諷刺——**論文正文開頭正是拿「2.0% 被讀成 0.2%」當核心動機**，說這會讓下游財務模型完全失真。而它自己的數字級檢查對這種**位置交換**是盲的。

（句級規則會抓到大部分這類錯誤，但若錯的只是同一句裡兩個數字對調，句級規則也可能因文字大致相符而放過。這個組合失效論文沒有討論。）

---

### 2.7 Semantic Formatting

#### 它在測什麼

只測**帶有語意的格式**，不測純裝飾。

> **Figure 4** — caption: *"Formatting loss changes document semantics. Each row shows a source snippet, what a formatting-unaware parser emits, and the resulting misinterpretation by a downstream agent."*

```
刪除線   標示已作廢 → 丟掉的話 agent 把舊價當現價
上下標   腳註、化學式、次方 → 壓平的話 x² 變 x2
粗體     定義詞、關鍵數值（財報的總計）
```

**每個類別都有正反兩種規則**：

```
is_strikeout      該有刪除線的，有沒有？        ← 抓「漏標」
is_not_strikeout  不該有刪除線的，有沒有誤加？  ← 抓「亂標」
```

（框架裡還有 italic、underline、highlight，但不計入正式分數。）

#### 總分公式（Equation 7、8）

```
        1.0·S_style + 1.0·S_title + (1/5)·S_latex + (1/5)·S_code
SFS = ──────────────────────────────────────────────────────────
                                W

W = Σ_c  w_c · 1[c 出現在此文件]

w_style = w_title = 1.0
w_latex = w_code  = 1/5
```

LaTeX 和 code block 被壓到 1/5，理由是它們只出現在極少數文件裡，不調整的話這兩個二元的通過/失敗會不成比例地左右總分。

**算例**（某文件無 LaTeX 也無 code block，所以 W = 1.0 + 1.0 = 2.0）：

```
S_style = 1.000
S_title = 0.658

SFS = (1.000 + 0.658) / 2.0 = 0.829
```

#### Styling 子分數：加權調和平均（Equation 9）

```
              (1 + β²) · s̄⁺ · s̄⁻
S_style = ──────────────────────────
                β² · s̄⁺ + s̄⁻

s̄⁺ = 正向規則的平均通過率（該標的有標）
s̄⁻ = 反向規則的平均通過率（不該標的沒亂標）
β  = 0.5
```

**這就是 F-score 的形式**（`F_β = (1+β²)PR / (β²P + R)`），只是把 precision / recall 換成正向 / 反向通過率。

**用調和平均的用意**：任何一邊很低，總分就被拉下來。算術平均不會——正向 1.0、反向 0.0 算術平均還有 0.5，調和平均直接趨近 0。**這個選擇是對的。**

#### ⚠️ 但 β = 0.5 的方向是錯的

論文寫：*"We set β = 0.5 to **penalise false styling more heavily** than missed styling: ... negative-rule failures carry greater weight."*

實際代數字驗算：

```
情況 A：正向全對，反向差   s̄⁺=1.0, s̄⁻=0.5
  分子 = 1.25 × 1.0 × 0.5 = 0.625
  分母 = 0.25 × 1.0 + 0.5 = 0.75
  S = 0.833

情況 B：正向差，反向全對   s̄⁺=0.5, s̄⁻=1.0
  分子 = 1.25 × 0.5 × 1.0 = 0.625
  分母 = 0.25 × 0.5 + 1.0 = 1.125
  S = 0.556
```

**反向差得 0.833，正向差得 0.556——這個公式罰「漏標」比罰「亂標」重，跟論文宣稱的完全相反。**

原因：標準 F_β 裡 β < 1 是加重**分母裡沒有 β² 的那一項的對手**（也就是加重 precision）。論文把 s̄⁺ 放在 P 的位置，所以被加重的是正向規則。想達成它宣稱的效果，β 應該要大於 1。

**這是實打實的公式與說明不一致。** 可能是公式寫錯，也可能是說明寫錯，論文沒給任何數值示範可判斷。

#### ⚠️ 這個維度有多少在測「格式理解」，多少在測「有沒有輸出 Markdown」？

> **Table 15** — caption: *"Per-provider Semantic Formatting scores on the infographic example. GPT-5 Mini preserves bold styling but flattens the heading hierarchy; Haiku 4.5 uses HTML tags instead of Markdown; Textract produces plain text with no formatting at all."*

有個模型把文字都抓對了，但輸出的是 HTML 標籤（`<h3>`、`<strong>`）而不是 Markdown 語法。規則期待的是 `**text**`，所以**整個 styling 分數歸零**。

一個能正確辨識出 `<strong>` 的模型，說它「不理解語意格式」顯然不對——**它只是輸出格式不合**。這也部分解釋了主表裡那些接近 0 的分數。

---

### 2.8 Visual Grounding：三段串接

#### 它在測什麼

**每一個抽出來的元素，能不能追回頁面上正確的那一塊區域。**

論文有一句話點得很好：一個 parser 可以產出讀起來完全正確的 Markdown，**卻在 grounding 上完全失敗**——因為它把對的字配到錯的區域。

#### 三段相乘，全過才算通過（Equation 10）

```
Pass(g_i) = L_i · C_i · [ (1 - E_i) + E_i · A_i ]

EPR = (1/N) · Σ_i Pass(g_i)
```

| 符號 | 意思 |
|---|---|
| g_i | 第 i 個 ground truth 元素 |
| L_i | 定位（localization）過了沒，1 或 0 |
| C_i | 分類（classification）過了沒 |
| A_i | 內容歸屬（attribution）過了沒 |
| E_i | 這個元素**適不適用**歸屬檢查 |
| N | ground truth 元素總數 |

**方括號那一項是個開關**：

```
E_i = 1（要查歸屬）→ 括號 = 0 + 1·A_i = A_i  → Pass = L·C·A
E_i = 0（不查歸屬）→ 括號 = 1 + 0    = 1     → Pass = L·C
```

三項相乘 = **任一項掛掉就整個歸零**。論文明講為什麼不用平均：*"averaging them would over-credit partial successes that still break provenance."*

#### 定位為什麼用 IoA 而不是 IoU

**這是全篇最務實的技術決定。**

```
IoU(A, B) = |A ∩ B| / |A ∪ B|     對稱，物件偵測的標準指標
IoA(A, B) = |A ∩ B| / |A|         非對稱，分母只看 A 自己的面積
```

論文用**兩個方向**的門檻：

```
IoA(GT, Pred) ≥ 0.50    GT 至少有一半被預測框蓋到 → 要求實質覆蓋
IoA(Pred, GT) ≥ 0.20    預測框至少兩成落在 GT 內  → 擋掉一框蓋整頁的偷吃步
```

**為什麼不用 IoU**：文件解析裡「切開」和「合併」是家常便飯——一個大文字區塊，A 系統輸出 1 框，B 系統輸出 3 個小框，兩種都不算錯。IoU 會重罰這種差異（聯集被撐大）；IoA 用單邊面積當分母，可以容忍。

門檻設成 0.20 這麼寬鬆，就是為了還能容忍切分。

**頁首頁尾特別處理**：Page-Header / Page-Footer 改用「整條上下緣的 furniture band」比對，避免一條很寬的 GT 帶狀區被拆成多個小框時被不公平地罰。

#### 歸屬（Attribution）

- 候選框用較寬鬆的 `IoA(GT, Pred) ≥ 0.30` 蒐集
- 文字正規化後比對
- **一般元素**：token 層級 **F1 ≥ 0.80** 才算過
- **圖表類的 `explicit` 元素**：改用 **recall ≥ 0.80**

為什麼圖表用 recall：那種區域裡有些數值標籤是該抽出來的，但 ground truth 不可能窮舉所有合理的描述方式。所以**該有的有抓到就算過，多寫的描述性內容不罰**。

#### 哪些元素被排除

```
formula        排除歸屬——同一條數學式有太多種合法的 LaTeX 寫法
caption=true   排除歸屬——那是描述性文字，不是字面目標字串
ignore=true    整個元素排除評分
```

還有 **merge-aware filtering**：算某元素的歸屬時，會把「其實屬於鄰近其他 GT 元素」的 token 過濾掉，避免一個合併的大預測框被重複給分。

---

## 🔑 關鍵問答（四）：IoA 算出來多少，為什麼不直接當定位分數？

### 短答：因為 EPR 是「乘法」，乘法需要 0/1

論文明確定義 L_i、C_i、A_i 是 **binary outcomes**。所以真正的問題是：**為什麼整個設計要用相乘的二元判定？**

### 因為分類那一段沒有連續分數可用

```
定位   IoA     → 天生就是連續值 0~1
分類   標籤對錯 → 天生就是 0/1
歸屬   token F1 → 也是連續值
```

**分類根本不存在「0.7 的正確」**——你不可能說一個 Table 被標成 Picture 是「分類對了七成」。

既然中間有一段只能是二元的，要串起來就得統一。而且在乘法裡，**只要有一段是二元的，整條鏈的連續性就是假的**：定位 0.9 但分類錯誤得 0 分，定位 0.3 分類錯誤也得 0 分。

### 更根本的理由：這個指標問的是「可不可用」，不是「有多接近」

**稽核是一個二元問題**——這個元素能不能追回原位置？能，或不能。「IoA = 0.45，所以追回了四成五」對稽核沒有意義。

### ⚠️ 代價：懸崖效應

```
IoA(GT,Pred) = 0.51  →  過關，計 1.0
IoA(GT,Pred) = 0.49  →  掛掉，計 0.0
```

兩個框畫得幾乎一樣，分數差 100%。而這個維度有**四個門檻**（0.50、0.20、0.30、0.80），三段又是**相乘**的——任何一個門檻微調都會被放大。**論文完全沒有做敏感度分析，也沒說明門檻怎麼定出來的。**

### 附帶：論文其實有保留連續版本

附錄定義了 **LAP / LAR / AF1** 三個「局部歸屬」診斷指標，它們是**連續的 token 加權微平均**，不需要整個元素通過。論文明說這些是 *diagnostic summaries rather than separate terms averaged into the main score*。

**主指標故意選二元（反映「能不能用」），連續資訊放到旁邊的診斷指標裡**——這個分工是合理的設計。

---

## 🔑 關鍵問答（五）：這篇論文提出的方法是開源還是付費？

要分**三層**看，答案不一樣：

| 層 | 開源？ | 意義 |
|---|---|---|
| **評分方法（metric 定義）** | 論文裡寫死了，公式全公開 | 可以自己實作，不需任何授權 |
| **資料集 + 評測程式碼** | 論文宣稱開源（HuggingFace + GitHub）| 可以拿來跑自己的 parser |
| **拿第一名的 LlamaParse** | **不開源，付費 API** | 想用就得付錢 |

**關鍵理解**：這篇論文提出的「方法」是**評分方法，不是解析方法**。它沒有告訴你怎麼把 PDF 解得更好。

論文對自家系統的描述只有一句：多步驟 pipeline、編排 VLM、搭配專用工具、迭代精修。**沒有任何實作細節、沒有架構圖、沒有 prompt。** 附錄反而把所有競品的 prompt 全文貼出來了，自己的一個字都沒有。

**商業結構：評分規則送你，得分的產品要你付錢。**

⚠️ *「dataset 和 eval code 開源」是論文的宣稱，實際 repo 狀態與授權條款未經確認。若要使用需自行查證。*

---

## 第三部分：實驗結果（以及該怎麼看它）

> 這一部分的細節資訊價值低，只保留判讀方式。

### 3.1 論文宣稱的結果

> **Table 5** — caption: *"Main ParseBench results (%). Overall is the unweighted mean across all five dimensions. Bold marks the best score across all providers in each column; underlined values mark the second-best. ..."*

LlamaParse Agentic 以 **84.9%** 居冠，最強外部競品是 Gemini 3 Flash（71.0%）和 Reducto（67.8%）。論文的整體結論是「能力版圖是破碎的，沒有任何方法在五個維度上都強」。

### 3.2 ⚠️ 為什麼這個數字要打折：三個理由

#### 理由一：這是廠商自家的 benchmark

作者信箱全部是 `@runllama.ai`。**自己出題、自己出考卷、自己訂評分標準，然後自己拿第一名。**

（論文有意識到這點，寫了「我們鼓勵獨立複現；外部得到更強結果會證實這個 benchmark 有用，而不是削弱它」。這句話寫得漂亮，但不改變評分規則的每一個設計選擇都是他們自己做的。）

#### 理由二：比較對象根本不對等

- **競品**：VLM 用單一 prompt 呼叫**一次**；商用 parser 用預設設定
- **自家系統**：多步驟、帶工具、會迭代精修的 **agent pipeline**

**拿 agent pipeline 去比單次推論，贏了不奇怪。** 這不是模型能力的比較，是「系統 vs 單次呼叫」的比較。

論文自己提供了佐證：另一家競品的 agentic 模式比它的一般模式整體 +5 分、表格 +10 分、圖表 +16 分。**「換成 agentic」這個動作本身就值不少分，跟是誰做的無關。**

#### 理由三：Overall 用未加權平均，放大了「對手沒做的功能」

Overall 是五個維度的**未加權平均**。而其中兩個維度——charts 和 semantic formatting——大部分競品接近 0 分（某些傳統 parser 的 charts 只有 1~6 分）。

**那不是能力差距，是「有沒有做這個功能」的差距。** 傳統 IDP 產品從來沒打算把圖表轉成資料表。

### 3.3 乾淨的對照

只看三個大家都真的有在做的維度（tables / content faithfulness / visual grounding）：

| | 五維 Overall | 三維平均 |
|---|---|---|
| LlamaParse Agentic | 84.9 | 87.0 |
| 最佳外部競品 | 71.0（Gemini 3 Flash）| 81.6（Azure DI）|
| **差距** | **+13.9** | **+5.4** |

**領先仍然是真的，但從 13.9 分縮到 5.4 分**，而且最強的競品換了人。

### 3.4 成本前緣

> **Figure 5** — caption: *"Quality vs. cost for all evaluated providers (Section 4.3). Per-page costs use publicly listed pay-as-you-go prices."*

論文的兩個結論：（1）加大推理預算報酬遞減；（2）自家系統在 Pareto frontier 上。

⚠️ **這張圖不可驗證**：自家成本 vs 別人的公開標價，不是同一種東西。

### 3.5 唯一值得記住的實驗觀察

**不是排名，而是這個現象**：

> VLM 擅長內容層級的理解，專用 parser 擅長結構與版面感知的抽取。而下游的 document agent **兩者都需要**。

以及一個具體的失效樣態：**單次呼叫的 VLM 在 visual grounding 上幾乎全滅**（有的只有 6 分）。原因不是框歪了一點，而是它們輸出的是「頁面級的粗略大區塊」——**根本沒在做元素級的分解**。要求一個 VLM 在單次呼叫裡同時輸出內容和幾十個 bounding box，這個任務對它太重。

---

## 第四部分：可以帶走的價值

### 4.1 先認清這篇論文的體質

**它是一份工程產物，不是一個理論框架。**

五個維度各有一套完全不同的評分機制（連續相似度、通過比例、兩層平均、加權調和平均、三段相乘），彼此沒有共同的數學基礎。每一套裡都塞了拍板決定的常數：GTRM 的 50/50、CFS 的 1.0/0.5、SFS 的 1/5、β=0.5、IoA 的四個門檻——**沒有一個給了依據或敏感度分析**。

**所以讀它的方式不是「把它當成一個整體來記」，而是「挑幾個有用的技巧帶走」。**

### 4.2 底下唯一的一條主線

> **當下游消費者從「人」變成「agent」，評分標準就得從「看起來像不像」改成「意思對不對」。**

五個維度全是這句話的不同展開。這句話本身不新鮮，但論文把它**具體化成可執行的指標**——這是它真正的貢獻。

### 4.3 三個可以直接帶走的技巧

#### ① TableRecordMatch 的概念轉換（最有價值）

把表格從「格子的排列」重新理解成「**以表頭為 key 的一袋記錄**」。

兩個設計技巧可以拆下來單獨用：
- **分母用聯集** → 同時懲罰多出來的欄位和缺少的欄位
- **分母用 max(|G|, |P|)** → 懲罰多餘的記錄

**這是全篇唯一一個「新的看事情的方式」，不只是新的算法。**

#### ② 兩層平均，解決「規則數量不均」

當評分底層是一堆數量懸殊的檢查項時（500 條漏字 vs 3 條幻覺），先**按型別內部平均**、再**跨型別平均**，數量就不再等於話語權。

**這跟文件解析完全無關，任何規則式評測都能用。**

#### ③ 「該通過的」和「不該誤判的」要成對

`is_strikeout` 一定配 `is_not_strikeout`。只測正向會獎勵「什麼都標」，只測反向會獎勵「什麼都不標」。**成對 + 調和平均**，任一邊崩掉總分就崩。

（但論文那個 β=0.5 的方向是錯的，要用的話自己驗算。）

### 4.4 值得記住但別當真的

**TEDS / GriTS 的失效模式**——表頭對調拿 0.999、語意等價的欄位重排卻只有 0.740。這兩個數字很有說服力，值得記住當作「**指標與任務不匹配**」的教科書例子。

但要記得：**TEDS 和 GriTS 不是爛指標。** 它們是為「表格結構辨識」設計的，那個任務關心的就是「格線在哪、合併儲存格對不對」，在那個脈絡下它們很合理。**問題出在任務變了，不是指標本身錯。**

### 4.5 不用帶走的

| | 為什麼 |
|---|---|
| 排行榜數字 | 廠商自家 benchmark；agentic pipeline 對打單次呼叫；Overall 未加權平均放大了「對手沒做的功能」|
| LlamaParse 的做法 | 論文一個字都沒寫 |
| 成本前緣圖 | 自家報價 vs 別人的公開標價，不可驗證 |
| 那一堆常數 | 全部拍板決定，要用就得自己重新校準 |

### 4.6 一句話

**這篇論文的價值是「TableRecordMatch 那個概念」加「兩三個聚合技巧」，其餘都是包裝。讀它是值得的，但值得的部分大概只佔全文的兩成。**
