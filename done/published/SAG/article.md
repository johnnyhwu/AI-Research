# SAG：與其在線下建知識圖譜，不如在查詢時用 SQL 連連看

## 前言

多步推論（multi-hop）一直是 RAG 系統最難落地的一塊。純向量檢索只看語意相似度，推理走到一半常常斷鏈；GraphRAG 這類做法能建立關聯，但要在線下把文本拆成三元組、做實體對齊、算全域分數，建置成本高，資料一直進來的時候更是難維護。

SAG（SQL-Retrieval Augmented Generation）這篇論文提出的折衷方案很直接：**線下不建圖，只把每個 chunk 轉成一個保留完整語意的「事件」加上一組實體標籤，寫進標準 SQL 資料庫；線上查詢時再用 SQL JOIN 把共用實體的事件動態串起來。** 圖只在查詢的那一瞬間存在，查完就丟。

它在 HotpotQA、2WikiMultiHop、MuSiQue 三個多跳基準的 9 個 Recall@K 指標裡拿下 8 個第一，其中推理鏈最長的 MuSiQue 達到 80.0% 的 Recall@5。但這篇文章的重點不只是數字——SAG 真正有意思的地方，是它把一個原本被當成「演算法問題」的東西，重新當成「資料庫結構設計問題」來解，而這個轉換帶來的工程紅利（無痛增量寫入、可稽核的檢索軌跡、對 embedding 品質不敏感）比 recall 數字更值得學。

## 兩種現有做法，兩種不同的痛

![NaiveRAG、GraphRAG 與 SAG 三種架構的流程與特性對照，涵蓋擴充性、成本、速度與精準度四個面向。](img-001)

*圖一 — 三種 RAG 範式的流程與效能對照。（來源：原始論文）*

### 向量檢索：沒有邏輯約束，而且會斷鏈

傳統的 dense retrieval 本質上就是語意相似度匹配：切塊、映射到向量空間、查詢時回傳 Top-K。用在多步推理上有三個根本限制。

第一，它建立不了顯式的實體關聯。查詢一旦涉及時間限制、特定角色或多步依賴，向量相似度只能找到「讀起來很像」的段落，還原不了實體之間明確的邏輯鏈。

第二，誤差會沿著推理鏈放大。Agent 做序列式檢索時，第一步只要因為相似度不夠高而稍微偏掉，後面每一步都是在錯的基礎上繼續，最後整條路徑徹底斷掉。

第三，也是最要命的一點——**推論鏈裡扮演橋樑的中間證據，字面和語意常常跟原始問題八竿子打不著**。你問「某公司創辦人的母校在哪」，中間那段講創辦人學歷的文字可能完全沒提到公司名。單靠向量距離，這種關鍵跳板在第一步就被過濾掉了。

### GraphRAG：結構有了，但代價很大

為了補上結構，GraphRAG、HippoRAG 這類方法在線下用 LLM 抽三元組、建全域知識圖譜。問題是這條路的代價很實在：

- **語意破碎化**：知識圖譜把關係限制成 `(主體, 關係, 客體)` 的二元組，但現實世界的事件多半是 N 元關係，牽涉多方、時間、地點。硬拆成幾條獨立三元組，原始上下文就沒了。
- **增量更新是工程災難**：真實系統的資料是持續寫入的。圖譜要維持正確，新文件進來時往往得重跑實體抽取、實體對齊、關係正規化，甚至重算全域節點權重（例如 PageRank）。這個成本讓即時增量更新幾乎不可行。
- **線上跟線下脫節**：論文指出一個很諷刺的現象——線下花大錢建出來的複雜圖結構，線上查詢時常常又退化成對「圖節點」或「社群摘要」做扁平的向量相似度匹配，結構根本沒發揮約束作用。
- **分數衰減與雜訊放大**：像 HippoRAG 用 Personalized PageRank 在圖上傳分數，跳數一多，遠端目標節點的分數會被阻尼係數（damping factor）壓得很低，深層答案排不上來；同時圖裡的高頻中心節點（hub nodes）會把訊號往無關的地方擴散，雜訊分數反而升高。

## SAG 的設計哲學：讓每個元件只做它最擅長的事

SAG 的核心不是發明更強的模型，而是**重新分配檢索管線裡的職責**。三個元件分工分得很死：

| 元件 | 負責什麼 | 為什麼是它 |
|---|---|---|
| SQL 資料庫 | 確定性關聯（filtering & joining） | 它不懂語意，但「A 是否等於 B」的精確比對是毫秒級、100% 確定，而且串聯時不衰減、天然支援併發與 append-only 寫入 |
| 向量資料庫 | 語意模糊擴展 | 專門處理別名、同義詞、錯字、換句話說，當實體與事件的容錯安全網 |
| LLM | 高價值的聯合判斷 | 只用在線下抽事件與實體，以及線上對壓縮過的候選集做 joint assessment |

這裡的關鍵取捨是：**向量檢索不拿來做多步推論，LLM 也不拿來走圖**。多步推論交給 SQL，LLM 只在候選集已經縮到 100 個以內時才出場，整套系統的 token 消耗跟 API 成本因此壓得很低。

### 什麼是「潛在超邊」

傳統圖論裡一條邊只能連兩個節點，SAG 借用的是超圖（hypergraph）裡的**超邊（hyperedge）**——一條超邊可以同時包含任意數量的節點。

在 SAG 中，一個 chunk 對應一個保留完整語意的事件 `e`，以及一組跟它綁定的實體集合。**這個「事件 ↔ 實體集合」的綁定關係，本身就定義了一條超邊。**

「潛在（latent）」這個字是重點。線下建索引時，系統不會去計算實體與實體之間的全域連線，也不會畫出任何顯性圖譜。這些超邊只是以一張「事件-實體」多對多資料表的形式，潛伏在 SQL 裡。只有在使用者發問、系統下 SQL JOIN 的那一瞬間，共用實體的事件才會在記憶體裡被串起來，形成一個局部超圖；查完就釋放。

說白了，**超邊就是一張沒有畫線的資料庫表格，只在查詢瞬間具現化**。維護全域靜態圖的開銷因此完全不存在。

### 為什麼 4 跳的推論只需要 1 跳的檢索

MuSiQue 裡有些問題在二元圖譜上要跳 4 次才到得了答案，但 SAG 實務上只用 `H=1`（一跳擴展）就取得領先的 recall。這個看起來不合理的落差，來自資訊密度。

在傳統圖譜裡節點被拆得極碎，一次跳轉只能跨越很短的邏輯距離。但 SAG 的一個事件是一句保留了完整上下文的話，**單一事件內部就已經壓縮了多個實體**。所以當你從問題出發命中第一個種子事件時，它內部蘊含的時間、地點、人物其實已經幫你跨完了頭一兩步；接著拿這些實體當跳板下一次 SQL JOIN，撈回來的又是另一個內部已經壓縮好後續鏈條的完整事件。

一跳 SQL 擴展的資訊覆蓋率，因此能跟傳統圖譜的三到四跳相提並論——而且它從根本上跳過了多跳傳播帶來的誤差累積與分數衰減。

## 線下階段：把文件變成可 JOIN 的索引

![SAG 的架構總覽，上半是線下的 chunk 轉事件與三重索引寫入，下半是線上的初步召回、查詢時擴展與候選集決選。](img-002)

*圖二 — SAG 的整體架構。上半部是線下攝取，下半部是線上檢索。（來源：原始論文）*

線下階段完全是批次處理，各文件之間互相獨立，所以可以高併發寫入。

### One-Chunk-to-One-Event

文件切成 chunk 之後，用輕量級 LLM（論文用 Qwen3.6-Flash）平行產生兩樣東西：一句濃縮但不打碎的事件敘述，以及一組索引用的實體標籤（涵蓋時間、人物、組織、產品等 11 種預設型別）。

具體長這樣：

```
輸入 Chunk (C001):
  「在 2014 年，Facebook 宣布以 190 億美元的天價收購了知名通訊軟體
   WhatsApp。這項決策主要是由馬克·祖克柏親自推動。隨後，WhatsApp 的
   共同創辦人揚·庫姆也因此加入了 Facebook 的董事會。」

LLM 產生的 Event (e1):
  「Facebook 於 2014 年以 190 億美元收購 WhatsApp，馬克·祖克柏推動此案，
   隨後 WhatsApp 創辦人揚·庫姆加入 Facebook 董事會。」

LLM 產生的 Entities:
  ['Facebook', '2014年', 'WhatsApp', '馬克·祖克柏', '揚·庫姆']
```

注意事件那一句話裡同時綁著五個實體——這就是前面說的「單一超邊內部已經壓縮了多個實體」。

### 刻意不做實體對齊

傳統知識圖譜線下最沉重的負擔是實體對齊與消歧：判斷「馬克·祖克柏」「祖克柏」「Mark Zuckerberg」是不是同一個人。對齊失敗，圖就斷了。

SAG 的選擇很務實——**線下完全不做全域實體對齊**，只做去空白、統一大小寫這種極輕量的字面清洗。

它敢這樣做，是因為在 SAG 裡承載語意價值的是事件，實體只是「連線指引」。別名對齊的壓力被推遲到線上，交給向量的模糊匹配去處理。這個取捨換來的工程紅利很大：線下處理完全擺脫全域圖譜鎖的限制，寫入是獨立的、吞吐量高的、真正無痛的 append-only。

### 三個索引，三重保障

抽取完的資料會同步寫進三個互補的底座。

**SQL 關聯式資料庫**存的是結構與超邊關係，核心是一張 `Event_Entity_Mapping` 多對多表：

| Event_ID | Chunk_ID | Entity_Text | Entity_Type |
| :--- | :--- | :--- | :--- |
| e1 | C001 | Facebook | 組織 |
| e1 | C001 | 2014年 | 時間 |
| e1 | C001 | WhatsApp | 產品 |
| e1 | C001 | 馬克·祖克柏 | 人物 |
| e1 | C001 | 揚·庫姆 | 人物 |

**向量資料庫**存兩種向量：事件向量（用於線上問題的直接語意匹配）跟實體向量（用於線上的別名模糊擴充）。

**全文檢索引擎**（論文用 Elasticsearch）建的是倒排索引。倒排索引跟「文章 → 包含哪些字」的正向索引相反，它記錄的是「詞彙 → 出現在哪些文章」。它在這裡的角色是精確字串匹配的保底：工業界的 RAG 常常在罕見專有名詞、產品型號、機器料號上翻車——你搜「晶片型號 M3-Max」，向量檢索未必撈得回來，倒排索引卻能在毫秒內定位。要注意的是，下一節那三個線上步驟並沒有動用到它；它是留給實務部署的保底通道，不是主線檢索流程的一環。

## 線上階段：雙軌種子、SQL 擴展、LLM 決選

線上完全不走全域圖譜，三個步驟跑完就出答案。

### Step 1：雙軌種子檢索

種子檢索要做的是精確又廣泛地鎖定推論的第一個線頭，SAG 用兩條路並行：

- **路徑 A（實體引導的 SQL 檢索）**：先用輕量 LLM 從問題裡抽出實體，拿去實體向量索引做相似度搜尋（門檻 0.9 以上）擴充出別名集合，例如 `{WhatsApp}` 擴成 `{WhatsApp, whatsapp messenger}`；再用 SQL 的 `OR` 邏輯，精確撈出關聯到其中任何一個實體的事件。
- **路徑 B（純事件向量檢索）**：同時把問題轉成向量，直接在事件向量庫裡撈相似度大於門檻 τ（預設 0.4）的事件。

兩條路取聯集去重。B 的存在是為了保底，預防 A 的實體提取漏接。

合併之後有一道總管閥門：**種子預算 `K_seed = 50`**。超過 50 就依向量相似度排序，只留 Top 50 進到下一步。這個機制可以想成水庫放水——上游不管來多少水，閘門開度是固定的，下游的處理量才控制得住。

### Step 2：查詢時動態擴展

有了種子事件，接著要往外跳一步找間接證據。SAG 用的是「反向收集實體 → 正向撈回事件」的批次 SQL：

```
[種子事件集] ──(SQL 反查)──> [實體前線 Entity Frontier] ──(SQL JOIN)──> [擴展事件集]
```

流程是三個動作：

1. **收集實體前線**：把種子事件綁定的實體全部提出來，組成一個實體前線集合。
2. **全域剪枝（預算 50）**：如果前線裡混進「2014年」這種高頻通用字，下一步會撈回海量無關事件。所以系統設了**剪枝預算 50**——前線實體超過 50 個時，計算它們跟 query 的向量相似度，強制只留 Top 50。這個 50 後面談限制時還會再出現一次，它是 2Wiki 那格輸掉的直接原因。
3. **批次 SQL 擴展**：拿這 50 個精選實體下一次 `WHERE Entity_Text IN (...)` 的批次 JOIN，撈回所有新關聯的事件，跟種子事件合併成候選池。

這批事件當下交織出來的網絡，就是那個臨時的局部超圖。

### Step 3：粗篩加 LLM 雙軌決選

候選池可能有好幾百個事件，這一步要把它精煉成最終給生成模組的 10 個 chunk。

先做向量粗篩：算所有候選事件跟 query 的相似度，截取 Top 100。這是個工程妥協——用便宜的方式把 LLM 要看的量壓到可負擔範圍。

然後兩條路並行決選：

- **路徑 A（LLM 結構化精選）**：把這 100 個事件一起送進推理 LLM，做**聯合評估（joint assessment）**——通盤考量哪些事件「組合起來」能構成一條多跳推論鏈，挑出最關鍵的 5 個，還原成對應的原始 chunk。這跟便宜的 pointwise reranker 有本質差異：pointwise 是一個一個打分，看不到事件之間的互補關係；joint assessment 看得到。
- **路徑 B（直接語意檢索）**：拿問題向量直接去原始 chunk 向量庫撈相似度最高的 5 個。

兩路聯集去重，輸出 Top 10。這個雙軌設計的用意是互補：結構路徑負責召回「需要跨文件拼湊、字面相似度低」的邏輯證據，語意路徑負責召回「跟問題高度相關」的直球證據。

## 實驗數據：它強在哪，又在哪裡露餡

### 主結果：越難的資料集領先越多

![SAG 與各類 baseline 在三個資料集上的 Recall@2/5 對照表，分成 Simple Baselines、Large Embedding Models 與 Graph-based Methods 三組。](img-004)

*表一 — 統一底層設定（BGE-Large-EN-v1.5 + Qwen3.6-Flash）下，SAG 與各 baseline 的 Recall@2/5 對照。（來源：原始論文）*

三個資料集的對照，重點看跟 HippoRAG 2 的差距（兩者用同一個 BGE-Large embedding）：

| 資料集 | 推論難度 | SAG (R@2/R@5) | HippoRAG 2 (R@2/R@5) |
|---|---|---|---|
| MuSiQue | 最難，4 跳且經反事實過濾 | **64.1 / 80.0** | 49.5 / 65.1 |
| HotpotQA | 2 跳，橋樑與比較型問題 | **91.6 / 96.5** | 78.4 / 94.4 |
| 2WikiMultiHopQA | 長實體鏈，含罕見橋樑 | **82.3** / 88.0 | 76.6 / **90.4** |

MuSiQue 上領先近 15 個百分點，而且這是最考驗連結能力的一組——它有 4 步邏輯鏈，還經過反事實過濾防止單步語意作弊。這支持了論文的機制主張：用 SQL 做確定性的局部超邊鏈接，比在全域圖上跑 PageRank 擴散更能保住深層證據。

HotpotQA 只有 2 跳，圖傳播的衰減效應本來就弱，所以 Recall@5 的差距縮到 2.1 個百分點。但 Recall@2 上 SAG 還是領先 13.2 個百分點——把最關鍵的證據排到最前面這件事，它比較穩。

**2Wiki 是唯一輸的一格，而且輸得很有意思。** SAG 的 Recall@2 領先（82.3 對 76.6），Recall@5 卻落後（88.0 對 90.4）。原因就是前面那個固定 50 的剪枝預算：2Wiki 含有極長、出現頻率極低的實體鏈，當某個橋樑實體在整個語料庫裡很罕見、跟原始問題的語意相關性又低時，它很容易在擴展階段被高頻通用實體擠出 50 個名額之外，鏈就斷了。反觀 HippoRAG 的全域 PageRank，靠全圖傳播反而到得了這些低頻節點。

### 消融一：事件結構值多少

![事件層級索引與三元組拆解索引在 MuSiQue 上 R@1 / R@2 / R@5 / R@10 的對照。](img-005)

*表二 — 事件層級索引 vs. 三元組拆解索引的消融比較（MuSiQue）。（來源：原始論文）*

作者把 SAG 強行拆成三元組來跑，Recall@5 從 80.0% 掉到 77.1%。

這組數字要分兩層讀。第一層：**就算拆成三元組，77.1% 依然大幅贏過 HippoRAG 2 的 65.1%**——也就是說，SAG 這套 SQL 檢索管線本身就有系統性優勢，跟用不用超邊無關。第二層：保留完整事件另外帶來 2.9 個百分點，因為一個事件記錄的是 N 元關係，不必像三元組那樣經歷多次 JOIN 走訪，也就少掉每一跳的剪枝損失。

換句話說，論文的招牌是超邊，但績效的大頭其實來自管線設計。

### 消融二：動態擴展抓的是什麼

![開啟與關閉查詢時擴展（H=0 與 H=1）在 MuSiQue 上各項 Recall 的對照。](img-006)

*表三 — 動態超邊建構中擴展跳數的消融實驗（MuSiQue）。（來源：原始論文）*

這組是我覺得整篇最漂亮的數字：

| 設定 | Recall@1 | Recall@5 |
|---|---|---|
| 無擴展（H=0） | 35.7 | 69.4 |
| 有擴展（H=1，預設） | 36.2 | **80.0** |

擴展機制**完全沒有提升 Recall@1**（35.7 → 36.2，等於沒動），卻讓 Recall@5 暴增 10.6 個百分點。

這說明擴展做的不是「把已有的種子事件排得更好」，而是雪中送炭——它找回了那些跟問題語意不相關、向量檢索絕對撈不到、但對推論鏈至關重要的中間證據。前面提過「橋樑證據字面上跟問題八竿子打不著」那個痛點，這組數字量的就是動態擴展把它解掉了多少。

### 對 embedding 品質的依賴度

![SAG 與 HippoRAG 2 在改用 NV-Embed-v2 設定後於 MuSiQue 上的檢索結果對照。](img-011)

*表四 — 換上 NV-Embed-v2 之後，SAG 與 HippoRAG 2 在 MuSiQue 上的表現。（來源：原始論文）*

把 embedding 從 BGE-Large 換成更強的 NV-Embed-v2：

| 系統 | 原本 Recall@5 | 換模型後 | 變化 |
|---|---|---|---|
| HippoRAG 2 | 65.1 | 74.6 | +9.5 |
| SAG | 80.0 | 81.7 | +1.7 |

差異很說明問題。HippoRAG 的多跳極度依賴向量打分（圖上節點的初始分數就是向量相似度給的），模型一弱，誤差會沿著傳播路徑放大；SAG 的結構收益主要來自字串精確匹配的 SQL JOIN，跟 embedding 品質基本無關。

實務上的意義是：**用比較弱、比較便宜的 embedding 模型，SAG 依然維持得住多步檢索的水準。** 對成本敏感的生產環境，這一點比 recall 領先 15 個百分點更有吸引力。

## 這套架構會在哪裡咬你

論文本身對限制寫得算誠實，這裡整理三個實務上真的會遇到的。

**剪枝預算會漏掉罕見實體。** 這是 2Wiki 那格輸掉的直接原因。目前的剪枝策略是拿實體向量跟 query 算相似度來排序，但深層推論鏈裡的關鍵橋樑實體常常同時具備「語料庫裡很罕見」跟「跟原始問題語意相關性很低」兩個特徵，正好是最容易被擠出 50 個預算的那種。可能的改法是引入類似 IDF（逆向文件頻率）的權重，或對實體做頻率分層，給低頻實體專屬的擴展額度。

**不做實體對齊是兩面刃。** 線下不對齊換來了無鎖的高吞吐寫入，但如果同一個實體在不同 chunk 裡寫法不同（"Meta" 對 "Facebook"、「祖克柏」對 "Zuckerberg"），而這些寫法在向量空間裡又沒近到 0.9 的門檻，SQL 就會把它們當成兩個完全無關的索引點，跨文件的連結密度因此被人為降低。折衷做法是在不破壞線下獨立性的前提下，加一張輕量的實體別名表，用背景非同步的方式慢慢聚合。

**目前只支援 append-only，不支援更新。** SAG 的設計對象是唯讀文件庫的增量追加，但 Agent 長期記憶體的知識是會變的：使用者偏好改變、工作狀態從「未完成」變「已完成」、歷史事實被修正。當資料庫裡同時存在互相衝突的新舊事件時，現在的索引沒有原生機制判斷哪一個才是最新有效的。要往這個方向走，schema 得補上時間戳記、生效標記與事件依賴鏈，讓檢索路徑能自動濾掉已被覆蓋的舊資訊。

## 結論

SAG 最值得帶走的不是那些 recall 數字，而是它示範的思路轉換：**要在檢索階段做穩健的多步推理，不一定要在線下建一個昂貴、脆弱、難維護的全域知識圖譜。** 把知識存成「事件 + 實體標籤」的關聯式表格，把圖的具現化推遲到查詢當下，用 SQL JOIN 取代圖走訪，一樣做得到，而且做得更好。

對工程師來說，核心啟發是職責的重新分配。它沒有讓 LLM 去承擔高成本的圖走訪，也沒有讓向量搜尋去猜嚴格的邏輯關聯，而是把確定性關聯交給運作了幾十年、優化到極致的 SQL 引擎。換來的是低廉的 API 成本、真正可用的增量寫入，以及一條每一步都能被 SQL 查詢重現的、可稽核的檢索軌跡——最後這點對線上除錯的價值，其實不亞於 recall 本身。

代價也很清楚：固定剪枝預算會漏掉長尾罕見實體，不做別名合併會稀釋跨文件連結密度，而且目前還處理不了知識的更新與失效。這些都是為了換取系統簡潔性與寫入吞吐量而付的帳，知道帳單長什麼樣，才知道這套架構適不適合你手上的場景。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1: Process and performance comparison of three RAG paradigms. NaiveRAG retrieves top-k chunks via dense vector similarity, offering good scalability, high speed, and low cost, but precision is limited by shallow semantic matching. GraphRAG extracts triples and builds a knowledge graph offline using an LLM; it enhances evidence organization capability, but incurs high construction cost and is difficult to update incrementally. SAG extracts events and entities with an LLM and activates dynamic hyperedge structures at query time via SQL; it balances retrieval quality, structural capability, and system overhead, while naturally supporting append-only incremental updates.",
    "why_used": "在拆解兩種現有做法的痛點之前，先讓讀者看到三種範式在流程與取捨上的整體對照。",
    "agent_match_hint": "並排的三欄流程示意圖，由左至右是 NaiveRAG、GraphRAG、SAG，各自標註擴充性、成本、速度、精準度。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2: Architecture overview of SAG. In the offline phase, each chunk is transformed into one event and a set of entities, and written into SQL, vector, and full-text indices. In the online phase, the system performs initial recall, then query-time expansion, and finally completes selection over the compressed candidate set.",
    "why_used": "線下與線上兩個階段接下來要分別細講，先放整體架構圖當作讀者的地圖。",
    "agent_match_hint": "上下兩層的架構圖，上層是 offline upload 流程，下層是 online search 流程，中間是三種索引儲存。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Table 2: Recall@2/5 of SAG and various baselines on three datasets under a unified underlying configuration (BGE-Large-EN-v1.5 + Qwen3.6-Flash). Values marked with * are taken from literature reports and serve only as background reference.",
    "why_used": "主結果的完整 baseline 對照，內文只摘出跟 HippoRAG 2 的關鍵三列，其餘分組留給表格本身。",
    "agent_match_hint": "一張分成 Simple Baselines、Large Embedding Models、Graph-based Methods 三段的表格，欄位是三個資料集的 Recall@2/5。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Table 3: Ablation comparison of event-level indexing vs. triple-decomposition indexing (MuSiQue).",
    "why_used": "支撐「超邊只值 2.9 個百分點，管線設計才是績效大頭」這個拆解，讀者需要看到 Triple 與 Hyperedge 兩列的完整數字。",
    "agent_match_hint": "一張兩列的小表格，列名是 Triple 與 Hyperedge，欄位是 R@1、R@2、R@5、R@10。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 4: Ablation study on the number of expansion hops in dynamic hyperedge construction (MuSiQue).",
    "why_used": "Recall@1 幾乎不動而 Recall@5 暴增，是判斷動態擴展作用機制的關鍵證據。",
    "agent_match_hint": "一張兩列的小表格，對照 Without Expansion 與 With Expansion 的四個 Recall 數值。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Table 8: Retrieval results of SAG and HippoRAG 2 on MuSiQue under the NV-Embed-v2 configura- tion.",
    "why_used": "換上更強的 embedding 之後兩系統的變化幅度差距，是「SAG 對 embedding 品質不敏感」這個論點的直接證據。",
    "agent_match_hint": "一張兩列表格，分別是 SAG (NV-Embed-v2) 與 HippoRAG 2 (NV-Embed-v2) 的四個 Recall 數值。"
  }
]
```
