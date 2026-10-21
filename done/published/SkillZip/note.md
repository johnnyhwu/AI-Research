# SkillZip 論文筆記

> Xiaofan Bai, Hongqiang Lin, et al., "SkillZip: Evaluation-Free Skill Compression for Self-Evolving Agents by Discovering Reusable Structure", Alibaba Group / Zhejiang University / Duke University, arXiv:2608.11079v2, 2026年8月16日

---

## 30 秒版本

self-evolving agent（會自我演化的 AI agent）會不斷把執行中學到的規則、警告、範例累積進一份叫做 skill 的文字檔，長期下來這份檔案會膨脹到原本的 5 倍以上，但其中真正「新」的知識早就不再增加了——多出來的都是同一件事被反覆講了好幾次。SkillZip 的解法是：把 skill 文字解析成一份「打了型別的合約」（介面、流程、工具規範、規則、輸出格式、佐證範例六種型別），再用「定義一次、到處引用」的邏輯，把重複的部分消掉，只保留真正不同的差異。整個過程完全不需要拿任何任務去驗證壓縮後的 skill 好不好用（作者稱為 evaluation-free），靠的是一個「硬性覆蓋約束」——原本每一條規則的意思，壓縮完都必須還找得到，找不到就不准這樣壓縮。

**這篇論文的工程價值高於研究價值**。用到的每一個底層技巧——重複片段偵測、把共同規則搬到上層、用分類器判斷兩句話的邏輯關係、動態規劃/集合裝箱/分群演算法——全部是電腦科學裡的經典技術，沒有一個是這篇論文原創的。真正的貢獻是把這些技巧組裝成一個完整、可落地的系統：不用任務驗證、壓縮速度比對手快 3.5 倍、壓縮率平均 31.2% 且整體不掉準確度。如果你在做 skill evolution 或 agent 記憶管理相關的實務工作，這篇論文的架構設計思路值得參考；如果是找理論創新，這篇論文能給的不多。

三個要留意的地方：
1. 論文的「保真度保證」只保住「解析步驟有抓到的東西」——如果一開始把 skill 文字轉成結構化資料時就漏抓了什麼，後面完全沒有機制能發現。
2. 論文說壓縮「不犧牲準確率」，但實際數據（Table I）裡 9 個測試設定中有 4 個其實是退步的，其中最差的一個案例掉了 3.2%，論文沒有特別解釋這個案例。
3. 論文拿來比較的對手 SkillReducer，其實是設計來處理另一種完全不同的冗餘（不相關的內容），拿它跟 SkillZip 比較「誰壓得比較多」某種程度上不是同一個賽道。

---

## 這份筆記怎麼讀

如果你只有 10 分鐘，讀完上面的 30 秒版本，再跳到最後「值得帶走的東西」就夠了。

如果你想搞懂方法本身，請照順序讀完「第二部分：核心方法」。

如果你是回來查某個當時卡住的概念，用下面的索引直接跳過去。

---

## 核心概念索引（當時最容易卡住、也最值得複習的地方）

這些段落是獨立的，跟 SkillZip 這篇論文本身沒有必然關係，是一般電腦科學/AI 領域的通用知識，被這篇論文用到才順便學的。之所以特別挑出來，是因為這些概念比論文本身更耐用——論文的結論會過期，但這些東西不會。

- [概念1：Grammar-based compression 與 BPE](#概念1grammar-based-compression-與-bpe) —— 「定義一次、到處引用」精神最直接的應用就是 LLM 的 tokenizer
- [概念2：Loop-invariant code motion](#概念2loop-invariant-code-motion) —— 編譯器最佳化技巧，是理解「規則為什麼能安全搬到更上層」的心智模型
- [概念3：NLI 與 relation checker](#概念3nli-與-relation-checker) —— 用一個現成分類器判斷兩段文字邏輯關係的標準做法
- [概念4：三個組合最佳化工具——DP / Weighted Set-Packing / Clustering](#概念4三個組合最佳化工具dp--weighted-set-packing--clustering) —— 「一堆候選，要挑選/歸類」問題最常見的三把工具
- [概念5：MDL（最小描述長度原理）](#概念5mdl最小描述長度原理) —— 整篇論文的理論骨架來源，也是機器學習裡「奧卡姆剃刀」的數學形式
- [概念6：Relevance-based vs Redundancy-based 壓縮](#概念6relevance-based-vs-redundancy-based-壓縮) —— 判斷「這份文件該用哪種思路精簡」的框架
- [概念7：「理解」與「決策」分離的架構設計原則](#概念7理解與決策分離的架構設計原則) —— 任何想要「用 LLM 但保持結果可重現」的系統都該遵守的分工原則

---

# 第一部分：問題與動機

## 1.1 現象：skill 檔案為什麼會越滾越大

Self-evolving agent 的運作方式是：工具失敗了，加一條警告；答案格式錯了，加一個範例；一個罕見分支成功了，記錄下這次的成功流程。每一次更新單獨看都合理，但這份 skill 檔案實際上是被當成「只增不減的筆記本」在維護，不是被當成一份「被整理過的程式」。

論文用一個縱向實驗量化這個現象。

**Fig. 1**（原文 caption：*"The skill growth tendency with respect to self-evolving progress on diverse benchmarks for a CodeX Agent. Self-evolution can keep increasing skill length after genuinely new procedural content has largely stabilized."*）畫了兩條線，橫軸是自我演化的輪數：
- 橘線（skill tokens）：skill 檔案的總字數，持續往上爬
- 藍線（unique contract content）：真正獨特、不重複的規則內容量，爬到一半就趨於平緩

兩條線之間的裂縫，就是這篇論文要處理的東西：**新增的文字量，遠超過新增的「真正新知識」量**。

論文舉的例子很傳神：跑了夠多輪之後，「不要覆蓋原始檔案」這句話可能同時出現在開頭介紹、三個 workflow 分支、還有一個範例裡——同一件事被講了四次。

RQ1 的實驗結果印證了這個現象：用 SkillOpt（一個既有的 skill 自我演化系統）跑到第 5 輪，skill 長度在 BFCL-V4、LiveMath、SpreadsheetBench 三個測試集上分別膨脹到約 5.6 倍、3.1 倍、6.7 倍，平均約 5.2 倍。

## 1.2 兩種「長」不是同一種問題

論文特別區分兩種會讓 skill 檔案變長的情況，這個區分決定了「該用什麼方法瘦身」。

**情境 A：一般公開、社群寫的教學型 skill**

這種 skill 通常混雜了背景說明、多餘的範例、跟執行無關的參考資料：

```
## 什麼是 API？
API 是應用程式介面的縮寫，讓不同軟體可以互相溝通...

## 為什麼選擇 OpenWeather 而不是其他服務？
市面上有很多天氣 API，我們選這個是因為...

## 範例 1：查詢台北天氣
（範例程式碼）

## 範例 2：查詢東京天氣
（幾乎一樣的程式碼，只是換城市名）
```

這裡「什麼是 API」「為什麼選這個服務」跟「怎麼執行這個任務」完全無關，刪掉這些，agent 照樣能查天氣，不會漏掉任何執行所需的規則。**這種冗餘,判斷依據是 relevance（跟執行相不相關）**。

**情境 B：多輪自我演化出來的 skill**

這種 skill 的每一條新增內容，都是被 rollout 回饋驗證過才接受的：

```
第 3 輪：查詢城市名有空格時（例如 "New York"）沒編碼，API 回傳 400 錯誤
        → agent 加了一條：「城市名有空格時要做 URL encode」

第 7 輪：查詢不存在的城市名時，API 沒有丟錯誤，而是回傳空的 JSON，
        導致 agent 誤判為「晴天」
        → agent 加了一條：「查完後要檢查回傳的 JSON 是否為空」

第 12 輪：另一個分支（批次查詢）又重新踩到「城市名要 URL encode」
         這件事，加了一次幾乎一樣的話，只是措辭不同
```

「城市名要 URL encode」跟「空 JSON 要視為失敗」，每一條單獨看都是真的、必要的、跟執行高度相關——不是可以砍掉的離題內容。但同一件事（URL encode）在第 3 輪跟第 12 輪各講了一次。**你不能靠「這段跟執行有沒有關係」來判斷要刪誰，因為兩段都相關；你能判斷的是「這兩段其實在講同一件事，可以合併」。這種冗餘，判斷依據是 redundancy（有沒有重複），不是 relevance**。

```
情境 A 的冗餘 = 內容本身不重要（跟主題無關）→ 判斷依據：relevance
情境 B 的冗餘 = 內容都重要，但同一件事被表達了很多次 → 判斷依據：redundancy
```

論文比較的 baseline「SkillReducer」是設計來處理情境 A 的（用 delta debugging 去蕪存菁、搭配任務驗證），SkillZip 則是設計來處理情境 B 的。這個差異也是後面 RQ2 結果比較時要留意的重點——兩者原本瞄準的就不是同一種冗餘。

## 1.3 為什麼不能直接套用現成的 prompt compression 工具

這一點展開在「[概念6：Relevance-based vs Redundancy-based 壓縮](#概念6relevance-based-vs-redundancy-based-壓縮)」，這裡先講結論：prompt compression（例如 LLMLingua）靠的是「這段文字跟當下這個查詢的相關性」去篩選要不要留，但 skill 必須對「所有未來可能的查詢」都保持有效——skill 被載入的當下，完全不知道等一下 agent 會被問什麼。既然沒有一個「當下的查詢」可以拿來當篩選依據，prompt compression 的整套邏輯在 skill 這個情境下就用不上。

---

# 第二部分：核心方法

## 2.1 把 skill 看成一份「打了型別的合約」

論文的基本主張：一份 skill 不是一段平坦的文字，而是一份合約（contract）。合約裡不同的句子管的是完全不同的東西——這件事直接決定「改動它們的安全規則」不一樣。

**Fig. 2**（原文 caption：*"A skill is a typed contract. Different text spans constrain different parts of execution. An example is removable only when every requirement it uniquely expresses is represented elsewhere."*）畫出這個合約 `C(S) = ⟨I, G, T, C, O, E⟩`（論文 Eq. 1）的六個組成部分：

| 符號 | 全名 | 管什麼 | 具體例子 |
|---|---|---|---|
| I | Interface（介面） | 這個 skill 叫什麼、何時該被觸發、何時不該被觸發 | 「觸發：使用者問天氣」「排除：使用者問氣候變遷歷史」 |
| G | Workflow（工作流程） | 執行順序、分支、迴圈、失敗時怎麼辦、什麼時候算做完 | 「先查城市代碼 → 再查天氣 API → 若失敗重試一次」 |
| T | Tool protocol（工具協定） | 呼叫哪個工具、要帶什麼參數、前提條件、回傳格式、錯誤處理 | 「呼叫 get_weather(city_code)，city_code 必須先做 URL encode」 |
| C | Scoped rules（有範圍的規則） | 「必須／不可以／建議」做什麼，且這條規則只在哪個範圍、哪個條件下成立 | 「（範圍：批次查詢分支）不可以一次查超過 10 個城市」 |
| O | Output contract（輸出合約） | 回傳格式、必填欄位、欄位順序、驗證方式、什麼時候算完成 | 「輸出必須是 JSON，含 temperature、condition 兩個必填欄位」 |
| E | Evidence（佐證） | 範例、範本、把某個決定講清楚的理由 | 「範例：查台北天氣的完整輸入輸出」 |

用一個簡單的線性圖表示這六塊怎麼分工：

```
使用者問題 -> [I 判斷要不要觸發] -> [G 依序執行步驟] -> [T 呼叫工具]
                                                          |
                                    [C 檢查規則有沒有違反]  |
                                                          v
                                    [O 檢查輸出格式] <- 工具回傳結果
```

`E`（範例/佐證）不在這條主線上，是輔助說明，貼在其他五塊旁邊幫忙解釋。

**這個拆解不是為了歸檔好看，而是決定「兩句話能不能合併」的安全依據**。論文原文舉的三個例子：
1. 同一個工具、但要求參數不同的兩句話——不能合併，因為要求的參數不同，硬合併會漏掉其中一個要求。
2. 每個分支都有的規則——可以搬到共同的父層（scope lifting）。
3. 只掛在某一個分支上的規則——不能搬，搬到父層會讓範圍變大，變成錯誤的規則。

## 2.2 六型別如何映射到步驟2的 JSON 結構

SkillZip 一次結構化抽取後，輸出的合約用一份 JSON 表示，最外層有 8 個欄位（論文 Appendix C）：`interface`、`scopes`、`workflow`、`rules`、`output`、`evidence`、`shared_procedures`、`residual`。前 6 個對應六型別（`scopes` 是輔助用的範圍樹，不是獨立型別；`shared_procedures` 存放已經被抽出來的共用流程；`residual` 是抽取信心不足的殘留內容，見 2.4 節）。

每個外層欄位底下是陣列，陣列裡每一筆資料各自有自己的 schema，且都帶著 `spans`（或 `source_blocks`）欄位，記錄它是從原文哪個/哪些區塊抽出來的。這個對應關係是**多對多**：一筆抽取單元可能同時引用好幾個原文區塊（例如條件在一處、規則本身在另一處），一個原文區塊也可能被拆成好幾筆不同的抽取單元。

一筆 `rules` 陣列裡的元素長這樣：

```
{
  "id": "C1",
  "scope": "if-validation-fails",
  "modality": "must_not",
  "predicate": "overwrite the input file",
  "guard": "true",
  "spans": ["B5"],
  "locked": false,
  "confidence": 0.92
}
```

`spans` 這個欄位就是可追溯性（provenance）機制的核心——每一個後續的壓縮決策，理論上都能回溯到「原文哪一塊」。

## 2.3 形式化目標：Minimum Description Length（MDL）

完整背景見「[概念5：MDL](#概念5mdl最小描述長度原理)」，這裡直接看論文怎麼把它寫成公式。

SkillZip 用一個庫 K（reusable contract elements，可重用的合約元素）加上一個殘差 R（unique, exceptional, or uncertain content，獨特、例外或不確定的內容）來表示壓縮後的 skill。目標式（論文 Eq. 4）：

```
(K*, R*) = argmin[L(K) + L(R|K)]
           限制條件：a ⪯ (K,R)，對所有 a 屬於 A_req(S) 都要成立
```

翻成白話：**在「不能弄丟任何規則」的前提下，找出總長度最短的表示方式**。`a ⪯ (K,R)` 讀作「單元 a 被 (K,R) 涵蓋」，這是硬性約束（hard constraint），不是可以打折扣的加權項——即使某個合併方案能省下大量 token，只要它會導致任何一個原本抽出的必要單元變得沒被涵蓋，這個方案直接不合法。

長度 `L(x)` 本身怎麼算（論文 Eq. 6）：

```
L(x) = |Render(x)|_tok + γ_def(x) + γ_ref(x) + γ_scope(x)
```

- `|Render(x)|_tok`：把 x 轉成文字後的 token 數
- `γ_def(x)`：如果 x 是「定義一個新規則/新流程」，要額外付的成本（取名字、寫清楚範圍）
- `γ_ref(x)`：如果 x 是「引用某個已定義好的規則」，要付的成本（比重寫便宜，但不是免費）
- `γ_scope(x)`：表達「這條規則適用範圍」要付的成本

這四項加總的用意：防止演算法耍小聰明——如果「定義+引用」的成本比「直接重複寫兩次」還貴，那乾脆不要合併，原地保留反而比較省。

## 2.4 抓不準的內容：locked residual

步驟 2 用一個受 schema 約束的 LLM 把原文轉成結構化合約，如果某段原文的型別或範圍判斷不準，不會勉強塞進六型別的某一類，而是整段原封不動放進 `residual`，並標記 `locked=true`。

```
原文：「這裡的行為比較特殊，建議依照經驗調整」
→ 不是明確規則（沒有明確的 must/must_not）
→ 也不是明確的 workflow 步驟或輸出格式要求
→ LLM 判斷不出該歸哪一類
→ 整句原封不動放進 residual，鎖住
```

被鎖住的內容**不會被拿去跟其他東西合併、不會被優化、不會被刪除**，會直接原封不動出現在最終輸出裡。這是整個系統「保守失敗」設計哲學的具體實作：寧可保留一段看不太懂的原文，也不要冒險把它硬塞進某個型別、結果塞錯導致資訊遺失或誤判。

## 2.5 四個決策：MDL 目標式的四種具體展開

同一個 Eq. 4 骨架，套用在四種不同的重複結構上，展開成四條判斷式。每一條的共同邏輯都是：

```
（省下的：不合併時要各自付的代價）大於（多付的：定義成本+引用成本+殘差成本）
才值得合併
```

### 決策1：Equivalent requirements（同義敘述合併）—— Eq. 7

```
L(z) + L(x1|z) + L(x2|z)  <  L(x1) + L(x2)
```

- `x1`、`x2`：兩句話，內容幾乎完全一樣
- `z`：合併後只留一份的共用版本
- `x1|z`、`x2|z`：合併後，x1 跟 x2 各自「還需要額外交代的差異」，如果兩者幾乎完全一樣，這兩項接近 0

**論文自己給的真實例子**（Appendix E，LiveMath skill 壓縮前後對照）——壓縮前這段話逐字重複出現兩次：

> "If the problem asks for a single specific value (e.g., maximum, minimum, unique solution) or implies a unique answer, output ONLY that single valid value. Strictly discard any extraneous candidates, negative roots, or intermediate results that do not satisfy all constraints..."

壓縮後只出現一次，且用詞更精簡。以下是這個例子的**示意估算**（不是論文報告的精確數字，論文只給了整份 skill 936→638 token 的總數，這裡是為了展示判斷式怎麼用而做的粗略估計）：

```
L(x1) ≈ 55 字，L(x2) ≈ 55 字 → 不合併的總成本 ≈ 110
L(z) ≈ 45 字（合併後精簡版），殘差 ≈ 0（兩句幾乎完全一樣）
判斷：45 < 110 → 划算，合併
```

### 決策2：Scope lifting（規則搬到共同父層）—— Eq. 8

```
L(c@u) + r · L(scope-ref)  <  Σ L(c@sᵢ)，i 從 1 到 r
```

- `c@sᵢ`：規則 c 掛在子分支 sᵢ 底下的樣子
- `c@u`：規則 c 改寫成掛在共同父層 u 底下的樣子（通常比掛在單一分支下多花一點 token，因為要交代清楚「對所有子分支都成立」）
- `scope-ref`：每個子分支留一個小小的繼承標記

**示意數字**（延續天氣查詢 skill 的例子）：

```
搬移前（3個分支各自寫一次「城市名要 URL encode」）：
  Σ L(c@sᵢ) = 12+12+12 = 36

搬移後（搬到共同父層，3個分支各留一個繼承標記）：
  L(c@u) + 3·L(scope-ref) = 15 + 3×1 = 18

判斷：18 < 36 → 划算，搬
```

**安全前提**（論文原文明講）：只有「每個相關的子路徑都真的需要這條規則」且「所有局部衝突都被編碼成 exception」時才能搬。如果某個分支其實不需要這條規則，硬搬上去會變成這條規則錯誤地套用到那個分支——即使數學上划算，也不能做。

這個判斷式跟編譯器裡的 **loop-invariant code motion**（把迴圈裡不變的運算搬到迴圈外）是同一個邏輯，完整說明見「[概念2](#概念2loop-invariant-code-motion)」。

### 決策3：Workflow reuse（重複流程共用）—— Eq. 9

```
L(def(q)) + r · L(call(q))  <  r · L(q)
```

- `q`：一段重複出現的動作序列（例如「驗證輸入 → 呼叫 API → 失敗就重試 → 解析結果」）
- `r`：q 在整份 skill 裡不重疊地出現了幾次
- `def(q)`：把 q 定義成一個有名字的共用流程要花的 token（含取名字+交代進出條件）
- `call(q)`：之後每次用到它時，只需要引用這個名字要花的 token

**示意數字**（論文原文只描述現象「the same validate–repair–verify sequence is copied repeatedly with only minor differences」，沒有給具體 token 數字，以下是自行編的示意）：

```
搬移前（3個分支各自完整寫一次驗證-修復流程，每次20字）：
  r · L(q) = 3×20 = 60

搬移後（定義一次24字，每次引用6字）：
  L(def(q)) + 3·L(call(q)) = 24 + 3×6 = 42

判斷：42 < 60 → 划算，共用
```

候選要能被提名，必須滿足兩個限制：**不重疊**（同一段文字不能同時被算成兩個不同候選的一部分）跟**進入/退出行為一致**（幾個分支裡這段流程執行前的前提、執行完銜接的下一步要一樣）。

論文 render 階段還有一個實務判斷（原文：*"A shared workflow is named only when references save tokens; otherwise it remains inline."*）——即使 Eq.9 數學上划算，如果 r 太小、流程很短，取名成本可能吃掉大半省下的空間，這時會選擇不特別命名、保持內聯。

這個判斷式的精神，跟 Re-Pair/SEQUITUR 這類 grammar-based compression 演算法、以及 LLM tokenizer 用的 BPE 演算法，是同一個「define once, reference many」邏輯的不同應用，完整說明見「[概念1](#概念1grammar-based-compression-與-bpe)」。

### 決策4：Guarded variants（通則 + 例外）—— Eq. 10

```
L(c) + Σ L(δᵢ)  <  Σ L(cᵢ@gᵢ)
```

- `cᵢ@gᵢ`：第 i 個帶條件的規則版本（`gᵢ` 是成立條件，`cᵢ` 是規則內容）
- `c`：這些版本的共同核心
- `δᵢ`：第 i 個版本跟通則 c 之間剩下的差異

**跟決策1的關係**：兩者判斷式的骨架完全一樣——都是「（共用部分只付一次）+（各自差異各付各的）跟（每份各自完整付一次）比大小」，差別只在於：

```
決策1 = 決策4 的特殊情況（差異部分 δᵢ 剛好接近 0，因為內容根本沒差異）
決策4 = 更一般的情況（允許每份留下一段不能被抹掉的真實差異）
```

**示意數字**（天氣查詢 skill 的城市數量上限規則）：

```
合併前（3個分支各自的城市數量上限規則）：
  Σ L(cᵢ@gᵢ) = 12+14+12 = 38

合併後（抽出共同核心「查詢有城市數量上限」，各自留下差異）：
  L(c) + Σ L(δᵢ) = 8 + 6+9+6 = 29

判斷：29 < 38 → 划算，用「通則+例外」表示
```

**這裡有一個論文沒交代清楚的地方**：怎麼從多個版本裡抽出這個共同核心 `c`，論文完全沒有給出具體演算法或 prompt，只在 §V.A 步驟3提到 relation checker 會把這類配對判斷成 "conflict"、送去產生 exception candidate，但「conflict 判斷完之後怎麼生成 c」這一步的機制沒有明講。

**這也是四個決策裡最容易出錯的一個**：如果三個分支的規則其實有隱藏的細微差異（不只是表面上看起來像），但抽共同核心這一步沒抓到、被錯誤合併成同一個 c，會發生「某個分支原本該有的限制被通則覆蓋掉」——這種錯誤不會被 coverage constraint 抓到（因為從 K 的角度看，規則「有被涵蓋」），但實際行為已經跟原本不一樣了。

### 四個決策比較表

| | 決策1 同義合併 | 決策2 Scope lifting | 決策3 Workflow reuse | 決策4 通則+例外 |
|---|---|---|---|---|
| 論文式子 | Eq.7 | Eq.8 | Eq.9 | Eq.10 |
| 判斷式結構 | L(z)+殘差 < 各自總和 | L(搬父層)+r·標記 < 各分支總和 | L(定義)+r·L(引用) < r·L(原長) | L(共同核心)+差異總和 < 各版本總和 |
| 觸發情境 | 兩句話完全同義 | 同一規則重複出現在多個子分支 | 同一段動作序列重複出現 | 多個版本部分相同、部分不同 |
| 主要對應合約型別 | 不限（C最常見） | C（scoped rules） | G（workflow） | C（scoped rules） |
| 合併後殘差是否為0 | 幾乎是0 | 用 scope-ref 標記取代 | 用 call(q) 取代 | 不為0，每份都留差異 |
| 安全前提 | modality/guard 完全一致 | 每個相關子路徑都真的需要這條規則 | 進入/退出行為一致+不重疊 | 差異必須完整收進δᵢ，不能漏 |
| 候選重疊時的處理演算法 | Union-Find clustering | Dynamic Programming（scope tree上） | Weighted set-packing | 論文沒有給出演算法名稱 |
| 最容易出錯的地方 | 表面像但modality不同，誤判可合併 | 誤判某分支其實不需要這條規則 | 進出行為看似一致，實際有隱藏差異 | 抽共同核心時漏掉某分支獨有的限制 |

## 2.6 六型別如何映射到四個決策：兩道關卡

六型別不是「決策的分類依據」，而是「決策能不能套用的篩選閘門」。**六型別決定「這兩個東西夠不夠格被拿來比較」，四個決策才是「比較完之後，划不划算」的數學測試**。兩者是先後兩道關卡，不是平行的兩套分類。

```
原始文字 -> 掃描抽取成六型別單元(I/G/T/C/O/E)
         -> 關卡1：型別相容篩選 -> 只有同型別、且細節相容的才能配對
         -> 關卡2：套用四個決策式(Eq.7-10) -> 算划不划算
         -> 選出最省的組合
```

論文 §V.A 步驟3 明講的 5 條型別相容篩選規則：

```
(a) I（介面）  同樣是 trigger 或同樣是 exclusion 角色，才能比
(b) C（規則）  modality、predicate family、scope ancestry 都相容，才能比
(c) T（工具）  同一個工具名稱 + 參數簽章相容，才能比
(d) O（輸出）  同一種 response type + 同一個欄位命名空間，才能比
(e) G（流程）  從重複的、有相同guard的動作序列裡找，不經過上面的比對機制
```

過關的候選，才輪到套用對應的決策式：

| 型別 | 過關卡1的規則 | 能套用哪個決策 |
|---|---|---|
| I 介面 | (a) 同角色 | 決策1 |
| C 規則 | (b) modality+scope相容 | 決策1、決策2、決策4——唯一同時吃到三個決策的型別 |
| T 工具 | (c) 同工具+參數相容 | 決策1（但參數不同就不能合併） |
| O 輸出 | (d) 同類型+同命名空間 | 決策1 |
| G 流程 | (e) 獨立序列比對機制 | 決策3（不經過relation checker） |
| E 佐證 | 不在 (a)~(e) 清單裡 | 沒有專屬決策，用另一套「覆蓋測試」判斷能不能整段刪除 |

**E（佐證）是特例**：判斷依據不是「跟別的範例像不像」，而是「這個範例講的東西，其他地方（通常是 O 或 C）有沒有已經寫清楚」（呼應 Fig. 2 caption 那句話）。走的是覆蓋測試，不是 Eq.7-10 那四條省 token 公式。

**論文沒有交代清楚的地方**：決策2（scope lifting）在 §V.A 步驟3 的五條規則裡沒有獨立列出，它其實不是靠 relation checker 判斷出一種獨立的關係，而是候選池 A（equivalence 群組）在步驟4被 DP 加工後，順帶決定的一種「安放形式」。也就是說，step3 直接生成的候選身分只有三種（equivalence/implication、conflict、workflow重複），決策2 是 equivalence 候選在 step4 的其中一種可能呈現方式，不是 step3 就分好的第四種候選。

---

# 第三部分：One-Shot SkillZip 演算法

論文 §V.A 把整個流程拆成 5 個子步驟，對應 Algorithm 1：

```
Algorithm 1 One-Shot SkillZip
輸入：Skill S，audit flag v
輸出：壓縮後的 skill S̃

1: B ← Scan(S)                       步驟1
2: (A, R) ← ExtractContract(B)       步驟2
3: H ← ProposeReuse(A)               步驟3
4: K ← MinCostCover(A, R, H)         步驟4
5: S̃ ← Render(K)                     步驟5
6: if v then
7:   K̂ ← Parse(S̃)
8:   M ← ContractDiff(K, K̂)
9:   S̃ ← RestoreMissingSpans(S, M)
10: return S̃
```

## 3.1 步驟1：Scan the SKILL.md（純規則式掃描，不用 LLM）

這一步完全不用 LLM，是純規則式的解析器（論文 Appendix B）。做的事：
- 把 skill 文件拆成一塊一塊帶 ID 的區塊（block），區塊 ID 是「正規化後文字內容 + 上層標題路徑」的 hash，不是行號——行號會因為前面插入新內容而跑掉，hash 不會。
- 把 Markdown 的巢狀標題結構，先轉成初步的 scope tree。scope 路徑長這樣：`["root", "workflow", "if-validation-fails"]`
- 抓「編號清單」跟「時間性字眼」（例如「先...再...然後...」）當作高信心的 workflow 線索。
- code block 跟表格當成不可切割的最小單位。

**為什麼要先做這一步、不直接丟給 LLM**：能用規則解決的結構（標題層級、編號清單），就不要浪費 LLM 的判斷力去猜——一方面省成本，另一方面每個後續決策都能回溯到「原文哪一塊」。

一條規則要從「掛在某個小分支底下」升級成「掛在更大範圍底下」，需要文字裡有明確線索：用詞像 "always"、"for every request" 這種明確宣稱全域適用的字，**或者**這條規則在好幾個相關的子節點下都重複出現。

**這是我從論文行文推論的一點，論文全文沒有正面處理過**：步驟1的機制骨幹是「Markdown 巢狀標題 → 初步 scope tree」跟「編號清單/時間字眼 → workflow 線索」，如果輸入不是 Markdown 格式、是一整段沒有標題沒有清單的純文字，這兩個線索來源都不存在，步驟1大概率抓不到什麼結構。這會連帶影響步驟5的 audit 機制——audit 依賴每個抽取單元都有 spans 可以回頭核對，如果純文字輸入導致步驟1切出來的區塊太粗，可追溯性的精細度會下降。

## 3.2 步驟2：Recover the typed contract（LLM抽取 + host驗證）

把步驟1切好的編號區塊，丟給一個受 schema 約束的 LLM，請它輸出 Eq.1 的合約。這一步的輸出**不是文字，是結構化的 JSON**。

**四種會被拒絕的錯誤**（論文原文明講，由確定性的 host 程式檢查，不是另一個 LLM）：

```
1. unsupported citations       抽出來的東西找不到對應來源區塊ID
2. polarity mismatch           必須/不可以的方向抽反了
3. unknown tool names          抽出的工具名稱不在任何來源區塊裡出現過
4. invalid workflow references 流程節點指向一個不存在的下一步
```

其中第 1、3、4 項，host 用純粹的 ID/字串比對就能做到，不需要理解語意：檢查引用的 block ID 存不存在（集合查找）、檢查工具名稱有沒有出現在來源文字裡（字串包含）、檢查流程節點指向的下一步存不存在（圖的節點是否存在）。**第 2 項（polarity mismatch）論文完全沒有交代具體怎麼檢查**——這牽涉到要理解原文那句話的語意，沒辦法只靠 ID 比對完成，論文也沒說這一步有沒有計入 Table II 報告的 LLM calls 成本統計裡。

**為什麼要把「理解」跟「壓縮」拆成兩個獨立步驟**：抽取器（步驟2）被刻意要求不做壓縮判斷。這麼做有兩個好處：合約抽取的品質可以獨立被檢驗（拿人工標註去對答案）；優化步驟（步驟3、4）一旦抽取單元固定，就是純數學運算，同樣輸入一定得到同樣輸出，不受 LLM 隨機性影響。完整說明見「[概念7](#概念7理解與決策分離的架構設計原則)」。

## 3.3 步驟3：Propose type-compatible reuse（找候選）

這一步只是「提名」候選，還不決定要不要真的合併。分成兩個小階段：

**3a. 結構篩選**：套用 2.6 節的五條型別相容規則，過濾掉明顯不可能配對的組合。

**3b. Embedding 檢索 + relation checker 判斷關係**：

```
1. 精確匹配（Exact matches）：用 hashing 找出正規化後一字不差的內容
2. 近似匹配（Near duplicates）：先用 embedding index 找出語意上接近的候選（快、粗略）
   → 再用 frozen relation checker（NLI-like）細判斷關係：
     equivalence   → 進候選池A（可能合併）
     implication   → 也進候選池A（論文沒明講implication具體怎麼被用）
     conflict      → 進候選池B（可能變成通則+例外，不是被丟棄！）
     unrelated/低信心 → 丟棄
```

**Workflow（G型別）走完全獨立的路**，不經過型別篩選也不經過 relation checker，是靠「重複的、有相同guard的動作序列」做獨立的序列比對（類似 Re-Pair 找重複子序列），自成候選池C。

完整背景見「[概念3：NLI 與 relation checker](#概念3nli-與-relation-checker)」。

## 3.4 步驟4：Select the shortest covering explanation（決定要不要真的合併）

**動作1**：每個候選先算一次 `save(h) = L(separate form) − L(form using h)`（Eq. 5，這是 Eq.7-10 的通用骨架），`save(h) ≤ 0` 的候選直接丟棄。這一步只回答「單獨看，這個候選划算嗎」，不代表「這些都划算的候選能同時執行」——候選之間可能互相搶用同一批原始單元，不能兩個都選。

**動作2**：不同候選池，用不同演算法解決「候選互相排擠」的問題：

```
候選池A（equivalence/implication） → conflict filtering + Union-Find clustering
                                       若群組跨scope分佈 → 再用DP決定放scope tree哪一層
候選池B（conflict）                 → Eq.10，論文沒給出候選互斥時的排序演算法
候選池C（workflow重複）             → weighted set-packing（貪心按效率排序+pairwise exchange微調）
```

完整背景與生活化類比見「[概念4：DP / Weighted Set-Packing / Clustering](#概念4三個組合最佳化工具dp--weighted-set-packing--clustering)」。

**動作3**：每選定一個候選，立刻重新檢查 coverage（Definition III.1）——原本每一條規則的意思，在目前選定的 K 裡還找得到嗎？找不到就撤銷這個候選。

**論文自己給的具體例子**（原文，把三個決策放在同一個 running example 裡）：

> "The two branch-local copies of "never overwrite the input" are represented by one rule at their common parent because Eq. (8) is satisfied. The validate step is shared only if its definition and calls are shorter than the copies. The JSON example is removed only after its fields are covered by the output contract."

```
"兩個分支各寫一次『不要覆蓋輸入』"  → 決策2 scope lifting (Eq.8)
"validate 步驟"                     → 決策3 workflow reuse (Eq.9)
"JSON 範例被刪除"                    → E的覆蓋測試（前提是欄位已被O涵蓋）
```

### Step3 輸出 → Step4 決策形式 完整對照表（這張表把整個決策流程串起來，值得記住）

| Step3 候選來源 | Step3 判斷機制 | Step4 呈現形式 | 對應公式 | 候選重疊時的處理演算法 |
|---|---|---|---|---|
| equivalence/implication 候選 | 結構篩選(3a)+embedding檢索+relation checker(3b) | 單純合併 | Eq.7 | Union-Find clustering |
| ↳ 同一批候選，若群組跨scope分佈 | （沿用同一批判斷結果，不是獨立生成） | 搬到共同父層 | Eq.8 | Dynamic Programming |
| conflict 候選 | 結構篩選(3a)+embedding檢索+relation checker(3b) | 通則+例外 | Eq.10 | 論文沒有給演算法名稱 |
| workflow重複候選 | 獨立序列重複偵測，不經過3a/3b | workflow共用 | Eq.9 | Weighted set-packing |

## 3.5 步驟5：Render + Structural Audit

**Render**：用固定樣板（不是 LLM）把最終決定的合約 K 轉回一份正常的 skill 文字，含簡潔的 purpose/triggers、全域規則、編號 workflow、巢狀的guarded分支、明確的工具要求、輸出 checklist。共用 workflow 只有在「引用確實比內聯省 token」時才特別命名，否則保持內聯。

**Structural Audit（可選）**：找一個「盲測」的 audit parser——完全不給它看原始 skill、也不給它看選定的合約 K，只給它看 render 完的最終文字，請它獨立重新解析一次，得到一份新的合約 K̂。拿 K̂ 跟原本的 K 做 diff：如果 K̂ 缺了某個 trigger、guard、workflow edge、tool argument、polarity、output field，代表這些資訊在 render 或抽取過程中被遺失了，就從原文 restore 能涵蓋這個缺失項目的最短片段，補回最終文字，並鎖住不准後續刪除。

這一步的用意是用「完全不看原文、只看最終渲染結果」的獨立視角，反向驗證這份最終文字是否真的完整表達了 K 要表達的東西。

---

# 第四部分：Zip-on-Write（持續壓縮模式）

## 4.1 為什麼需要一個「持續」模式

Self-evolving agent 實際運作是不斷收到小 patch（一次修正、一次新增），不是整份重寫。如果每次都重跑一次完整的 One-shot 流程，成本會隨 skill 越變越大而越來越貴。Zip-on-Write 要解決的問題是：只處理這次新增的 patch，不用把整份 skill 重新分析一次。

## 4.2 Sidecar 機制

論文原文：*"SkillZip stores a sidecar, skillzip.json, containing the current contract, source provenance, scope tree, workflow graph, and candidate indices. The rendered SKILL.MD remains the only artifact loaded by the agent."*

```
skillzip.json（sidecar）：存結構化的內部狀態——目前的合約K、來源(spans)、
                          scope tree、workflow graph、候選索引
                          agent不會讀這個檔案，這是SkillZip自己維護的工作記憶

SKILL.md（渲染出來的最終文字）：agent實際載入、實際讀取的東西
                          每次sidecar更新後都要重新render一次
```

## 4.3 四種操作：ABSORB / REFINE / EXTEND / REFACTOR

每一個新 patch，都會被歸類成這四種之一：

```
ABSORB   ：patch只是重述現有規則，沒有增加任何新的合約內容
REFINE   ：patch幫現有單元加了guard、tool argument、validation或exception
EXTEND   ：patch引入一個真正全新的規則
REFACTOR ：patch讓某個舊有的規則/流程「現在」變得值得共用
```

用天氣查詢 skill 的例子分別走一次：

```
ABSORB：現有規則「城市名要url encode」的guard是"true"(適用所有情況)
        → 新patch說「批次查詢時城市名也要url encode」
        → 內容早就被現有規則涵蓋 → ABSORB，合約完全不變

REFINE：新patch說「批次查詢時城市名有逗號要額外處理，不只是url encode」
        → 現有規則沒涵蓋這個新細節，但可以在現有規則上加一個guard
        → REFINE，直接在既有單元上新增這段細節

EXTEND：新patch說「查詢歷史天氣時，日期格式必須是YYYY-MM-DD」
        → 完全沒在任何現有規則出現過 → EXTEND，新增一條規則

REFACTOR：目前分支A、B各自寫了一次「驗證-修復」流程(r=2，還不夠划算共用)
          新patch：分支C也新增完全一樣的流程 → r變成3，重新套Eq.9可能划算了
          → REFACTOR，把三份獨立流程重構成一份共用流程
```

REFACTOR 是唯一一種「不是因為新內容本身，而是因為新內容改變了周邊環境的划算與否」而觸發的操作。

**Host 怎麼決定選哪一種操作**：論文原文：*"The host selects the feasible operation with the smallest increase in Eq. (4)."* 先篩掉不可行的操作（例如：ABSORB 只有在 patch 沒引入任何目前合約沒涵蓋的內容時才可行；EXTEND 要求真的是全新的必要單元），剩下可行的操作裡，選「讓 Eq.4 的總成本增加最少」的那一個。

**要注意的地方**：這裡比的是「增加最少」（smallest **increase**），不是「哪個變小最多」。因為 Zip-on-Write 處理的是「新增內容」，資訊量原則上只會持平或增加，不會無中生有地減少——除非觸發了 REFACTOR，把原本沒共用的東西變成共用，理論上總長度才可能真的比 patch 之前更短。這跟 One-shot 模式的 Eq.5（`save(h) > 0`，真的在縮小既有的膨脹內容）性質不一樣：一個是「壓縮既有的胖」，一個是「新增時盡量少長胖」。

論文特別強調：*"No operation is accepted because it improves a task score."* 四個操作之間的選擇純粹靠 Eq.4 的成本計算，不會跑一次任務去看哪個操作讓 agent 表現更好——保持跟 One-shot 一致的 evaluation-free 精神。

## 4.4 候選搜尋範圍限縮

如果每次來一個小 patch，都要跟歷史上所有規則重新比對一次，完全沒有省到「只處理增量」的好處。論文原文：*"Candidate search is restricted to the matching type, current scope, ancestor scopes, and adjacent workflow nodes."*

```
matching type          只跟同型別的東西比
current scope           只跟patch所在的那個scope裡的東西比
ancestor scopes         以及這個scope往上到root的所有祖先scope
adjacent workflow nodes 只跟前後緊鄰的節點比，不跟整個workflow graph比
```

複雜度是 `O(d·k)`（d 是這個 patch 抽出的單元數，k 是檢索出的候選數量，是個小常數），不會隨著整份 skill 的歷史長度增加而變大。

**代價**：可能漏掉「跨 scope」才能發現的共用機會——例如兩個原本毫無關聯的分支，各自累積 patch 之後，現在才發現有一段一模一樣的流程，但因為每次只看「附近」，這種跨越不相關分支的共用機會不會被單次的局部比對抓到。

## 4.5 什麼時候觸發全域 repack

Sidecar 額外追蹤「約略計數」（approximate counts，不是精確計數，用意是避免每次都要做完整的 embedding+relation checker 比對），三個觸發條件任一滿足就觸發：

```
條件1：估計可回收的省下空間超過 θ_repack（門檻值）
       sidecar追蹤rule families、action n-grams的約略出現次數，
       粗略估計「如果現在做一次全域整理，大概可以省下多少token」
條件2：合約成長超過 ρ（自從上次repack以來）
條件3：累積了 B 個patch
```

條件1 跟條件3 表面上很像，但判斷邏輯不同：**條件3 是單純計數，不管內容像不像**；**條件1 是要看 patch 彼此之間有沒有「重複的味道」**——即使 patch 數量還不多，但只要重複結構已經濃到值得整理，就提早觸發；即使 patch 數量到了但彼此內容都不相關，估計省下空間趨近於 0，不會觸發。

Repack 只整理「合約 K」，不重新分析歷史 prose——論文原文：*"Repacking operates on the compact contract rather than all historical prose."*

## 4.6 Algorithm 2 完整流程

```
Algorithm 2 Zip-on-Write Continual Compression
輸入：狀態 Z_(t-1)，接受的patch Δt，repack政策η
輸出：更新後狀態 Z_t 與渲染出的 skill S̃_t

1: Bt ← ScanPatch(Δt)                掃描這個patch（跟步驟1類似，範圍小很多）
2: (At, Rt) ← ExtractPatch(Bt)       抽取patch的合約單元
3: Nt ← RetrieveCompatible(Z_(t-1), At)  只檢索"附近"的相容候選
4: Ht ← ProposeOps(At, Nt)           提出ABSORB/REFINE/EXTEND/REFACTOR候選
5: Z' ← LocalMinCostUpdate(...)      套用Eq.4，選增加最少的操作
6: AssertCoverage(Z', At)            檢查coverage
7: UpdateReuseStatistics(Z')         更新sidecar裡的約略計數
8: if RepackDue(Z', η) then          檢查是否觸發repack
9-12:   對整個compact contract重跑一次類似One-shot的候選搜尋+選擇
13: S̃_t ← Render(Z')                 render成文字
14: if AuditDue(Z') then             檢查是否該做structural audit
15:     執行audit+補回遺漏
16: Zt ← AtomicCommit(...)           原子性提交
17: return (Zt, S̃t)
```

**"範圍偵測(RetrieveCompatible)" 跟 "決定action(ProposeOps)" 是兩個獨立步驟**：範圍偵測只是縮小候選池，即使檢索出來什麼都沒找到（Nt 是空的），依然可以往下判斷 action——這種情況下最合理的結果通常是 EXTEND（附近沒有任何相關的既有單元，這個 patch 大概率是全新規則），甚至不用比較 Eq.4 增加多少，因為只有一個可行選項。

**AtomicCommit（原子性提交）**：確保萬一中途 crash，不會留下一半寫好一半沒寫好的狀態——這是系統可靠性層面的工程設計，跟前面的壓縮理論是不同層次的關注點。

---

# 第五部分：實驗結果

## 5.1 RQ1：Skill 在自我演化中膨脹多少（一句話帶過）

用 SkillOpt 這個既有的 skill 自我演化方法，跑到 Round 5，skill 長度在 BFCL-V4、LiveMath、SpreadsheetBench 上分別膨脹到約 5.6×、3.1×、6.7×，平均約 5.2×（**Fig. 4**，原文 caption：*"The skill growth tendency with respect to agent self-evolving progress for SkillOpt [2] and Memento-Skills [34]."*，圖裡另外畫了 Memento-Skills 這個方法的膨脹曲線做對比，但正文只針對 SkillOpt 給出具體倍數）。

## 5.2 RQ2：SkillZip 能不能保住保真度——這是最重要的結果表格

**Table I**（原文 caption：*"Compressed skill performance and average skill compression rate. The best task performance is shown in bold. Compression rate (C-Rate) is measured relative to the corresponding uncompressed evolved skill."*）比較了 3 個模型（Qwen-3.7-Max、Qwen-3.6-Plus、Kimi-K2.6）× 3 個 benchmark（BFCL-V4、LiveMath、SpreadsheetBench），共 9 個設定：

```
SkillZip壓縮率：27.1%–36.9%（平均31.2%）
SkillZip宏平均分數：0.577（未壓縮的evolved skill是0.570）
SkillReducer（baseline）壓縮率：平均9.2%，宏平均分數0.544
```

**逐設定看漲跌，最差案例挖出來**（壓縮後 - 未壓縮的差值）：

```
Qwen-3.7-Max：  BFCL-V4 -0.006 / LiveMath -0.002 / Spreadsheet -0.006  （三項全跌）
Qwen-3.6-Plus： BFCL-V4 +0.009 / LiveMath +0.043 / Spreadsheet +0.019  （三項全漲）
Kimi-K2.6：     BFCL-V4 -0.025 / LiveMath +0.024 / Spreadsheet +0.007  （最差案例在這裡）
```

**最差案例：Kimi-K2.6 在 BFCL-V4 上，從 0.772 掉到 0.747，掉了 0.025（絕對值），相對跌幅約 3.2%**。論文全篇沒有對這個個案做任何額外分析。9 個設定裡，有 4 個其實是變差的，這跟論文行文「沒有系統性下降」的正面敘述有落差——嚴格說是「沒有一致地下降，但確實有退步的案例」。

**一個值得注意、論文沒有明講的規律**：跌的三個案例全部發生在 Qwen-3.7-Max 這個模型身上（Qwen-3.7-Max 是三個模型裡 evolved skill 表現最好的，0.869/0.474/0.525 三項都是最高），這暗示壓縮對「原本 skill 品質已經很好」的情境風險可能較高——這是從數據排列推論出的規律，不是論文明講的結論。

**跟 SkillReducer 比較的公平性疑慮**：論文自己在 §VI.C 承認 SkillReducer *"is more naturally positioned as a first-pass debloating and quality-control method for general public skills"*——也就是說 SkillReducer 設計來處理的是「情境A」的冗餘（見 1.2 節），SkillZip 壓縮率大幅贏過 SkillReducer（31.2% vs 9.2%），某種程度上可能只是因為兩者設計目標不同、baseline 沒有選在同一個賽道上，不完全是純方法論優劣的差距。

## 5.3 RQ3：壓縮成本——SkillZip 真正紮實的優勢

**Table II**（原文 caption：*"Compression overhead of SkillZip and SkillReducer."*）：

```
SkillZip平均耗時：286秒
SkillReducer平均耗時：約1000秒
加速倍數：3.5倍

SkillZip所需task rollout：0
SkillReducer所需task rollout：40–80次（每次至少一次agent call）
```

SkillReducer 用的直接壓縮模型呼叫次數其實比 SkillZip 少（3次 vs SkillZip的4-8次），但額外要跑 40-80 次任務驗證的 rollout，這才是真正拖慢速度的主因。**這組結果是整篇論文工程價值最直接、最可驗證的體現**——「不用跑任何 task 就能壓縮」這件事，直接省下了 evaluation-guided compression 最貴的那部分成本。

## 5.4 RQ5：Zip-on-Write 的效果——直接驗證持續壓縮機制

**Fig. 6**（原文 caption：*"Skill length (by N×) during self-evolution on LiveMath for three agent backbones. Each panel compares no compression against Zip-on-Write continual compression activated at round 8 and at round 1; legends report the final test accuracy."*）在 LiveMath 上跑 16 輪自我演化，三個模型：

```
不壓縮：膨脹到 2.5×–3.7×
Zip-on-Write從第1輪就開啟：控制在 1.6×–1.9×（減少38%–50%）
Zip-on-Write第8輪才開啟：只能追回部分膨脹，追不上「從第1輪就開啟」的效果
                        （例如Kimi-k2.6：2.6× vs 1.9×）
```

準確率方面：round-1 配置（從頭就壓縮）的最終準確率，跟完全不壓縮的版本打平或略高，沒有新增額外的準確率疑慮。

**這個 RQ 最值得記住的一句洞見**（論文原文 Takeaway）：

> "redundancy is cheaper to prevent than to remove"

冗餘「預防」比「事後清除」便宜——越早開啟持續壓縮，效果越好，且不用等到膨脹了才回頭處理。這跟 Zip-on-Write 整體的設計精神（新增時就順手整理，不是等膨脹了才壓縮）完全對上，是這組實驗裡最有實務指導性的結論。

---

# 第六部分：值得帶走的東西

## 桶1：這篇論文本身的貢獻

拆開來看，論文用的每一個底層技巧都不是原創——這在整份筆記的每個技術段落都已經標出來了。所以論文本身的原創性貢獻並不大。但仍有幾點是這篇論文真正組裝出來、有實質價值的：

1. **把「skill是typed contract」這個框架，跟MDL objective結合，用hard coverage constraint取代task驗證來保證保真度**——這是整篇論文唯一真正新的理論貢獻（對應 Proposition IV.1 跟 Corollary IV.2：稀有規則的保留不取決於它在壓縮時的任務分佈裡出現頻率多高，而是取決於它有沒有被解析步驟抓到）。

2. **四個決策共用同一個長度比較骨架（Eq.5的四種展開），把equivalence/scope/workflow/exception四種不同性質的重複，統一成同一套判斷邏輯**——這是好的工程整合，不是新演算法。

3. **Zip-on-Write的局部更新等價性**（Proposition IV.2）：在沒有跨scope新reuse機會時，局部優化等於全域重跑，這個證明讓「只看附近」這件事有理論支撐，不只是一個工程捷徑。

4. **實證上，31.2%壓縮率+整體持平的準確率+3.5倍加速+零rollout**，這組數字本身是紮實的工程成果（即使也存在 Kimi-K2.6 在 BFCL-V4 上退步 3.2% 這種個案）。

5. **"redundancy is cheaper to prevent than to remove"**——這是 RQ5 裡少數真正被數據支撐、且有實務指導性的洞見。

## 桶2：通用、脫離這篇論文也成立的東西（這才是真正的收穫）

### 演算法/理論層

**Grammar-based compression（Re-Pair / SEQUITUR）與 BPE**：「define once, reference many」的 MDL 精神，現代最直接的應用就是 LLM tokenizer 的 BPE 演算法。完整走過的 cook/cooker/cookies/look 範例，跟「詞彙表只會變大、不會收斂成一個 token」這個釐清，是理解所有 LLM tokenizer 運作方式的基礎，用途遠超過這篇論文本身。詳見「[概念1](#概念1grammar-based-compression-與-bpe)」。

**Loop-invariant code motion**：「這段運算跟迴圈變數無關 → 搬到迴圈外只算一次」，是理解「為什麼有些重複可以安全提升到更高範圍」的通用心智模型，不只適用 skill，適用任何有巢狀結構的系統（設定檔繼承、物件導向的方法覆寫都是同一個邏輯）。詳見「[概念2](#概念2loop-invariant-code-motion)」。

**NLI（Natural Language Inference）**：entailment/contradiction/neutral 三分類，是 NLP 裡的經典任務；"frozen" 模型的意思（參數不更新、確保結果可重現），是理解任何「用一個現成分類器當判斷工具」架構的基礎知識。詳見「[概念3](#概念3nli-與-relation-checker)」。

**三個經典演算法模式，及各自適用的問題形狀**：
- DP：大問題可拆小問題，小問題答案能重複利用（爬樓梯類比）
- Weighted set-packing：候選互斥，要選出不衝突的最高價值組合（廣告時段排程類比）
- Clustering (Union-Find)：關係有連鎖性，要自動歸併成群（水果分堆類比）

這三個是解決「一堆候選要挑選/歸類」問題時最常見的三把工具，遇到類似的組合最佳化問題，可以先想「這比較像哪一種」。詳見「[概念4](#概念4三個組合最佳化工具dp--weighted-set-packing--clustering)」。

**MDL（最小描述長度原理）**：L(模型) + L(資料|模型) 的兩項式結構，是統計學/資訊理論裡「奧卡姆剃刀」的數學形式化，機器學習裡的正則化、決策樹剪枝、BIC 都是同一精神的不同實作。詳見「[概念5](#概念5mdl最小描述長度原理)」。

### 判斷框架層

**Relevance-based compression vs Redundancy-based compression**：prompt compression 靠「跟當下查詢的相關性」篩選；skill compression 沒有「當下查詢」可用，只能靠「這些內容是否在講同一件事」篩選。這個區分可以用來判斷任何「要不要壓縮/精簡一份文件」的情境該用哪種思路：有沒有一個明確、當下的使用情境可以拿來當篩選依據？有 → relevance 思路；沒有（要對所有未來情境都成立）→ redundancy 思路。詳見「[概念6](#概念6relevance-based-vs-redundancy-based-壓縮)」。

**「理解」與「決策」分離的架構設計原則**：LLM 只負責語意判斷（relation checker 貼標籤、結構抽取），確定性程式碼負責一切會影響最終結果的決策（成本計算、選擇、驗證）。這是任何想要「用 LLM 但保持結果可重現」的系統都該採用的分工原則，不只適用 skill 壓縮。詳見「[概念7](#概念7理解與決策分離的架構設計原則)」。

**Hard constraint vs soft objective 的設計選擇**：coverage 被設計成「不可違反的硬約束」而不是「盡量兼顧的加權項」，這個選擇本身決定了系統的失敗模式（寧可少壓縮，不可靜默遺失資訊）。這是任何要在「效率」與「正確性」之間做取捨的系統設計時，值得先問自己的問題：這裡的正確性該是硬約束，還是可以放進同一個目標函數裡加權？

---

# 附錄：核心背景概念完整說明

## 概念1：Grammar-based compression 與 BPE

**起源領域**：資料壓縮/文法推導（grammar induction），1990s–2000s 的經典理論 CS 主題。在 AI 領域雖然不常見有人直接用 Re-Pair/SEQUITUR 這兩個名字，但它們背後的精神——BPE（Byte Pair Encoding）——幾乎所有 LLM tokenizer 都在用。

**Re-Pair 核心想法**：反覆做「找出目前最常出現的相鄰兩個符號組合 → 合併成一個新符號」，直到沒有 pair 重複出現。

**SEQUITUR**：線上增量版，逐個符號讀入，維護兩個 invariant：(1) 任何 pair 不能重複出現超過一次，重複就立刻拆成新規則；(2) 每條規則至少要被用兩次以上，否則內聯刪掉。這會自然產生巢狀/遞迴文法。

**最簡單的例子**：

```
S = a b c a b c a b c   （長度9，"abc"重複3次）

發現重複片段 "abc" → 定義新規則：X -> a b c → 改寫成：S -> X X X

改寫後大小：規則本體X（3個符號）+ 主體（3次引用X，3個符號）= 6個符號
比原本9個短
```

**BPE 完整走一次**（跟論文內容無關，自己編的範例）：

假設語料裡只有4個字，出現次數如下：`cook_`出現6次、`cooker_`出現2次、`cookies_`出現3次、`look_`出現1次（`_`代表字尾結束的特殊符號）。

初始狀態每個字拆成單一字元：

```
cook_    -> c o o k _
cooker_  -> c o o k e r _
cookies_ -> c o o k i e s _
look_    -> l o o k _
```

第1輪：數所有相鄰字元對，乘上出現次數，最高的是 (o,o) 跟 (o,k)，並列12，選 (o,o) → 合併成 `OO`：

```
cook_    -> c OO k _
cooker_  -> c OO k e r _
cookies_ -> c OO k i e s _
look_    -> l OO k _
```

第2輪：(OO,k) 最高，次數12 → 合併成 `OOK`。第3輪：(c,OOK) 最高，次數11 → 合併成 `COOK`：

```
cook_    -> COOK _
cooker_  -> COOK e r _
cookies_ -> COOK i e s _
look_    -> l OOK _
```

只花3輪，「cook」這4個字元就被壓成1個token `COOK`，且這個token在3個不同的字裡被重複使用——這就是「define once, reference many」的具體樣子。

**釐清一個容易誤解的地方：詞彙表是「累積」的，不是「取代」的**。每做一次合併，是新增一個token到詞彙表裡，不是把舊的token刪掉、換成新的。跑完第3輪後，詞彙表是：`c, o, k, _, e, r, i, s, l, OO, OOK, COOK`，一共12個token，不是只剩`COOK`一個。這裡要區分兩個概念：

```
詞彙表（vocabulary）= 所有「合法token」的清單，是一份固定的字典
編碼結果（encoding）= 用詞彙表裡的token，把每一句話重新拼出來
```

`cook_` 這個字被編碼成 `COOK _`（兩個token），`cooker_` 被編碼成 `COOK e r _`（四個token）——每個字用到的token數量不一樣。字典會越編越厚，但字典本身不會因為你寫了一句話，就把字典裡其他字刪掉。

**為什麼不會一路合併到只剩一個token**：實務上會設一個「詞彙表大小」當煞車（例如5萬個token就停）。但即使不設煞車，繼續合併下去，能省的效益也會越來越低——語料裡不同的字彼此差異越來越大，重複出現的相鄰pair會越來越稀少，例如只出現1次的pair合併成新token完全沒有省到東西（定義一次要花成本，卻只用一次），這正好呼應 SkillZip Eq.9：`r=1`時，`L(def)+1×L(call)` 幾乎不可能小於 `L(q)`，不划算，演算法自然不會選它。

**三者關聯**：

```
Re-Pair    → 合併對象：任意符號序列（通用壓縮）
BPE        → 合併對象：字元/子詞（做LLM詞彙表）
SkillZip   → 合併對象：打了型別的技能規則/工作流程片段
```

## 概念2：Loop-invariant code motion

**起源領域**：編譯器最佳化，一般計算機科學背景知識。

**Invariant（不變的東西）**：在迴圈情境下，「loop-invariant」指這段運算，不管迴圈跑到第幾輪，算出來的結果都一樣——跟迴圈變數完全無關，只是剛好被寫在迴圈裡面。

**沒最佳化前**：

```
a = 5
b = 3
for i in 0..1000000:
    x = a * b          # 這行跟i完全無關
    result[i] = x + i
```

`a * b` 每一輪都被重新算一次，但因為`a`、`b`從頭到尾沒被改過，算1000000次跟算1次結果完全一樣，白算了999999次。

**編譯器自動偵測後搬移**：

```
a = 5
b = 3
x = a * b               # 搬出來了，只算一次
for i in 0..1000000:
    result[i] = x + i
```

行為完全不變，省下999999次重複運算。

**判斷是否可以搬的條件**：這段運算不寫入任何迴圈變數會改變的東西、不依賴任何迴圈內才會變的變數、搬到迴圈外不會改變程式行為（不能有副作用）。如果 `a` 或 `b` 在迴圈中途被改了，就不再是invariant，不能搬。

**跟 SkillZip 的 scope lifting（Eq.8）是同一個邏輯**：

```
迴圈裡的loop-invariant code motion：這段運算在每一輪迭代都一樣 → 搬到迴圈外，只算一次
SkillZip的scope lifting：這條規則在每個子分支都一樣 → 搬到共同父層scope，只寫一次
```

判斷條件也對得上：編譯器要求「每一輪都不變」，SkillZip 要求「每個相關的子路徑都需要這條規則」；編譯器如果中途被改就不能搬，SkillZip 如果某個分支有衝突，也不能整條搬走，得留下 exception。

## 概念3：NLI 與 relation checker

**起源領域**：自然語言推論（Natural Language Inference，NLI），NLP 裡一個經典任務，在 AI 領域非常常見。

**NLI 標準定義**：給你兩句話（premise前提、hypothesis假設），判斷邏輯關係，通常分三類：

```
entailment（蘊含）：premise為真，hypothesis一定也為真
                     例："今天下大雨" -> "今天天氣不好"
contradiction（矛盾）：兩句話互相衝突，不可能同時為真
                     例："今天下大雨" -> "今天萬里無雲"
neutral（中立）：兩句話沒有必然關係
```

**SkillZip 用的四分類跟 NLI 三分類是同一個家族，只是多切了一種**：

```
NLI標準三分類          SkillZip四分類
entailment      ────►  implication（單向蘊含）
                ────►  equivalence（雙向蘊含，entailment的特例）
contradiction   ────►  conflict
neutral         ────►  unrelated
```

**"frozen"（凍結）的意思**：這個分類器的參數在使用時完全不會被更新、微調，是拿一個訓練好的現成模型直接當工具用（跟 embedding index 用的向量模型一樣凍結不動）。之所以強調 frozen，是為了呼應「optimization is deterministic」——如果分類器參數會變動，同樣輸入在不同次執行可能給出不同答案，破壞確定性保證。

**Embedding index 是什麼**：先把每段文字轉成一串數字（向量），設計方式讓「意思相近的文字，向量也會相近」，把大量文字的向量事先算好存進一個資料結構，之後給一個新向量能快速找出「哪些向量離它最近」，不用逐一比對。這一步只能告訴你「兩者語意上接近」，沒辦法告訴你「接近到可以合併還是接近但互相衝突」，這就是為什麼還需要 relation checker 再判斷一次。

**論文用得算不算「輕」**：不算輕。NLI 標準任務通常判斷「兩個完整句子」的邏輯關係，SkillZip 這裡拿它判斷「兩個帶了scope、guard、modality標籤的規則」之間的關係，多了一層「先做結構篩選才丟進去問」的前置步驟（先過型別相容篩選），是合理的延伸，不是掛名裝飾。

## 概念4：三個組合最佳化工具——DP / Weighted Set-Packing / Clustering

### Dynamic Programming（動態規劃）

**跟論文無關的例子——爬樓梯**：每次可以爬1階或2階，樓梯共5階，問總共有幾種爬法？

DP的核心想法：把「爬到第N階，總共有幾種方法」的答案算過一次就存起來，之後遇到同樣的問題直接查表，不重算。

```
爬到第1階 = 1
爬到第2階 = 2
爬到第3階 = 爬到第1階 + 爬到第2階 = 1+2 = 3
爬到第4階 = 爬到第2階 + 爬到第3階 = 2+3 = 5
爬到第5階 = 爬到第3階 + 爬到第4階 = 3+5 = 8
```

適用條件：大問題可以拆成很多小問題，很多小問題其實是一樣的（會被問到很多次），大問題答案可以用小問題答案組合出來。

**對回 SkillZip**：DP 在 scope tree 上「由下往上」算，先算子節點自己的規則放置成本，存起來，回頭算父節點時：「如果把規則從兩個子節點都搬到父層，總成本會不會比各自保留更低」——用到的正是子節點已經算好、存起來的答案，不用重新掃過整棵樹。

### Weighted Set-Packing（帶權重的集合裝箱問題）

**跟論文無關的例子——排廣告時段**：一個晚上8點到11點的時段，好幾個廣告商想投放，但每個廣告有自己的起訖時間，時間重疊的不能同時播出，每個廣告出價不同，要選出總收入最大的組合。

```
廣告A：8:00-8:30，$100
廣告B：8:15-9:00，$150   （跟A重疊）
廣告C：9:00-10:00，$200
廣告D：8:30-9:30，$180   （跟C重疊）
廣告E：10:00-11:00，$120
```

重疊的候選只能選一個，要在有限、互斥的選項裡湊出總價值最高的組合。

**論文的近似解法（貪心+pairwise exchange）**：
1. 貪心：不是照「總價值高低」排序，是照「每單位覆蓋的token能省多少」排序，先選最划算的，選了就把跟它重疊的候選排除，重複直到選不出新的。
2. pairwise exchange微調：試著把已選的某一個候選換成另一個沒被選的，看總價值會不會變高，會就換，不會就維持原狀，反覆做直到換不出更好的組合。

**對回 SkillZip**：workflow候選的「不重疊」限制就是這個問題的具體版本——例如`[1]驗證->[2]修復->[3]驗證->[4]確認->[5]輸出`這條序列裡，候選A涵蓋`[1][2][3]`、候選B涵蓋`[2][3][4]`，兩者重疊在`[2][3]`，只能選一個，用「省下token/涵蓋token數」這個效率比率排序決定選誰。

### Clustering（分群，Union-Find）

**跟論文無關的例子——水果分堆**：根據某種相似程度，把一堆東西自動分成幾群，讓同一群裡的東西彼此相似。

**Union-Find 的連鎖合併特性**：

```
初始：每個東西自己一群 {C1} {C2} {C3} {C4} {C5}

看到"C1 equivalence C2"：合併 -> {C1,C2} {C3} {C4} {C5}
看到"C3 equivalence C4"：合併 -> {C1,C2} {C3,C4} {C5}
看到"C2 equivalence C4"：C2在{C1,C2}、C4在{C3,C4}，
                         這兩個群要合併成一個大群
                         -> {C1,C2,C3,C4} {C5}
```

即使原始關係只是兩兩配對，Union-Find 會自動處理連鎖效應。

**為什麼要先做conflict filtering才clustering**：如果relation checker還回報了"C1 conflict C5"這種不相容的關係，要先把這種pair排除，不讓它們進入union-find的合併名單——只有equivalence/implication的pair才能進入union-find，conflict的pair要走決策4那條路，不能混在一起處理。

**對回 SkillZip**：Union-Find分完群之後，同一群裡的所有規則最終會被合併成一份共用內容（決策1），如果這群規則分散在不同scope，DP接著決定共用內容該放在scope tree的哪個位置（決策2）。

### 三者比較

| | Dynamic Programming | Weighted Set-Packing | Clustering (Union-Find) |
|---|---|---|---|
| 通用問題形狀 | 大問題可拆成小問題，答案能重複利用 | 候選互斥，選出互不衝突、總價值最高的一組 | 一堆東西兩兩之間有關聯，自動歸併成幾群 |
| 關鍵特徵 | 後面的答案倚賴前面已算好的答案 | 候選會重疊/衝突，選了一個排擠另一個 | 關係有連鎖性 |
| 解法性質 | 精確解 | 近似解（貪心+微調） | 精確解 |
| 論文中對應子問題 | 決策2 scope放置 | 決策3 workflow候選互斥 | 決策1 equivalence群組歸併 |
| 對應公式 | Eq.8 | Eq.9 | Eq.7 |
| 生活化類比 | 爬樓梯 | 廣告時段排程 | 水果分堆 |

## 概念5：MDL（最小描述長度原理）

**起源領域**：1970年代末的資訊理論/統計學（代表人物 Rissanen），是「奧卡姆剃刀」（越簡單的解釋越好）的數學形式化版本。在機器學習裡非常常見的親戚：統計學的 BIC、決策樹剪枝、正則化（L1/L2懲罰項），背後都是同一精神的不同實作。

**核心直覺**（跟論文無關的經典例子）：一組資料點 `(1,1)(2,4)(3,9)(4,16)(5,25)`。

```
選項A：用簡單公式 y=x^2 描述 → 模型本身很短，殘差=0
選項B：用一個5次多項式硬湊，剛好穿過這5個點 → 模型本身很長（要記5個怪係數），殘差=0
```

兩者「準確度」一樣（殘差都是0），但總成本（模型描述長度+殘差描述長度）不一樣：選項A更短。**MDL選選項A**——即使準確度打平，選項A用更精簡的方式捕捉到資料裡真正的結構，選項B只是硬背答案。

**標準兩項式**：

```
總成本 = L(模型) + L(資料 | 模型)
```

`L(模型)`：描述這個模型本身要花多少篇幅；`L(資料|模型)`：在有了這個模型的前提下，還要多少篇幅才能完整描述資料（沒被模型解釋到的殘差）。

**對回 SkillZip Eq.4**：

```
論文Eq.4：  L(K) + L(R|K)
標準MDL：   L(模型) + L(資料|模型)

K(合約庫) 對應 模型
R(殘留)   對應 殘差/沒被模型解釋到的部分
```

`K` 扮演的角色跟「y=x^2這個公式」一樣，用最精簡的方式捕捉skill裡真正的結構性規律；`R` 扮演的角色跟「殘差」一樣，是沒辦法被規則庫解釋、必須原封不動保留的特殊內容。

**論文不是輕度借用**：不是隨口說「有點像MDL」，是直接把Eq.4寫成MDL的標準兩項式，四個決策（Eq.7-10）全部是這個式子在不同情境下的具體展開，論文自己在Related Work D節也明講了這個傳承關係。

**MDL在AI領域的其他常見身影**：決策樹剪枝（樹太複雜但準確度沒顯著提升就該剪）、正則化（懲罰過度複雜的模型參數）、Re-Pair/SEQUITUR（論文自己把它們歸為MDL精神的實例）、BIC（統計學裡比較模型好壞的準則，公式結構跟MDL幾乎一樣）。

## 概念6：Relevance-based vs Redundancy-based 壓縮

**Prompt compression 的典型情境**（例如 LLMLingua）：一篇長文件+一個具體問題，要 LLM 回答。

```
輸入：[一篇5000字的糖尿病維基百科文章] + 問題："第二型糖尿病怎麼治療？"

做法：根據"這個問題"估計每一段文字重不重要
     -> 治療相關段落：保留
     -> 病因、流行病學段落：低相關 -> 刪掉
```

這樣做合理，因為有一個明確的「當下問題」可以拿來當篩選依據。

**Skill 的情境不一樣**：skill 不是配合一個已知問題而寫的，是配合「未來任何一個屬於這個任務類別的問題」而寫的。skill 載入的當下，完全不知道等一下會被問什麼。如果套用 prompt compression 的邏輯（跟當下查詢相關性低就刪），今天問代數題時把「跟階乘有關的規則」判斷成低相關刪掉，明天問到階乘題目時，這條規則就是必要的，卻已經被錯誤刪掉了。

論文原文對應這個邏輯：*"Skills should be reusable for all queries of certain tasks... a reusable skill must retain requirements that no compression-time query activates."*

```
Prompt compression：有一個具體問題可以當篩選標準 → 判斷relevance
Skill compression： 沒有任何具體問題可以當標準 → 只能判斷redundancy
```

## 概念7：「理解」與「決策」分離的架構設計原則

SkillZip 整個系統的分工原則：

```
語意判斷（該分去哪一類）  → 交給LLM（步驟2的抽取器、relation checker）
數學判斷（划不划算、選哪個）→ 交給確定性程式碼（host驗證、Eq.5-10成本計算、
                              DP/weighted packing/clustering）
```

論文原文明講這個分工的用意：*"The extractor is deliberately not asked to compress. Separating interpretation from optimization has two benefits: contract recovery can be evaluated against human annotations, and the optimization is deterministic once the extracted units are fixed."*

兩個好處：
1. 抽取的品質可以獨立被檢驗（拿人工標註去對答案，不會被後面的壓縮邏輯干擾）。
2. 一旦抽取單元固定，後面「要不要合併」是純數學運算，同樣輸入一定得到同樣輸出，不會因為LLM隨機性讓每次壓縮結果不一樣。

這個原則不只適用 skill 壓縮——任何想要「借助LLM的語意理解能力，但又要求整個系統的最終行為可重現、可驗證」的場景，都值得採用這個分工：把「這是什麼、這兩者是什麼關係」這種需要語意判斷的部分交給模型，把「基於這個判斷該怎麼做」這種可以用明確規則表達的部分交給確定性程式碼。

---

（筆記完）