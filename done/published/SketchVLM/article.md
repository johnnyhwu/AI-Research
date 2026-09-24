# SketchVLM：讓 VLM 用畫的來解釋自己在想什麼

## 前言

問一個視覺推理問題給現在最強的多模態大模型（VLM），它通常會回你一大段文字：機油夠不夠、球會掉進哪個桶子、迷宮該怎麼走。問題是，這段文字要怎麼驗證？它跟圖片之間沒有直接對應，模型也可能只是矇對答案，你完全看不出判斷依據在哪。

SketchVLM 想解的正是這個「驗證落差」。它讓 VLM 不只用文字回答，還會直接在原圖上畫線、框選、標數字，把思考過程攤開來給你看，而且不需要重新訓練模型，也不會動到原始影像的任何一個像素。

這篇文章會照著 SketchVLM 的技術脈絡走一遍：它怎麼讓模型在畫布上「畫得準」、怎麼把畫畫變成模型能穩定輸出的結構化指令、又怎麼用數學把抖動的座標點修成平滑的曲線，最後看看這套框架在實際任務上的表現，以及它還沒解決的問題。

## 「你怎麼知道你是對的？」——VLM 的驗證落差

GPT-4o、Gemini 這類頂級模型的文字生成能力已經很成熟，但一碰到需要精準對應像素位置的空間推理任務，問題就浮現了。使用者問一個關於汽車維修或物理路徑的問題，模型給出一長串文字敘述，這段文字卻很難精確對應到圖片上的哪個位置。

更麻煩的是幻覺。模型可能文字答對了，但其實是猜對的，或者根本看錯了位置卻剛好給出正確答案。純文字輸出讓使用者沒辦法反過來檢查模型的判斷邏輯，只能選擇相信或不相信。

SketchVLM 的做法是把這個黑盒子打開一角。同樣是回答「機油油尺該怎麼看」，傳統 VLM 給你一段文字說明，SketchVLM 則直接在油尺照片上標出安全刻度的位置，一步步引導你對照著看。

![左邊是傳統 VLM 純文字回覆機油油尺的檢查方式，右邊是 SketchVLM 直接在照片上標出油尺位置與安全刻度，一步步引導使用者對照。](img-001)
*圖 1 — 面對「機油夠不夠」這類需要對照圖片才能確認的問題，傳統聊天機器人只給文字，SketchVLM 則直接在照片上畫出重點。（來源：原始論文）*

## 現有標註手法，各有各的坑

在 SketchVLM 之前，讓 VLM「指出」畫面重點的做法大致分三種，但每一種都有明顯的天花板：

- **座標點輸出**（如 Molmo、MoonDream）：計算量小，但只能給點，沒辦法畫出連續的軌跡或形狀，遇到需要框選或連線的任務就束手無策。
- **影像編輯**（如 Nano Banana Pro）：視覺效果直觀，問題是它會直接修改原始像素，這是破壞性的做法，還容易產生跟原圖無關的幻覺內容。
- **特定任務微調**（如 ViLaSR、ThinkMorph）：在訓練過的任務上表現不錯，但換一個沒看過的任務類型，例如新的迷宮佈局，準確度就會崩掉，泛化能力差。

論文用一組彈跳軌跡、連連看、迷宮導航的實際案例把這三個缺點具體攤開來看：Nano Banana Pro 常常直接改動了原始畫面，畫出的軌跡也不符合物理直覺；微調過的模型雖然在自己訓練過的任務上還算穩，但一換場景就明顯失準。

![三種方法在彈跳軌跡、連連看、迷宮導航任務上的定性比較，SketchVLM 畫出的軌跡與路徑明顯比 Nano Banana Pro 與微調模型更準確合理。](img-002)
*圖 2 — SketchVLM 在三個任務上的表現對照：Nano Banana Pro 常改動原圖並畫出不合理的軌跡，微調模型則難以泛化到新任務。（來源：原始論文）*

SketchVLM 論文對這幾種路線做了系統性的比較，核心就是看誰同時具備「免訓練」和「向量疊加、非破壞性標註」這兩個特性。

![論文整理的標註方法比較表，橫向列出各方法是否免訓練、支援多輪對話、是否需要輸入圖片、能否自由繪圖，以及標註類型是向量疊加還是影像編輯。](img-003)
*表 1 — SketchVLM 與其他標註模型/方法的特性比較，關鍵差異在「免訓練」與「向量疊加（非破壞性）」這兩欄。（來源：原始論文）*

「非破壞性」聽起來像加分項，但在某些場景其實是硬性需求。想像醫療影像或工業維修現場，如果標註過程把照片裡的一道裂縫或一個零件蓋住了，這個 AI 助手反而會變得危險。SketchVLM 用 SVG 向量圖層疊加，原始影像的每一個像素都維持完整，標註只是蓋在上面的一張透明投影片，使用者隨時可以編輯或整層拿掉。

## SketchVLM 的三個設計支柱

把前面的問題和限制擺在一起看，SketchVLM 的設計目標其實很清楚，可以歸納成三點：

- **非破壞性標註**：用 SVG 向量層蓋在原圖上，原始資料完整保留。
- **免訓練（training-free）**：整套框架是模型無關的，不需要重新訓練，靠設計精細的 system prompt 就能讓現有的強大 VLM 具備畫圖能力。
- **視覺思維鏈（visual chain-of-thought）**：把模型的推理過程直接畫出來，讓標註內容跟模型給出的文字答案彼此一致，可以互相驗證。

後面幾節會分別拆解這三點是怎麼落地的：先看模型怎麼畫得準，再看它怎麼把畫畫變成穩定的指令輸出，最後看畫出來的抖動線條怎麼被修整成漂亮的曲線。

## 座標網格：先幫模型量好尺

VLM 本身沒有內建的精確座標感，要它憑直覺在圖片上點出正確位置並不容易。SketchVLM 的做法不是相信模型的直覺，而是先給它一把外部的尺：座標網格。

具體做法上，系統不是直接在原始影像的像素上畫格線，那樣會遮住畫面內容。它改用 Pillow 這類影像處理工具，在圖片的左側和下方額外拼接出白色邊框，在邊框上標出刻度數字，並讓刻度跟影像解析度對齊：一張 1000x1000 的圖片，邊框刻度就對應 0 到 1000。這樣一來，原始影像的每個像素都不受影響，模型看到的是「原圖加外掛尺規」，而不是被格線切碎的畫面。

這也是為什麼作者把這個技巧稱為「視覺提示（visual prompting）」而不是單純的影像前處理：它完全不動模型的參數，只是改變輸入端的影像內容，誘導模型產生更有規律的行為。有點像是給一個視力正常但沒有方向感的人一張畫了方格線的地圖，地圖上的格線就是提示，讓他能準確描述路徑。

有趣的是，並非所有模型都吃這一套。論文的消融實驗顯示，Gemini-3-Pro 加了網格之後，連連看任務的誤差大幅下降；但 GPT-5 的反應平平，甚至有些微下降。推測原因是 GPT 系列內部本來就有一套強大的正規化座標系統（0 到 1000），外部再疊一層網格，反而可能跟它內建的座標感產生視覺干擾。

![消融實驗表格，比較單輪模式下有無加入格線提示，對 Gemini-3-Pro 與 GPT-5 在多項任務上的準確度影響。](img-007)
*表 2 — 加入座標網格對不同模型的影響並不一致：Gemini-3-Pro 在有網格時表現最好，GPT-5 反而在沒有網格時表現更好。（來源：原始論文）*

## 把畫畫變成結構化指令：XML 語法與座標編碼

有了外部的座標系統，下一個問題是：模型要怎麼把「我想在這裡畫一條線」講清楚，而且講得穩定、能被程式可靠地解析？

SketchVLM 捨棄了 JSON，改用 XML 風格的標籤。原因很實際：語言模型生成「成對標籤」（開始標籤配對結束標籤）的穩定性明顯比生成巢狀 JSON 結構好，後端也能用簡單的正規表達式精準抓取內容，不用處理 JSON 格式跑掉的問題。每一筆劃被包在 `<sN>...</sN>` 裡，`N` 是筆劃的序號；座標則採用 `x500y100` 這種把 x、y 直接黏在一起的格式，用意是把一組座標壓成單一 token，減少模型在輸出座標對時把 x、y 錯位配對的機率。

在這個語法之上，模型可以描述幾種基本的繪圖動作：

| 形狀類型 | 表示方式 | 使用時機 |
| --- | --- | --- |
| 自由繪圖 | 一串連續座標點 | 描述複雜路徑，例如彈跳軌跡 |
| 直線 | 只需起點與終點 | 指向、簡單畫線 |
| 矩形／框選 | 依序給出四個角點 | 框出物體範圍 |
| 箭頭 | 拆成箭身與箭頭兩部分 | 需要明確方向性時 |
| 文字標註 | `<text>` 加錨點座標 | 標數字或名稱，字體大小顏色由模型自行判斷對比度 |

畫矩形的時候有個小技巧值得一提：在四個角點上，系統要求模型在轉角處連續輸出兩次同一座標。這是因為後續會用貝茲曲線把這些點連成弧線，如果沒有這個技巧，方形的角會被平滑成圓角；讓座標在同一點重複輸出，等於告訴平滑演算法「這裡要停一下」，就能保留銳角。這算是用指令設計解決幾何渲染問題的一個聰明例子。

除了座標，模型還要為每個點附上一個 $t$ 值，範圍是 $0$ 到 $1$，代表這一筆劃畫到百分之幾的進度。這個參數本身不影響座標位置，但後面的貝茲曲線平滑化演算法需要靠它才能算出每個點的先後順序和切線方向，沒有 $t$，演算法沒辦法判斷這些點該怎麼串成一條有方向性的平滑曲線。

針對不同任務，作者也設計了對應的指令限制：物體計數只能在中心點標數字、不准畫框；零件標註強制使用預先定義好的標籤清單，避免模型亂取名字；迷宮導航則要求模型「先畫圖、再給答案」，讓標註變成模型自己的草稿紙，輔助它一步步推理，而不只是事後解釋。

## 從抖動的點到平滑的線：貝茲曲線與最小平方法

VLM 輸出的座標點通常是離散、略帶抖動的，如果直接把這些點用直線連起來，畫出來的東西會有明顯的鋸齒感，不像人手繪的線條。這一段要講的就是 SketchVLM 怎麼把不完美的點變成看起來順眼的曲線。

三次貝茲曲線是這裡的核心工具。它的特別之處在於：不需要描述線上的每一個點，只要四個控制點就能定義一條平滑曲線。其中兩個是端點 $P_0$、$P_3$，線一定會通過這兩點；另外兩個 $P_1$、$P_2$ 不在線上，功能比較像磁鐵，$P_1$ 決定線離開起點時的方向，$P_2$ 決定線進入終點時的方向，把整條曲線的走勢往自己的方向拉。

問題是，VLM 給的是路徑上的點，但貝茲曲線需要的是控制點（磁鐵），這兩者不是同一種東西，需要一個轉換的橋樑，這就是最小平方法登場的地方。做法是先收集模型給出的一串座標點跟對應的 $t$ 值，接著假設一條貝茲曲線，計算這條曲線跟這些點之間的距離平方和，再透過微積分找出讓這個誤差最小的 $P_1$、$P_2$ 座標。白話一點說，最小平方法就是在幫忙翻譯：把模型隨手給的一串抖動路徑點，轉換成數學上最貼合這些點的兩個磁鐵位置。

以物理掉落軌跡的預測為例，模型只需要輸出球在彈跳過程中的三個關鍵點，最小平方法就能補完整條拋物線該有的弧度，讓軌跡看起來符合物理直覺。這也帶來一個附帶的工程好處：因為只需要少數幾個關鍵點就能描述複雜的形狀，模型輸出的 XML 長度縮短了，反應速度變快，API 成本也跟著降低。

## 讓標註「看得懂」也「教得動」

畫得準、畫得穩之後，還有兩個實務問題：這些標註要怎麼在各種背景下都清楚可見？以及當任務需要一步一步引導使用者時，模型要怎麼維持多輪對話的連貫性？

可視性的部分，SketchVLM 採用「模型自行決策加渲染端保護」的雙重機制。顏色上，模型會分析影像的背景色，在 XML 裡直接指定對比度夠高的色碼；大小上，文字標籤和線條粗細會依物體在畫面中的比例動態調整；渲染時再統一為文字加上一層對比色的描邊，有點像遊戲字幕常見的黑邊效果，確保就算背景很複雜，標註也不會糊成一團。

至於多輪對話，SketchVLM 支援單輪和多輪兩種模式，適合的場景不太一樣：

| 特性 | 單輪模式 | 多輪模式 |
| --- | --- | --- |
| 行為 | 一次給出所有標註與答案 | 畫一筆、說一句、等回饋 |
| 適合場景 | 快速診斷、物理路徑預測 | 軟體操作教學、複雜維修指南 |
| 系統成本 | 低，單次 API 呼叫 | 高，需要多次上傳、處理影像 |

值得一提的是，單輪模式的準確度其實也不差。這反映了目前像 Gemini 3 Pro 這樣的模型，就算不邊畫邊想，也能在內部先完整模擬出整條物理路徑或整個解題流程，等於是把多輪推理壓縮成一次輸出，某種程度上這算是模型自帶的「內在心智模擬」能力。

![單輪與多輪生成流程的對照示意圖，展示同一個物理推論任務樣本在單輪模式下一次輸出所有標註與答案，以及在多輪模式下逐輪產生標註並重複利用先前標註的過程。](img-004)
*圖 3 — 單輪模式一次生成所有標註與答案；多輪模式則每一輪只產生一筆標註，並把先前的標註（影像加文字紀錄）重新餵回模型，直到給出最終答案為止。（來源：原始論文）*

多輪模式有個容易被忽略的細節：模型每一輪除了拿到目前為止畫好的圖，還必須拿到過去每一筆標註的 XML 文字紀錄。原因是單看畫好的圖，模型其實很難精確辨識線條末端的像素座標，下一筆很容易接不上；而文字紀錄提供的是精準的數字記憶，影像提供的是空間感，兩者合在一起才能讓多輪標註連貫。作者也設計了一個「單筆守門」規則，強制模型每一輪只能畫一筆，把複雜的操作拆解成使用者能消化的步驟，這在教學情境下特別有用，因為畫面不會一下子塞滿一堆標註讓人眼花。

論文也示範了幾個實際場景：一個是引導使用者在 Photoshop 裡移除背景，模型每一輪收到當下的螢幕截圖，用帶標籤的箭頭跟高亮框指出下一步該點哪裡；另一個是在 AWS 主控台裡設定雲端主機，面對這種按鈕密集、介面複雜的網頁，模型同樣靠多輪標註一步步指出該點擊的位置。這兩個例子都說明了「單筆守門加文字歷史」這套組合拳，在真正複雜的操作教學場景裡有多重要。

![多輪教學範例，模型在每一輪螢幕截圖上用帶標籤的箭頭與高亮框，逐步指示使用者如何在影像編輯軟體中移除背景。](img-017)
*圖 4 — SketchVLM 引導使用者移除圖片背景的多輪範例：每一輪都根據當前畫面標出下一步該做什麼。（來源：原始論文）*

## 實驗結果：七個任務、三個指標

論文在七項任務上測試 SketchVLM：連連看、物體計數、畫出形狀、零件標註、迷宮導航、物理直覺（預測球會落入哪個容器）、以及進階物理（模擬掉落與彈跳軌跡）。這些任務涵蓋的範圍很廣，從單純的空間精準度到需要規劃的路徑推理都有。

評估方式也不只看最終答案對不對，作者定義了三個維度：答案本身的準確度、標註是否平滑美觀（標註品質），以及「標註-文本對齊」，也就是如果只看標註、不看文字答案，能不能反推出模型的結論。作者特別強調第三個指標最關鍵，因為它驗證的是標註是不是真的反映了模型的思考過程，而不是畫好看的裝飾。

![不同物理與空間推理任務的準確度數據表，比較 SketchVLM、變體模型與微調模型在多項任務上的表現。](img-006)
*表 3 — SketchVLM 在維持視覺推理軌跡的同時，準確度依然具有競爭力；微調過的標註模型在這些任務上的表現接近隨機猜測。（來源：原始論文）*

實際數據上，SketchVLM 在推理準確度上比影像編輯類的基準方法（如 Nano Banana Pro）高出達 28.5 個百分點；標註品質比微調模型（ViLaSR、ThinkMorph）好上約 1.48 倍；標註-文本對齊的平均分數是 95.5%，遠高於微調模型的 28.6% 到 46.8%。

![VLM 裁判評分的標註-文本對齊分數與標註品質分數對照表，比較 SketchVLM 與微調模型的表現。](img-015)
*表 4 — 標註-文本對齊與標註品質這兩個指標上，微調模型的分數都明顯偏低，SketchVLM 則同時拿下最高分。（來源：原始論文）*

「標註-文本對齊」這個指標比較抽象，論文用一個具體案例說明了它為什麼重要：ThinkMorph 和 ViLaSR 這類微調模型有時候標註品質很差，邏輯上甚至有明顯錯誤，但最後給出的文字答案卻剛好是對的。這種「答案對、過程亂」的情況，讓使用者根本沒辦法靠標註去驗證模型的推理，跟 SketchVLM 那種標註與答案彼此呼應的高品質輸出形成明顯對比。

![低品質標註範例，ThinkMorph 與 ViLaSR 雖然最終答案正確，但標註過程存在邏輯錯誤，比 SketchVLM 的高品質標註更難讓使用者驗證。](img-016)
*圖 5 — 微調模型有時候答案對了，但標註本身邏輯混亂，反而比 SketchVLM 清楚一致的標註更難驗證。（來源：原始論文）*

零件標註任務上也有一個值得一提的細節：SketchVLM 標出的標籤位置跟正確位置非常接近，在每一個容許誤差範圍內都比基準方法準，跟基準的差距甚至只有幾個像素。

![不同容許誤差下，SketchVLM 標籤位置準確度與基準方法的比較表。](img-011)
*表 5 — SketchVLM 標出的部件標籤幾乎都落在正確位置附近，各個誤差容忍度下都優於基準方法，差距僅有幾個像素。（來源：原始論文）*

## 侷限與還沒解決的問題

SketchVLM 表現不錯，但作者自己也點出了幾個現實的限制。第一個是小物件的挑戰：論文裡有一個誠實的發現，處理極小型物體時，SketchVLM 的標註精準度略遜於單純輸出座標框的做法，這跟 VLM 對小區域像素本來就比較不敏感有關。

第二個是互動功能還不夠完整。目前的多輪對話沒有「撤銷」或「擦除」這類操作，如果模型畫錯了，沒辦法像真實白板討論那樣局部修正，只能繼續往下畫。第三個是目前只支援靜態影像，還沒有把這套標註機制延伸到動態影片上。這幾點都算是框架接下來明確可以努力的方向，而不是根本性的設計缺陷。

## 結論

SketchVLM 想解的核心問題很單純：VLM 越來越會講，但講的東西沒辦法讓人驗證。它的解法可以歸納成三件事。第一，用最小平方法把貝茲曲線接上模型輸出的抖動座標點，把模糊的視覺感知轉成精確的幾何線條，這也是這套框架能用少量座標點畫出平滑曲線的數學基礎。第二，透過 XML 標籤和座標網格，建立起一套模型可以穩定輸出、後端也能可靠解析的「視覺思考語言」，而且完全不需要重新訓練模型。第三，堅持用 SVG 向量疊加而不是修改像素，確保原始影像的完整性不受影響。

在準確度、標註品質、標註與文字對齊度三個指標上，SketchVLM 都明顯超過現有的影像編輯與微調方法，唯一比較吃虧的地方是極小物體的標註精度，以及還缺少撤銷、擦除這類互動細節。整體而言，這是一個把「讓模型畫圖解釋自己」這件事，從概念變成一套可以實際落地、免訓練、非破壞性框架的紮實工作。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Fig. 1: For complex questions, modern chatbots like ChatGPT often return long text responses (a) that are hard for users to understand, verify, and follow. In contrast, SketchVLM guides users (b) step-by-step by annotating the input image and grounding answers to relevant image regions—here, guiding a user how to check their car’s oil level (source: https://www.youtube.com/watch?v=tNNyu9S65E4).",
    "why_used": "開篇用機油油尺的具體例子，讓讀者一眼看出傳統文字回覆與 SketchVLM 視覺標註回覆的差異，對應前言提出的「驗證落差」問題。",
    "agent_match_hint": "左右對照圖，左邊是聊天機器人純文字回覆機油檢查問題，右邊是同一張機油油尺照片被標註出重點位置。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Fig. 2: Our sketchVLM (Gemini-3-Pro-Preview) draws more accurate predicted trajectories in Ball Drop (a); connects the dots more accurately (b); and sketches more plausible maze navigation paths (c). Nano Banana ( + ) often undesirably alters the image and draws implausible trajectories in ball drop and maze navigation. Specialist VLMs ( and ) ﬁne-tuned to sketch often fail to generalize to new tasks.",
    "why_used": "為「現有標註手法各有各的坑」一節提供具體視覺證據，讓讀者看到影像編輯法會改動原圖、微調模型難以泛化這兩個缺點實際長什麼樣子。",
    "agent_match_hint": "三組任務（彈跳軌跡、連連看、迷宮）的定性比較圖，並排呈現 SketchVLM、影像編輯方法與微調模型各自畫出的結果。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Table 1: Comparison of sketching models and methods. Annotation type describes the visual artifact used during reasoning: Vector overlay denotes structured, non- destructive marks (e.g., strokes/boxes/text) aligned to an image or canvas, while Image edit denotes pixel-space image modiﬁcation or synthesis that may change image con- tent. Input image is marked only when a provided image is the primary visual context (vs. blank canvas or purely generative visual thoughts). Free-form drawing indicates support for arbitrary stroke-like annotations beyond a ﬁxed mark set.",
    "why_used": "支撐「現有標註手法各有各的坑」一節，具體呈現各家方法在免訓練、多輪對話、向量疊加等特性上的差異，讓讀者看到 SketchVLM 在這張表中的定位。",
    "agent_match_hint": "一張表格，直欄是各種標註模型/方法名稱，橫欄是免訓練、多輪對話、需要輸入圖片、自由繪圖、標註類型等特性。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Table 3: Ablation across inputs in single-turn mode. “Sketch” adds strokes/sys- tem prompt; “Grid” additionally overlays the coordinate grid. RMSE is reported for Connect-the-Dots while accuracy is reported for the other tasks. sketchVLM works best with the grid while sketchVLM works best without the grid",
    "why_used": "佐證座標網格一節提到「不同模型對網格反應不一致」的說法，用實際消融數據呈現 Gemini 加網格提升、另一模型加網格反而下降的對比。",
    "agent_match_hint": "消融實驗數據表，比較有無加入座標網格（Grid）時，不同模型在多項任務上的準確度或 RMSE 數值變化。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Fig. 3: Single-turn and multi-turn generation on the same VPCT sample. In (a) single- turn, SketchVLM receives the system prompt, the task prompt, and the input image, then outputs all annotations and the ﬁnal answer in a single model call. In (b) multi- turn, Turn 1 uses the same inputs and outputs one annotation. For later turns, the model reuses the system prompt, the task prompt, and the previous annotations, which are provided in both the rendered image and text form. This process repeats until the model outputs its ﬁnal text answer on the last turn.",
    "why_used": "把單輪與多輪模式的流程差異用示意圖具體呈現，補足前面表格說明的抽象描述，讓讀者看到多輪模式如何逐輪重複利用先前標註。",
    "agent_match_hint": "流程示意圖，分成 (a) 單輪與 (b) 多輪兩個部分，用箭頭呈現模型每一輪的輸入輸出與資料流動方向。"
  },
  {
    "id": "img-017",
    "references_manifest_caption": "Fig. 12: Multi-turn example of SketchVLM guiding a user through how to remove an image’s background. At each turn, the model receives a screenshot then annotates the screenshot with labeled arrows and highlights UI elements to indicate the next step.",
    "why_used": "作為多輪對話教學情境的具體案例，讓「模型逐輪標出下一步該做什麼」這個抽象描述有一個讀者能想像的真實畫面。",
    "agent_match_hint": "一連串螢幕截圖，每張截圖上都有帶標籤的箭頭與高亮框，指出使用者在影像編輯軟體中移除背景時該點擊的位置。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 2: SketchVLMs produce visual reasoning traces while maintaining competitive accuracy. + underperforms default , and ﬁne-tuned sketching models ( , ) perform near random chance on visual reasoning tasks.",
    "why_used": "為實驗結果一節的整體準確度說法提供具體任務層級的數據佐證，對照微調模型在同樣任務上接近隨機猜測的表現。",
    "agent_match_hint": "多欄數據表，直欄是不同模型（含 SketchVLM 與微調模型），橫欄是多項物理與空間推理任務的準確度數值。"
  },
  {
    "id": "img-015",
    "references_manifest_caption": "Table 5: VLM-judged annotation–text alignment (higher is better) and annotation quality (1–5, higher is better). Models ﬁne-tuned to generate annotations show lower alignment, while sketchVLM has the highest alignment and annotation quality.",
    "why_used": "直接對應標註品質與標註-文本對齊這兩個指標的具體分數來源，支撐文中引用的 1.48 倍與 95.5% 等數據。",
    "agent_match_hint": "數據表格，比較不同模型在標註-文本對齊分數與標註品質評分（1 到 5 分）上的表現。"
  },
  {
    "id": "img-016",
    "references_manifest_caption": "Fig. 11: Low-quality annotations from ThinkMorph and ViLaSR may still lead to the correct ﬁnal answer, but contain logical errors that are harder for users to verify than the high-quality annotations from SketchVLMs.",
    "why_used": "具體示範「標註-文本對齊」為何重要：微調模型即使答案正確，標註本身邏輯混亂也難以讓使用者驗證，形成與 SketchVLM 的對比。",
    "agent_match_hint": "並排比較圖，展示 ThinkMorph、ViLaSR 等模型邏輯混亂但答案正確的標註，對比 SketchVLM 清楚一致的標註。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Table 4: Labels placed by SketchVLMs land very close to the correct location. sketchVLM is more accurate than the baseline at every tolerance level, and sketchVLM matches it within a few pixels.",
    "why_used": "為零件標註精準度的段落提供具體數據佐證，支撐「標籤位置跟正確位置非常接近」這個論點。",
    "agent_match_hint": "數據表格，橫列是不同的容許誤差距離，直欄比較 SketchVLM 與基準方法在各誤差範圍下的標籤準確率。"
  }
]
```
