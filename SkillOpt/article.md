任何一個在凍結、僅能透過 API 呼叫的 LLM 之上做開發的工程師，遲早都會撞上同一堵牆：模型沒辦法針對手上的任務微調，但它預設的行為又不太對。

它寫出的 SQL 忽略了某個 schema 的細節、忘記檢查某個邊界情況，或是選錯了工具——而這種錯誤，它可能已經犯過十次了。

常見的解法有兩種，但都有各自的毛病。第一種是寫一份手動調整過的 system prompt，或是一份「技能」文件——一頁指令，附加在每一次呼叫前面。問題是，這種文件幾乎都是一次性手調後就再也沒人碰。

第二種解法是透過一個迴圈來「改善」：模型針對上一次的失敗進行反思，並當場改寫提示詞。這聽起來很吸引人，但實務上它往往會對「最近發生的錯誤」過度擬合，讓提示詞被一次性的補丁越塞越肥大，甚至悄悄抹除掉先前學到的教訓——這其實是一種災難性遺忘，只是它發生在純文字上，而不是權重上。

**SkillOpt** 是微軟近期發表的一篇論文，它沒有選擇繼續在這個問題上打補丁，而是直接重新框定了整個問題。

它的核心作法是：不再把技能文件的編輯當成一種隨性、不受約束的重寫過程，而是把它當成深度學習優化器對待一個權重張量的方式——一種外部的、有版本紀錄的、可訓練的狀態，透過受控且有界的步驟來更新，通過驗證才會被保留，沒有幫助就會被回滾。

目標模型本身完全沒有任何改變，所有的「學習」都發生在一份文字檔案裡。

## 兩個模型，各司其職

SkillOpt 把責任拆分給兩個獨立的模型，而不是要求同一個模型既要完成任務、又要幫自己的作業打分。

**目標模型（$M$）** 是實際執行工作的那一方——回答問題、呼叫工具、寫程式碼——並在任務所需的任何執行環境中運作，可能只是單純的對話環境，也可能是像 Codex 或 Claude Code 這種在真實工作區中運作、更複雜的環境。

它的權重與原生的 system prompt 在整個訓練過程中都**保持凍結**。對它來說，唯一會隨著每一輪跑分而改變的，是被塞進它工作區、或附加在前面的技能文件 $s$。用公式來說，給定一個任務 $x$ 與一份技能 $s$，目標模型會產生一條執行軌跡與一個介於 0 到 1 之間的純量分數：$(\tau(s), r(s)) = h(M, x, s)$。

**優化器模型（$O$）** 完全不碰任務本身，通常是一個能力更強的「前沿（frontier）」模型，而且只在離線訓練階段運作。

它的工作是讀取目標模型的執行軌跡與分數，然後針對技能文件提出具體的修改建議——新增這條啟發式規則、刪掉那句過時的指令、把這段模糊的措辭換掉。

把這兩個角色徹底分開，正是這整套設計在部署階段成本幾乎為零的原因：一旦訓練結束，優化器那一側的 API 花費就完全消失了，實際送進正式環境的，只有那個凍結的目標模型，加上一份小小的文字檔。

## 技能檔案本身

那份文字檔叫做 `best_skill.md`，長度通常落在 300 到 2,000 個 token 之間。

依照執行環境的不同，它的存在形式有兩種：單純的問答任務裡，它會直接被附加到 system prompt 前面；像 Codex 或 Claude Code 這種操作工具的 Agent，它則會被寫進目標模型的工作區，作為一份持久化、存在硬碟上的筆記。

它的內容，正如你對一份寫得好的內部作業手冊會有的期待：

- 通用的操作程序
- 領域特定的啟發式規則
- 工具呼叫的慣例
- 輸出格式的限制
- 針對已知失敗模式的防禦性提醒

## 避免球員兼裁判

SkillOpt 整套設計裡最重要的一項工程紀律，就是資料隔離——這個做法直接借用自標準的機器學習實務：訓練集（$D_{tr}$）、選擇／驗證集（$D_{sel}$），以及保留的測試集（$D_{test}$）。

優化器模型永遠只能看到來自 $D_{tr}$ 的執行軌跡，那是它取得「該改什麼」證據的地方。但它完全看不到 $D_{sel}$。

任何一份在訓練期間產生的候選技能，都必須獨立地拿到 $D_{sel}$ 上打分，而接受的規則非常嚴格：新技能的平均分數必須**嚴格大於**目前技能的分數，平手不算。

這條「嚴格大於」的門檻，堵住了迭代式提示詞編輯最常見的失敗模式——一連串各自看起來都很合理的修改，累加起來卻只是增加了雜訊或讓文件膨脹，並沒有真正帶來幫助。

![SkillOpt 總覽：目標模型帶著目前的技能執行任務，優化器模型把產生的執行軌跡轉換成有界的修改建議，而一道保留的驗證守門機制只會接受能確實提升驗證分數的修改。](img-001)
*圖 1 —— SkillOpt 總覽。被接受的修改會併入部署用的技能檔案；被拒絕的修改則會變成後續步驟的負面回饋。（來源：原始論文。）*

貫穿全文的心智模型——也是讓後面所有設計都能說得通的關鍵——是直接對照經典深度學習優化器的類比：

| 深度學習組件 | SkillOpt 的文字空間對應 |
| --- | --- |
| 參數（$W$） | 技能文件（`best_skill.md`） |
| 梯度 | 基於 Minibatch 產生的修改建議 |
| 學習率 | 編輯預算（$L_t$） |
| 驗證集 Checkpoint | $D_{sel}$ 盲測守門機制與嚴格淘汰制 |
| 動量／EMA | 逐 Epoch 的「慢速更新」 |

下面描述的每一個機制，存在的目的都是為了讓這張表的其中一邊，真正能在文字空間裡而不是梯度空間裡運作起來。

## 動手修改之前，先收集證據

每一個訓練步驟都從一次**Rollout（前向執行）**開始：目標模型帶著目前的技能，在從 $D_{tr}$ 抽出的一批 40 個任務上執行。

這是刻意設計的大批次。如果讓優化器只對單一失敗的執行軌跡做出反應，它往往會對造成那次失敗的特定雜訊過度擬合——例如一次網路延遲、一個措辭特別奇怪的輸入——而不是找出真正反覆出現的模式。40 個樣本能提供足夠的統計份量，讓系統得以分辨出「系統性的弱點」與「單一的偶發狀況」。

40 條執行軌跡收集完成後，會依照分數被分成**失敗池**與**成功池**。這個分流很重要，因為這兩個池子需要不同種類的修改：失敗池的目的是找出可以糾正的修復方式（什麼壞掉了、怎麼補）；成功池的目的則是找出強化（reinforcement）——那些已經在發揮作用、但還沒被寫進技能文件裡的好習慣，如果沒被記錄下來，下一次未必還能單靠運氣重現。

## 以 MapReduce 的方式進行平行診斷

如果把一個池子裡所有的失敗案例（大約 20 個左右）一次全部塞進單一次的優化器呼叫裡，會超出有用的上下文範圍，並且可能招致那種隨著提示詞越來越長而愈發嚴重的「lost-in-the-middle」現象。

因此，SkillOpt 改把每個池子切成大小為 8 的 Minibatch，並針對每個 Minibatch 各自發出一次平行 API 呼叫——這個形狀恰好對應到 MapReduce 的架構：每個 Minibatch 被獨立分析（Map），分析完的建議之後再被彙整起來（Reduce）。

系統支援最多同時執行 16 個這樣的呼叫，因此即使某個步驟需要在兩個池子裡診斷多達數十條執行軌跡，也能在一輪平行運算中處理完畢，而不必排成一條長長的序列佇列。

小批次大小訂在 8，本身也是刻意折衷的結果：大小為 1 會重現原本就想避免的單一軌跡過擬合問題，而 8 則小到足以留在上下文限制之內，又大到足以強迫模型「橫向比較」這幾條軌跡，找出真正在多個任務裡共同出現的失敗模式，而不是只盯著單一案例。

每一次平行呼叫都遵循固定的合約，而失敗面與成功面各有一位專門的分析師負責：

| 分析師 | 輸入 | 輸出 |
| --- | --- | --- |
| 失敗面（`analyst_error.md`） | 8 個失敗任務的執行軌跡＋目前的技能文件 | 共同失敗模式，以及一份 `patch`——一小串原子級修改操作（`append`、`insert_after`、`replace`、`delete`），每一項都精確定位在技能文件中的某個目標字串 |
| 成功面（`analyst_success.md`） | 8 個成功任務的執行軌跡＋目前的技能文件 | 目標模型已表現出、但技能文件裡還沒寫下的好習慣；對已經被充分涵蓋的內容保持保守，不重複強化 |

## 合併，但不失去脈絡

當並行的分析師們回傳各自的修改建議之後，SkillOpt 必須把可能重疊、有時互相矛盾的多份修改清單，收斂成一份。它透過兩階段的階層式合併來完成這件事。

第一步，如果任一個池子裡的提案超過 8 份，就會進行**樹狀合併（Tree Reduce）**：每最多 8 份為一批，兩兩合併（透過 `merge_failure.md` 或 `merge_success.md`），直到每個池子都只剩下一份統一的清單為止。

在這個合併過程中，重複的建議會被收斂成措辭最通用的一版，並附上 `support_count`，用來追蹤有多少個獨立的分析師提出了等價的建議——這是「這個失敗或好習慣到底有多常出現」的粗略指標。試圖修改技能文件中完全相同位置、但方式互不相容的提案，也會在這一步就被解決，而不是留到之後才發生衝突。

第二步，兩份此時已經各自統一的清單——一份來自失敗池、一份來自成功池——會經過最終的跨池合併（`merge_final.md`），而這裡的規則毫不含糊：**修復失敗永遠優先**。

如果一個來自成功池的修改與一個來自失敗池的修改，鎖定了同一個位置，失敗池的版本會被保留，沒有例外，只有不衝突的成功面修改才能存活到下一個階段。修復壞掉的東西，被視為嚴格高於強化已經運作良好的東西的優先級。

![SkillOpt 完整的管線：Rollout、Minibatch 反思、階層式合併、在預算限制下排序，以及一道保留的驗證守門機制，並在多個 Epoch 之間疊加一層慢速／元技能更新。](img-002)
*圖 2 —— SkillOpt 的完整管線，展示一批 Rollout 資料如何流經 Minibatch 反思、合併、在預算限制下的排序，以及在被真正寫入硬碟之前的驗證。（來源：原始論文。）*

## 文字版的學習率：編輯預算

合併完成之後，提案的修改數量可能還是遠超過一次套用的安全上限。SkillOpt 用**編輯預算** $L_t$ 來限制單一步驟能套用多少修改——這是學習率在文字空間裡的直接對應。

一次套用太多修改，就跟梯度下降時踩了太大的步伐一樣：技能文件可能因此陷入不穩定的狀態，並丟失先前辛苦累積下來的教訓。

這個預算本身遵循餘弦衰減排程，通常從 $L_t = 4$ 開始，逐漸衰減到 $L_t = 2$。訓練初期，技能文件大部分還是空的，所以較大幅度的結構性修改是安全且有用的（探索）；到了後期，一旦文件已經累積了實質內容，就只該讓小幅度的用詞微調通過（鞏固）——再多推進就有可能拆解掉已經運作良好的部分。

決定哪些修改能進入這個預算，由一個專門的排序步驟（`ranking.md`）負責，它嚴格按照優先順序，依照四項標準排序所有合併後的候選修改：

1. 能修復多少條軌跡的問題（與 `support_count` 直接掛鉤）
2. 是否真正補上一個缺口，而不是重複陳述文件裡已經有的內容
3. 是否讀起來像一條普遍適用的規則，而不是死板地寫死了某個任務的特定細節
4. 是否具體、可操作，而不是空泛的建議

只有排名前 $L_t$ 名的修改，才能進入候選技能。

## 真正做出決定的守門員

套用這些修改後產生的候選技能 $\tilde{s}$，並不會因為看起來合理就被信任——它必須靠著在 $D_{sel}$ 上被盲測打分來爭取通過，而 $D_{sel}$ 正是優化器從未看過的那個切分。

只有當 $\text{score}(\tilde{s})$ **嚴格大於**目前技能的分數，這個候選才會被寫入硬碟，成為新的目前技能。平手或分數下降，則整個步驟都會被丟棄，先前的技能維持不變。

被拒絕的修改並不會就此浪費。任何一個被拒絕的步驟，連同它試圖修復的失敗模式、以及分數下降了多少，都會被記錄進一個短期的**被拒修改緩衝區**。

這份歷史紀錄會被當成上下文，注入到**下一個**步驟的分析師與排序器呼叫裡，內容大致是：「我們已經試過這個做法，而且它傷害了驗證分數——別再提出一樣的建議了。」這是一個很小的機制，但它能阻止優化器一步一步重複嘗試同一個壞主意。

還有一個針對更平凡的失敗模式的實務保險機制：優化器提出的修改，是透過精確字串比對套用到技能文件上的，而 LLM 偶爾確實會產生幻覺，提出一個並沒有真的逐字出現在文件裡的目標字串。

發生這種情況時，那一項修改會被標記為 `skip`，記錄在 `edit_apply_report.json` 這份日誌裡，而不會讓整條管線崩潰，同一批次裡其他不受影響的修改仍會照常套用。

## 每個 Epoch 結束時的宏觀調控

逐步的修改在設計上本來就是短視的——每一步都只針對最近這一批 40 個任務做出反應。為了抓住更長時程的退步，SkillOpt 加入了第二層、比較慢的控制迴圈，每個 Epoch 才跑一次，而不是每個 Step 都跑。

在 Epoch 邊界，系統會從訓練集裡隨機抽出 20 個任務，讓**上一個 Epoch 的舊技能**與**這一個 Epoch 的新技能**，都在同一份固定的 20 題考卷上重新跑一次——這是一次受控的 A/B 對照，而不只是單純比較原始分數。這 20 題接著會被分到四種狀態之一：

| 狀態 | 定義 |
| --- | --- |
| 進步 | 舊技能做錯，新技能做對了 |
| 退步 | 舊技能做對，新技能卻做錯了——這是最危險的警訊 |
| 持續失敗 | 新舊技能都做錯，代表死穴還沒被解開 |
| 穩定成功 | 新舊技能都做對 |

**退步**這一類是最重要的，因為它是最清楚的訊號，顯示最近的步驟級修改——即使每一項都各自通過了自己的驗證守門——加總起來卻讓某些東西變得更糟。

一個專門的「慢速更新」呼叫（`slow_update.md`）會讀取這份對照結果，寫出一份宏觀層級的戰略筆記，並插入到 `best_skill.md` 裡一個特別標記、受保護的區塊，以 `<!-- SLOW_UPDATE_START -->` / `<!-- SLOW_UPDATE_END -->` 這組註解框起來。

在同一個 Epoch 剩下的時間裡，一般的步驟級修改被禁止碰觸這個區塊——只有 Epoch 邊界的流程能更新它。這正是傳統優化器裡動量或指數移動平均在文字空間的對應版本：它捕捉一個更長時程的趨勢，不該被短期的雜訊給抹掉。即使是這項更新，也不會被無條件信任——它同樣得通過 $D_{sel}$ 的驗證守門，如果沒能帶來實質幫助，就會被回滾。

除了慢速更新之外，還有第二個比較特別的機制：**元技能（Meta Skill）**。這是一份獨立的文件，由優化器寫給自己，總結在這個特定領域裡，哪些類型的修改容易通過驗證、哪些容易被拒絕。

它完全不會寫進 `best_skill.md`，目標模型永遠看不到它——相反地，它會被附加到**優化器自己**下一個 Epoch 的 system prompt 最前面，讓「教練」隨著時間越來越擅長提出修改建議，而部署出去的技能檔案卻不會因此多長一個 token。這是一個小巧但乾淨的元學習（meta-learning）範例：優化器在學習如何在這個環境裡做優化，而這與實際部署的內容完全分開。

## 這一切真的有效嗎？

論文的主要結果，是在六個基準測試、多種目標模型規模（從 GPT-5.5 一路到小得多的 Qwen3.5-4B），以及三種執行環境（直接對話、Codex、Claude Code）下進行的主要比較——總共 52 個（模型、基準測試、執行環境）組合。

![主要結果表：SkillOpt 在全部 52 個測量的（模型、基準測試、執行環境）欄位中都是最佳或並列最佳，且相較於無技能基準線持續有正向提升。](img-003)
*表 1 —— 在保留測試切分上的主要結果，將 SkillOpt 與無技能基準線以及其他幾個提示詞優化基準方法進行比較。（來源：原始論文。）*

SkillOpt 在這 52 個欄位裡，每一個都拿到最佳或並列最佳的成績，全面勝過像 TextGrad、GEPA、EvoSkill 這類基準方法。提升幅度的大小則相當取決於執行環境：

| 執行環境 | 平均提升 |
| --- | --- |
| 直接對話 | +23.5 分 |
| Codex（操作工具） | +24.8 分 |
| Claude Code | +19.1 分 |

Codex 這個數字，恐怕是三者之中更值得玩味的一個：它暗示著，在操作工具的 Agent 身上，還有大量可挖掘的空間，根本不在底層模型本身的能力上，而是在於周邊的操作流程被講清楚了多少。

比起「我們只是在測試集上調得特別用力」，更能證明這些提升可信的證據，是最終產物有多便宜、以及實際上只花了多少次修改就達到了這樣的成果。

![六個基準測試的成本與編輯經濟：每個基準測試只接受了 1 到 4 次修改，而每提升一分所需的訓練 token 成本則有相當大的差異。](img-009)
*表 6 —— GPT-5.5/GPT-5.5 訓練組的成本與編輯經濟，展示最終技能長度、被接受的修改次數，以及每提升一個絕對測試分數所花費的訓練 token 數。（來源：原始論文。）*

在全部六個基準測試中，最終的技能檔案都只需要**一到四次被接受的修改**——驗證守門把絕大多數提出的修改都擋了下來，這正是這種謹慎系統應有的選擇性。然而每提升一分所需的 token 成本，則依任務型態而有極大差異：

| 任務型態 | 每提升一分的訓練 token 成本 |
| --- | --- |
| 短、以工具呼叫為主（SpreadsheetBench、OfficeQA） | 0.6M – 1.1M |
| 長上下文（SearchQA、DocVQA） | 38M – 46M |

這對於任何在評估「這套方法對某個任務值不值得跑」的人來說，都是很實際的規劃依據。

論文同時也追問：模型學到的東西，究竟是真正通用的，還是只是死背了訓練時見過的那些題目的答案。遷移實驗是支持前者最有力的證據。

![跨三個軸向的遷移結果：跨模型、跨執行環境，以及跨基準測試。每一個遷移後的欄位，相較於目標自身的無技能基準線，都是正向提升。](img-006)
*表 4 —— 優化後的技能跨模型規模、跨執行環境、跨基準測試的遷移結果，每一個遷移後的欄位都優於目標自身的無技能基準線。（來源：原始論文。）*

這裡最驚人的單一數字，來自一次跨執行環境的遷移：一份在 Codex 環境裡針對試算表任務訓練出來的技能，在完全沒有進一步優化的情況下，直接丟進 Claude Code 環境，把那個環境的分數從 22.1 拉到 81.8——足足提升了 +59.7 分。

這個成績甚至**超過**了直接在 Claude Code 環境裡訓練出來的技能（80.4）。這強烈暗示，優化器萃取出來的東西，更接近「該怎麼用 Pandas 思考如何處理試算表資料」，而不是「該怎麼針對這個特定執行環境的語法來措辭指令」。在測試過的三個遷移軸向——模型規模、執行環境、基準測試——之中，沒有任何一個遷移後的欄位，分數低於目標自身的無技能基準線。

最後，論文也檢驗了這一切有多依賴一開始就擁有一個前沿等級的優化器模型。

![優化器強度的影響：即使換成能力較弱、與目標模型相同的優化器，依然能挽回大部分使用更強大前沿優化器所取得的收益。](img-008)
*表 5 —— 優化器強度的影響，比較強大的前沿優化器（GPT-5.5）與一個和目標模型共用同一個模型的「同型」優化器，其餘整套流程的設定都維持不變。（來源：原始論文。）*

即使把「教練」降級成跟目標模型一樣（規模小得多）的模型——也就是目標模型自己優化自己——有界更新加上驗證守門這套機制，依然足以挽回相較於前沿等級優化器所取得收益的 56% 到 74%。對於沒有前沿模型預算可以花在離線訓練上的團隊來說，這是一個相當實際的結果：自我教練的效果雖然打了折扣，但遠遠稱不上沒用。

這種選擇性，還可以從另一個角度得到驗證：驗證集挑出來的 checkpoint，是不是真的跟未見過測試集上表現最好的那個 checkpoint 一致。

![三個基準測試在不同 Epoch checkpoint 下的表現趨勢：訓練 Rollout 分數、驗證集最佳分數，以及測試集分數三條線高度重合。](img-007)
*圖 3 —— SpreadsheetBench、SearchQA、LiveMath 三個基準測試，隨著訓練 Epoch 推進的表現趨勢。（來源：原始論文。）*

在這三個基準測試上，驗證集分數（橘線）的最高點，跟測試集分數（綠線）的最高點高度重合。這在統計上是一個很好的訊號：代表驗證守門機制真正挑出來的，是泛化能力最好的版本，而不是恰好在訓練批次上表現亮眼、但換個題目就現形的過擬合版本。

## 裂縫在哪裡

看到 52/52 的全勝成績，很容易就此打住不再深究，但這篇論文（以及本文所依據的討論）其實相當坦承這套設計在正式生產環境中，可能會在哪些地方吃緊。

整套系統完全仰賴驗證守門機制，而驗證守門機制又完全仰賴一個**便宜、可靠、自動化的評分方式**。對於有可驗證答案的任務——通過測試與否的程式碼、符合目標與否的試算表轉換——這是一個合理的假設。

但對於開放式、主觀性高的任務（創意寫作、開放式的客服對話），要打造一個好到足以做為守門依據的評分器，老實說可能需要引入 LLM-as-judge 這類機制，而這又把這整套管線原本想避開的成本與雜訊給帶了回來。

這筆經濟帳也是雙面刃。部署成本確實是零——沒有額外的推論、沒有額外的延遲，就只是一份靜態的文字檔——但如上面表 6 所示，即使只訓練一份技能，也需要花上數千萬到上億個訓練 token。

這樣的取捨，明顯比較適合**高頻率、結構穩定、犯錯代價高**的正式生產 Agent（例如財務報表自動化、維運腳本執行），而不太適合一次性或低頻的任務，對後者來說，這筆 token 投資大概永遠回不了本。

在結構上，這套設計刻意把一切都塞進單一一份 `best_skill.md` 檔案，以維持簡潔——但這正是在一個涵蓋數百種不同業務情境的大型、異質化部署裡，最終會變成瓶頸的地方。單一一份 Markdown 檔案很快就會撞上 context 上限，而針對不同情境設計的規則，也可能開始在同一份文件裡互相牴觸。

如果真的需要擴展到那種規模，自然的下一步，看起來會是把 SkillOpt 跟某種技能庫路由機制結合起來——多份針對不同領域、各自獨立優化的技能檔案，在執行時由一個調度器來選擇，而不是全部擠進同一份檔案裡。

## 總結

SkillOpt 真正在主張的，是一種思維上的轉變：提示詞／技能的迭代，不該是一個黑盒子式的試錯過程，而應該是一套真正的優化管線，擁有深度學習領域早已視為理所當然的那些紀律。

用成批的證據取代單一的軼事、用有界的步伐取代不受約束的重寫、用真正盲測的驗證切分取代憑感覺判斷「這個修改看起來有幫助」，再加上一個較長時程的機制，防止短期的補丁侵蝕掉先前學到的教訓。

這一切都不需要碰模型權重，部署之後也不會多花一分錢——這正是為什麼，任何一個維護著會反覆犯下同一種錯誤的凍結模型 Agent 的團隊，都值得認真看看這套做法。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1 Overview of SkillOpt. The target model executes tasks with a current skill, an additional frontier optimizer model converts trajectories into bounded add/delete/replace skill edits, and a held-out gate accepts only edits that improve validation performance. Accepted edits are exported as a reusable skill artifact, while rejected edits become negative feedback for later updates.",
    "why_used": "在資料隔離／驗證守門機制的說明之後，馬上放上 SkillOpt 整體迴圈的示意圖，讓讀者在文章深入拆解每個階段之前，先有一個視覺化的錨點。",
    "agent_match_hint": "一張示意圖/總覽圖，畫出目標模型、優化器模型與驗證守門機制排成一個迴圈，並標示出已接受/已拒絕修改的路徑。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2 Pipeline of SkillOpt. A frozen target model executes a rollout batch with the current skill; an optimizer model performs minibatch reflection over successes and failures, proposes bounded add/delete/replace edits, merges and ranks them under a scheduled edit budget, and accepts the candidate skill only through a held-out validation gate. Across epochs, the slow/meta update retains longer-horizon lessons without changing the target model.",
    "why_used": "放在編輯預算／排序機制的說明之後，用一張圖總結整個步驟級管線(Rollout -> 反思 -> 合併 -> 排序 -> 守門)，接著文章才轉向討論 Epoch 層級的機制。",
    "agent_match_hint": "一張更詳細的管線圖，包含多個階段/方塊：Rollout 批次、Minibatch 反思、階層式合併、在預算下排序，以及驗證守門機制，再加上一個 Epoch 層級的慢速/元更新迴圈。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Table 1 Main results on held-out test splits. Scores are percentages; within each model–harness block, bold marks the best measured entry and underlining marks the second-best entry for each benchmark. Blue cells denote SkillOpt, and small green/red subscripts show the absolute change relative to the No skill row of the same model in the same harness. We omit ALFWorld under Codex and Claude Code harnesses because ALFWorld requires persistent embodied-environment interaction. SkillOpt is the best-or-tied entry on every measured cell of the table, with positive gains over the no-skill baseline throughout.",
    "why_used": "支撐文中報告 SkillOpt 在全部 52 個(模型、基準測試、執行環境)欄位中都是最佳或並列最佳的主要結果段落。",
    "agent_match_hint": "一張大型的結果矩陣/表格，以模型與執行環境作為列或欄群組，基準測試作為欄位，內容為百分比分數，含粗體/底線標示的儲存格，以及小的彩色上標數字。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 4 Transfer of optimized skills across three axes. (a) Cross-model: a skill optimized for the source model is deployed on the target model. (b) Cross-harness: a skill trained inside the source harness is evaluated inside the target harness, all on GPT–5.5. (c) Cross-benchmark: the source benchmark skill is evaluated on the target benchmark across three target models. Baseline is the target’s no-skill score, Direct is the in-domain SkillOpt score, and Transferred applies the source skill without further optimization. Subscripts show the change over the target baseline. The GPT–5.4→GPT–5.4 transferred cells in (a) are marked – because source and target match (i.e. no transfer occurs); we still report the GPT–5.4 baseline and in-domain SkillOpt score (taken from Table 1) in those rows for reference. Every remaining row in (a)–(c) is a positive transfer (no row falls below the target’s no-skill baseline).",
    "why_used": "支撐文中對跨模型/跨執行環境/跨基準測試遷移實驗的討論，尤其是那個 +59.7 分的跨執行環境結果。",
    "agent_match_hint": "一張含三個標示為 (a)(b)(c) 子表格的表，分別對應跨模型、跨執行環境、跨基準測試的遷移，每個子表格都有基準線/直接訓練/遷移後的分數欄位。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Figure 3 Performance trends across epoch checkpoints on three benchmarks: (a) SpreadsheetBench, (b) SearchQA, and (c) LiveMath. For each checkpoint, we report the training rollout score, the selection-best score on the validation set, and the final performance on the unseen test set. The results show how skill quality evolves during optimization and whether the checkpoint preferred by validation selection aligns with the checkpoint that yields the best generalization to the test set.",
    "why_used": "在優化器強度的討論旁引用，作為佐證，說明驗證集選出的 checkpoint 確實對應到真正的測試集泛化能力，而不是對訓練 Rollout 過擬合。",
    "agent_match_hint": "一張(或三張並列的小)折線圖，橫軸為 epoch/checkpoint，縱軸為分數，圖中有三條線：訓練 Rollout 分數、驗證集最佳分數，以及測試集分數。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Table 5 Effect of optimizer strength. Each (benchmark, target) pair is optimized either by a strong frontier optimizer (GPT–5.5, bolded) or by a target-matched optimizer that shares the target model; everything else in the SkillOpt loop is held fixed. Gains over the target’s no-skill baseline are shown as small green subscripts; the same baseline is used for both optimizer settings within a row. The optimizer runs only during offline training, so the stronger-optimizer column adds zero cost at deployment.",
    "why_used": "支撐文中討論 SkillOpt 的收益有多少依賴前沿等級的優化器，相對於一個與目標模型同型(自我教練)的優化器。",
    "agent_match_hint": "一張表格，針對相同的基準測試，比較強大的前沿優化器欄位與同型優化器欄位，附上上標的提升數值。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Table 6 Cost and edit economy of the GPT–5.5 / GPT–5.5 (student / teacher) skill runs. Initial and final best_skill.md lengths are in tokens; Edits is the number of accepted bounded updates; Cost / pt is training tokens per absolute test-point gain. One representative learned rule per benchmark is shown in Figure 4.",
    "why_used": "支撐文中討論每個基準測試只需要 1 到 4 次修改，以及不同基準測試之間每提升一分所需訓練 token 成本的巨大差異。",
    "agent_match_hint": "一張表格，每個基準測試各一列，欄位包含初始/最終技能長度(token 數)、被接受的修改次數、總訓練 token 數，以及每提升一個測試分數所花費的成本。"
  }
]
```
