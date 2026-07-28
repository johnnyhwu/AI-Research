# 拆解 Persona-Aware-D2S：同一份文件，怎麼依受眾和長度長出不同簡報

## 前言

同一篇論文，拿去跟工程師報告和拿去跟業務主管報告，理想上內容應該完全不一樣：術語密度不同、細節深度不同、甚至該講的重點都不同。但現有的「文件轉投影片」（document-to-slides，簡稱 D2S）系統大多是單一輸出——不管誰要看，吐出來的都是同一份大綱。

Persona-Aware-D2S 這篇 EACL 2024 論文想解決的正是這個問題：讓同一份文件，依照「受眾是不是專家」「簡報要長還是短」這兩個條件，生成四種不同版本的投影片內容。做法上結合了 supervised fine-tuning 和一種借用自 Decision Transformer 的輕量版 preference fine-tuning。這篇文章會照著論文的三階段 pipeline，把方法拆開講清楚，也會老實列出這套做法在資料規模、架構設計上站不住腳的地方——先講結論：這篇論文的價值主要在「把 persona-aware 生成這個任務定義清楚」，而不是提供一套可以直接搬進 production 的系統。

## 同一份文件，兩種讀者要的東西差很多

![Persona-Aware-D2S 模型針對同一篇論文，對兩種不同受眾生成完全不同投影片內容的範例](img-001)
*圖 1 — 同一篇論文，模型依照受眾條件產生出內容完全不同的簡報。*

論文舉的例子很直覺：同一篇論文，講給一般大眾或業務主管聽，重點應該放在「這東西能幹嘛」的整體流程；講給技術聽眾聽，才需要深入模型架構的細節。這聽起來理所當然，但過去的 D2S 系統（像是 Doc2PPT、D2S）架構上就是「文件進、單一投影片出」的固定映射，沒有把「受眾是誰」當成輸入變數，加不了、也改不了。

除了缺少受眾條件，論文還點出另外三個問題。時長限制也沒被當成輸入：一小時的技術報告跟五分鐘的概覽需要的資訊密度天差地遠，但過去的系統一樣沒有這個維度可調。訓練方式本身也有問題：如果只用「最大化跟單一 gold reference 的相似度」（也就是常見的 ROUGE 分數）去訓練，模型學到的其實是逼近某一位標註者的寫法，而不是理解「不同受眾需要不同東西」這件事——這是一對多問題硬套單一答案訓練法的根本衝突。抽取式方法（直接複製貼上原文句子當投影片內容）則是另一個老問題，讀起來生硬、無法跨句整合。最後，要做這種條件式生成，需要「同一篇論文對應多種 persona 版本」的平行資料，這種資料集在這篇論文之前並不存在。

## 方法總覽：三階段 pipeline

![Persona-Aware-D2S 完整 pipeline 流程圖，包含 Topic Generator、Content Extractor 與 Reward Model 訓練流程](img-003)
*圖 2 — 完整 pipeline：上半部是主題生成的訓練流程，下半部是內容抽取，最後匯入摘要與對齊，產出最終投影片。*

論文把整個任務寫成一個條件機率：給定文件內容 C、受眾 B（專家或非專家）、長度 L（長版或短版），要生成最終投影片 O，也就是 p(O | C, B, L)。嚴格來說論文正文沒有把這個目標函式明確拆成連乘的形式，但照著 pipeline 實際的運作方式，可以近似拆成三段：

1. **Stage 1（主題大綱生成）**：先產生投影片的標題序列
2. **Stage 2（內容抽取）**：針對每個標題，從文件中挑出相關的句子和圖表說明
3. **Stage 3（摘要與邏輯對齊）**：把抽出來的零散內容整理成連貫的投影片

三個階段依序執行，前一階段的輸出是後一階段的輸入。以下照順序拆解每一階段實際在做什麼。

## Stage 1：先決定投影片要講哪些主題

第一階段的目標很單純：給定文件內容加上 persona 條件，生出一串投影片標題。做法分兩步，先用監督式微調打底，再用偏好資料修正。

**監督式微調（SFT-F）**用的是標準的 cross-entropy loss，讓生成的標題盡量貼近人工標註的 ground truth。這裡有個值得注意的設計選擇：論文訓練了**四個獨立的模型**，分別對應「專家＋長版」「專家＋短版」「非專家＋長版」「非專家＋短版」四種組合，而不是訓練一個模型、把受眾和長度當成 prompt 裡的條件文字。訓練資料規模也偏小——train split 只有 20 篇論文乘上 4 種配置，總共 80 筆樣本，拿去微調 GPT-3.5-turbo。80 筆樣本訓練出的模型，換到寫作風格差異較大的領域時，泛化能力有多少保留，論文並沒有進一步驗證。

**偏好微調（P-F）**是為了解決「單一 gold reference 不夠用」這個問題，分三步走。第一步收集人類偏好：讓四個 SFT 模型各自用不同的 temperature、top-K、top-p 生出五組候選主題，再找專家和非專家針對自己那組配置做兩兩比較（pairwise ranking），評分準則是「對目標受眾好不好懂」和「長度符不符合需求」；只有多數決有共識的樣本才保留，沒共識的直接丟棄。

第二步是用這些偏好資料訓練 reward model，數學上用的是 Bradley-Terry model——一個 1952 年就有的老統計方法，原本是拿來算球隊排名的，核心假設是每個項目都有一個看不見的「實力值」，比較結果只是這個實力值的機率反映。公式是 P(i 贏 j) = 實力_i / (實力_i + 實力_j)：如果 A 的實力值是 8、B 是 2，P(A 贏 B) 就是 0.8，A 實力強四倍、贏面八成，但 B 仍有兩成機率爆冷。這種容許不確定性的設計，剛好適合套在「人類偏好」這種本來就有雜訊的場景——這也是為什麼從 2017 年 RLHF 的開山文獻，到 InstructGPT、再到後來的 DPO，底層數學用的都是同一套 Bradley-Terry loss。論文訓練出四個 reward model（分別對應專家/非專家的 comprehensibility 和 length-based satisfaction），用的 encoder 是 distilbert-base-cased，參數量大約只有 66M，這樣的容量拿來判斷「好不好懂」這種語意複雜的任務夠不夠用，論文沒有做消融實驗驗證。

第三步才是真正的偏好微調，借用了 Decision Transformer（Chen et al., 2021）的技巧：從訓練集抽 prompt，用 SFT 模型生成五組候選，reward model 幫每組打分，把 (prompt, reward 分數) 當成訓練 pair，再拿去微調一次 LLM；推論時直接餵入「最大 reward 值」當條件，換出對應的高分輸出。Decision Transformer 原本是把強化學習問題重新包裝成序列預測問題：一條軌跡由一連串 (state, action, reward) 組成，訓練時模型看著「還想拿多少分（return-to-go）」加上「現在在哪個狀態」去預測該做什麼動作，推論時使用者先設定想要的分數，模型就照著這個目標吐出動作，一步一步往前推。但這裡有個不完整的挪用：Decision Transformer 真正的威力在處理「這一步的選擇會影響下一步能拿多少分」的多步驟決策問題，而 Persona-Aware-D2S 的應用場景是單次生成——一次把 prompt 丟進去，一次吐出完整大綱，沒有真正的多步驟決策結構，也沒有「軌跡」的概念。嚴格來說只是借了「把 reward 當條件塞進監督學習」這個表層技巧，繞開 PPO 的訓練複雜度，並沒有用到 Decision Transformer 真正被設計來解決的問題。論文裡也沒交代「最大 reward」這個數值具體怎麼決定、reward 是合併成單一純量還是多維度塞進 prompt，這些實作細節的缺失會讓人難以完整複現。

## Stage 2：從文件裡挑出真正用得到的內容

有了標題大綱之後，第二階段要幫每個標題找出對應的內容。直接把整篇論文丟給 LLM 挑句子成本太高，而且原文提到目標是要把 prompt 壓進 GPT-3.5-turbo 的 4096 token 限制內，所以論文設計了一個不靠 LLM 的兩層檢索機制：先拿每個投影片標題跟論文的章節標題做字面相似度比對（fuzzy match），取超過門檻值的候選；如果沒有任何章節通過門檻，才 fallback 到用 Sentence-BERT 算語意相似度，挑最像的章節。選定章節之後，該章節底下所有句子和圖表說明全部串接起來，就是這個標題的候選內容池。

這個機制換來的成本節省相當明確——論文自己在 Table 10 裡對照了三種檢索策略：

| 策略 | 平均 GPT 呼叫次數 | Recall |
|---|---|---|
| 論文提出的輕量 filter | 約 1 次 | 78.89% |
| 中等範圍候選 | 約 5.3 次 | 81.34% |
| 幾乎用整篇論文當候選 | 約 8.2 次 | 100% |

論文宣稱省了八倍的 GPT 呼叫次數，代價是永久漏掉大約 21% 真正相關的內容——這一步篩選是不可逆的，後面的階段完全沒機會再看到被漏掉的句子。這個門檻值本身也只在 5 篇論文組成的 dev split 上調過，樣本數很小，換到章節命名習慣不同的領域，大概率需要重新調整；而且整套機制高度依賴文件有標準化的章節結構，拿去處理會議紀錄、PRD 這類非結構化文件會直接失效。（順帶一提，Table 10 裡的 precision 欄位數字看起來不太合理，通常 precision 應該落在 0 到 1 之間，這裡的數字明顯偏大，懷疑是論文表格排版或欄位對齊出了問題，引用時建議留意。）

挑出候選內容之後，實際抽取哪些句子真正相關，用的是跟 Stage 1 完全相同的機制——同樣的 cross-entropy 監督式微調、同樣的 Bradley-Terry reward model、同樣的 Decision-Transformer-style 偏好微調，只是這次輸入輸出換成「(標題， 候選內容) → 真正相關的內容」。

## Stage 3：沒做任何訓練，卻是效果最明顯的一步

前兩個階段都投入大量心力在 SFT 加偏好微調上，第三階段反而完全沒有客製化訓練，只靠兩次 prompting：先把抽出來的內容摘要成條列重點，再把這些重點丟給 LLM，要求在同一個標題內部、或跨標題之間重新排列，讓內容更適合聽眾消化。論文沒有解釋為什麼對使用者體驗影響最大的一步，反而是資源投入最少的一步，這個不對稱的資源分配有點奇怪。

具體效果長什麼樣子，論文用同一個標題「Model Details」做了對照：

![P-F 模型針對同一個投影片標題，分別產生給非專家和給專家看的兩個版本](img-011)
*圖 6 — 左邊是給非專家看的版本，會解釋 LSTM、semantic similarity 這類術語，內容也比較精簡；右邊是給專家看的版本，直接進入訓練細節和網路架構，不解釋術語。*

這張對照圖是驗證整條 pipeline（三個階段疊加起來）最終效果的最直接方式：兩邊用詞密度和細節深度的差異一眼就看得出來。

Stage 3 這個摘要加重排的步驟到底有沒有用，論文做了一個消融實驗，找了 10 篇論文，對比「Stage 2 直接抽取的版本」和「Stage 3 摘要重排過的版本」：

![Summarization+Alignment 前後，Coherence、Coverage、Readability、Relevance 四項指標的長條圖對照](img-009)
*圖 5 — 紅色是對齊後、藍色是對齊前，可以看到 Readability 和 Coherence 兩項明顯提升，Coverage 和 Relevance 幾乎沒變。*

具體數字是 Coherence 提升 0.5 分、Readability 提升 1.0 分，Coverage 只掉了 0.05 分（幾乎不變）、Relevance 完全不變。這是全篇論文裡證據力相對紮實的實驗——直接 before/after 對照，證實摘要加重排確實提升了可讀性和連貫性，而且沒有明顯犧牲內容涵蓋度。不過樣本數只有 10 篇，評分者也不是獨立第三方，結論的外推空間有限。

幻覺（hallucination）的處理方式也值得留意：論文沒有做自動化事實查核，而是讓標註者對「內容跟標題的相關性」打分，用這個分數間接代表有沒有幻覺。這個做法不夠嚴謹——內容可以「跟標題高度相關」，同時「捏造論文裡根本沒講過的細節」，這種類型的幻覺用相關性分數是測不出來的。

## 整體評測結果

三個階段串起來之後，端到端的表現如何：

![四種 persona 配置下，Zero-shot、Few-shot、SFT-F、P-F 四種方法的 ROUGE-1/2/L 端到端評測結果](img-007)
*表 4 — P-F 模型在幾乎所有配置下都贏過 Zero-shot、Few-shot 和 SFT-F，唯獨在「專家＋短版」這個配置例外。*

P-F 在多數配置下都是表現最好的，唯獨在「專家＋短版」這個組合反而是 SFT-F 更好（表中 R-1 分數是 0.17 對 0.13）。整體上微調確實有用，Zero-shot 和 Few-shot 都明顯落後。另外值得一提的是，論文附錄 D 到 G 提供了 Zero-shot 和 Few-shot 版本在主題生成、內容抽取兩個模組的完整 prompt，但唯獨沒有提供 Stage 3 摘要重排用的 prompt template，是四個模組裡唯一沒辦法從附錄還原的一步。

## 批判性評估：這篇論文站不住腳的地方

論文自己在 Limitations 章節承認了幾點：內容忠實度有限；大部分技術術語需要額外解釋才能讓非專家理解，但模型能力有限；完全依賴人工寫的圖表說明，不會生成原創圖表也不理解圖片本身內容；只能產生文字條列摘要，不涉及排版設計；沒有多模態表徵能力，圖片相關資訊可能因此流失。

除了論文自己承認的，還有幾個論文沒提、但分析之後看得出來的問題。訓練資料規模是最明顯的一個：主題生成訓練只有 80 筆樣本，dev split 只有 5 篇論文，小樣本微調很容易 overfit 到這批論文的寫作風格，換到不同領域的效果存疑。架構的 scalability 也是硬傷：四種 persona 配置就要訓練四個獨立的 SFT 模型加四組 reward model，如果之後想擴展 persona 維度（比如加入角色區分：PM、工程師、主管），模型數量會是乘法爆炸，完全不 scalable。前面提到的檢索機制隱藏成本（21% 內容永久漏掉、門檻值只在 5 篇論文上調過、依賴標準化章節結構）也是實務上會踩到的坑。

Reward model 的容量、P-F 訓練細節的缺失、Stage 3 資源分配不對稱、幻覺評測方法薄弱——這幾點前面段落已經個別提過，這裡不重複。值得補充的是實驗樣本數普遍偏小這件事：質化分析只有 10 篇論文，認知負荷研究只找了 3 位專家，消融實驗也是 10 篇，統計效力都不高。但這不代表論文「沒做實驗」——模組級評測、端到端評測、消融實驗、質化分析，該有的類型其實都涵蓋到了，只是每一種的樣本規模都偏薄。最後，產出物本身離「真正的投影片」還有明顯落差：完全不含排版、顏色、字體這些視覺設計元素，本質上輸出的是結構化文字大綱，不是可以直接上台用的簡報。

## 如果你想在工程上參考這篇論文，該怎麼取捨

拆開來看，這篇論文裡各模組的落地價值差異很大。Stage 2 的兩層檢索設計（先便宜的字面匹配，字面匹配失敗才動用語意模型）成熟又好遷移，確實解決了真實的痛點——省下大量 API 成本，思路上也跟通用的 retrieve-then-rerank RAG 設計一致，值得直接借鑑。Stage 3 的「抽取後摘要重排」兩步驟 prompting 模式投入產出比最高：不用額外訓練，每個標題只多花兩次 LLM 呼叫，消融實驗也證實了效果，這是全篇論文裡最划算的部分。

相對地，Stage 1 和 Stage 2 共用的「每種條件訓練一個獨立模型」架構不建議直接複現，訓練和維運成本會隨 persona 維度乘法增長。Decision-Transformer-style 的偏好微調技巧則要看情境：如果你自己有需要做輕量版 preference alignment、又想避開 PPO 的 infra 複雜度，「把 reward 當條件塞進監督學習」這個思路值得參考，但要清楚意識到它捨棄了 Decision Transformer 真正的多步驟決策優勢，只是借了個殼。

總的來說，這篇論文更適合當作「問題定義」的參考，而不是「解決方案」的參考——它的價值在於清楚描述了 persona-aware 生成這個任務該長什麼樣子，而不是提供一套可以直接搬走的系統。

## 結論

Persona-Aware-D2S 的核心貢獻是定義了「依受眾和長度動態生成投影片」這個新任務，並且建立了對應的資料集；方法論本身（SFT 加上 RLHF-lite 組合）沒有原創性，是直接沿用 Christiano et al. 2017 的 RLHF 框架和 Chen et al. 2021 的 Decision Transformer 拼裝而成。研究價值中等偏低，工程價值也偏低，訓練資料規模撐不起真實世界的領域多樣性，四倍模型數量的架構不 scalable，產出物離「可以直接使用的投影片」還有一大段距離。

如果要從這篇論文帶走兩樣東西，一個是 Stage 2 的 retrieve-then-rerank 檢索設計（字面匹配加 Sentence-BERT fallback），另一個是 Decision Transformer 那種「reward-conditioning」訓練思路的基本概念——即便這篇論文本身只是不完整的借殼使用，這個思路在你自己想做輕量偏好對齊時仍然值得參考。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1: Output from our proposed Persona-Aware- D2S model showing the type of content preferred by end-users of two different persona while demonstrating the main pipeline of a conference paper.",
    "why_used": "在前言之後立刻用這張圖具體呈現「同一份文件、不同受眾要不同內容」這個核心動機，讓讀者一開始就有具體畫面。",
    "agent_match_hint": "同一篇論文左右並列兩種不同受眾版本的投影片內容範例圖。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 2: Shows the entire information flow of Persona-Aware D2S-Model Pipeline. Initially, LLM for Topic Generator is trained with supervision from Persona-Aware D2S dataset, followed by finetuning using human- feedback to produce Fine-tuned LM for Topic Generator. For each generated slide outline, we filter content from document to extract relevant snippet for the title, the final content generator LLM is fine-tuned with Human Feedback. The content for all slide outlines are summarized and aligned to produce a logically coherent slide deck.",
    "why_used": "在說明三階段 pipeline 的整體架構時，用這張流程圖幫讀者建立一次性的全局畫面，之後每個階段的細節說明都能對照這張圖。",
    "agent_match_hint": "一張分成上下兩部分的 pipeline 流程圖，包含 Topic Generator 訓練流程、Reward Model 訓練與最終的 Summarization+Alignment。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Figure 6: Source: (Zhang et al., 2019) the left slide is produced by P-F model for non-experts on ‘Model Details’ with explanations of technical jargons and less details on network and the right slide is generated by P-F model on ‘Model Details’ with content explaining the nitty gritty details of training and no explanations of jargons.",
    "why_used": "在講解 Stage 3 最終產出時，用同一個標題「Model Details」的兩個版本並列對照，讓讀者具體看到 persona 條件實際造成的內容差異，而不只是抽象敘述。",
    "agent_match_hint": "同一個投影片標題「Model Details」左右並列非專家版本與專家版本兩張投影片截圖。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Figure 5: Average User Ratings (1–5) on 10 randomly sampled slide decks after Summarization+Alignment (Step-3) compared to extractive approach of slide gener- ation (Step-2) indicating that summarization and align- ment is important for improved user experience.",
    "why_used": "作為 Stage 3 效果的量化證據，搭配前面的質化對照圖（Figure 6），讓讀者同時看到「感覺上有差」和「數字上真的有差」兩種證據。",
    "agent_match_hint": "一張長條圖，紅藍兩色分別代表對齊後與對齊前，四個指標包含 Coherence、Coverage、Readability、Relevance。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Table 4: Final Evaluation of Slides using the Persona-Aware-D2S pipeline (topic generation, content extraction, summmarization) for all four persona-aware configurations on Rouge-1, Rouge-2 and Rouge-L measures, showing that P-F models outperform others on all configuration except Expert-Short. The P-F model consistently outperforms other methodologies in the final evaluation of the pipeline, achieving the highest scores in Rouge-1, Rouge-2, and Rouge-L measures across almost all configurations. Notably, the P-F model excels in both expert and non-expert settings for long presentations. However, in the Expert-Short configuration, the SFT-F model shows superior performance, suggesting its effectiveness in concise content summarization for expert audiences.",
    "why_used": "作為整條 pipeline 端到端表現的總結證據，支撐「微調確實有效，但 Expert-Short 配置是例外」這個結論。",
    "agent_match_hint": "一張表格，橫向是四種 persona 配置，縱向列出 Zero-shot、Few-shot、SFT-F、P-F 四種方法在 ROUGE-1/2/L 上的數值。"
  }
]
```
