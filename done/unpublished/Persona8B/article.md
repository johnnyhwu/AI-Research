# MatrAIx：用 1,290 個欄位造出虛擬使用者，再讓它們去試用你的產品

**來源**：[MatrAIx: Simulating the World with 8.3 Billion Persona Agents](https://arxiv.org/abs/2608.04205)（arXiv:2608.04205v1，2026 年 8 月）

## 前言

MatrAIx 想做的事很好懂：與其找真人來試用產品，不如造出一大群虛擬使用者（persona），讓 LLM 扮演他們去填問卷、跟聊天機器人對話、逛網站、操作 App，最後把結果統計起來。它把「造人、操作、檢查」三件事都做成可以重跑的流程，基礎設施本身相當扎實。

但論文自己的實驗給了一個不太討喜的答案：同一批 persona，換一個 LLM 來扮演，結論可以整個翻過來。在「糖果漲價後還買嗎」這個任務裡，猶豫的比例 GPT 5.5 是 98.3%，Claude Opus 4.8 只有 27.0%。說話風格類的設定大多能被演出來，但年齡這類人口欄位到底有沒有影響決策，在這份證據下沒有被證明。

本文依序走過：為什麼需要模擬使用者、persona 怎麼造（合成與真人兩條路）、模擬怎麼跑、實驗結果，最後獨立一節講 Cohen's kappa，這個統計量脫離這篇論文也很實用。文中標（推論）的是本文作者的判斷，標（自編）的是為了說明而自己編的數字，標（自算）的是本文作者用論文數字算出來的結果，其餘都是論文內容。論文沒交代的地方，多半就地說明，最後〈論文沒交代的地方〉一節再集中列一次索引。

## 為什麼要用虛擬使用者測產品

真人測試太貴、太慢；離線 benchmark 又只量「任務有沒有做對」，看不到不同的人用起來有什麼差別。論文想用大量虛擬使用者補上這個洞。

|  | 真人評估 | 離線 benchmark | 模擬使用者（MatrAIx） |
| --- | --- | --- | --- |
| 成本與速度 | 貴、慢（數週） | 便宜、快 | 便宜、快（數小時） |
| 看得到使用者差異 | 看得到 | 看不到，只量任務有沒有做對 | 想看到 |
| 可重跑 | 難 | 容易 | 容易（同一批人可重跑） |

論文舉的例子是寫程式的 agent。unit test 全過，只代表功能正確；但新手想要解釋和小幅修改，專家想要簡短回覆和更大的自主權。同一個系統，對這兩種人的體驗可能完全不同，平均分數看不出來。

所以挑戰是要讓 LLM 扮演的虛擬使用者同時做到三件事：

1. **人群多樣又合理**：造出一群像樣的「人」，對應〈造人：Persona 8B 怎麼產生 persona〉。
2. **能在不同產品裡真的操作**：讓他們去用產品，對應〈跑模擬：一次 trial 從設定到結果〉。
3. **行為真的照設定走**：證明他們演得像，對應〈實驗：結果主要取決於誰在扮演〉。

---

## 造人：Persona 8B 怎麼產生 persona

MatrAIx 負責造人的這一塊，論文稱為 Persona 8B。先講結論：一個 persona 就是一列 1,290 個選項。合成的 persona 靠欄位之間的依賴關係逐欄抽出來；真人來源轉成同一個格式，沒有證據的格子留空。論文公開釋出的子集（coreset，下文稱公開版）約 100 萬筆，其中真人來源 599,847 筆、合成 400,000 筆。

### 一筆 persona 長什麼樣

persona 是一份固定格式的表單：1,290 個欄位，每格只能從有限的選項裡選，例如年齡層是 18–24、25–34、35–44 這種級距，英語程度從 Native 到 None。欄位分五大類：Background 238 個、Psychology 210 個、Capability 331 個、Behavior and Interaction 124 個、Lifestyle 387 個（表 1）。

![五大類欄位的總覽表，列出每類的欄位數、代表性屬性與資料依據，總計 1,290 個欄位。](img-002)
*表 1 — Persona 8B 欄位架構總覽。（來源：原始論文 Table 1。）*

合成的 persona 每格都填滿；真人來源的紀錄只填有證據的格子，其餘是 null，論文不補值。下面這個對照是自編的例子：

| 欄位（自編） | 合成紀錄 | 真人來源紀錄 |
| --- | --- | --- |
| age bracket | 25–34 | 35–44 |
| English proficiency | Native | Fluent (C1-C2) |
| risk tolerance | Risk-averse | null |
| Python | Advanced | Intermediate |
| time pressure | High | null |
| exercise frequency | Weekly | null |

兩種紀錄用的是同一份欄位清單，差別只在有沒有填滿。

### 合成 persona 用依賴圖逐欄抽樣

只讓每個欄位的比例準確還不夠。如果各欄位各抽各的，很可能抽出「20 歲、博士、已退休」這種不可能的人（自編）。

MatrAIx 的做法是把每個欄位當成圖上的一個節點。某個資料來源若直接報告了「A 欄位依 B 欄位拆開的分布」，就畫一條 $B \to A$ 的箭頭，表示 A 要等 B 抽好才抽。沒有父欄位的節點叫 root，直接用全人口比例抽；有父欄位的叫 child。抽的順序一律先父後子。這張圖是有向無環圖（DAG），整個 persona 的機率，就是每一格「給定父欄位」的機率連乘（論文 Eq. 3）：

$$
p(x)=\prod_{i=1}^{d} p\left(x_i \mid x_{\mathrm{Pa}(i)}\right)
$$

- $x_i$：第 $i$ 格的值，例如學歷。
- $\mathrm{Pa}(i)$：第 $i$ 格的父欄位集合；root 的集合是空的。
- $\prod$：把 $d$ 格（這裡 $d = 1{,}290$）的機率全部相乘。

用自編的數字看一次：只看年齡與學歷兩格，$p(\text{age}=25\text{–}34)=0.20$，$p(\text{edu}=\text{Bachelor} \mid \text{age}=25\text{–}34)=0.40$，這兩格的組合機率就是 $0.20 \times 0.40 = 0.08$。學歷的機率會隨年齡改變，欄位之間的關聯就是這樣被保留下來的。

論文選擇這種連乘分解，理由很務實：沒有任何來源提供完整的聯合分布，手上只有零散的條件分布可用（附錄 C.1）。

### root 與 child 怎麼決定，依賴只有一層嗎

root 與 child 不是事先指定的，而是由前面那條畫邊規則決定：手上有沒有「依 B 拆開的 A」的統計表；依賴也可以有很多層。用三張自編的統計表來看：

| 手上有的統計表（自編） | 意思 | 結果 |
| --- | --- | --- |
| 各年齡層各占多少 | 年齡不用看別的欄位就能抽 | age 沒有父欄位，是 root |
| 每個年齡層的學歷分布 | 學歷要先知道年齡才抽得準 | age → education，education 是 child |
| 每種「語言＋地區」組合的英語程度分布 | 英語程度要先知道語言和地區 | language、region → English proficiency |

依賴不只一層。一個欄位的父欄位自己也可以有父欄位，抽樣只要求「父欄位先抽」，所以 $A \to B \to C$ 沒有問題：B 依 A 抽，C 再依 B 抽。三層鏈的機率是 $p(a)\,p(b \mid a)\,p(c \mid b)$，代入自編數字就是 $0.20 \times 0.40 \times 0.50 = 0.04$。

畫一條邊要過三道關（附錄 C.1）：

- **來源審查**：即前面那條規則，來源有直接報告條件分布才加邊。
- **語意確認**：父欄位對子欄位的值域必須真的有意義，而不只是統計上相關。
- **LLM 輔助補漏**：LLM 提議可能漏掉的邊，再由人逐條接受或拒絕。

完整的依賴圖在附錄 C.1（圖 1）。

![完整的 persona 依賴圖，節點從左到右按抽樣順序排列，依欄位類別分成橫向泳道，半透明曲線是有向邊。](img-010)
*圖 1 — 完整的 persona DAG。（來源：原始論文 Figure 5。）*

幾點要分清楚哪些是論文講的、哪些不是：

- root 是「手上沒有對應統計表、所以沒有邊」造成的結果，這是推論；論文只說 root 用 categorical prior（類別式的全人口比例）抽。
- 邊的方向怎麼定，論文未說明；（推論）大概跟著來源表格的拆分方向。
- 最深有幾層，論文文字沒寫，只能看圖 1。
- 另外有 18 個隱藏的 root（例如 `latent_financial_security`），設計上就是 root，用來協調一整族欄位，不會輸出到 persona 裡（附錄 C.1）。

### 每一格怎麼抽：先驗、調整、遮罩、正規化

輪到某一格時，對它的每個候選值依序做四步，最後按機率抽一個：

1. **先驗**：不看任何父欄位時，全人口中取到這個值的比例。
2. **調整**：父欄位會改變機率。每個父欄位給一個比值（這個父欄位條件下的比例 ÷ 先驗），比值大於 1 表示這個值在該條件下更常見。多個父欄位的比值直接相乘，因為沒有任何來源提供「多個父欄位一起」的表。
3. **遮罩**：只有 0 或 1。不可能的組合設為 0，直接排除。
4. **正規化**：把所有候選值的分數加總成 1，變成機率。

調整與遮罩分開，是這套設計的眉角：「很少見但可能」的人不會被誤殺，只有「不可能」的人才會被真正排除。

表 2 是論文附的完整算例。情境是語言＝英文、地區＝北美，要抽「英語程度」。論文明寫這些是示意用的數字，不是實際部署的參數。

| 候選值 | 先驗 | 語言比值 | 地區比值 | 調整（兩者相乘） | 遮罩 | 分數（先驗×調整×遮罩） | 機率 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| None | 0.30 | 0.02÷0.30＝0.067 | 0.10÷0.30＝0.333 | 0.022 | 0 | 0.000 | 0.000 |
| Basic | 0.30 | 0.08÷0.30＝0.267 | 0.20÷0.30＝0.667 | 0.178 | 1 | 0.053 | 0.028 |
| Fluent | 0.25 | 0.30÷0.25＝1.200 | 0.35÷0.25＝1.400 | 1.680 | 1 | 0.420 | 0.224 |
| Native | 0.15 | 0.60÷0.15＝4.000 | 0.35÷0.15＝2.333 | 9.333 | 1 | 1.400 | 0.747 |
| 合計 | 1.00 |  |  |  |  | 1.873 | 1.000 |
*表 2 — 英語程度這一格的逐步計算（示意數字）。（來源：原始論文 Table 6。）*

以 Native 為例逐步算：

```
先驗              0.15
語言比值          0.60 ÷ 0.15 = 4      （語言＝英文的人裡 Native 的比例是平常的 4 倍）
地區比值          0.35 ÷ 0.15 = 2.333  （北美是平常的 2.333 倍）
調整              4 × 2.333 = 9.333
分數              0.15 × 9.333 × 1 = 1.400
機率              1.400 ÷ 1.873 ≈ 0.747
```

Native 從先驗的 15% 變成 74.7%。再看 None：如果沒有遮罩，它的分數約 0.0067，仍有約 0.35% 的機率被抽中（自算）；遮罩把它乘上 0，才讓它變成真正的 0。

### forward sampling 實際怎麼抽

組合總數是各欄位選項數相乘。1,290 個欄位就算每欄只有 2 個選項，也有 $2^{1290}$ 種組合，根本列不完，所以完整的聯合機率既不算、也不存。

實際的做法論文稱為 forward sampling（論文 Eq. 5）：照先父後子的順序逐欄走一遍，每一格只依父欄位「已經抽到的值」得到自己那一格的小分布，再從中抽一個值。每個 persona 只需要 1,290 次小抽樣，每次只面對一欄的幾個選項。重複 $N$ 次就得到 $N$ 個 persona（Eq. 8）；種子固定就能重現，也能切成多個 shard 平行生成（附錄 C.1）。

用前面的數字串一次三格（前兩格是自編，第三格是表 2 的結果；這是教學用的走查，不是論文逐格的實際抽樣紀錄）：

```
第 1 格 age（root）           按全人口比例抽 → 抽到 25–34（機率 0.20）
第 2 格 education（父：age）  看 age=25–34 的學歷分布 → 抽到 Bachelor（機率 0.40）
第 3 格 English proficiency   language=English、region=North America 已抽好
       （父：language、region）→ 用表 2 的分布：Native 0.747、Fluent 0.224、Basic 0.028、None 0
```

第 2 格的分布會隨第 1 格抽到的年齡改變，關聯就是在這裡被保留的。

### 真人資料轉成同一個格式

六個真人來源，依資料本身有多結構化，分成四種轉法。一筆 persona 對應來源裡的一個單位：

| 轉法 | 來源與公開版筆數 | 一筆 persona 對應 | 論文有沒有明寫單位 |
| --- | --- | --- | --- |
| 已編碼的問卷答案，查表轉換 | Stack Overflow 調查 113,120、GSS 63,532 | 一位受訪者 | 沒寫，（推論）一人一筆 |
| 志願者自填 | 355 | 一份自填的紀錄 | 明寫 |
| 編碼欄位查表，加上 LLM 讀自述 | PRISM 1,487 | 一位參與者 | 沒寫，（推論）一人一筆 |
| LLM 讀自由文字 | Wikipedia 傳記 323,438、Amazon 評論 97,915 | 一篇傳記、一位評論者 | 明寫 |

論文的原表見表 3。

![公開版的組成表，列出各真人來源的筆數、真人來源小計與合成筆數。](img-003)
*表 3 — 公開版（約 100 萬筆）的組成。（來源：原始論文 Table 2。）*

合計 599,847 筆，每組數字都是該來源最後留在公開版裡的 persona 筆數。每一格都遵守同一條規則：沒有證據就留 null，並標明證據類型（直接證據、結構化主張、摘要推論、無依據）。

使用時要注意兩件事。第一，用到 LLM 的有 Wikipedia、Amazon、PRISM 共 422,840 筆，占 599,847 的約 70.5%（自算；PRISM 有部分欄位是查表，所以這是上限）。第二，論文在表 3 的說明裡提醒：human-grounded 只表示這筆紀錄的來源是真人資料，不保證每一格都是被驗證過的事實。

兩個極端的例子（內容自編）：一位 Amazon 評論者，由 LLM 讀他的評論文字抽出欄位；一位 GSS 受訪者，由對照表把編碼答案轉成欄位。

數字和原始量的關係也值得看一下：

- **Wikipedia**：來源資料庫有 2,125,897 篇傳記，為了讓整體分布貼近人口統計，只取了 323,438 篇。
- **Amazon**：先挑出 100,000 位歷史評論夠長、夠重複的評論者，最後留下 97,915 位；差額論文沒有逐一說明，（推論）是品質過濾與去重。

各來源的填格程度差很多。GSS 只有 18 個編碼變數，所以一筆 persona 最多十幾格有值，其餘都是 null；志願者問卷最多可以答滿 1,290 題，355 份裡有 272 份全答。其他來源每筆平均填了幾格，論文沒有交代。

### LLM 抽取的信心值存了，卻看不出怎麼用

用 LLM 抽取自由文字時，有兩路並行：regex（規則比對）找原文裡直接出現的選項字樣；LLM 評審只看檢索到的相關欄位和固定選項，而且可以棄權。每一格紀錄都附一個信心欄位，但它只是標記可靠度的分數，不是經過校準的機率。三種來源的信心值刻度不同，不能直接拿來比：

| 來源 | 信心值 | 怎麼來 |
| --- | --- | --- |
| 原始精確答案（查表與志願者自填） | 1.0 | 受訪者自己答的，覆蓋任何推論 |
| regex 字面比對 | 0.7 | 設計者固定給的常數，不是算出來的；0.7 怎麼定，論文未說明 |
| LLM 判斷 | 模型自己給的 | 是模型自述還是 logprob 算的，論文未說明 |

合併階段（附錄 D.1、D.4）：兩路結果按欄位對齊、分開留存，不一致的會保留下來供稽核。最後選哪一路、信心值有沒有參與選擇，論文沒有說清楚（本文作者讀到的 D.1 相關句子在換頁處中斷，可對照原文確認）。

（推論）在本文作者讀到的全文裡，信心值被存了起來，卻找不到任何地方拿它來過濾或加權。一筆資料可不可信，主要靠證據類型（直接證據、結構化主張、摘要推論、無依據）和「證據是否出自原文」來判斷。

---

## 跑模擬：一次 trial 從設定到結果

一次模擬（trial）由五樣設定組成，跑完留下一包證據，再由任務自帶的驗證器轉成有型別的結果。論文的執行平台叫 Playground，四種環境只差在互動方式與留下的證據種類。

### 一次 trial 由什麼組成

| 設定 | 是什麼 |
| --- | --- |
| persona | 一筆 1,290 格的紀錄 |
| task（任務） | 要做什麼、怎麼檢查 |
| agent（操作介面） | 決定 persona 能看到什麼、能做什麼動作，例如對話介面或瀏覽器 |
| model（模型） | 背後負責做決定的 LLM；persona 紀錄配上模型，才叫 persona agent |
| seed（隨機種子） | 讓抽樣與重跑可以重現 |

流程是三步：

```
五樣設定 → 執行 → 留下 artifact bundle（證據包：提交內容、軌跡、環境狀態）→ 驗證器轉成結果
```

論文 5.3 節的 meal-planning（餐飲規劃）任務，就是用這五樣設定組出來的一個實例。同一組設定對 $N$ 位 persona 各跑一次，叫一個 job。每個 trial 互不共用狀態，所以可以平行跑。五樣設定可以各自獨立更換：只改一樣、其他固定，就是一組乾淨的對照。後面〈實驗：結果主要取決於誰在扮演〉的核心實驗，就是只換 model 這一格。

### 四種環境

| 環境 | persona 做什麼 | 論文例子 | 留下的證據 |
| --- | --- | --- | --- |
| Survey 問卷 | 填問卷，做概念測試、價格敏感度 | 汽水漲 2 美元還買嗎 | 結構化答案＋理由 |
| AI Chatbot 聊天機器人 | 跟被測的聊天機器人對話 | 機器人答錯又更正後，還會繼續聊嗎 | 完整對話、工具呼叫、目標是否解決 |
| Web 網頁 | 用瀏覽器自動化或 CUA 逛網站 | 不同預算的人找筆電 | 看過的頁面、動作、截圖、最終提交 |
| App 應用程式 | 用滑鼠、鍵盤或觸控操作原生 App | 找到並修改隱私設定 | 操作序列、最終 App 狀態、檔案或設定變更 |

CUA（Computer-Use Agent，電腦操作 agent）是看螢幕畫面、用滑鼠鍵盤操作電腦的 agent，用在 Web 與 App 環境。App 環境在 Docker 沙盒（隔離的容器環境）裡跑 Linux 桌面程式，macOS 與 iOS 則用遠端桌面或模擬器。四種環境共用同一套 trial 規格。

### 一個任務怎麼寫

任務就是一份可以重跑的實驗說明書，要寫四件事。右欄用論文 5.2 節的汽水漲價例子：

| 這一項 | 要寫什麼 | 汽水漲價例子 |
| --- | --- | --- |
| 測什麼 | 被評估的系統或產品 | 汽水的新價格 |
| 找誰測（cohort） | 要抽哪些 persona、抽多少、用什麼種子 | 不同收入、經濟動機的 persona |
| 情境與目標 | persona 看到什麼、要完成什麼 | 看到漲價，決定還買不買 |
| 證據 | 什麼回應或狀態算數、怎麼檢查 | 買或不買＋理由；檢查兩者都有 |

cohort 存的是「查詢條件加種子」，不是一份名單。同樣的條件加同樣的種子，可以重抽出同一批人；換條件、保持產品與情境不變，就能比較不同族群。每次執行都會記錄「想要的 cohort」與「實際跑出的 cohort」，失敗或缺漏的 trial 留在帳上，不事後補。

任務契約把三樣東西分開放，persona 只拿得到其中一樣。用考試來比喻：

| 放在哪裡 | 放什麼 | 對應考試 |
| --- | --- | --- |
| persona 看到的指令 | 情境與目標（「汽水漲價了，你還買嗎？說明理由」） | 考卷上的題目 |
| 驗證器那邊 | 評分規則（「回答必須同時有購買意圖與理由」） | 老師手上的評分標準 |
| 產品那邊 | 產品帳密、怎麼連到被測產品 | 考場的鑰匙 |

![任務契約的邏輯元件表，列出每個元件宣告的內容與稽核用途，包含 persona 看到的情境、驗證器與產品連線。](img-018)
*表 4 — 任務契約的邏輯元件。（來源：原始論文 Table 10。）*

論文只交代了「分開放」這個原則（5.2 節、表 4），沒說為什麼這樣設計。（推論）用意是避免 persona 為了通過檢查而作答。

### 任務庫有多少，以及這個數字要怎麼讀

任務庫有 1,010 個規格：Survey 621、AI Chatbot 371、Web 12、App 6。領域以 Commerce 207、Software 156、Finance 161、Healthcare 168 為主，其他 318 個分散在 25 個以上的領域（表 5）。

![任務覆蓋表，列為四種環境，欄為 Commerce、Software、Finance、Healthcare、Other 與合計，總數 1,010。](img-004)
*表 5 — 任務庫依環境與領域的分布。（來源：原始論文 Table 3。）*

這個數字看起來很大，但拆開來看就沒那麼漂亮。分母都是 1,010：

| 切法 | 數量 | 占比 |
| --- | --- | --- |
| 模板批次生成（表 6） | 956 | 94.7% |
| Survey 加 AI Chatbot | 992 | 98.2% |
| 真正需要操作介面的 Web 與 App | 18 | — |
| 論文有報告結果的任務 | 8 | 0.8%（自算） |

![大型模板任務集合表，列出合成 persona 問卷、產品問卷與合成聊天機器人三個批次的任務數與組成。](img-017)
*表 6 — 由模板批次生成的任務集合。（來源：原始論文 Table 9。）*

模板批次的 956 個，由合成 persona 問卷 405、產品問卷 200、合成聊天機器人 351 組成（表 6）。1,010 只代表「規格能被找到」；實作過、真正跑過的有多少，論文沒有報告。

### 驗證器怎麼把證據變成有型別的結果

驗證器是任務自帶的檢查程式，原則是規則優先：

- **看得見的結果用程式規則檢查**：輸出格式、必填題有沒有答、最終狀態、權限變更、副作用。
- **只有需要解讀的性質才交給評審**：清晰、同理、可信、persona 有沒有照設定走，這些交給 LLM 或人工評審。評審給的結果會標明出處，並保留它判斷時看的原文。
- **每一條結果都是 typed finding**（有型別的結構化結果）：名稱、型別（數字、類別、布林、文字）、值，以及指向支持它的證據。
- **報告先用不靠 LLM 的方式彙整**（筆數、分布、排名），再選擇性加上 LLM 摘要。報告會存任務版本、想要的與實際跑出的 cohort、模型與 agent 設定、驗證器版本，並連回每一筆 trial 的證據。

整體流程是：單次 trial 先跑規則檢查，評審只在無法化成客觀條件時才出場；產出的 typed finding 再往上彙整成報告。

任務產出、使用者行為、persona 是否照設定、執行失敗，這四類結果分開記，不混成一個分數；任務成功也不被當成「模擬得像真人」的證據（5.2 節）。至於什麼情況算「無法化成客觀條件」而要交給評審，論文沒有界定。

---

## 實驗：結果主要取決於誰在扮演

論文用 GPT 5.5、Claude Opus 4.8、Claude Haiku 4.5 三個模型扮演 persona，跑了八個任務，共 18,189 次 trial。最重要的發現是：結果主要取決於「誰在扮演」，而不是「扮演誰」。

### 實驗 A：換扮演的模型，結論會不會變

這個實驗想分清楚：模擬結果的差異，主要來自 persona 不同，還是 LLM 不同？Candy Land（糖果漲價後還買嗎）這個任務剛好兩邊都能回答。每個模型各跑 1,000 位 persona（論文 Table 13），看的數字是「在新價格下猶豫的人占多少」。

| 比較方式 | 只改了什麼 | 猶豫比例 |
| --- | --- | --- |
| 換扮演的模型 | 模型；persona 完全相同 | GPT 98.3%、Haiku 83.3%、Opus 27.0%，最高與最低差 71.3 個百分點 |
| 同一模型內，按經濟動機把 persona 分四組 | persona 子群；模型固定 | 各組擠在一小段裡：GPT 差 2.0 個百分點、Haiku 差 5.6 個百分點；Opus 至少差 14.0 個百分點，仍遠小於 71.3 |

![八個驗證任務的主要結果表，列出每個任務在 GPT、Opus、Haiku 三個模型下給出同一答案的比例、極差與校正後的 q 值。](img-022)
*表 7 — 八個驗證任務的主要結果。（來源：原始論文 Table 12。）*

換模型的數字在表 7，子群的數字在附錄 F.6。校正後，經濟動機這個因素在三個模型下都不顯著。各組人數論文沒有列在文字裡。

兩點結論：

1. 在這個任務裡，換模型造成的差異（71.3 個百分點）遠大於換 persona 子群（GPT 2.0、Haiku 5.6、Opus 至少 14.0 個百分點，而且統計上不顯著），所以結果主要反映「誰在扮演」，不是「扮演誰」。
2. 這個實驗沒有真人資料對照，不能說哪個模型比較準，只能說模擬結果對模型非常敏感。

### 四個實驗的快速總結

數據來源是表 7、表 8，以及論文 Table 13、論文 Table 14 與附錄 I.2。各實驗做了什麼：

- **A**：同一批 persona 換三個模型扮演，比較同一個問題的答案比例（見〈實驗 A：換扮演的模型，結論會不會變〉）。
- **B**：給 persona 一種說話風格設定（例如表情符號、囉嗦程度、禮貌），分成正向與反向兩組，由 LLM 評審讀軌跡判斷有沒有照做，每次二選一。
- **C1**：請 persona 自述年齡層，跟設定比對，六選一精確比對。
- **C2**：同一批 persona 交給三個模型各演一次，比較 88 個欄位上兩兩的答案是否一致。

| 實驗 | 數據（分母） | 一句話 |
| --- | --- | --- |
| A 換扮演的模型（Candy Land） | 猶豫比例 GPT 98.3%、Haiku 83.3%、Opus 27.0%（各 1,000 位 persona）；同一模型內 persona 子群差距小且不顯著 | 同一批 persona，換模型就得到相反結論 |
| B 受控行為遵守 | Opus 扮演、Opus 評審：366/400＝91.5%；GPT-5.6-sol 扮演：317/400＝79.2% | 說話風格大多能被演出，但不證明人口欄位會影響決策 |
| C1 年齡自述 | 自述年齡層符合設定：GPT 16.3%、Opus 16.9%、Haiku 100%（隨機猜是 16.7%；Haiku 為 1,000/1,000，其他分母論文未列） | GPT 與 Opus 自述的年齡跟設定無關 |
| C2 模型間一致性 | κ 中位數 0.000 到 +0.001；κ ≤ 0 的欄位 59、50、40 個；κ ≥ 0.2 只有 7、8、7 個（皆為 88 個欄位中） | 扣掉碰巧之後，模型之間幾乎沒有一致 |

![三組模型配對的 persona 忠實度表，包含 88 個欄位上的 Cohen's κ 中位數、κ 不大於 0 的欄位數，以及年齡層自述的符合率。](img-025)
*表 8 — 三組模型配對的 persona 忠實度。（來源：原始論文 Table 15。）*

C2 用的 κ（Cohen's kappa）是扣掉「碰巧一致」之後的一致程度，0 代表不比碰巧好，完整說明在〈值得帶走：Cohen's kappa〉。另外，B 實驗的對照模型是 GPT-5.6-sol，跟其他實驗的 GPT 5.5 不是同一個名稱，論文沒有解釋。

### 風格被遵守、年齡自述卻像亂猜：矛盾嗎？

乍看之下，B 說 persona 大多被遵守，C1 卻說年齡自述跟亂猜一樣。其實兩者測的是不同東西：

|  | B 受控行為遵守 | C1 年齡自述 |
| --- | --- | --- |
| 測什麼 | 說話風格（表情符號、囉嗦程度、禮貌…） | 人口欄位（年齡層） |
| 怎麼判 | LLM 評審讀軌跡，二選一 | 自述年齡層是否等於設定，六選一精確比對 |
| 隨機基準 | 約 50%（推論，論文沒報基準） | 16.7% |
| 結果 | Opus 91.5%、GPT-5.6-sol 79.2%（Haiku 沒測） | GPT 5.5 16.3%、Opus 16.9%、Haiku 100% |

B 的 50% 基準是推算出來的：如果模型完全忽略 persona，正向與反向兩組會輸出同一種風格，剛好一組成功、一組失敗，整體約 50%。C1 用的是哪個任務，論文文字沒標；（推論）是有六個年齡組的 Annual checkup。

兩個結果為什麼會並存，論文沒有解釋。（推論）可能有兩個原因：

- 年齡這一格可能根本沒有被當成要演出的內容。論文只說 persona 會被轉成給模型的指令，沒說每一格都會轉（附錄 E.3）。
- 自述題的問法，可能讓模型以「自己」的身分作答。

（推論）把幾個實驗合起來看：實驗 A（persona 子群差異小且不顯著）、C1、C2 都指向人口欄位的影響很弱；只有 B 偏樂觀，而它測的恰好是最容易被執行的風格。所以「persona 被遵守」比較準確的說法是：風格類被遵守，人口類在這份證據下沒有被證明。

---

## 整體評價

一句話：基礎設施做得扎實，值得參考；但「用大量 persona 模擬市場」這個賣點，論文自己的實驗並沒有撐起來。

從實驗數據來看，這套框架適合找問題、壓力測試、比較版本，不能直接拿來估計真實人群的比例。論文自己也建議註明用了哪個模型、跨模型交叉檢查，並保留真人研究。 （推論）具體做法是用多個模型、多種 persona 跑一遍，看哪些情境讓產品出現異常，而不是拿模擬出來的百分比去推論真實使用者。

## 值得帶走：Cohen's kappa

原始一致率會騙人。當答案都偏向同一個選項時，兩邊就算隨便答也會大量撞在一起；Cohen's kappa（κ）先把這部分扣掉，只看多出來的一致。

公式是：

$$
\kappa=\frac{p_o-p_e}{1-p_e}
$$

- $p_o$：實際一致的比例，也就是兩個模型給出相同答案的 persona 占多少。
- $p_e$：如果兩個模型各自照自己的答案頻率獨立作答，預期會碰巧一致的比例。
- 分母 $1-p_e$ 是「碰巧之外，最多還能多一致多少」。
- $\kappa = 1$ 表示完全一致，$\kappa = 0$ 表示不比碰巧好，$\kappa < 0$ 表示比碰巧還不一致。

用 100 位 persona 算兩種情況（數字自編）：

| | 情況一 | 情況二 |
| --- | --- | --- |
| 實際一致 $p_o$ | 82%，看起來很高 | 90% |
| 碰巧一致 $p_e$ | 82%：兩個模型各有 90% 的機率答「是」，光靠碰巧就會一致這麼多 | 50% |
| $\kappa$ | $(0.82-0.82)/(1-0.82) = 0$，沒有任何額外的一致 | $(0.90-0.50)/(1-0.50) = 0.80$ |

情況一的 $p_e$ 是這樣來的（自算）：兩邊都答「是」的機率 $0.9 \times 0.9 = 0.81$，兩邊都答「否」的機率 $0.1 \times 0.1 = 0.01$，加起來 $0.82$。

使用時有兩個提醒：

- κ 只量一致、不量對錯。兩個模型都答錯，κ 也可以很高。
- 一致率高但 κ 很低，通常代表答案太集中在單一選項，不代表兩邊有分歧。

**在這篇論文裡怎麼用：** 論文把 κ 用在「模型對模型」：同一批 persona 交給三個模型各演一次，比較 88 個欄位上兩兩的答案是否一致，三組配對的 κ 中位數是 0.000、0.000、+0.001（表 8）。意思是扣掉碰巧之後，不同模型對同一批 persona 幾乎沒有共同的走向。（推論）這可能是兩個模型都沒怎麼用到 persona，也可能是各自用法不同，論文沒有區分是哪一種。另外，κ 在某些欄位上沒有定義（兩邊都只給同一個答案，分母變成 0），這些欄位怎麼處理，論文也沒說。

## 論文沒交代的地方

大部分留白已經在相關段落就地說明，這裡只做索引：

| 論文沒交代的事 | 在哪一節 |
| --- | --- |
| 依賴圖的邊方向怎麼定、最深幾層 | 〈root 與 child 怎麼決定，依賴只有一層嗎〉 |
| Amazon 從 100,000 到 97,915 的差額、各來源平均填了幾格 | 〈真人資料轉成同一個格式〉 |
| regex 信心值 0.7 怎麼定、LLM 信心值怎麼來、合併時選誰 | 〈LLM 抽取的信心值存了，卻看不出怎麼用〉 |
| 任務契約為什麼要分開放、什麼情況交給評審 | 〈一個任務怎麼寫〉、〈驗證器怎麼把證據變成有型別的結果〉 |
| 1,010 個任務裡實作過、跑過的數量 | 〈任務庫有多少，以及這個數字要怎麼讀〉 |
| Candy Land 各子群人數 | 〈實驗 A：換扮演的模型，結論會不會變〉 |
| C1 除 Haiku 外的分母、GPT-5.6-sol 與 GPT 5.5 的關係 | 〈四個實驗的快速總結〉 |
| 風格被遵守與年齡自述隨機為何並存、C1 是哪個任務 | 〈風格被遵守、年齡自述卻像亂猜：矛盾嗎？〉 |
| κ 為 0 是「都沒用 persona」還是「各用各的」、κ 無定義的欄位怎麼處理 | 〈值得帶走：Cohen's kappa〉 |

## 結論

- **造人**：一筆 persona 是 1,290 個固定選項的欄位。合成的用依賴圖逐欄抽（先驗 × 調整 × 遮罩，再正規化），真人來源轉成同一格式、沒證據就留 null；公開版約 100 萬筆，最多約七成真人紀錄經過 LLM 抽取。
- **跑模擬**：一次 trial 由 persona、task、agent、model、seed 五樣決定，證據交給規則優先的驗證器轉成 typed finding。任務庫 1,010 個，但九成以上是模板批次生成的問卷與聊天任務，有報告結果的只有 8 個。
- **實驗**：換扮演的模型，Candy Land 的猶豫比例從 27.0% 跳到 98.3%；同一模型內換 persona 子群，差距小得多（GPT 2.0、Haiku 5.6、Opus 至少 14.0 個百分點）且統計上不顯著。風格設定大多被演出，年齡這類人口欄位則沒有被證明有作用，模型之間的 κ 也接近 0。
- **怎麼用**：拿來找問題、壓力測試、比較版本很合適；拿來估計真實人群的比例就不行，而且一定要註明用了哪個模型、做跨模型檢查。
- **帶走一個工具**：看兩組答案一不一致時，別只看原始一致率，先用 Cohen's kappa 把碰巧的部分扣掉。

```figure-map
[
  {
    "id": "img-002",
    "references_manifest_caption": "Table 1: Persona 8B schema overview. Dimension counts refer to emitted categorical attributes. Sources provide different kinds and strengths of grounding; they do not imply direct population estimates for every value.",
    "why_used": "支撐說明一筆 persona 的 1,290 個欄位分成五大類的段落。",
    "agent_match_hint": "一張四欄表格：Top-level group、Dims.、Representative attributes、Representative grounding，最後一列 Total 1,290。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "Figure 5: The full persona DAG. All 1,308 graph nodes and 6,999 directed edges. Nodes are placed left to right by the topological order used in Equation 5 and grouped vertically into one lane per schema category, with lanes ordered by their mean topological position; marker area scales with a node’s directed degree. Edges are drawn as translucent curves, so darker bands mark the depen- dency bundles that connect demographic and educational roots to downstream expertise, interest, and behavior dimensions.",
    "why_used": "說明依賴圖的深度只能從完整 DAG 看出來，放在 root 與 child 的段落。",
    "agent_match_hint": "一張很寬的網路圖，左側是欄位類別名稱，節點由左到右排列，大量半透明曲線連接，右上角有 degree 圖例。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Table 2: Composition of the public Persona 1M coreset. “Human-grounded” identifies the origin of a record, not a guarantee that every extracted field is a verified fact. These counts mirror the Composition table of the dataset card (footnote ∗), which is the authoritative record for the release.",
    "why_used": "支撐真人來源各組筆數與合計 599,847 的段落。",
    "agent_match_hint": "一張兩欄小表格：Source、Released records，列出 Wikipedia、Amazon Review、Stack Overflow 等來源與 Human-grounded subtotal、Full-DAG synthetic。"
  },
  {
    "id": "img-018",
    "references_manifest_caption": "Table 10: Logical components of an application-task contract.",
    "why_used": "支撐任務契約把 persona 指令、驗證器與產品連線分開放的段落。",
    "agent_match_hint": "一張三欄表格：Contract component、Declared content、Audit purpose，列有 Task metadata、Persona-facing scenario、Verifier 等。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Table 3: Application-task coverage. Counts are unique specifications on the repository’s main branch together with the batch collections on its synthetic-task branches; individually contributed tasks still under review on open pull requests are not counted. “Other” aggregates more than 25 additional domains.",
    "why_used": "支撐任務庫 1,010 個規格依環境與領域分布的段落。",
    "agent_match_hint": "一張格狀表：欄為 Commerce、Software、Finance、Healthcare、Other、Total，列為 Survey、AI Chatbot、Web、App、Total。"
  },
  {
    "id": "img-017",
    "references_manifest_caption": "Table 9: Large template-based task collections. Members of a collection are separate task specifications but reuse a common contract and verifier pattern.",
    "why_used": "支撐 956 個任務來自模板批次生成、占 94.7% 的段落。",
    "agent_match_hint": "一張四欄表格：Collection、Tasks、Environment、Composition，第一列 Synthetic persona surveys 405。"
  },
  {
    "id": "img-022",
    "references_manifest_caption": "Table 12: Complete primary-outcome results for the eight validation tasks. Range is the largest minus smallest model share in percentage points. The 𝑞column reports a three-arm 𝜒2 test after Benjamini–Hochberg correction across the eight tasks (∗∗∗𝑞< 0.001, ∗𝑞< 0.05; ns otherwise).",
    "why_used": "支撐 Candy Land 換模型後猶豫比例相差 71.3 個百分點的實驗 A。",
    "agent_match_hint": "一張八列的結果表：Task、Env.、Primary outcome、GPT、Opus、Haiku、Range (pt)、q，列有 Annual checkup、Candy Land price 等。"
  },
  {
    "id": "img-025",
    "references_manifest_caption": "Table 15: Persona fidelity across all three model pairs. Cohen’s 𝜅corrects raw agreement for each model’s answer distribution. GPT and Opus age-band matches are indistinguishable from uniform guessing (𝑞= 0.84 and 𝑞= 0.85); Haiku matches 1,000 of 1,000 trials.",
    "why_used": "支撐年齡自述符合率與模型間 κ 中位數接近 0 的快速總結，也在 Cohen's kappa 一節被引用。",
    "agent_match_hint": "一張表格，欄為 GPT × Opus、GPT × Haiku、Opus × Haiku，上半是 88 個欄位的 Cohen's κ 統計，下半是年齡層自述符合率。"
  }
]
```
