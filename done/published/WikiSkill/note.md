# WikiSkill 論文筆記:把 Agent 經驗編譯成持久知識,驅動 Skill 演化

> 論文:*WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution*
> 作者:Liyan Tang, Cyrus Rashtchian, Chun-Sung Ferng, Andrew Tomkins, Da-Cheng Juan, Tu Vu(Google Research / Virginia Tech)
> arXiv:2608.27454v1,2026-08-27

---

## 0. 三十秒版本

這篇論文在解決一個具體問題:讓 LLM agent 自動演化 skill(可重複使用的技能文件)的既有方法,每一輪迭代都要重新從原始執行紀錄裡分析失敗原因,過去累積下來的知識散落在「一次次的優化紀錄」裡,沒有被當成一個獨立、持續增厚的知識庫來維護。WikiSkill 的解法,是在「原始執行紀錄」跟「最終的 skill 文件」之間插入一層**不會被回滾的持久知識層(wiki)**,讓每一輪的 skill 修改都能站在累積證據上做判斷,而不是每次從零分析。

**做得最紮實的地方**:論文有一組乾淨的消融實驗(見第 5 節、Table 3),獨立量出「給提案者一個持久知識層」這件事本身,帶來 +15 個百分點的效果(48.7% → 63.7%,Gemini-3.5-Flash 五個 benchmark 平均)。這是整篇論文裡最有說服力的證據。

**沒有處理乾淨的地方**:論文最核心的論點——「結構化整理過的知識」勝過「像其他方法那樣的扁平歷史紀錄列表」——並沒有被這組消融實驗直接驗證。消融實驗比的是「有結構化知識」vs「完全沒有知識」,不是「結構化知識」vs「扁平列表知識」。跟其他 baseline 方法的整體比較(Table 1)雖然 WikiSkill 全面領先,但這個比較混雜了另一個變因:WikiSkill 的 Skill Proposer 是多輪 ReAct agent(可動態探索 10-20 輪),而其他方法多半是單次或固定流程的呼叫,這個探索預算的差異沒有被排除。

**一句話判斷**:如果你在做 agent skill 或 memory 系統,這篇論文「三層架構 + gating + 永不重置的知識庫」這個設計模式值得直接參考;但不要把它當成演算法突破——核心洞察(把經驗編譯成持久知識)是作者自己承認借用 Karpathy 的一篇 gist,這篇論文做的是紮實的系統化驗證,不是全新的想法。

---

## 1. 索引:這份筆記要解決的具體困惑

這幾個問題是讀這篇論文時最容易卡住、也最值得記住的地方,可以直接跳過去看:

- **[Q1]** 三層架構(Raw / Wiki / Skill)的讀寫規則到底是什麼?哪一層可以刪除內容、哪一層只能新增? → 見 3.3
- **[Q2]** 負責整理知識的 Wiki Maintainer,實際上是怎麼被 prompt 的? → 見 3.4
- **[Q3]** 為什麼系統要跑過整個訓練集,但分析知識的時候卻只精讀其中一小部分 trace? → 見 3.5
- **[Q4]** 為什麼模型越大,skill evolution 帶來的效益反而越大?直覺上不是應該越強的模型越不需要輔助嗎? → 見 4.2
- **[Q5]** 論文提到「更強的來源模型不等於更好的 skill」,甚至觀察到小模型演化出的 skill 可以讓大模型變更好——論文有解釋這個現象嗎? → 見 4.4
- **[Q6]** 這篇論文真正定義的問題是什麼?過去的方法(例如 EvoSkill)不是也有跨迭代的記憶機制嗎,WikiSkill 到底多做了什麼? → 見 5.1

---

## 2. 這篇論文想解決的問題

Agent skill 是一種輕量級的知識封裝方式:把特定領域的操作步驟、程序性知識,打包成一個獨立的檔案目錄(核心是一份 `SKILL.md`),讓 agent 在執行任務時可以讀取、套用,而不需要重新訓練模型參數。手動寫這些 skill 很花人力,因此最近一批研究開始讓 agent **自動演化**skill:讓 agent 先跑一批訓練任務,分析成功與失敗的執行軌跡,再根據這些軌跡修改 skill 內容,如此反覆迭代。

這批既有方法(EvoSkill、Trace2Skill、SkillOpt 是論文拿來比較的三個代表)都遵循同一套流程:**跑任務 → 分析 trace → 修改 skill → 驗證後決定是否採用**。它們也都有某種形式的「記憶」,例如 EvoSkill 會保留一份跨迭代不清空的「過去提案與評估結果」清單。但論文指出一個共同的弱點:這些記憶都是附屬在「skill 修改紀錄」本身上面的**扁平清單**,沒有被當成一個獨立、會持續整理、隨時間增厚的知識表示法來維護。

論文的出發點,是受到 Andrej Karpathy 提出的「LLM Wiki」概念啟發(把 agent 的經驗持續編譯成一個會複利累積的知識庫),提出的問題是:**能不能把 agent 的經驗,用同樣的方式編譯成一個持久知識層,來支撐長期的 skill 演化?**

---

## 3. 方法:WikiSkill 怎麼運作

### 3.1 三層架構

WikiSkill 把 agent 的工作空間切成三層,對應原文 **Figure 2**(標題:*Overview of the WikiSkill framework*。原文 caption:「The agent workspace is structured into three layers: immutable execution traces (Raw Layer), a persistent knowledge base that compounds across iterations (Wiki Layer), and active procedural instructions (Skills Layer).」):

```
Skill Layer (skills/)   -- 可逆、有條件更新    -- 實際會被注入 prompt 的技能
Wiki Layer  (wiki/)     -- 持續累積、絕不重置   -- 整理過的結構化知識
Raw Layer   (raw/)      -- 永久保存、只能新增   -- 原始執行紀錄
```

- **Raw Layer**:存每次訓練任務跑完的完整執行軌跡(推理過程、工具呼叫、工具回傳結果、最終答案)。
- **Wiki Layer**:這是這篇論文新加的中間層。裡面有三種檔案:`patterns/` 底下一堆 markdown 檔,一個檔案對應一個具體的失敗模式或成功策略;`logs.md` 按時間順序記錄每次迭代做了什麼;`skill-impact.md` 記錄每次提案的內容、驗證分數、被接受或拒絕的結果。
- **Skill Layer**:真正會被注入 agent prompt、實際發揮作用的技能文件。每個 skill 資料夾有兩個檔案:`SKILL.md`(技能內容本身)跟 `PURPOSE.md`(記錄這個技能是被 wiki 裡哪些 pattern 啟發、修改過的動機)。

### 3.2 一次迭代的完整流程

三層架構是靜態的空間結構,實際運作靠四個角色依序互動一次迭代:

```
[1] Inference Agent
    用上一輪的 skill 集合跑訓練任務
    -> 寫入 raw/ (新增,不可修改舊紀錄;不能存取 wiki)
        |
        v
[2] Wiki Maintainer  (單次 LLM 呼叫)
    抽樣少量 trace,做 root-cause 分析
    -> 更新 wiki/patterns/*.md、index.md、logs.md
        |
        v
[3] Skill Proposer  (多輪 ReAct agent)
    讀 wiki index -> skill-impact.md -> 相關 pattern -> 原始 trace
    -> 提出一個 skill 的 create 或 patch(一次只改一個)
        |
        v
[4] Gating & Rollback
    在驗證集上測試候選 skill
    -> 分數進步就採用新 skill,沒進步就整組退回上一版
    -> 不論結果,都把提案內容、diff、分數、accept/reject 寫進 skill-impact.md
        |
        v
    回到 [1],進入下一輪迭代
```

一個關鍵設計:**Inference Agent 在跑訓練任務時不能存取 wiki**。這個限制在第 5 節的消融實驗裡被驗證是必要的——如果讓它偷看 wiki,反而會讓最終 skill 品質變差。

---

### 3.3 [Q1] 三層架構的讀寫規則,到底哪一層可以刪、可以改、只能加?

這是討論方法論時最容易產生錯誤直覺的地方,精確對照如下:

| 層 | 常見的錯誤假設 | 論文實際的規則 |
|---|---|---|
| Skill Layer | 可以新增或刪除 | **沒有「刪除」這個操作**。Skill Proposer 的輸出格式只有 `create`(新建)、`patch`(修改既有)、`no_action` 三種,沒有 delete。你以為的「刪除」其實是 Gating & Rollback 造成的**整組版本回退**——如果新提案沒通過驗證,系統直接把整個 skill 集合退回上一輪版本,不是針對單一 skill 做刪除動作 |
| Wiki Layer | 只能新增 | **不完全對**。Wiki Maintainer 對既有 pattern 頁面的 patch 操作有三種:`append`(在檔案尾端加)、`replace`(找到指定文字並替換)、`insert_after`(在指定文字後插入)。所以既有內容可以被修正、覆寫,不是只能疊加。「永不重置」講的是**整個 wiki 狀態不會因為某次 skill 提案被拒絕而回滾**,不是「每個檔案只能加不能改」 |
| Raw Layer | 只能 read | **不太精確**。Raw Layer 每輪迭代都會新增這一輪的執行紀錄,持續增長。「immutable」指的是**已經寫入的紀錄不會被修改或覆蓋**,新資料只能追加。Wiki Maintainer 和 Skill Proposer 對它的存取方式確實是唯讀,但這是「使用方式唯讀」,不是這層本身唯讀 |

補充一點論文自己在 Limitations 承認的缺口:wiki 目前**沒有自動清理機制**,隨著迭代數增加會持續膨脹,論文明講這是留給未來研究的問題。

---

### 3.4 [Q2] Wiki Maintainer 實際上是怎麼被 prompt 的?

論文附錄 E.2 提供了完整的 system prompt,結構重點如下:

**角色定義**:要求它對執行紀錄做深度根因分析(root cause analysis),不能只看表面症狀。

**輸入**:這輪迭代的原始執行 trace + 目前的 wiki context(index、log、pattern 頁面)。

**輸出格式**(固定 JSON,四個欄位):
- `create_patterns`:新建的 pattern(給完整內容)
- `update_patterns`:對既有 pattern 的 patch(用 append / replace / insert_after 三種操作)
- `update_index`:**每次都要求給出完整更新後的 index 內容**,不是差異
- `append_log`:這輪迭代的摘要

**值得特別注意的一段指示**,原文標注為 CRITICAL:

> index.md 的條目是 wiki 裡**最重要**的部分,因為它們決定了 inference agent 會不會去讀完整的 pattern 頁面……描述必須具體到讓 agent 不用讀完整頁面就能判斷相關性,要同時包含問題、根因、跟解法。

這透露一個工程細節:pattern 頁面寫得再好,如果 index 摘要品質差,後面的 agent 根本不會點進去看——所以 prompt 特別把「index 品質」的重要性拉到跟 pattern 內容本身同等地位。

---

### 3.5 [Q3] 為什麼 batch size 設成全資料集,分析階段卻只讀一小部分 trace?

這個問題要拆成兩層看,分開之後就清楚了:

**第一層:Inference Agent 每輪一定跑全部訓練集,這跟 batch size 無關。** Algorithm 1(附錄 A.1)寫得很明確,每輪迭代都對整個 `D_train` 跑一次 rollout,不受 batch size 影響。

**第二層:batch size 控制的是「分析+提案」這個步驟要分幾次做。** 附錄 D 定義的 batch size B,講的是:訓練集全部跑完、產生一批 trace 之後,要分幾次交給 Wiki Maintainer + Skill Proposer 去分析、產出提案。如果 B < N_train(EvoSkill、SkillOpt 用的方式),訓練集會被切成多個小批次,每個小批次各自觸發一輪完整的分析流程;WikiSkill 把 B 設成等於 N_train(全批次),所以每輪迭代**只做一次**分析。

**廣度跟深度是分開處理的兩個旋鈕**:

- 廣度(看到全部訓練任務的結果全貌)→ 靠全批次 rollout + Skill Proposer 一開始拿到的「全部任務 pass/fail 摘要」取得,目的是避免只看到部分資料而誤判某個錯誤模式的普遍性,同時讓一次迭代只需要觸發一次分析(降低呼叫成本)
- 深度(逐字精讀某幾筆 trace 的細節)→ 靠有限抽樣控制成本:Wiki Maintainer 每輪固定抽樣最多 8 筆(5 敗 + 3 成,見附錄 C),每筆截斷到 15,000 字元;Skill Proposer 不受這 8 筆限制,可以自己動態挑選整個訓練集的 trace 來精讀,規則只要求至少讀滿 4 筆,沒有上限

兩者背後的共同理由都是 context window 限制,但解法不同:Wiki Maintainer 是單次呼叫、固定抽樣;Skill Proposer 是多輪 ReAct、動態按需讀取。

---

## 4. 實驗結果

實驗涵蓋 5 個模型(Qwen-3.5-4B/9B、Qwen-3.6-27B、Gemma-4-31B、Gemini-3.5-Flash)× 5 個任務,每個組合跑 3 次完整演化流程取平均,用 paired bootstrap 檢定(p<0.05)判斷差異是否顯著。5 個任務簡介:

| 任務 | 內容 |
|---|---|
| LiveMath | 近期數學競賽選擇題,測複雜數學推理 |
| SealQA | 學術性事實問答,需要用 web search 找答案 |
| SpreadSheet | 試算表操作,寫 Python 程式碼做表格轉換 |
| OfficeQA | 長文件問答(財政部歷史公報),需跨長文本整合證據 |
| ALFWorld | 互動式具身任務模擬器,做多步驟家務任務 |

### 4.1 跨模型/跨任務主結果

對應 **Table 1**(標題:*Method comparison across inference models and test sets*。原文 caption 說明:每個模型區塊分別評測無 skill、以及用 EvoSkill/Trace2Skill/SkillOpt/WikiSkill 演化出的 skill;所有方法都從空 skill 集合開始,取三次獨立演化流程的平均測試表現)。

核心數字:WikiSkill 在全部 5 個模型上平均分數都最高。跟每個模型「表現最好的競爭對手方法」相比,分別多贏 3.3、5.1、10.0、5.8、12.0 個百分點(依序對應 4B、9B、27B、Gemma-4-31B、Gemini-3.5-Flash)。幾個較顯眼的單點例子:Gemini-3.5-Flash 在 LiveMath 上從 33.0% 拉到 72.6%,在 SpreadSheet 上從 50.5% 拉到 76.6%;Qwen-3.6-27B 在 ALFWorld 上從 52.8% 拉到 77.6%。

論文特別強調的是**穩定性**,不只是峰值表現:其他方法在部分設定上會明顯**退步**,不是單純進步較少——例如 EvoSkill 讓 Qwen-9B 在 LiveMath 上大幅進步(28.2%→58.1%),卻讓 Gemma-4-31B 在同一任務上退步(33.9%→29.8%);SkillOpt 讓 Gemini-3.5-Flash 在 SealQA 上退步(29.4%→28.2%)。WikiSkill 沒有出現這種時好時壞的情況。

> 資料清理提醒:Gemini-3.5-Flash 在 ALFWorld 上所有方法(含無 skill)分數都一樣(85.9%),原因是它在演化開始前驗證集就已經拿到 100% 分數,觸發了 Algorithm 1 裡的提早終止機制,根本沒真的跑演化流程。這也是為什麼 Table 2 裡它在 ALFWorld 那欄標的是「−」。

---

### 4.2 [Q4] 為什麼模型越大,skill evolution 帶來的效益反而越大?

論文摘要用「skill evolution **complements**(互補)model scaling」來描述這個發現——模型越大,skill evolution 帶來的加分反而越多。

在 Qwen 系列裡看得最清楚(同一家族只有參數量不同,比較乾淨):WikiSkill 帶來的平均進步幅度隨規模遞增——4B 是 +12.3 分,9B 是 +17.5 分,27B 是 +23.9 分。在 SpreadSheet 這個任務上尤其明顯:三個模型分別進步 +6.5、+9.3、+40.9 分。

另一個更直覺的說法:小模型加上好的 skill,可以反過來打贏沒有 skill 的大模型。Qwen-3.5-9B 加上 WikiSkill,平均準確率拿到 47.4%,超過 Qwen-3.6-27B 完全沒用 skill 時的 39.4%。

**論文自己的解讀**(這是論文原文的論述,不是筆者的推論):模型能力跟演化出的程序性知識,提供的是**互補的效能來源**——越強的模型,越能有效地開發跟執行更精細的 skill,所以從 skill evolution 中獲益更多;而有效的 skill,則可以讓小模型彌補跟大模型之間的能力差距。

跨資料集的效益也不平均:Qwen-3.6-27B 在 OfficeQA 只進步 11.6 分、SealQA 進步 14.1 分,相較之下 SpreadSheet 進步 40.9 分。論文對 OfficeQA(長文件檢索型任務)的解釋是:大模型能有效運用演化出的搜尋流程導覽長文件,但小模型(如 Qwen-3.5-4B)沒辦法執行這種多步驟搜尋流程,反而退回預設閱讀行為,導致些微退步——這點跟下一節的跨模型遷移結果互相呼應。

---

### 4.3 跨模型 skill 遷移

對應 **Table 2**(標題:*Cross-model skill transfer results*。原文 caption:用無 skill、以及 Qwen-3.5-4B / Qwen-3.6-27B / Gemini-3.5-Flash 三個來源模型演化出的 skill,分別評測各個推論模型;標示灰底的列是「自己演化自己用」的情況)。這裡在測:用模型 A 演化出來的 skill,能不能直接拿給模型 B 用?

**發現一:遷移過去的 skill,常常比模型自己演化出的 skill 還好用。** 例如 Qwen-3.6-27B 演化出的 skill,拿給 Qwen-3.5-9B 在 SpreadSheet 上用,拿到 50.5%——比它自己沒用 skill 的 24.3% 高很多,甚至比它**自己演化的 skill**(33.6%)還高。

**發現二:能不能遷移,取決於 skill 裡包的是通用程序,還是模型專屬的權宜之計。** LiveMath 的 skill 遷移得特別好(Qwen-3.5-4B、Qwen-3.6-27B 的 skill 都能把 Gemini-3.5-Flash 從 33.0% 拉到 67-74% 區間)。但 SpreadSheet 出現明顯負遷移:Qwen-3.5-4B 的 skill 拿給 Gemini-3.5-Flash,分數從 50.5% **掉到** 18.1%,同樣情境換成 Qwen-3.6-27B 的 skill 反而拉到 63.4%。論文的錯誤分析指出兩個原因:(1)小模型演化出的 skill 包了很多低階權宜之計(例如單行 Python 指令、字串轉換規則),幫小模型避開執行失敗,但反而限制了強模型使用更完整的端到端腳本;(2)破碎化的診斷流程會製造多餘工具呼叫,可能在任務完成前就耗光強模型的互動預算。

**發現三:即使 skill 來源相同,不同接收模型「消化」skill 的能力也不一樣。** OfficeQA 上有個反直覺例子:Qwen-3.5-4B 自己演化的 skill,拿給自己用反而**退步**(30.2%→28.5%),但同一份 skill 拿給 Qwen-3.6-27B 用卻進步(42.1%→52.9%)——小模型「發現」了有用的知識,卻沒有能力好好「執行」自己發現的東西。

---

### 4.4 [Q5] 「更強的來源模型不等於更好的 skill」,論文有解釋嗎?

論文**只針對 SpreadSheet 的負遷移案例做了根因分析**(就是上一節發現二講的「低階權宜之計 + 破碎化工具呼叫」兩點),但那個分析對象是「小模型的 skill 讓大模型**變差**」。

論文**沒有**針對另一種更反直覺的現象給出解釋:小模型(Qwen-3.5-4B)演化出的 skill,拿給 Gemma-4-31B 用之後在 LiveMath、ALFWorld 上都讓它**變好**(LiveMath 拉到 73.1%、ALFWorld 拉到 66.9%)——這件事論文只報告了數字,沒有進一步的根因分析。

> 這是一個值得記住的閱讀提醒:論文給了很多「哪個方向遷移得好/不好」的**現象描述**,但因果解釋只在 SpreadSheet 這一個案例上做了,而且做的也只是定性的錯誤分析,不是系統性驗證。其他違反直覺的遷移結果(例如這裡的小模型→大模型正遷移),就只停在報告數字,沒有進一步深挖。

---

### 4.5 論文的框架性結論:發掘知識 vs 執行知識,是兩種可拆分的能力

把上面三個發現合起來看,論文提出一個值得記住的框架性論點:**自我演化(self-evolution)這件事,其實混雜了兩種不同的能力——「從經驗中發掘出有用的程序性知識」跟「在推論時有效執行這些知識」——這兩者是可以被拆開來看待的獨立能力,不是同一件事。**

這個視角比論文本身更通用:未來評估任何「self-improving agent」系統時,都可以先問一句——這個系統進步了,是因為它學到更好的東西,還是因為它更會照著指示做?

---

## 5. Ablation:wiki 到底在哪裡起作用

對應 **Table 3**(標題:*Ablation study on WikiSkill using Gemini-3.5-Flash*。原文 caption:在四種設定下比較表現,分別調整 Inference Agent 跟 Skill Proposer 是否有 wiki 存取權;當 Skill Proposer 沒有 wiki 存取權時,Wiki Maintainer 這個角色也一併移除,消除跨迭代的知識累積;最後一列是 WikiSkill 的預設設定)。這是整篇論文裡實驗設計做得最乾淨的一組,只用 Gemini-3.5-Flash 一個模型做,對應 §5.1。

四種設定與五個 benchmark 平均分數:

| Inference Agent 有 Wiki? | Skill Proposer 有 Wiki? | 平均分數 | 備註 |
|---|---|---|---|
| — | — | 40.4 | 無 skill 基準線 |
| 有 | 無 | 45.3 | Wiki Maintainer 已移除 |
| 無 | 無 | 48.7 | Wiki Maintainer 已移除 |
| 有 | 有 | 60.9 | 完整配置 |
| 無 | 有 | 63.7 | **WikiSkill 預設配置** |

**結論一:讓 Skill Proposer 存取持久 wiki,效果非常顯著。** 在 Inference Agent 不能碰 wiki 的前提下,單純把 Skill Proposer 的 wiki 存取權打開,平均分數從 48.7% 跳到 63.7%,**+15.0 個百分點**——這是整篇論文裡最大幅度的單一變因效果。細看子項:LiveMath 從 51.3%→72.6%,SpreadSheet 從 49.9%→76.6%。論文的解釋:沒有跨迭代累積的知識,Skill Proposer 很難處理複雜、需要多次迭代才能收斂的失敗模式。

**結論二:讓 Inference Agent(訓練時)也碰 wiki,反而讓最終 skill 品質變差。** 在 Skill Proposer 已經有 wiki 存取權的前提下,如果連 Inference Agent 訓練時也讓它看 wiki,平均分數從 63.7% 掉到 60.9%,LiveMath 掉最多(72.6%→64.8%)。論文給的解釋明確標注是一個假設(原文用字是「we hypothesize」,沒有進一步驗證):當 Inference Agent 訓練時同時能看到 skill 跟 wiki,它可能會直接從 wiki 裡找答案來解題,而不是靠 skill 本身解題;這樣一來,產生出來的訓練 trace 就會失真——因為 agent 表現好不是因為 skill 好用,是因為 wiki 幫了忙,這會讓 Skill Proposer 拿到的訓練訊號失去代表性。這也解釋了為什麼架構設計裡(見 3.2)刻意規定 Inference Agent 訓練時不能看 wiki。

---

### 5.1 [Q6] 這篇論文真正定義的問題是什麼?過去的方法不是也有跨迭代記憶嗎?

這是理解這篇論文動機時最容易卡住的地方。表面上看,EvoSkill 也維護了一份「跨迭代不清空的提案歷史與評估結果」,那 WikiSkill 到底多做了什麼?

答案不是「有沒有記憶」,而是**記憶的形式**:

| | Skill(含 EvoSkill 的歷史列表) | WikiSkill 的 wiki |
|---|---|---|
| 儲存形式 | 扁平列表:一筆一筆的「提案內容+驗證分數+接受/拒絕」 | 結構化、按主題組織的知識頁面(patterns/),每頁對應一個具體的失敗模式或成功策略 |
| 有沒有獨立的整理步驟 | 沒有——proposer 自己看歷史列表+這次的原始 trace,現場消化 | 有專門的 Wiki Maintainer 角色,職責就是做 root-cause 分析、把原始 trace 提煉合併進既有 pattern 頁面 |
| 證據累積方式 | 每次的失敗案例基本上獨立存在 | 同一個 pattern 頁面會跨迭代持續疊加證據(例如 Figure 3 案例裡:「Iter 0: train 00,02 \| Iter 1: train 01 \| Iter 2-4: train 02 persists」) |
| 能不能查找相關知識 | 沒有索引機制,只能整份歷史從頭看 | 有 `index.md`,每個 pattern 一行摘要(問題+根因+解法),讓 proposer 能快速判斷哪些知識相關 |

可以把這個核心論點濃縮成一句話:**知識需要被主動整理、消化、累積證據,而不只是被動地按時間堆疊。**

> **評析(這是筆者對實驗設計的評估,不是論文的主張)**:Table 3 的消融實驗,拿掉 wiki 的那組設定是「完全移除 Wiki Maintainer」,也就是說,它測的是「有結構化知識」vs「完全沒有跨迭代知識」,並**沒有**設計一組對照組去比較「結構化 wiki」vs「像 EvoSkill 那樣的扁平歷史列表」。換句話說,Table 3 證明了「有結構化知識 > 完全沒有知識」(+15%),但**沒有**直接證明這篇論文最想主張的那件事——「結構化知識 > 扁平列表知識」。Table 1 雖然有跟 EvoSkill 整體比較分數,但那個比較混雜了 ReAct 多輪工具呼叫探索預算的差異(WikiSkill 的 Skill Proposer 可以動態讀 10-20 輪,EvoSkill 沒有這種機制),沒辦法乾淨歸因到「wiki 的結構化程度」這個變因上。這是這篇論文論證上最大的一個缺口。

---

## 6. 案例:一個 skill 怎麼被 wiki 一步步塑造出來

對應 **Figure 3**(標題:*Case study of Wiki-guided skill evolution on ALFWorld (Qwen-3.6-27B)*。原文 caption:「The persistent Wiki Layer compiles cross-iteration patterns, an audit trail of past proposal diffs and acceptance decisions, and chronological history. Informed by the rejection of the skill proposal at Iteration 0, the proposer synthesizes the accepted skill update at Iteration 1, and later refines it with new pattern evidence.」)。這個具體案例示範了 3.4 節提到的「回溯機制」實際長什麼樣。

時間軸(論文簡化過內容方便呈現):

```
Iteration 0
  Wiki Maintainer: 建立 pattern -> take-examine-move-loop.md
    描述:agent 拿起物品、檢查、放回原位、重複
    證據:train 00, 02
  Skill Proposer: 提案 create "goal-directed-action"
    -> 驗證分數 0.72,沒超過 baseline,REJECTED
    -> skill-impact.md 記下完整 diff + 拒絕結果
        |
        v
Iteration 1
  Wiki Maintainer: 發現同樣錯誤又出現(train 01, 02)+ 新變體(use-examine loop, train 30, 31)
    -> 把新證據 append 進既有 pattern 頁面
  Skill Proposer: 讀到 Iteration 0 的拒絕紀錄
    -> 提案 create "break-repetition-loop"(更具體、更聚焦動作模式)
    -> 驗證分數 0.78,ACCEPTED
        |
        v
Iteration 2-3(簡化未展開)
  Wiki Maintainer: 建立新 pattern -> multi-operation-loop.md
    描述:agent 對同一物品重複做操作,卻不檢查任務是否已完成
        |
        v
Iteration 4
  Skill Proposer: 讀到新 pattern 證據
    -> 提案 update "break-repetition-loop"(patch,不是重建)
    -> ACCEPTED
```

最終 skill 內容節錄:
```
Trigger: 當 agent 即將重複某個動作時套用這個 skill

Rule: 絕不要把物品放回原本拿取的位置
  失敗案例:take clock from desk -> examine -> move clock to desk
  成功案例:take clock -> go to shelf -> move clock to shelf

Rule: 每種操作類型,對同一物品只做一次
Anti-Pattern: Take -> Operate -> Move -> Take (無限循環)
  修正:完成 take -> operate -> move 一次之後,不要重複
```

對應的 `PURPOSE.md`:「建立為 break-repetition-loop。前一次嘗試 goal-directed-action 因為太抽象而被拒絕。這一版更精簡,用的是具體的動作模式。」——光看這一行就能直接知道這版 skill 為什麼長這樣,不用回頭爬原始 trace 自己猜。而「每種操作類型只做一次」這條規則能在 Iteration 4 被加進去,正是因為對應的 pattern 頁面持續累積了跨迭代證據(Iter 2 出現、Iter 3-4 仍然存在)——這是第 5 節消融實驗「Skill Proposer 有 wiki 存取權帶來 +15 分」的一個具體實例。

---

## 7. 工程成本:Optimizer API 呼叫複雜度

對應附錄 D.2 與 **Table 7**(標題:*Comparison of optimizer API call complexity per evolution iteration across self-improving agent frameworks*。原文 caption 定義符號:N_train 為訓練任務數、B 為批次大小、T_ReAct 為 Skill Proposer 的 ReAct 推理輪數、K_opt 為 SkillOpt 每步的反思+合併呼叫次數、c 為 Trace2Skill 階層式合併的分支因子)。這裡算的是「每輪迭代,分析+提案這個步驟本身要打幾次 LLM API」,不含 Inference Agent 本身跑訓練任務的呼叫。

四家方法的每輪迭代呼叫次數公式:

```
WikiSkill:   C = (1 + T_ReAct) * (N_train / B)
EvoSkill:    C = 2 * N_train / B
SkillOpt:    C = K_opt * N_train / B
Trace2Skill: C ~= N_train + (1 + 1/(c-1)) * (N_train / B) + 1
```

論文實驗裡 WikiSkill 全部資料集都設 **B = N_train**(全批次),所以 `N_train/B` 恆等於 1,公式化簡成:

```
C_WikiSkill = 1 + T_ReAct   (只跟 ReAct 輪數有關,跟訓練集大小完全無關)
```

其中 T_ReAct 論文實驗裡大約落在 10 到 20 之間。這代表:如果訓練集從 80 筆變成 800 筆,WikiSkill 每輪迭代的呼叫次數不變。但 EvoSkill、SkillOpt 都是批次越小、資料越多,呼叫次數線性增加(O(N_train/B));Trace2Skill 更明確——因為它規定**每一筆 trace 都要單獨分析一次**,不管怎麼調 batch size,呼叫次數下界永遠跟訓練集大小成正比(O(N_train)),是四者裡複雜度最差的。

> **工程判斷提醒**:論文自己承認這個 O(1) 有代價——「這種固定呼叫次數可能在某些資料集上帶來更高的推論成本」。每一輪 ReAct 都是一次完整的 LLM 呼叫,而且 Skill Proposer 讀的 context 通常比單筆 trace 分析要大很多。**換句話說,「呼叫次數少」不等於「總 token 成本低」**——如果每一輪 ReAct 都在讀很長的 wiki context + trace 內容,單次呼叫的 token 用量可能遠超過 EvoSkill 那種「小批次、多次但每次讀得少」的呼叫。論文完全沒有提供 token 層級的成本比較,只比較了呼叫次數這一個指標,這是評估這套框架實際部署成本時容易被忽略的陷阱。

---

## 8. 值得帶走的東西

### 8.1 這篇論文本身的貢獻

核心貢獻本身**不算原創**——作者自己在 Introduction 就講明是受 Karpathy 的 LLM Wiki 這篇 gist 啟發,把「持久累積知識」的構想套用到 skill evolution 上。這篇論文真正做的事,是把這個構想系統化實作,並在 5 個模型 × 5 個任務上紮實驗證,做出了整篇論文裡唯一算乾淨的消融實驗(+15 分)。

具體來說,論文證明了三件事,但證據強度不一:

- **證得最紮實的**:給 Skill Proposer 一個持久、不隨 gating 結果回滾的知識層,比完全沒有跨迭代知識,效果好上一大截(Table 3)
- **證得中等的**:skill evolution 帶來的效益隨模型規模遞增,以及發掘知識與執行知識是可拆分的兩種能力(Table 1、Table 2 的現象觀察,但部分現象——例如小模型 skill 讓大模型變好——沒有因果解釋)
- **沒有被證明、只是被論文自己主張的**:「結構化整理過的知識」比「像 EvoSkill 那樣的扁平歷史列表」更好——這是整篇論文論證上最大的缺口,消融實驗測的是「有 vs 完全沒有」,不是「結構化 vs 扁平」

論文誠實承認的限制(附錄 Limitations):wiki 沒有自動清理機制;驗證門檻是嚴格的「必須超越最佳分數」,排除了中性但可能有長期價值的提案;目前只驗證到單次 rollout 規模的任務,沒測過真正長時程(數百步、數小時)的場景。

### 8.2 脫離論文也成立的東西

1. **知識需要被主動消化整理,而不只是被動按時間堆疊**——這是一個可以套用到任何「累積經驗改進系統」的判斷框架,不限於 agent skill。

2. **三層分離的設計模式**(不可變的原始紀錄 / 持續累積且不回滾的結構化知識 / 可回退的可執行產出)——這是一個通用的系統設計模式,可以直接遷移到其他 agent 演化系統上,跟這篇論文本身的驗證結果是否可信無關。

3. **「發掘知識」跟「執行知識」是兩種可拆分的能力**——評估任何 self-improving agent 系統時,都可以先問:這個系統進步了,是因為它學到更好的東西,還是因為它更會照著指示做?

4. **訓練時的 actor 不該偷看 optimizer 用的知識來源**——如果訓練時的 agent 能直接從知識庫查到答案,產生的訓練訊號會失真,因為表現好壞不再反映被評估對象(這裡是 skill)本身的品質。這是一個更廣義的原則:訓練訊號的收集環境要跟被評估對象的真實能力對齊,不能被額外資訊污染。

5. **廣度用全批次摘要拿、深度用有限抽樣或動態檢索做**——當一個 agent 系統既需要全局情況的統計視野、又需要對個案做深入分析,而 context window 有限時,可以把這兩件事拆開處理,不用兩者都妥協。

6. **評估「持續演化型 optimizer」的成本時,呼叫次數的複雜度量級(O(1) vs O(N))是一個有用但不完整的指標**——呼叫次數少不等於總 token 成本低,這是容易被忽略的陷阱。

7. **做消融實驗時,對照組要精準對應到你想否定的那個具體形式,不能只對照「完全沒有」**——這篇論文最想證明的核心論點(結構化知識勝過扁平列表),恰好就是全文中唯一沒有被消融實驗直接驗證的一塊,值得引以為戒。

---

## 9. 附錄:延伸閱讀

以下是這篇論文引用、且跟核心討論直接相關的文獻,列出來方便之後追蹤原始出處:

- Karpathy, A. *LLM Wiki*. GitHub Gist, 2026. https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f —— 本篇論文核心構想的直接靈感來源
- Alzubi et al. *EvoSkill: Automated skill discovery for multi-agent systems*. arXiv:2603.02766, 2026 —— 本篇論文對比討論最多的 baseline
- Ni et al. *Trace2Skill: Distill trajectory-local lessons into transferable agent skills*. arXiv:2603.25158, 2026
- Yang et al. *SkillOpt: Executive strategy for self-evolving agent skills*. arXiv:2605.23904, 2026
- Yao et al. *ReAct: Synergizing reasoning and acting in language models*. ICLR 2023 —— Skill Proposer 使用的多輪推理機制的原始出處