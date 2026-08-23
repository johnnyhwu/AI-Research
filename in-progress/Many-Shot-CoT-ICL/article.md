# Many-Shot CoT-ICL：範例不是塞越多越好，順序也不能隨便排

## 前言

長上下文模型讓我們可以一次塞進幾十甚至上百個範例做語境學習（In-Context Learning, ICL），過去在分類、意圖辨識這類簡單任務上，業界累積出兩條近乎常識的經驗法則：範例越多越好、順序基本不影響結果。這篇論文要問的問題是：當範例本身帶著思維鏈（Chain-of-Thought, CoT），任務也換成幾何證明、數論這種需要多步推理的題目時，這兩條法則還站得住腳嗎？

答案是不太行。作者發現 Many-Shot CoT 在推理任務上會出現一系列反直覺的翻車現象，範例給得越多表現反而越不穩定，找「最相似」的範例當參考居然是陷阱，順序的影響力也隨著範例數量增加而暴增。針對這些問題，論文提出兩個設計原則——範例內容要「看得懂」、範例順序要「夠平滑」——並用一個叫 CDS（Curvilinear Demonstration Selection）的排序演算法把第二個原則落地。這篇筆記會照著這個脈絡，把論文的核心發現和 CDS 的運作機制講清楚。

## 一、典範轉移：ICL 不是抄答案，而是「測試時的即時學習」

要理解為什麼舊法則會失效，得先搞懂作者對 ICL 的重新定義。

傳統上我們把長上下文當成一個靜態的檢索緩衝區：模型在 Prompt 裡找和目前問題表面特徵最像的範例，然後把答案格式「抄」過來。這套邏輯在分類任務上很管用，畢竟分類只需要辨識標籤的分佈特徵。但作者主張，面對複雜推理時，Many-Shot CoT 實際上更接近一種無梯度的即時適應——Prompt 不再只是參考資料，而是模型在 forward pass 當下用來動態塑造內部解題程序的訓練訊號。

換個方式理解：傳統做法像是給學生一張寫滿考古題的小抄，考試時字面對得上就直接抄答案，簡單題目夠用。但複雜的數學推理題型一變、數字一換就沒用了，這時候學生需要的是一本「考前衝刺講義」——難易度要貼近他目前的理解程度，題目編排也要循序漸進。

![CoT-ICL 被重新框架為模型在測試當下進行的即時學習，而不是單純的範例檢索。](img-001)
*圖 1 — 論文將 Many-Shot CoT-ICL 重新詮釋為「上下文中的測試期學習」，而非傳統的靜態模式匹配。*

這個「教育學視角」的轉換，直接導出了論文後面兩個核心設計原則：內容要可理解、順序要平滑。下一節先看看，如果沒有照著這兩個原則做，會踩到哪些坑。

## 二、三個反直覺現象：Many-Shot CoT 到底哪裡出問題

### 2.1 範例越多，模型反而越亂

按照舊法則，範例數量從 16 增加到 128，表現應該穩步上升。論文在非推理任務（如 SuperGLUE、BANKING77）上確實觀察到這個趨勢，但換成幾何、數論、GSM8K 這類推理任務，準確率曲線開始劇烈震盪，甚至明顯下滑——即使把模型規模拉大到 LLaMA 3.3 70B 也一樣，增加範例照樣帶來負面收益。

![左圖為 LLaMA 3.3（非推理模型）在數學推理任務上隨範例數增加反而退步；右圖為 QwQ 與 R1 兩個推理模型則呈現正向 scaling。](img-002)
*圖 2 — 模型類型之間的 scaling 差異：非推理模型在數學推理任務上隨範例增加而退步，推理模型則相反。*

![暖色系代表分類任務、冷色系代表推理任務，分類任務的準確率隨範例數穩定上升，推理任務則劇烈震盪甚至下滑。](img-003)
*圖 3 — 非推理模型在分類任務與推理任務上的 scaling 對比，兩者呈現明顯的分歧。*

這其實不難想像：找一個資質普通的學生，塞給他一本一百頁、寫滿複雜幾何證明題的題庫，卻沒給任何引導。他不會因為多看幾頁就突然開竅，反而容易被龐大的資訊量搞到腦袋打結，連原本會寫的簡單題都寫錯。

### 2.2 找「最相似」的範例，反而是陷阱

傳統 RAG 的黃金標準是語義相似度檢索——找字面上最像測試題的範例，模型最容易模仿。但論文發現，在推理任務裡，最相似的範例往往是毒藥。

問題出在「語義相似」不等於「程序相容」。舉個論文裡的例子：兩道幾何題字面上都提到「直角三角形、角度為 30°-60°-90°」，語義相似度極高，但一題要用三角形相似性質證明邊長關係，另一題要用畢氏定理和面積公式求高。如果模型照抄第一題的解題步驟去解第二題，邏輯完全對不上，自然全盤皆輸。

![論文中的幾何案例：測試題與檢索出的相似題雖然表面上都是直角三角形，但正確解法（相似三角形比例）與檢索範例的解法（面積與投影高）完全不相容，套用後導致模型解題失敗。](img-024)
*表 5 — 一個具體的失敗案例：語義最相似的範例，解題邏輯卻和測試題完全不相容。*

作者在論文第 4.3 節做了對照實驗：在非推理任務中，「最相似」範例表現最好；但在幾何、數論、DetectiveQA 這些推理任務上，「最相似」的表現一致地比「最不相似」和隨機挑選還差。原因就是語義相似度只是個弱代理指標，它保證不了範例和測試題之間的解題程序是相容的。

### 2.3 範例一多，順序的影響力反而暴增

按照舊法則，範例數量夠多時，隨機打亂順序對結果幾乎沒有影響——這叫「順序魯棒性」。論文透過 5 種不同隨機順序測量準確率的標準差，結果分類任務確實符合舊法則：範例越多，標準差越小，模型越穩定。但推理任務完全相反，標準差隨範例數增加而爆發式成長。

![暖色系（分類任務）的標準差隨範例數增加而下降，冷色系（推理任務）的標準差則隨範例數增加而急遽上升。](img-006)
*圖 6 — 分類任務與推理任務的順序敏感度對比，推理任務的標準差隨範例增加而暴增。*

這代表 Many-Shot CoT 存在明顯的「路徑依賴」——把一百個推理範例隨機排列，就像一本編排混亂的教科書，第一頁教加法，第二頁跳去教微積分，第三頁又跳回減法。這種概念上的急轉彎會讓模型的推理軌跡瘋狂折返，範例數量越多，出現這種「邏輯斷崖」的機率也越高。

## 三、原則一：範例要「看得懂」，而不是「寫得好」

第一個挑戰的解法，是教育心理學裡「近側發展區間」（Zone of Proximal Development）的概念：最有效的教材不是難度最高的教科書，而是落在學生「在適當引導下能夠理解」的範圍內。

論文把這個概念套到語言模型上，提出「分佈對齊」（Distributional Alignment）的說法：如果範例的語言風格、推理步長、邏輯架構越貼近目標模型自己的輸出分佈，模型就越容易把這些推理步驟內化。說白了，資料集裡人類寫的標準答案就像大學教授寫的課本，邏輯精煉但跨度大，一個 8B 的小模型看了未必吃得下；反倒是模型自己生成的思維鏈，就算寫法笨拙、甚至算錯，因為用的是「同分佈的語言」，模型反而學得更快。

為了驗證這個猜想，作者讓 LLaMA 3.1（8B）在推理任務上分別使用三種範例來源：資料集的標準答案（origin）、模型自己生成且算對的範例（cr）、模型自己生成但算錯的範例（wr）。結果相當意外：不管是算對還是算錯，只要是模型自己生成的 CoT，表現都穩定超越標準答案。

![LLaMA 3.1（8B）在幾何與 GSM8K 任務上，使用自我生成的錯誤答案（wr）的準確率曲線，顯著高於使用人類標準答案（origin）的曲線。](img-007)
*圖 7 — 自我生成範例（即使答案是錯的）在準確率上依然勝過資料集提供的標準答案。*

![Qwen 3（8B）在 DetectiveQA 與數論任務上，使用自我生成範例（first）的表現明顯優於原裝範例（origin），甚至優於用更強模型（Qwen 3 14B）生成的跨模型範例。](img-008)
*圖 8 — 自我生成範例的優勢在跨模型情境下依然成立，甚至勝過用更強模型生成的範例。*

也就是說，模型在 ICL 過程中真正吸收的是「程序性監督」——也就是解題的邏輯框架與步驟——而不是死記最後的答案數字。這個優勢會隨著模型規模變大而縮小，因為理解能力越強的模型，越有能力穿透高難度標準答案裡的語意結構；而 Qwen 3、DeepSeek-R1 這類具備顯式推理機制（比如 `<think>` 標記）的模型，也對不對齊的標準答案表現出更高的抗干擾能力。

## 四、原則二：CDS——把排序問題變成一趟不急轉彎的旅行

解決了「選什麼內容」，接下來要處理「怎麼排序」。這是論文最有份量的貢獻，作者提出了 CDS（Curvilinear Demonstration Selection，曲線範例選擇）演算法。

### 4.1 把範例排序想成一趟高維空間裡的旅行

把每個範例（問題 + 思維鏈 + 答案）丟進 embedding 模型，它就變成高維空間裡的一個點。如果有 100 個範例，就有 100 個點，排序的本質就是找出一條「一筆畫」穿過這 100 個點的路線。路線在概念空間裡不斷急轉彎、瘋狂折返，模型的推理思維就容易亂；路線走得平滑，概念與概念之間的過渡自然，模型才吸收得順。

這正好對應到一個經典的最佳化問題：旅行推銷員問題（Traveling Salesperson Problem， TSP）——訪問所有城市各一次、最後回到起點，並讓總路程最短。TSP 是 NP-hard 問題，100 個城市就有 100! 種排列組合，實務上得靠啟發式演算法在合理時間內找出「夠好」的解，而不是求全域最優解。放到 CDS 的情境裡，城市就是範例，路線就是排列順序，車資則是「讀完前一個範例後，再讀下一個範例的理解負擔」。

### 4.2 成本函數：同時考慮距離和轉彎角度

CDS 中，從範例 $i$ 走到範例 $j$ 的成本由兩部分組成：

$$D_{CDS}(i, j) = \delta_{ij} + \gamma_{ij}$$

$\delta_{ij}$ 是兩點間的歐式距離，確保相鄰範例在概念上循序漸進、不跳題型；$\gamma_{ij}$ 則是曲率代理成本，目的是量化路徑會不會急轉彎。

這裡有個技術上的眉角：要判斷路徑在 $j$ 點有沒有急轉彎，理論上要同時知道前一步（$i \to j$）和下一步（$j \to k$）的方向，但排到 $j$ 的時候，演算法根本還不知道下一步會是誰。作者的解法是找出離「$i$ 和 $j$ 的幾何中點」最近的候選範例，把它當成「預想的下一步 $k(i,j)$」，再用內積算出 $i \to j$ 與 $j \to k$ 之間的夾角，轉彎角度越大，曲率成本就越高。

### 4.3 四步工作流程：貪婪初始化 → 局部搜尋 → 多起點 → 剪斷迴圈

CDS 實際運作可以拆成四步：

1. **貪婪初始化（Nearest Neighbor）**：隨機挑一個起點，每步都選成本最低的下一個點，直到繞完一圈，建立一個初始迴圈——但這個迴圈通常有不少自我交叉的「打結」處。
2. **2-opt 局部搜尋**：反覆檢查有沒有更便宜的連接方式，透過反轉子序列來消除交叉，把路線微調得更平滑。
3. **多起點嘗試（Random Restart）**：局部搜尋容易卡在局部最佳解，所以換不同的隨機起點重跑，最多跑 10 次，挑出平滑度分數最高的一條。
4. **剪斷最長邊**：TSP 算出來的是閉合迴圈，但 Prompt 是一條直線，所以最後要找出路線裡跨度最大、最突兀的那條邊，一刀剪斷，變成有頭有尾的序列。

2-opt 這一步值得再拆細一點，因為它是整個演算法真正在「動手術」的地方。假設目前的排列是 `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]`（最後一點會連回起點），演算法用雙層迴圈挑兩條不相鄰的邊，比如 `0→1` 和 `4→5`。它會去成本矩陣裡查兩種連法的總成本：原本的 `Cost(0,1) + Cost(4,5)`，以及反轉後的 `Cost(0,4) + Cost(1,5)`。如果反轉後成本更低，就把 `1` 到 `4` 這一段整段倒過來，排列變成 `[0, 4, 3, 2, 1, 5, 6, 7, 8, 9]`。每次修改後重新從頭巡邏，直到找不到任何能降低成本的反轉為止，才算收斂。

整個流程單核 CPU 執行時間在一分鐘以內，不需要更動模型參數，算是相當划算的一個 Prompt 前處理模組。

## 五、實驗數據總覽：這些原則真的有用嗎？

前面講的都是機制，這一節看實際數字。

**語義相似度在推理任務上全面失靈。** 對比原裝（ori）、語意相似（sim）、語意不相似（dis）三種範例挑選方式，在非推理任務（BANKING77）裡 sim 表現最好；但在幾何、數論、DetectiveQA 三個推理任務裡，sim 幾乎全程墊底，找「最不相似」的範例反而比找「最相似」的表現更好。

![紅色曲線（BANKING77，非推理任務）中 Sim 表現最好；綠色、藍色曲線（幾何、數論、DetectiveQA 等推理任務）中 Sim 幾乎全程墊底。](img-005)
*圖 5 — 語意相似度在非推理任務與推理任務上呈現完全相反的效果。*

**自我生成範例的優勢有具體數字支撐。** LLaMA 3.1（8B）在 32-shot 設定下，用標準答案（origin）準確率只有 22.21%，換成自己寫錯的答案（wrong）反而衝到 35.91%。把更強模型（如 Qwen 2.5 14B）生成的範例餵給 LLaMA 3.1 8B，表現（33.53%–34.28%）也顯著低於餵給它自己生成的範例（35.57%–35.91%）。

![數據表格列出 LLaMA-3.1-8B 與 Qwen2.5-14B 在幾何任務不同 shot 數下，使用標準答案（Origin）與自我生成錯誤範例（Wrong）的準確率與標準差。](img-026)
*表 7 — 非推理模型 LLaMA-3.1-8B 在幾何任務上，使用自我生成的錯誤範例（Wrong）明顯優於標準答案（Origin）。*

![數據表格對比更強模型生成的範例與自我生成範例，在幾何任務不同 shot 數下的準確率與標準差。](img-027)
*表 8 — 把更強模型生成的範例餵給較弱模型，表現反而不如較弱模型的自我生成範例。*

**CDS 排序帶來穩定且跨模型的提升。** 在 Qwen3-14B 的幾何任務上（64-shot），隨機排列準確率只有 65.14%，經過 CDS 排序後提升到 68.89%，換成開源的 bge-m3 embedding 排序更高達 70.36%。就算換成閉源模型 gpt-5.2，在數論任務（32-shot）上，CDS 依然能把準確率從隨機的 91.11% 推到 92.59%——證明這個方法不挑 embedding 模型，也不挑 LLM。

![數據表格列出不同任務、不同 LLM、不同 embedding 模型下，origin、CDS、CDSbge 三種排序方式的準確率。](img-022)
*表 3 — CDS 在多種任務、多種 embedding 模型、多種 LLM 上都能帶來穩定的準確率提升。*

**曲率才是關鍵因果變數，不只是群聚效應。** 為了排除「CDS 表現好只是因為把相似題目分在同一區塊」這個質疑，作者設計了一組刻意製造急轉彎的對照組（high curv）——兩組都用歐式距離把相似題聚在一起，但 high curv 組在區塊過渡時故意選轉彎角度最大的排法。結果在 Qwen3-14B 的數論任務（16-shot）上，CDS 準確率 85.37%，high curv 掉到 79.26%；在 gpt-5.2 的幾何任務（16-shot）上，CDS 是 80.37%，high curv 只有 72.65%，差距高達 7.72 個百分點。這說明轉彎角度本身就是造成表現差異的因果因素，不是群聚效應的副產物。

![數據表格對比 CDS 與刻意製造急轉彎的 high curv 排序方式，在不同任務、不同模型下的準確率。](img-023)
*表 4 — 控制群聚效應後，刻意製造急轉彎的排序依然明顯拖累表現，證明曲率是因果因素。*

## 結論

這篇論文的核心結論，可以濃縮成兩句話給做 Prompt Engineering 的工程師：內容要看得懂，順序要走得順。在挑選範例內容時，與其追求由最強模型生成的完美解答，不如優先用目標模型自己生成的思維鏈——就算偶有瑕疵，分佈對齊帶來的吸收效果反而更好；在排序範例時，與其依賴語意相似度的傳統 RAG 檢索，不如用 CDS 這類方法把曲率降到最低，替模型鋪一條沒有急轉彎的推理路徑。

CDS 本身運算成本低、不用動模型參數，很適合直接接進現有的 LLM pipeline 當一層 Prompt 前處理。往後如果要延伸，一個自然的方向是把它跟現有的 RAG 架構結合，讓檢索增強生成不只挑「知識片段」，也一併排好「思維軌跡」；另一個值得關注的方向，是這套「模型讀自己生成的推理軌跡來自我提升」的機制，在 Agent Planning 或程式碼生成這類需要多步驟決策的任務上，可能也有發揮空間。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1. Reframing of CoT-ICL as in-context test-time learning.",
    "why_used": "支撐第一節說明論文如何把 ICL 重新框架成測試期即時學習的核心概念圖。",
    "agent_match_hint": "一張示意圖,呈現傳統靜態模式匹配與測試期學習兩種 ICL 觀點的對比。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 3. Scaling disparity between model types on math reasoning tasks. Left: Llama 3.3 (non-reasoning LLM) shows negative gains. Right: QwQ (32B) and R1 (685B) (reasoning LLM) shows clear positive scaling.",
    "why_used": "佐證非推理模型與推理模型在數學推理任務上呈現相反的 scaling 趨勢。",
    "agent_match_hint": "左右並排兩張折線圖,左邊 LLaMA 3.3 曲線下滑,右邊 QwQ 與 R1 曲線上升。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 2. Scaling disparity between task types. Performance (normalized accuracy) of non-reasoning LLMs on classification tasks (warm colors) versus reasoning tasks (cool colors). The x-axis represents normalized accuracy (i.e., x−x̄/σx for accuracy x), while the y-axis indicates the number of in-context demonstrations.",
    "why_used": "呈現分類任務與推理任務在範例數量增加時的準確率走勢對比,是第一個反直覺現象的核心證據。",
    "agent_match_hint": "多張子圖組成的圖表,暖色系(分類任務)曲線上升,冷色系(推理任務)曲線震盪下滑。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Figure 5. Performance with original(ori), similarity(sim) and dissimilar(dis) sets averaged across five LLMs. The area between the two sets is filled with colors, indicating the relative performance.",
    "why_used": "說明語意相似度檢索在推理任務上反而表現最差,支撐第五節的實驗數據討論。",
    "agent_match_hint": "多個任務並排的折線圖,呈現 origin、similarity、dissimilar 三種範例挑選方式的準確率對比。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Figure 6. Standard deviation of performance across five random demonstration orders on classification tasks (warm colors) versus reasoning tasks (cool colors), where nt corresponds to number theory. Results shown for Qwen2.5 (14B) (non-reasoning) and Qwen3 (14B) (reasoning).",
    "why_used": "佐證推理任務的順序敏感度(標準差)隨範例數增加而暴增,是第三個反直覺現象的核心證據。",
    "agent_match_hint": "折線圖呈現分類任務與推理任務的標準差隨範例數量變化的走勢,兩者方向相反。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Figure 7. Performance of two sets of self-generated in-context CoT, including the set filtered with only correct answer(cr) and the set filtered with only wrong answer(wr). crqwen14 is prompting the LLaMA model with the in-context CoT generated by Qwen 2.5 (14B). Left: Llama 3.1 Right: Qwen 2.5 (14B)",
    "why_used": "證明自我生成範例(即使答案錯誤)的表現優於資料集標準答案,支撐分佈對齊原則。",
    "agent_match_hint": "左右並排的折線圖,呈現 origin、cr、wr 三種範例來源的準確率對比。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Figure 8. Performance of the first set of self-generated in-context CoT. firstqwen3(14b) is prompting the Qwen 3 (8B) model with the in-context CoT generated by Qwen 3 (14B). Left: Qwen 3 (8B) Right: Qwen 3 (14B)",
    "why_used": "在跨模型情境下再次驗證自我生成範例優於原裝範例與更強模型生成範例。",
    "agent_match_hint": "左右並排的折線圖,呈現 origin、first、first_qwen3-14b 等範例來源的準確率對比。"
  },
  {
    "id": "img-022",
    "references_manifest_caption": "Table 3. CDS robustness across tasks, embedding models, and target LLMs. CDS uses the original embedding model, while CDSbge replaces it with bge-m3.",
    "why_used": "呈現 CDS 排序在多種任務、embedding 模型與 LLM 上都能帶來穩定提升,支撐第五節的跨模型有效性討論。",
    "agent_match_hint": "一張數據表格,列出不同任務、不同 LLM、不同 embedding 模型下 origin、CDS、CDSbge 三種排序方式的準確率。"
  },
  {
    "id": "img-023",
    "references_manifest_caption": "Table 4. Controlled smoothness ablation with bge-m3 embeddings. The same demonstrations are used for both orderings; only the transition curvature objective is inverted.",
    "why_used": "透過控制群聚效應的消融實驗,證明曲率本身是造成表現差異的因果因素。",
    "agent_match_hint": "一張數據表格,對比 CDS 與刻意製造急轉彎的 high curv 排序方式在不同任務、模型下的準確率。"
  },
  {
    "id": "img-024",
    "references_manifest_caption": "Table 5. A qualitative example illustrating why question-level semantic similarity selects demonstrations with incompatible reasoning trajectories.",
    "why_used": "用具體案例說明語意相似的範例可能解題邏輯完全不相容,支撐第二節的檢索陷阱討論。",
    "agent_match_hint": "一段幾何題目的文字案例,包含測試題、檢索出的相似題,以及兩者解法為何不相容的說明。"
  },
  {
    "id": "img-026",
    "references_manifest_caption": "Table 7. Non-reasoning LLMs on geometry across five random ordering seeds.",
    "why_used": "提供自我生成錯誤範例優於標準答案的具體數字佐證。",
    "agent_match_hint": "一張數據表格,列出 LLaMA-3.1-8B 與 Qwen2.5-14B 在幾何任務不同 shot 數下,origin 與 wrong 範例來源的準確率與標準差。"
  },
  {
    "id": "img-027",
    "references_manifest_caption": "Table 8. CoT-ICL generated from stronger LLMs versus self-generated demonstrations across five random ordering seeds. Values report μ ± σ.",
    "why_used": "提供更強模型生成範例反而不如自我生成範例的具體數字佐證。",
    "agent_match_hint": "一張數據表格,對比更強模型生成的範例與自我生成範例在幾何任務上的準確率與標準差。"
  }
]
```
