# LLM-as-a-Verifier：不要讀模型吐出的分數，去讀它吐分數時的機率分佈

## 前言

用 LLM 幫另一個 LLM 的輸出打分數，現在幾乎是標配。做法通常長這樣：叫模型輸出一個 1 到 5 的整數，然後你拿那個整數去排序、篩選、當 reward。

這篇論文（arXiv 2607.05391v2，Stanford / UC Berkeley / NVIDIA）指出這個流程有個很少人注意的漏洞：模型在輸出分數的那個 token 位置，內部產生的是一個**完整的機率分佈**，但標準做法只取機率最高的那一個，其餘全丟。資訊不是模型沒產生，是解碼策略把它丟掉的。

改法很單純：不取 argmax，改算期望值。分數從離散整數變成連續實數。作者把這個改動加上重複取樣、準則拆解，包成一個叫 LLM-as-a-Verifier 的框架，再配一個新的排名演算法 PPT，橫跨程式、機器人、醫療三個領域做了實驗。

這篇文章要做兩件事：把這套機制講清楚到你可以自己實作，以及誠實標出論文哪些地方的證據沒有它宣稱的那麼強。先講結論——**這是一篇工程價值高於研究新穎性的論文**。期望值解碼、重複取樣、ensemble 都不是新發明，真正的貢獻在於系統化打包、扎實的 ablation，以及那個排名演算法。而它最漂亮的實證，其實不是摘要裡那些 SOTA 數字。

## 一、問題：資訊在 argmax 那一步被壓扁了

傳統 LM judge 的形式大概是這樣：

```
R_LM(x, τ) ∈ {1, ..., G}     ← 分數就是「生成出來的那個 token」
```

模型在分數 token 的位置有一個 vocabulary 上的機率分佈，argmax 把它塌縮成一個整數。粗粒度的量表配上這種解碼方式，後果很直接：**大量候選解會打成平手**。在 Terminal-Bench 上，論文量到 27% 的比較結果是平手。平手就是不能排序，不能排序就沒辦法從 N 條候選裡挑一條。

論文另外主張了第二個問題：訓練式的 reward model（ORM，只看最終結果打分；PRM，逐步驟打分；機器人領域則有 RoboReward-8B、Robometer-4B）會被訓練資料綁死，跨領域就失靈。這裡先標一個保留——**這只是 Section 1 的一句背景假設，論文沒有提供任何跨域失效的實驗數據**。

### 這件事值得解決嗎？看 oracle 的落差

![Terminal-Bench V2 上的 Oracle Pass@K 曲線，隨著每題抽樣的軌跡數增加，覆蓋率從約六成一路爬升到 98.9%，遠高於單一模型的 Pass@1。](img-005)
*圖一 — 如果有一個完美的 verifier，光靠重複抽樣就能把 Terminal-Bench V2 解到 98.9%。（來源：原始論文。）*

這張圖是整篇論文的動機基礎。它說的是：如果存在一個完美的 oracle verifier，每次都能從抽樣出來的候選裡挑中對的那條，Terminal-Bench V2 的解出率可以到 **98.9%**。而實際的 Pass@1 只有 83.1%。

```
Pass@1  83.1% ─────────── 落差 ~16pp ─────────── Oracle 98.9%
                    這段全靠 verifier 去兌現
```

要提醒的是這張圖的功能：它不是一個獨立的第三個挑戰，而是「上面那個挑戰值得解決」的量化證據。論文的行文順序是先給 oracle 落差、再說要拿到這段潛力得有夠準的 verifier、然後繞回標準 judge 不夠細緻。

順帶先打個預防針：這裡的 98.9% 是**放任 K 一路增大**時的 oracle 覆蓋率上限，後面主實驗表格裡那個 92.1% 則是**實際候選池只有 N=5** 時的 oracle Pass@N。兩個數字量的不是同一件事——前者是理論天花板，後者才是這套系統真正在爭取的空間。後面對照兌現比例時用的是後者。

## 二、方法：把分數讀成機率分佈

![LLM-as-a-Verifier 的整體框架圖，左側是文字、影像、影片三種輸入模態，中間是由 Uncertainty、Granularity、Repetition、Decomposition 四塊組成的驗證核心與獎勵公式，右側是測試時擴展、進度追蹤、強化學習三種下游應用。](img-002)
*圖二 — 框架全貌：任何模態進來，讀分數 token 的完整分佈出去，接三種下游用途。（來源：原始論文。）*

論文在方法一開頭先做了一個字典式的區分：**judge** 是形成整體意見、給出一個決定（像老師打總分）；**verifier** 是確認真偽與正確性，需要更細緻的評估（像審計，逐項核對）。

老實說，這段是修辭鋪墊，不是技術論證。論文並沒有從「verifier 的角色定義」推導出「所以必須用機率分佈的期望值」，它是先斷言了這個區分，再用來合理化接下來要推出的三個維度。當成一個記憶用的比喻可以，當成論證就不行。

### Scoring prompt 長什麼樣

```
You are an expert [domain] reviewer. You will see a
task description and two trajectories.

Evaluation Criteria: [domain specific criteria]
Task: {task prompt}
Trajectory A: {A}   Trajectory B: {B}

Carefully analyze each trajectory, then provide your
final scores:
<score_A> INTEGER_1_TO_20 </score_A>
<score_B> INTEGER_1_TO_20 </score_B>

Rating Rules: Rate correctness on a 1–20 scale
(1 = incorrect, 10 = borderline, 20 = correct)
```

三個設計要點值得單獨拿出來講。

**一次 prompt 塞兩個候選解，對照著評。** 不是各自單獨評分再比大小。

**`<score_A>` / `<score_B>` 這兩個標籤是整個機制的關鍵。** 真正要的不是標籤裡輸出的那串文字，而是該 token 位置上整個 vocabulary 的機率分佈。標籤存在的意義是讓你能精準定位「分數在第幾個 token」，才有辦法去撈 logprob。

**1–20 分制只給了三個錨點**（1 = 錯、10 = 邊緣、20 = 對），中間的 2 到 9、11 到 19 怎麼判斷，論文沒說，靠模型自己內插。

這裡有個容易被忽略的設計：**prompt 裡沒有 ground truth**。verifier 只拿到任務描述和軌跡內容，必須自己從 log、工具呼叫結果、輸出格式這些證據判斷對錯，不是拿去跟標準答案比對。這是刻意的 reference-free 設計，後面三個子準則（Specification / Output / Errors）全都是「拿軌跡對照任務要求」也印證了這點。論文其他地方提到的 "ground-truth successful solution" 是研究者事後拿來評估 verifier 準不準的標籤，永遠不會進到 verifier 的 prompt 裡。

至於為什麼要兩條軌跡一起放？數學上不需要——公式只要兩個獨立算出的純量相減，分兩次 prompt 各自評分完全可行。但論文明講是同一個 prompt 一次拿兩個分數，而且**沒有解釋原因**。合理的猜測是相對比較比絕對評分校準更穩，或是後面的 PPT 本來就要成對比較、一次呼叫拿兩個分數更省，但這些都是我們的推測，不是論文的論述。

還有一個字面上的矛盾：prompt 裡寫的是 `INTEGER_1_TO_20`，但緊接著的註解卻說「我們用字母而非數字，以利抽取 logprob」。兩處對不上，論文沒澄清。可能的解釋是 tokenization——兩位數在 tokenizer 裡常被切成兩個 token，改用單一字母（A=1 … T=20）才能保證每個分數恰好一個 token，撈 logprob 才有意義。但論文沒有這樣說明。

### 核心公式：期望值取代 argmax

```
R(x,τ) = (1/CK) · Σ_c Σ_k Σ_g  p_θ(v_g | x,c,τ) · φ(v_g)
                    C   K   G
```

| 符號 | 意義 |
|---|---|
| `x` / `τ` | 任務描述 / 被評分的軌跡 |
| `c` / `C` | 第 c 個評分準則 / 準則總數（主實驗 C=3） |
| `k` / `K` | 第 k 次重複評估 / 重複次數（主實驗 K=8） |
| `v_g` / `G` | 第 g 個分數 token / 取用的分數 token 數（主實驗 G=20） |
| `p_θ(v_g \| ...)` | 模型在該位置給 `v_g` 的機率 |
| `φ(v_g)` | 把分數 token 對應回實際數值（代表 3 分的 token → 3.0） |

拆成三層來看比較好懂：

```
【最內層 Σ_g】granularity
  一次 LLM 呼叫 → 分數 token 位置的機率分佈
  → G 個候選分數做機率加權 → 得 1 個期望值

【中層 Σ_k】repetition
  同一準則重複 K 次 → 得 K 個期望值 → 加總

【外層 Σ_c】criteria
  每個準則各自跑完中層 → 全部加總

【最後】÷ (C×K)
```

注意分母沒有除以 G。因為最內層是機率加權，`Σ_g p_θ = 1`，那一層本身已經是加權平均了。順帶一提，**總 LLM 呼叫次數是 C × K**，主實驗每條軌跡 24 次；G 不影響呼叫次數（這句話稍後會被打上問號）。

實際算一遍最有感。假設 G=5，某條軌跡的分數分佈是：

| v_g | φ(v_g) | p_θ(v_g) | 乘積 |
|---|---|---|---|
| v_1 | 1 | 0.02 | 0.02 |
| v_2 | 2 | 0.05 | 0.10 |
| v_3 | 3 | 0.13 | 0.39 |
| v_4 | 4 | 0.35 | 1.40 |
| v_5 | 5 | 0.45 | 2.25 |
| | | **合計** | **4.16** |

離散 judge 走 argmax 拿到 **5**；verifier 算期望值拿到 **4.16**。現在關鍵來了：另一條軌跡如果分佈是 p(v_5)=0.52、p(v_4)=0.30，argmax 一樣是 5（**平手**），但期望值會落在 4.3 附近（**不平手**）。平手率歸零的機制就是這麼來的。

上面那組機率是示意值，因為**論文從未公布任何一次評分的實際機率分佈**。

公式本身也有兩個瑕疵值得記一下。被加總項 `p_θ(v_g | x, c, τ)` 裡有 c 卻**沒有 k**——既然外面在對 k 加總，被加總的東西理應隨 k 變化，否則就是把同一個數字加 K 次再除以 K。內文另一處寫成 `R^(k)(x,τ)`（有標 k）才是對的，公式本身寫得不嚴謹。另外這條公式編號是 Eq. 3.1，但論文後面兩個地方又改稱它為 Eq. 1，標號沒對齊。

### 正規化與 Bradley–Terry

分數算完之後會壓到 [0,1]：

```
R ← (R − φ_min) / (φ_max − φ_min)
```

上例是 (4.16 − 1) / (5 − 1) = **0.79**。論文沒解釋為什麼要正規化，但從機制推敲得出來：正規化不改變單次比較的排序（它是線性單調變換），真正影響的是下一步 sigmoid 會不會飽和。

| 情境 | 差值 | σ(差值) |
|---|---|---|
| 1–20 原始量表，兩條差 8 分 | 8.0 | 0.9997 |
| 正規化後同樣差距 | 0.42 | 0.60 |

沒有正規化的話，「好一點」和「好很多」都會被壓成 1.0，等於把剛剛辛苦保留下來的細緻度又丟掉一次。這在後面的 PPT 裡才真正出問題，因為 PPT 是把多場比較的機率**累加**起來當排名依據；一旦飽和，累加值就幾乎只反映「你有沒有碰到弱對手」，而不是「你到底多強」。

接著把分數差轉成偏好機率，用的是 Bradley–Terry：

```
P(τi ≻ τj | x) = 1 / ( 1 + exp( −( R(x,τi) − R(x,τj) ) ) )
```

R(τi)=0.79、R(τj)=0.62 → 差值 0.17 → P = 0.542，忠實反映「差不多但略勝」。

這裡有個常見的誤解要澄清：**O(N²) 不是 Bradley–Terry 造成的，是「循環賽這個比較排程」造成的**。兩者是不同層次的東西：

```
比較排程（要比哪些配對）      ← O(N²) 出在這裡
       ↓ 產生比較結果
Bradley–Terry（結果 → 機率）  ← 只是一個數學模型
```

而且這篇的用法跟經典 BT 是反過來的：

| | 經典 BT | 本篇 |
|---|---|---|
| 已知 | 勝負紀錄 | 分數 R(x,τ) |
| 求 | 潛在實力值 | 偏好機率 P(τi ≻ τj) |
| 方向 | 觀測 → 反推 | 實力 → 正推 |

論文直接把 R 當成 latent strength，等於跳過了 BT 最麻煩的參數估計。所以 PPT 要省的從來不是 BT 的計算成本（sigmoid 幾乎免費），而是**取得每個 R 所需的 LLM 呼叫成本**——每一對就是 C×K = 24 次。

那為什麼不乾脆直接比大小就好？因為那只會得到 0 或 1，資訊又被壓扁一次。轉成機率能保留「贏多少」，而 PPT 累加的正是機率而不是勝負。

## 三、三個 scaling 維度

![三張並排的折線與長條圖，分別顯示驗證準確率隨分數 token 粒度、重複評估次數、評分準則拆解而提升，其中三準則 ensemble 的準確率高於任一單一準則。](img-004)
*圖三 — 驗證準確率沿著三個維度都會上升：分數粒度、重複次數、準則拆解。（來源：原始論文。）*

### (A) Score Token Granularity（G）：對付解析度不足

| G | 1 | 2 | 4 | 8 | 16 | 20 |
|---|---|---|---|---|---|---|
| 準確率 | 73.1% | 73.3% | 75.1% | 75.9% | 77.2% | 77.5% |

反直覺的地方在於：擴大量表**並沒有給 verifier 任何新資訊**。論文的說法是，它給了 decoder 一個更細的空間，去投射模型內部本來就有的信念——原本會被四捨五入到同一格的相近信念，現在落到不同的連續值上。

這裡有個實務上很要緊、但論文自相矛盾的點：**G 到底要不要重跑 LLM？**

| 讀法 | 論文依據 | 成本後果 |
|---|---|---|
| 不用重跑 | Section 1 說 "scaling the number of extracted token logits"；Section 4 說 Gemini 2.5 Flash「可以每個 scoring token 抽到 20 個 top logprob」 | G 只是事後從 API 回傳的候選清單多取幾個，**免費** |
| 要重跑 | Section 3.2 把 `V_score = {v_1,...,v_G}` 定義成分數等級的 token 集合；Table 2 把 G=5 標為「同一個 1–5 量表上的期望值」，而 1–5 和 1–20 是兩個不同的 prompt | 換 G 就要換 prompt 重跑，**不免費** |

論文沒有澄清，兩處講法直接打架。這件事影響很大——如果是第二種讀法，前面「G 不影響呼叫次數」那句就不成立，整個成本評估要重算。

論文另外用 SNR 來佐證 granularity 的效果：

```
SNR(G) = E[s_c − s_i] / sqrt( Var(s_c − s_i) )
         ↑ 訊號：平均贏多少   ↑ 雜訊：贏得多不穩定
```

| G | 1 | 4 | 16 | 20 |
|---|---|---|---|---|
| SNR (k=16) | 0.775 | 0.786 | 0.797 | 0.799 |

這個式子跟統計上的 effect size（Cohen's d）同形式：平均差距除以標準差，標準化之後才能跨情境比較。SNR 在論述裡的定位不是解釋 granularity 的作用機制（那是「更細的投射空間」在做的事），而是把「分得更開」和「最終更準」連起來的橋樑指標。

但這座橋是斷言出來的。論文只說準確率是 SNR 的單調函數，沒給函數形式，也沒解釋 SNR 僅漲 0.024（約 3%）為什麼能對應到準確率漲 4.4pp。四個裸數字，沒有誤差範圍，論述強度撐不太住。

### (B) Repeated Evaluation（K）：對付單次評估的隨機偏差

```
(1/K) · Σ_k R^(k)(x,τ)      ← 就是個 Monte Carlo estimator
```

| K | 1 | 2 | 4 | 8 | 16 |
|---|---|---|---|---|---|
| 準確率 | 74.7% | 76.1% | 77.1% | 77.3% | 77.5% |

這裡的眉角是：**平均只降變異數，不降偏誤**。變異數以 O(1/K) 縮小，偏誤完全不變。如果 verifier 對某類軌跡有系統性誤判、每次都往同一個方向錯，跑一百次還是錯。論文自己也承認 K 變大時報酬遞減，因為困難樣本上的偏誤是相關的。

拿量測來類比就很清楚：增加樣本數可以縮小標準誤，但如果秤本身永遠多 2 公斤，量再多次也修不掉那 2 公斤。

所以前兩個維度的分工是：

```
Granularity  → 讓每一個估計值本身更銳利
Repetition   → 把 granularity 消不掉的雜訊平均掉
```

### (C) Criteria Decomposition（C）：對付評分標準本身不合理

前兩個維度都假設 rubric 本身是好的。但在長時序的 agent 任務裡，「這條軌跡正確嗎？」這個問題把好幾個邏輯上獨立的因素混在一起，verifier 往往只抓住 prompt 裡最顯眼的那一個。

論文對 code agent 拆出三個子準則：

```
Specification → 有沒有滿足任務的所有要求？   → 檢查完整性
Output        → 最終輸出格式是否符合預期？   → 檢查結果
Errors        → log／工具輸出有無失敗訊號？   → 檢查證據
```

| 準則 | 準確率 |
|---|---|
| Specification 單獨 | 75.2% |
| Errors 單獨 | 76.0% |
| Output 單獨 | 76.4% |
| **三者 ensemble** | **78.3%** |

說白了這就是 ML 的 ensemble：多個各有不同偏誤的弱分類器，只要錯誤不完全相關，平均起來就會優於單一最強者。

不過這一節的問題比前兩個維度多。**三個準則怎麼來的，論文沒說**，沒有交代選擇過程，也沒有「試過 4 個、5 個」的 ablation，論文自己在附錄裡承認未來應該改成學習或動態生成。更要緊的是 **C 根本沒有 scaling 曲線**——G 和 K 都有完整曲線，C 只有四根柱子，沒有 C=2 的資料，也不知道 C=5、C=10 會怎樣。嚴格講，論文只證明了「3 個比 1 個好」，沒證明 C 是一個可 scaling 的軸，但摘要就把它跟另外兩個並列。加上圖裡誤差棒重疊得很明顯，1.9pp 的改善沒做顯著性檢定，也沒說明誤差棒代表什麼。

最後一個缺口：這三個準則明說是為 code-agent 軌跡設計的，但機器人和醫療的實驗也宣稱用同一組。「輸出格式是否符合預期」對一段機器手臂的影片來說是什麼意思？論文從頭到尾沒給答案。

## 四、query-optimize：一個把機制講活的案例

這個案例來自 Terminal-Bench V2，是全篇最能建立直覺的地方。

**任務**：給定一個 SQLite 資料庫和一段沒優化過的 SQL 查詢，寫出效能更好、而且**輸出結果完全相同**的版本。

兩條軌跡都由 Claude Opus 4.5 產生，差別在這裡：

```
✅ 正確：等原始查詢在未動過的原始資料庫上跑完（等了 5 分 03 秒）
        → 直接 diff 比對 → 通過

❌ 失敗：嘗試跑原始查詢，兩次都超時中斷（60 秒、5 分 02 秒）
        → 把資料庫複製到 /tmp
        → 在複製品上加索引，讓原始查詢跑得動
        → 拿「有索引副本上的原查詢」對比「未加索引的原始庫上的優化查詢」
        → 刪掉所有驗證產物
```

失敗的關鍵在於它是在**兩個不同的物理存取路徑**上比較結果。加了索引之後，ORDER BY 碰到相同鍵值的排序可能不一樣，在 LIMIT 500 的邊界上就可能切出不同的資料。所以它從來沒有真正驗證等價性——但它自己回報「內部 diff 檢查通過」。

verifier 有看出來嗎？有。論文附錄引用的 Gemini 2.5 Flash 推理過程明確指出：agent 修改了資料庫來取得參考輸出，違反了任務的隱含限制，因此並未正確驗證等價性。

那問題出在哪？**verifier 抓到了，卻用帶保留、程度性的措辭表達**（像是「稍微乾淨一些」「略為直接一點」），講得像無關緊要。模型內部有正確判斷，但這個判斷在 argmax 那一步被壓扁了。

![一張三列的表格，比較離散 judge 與連續 verifier 在同一個任務上重複一百次的排序結果，離散 judge 有 88 次平手，連續 verifier 平手次數為零。](img-008)
*圖四 — 同一個任務跑一百次：離散 judge 有 88 次無法區分，連續 verifier 一次都沒有。（來源：原始論文。）*

| 方法 | s_c > s_i ✓ | 平手 | s_c < s_i ✗ |
|---|---|---|---|
| Judge（離散，G=5） | 12/100 | **88/100** | 0/100 |
| Verifier（連續，G=5） | 69/100 | 0/100 | 31/100 |
| Verifier（連續，G=20） | **77/100** | 0/100 | 23/100 |

這個對照設計很乾淨，因為它一次只動一個變因：

- **第 1 列 → 第 2 列**：同一個 1–5 量表，只換解碼方式（argmax → 期望值）。88 次平手歸零，正確排序從 12 上升到 69。
- **第 2 列 → 第 3 列**：同樣是期望值，只換量表（1–5 → 1–20）。正確排序從 69 上升到 77。

不過最右欄有個論文沒討論的 trade-off：**離散 judge 的排錯次數是 0/100**。它從不把錯的排在對的前面，它只是不表態。連續 verifier 消除平手的代價，是被迫每次都表態，其中二三成表錯了。

用「平手算半分」計分的話，Judge = 12 + 88×0.5 = 56，Verifier G=5 = 69，G=20 = 77，verifier 確實還是勝出，結論站得住腳。但如果你的下游流程是「平手就交給人審」，judge 的行為反而更安全。論文沒有提這一層。

![兩張並排的長條圖，左圖是不同重複次數下 judge 與 verifier 的配對驗證準確率，右圖是兩者的平手率，verifier 的平手率在所有設定下都是零。](img-009)
*圖五 — 拉高重複次數，judge 的平手率從 26.7% 掉到 5.5%，但準確率幾乎沒動；verifier 從頭到尾零平手。（來源：原始論文。）*

| K | Judge 準確率 | Verifier 準確率 | Judge 平手率 | Verifier 平手率 |
|---|---|---|---|---|
| 1 | 71.8% | 74.7% | 26.7% | 0.0% |
| 4 | 74.4% | 77.1% | 11.7% | 0.0% |
| 16 | 74.7% | 77.5% | 5.5% | 0.0% |

論文想讓你看的是對角線：**verifier 只跑 1 次（74.7%）就等於 judge 跑 16 次（74.7%）**。judge 靠重複評估得到的改善，主要機制是用平均打破平手（26.7% → 5.5%），而不是真的變會判斷。就像用重複測量去彌補一把刻度太粗的尺，而 verifier 是直接換一把刻度細的。

「16 倍運算」這個對比其實有點誇大——judge 和 verifier 在每個 K 下的差距都落在 2.7 到 2.9pp 之間，那個對比只在你剛好只在乎「追平 74.7%」這個門檻時才成立。更實質的差別是天花板不同：judge 在 K=16 已經飽和（74.4 → 74.7），verifier 還停在 77.5%。

## 五、PPT：從 N 條裡挑最好的那條

verifier 一次只能比兩條，但實際任務是「從 N 條選最好」。完整循環賽是 O(N²)：

```
N = 20  →  C(20,2) = 190 對  →  190 × 24 = 4,560 次 LLM 呼叫
```

Probabilistic Pivot Tournament（PPT）是全篇唯一算得上演算法新貢獻的部分。核心想法是每條候選只跟一小群 pivot 比，成本降到 O(Nk)。但真正的設計重點不是「用 pivot 省錢」——那很直觀——而是**怎麼用一個便宜的前置步驟，找出值得當 pivot 的候選**。

![PPT 的五階段流程圖：候選池、環狀比較、選出 pivot、pivot 錦標賽、最終依正規化勝分選出優勝者。](img-006)
*圖六 — PPT 的五個階段，重點在第二階段那圈環狀比較。（來源：原始論文。）*

```
① Candidates    N 條候選
       ↓
② Ring pass     隨機環狀比較 N 場 → 粗略排名 + 消位置偏誤
       ↓
③ Pivot select  取前 k 名為 pivot 集合 P
       ↓
④ Pivot rounds  非 pivot vs pivot ＋ pivot 彼此互比
       ↓
⑤ Selection     累積 w_i / c_i，取最高者
```

### Ring pass：一石二鳥

把 N 條候選隨機排成一個環，只比較環上相鄰的 N 對。

```
      τ4 ── τ1
     ╱          ╲
   τ2            τ5
     ╲          ╱
      τ6 ── τ3

比較：(τ4,τ1)(τ1,τ5)(τ5,τ3)(τ3,τ6)(τ6,τ2)(τ2,τ4)
共 6 對 = N 對，而非 C(6,2) = 15 對
```

這個結構同時做到兩件事。第一是**便宜取得粗略排名**，只花 N 場就能大致看出誰強誰弱。第二是**消除位置偏誤**——LLM 對 prompt 裡「Trajectory A」和「Trajectory B」這兩個位置常有系統性偏好，這是已知問題。環狀結構讓每條候選恰好當一次 A、當一次 B，偏好在期望值上互相抵消。這其實就是實驗設計裡的平衡設計（counterbalancing）：讓每個條件在每個位置出現一樣多次，順序效應就會在整體平均中抵銷。

順帶提一下論文用的「Hamiltonian cycle」這個詞。這是圖論術語（每個節點恰好經過一次並回到起點），因為「判斷任意圖是否存在 Hamiltonian cycle」是 NP-complete 而有名。但這篇完全沒碰到那個難點——這裡是完全圖，任兩條都可以比較，隨便打亂順序就是一個合法的環，論文自己的偽代碼寫的其實就是「取一個隨機排列」。用詞偏華麗，實質是隨機排列成環。

另外，「在期望值上抵消」只在**偏誤是加性常數**的時候嚴格成立。如果偏誤跟內容有關（例如只在兩條差不多時才偏好 A），環狀結構不保證能抵消。論文沒討論這個前提，也沒有做「有 ring pass vs 無 ring pass」的對照實驗。

### Pivot selection 與最終選出

每場比較兩邊都更新：

```
p = σ(R_i − R_j)
w_i += p        c_i += 1      ← w_i 是 win mass
w_j += (1 − p)  c_j += 1      ← 兩者相加恰為 1
```

環狀結構讓跑完之後每條的 c_i 都是 2，然後按 w_i/c_i 排序取前 k 名當 pivot，沒有額外規則，純粹 top-k。

為什麼挑表現好的當 pivot？因為目標是選出最好的那條，需要細分的是頂端誰最好，不是墊底誰比較不爛。如果 pivot 挑到明顯很差的候選，所有比較都只會得到「大家都比它好」這種沒有鑑別力的結果。這跟 quickselect 選 pivot 的思路一樣：不需要完全排序，只要找最大者，資源就該集中在可能是答案的那一區。

這裡有個論文完全沒分析的疑慮：**pivot 是根據 ring pass 裡僅僅兩場比較選出來的，樣本量極小。** 如果某條真正最好的候選在 ring pass 中運氣不好、兩場都碰到強對手，它的 w_i/c_i 就會偏低，可能直接落榜、進不了 pivot 集合。論文沒有分析這個「好候選被誤篩掉」的機率。

接著比兩類配對：非 pivot 對每個 pivot（(N−k)×k 對），以及 pivot 彼此互比（C(k,2) 對）。後者是必要的，因為最後還得在 pivot 之間分高下。

```
總比較次數 = N + k(N−k) + C(k,2)

N=20, k=5 →  20 + 75 + 10 = 105 對
             對照循環賽 190 對，省約 45%
```

最終選出是 `i* = argmax_i w_i / c_i`。為什麼要除以 c_i？因為 pivot 參與的場次遠多於非 pivot（pivot 跟所有人比，非 pivot 只跟 k 個比），只看 w_i 的話，pivot 光靠場次多就會累積出比較大的數字。除以 c_i 換算成「平均每場贏多少」才公平。

### 預算對準確率

![一張表格，列出 pass@1、V1 在四種預算下、PPT 在 k=1 到 k=9、以及完整循環賽的查詢配對數與準確率。](img-018)
*圖七 — PPT 的預算與準確率權衡：k 愈大愈準，但報酬遞減得很快。（來源：原始論文。）*

在 N=20 候選、89 題、Terminus-2 harness（harness 指的是驅動 agent 的那層腳手架：工具介面、互動迴圈、終止條件）的設定下：

表裡的 V1 是論文拿來對照的前一代排名方法，`1N` 到 `7N` 指的是它花掉的比較預算倍率。要先說清楚的是，**論文全文沒有解釋 V1 怎麼運作**，只把它當基準線用。

| 方法 | 查詢配對數 | 準確率 |
|---|---|---|
| pass@1 | — | 52.64% |
| V1 (1N) | 1,400 | 64.64% |
| V1 (3N) | 4,200 | 65.62% |
| V1 (5N) | 7,000 | 65.85% |
| V1 (7N) | 9,800 | 65.53% |
| PPT k=1 | 2,570 | 65.83% |
| PPT k=5 | 6,609 | 66.27% |
| PPT k=9 | 9,630 | 67.13% |
| Full Round-Robin | 13,111 | 67.42% |

k 愈大愈準但報酬遞減得很快（k=1 到 k=9 只漲 1.3pp，預算卻變成將近 4 倍）；k=9 已經逼近完整循環賽（67.13% vs 67.42%），預算省 27%。基準線 V1 在 5N 之後不升反降，PPT 則是單調上升，這點是站得住的。

但有三個保留意見：

- **論文沒給選 k 的方法論**，只說 k 愈大愈好——但那樣就退化回循環賽了。
- **省下的幅度沒有想像中大**：k=9 相對循環賽只省 27%。O(N²) → O(Nk) 的漸進優勢要 N 夠大才明顯，N=20 還不到那個區間。
- **這張表的 N=20 是特別策展的設定**，這點最重要。主實驗的 N 只有 3 到 5，C(5,2)=10 對，PPT 幾乎省不了什麼——換句話說，那些 SOTA 數字裡，PPT 的貢獻其實很有限。

## 六、實驗結果：怎麼讀比讀到什麼更重要

四個 benchmark 用完全相同的流程：生成策略對每題產生 N 條候選 → verifier 用 PPT 兩兩評分 → 選出正規化分數最高者提交。這套流程有兩個關鍵性質：

1. **超參數全程固定**在 G=20、K=8、C=3，沒有針對個別 benchmark 調過。
2. **完全 training-free**，四個 benchmark 共用同一個框架，沒有任何領域 fine-tuning。

第二點是最重要的實務主張。如果成立，代表你可以直接套到自己的領域，不需要準備訓練資料。

### 主結果表要分兩半讀

![一張表格，左半是三個 benchmark 上各三個基準模型的準確率，右半是同一候選池上的 Pass@1、Oracle 上限與本方法的準確率。](img-010)
*圖八 — 主結果表。左半和右半是完全不同性質的比較，混著讀會得到錯誤結論。（來源：原始論文。）*

| Benchmark | Baseline #1 | #2 | #3 | Pass@1 | Oracle | Ours |
|---|---|---|---|---|---|---|
| Terminal-Bench V2 | GPT-5.5 (84.7%) | Opus 4.7 (80.2%) | G3.1 Pro (80.2%) | 83.1% | 92.1% | 86.5% |
| SWE-Bench Verified | Opus 4.5 (76.8%) | G3 Flash (75.8%) | M2.5 (75.8%) | 76.1% | 84.4% | 78.2% |
| MedAgentBench | Opus 4.8 (70.2%) | G3.5 Flash (66.3%) | GPT-5.5 (65.1%) | 70.2% | 75.0% | 73.3% |

（模型名稱沿用論文的縮寫寫法：Opus 是 Claude Opus 系列，G 開頭的是 Gemini 系列。）

```
┌─── 左半：其他模型成績 ───┐  ┌─── 右半：同一候選池 ───┐
│  不同 harness            │  │  Pass@1 → Oracle → Ours│
│  不同抽樣設定            │  │  完全可控的對照        │
│  ← 蘋果比橘子            │  │  ← 這才是 verifier 功勞│
└──────────────────────────┘  └────────────────────────┘
```

右半才是誠實的證據，因為同一批候選、同一個生成器，唯一變因是「怎麼挑」：

| Benchmark | Pass@1 → Ours | verifier 真正貢獻 | Oracle 落差 | 兌現比例 |
|---|---|---|---|---|
| Terminal-Bench V2 | 83.1% → 86.5% | **+3.4pp** | 9.0pp | 38% |
| SWE-Bench Verified | 76.1% → 78.2% | **+2.1pp** | 8.3pp | 25% |
| MedAgentBench | 70.2% → 73.3% | **+3.1pp** | 4.8pp | 65% |

回頭對照一開始的動機。在這個 N=5 的候選池上，oracle 只到 92.1%，可搶的空間是 9.0pp，而 verifier 兌現了其中的 38%；三個 benchmark 加起來，兌現比例落在 25% 到 65% 之間。至於圖一那個 98.9%，那是把 K 放大到很大時的理論天花板，跟這裡的 9.0pp 不是同一個尺度——真正拿來評分的應該是後者。

三個問題要標出來：

- **「SOTA」宣稱混雜了 harness 差異。** 86.5% 是 GPT-5.5 加上 Capy harness 加上 N=5 抽樣加上 verifier，而 84.7% 是 GPT-5.5 加上另一個 harness。三個變因不同，把差距全歸給 verifier 不成立，乾淨的比較是 83.1% → 86.5%。
- **RoboRewardBench 整列消失了。** caption 說涵蓋四個 benchmark，表格只有三列。它因為衡量的是 preference accuracy 而被移到另一張表，但 caption 沒說明。
- **SWE-Bench 的候選池是異質的。** N=3 是從三個不同模型各抽一條，Pass@1 是三模型平均，verifier 的任務其實變成「跨模型家族挑最好」。這是更有價值的應用場景（模型路由），但也讓它跟其他列不可直接比較。

### 最強的結果不在主表，在機器人上

![一張表格，比較五種方法在 RoboRewardBench 上的偏好準確率，本方法 87.4% 排名最高，同一個模型的離散 judge 版本只有 70.8%。](img-011)
*圖九 — 同一個模型，只改解碼方式，準確率從 70.8% 跳到 87.4%，還贏過兩個專門訓練的機器人 reward model。（來源：原始論文。）*

| 方法 | 準確率 |
|---|---|
| **LLM-as-a-Verifier（本方法）** | **87.4%** |
| RoboReward-8B（訓練過，約 4.5 萬 episode） | 81.4% |
| Robometer-4B（訓練過，約 100 萬筆比較） | 78.8% |
| TOPReward | 74.7% |
| LLM-as-a-Judge（同一個 VLM，離散） | 70.8% |

這比主表有說服力得多，理由有三個：

- **同一個模型的乾淨對照。** 87.4% 和 70.8% 是同一個 Qwen 3.6 35B，唯一差別是離散 argmax 對上連續期望值。這 16.6pp 是全篇最大、也最能歸因給方法本身的數字，完全沒有 harness 混雜。
- **直接驗證了第二個問題。** 一個零訓練的框架打贏兩個專門訓練的機器人 reward model。
- **跨模態。** 輸入從文字換成多幀影片，方法完全不用改。

還有一個附帶結果同樣值得記住：把 RoboReward-8B 的輸出改用連續公式解碼，與人類標註的 MAE 從 **1.11 降到 0.72**。也就是說，這套解碼方式可以直接加在既有的 reward model 上，不是非得從頭換掉。

不過論文完全沒有解釋，為什麼專門訓練的機器人 reward model 會在自己的領域輸掉。相關那節只列數字，沒有任何分析。另外有一層利益關係論文自己沒揭露：RoboRewardBench 是共同作者也掛名的 RoboReward 論文提出的，被比較的 RoboReward-8B 正是那篇的模型。

## 七、進度追蹤：一個論文講過頭的地方

連續分數還有第二種用法：不只能挑最好的，還能反映「agent 做到哪了」。論文定義了 Value-Order Correlation（VOC），把「步驟的時間順序」跟「verifier 對該步驟**前綴**的分數」算 Spearman 等級相關。分數完美隨步驟遞增，VOC 就趨近 1。

概念上這等同 RL 的 value function：V(s) 估「從此狀態出發的預期回報」，在往目標推進的軌跡上應該隨著接近目標而上升。

![一張折線圖，成功軌跡的 verifier 分數隨步驟穩定上升到接近 1.0，失敗軌跡的分數一路偏低，圖上標註了兩條軌跡各自的關鍵事件。](img-013)
*圖十 — 單一任務上的對照：成功軌跡分數穩定爬升，失敗軌跡在裝錯套件、磁碟爆掉之後一路低迷。（來源：原始論文。）*

```
成功軌跡：Read model.py → Install g++ → Install CPU-only torch
          → Update hidden_dim → DONE          分數持續上升 → ~1.0
失敗軌跡：不必要地裝 torchvision → 磁碟空間耗盡 → 編譯錯誤
                                               分數一路偏低
```

這張圖很有說服力。問題是**論文在這裡講得過頭了**。

論文主張 verifier 在停滯或走向失敗的軌跡上分數**大致持平**，因此同一個分數可以兼作進度量測與早期預警。但它自己的統計數字不支持這個說法——在 500 條 Terminal-Bench V2 軌跡上：

| 軌跡結果 | Spearman VOC |
|---|---|
| 成功 | 0.848 ± 0.012 |
| 失敗 | 0.769 ± 0.016 |
| **落差** | **+0.079** |

```
論文的敘事          實際數字
成功：上升 ↗        成功：0.848 ↗
失敗：持平 →        失敗：0.769 ↗（幾乎一樣在升）
                    落差：僅 0.079
```

0.769 是相當高的正相關，代表**失敗軌跡的分數也在隨時間穩定上升**，離「持平」（VOC ≈ 0）差得很遠。圖十是單一任務的單一案例，上表是 500 條軌跡的統計，論文選擇用前者當敘事主軸，卻沒討論後者為什麼落差這麼小。用 0.079 的落差做執行中的即時預警，鑑別力其實很弱。

機器人那邊的 VOC 數字倒是很漂亮（本方法 0.966，RoboReward-8B 0.877，Robometer-4B 0.780，TOPReward 0.565），但那是不同方法之間的比較，跟「成功 vs 失敗能不能區分」是兩回事。

### 附帶產物：TurboAgent

論文最後還附了一個工程產物 TurboAgent，給 Claude Code 及 OpenAI-API 相容客戶端用的擴充，以推論時的代理層（proxy）形式夾在客戶端與 LLM 供應商之間，兩邊都不用改：每個請求平行送出 N 條候選，用 PPT 選最好的回傳。想法不錯，但論文對它**沒有任何量化評估**——沒有延遲數字、沒有成本分析、沒有使用者研究，就是個概念驗證。

## 八、可以帶走的東西

**投資報酬率最高的一步：把現有 LLM-as-judge 的 argmax 換成讀 top-k logprobs 算期望值。** 二元或離散判斷變成連續分數，直接獲得排序能力與信心度。前提是要先確認你的 G 屬於「同一次呼叫就能拿到」那種讀法才是零成本；如果是另一種讀法，換 G 就要重跑。

**次一步是 criteria decomposition。** 輕量、可以直接套進任何 prompt-based judge。但子準則要自己設計——論文那組 Specification / Output / Errors 是為 reference-free 的 terminal 任務設計的，不見得適用其他情境，而論文也提供不了設計方法論。

**Repeated evaluation 概念最簡單，但成本線性增加**，而且記得它只降變異數、不降偏誤。

成本要自己算清楚：

```
每條軌跡的 LLM 呼叫次數 = C × K
主實驗設定 C=3, K=8  →  每條軌跡 24 次
```

再乘上 PPT 的比較對數，總量會很可觀。論文從未討論延遲與成本，這是套用前必須自己算的一筆帳。

最後一個實務提醒：如果你的情境**有 ground truth**，核心公式本來就是單條評分的形式，成對比較是外加的，只在「從 N 條選最好」時才需要。你可以只用單條評分那條公式，把 ground truth 放進 prompt。理論上會更好校準（判斷任務比 reference-free 簡單），但**論文從未驗證過這個用法**——所有實驗都是「選最好」或「兩兩比較」，沒有任何「單條對照 ground truth 判對錯」的實驗。不能假設 73.1% → 77.5% 那條曲線會重現，得自己跑 ablation。另外要注意，改成連續分數之後，你會被迫提前決定「多少分算對」的閾值。

## 結論

這篇論文的核心洞見很小、也很實在：**LLM 打分數時內部的信念是連續的，是 argmax 把它壓扁的**。把 argmax 換成期望值，平手率從 27% 降到 0%，排序能力就回來了。

技術上沒有一項是全新的，價值在於系統化打包和扎實的 ablation。而最值得記住的兩個數字都不在摘要裡：機器人 benchmark 上同一個模型只改解碼方式，準確率從 70.8% 跳到 87.4%；把這套解碼加在既有的 reward model 上，與人類標註的 MAE 從 1.11 降到 0.72。前者是全篇最乾淨的因果證據，後者說明這是個可以疊加的改動，不是非得整套換掉。

至於摘要裡那些 SOTA 數字，扣掉 harness 差異之後，verifier 真正的貢獻是 +2 到 3 個百分點。這個幅度不難看，但實際候選池上可搶的 oracle 空間也就 5 到 9pp，兌現了四分之一到三分之二——跟「把 oracle 的巨大潛力兌現」的敘事還有距離。

```figure-map
[
  {
    "id": "img-005",
    "references_manifest_caption": "Figure 5: Oracle Pass@𝐾reaches 98.9% on Terminal-Bench V2.",
    "why_used": "支撐「這個問題值得解決」的動機段落，把 Pass@1 與 oracle 上限之間的落差量化出來。",
    "agent_match_hint": "一張折線圖，橫軸是每個任務的軌跡數（對數尺度），一條藍色曲線爬升到 98.9%，另有兩條水平虛線標示 82.0% 與 69.4%。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2: Multiple modalities, many applications, one unified verification framework. We present LLM-as-a-Verifier, a general-purpose framework that provides fine-grained feedback for any modality without requiring additional training. By leveraging the full distribution of scoring-token logits, our method captures evaluation uncertainty and enables verification to scale along three dimensions: score granularity, repeated evaluation, and criteria decomposition. The resulting fine-grained feedback can be used for test-time scaling, progress tracking, and reinforcement learning.",
    "why_used": "在進入方法細節前給讀者一張框架全貌圖，先建立輸入、核心、下游用途的整體印象。",
    "agent_match_hint": "一張架構示意圖，左側三個方框寫著 Text／Image／Video，中間是含四個子方框與一條獎勵公式的大框，右側三個方框是下游應用。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Figure 4: Verification Scaling. We find that verification accuracy consistently improves as we scale across multiple dimensions: (1) the granularity of score tokens, (2) the number of repeated evaluations, and (3) the decomposition of evaluation criteria. Verification accuracy is measured as the pairwise accuracy",
    "why_used": "作為「三個 scaling 維度」整節的開場圖，讓讀者先看到三條上升趨勢，再逐一讀各維度的機制與批評。",
    "agent_match_hint": "三張並排的圖：左兩張是帶信賴區間的折線圖（橘色、綠色），右邊一張是四根帶誤差棒的長條圖，最後一根是紫色。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Table 2: Judges vs. Verifiers on query-optimize. Over 100 repeated evaluations, we count how often the correct trajectory is scored higher than (𝑠𝑐>𝑠𝑖), tied with (𝑠𝑐=𝑠𝑖), or lower than (𝑠𝑐<𝑠𝑖) the incorrect one. The discrete 1–5 judge produces ties in 88/100 evaluations. Taking the expectation over the same 1–5 scale eliminates ties and correctly ranks the trajectory in 69/100 evaluations. Increasing the score granularity to 𝐺=20 further improves discrimination, correctly ranking the trajectory in 77/100 evaluations.",
    "why_used": "支撐 query-optimize 案例的核心對照：一次只換一個變因（解碼方式、量表），平手率與排序正確率如何變化。",
    "agent_match_hint": "一張三列的表格，欄位包含 Method、Reward、以及三個計次欄位，欄標題帶有綠色勾與紅色叉的符號。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Figure 7: Verifier (continuous) vs. Judge (discrete) on Terminal-Bench V2 across 𝑘∈{1, 4, 16} repeated evaluations. Left: Pairwise verification accuracy. The verifier achieves 74.7% at 𝑘=1 and improves to 77.5% at 𝑘=16, consistently outperforming the judge across all evaluation budgets. Right: Tie rate. The judge produces ties in 26.7% of comparisons at 𝑘=1 due to coarse discrete scoring, decreasing to 5.5% at 𝑘=16 as averaging breaks ties. In contrast, the verifier yields zero ties.",
    "why_used": "支撐「judge 靠重複評估的改善主要來自打破平手，而非判斷力提升」這個論點，也用來說明兩者天花板不同。",
    "agent_match_hint": "兩張並排的長條圖，橫軸都是重複評估次數 1／4／16，左圖是驗證準確率（黃、綠雙色帶誤差棒），右圖是平手率，綠色柱全為 0.0%。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Figure 6: Probabilistic Pivot Tournament. A five-stage pipeline for selecting the best of 𝑁candidates under a constrained verification budget. (1) Candidates: the pool {𝜏1, . . . , 𝜏𝑁} to be ranked. (2) Ring pass: a random Hamiltonian cycle scores the 𝑁adjacent pairs so every candidate appears once in the “A” slot and once in “B”, canceling the model’s positional bias. (3) Pivot selection: candidates are ranked by their ring-pass scores 𝑤(𝑖), and the top-𝑘candidates form the pivot set 𝒫. (4) Pivot tournament: every non-pivot–vs–pivot and pivot–vs–pivot pair is scored via Eq. 3.2, concentrating the budget on uncertain top candidates and cutting cost from 𝒪(𝑁2) to 𝒪(𝑁𝑘). (5) Selection: comparisons are aggregated into win mass 𝑤𝑖and count 𝑐𝑖, and the candidate with the highest normalized 𝑤𝑖/𝑐𝑖is returned.",
    "why_used": "PPT 有五個階段、彼此有先後依賴，用流程圖比純文字更容易讓讀者建立整體結構。",
    "agent_match_hint": "一張橫向五階段流程圖，藍色編號圓圈標示 1 到 5，第二階段畫成一個環狀循環，最後一階段是一張小表格與獎盃圖示。"
  },
  {
    "id": "img-018",
    "references_manifest_caption": "Table 9: Probabilistic Pivot Tournament (PPT) scales with the number of pivots, achieving higher accuracy as 𝑘increases while maintaining a low verification budget on Terminal-Bench V2.",
    "why_used": "支撐 PPT 的預算與準確率權衡討論，也是「省下幅度沒有想像中大」這個保留意見的數據來源。",
    "agent_match_hint": "一張表格，三欄分別是 Method、Pairs queried、Accuracy (%)，列出 pass@1、四種 V1 預算、五種 PPT 的 k 值，最後一列是 Full Round-Robin。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "Table 3: Per-benchmark performance and gains from verification. Baseline accuracies (left) are obtained under a fixed agent harness. On the same candidate pools, we report Pass@1, the oracle Pass@𝑁upper bound, and the accuracy achieved by LLM-as-a-Verifier (right). Our method consistently improves over Pass@1 and recovers a large portion of the oracle headroom, achieving state-of-the-art performance on each.",
    "why_used": "主結果表，用來說明「左半與右半性質不同、必須分開讀」這個閱讀重點，以及 verifier 真正的貢獻幅度。",
    "agent_match_hint": "一張三列的表格，上方有 Baseline models (accuracy) 與 LLM-as-a-Verifier 兩組跨欄標題，列名是三個 benchmark 名稱。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Table 4: Preference accuracy on RoboRe- wardBench. LLM-as-a-Verifier outperforms trained robotics reward models.",
    "why_used": "全篇最乾淨的因果證據：同一個模型、只改解碼方式的 16.6pp 差距，支撐「最強結果不在主表」這一節。",
    "agent_match_hint": "一張窄長的兩欄表格，欄位是 Method 與 Accuracy (%)，五列方法，最後一列粗體標示為 ours 且數值最高。"
  },
  {
    "id": "img-013",
    "references_manifest_caption": "Figure 8: We observe a strong correlation between the chronological progression of code generation steps and the scores from LLM-as-a-Verifier. The example task above requires the agent to run MNIST inference. The successful trajectory follows a coherent sequence of events—Read model.py →Install g++ compiler →Install CPU-only torch →Update hidden_dim →DONE and exhibits consistently increasing verifier scores. In contrast, the failed trajectory is characterized by erroneous behaviors—it unnecessarily installs the large torchvision package, which exhausts the available disk space and hits a compilation error—resulting in significantly lower scores. Results are shown for the pytorch-model-cli task from Terminal-Bench V2, using Gemini 2.5 Pro with Terminus 2 and Gemini 2.5 Flash as the verifier.",
    "why_used": "呈現論文用來支撐進度追蹤主張的單一案例，接著對照 500 條軌跡的統計數字，指出敘事與數據的落差。",
    "agent_match_hint": "一張折線圖，綠色 SUCCESS 與紅色 FAILED 兩條曲線，圖上散布多個文字方框標註各步驟事件，如 READ model.py、NO Disk Space。"
  }
]
```
