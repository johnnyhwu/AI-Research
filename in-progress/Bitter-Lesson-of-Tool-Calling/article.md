# JSON Tool Calling vs. 程式碼呼叫工具：一篇評測論文教我們的，是怎麼測而不是誰贏

## 前言

如果你的 agent 系統需要呼叫外部工具，現行業界標準做法幾乎都是同一套：讓模型輸出一段結構化的 JSON，描述要呼叫哪個函式、帶什麼參數。但這幾年也有另一派做法逐漸成形：讓模型直接寫一段 Python script 去呼叫工具，也就是 Programmatic Tool Calling（下面簡稱 PTC）。CodeAct、smolagents、Cloudflare 的 Code Mode 都是這個路線的代表。

《The Bitter Lesson of Tool Calling》這篇論文（arXiv 2608.06370v1）想做的，是把這兩種介面拿去對打：找 14 個模型、跑 BFCL v4 這個業界常用的 function-calling benchmark，外加三個消融實驗。聽起來是一篇很扎實的系統性實測，但仔細拆開它的數據會發現，好幾個 headline 結論其實是同一個軟體 bug 造成的假訊號，摘要宣稱的數字在正文裡也找不到支撐資料。

這篇文章會先照論文的順序走一遍實驗設計跟結果，把哪裡站得住腳、哪裡站不住腳講清楚；後半段則會抽出幾個跟這篇論文本身是否可信無關、單獨拿出來都值得學的判讀與設計觀念——這才是這篇文章真正想留給你的東西。

## 兩種工具呼叫範式：JSON vs. 程式碼

![JSON tool calling 與 Programmatic Tool Calling（PTC）兩種範式的流程對照，另外還有作為次要對照組的檔案系統探索模式。](img-001)
*圖 1 — 兩種主要範式的流程對照。（來源：原始論文。）*

**JSON tool calling**（現行業界標準做法）的流程是這樣的：

1. System prompt 內嵌工具的 JSON schema。
2. LLM 第一輪：輸出呼叫 f1 的 JSON 物件。
3. Tool runtime 執行 f1，把結果塞回對話裡。
4. LLM 第二輪：讀到 f1 的回傳值，輸出呼叫 f2 的 JSON 物件。
5. 每多一個函式呼叫，就多花一次 LLM 推論。這是這個範式天生的成本結構。

**Programmatic Tool Calling** 換了一種做法：

1. System prompt 內嵌一份 typed 的 Python stub module，每個工具對應一支簽名跟真實工具一致的 stub 函式。
2. LLM 只寫「一次」Python script，import 這個 module，在同一支 script 裡把所有需要的函式都呼叫完。
3. Agent loop 把這支 script 丟進 shell subprocess 執行。
4. Scorer 解析 subprocess 印出的 stdout，從中抽出函式名稱跟參數。
5. 「stop middleware」（下面背景知識段落之後會有專門一節解釋這是什麼）攔截下一次模型呼叫，強制終止整個 agent loop。

論文在 Appendix B.1 給了一個具體例子，任務是「求底 10、高 5 的三角形面積」。工具 stub 長這樣：

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

Subprocess 印出 `{"calculate_triangle_area": {"base": 10, "height": 5}}`，評分程式只核對函式名稱跟參數是不是跟 ground truth 一致——這個評分機制本身有個重要的前提，後面「Benchmark 測的是什麼」那一節會拆開講。

## 背景知識：讀懂後面表格前要知道的三件事

**BFCL（Berkeley Function-Calling Leaderboard）** 是業界常用的 tool-calling 準確度 benchmark，本文用的是第 4 版（v4）。

**Wilson confidence interval（Wilson CI）** 是一種計算比例型資料信賴區間的統計方法，在樣本數小或比例接近 0%/100% 時，比常見的常態近似法準確。本文所有表格的「±」欄位都是 95% Wilson CI 的半寬——區間越寬，代表那筆準確率的數字越不可靠。樣本數小的消融實驗（各自只有 31 到 52 筆）尤其要留意這件事，之後幾個表格會直接看到寬達 ±16.6% 的區間。

**\n 逃逸字元 bug** 是本文反覆出現的一個失效模式：部分模型在生成 multiline 的 Python script 時，把「換行」寫成字面上的兩個字元 `\` 跟 `n`，而不是真正的斷行符號。這種程式碼丟進 shell subprocess 執行會直接產生語法錯誤，整筆任務算 0 分。受影響的模型是 GPT-4o、GPT-4.1、GPT-5.4-mini。記住這三個名字，後面每張表格幾乎都會再看到它們。

## 實驗設計總覽

![受測的 14 個模型清單，含 Anthropic 與 OpenAI 兩個廠牌陣營。](img-002)
*表 1 — 受測的 14 個模型。（來源：原始論文。）*

論文找了 14 個模型，Anthropic 5 個（Haiku 4.5、Sonnet 4.5、Sonnet 4.6、Opus 4.8、Sonnet 5），OpenAI 9 個（GPT-4o、GPT-4.1、GPT-5-nano、GPT-5、GPT-5.4-mini、GPT-5.4、GPT-5.6-Luna/Sol/Terra），涵蓋 2024 年 11 月到 2026 年 7 月共 20 個月的發布時間軸，全部在溫度 0 下執行。主測試用 BFCL v4 的 309 筆代表性子集，涵蓋 8 個任務類別。

除了主測試，論文另外設計了三個消融實驗，各自針對「PTC 比較強」這個宣稱裡最常被質疑的任務結構：連鎖呼叫（chaining）、高扇出（parallelism）、上下文汙染（context rot）。這三個名字先記住，後面三節會分別展開。

## 主要結果：準確率打平還是壓倒性？

![各模型在 BFCL v4 子集上，JSON tool calling 與 PTC 的準確率對照表，含 95% Wilson 信賴區間。](img-003)
*表 2 — 主要結果：309 筆子集上的準確率（%）。（來源：原始論文。）*

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

先看崩掉的三個：GPT-4o、GPT-4.1、GPT-5.4-mini，PTC 準確率分別掉了 26.9、19.8、24.3 個百分點，剛好就是前面提到那三個受 \n 逃逸字元 bug 影響的模型。這不是「PTC 這個範式對這些模型比較差」，是一個具體的軟體 bug 讓整筆任務直接算 0 分。

排除這三個之後，模式就清楚多了：**Anthropic 五個模型全部打平或小贏，沒有世代差異；OpenAI 分裂成兩群：最新三個 GPT-5.6 全部大贏，被 bug 拖累的三個慘跌，其餘三個小贏或持平。** 換句話說，效應跟著模型世代走，不是跟著廠牌走。

![OpenAI 與 Anthropic 兩個廠牌陣營，各自的 JSON tool calling 與 PTC 準確率隨模型世代的變化趨勢，兩條線走勢明顯不同。](img-007)
*圖 2 — 準確率隨模型世代的變化，OpenAI 與 Anthropic 呈現相反的模式。（來源：原始論文。）*

圖 2 把這個對比畫得很直接：OpenAI 陣營要花好幾個世代才追上 JSON tool calling 的準確率，Anthropic 陣營則是從一開始就沒有落差。排除三個 bug 模型後，headline 的「11/14 模型打平或超車」其實比表面數字更一致——但這句話本身也藏著一個判讀陷阱，後面「讀 benchmark 論文的三個判讀習慣」那節會回頭講。

## 消融實驗一：連鎖呼叫任務裡，誰真的比較強？

![連鎖呼叫消融實驗（$n=52$，鏈長 2 到 20）的準確率對照表。](img-005)
*表 3 — 連鎖呼叫消融：JSON tool calling vs. PTC 準確率（%）。（來源：原始論文。）*

這個消融實驗測的是「f2 的參數依賴 f1 的執行結果」這種依序相依的多跳呼叫，樣本數 $n=52$，鏈長從 2 到 20 不等。

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

排除 GPT-4.1 這個 bug 造成的異常值後，14 個模型裡是 6 勝 6 敗 1 平，而且多數模型的 95% CI 互相重疊。這張表本身看不出兩種範式在連鎖呼叫任務上誰有系統性優勢。

> 論文摘要跟 Introduction 宣稱「PTC 在連鎖呼叫上的優勢隨鏈長增加擴大，鏈長 ≥12 時達到 18.8% 的絕對差距」，但這句話在論文全文找不到任何按鏈長分組的數據去支撐。§4.2 的討論只用了這張把鏈長 2 到 20 全混在一起的聚合表，加上 GPT-4.1 的異常值。摘要宣稱的具體數字，跟正文呈現的數據之間存在一段沒交代的落差。

延遲面倒是有個扎實的附帶發現（§5.3）：13/14 個模型下，PTC 完成一筆連鎖任務的實際時間約為 baseline 的一半，因為省掉了「等回傳、再打一次 LLM」的往返。唯一的例外是 GPT-5，PTC 延遲反而是 baseline 的 2.8 倍，論文的解釋是它的 reasoning 輸出拉長了，把省下的時間又吃了回去。

## 消融實驗二：高扇出下的結構性崩潰

![高扇出消融實驗（$n=32$，扇出數 7 到 48）的準確率對照表，多數模型兩邊都接近滿分。](img-004)
*表 4 — 高扇出消融：JSON tool calling vs. PTC 準確率（%）。（來源：原始論文。）*

這個消融實驗的樣本數 $n=32$，扇出數（一次要並行處理的呼叫數量）從 7 到 48。多數模型兩邊都是 100%，這張表本身看不太出差異。

| 模型 | JSON | PTC |
|---|---|---|
| Haiku 4.5 / Sonnet 4.5 / Sonnet 4.6 / Opus 4.8 / Sonnet 5 / GPT-4o / GPT-5.4-mini / GPT-5.4 / GPT-5.6-Luna / GPT-5.6-Terra | 100.0 | 100.0 |
| GPT-4.1 | 96.9 | 90.6（\n bug） |
| GPT-5-nano | 78.1 | 87.5 |
| GPT-5 | 71.9 | 96.9 |
| GPT-5.6-Sol | 96.9 | 100.0 |

真正有意義的發現藏在 §5.2 的額外探測實驗裡。作者對 **Claude Sonnet 5 一個模型**，把扇出數一路推高到 $N = 60, 70, 72, 75, 100$，量到一個很清楚的斷崖：

- JSON tool calling 的 enumeration 準確率：$N \le 70$ 時是 100%，$N = 72$ 時掉到 75%，$N = 100$ 時直接歸零，是結構性崩潰，不是漸進衰退。
- PTC 的 enumeration 準確率：$N = 72$ 跟 $N = 100$ 都還是 100%，完全沒受影響。

這是全篇論文我認為最站得住腳的發現：JSON tool calling 要求模型把 $N$ 個呼叫全部塞進單次回應，數量一多就開始遺漏；PTC 用迴圈或 `asyncio.gather` 表達「呼叫 $N$ 次」，不受回應長度限制。但這個崩潰**只在 Sonnet 5 一個模型上量到**，論文自己也提到 GPT-5.6-Sol 在 $N=100$ 完全沒有這個問題，所以這只能算是「觀察到的現象」，不是可以直接推廣到所有模型的普遍結論。

（這裡用到 enumeration accuracy 而不是更直覺的「最終答案對不對」，是有原因的，細節留到後面「Enumeration Accuracy vs. Aggregation Accuracy」那節展開。）

另外一個值得記住的實務數字是 token 成本的損益平衡點：$N \approx 26$。$N<26$ 時 PTC 比較貴，因為 system prompt 要塞進整份 stub module 是固定成本；$N>26$ 之後 JSON tool calling 反而比較貴，$N=30$ 時 JSON 用了 3559 tokens、PTC 只要 3380；$N=48$ 時 JSON 用了 5097、PTC 只要 3535。

## 消融實驗三：塞進雜訊工具後會發生什麼事

![上下文汙染消融實驗（$n=31$，Filtered 與 Flood 兩種情境）的準確率對照表，涵蓋 JSON、PTC、Arg 三種範式。](img-006)
*表 5 — 上下文汙染消融：Filtered 到 Flood 情境下的準確率變化（%）。（來源：原始論文。）*

這個消融實驗的樣本數 $n=31$，設計了兩種情境：**Filtered**（system prompt 裡只放任務相關的工具 schema）跟 **Flood**（塞進 128 個 schema，多數是跟任務無關的誘餌）。

| 模型 | JSON（F→Fl） | PTC（F→Fl） | Arg（F→Fl） |
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

表裡的 **Arg（filesystem-discovery）** 是論文額外加的第三種範式，論文明確說這不是業界常見做法，只是作者自己加的內部參考點。它在 Flood 情境下慘跌（平均 −32.0），這件事本身不意外。

但有個細節值得注意：Arg 在**沒有任何額外雜訊**的 Filtered 情境下，準確率就已經比 JSON tool calling 平均低了約 30 個百分點。如果 Arg 的弱點只是「雜訊下搜尋容易失敗」，那在零雜訊的 Filtered 情境下不該輸這麼多。論文把 Arg 的退步完全歸因於「context navigation 在雜訊下的結構性弱點」，但這個歸因沒有解釋 Filtered 條件下就已存在的基礎落差。

> Arg 的具體實作機制，論文自己也沒有交代清楚：全文只給了「filesystem-discovery」「file-based tool delivery」這幾個詞，不像 Figure 1 對另外兩種範式那樣畫圖或給實作細節。

PTC 在 Flood 下平均反而進步（+5.5），論文的解釋是部分模型在 Filtered 情境下被嚴格的型別限制卡住，Flood 情境下因為看到更多同類型工具的範例，反而更容易辨認出正確函式。但這個解釋論文沒有給出機制細節，也沒有做對照實驗驗證。更值得留意的是，貢獻最大的三個模型（GPT-5.4-mini +35.5、GPT-4o +22.6、GPT-4.1 +12.9）剛好就是前面反覆出現、受 \n 逃逸字元 bug 影響的同一批模型——論文沒有討論或排除這個關聯的可能性。

## 論文自己承認的限制

論文在 §7 Limitations 自己列出四點，這幾點是論文自陳的，不需要展開懷疑，直接記錄：

1. BFCL v4 用 echo-return stub（下一節會解釋這是什麼），測的是參數序列化正確性，不是端到端工具使用的正確性。
2. 消融實驗樣本數小（各自只有 31 到 52 筆），個別模型的數字信賴區間都不窄，只有跨模型的整體模式（例如「11/14 打平或超車」、「flood 下 PTC 平均進步」）才夠大到值得解讀。
3. 一份針對 BFCL v4 的獨立審計（Vaghasiya et al., 2026）發現它的 LLM-judge 模式有 20% 跟人類評分不一致；本文用的是確定性字串比對評分，不是 LLM judge，繞開了這個問題，但 benchmark 本身的 ground-truth 標籤仍可能帶有審計沒抓出的雜訊。
4. PTC 相對 JSON tool calling 有固定的 input token 開銷（system prompt 要嵌入完整的 stub module 原始碼），在連鎖呼叫消融裡 PTC 用了 1.5 倍的 input token；這個劣勢在高扇出情境下會反轉，前面消融二的 token 成本交叉點就是這個道理。

## 這篇論文本身的研究價值：接近零

把前面幾節攤開來看，這篇論文的定位其實有點尷尬。PTC 這個想法不是本文提出的：CodeAct、smolagents、Cloudflare Code Mode 都已經在做了，本文的定位是「系統性實測」。但實測品質有明顯瑕疵：多個 headline 結論拆開後發現是同一個 \n 逃逸字元 bug 造成的假訊號，摘要宣稱的具體數字（連鎖呼叫 18.8% 差距）在正文找不到對應的支撐資料，Arg baseline 的實作機制也完全沒交代清楚。

真正站得住腳、可驗證的發現只有一個：JSON tool calling 在極高扇出下有結構性的硬上限，會突然崩潰而不是漸進變差。但這個發現只在單一模型（Claude Sonnet 5）上驗證過，不能直接推廣到「所有模型都這樣」。

老實說，如果你只是想知道「PTC 到底比較好嗎」，這篇論文給不了一個乾淨的答案。但這不代表整篇論文白讀——它在判讀方法跟實驗設計上留下的教訓，反而比它自己的結論更耐用，這是接下來要講的重點。

## 真正值得帶走的六個觀念

這幾節是這篇文章的核心，跟前面「這篇論文到底站不站得住腳」是兩件獨立的事——就算你完全不信這篇論文的任何一個數字，下面這六個觀念本身依然成立，值得學起來用在自己的 eval 設計或論文判讀上。

### A. Benchmark 測的是「格式對不對」，不是「任務做完了沒」

像 BFCL 這類 function-calling benchmark，從設計上就不是在驗證「工具執行後算出的最終結果對不對」，而是「模型有沒有選對函式、填對參數」。Ground truth 是一組事先定義好的（函式名稱、參數）配對，模型輸出的呼叫只要跟這組配對做字串比對吻合就算對，完全不涉及「如果這個函式真的執行，算出來的數字對不對」。

這樣設計是有現實考量的：如果要驗證最終結果，就得架一套真的會運算的後端服務，整個 benchmark 會變得昂貴、難重現，還要處理外部服務本身的不確定性。所以這類 benchmark 普遍選擇退一步，只測「工具選擇與參數化能力」，把「工具背後真的算出什麼」排除在評分範圍之外。

理解這點很重要：任何用 BFCL 這類 benchmark 做結論的論文，量的都是「格式與呼叫正確性」，不是「任務有沒有真的被解決」。前面看到的所有準確率數字，都要用這個濾鏡去讀。

### B. Echo-return Stub：為什麼連鎖呼叫測試沒測到你以為的東西

本文用的工具 stub 不會真的執行運算，只會把收到的參數原封不動包成一包資料丟回來——例如收到 `radius=7`，回傳的是 `{"circumference": {"radius": 7}}`，不會回傳算出來的數字 43.98。這種設計叫 echo-return：便宜、快、可重現，代價是「工具真的算出了什麼」這件事完全測不到。

這對連鎖呼叫實驗有直接影響。任務要求「用 f1 的結果當 f2 的參數」，但 f1 從來不會給出真正算出來的數字，所以無論哪種範式，模型唯一能完成任務的辦法就是自己用參數知識跟數學能力把中繼值算出來，再填進第二次呼叫——工具本身完全不參與這個計算。也就是說，連鎖呼叫測試表面上看起來在測「模型有沒有正確串接前後呼叫」，實際上測的更接近「模型自己會不會算數學、函式簽名填得對不對」。

> 論文對 JSON tool calling 中間步驟拿到的回傳值是否也是同樣的 echo-return 設計，沒有給出明確的文字說明。Figure 1 的圖說裡對 JSON tool calling 那欄的回傳值有一句附註，說這個回傳值僅用來示意依賴關係；Appendix C 對 stub 的描述也是套用在「跨範式共用的同一套工具語意」上。這兩處線索都指向「兩種範式面對的可能是同一套 echo-return 工具」，但論文沒有用一句話把這件事講清楚——這是論文文字本身含糊、可以有兩種讀法的地方，不是這裡替它下的定論。

### C. Stop Middleware：比較兩個系統時，先鎖死混淆變因

Middleware 這個詞借自一般軟體工程，尤其是 web framework，指插在兩個元件之間、攔截並處理訊息流的一層。本文的 stop middleware 攔截的是「agent loop 準備再打一次的 LLM API 呼叫」，攔下來後直接終止整個迴圈。

它要解決的問題是：兩種範式天生消耗的 LLM 呼叫次數不同。JSON tool calling 做一條長度 n 的連鎖呼叫，天生要 n 次 turn；PTC 理論上一次 turn 就能把整條鏈寫完。如果放任 agent loop 在 PTC 執行完 subprocess 後繼續問模型一次，這次額外的 turn 會讓模型看到 subprocess 真實印出的結果，等於多了一次修正機會。這個修正機會如果沒被鎖住，PTC 的準確率提升就分不清楚是「程式碼這個介面本身比較好」，還是「多吃了一次免費的修正機會」。Stop middleware 把兩邊的 LLM 呼叫次數鎖成一樣，讓準確率的差距能乾淨地歸因於範式選擇本身。

這是一個可以獨立遷移的實驗設計原則，不只適用於 tool calling：比較兩個系統時，要先確認除了想測的那個變因之外，其他資源消耗有沒有被控制住。這裡是推論次數，換個情境可能是時間、token 數，或任何一種隱性的額外機會。沒控制住的話，贏的可能只是「資源用得比較多」，不是方法本身更好。

### D. Enumeration Accuracy vs. Aggregation Accuracy

高扇出消融裡有一類任務是「這 N 個項目裡，哪 3 個符合某條件」。PTC 底下，部分模型會直接用參數知識講出答案，完全沒有真的把 N 次查詢跑過一遍。如果用「最終答案對不對」（aggregation accuracy）來評分，這種行為會被誤判成「做對了」，但工具其實沒被真正呼叫過。

論文因此把 enumeration accuracy（是否真的發出全部 N 次工具呼叫）當成主要指標，而不是 aggregation accuracy——這個判斷是對的，因為它測的才是「行為是否合規」，而不是「結果是否碰巧正確」。這個區分是一個通用的 agent 評測設計手法：任何允許模型跳過工具、直接用內部知識回答的系統，都需要把「行為有沒有真的發生」跟「最終結果對不對」拆成兩個獨立指標，否則會系統性高估工具使用的真實發生率。

### E. 程式碼介面的武斷性問題，與一條可遷移的選型規則

PTC 的執行方式，至少在本文的實作裡，要求模型在「看到任何真實執行結果之前」，把整條邏輯一次寫進一支 script。遇到需要權衡、需要模糊判斷的地方，程式碼只能寫成 if/else、threshold、布林條件——沒有辦法像自然語言那樣說「這兩個選項差不多，但 A 稍微更合適，因為……」這種帶著猶豫、多因素權衡的判斷。自然語言可以表達模糊地帶，程式碼被迫把模糊地帶壓縮成一個明確的分支條件。

這件事跟本文的評測範圍有直接關係。BFCL 的評分標準是函式名稱與參數是否精確吻合 ground truth，是一個徹頭徹尾封閉式、非黑即白的任務類型。本文只在這種任務上測試兩種範式，等於選了一個結構上偏袒 PTC 的測試場：封閉式、決定性的任務正是程式碼最擅長表達的東西。本文完全沒有測試任何帶模糊判斷的任務，例如回應語氣是否合適、兩個候選答案哪個更貼合使用者意圖，所以「程式碼介面在開放式判斷任務上可能給出過度武斷的答案」這個弱點，本文的實驗設計從一開始就沒有能力揭露。

另外要注意，本文的 PTC 實作被 stop middleware 強制成「一次寫完整支 script、執行完就結束」，不允許模型看到真實執行結果後再寫下一段程式碼。這是本文為了控制 LLM turn 數公平性而做的特定設計選擇，不是「用程式碼當工具介面」這件事本身的必然限制。允許多輪程式碼執行、每輪之間插入自然語言反思的 PTC 實作，例如一般的 code-agent 產品，武斷問題可能沒有本文這個受限版本這麼嚴重，但代價是失去「一次 turn 搞定」的效率優勢。

把這件事整理成一條可以帶著走的選型規則：

| 任務性質 | 建議範式 | 原因 |
|---|---|---|
| 封閉式、有明確對錯（數學、結構化資料轉換、確定性 API 串接） | PTC（可一次性 commit） | 不需要中途反思，程式碼的決定性是優勢不是缺點 |
| 開放式、需權衡模糊標準、依賴真實中繼結果調整策略 | JSON tool calling，或允許多輪執行的 PTC | 需要在步驟之間插入自然語言判斷，一次性 commit 的程式碼會把模糊判斷壓成武斷的二元決策 |
| 高扇出、大量獨立且確定性的呼叫 | PTC | 迴圈不受回應長度限制，不過目前只有單一模型的證據支持這點 |

### F. 讀 Benchmark 論文的三個判讀習慣

這篇論文本身就是一個很好的反面教材，剛好拿來整理出三個往後讀任何 benchmark 論文都用得上的習慣。

1. **先拆解 headline 聚合數字，再相信它。** 看到「11/14 模型打平或超車」這類聚合統計，先問這個數字是不是被少數模型的異常值拉動的。本文的例子是同一個 \n 逃逸字元 bug 在三個模型上反覆出現，把整體數字撐高或壓低。平均值會掩蓋變異，永遠先問變異從哪裡來。
2. **檢查效應是跟著模型世代走、還是跟著廠牌走。** 如果一個現象只跟時間軸相關、不跟廠牌相關，通常指向的是某個具體 bug，或訓練資料裡新增的能力，而不是「這個架構或廠牌天生比較適合」。本文自己就用了這個框架區分 Anthropic（全世代通過）跟 OpenAI（新舊分裂），前面圖 2 看到的對比，值得當成一個通用的判讀濾鏡拿去套別的論文。
3. **區分「結構性斷崖」跟「漸進式衰退」是兩種不同的失效模式。** JSON tool calling 在 $N=70$ 到 $72$ 之間的行為是突然崩潰，不是慢慢變差，這種斷崖通常代表系統裡有一個固定容量的資源，例如單次回應的 token 上限，或生成長列表時的注意力限制。設計任何有輸出長度或並行度上限的系統時，值得假設會有這種斷崖存在，主動去測出門檻在哪裡，而不是假設效能會平滑下降。

## 結論

《The Bitter Lesson of Tool Calling》這篇論文本身交出的東西並不多：核心想法不是自己提出的，headline 結論裡混雜著同一個軟體 bug 造成的假訊號，摘要宣稱的具體數字在正文找不到支撐資料，唯一站得住腳的具體發現（JSON tool calling 在高扇出下有結構性硬上限）也只在單一模型上驗證過。如果你想從這篇論文得到「PTC 到底該不該用」的乾脆答案，恐怕會失望。

但它的實驗設計跟論證過程，留下了一組不受這篇論文本身對錯影響的觀念：benchmark 評分範圍的認知、echo-return 這類簡化評分機制的取捨、用資源消耗鎖死混淆變因的實驗設計紀律、enumeration 與 aggregation accuracy 的區分、程式碼介面在開放式任務上的武斷性問題與對應的選型規則，還有讀 benchmark 論文該養成的三個判讀習慣。這些東西獨立於這篇論文是否可信都成立，也是這篇文章真正想留給你的部分——下次讀到任何一篇評測論文的 headline 數字，不妨先套上面這幾個濾鏡看看，往往會看到不一樣的東西。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1: Overview of the two primary paradigms evaluated. In JSON tool calling, the model emits JSON tool-call objects via the API. In programmatic tool calling, it writes a Python script using typed stubs; the agent loop executes it in a subprocess. A filesystem-discovery condition is included as a secondary reference point.",
    "why_used": "文章一開始說明兩種工具呼叫範式的流程差異，用這張圖對照兩者的架構。",
    "agent_match_hint": "一張流程對照圖，左右兩欄分別畫出 JSON tool calling 與 programmatic tool calling 的步驟。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Table 1: Models evaluated, covering releases from November 2024 to July 2026.",
    "why_used": "介紹實驗設計時列出受測的 14 個模型清單，作為後續所有結果表格的對照基礎。",
    "agent_match_hint": "一張表格，列出模型名稱與對應的發布時間範圍，分成兩個廠牌區塊。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Table 2: Accuracy (%) on our 309-entry BFCL v4 sub- set. JSON = JSON tool calling; PTC = programmatic tool calling. ± columns show 95% Wilson CI half- widths. Bold indicates the higher value per row (ties bolded on both).",
    "why_used": "呈現主要結果，作為文中條列數據表的原始論文對照版本。",
    "agent_match_hint": "一張表格，欄位是模型、JSON 準確率、PTC 準確率與信賴區間。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Figure 2: Accuracy (%) on the BFCL v4 subset for JSON tool calling and programmatic tool calling (PTC) by model generation. The two families exhibit opposite patterns: OpenAI models required several generations to close the gap, while Anthropic models show consistent PTC parity from the outset.",
    "why_used": "視覺化「效應跟著模型世代走、不跟著廠牌走」這個主要結果的核心發現。",
    "agent_match_hint": "兩張並排的折線圖，分別是 OpenAI 與 Anthropic 陣營的準確率隨模型世代變化的趨勢。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Table 3: Chaining ablation accuracy (%, n = 52, chain lengths 2–20). JSON = JSON tool calling; PTC = pro- grammatic tool calling. ± columns show 95% Wilson CI half-widths. Bold indicates the higher value per row (ties bolded on both). †GPT-4.1 PTC collapse caused by \\n encoding failure; see text.",
    "why_used": "呈現連鎖呼叫消融實驗的原始資料，作為文中數據表的原始論文對照版本。",
    "agent_match_hint": "一張表格，欄位是模型、JSON 準確率、PTC 準確率，其中一格有 † 註記。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Table 4: Parallelism ablation accuracy (%, n = 32). JSON = JSON tool calling; PTC = programmatic tool calling. Enumeration and overall accuracy are identical for all models here; aggregation accuracy is discussed separately in the text. ± columns show 95% Wilson CI half-widths. Bold indicates the higher value per row (ties bolded on both).",
    "why_used": "呈現高扇出消融實驗的原始資料，作為文中數據表的原始論文對照版本。",
    "agent_match_hint": "一張表格，多數模型的 JSON 與 PTC 準確率都接近或等於 100%。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 5: Context rot ablation accuracy (%, n = 31 per condition). Filtered = entry-relevant schemas only; Flood = 128 total schemas (relevant + corpus decoys). JSON = JSON tool calling; PTC = programmatic tool calling; Arg = filesystem-discovery. Bold indicates the highest value among the three paradigms within each condition. Anthropic model names omit “Claude” for space. Mean ∆= average change from filtered to flood across all 14 models. 95% Wilson confidence intervals range from ±7.8% to ±16.6% (n = 31; widest near 50% accuracy).",
    "why_used": "呈現上下文汙染消融實驗的原始資料，作為文中數據表的原始論文對照版本。",
    "agent_match_hint": "一張表格，欄位是模型與三種範式（JSON、PTC、Arg）在 Filtered 與 Flood 兩種情境下的準確率變化。"
  }
]
```
