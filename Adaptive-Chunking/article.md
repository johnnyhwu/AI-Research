# Adaptive Chunking：讓 RAG 系統學會「因材施教」的切分策略

做過 RAG（Retrieval-Augmented Generation）系統的人大概都有類似的經驗：花了大把時間換更貴的 Embedding 模型、調 Prompt、甚至上了 Rerank，結果系統還是常常答非所問。

問題往往不在後段的檢索或生成，而是在最前面、最容易被輕忽的一步——把文件切成一塊一塊的 chunk，寫進向量資料庫。

這篇論文談的就是這件事：文本切分（Document Chunking）品質不好，後面再怎麼補都補不回來。切得不好，向量資料庫裡存的知識顆粒度就是錯的，檢索器抓不到完整又精準的上下文，下游 LLM 再強也只是「垃圾進、垃圾出」。

## 三個切分老問題，一直沒被真正解決

作者整理出目前 chunking 實務上三個尚未妥善解決的痛點。

第一個是**上下文保存困境**：傳統切法多半依賴固定字元長度或標點符號硬切，一刀下去很容易把邏輯連貫的段落切成兩半，甚至把代名詞（「它」）跟它指代的實體（某個技術名詞）分到不同 chunk，語意就這樣斷了。

第二個是「一招打天下」的迷思：多數工程管線圖方便，全庫統一套用同一套切法，例如全部用 LangChain 的 Recursive Splitter、限制 1000 tokens。

但真實世界的知識庫往往異質性很高——排版嚴謹的法律合約、塞滿表格的技術手冊、純敘事的學術論文全混在一起，不存在哪一種切法能通吃所有結構。

第三個問題比較根本：業界缺乏一把可以獨立衡量「這個 chunk 切得好不好」的尺。開發者通常只能整套 RAG 流程跑完，看最終答案準不準來反推切分好壞，但這種做法把檢索器和生成模型的雜訊全混進來了，根本沒辦法單獨拆解出切分本身的影響。

論文提出的 **Adaptive Chunking** 框架，核心想法是把「靜態盲切」換成「動態評估與選擇」：不再執著找一種萬能切法，而是幫每份文件同時試跑多種切分方法。

再用一套不需要真的跑 RAG 就能打分的「內在評估指標」去比較，自動選出得分最高的那一版寫入資料庫——說白了就是讓系統自己「因材施教」。

## 前處理：先把 PDF 轉成乾淨的 Markdown

在切分之前，作者其實還做了一層前處理：把 PDF 轉成結構化程度更高的 Markdown，而不是直接丟純文字給後面的切分演算法。這一步很重要，因為純文字會把表格、標題、段落之間的結構線索全部抹平，切分演算法等於是瞎子摸象。

這套客製化的轉換管線裡藏了幾個工程細節：

- **超大表格拆解＋保留表頭**：避免表格切到一半時，後面的資料失去欄位對照。
- **頁首頁尾過濾與歸類**：減少之後檢索時混進不相關的雜訊。
- **標題、註腳與對應內文綁定成不可分割的區塊**：避免切分時把彼此的關聯性打散。

這幾個看似瑣碎的前處理巧思，其實是後面所有切分演算法能夠「感知結構」的基礎。

## 切分工具箱：兩款新設計的演算法

為了讓候選切法池夠多元，作者除了常見的基準方法（按頁切、按句切）之外，另外設計了兩款兼顧「結構感知」與「執行效率」的新演算法。

### 演算法一：LLM-guided Regex Splitter

對合約、法規這類結構規律很強的文件，傳統按字數遞迴切分很容易破壞條款的完整性；但直接叫 LLM 切全文，運算時間跟 API 成本又會爆炸。

這個演算法走了一條折衷路線：把 LLM 降維成「規則產生器」。系統只讓 LLM 讀文件前段（大約 8,000 tokens），歸納出最適合這份文件的正則表達式（Regex）分隔符，之後全文就交給 Python 原生的 `re.split()` 在毫秒等級內切完。

要讓 LLM 穩定吐出可用的 Regex，Prompt 設計上做了幾層防呆：

- **強制輸出格式**：只准輸出一段相容 Python `re` 引擎的正則表達式，並用 `<regex>...</regex>` 包起來，方便程式直接解析。
- **結構保護指南**：明確要求不能切斷用 `<Table>` 標籤包起來的表格，完美銜接了前面前處理階段建立的結構化文本。
- **Few-shot 範例**：示範「輸入文本 → 期望 Regex」的對應，穩定模型的推理邏輯。

![LLM 輔助的正則表達式切分管線與 Prompt 設計：左邊是從抽樣文本、產生 Prompt 到套用 Regex 切分的流程，右邊是實際的 Prompt 內容。](img-009)
*圖：LLM Regex splitter 的執行流程。系統只讓 LLM 看一小段樣本文字，產生規則，再用原生 Regex 引擎切分全文，兼顧了 LLM 的理解力與程式執行的效率。（來源：原始論文 Figure 3）*

### 演算法二：Split-then-Merge Recursive Splitter

這款演算法是對業界主流 LangChain `RecursiveCharacterTextSplitter` 的深度改良，主要解決的是傳統遞迴切分在邊界控制跟重疊機制上的老毛病。

傳統的遞迴切分是 **Top-Down** 邏輯：區塊大於上限（比如 1000 tokens）就找優先級較高的分隔符（像雙換行）切開，一旦切下來的片段小於等於上限，就停手當成最終 chunk。

這套邏輯的致命傷是完全沒有「下界」控制——如果切出來的片段只有 50 個 token，演算法照樣照單全收，結果產出一堆缺乏上下文、白白佔用檢索空間的「極小碎片」。

本論文的做法反過來，採用 **Bottom-Up** 的兩階段策略：

- **第一階段「無腦切細」**：依照事先排好優先順序的 Markdown 分隔符表，一路遞迴切到所有片段都小於目標大小 S，文本這時候變成一堆微小的結構單元。
- **第二階段「貪婪合併」**：由上而下遍歷這些小片段，只要累加起來的 token 數不超過上限 S，就持續往下併，直到逼近上限為止。

這套順序幾乎完全消滅了無意義的微小碎片。

重疊機制也做了調整。傳統做法多半是被動依字元數截斷，很容易把句子切碎。

這個演算法在合併過程中，一旦加入下一個片段會超過上限，就開啟新的 chunk，並啟動「回溯」機制——新 chunk 會複製上一個 chunk 結尾的「完整結構碎片」（比如一個完整句子）當開頭，讓重疊是以語意單元、而不是字元數為基準。

![兩階段的 split-then-merge 流程圖：文字先依分隔符優先順序遞迴切到極細，再由上而下貪婪合併，超過上限時以回溯方式帶入上一段結尾的完整片段作為重疊。](img-011)
*圖：Split-then-Merge 遞迴切分管線。先打碎、再合併、必要時回溯重疊，兩階段設計解決了傳統 Top-Down 遞迴容易產生碎片的問題。（來源：原始論文 Figure 5）*

![分隔符優先順序表，由高到低排列，包含 Markdown 各級標題對應的正則表達式。](img-010)
*圖：切分時使用的分隔符優先順序清單。演算法會優先處理 Markdown 的各級標題（例如一級標題對應的正則規則），確保同一個標題底下的內文能在合併階段優先被組合在一起。（來源：原始論文 Figure 4）*

兩種遞迴切分法的差異，整理起來大概是這樣：

| 比較項目 | 傳統 Recursive Splitter（LangChain 原生） | Split-then-Merge Recursive（本論文改良） |
| --- | --- | --- |
| 運作方向 | Top-down，切到低於上限就停 | Bottom-up，先切到極細，再貪婪合併到上限 |
| 碎片控制 | 弱，容易產生大量 0~50 token 的廢棄碎片 | 強，合併機制大幅提高空間利用率 |
| 重疊機制 | 被動依字元數截斷，容易破壞句子完整性 | 主動以完整結構片段為單位回溯重疊 |
| 結構感知力 | 弱，只靠原生換行與空白判斷 | 強，深度整合 Markdown 標題與列表的正則規則 |
| 尺寸合規性 | 不穩定，變異數大 | 高，Size Compliance 指標表現優異 |

## 品質保證：強制性的後處理防線

不管前面的切分演算法設計得多細，遇到排版特別異常的文件，還是難免會出現不符規格的「離群 chunk」。這些極端值不只會干擾 Embedding 的語意表達，更可能變成污染檢索結果的雜訊。所以作者在所有切分演算法跑完之後，額外掛了一道雙階段的強制品管機制，只針對極端值出手，不動正常尺寸的 chunk。

第一道防線是**過大重切**。如果切分結果（例如 LLM Regex 判斷失準時）產出遠超過上限（論文設定 1,100 tokens）的超大 chunk，裡面往往混雜了好幾個不相關的主題——技術規格跟免責聲明包在一起是常見情況。

Embedding 模型被迫把這些龐雜概念壓進同一個向量時，關鍵語意訊號會被嚴重稀釋，檢索時很難跟使用者的具體查詢對上。

系統的做法是：一旦偵測到超過 1,100 tokens 的 chunk，就用前面提到的分隔符優先順序規則（依序找段落、換行、句號）硬切開，把它拉回合理範圍。

第二道防線是**極小合併**。切分過程中遇到殘缺表格、孤立數字、孤兒標題，很容易產出低於幾十個 token 的微型碎片。這些碎片沒有實質內容，但要是剛好包含使用者查詢的關鍵字（尤其在用 BM25 這類詞彙匹配演算法時），反而可能搶佔寶貴的 Top-k 檢索名額，讓 LLM 讀到一堆無意義的背景資訊，進而產生幻覺或直接拒答。

系統設了下限（論文用 100 tokens），偵測到過小的碎片就嘗試跟前後相鄰段落合併，但合併前會先檢查：只有合併後總長度不超過寬鬆上限（1,150 tokens）才會真的執行，避免合併出另一種超大 chunk。

這兩道防線看起來簡單粗暴，但效果很扎實。經過後處理，原本尺寸合規性（SC）表現極不穩定的演算法（像未加工的語意切分器或 LLM Regex）都躍升到接近滿分。

而且極端值幾乎被徹底消滅：後處理前，不少傳統基準方法會產出僅 0 到 4 個 token 的廢棄碎片，後處理後所有方法的最小長度都被穩定拉到 69 到 104 tokens 的健康範圍。

![Table 2 呈現各切分方法的 chunk 尺寸統計與執行時間；Table 7 呈現後處理前後 Size Compliance 的變化。](img-002)
*圖：各切分方法的 chunk 尺寸與執行時間統計。標有十字記號（†）的是未經後處理的傳統方法，可以看到它們的最小長度欄位經常出現 0 到 4 個 token 這種無意義碎片。（來源：原始論文 Table 2）*

![後處理管線對 Size Compliance 的具體提升幅度對照表。](img-012)
*圖：後處理前後的 Size Compliance 對照。LLM Regex 與語意切分器原本的合規率只有約 58% 與 48%，經過「過大重切」加「極小合併」雙管齊下後，兩者都飆升到 99% 以上。（來源：原始論文 Table 7 相關數據）*

## 核心創新：不用真的跑 RAG 也能打分的五個指標

傳統要評估一種切分方法好不好，得先把 chunk 寫進資料庫，串起檢索器跟 LLM 跑一輪端到端測試。這種「外在評估」不只運算成本高，還很難判斷到底是切分不好、Embedding 語意跑偏，還是 LLM 本身理解力不足——三個環節的誤差全部混在一起。

論文提出的解法是「內在評估」：跳過檢索跟生成這兩步，直接用輕量級的專用 NLP 模型、向量餘弦相似度、加上排版結構邊界，對切分後的 chunk 做五個維度的打分，每個指標分數都落在 0 到 1 之間。

### RC（References Completeness，參考完整性）

這個指標要抓的是「代名詞消解失敗」這個 RAG 死穴——如果一個實體（比如「特斯拉」）跟指代它的代名詞（「它」）被切刀分到不同 chunk，檢索只抓到代名詞那一塊時，LLM 就會因為資訊不完整而答不出來。

計算方式是先用共指解析模型 **Maverick**（ACL 2024）掃過全文，找出所有「實體—代名詞」配對，記下每一組配對在原文中的字元位置範圍。

接著檢查每一刀切下去的位置有沒有落在某組配對的範圍中間，只要有一刀切斷了配對，這組配對就算「被破壞」，沒有任何一刀切進範圍才算完整保留。RC 分數就是「完整保留的配對比例」。

舉個具體例子比較好懂。假設輸入文本是：

```
"Elon Musk founded SpaceX. He wants to land on Mars with his rockets."
```

Maverick 模型會輸出類似這樣的共指簇資料：

```json
[
  {
    "cluster_id": 0,
    "entity": "Elon Musk",
    "mentions": [
      {"start": 0, "end": 9, "text": "Elon Musk", "type": "PROPER"},
      {"start": 26, "end": 28, "text": "He", "type": "PRONOUN"},
      {"start": 54, "end": 57, "text": "his", "type": "PRONOUN"}
    ]
  }
]
```

系統從這份資料萃取出兩組關鍵範圍：「Elon Musk → He」對應字元位置 0 到 28，「Elon Musk → his」對應 0 到 57。

如果切分器剛好在 `founded` 後面（字元位置 15 附近）切了一刀，這一刀正好落在這兩組範圍裡面，RC 計算就會把這兩組配對都標記成「被切斷」——這一刀雖然位置看起來平凡無奇，實際上卻同時傷到了兩個代名詞指代關係。

### ICC（Intrachunk Cohesion，塊內內聚度）

這個指標關心的是單一 chunk 有沒有「跑題」。做法是把一個 chunk 拆成好幾個句子，分別算出每個句子的 Embedding 向量，以及整個 chunk 的整體向量（論文用的是 Jina AI v3）。

再算每個句子跟整體向量的平均餘弦相似度：相似度越高，代表這個 chunk 裡的句子越集中在同一個主題上，ICC 分數就越高。

### DCC（Document Contextual Coherence，上下文連貫性）

DCC 剛好跟 ICC 拉扯：它要確保 chunk 不會變成一座沒有背景脈絡的孤島。

做法是在全文上開一個最大 3,000 tokens 的滑動視窗，涵蓋好幾個相鄰的 chunk，算出視窗整體的向量，再看視窗內每個 chunk 跟這個大環境向量有多接近。分數越高，代表 chunk 跟周遭脈絡的關聯性保存得越好。

### BI（Block Integrity，區塊完整性）

BI 要保護的是表格、圖說、段落這類「天然結構」不被硬性截斷破壞。系統事先記錄好每個表格或段落的起訖字元位置，當成「保護區間」，再檢查有沒有任何一刀切進區間內部（容許 5 個字元的誤差，排除換行符干擾）。

只要沒有任何刀口切進去，這個區塊就算完整，BI 分數就是所有區塊「完整與否」的平均。BI 等於 1，代表所有表格、段落都保持了 100% 完整。

### SC（Size Compliance，尺寸合規性）

這個最直觀，就是計算 chunk 長度落在 100 到 1,100 tokens 這個指定範圍內的比例，直接反映有多少 chunk 沒有過大或過小的問題。

## 動態決策：系統怎麼幫每份文件挑切法

有了候選演算法跟評分指標之後，系統進入最後的整合決策階段：針對每一份輸入的文件，自動跑完「並行切分 → 五維打分 → 加權決選 → 寫入向量庫」這一整套流程。

具體來說分四步：

1. **並行生成候選**：系統同時用好幾種性質不同的切分方法處理同一份文件（都掛著前面提到的後處理品管），論文的候選池包含頁面切分（後處理過）、遞迴切分（s=1100）、遞迴切分（s=600）、以及 LLM Regex（用 GPT-5）這四種。
2. **五維打分**：對這四組結果分別算出 RC、ICC、DCC、BI、SC 五項分數。
3. **加權決選**：為了維持框架的通用性、避免對特定資料集過度擬合，作者用最簡單直觀的等權重算術平均當最終分數，五個指標各佔五分之一。
4. **動態寫入**：系統比對四種方法的最終分數，只留下分數最高的那一組去做 Embedding、寫進向量資料庫，其餘全部捨棄。

這套機制在實際 33 份跨領域文件庫上的表現，直接證實了「單一策略」注定行不通。

![四種候選切分方法在整個文件庫中被選中的比例分佈。](img-006)
*圖：Adaptive 框架在異質文件庫中的演算法選中比例。頁面切分被選中 48%，遞迴切分（s=1100）被選中 42%，LLM Regex 和小尺寸遞迴合計佔剩下的 9%。沒有任何一種切法能壟斷所有文件類型——這份分佈本身，就是對「單一最佳切分法」最直接的反駁。（來源：原始論文 Table 4）*

這裡有個挺有意思的細節：遞迴切分（s=1100）單獨拿出來看，平均內在分數其實是所有方法裡最高的，但系統實際運作時，頁面切分反而在將近一半的文件上勝出。

這說明「平均表現最好」跟「對每一份具體文件都最好」根本是兩回事——這也正是 Adaptive 框架存在的意義：不是找一個全域最優解，而是讓每份文件都能配到適合自己結構的切法。

當然，這套機制不是沒有代價。根據論文的執行時間數據：

- 計算 DCC 最耗時，花了 15 分 58 秒，因為要對滑動視窗反覆算向量。
- 用 Maverick 做實體代名詞提取花了 13 分 13 秒，主要卡在 CPU 上串行聚類的瓶頸。
- LLM Regex 因為要呼叫 LLM，平均單次運行也要 146.85 秒。

整個語料庫跑完 Adaptive 流程，平均總耗時大約 210.66 秒。

不過這筆開銷值不值得，得看它花在哪個階段。切分跟指標評估都只發生在「離線」的建置索引階段，一旦 chunk 寫進資料庫，線上檢索跟生成的延遲完全不受影響。換句話說，這是用離線幾分鐘的運算，換線上長期穩定的答案品質——對多數企業級應用來說，這筆帳算下來相當划算。

## 這套指標真的有用嗎？看下游數據說話

前面講了一堆內在指標，但工程師真正關心的問題是：分數高的 chunk，真的能換來更準的答案嗎？為了驗證這件事，作者設計了一組控制變因實驗——檢索器（Hybrid Search）、重排器、生成模型（GPT-4.1）全部固定不變，唯一改變的是寫入向量庫時用的切分策略。

![Adaptive Chunking 與其他基準方法在檢索完整性、答案正確性等下游指標上的對照表。](img-007)
*圖：下游 RAG 效能對照。Adaptive Chunking 篩選出的高分 chunk，在檢索完整性（Retrieval Completeness）上達到 67.68%，比常見的 LangChain 遞迴基準（58.08%）高出 9.6 個百分點；答案正確性（G-Eval）則達到 78.01%，比基準高 7.9 個百分點。在總共 99 題測試中，Adaptive 方法答對了 65 題，基準方法只答對 49 題。（來源：原始論文 Table 5）*

這組數據算是內在指標有效性的鐵證：分數高的切分結果，確實能實打實轉化成更好的下游答案品質。

不過，想靠單一參數就同時把五個指標都拉滿，現實中做不到。作者算了指標兩兩之間的斯皮爾曼相關係數，結果普遍落在弱相關到中度相關之間（介於 -0.44 到 0.31），說明這五個指標各自捕捉了切分品質的不同面向，彼此互補而不是重複計算同一件事。

![五個內在指標兩兩之間的斯皮爾曼相關係數矩陣。](img-003)
*圖：內在指標之間的相關係數矩陣。ICC 跟 DCC 呈現顯著負相關（ρ = -0.44），ICC 跟 BI 也呈負相關（ρ = -0.34）。（來源：原始論文 Figure 1）*

這兩組負相關背後其實都有物理上的道理：

- **ICC vs. DCC**：反映切分尺寸的天生極限。chunk 切得越小，主題越純（ICC 越高），但跟周圍文本的關聯性也跟著流失（DCC 越低）。
- **ICC vs. BI**：是另一種取捨。如果為了保住高 BI 分數，硬把一整段表格或段落綁在一起不切開，往往得連帶把一些不相關的引言、過渡句塞進同一個 chunk，結果反而拉低了語意純度。

工程師在調整切分策略時，與其幻想找到一個五項全滿分的完美參數，不如接受這些取捨是結構性的，再依實際應用場景決定要偏向哪一邊。

還有一個現象特別值得工程師警惕：Adaptive Chunking 的平均內在得分是 91.07%，傳統 LangChain 遞迴切分（預設參數）是 88.62%，兩者只差 2.45 個百分點，看起來不算大。

但這個小差距一旦丟進完整的 RAG 管線跑一輪，到了下游輸出端卻被放大了好幾倍：檢索完整性差了 9.6 個百分點，答對題數的相對成長幅度更高達 32.7%（也就是前面提到的 65 題對 49 題那組數字）。

這是典型的錯誤累積放大效應。RAG 本質上是一條多步驟串接的管線，切分階段一個看似微小的語意偏移（比如一個代名詞的主詞被切斷，讓向量產生一點點偏移），會沿著管線逐級放大：

1. 檢索階段：這個 chunk 的餘弦相似度掉出 Top-k 名單。
2. 重排階段：因為資訊不完整被排到後面。
3. 生成階段：LLM 讀到的是殘缺的上下文，只好選擇安全牌回答「我不知道」。

前處理跟切分階段的優化，在 RAG 系統裡不是線性關係，而是會被後面的環節逐級放大——這也是為什麼，把資料洗鍊乾淨的投資報酬率，常常比在管線尾端對 LLM 做複雜微調高得多。

## 給 AI 工程師的實務建議，以及這套框架還有哪些限制

整篇論文的實驗結果，對實際在做 RAG 系統的工程師來說，大概可以濃縮成三條可以直接落地的建議。

第一，別再迷信單一切分參數。不同結構的文件對切分方法有明顯不同的偏好，與其花時間微調一組「萬用參數」，不如建一個包含頁面切分、遞迴切分、規則切分的候選池，讓系統依文件特性動態挑選。

第二，後處理是報酬率最高的優化。實作「過大重切」和「極小合併」這兩道後處理防線，代價很低，卻能有效清掉檢索階段最惱人的雜訊——微型碎片跟語意稀釋的超大 chunk——讓向量資料庫的品質穩定不少。

第三，把資源花在資料輸入層。把 PDF 轉成保護好表頭、實體關聯、標題內文綁定的高品質 Markdown，這件事對最終答案正確率的貢獻，往往比盲目換一個更大的 LLM 來得實在。

當然，這套框架也不是沒有代價跟侷限：

- **離線建置的運算開銷偏高**：尤其是計算 DCC 跟用 Maverick 做實體代名詞提取都很花時間。在百萬甚至千萬級 token 的大規模生產環境裡，Maverick 缺乏批次處理能力會是個明顯的效能瓶頸，未來可能得找更輕量、支援 GPU 批次加速的替代方案。
- **權重分配仍是粗略的算術平均**：目前五個指標是用最簡單的 1:1:1:1:1 算術平均，但不同應用場景對指標的敏感度顯然不一樣——重視精準數據的金融場景可能更在意 Block Integrity，重視流暢問答的客服場景可能更依賴 DCC。怎麼自動學出適合場景的權重分配，還是留待未來研究的問題。
- **多語言支援受限**：RC 指標高度依賴 Maverick 這個共指解析模型，而它目前只支援英文。如果要把這套框架搬到中文或其他語言的 RAG 系統上，得先找到並驗證對應語言的共指解析工具，這會增加不少工程複雜度。

```figure-map
[
  {
    "id": "img-009",
    "references_manifest_caption": "Figure 3: LLM Regex splitter pipeline. From markdown input and a token budget, the system builds a context-aware prompt, obtains a delimiter regex from the LLM, and applies it to split the document into chunks.",
    "why_used": "支撐説明 LLM-guided Regex Splitter 如何結合 LLM 的規則歸納與 Regex 執行效率的段落。",
    "agent_match_hint": "一張流程圖,左側是從樣本文字產生 Prompt 到套用 Regex 切分的步驟,右側附有實際 Prompt 內容。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Figure 5: Split–then–merge recursive splitter pipeline. Text is recursively split following a priority list of separators until each piece is ≤chunk size, then merged forward into chunks; when the next piece would exceed chunk size, a new chunk starts with up to chunk overlap tokens of backtracked overlap.",
    "why_used": "支撐説明 Split-then-Merge 演算法兩階段(打碎、合併)加回溯重疊機制的段落。",
    "agent_match_hint": "兩階段流程圖,展示文字先被切到極細,再由上而下貪婪合併,並在超過上限時以回溯方式帶入重疊片段。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "Figure 4: Regex separators list for recursive splitters, adapted to our Markdown parser outputs. The list is sorted from highest to lowest priority.",
    "why_used": "支撐説明分隔符優先順序如何讓演算法優先辨識 Markdown 標題,提升結構感知力的段落。",
    "agent_match_hint": "一份由高到低排序的分隔符清單表格,包含 Markdown 各級標題對應的正則表達式。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Table 2: Chunk sizes in tokens (OpenAI’s o200k_base) and runtime statistics. Chunking methods marked with ∗are included in the Adaptive Chunking results. Those marked with † were not post-processed; ** was computed considering asynchronous API calls.",
    "why_used": "支撐説明後處理前,傳統方法容易產生極小碎片的段落。",
    "agent_match_hint": "一張表格,列出各切分方法的 chunk 尺寸統計(含最小值、最大值)與執行時間,部分列標有十字記號。"
  },
  {
    "id": "img-012",
    "references_manifest_caption": "Table 7 reports the detailed effect of our two-stage post-processing pipeline on Size Compliance (SC) and overall mean chunking scores. The pipeline consists of: (1) oversized re-split, applied only to chunks exceeding 1100 tokens, and (2) tiny-chunk merge, applied only to chunks smaller than 100 tokens, with a maximum merged size of 1150 tokens. The “–” symbol indicates that a particular step was not required for that method (e.g., our recursive splitters with s = 1100 or s = 600 already produce well-sized chunks in the raw output).",
    "why_used": "支撐説明後處理如何大幅提升 Size Compliance 指標的段落。",
    "agent_match_hint": "一張表格,對照後處理前後各方法的 Size Compliance 百分比與平均分數變化。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 4: Results for chunking method selection in the Adaptive Chunking method with respect to the entire document corpus. Other chunking methods were not selected and omitted here.",
    "why_used": "支撐説明沒有任何單一切分方法能壟斷所有文件類型的段落。",
    "agent_match_hint": "一張表格或長條圖,顯示四種候選切分方法各自被系統選中的文件比例。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Table 5: RAG performance results (% mean) evaluated using OpenAI’s GPT-4.1 (temperature = 0) as the LLM judge. Retrieval Completeness is evaluated for all queries, while Answer Correctness skips queries where the model decided not to provide an answer (insufficient context). Highest scores per column are marked in bold; “LC\" means LangChain. Retrieval Completeness differences are statistically significant (Wilcoxon signed-rank, p < 0.05).",
    "why_used": "支撐説明內在指標分數高的切分結果,確實能轉化為更好下游 RAG 表現的段落。",
    "agent_match_hint": "一張表格,對照不同切分方法在檢索完整性、答案正確性等欄位上的百分比數據。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 1: Spearman correlation (ρ) between chunk- ing metrics, computed using the metric results for each document and chunking method.",
    "why_used": "支撐説明五個內在指標之間存在互補而非重複關係的段落。",
    "agent_match_hint": "一張相關係數矩陣圖或熱力圖,顯示五個指標兩兩之間的斯皮爾曼相關係數。"
  }
]
```
