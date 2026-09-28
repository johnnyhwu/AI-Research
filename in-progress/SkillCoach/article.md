# 答案對了，不代表技能學會了：SkillCoach 怎麼評估與訓練 Agent 的技能使用能力

## 前言

企業把大量操作手冊包裝成一份份 SKILL.md，讓 agent 系統照著標準作業流程做事，已經是常見的部署方式。但技能庫一大，麻煩就跟著來：agent 可能選錯技能、跳過關鍵步驟、順序做亂、提交前也不檢查——問題是，就算流程一團亂，最後答案有時候還是對的。只看「verifier 有沒有通過」，完全看不出這種差別。

這篇論文提出 SkillCoach，把「技能用得好不好」拆成四個可以分別打分的維度，再設計一套機制讓評分規則能靠真實執行資料自動修正、演化。這套規則後來被拿來做兩件事：診斷 agent 哪裡出問題、篩選訓練資料做 SFT。文章會先講清楚問題出在哪、SkillCoach 怎麼把「過程」變成可以量化的東西，再帶過關鍵實驗結果，最後留一段獨立於論文本身也站得住腳的心得——這幾點即使你完全不關心 SkillCoach 這個系統，日後在設計任何用 LLM 當 judge 的評分機制時，多半都用得上。

---

## 一、為什麼「答案對」不代表「技能用對了」

企業裡的 agent 系統常見這樣的情境：技能庫裡塞了一大堆 SKILL.md 文件，記錄著標準作業流程、工具呼叫方式、驗證規則。技能庫一變大，技能之間難免互相重疊——不同部門可能有各自版本的報表流程、相似的合規檢查腳本。agent 面對這種局面，容易漏看該用的技能、選錯技能、跳過關鍵步驟、順序做錯，甚至提交前根本沒檢查自己做的東西對不對。

論文用一個防洪任務的例子說明這個問題有多隱蔽：兩條執行軌跡都算出了正確的淹水天數。

- **軌跡 A**：老老實實讀了技能文件，照著規定的步驟做——先下載官方閾值資料，再計算門檻表，最後檢查結果。
- **軌跡 B**：完全沒碰技能文件，靠自己瞎猜資料、反覆試錯，運氣好蒙對了答案。

![一個防洪任務的兩條執行軌跡對照圖，左邊是照著技能文件一步步做的軌跡 A，右邊是完全沒用技能、靠反覆試錯蒙對答案的軌跡 B，兩者最終答案相同。](img-001)
*圖 1 — 兩條軌跡都通過了 verifier，但只有一條展現出可重複、可信賴的技能使用行為。（來源：原始論文）*

用 verifier 去看，這兩條軌跡的分數一模一樣。但只有軌跡 A 展現出可重複、可信賴的技能使用行為，軌跡 B 只是撞對而已。這帶來兩層麻煩：在**評估**層面，只看 pass/fail 完全看不出 A、B 的差異，也就看不出 agent 到底學會了什麼；在**訓練**層面，如果把所有「verifier 通過」的軌跡都當成好示範拿去做 SFT，等於把軌跡 B 那種亂試一通、繞過流程的行為也一起訓練進模型——後面第五節的實驗會證實，這個擔憂不是杞人憂天，它是真的會發生的事。

---

## 二、把「技能使用」拆成四個可以打分的維度

SkillCoach 給每個技能依賴任務都準備一套獨立的評分規則（rubric），評估的對象是一個交付執行環境、技能庫（同時混著任務真正需要的 gold skill 和干擾用的 distractor skill）的 agent，看它跑出來的軌跡表現如何。

![SkillCoach 整體框架示意圖，顯示任務、執行環境、技能庫作為輸入，經過觀測四個維度打分後，用來做診斷與訓練資料篩選兩件事。](img-002)
*圖 2 — SkillCoach 的整體框架：給定技能依賴任務與含有干擾項的技能庫，觀測 agent 軌跡在四個維度上的表現。（來源：原始論文）*

論文把「agentic skill-use」定義成一種軌跡層級的 meta-ability，拆成四個維度，各自有獨立公式和權重：

| 維度 | 在測什麼 | 預設權重 |
|---|---|---|
| skill_selection（技能選擇） | 有沒有選對 gold skill、有沒有誤用 distractor 技能 | 0.40 |
| skill_following（步驟遵循） | 有沒有照著技能文件規定的關鍵步驟做，不是只是提到技能名稱 | 0.30 |
| skill_composition（組合順序） | 多個技能／步驟之間的順序、中間產物有沒有正確傳遞（單一技能任務時此項不適用） | 0.20 |
| skill_reflection（結果反思） | 提交答案前有沒有明確的自我檢查行為，不等於 verifier 通過 | 0.10 |

除了這四項，還有一個**verifier**：獨立於四個維度之外的外部結果訊號，不計入加權平均。這個獨立性很重要，後面第三節、第四節都會反覆用到它。

`skill_selection` 在設計上是一道閘門：如果技能一開始就選錯，下游維度的分數會被打折。邏輯很直白——技能都選錯了，後面步驟做得再仔細也沒有意義。

### 公式怎麼寫

四條公式本質上都是加權平均的變形，其中 selection 比較特殊，用 F1 score 同時兼顧「漏選」和「濫選」；其他三項則是「規定好的事有沒有做到」，用加權平均就夠了。

**技能選擇**。令 $S_b$ 為 agent 實際選用的技能集合，$G_t$ 為該任務真正需要的 gold skill 集合。如果任務本來就需要用到 gold skill：

$$s_{sel} = \frac{2 \cdot |S_b \cap G_t|}{|S_b| + |G_t| + \epsilon}$$

如果任務本來就不需要任何技能，衡量的則是 agent 有沒有正確地「什麼都不選」：

$$s_{sel} = \mathbb{I}[S_b = \emptyset]$$

**步驟遵循**。令 $w_k$ 為第 $k$ 個步驟的權重，$c_k \in \{0, 0.5, 1\}$ 代表完成程度，$m_k \in \{0, 1\}$ 代表有沒有可見證據：

$$s_{fol} = \frac{\sum_k w_k \cdot c_k \cdot m_k}{\sum_k w_k}$$

這裡有個關鍵設計：$m_k$ 是乘法項，不是加法項。就算 agent 聲稱自己完成了某個步驟（$c_k = 1$），只要軌跡裡找不到對應的證據（$m_k = 0$），這步就直接算零分。這是防止 agent 靠嘴巴宣稱就拿到分數的機制，後面第六節會再談為什麼這個設計值得記住。

**技能組合**。令 $(u, v)$ 為一組先後依賴，$q_{uv} \in [0, 1]$ 衡量是否真的先做 $u$ 再做 $v$，而且中間產物有正確傳遞：

$$s_{comp} = \frac{\sum_{(u,v)} \beta_{uv} \cdot q_{uv}}{\sum_{(u,v)} \beta_{uv}}$$

**結果反思**。令 $c$ 為一項預期檢查，$r_c \in \{0, 0.5, 1\}$ 衡量檢查品質：

$$s_{ref} = \frac{\sum_c \rho_c \cdot r_c}{\sum_c \rho_c}$$

四項分數最後依權重加總成一個總分 $S_{meta}$，拿來做訓練資料篩選；但 verifier 永遠獨立保留，不會被這個加總分數蓋掉。

---

## 三、誰在打分？規則、LLM judge、外部 verifier 的分工

這裡有一個很容易產生的誤解，值得先講清楚：不是四個維度全都靠 LLM 打分。

| 維度 | 誰來判 | 為什麼這樣設計 |
|---|---|---|
| skill_selection | 規則為主，機械式偵測，非 LLM | 論文原文明講這一項是「rule-dominant」——用「有沒有出現讀取 SKILL.md 這種事件」來判定，避免 LLM 幻覺出「選對了」的假證據 |
| skill_following | LLM judge，但強制要求引用具體證據（event_index） | 判斷步驟有沒有真的做需要理解語意，但要求證據引用可以防止空判斷 |
| skill_composition | 同上 | 同上 |
| skill_reflection | 同上 | 同上 |
| verifier（外部結果） | 完全不是 LLM，是 code-level 的硬性檢查器 | 直接讀 benchmark 產生的結果檔案，跟 LLM 判斷完全獨立 |

訓練資料篩選的規則是：一條軌跡要同時滿足 $S_{meta} \geq 0.95$ 且 verifier 通過，才會被收進 SFT 訓練集。兩個條件缺一不可——光是過程分數高沒用，答案本身也得是對的。

---

## 四、Rubric 怎麼自我演化

### 4.1 整體迴圈

每個任務都有自己專屬的 rubric，透過反覆迴圈演化出更好的版本。流程大致是這樣：先用 SKILL.md、任務指令、oracle 解法、verifier 資訊建構出一份初始 rubric $R^0$；接著讓 agent 在真實環境跑出一批軌跡（rollout）；用目前版本的 rubric 對每條軌跡打四維度分數（judge）；再由另一個 LLM 提出一個局部修改建議（arbitration，產出一份 patch）；最後用沒被拿去提案的保留軌跡驗證這個 patch 有沒有真的變好（validation gate）。

patch 被接受，版本就升級，重複這個迴圈，最多跑六輪；被拒絕，就保留舊版，換下一輪再試——連續拒絕三次就提早停止。整個過程結束後，並不是直接拿最後一輪的版本收工，而是從「所有曾經被接受過的版本」裡，挑驗證分數最高的那個當 $R^{best}$。

![Self-Evolving Rubric Framework 的完整迴圈示意圖，顯示 rollout、judge、arbitration、validation gate 四個階段如何串接，以及接受或拒絕 patch 後的版本演進路徑。](img-004)
*圖 3 — 自我演化 rubric 的完整迴圈：從初始 rubric 出發，透過 rollout、judge、arbitration、validation gate 反覆修正。（來源：原始論文）*

每一輪的軌跡會切成兩份：十條「校準集」給 arbitration model 看，拿去提案修改；五條「驗證集」對 arbitration model 隱藏，只用來檢驗 patch 到底有沒有變好。這個切分方式跟機器學習裡常見的 train/validation split 是同一個道理，目的是防止 rubric 對少數校準軌跡過擬合。

實際跑起來的規模不算誇張：28 個任務總共跑了 94 輪演化，平均每個任務 3.36 輪，最少 3 輪、最多觸頂 6 輪。這個數字其實在說一件事——多數任務的初版 rubric 品質已經不差，只需要小修小補就能收斂，用不著大改特改。

Patch 本身也有硬性限制：不能動 `key_steps` 的定義本身、不能改 `score_weights`、不能繞過 verifier，只能修改判定標準，像是 criteria、evidence_requirements、score_rules 這類欄位。這確保每次修改都是局部的、可控的，不會演變成規則整個被重寫。

> **論文沒講清楚的地方**：這十五條軌跡（十條校準加五條驗證）具體是怎麼生成的——是同一題用不同 temperature 重跑，還是同任務家族下不同的具體實例，還是換了不同的 agent backend——論文全文沒有明確交代。下面表 1 顯示每個任務家族底下都有多個 instance，這暗示軌跡池可能包含不同題目實例，但這只是一個合理推論，不是論文明講的事實。

![SkillCoach 訓練與測試任務清單表格，依類別列出任務名稱、gold 技能數、distractor 技能數與任務實例數，並分別給出訓練與測試任務的總計。](img-009)
*表 1 — SkillCoach 的訓練與測試任務清單，Gold 代表任務所需技能、Distr. 代表干擾技能、Inst. 代表任務實例數。（來源：原始論文）*

### 4.2 Validation Gate 怎麼運作——不是「judge of judge」

這裡有另一個容易搞混的地方，直覺上很容易以為：既然要比較舊版 rubric 和候選版 rubric 誰比較好，是不是要再設計一個 LLM 去當「評審中的評審」？

實際上不是。整個流程更接近 A/B test：用**同一套 judge 機制**，套用兩個不同版本的規則，跑在**同一批驗證資料**上，再用可計算的機械指標量化兩者的差異。具體來說，五條驗證軌跡會分別用舊版 rubric 和候選版 rubric 跑同一套 judge prompt（用的是同一個 LLM），各自產出結構化的 JSON 輸出，記錄每個 key step 的完成情況、以及引用了哪個 event_index 當證據。接著程式碼（不是 LLM）對這兩份 JSON 做機械式統計比對：有幾個 key step 引用了有效證據、process 分數的方向跟 verifier 的 pass/fail 一不一致、有沒有出現「沒證據卻判完成」這種違規。這些比對算出兩個數字：$\Delta H$（hard gate 差異）跟 $\Delta Q$（soft objective 差異）。

接受一個候選版本，需要同時滿足四個條件：

1. **Hard gate $H$ 不能退步**——候選版本不能出現破壞性行為，像是沒證據卻給 credit、忽略 distractor、刪除關鍵步驟、繞過 verifier，這些都可以機械化偵測。
2. **Soft objective $Q$ 要改善超過閾值 $\epsilon = 0.2$**——$Q$ 由證據覆蓋率、證據品質、reflection 證據紮實度、process 分數與 verifier 一致性、規則精簡度這幾項組成。
3. **材料性改善**——不能只是「judge 看起來更有信心」，必須有實際變化，例如證據覆蓋率要提升超過 0.02、維度分數要提升超過 0.01 這類門檻。
4. **Patch 本身沒有結構性違規**——沒有偷改 key_steps、score_weights，或整個刪掉某個維度。

> **論文沒講清楚的地方**：$Q$ 的精確計算公式論文沒有給出，只列出它包含哪些子項；其中「evidence quality」「reflection grounding」這類子項究竟是純機械統計出來的（例如算證據引用次數），還是背後也讓 LLM 給了品質分數，論文全文沒有交代。

跟這套機制容易搞混、但其實是不同東西的，是論文 Table 2 裡一個真正的 judge-of-judge——不過那是離線的、一次性的驗證研究，不是每輪演化都會跑。拿演化完成的 $R^0$ 和 $R^{best}$ 兩個版本，找一個獨立的 LLM（Gemini 3.1 Pro）跟人工標註的 gold reference 做比對，打出以下幾項指標：

![人工標註驗證表格，列出 gold-keypoint coverage、usability、hallucination rate、filtering consistency 四項指標在演化前後的分數對照。](img-005)
*表 2 — 演化前後 rubric 品質的人工比對結果：gold-keypoint coverage 從 71.56 升到 83.70、usability 從 81.53 升到 94.33、hallucination rate 從 2.00 降到 0.00、filtering consistency 從 82.00 升到 96.00。（來源：原始論文）*

這組結果證明，自我演化之後的 rubric 品質確實變好了——但這個實驗只是拿最終結果去做一次外部驗證，跟前面講的 validation gate 是兩件不同的事，不要混為一談。

---

## 五、關鍵實驗結果

### 5.1 Rubric-filtered SFT 對比 Outcome-only SFT——全篇最重要的證據

在混有 gold 技能和 distractor 技能的設定下，訓練 Qwen3.5-4B 跟 9B 兩個模型規模，結果如下：

![SFT ablation 實驗結果表格，比較 Base、Outcome-only SFT、用 R0 篩選訓練、用 Rbest 篩選訓練四種設定下 4B 與 9B 模型的最終準確率。](img-007)
*表 3 — 用不同方式篩選訓練資料的最終效果對比（Gold + Distractors 設定，單位為準確率百分比）。（來源：原始論文）*

最值得注意的是 Outcome-only SFT 這一行：只挑 verifier 通過的軌跡去訓練，在 4B 模型上的效果是**負向**的——從 8.0 掉到 6.0。這直接驗證了第一節提出的擔憂：把 verifier 過了但過程亂七八糟的軌跡當成好示範拿去訓練，真的會把模型教壞。相對地，用未演化的初版 rubric $R^0$ 篩選，效果已經比 outcome-only 好上不少；用演化完成的 $R^{best}$ 篩選，又比 $R^0$ 更進一步——這說明 rubric 演化本身有實際的增量價值，不是白費工夫。

論文還做了拿掉某個維度篩選的 ablation，結果指向一件很具體的事：拿掉 key-step following（也就是 skill_following 這個維度）傷害最大，4B 模型從 24 掉到 10、9B 從 32 掉到 16；拿掉 composition order 也有明顯傷害；拿掉 reflection 傷害比較小但仍然看得出來。換句話說，四個維度裡，「有沒有照步驟做」是篩選訓練資料時信號量最強的一項。

> 測試集只有十個任務家族、五十個 instance，論文沒有報告這些百分點差異的信賴區間，引用這組數字時最好保留一點保守態度。

### 5.2 Distractor-boundary 分析——工程參考價值最高的部分

這一節測的是：當技能庫規模變大、干擾項變多，模型還能不能選對技能。

![技能庫規模擴大分析圖，左半部顯示不同模型在干擾項數量增加時 F1 分數的下滑曲線與 degradation/collapse 邊界估計，右半部顯示三種干擾項類型下，幾個模型 F1 分數的對照長條圖與正確決策比例分析。](img-008)
*圖 4 — 技能庫規模擴大下的失效邊界分析，以及不同干擾項語意相似度對選技能準確率的影響。（來源：原始論文）*

實驗把失效分成兩種邊界，而且這兩種邊界用的是同一套測試機制，只是技能庫規模不一樣——不是「一次塞給模型」對「搜尋」這種兩種不同測法。模型透過一個類似瀏覽器的多輪互動介面去逐步探索技能庫：`list` 列出候選、`search` 搜尋、`read` 讀取內容、`final` 輸出選定的技能或直接放棄。這個設計刻意把「技能選擇」這個能力單獨抽出來測，不跟工具呼叫失敗、環境錯誤這些雜訊混在一起。

> 論文沒講清楚 `search` 動作底層是關鍵字搜尋還是語意（embedding）檢索。如果是後者，代表模型在探索過程中其實有拿到輔助工具幫忙縮小範圍，這對「模型自己判斷力有多強」這個解讀會打一些折扣——這是我的推論，不是論文明講的事實。

**Degradation boundary**（F1 第一次掉超過 0.10 而且回不去了）跟模型能力高度相關：Gemini 3.1 Pro 大約在 45 到 46 個干擾項就開始退化，GPT-5.5 大約在 55 到 56 個，Opus 4.7 可以撐到 194 到 195 個才開始掉。**Collapse boundary**（80% 樣本連一個 gold skill 都選不到）的差距拉得更開：DeepSeek V4 Flash 在 6,400 到 6,500 個干擾項就崩潰，Kimi K2.6 撐到兩萬左右，Gemini 3.1 Pro 撐到三萬五千左右；GPT-5.5 跟 Opus 4.7 兩個測到五萬個干擾項都還沒崩潰。

比起數字本身，圖 4 子圖 (b) 的發現在實務上更有參考價值：干擾項的**語意相似度**比**數量**更致命。固定五十個干擾項，拿「隨機無關」跟「高相似度」兩種類型比較：

| 模型 | 隨機無關 | 高相似度 |
|---|---|---|
| GPT-5.5 | 0.84 | 0.59 |
| Opus 4.7 | 0.87 | 0.71 |
| DeepSeek V4 Flash | 0.70 | 0.46 |

三個模型的 F1 分數全部大幅下滑。最危險的干擾項從來不是明顯無關的東西，而是「長得很像但實際用不上」的技能——例如同一類報表流程的不同版本、不同部門的相似合規檢查腳本。

---

## 六、值得帶走的東西

### 這篇論文本身的貢獻（時效性較短）

這篇論文自己在 Related Work 也承認，「過程監督優於結果監督」這個原則不是它發明的，在 RLHF、數學推理 process reward model 的文獻裡早就是成熟共識。它真正的貢獻集中在兩塊：SkillCoach 這套 rubric 自動演化的具體工程機制(validation gate 的四個接受條件、校準／驗證集的切分方式)，以及在論文自己選定的 18 加 10 個任務家族上，rubric-filtered SFT 優於 outcome-only SFT 的具體數字。樣本量不大，這些百分點數字不必照單全收，但方向性的結論仍有參考價值。

### 脫離這篇論文也成立的通用觀念

這幾點才是真正耐久的收穫——就算你完全不關心 SkillCoach 這個具體系統，以下觀念在設計其他評分機制時大概率也用得上。

**「過程監督比結果監督更適合拿來篩訓練資料」這個原則本身不是這篇論文的發明**，讀論文時要有能力分辨「這是這篇獨創的」還是「這是站在已知結論上的具體應用」。SkillCoach 的價值在於把這個已知原則自動化、工程化，並且綁定到「企業技能庫」這個具體場景。

**驗證證據的乘法設計是一個可以遷移的 pattern**。判斷「某件事有沒有完成」時，「agent 聲稱完成」和「軌跡裡有可見證據支持完成」應該用乘法而不是加法結合——第二節提到的 $c_k \cdot m_k$ 就是這個道理，只要有一項是零，分數就直接歸零。這防止了任何靠自我宣稱就拿高分的評分機制，不限於 agent 技能評估，任何用 LLM 當 judge 的場景都用得上。

**技能庫規模化的風險，語意相似度比數量更致命**。如果你正在設計技能檢索或路由系統，測試干擾項的抗性時不能只測「數量夠不夠多」，更要測「有沒有語意上高度相似但功能不同的近鄰選項」——這類近鄰選項才是實際部署時最容易造成誤觸發、誤選的來源。

**Degradation 跟 Collapse 是兩種不同的失效訊號，處理方式也不一樣**。性能開始下滑代表應該優化檢索、排序或候選過濾機制；性能幾乎完全失效則代表技能庫規模已經超出模型可靠判斷的範圍，光靠優化排序解決不了，得換架構——例如先用檢索大幅縮小候選集，而不是讓模型直接面對整個技能庫。

**驗證新舊版本評分規則好壞時，不一定需要疊加一層新的評審機制**。可以用「同一套 judge、跑在同一批資料上、套用不同版本的規則，再用可計算的機械指標比較輸出差異」，這比另外設計一個 judge-of-judge 更輕量、更可控。不過論文裡也保留了一個真正的 judge-of-judge 機制，當作離線的、獨立的最終驗證手段——兩者用途不同，不衝突。

---

## 結論

「答案對了」跟「技能用對了」是兩件事，只看 verifier pass/fail 沒辦法分辨 agent 是真的學會用技能，還是純粹運氣好蒙對。SkillCoach 把技能使用拆成選擇、遵循、組合、反思四個維度分別打分，再用一套「rollout、judge、arbitration、validation gate」的迴圈，讓評分規則能自己從真實執行資料修正演化，不必大量人工逐步標註。實驗證實了這套過程分數拿來篩選 SFT 訓練資料，效果比只看 verifier 通過與否更好——後者在小模型上甚至是負向的。

比起這篇論文的具體數字，更值得記住的是幾個可以直接搬到別的場景用的設計：證據要用乘法而非加法跟宣稱綁定、技能庫的風險看語意相似度而非單純數量、驗證新舊評分規則不一定需要疊加額外的評審層。這些觀念脫離 SkillCoach 這個系統本身依然成立，也是這篇論文留下來最耐用的部分。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1 Motivating example of agentic skill-use diagnosis.",
    "why_used": "具體展示兩條答案相同但技能使用行為完全不同的軌跡,支撐第一節「答案對不代表技能用對」的核心論點。",
    "agent_match_hint": "一張防洪任務的流程對照圖,左右兩側分別是軌跡 A 與軌跡 B 的步驟示意,包含環境、技能檔案、verifier 等元素標籤。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2 Overall framework of SkillCoach.",
    "why_used": "在介紹四個評分維度之前,先讓讀者看到 SkillCoach 的整體輸入輸出關係。",
    "agent_match_hint": "三段式流程圖,顯示任務/技能庫作為輸入,中間是四維度評分機制,右側是診斷與訓練資料篩選兩個下游用途。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Figure 3 The Self-Evolving Rubric Framework.",
    "why_used": "搭配 4.1 節文字說明 rollout、judge、arbitration、validation gate 四個階段如何串成一個演化迴圈。",
    "agent_match_hint": "一個循環流程圖,包含 rollout、judge、arbitration、validation gate 等標籤方塊與箭頭連接。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Table 5 SkillCoach task inventory. Gold denotes task-required skills, Distr. denotes distractor skills, and Inst. denotes task instances. Distractors include cross-task skills and semantically near but functionally inapplicable skills, simulating realistic industrial skill libraries.",
    "why_used": "支撐 4.1 節的一個推論性註記——每個任務家族底下有多個 instance,暗示軌跡池可能包含不同題目實例。",
    "agent_match_hint": "一張任務清單表格,依類別列出任務名稱與 gold/distractor 技能數、instance 數,底部有訓練與測試任務兩個總計列。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Table 2 Human-gold validation of rubrics before and after self-evolution.",
    "why_used": "呈現真正的離線 judge-of-judge 實驗數字,證明演化後的 rubric 品質確實比演化前更好。",
    "agent_match_hint": "一張數據表格,列出四個指標名稱與演化前後兩欄數值對照。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Table 4 SFT ablation under the Gold + Distractors setting. Results are final accuracy (%).",
    "why_used": "全篇最核心的實驗證據,直接對比 outcome-only 與 rubric-filtered 兩種篩選方式訓練出的模型準確率。",
    "agent_match_hint": "一張表格,列出 Base、Outcome-only SFT、R0 篩選、Rbest 篩選四種設定,以及 4B 與 9B 兩欄準確率數字。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Figure 4 Distractor-boundary analysis under growing and semantically overlapping skill libraries.",
    "why_used": "支撐 5.2 節對 degradation/collapse 邊界與干擾項語意相似度分析的說明。",
    "agent_match_hint": "多子圖組合:左上是不同模型 F1 分數隨干擾項數量增加的折線圖,右上是邊界估計圖,下方是干擾項類型敏感度的長條圖與決策分析圖。"
  }
]
```
