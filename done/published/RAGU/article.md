# RAGU：一篇替 GraphRAG 量出天花板的論文（雖然它本來想證明別的）

## 前言

RAGU 是 ITMO University 團隊在 2026 年 7 月放上 arXiv 的 GraphRAG 引擎，附帶一個 7B 的抽取模型 Meno-Lite-0.1，兩者都開源（`pip install graph_ragu`，MIT 授權）。論文的主張是：把知識圖的「抽取」跟「整併」拆成兩個階段，圖會更乾淨，檢索也會更完整。

這篇文章要談的不只是它做了什麼，而是把它的實驗設計拆開來看之後剩下什麼。結論會有點反直覺：RAGU 論文本身的研究貢獻很薄，但它的數據表裡藏著一個很少有人願意發表的數字——**整套 GraphRAG 相對於「什麼圖都不建、純向量檢索」的淨貢獻，只有 1.2 到 4.3 個百分點**。這個數字比論文想證明的任何一件事都有價值。

沿路會帶到三個脫離這篇論文也成立的觀念：去重跟分群為什麼是兩種不同的任務、圖分群跟向量分群的「像」差在哪，以及最重要的——檢索指標好不等於答案好。

## GraphRAG 在解什麼問題

先把背景鋪一下。標準的 RAG 做法是把文件切成 chunk、轉成向量存起來，使用者提問時撈出最相似的幾塊塞進 prompt。這種檢索是扁平的：每個 chunk 各自獨立，系統看不到跨文件的關聯。如果答案需要「A 文件提到的人」跟「B 文件提到的公司」之間的關係，向量相似度撈不出來。

GraphRAG 的解法是先請 LLM 把文件裡的實體（人、組織、產品）跟關係抽出來建成知識圖，檢索時可以沿著圖上的邊走。這條路線上的代表系統是 Microsoft GraphRAG、LightRAG 跟 HippoRAG 2。

RAGU 認為現有系統有三個問題：一次性抽完就建圖，產生大量重複與噪音實體，沒有跨 chunk 整併的機制；預設要用 GPT-4 等級的模型做抽取，成本太高；開源框架工程品質參差，甚至有對 LLM 原始輸出直接跑 `eval()` 這種不安全路徑。它針對這三點分別提出多步驟 pipeline、7B 的 Meno-Lite-0.1，以及一套認真寫過的工程實作。

## 「7B 就夠了」這個假說，還有它的問題

論文最核心的科學主張是：LLM 在 RAG pipeline 裡做的事——讀懂 context、抽實體、摘要、從 context 生答案——屬於語言能力，而不是世界知識。語言能力隨模型規模成長很慢，世界知識成長很快。所以抽取端用 7B 就夠。

證據是這張圖：

![CheGeKa 與 MultiQ 兩項任務在 Qwen2.5-Instruct 家族上的 F1 隨模型規模變化，世界知識任務的成長曲線明顯比語言能力任務陡。](img-001)

*圖一 — 世界知識（CheGeKa）與語言能力（MultiQ）兩類任務隨模型規模的成長差異。（來源：原始論文）*

兩個任務的性質差在哪：CheGeKa 是俄語常識問答，沒有 context，純粹考背下來的知識；MultiQ 是多跳問答，所有事實都在 context 裡。論文報的數字是 0.5B 到 72B 之間，CheGeKa 成長 21.1 倍，MultiQ 只有 4 倍。

這個比法有灌水成分。CheGeKa 在 0.5B 時 F1 幾乎貼地（約 0.015），分母趨近於零，任何成長換算成倍數都會很誇張；MultiQ 起點高（約 0.12），而且大概在 32B 就打到天花板（約 0.57 之後持平），倍數小有一部分是因為它飽和了。真正站得住腳的是同一張圖裡的 log-linear 斜率 0.65 對 0.26，至少是同一個尺度上的比較。論文卻把「21.1 倍 vs 4 倍」放進 abstract 當主打。

還有兩個問題。第一，MultiQ 測的是「讀 context 回答問題」，但 pipeline 真正的關鍵動作是抽出結構化的實體與關係——而論文自己的資訊抽取實驗顯示，純 Qwen2.5 家族在抽取上是單調隨規模上升的（7B 0.356 → 14B 0.396 → 32B 0.416）。第二，兩個 benchmark 都是俄語，CheGeKa 更是俄國文化常識題，拿來代表「world knowledge」再推論到英語醫療語料，跨度不算小。

### 真正該有的說法：任務落在飽和區

「語言能力不隨規模成長」這句話跟現實是矛盾的。現在的 SOTA 模型明顯就是 scaling law 的展現，推理能力隨模型與資料規模一路變強。比較準確的說法應該是：

> 這個 pipeline 裡的任務難度太低，低到落在 scaling 的飽和區。

差別在天花板效應。「把這句話裡的人名抽出來」這種任務的難度分佈集中在容易區，7B 可能已經 85 分、72B 也只有 90 分，本來就沒有空間讓規模發揮；AIME（數學競賽題）、GPQA（研究生等級的科學問答）那種多步推導才有難尾巴，7B 拿 5 分、大模型拿 80 分，規模的效果才看得出來。

實務推論是一樣的——pipeline 內部負責「讀懂並搬運資訊」的元件，小模型通常夠用。但理由是「任務簡單」，不是「規模無效」。搞錯理由，你會把它錯誤地套用到真正需要推理的環節上。

順帶一提，論文的證據來自 Qwen2.5-Instruct，2024 年的非 reasoning 模型。現代推理模型的主要 gain 來自 RL post-training 這條軸線，論文完全沒碰到。

### 為什麼論文非要這個假說不可

這點值得單獨講，因為判讀其他 system paper 時也用得上：**沒有這個假說，Meno-Lite-0.1 就不是研究貢獻，只是省錢**。

```
沒有假說 →「我們訓了個小模型，因為我們買不起大的」  = 工程妥協
有了假說 →「我們發現大模型是浪費的，小模型原理上就夠」= key insight
```

abstract 裡那句 "A key insight motivates a compact extractor" 就是在做這件事：為一個先有的決定補上事後的理論理由。它同時還撐起了成本敘事（$0.001/doc vs $0.10/doc，只有在「小模型不犧牲品質」成立時才有說服力），並且在後面 Meno-Lite-0.1 的優勢消失時，提供一個把壞消息改寫成好消息的角度。

## 方法：六個步驟，原創的只有一格

![RAGU 的索引流程圖：文件切塊、抽取實體與關係、去重與摘要、建圖、Leiden 社群偵測、社群摘要，最後落到三層儲存。](img-002)

*圖二 — RAGU 的端到端索引流程。三層儲存（圖資料庫、key-value store、向量庫）都是可抽換的。（來源：原始論文）*

流程本身很好懂：

```
Documents
   ↓  Step 1  Chunking
Chunks
   ↓  Step 2  Entity & Relation Extraction   ← 兩階段、有 schema 約束
Entities & Relations（很髒：重複、別名、噪音）
   ↓  Step 3  Deduplication & Summarization  ★ 這篇唯一的原創處
Entities & Relations（乾淨版）
   ↓  Step 4  Graph Construction
   ↓  Step 5  Community Detection（Leiden）
   ↓  Step 6  Community Summarization
```

跟 Microsoft GraphRAG、LightRAG 相比，差別只有 Step 3 這一格，其他每一格都是既有做法。

「先洗再建圖」在原理上是說得通的。社群偵測是看圖的連接結構在分群，如果同一個實體被拆成三個節點（「Dennis Ritchie」/「Ritchie」/「D. Ritchie」），本來該集中的 3 條邊會被分散成 1+1+1，這個節點在結構上就變得不重要，可能被分進錯的社群，甚至變成孤立點。換句話說，抽取階段的噪音會經過社群偵測放大成結構性錯誤，而且下游修不回來。

這裡先記一個保留：**論文從頭到尾沒有做「有 Step 3 vs 沒 Step 3」的 ablation**。附錄的組態實驗只測了 ICL（in-context learning，要不要在 prompt 裡放範例）、validation、抽取模型大小三個開關，唯獨沒測它自己的核心賣點。所以 consolidation 究竟帶來多少 gain，論文只有跟 LightRAG 的跨系統比較，而兩者的差異遠不只 Step 3。

### Step 2：兩階段抽取，把生成變成選擇題

抽取被拆成兩趟 LLM 呼叫：

```
Stage 1: chunk → 抽實體 → 用 NEREL schema 驗證型別
         產出已驗證的實體集合 E = {e1, e2, ...}

Stage 2: chunk + E → 抽關係
         約束：每個關係的 source_entity 與 target_entity
               必須是 E 裡面已驗證過的名字
```

它解決的是懸空的邊。單次抽取時，LLM 常在關係裡寫出實體清單裡不存在的名字——實體抽到「Bell Laboratories」，關係卻寫「Bell Labs」，邊就指向一個不存在的節點。兩階段先把「有哪些節點」定死，第二階段就從開放式生成變成封閉集合上的選擇題。

這個 pattern 可以脫離 GraphRAG 單獨用：任何時候要 LLM 產生「指向既有事物」的輸出，先把合法選項定死，再讓它選。跟 constrained decoding 是同一個思路。

至於型別怎麼定，論文用的 NEREL schema 有 29 種實體型別、49 種關係型別，來自一套俄語新聞語料的標註體系。論文自己在 Bias 段承認換語言或換領域可能要重新設計 schema——而它挑出來的 demo 就露餡了。那段 Dennis Ritchie 的文字抽出 8 條關係，論文展示其中 5 條：

| Source | Target | Relation |
|---|---|---|
| Dennis Ritchie | C Programming Language | WORKS_AS |
| Dennis Ritchie | Unix Operating System | WORKS_AS |
| Dennis Ritchie | October 12, 2011 | DATE_OF_DEATH |
| Alistair E. Ritchie | Dennis Ritchie | PARENT_OF |
| Bell Laboratories | Murray Hill | LOCATED_IN |

前兩條是錯的。原文說 Ritchie 創造了 C 語言，`WORKS_AS` 的語意是「擔任某職位」，完全不對。這是 schema 覆蓋不足的典型症狀：NEREL 裡沒有 `CREATOR_OF` 這類關係，LLM 被迫在 49 個型別裡挑一個最接近的，就挑錯了。而這還是論文自己挑出來展示的最佳案例，5 條裡錯 2 條。

（有意思的是，後面的多跳問答還是答對了「Ritchie 創造了 C 語言」，因為檢索回來的是原始 chunk 文字，不是只有那條錯誤的邊。這反過來說明圖在這裡的作用主要是「找到相關段落」，最終答案還是 LLM 從原文讀出來的。）

### Step 3：consolidation，論文的核心賣點

論文對這一步的全部描述只有三句話：EntitySummarizer 按 (name, type) 分組，對重複提及很多的實體套用 DBSCAN 分群加上 LLM 摘要，RelationSummarizer 比照辦理。abstract 則稱之為 DBSCAN-backed deduplication。

要理解它在幹嘛，得先知道抽取出來的東西是「提及（mention）」，不是節點。同一個真實世界的實體，在 9 個 chunk 裡會產生 9 筆各自獨立的 mention：

```
chunk_1: ("Dennis Ritchie",      PERSON, "C 語言的創造者")
chunk_2: ("Dennis Ritchie",      PERSON, "Unix 共同開發者")
chunk_3: ("Dennis Ritchie",      PERSON, "貝爾實驗室研究員")
chunk_4: ("Dennis M. Ritchie",   PERSON, "1983 圖靈獎得主")
chunk_5: ("Ritchie",             PERSON, "K&R 一書的作者之一")
chunk_6: ("Alistair E. Ritchie", PERSON, "貝爾實驗室工程師")
chunk_7: ("Bell Laboratories",   ORG,    "位於 Murray Hill 的研究機構")
chunk_8: ("Bell Laboratories",   ORG,    "Unix 的誕生地")
chunk_9: ("Bell Labs",           ORG,    "AT&T 旗下研究部門")
```

直接建圖會得到 9 個節點，正確答案是 3 個。

第一層是便宜的做法：字串完全相同、型別也相同的合成一組。純 hash 比對，零 LLM 呼叫，9 筆變 6 組。但它只能處理「寫法完全一樣」的重複——「Dennis Ritchie」「Dennis M. Ritchie」「Ritchie」明明是同一個人，「Bell Laboratories」跟「Bell Labs」明明是同一個機構，一個都合不掉。**字串比對抓得到重複，抓不到別名。**

第二層才是貴的：把每一組當成一個點丟進 embedding 空間跑 DBSCAN。DBSCAN 的規則是，在半徑 `eps` 內至少有 `min_samples` 個鄰居的點算核心點，核心點跟鄰居連成一群，連不上任何群的點標成 noise。合完之後再讓 LLM 把該群所有描述融成一段 canonical 描述。所以這一層同時做兩件事：DBSCAN 決定合誰，LLM 決定合出來長什麼樣。

這個機制最脆弱的地方是 Alistair E. Ritchie，Dennis 的父親。兩人的名字字串高度相似、描述也都跟貝爾實驗室有關，`eps` 稍微放寬，父子就被合併成同一個節點，而且下游沒有任何機制救得回來。

第二層還有一道門檻：只有「重複提及很多」的實體才會啟動，因為每個 cluster 至少一次 LLM 呼叫，加上全體 embedding，十萬份文件可能有幾十萬個候選組。這個取捨合理，但論文沒討論它的代價——只出現一兩次的實體永遠不會被 consolidate，而多跳問答的關鍵橋樑實體常常正好是低頻的。這可能是 RAGU 在 MuSiQue 上落後的原因之一：consolidation 優化的是高頻主幹，多跳推理靠的是低頻支線。

論文另外有三件事沒交代：embedding 的對象到底是實體名稱、描述、還是名稱加描述加來源 chunk（這直接決定能不能合併「Bell Labs」跟「Bell Laboratories」）；`eps` 跟 `min_samples` 怎麼設（DBSCAN 對 eps 極度敏感，這是整個機制最需要調的旋鈕）；「many duplicate mentions」的門檻是多少。而且敘述本身前後不一致——abstract 說 DBSCAN 用於跨名字去重，方法段讀起來卻像是先用 (name, type) 分好組、再在同一組內部做 DBSCAN。後者根本無法合併別名。論文的文字本身無法判定，要確認只能翻原始碼。

## 觀念一：去重不是分群

RAGU 用 DBSCAN 做去重看起來理所當然，但去重（entity resolution）跟分群（clustering）其實是兩種性質不同的任務：

| | 分群 Clustering | 去重 Entity Resolution |
|---|---|---|
| 有標準答案嗎 | 沒有。分 3 群或 5 群都可能對，取決於用途 | 有。"Bell Labs" 跟 "Bell Laboratories" 就是同一個 |
| 任務本質 | 無監督的結構發現 | 對每組 pair 做二元判斷：同一個？是/否 |
| 群數相對於資料量 | k << n（1000 個客戶分 5 群） | k ≈ n（10 萬個 mention 可能有 7 萬個實體） |
| 群的大小 | 大，幾十到幾千 | 極小，多半 1～5 |
| 能不能評估 | 只能用 silhouette 之類的代理指標 | 可標註 pair，直接算 precision / recall |
| 錯了的後果 | 換個分法重跑就好 | 誤合併不可逆，錯誤會傳到下游 |

最關鍵的是群數跟群大小那兩列。所有幾何式分群演算法的設計前提都是「少數幾個大群」，靠的是密度或距離的全域結構；而去重的真實結構是「幾萬個大小 1 到 3 的微群」，那個空間裡根本沒有全域結構可言。

這造成三個具體後果。

**幾何式演算法在這裡會退化。** 去重時一個實體可能只有 2 個 mention，所以 `min_samples` 必須設到 2。而 `min_samples=2` 的 DBSCAN，數學上等價於「相似度門檻加上 connected components（union-find）」。也就是說，在去重所需的參數設定下，DBSCAN 會自動塌陷成 union-find，只是多背了一個難調的 `eps`。

**去重可以用「嵌不進向量空間」的訊號。** 分群演算法只能看向量距離，但去重最有用的訊號常常不是幾何的：型別必須相同（PERSON 絕不併 ORGANIZATION）是硬規則；編輯距離、縮寫展開（Bell Labs → Bell Laboratories）；有沒有共用 ID、URL、電話。最後還有一條特別重要——**兩個名字出現在同一個 chunk 裡，幾乎確定是兩個不同實體**，但在 embedding 空間裡它們反而更近。這個負向證據，向量距離完全看不到。

**錯誤代價不對稱。** 誤合併遠比漏合併嚴重：漏了頂多資訊分散，合錯了是事實層面的錯誤而且很難察覺。pairwise 框架可以直接把門檻調得保守一點，clustering 的參數（k、eps）跟這個代價沒有直接對應。

實務上的標準去重流程長這樣，注意它整條都不是 clustering：

```
1. Blocking：用便宜方式縮小候選對（同型別、首字母相同、BM25 top-k）
2. 對候選對算相似度（embedding cosine 或 fuzzy string）
3. 相似度 > 門檻 → 連一條邊
4. 取 connected components（union-find）→ 每個連通塊 = 一個實體
```

唯一的坑是鏈式蔓延：A≈B、B≈C，但 A 跟 C 完全不像，仍然會被併成一群。（DBSCAN 也逃不掉，它的 density-reachable 本質上就是帶密度條件的 connected components。）

所以對 RAGU 的評價是：DBSCAN 在這裡不是必要的，「門檻加 union-find」能做到同樣的事，而且更好調、更好 debug。選 DBSCAN 讓 abstract 好看（DBSCAN-backed deduplication 聽起來就是比 threshold-based merging 學術），但技術上沒有非它不可的理由。

順帶附上一條實務建議：想用 DBSCAN 的時候，先試 HDBSCAN。它是 DBSCAN 的階層式改良版，把 `eps` 這個參數拿掉了（改成掃過所有 eps 值再挑最穩定的分群），只留 `min_cluster_size`，語意直觀很多。DBSCAN 最痛的兩點——`eps` 難調、資料密度不均時整組分群失效——它大致都解決了。

## 觀念二：圖分群跟向量分群，是兩種不同的「像」

Step 5 的社群偵測用的是 Hierarchical Leiden，這部分跟 Microsoft GraphRAG 相同。它的目標函數叫 **modularity（模組度，記作 Q）**，白話講就是：

> 這一群內部的邊，比隨機亂連的情況多出多少？

為什麼要跟隨機比？因為光看「內部邊很多」會被高連接度的節點騙——一個連了 100 條邊的節點，跟誰都會有很多內部邊。所以要扣掉「純粹因為它度數高、本來就該有的邊數」：

```
Q = Σ_c [ e_c/m  −  (d_c / 2m)^2 ]

m   = 全圖總邊數
e_c = 社群 c 內部的邊數
d_c = 社群 c 裡所有節點的度數總和

前項 = 實際觀察到的內部邊比例
後項 = 隨機連線下的期望內部邊比例
```

後項的平方是這樣來的：隨機連一條邊時，一端落在社群 c 的機率是度數佔比 `d_c/2m`，兩端都落在 c 就是平方。

拿論文自己的 demo 實算一次會更有感。那段 Ritchie 文字建出來的圖是這樣（圖裡的 `70` 是 Ritchie 過世時的年齡，也是抽出來的節點之一）：

![由 Ritchie 段落建出的知識圖，Dennis Ritchie 連向 C 語言、Unix、死亡日期等節點，另一側是 Alistair、貝爾實驗室、Murray Hill 這條地理鏈。](img-009)

*圖三 — 從 Ritchie 段落建出的知識圖，Leiden 把它切成兩個社群：Ritchie 的專業成就，以及貝爾實驗室的地理叢集。（來源：原始論文）*

```
        C語言   Unix   Oct 12,2011   70
            \    |      /          /
             Dennis Ritchie
                    |                  ← 唯一的橋
             Alistair E. Ritchie
                    |
             Bell Laboratories
                    |
             Murray Hill
                    |
             New Jersey
```

總邊數 `m = 8`，度數是 Dennis 5、Alistair 2、Bell Labs 2、Murray Hill 2、其餘各 1。

```
社群 1 = {Dennis, C語言, Unix, Oct12, 70}
   e_1 = 4，d_1 = 9
   4/8 − (9/16)^2 = 0.500 − 0.316 = 0.184

社群 2 = {Alistair, Bell Labs, Murray Hill, New Jersey}
   e_2 = 3，d_2 = 7
   3/8 − (7/16)^2 = 0.375 − 0.191 = 0.184

Q = 0.367

對照組：全部塞成一群
   8/8 − (16/16)^2 = 0
```

0.367 大於 0，所以切成兩群比不切好。Alistair 跟 Dennis 之間那條橋被犧牲成跨社群的邊，換來兩邊各自的內聚度——這就是演算法在做的權衡。（Q 的理論上限是 1，實務上 0.3 到 0.7 表示有明顯的社群結構。）

演算法本身，Louvain 是貪婪法，反覆做兩件事：把節點移到能讓 Q 增加最多的鄰居社群，然後把每個社群壓縮成超級節點、在更小的圖上再跑一次，後者就是 hierarchical 的來源。Leiden 是 Louvain 的修正版，補上一個 refinement 步驟保證社群內部連通、順便收斂更快，可以就理解成「不會出那個 bug 的 Louvain」。

現在回到標題那句。社群偵測就是分群，只是輸入是圖而不是向量。差別在用什麼定義「像」：

| | 向量分群（k-means / DBSCAN） | 圖分群（Leiden） |
|---|---|---|
| 輸入 | 每個點一個向量 | 節點加邊 |
| 「像」的定義 | 向量距離近（語意相似） | 連得多（結構相關） |
| 會分到一起的 | 同類的東西 | 有關係的東西 |

拿上面那張圖對照就很清楚：

```
向量分群的結果（按語意）:
  群 A = {Dennis Ritchie, Alistair E. Ritchie}   ← 都是人
  群 B = {C語言, Unix}                            ← 都是軟體
  群 C = {Murray Hill, New Jersey}                ← 都是地名
  群 D = {Oct 12 2011, 70}                        ← 都是數值

圖分群的結果（按結構）:
  群 1 = {Dennis, C語言, Unix, Oct12, 70}         ← 都跟 Ritchie 這個主題有關
  群 2 = {Alistair, Bell Labs, Murray Hill, NJ}   ← 都跟貝爾實驗室這個地點有關
```

向量分群給你「分類」，圖分群給你「主題」。對 RAG 來說要的是後者：使用者問「Dennis Ritchie 是誰」，你希望一次撈到他的作品、死亡日期、年齡，這些東西語意上八竿子打不著，但共同構成一個可以被摘要的主題。

所以「一個社群內部語意差很多」不是缺陷，是設計目的。GraphRAG 的整個價值主張就建立在這裡：知識圖的邊帶著語意向量看不見的關聯資訊，社群偵測是把它變現的方式。

一個好記的對照是，RAGU 同一條 pipeline 裡用了兩種「像」——Step 3 的 consolidation 用語意相似度（同一個東西的不同寫法），Step 5 的社群偵測用結構相關性（不同東西之間的關聯）。用途完全不同。

## 實驗：把混淆變因一層層剝掉

論文最漂亮的敘事是 cross-over：任務越難，RAGU 越強，最後反超 HippoRAG 2。這段我們一層層檢查。

實驗設定本身是乾淨的：四個 benchmark（GraphRAG-Bench Medical、BioASQ、MuSiQue、2WikiMultiHopQA），所有系統用同一個生成模型 gpt-4o-mini，只變建圖端的 LLM，這樣才隔離得出建圖品質；評分用 gemini-3-flash-preview 當 judge，避免自己評自己。

先把指標對齊，後面會一直用到：

| 縮寫 | 全名 | 測什麼 |
|---|---|---|
| AC | Answer Correctness | 答案語意上對不對（LLM-judge） |
| RL | ROUGE-L | 答案跟標準答案的字面重疊度 |
| Cov | Coverage | 有沒有涵蓋所有該講的重點 |
| Faith | Faithfulness | 答案有沒有忠於檢索到的材料 |
| ER | Evidence Recall | 檢索階段撈回了多少比例的相關材料 |

其中 ER 只評檢索，AC / Cov / Faith 評最終答案，RL 評字面形式。另外提醒一句：AC 是單一 judge 模型的單次評分，論文沒有 error bar、也沒有人工驗證 judge 準確度，個位數 pp 的差距不宜當結論。

### 第一層：答案格式

這一層是論文自己承認的，值得肯定。多跳 QA 的標準答案是短答案（「Bell Laboratories」），RAGU 預設吐長答案，HippoRAG 2 預設吐短答案。用字面重疊指標比，RAGU 是被自己的 prompt 害的，不是被檢索品質害的。

同一套檢索、只改 generation prompt 的效果：

| Benchmark | verbose AC | terse AC | 只改 prompt 的增益 |
|---|---|---|---|
| BioASQ | 56.0 | 72.9 | +16.9 pp（百分點） |
| 2Wiki | 46.6 | 58.0 | +11.4 pp |
| MuSiQue | 43.5 | 40.1 | −3.4 pp |

ROUGE-L 更誇張，BioASQ 從 12.2 跳到 48.7。**+16.9 pp 是「換個 prompt」買來的，比論文任何一項方法貢獻都大。**

扣掉格式之後，RAGU 對 HippoRAG 2 的真實對照（terse 設定下的 AC）是這樣：

| Benchmark | RAGU | HippoRAG 2 | 差距 |
|---|---|---|---|
| BioASQ | 72.9 | 72.4 | +0.5 pp（打平） |
| 2Wiki | 58.0 | 63.5 | −5.5 pp |
| MuSiQue | 40.1 | 54.4 | −14.3 pp |

論文說這是「互補的強項而非全面壓制」，這個說法站得住——但要注意，扣掉格式後 RAGU 是追平或落後，沒有任何一項贏。

### 第二層：NaiveRAG 才是照妖鏡

這是同一張表裡最重要、但論文正文一個字都沒分析的對照。

NaiveRAG 就是 RAGU 自己的 `NaiveSearchEngine`——同一套程式、同一個 generation prompt，但完全不用圖。所以「RAGU vs NaiveRAG」是全篇唯一乾淨的「圖到底有沒有用」對照：

| Benchmark（terse, AC） | NaiveRAG（不用圖） | RAGU（用圖） | 圖的淨貢獻 |
|---|---|---|---|
| BioASQ | 71.7 | 72.9 | +1.2 pp |
| 2Wiki | 53.7 | 58.0 | +4.3 pp |
| MuSiQue | 36.6 | 40.1 | +3.5 pp |

整套 GraphRAG——兩階段抽取、DBSCAN consolidation、Leiden 分群、社群摘要——相對於純向量檢索的淨貢獻，就是這 1.2 到 4.3 pp。

對比一下成本：建圖要跑一遍 LLM 抽取（論文估約 8k tokens/doc）、embedding、分群、社群摘要；NaiveRAG 只要切 chunk 加 embedding。

### 第三層：所謂的 cross-over 是誰在動

GraphRAG-Bench Medical 上四個難度層級的 AC（都用 Meno-Lite-0.1 建圖）：

| 任務 | LightRAG | HippoRAG 2 | RAGU |
|---|---|---|---|
| Fact Retrieval | 26.2 | **72.4** | 54.2 |
| Complex Reasoning | 20.2 | **68.4** | 53.7 |
| Contextual Summarize | 22.6 | **65.0** | 64.1 |
| Creative Generation | 14.4 | 56.9 | **59.0** |

論文說 gap 從 −18.2 單調收斂到 +2.1，是「越難越強」的證據。但看 RAGU 自己那一欄：54.2 → 53.7 → 64.1 → 59.0，幾乎是平的。

![四個難度層級上三個系統的 Answer Correctness 與 Evidence Recall 對照長條圖，RAGU 的曲線相對平坦，HippoRAG 2 隨難度上升明顯下滑。](img-004)

*圖四 — 依任務複雜度呈現的 cross-over。(a) 是 Answer Correctness，(b) 是 Evidence Recall。（來源：原始論文）*

所謂 cross-over，主要不是 RAGU 變強，而是 HippoRAG 2 從 72.4 掉到 56.9，跌了 15.5 pp。準確的描述應該是：RAGU 的表現對任務難度不敏感，HippoRAG 2 敏感，所以在最難的一格被追過。「在難任務上更強」跟「在難任務上比較不會退步」是兩件事，論文的敘事把後者說成了前者。何況最後那格贏的是 59.0 對 56.9，2.1 pp，落在 LLM-judge 的雜訊範圍內。

## 觀念三：檢索指標好，不等於答案好

有一組數字是真的。Creative Generation 的 Coverage：LightRAG 3.9、HippoRAG 2 34.7、RAGU 57.4。RAGU 的 Evidence Recall 在四個難度上分別是 82.4 / 74.5 / 74.8 / 53.1，四格都高過 LightRAG 與 HippoRAG 2。（絕對值隨難度下滑是任務本身變難，不影響「誰領先」這件事。）22.7 pp 的 Coverage 差距不是雜訊，也不是格式造成的，它確實支持論文的機制假說：consolidation 讓圖更完整、更連通，撈得回更多相關材料。

但這就引出整篇論文最值得想清楚的張力：**如果 RAGU 檢索到更完整的證據，為什麼最終答案正確率反而輸？**

關鍵在於，Evidence Recall 只測「該撈的撈到沒有」，完全不測「不該撈的有沒有撈進來」。

```
Recall    = 撈到的相關材料 / 全部相關材料      ← ER 測這個
Precision = 撈到的相關材料 / 全部撈到的材料    ← 沒有人測
```

兩者可以同時發生：

```
HippoRAG 2 的 context:  [相關][相關][相關]
   → ER = 3/4 = 0.75    precision = 3/3 = 1.00

RAGU 的 context:        [相關][相關][相關][相關][雜訊][雜訊][雜訊][雜訊]
   → ER = 4/4 = 1.00    precision = 4/8 = 0.50
```

**RAGU 撈到的不是「更正確的資訊」，是「更完整但濃度更低的資訊」。** 而且這不是意外，是設計必然：consolidation 把同一實體的所有提及合併起來，LocalSearch 又從實體擴展到關係、再擴展到 chunk，整條路線的傾向就是多撈。Coverage 領先 22.7 pp，反過來說就是它把很多東西掃進來了。

多撈為什麼實際上會傷害答案，有三個機制。第一是干擾項：factoid 問題只有一個正確答案，context 裡多塞幾段語意相關但答案不同的材料，LLM 挑錯的機率就上升。第二是 lost in the middle，長 context 裡模型對開頭結尾敏感、中間容易被忽略，「答案在 context 裡」跟「模型會用到它」是兩回事，ER 測前者、AC 測後者。第三是任務性質決定誰吃虧：

| | Fact Retrieval | Creative Generation |
|---|---|---|
| 需要 | 一個精確的事實 | 廣泛的相關材料 |
| 多餘材料是 | 干擾 | 資產 |
| 有利於 | 高 precision | 高 recall |

這才是 cross-over 的真正機制。RAGU 不是在難任務上變聰明，而是它一路用同一種策略（多撈），這個策略在簡單任務上是負擔、在合成類任務上才變成優勢。

論文只用一句話帶過這件事：HippoRAG 2 在 Evidence Recall 較低的情況下仍然贏得 factoid AC，反映的是它鏈式走訪在單一事實查詢上的 precision。方向是對的，但沒有任何數據支持。而最關鍵的缺口在這裡——**論文列出使用的指標時包含了 Context Relevancy，正好就是回答這個問題需要的那個數字，但它在所有表格與圖裡全部沒有出現，全篇沒有任何一個數值**，論文也沒有說明原因。

這個觀念脫離這篇論文也成立：優化 recall 跟優化最終正確率，在 factoid 任務上是互相拉扯的。只盯著 recall 類指標（撈回率、hit rate）會系統性地把系統推向「撈更多」，而最終答案品質可能不動甚至下降。至少要同時看 context precision，最好直接看 end-to-end 的答案指標。

## Meno-Lite-0.1：一個尷尬的結果

單獨測資訊抽取，7B 的 Meno-Lite-0.1 確實贏過 32B：

| Model | Size | NER | Def | RE | RDef | HM |
|---|---|---|---|---|---|---|
| Meno-Lite-0.1 | 7B | 0.504 | 0.527 | **0.347** | 0.558 | **0.468** |
| Qwen2.5-32B | 32B | 0.536 | 0.528 | 0.239 | 0.599 | 0.416 |
| Qwen2.5-14B | 14B | 0.510 | 0.518 | 0.222 | 0.583 | 0.396 |
| Qwen2.5-7B | 7B | 0.477 | 0.479 | 0.192 | 0.541 | 0.356 |

欄位的意思是：NER 是實體辨識（F1）、RE 是關係抽取（F1）、Def 與 RDef 分別是實體與關係的描述生成品質（chrF++）、HM 是前四項的調和平均。整體 HM 相對高出 12.5%，主要靠關係抽取那一欄（0.347 對 0.239）。

問題是這個優勢接到 end-to-end 就消失了。論文自己寫：Meno-Lite-0.1 巨大的單獨抽取優勢，到了 GraphRAG-Bench 的端到端問答上壓縮到 1 pp 以內。附錄的組態表更直接——3B 到 14B 的抽取模型換來換去，最終 AC 只差 1.5 pp 以內。

同一份證據既證明了「小模型夠用」，也證明了「抽取模型換誰都差不多」，連帶讓 Meno-Lite-0.1 本身的存在意義變薄。論文把它重新框架成 pipeline 的 robustness。

還有一個 caveat 是論文自己在 Limitations 承認的：Meno-Lite-0.1 的微調用了 NEREL 的 train/validation split，而 IE benchmark 用的是 held-out test split。論文說重疊僅限於標註 schema 跟文本領域，但殘留優勢無法完全排除。

## 工程面：這篇論文最紮實的部分

附錄裡 RAGU 與 HippoRAG 2 的工程比較，是整篇論文我最欣賞的一段。它釘住特定 commit，每一條指控都附上檔名跟行號（`eval()` 出現在 `openie_openai.py:36,88`、`assert False` 當控制流出現在 `HippoRAG.py:216`）。這種可查證性在論文裡很罕見。

![RAGU 與 HippoRAG 2 的工程特性對照表，依各項目對應的生產環境風險分類。](img-010)

*圖五 — RAGU 與 HippoRAG 2 的工程比較，依每項特性對應的生產風險組織。（來源：原始論文）*

RAGU 這一側的實質內容：

- 三層可抽換 storage（NetworkX → Neo4j、NanoVDB → Qdrant，只改兩個 constructor 參數）
- async-first API、有上限的並行控制
- 用 Pydantic v2 驗證所有 LLM 結構化輸出，取代 `eval()`，消除 code injection
- 增量 upsert / update / delete、確定性 hash ID、一致性稽核
- 約 374 個測試搭配 deterministic mock LLM server，CI 不需要 API key

說白了，這一段的價值是工具書等級的：哪天真的要做 GraphRAG，它是個裝得起來、能換 backend 的實作，比自己從頭寫省事。但這不是需要記在腦中的知識。

論文自陳的限制也很誠實：預設的 NetworkX backend 撐不了百萬節點級的語料；NEREL schema 是為俄語新聞設計的，換領域要重新設計；抽取模型太弱時引入的結構噪音，consolidation 也救不回來。

## 值得帶走的五件事

論文本身的研究貢獻接近零，但下面幾點是耐久的，按價值排序。

**一、檢索指標好不等於答案好。** ER 只測 recall、不測 precision。只看 hit rate 會系統性地把系統推向「撈更多」，而最終答案品質可能不動甚至下降。這條會改變你調系統時盯哪個儀表板，而且跟 GraphRAG 完全無關。

**二、混淆變因的量級感。** 換一個 generation prompt 值 +16.9 pp AC，比這篇論文所有方法貢獻加起來都大。在做任何檢索改動的評估之前，先問：有沒有一個更無聊的變因（prompt、答案格式、chunk 大小、baseline 設定）在解釋這個差異？

**三、一個有用的負面結果。** RAGU 對 NaiveRAG，同程式、同 prompt、唯一差別是用不用圖，答案是 +1.2 到 +4.3 pp。整套 GraphRAG 就值這麼多。知道「不要做什麼」跟知道「要做什麼」一樣值錢，而且這種數字很少有人願意發表。

**四、兩個概念工具。** entity resolution 不是 clustering——判斷同一性 vs 發現結構、k≈n vs k<<n、誤合併不可逆，這決定你選 union-find 還是 DBSCAN。以及圖分群跟向量分群是兩種「像」——結構相關 vs 語意相似，同一條 pipeline 裡兩種都用得到。

**五、一組讀論文的檢查動作。** 這篇論文三個動作全部命中，是判斷成色最快的方式：找「乾淨對照」（誰跟誰只差一個變因），這裡找到了 NaiveRAG；查「宣告了卻沒報的指標」，這裡是消失的 Context Relevancy；查「核心賣點有沒有 ablation」，這裡 consolidation 沒有。

## 結論

RAGU 是一篇工程價值高、研究價值低的 system paper。它的兩階段 typed extraction 是個可以單獨拿走用的好 pattern，工程品質在同類開源專案裡罕見地紮實，但核心賣點 consolidation 從頭到尾沒有 ablation，「7B 就夠」的假說是為既定決定補的事後理由，而最漂亮的 cross-over 敘事拆開來看主要是對手掉下去，不是它爬上來。

真正值得記住的，是它無意間量化了 GraphRAG 的天花板——用它自己的程式、自己的 prompt 做對照，整套圖的淨貢獻只有 1.2 到 4.3 pp，而那個天花板比宣傳的低很多。這對任何正在評估要不要導入 GraphRAG 的人來說，比論文想證明的東西有用得多。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1: Effect of model size on world-knowledge (CheGeKa) vs. language-skill (MultiQ) tasks in the Qwen2.5-Instruct family (F1 scores on MERA (Fenogenova et al., 2024)). CheGeKa F1 grows 21.1× from 0.5 B to 72 B; MultiQ only 4×. Log-linear slopes: 0.65 vs. 0.26.",
    "why_used": "支撐「7B 就夠了」這個核心假說的唯一實證，也是後面拆解這個假說時要對照的對象。",
    "agent_match_hint": "一張模型規模對 F1 的折線圖，兩條線分別是 CheGeKa 與 MultiQ，橫軸從 0.5B 到 72B。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2: End-to-end indexing pipeline. Documents are chunked, entities and relations are extracted under the NEREL schema, deduplicated and summarized, then grouped into communities via Leiden clustering. All artifacts persist across three swappable storage tiers (graph database, key-value store, vector store). Solid arrows indicate data flow between pipeline stages; dashed arrows indicate artifacts produced at each stage.",
    "why_used": "讓讀者先看到六個步驟的全景，再進入逐步驟拆解，特別是標出唯一原創的 Step 3 落在哪。",
    "agent_match_hint": "一張左到右的流程方塊圖，從 Documents 開始，末端接到三個儲存層。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Figure 4: Knowledge graph built from the Ritchie pas- sage. Nodes are typed entities; edges are typed relations. Two communities emerge: Ritchie’s professional legacy and the Bell Labs geographic cluster.",
    "why_used": "modularity 的手算範例就是用這張圖的節點與邊，讀者需要看到實際的圖形結構才跟得上兩個社群怎麼切出來的。",
    "agent_match_hint": "一張小型知識圖，中心是 Dennis Ritchie，節點以顏色區分成兩個社群。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Figure 3: Cross-over by task complexity on GraphRAG-Bench (Medical). All three systems use Meno-Lite-0.1 (7 B) as the index LLM and gpt-4o-mini for answer generation. (a) Answer Correctness: RAGU trails HippoRAG 2 on Fact Retrieval, but the gap closes and RAGU leads on Creative Generation. (b) Evidence Recall: RAGU retrieves the most complete context on all factoid levels. Task difficulty increases left to right.",
    "why_used": "cross-over 的真正機制是 HippoRAG 2 下滑而非 RAGU 上升，這件事看曲線的形狀比看表格數字直觀。",
    "agent_match_hint": "並排的兩組長條圖，(a) Answer Correctness 與 (b) Evidence Recall，橫軸是四個難度層級。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "Table 6: Engineering comparison between RAGU and HippoRAG 2, organized by the production risk each property addresses.",
    "why_used": "工程面是這篇論文最紮實的部分，逐項對照表能直接呈現兩個系統在生產風險上的差距，不需要在內文重述。",
    "agent_match_hint": "一張兩欄對照表，左欄 RAGU、右欄 HippoRAG 2，每列對應一項生產風險。"
  }
]
```
