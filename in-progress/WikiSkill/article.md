# WikiSkill:把 Agent 的執行經驗編譯成一個不會被回滾的知識庫

## 前言

如果你有做過 agent skill(把某個領域的操作步驟包裝成 `SKILL.md`,讓 agent 讀取套用)自動演化,大概踩過同一個問題:每一輪迭代都要重新從原始執行紀錄爬一次失敗原因,前幾輪分析出來的東西沒有被好好留下來,頂多變成一份「提案歷史清單」附掛在 skill 修改紀錄旁邊,不算一個真正被維護的知識庫。

Google Research 跟 Virginia Tech 這篇 *WikiSkill* 論文(arXiv:2608.27454,2026 年 8 月),想解的就是這件事:在「原始執行紀錄」跟「最終的 skill 文件」之間,插入一層**不會因為某次提案被拒絕就被回滾的持久知識層**,讓每一輪的 skill 修改都能站在累積證據上做判斷,而不是每次從零分析。這個構想不是原創——作者自己在論文開頭就講明是受 Andrej Karpathy 一篇談「LLM Wiki」的 gist 啟發——但論文把它系統化實作,並在 5 個模型、5 個任務上紮實驗證。

這篇文章會照著論文的順序,先講三層架構怎麼運作,再看實驗結果證明了什麼、又留下哪些沒證明的缺口,最後帶一個具體案例,示範一個 skill 是怎麼被這套機制一步步塑造出來的。

## 這篇論文想解決的問題

Agent skill 是一種輕量級的知識封裝方式:把特定領域的操作步驟打包成一個獨立的檔案目錄,核心是一份 `SKILL.md`,讓 agent 執行任務時可以讀取套用,不需要重新訓練模型參數。手動寫這些 skill 很花人力,於是最近一批研究開始讓 agent 自動演化 skill——先跑一批訓練任務,分析成功與失敗的執行軌跡,再據此修改 skill 內容,如此反覆迭代。

論文拿來比較的三個代表方法——EvoSkill、Trace2Skill、SkillOpt——都遵循同一套流程:跑任務、分析 trace、修改 skill、驗證後決定是否採用。它們也都有某種形式的「記憶」,例如 EvoSkill 會保留一份跨迭代不清空的提案與評估結果清單。但論文點出一個共同弱點:這些記憶都是附屬在「skill 修改紀錄」本身上面的**扁平清單**,沒有被當成一個獨立、會持續整理、隨時間增厚的知識表示法來維護。

## 方法:三層架構怎麼運作

WikiSkill 把 agent 的工作空間切成三層:

| 層 | 特性 | 內容 |
|---|---|---|
| Skill Layer(`skills/`) | 可逆、有條件更新 | 實際會被注入 prompt 的技能文件 |
| Wiki Layer(`wiki/`) | 持續累積、絕不重置 | 整理過的結構化知識 |
| Raw Layer(`raw/`) | 永久保存、只能新增 | 原始執行軌跡 |

Wiki Layer 是這篇論文新加的中間層,裡面有三種檔案:`patterns/` 底下一堆 markdown 檔,一個檔案對應一個具體的失敗模式或成功策略;`logs.md` 按時間順序記錄每次迭代做了什麼;`skill-impact.md` 記錄每次提案內容、驗證分數、被接受或拒絕的結果。Skill Layer 每個 skill 資料夾則有兩個檔案:`SKILL.md` 是技能內容本身,`PURPOSE.md` 記錄這個技能是被 wiki 裡哪些 pattern 啟發、修改過的動機。

三層架構是靜態的空間結構,實際運作靠四個角色依序互動,跑完一次迭代:

1. **Inference Agent** 用上一輪的 skill 集合跑訓練任務,結果寫入 Raw Layer(只能新增,不能存取 wiki)。
2. **Wiki Maintainer** 用一次 LLM 呼叫,抽樣少量 trace 做根因分析,更新 wiki 的 pattern、index、log。
3. **Skill Proposer** 以多輪 ReAct(交替進行推理與工具呼叫)agent 的方式,依序讀 wiki index、`skill-impact.md`、相關 pattern、原始 trace,提出一個 skill 的新建或修改(一次只改一個)。
4. **Gating & Rollback** 在驗證集上測試候選 skill,分數進步就採用,沒進步就整組退回上一版,不論結果都把提案內容、diff、分數寫進 `skill-impact.md`,再進入下一輪。

![WikiSkill 框架示意圖:最底層是不可變的原始執行紀錄,中間是持續累積的 Wiki 知識層,最上層是實際會被注入 prompt 的 Skill 層,四個角色依序互動完成一次迭代。](img-002)
*圖 2 — WikiSkill 框架總覽:Raw / Wiki / Skill 三層架構,以及一次迭代裡四個角色的互動順序。（來源:原始論文 Figure 2。）*

這裡有個關鍵設計:**Inference Agent 在跑訓練任務時完全不能存取 wiki**。這個限制在後面的消融實驗裡被驗證是必要的——如果讓它偷看 wiki,反而會讓最終 skill 品質變差,原因留到後面講。

### 三層架構最容易搞錯的地方

討論這類分層設計時最容易產生誤解的,是「哪一層能刪、能改、只能加」。實際規則跟直覺不太一樣:

- **Skill Layer 沒有「刪除」這個操作。** Skill Proposer 的輸出格式只有新建、修改既有、不動作三種,沒有刪除。你以為的「刪除」其實是 Gating & Rollback 造成的整組版本回退——新提案沒通過驗證,系統直接把整個 skill 集合退回上一輪版本,不是針對單一 skill 做刪除。
- **Wiki Layer 不是只能新增。** Wiki Maintainer 對既有 pattern 頁面有三種修改方式:在檔案尾端加、找到指定文字替換、在指定文字後插入。所以既有內容可以被修正、覆寫。「永不重置」講的是整個 wiki 狀態不會因為某次提案被拒絕而回滾,不是「每個檔案只能加不能改」。
- **Raw Layer 的唯讀,是「使用方式」的唯讀。** 這層每輪迭代都會新增這輪的執行紀錄,持續增長,「immutable」指的是已寫入的紀錄不會被修改或覆蓋。Wiki Maintainer 跟 Skill Proposer 對它的存取確實是唯讀,但這層本身一直在長大。

補充論文自己在 Limitations 承認的缺口:wiki 目前沒有自動清理機制,隨著迭代數增加會持續膨脹,論文明講這是留給未來研究的問題。

### Wiki Maintainer 實際上怎麼被 prompt

論文附錄提供了 Wiki Maintainer 完整的 system prompt。角色定義要求它對執行紀錄做深度根因分析,不能只看表面症狀;輸入是這輪的原始 trace 加上目前的 wiki context;輸出固定成 JSON,包含新建 pattern、對既有 pattern 的修改、完整更新後的 index 內容(不是差異)、這輪迭代的摘要。

其中有一段標注為 CRITICAL 的指示特別值得注意:index.md 的條目是 wiki 裡最重要的部分,因為它們決定了 inference agent 會不會去讀完整的 pattern 頁面,描述必須具體到讓 agent 不用讀完整頁面就能判斷相關性,同時包含問題、根因跟解法。這透露一個工程細節:pattern 頁面寫得再好,如果 index 摘要品質差,後面的 agent 根本不會點進去看——所以 index 品質被拉到跟 pattern 內容本身同等地位。

### 為什麼訓練時跑全資料集,分析時卻只精讀一小部分

論文附錄定義的 batch size 這個參數,常常讓人搞混它管的到底是什麼。要拆成兩層看才清楚:Inference Agent 每輪迭代一定對整個訓練集跑一次 rollout,這件事跟 batch size 無關;batch size 真正控制的是「分析加提案」這個步驟要分幾次做——如果 batch size 小於訓練集大小(EvoSkill、SkillOpt 用的方式),訓練集會被切成多個小批次,各自觸發一輪完整分析,WikiSkill 則把 batch size 設成等於訓練集大小,所以每輪迭代只做一次分析。

這其實是把「廣度」跟「深度」拆成兩個旋鈕分開處理:廣度靠全批次 rollout 加上 Skill Proposer 一開始拿到的全部任務成敗摘要取得,目的是避免只看到部分資料而誤判某個錯誤模式的普遍性;深度則靠有限抽樣控制成本——Wiki Maintainer 每輪固定抽樣最多 8 筆(5 敗 3 成),每筆截斷到 15,000 字元,而 Skill Proposer 不受這個限制,可以自己動態挑選整個訓練集的 trace 精讀,規則只要求至少讀滿 4 筆,沒有上限。兩者都是為了應付 context window 限制,只是解法不同:一個是單次呼叫、固定抽樣,一個是多輪 ReAct、動態按需讀取。

## 實驗結果:穩定領先,但領先幅度差很多

實驗涵蓋 5 個模型(Qwen-3.5-4B、Qwen-3.5-9B、Qwen-3.6-27B、Gemma-4-31B、Gemini-3.5-Flash)乘上 5 個任務(數學推理 LiveMath、需要 web search 的事實問答 SealQA、試算表操作 SpreadSheet、長文件問答 OfficeQA、具身互動任務 ALFWorld),每個組合跑三次完整演化流程取平均。

![長條圖顯示五個模型在無 skill、以及 EvoSkill、SkillOpt、WikiSkill 三種演化方法下的平均準確率,WikiSkill 全面領先,且模型越大領先幅度越明顯。](img-001)
*圖 1 — 五個模型的平均表現對照:WikiSkill 在所有模型上都領先,且優勢隨模型能力增強而放大。（來源:原始論文 Figure 1。）*

核心數字是:WikiSkill 在全部 5 個模型上平均分數都最高,跟每個模型「表現最好的競爭對手」相比,分別多贏 3.3、5.1、10.0、5.8、12.0 個百分點(依序對應 4B、9B、27B、Gemma-4-31B、Gemini-3.5-Flash)。幾個較顯眼的單點例子:Gemini-3.5-Flash 在 LiveMath 上從 33.0% 拉到 72.6%,在 SpreadSheet 上從 50.5% 拉到 76.6%;Qwen-3.6-27B 在 ALFWorld 上從 52.8% 拉到 77.6%。

![表格顯示五個模型分別在無 skill、以及 EvoSkill、Trace2Skill、SkillOpt、WikiSkill 四種方法下,於五個任務上的準確率對照。](img-003)
*表 1 — 跨模型、跨任務的主要結果對照表。WikiSkill 在每個模型區塊的平均分數都是最高。（來源:原始論文 Table 1。）*

論文特別強調的是**穩定性**,不只是峰值表現。其他方法在部分設定上會明顯退步,不是單純進步較少而已——例如 EvoSkill 讓 Qwen-9B 在 LiveMath 上大幅進步(28.2%→58.1%),卻讓 Gemma-4-31B 在同一任務上退步(33.9%→29.8%);SkillOpt 讓 Gemini-3.5-Flash 在 SealQA 上退步(29.4%→28.2%)。WikiSkill 沒有出現這種時好時壞的情況。

有個資料清理細節值得記一下:Gemini-3.5-Flash 在 ALFWorld 上所有方法(含無 skill)分數都是 85.9%,原因是它在演化開始前驗證集就已經拿到 100% 分數,觸發了提早終止機制,根本沒真的跑演化流程——不是 WikiSkill 在這個任務上沒效果,是這個任務對它來說本來就太簡單。

### 模型越大,skill evolution 帶來的效益反而越大

論文用「skill evolution 跟 model scaling **互補**」來描述這個發現。在 Qwen 系列裡看得最清楚(同一家族只有參數量不同,比較乾淨):WikiSkill 帶來的平均進步幅度隨規模遞增,4B 是 +12.3 分,9B 是 +17.5 分,27B 是 +23.9 分。在 SpreadSheet 這個任務上尤其明顯,三個模型分別進步 +6.5、+9.3、+40.9 分。

一個更直覺的說法是:小模型加上好的 skill,可以反過來打贏沒有 skill 的大模型。Qwen-3.5-9B 加上 WikiSkill,平均準確率拿到 47.4%,超過 Qwen-3.6-27B 完全沒用 skill 時的 39.4%。論文的解讀是:模型能力跟演化出的程序性知識,提供的是互補的效能來源——越強的模型越能有效開發跟執行更精細的 skill,獲益也就越多;而有效的 skill,則可以讓小模型彌補跟大模型之間的能力差距。

不過跨資料集的效益也不平均。Qwen-3.6-27B 在 OfficeQA(長文件檢索型任務)只進步 11.6 分,相較之下 SpreadSheet 進步 40.9 分。論文對此的解釋是:大模型能有效運用演化出的搜尋流程導覽長文件,但小模型沒辦法執行這種多步驟搜尋流程,反而退回預設閱讀行為,導致些微退步——這點跟下一節的跨模型遷移結果互相呼應。

### 跨模型 skill 遷移:能不能遷移,看 skill 裡包的是什麼

這一組實驗在測:用模型 A 演化出來的 skill,能不能直接拿給模型 B 用?

![表格顯示用無 skill、以及 Qwen-3.5-4B、Qwen-3.6-27B、Gemini-3.5-Flash 三個來源模型演化出的 skill,分別套用到各個推論模型上的準確率對照。](img-004)
*表 2 — 跨模型 skill 遷移結果。灰底列是模型自己演化、自己使用的情況。（來源:原始論文 Table 2。）*

三個發現值得拆開來看:

| 發現 | 具體例子 |
|---|---|
| 遷移過去的 skill,常常比自己演化的還好用 | Qwen-3.6-27B 的 skill 拿給 Qwen-3.5-9B 用在 SpreadSheet 上,拿到 50.5%,比它自己演化的 skill(33.6%)還高 |
| 能不能遷移,取決於 skill 包的是通用程序還是模型專屬的權宜之計 | LiveMath 的 skill 遷移得特別好(33.0%→67-74%);但 SpreadSheet 上,Qwen-3.5-4B 的 skill 拿給 Gemini-3.5-Flash 用,分數從 50.5% 掉到 18.1%,同樣情境換成 Qwen-3.6-27B 的 skill 卻拉到 63.4% |
| 即使 skill 來源相同,不同接收模型「消化」skill 的能力也不一樣 | Qwen-3.5-4B 自己演化的 skill 拿給自己用反而退步(30.2%→28.5%),同一份 skill 拿給 Qwen-3.6-27B 用卻進步(42.1%→52.9%) |

第二點的負遷移案例,論文有做根因分析:小模型演化出的 skill 包了很多低階權宜之計(例如單行 Python 指令、字串轉換規則),幫小模型避開執行失敗,卻反而限制了強模型使用更完整的端到端腳本;破碎化的診斷流程也會製造多餘工具呼叫,可能在任務完成前就耗光強模型的互動預算。

但論文**沒有**解釋另一個更反直覺的現象:小模型(Qwen-3.5-4B)演化出的 skill,拿給 Gemma-4-31B 用之後,在 LiveMath、ALFWorld 上都讓它變好(分別拉到 73.1%、66.9%)——這件事論文只報告了數字,沒有進一步的根因分析。整體來看,論文給了很多「哪個方向遷移得好/不好」的現象描述,但真正做因果解釋的只有 SpreadSheet 這一個案例,而且做的也只是定性的錯誤分析,不是系統性驗證。

把上面三個發現合起來看,論文提出一個值得記住的框架性論點:自我演化這件事,其實混雜了兩種不同的能力——「從經驗中發掘出有用的程序性知識」跟「在推論時有效執行這些知識」——這兩者是可以拆開來看待的獨立能力,不是同一件事。這個視角比論文本身更通用:評估任何「self-improving agent」系統時,都可以先問一句,這個系統進步了,是因為它學到更好的東西,還是因為它更會照著指示做?

## 消融實驗:wiki 到底在哪裡起作用

這是整篇論文實驗設計做得最乾淨的一組,只用 Gemini-3.5-Flash 一個模型做,分別調整 Inference Agent 跟 Skill Proposer 是否有 wiki 存取權。

![表格顯示四種消融設定下(Inference Agent 有無 wiki 存取、Skill Proposer 有無 wiki 存取)的五個 benchmark 平均分數。](img-005)
*表 3 — 消融實驗結果:分別關閉 Inference Agent、Skill Proposer 的 wiki 存取權,觀察平均分數變化。（來源:原始論文 Table 3。）*

四種設定的平均分數,排出來是這樣:無 skill 基準線 40.4%;只有 Inference Agent 能看 wiki(Wiki Maintainer 已移除)45.3%;兩邊都不能看 wiki(Wiki Maintainer 已移除)48.7%;兩邊都能看 wiki 60.9%;只有 Skill Proposer 能看 wiki(WikiSkill 預設配置)63.7%。

兩個結論很清楚。第一,讓 Skill Proposer 存取持久 wiki 效果非常顯著:在 Inference Agent 不能碰 wiki 的前提下,單純把 Skill Proposer 的 wiki 存取權打開,平均分數從 48.7% 跳到 63.7%,足足 +15.0 個百分點,是整篇論文裡最大幅度的單一變因效果。細看子項,LiveMath 從 51.3% 拉到 72.6%,SpreadSheet 從 49.9% 拉到 76.6%。論文的解釋是:沒有跨迭代累積的知識,Skill Proposer 很難處理複雜、需要多次迭代才能收斂的失敗模式。

第二,讓 Inference Agent 訓練時也碰 wiki,反而讓最終 skill 品質變差:在 Skill Proposer 已經有 wiki 存取權的前提下,如果連 Inference Agent 訓練時也讓它看 wiki,平均分數從 63.7% 掉到 60.9%,LiveMath 掉最多(72.6%→64.8%)。論文給的解釋明確標注是一個假設,沒有進一步驗證:當 Inference Agent 訓練時同時能看到 skill 跟 wiki,它可能直接從 wiki 裡找答案來解題,而不是靠 skill 本身解題,這樣一來產生出來的訓練 trace 就會失真——agent 表現好不是因為 skill 好用,是因為 wiki 幫了忙,這會讓 Skill Proposer 拿到的訓練訊號失去代表性。這也是為什麼架構設計裡刻意規定 Inference Agent 訓練時不能看 wiki。

### 這篇論文真正定義的問題,跟消融實驗沒證明的事

表面上看,EvoSkill 也維護了一份跨迭代不清空的提案歷史,那 WikiSkill 到底多做了什麼?答案不是「有沒有記憶」,而是**記憶的形式**:

| | EvoSkill 的歷史列表 | WikiSkill 的 wiki |
|---|---|---|
| 儲存形式 | 扁平列表:一筆一筆的提案內容、驗證分數、接受/拒絕 | 結構化、按主題組織的知識頁面,每頁對應一個具體的失敗模式或成功策略 |
| 有沒有獨立的整理步驟 | 沒有,proposer 自己看歷史列表加這次的原始 trace,現場消化 | 有專門的 Wiki Maintainer,職責就是做根因分析、把原始 trace 提煉合併進既有 pattern 頁面 |
| 證據累積方式 | 每次的失敗案例基本上獨立存在 | 同一個 pattern 頁面會跨迭代持續疊加證據 |
| 能不能查找相關知識 | 沒有索引機制,只能整份歷史從頭看 | 有 index.md,每個 pattern 一行摘要(問題、根因、解法),讓 proposer 快速判斷哪些知識相關 |

濃縮成一句話:知識需要被主動整理、消化、累積證據,而不只是被動地按時間堆疊。

不過這裡要老實講一個消融實驗設計上的缺口:表 3 拿掉 wiki 的那組設定,是完全移除 Wiki Maintainer,測的是「有結構化知識」對比「完全沒有跨迭代知識」,並沒有設計一組對照組去比較「結構化 wiki」對比「像 EvoSkill 那樣的扁平歷史列表」。換句話說,表 3 證明了「有結構化知識 > 完全沒有知識」(+15%),但沒有直接證明這篇論文最想主張的那件事——「結構化知識 > 扁平列表知識」。表 1 雖然有跟 EvoSkill 整體比較分數,但那個比較混雜了另一個變因:WikiSkill 的 Skill Proposer 是可以動態探索 10 到 20 輪的多輪 ReAct agent,而 EvoSkill 沒有這種機制,沒辦法乾淨歸因到「wiki 的結構化程度」這一項上。這是整篇論文論證上最大的一個缺口。

## 案例:一個 skill 怎麼被 wiki 一步步塑造出來

這個案例具體示範了前面講的「回溯機制」實際長什麼樣——場景是 ALFWorld 上,Qwen-3.6-27B 演化出一個叫 `break-repetition-loop` 的 skill 的完整過程。

![時間軸示意圖:第 0 輪 Wiki Maintainer 建立 pattern 頁面、Skill Proposer 提案被拒絕;第 1 輪根據拒絕紀錄提出更聚焦的新提案並被接受;之後幾輪持續有新證據疊加進同一個 pattern 頁面,並在第 4 輪據此修改該 skill。](img-006)
*圖 3 — Wiki 引導 skill 演化的案例研究(ALFWorld,Qwen-3.6-27B)。（來源:原始論文 Figure 3。）*

第 0 輪,Wiki Maintainer 建立了一個 pattern 頁面 `take-examine-move-loop.md`,描述 agent 會拿起物品、檢查、放回原位、不斷重複這個循環,證據來自兩筆訓練資料。同一輪,Skill Proposer 提案新建一個叫 `goal-directed-action` 的 skill,但驗證分數 0.72,沒超過 baseline,被拒絕——`skill-impact.md` 完整記下了這次的 diff 跟拒絕結果。

第 1 輪,Wiki Maintainer 發現同樣的錯誤又出現了,還多了一個新變體,於是把新證據追加進既有的 pattern 頁面。Skill Proposer 這次讀到了第 0 輪的拒絕紀錄,提案改成新建一個更具體、更聚焦動作模式的 skill `break-repetition-loop`,驗證分數 0.78,通過。第 2 到第 3 輪(論文簡化未展開),Wiki Maintainer 又建立了一個新 pattern `multi-operation-loop.md`,描述 agent 對同一物品重複做操作卻不檢查任務是否已完成。到了第 4 輪,Skill Proposer 讀到這個新證據,提案修改(不是重建)`break-repetition-loop`,再次通過。

最終這個 skill 的 `PURPOSE.md` 只用一行話就交代清楚了來龍去脈:「建立為 break-repetition-loop。前一次嘗試 goal-directed-action 因為太抽象而被拒絕。這一版更精簡,用的是具體的動作模式。」不用回頭爬原始 trace 自己猜,光看這一行就知道這版 skill 為什麼長這樣。而「每種操作類型只做一次」這條規則能在第 4 輪被加進去,正是因為對應的 pattern 頁面持續累積了跨迭代證據——這正是前面消融實驗裡「Skill Proposer 有 wiki 存取權帶來 +15 分」的一個具體實例。

## 工程成本:呼叫次數少,不等於總成本低

這裡算的是「每輪迭代,分析加提案這個步驟本身要打幾次 LLM API」,不含 Inference Agent 本身跑訓練任務的呼叫。

![表格列出 WikiSkill、EvoSkill、SkillOpt、Trace2Skill 四種框架每輪迭代的 optimizer API 呼叫次數公式與複雜度等級對照。](img-010)
*表 7 — 四種 self-improving agent 框架的 optimizer API 呼叫複雜度對照。（來源:原始論文 Table 7,符號定義見原文。）*

四家方法每輪迭代的呼叫次數公式分別是:WikiSkill 是 `(1 + T_ReAct) × (N_train / B)`,EvoSkill 是 `2 × N_train / B`,SkillOpt 是 `K_opt × N_train / B`,Trace2Skill 大約是 `N_train + (1 + 1/(c-1)) × (N_train / B) + 1`。論文實驗裡 WikiSkill 全部資料集都把 batch size 設成等於訓練集大小,`N_train / B` 恆等於 1,公式因此化簡成 `1 + T_ReAct`——只跟 ReAct 輪數有關,跟訓練集大小完全無關,T_ReAct 在論文實驗裡大約落在 10 到 20 之間。

這代表訓練集從 80 筆變成 800 筆,WikiSkill 每輪迭代的呼叫次數不會變,但 EvoSkill、SkillOpt 都是批次越小、資料越多,呼叫次數線性增加;Trace2Skill 更明確,因為它規定每一筆 trace 都要單獨分析一次,不管怎麼調 batch size,呼叫次數下界永遠跟訓練集大小成正比,是四者裡複雜度最差的。

不過論文自己也承認這個「呼叫次數固定」的代價:每一輪 ReAct 都是一次完整的 LLM 呼叫,而且 Skill Proposer 讀的 context 通常比單筆 trace 分析要大很多。換句話說,呼叫次數少不等於總 token 成本低——如果每一輪 ReAct 都在讀很長的 wiki context 加 trace 內容,單次呼叫的 token 用量可能遠超過 EvoSkill 那種「小批次、多次但每次讀得少」的呼叫方式。論文完全沒有提供 token 層級的成本比較,只比較了呼叫次數這一個指標,這是評估這套框架實際部署成本時容易被忽略的陷阱。

## 值得帶走的東西

論文的核心貢獻本身不算原創,作者自己講明是把 Karpathy 的 LLM Wiki 構想套用到 skill evolution 上。這篇論文真正做的事,是把這個構想系統化實作,並在 5 個模型、5 個任務上紮實驗證,做出了整篇論文裡唯一算乾淨的消融實驗。三件事證得程度不一:證得最紮實的,是給 Skill Proposer 一個持久、不隨 gating 結果回滾的知識層,效果遠好於完全沒有跨迭代知識;證得中等的,是效益隨模型規模遞增、發掘知識與執行知識可以拆分,但部分現象(例如小模型的 skill 讓大模型變好)沒有因果解釋;沒有被證明、只是論文自己主張的,是「結構化整理過的知識」比「扁平歷史列表」更好——這是整篇論文論證上最大的缺口。

論文誠實承認的限制還有:wiki 沒有自動清理機制;驗證門檻是嚴格的「必須超越最佳分數」,排除了中性但可能有長期價值的提案;目前只驗證到單次 rollout 規模的任務,沒測過真正長時程(數百步、數小時)的場景。

脫離這篇論文本身,有幾個判斷框架是通用的,值得留在腦子裡:三層分離的設計模式(不可變的原始紀錄、持續累積且不回滾的結構化知識、可回退的可執行產出)可以直接遷移到其他 agent 演化系統上;訓練時的 actor 不該偷看 optimizer 用的知識來源,否則訓練訊號會失真;廣度用全批次摘要拿、深度用有限抽樣或動態檢索做,是處理「既要全局視野又要個案深度、但 context window 有限」這類問題的通用拆法;還有做消融實驗時,對照組要精準對應到你想否定的那個具體形式,不能只對照「完全沒有」——這篇論文最想證明的核心論點,恰好就是全文中唯一沒有被消融實驗直接驗證的一塊,值得引以為戒。

## 結論

WikiSkill 在「原始執行紀錄」跟「skill 文件」之間插入一層結構化、永不回滾的知識庫,讓 Skill Proposer 能站在跨迭代累積的證據上做判斷——這是整篇論文最紮實的貢獻,也是本文的核心線索。它證得多紮實、哪裡還留著缺口,前一節已經拆開講過,這裡不重複。如果你在做 agent skill 或 memory 系統,三層分離加上永不重置的知識庫這個設計模式,值得直接拿去參考。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1 | WikiSkill consistently improves over both the no-skill baseline and existing skill- evolution methods. Interestingly, its advantage becomes more pronounced for stronger models. We report average accuracy across the evaluated benchmarks for each model using no skills or skills evolved by EvoSkill, SkillOpt, and WikiSkill (see Table 1 for details).",
    "why_used": "支撐説明 WikiSkill 全面領先且優勢隨模型能力增強而放大這個主結果。",
    "agent_match_hint": "長條圖,橫軸為五個模型,縱軸為平均準確率,比較無 skill 與三種演化方法。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2 | Overview of the WikiSkill framework. The agent workspace is structured into three layers: immutable execution traces (Raw Layer), a persistent knowledge base that compounds across iterations (Wiki Layer), and active procedural instructions (Skills Layer). In each evolutionary loop, the Inference Agent runs rollouts (injecting active skills but restricting Wiki access), the Wiki Maintainer consolidates traces into the Wiki, and the Skill Proposer (with the ReAct mechanism) suggests updates while the Wiki is retained across all iterations.",
    "why_used": "說明三層架構跟一次迭代裡四個角色互動流程的整體示意圖。",
    "agent_match_hint": "架構示意圖,顯示 Raw/Wiki/Skill 三層,以及 Inference Agent、Wiki Maintainer、Skill Proposer 之間的資料流箭頭。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Table 1 | Method comparison across inference models and test sets. Each horizontal block evaluates a specific inference model without skills (No skill) and with skills developed by different skill-evolution methods. To ensure a fair comparison, all skill-evolution methods start with an empty skill set, and evolved skills are injected into the Inference Agent’s prompt at inference time. All reported scores are the average test performance across three independent runs of the full evolution process. Our method (WikiSkill) is highlighted. Bold indicates the best performance for each dataset; multiple bold results",
    "why_used": "支撐跨模型、跨任務主結果的具體數字對照。",
    "agent_match_hint": "表格,列為五個模型分區塊,欄為五個任務加平均分數,比較無 skill 與四種演化方法。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Table 2 | Cross-model skill transfer results. We evaluate inference models using no skills (None) and skills evolved by WikiSkill with Qwen-3.5-4B, Qwen-3.6-27B, and Gemini-3.5-Flash as source models. Skills are injected into the Inference Agent’s system prompt at inference time. Highlighted rows indicate self-evolved skills, where the inference model and skill source are the same. The highest performance per benchmark within each model block is bolded. ‘−’ indicates that the source model reached 100% validation performance before skill evolution, so no skill was evolved.",
    "why_used": "支撐跨模型 skill 遷移三個發現的具體數字。",
    "agent_match_hint": "表格,列為接收模型分區塊,欄為不同來源模型演化出的 skill 在各任務上的準確率。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Table 3 | Ablation study on WikiSkill using Gemini-3.5-Flash. We evaluate performance across benchmarks under four configurations that vary whether the Inference Agent and Skill Proposer have wiki access during skill evolution. When the Skill Proposer has no Wiki access, we also remove the Wiki Maintainer, eliminating persistent knowledge accumulation across iterations. The bottom row",
    "why_used": "支撐消融實驗四種設定的平均分數對照,是全文最關鍵的證據。",
    "agent_match_hint": "表格,四列分別對應 Inference Agent 與 Skill Proposer 是否有 wiki 存取權的四種組合,欄為五個任務平均分數。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Figure 3 | Case study of Wiki-guided skill evolution on ALFWorld (Qwen-3.6-27B). The persistent Wiki Layer compiles cross-iteration patterns, an audit trail of past proposal diffs and acceptance decisions, and chronological history. Informed by the rejection of the skill proposal at Iteration 0, the proposer synthesizes the accepted skill update at Iteration 1, and later refines it with new pattern evidence. File contents are simplified for clarity.",
    "why_used": "具體示範一個 skill 如何跨迭代被 wiki 累積的證據逐步塑造出來。",
    "agent_match_hint": "時間軸/流程示意圖,顯示多輪迭代中 wiki pattern 頁面與 skill 提案的互動過程,包含被拒絕與被接受的提案。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "Table 7 | Comparison of optimizer API call complexity per evolution iteration across self- improving agent frameworks. 𝑁train = |Dtrain| denotes the number of training tasks, 𝐵denotes the batch size, 𝑇ReAct denotes the number of interactive ReAct reasoning turns used by the Skill Proposer agent in WikiSkill, 𝐾opt denotes the number of reflection and merging calls per step in SkillOpt, and 𝑐 denotes the reduction-tree branching factor in Trace2Skill. WikiSkill uses 𝐵= 𝑁train across all datasets. In full-batch mode, WikiSkill’s optimizer call count is independent of training set size 𝑁train, requiring 1 + 𝑇ReAct optimizer calls per iteration.",
    "why_used": "支撐四種框架的 optimizer API 呼叫複雜度公式對照。",
    "agent_match_hint": "表格,列出四個框架名稱、每輪迭代呼叫次數公式、以及複雜度等級。"
  }
]
```
