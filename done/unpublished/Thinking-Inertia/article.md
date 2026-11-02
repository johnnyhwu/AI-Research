# 叫 LLM 不要思考，它就真的不想了嗎？Thinking Inertia 論文筆記

**來源**：[Thinking Inertia: LLMs Keep Thinking When Told Not To](https://arxiv.org/abs/2610.11765)（Dianqiao Lei、Kevin Qinghong Lin、Pan Lu、Philip Torr、James Zou，2026/10）

## 前言

很多推理模型都有「關掉思考」的選項：API 參數設成 no-think，或在提示詞裡叫它直接給答案。問題是，關掉之後，回應真的只剩答案嗎？這篇論文的答案是否定的。就看得到的回應文字而言，不管用參數還是提示詞，都沒辦法可靠地把推理關掉。論文把這個現象叫做 **thinking inertia**（思考慣性）。

只關思考開關時，六個模型合併來看，答案前出現明確推理的比例在是非題約 5%、選擇題約 46%，開放式題目幾乎 100%。開放式就算再加上「不要推理」的指令，仍有 62%，而且準確度會掉。

這篇文章依序回答三個問題：舊的判斷方式為什麼失效、論文怎麼改用回應內容來量、量出來的結果是什麼。最後整理限制。文中標（自編）的是筆記作者為了說明自己舉的例子，標（論文的解讀，未直接驗證）的是論文自己提出、但實驗沒有直接驗證的說法，其餘都是論文內容。另外要先講清楚：論文只量**可見的回應**，不對模型內部的運算下任何結論。

## 三個舊指標為什麼會誤判

判斷模型有沒有在思考，既有工作常看三樣東西：思考開關、特殊標記、輸出長度。三者共同的問題是，它們都不看回應的實際內容，所以會誤判。

![論文用三個表面指標判斷模型是否在思考，並展示它們各自失敗的案例。](img-002)
*圖 1 — 三種表面指標都無法辨認回應層級的「不思考」。（來源：原始論文 Figure 2。）*

圖 1 的 (b) 部分用同一題 `If 3x + 1 = 10, what is x?` 示範三種失敗方式：

| 舊指標 | 判斷依據 | 失敗案例 |
| --- | --- | --- |
| 1. 提示端控制 | 開關設成 no-think，就當作沒思考 | 開關已關，輸出仍寫出「兩邊減 1，$3x = 9$，再除以 3」 |
| 2. 特殊標記 | 沒有 `<think>` 區塊，就當作沒思考 | 沒有標籤，正文仍寫出「$3x = 9$，所以 $x = 3$」 |
| 3. 輸出長度 | 輸出夠短，就當作沒思考 | 只有一行 `3x = 9, so x = 3`，但這一行本身就是一步推導 |
*表 1 — 三種表面指標的失敗案例。（來源：整理自原始論文 Figure 2(b)。）*

誤判也會反方向發生。一句完全沒有題目內容的開場白，例如論文舉的 "Let me think about this. The answer should be `<ans>`"，裡面沒有任何推論，卻會被表面指標算成「有在思考」。

既然看開關、標籤、長度都不準，論文的做法就是直接檢查答案前面那段文字到底寫了什麼。

## 方法：把回應拆成 T 與 A，再用三層指標量 T

一句話版本：題目要求模型把最終答案放進 `\boxed{}`，最後一個可解析的答案就是 $A$，答案以外所有看得到的文字是 $T$（幾乎都出現在 $A$ 前面）。三層指標只量 $T$，準確度另外用 $A$ 評估。切分細節見〈先切開：T 與 A〉。

![論文 Figure 3：上半部是推論流程，題目經介入後送進模型，輸出拆成答案前文字與最終答案；下半部是六個回應案例。](img-003)
*圖 2 — 以回應為中心的「不思考」量測方式。（來源：原始論文 Figure 3。）*

圖 2 上半部是整個流程：題目 $Q$ 經過介入 $S(\cdot)$（提示詞、輸出限制、思考開關等）送進模型 $\pi$，輸出被拆成 $T$ 與 $A$。三層指標由嚴到寬依序是 ETR、QRel.、EIR。介入有哪幾種，見〈六種介入模式〉。

### 先切開：T 與 A

$$
\pi\big(S(Q)\big) = (T, A)
$$

- $Q$：一個題目
- $S(\cdot)$：套在題目外面的介入（提示、輸出限制、思考開關等）
- $\pi$：被測的語言模型
- $A$：最後一個可解析的最終答案
- $T$：$A$ 以外所有看得到的文字

說穿了就是以最終答案為界切開。（自編）拿圖 2 下半部的案例 2 來切（題目 $42 + 79 = ?$）：

| 部分 | 內容 |
| --- | --- |
| 完整輸出 | `Ones: 2+9=11, carry 1. Tens: 4+7+1=12. \boxed{121}` |
| $T$ | `Ones: 2+9=11, carry 1. Tens: 4+7+1=12.` |
| $A$ | `121` |

幾個邊界情況：

- **$T$ 不限格式。** 文字出現在 `<think>` 區塊、一般回答區，或只有一句開場白，都算 $T$；有獨立推理欄位的 API，欄位內容也算進 $T$。
- **「$T$ 在 $A$ 之前」是常態，不是硬性假設。** 在 535,208 筆含 `\boxed{}` 的輸出中，先給答案再解釋的只有 149 筆（約 0.028%，論文附錄 E），這些答案後面的解釋一樣計入 $T$。

### 層 1：ETR（Empty-Thinking Rate）

ETR 是最嚴格的檢查，只問一件事：$T$ 是不是完全空的。換句話說，有多少比例的輸出乾淨地只給答案。

$$
e_i = \mathbb{1}\{|T_i| = 0\}, \qquad \mathrm{ETR} = 100\% \times \frac{1}{N}\sum_{i=1}^{N} e_i
$$

- $i$：第 $i$ 個輸出
- $T_i$：第 $i$ 個輸出中 $A$ 以外的文字
- $|T_i| = 0$：$T_i$ 是空的，沒有任何實質文字
- $\mathbb{1}\{\cdot\}$：括號內成立為 1，否則為 0
- $e_i$：單一輸出的分數
- $N$：同一個模型、同一種介入、同一個 benchmark 下的輸出總數

也就是每個輸出各打 0 或 1，再取平均。

$e_i = 1$ 的條件比「$T$ 是空的」多一層：$A$ 必須可解析，而且整段輸出在允許的答案框之外沒有實質文字，包含 $A$ 之後的文字（嚴格檢查掃的是整段輸出）。所以格式壞掉、或給完答案又接解釋的輸出，一樣得 0。

ETR 的限制很明顯：$T$ 一旦非空，它就分不出那是空話、改寫題目，還是真正的推理。這就是需要層 2 與層 3 的原因。數字例子見〈三層合起來看：六個回應案例〉。

### 層 2：QRel.（Question–Pre-answer Relevance）

QRel. 補上一個連續分數，量 $T$ 和題目有多相關。它的角色是用「相關性」取代「長度」。

$$
\mathrm{QRel.}(Q_i, T_i) = \begin{cases} 0, & |T_i| = 0 \\ \cos\big(\phi(Q_i),\ \phi(T_i)\big), & |T_i| > 0 \end{cases}
$$

- $\phi$：embedding 編碼器，論文用 Qwen3-Embedding-4B
- $\phi(Q_i)$：題目加上查詢指令後編成的向量；指令是「給定一個問題，檢索包含回答此問題之推理的答案前文字」
- $\phi(T_i)$：把 $T_i$ 當成候選段落編成的向量
- $\cos$：兩個向量先各自除以自己的長度（$\ell_2$ 正規化），再取內積，也就是夾角的餘弦
- 第一行：$T_i$ 是空的，直接給 0

白話：空的給 0，不空的就看 $T$ 和題目在語意上靠得多近。選一個可以下指令的編碼器，是為了讓它比較的是「對回答這題有沒有用」，而不只是字面像不像。

報告值是全部 $N$ 個輸出的算術平均，空 $T$ 的 0 也算進去。所以 ETR 越高，平均 QRel. 自然越低。

（自編）假設有五個輸出，QRel. 分別是 0（空）、0.896、0.310、0.831、0.276（分數取自論文 Supplementary Table F.1）。平均是 $(0 + 0.896 + 0.310 + 0.831 + 0.276) / 5 \approx 0.463$。

QRel. 量的是相關，不是推理。一句相關的事實陳述，沒有任何推論，也可以拿高分。論文自己也把它定位成相關性訊號，不當作推理的證據。

### 層 3：EIR（Explicit Inference Rate）

EIR 用來把「相關」和「推理」分開：請一個 LLM 裁判逐筆判斷非空的 $T$ 裡有沒有明確的推理步驟。

裁判是 GPT-5.5，而且是盲測：它只看得到 $(Q_i, T_i)$，模型名稱、介入模式、最終答案 $A$、答案對錯、QRel. 分數全部隱藏。裁判從五個標籤選一個，並摘一段原文當證據；這段原文只給人檢查用，不進指標。

| 編號 | 標籤 | 判準 | 算進 EIR |
| --- | --- | --- | --- |
| 1 | 泛用／離題 | 開場白、格式字、離題內容，沒有針對題目的推論 | 否 |
| 2 | 只改寫 | 重述題目或給定事實，沒有用推論連起來 | 否 |
| 3 | 相關但無推論 | 給出相關的事實、定義或答案斷言，沒有推論步驟 | 否 |
| 4 | 明確推理 | 有演繹、計算、比較、排除、套用規則、從證據到結論或因果，且針對題目 | 是 |
| 5 | 無法判定 | 光看可見文字無法可靠分類 | 否 |
*表 2 — LLM 裁判的盲測評分標準。（來源：原始論文 Table 1。）*

門檻很低：只要有一個具體的推論步驟就算，即使很短、很淺，甚至最後算錯。

$$
\mathrm{EIR} = 100\% \times \frac{1}{N}\sum_{i=1}^{N} \mathrm{Judge}(Q_i, T_i)
$$

- $\mathrm{Judge}(Q_i, T_i)$：裁判選「明確推理」為 1，選其他四種為 0
- $N$：所有輸出的數量；空的 $T_i$ 不送裁判，直接算 0

EIR 就是「答案前有明確推理的輸出佔幾成」，分母和 ETR、QRel. 一樣是全部輸出。

### 三層合起來看：六個回應案例

圖 2 下半部用 $42 + 79 = ?$ 這一題示範三層指標怎麼一起運作。六個案例的最終答案都是 121，差別只在 $T$：

| 案例 | $T$ 的內容 | $e_i$（ETR） | QRel. | 裁判標籤（EIR） |
| --- | --- | --- | --- | --- |
| 1 | 空 | 1 | 0 | 不送裁判，Judge = 0 |
| 2 | 短，寫出個位相加進位、十位相加 | 0 | 高 | 明確推理，Judge = 1 |
| 3 | 短，只寫 `The answer is 121.` | 0 | 低 | 泛用，Judge = 0 |
| 4 | 長，案例 2 的算式加上前後說明 | 0 | 高 | 明確推理，Judge = 1 |
| 5 | 長，泛談數學很重要 | 0 | 低 | 泛用，Judge = 0 |
| 6 | 長，說明加法是什麼，再說和是 121 | 0 | 中 | 相關但無推論，Judge = 0 |
*表 3 — 同一題的六個回應在三層指標下的結果。（來源：整理自原始論文 Figure 3 下半部。）*

這張表說明了兩件事：

- **長度與相關性互相獨立。** 案例 2、3 一樣短，一個有算式、一個沒有；案例 4、5 一樣長，同樣一有一無。只看長度，兩組都會判錯。
- **相關不等於推理。** 案例 6 和題目有關，卻沒有推論步驟，只有層 3 分得出來。

（自編）把這六個案例當成六個輸出來算：ETR $= 1/6 \approx 16.7\%$，EIR $= 2/6 \approx 33.3\%$。兩者加起來不是 100%，因為案例 3、5、6 的 $T$ 非空，卻沒有推理。

### 六種介入模式

論文用六種模式來推動模型往「思考」或「不思考」的方向走：

| 模式 | 名稱 | 思考開關 | 額外加的內容 | 壓制力道 |
| --- | --- | --- | --- | --- |
| M1 | THINK-ON | 開 | 無 | −（鼓勵思考） |
| M2 | THINK-OFF | 關 | 無 | 0（基準線） |
| M3 | COT | 關 | "Think step by step." | −（鼓勵思考） |
| M4 | SOFT | 關 | "A very short lead-in is allowed, but do not explain." | + |
| M5 | STRICT | 關 | "Give the final answer directly without any reasoning." | ++ |
| M6 | PREFIX | 關 | 預填答案範本 `The answer is \boxed{` | +++（預填，獨立一支） |
*表 4 — 六種與題目無關的提示介入。（來源：原始論文 Table 2。）*

壓制力道一欄：− 代表鼓勵思考，0 是基準線，+ 越多代表壓制得越強；M6 的 +++ 是另一種手段，不是更強的 STRICT。

六種模式的題目，以及「把最終答案放進 `\boxed{}`」的要求都相同，差別只在思考開關和額外加的內容：

- M1、M3 是反方向的參照，用來引出思考。
- M2 是原生關閉，當作基準線。
- M4、M5 用自然語言逐步加強限制。
- M6 不加指令，而是直接預填答案範本。論文因此把它當成獨立的一支，而不是更強版的 STRICT。

## 實驗：關掉開關擋不住可見推理，題型越開放越明顯

**設定。** 六個模型：Qwen3-4B、Qwen3-32B、Qwen3-235B-A22B、DeepSeek-V4-Flash、GPT-5.4、Gemini-3-Flash。三種答案空間各兩個 benchmark：是非題（BoolQ、StrategyQA）、選擇題（MMLU、MMLU-Pro）、開放式（GSM8K、MATH）。所有指標的分母都是全部輸出。

**主結果。** 只關掉思考開關（M2）時，答案前仍有明確推理的輸出比例隨題型越開放而升高：是非題 5.15%、選擇題 45.57%、開放式 99.69%。這就是 thinking inertia：開關關了，模型還是照樣把推理寫出來。

![六個模型在三種答案空間下，於 THINK-ON、THINK-OFF、Step-by-step 三種模式的 ETR 長條與 EIR 點。](img-007)
*圖 3 — 開啟思考、關閉思考、逐步思考三種模式在六個模型與三種答案空間下的比較。（來源：原始論文 Figure 4。）*

加上嚴格指令之後呢？下表整理六個模型、六個 benchmark 合併後的 EIR（裁判為 GPT-5.5）：

| 答案空間 | M2 THINK-OFF | M5 STRICT |
| --- | --- | --- |
| 是非題 | 5.15% | 0.12% |
| 選擇題 | 45.57% | 25.39% |
| 開放式 | 99.69% | 62.00% |
*表 5 — 只關開關與加上嚴格指令時的 EIR（六模型合併）。（來源：整理自原始論文 Supplementary Table D.3。）*

從這裡可以讀出四個結果：

- **加強指令只能部分壓制。** M5 STRICT（"Give the final answer directly without any reasoning."）讓三種題型的 EIR 都下降，但開放式仍有六成以上的輸出帶著推理。
- **開放式要付準確度的代價。** 在思考可以完全關閉的五個模型上（不含 Gemini），從 M2 到 M5，開放式的 ETR 平均從接近 0 升到約 40%，準確度平均卻下降約 15 個百分點；是非題與選擇題的準確度大致持平。論文把這個取捨稱為 no-thinking–performance trade-off。
- **預填答案不是更強的 STRICT。** 從 M5 到 M6，選擇題與開放式的 ETR 平均下降（開放式回到接近 0），而 QRel. 與 EIR 在每種題型都回升。也就是說，預填範本反而讓模型更不會「只給答案」。
- **開關不是唯一的因素。** 只在提示裡加一句 "Think step by step"（M3），許多模型在是非題上就重新出現可見的明確推理，GPT-5.4 是例外。

為什麼開放式特別難壓？（論文的解讀，未直接驗證）開放式題目需要較多和任務相關的計算，所以模型比較難只給答案。

## 限制與要注意的地方

- **只量看得到的文字。** 整套指標和 $T$、$A$ 的切法都建立在可見回應上，不代表模型內部的運算；論文不對內部有沒有在運算下結論，所以「EIR 低」不等於「模型沒在想」。
- **真正判斷推理的只有層 3。** ETR 與 QRel. 的盲點見〈層 1：ETR（Empty-Thinking Rate）〉與〈層 2：QRel.（Question–Pre-answer Relevance）〉；能分出「有沒有推理」的只有 EIR，而它依賴 LLM 裁判。
- **比較的基礎不一致。** 〈實驗：關掉開關擋不住可見推理，題型越開放越明顯〉裡的 EIR 取自六模型合併，ETR 與準確度則取自不含 Gemini 的五模型平均，兩組數字不能直接對比。

## 結論

- 判斷模型有沒有在「不思考」，要看回應內容本身；開關、`<think>` 標籤、輸出長度都會誤判，而且兩個方向都會錯。
- 論文把回應拆成 $T$ 與 $A$，用 ETR（$T$ 是否為空）、QRel.（$T$ 和題目多相關）、EIR（$T$ 有沒有明確推理）三層由嚴到寬地量 $T$。
- 只關思考開關，可見的明確推理在是非、選擇、開放式分別約 5%、46%、近 100%；加上嚴格指令後開放式仍有 62%；另外在可完全關閉思考的五個模型上，開放式準確度平均下降約 15 個百分點。
- 預填答案範本和「Think step by step」這類提示也會改變結果，開關不是唯一的控制點。以上都只針對可見回應。

```figure-map
[
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2: Surface proxies fail to identify response-level no-thinking. (a) Three common proxies: 1. prompt-side control, 2. special reasoning tokens (e.g., <think>), and 3. generation token length. (b) On the same algebra question, disabling the thinking mode, omitting special thinking tokens, or producing a short output can each leave a visible inferential step before the final answer. These cases motivate sepa- rately evaluating strict answer-only compliance, pre-answer relevance, and visible explicit inference.",
    "why_used": "支撐〈三個舊指標為什麼會誤判〉一節，展示開關、特殊標記、輸出長度三種表面指標如何誤判。",
    "agent_match_hint": "一張分成 (a)(b) 的示意圖，(a) 列出三種表面指標，(b) 用 3x + 1 = 10 這題展示失敗案例。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 3: Response-centric metrics for measuring no-thinking. Top: the LLM inference process. A ques- tion Q is wrapped by an intervention S(·) to form the model input S(Q), which the model π maps to a response decomposed into pre-answer text T and final answer A. We evaluate the visible response through three levels: strict answer-only compliance (ETR), question–pre-answer relevance (QRel.), and LLM judge explicit inference (EIR); accuracy independently evaluates A. Bottom: six representative response cases to the same question “42 + 79 =?” vary in length, relevance, and inferential content while sharing the same final answer. Case 1 is answer-only (empty T), whereas Cases 2–6 use the non-empty-T labels from the mu- tually exclusive rubric in Table 1: Cases 2 and 4 are explicit reasoning, Cases 3 and 5 are generic/off-topic, and Case 6 is relevant non-inferential. Table 1 additionally defines paraphrase-only and unclear; represen- tative real outputs are provided in Appendix F.1.",
    "why_used": "支撐方法一節的流程說明（題目經介入送進模型、輸出拆成 T 與 A），以及六個回應案例的表 3。",
    "agent_match_hint": "上半部是推論流程示意圖，下半部是 42 + 79 這題的六個回應案例與三層指標。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Figure 4: Think-on (M1), Think-off (M2), and Step-by-step (M3) across six models and three answer- space families. Rows show modes; the columns pair ETR bars with EIR points (left) and QRel. bars with visible pre-answer length for the four models with complete length traces (right). Gray dashed segments mark six-model means for ETR and QRel.; black triangles connected by dark lines mark the mean EIR; colored marks follow the model legend.",
    "why_used": "支撐實驗主結果：關掉思考開關後，答案前的明確推理比例隨題型越開放而升高。",
    "agent_match_hint": "多列多欄的長條圖加散點圖，列為 THINK-ON、THINK-OFF、Step-by-step 三種模式，欄為三種答案空間，包含六個模型。"
  }
]
```
