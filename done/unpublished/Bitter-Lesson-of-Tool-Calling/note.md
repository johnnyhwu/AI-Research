# The Bitter Lesson of Tool Calling — 論文筆記

**論文**：*The Bitter Lesson of Tool Calling*，Ishan Patel, Sahil Sen, Elias Lumer, Vamse Kumar Subbiah（PricewaterhouseCoopers），arXiv 2608.06370v1，2026年8月

---

## 30 秒版本

這篇論文比較兩種讓 LLM 呼叫外部工具的介面：**JSON tool calling**（模型輸出結構化 JSON 物件，業界標準做法）vs. **Programmatic Tool Calling（PTC）**（模型改寫一段 Python script 去呼叫工具）。實驗涵蓋 14 個模型（Anthropic 5 個、OpenAI 9 個，橫跨 2024/11–2026/7 發布），在 BFCL v4 這個 benchmark 上做主測試，另外加三個消融實驗（連鎖呼叫、高扇出、上下文汙染）。

**研究價值：接近零。** PTC 這個想法不是本文提出的（CodeAct、smolagents、Cloudflare Code Mode 都已經在做），本文的定位是「系統性實測」，但實測品質有明顯瑕疵：多個 headline 結論拆開後發現是同一個軟體 bug 造成的假訊號、或是摘要宣稱的數字在內文找不到對應的支撐數據。

**工程價值：中等，但要挑著信。** 真正站得住腳、可驗證的發現只有一個：JSON tool calling 在極高扇出（並行呼叫數）下有結構性的硬上限，會突然崩潰而不是漸進變差；但這個發現只在單一模型（Claude Sonnet 5）上驗證過，不能直接推廣。

這篇筆記的核心價值不在複述論文結論，而在下面「概念索引」列出的幾個判讀與設計層面的觀念——這些獨立於這篇論文本身是否站得住腳，都是值得學起來的東西。

---

## 概念索引（本筆記核心內容，建議優先讀這裡）

- [A. Tool-calling benchmark 測的是什麼？](#a-tool-calling-benchmark-測的是什麼)
- [B. Echo-return stub：為什麼「連鎖呼叫」測試沒有測到你以為的東西](#b-echo-return-stub)
- [C. Stop middleware：比較兩個系統時如何鎖死混淆變因](#c-stop-middleware)
- [D. Enumeration accuracy vs. Aggregation accuracy](#d-enumeration-vs-aggregation)
- [E. 程式碼介面的武斷性問題，與一條可遷移的選型規則](#e-程式碼介面的武斷性問題)
- [F. 讀 benchmark 論文的三個判讀習慣](#f-讀-benchmark-論文的三個判讀習慣)

---

## 背景知識

**BFCL（Berkeley Function-Calling Leaderboard）**：業界常用的 tool-calling 準確度 benchmark，本文用的是第 4 版（v4）。

**Wilson confidence interval（Wilson CI）**：一種計算比例型資料信賴區間的統計方法，比常見的常態近似法在樣本數小或比例接近 0%/100% 時更準確。本文所有表格的 `±` 欄位都是 95% Wilson CI 的半寬——區間越寬，代表該筆準確率的數字越不可靠，樣本數小的消融實驗（n=31~52）尤其如此。

**\n 逃逸字元 bug**：本文反覆出現的一個失效模式。部分模型在生成 multiline Python script 時，把「換行」寫成字面上的兩個字元 `\` 和 `n`，而不是真正的斷行符號。這種程式碼丟進 shell subprocess 執行會直接產生語法錯誤，整筆任務算 0 分。受影響的模型：GPT-4o、GPT-4.1、GPT-5.4-mini。

---

## 兩種範式的設計（Figure 1）

> Figure 1 原文 caption：*"Overview of the two primary paradigms evaluated. In JSON tool calling, the model emits JSON tool-call objects via the API. In programmatic tool calling, it writes a Python script using typed stubs; the agent loop executes it in a subprocess. A filesystem-discovery condition is included as a secondary reference point."*

**JSON tool calling**（現行業界標準做法）：

```
System Prompt 內含工具的 JSON schema
  → LLM Turn 1：輸出一個 JSON tool-call 物件（呼叫 f1）
  → Tool runtime 執行 f1，回傳結果塞回對話
  → LLM Turn 2：讀到 f1 的回傳，輸出呼叫 f2 的 JSON 物件
  → ……每多一個函式呼叫，多消耗一次 LLM 推論
```

**Programmatic Tool Calling（PTC）**：

```
System Prompt 內嵌一份 typed Python stub module
（每個工具對應一個 stub 函式，簽名跟真實工具一致）
  → LLM 只寫「一次」Python script，import 這個 module，
    在同一支 script 裡呼叫所有需要的函式
  → Agent loop 把這支 script 丟進 shell subprocess 執行
  → Scorer 解析 subprocess 印出的 stdout，抽出函式名稱與參數
  → 「stop middleware」（見 [C](#c-stop-middleware)）攔截下一次模型呼叫、
    強制終止 agent loop
```

**Worked example**（Appendix B.1，simple_python 類任務）：任務是「求底 10、高 5 的三角形面積」。工具 stub 定義：

```python
def calculate_triangle_area(
    base: int, height: int,
    unit: str | None = None) -> dict:
    return _rpc.call('calculate_triangle_area',
        base=base, height=height, unit=unit)
```

模型輸出的 PTC script：

```python
from stubs import calculate_triangle_area
result = calculate_triangle_area(base=10, height=5)
print(__import__('json').dumps(result))
```

subprocess 印出：`{"calculate_triangle_area": {"base": 10, "height": 5}}`。評分程式只核對函式名稱跟參數是否跟 ground truth 一致（見 [A](#a-tool-calling-benchmark-測的是什麼)）。

---

## 實驗設計總覽

14 個模型（Table 1）：Anthropic 5 個（Haiku 4.5、Sonnet 4.5、Sonnet 4.6、Opus 4.8、Sonnet 5），OpenAI 9 個（GPT-4o、GPT-4.1、GPT-5-nano、GPT-5、GPT-5.4-mini、GPT-5.4、GPT-5.6-Luna/Sol/Terra），全部在溫度 0 下執行。BFCL v4 的 309 筆代表性子集涵蓋 8 個任務類別。另外設計三個消融實驗，各自針對「PTC 比較強」這個宣稱裡最常被質疑的任務結構：連鎖呼叫（chaining）、高扇出（parallelism）、上下文汙染（context rot）。

---

## 主要結果（Table 2）

> 原文 caption：*"Accuracy (%) on our 309-entry BFCL v4 subset. JSON = JSON tool calling; PTC = programmatic tool calling. ± columns show 95% Wilson CI half-widths."*

| 模型 | JSON | PTC | 差異 |
|---|---|---|---|
| Haiku 4.5 | 81.9 | 85.8 | +3.9 |
| Sonnet 4.5 | 86.4 | 87.7 | +1.3 |
| Sonnet 4.6 | 80.9 | 87.4 | +6.5 |
| Opus 4.8 | 84.8 | 84.8 | 0.0 |
| Sonnet 5 | 84.5 | 86.1 | +1.6 |
| GPT-4o | 81.9 | 55.0 | −26.9 |
| GPT-4.1 | 81.9 | 62.1 | −19.8 |
| GPT-5-nano | 66.7 | 68.3 | +1.6 |
| GPT-5 | 71.5 | 76.1 | +4.6 |
| GPT-5.4-mini | 79.3 | 55.0 | −24.3 |
| GPT-5.4 | 79.3 | 81.9 | +2.6 |
| GPT-5.6-Luna | 76.1 | 80.3 | +4.2 |
| GPT-5.6-Sol | 72.2 | 82.8 | +10.6 |
| GPT-5.6-Terra | 73.5 | 84.1 | +10.6 |

**模式跟著模型世代走、不跟著廠牌走**：Anthropic 五個模型全部打平或小贏，沒有世代差異；OpenAI 分裂成兩群——最新三個 GPT-5.6 全部大贏，GPT-4o / GPT-4.1 / GPT-5.4-mini 三個慘跌，全部歸因於 \n 逃逸字元 bug。排除這三個模型後，headline 的「11/14 打平或超車」其實比表面數字更一致。

---

## 消融實驗一：Chaining（Table 3）

> 原文 caption：*"Chaining ablation accuracy (%, n = 52, chain lengths 2–20)."*

n=52，鏈長 2–20。測「f2 的參數依賴 f1 的執行結果」這種依序相依的多跳呼叫。

| 模型 | JSON | PTC |
|---|---|---|
| Haiku 4.5 | 88.5 | 73.1 |
| Sonnet 4.5 | 90.4 | 88.5 |
| Sonnet 4.6 | 90.4 | 92.3 |
| Opus 4.8 | 80.8 | 94.2 |
| Sonnet 5 | 80.8 | 96.2 |
| GPT-4o | 92.3 | 86.5 |
| GPT-4.1 | 98.1 | 40.4（\n bug 崩盤） |
| GPT-5-nano | 69.2 | 80.8 |
| GPT-5 | 92.3 | 92.3 |
| GPT-5.4-mini | 76.9 | 80.8 |
| GPT-5.4 | 94.2 | 90.4 |
| GPT-5.6-Luna | 82.7 | 92.3 |
| GPT-5.6-Sol | 96.2 | 90.4 |
| GPT-5.6-Terra | 98.1 | 96.2 |

排除 GPT-4.1 這個 bug 造成的異常值後，14 個模型裡是 6 勝 6 敗 1 平，且多數模型的 95% CI 互相重疊。**這張表本身看不出兩種範式在連鎖呼叫任務上誰有系統性優勢。**

**論文摘要與 Introduction 宣稱「PTC 在連鎖呼叫上的優勢隨鏈長增加擴大，鏈長 ≥12 時達到 18.8% 的絕對差距」——這句話論文全文找不到任何按鏈長分組的數據去支撐，§4.2 的討論只用了這張聚合表（鏈長 2–20 全混在一起）跟 GPT-4.1 的異常值。摘要宣稱的具體數字與正文呈現的數據之間存在落差，論文沒有交代。**

延遲面的附帶發現（§5.3）：13/14 個模型下，PTC 完成一筆連鎖任務的實際時間約為 baseline 的一半（因為省掉「等回傳、再打一次 LLM」的往返）。例外是 GPT-5，PTC 延遲反而是 baseline 的 2.8 倍，論文解釋是它的 reasoning 輸出拉長，把省下的時間吃回去了。

---

## 消融實驗二：Parallelism（Table 4）

> 原文 caption：*"Parallelism ablation accuracy (%, n = 32). Enumeration and overall accuracy are identical for all models here; aggregation accuracy is discussed separately in the text."*

n=32，扇出數 7–48。多數模型兩邊都是 100%，這張表本身看不太出差異。

| 模型 | JSON | PTC |
|---|---|---|
| Haiku 4.5 / Sonnet 4.5 / Sonnet 4.6 / Opus 4.8 / Sonnet 5 / GPT-4o / GPT-5.4-mini / GPT-5.4 / GPT-5.6-Luna / GPT-5.6-Terra | 100.0 | 100.0 |
| GPT-4.1 | 96.9 | 90.6（\n bug） |
| GPT-5-nano | 78.1 | 87.5 |
| GPT-5 | 71.9 | 96.9 |
| GPT-5.6-Sol | 96.9 | 100.0 |

真正有意義的發現在 §5.2 的額外探測實驗：作者對 **Claude Sonnet 5 一個模型**，把扇出數推高到 N=60, 70, 72, 75, 100：

```
JSON tool calling enumeration 準確率：
  N ≤ 70 → 100%　N = 72 → 75%　N = 100 → 0%（結構性崩潰，不是漸進衰退）

PTC enumeration 準確率：
  N = 72 → 100%　N = 100 → 100%（完全沒受影響）
```

這是全篇論文我認為最站得住腳的發現：JSON tool calling 要求模型把 N 個呼叫全塞進單次回應，數量一多就開始遺漏；PTC 用迴圈或 `asyncio.gather` 表達「呼叫 N 次」，不受回應長度限制。**但這個崩潰只在 Sonnet 5 一個模型上量到——論文自己提到 GPT-5.6-Sol 在 N=100 完全沒有這個問題，只能算是「觀察到的現象」，不是可推廣的普遍結論。**

**Enumeration accuracy vs. Aggregation accuracy** 的區分見 [D](#d-enumeration-vs-aggregation)。

**Token 成本交叉點**：N≈26 是損益平衡點。N<26 時 PTC 較貴（system prompt 要塞整份 stub module 是固定成本）；N>26 後 JSON tool calling 較貴（N=30 時 JSON 3559 tokens vs PTC 3380；N=48 時 JSON 5097 vs PTC 3535）。

---

## 消融實驗三：Context Rot（Table 5）

> 原文 caption：*"Context rot ablation accuracy (%, n = 31 per condition). Filtered = entry-relevant schemas only; Flood = 128 total schemas (relevant + corpus decoys). JSON = JSON tool calling; PTC = programmatic tool calling; Arg = filesystem-discovery."*

n=31，兩種情境：**Filtered**（只放任務相關的工具 schema）vs. **Flood**（塞進 128 個 schema，多數是不相關的誘餌）。

| 模型 | JSON (F→Fl) | PTC (F→Fl) | Arg (F→Fl) |
|---|---|---|---|
| Haiku 4.5 | 93.5→87.1 | 83.9→77.4 | 48.4→25.8 |
| Sonnet 4.5 | 90.3→93.5 | 83.9→80.6 | 58.1→29.0 |
| Sonnet 4.6 | 93.5→87.1 | 83.9→87.1 | 83.9→32.3 |
| Opus 4.8 | 87.1→83.9 | 83.9→80.6 | 90.3→41.9 |
| Sonnet 5 | 87.1→90.3 | 87.1→87.1 | 80.6→45.2 |
| GPT-4o | 96.8→90.3 | 51.6→74.2 | 61.3→16.1 |
| GPT-4.1 | 83.9→80.6 | 51.6→64.5 | 41.9→19.4 |
| GPT-5-nano | 74.2→64.5 | 54.8→71.0 | 25.8→16.1 |
| GPT-5 | 77.4→74.2 | 67.7→77.4 | 48.4→32.3 |
| GPT-5.4-mini | 80.6→87.1 | 45.2→80.6 | 54.8→12.9 |
| GPT-5.4 | 80.6→77.4 | 83.9→77.4 | 64.5→9.7 |
| GPT-5.6-Luna | 83.9→80.6 | 77.4→74.2 | 35.5→6.5 |
| GPT-5.6-Sol | 77.4→71.0 | 80.6→80.6 | 32.3→12.9 |
| GPT-5.6-Terra | 64.5→71.0 | 80.6→80.6 | 35.5→12.9 |
| **平均變化** | **−2.3** | **+5.5** | **−32.0** |

**Arg（filesystem-discovery）**：論文明確說明這不是業界常見做法，是作者額外加的內部參考點（"not an industry practice"，"an internal reference point"）。**論文沒有交代 Arg 的具體實作機制**——只給了 "filesystem-discovery"、"file-based tool delivery" 這幾個詞，沒有像 Figure 1 對另外兩種範式那樣畫圖或給實作細節。

值得注意：Arg 在 **Filtered**（零額外雜訊）條件下就已經比 JSON tool calling 平均低了約 30 個百分點——如果 Arg 的弱點只是「雜訊下搜尋容易失敗」，那在沒有雜訊的 Filtered 條件下不該輸這麼多。論文把 Arg 的退步完全歸因於「context navigation 在雜訊下的結構性弱點」，但這個歸因沒有解釋 Filtered 條件下的基礎落差，論文在這裡沒有把機制交代清楚。

**PTC 在 Flood 下平均進步（+5.5）**：論文解釋是部分模型在 Filtered 情境下被嚴格的型別限制卡住，Flood 情境下因為看到更多同類型工具範例反而更容易辨認出正確函式。**這個解釋論文沒有給出機制細節，也沒有做對照實驗驗證。** 貢獻最大的三個模型（GPT-5.4-mini +35.5、GPT-4o +22.6、GPT-4.1 +12.9）剛好就是本文其他地方受 \n 逃逸字元 bug 影響的同一批模型；論文沒有討論或排除這個關聯的可能性。

---

## 論文自陳的限制（§7 Limitations）

論文自己列出四點，值得直接記錄，不需要展開懷疑：
1. BFCL v4 用 echo-return stub（見 [B](#b-echo-return-stub)），測的是參數序列化正確性，不是端到端工具使用的正確性。
2. 消融實驗樣本數小（n=31–52），個別模型數字信賴區間寬，只有跨模型的整體模式（如「11/14 打平或超車」「flood 下 PTC 平均進步」）夠大到可以解讀。
3. 一份針對 BFCL v4 的獨立審計（Vaghasiya et al. 2026）發現其 LLM-judge 模式有 20% 跟人類評分不一致；本文用的是確定性字串比對評分（不是 LLM judge），繞開了這個問題，但 benchmark 本身的 ground-truth 標籤仍可能帶有審計沒抓出的雜訊。
4. PTC 相對 JSON tool calling 有固定的 input token 開銷（system prompt 要嵌入完整的 stub module 原始碼），在連鎖呼叫消融裡 PTC 用了 1.5 倍的 input token；這個劣勢在高扇出情境下會反轉（見消融二的 token 成本交叉點）。

---

## 概念段落

### A. Tool-calling benchmark 測的是什麼？

像 BFCL 這類 function-calling benchmark，從設計上就不是在驗證「工具執行後算出的最終結果對不對」，而是「模型有沒有選對函式、填對參數」。Ground truth 是一組事先定義好的 `(函式名稱, 參數)` 配對，模型輸出的呼叫只要跟這組配對做字串比對吻合就算對，完全不涉及「如果這個函式真的執行，算出來的數字對不對」。

這樣設計的原因：如果要驗證最終結果，就得架一套真的會運算的後端服務，這樣整個 benchmark 會變昂貴、難重現、還要處理外部服務的不確定性。所以這類 benchmark 普遍選擇退一步，只測「工具選擇與參數化能力」，把「工具背後真的算出什麼」排除在評分範圍之外。

理解這點很重要：任何用 BFCL 這類 benchmark 做結論的論文，量的都是「格式與呼叫正確性」，不是「任務有沒有真的被解決」。

### B. Echo-return Stub

本文用的工具 stub 不會真的執行運算，只會把收到的參數原封不動包成一包資料丟回來（例如收到 `radius=7`，回傳 `{"circumference": {"radius": 7}}`，不會回傳算出來的數字 43.98）。這種設計叫 echo-return：便宜、快、可重現，但代價是「工具真的算出了什麼」這件事完全測不到。

這對連鎖呼叫（chaining）實驗有直接影響：任務要求「用 f1 的結果當 f2 的參數」，但 f1 從來不會給出真正算出來的數字。所以無論哪種範式，模型唯一能完成任務的辦法就是自己用參數知識/數學能力把中繼值算出來，再填進第二次呼叫——工具本身完全不參與這個計算。也就是說，chaining 測試表面上看起來在測「模型有沒有正確串接前後呼叫」，實際上測的更接近「模型自己會不會算數學、函式簽名填得對不對」。

論文對 JSON tool calling 中間步驟拿到的「回傳值」是否也是同樣的 echo-return 設計，沒有給出明確的文字說明。Figure 1 的圖說裡對 JSON tool calling 那欄的回傳值有一句附註：*"Return value shown only to illustrate dependency for chaining"*（該回傳值僅用來示意依賴關係），Appendix C 對 stub 的描述也是套用在「跨範式共用的同一套工具語意」上。這兩處線索都指向「兩種範式可能面對的是同一套 echo-return 工具」，但論文沒有用一句話把這件事講清楚——這是論文文字本身含糊、可以有兩種讀法的地方，不是本筆記替它下的定論。

### C. Stop Middleware

Middleware 這個詞借自一般軟體工程（尤其是 web framework），指插在兩個元件之間、攔截並處理訊息流的一層。本文的 stop middleware 攔截的是「agent loop 準備再打一次的 LLM API 呼叫」，攔下來後直接終止整個迴圈。

它要解決的問題：兩種範式天生消耗的 LLM 呼叫次數不同。JSON tool calling 做一條長度 n 的連鎖呼叫，天生要 n 次 turn；PTC 理論上一次 turn 就能把整條鏈寫完。如果放任 agent loop 在 PTC 執行完 subprocess 後繼續問模型一次，這次額外的 turn 會讓模型看到 subprocess 真實印出的結果，等於多了一次修正機會——這個修正機會如果沒被鎖住，PTC 的準確率提升就分不清楚是「程式碼這個介面本身比較好」還是「多吃了一次免費的修正機會」。Stop middleware 把兩邊的 LLM 呼叫次數鎖成一樣，讓準確率的差距能乾淨地歸因於範式選擇本身。

這是一個可以獨立遷移的實驗設計原則：比較兩個系統時，要先確認除了想測的那個變因外，其他資源消耗（這裡是推論次數，也可能是時間、token 數等）有沒有被控制住，否則贏的可能只是「資源用得比較多」，不是方法本身更好。

### D. Enumeration vs. Aggregation

高扇出（parallelism）消融裡有一類任務是「這 N 個項目裡，哪 3 個符合某條件」。PTC 底下，部分模型會直接用參數知識講出答案，完全沒有真的把 N 次查詢跑過一遍。用「最終答案對不對」（aggregation accuracy）來評分，這種行為會被誤判成「做對了」，但工具其實沒被真正呼叫過。

論文因此把 enumeration accuracy（是否真的發出全部 N 次工具呼叫）當成主要指標，而不是 aggregation accuracy——這個判斷是對的，因為它測的才是「行為是否合規」，而不是「結果是否碰巧正確」。這個區分是一個通用的 agent 評測設計手法：任何允許模型跳過工具、直接用內部知識回答的系統，都需要把「行為有沒有真的發生」跟「最終結果對不對」拆成兩個獨立指標，否則會系統性高估工具使用的真實發生率。

### E. 程式碼介面的武斷性問題

PTC 的執行方式（至少在本文的實作裡）要求模型在「看到任何真實執行結果之前」，把整條邏輯一次寫進一支 script。遇到需要權衡、需要模糊判斷的地方，程式碼只能寫成 `if/else`、threshold、布林條件——沒有辦法像自然語言那樣說「這兩個選項差不多，但 A 稍微更合適，因為……」這種帶著猶豫、多因素權衡的判斷。自然語言可以表達模糊地帶，程式碼被迫把模糊地帶壓縮成一個明確的分支條件。

這件事跟本文的評測範圍有直接關係：BFCL 的評分標準是「函式名稱與參數是否精確吻合 ground truth」，是一個徹頭徹尾封閉式、非黑即白的任務類型。本文只在這種任務上測試兩種範式，等於選了一個結構上偏袒 PTC 的測試場——封閉式、決定性的任務正是程式碼最擅長表達的東西。本文完全沒有測試任何帶模糊判斷的任務（例如回應語氣是否合適、兩個候選答案哪個更貼合使用者意圖），所以「程式碼介面在開放式判斷任務上可能給出過度武斷的答案」這個弱點，本文的實驗設計從一開始就沒有能力揭露。

另外要注意，本文的 PTC 實作被 stop middleware 強制成「一次寫完整支 script、執行完就結束」，不允許模型看到真實執行結果後再寫下一段程式碼。這是本文為了控制 LLM turn 數公平性而做的特定設計選擇，不是「用程式碼當工具介面」這件事本身的必然限制——允許多輪程式碼執行、每輪之間插入自然語言反思的 PTC 實作（例如一般的 code-agent 產品），武斷問題可能沒有本文這個受限版本這麼嚴重，但代價是失去「一次 turn 搞定」的效率優勢。

**可遷移的選型規則：**

| 任務性質 | 建議範式 | 原因 |
|---|---|---|
| 封閉式、有明確對錯（數學、結構化資料轉換、確定性 API 串接） | PTC（可一次性 commit） | 不需要中途反思，程式碼的決定性是優勢不是缺點 |
| 開放式、需權衡模糊標準、依賴真實中繼結果調整策略 | JSON tool calling，或允許多輪執行的 PTC | 需要在步驟之間插入自然語言判斷，一次性 commit 的程式碼會把模糊判斷壓成武斷的二元決策 |
| 高扇出、大量獨立且確定性的呼叫 | PTC | 迴圈不受回應長度限制（但只有單一模型的證據） |

### F. 讀 Benchmark 論文的三個判讀習慣

1. **先拆解 headline 聚合數字，再相信它**：看到「11/14 模型打平或超車」這類聚合統計，先問這個數字是不是被少數模型的異常值拉動的。本文的例子是同一個 \n 逃逸字元 bug 在三個模型上反覆出現，把整體數字撐高或壓低。平均值掩蓋變異，永遠先問變異來自哪裡。

2. **檢查效應是跟著模型世代走、還是跟著廠牌走**：如果一個現象只跟時間軸（新舊）相關、不跟廠牌相關，通常指向的是某個具體 bug 或訓練資料裡新增的能力，而不是「這個架構/廠牌天生比較適合」。本文自己用了這個框架區分 Anthropic（全世代通過）跟 OpenAI（新舊分裂），值得當成一個通用的判讀濾鏡。

3. **區分「結構性斷崖」跟「漸進式衰退」是兩種不同的失效模式**：JSON tool calling 在 N=70→72 的行為是突然崩潰，不是慢慢變差——這種斷崖通常代表系統裡有一個固定容量的資源（例如單次回應的 token 上限、生成長列表時的注意力限制）。設計任何有輸出長度或並行度上限的系統時，值得假設會有這種斷崖存在，主動去測出門檻在哪，而不是假設效能會平滑下降。

---

## 值得帶走的東西

### 這篇論文本身的貢獻

近乎零。核心想法（用程式碼取代 JSON 當工具呼叫介面）不是本文提出的；本文交出的「系統性實測」品質也有明顯瑕疵——headline 結論裡混雜著同一個軟體 bug 造成的假訊號、摘要宣稱的具體數字（18.8% 差距）在正文找不到支撐數據、部分關鍵條件（Arg baseline 的機制）完全沒有交代清楚。唯一站得住腳的具體發現——JSON tool calling 在高扇出下有結構性硬上限——也只在單一模型上驗證過。

### 通用、可遷移、不受限於這篇論文的東西

1. **Benchmark 評分範圍的認知**：tool-calling benchmark 測的通常是「呼叫格式對不對」，不是「任務有沒有真的被解決」（[A](#a-tool-calling-benchmark-測的是什麼)）。
2. **Echo-return stub 這類簡化評分機制的取捨**：便宜、可重現，但會讓某些能力（工具真的被依賴）測不出來；設計 eval 系統時，「測不到什麼」要跟「測到了什麼」同等重要地寫清楚（[B](#b-echo-return-stub)）。
3. **用資源消耗鎖死混淆變因（stop middleware）的實驗設計紀律**：比較兩個系統時，先確認除了目標變因外，其他資源消耗是否被控制住（[C](#c-stop-middleware)）。
4. **Enumeration accuracy vs. aggregation accuracy 的區分**：任何允許模型跳過工具、直接用內部知識回答的系統，都需要把「行為是否真的發生」跟「結果是否正確」拆成獨立指標（[D](#d-enumeration-vs-aggregation)）。
5. **程式碼介面在開放式判斷任務上的武斷性問題，以及對應的選型規則**（[E](#e-程式碼介面的武斷性問題)）：封閉式、決定性任務適合一次性 commit 的 PTC；開放式、需要權衡的任務適合 JSON tool calling 或允許多輪反思的 PTC。這點在本文的實驗設計裡完全沒被測到，因為 BFCL 本身就是封閉式任務。
6. **讀 benchmark 論文的三個判讀習慣**：拆解 headline 聚合數字、檢查效應跟世代還是廠牌相關、區分結構性斷崖與漸進衰退（[F](#f-讀-benchmark-論文的三個判讀習慣)）。
