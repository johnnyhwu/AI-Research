RAG 系統上線之後最先被檢討的,通常是 Embedding 模型選得好不好,或是 Prompt 寫得夠不夠精細。但實務上真正卡住效能的,常常是更早、更不起眼的一步:文本切分(Document Chunking)。切得好不好,直接決定了寫進向量資料庫的知識顆粒大小與語意完整性——切壞了,檢索器再怎麼調也抓不到完整的上下文,LLM 推理能力再強也救不回來,這就是典型的 garbage in, garbage out。

目前業界處理 Chunking 的方式,大致卡在三個沒有真正被解決的痛點上。第一個是「上下文保存困境」:固定字元長度或標點切分,常常把邏輯連貫的段落硬生生切成兩半,甚至讓代名詞(「它」)跟它指代的實體被分到不同 Chunk。第二個是「一招打天下」的迷思:大多數管線不管文件類型,一律套用同一種切分策略——像是全部丟給 LangChain 的 Recursive Splitter,限制 1000 tokens——但真實世界的知識庫異質性很高,合約、技術手冊、學術論文的排版邏輯完全不同,沒有一種切法能通吃所有結構。第三個,也是最根本的一個,是「評估落差」:業界長期缺乏獨立衡量「這個 Chunk 切得好不好」的標準,只能透過跑完整條 RAG 流程、看最終答對率來反推,但這種外在評估混雜了檢索器與生成模型的雜訊,很難單獨拿來優化切分策略本身。

這篇論文提出的 **Adaptive Chunking**,做法是把「找一個最好的切分演算法」這個問題直接放棄,改成「幫每一份文件挑一個當下最適合的切法」。具體來說,系統會對同一份文件平行跑好幾種切分方法,用五種不需要真的跑一次 RAG 就能算出來的「內在評估指標」幫每種結果打分,最後只留下平均分數最高的那一組寫進向量庫。接下來的內容,基本上就是把這句話拆解成可以落地的工程細節。

## 從 PDF 到「模型看得懂」的 Markdown

在切分之前,論文團隊做的第一件事,是把 PDF 轉成結構化的高品質 Markdown——這一步聽起來像雜務,卻直接決定了後面所有切分演算法拿到的原始素材長什麼樣子。純文字抽取容易把表格拆散、把標題跟內文混在一起,切分演算法再厲害,面對這種輸入也很難做出正確的結構判斷。

為此,團隊在既有的解析管線上加了三個工程巧思。第一個是處理超大表格:遇到跨頁或欄位過多的表格,直接拆解並保留表頭,避免表格被切斷後,後半段的數字失去對應的欄位名稱這種資訊斷層。第二個是頁首頁尾的過濾與群組化,把重複出現、對語意沒有貢獻的頁首頁尾雜訊濾掉,降低後續檢索時的雜訊干擾。第三個是綁定「不可分割跨度」——標題與其後續內文、註腳與被註解的本文——確保這些天生綁在一起的內容,不會在切分階段被意外拆開。

這三個巧思共同的目的很單純:讓後面章節介紹的切分演算法,拿到的是一份結構清楚、天生該綁在一起的東西已經先綁好的文件,而不用自己從一坨純文字裡重新猜測段落與表格的邊界。

## 切分工具箱:兩款新演算法

在常見的基準方法(按頁切、按句切)之外,論文另外設計了兩款兼顧「結構感知能力」與「運算效率」的切分演算法,跟前面提到的高品質 Markdown 前處理緊密搭配,一起擴充了系統的候選切分池。

### LLM-guided Regex Splitter:讓 LLM 只負責歸納規則

對於結構規律性很強的文件——合約、法規條文這類——傳統的按字數遞迴切分很容易切斷條款,但如果每次切分都直接叫 LLM 處理全文,運算時間跟 API 成本又會爆掉。這款演算法採取一個折衷:把 LLM 降維成「規則生成器」。系統只要求 LLM 讀文件的前段(大約 8,000 tokens),歸納出一段適用於這份文件的正則表達式(Regex)分隔符,接下來全文的切分,就交給 Python 原生的 `re.split()` 在毫秒等級完成。

要讓 LLM 穩定吐出「工程上可以直接用」的 Regex,靠的是幾個 Prompt 設計上的防呆機制。輸出格式被限制成只能有一段相容於 Python `re` 引擎的 Regex,而且包在特定的 XML 標籤(`<regex>...</regex>`)裡,方便 Zero-shot 情境下穩定解析。Prompt 裡也明確下了結構保護指南,要求生成出來的 Regex 不能切在 `<Table>` 到 `</Table>` 之間,也不能切斷段落——直接把前處理階段建立的結構標記,轉換成對 LLM 輸出的硬性限制。最後再搭配幾組「輸入文字 → 期望 Regex」的 Few-shot 範例,穩住輸出的一致性。

![LLM Regex splitter 的完整管線:從 Markdown 輸入與 token 預算出發,組出情境感知 Prompt,向 LLM 取得分隔符 Regex,最後套用到全文完成切分。](img-009)
*圖 3 —— LLM Regex splitter pipeline。(來源:原始論文。)*

### Split-then-Merge Recursive Splitter:先打碎,再貪婪合併回去

第二款演算法,對業界最常用的 LangChain `RecursiveCharacterTextSplitter` 動了刀。傳統的遞迴切分是 Top-down 邏輯:區塊大於上限(例如 1000 tokens)就找高優先級的分隔符切開,一旦切出來的片段小於等於上限就停手。問題在於它完全沒有下界控制——切出來只剩 50 tokens 的碎片,演算法照樣接受,結果就是向量庫裡塞滿一堆缺乏上下文、浪費檢索名額的「極小碎片」。

這款演算法反過來,採用 Bottom-up 的兩階段策略。第一階段先「無腦切細」:依照事先排好優先順序的 Markdown 分隔符表,不斷往下遞迴切,直到所有片段都小於目標大小 $S$——這時候文本已經變成大量微小的結構單元。這張分隔符優先順序表會優先處理 Markdown 的各級標題(例如一級標題對應的正則 `(?<=\n)#{1}\s`),確保同一個標題底下的內文在合併階段能被優先湊在一起,而不是隨機跟隔壁段落黏在一起。

![依優先順序排列的分隔符清單,從最高優先級的標題層級,到最低優先級的字元邊界。](img-010)
*圖 4 —— Regex separators list for recursive splitters。(來源:原始論文。)*

第二階段才是重點,「貪婪合併」:由上而下走過這些碎片,只要累加起來的 token 數不超過 $S$,就持續往同一個 Chunk 裡塞。這麼一來,產出的 Chunk 會盡量逼近長度上限,幾乎不會留下無意義的微小碎片。

重疊(Overlap)的處理方式也一併改了。傳統做法是被動用字元數截斷,很容易把句子攔腰切斷;這款演算法在合併時,一旦下一個片段會讓 Chunk 超過上限 $S$,就開一個新 Chunk,並把上一個 Chunk 結尾那個「完整的結構碎片」(例如一個完整句子)複製到新 Chunk 開頭——重疊的單位是語意結構,而不是字元數,連貫性因此提升不少。

![Split-then-Merge 遞迴切分管線,分兩階段運作:先依分隔符優先順序遞迴切至極細,再由上而下貪婪合併並在超界時啟動回溯重疊。](img-011)
*圖 5 —— Split-then-merge recursive splitter pipeline。(來源:原始論文。)*

兩種遞迴切法,工程特性差在哪裡,整理成一張表會比較清楚:

| 比較維度 | 傳統 Recursive Splitter(LangChain 原生) | Split-then-Merge Recursive(本論文改良) |
| --- | --- | --- |
| 運作方向 | Top-down,切到低於上限就停 | Bottom-up,先切到極細再貪婪合併到上限 |
| 碎片控制 | 弱,容易產生 0~50 tokens 的廢棄碎片 | 強,合併機制大幅提高空間利用率 |
| 重疊機制 | 被動依字元數截斷,易破壞句子 | 主動以完整結構片段回溯重疊 |
| 結構感知力 | 弱,只認原生換行與空白 | 強,深度整合 Markdown 標題與列表規則 |
| 尺寸合規性 | 不穩定,變異數大 | 高度合規 |

## 兩道後處理防線,補上演算法自己顧不到的地方

不管前處理做得多細、切分演算法設計得多聰明,遇到排版特別異常的文件,還是會產出不符規格的離群 Chunk。這些極端值——太大或太小——會干擾 Embedding 的語意表達,也會變成污染檢索結果的雜訊。論文的做法是在所有切分演算法跑完之後,再加掛一套雙階段的後處理品管流程,只針對這些極端值動手,正常尺寸的 Chunk 完全不受影響。

第一道防線處理「過大」。切分演算法偶爾會失手(例如 LLM Regex 判斷失準),吐出遠超過長度上限(論文設定 1,100 tokens)的超大 Chunk,裡面往往混雜了好幾個不相關的主題。Embedding 模型被迫把這些雜七雜八的內容壓成單一向量時,關鍵的語意訊號會被稀釋,檢索時很難跟使用者的具體查詢對上。系統一旦偵測到超過 1,100 tokens 的 Chunk,就會直接呼叫前面提到的分隔符級聯規則(段落 → 換行 → 句號),把它重新剖開,拉回合理的長度區間。

第二道防線處理「過小」。殘缺的表格、孤立的數字、孤兒標題,很容易產出低於幾十個 token 的微型碎片——這些碎片缺乏實質內容,但只要剛好包含使用者查詢的關鍵字(尤其在用 BM25 這類詞彙比對演算法時),就有機會擠進 Top-k 名單,讓 LLM 讀到一堆沒用的背景資訊。系統設了長度下限(論文用 100 tokens),偵測到過小的碎片,就嘗試跟前後相鄰的段落合併——但合併前會先檢查,只有合併後的總長度不超過寬鬆上限(1,150 tokens)才會真的執行,避免把小碎片硬塞進一個本來就已經夠大的 Chunk。

這兩道防線看起來簡單粗暴,數據上的效果卻很明顯。原本尺寸合規性(SC)表現極不穩定的方法——像是沒加工過的語意相似度切分法(Semantic chunker,依句子間語意相似度自動抓分界點)或 LLM Regex——經過處理後,SC 幾乎都衝上 99% 以上;未經後處理的傳統方法,最小 Chunk 長度常常只有 0 到 4 個 token,經過強制合併之後,所有方法的最小長度都被穩定拉到 69 到 104 tokens 的健康範圍。

![各切分方法在後處理前後的 Chunk 尺寸與執行時間統計表,標有十字架的方法代表未經後處理。](img-002)
*表 2 —— Chunk sizes in tokens and runtime statistics。(來源:原始論文。)*

![後處理對尺寸合規性(SC)的實質影響:未後處理的方法 SC 普遍偏低,經過過大重切與極小合併雙重處理後大多躍升至 99% 以上。](img-012)
*表 7 —— Effect of post-processing on Size Compliance。(來源:原始論文。)*

## 五把不需要跑 RAG 的尺

要判斷一個 Chunk 切得好不好,傳統做法得把它寫進資料庫、接上檢索器跟 LLM,跑一次完整的端到端流程才知道結果——這種「外在評估」不但貴,還很難分辨問題到底出在切分、Embedding,還是 LLM 本身。論文提出的「內在評估」繞開了這一步,直接靠一個輕量級的共指解析模型、向量餘弦相似度,以及排版結構邊界,對切分完的 Chunk 做五個維度的打分,每個指標的分數都落在 $[0, 1]$ 之間。

**References Completeness(RC,參考完整性)** 對付的是「代名詞消解失敗」這個 RAG 死穴——如果「馬斯克」跟指代他的「他」被切到不同 Chunk,檢索只抓到後者時,LLM 就會因為資訊缺失答不出來。做法是用共指解析模型 Maverick(ACL 2024)掃過全文,找出所有(實體, 代名詞)配對 $P=\{(e_i,p_i)\}_{i=1}^N$,其中 $s_i=\text{start}(e_i)$、$t_i=\text{end}(p_i)$ 是這對配對在原文的字元邊界。接著檢查切分邊界集合 $B$(不含首尾),如果任何一刀 $b\in B$ 落在 $s_i<b\le t_i$ 之間,就代表這對配對被切斷,記 $m_i=1$,否則 $m_i=0$:

$$RC = 1 - \frac{1}{N} \sum_{i=1}^N m_i$$

舉個具體例子會比較好懂。假設輸入是 `"Elon Musk founded SpaceX. He wants to land on Mars with his rockets."`,Maverick 會輸出類似這樣的共指簇:

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

系統從中萃取出兩組配對範圍:`[0, 28]`(Elon Musk → He)與 `[0, 57]`(Elon Musk → his)。假如切分器剛好在字元偏移量 15 的地方下刀(大概是 `founded` 後面),這一刀同時落在兩個範圍裡,$m_1$、$m_2$ 都會被記成 1——也就是說,這一刀確實傷到了代名詞的完整性,RC 的公式會忠實地把這件事反映出來。

**Intrachunk Cohesion(ICC,塊內內聚度)** 處理的是「主題混雜稀釋語意」——確保單一 Chunk 只專注談一件事。做法是把 Chunk $c_k$ 拆成句子 $S_k$,用 Jina AI v3 分別算出每個句子的正規化向量 $v(s_{kj})$ 與整個 Chunk 的正規化向量 $v(c_k)$,取平均餘弦相似度作為這個 Chunk 的 Cohesion 分數,ICC 則是所有合規 Chunk 的 Cohesion 平均(取 0 為下限):

$$ICC = \max\left\{0, \frac{1}{|K|} \sum_{k \in K} \frac{1}{n_k}\sum_{j=1}^{n_k} v(s_{kj})^\top v(c_k)\right\}$$

**Document Contextual Coherence(DCC,上下文連貫性)** 跟 ICC 是天生互相拉扯的一對——它要確保 Chunk 不會變成一座沒有背景資訊的孤島。做法是在全文上開一個最大 3,000 tokens 的滑動視窗 $W_m$,包含好幾個相鄰的 Chunk,算出視窗整體的正規化向量 $w(W_m)$ 跟窗內各 Chunk 的向量 $v(c_k)$,取平均相似度作為這個視窗的 Coherence,DCC 是所有視窗的平均:

$$DCC = \max\left\{0, \frac{1}{|M|} \sum_{m=0}^M \frac{1}{|C_m|}\sum_{k \in C_m} w(W_m)^\top v(c_k)\right\}$$

**Block Integrity(BI,區塊完整性)** 處理「硬性截斷破壞天然結構」——表格、圖說、段落這類邏輯單元,不該在切分時被打斷。做法是取得前處理階段標記出來的黃金邊界列表 $G=\{0,d_1,\dots,d_M,L\}$,對每個保護區間 $[d_j+\tau, d_{j+1}-\tau]$(論文設定字元容差 $\tau=5$ 排除換行符干擾)檢查是否有切分邊界 $b\in B$ 落在裡面,沒有就記該區塊 $I_j=1$(完整),有就記 0:

$$BI = \frac{1}{|G|-1} \sum_{j=0}^{|G|-1} I_j$$

BI 等於 1,代表所有表格、段落等邏輯單元在切分後都保持完整。

**Size Compliance(SC,尺寸合規性)** 對付的是超限或微型 Chunk 損害檢索的問題,計算 token 長度落在指定範圍(100 到 1,100 tokens)內的 Chunk 佔比:

$$SC = \frac{1}{K} \sum_{k=1}^K \mathbb{1}[100 \le \tau_k \le 1100]$$

這五個指標各自盯著切分品質的一個面向,合起來才是完整的體檢報告——下一節說明系統怎麼用這五個分數,幫每份文件挑出當下最適合的切法。

## 動態決選:讓文件自己選切法

前面的切分演算法跟後處理防線準備好之後,系統進入真正的決策階段。針對每一份輸入文件,自適應切分機制要做的事,可以濃縮成四個步驟。

系統會先平行跑好幾種候選切分演算法(每一種都掛好前面提到的後處理防線),論文用的候選池包含頁面切分(後處理過)、本文的遞迴切分(s=1100 與 s=600 兩種尺寸),以及 LLM regex(GPT-5)切分,四種方法各自切出一組候選 Chunk。接著針對每組候選,分別算出 RC、ICC、DCC、BI、SC 五項分數。為了維持框架的通用性、避免過度擬合特定資料集,決選階段用的是最簡單的等權重算術平均:

$$\text{Score}_{\text{method}} = \frac{RC + ICC + DCC + BI + SC}{5}$$

最後系統只保留分數最高的那組切分結果,向量化寫入資料庫,其餘候選全部捨棄。

這套機制在真實資料上跑出來的分佈,直接證明了「單一策略」行不通。論文用這套框架處理了 33 份跨領域文件庫,結果顯示:頁面切分(後處理過)被選中 48%,適合排版嚴謹、表格剛好落在單一頁面內的文件;本文遞迴切分(s=1100)被選中 42%,適合長篇敘事或階層結構分明的文件;LLM regex 跟小尺寸遞迴分別只佔 6% 跟 3%,主要應付法規條文之類極度緊湊的特殊文本。沒有任何一種演算法能通吃所有文件類型。

![Adaptive 框架在 33 份跨領域文件庫上的演算法選中比例分佈,四種候選方法的被選中比例明顯不均。](img-006)
*表 4 —— Results for chunking method selection in the Adaptive Chunking method。(來源:原始論文。)*

當然,這套機制不是沒有代價,而且成本要分兩塊來看。一塊是替候選結果打分所需的指標運算:對整個語料庫來說,計算 DCC 最耗時,花了 15 分 58 秒,因為需要對滑動視窗反覆算向量;用 Maverick 做實體-代名詞抽取花了 13 分 13 秒,主要卡在 CPU 上的跨視窗聚類。

![各評估步驟的執行時間統計,DCC 與 Maverick 實體-代名詞抽取是耗時最長的兩個環節。](img-008)
*表 6 —— Runtime per evaluation component。(來源:原始論文。)*

另一塊則是切分本身的執行時間:LLM-regex 演算法即使用了非同步 API,單一文件平均也要跑 146.85 秒;而整套 Adaptive 流程(平行跑完四種候選切法並完成決選)處理單一文件,平均總耗時大約 210.66 秒。換句話說,真正燒時間的大宗其實是指標評估,尤其是 DCC 跟 Maverick 這兩項——這也是後面談離線/線上取捨時,真正該放進成本考量的部分。

這筆帳要放在「離線建置」跟「線上查詢」的框架下看才划算。切分跟指標評估只發生在資料寫入向量庫的離線階段,一旦 Chunk 進了資料庫,線上的檢索跟生成延遲完全不受影響。換句話說,這是用離線幾分鐘的運算,換線上長期、無限次的低延遲高精準查詢——對大多數企業級應用來說,這筆投資報酬率相當合理。

## 這些指標真的有用嗎:實驗結果與工程啟示

前面定義的五個內在指標,終究要接受一個檢驗:高分的 Chunk,是不是真的能換來下游更好的答案?論文設計了一組控制變因實驗來驗證這件事——固定檢索器(Hybrid Search)、重排器(Reranker)與生成模型(GPT-4.1)不變,只改變寫進向量庫時用的切分策略。

![固定不變的檢索評估管線:結合關鍵字與語意檢索的 Hybrid Search,加上重排與生成兩個階段。](img-004)
*圖 2 —— Hybrid search retrieval pipeline。(來源:原始論文。)*

結果相當一致地支持內在指標是有效的。Adaptive Chunking 把檢索完整性(Retrieval Completeness)拉到 67.68%,比廣泛使用的 LangChain 遞迴基準(58.08%)高出 9.60 個百分點;答案正確性(G-Eval)達到 78.01%,比基準高 7.90 個百分點,代表更乾淨連貫的上下文確實降低了 LLM 的幻覺。在總計 99 題的測試集裡,Adaptive 方法答對 65 題,基準方法只有 49 題——換算下來,系統因為上下文不足而選擇拒答的比例降低了 32.7%。

![不同切分策略下游 RAG 效能比較,Adaptive Chunking 在檢索完整性與答案正確性上全面領先。](img-007)
*表 5 —— RAG performance results evaluated using GPT-4.1。(來源:原始論文。)*

但這五個指標之間,也不是可以同時拉到滿分的——論文用斯皮爾曼相關係數($\rho$)算出的指標間相關性,普遍落在弱到中度的區間($-0.44<\rho<0.31$),代表五個指標各自捕捉切分品質的不同面向,而不是同一件事的五種說法。其中兩組拉扯特別值得工程師留意。ICC 跟 DCC 呈顯著負相關($\rho=-0.44$):Chunk 切得越小,主題越純(ICC 越高),但跟周圍文本的關聯就越弱(DCC 越低),這其實是尺寸本身的物理極限,很難兩全。ICC 跟 BI 也是負相關($\rho=-0.34$):為了保留完整的排版結構(比如把整張表格、整段文字綁在一起以拿到高 BI),往往得連帶把一些不相關的引言或過渡句也塞進同一個 Chunk,語意純度自然就被拉低了。

![五大內在評估指標之間的斯皮爾曼相關係數矩陣,整體呈弱到中度相關,ICC 與 DCC、ICC 與 BI 呈現明顯負相關。](img-003)
*圖 1 —— Spearman correlation between chunking metrics。(來源:原始論文。)*

最值得工程師警惕的,是一個「乘數效應」。對照 Table 3 的內在指標分數,Adaptive Chunking 的平均分數是 91.07%,LangChain 遞迴(預設)是 88.62%,兩者只差 2.45 個百分點,乍看是個不起眼的小差距。但把這個差距丟進完整的 RAG 管線跑一遍,到了下游輸出端,卻放大成 9.60% 的檢索完整性落差跟 32.7% 的答對率躍升。

![Adaptive Chunking 與各基準方法的內在指標平均分數對照,差距看似不大,卻在下游被大幅放大。](img-005)
*表 3 —— Chunking performance results across five intrinsic metrics。(來源:原始論文。)*

這其實是典型的錯誤累積與放大:RAG 是一條多步驟串接的管線,切分階段一個很小的語意偏離(比如一個代名詞的主詞被切斷,導致向量偏移個 2%),在檢索階段可能讓這個 Chunk 的相似度剛好跌出 Top-k 名單;進了重排階段,又因為資訊不完整被排到名單末端;最後到了生成階段,LLM 讀到的是殘缺的上下文,只能選擇安全牌,回答「我不知道」。前處理階段的微小優化,在 RAG 系統裡不是線性關係,而是會被逐層放大——這也是為什麼投資資料品質,報酬率往往比在管線後端對 LLM 做複雜微調來得高。

## 裂縫在哪裡

這套框架把三個工程建議收攏得很清楚:別再迷信單一切分參數,改用候選池動態適配文件特性;後處理的上下界控制,是投入產出比最高的優化,幾乎是零成本消除掉檢索雜訊跟語意稀釋;比起後期盲目換更大的 LLM,把心力放在前處理階段的資料品質上,回報通常更高。

但這套系統也有幾個現階段還沒解掉的限制。離線建置的運算開銷偏高——DCC 的滑動視窗計算跟 Maverick 的實體-代名詞抽取都不便宜,如果拉到百萬甚至千萬級 token 的正式生產管線,Maverick 缺乏批次處理能力,很可能變成明顯的效能瓶頸,未來大概需要換成更輕量、支援 GPU 批次加速的專用模型。指標權重目前也只是啟發式的 1:1:1:1:1 算術平均,但不同場景對指標的敏感度顯然不一樣——重視精準數據的金融 RAG 可能該更依賴 Block Integrity,重視對話流暢度的客服 RAG 則可能更吃 DCC——怎麼自動學出合適的權重組合,還是一個開放問題。多語言支援也是個現實限制:RC 指標高度依賴 Maverick 共指解析模型,而這個模型目前只支援英文,要把整套框架搬到中文或其他語言的 RAG 系統上,得先找到、驗證對應語言的共指解析工具才行。

## 總結

Adaptive Chunking 這篇論文真正想說的,其實是一個心態上的轉變:與其花力氣去找一個放諸四海皆準的完美切分演算法,不如老實承認異質文件庫本來就沒有這種東西存在,轉而建立一套能自己評分、自己選擇的管線。五個內在指標讓「Chunk 切得好不好」第一次可以在不跑完整 RAG 的情況下被量化,而實驗也證明了,這幾個百分點的內在分數差距,在下游會被放大成雙位數的答對率差異。對正在維護 RAG 系統的工程團隊來說,這篇論文給的訊息很直接:與其把預算全部押在下一個更強的 LLM 上,不如先回頭檢查一下,資料進向量庫之前,到底是怎麼被切開的。

```figure-map
[
  {
    "id": "img-002",
    "references_manifest_caption": "Table 2: Chunk sizes in tokens (OpenAI’s o200k_base) and runtime statistics. Chunking methods marked with ∗are included in the Adaptive Chunking results. Those marked with † were not post-processed; ** was computed considering asynchronous API calls.",
    "why_used": "支撐後處理章節對「最小 Chunk 長度從 0~4 tokens 拉回 69~104 tokens」的具體數據說明。",
    "agent_match_hint": "一張表格,列出多種切分方法的 chunk 尺寸統計(mean/min/max)與執行時間欄位,部分列標有十字架符號。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 1: Spearman correlation (ρ) between chunk- ing metrics, computed using the metric results for each document and chunking method.",
    "why_used": "支撐工程洞察段落中,關於 ICC 與 DCC、ICC 與 BI 呈現負相關拉扯的說明。",
    "agent_match_hint": "一張 5x5 的相關係數矩陣熱力圖或表格,列出 RC、ICC、DCC、BI、SC 五個指標兩兩之間的相關係數。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Figure 2: Hybrid search retrieval pipeline.",
    "why_used": "說明下游 RAG 驗證實驗中固定不變的檢索管線架構(結合關鍵字與語意檢索、重排、生成)。",
    "agent_match_hint": "一張流程圖,畫出 Hybrid Search(結合關鍵字與語意檢索)、重排器、生成模型串接的檢索管線。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Table 3: Chunking performance results (% mean ± % st. dev.) for References Completeness (RC), Intrachunk Cohesion (ICC), Document Contextual Coherence (DCC), Block Integrity (BI), and Size Compliance (SC). “LC\" denotes LangChain, and s is the chunk size parameter in tokens. Rows marked with ∗are included in the Adaptive Chunking results; those with † were not post-processed and are here for reference and comparison. Differences between Adaptive Chunking and all individual methods are statistically significant (Wilcoxon signed-rank test, p < 0.001).",
    "why_used": "支撐乘數效應段落中,Adaptive Chunking(91.07%)與 LC recursive 預設(88.62%)僅相差 2.45 個百分點的具體數據來源。",
    "agent_match_hint": "一張表格,列出各切分方法在 RC、ICC、DCC、BI、SC 五項指標上的平均分數與標準差,並標示統計顯著性。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 4: Results for chunking method selection in the Adaptive Chunking method with respect to the entire document corpus. Other chunking methods were not selected and omitted here.",
    "why_used": "支撐 Adaptive 框架在 33 份跨領域文件庫上,四種候選演算法被選中比例(48%/42%/6%/3%)分佈不均的說明。",
    "agent_match_hint": "一張表格,列出各候選切分方法(頁面切分、遞迴 s=1100、遞迴 s=600、LLM regex)被選中的文件比例。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Table 5: RAG performance results (% mean) evaluated using OpenAI’s GPT-4.1 (temperature = 0) as the LLM judge. Retrieval Completeness is evaluated for all queries, while Answer Correctness skips queries where the model decided not to provide an answer (insufficient context). Highest scores per column are marked in bold; “LC\" means LangChain. Retrieval Completeness differences are statistically significant (Wilcoxon signed-rank, p < 0.05).",
    "why_used": "支撐內在指標有效性驗證段落,關於檢索完整性(67.68% vs 58.08%)與答案正確性(78.01%)的下游 RAG 實驗數據。",
    "agent_match_hint": "一張表格,列出各切分方法在檢索完整性(Retrieval Completeness)與答案正確性(Answer Correctness)兩項下游指標上的百分比分數。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Table 6: Runtime per evaluation component. All embeddings were computed using jina- embeddings-v3 sentence transformer, and the entity-pronoun pairs were extracted using Sapienza NLP maverick-mes-ontonotes.",
    "why_used": "支撐系統建置成本段落,關於 DCC(15:58)與 Maverick 實體-代名詞抽取(13:13)是最耗時評估步驟的說明。",
    "agent_match_hint": "一張表格,列出每個評估步驟(DCC、實體-代名詞抽取、chunk embedding、token 指標等)各自花費的執行時間。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Figure 3: LLM Regex splitter pipeline. From markdown input and a token budget, the system builds a context-aware prompt, obtains a delimiter regex from the LLM, and applies it to split the document into chunks.",
    "why_used": "在說明 LLM-guided Regex Splitter 的設計邏輯與 Prompt 工程拆解之後,搭配整體管線示意圖讓讀者建立視覺化的架構印象。",
    "agent_match_hint": "一張流程圖,畫出從 Markdown 輸入、token 預算、組出 Prompt、向 LLM 取得 Regex,到最終套用切分的步驟。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "Figure 4: Regex separators list for recursive splitters, adapted to our Markdown parser outputs. The list is sorted from highest to lowest priority.",
    "why_used": "說明 Split-then-Merge 演算法依循的分隔符優先順序表,尤其是 Markdown 標題層級優先於一般段落與字元邊界的設計。",
    "agent_match_hint": "一張清單或表格,由上到下列出各種正則表達式分隔符,依優先順序排列,最上方通常是 Markdown 標題層級。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Figure 5: Split–then–merge recursive splitter pipeline. Text is recursively split following a priority list of separators until each piece is ≤chunk size, then merged forward into chunks; when the next piece would exceed chunk size, a new chunk starts with up to chunk overlap tokens of backtracked overlap.",
    "why_used": "搭配 Split-then-Merge 兩階段策略(先切細、再貪婪合併、回溯重疊)的文字說明,提供對應的整體管線示意圖。",
    "agent_match_hint": "一張流程圖,畫出遞迴切分至極細、由上而下貪婪合併,以及超界時開新 chunk 並回溯重疊的兩階段機制。"
  },
  {
    "id": "img-012",
    "references_manifest_caption": "Table 7 reports the detailed effect of our two-stage post-processing pipeline on Size Compliance (SC) and overall mean chunking scores. The pipeline consists of: (1) oversized re-split, applied only to chunks exceeding 1100 tokens, and (2) tiny-chunk merge, applied only to chunks smaller than 100 tokens, with a maximum merged size of 1150 tokens. The “–” symbol indicates that a particular step was not required for that method (e.g., our recursive splitters with s = 1100 or s = 600 already produce well-sized chunks in the raw output).",
    "why_used": "支撐後處理章節中,尺寸合規性(SC)在過大重切與極小合併雙重處理後躍升至 99% 以上的數據佐證。",
    "agent_match_hint": "一張表格,列出各切分方法在 raw、經過大重切、再經極小合併三個階段的尺寸合規性(SC)分數變化。"
  }
]
```
