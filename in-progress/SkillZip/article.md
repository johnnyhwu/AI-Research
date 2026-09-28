# SkillZip：不用跑任務驗證，也能幫自我演化 Agent 的技能檔案瘦身

## 前言

自我演化（self-evolving）的 AI agent 有一個共通的副作用：用來記錄行為準則的 skill 檔案，會隨著使用時間越滾越大。工具呼叫失敗了加一條警告、輸出格式錯了補一個範例、某個罕見分支意外成功就記下這次流程。每次更新單獨看都合理，長期下來卻讓這份檔案變成一本只增不減的筆記本，而不是一份被整理過的程式。

這篇文章要介紹的 SkillZip，做的事情就是幫這份檔案瘦身，而且瘦身過程完全不用跑任何一次任務去驗證「壓縮完好不好用」，論文自己稱這個特性為 evaluation-free。做法是先把 skill 文字解析成一份「打了型別的合約」，再用「定義一次、到處引用」的邏輯把重複的部分收斂掉，同時用一條硬性規則保證原本每一條規則的意思壓縮完都還找得到。

先講結論：**這篇論文的工程價值高於研究價值**。裡面用到的每一項底層技巧（重複片段偵測、把共同規則搬到上層、拿分類器判斷兩句話的邏輯關係、動態規劃、集合裝箱、分群演算法）全部是電腦科學裡的經典技術，沒有一項是原創。真正的貢獻在於把這些技巧組裝成一個能落地的系統：不用任務驗證、壓縮速度比對手快 3.5 倍、平均壓縮率 31.2% 且整體不掉準確度。如果你在做 skill evolution 或 agent 記憶管理相關的實務工作，這篇論文的架構設計思路值得參考；如果是在找理論創新，這篇論文能給的不多。

在進入細節之前，先列三個貫穿全文、值得放在心裡的疑點：論文的保真度保證只保得住「解析步驟有抓到的東西」，前面漏抓的內容完全沒有機制能救回來；論文說壓縮「不犧牲準確率」，但九個測試設定裡其實有四個是退步的；論文拿來比較的對手 SkillReducer，設計目標其實是另一種完全不同的冗餘，兩者不完全站在同一個賽道上比較。這三點後面都會攤開來講。

---

## 一、問題：Skill 檔案為什麼越滾越大

### 1.1 現象：只增不減的筆記本

Self-evolving agent 的運作方式很直覺：工具呼叫失敗就加一條警告，輸出格式錯了就補一個範例，某個罕見分支意外成功就記錄下這次的流程。問題是每一次更新都是「加」，沒有人回頭做「減」，結果 skill 檔案被當成一本只增不減的筆記本在維護，而不是一份被整理過的程式。

論文用一個縱向實驗把這個現象量化出來。

![左邊橘線是 skill 檔案的總字數，隨自我演化輪數持續往上爬；藍線是真正獨特、不重複的合約內容量，爬到中段就趨於平緩，兩條線之間越拉越開的裂縫就是重複膨脹的部分。](img-001)
*圖1 — skill 總長度與「真正獨特的合約內容」隨自我演化輪數變化的落差。（來源：原始論文 Fig. 1。）*

圖裡有兩條線，橫軸是自我演化的輪數。橘線是 skill 檔案的總字數，一路往上爬；藍線是真正獨特、不重複的規則內容量，爬到中段之後就趨於平緩。兩條線之間越拉越開的裂縫，正是這篇論文要處理的目標：新增的文字量，遠遠超過新增的「真正新知識」量。

論文舉的例子很傳神：跑了夠多輪之後，「不要覆蓋原始檔案」這句話可能同時出現在開頭介紹、三個 workflow 分支、還有一個範例裡，同一件事講了四次。作者用 SkillOpt（一個既有的 skill 自我演化系統）實際測了膨脹速度：跑到第 5 輪，skill 長度在 BFCL-V4、LiveMath、SpreadsheetBench 三個測試集上分別膨脹到約 5.6 倍、3.1 倍、6.7 倍，平均約 5.2 倍。五輪之內，skill 檔案平均就已經比一開始重了五倍以上。

### 1.2 兩種「長」不是同一種問題

論文特別區分了兩種會讓 skill 檔案變長的情況，這個區分之後會決定「該用什麼邏輯瘦身」。

第一種情境是一般公開、社群寫的教學型 skill。這種 skill 通常混雜了背景說明、多餘的範例，跟真正執行無關的參考資料：

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

「什麼是 API」「為什麼選這個服務」跟「怎麼執行這個任務」完全無關，刪掉它們，agent 照樣能查天氣，不會漏掉任何執行所需的規則。這種冗餘的判斷依據是 relevance，跟執行相不相關。

第二種情境是多輪自我演化出來的 skill，情況完全不同。這種 skill 的每一條新增內容，都是被 rollout 回饋驗證過才被接受的：

```
第 3 輪：查詢城市名有空格時（例如 "New York"）沒編碼，API 回傳 400 錯誤
        → agent 加了一條：「城市名有空格時要做 URL encode」

第 7 輪：查詢不存在的城市名時，API 沒有丟錯誤，而是回傳空的 JSON，
        導致 agent 誤判為「晴天」
        → agent 加了一條：「查完後要檢查回傳的 JSON 是否為空」

第 12 輪：另一個分支（批次查詢）又重新踩到「城市名要 URL encode」
         這件事，加了一次幾乎一樣的話，只是措辭不同
```

「城市名要 URL encode」跟「空 JSON 要視為失敗」，每一條單獨看都是真的、必要的、跟執行高度相關，不是可以砍掉的離題內容。但同一件事在第 3 輪跟第 12 輪各講了一次。這裡不能靠「這段跟執行有沒有關係」來判斷要刪誰，因為兩段都相關；能判斷的是「這兩段其實在講同一件事，可以合併」。這種冗餘的判斷依據是 redundancy，有沒有重複，而不是 relevance。

論文拿來比較的 baseline「SkillReducer」，設計來處理的正是第一種情境：用 delta debugging 去蕪存菁，搭配任務驗證。SkillZip 瞄準的則是第二種情境。這個差異在後面看實驗數字時要一直記著：兩者原本瞄準的就不是同一種冗餘。

### 1.3 為什麼不能直接套現成的 prompt compression 工具

一個很自然的問題是：既有的 prompt compression 工具（例如 LLMLingua）能不能直接拿來用？答案是不行，而且理由很直接：prompt compression 靠的是「這段文字跟當下這個查詢的相關性」去篩選要不要留，但 skill 必須對「所有未來可能的查詢」都保持有效。skill 被載入的當下，完全不知道等一下 agent 會被問什麼。既然沒有一個「當下的查詢」可以拿來當篩選依據，prompt compression 那套邏輯在 skill 這個情境下根本用不上。這個對比在文章後段「延伸」的部分會再展開，因為它是個比這篇論文本身更通用的判斷框架。

---

## 二、核心方法：把 Skill 看成一份「打了型別的合約」

SkillZip 的基本主張是：一份 skill 不是一段平坦的文字，而是一份合約（contract）。合約裡不同的句子管的是完全不同的東西，這件事直接決定了「改動它們的安全規則」不一樣。

![SkillZip 整體架構圖：左半邊是一次性的 One-Shot Compression，從完整技能出發，掃描還原打了型別的合約，套用「解釋一次、到處引用」的原則消除重複；右半邊是 Continual Compression Zip-on-Write，每次收到新的修補就跟合約鄰域比對，需要時才觸發整份重新打包。](img-003)
*圖2 — SkillZip 的兩種運作模式：一次性壓縮（One-Shot）與持續壓縮（Zip-on-Write）。（來源：原始論文 Fig. 3。）*

整篇論文接下來要講的東西，基本上都是這張圖的展開：左半邊是拿一份完整、已經膨脹的 skill 去做一次性壓縮，右半邊是每次收到一個小修補，就順手做局部整理，不用等到膨脹了才回頭處理。這一節先講兩邊共用的核心基礎，也就是合約怎麼定義、怎麼判斷划不划算合併；下一節再講一次性壓縮的完整流程，之後再講持續壓縮模式。

### 2.1 六個型別，一份合約

![六個色塊分別代表合約的六個組成部分：Interface、Workflow、Tool protocol、Scoped rules、Output contract、Evidence，中央用箭頭串出「使用者問題觸發、依序執行、呼叫工具、檢查規則、檢查輸出」的主線，Evidence 則貼在旁邊作為輔助說明。](img-002)
*圖3 — 一份 skill 被拆解成六種型別的合約元件，各自管不同的執行面向。（來源：原始論文 Fig. 2。）*

論文把這份合約寫成 $C(S) = \langle I, G, T, C, O, E \rangle$（論文 Eq. 1），六個組成部分分工如下：

| 符號 | 全名 | 管什麼 | 具體例子 |
|---|---|---|---|
| $I$ | Interface（介面） | 這個 skill 叫什麼、何時該被觸發、何時不該被觸發 | 「觸發：使用者問天氣」「排除：使用者問氣候變遷歷史」 |
| $G$ | Workflow（工作流程） | 執行順序、分支、迴圈、失敗時怎麼辦、什麼時候算做完 | 「先查城市代碼 → 再查天氣 API → 若失敗重試一次」 |
| $T$ | Tool protocol（工具協定） | 呼叫哪個工具、要帶什麼參數、前提條件、回傳格式、錯誤處理 | 「呼叫 get_weather(city_code)，city_code 必須先做 URL encode」 |
| $C$ | Scoped rules（有範圍的規則） | 「必須／不可以／建議」做什麼，且這條規則只在哪個範圍、哪個條件下成立 | 「（範圍：批次查詢分支）不可以一次查超過 10 個城市」 |
| $O$ | Output contract（輸出合約） | 回傳格式、必填欄位、欄位順序、驗證方式、什麼時候算完成 | 「輸出必須是 JSON，含 temperature、condition 兩個必填欄位」 |
| $E$ | Evidence（佐證） | 範例、範本、把某個決定講清楚的理由 | 「範例：查台北天氣的完整輸入輸出」 |

這六塊的分工，用一張簡單的流程可以表示：使用者問題進來後，先由 $I$ 判斷要不要觸發，接著 $G$ 依序執行步驟並呼叫 $T$ 指定的工具，過程中 $C$ 負責檢查規則有沒有違反，工具回傳結果後由 $O$ 檢查輸出格式。$E$（範例、佐證）不在這條主線上，是貼在其他五塊旁邊幫忙解釋的輔助說明。

這個拆解不是為了歸檔好看，而是決定「兩句話能不能合併」的安全依據。論文原文舉了三個例子：同一個工具、但要求參數不同的兩句話不能合併，因為要求的參數不同，硬合併會漏掉其中一個要求；每個分支都有的規則，可以搬到共同的父層（這就是後面會講的 scope lifting）；只掛在某一個分支上的規則不能搬，搬到父層會讓範圍變大，變成一條錯誤的規則。

### 2.2 從六型別到 JSON：抽取後的實際結構

結構化抽取後，合約用一份 JSON 表示，最外層有 8 個欄位（論文 Appendix C）：`interface`、`scopes`、`workflow`、`rules`、`output`、`evidence`、`shared_procedures`、`residual`。前六個大致對應六型別。

其中 `scopes` 是輔助用的範圍樹，不算獨立型別；`shared_procedures` 存放已經被抽出來的共用流程；`residual` 存放抽取信心不足、原封不動保留的殘留內容，下一節會細講。

每個外層欄位底下是陣列，每一筆資料各自有自己的 schema，且都帶著 `spans`（或 `source_blocks`）欄位，記錄它是從原文哪個或哪幾個區塊抽出來的。這個對應關係是多對多的：一筆抽取單元可能同時引用好幾個原文區塊（例如條件在一處、規則本身在另一處），一個原文區塊也可能被拆成好幾筆不同的抽取單元。

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

`spans` 這個欄位就是可追溯性（provenance）機制的核心，理論上每一個後續的壓縮決策，都能回溯到「原文哪一塊」。

### 2.3 形式化目標：用 MDL 寫成一條算式

SkillZip 用一個庫 $K$（reusable contract elements，可重用的合約元素）加上一個殘差 $R$（unique, exceptional, or uncertain content，獨特、例外或不確定的內容）來表示壓縮後的 skill。目標式（論文 Eq. 4）是：

$$(K^*, R^*) = \arg\min_{(K,R)} L(K) + L(R \mid K)$$

限制條件是：對所有 $a \in A_{req}(S)$，都必須滿足 $a \preceq (K,R)$。

翻成白話：**在「不能弄丟任何規則」的前提下，找出總長度最短的表示方式**。$a \preceq (K,R)$ 讀作「單元 $a$ 被 $(K,R)$ 涵蓋」，這是硬性約束（hard constraint），不是可以打折扣的加權項。即使某個合併方案能省下大量 token，只要它會導致任何一個原本抽出的必要單元變得沒被涵蓋，這個方案就直接不合法。

長度 $L(x)$ 本身怎麼算，論文 Eq. 6 給出：

$$L(x) = |\text{Render}(x)|_{tok} + \gamma_{def}(x) + \gamma_{ref}(x) + \gamma_{scope}(x)$$

其中 $|\text{Render}(x)|_{tok}$ 是把 $x$ 轉成文字後的 token 數；$\gamma_{def}(x)$ 是如果 $x$ 是「定義一個新規則或新流程」要額外付的成本（取名字、寫清楚範圍）；$\gamma_{ref}(x)$ 是如果 $x$ 是「引用某個已定義好的規則」要付的成本（比重寫便宜，但不是免費）；$\gamma_{scope}(x)$ 是表達「這條規則適用範圍」要付的成本。這四項加總的用意是防止演算法耍小聰明：如果「定義加引用」的成本比「直接重複寫兩次」還貴，那乾脆不要合併，原地保留反而比較省。

### 2.4 抓不準的內容：locked residual

步驟 2（下一章會細講）用一個受 schema 約束的 LLM 把原文轉成結構化合約，如果某段原文的型別或範圍判斷不準，系統不會勉強把它塞進六型別的某一類，而是整段原封不動放進 `residual`，並標記 `locked=true`：

```
原文：「這裡的行為比較特殊，建議依照經驗調整」
→ 不是明確規則（沒有明確的 must/must_not）
→ 也不是明確的 workflow 步驟或輸出格式要求
→ LLM 判斷不出該歸哪一類
→ 整句原封不動放進 residual，鎖住
```

被鎖住的內容不會被拿去跟其他東西合併、不會被優化、也不會被刪除，會直接原封不動出現在最終輸出裡。這是整個系統「保守失敗」設計哲學的具體實作：寧可保留一段看不太懂的原文，也不要冒險把它硬塞進某個型別，結果塞錯導致資訊遺失或誤判。

### 2.5 四個決策：同一條骨架的四種展開

同一個 Eq. 4 的骨架，套用在四種不同的重複結構上，展開成四條判斷式。每一條的共同邏輯都是：**省下的（不合併時要各自付的代價）大於多付的（定義成本加引用成本加殘差成本），才值得合併**。

**決策1：同義敘述合併（Eq. 7）**

$$L(z) + L(x_1 \mid z) + L(x_2 \mid z) < L(x_1) + L(x_2)$$

$x_1$、$x_2$ 是兩句內容幾乎完全一樣的話，$z$ 是合併後只留一份的共用版本，$x_1 \mid z$ 跟 $x_2 \mid z$ 是合併後 $x_1$、$x_2$ 各自「還需要額外交代的差異」，如果兩者幾乎完全一樣，這兩項會接近 0。

論文自己給的真實例子出自 Appendix E，是 LiveMath skill 壓縮前後的對照：壓縮前這段話逐字重複出現兩次——「If the problem asks for a single specific value (e.g., maximum, minimum, unique solution) or implies a unique answer, output ONLY that single valid value. Strictly discard any extraneous candidates, negative roots, or intermediate results that do not satisfy all constraints...」壓縮後只出現一次，且用詞更精簡。以下是這個例子的示意估算（不是論文報告的精確數字，論文只給了整份 skill 936 到 638 token 的總數，這裡是為了展示判斷式怎麼用而做的粗略估計）：

```
L(x1) ≈ 55 字，L(x2) ≈ 55 字 → 不合併的總成本 ≈ 110
L(z) ≈ 45 字（合併後精簡版），殘差 ≈ 0（兩句幾乎完全一樣）
判斷：45 < 110 → 划算，合併
```

**決策2：規則搬到共同父層，Scope lifting（Eq. 8）**

$$L(c@u) + r \cdot L(\text{scope-ref}) < \sum_{i=1}^{r} L(c@s_i)$$

$c@s_i$ 是規則 $c$ 掛在子分支 $s_i$ 底下的樣子，$c@u$ 是規則 $c$ 改寫成掛在共同父層 $u$ 底下的樣子（通常比掛在單一分支下多花一點 token，因為要交代清楚「對所有子分支都成立」），scope-ref 是每個子分支留一個小小的繼承標記。延續天氣查詢 skill 的例子，示意數字如下：

```
搬移前（3個分支各自寫一次「城市名要 URL encode」）：
  Σ L(c@sᵢ) = 12+12+12 = 36

搬移後（搬到共同父層，3個分支各留一個繼承標記）：
  L(c@u) + 3·L(scope-ref) = 15 + 3×1 = 18

判斷：18 < 36 → 划算，搬
```

安全前提是論文原文明講的：只有「每個相關的子路徑都真的需要這條規則」且「所有局部衝突都被編碼成 exception」時才能搬。如果某個分支其實不需要這條規則，硬搬上去會變成這條規則錯誤地套用到那個分支，即使數學上划算，也不能做。這個判斷式跟編譯器裡的 loop-invariant code motion（把迴圈裡不變的運算搬到迴圈外）是同一個邏輯，後面延伸段落會細講。

**決策3：重複流程共用，Workflow reuse（Eq. 9）**

$$L(\text{def}(q)) + r \cdot L(\text{call}(q)) < r \cdot L(q)$$

$q$ 是一段重複出現的動作序列（例如「驗證輸入 → 呼叫 API → 失敗就重試 → 解析結果」），$r$ 是 $q$ 在整份 skill 裡不重疊地出現了幾次，$\text{def}(q)$ 是把 $q$ 定義成一個有名字的共用流程要花的 token（含取名字加交代進出條件），$\text{call}(q)$ 是之後每次用到它時只需要引用這個名字要花的 token。論文原文只描述了現象——「the same validate–repair–verify sequence is copied repeatedly with only minor differences」——沒有給具體 token 數字，以下是自行編的示意：

```
搬移前（3個分支各自完整寫一次驗證-修復流程，每次20字）：
  r · L(q) = 3×20 = 60

搬移後（定義一次24字，每次引用6字）：
  L(def(q)) + 3·L(call(q)) = 24 + 3×6 = 42

判斷：42 < 60 → 划算，共用
```

候選要能被提名，必須滿足兩個限制：不重疊（同一段文字不能同時被算成兩個不同候選的一部分），以及進入退出行為一致（幾個分支裡這段流程執行前的前提、執行完銜接的下一步要一樣）。論文 render 階段還有一個實務判斷——原文是「A shared workflow is named only when references save tokens; otherwise it remains inline.」——即使 Eq. 9 數學上划算，如果 $r$ 太小、流程很短，取名成本可能吃掉大半省下的空間，這時系統會選擇不特別命名，保持內聯。這個判斷式的精神，跟 grammar-based compression 演算法、以及 LLM tokenizer 用的 BPE 演算法是同一個「define once, reference many」邏輯的不同應用，後面延伸段落會走一次完整的 BPE 範例。

**決策4：通則加例外，Guarded variants（Eq. 10）**

$$L(c) + \sum_i L(\delta_i) < \sum_i L(c_i@g_i)$$

$c_i@g_i$ 是第 $i$ 個帶條件的規則版本（$g_i$ 是成立條件，$c_i$ 是規則內容），$c$ 是這些版本的共同核心，$\delta_i$ 是第 $i$ 個版本跟通則 $c$ 之間剩下的差異。這條判斷式跟決策1的骨架完全一樣，差別只在於決策1是決策4的特殊情況（差異部分 $\delta_i$ 剛好接近 0，因為內容根本沒差異），決策4則是更一般的情況，允許每份留下一段不能被抹掉的真實差異。示意數字（天氣查詢 skill 的城市數量上限規則）：

```
合併前（3個分支各自的城市數量上限規則）：
  Σ L(cᵢ@gᵢ) = 12+14+12 = 38

合併後（抽出共同核心「查詢有城市數量上限」，各自留下差異）：
  L(c) + Σ L(δᵢ) = 8 + 6+9+6 = 29

判斷：29 < 38 → 划算，用「通則+例外」表示
```

這裡有一個論文沒交代清楚的地方：怎麼從多個版本裡抽出這個共同核心 $c$，論文完全沒有給出具體演算法或 prompt，只在方法章節步驟3提到 relation checker 會把這類配對判斷成 conflict、送去產生 exception candidate，但「conflict 判斷完之後怎麼生成 $c$」這一步的機制沒有明講。這也是四個決策裡最容易出錯的一個：如果三個分支的規則其實有隱藏的細微差異，但抽共同核心這一步沒抓到、被錯誤合併成同一個 $c$，會發生「某個分支原本該有的限制被通則覆蓋掉」的情況。這種錯誤不會被覆蓋約束抓到（因為從 $K$ 的角度看，規則「有被涵蓋」），但實際行為已經跟原本不一樣了。

四個決策的差異整理成一張表方便對照：

| | 決策1 同義合併 | 決策2 Scope lifting | 決策3 Workflow reuse | 決策4 通則+例外 |
|---|---|---|---|---|
| 論文式子 | Eq.7 | Eq.8 | Eq.9 | Eq.10 |
| 判斷式結構 | $L(z)$+殘差 < 各自總和 | $L$(搬父層)+$r\cdot$標記 < 各分支總和 | $L$(定義)+$r\cdot L$(引用) < $r\cdot L$(原長) | $L$(共同核心)+差異總和 < 各版本總和 |
| 觸發情境 | 兩句話完全同義 | 同一規則重複出現在多個子分支 | 同一段動作序列重複出現 | 多個版本部分相同、部分不同 |
| 主要對應合約型別 | 不限（$C$ 最常見） | $C$（scoped rules） | $G$（workflow） | $C$（scoped rules） |
| 合併後殘差是否為0 | 幾乎是0 | 用 scope-ref 標記取代 | 用 call(q) 取代 | 不為0，每份都留差異 |
| 安全前提 | modality/guard 完全一致 | 每個相關子路徑都真的需要這條規則 | 進入/退出行為一致+不重疊 | 差異必須完整收進 $\delta_i$，不能漏 |
| 候選重疊時的處理演算法 | Union-Find clustering | Dynamic Programming（scope tree上） | Weighted set-packing | 論文沒有給出演算法名稱 |
| 最容易出錯的地方 | 表面像但modality不同，誤判可合併 | 誤判某分支其實不需要這條規則 | 進出行為看似一致，實際有隱藏差異 | 抽共同核心時漏掉某分支獨有的限制 |

### 2.6 兩道關卡：六型別怎麼跟四決策接起來

六型別不是「決策的分類依據」，而是「決策能不能套用的篩選閘門」。**六型別決定「這兩個東西夠不夠格被拿來比較」，四個決策才是「比較完之後，划不划算」的數學測試**。兩者是先後兩道關卡，不是平行的兩套分類：原始文字先被掃描抽取成六型別單元，接著過第一道關卡（型別相容篩選，只有同型別且細節相容的才能配對），過關的才輪到套用四個決策式算划不划算，最後選出最省的組合。

方法章節步驟3明講了五條型別相容篩選規則：$I$（介面）要同樣是 trigger 或同樣是 exclusion 角色才能比；$C$（規則）要 modality、predicate family、scope ancestry 都相容才能比；$T$（工具）要同一個工具名稱加參數簽章相容才能比；$O$（輸出）要同一種 response type 加同一個欄位命名空間才能比；$G$（流程）走的是完全獨立的路，從重複的、有相同 guard 的動作序列裡找，不經過上面這套比對機制。

過關的候選才輪到套用對應的決策式：

| 型別 | 過關卡1的規則 | 能套用哪個決策 |
|---|---|---|
| $I$ 介面 | 同角色 | 決策1 |
| $C$ 規則 | modality+scope相容 | 決策1、決策2、決策4，唯一同時吃到三個決策的型別 |
| $T$ 工具 | 同工具+參數相容 | 決策1（但參數不同就不能合併） |
| $O$ 輸出 | 同類型+同命名空間 | 決策1 |
| $G$ 流程 | 獨立序列比對機制 | 決策3（不經過relation checker） |
| $E$ 佐證 | 不在上述清單裡 | 沒有專屬決策，用另一套「覆蓋測試」判斷能不能整段刪除 |

$E$（佐證）是個特例：判斷依據不是「跟別的範例像不像」，而是「這個範例講的東西，其他地方（通常是 $O$ 或 $C$）有沒有已經寫清楚」，呼應前面圖2 caption 裡「an example is removable only when every requirement it uniquely expresses is represented elsewhere」那句話。走的是覆蓋測試，不是 Eq.7 到 Eq.10 那四條省 token 公式。

還有一個論文沒有交代清楚的地方：決策2（scope lifting）在方法章節步驟3的五條規則裡沒有獨立列出。它其實不是靠 relation checker 判斷出一種獨立的關係，而是候選池 A（equivalence 群組）在步驟4被動態規劃加工後，順帶決定的一種「安放形式」。也就是說，步驟3直接生成的候選身分只有三種：equivalence/implication、conflict、workflow重複；決策2是 equivalence 候選在步驟4的其中一種可能呈現方式，不是步驟3就分好的第四種候選。

---

## 三、One-Shot SkillZip：完整流程走一次

方法章節把整個一次性壓縮流程拆成 5 個子步驟，對應論文的 Algorithm 1：

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

### 3.1 步驟1：掃描（純規則式，不用 LLM）

第一步完全不用 LLM，是純規則式的解析器（論文 Appendix B）。它做的事情包括：

- 把 skill 文件拆成一塊一塊帶 ID 的區塊，區塊 ID 是「正規化後文字內容加上層標題路徑」的雜湊值，不是行號。行號會因為前面插入新內容而跑掉，雜湊值不會。
- 把 Markdown 的巢狀標題結構先轉成初步的 scope tree，scope 路徑長這樣：`["root", "workflow", "if-validation-fails"]`。
- 抓「編號清單」跟「時間性字眼」（例如「先...再...然後...」）當作高信心的 workflow 線索。
- 把 code block 跟表格當成不可切割的最小單位。

為什麼要先做這一步、不直接丟給 LLM？能用規則解決的結構，像標題層級、編號清單，就不要浪費 LLM 的判斷力去猜，一方面省成本，另一方面每個後續決策都能回溯到「原文哪一塊」。一條規則要從「掛在某個小分支底下」升級成「掛在更大範圍底下」，需要文字裡有明確線索：用詞像 "always"、"for every request" 這種明確宣稱全域適用的字，或者這條規則在好幾個相關的子節點下都重複出現。

> 這是從論文行文推論出來的一點，論文全文沒有正面處理過：步驟1的機制骨幹是「Markdown 巢狀標題轉初步 scope tree」跟「編號清單或時間字眼轉 workflow 線索」，如果輸入不是 Markdown 格式、是一整段沒有標題沒有清單的純文字，這兩個線索來源都不存在，步驟1大概率抓不到什麼結構。這會連帶影響步驟5的 audit 機制，因為 audit 依賴每個抽取單元都有 spans 可以回頭核對，如果純文字輸入導致步驟1切出來的區塊太粗，可追溯性的精細度會下降。

### 3.2 步驟2：還原打了型別的合約

把步驟1切好的編號區塊，丟給一個受 schema 約束的 LLM，請它輸出前面 2.1 節那份合約。這一步的輸出不是文字，是結構化的 JSON。

論文原文明講了四種會被拒絕的錯誤，而且是由確定性的 host 程式檢查，不是另一個 LLM：unsupported citations，抽出來的東西找不到對應來源區塊 ID；polarity mismatch，必須或不可以的方向抽反了；unknown tool names，抽出的工具名稱不在任何來源區塊裡出現過；invalid workflow references，流程節點指向一個不存在的下一步。其中第 1、3、4 項，host 用純粹的 ID 或字串比對就能做到，不需要理解語意：檢查引用的 block ID 存不存在是集合查找、檢查工具名稱有沒有出現在來源文字裡是字串包含、檢查流程節點指向的下一步存不存在是圖的節點是否存在。**第 2 項（polarity mismatch）論文完全沒有交代具體怎麼檢查**。這牽涉到要理解原文那句話的語意，沒辦法只靠 ID 比對完成，論文也沒說這一步有沒有計入成本統計表報告的 LLM calls 裡面。

為什麼要把「理解」跟「壓縮」拆成兩個獨立步驟？抽取器（步驟2）被刻意要求不做壓縮判斷。這麼做有兩個好處：合約抽取的品質可以獨立被檢驗，拿人工標註去對答案；優化步驟一旦抽取單元固定，就是純數學運算，同樣輸入一定得到同樣輸出，不受 LLM 隨機性影響。這個「理解與決策分離」的原則後面延伸段落會再深入談。

### 3.3 步驟3：提名候選

這一步只是「提名」候選，還不決定要不要真的合併，分成兩個小階段。第一階段是結構篩選，套用 2.6 節的五條型別相容規則，過濾掉明顯不可能配對的組合。第二階段是 embedding 檢索加 relation checker 判斷關係：先用 hashing 找出正規化後一字不差的精確匹配；再用 embedding index 找出語意上接近的近似匹配候選（快、粗略），然後用一個 frozen 的 relation checker（NLI-like 的分類器）細判斷關係：equivalence 進候選池 A（可能合併）；implication 也進候選池 A（論文沒明講 implication 具體怎麼被用）；conflict 進候選池 B（可能變成通則加例外，不是被丟棄）；unrelated 或低信心的就直接丟棄。

Workflow（$G$ 型別）走完全獨立的路，不經過型別篩選也不經過 relation checker，是靠「重複的、有相同 guard 的動作序列」做獨立的序列比對，自成候選池 C。

### 3.4 步驟4：選出最短的涵蓋解釋

這一步分三個動作。動作一：每個候選先算一次 $\text{save}(h) = L(\text{separate form}) - L(\text{form using } h)$（Eq. 5，這是 Eq.7 到 Eq.10 的通用骨架），$\text{save}(h) \le 0$ 的候選直接丟棄。這一步只回答「單獨看，這個候選划算嗎」，不代表「這些都划算的候選能同時執行」。候選之間可能互相搶用同一批原始單元，不能兩個都選。

動作二：不同候選池用不同演算法解決「候選互相排擠」的問題。候選池 A（equivalence/implication）先做 conflict filtering，再用 Union-Find clustering 歸群，若群組跨 scope 分佈，再用動態規劃決定放在 scope tree 哪一層；候選池 B（conflict）套 Eq.10，但論文沒給出候選互斥時的排序演算法；候選池 C（workflow重複）用 weighted set-packing，貪心按效率排序加 pairwise exchange 微調。這三種工具的完整原理，後面延伸段落會各自用一個跟論文無關的例子走一次。

動作三：每選定一個候選，立刻重新檢查 coverage，也就是原本每一條規則的意思，在目前選定的 $K$ 裡還找得到嗎？找不到就撤銷這個候選。

論文自己給了一個把三個決策放進同一個 running example 的具體例子：「The two branch-local copies of "never overwrite the input" are represented by one rule at their common parent because Eq. (8) is satisfied. The validate step is shared only if its definition and calls are shorter than the copies. The JSON example is removed only after its fields are covered by the output contract.」翻成對照表就是：兩個分支各寫一次「不要覆蓋輸入」，走的是決策2 scope lifting；validate 步驟走的是決策3 workflow reuse；JSON 範例被刪除，走的是 $E$ 的覆蓋測試，前提是欄位已經被 $O$ 涵蓋。

下面這張表把步驟3到步驟4的整條決策流程串起來，值得記住：

| Step3 候選來源 | Step3 判斷機制 | Step4 呈現形式 | 對應公式 | 候選重疊時的處理演算法 |
|---|---|---|---|---|
| equivalence/implication 候選 | 結構篩選+embedding檢索+relation checker | 單純合併 | Eq.7 | Union-Find clustering |
| ↳ 同一批候選，若群組跨scope分佈 | （沿用同一批判斷結果，不是獨立生成） | 搬到共同父層 | Eq.8 | Dynamic Programming |
| conflict 候選 | 結構篩選+embedding檢索+relation checker | 通則+例外 | Eq.10 | 論文沒有給演算法名稱 |
| workflow重複候選 | 獨立序列重複偵測，不經過結構篩選 | workflow共用 | Eq.9 | Weighted set-packing |

### 3.5 步驟5：渲染與結構稽核

Render 這一步用固定樣板（不是 LLM）把最終決定的合約 $K$ 轉回一份正常的 skill 文字，內容包含簡潔的 purpose 與 triggers、全域規則、編號 workflow、巢狀的 guarded 分支、明確的工具要求、輸出 checklist。共用 workflow 只有在「引用確實比內聯省 token」時才特別命名，否則保持內聯。

結構稽核（可選）的做法很巧：找一個「盲測」的 audit parser，完全不給它看原始 skill、也不給它看選定的合約 $K$，只給它看 render 完的最終文字，請它獨立重新解析一次，得到一份新的合約 $\hat{K}$。拿 $\hat{K}$ 跟原本的 $K$ 做 diff，如果 $\hat{K}$ 缺了某個 trigger、guard、workflow edge、tool argument、polarity 或 output field，代表這些資訊在 render 或抽取過程中被遺失了，就從原文 restore 能涵蓋這個缺失項目的最短片段，補回最終文字，並鎖住不准後續刪除。這一步的用意，是用「完全不看原文、只看最終渲染結果」的獨立視角，反向驗證這份最終文字是否真的完整表達了 $K$ 要表達的東西。

---

## 四、Zip-on-Write：持續壓縮模式

### 4.1 為什麼需要一個「持續」模式

Self-evolving agent 實際運作是不斷收到小 patch，一次修正、一次新增，不是整份重寫。如果每次都重跑一次完整的 One-Shot 流程，成本會隨 skill 越變越大而越來越貴。Zip-on-Write 要解決的問題是：只處理這次新增的 patch，不用把整份 skill 重新分析一次。

### 4.2 Sidecar 機制

論文原文：「SkillZip stores a sidecar, skillzip.json, containing the current contract, source provenance, scope tree, workflow graph, and candidate indices. The rendered SKILL.MD remains the only artifact loaded by the agent.」

換句話說，SkillZip 維護兩份東西：`skillzip.json` 這個 sidecar 存的是結構化的內部狀態，包括目前的合約 $K$、來源 spans、scope tree、workflow graph、候選索引，agent 本身不會讀這個檔案，這是 SkillZip 自己維護的工作記憶；`SKILL.md` 是渲染出來的最終文字，是 agent 實際載入、實際讀取的東西，每次 sidecar 更新後都要重新 render 一次。

### 4.3 四種操作：ABSORB / REFINE / EXTEND / REFACTOR

每一個新 patch，都會被歸類成這四種之一：ABSORB 表示 patch 只是重述現有規則，沒有增加任何新的合約內容；REFINE 表示 patch 幫現有單元加了 guard、tool argument、validation 或 exception；EXTEND 表示 patch 引入一個真正全新的規則；REFACTOR 表示 patch 讓某個舊有的規則或流程「現在」變得值得共用。

用天氣查詢 skill 的例子分別走一次：ABSORB 的情況是現有規則「城市名要 url encode」的 guard 是 `true`（適用所有情況），新 patch 說「批次查詢時城市名也要 url encode」，內容早就被現有規則涵蓋，於是 ABSORB，合約完全不變。REFINE 的情況是新 patch 說「批次查詢時城市名有逗號要額外處理，不只是 url encode」，現有規則沒涵蓋這個新細節，但可以在現有規則上加一個 guard，於是 REFINE，直接在既有單元上新增這段細節。EXTEND 的情況是新 patch 說「查詢歷史天氣時，日期格式必須是 YYYY-MM-DD」，完全沒在任何現有規則出現過，於是 EXTEND，新增一條規則。REFACTOR 的情況是目前分支 A、B 各自寫了一次「驗證-修復」流程（$r=2$，還不夠划算共用），新 patch 讓分支 C 也新增完全一樣的流程，$r$ 變成 3，重新套 Eq.9 可能划算了，於是 REFACTOR，把三份獨立流程重構成一份共用流程。

REFACTOR 是四種操作裡唯一一種「不是因為新內容本身，而是因為新內容改變了周邊環境的划算與否」而觸發的操作。

Host 怎麼決定選哪一種操作？論文原文：「The host selects the feasible operation with the smallest increase in Eq. (4).」實際運作是先篩掉不可行的操作，例如 ABSORB 只有在 patch 沒引入任何目前合約沒涵蓋的內容時才可行，EXTEND 要求真的是全新的必要單元；剩下可行的操作裡，選「讓 Eq.4 的總成本增加最少」的那一個。

這裡要注意的地方是：比的是「增加最少」，不是「哪個變小最多」。因為 Zip-on-Write 處理的是新增內容，資訊量原則上只會持平或增加，不會無中生有地減少，除非觸發了 REFACTOR，把原本沒共用的東西變成共用，理論上總長度才可能真的比 patch 之前更短。這跟 One-Shot 模式的 Eq.5（$\text{save}(h) > 0$，真的在縮小既有的膨脹內容）性質不一樣：一個是壓縮既有的胖，一個是新增時盡量少長胖。論文也特別強調：「No operation is accepted because it improves a task score.」四個操作之間的選擇純粹靠 Eq.4 的成本計算，不會跑一次任務去看哪個操作讓 agent 表現更好，這跟 One-Shot 一致，保持了 evaluation-free 的精神。

### 4.4 候選搜尋範圍限縮

如果每次來一個小 patch，都要跟歷史上所有規則重新比對一次，完全沒有省到「只處理增量」的好處。論文原文：「Candidate search is restricted to the matching type, current scope, ancestor scopes, and adjacent workflow nodes.」也就是只跟同型別的東西比，只跟 patch 所在的那個 scope 裡的東西比，以及這個 scope 往上到 root 的所有祖先 scope，workflow 部分也只跟前後緊鄰的節點比，不跟整個 workflow graph 比。複雜度是 $O(d \cdot k)$，$d$ 是這個 patch 抽出的單元數，$k$ 是檢索出的候選數量（一個小常數），不會隨著整份 skill 的歷史長度增加而變大。

代價是可能漏掉「跨 scope」才能發現的共用機會。例如兩個原本毫無關聯的分支，各自累積 patch 之後，現在才發現有一段一模一樣的流程，但因為每次只看「附近」，這種跨越不相關分支的共用機會不會被單次的局部比對抓到。

### 4.5 什麼時候觸發全域 repack

Sidecar 額外追蹤「約略計數」（approximate counts，不是精確計數，用意是避免每次都要做完整的 embedding 加 relation checker 比對），三個觸發條件任一滿足就觸發：條件一是估計可回收的省下空間超過門檻值 $\theta_{repack}$，sidecar 追蹤 rule families、action n-grams 的約略出現次數，粗略估計「如果現在做一次全域整理，大概可以省下多少 token」；條件二是合約成長超過 $\rho$（自從上次 repack 以來）；條件三是累積了 $B$ 個 patch。

條件一跟條件三表面上很像，但判斷邏輯不同：條件三是單純計數，不管內容像不像；條件一是要看 patch 彼此之間有沒有「重複的味道」：即使 patch 數量還不多，但只要重複結構已經濃到值得整理，就提早觸發；即使 patch 數量到了但彼此內容都不相關，估計省下空間趨近於 0，也不會觸發。Repack 只整理「合約 $K$」，不重新分析歷史 prose，論文原文：「Repacking operates on the compact contract rather than all historical prose.」

### 4.6 Algorithm 2 完整流程

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

有兩個地方值得特別留意。第一，「範圍偵測」（`RetrieveCompatible`）跟「決定 action」（`ProposeOps`）是兩個獨立步驟：範圍偵測只是縮小候選池，即使檢索出來什麼都沒找到（`Nt` 是空的），依然可以往下判斷 action，這種情況下最合理的結果通常是 EXTEND（附近沒有任何相關的既有單元，這個 patch 大概率是全新規則），甚至不用比較 Eq.4 增加多少，因為只有一個可行選項。第二，`AtomicCommit`（原子性提交）確保萬一中途 crash，不會留下一半寫好一半沒寫好的狀態，這是系統可靠性層面的工程設計，跟前面的壓縮理論是不同層次的關注點。

---

## 五、實驗結果：數字說了什麼

### 5.1 RQ1：Skill 在自我演化中膨脹多少

前面 1.1 節已經看過 SkillOpt 的膨脹曲線，這裡再補上另一個對照方法 Memento-Skills 的數字。

![左圖 (a) 是 SkillOpt、右圖 (b) 是 Memento-Skills，兩張圖都畫出 BFCL-v4、LiveMath、SpreadsheetBench 三條相對變化率曲線加平均線，橫軸是自我演化輪數，兩種方法的曲線都隨輪數持續往上爬。](img-004)
*圖4 — SkillOpt 與 Memento-Skills 兩種既有自我演化方法各自的 skill 膨脹趨勢對照。（來源：原始論文 Fig. 4。）*

用 SkillOpt 跑到第 5 輪，skill 長度在 BFCL-V4、LiveMath、SpreadsheetBench 上分別膨脹到約 5.6 倍、3.1 倍、6.7 倍，平均約 5.2 倍。圖裡另外畫了 Memento-Skills 這個方法的膨脹曲線做對比，但論文正文只針對 SkillOpt 給出具體倍數。整體來說，兩種既有的自我演化方法都有同樣的膨脹問題，不是 SkillOpt 特有的現象。

### 5.2 RQ2：SkillZip 能不能保住保真度（最重要的結果表格）

論文的 Table I 比較了 3 個模型（Qwen-3.7-Max、Qwen-3.6-Plus、Kimi-K2.6）乘上 3 個 benchmark（BFCL-V4、LiveMath、SpreadsheetBench），共 9 個設定。整體數字是：

| | 壓縮率 | 宏平均分數 | 所需task rollout |
|---|---|---|---|
| SkillZip | 27.1%–36.9%（平均31.2%） | 0.577（未壓縮的evolved skill是0.570） | 0 |
| SkillReducer（baseline） | 平均9.2% | 0.544 | 40–80次 |

單看整體平均，SkillZip 壓縮率大幅贏過 SkillReducer，宏平均分數也沒有下滑，甚至比未壓縮版本略高一點。但逐設定看漲跌，情況沒有這麼一致（壓縮後減未壓縮的差值）：

| 模型 | BFCL-V4 | LiveMath | SpreadsheetBench |
|---|---|---|---|
| Qwen-3.7-Max | −0.006 | −0.002 | −0.006 |
| Qwen-3.6-Plus | +0.009 | +0.043 | +0.019 |
| Kimi-K2.6 | −0.025 | +0.024 | +0.007 |

最差的案例是 Kimi-K2.6 在 BFCL-V4 上，從 0.772 掉到 0.747，掉了 0.025（絕對值），相對跌幅約 3.2%，論文全篇沒有對這個個案做任何額外分析。九個設定裡有四個其實是變差的，這跟論文行文裡「沒有系統性下降」的正面敘述有落差。嚴格一點說，是「沒有一致地下降，但確實有退步的案例」。

有一個值得注意、論文沒有明講的規律：跌的三個案例全部發生在 Qwen-3.7-Max 這個模型身上，而 Qwen-3.7-Max 恰好是三個模型裡 evolved skill 表現最好的（0.869、0.474、0.525 三項都是最高）。這暗示壓縮對「原本 skill 品質已經很好」的情境，風險可能較高。這是從數據排列推論出的規律，不是論文明講的結論，值得帶著保留態度看待。

另外還有一個跟 SkillReducer 比較的公平性疑慮：論文自己在討論章節承認 SkillReducer「is more naturally positioned as a first-pass debloating and quality-control method for general public skills」，也就是說，SkillReducer 設計來處理的是前面 1.2 節講的第一種冗餘情境（跟主題不相關的內容），SkillZip 壓縮率大幅贏過 SkillReducer，某種程度上可能只是因為兩者設計目標不同，baseline 沒有站在同一個賽道上，不完全是純方法論優劣的差距。

### 5.3 RQ3：壓縮成本，整篇論文最紮實的優勢

論文的 Table II 報告了 SkillZip 和 SkillReducer 各自的壓縮開銷：

| | 平均耗時 | 所需task rollout |
|---|---|---|
| SkillZip | 286秒 | 0 |
| SkillReducer | 約1000秒 | 40–80次（每次至少一次agent call） |

加速倍數約 3.5 倍。有意思的是，SkillReducer 用的直接壓縮模型呼叫次數其實比 SkillZip 少（3 次 vs SkillZip 的 4 到 8 次），但額外要跑 40 到 80 次任務驗證的 rollout，這才是真正拖慢速度的主因。這組結果是整篇論文工程價值最直接、最可驗證的體現：「不用跑任何 task 就能壓縮」這件事，直接省下了 evaluation-guided compression 最貴的那部分成本。

### 5.4 RQ5：Zip-on-Write 的效果，直接驗證持續壓縮機制

![三個並排的折線圖分別對應 Qwen3.6-plus、Qwen3.7-max、Kimi-k2.6 三個 agent 骨幹，每張圖畫三條線：不壓縮、第8輪才開啟 Zip-on-Write、第1輪就開啟 Zip-on-Write，橫軸是自我演化輪數，縱軸是 skill 長度倍數，不壓縮那條線始終爬得最高。](img-006)
*圖5 — 在 LiveMath 上跑 16 輪自我演化，比較不壓縮、第 8 輪才啟動、第 1 輪就啟動 Zip-on-Write 三種情境下的 skill 長度變化。（來源：原始論文 Fig. 6。）*

在 LiveMath 上跑 16 輪自我演化，三個模型的結果是：不壓縮的情況下膨脹到 2.5 倍到 3.7 倍；Zip-on-Write 從第 1 輪就開啟的話，能控制在 1.6 倍到 1.9 倍，相當於減少 38% 到 50%；Zip-on-Write 到第 8 輪才開啟的話，只能追回部分膨脹，追不上「從第 1 輪就開啟」的效果，例如 Kimi-K2.6 的情況是 2.6 倍對 1.9 倍。準確率方面，從頭就壓縮的配置，最終準確率跟完全不壓縮的版本打平或略高，沒有新增額外的準確率疑慮。

這個 RQ 最值得記住的一句話，是論文原文的 takeaway：「redundancy is cheaper to prevent than to remove」。冗餘「預防」比「事後清除」便宜，越早開啟持續壓縮，效果越好，不用等到膨脹了才回頭處理。這跟 Zip-on-Write 整體的設計精神完全對上：新增時就順手整理，不是等膨脹了才壓縮，是這組實驗裡最有實務指導性的結論。

---

## 六、這篇論文真正的貢獻是什麼

拆開來看，論文用的每一個底層技巧都不是原創，這一點在前面每個技術段落都已經標出來了。但仍有幾點是這篇論文真正組裝出來、有實質價值的。

第一，把「skill 是 typed contract」這個框架跟 MDL 目標式結合，用硬性覆蓋約束取代任務驗證來保證保真度，這是整篇論文唯一真正新的理論貢獻，對應論文的 Proposition IV.1 跟 Corollary IV.2：稀有規則的保留不取決於它在壓縮時的任務分佈裡出現頻率多高，而是取決於它有沒有被解析步驟抓到。第二，四個決策共用同一個長度比較骨架（Eq.5 的四種展開），把 equivalence、scope、workflow、exception 四種不同性質的重複統一成同一套判斷邏輯，這是好的工程整合，不是新演算法。第三，Zip-on-Write 的局部更新等價性（Proposition IV.2）：在沒有跨 scope 新 reuse 機會時，局部優化等於全域重跑，這個證明讓「只看附近」這件事有理論支撐，不只是一個工程捷徑。第四，實證上 31.2% 壓縮率加整體持平的準確率加 3.5 倍加速加零 rollout，這組數字本身是紮實的工程成果，即使也存在 Kimi-K2.6 在 BFCL-V4 上退步 3.2% 這種個案。第五，「redundancy is cheaper to prevent than to remove」是 RQ5 裡少數真正被數據支撐、且有實務指導性的洞見。

---

## 七、延伸：七個藏在論文背後的通用觀念

這一節的內容，跟 SkillZip 這篇論文本身沒有必然關係，是一般電腦科學或 AI 領域的通用知識，被這篇論文用到才順便整理出來的。之所以特別獨立成一節，是因為這些概念比論文本身更耐用：論文的結論會過期，這些東西不會。

### 概念1：Grammar-based compression 與 BPE

起源領域是資料壓縮與文法推導（grammar induction），1990 年代到 2000 年代的經典理論 CS 主題。在 AI 領域雖然不常見有人直接用 Re-Pair、SEQUITUR 這兩個名字，但它們背後的精神幾乎所有 LLM tokenizer 都在用，也就是 BPE（Byte Pair Encoding）。

Re-Pair 的核心想法是反覆做「找出目前最常出現的相鄰兩個符號組合，合併成一個新符號」，直到沒有 pair 重複出現。SEQUITUR 是線上增量版，逐個符號讀入，維護兩個不變性：任何 pair 不能重複出現超過一次，重複就立刻拆成新規則；每條規則至少要被用兩次以上，否則內聯刪掉。這會自然產生巢狀、遞迴的文法。

最簡單的例子：$S = a\ b\ c\ a\ b\ c\ a\ b\ c$（長度 9，「abc」重複 3 次）。發現重複片段「abc」後，定義新規則 $X \to a\ b\ c$，改寫成 $S \to X\ X\ X$。改寫後大小是規則本體 $X$（3 個符號）加主體（3 次引用 $X$，3 個符號）等於 6 個符號，比原本 9 個短。

BPE 完整走一次（這個例子跟論文內容無關，是自己編的）。假設語料裡只有 4 個字，出現次數如下：`cook_` 出現 6 次、`cooker_` 出現 2 次、`cookies_` 出現 3 次、`look_` 出現 1 次（底線代表字尾結束的特殊符號）。初始狀態每個字拆成單一字元：

```
cook_    -> c o o k _
cooker_  -> c o o k e r _
cookies_ -> c o o k i e s _
look_    -> l o o k _
```

第 1 輪，數所有相鄰字元對乘上出現次數，最高的是 (o,o) 跟 (o,k)，並列 12，選 (o,o) 合併成 `OO`：

```
cook_    -> c OO k _
cooker_  -> c OO k e r _
cookies_ -> c OO k i e s _
look_    -> l OO k _
```

第 2 輪，(OO,k) 最高，次數 12，合併成 `OOK`。第 3 輪，(c,OOK) 最高，次數 11，合併成 `COOK`：

```
cook_    -> COOK _
cooker_  -> COOK e r _
cookies_ -> COOK i e s _
look_    -> l OOK _
```

只花 3 輪，「cook」這 4 個字元就被壓成 1 個 token `COOK`，且這個 token 在 3 個不同的字裡被重複使用，這就是「define once, reference many」的具體樣子。

這裡有個容易誤解的地方需要釐清：詞彙表是「累積」的，不是「取代」的。每做一次合併，是新增一個 token 到詞彙表裡，不是把舊的 token 刪掉、換成新的。跑完第 3 輪後，詞彙表是 `c, o, k, _, e, r, i, s, l, OO, OOK, COOK`，一共 12 個 token，不是只剩 `COOK` 一個。詞彙表（所有合法 token 的清單，一份固定的字典）跟編碼結果（用詞彙表裡的 token，把每一句話重新拼出來）是兩個不同的概念：`cook_` 這個字被編碼成 `COOK _`（兩個 token），`cooker_` 被編碼成 `COOK e r _`（四個 token），每個字用到的 token 數量不一樣。字典會越編越厚，但字典本身不會因為你寫了一句話，就把字典裡其他字刪掉。

為什麼不會一路合併到只剩一個 token？實務上會設一個「詞彙表大小」當煞車，例如 5 萬個 token 就停。但即使不設煞車，繼續合併下去，能省的效益也會越來越低。語料裡不同的字彼此差異越來越大，重複出現的相鄰 pair 會越來越稀少，只出現 1 次的 pair 合併成新 token 完全沒有省到東西（定義一次要花成本，卻只用一次）。這正好呼應 SkillZip 的 Eq.9：$r=1$ 時，$L(\text{def})+1 \times L(\text{call})$ 幾乎不可能小於 $L(q)$，不划算，演算法自然不會選它。

三者的關聯是：Re-Pair 合併的對象是任意符號序列（通用壓縮），BPE 合併的對象是字元或子詞（做 LLM 詞彙表），SkillZip 合併的對象是打了型別的技能規則或工作流程片段。

### 概念2：Loop-invariant code motion

起源領域是編譯器最佳化，一般電腦科學背景知識。Invariant（不變的東西）在迴圈情境下，指這段運算不管迴圈跑到第幾輪，算出來的結果都一樣，跟迴圈變數完全無關，只是剛好被寫在迴圈裡面。

沒最佳化前：

```
a = 5
b = 3
for i in 0..1000000:
    x = a * b          # 這行跟i完全無關
    result[i] = x + i
```

`a * b` 每一輪都被重新算一次，但因為 `a`、`b` 從頭到尾沒被改過，算 1000000 次跟算 1 次結果完全一樣，白算了 999999 次。編譯器自動偵測後會把它搬出來：

```
a = 5
b = 3
x = a * b               # 搬出來了，只算一次
for i in 0..1000000:
    result[i] = x + i
```

行為完全不變，省下 999999 次重複運算。判斷是否可以搬的條件是：這段運算不寫入任何迴圈變數會改變的東西、不依賴任何迴圈內才會變的變數、搬到迴圈外不會改變程式行為（不能有副作用）。如果 `a` 或 `b` 在迴圈中途被改了，就不再是 invariant，不能搬。

這跟 SkillZip 的 scope lifting（Eq.8）是同一個邏輯：迴圈裡的 loop-invariant code motion 是「這段運算在每一輪迭代都一樣，搬到迴圈外只算一次」；SkillZip 的 scope lifting 是「這條規則在每個子分支都一樣，搬到共同父層 scope 只寫一次」。判斷條件也對得上：編譯器要求每一輪都不變，SkillZip 要求每個相關的子路徑都需要這條規則；編譯器如果中途被改就不能搬，SkillZip 如果某個分支有衝突，也不能整條搬走，得留下 exception。這個心智模型不只適用 skill，任何有巢狀結構的系統，像是設定檔繼承、物件導向的方法覆寫，都是同一個邏輯。

### 概念3：NLI 與 relation checker

起源領域是自然語言推論（Natural Language Inference，NLI），NLP 裡一個經典任務，在 AI 領域非常常見。標準定義是給兩句話（premise 前提、hypothesis 假設），判斷邏輯關係，通常分三類：entailment（蘊含），premise 為真、hypothesis 一定也為真，例如「今天下大雨」蘊含「今天天氣不好」；contradiction（矛盾），兩句話互相衝突，不可能同時為真，例如「今天下大雨」跟「今天萬里無雲」；neutral（中立），兩句話沒有必然關係。

SkillZip 用的四分類跟 NLI 三分類是同一個家族，只是多切了一種：entailment 對應到 implication（單向蘊含），而 equivalence（雙向蘊含）是 entailment 的特例；contradiction 對應到 conflict；neutral 對應到 unrelated。

「frozen」（凍結）的意思是這個分類器的參數在使用時完全不會被更新、微調，是拿一個訓練好的現成模型直接當工具用，跟 embedding index 用的向量模型一樣凍結不動。之所以強調 frozen，是為了呼應「optimization is deterministic」：如果分類器參數會變動，同樣輸入在不同次執行可能給出不同答案，破壞確定性保證。

Embedding index 的做法是先把每段文字轉成一串數字（向量），設計方式讓「意思相近的文字，向量也會相近」，把大量文字的向量事先算好存進一個資料結構，之後給一個新向量能快速找出「哪些向量離它最近」，不用逐一比對。這一步只能告訴你「兩者語意上接近」，沒辦法告訴你「接近到可以合併還是接近但互相衝突」，這就是為什麼還需要 relation checker 再判斷一次。

論文用得算不算「輕」？不算輕。NLI 標準任務通常判斷「兩個完整句子」的邏輯關係，SkillZip 這裡拿它判斷「兩個帶了 scope、guard、modality 標籤的規則」之間的關係，多了一層「先做結構篩選才丟進去問」的前置步驟，是合理的延伸，不是掛名裝飾。

### 概念4：三個組合最佳化工具，DP、Weighted Set-Packing、Clustering

**Dynamic Programming（動態規劃）**：跟論文無關的例子是爬樓梯——每次可以爬 1 階或 2 階，樓梯共 5 階，問總共有幾種爬法？核心想法是把「爬到第 N 階，總共有幾種方法」的答案算過一次就存起來，之後遇到同樣的問題直接查表，不重算。

```
爬到第1階 = 1
爬到第2階 = 2
爬到第3階 = 爬到第1階 + 爬到第2階 = 1+2 = 3
爬到第4階 = 爬到第2階 + 爬到第3階 = 2+3 = 5
爬到第5階 = 爬到第3階 + 爬到第4階 = 3+5 = 8
```

適用條件是大問題可以拆成很多小問題，很多小問題其實是一樣的（會被問到很多次），大問題答案可以用小問題答案組合出來。對回 SkillZip，DP 在 scope tree 上「由下往上」算，先算子節點自己的規則放置成本，存起來，回頭算父節點時，就用子節點已經算好、存起來的答案判斷「如果把規則從兩個子節點都搬到父層，總成本會不會比各自保留更低」，不用重新掃過整棵樹。

**Weighted Set-Packing（帶權重的集合裝箱問題）**：跟論文無關的例子是排廣告時段——一個晚上 8 點到 11 點的時段，好幾個廣告商想投放，但每個廣告有自己的起訖時間，時間重疊的不能同時播出，每個廣告出價不同，要選出總收入最大的組合：

```
廣告A：8:00-8:30，$100
廣告B：8:15-9:00，$150   （跟A重疊）
廣告C：9:00-10:00，$200
廣告D：8:30-9:30，$180   （跟C重疊）
廣告E：10:00-11:00，$120
```

重疊的候選只能選一個，要在有限、互斥的選項裡湊出總價值最高的組合。論文的近似解法是貪心加 pairwise exchange：先按「每單位覆蓋的 token 能省多少」（而不是總價值高低）排序，選最划算的，選了就把跟它重疊的候選排除，重複直到選不出新的；接著試著把已選的某一個候選換成另一個沒被選的，看總價值會不會變高，會就換，不會就維持原狀，反覆做直到換不出更好的組合。對回 SkillZip，workflow 候選的「不重疊」限制就是這個問題的具體版本，例如「[1]驗證→[2]修復→[3]驗證→[4]確認→[5]輸出」這條序列裡，候選 A 涵蓋 [1][2][3]、候選 B 涵蓋 [2][3][4]，兩者重疊在 [2][3]，只能選一個，用「省下token除以涵蓋token數」這個效率比率排序決定選誰。

**Clustering（分群，Union-Find）**：跟論文無關的例子是水果分堆——根據某種相似程度，把一堆東西自動分成幾群，讓同一群裡的東西彼此相似。Union-Find 的連鎖合併特性是：初始每個東西自己一群；看到「C1 equivalence C2」就合併成 {C1,C2}；看到「C3 equivalence C4」就合併成 {C3,C4}；再看到「C2 equivalence C4」，因為 C2 在 {C1,C2}、C4 在 {C3,C4}，這兩個群要合併成一個大群 {C1,C2,C3,C4}。即使原始關係只是兩兩配對，Union-Find 會自動處理連鎖效應。要先做 conflict filtering 才 clustering 的原因是：如果 relation checker 還回報了「C1 conflict C5」這種不相容的關係，要先把這種 pair 排除，不讓它進入 union-find 的合併名單，只有 equivalence 或 implication 的 pair 才能進入 union-find，conflict 的 pair 要走決策4那條路，不能混在一起處理。對回 SkillZip，Union-Find 分完群之後，同一群裡的所有規則最終會被合併成一份共用內容（決策1），如果這群規則分散在不同 scope，DP 接著決定共用內容該放在 scope tree 的哪個位置（決策2）。

三者比較：

| | Dynamic Programming | Weighted Set-Packing | Clustering (Union-Find) |
|---|---|---|---|
| 通用問題形狀 | 大問題可拆成小問題，答案能重複利用 | 候選互斥，選出互不衝突、總價值最高的一組 | 一堆東西兩兩之間有關聯，自動歸併成幾群 |
| 關鍵特徵 | 後面的答案倚賴前面已算好的答案 | 候選會重疊/衝突，選了一個排擠另一個 | 關係有連鎖性 |
| 解法性質 | 精確解 | 近似解（貪心+微調） | 精確解 |
| 論文中對應子問題 | 決策2 scope放置 | 決策3 workflow候選互斥 | 決策1 equivalence群組歸併 |
| 對應公式 | Eq.8 | Eq.9 | Eq.7 |
| 生活化類比 | 爬樓梯 | 廣告時段排程 | 水果分堆 |

### 概念5：MDL（最小描述長度原理）

起源領域是 1970 年代末的資訊理論與統計學，代表人物是 Rissanen，是「奧卡姆剃刀」（越簡單的解釋越好）的數學形式化版本。在機器學習裡非常常見的親戚有統計學的 BIC、決策樹剪枝、正則化（L1/L2 懲罰項），背後都是同一精神的不同實作。

核心直覺用一個跟論文無關的經典例子說明：一組資料點 $(1,1)(2,4)(3,9)(4,16)(5,25)$。選項 A 用簡單公式 $y=x^2$ 描述，模型本身很短，殘差為 0；選項 B 用一個 5 次多項式硬湊，剛好穿過這 5 個點，模型本身很長（要記 5 個怪係數），殘差也是 0。兩者「準確度」一樣，殘差都是 0，但總成本（模型描述長度加殘差描述長度）不一樣，選項 A 更短。MDL 選選項 A。即使準確度打平，選項 A 用更精簡的方式捕捉到資料裡真正的結構，選項 B 只是硬背答案。

標準兩項式是：

$$\text{總成本} = L(\text{模型}) + L(\text{資料} \mid \text{模型})$$

$L(\text{模型})$ 是描述這個模型本身要花多少篇幅，$L(\text{資料}\mid\text{模型})$ 是在有了這個模型的前提下，還要多少篇幅才能完整描述資料，也就是沒被模型解釋到的殘差。對回 SkillZip 的 Eq.4，$K$（合約庫）對應「模型」，$R$（殘留）對應「資料裡沒被模型解釋到的部分」。$K$ 扮演的角色跟「$y=x^2$ 這個公式」一樣，用最精簡的方式捕捉 skill 裡真正的結構性規律；$R$ 扮演的角色跟「殘差」一樣，是沒辦法被規則庫解釋、必須原封不動保留的特殊內容。

論文不是輕度借用這個概念，不是隨口說「有點像 MDL」，而是直接把 Eq.4 寫成 MDL 的標準兩項式，四個決策（Eq.7 到 Eq.10）全部是這個式子在不同情境下的具體展開，論文自己在相關工作章節也明講了這個傳承關係。MDL 在 AI 領域的其他常見身影，還包括決策樹剪枝（樹太複雜但準確度沒顯著提升就該剪）、正則化（懲罰過度複雜的模型參數）、Re-Pair/SEQUITUR（論文自己把它們歸為 MDL 精神的實例）、BIC（統計學裡比較模型好壞的準則，公式結構跟 MDL 幾乎一樣）。

### 概念6：Relevance-based vs Redundancy-based 壓縮

Prompt compression 的典型情境（例如 LLMLingua）是一篇長文件加一個具體問題，要 LLM 回答：

```
輸入：[一篇5000字的糖尿病維基百科文章] + 問題："第二型糖尿病怎麼治療？"

做法：根據"這個問題"估計每一段文字重不重要
     -> 治療相關段落：保留
     -> 病因、流行病學段落：低相關 -> 刪掉
```

這樣做合理，因為有一個明確的「當下問題」可以拿來當篩選依據。Skill 的情境不一樣：skill 不是配合一個已知問題而寫的，是配合「未來任何一個屬於這個任務類別的問題」而寫的。skill 載入的當下，完全不知道等一下會被問什麼。如果套用 prompt compression 的邏輯，跟當下查詢相關性低就刪，今天問代數題時把「跟階乘有關的規則」判斷成低相關刪掉，明天問到階乘題目時，這條規則就是必要的，卻已經被錯誤刪掉了。論文原文對應這個邏輯：「Skills should be reusable for all queries of certain tasks... a reusable skill must retain requirements that no compression-time query activates.」

這個區分可以用來判斷任何「要不要壓縮或精簡一份文件」的情境該用哪種思路：有沒有一個明確、當下的使用情境可以拿來當篩選依據？有的話用 relevance 思路；沒有的話，也就是要對所有未來情境都成立的情況，只能用 redundancy 思路。

### 概念7：「理解」與「決策」分離的架構設計原則

SkillZip 整個系統的分工原則是：語意判斷（該分去哪一類）交給 LLM，也就是步驟2的抽取器跟 relation checker；數學判斷（划不划算、選哪個）交給確定性程式碼，也就是 host 驗證、Eq.5 到 Eq.10 的成本計算、DP、weighted packing、clustering。

論文原文明講這個分工的用意：「The extractor is deliberately not asked to compress. Separating interpretation from optimization has two benefits: contract recovery can be evaluated against human annotations, and the optimization is deterministic once the extracted units are fixed.」翻成白話有兩個好處：抽取的品質可以獨立被檢驗，拿人工標註去對答案，不會被後面的壓縮邏輯干擾；一旦抽取單元固定，後面「要不要合併」是純數學運算，同樣輸入一定得到同樣輸出，不會因為 LLM 隨機性讓每次壓縮結果不一樣。

這個原則不只適用 skill 壓縮，任何想要借助 LLM 的語意理解能力，但又要求整個系統的最終行為可重現、可驗證的場景，都值得採用這個分工：把「這是什麼、這兩者是什麼關係」這種需要語意判斷的部分交給模型，把「基於這個判斷該怎麼做」這種可以用明確規則表達的部分交給確定性程式碼。

---

## 結論

SkillZip 想解決的問題很具體：自我演化 agent 的 skill 檔案，會因為只增不減的維護方式越滾越大，而膨脹裡真正新的知識量早就趨於平緩。它的解法，是先把 skill 拆解成一份打了型別的合約（介面、流程、工具協定、規則、輸出、佐證六種型別），再用 MDL 目標式下的四個決策（同義合併、scope lifting、workflow reuse、通則加例外）把重複收斂掉，全程用一條硬性覆蓋約束保證原本的規則意思不會憑空消失，也因此完全不需要跑任何任務去驗證壓縮結果。

實測數字相當紮實：平均壓縮率 31.2%、整體準確率持平甚至略升、壓縮速度比對手快 3.5 倍、且不用任何 task rollout。Zip-on-Write 這個持續壓縮模式進一步驗證了「redundancy is cheaper to prevent than to remove」：越早開始持續壓縮，膨脹控制得越好。但這篇論文本身用到的每一項技巧都不是原創，真正的貢獻在於系統整合，以及把「保真度」從「拿任務去驗證」換成「用結構化的硬性約束保證」這個設計選擇。

三個開頭就提過的保留態度，這裡再收斂一次：保真度保證只保得住解析步驟有抓到的東西，解析步驟本身漏抓什麼，後面完全沒有補救機制；九個測試設定裡有四個其實是退步的，最差的案例掉了 3.2%，論文沒有進一步分析；跟 SkillReducer 的比較某種程度上是不同賽道的比較，因為兩者設計目標鎖定的冗餘類型本來就不同。如果你在做 skill evolution 或 agent 記憶管理相關的實務工作，這篇論文的架構設計思路，尤其是「理解與決策分離」跟「用硬約束取代任務驗證」這兩點，值得直接借用；至於論文提到的那些通用電腦科學工具，前面延伸段落整理的內容，脫離這篇論文本身也一樣有用。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Fig. 1. The skill growth tendency with respect to self-evolving progress on diverse benchmarks for a CodeX Agent. Self-evolution can keep increasing skill length after genuinely new procedural content has largely stabilized.",
    "why_used": "文章開頭用來具體呈現「skill 總長度」與「真正獨特內容」之間的裂縫，是整篇論文的問題起點。",
    "agent_match_hint": "一張折線圖，橫軸是自我演化輪數，橘線（skill tokens）持續上升，藍線（unique contract content）中段趨緩，兩線間有陰影標註重複膨脹的部分。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Fig. 3. Overview of SkillZip. One-shot compression first recovers the skill contract, then applies the “explain once, reference many” principle to repeated rules and workflows, while unique and uncertain content remains explicit. Zip-on-Write compares each patch with the affected contract neighborhood and performs occasional repacking when reuse accumulates across patches.",
    "why_used": "在介紹合約框架之前，先給讀者一張整體架構圖，說明 One-Shot 與 Zip-on-Write 兩種模式的分工，作為後續兩大章節的路線圖。",
    "agent_match_hint": "一張系統架構圖，左半部標示 One-Shot Compression 的流程方塊（掃描、還原合約、比對重用、渲染），右半部標示 Continual Compression Zip-on-Write 的流程方塊（本地更新、觸發重新打包）。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Fig. 2. A skill is a typed contract. Different text spans constrain different parts of execution. An example is removable only when every requirement it uniquely expresses is represented elsewhere.",
    "why_used": "配合六型別合約的說明，讓讀者直接看到 Interface/Workflow/Tool/Scoped rules/Output/Evidence 六個色塊如何分工。",
    "agent_match_hint": "一張示意圖，六個標示不同顏色的區塊分別代表六種合約型別，中間用箭頭串接成一條執行主線，Evidence 貼在旁邊。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Fig. 4. The skill growth tendency with respect to agent self-evolving progress for SkillOpt [2] and Memento-Skills [34].",
    "why_used": "支撐 RQ1 段落裡「兩種既有自我演化方法都有膨脹問題」的說法，讓讀者看到不是單一方法的特例。",
    "agent_match_hint": "並排兩張折線圖，(a) SkillOpt 與 (b) Memento-Skills，各自畫出 BFCL-v4、LiveMath、SpreadsheetBench 三條曲線加平均線，橫軸為自我演化輪數。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Fig. 6. Skill length (by 𝑁×) during self-evolution on LiveMath for three agent backbones. Each panel compares no compression against Zip-on-Write continual compression activated at round 8 and at round 1; legends report the final test accuracy.",
    "why_used": "直接支撐 RQ5 段落的核心論點：Zip-on-Write 從第 1 輪就開啟，比第 8 輪才開啟能更有效控制膨脹。",
    "agent_match_hint": "三張並排的折線圖，分別對應 Qwen3.6-plus、Qwen3.7-max、Kimi-k2.6，每張圖有三條線：不壓縮、第8輪啟動、第1輪啟動，橫軸為自我演化輪數，縱軸為 skill 長度倍數。"
  }
]
```
