# SKILL.state：把 Agent 的「記憶」從對話歷史換成一份會更新的狀態

## 前言

現在幾乎所有 LLM agent runtime 都用同一套做法執行任務，也都有同一個很直接的副作用——執行越久，prompt 越長，成本跟延遲跟著爆。

Google 跟 Purdue 的這篇論文《SKILL.state: Scalable Long-Horizon Agent Skills》提出一個不同的做法：模型每一步只看「任務指令」加「當下的結構化狀態」加「最新觀察」這三樣東西，推理過程用完就丟，只把「狀態該怎麼修改」的結論留下來。結果是 prompt 大小跟已經走了幾步無關，整體成本從平方成長變成線性成長。

這篇文章會照著論文的邏輯走一遍：問題出在哪、方法怎麼設計、複雜度怎麼證明、實驗怎麼做、數字說了什麼——但也會誠實地指出證據強弱不對等的地方。文章最後還會整理幾個脫離這篇論文本身、也還是成立的通用心法。

先劇透判決：**工程／成本價值高，證據紮實**（尤其是 token 節省，$T=200$ 時省下 41 倍）；**研究價值中等偏低**，核心概念在 MemGPT、LangGraph、Dialogue State Tracking 裡都已經存在；**準確率提升的證據比 token 節省弱很多**，而且不是在所有環境下都成立。

---

## 一、問題出在哪：對話式執行為什麼撐不住長任務

這個做法有兩個具體的問題。第一，prompt 長度隨執行步數增長，token 成本與延遲跟著漲——執行越久，context 裡塞的東西越多。

第二，舊資訊會「賴著不走」，模型得自己分辨哪些還有效。早期的觀察結果、已經走過的推理過程，即使已經過期，還是留在 context 裡。模型每一步都要重新判斷「這段舊文字現在還算數嗎」，這本身就是一種額外負擔，也容易出錯：如果世界狀態已經被外部事件改變了，但舊的觀察紀錄還壓在上面，模型很可能還是照舊資訊做判斷。

加了記憶系統（摘要、檢索）也沒有真正解決這兩個問題，因為這些方法本質上還是「把過去的文字歷史重新整理一遍再餵回去」。模型的決策仍然建立在「重建過去發生了什麼」，而不是「直接讀取現在世界長什麼樣子」——執行的邏輯本質沒變，只是換了一種壓縮歷史的方式。

論文真正瞄準的問題是：能不能把「現在的世界狀態」變成一個獨立於歷史文字之外、可以直接讀取的東西，讓模型不用每次都從一堆文字裡重建現況。

---

## 二、SKILL.state 的核心設計

### 2.1 每一步只看三樣東西

SKILL.state 把每一步要餵給模型的東西壓縮成一個固定形狀：

$$A_t = (P, \Sigma_t, O_t)$$

- $P$：procedural specification，任務的固定指令（例如「你是倉儲管理員，可用動作是 Store/Ship/Move/Wait」），整個執行過程中不變。
- $\Sigma_t$：第 $t$ 步當下的「結構化執行狀態」，一個 JSON 字典，記錄目前世界長什麼樣子（例如「shelf_42 放著 item_12」）。
- $O_t$：這一步環境傳來的最新觀察（例如「Customer ordered item_12」）。

![SKILL.state 執行架構總覽：左半邊是傳統對話式做法，prompt 隨步數線性疊加；右半邊是 SKILL.state，prompt 大小固定，下方兩張圖分別畫出兩種做法的 context 成長曲線。](img-001)
*圖1 — SKILL.state 架構總覽：傳統做法 prompt 隨步數成長，SKILL.state 維持固定大小。（來源：原始論文。）*

模型看到這三樣東西之後，輸出三個東西：

$$(R_t, \Delta\Sigma_t, a_t)$$

- $R_t$：推理過程（chain-of-thought）。用完立刻丟掉，**永遠不會出現在下一步的 prompt 裡**。
- $\Delta\Sigma_t$：狀態的「差異」，一個 JSON 字典，描述這一步要對狀態做哪些修改。
- $a_t$：要執行的動作。

狀態更新公式很單純：

$$\Sigma_{t+1} = \Sigma_t \oplus \Delta\Sigma_t$$

這裡的 $\oplus$ 是論文定義的「字典合併運算子，帶 null 刪除語意」：$\Delta\Sigma_t$ 裡有的 key，直接覆蓋 $\Sigma_t$ 裡同名 key 的值；某個 key 的值被設成 `null`，代表把這個 key 從狀態裡整個刪掉；$\Delta\Sigma_t$ 沒提到的 key，維持原樣不動。

### 2.2 執行迴圈：狀態怎麼被更新、什麼被丟棄

把上面的輸入輸出串起來，整個迴圈長這樣：

1. Runtime 收到觀察 $O_t$。
2. 組成 prompt $(P, \Sigma_t, O_t)$——大小跟第幾步無關。
3. LLM 輸出 $(R_t, \Delta\Sigma_t, a_t)$。
4. Runtime 驗證 $\Delta\Sigma_t$ 是否合法（格式檢查）。合法就進下一步；不合法就回滾，要求模型重新輸出。
5. 套用更新：$\Sigma_{t+1} = \Sigma_t \oplus \Delta\Sigma_t$。
6. 執行動作 $a_t$，$R_t$ 永久丟棄。
7. 環境回傳新觀察 $O_{t+1}$，回到步驟一。

對照傳統的 ReAct 式做法，prompt 是不斷往後疊加的：

```
傳統做法：
  第1步 prompt: [P] + [O_1]
  第2步 prompt: [P] + [O_1, R_1, a_1] + [O_2]
  第3步 prompt: [P] + [O_1,R_1,a_1] + [O_2,R_2,a_2] + [O_3]
  ...越疊越長

SKILL.state：
  第1步 prompt: [P] + [Σ_1] + [O_1]
  第2步 prompt: [P] + [Σ_2] + [O_2]
  第3步 prompt: [P] + [Σ_3] + [O_3]
  ...大小大致固定（Σ 可能隨任務複雜度緩慢變化，但跟走了幾步無關）
```

差別就是這麼直白：傳統做法每一步都在「加一段新的」，SKILL.state 每一步都在「換掉整份狀態」。

### 2.3 具體例子：一次出貨動作的完整流程

論文附錄用一個倉儲情境示範整個流程，讀起來比公式直觀得多。情境是 item_12 目前放在 shelf_42。

Runtime 收到觀察：

```
O_t = "Customer ordered item_12."
```

模型內部的推理（這段之後會被丟掉）大概是：「顧客訂購了 item_12，我需要出貨。查看目前狀態，item_12 在 shelf_42。我要下 Ship 動作，並把狀態裡 shelf_42 的紀錄清掉。」

模型實際輸出的是這個 JSON：

```json
{
  "state_patch": { "inventory": { "shelf_42": null } },
  "action": "Ship item_12 shelf_42"
}
```

套用 $\oplus$ 之前，狀態是：

```
Σ_t.inventory = { shelf_42: "item_12", shelf_43: "item_9", ... }
```

套用之後：

```
Σ_(t+1).inventory.shelf_42 = null      ← 被刪除／清空
Σ_(t+1).inventory.shelf_43 = "item_9"  ← 沒被提到，維持原樣
```

環境執行完動作後回傳新觀察：`O_(t+1) = "Success: Shipped item_12 from shelf_42."`

下一輪 prompt 就是 $(P, \Sigma_{t+1}, O_{t+1})$——注意 $R_t$（推理過程）完全沒有出現，上一步的 $O_t$ 也沒有出現。模型下一輪看到的只有「現在的狀態」加「最新的觀察」，沒有半點歷史文字。

### 2.4 Schema 是為 domain 設計，不是為任務設計

同一個 domain 裡的所有任務共用同一份 schema，只設計一次。例如 InterCode CTF benchmark 裡 100 個完全不同的挑戰題目（逆向工程、鑑識、密碼學、二進位漏洞利用），全部共用同一組固定的欄位：已找到的 flag、已試過的假設／指令、目前操作的檔案、目前工作目錄、指令執行摘要。好處很直接：工程上省事，不用每個任務重新設計狀態格式，不同任務還能共用同一套 runtime 程式碼。

但這個做法有個前提：這個 domain 事先就知道該追蹤哪些欄位。如果一個 domain 沒辦法事先固定 schema、必須邊執行邊發現該追蹤什麼，這套做法就不適用——這是論文自己在 Limitations 承認的第一個失效情境，後面第七節會再細談。

### 2.5 驗證機制擋得住格式錯誤，擋不住語意錯誤

Runtime 在套用 $\Delta\Sigma_t$ 之前，會先做格式驗證：檢查是不是合法 JSON、是否符合預期的 key 結構。驗證失敗就觸發「回滾重試」，狀態退回上一步，要求模型重新輸出。這個機制確保格式錯誤的輸出不會污染狀態。

> **這裡有個很現實的限制**：這個機制擋得住「格式不合法」，擋不住「格式合法、但語意錯誤」的輸出。舉例來說，模型合法地輸出了一個會誤刪重要資訊的 patch，這種 patch 格式上完全沒問題，驗證機制抓不到，只能算完全「成功」地套用一次錯誤更新。更關鍵的是：因為舊狀態已經不在 context 裡了，一旦錯誤的 patch 被合法套用，就沒有「回頭看歷史文字」自我修正的機會，這是整個架構相對於保留完整歷史的做法，結構性更脆弱的地方。這件事不是猜測——論文自己的實驗數據顯示，小模型 68% 的失敗案例正是這種「語意上合法但錯誤的更新被無感套用」，第七節會用實際數字回頭對照這一點。

---

## 三、複雜度：$O(T^2)$ 怎麼變成 $O(T)$

論文用 $T$ 代表總執行步數，證明兩種做法的總 token 消耗量級不同。

傳統做法第 $t$ 步的 prompt 長度 $|C_t| = O(t)$——跟 $t$ 成正比。把所有步驟的 prompt 長度加總：

$$\sum_{t=1}^{T} |C_t| = O(T^2)$$

SKILL.state 第 $t$ 步的 prompt 長度 $|P_t| = O(|P| + |\Sigma| + |O|)$——跟 $t$ 無關，大致是常數。加總 $T$ 步：

$$\sum_{t=1}^{T} |P_t| = O(T)$$

用具體數字驗證直覺比較好懂。假設走 10 步，每一步的「單位長度」簡化成 1, 2, 3, ..., 10（傳統做法）vs 1, 1, ..., 1（SKILL.state）：傳統做法是 $1+2+\cdots+10=(1+10)\times10/2=55$，是等差數列求和，量級是 $T^2$；SKILL.state 是 $1+1+\cdots+1$（10 次）$=1\times10=10$，量級是 $T$。

這正是 $O(T^2)$ 對 $O(T)$ 差距的來源：傳統做法每一步長度隨 $t$ 線性增加，把這些「線性增加的量」再加總一次，結果就變成平方量級；SKILL.state 每一步長度大致固定，加總後自然只跟 $T$ 成正比。

這裡的「1 單位」是簡化說法，實際上 SKILL.state 每一步的大小是 $|P|+|\Sigma|+|O|$，不是完全釘死的常數——狀態 $\Sigma$ 可能隨任務複雜度緩慢變大（例如關聯密集的環境裡，狀態本身會隨分支、PR 數量增加而變胖）。但關鍵是：它的變化跟「已經走了幾步 $t$」無關，只跟「當下世界有多複雜」有關，這也是為什麼稱為每步 $O(1)$、總和 $O(T)$，而不是嚴格意義上「每步剛好等於某個固定常數」。

理論推導有沒有反映在實測數字上？答案是有——後面第六節的 Table 1 顯示，$T$ 從 100 加倍到 200 時，Stateful baseline 的總 token 消耗成長了約 4.7 倍（接近理論預期的 4 倍，也就是 $2^2$），SKILL.state 只成長約 1.9 倍（接近理論預期的 2 倍，也就是 $2^1$）。實測趨勢跟數學推導基本吻合。

---

## 四、怎麼測的：三個環境、三種對照組

### 4.1 三個測試環境

論文用三個環境驗證這套架構，其中兩個是自己設計的合成測試台，一個是別人設計的真實公開 benchmark。

**SkillExecBench** 是論文自建的控制型診斷測試台，用決定性的世界轉換規則，把「執行機制本身」跟「開放式啟發式搜尋」分開測，底下又分兩個子環境：

- **倉儲管理**：500 個獨立、互不重疊的貨架，動作只有 Store/Ship/Move/Wait，測試模型能否在長執行過程中維持大量互不干擾的狀態變數。
- **軟體版本庫**：有深度巢狀關聯的 Git 分支、commit、PR、CI 狀態圖，動作包括 CherryPick、Merge、RunTests、CreateRelease、Rollback。特色是「密集依賴關係」——單一動作（例如合併 PR）會連帶影響目標分支跟其他相依 PR，測試模型在互相糾纏的關聯圖上做結構化推理的能力。

另外兩個是公開 benchmark。**InterCode CTF**（Yang et al., 2023）是 100 道 Linux bash 的 Capture-The-Flag 挑戰，涵蓋逆向工程、鑑識、密碼學、二進位漏洞利用，agent 在 Docker 容器裡執行 bash 指令，反覆測試假設找出隱藏 flag。

**Sierra τ-Bench**（Yao et al., 2024）測試工具、agent、使用者三方互動的企業客服場景（零售、航空兩個領域），agent 要跟模擬使用者對話、透過工具呼叫查詢 SQLite 資料庫，並在商業政策限制下執行交易性動作。

### 4.2 怎麼算分

三個環境用不同方式算分：SkillExecBench 是連續分數（成功動作數除以總事件數）；InterCode CTF 是二元的 pass@1；τ-Bench 用官方評分器檢查資料庫的最終狀態。除了準確率，論文也追蹤每次呼叫 LLM 的平均 prompt 大小，以及整個執行過程累積的 token 總量。

### 4.3 對照組：誰在跟誰比

主要的架構層面對照組有三個：Prompt(ReAct)，也就是每步觀察、推理、動作全部往後疊加的最原始做法；Memory(Summary)，保留最近三輪原文加上定期更新的自然語言摘要；還有 Stateful(LangGraph)，有結構化 state block，但**同時**還保留完整的滾動對話紀錄。

其中 Stateful 是最關鍵的對照組——它跟 SKILL.state 一樣有結構化狀態，唯一差異是「狀態加完整歷史並存」vs「只有狀態，歷史全丟」。Stateful vs SKILL.state 這組比較，才是真正驗證「丟棄歷史」這個決定有沒有價值的關鍵對照，其他對照組頂多只能證明「結構化狀態比純文字歷史好」。

除了架構層面的對照組，論文還設了一組「預算對齊控制組」，專門用來排除「贏只是因為 prompt 比較短」這個混淆變因：Truncated(Sliding Window) 只留最近幾輪，硬卡 token 上限；Summary-capped 用自然語言摘要，但嚴格限制摘要本身的 token 上限；ReAct+LLMLingua 用小模型做困惑度壓縮，硬壓到目標 token 數。

實驗用的模型是 Gemini-3-Flash（proprietary）、Gemma-4-31B-it 跟 Qwen-3-8B-it（open-weight），溫度設 0.0，合成實驗跑 5 個隨機種子，$T \geq 50$ 時做 paired t-test（論文聲稱 $p<0.01$）。

---

## 五、在看數字之前：這個實驗設計真的測到「long horizon」了嗎？

論文在合成環境（SkillExecBench）裡刻意把 horizon 拉到 $T=10$ 到 $T=200$，是明確的「長度掃描」設計。但翻遍 InterCode CTF 跟 τ-Bench 那兩節，論文完全沒有報告這兩個公開 benchmark 裡，一個任務平均要走幾步才能完成。如果這些任務平均只需要 10 到 20 步就結束，那麼「公開驗證」根本沒有真正測試到 SKILL.state 宣稱最擅長的長距離場景——唯一真正壓力測試過「long horizon」的，就只剩自己設計、自己控制的合成環境。

業界確實存在專門設計來測試長距離、真實世界 agent 能力的公開 benchmark，這篇論文一個都沒用：

- **SWE-bench**：真實 GitHub issue 修復任務，往往需要數十到上百輪工具呼叫。值得注意的是，論文自己的「軟體版本庫」合成環境本質上就是在模仿這類任務，卻選擇自己造一個簡化版，而不是直接採用真實的 SWE-bench。
- **WebArena / Mind2Web**：長距離網頁導航任務。
- **GAIA**：需要多步驟工具串接推理的通用助理任務。
- **OSWorld**：真實作業系統操作任務。

論文沒有解釋為什麼沒有採用這些更有代表性的 long-horizon benchmark。

這不是說論文的數字是假的，而是「long horizon 假設在真實世界真的 work」這個宣稱，證據力比表面上看起來薄——最有說服力的長距離數字，全部來自自己設計、自己控制的合成環境。接下來看數字的時候，這個保留很值得放在心裡。

---

## 六、結果解讀

### 6.1 Warehouse 長距離 scaling

![倉儲管理環境下，準確率與總 token 消耗隨執行步數（Horizon T = 10 到 200）變化的表格，比較 Prompt、Memory、Stateful、SKILL.state 四種 runtime。](img-002)
*表1 — Warehouse Management 長距離 scaling 結果。（來源：原始論文 Table 1。）*

短任務（$T=10$）沒有準確率優勢，主要 baseline（Memory、Stateful）跟 SKILL.state 都是 1.00，打平。優勢只在長任務才浮現，而且差距不算壓倒性——$T=200$ 時是 0.94 對 0.88，差 6 個百分點。真正壓倒性的是 token 節省：$T=200$ 時差了 41 倍（Stateful 是 5,041,164 token，SKILL.state 是 122,384 token）。這篇論文最硬的證據是「省成本」，不是「更準」。

baseline 準確率也隨 $T$ 增加而下降、標準差放大——Prompt runtime 從 $T=10$ 的 $0.90\pm0.02$ 跌到 $T=200$ 的 $0.74\pm0.14$，SKILL.state 相對穩定。更精確的講法是「baseline 會隨執行時間拉長而退化，SKILL.state 不太退化」，而不是「SKILL.state 準確率大幅領先」。

### 6.2 公開 benchmark 的結果

![三個公開 benchmark（InterCode CTF、Sierra τ-Bench 零售、Sierra τ-Bench 航空）的成功率與總 token 消耗對照表，比較四種 runtime。](img-005)
*表2 — 公開互動式 benchmark 評估結果。（來源：原始論文 Table 4。）*

這是全篇最有說服力的準確率提升證據，因為是在別人設計的真實任務上：三個獨立任務都贏，CTF pass@1 高出最強 baseline 7.8 個百分點、τ-Bench 零售高 6.6 個百分點、航空高 4.3 個百分點。

但有個異常值值得留意：Memory baseline 在 τ-Bench 零售上崩得很慘（29.9%，比 Prompt 的 48.2% 還低將近 20 個百分點），可能是摘要式記憶把交易細節搞丟了，論文並沒有討論這個異常值。這代表零售這一欄的比較基準不穩定——SKILL.state 贏的是「表現最好的 baseline」還是「表現最差的 baseline」，差距很大，解讀時要留意對照組是誰。另外要說清楚的是，這張表本身無法回答上一節「long horizon 假設在真實世界成立」的疑慮，它證明的是「整體上表現比較好」，範圍比摘要暗示的窄。

### 6.3 反例登場：軟體版本庫環境

![軟體版本庫環境下，Stateful 與 SKILL.state 在四個執行步數（T=10, 25, 50, 100）的準確率對照表。](img-007)
*表3 — 軟體版本庫長距離執行 scaling 結果，論文全篇最重要的反例出現在這裡。（來源：原始論文 Table 6。）*

這張表是全篇最重要的反例。$T=10$ 時 Stateful 跟 SKILL.state 都是 $1.00\pm0.00$，打平；到了 $T=25$，SKILL.state（$0.88\pm0.08$）反而**輸給** Stateful（$0.94\pm0.03$）6 個百分點；$T=50$ 才贏回來（0.86 對 0.74）；$T=100$ 領先擴大到 15 個百分點（0.78 對 0.63）。

> **$T=25$ 這個點直接跟論文自己的宣稱矛盾**：摘要說「SKILL.state improves task accuracy... across diverse datasets」，正文說「matches or exceeds baseline accuracy across all horizons」，但「across all horizons」只在 Warehouse 環境成立，換到軟體版本庫環境就有反例，論文正文完全沒有提到這個反例。SKILL.state 在這張表的標準差也偏大（$\pm0.08$），代表結果不算穩定。

這跟軟體版本庫環境的特性有關：它的設計特色是密集依賴關係，單一動作可能連帶影響多個分支。這類強關聯的狀態，一旦某次 patch 更新沒有正確捕捉到連帶影響（例如合併 PR 卻漏更新相依分支的狀態），錯誤可能一路延續到後面步驟，因為沒有原始歷史文字可以回頭核對——這正好呼應第 2.5 節提到的驗證機制盲區，$T=25$ 這個反例很可能就是這個風險在實際發生。

「準確率全面提升」這個宣稱，在真實、複雜關聯的任務上不是穩定成立的，會因環境的關聯密度而有反例；真正跨所有環境都穩定成立的優勢，只有 token 節省。

### 6.4 其他佐證實驗

除了上面三張主表，論文還有幾組實驗值得一提，各自證明一件比較單純的事：

![高雜訊環境下（T=50），比較 Prompt runtime 跟 SKILL.state 在不同雜訊強度下的準確率。](img-003)
*表4 — Warehouse 雜訊魯棒性測試結果。（來源：原始論文 Table 2。）*

**雜訊魯棒性**：高雜訊環境下，Prompt baseline 準確率從 0.68 掉到 0.53，SKILL.state 全程維持 0.97 到 1.00。這個結論其實可以預期——雜訊不會被寫進 state patch，自然不影響後續決策，算是架構設計的直接推論，不算意外發現。

![外部環境悄悄改變世界狀態後，各種 runtime 需要多少步才能從錯誤認知中恢復的對照表。](img-004)
*表5 — Warehouse 狀態恢復實驗結果。（來源：原始論文 Table 3。）*

**狀態恢復**：外部環境悄悄改變世界狀態時，history-based baseline 需要 5 到 8 步才能從錯誤的舊認知中恢復，SKILL.state 需要 0 步。這個結果同樣接近同義反覆——SKILL.state 定義上不保留歷史文字，「被舊觀察蓋過新事實」這件事在架構設計上本來就不可能發生，只要修正性的觀察能成功寫進 patch，恢復步數邏輯上必然是 0。

![把所有做法的 token 預算硬性對齊到 SKILL.state 水準後的準確率對照表。](img-006)
*表6 — Warehouse 預算對齊控制組實驗結果。（來源：原始論文 Table 5。）*

**預算對齊控制組**：把所有做法的 token 預算硬性對齊到 SKILL.state 的水準（約 1,800 token）後比較，Truncated(Sliding Window) 只剩 0.18，ReAct+LLMLingua 只剩 0.22，Summary-capped 有 0.52，SKILL.state 維持 0.94。

這是全篇最紮實的實驗，因為它排除了「贏只是因為 prompt 比較短」這個混淆變因——在同樣的 token 預算下，統計式壓縮（LLMLingua）跟簡單截斷都會把語意上關鍵的資訊一起壓爛掉，SKILL.state 的結構化狀態能完整保留關鍵的關聯資訊。

---

## 七、小模型為什麼會失敗，以及論文自己承認的三個失效情境

![Gemma-4-31B-it 在倉儲環境下，隨執行步數變化的準確率與 token 消耗對照表。](img-008)
*表7 — Gemma-4-31b-it 在 Warehouse 環境的 scaling 結果。（來源：原始論文 Table 7。）*

換成開放權重的 Gemma-4-31B（$T=100$），準確率只剩 0.42。論文對失敗案例做了分類：**Premature State Overwrite/Deletion**（合併時不小心漏掉既有 key，等於誤刪）占 68%；**Schema Comprehension/Type 錯誤**（巢狀 list/dict 搞混）占 20%；**JSON 語法/格式錯誤**（漏逗號、括號沒對齊）占 12%。論文的結論是：小模型失敗的根源是「結構化輸出的遵從度」，不是「推理能力不足」。

第一類（68%）正是第 2.5 節提到的架構性風險的直接證據——語意上合法、但錯誤的 patch 被套用之後無法回頭校正，跟第 6.3 節 Table 6 的 $T=25$ 反例，本質上是同一個問題的不同表現形式。

整套設計依賴一個前提：**執行狀態可以成為未來執行的充分統計量**——過去發生的一切，只要在當下就被正確寫進狀態裡，就不需要保留原始文字。論文自己承認，這個前提在三種情境下會失效：

1. **Schema 沒辦法事先固定**——必須邊執行邊發現該追蹤什麼欄位。
2. **某個早期觀察，當下沒被判斷為重要，後來才發現有關**——因為沒寫進狀態，事後也找不回來了。這是三者中最現實、最容易在生產環境踩到的一項——整個架構最根本的賭注，是賭模型在**當下**就能做出正確的取捨判斷，一旦賭錯，沒有回頭路。
3. **任務本身的目標就是「歷史軌跡」本身**——例如稽核、debug 溯源、解釋過去做了什麼決策。這種任務下，丟棄歷史直接跟任務目標衝突。

論文另外還承認兩個附帶限制：多 agent 場景下共享狀態的同時寫入衝突，論文只說「可以自然擴展」但沒有實作或測試；grammar-constrained decoding 可以消除上面第三類的純語法錯誤，但解決不了第一類的語意錯誤。

---

## 八、實務上怎麼選：ReAct 還是 SKILL.state？

一個常見的直覺是：「保留過去的動作紀錄比較有容錯空間，對強模型來說應該是利大於弊」。這個直覺其實要拆成兩種不同意義的「容錯」。

意義一是「事後可追溯、可除錯」——保留歷史確實佔優勢，出錯後還能回頭檢查原始資料，SKILL.state 一旦資訊被丟棄就真的回不去了（對應上一節第 2 點限制）。

意義二是「模型在長距離任務中的準確率會不會因保留歷史而更穩」——第 6.1 節 Table 1 的實測數字反駁了這個直覺。即使用論文測過最強的模型（Gemini-3-Flash），保留完整歷史的 Prompt(ReAct) 從 $T=10$ 的 $0.90\pm0.02$ 一路跌到 $T=200$ 的 $0.74\pm0.14$，準確率下滑、標準差還放大了 7 倍。

這不是模型推理能力不夠，而是長 context 裡的資訊即使模型「看得到」，也不代表會可靠地「用得到」（也就是下一節會提到的 lost-in-the-middle 現象）——這個弱點換成更強的前沿模型也不會消失，只是程度可能緩和。所以「強模型加保留歷史等於利大於弊」這個推論，在短中距離任務成立，但在長距離任務上被實測數據推翻。

把這些線索整理成一個決策框架，可以拆成六個軸線來看：

| 軸線 | 傾向 ReAct（保留歷史） | 傾向 SKILL.state（丟棄歷史） |
|---|---|---|
| 相關性何時能判斷 | 事後才發現某觀察有用（debug、探索式研究） | 當下就能判斷「這筆該不該記」（倉儲、資料庫狀態這類） |
| 軌跡本身是不是產出物 | 是（稽核、合規、解釋過程） | 否（只要最終狀態或結果對） |
| 狀態的關聯密度 | 密集互相依賴（Git 圖、連鎖財務計算），patch 一旦出錯，後果會無聲擴散、且無法回頭比對原文 | 稀疏獨立（像 500 個互不相關的貨架），patch 錯誤的影響範圍被限制住 |
| 預期執行長度 | 短到中（25 步以內左右，且關聯密度低——見上一列；關聯密集的環境這條線會更早出現，例如軟體版本庫在 $T=25$ 就已經反過來輸）：兩者準確率打平，用 ReAct 更簡單，不用多蓋一層 schema／validate 基礎設施 | 長（100 步以上）：歷史型準確率會退化且變異數放大，狀態型維持穩定 |
| 模型能力 | 弱模型：合法但語意錯誤的 patch 被無感套用是重大風險 | 強模型能降低這個風險，但沒有證據顯示前沿模型完全免疫，只是沒測過 |
| 對成本／延遲的敏感度 | 不敏感（少量呼叫、預算充足） | 敏感（高頻呼叫、要上生產環境，$O(T^2)$ 成本會爆表） |

簡短的判斷規則是：先問「這個 domain 的狀態，我能不能在事情發生的當下就決定該不該記」——如果能（結構清楚、關聯稀疏、任務夠長），選 SKILL.state；如果不能，或需要稽核軌跡，或狀態關聯密集，優先考慮 ReAct 或「狀態加有限歷史」的混合做法。

這裡還有一個中間選項值得注意：第 6.1 節跟第 6.3 節裡的 Stateful（LangGraph 風格）baseline——「結構化狀態加完整對話歷史同時保留」，不是純 ReAct，也不是 SKILL.state 那種「只留狀態」。這個做法在軟體版本庫環境 $T=25$ 時甚至贏過 SKILL.state（0.94 對 0.88）。

如果不完全確定「當下就能正確判斷什麼該記」這個假設成不成立，「狀態加有限窗口的近期歷史」這種混合做法，可能比論文提供的兩個極端選項都更務實——用結構化狀態處理有信心的部分，同時保留一小段滾動歷史當安全網，萬一 schema 漏掉了什麼，近期歷史還能補救。成本介於兩者之間，不是 $O(1)$，但也不是純線性疊加到底。

---

## 九、這篇論文真正該帶走的東西

### 論文本身的貢獻

這篇論文最扎實的部分，是把「結構化狀態加丟棄歷史」這個做法系統化，並給出複雜度證明（$O(T)$ vs $O(T^2)$）。但要老實說，核心概念——Dialogue State Tracking、MemGPT、LangGraph 的 state block——都已經存在，論文的貢獻是「證明加系統化衡量」，不是提出新概念。

另一個值得記住的地方，是第 6.4 節提到的 budget-matched control 這個實驗設計本身：它證明了贏的是「結構化」而不是單純「變短」，這個實驗方法論其實比論文的核心主張更值得留在腦子裡。

### 脫離論文也成立的心法

讀這篇論文的過程中，比論文結論本身更有用的，是幾個獨立於這篇論文、換到別的場景也還是成立的判斷習慣。

**「準確率提升」跟「成本降低」是兩個獨立的宣稱**，論文常把它們包裝成同一個賣點，但證據力不對等——這篇論文成本的證據明顯強得多。遇到任何宣稱「又快又準」的論文，習慣把兩個宣稱拆開分別檢查證據強度，通常其中一個會明顯強於另一個。

**判斷一個架構該用「保留歷史」還是「壓縮／丟棄狀態」，關鍵問題是「相關性能不能在資訊出現的當下就被正確判斷」**，不是「模型夠不夠強」。這是一個可以帶到未來任何「要不要保留原始資料 vs 只留摘要／結構化萃取」場景的通用判斷規則，不限於 agent 設計。

**檢查一篇論文的「across all X」這類全稱宣稱時，去找有沒有跨資料集或跨環境的反例**——像第 6.3 節 Table 6 的 $T=25$ 反例。全稱宣稱通常只在最有利的那個環境成立，附錄或次要表格反而常藏著誠實的反例。

**Lost-in-the-middle 現象**（Liu et al., 2024，本論文引用來解釋長 context 準確率退化的原因）：模型技術上「看得到」長 context 裡的資訊，不代表「用得到」，這跟模型強弱是兩個獨立的維度，值得日後單獨深入了解。

**Dialogue State Tracking（DST）跟這篇論文的差異**在於：DST 是「狀態加完整對話歷史並存」，這篇是「只留狀態」。任何「要不要維護結構化狀態」的系統設計，都可以先問「歷史要不要跟狀態並存」這個子問題，而不是把「有沒有結構化狀態」當成唯一的分類維度。

**驗證機制能擋語法錯誤，擋不住語意錯誤**——這是這篇論文自己的實驗（68% 錯誤來自語意合法但錯誤的 patch）暴露出來、但論文沒有明講其架構性含義的發現。任何「用 runtime 驗證 LLM 輸出再套用」的設計，都要清楚意識到 validate 只能擋格式層面的錯，擋不住「格式對、但內容錯」這類錯誤——這是一個可以遷移到任何「LLM 產生結構化輸出、程式自動套用」場景的提醒。

最後一點也是最根本的：**架構設計如果消除了「回頭核對原始資料」這條路，就等於把賭注全押在「當下的判斷一定要對」上**。這個 trade-off 不只是這篇論文的特例，任何為了效率而丟棄原始資料、只留摘要或萃取結果的系統，都在做同一種賭注。

---

## 結論

SKILL.state 用一個簡單的想法解決了一個很具體的問題：把「現在的世界狀態」跟「歷史文字」分開，讓 prompt 大小不再隨執行步數增長。複雜度證明紮實，token 節省的實測數字也很硬（$T=200$ 時省 41 倍）。但「準確率全面提升」這個宣稱沒有那麼穩，軟體版本庫環境的 $T=25$ 反例就是最直接的證據——關聯密集的任務、加上驗證機制擋不住的語意錯誤，是這個架構真正的軟肋。

如果要用一句話總結該怎麼用這篇論文：把它當成「省成本」的解法來考慮，證據很夠；把它當成「全面比較準」的解法來期待，證據還不到那個程度。而比論文結論本身更值得留下來的，是那幾個脫離這篇論文也成立的判斷習慣——尤其是「相關性能不能在當下判斷」這個問題，值得帶到任何「要不要丟棄原始資料」的系統設計場景裡重新問一次。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1: Overview of the SKILL.state architecture.",
    "why_used": "在介紹核心設計（每一步只看三樣東西）時，用來讓讀者直接看到傳統做法與 SKILL.state 的 prompt 組成差異，以及兩者 context 成長曲線的對比。",
    "agent_match_hint": "左右兩欄對比圖，左邊是傳統對話式執行架構，右邊是 SKILL.state 架構，下方各有一張 context 成長曲線圖。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Table 1: Warehouse Management Long-Horizon Scaling using Gemini-3-Flash. Baseline runtimes suffer O(T 2) context accumulation, whereas SKILL.state maintains a bounded O(1) prompt footprint (Mean ± SD across 5 seeds).",
    "why_used": "支撐結果解讀第一小節，展示 Warehouse 環境下準確率與 token 消耗隨執行步數變化的完整數字。",
    "agent_match_hint": "一張表格，欄位是 Horizon、Runtime、Score、Avg Prompt、Total Tokens，列出 T=10 到 T=200 五個區段，每區段四種 runtime。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Table 2: Warehouse Noise Robustness (T = 50, Gemini-3-Flash).",
    "why_used": "支撐其他佐證實驗小節裡「雜訊魯棒性」的描述，讓讀者看到 Prompt runtime 與 SKILL.state 在不同雜訊強度下的準確率對比。",
    "agent_match_hint": "一張表格，欄位是 Noise Level、Runtime、Score，列出低、中、高三種雜訊強度下四種 runtime 的分數。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Table 3: Warehouse State Recovery (Gemini-3-Flash).",
    "why_used": "支撐其他佐證實驗小節裡「狀態恢復」的描述，展示各種 runtime 從錯誤認知恢復所需的步數。",
    "agent_match_hint": "一張表格，欄位是 Scenario、Runtime、Success、Recovery Steps，列出 A 到 D 四個情境。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Table 4: Evaluation on Public Interactive Benchmarks using Gemini-3-Flash. SKILL.state achieves the highest task success rates while significantly reducing prompt sizes and cumulative token consumption.",
    "why_used": "支撐結果解讀第二小節，這是全篇在真實公開 benchmark 上最有說服力的準確率提升證據。",
    "agent_match_hint": "一張表格，分成 InterCode CTF、Sierra τ-Bench 零售、Sierra τ-Bench 航空三組欄位，各自有 Pass Rate 跟 Total Tokens。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 5: Budget-Matched Controls on Warehouse (T = 100, Gemini-3-Flash, Budget ∼1,800 tokens).",
    "why_used": "支撐其他佐證實驗小節裡「預算對齊控制組」的描述，這是排除 prompt 長度混淆變因後最紮實的比較。",
    "agent_match_hint": "一張表格，欄位是 Runtime/Configuration、Score、Avg Prompt、Total Tokens，列出五種在相同 token 預算下的做法。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Table 6: Software Repository Long-Horizon Execution Scaling using using Gemini-3-Flash. Baseline runtimes suffer catastrophic O(N 2) context collapse, whereas SKILL.state maintains an O(1) prompt footprint.",
    "why_used": "支撐結果解讀第三小節，這是全篇最重要的反例，T=25 時 SKILL.state 準確率輸給 Stateful baseline。",
    "agent_match_hint": "一張表格，比較 Stateful 與 SKILL.state 在 T=10、25、50、100 四個執行步數下的準確率與標準差。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Table 7: Gemma-4-31b-it Warehouse Scaling.",
    "why_used": "支撐第七節小模型失敗模式的討論，實際數字佐證 T=100 時 Gemma-4-31B 準確率僅 0.42 這個說法。",
    "agent_match_hint": "一張表格，欄位是 Horizon、Runtime、Score ± SD、Avg Prompt ± SD、Total Tokens ± SD，列出 T=10 到 T=100 四個區段。"
  }
]
```
