# 論文筆記:Same Model, Different Harness: Different Coding-Agent Results

**來源**:Sydney Lewis, arXiv:2608.26218v1 [cs.AI], August 2026

---

## 30 秒版本

一篇比較「同一個 coding agent,換一套 harness 設定」會不會改變表現的實證論文。作者把自己開發的 harness(Yuj)設計成兩種模式:Control(把完整對話依時間序全部塞給模型,context 滿了就停)vs Treatment(保留完整記錄,但動態壓縮模型看到的舊內容 + 偵測卡關並介入 + 一些指令防護)。

**核心發現**:在 context 空間吃緊的情境下,Treatment 讓表現大幅提升(例如 SWE-bench Verified 的 F2PF 從 28% 衝到 49%)。但把 context window 開大到不再吃緊之後,**這個優勢幾乎完全消失**。

**研究價值:低**(作者自己承認沒有方法論上的新穎性)。**工程/實證價值:中等偏正面,但有一個重大保留**——Treatment 用的運算量(model turns、tokens、時間)是 Control 的 2~4 倍,而且 Control 表現差有很大一部分是「被 context 塞滿、提早被迫收工」造成的,不是真的能力比較弱。所以這篇論文真正證明的東西,比它表面上看起來的「智慧型機制」要單薄一些——比較接近「別讓模型因為 context 爆掉而提早陣亡」這種務實的工程修正,而不是什麼演算法突破。

---

## 核心概念索引(跳讀用)

以下六段是這篇論文之外、也完全成立的通用觀念,理解這些比記住論文本身的結論更重要。想直接跳讀可以用下面的錨點:

- [A] [F2P / F2PF / P2P 是什麼,三者的關係](#a-f2p--f2pf--p2p-是什麼)
- [B] [F2PF 這個指標為什麼要存在](#b-f2pf-這個指標為什麼要存在)
- [C] [Context 半衰期縮減規則的完整運作機制](#c-context-半衰期縮減規則的完整運作機制)
- [D] [McNemar Test vs Sign Test——遇到配對比較時怎麼選檢定](#d-mcnemar-test-vs-sign-test)
- [E] [p value 到底是什麼意思(常見誤解澄清)](#e-p-value-到底是什麼意思)
- [F] [Repository-level 敏感度分析是什麼、為什麼需要](#f-repository-level-敏感度分析是什麼)

---

## 1. 論文想解決的問題

一個 coding agent 的工作流程是:拿到一個 bug/issue → 搜尋相關程式碼 → 讀檔案 → 改程式 → 跑測試 → 視結果再改。每一步都會留下文字紀錄(指令、輸出、錯誤訊息、模型自己的回覆),這些紀錄會不斷累積。在大型程式庫上,這些累積的文字會跟模型能看到的「context window(上下文視窗,也就是模型單次能讀進去的文字容量上限)」互相競爭空間。

論文區分了兩層:

- **Model(模型)**:負責決定下一步要做什麼(搜什麼、改什麼、跑什麼測試)
- **Harness(執行框架)**:負責決定模型「看得到什麼」、「能用什麼工具」、「什麼時候該停」

論文的核心提問是:**如果模型權重完全不變,只改變 harness 決定「模型看到什麼」的方式,結果會不會不一樣?**

最傳統的做法(論文稱為 Control)是把完整對話依照發生的時間順序,原封不動地全部塞給模型,一旦這個對話塞不進 context window,任務就直接中止(即使程式還沒改完)。論文開發的替代做法(Treatment)則是:**保留一份完整的記錄,但模型實際看到的「視窗畫面」是動態、精簡過的**,同時再加上一個偵測卡關模式並介入提醒的機制。

---

## 2. Treatment Harness 的方法設計

Treatment 由三個機制組成:①context 半衰期縮減規則、②卡關偵測器、③指令防護。這三者是**綁在一起測試的整包(package)**,論文沒有做拆解(ablation),所以你沒辦法從這篇論文知道三者各自貢獻了多少——這點在後面「限制」部分還會再提到。

### 2.1 機制一:Context 半衰期縮減規則

**要解決的問題**:Control 模式下,舊的工具呼叫結果(搜尋結果、測試 log、錯誤訊息)會一直佔著 context 空間,擠壓後面真正需要的資訊,導致大型早期輸出可能吃光後面需要的空間。

**核心設計**:把「模型實際看到的畫面(working view)」跟「完整的執行記錄(in-memory conversation)」分開。完整記錄永遠留著、永遠可以事後查,但模型當下看到的東西可以被動態壓縮。

完整的運作細節(啟動時機、縮減規則、真實數值範例)整理在 **[核心概念 C]**,這裡是不可跳過的重點段落。

**視覺化(對應 Figure 1,原文 caption:"The closed loop. The harness retains the in-memory conversation but rebuilds the model's current view for each step. Recorded execution patterns can change a later step. Separate files preserve the complete run record.")**:

```
完整執行記錄(永遠保留,不縮減)
        │
        ▼
  建構「模型當下看到的畫面」(舊結果依規則縮減)
        │
        ▼
      模型決定下一步動作
        │
        ▼
    工具實際執行,結果寫回完整記錄 ──┐
        │                        │
        └────────────────────────┘(迴圈)
```

### 2.2 機制二:卡關偵測器(Detector)

**要解決的問題**:context 縮減只解決「空間不夠」,但還有另一種浪費——空間明明還夠,模型卻在原地打轉:重複下同一個會失敗的指令、連續拿到一樣的錯誤訊息、或反覆讀同一份資料卻遲遲不動手改程式碼。

**運作方式**:偵測器**不會**重新理解或解讀對話內容,它只比對「執行記錄裡已經存在的固定事實」(例如:這個指令之前出現過嗎?上次結果跟這次一樣嗎?),完全不耗用模型 token、不呼叫模型。規則是寫死的,同樣的模式一定觸發同樣的反應,不會臨場判斷。偵測到模式後,harness 會送出一段固定文字提醒模型換個做法(論文稱為 **intervention,介入**),然後繼續觀察下一步。這個「觀察 → 回應 → 再觀察」的迴圈,就是論文把整套 Treatment 稱為 **closed-loop harness(閉迴路 harness)** 的原因。

**論文只給了三種質性的症狀描述**,原文(Section 2.3):

1. 模型重複下同一個會失敗的指令(repeats a failing command)
2. 連續拿到同樣的錯誤訊息(receives the same error several times)
3. 反覆讀同一份資料但沒有做任何原始碼變更(rereads the same material without making an edit)

**這裡論文沒有講清楚具體的判定規則跟門檻值**——比如「重複幾次才算觸發」「多少 turn 內算同一次重複」「怎麼判定兩次錯誤訊息算『一樣』」,論文只說這些規則「is part of the harness and treatment configuration」,實際定義藏在程式碼設定檔裡,正文完全沒有揭露。7.1 節也明講「detector 各機制的個別貢獻」是未來工作,連作者自己都還沒做拆解實驗。

**實際案例(對應 Figure 4 的一部分,任務 `django_django-11211`)**:第 32 個 model-call turn,偵測器記錄到「arguments reissued after 7 turns, no source write」(同樣的參數 7 個 turn 後又被重送一次,期間完全沒有寫入任何原始碼變更);第 33 turn,harness 送出固定回應:「Loop detected ... Stop repeating ... change approach.」

**值得帶走的通用觀念**:雖然論文沒揭露具體規則,但這三種症狀分類(重複失敗指令 / 重複錯誤訊息 / 空轉重讀無編輯)本身是一個可以脫離這篇論文、直接套用到其他 agent harness 設計上的分類框架。

### 2.3 機制三:指令防護(Command Safeguards)

論文對這個機制的描述極為單薄,原文(Section 2.4)整段就只有一句:「The treatment also handles a few predictable command problems by putting a test command into the expected form, stopping a forbidden command before it runs, and preventing oversized setup output from taking over the context.」

也就是三件事:①把測試指令重寫成預期格式、②在禁止指令執行前先攔下來、③防止過大的 setup 輸出佔滿 context。

**這裡論文完全沒有講清楚具體規則**——沒有列出「禁止指令」清單、沒有解釋「預期格式」指的是什麼、也沒說明這個機制跟機制一的縮減邏輯是共用還是獨立。三個機制裡,這個揭露程度最低,筆記到此為止,不做任何推測性補充。

---

## 3. 實驗設計

### 3.1 Paired Comparison(配對比較)設計

**核心設計**:同一個任務,同時跑兩次——一次 Control、一次 Treatment,兩次共用完全相同的模型權重、任務、context 容量、執行協定、評分器,唯一的差異只在 harness 設定這一個變因。原文(3.1 節):「The control and treatment differ only in one checked-in configuration package.」

**這樣做要解決的問題**:如果不做配對,直接把任務隨機分成兩組分別跑,你沒辦法排除「任務難度差異」這個干擾因素——萬一某一組剛好分到比較簡單的任務,你不知道進步是來自 harness 設計還是純粹運氣。配對設計把任務難度這個變因鎖死,能歸因的變數只剩下 harness 設定。

**一個容易被忽略但重要的前置檢查**:在正式比較之前,作者先驗證了自己的 Control 版本是不是一個可信的基準,而不是刻意做弱的稻草人對照組。做法:拿同一個模型(GPT-5.5)、同一批 500 個 SWE-bench Verified 任務,分別跑在 Yuj(未開 Treatment)跟一個外部現成的 harness(mini-SWE-agent v2.2.8)上,結果兩邊在 87.6% 的任務判定上一致(Cohen's kappa = 0.66)。**這裡論文沒有進一步討論那 12.4% 不一致的任務屬於什麼類型**,只用一句話帶過就接受了這個前測結果,算是交代得比較簡略的環節。

### 3.2 評分指標:Resolution 與 F2PF 雙尺度

論文同時報兩個指標:

- **Resolution(是否完全解決)**:二元,是/否
- **F2PF(Fail-to-Pass Fraction,部分修復比例)**:連續值,0 到 1 之間

這兩個指標分別是什麼、彼此的關係、以及為什麼需要兩把尺一起用,完整解釋見 **[核心概念 A]** 跟 **[核心概念 B]**。

**指標邊界規則**(3.4 節):如果某筆記錄沒有 F2P 分母(這個任務本身沒有可用的目標測試),評分規則直接把 operational F2PF 設為 0——但這跟「有分母、測試全部沒過」的真實 0 分是兩種不同情況,論文在 Figure 7 用不同顏色(斜線 vs 灰色)區分這兩種零分。

### 3.3 統計檢定方法

Resolution 是二元配對資料,用 **McNemar test**;F2PF 是連續配對資料,用 **Sign test**。這兩個檢定分別在檢什麼、遇到類似情境該怎麼直覺選擇,完整整理在 **[核心概念 D]**。理解 p value 本身代表什麼、常見的誤解,整理在 **[核心概念 E]**。

論文選 Sign test 而非其他連續值檢定(如 Wilcoxon signed-rank test 或配對 t-test)的原因,原文(3.5 節):「We chose the sign test because the frozen hypothesis concerns direction across tasks, and the test requires neither a normal nor a symmetric distribution of difference magnitudes.」——研究問題本身只關心「哪個方向的題目比較多」,不關心贏多少,而且 sign test 對資料分布沒有假設要求。

---

## 4. 主要結果

### 4.1 Context 壓力大時的核心成果(Table 2)

Table 2 原文 caption:「Outcomes for the three primary Qwen3.6 pressure comparisons. Each row gives mean per-task F2PF and complete solutions for both arms.」

```
Benchmark              mean F2PF (C→T)      complete solutions (C→T)
SWE-bench Verified      28% → 49%              43 → 72
SWE-bench Pro           15% → 33%              31 → 72
FeatureBench            11% → 20%               2 → 3
```

三個 benchmark 的 F2PF 差異都是 p < 0.0001(sign test);Verified 跟 Pro 的 resolution 差異也都是 p < 0.0001(McNemar test);FeatureBench 因樣本太小(2→3)沒測出顯著性。

### 4.2 隱藏的代價:這不是免費的午餐(Table 9)

**這是整篇論文最關鍵、也最容易被忽略的一塊。** 乍看 4.1 的數字會覺得 Treatment 像變魔法,但 Table 9(原文 caption:「Recorded model work for the three primary Qwen3.6 pressure comparisons... Model turns count unique recorded turns within each solver invocation, while prompt tokens count the assembled model inputs at those turns.」)揭露了代價:

```
Benchmark            model turns (C/T)     prompt tokens百萬(C/T)   wall time小時(C/T)
Verified              3,280 / 6,517          37.8 / 80.7              1.3 / 4.6
Pro                    8,357 / 25,750        210.6 / 657.1            5.4 / 21.8
FeatureBench           5,281 / 15,178        140.3 / 412.8            2.5 / 14.7
```

Pro 這行:Treatment 用了將近 **3 倍**的 model turns、**3.1 倍**的 prompt tokens、**4 倍**的 wall time。表現提升(F2PF 15%→33%)有很大一部分可能就是「多做了 3 倍的工」換來的,不是「同樣的工作量、做得更聰明」。

**論文自己也承認這一點**,原文(4.1 節):「Less model work can mark an earlier stop rather than greater efficiency: under pressure, control often reached the context limit while treatment continued.」——Control 表現差,很大一部分原因是**它被 context 塞滿、提早被迫收工**,不是它真的能力比較差。這句話直接動搖了 4.1 那組數字表面上給人的「智慧型機制」印象。

### 4.3 Context 解除限制後,優勢幾乎消失(Figure 6)

Figure 6 原文 caption:「Qwen3.6 outcomes across the three Verified context windows at the completed-run endpoint under the fixed 480-second budget. Every point uses the same 169 tasks.」——同一批 169 個任務,只改變 context window 大小:

```
context window     mean F2PF (C / T)        差距          resolution (C/T)
  20,480(緊)        28.0% / 49.1%          +21.1pp        43/169 → 72/169
  43,008(中)        53.8% / 60.1%           +6.4pp        76/169 → 87/169
  262,144(寬鬆)      69.0% / 68.7%           -0.3pp       102/169 → 101/169
       ⚠️ 這一列的 resolution 差異,repository-level 重新檢驗後 p 值 = 0.0625,不顯著(見下方註記)
```

262,144 tokens 時,每個 benchmark 每個 arm 裡低於 1% 的任務真的會撞到 context 上限,等於**完全不受限**。優勢在這裡直接歸零(95% 信賴區間 [-4.5, +3.9],涵蓋 0)。**Treatment 的優勢幾乎完全集中在「context 不夠用」這個特定情境下**,一旦拿掉限制,兩者表現趨於一致。

> **統計嚴謹度註記**(來自附錄 Table 12/13 的 repository-level 敏感度分析,概念解釋見 [核心概念 F]):task-level 統計把每一題當獨立樣本,但同一個 repository 底下的多筆任務可能不是真正獨立的。換成以 repository 為單位重新檢定後:Verified 的 resolution 差異 p 值從 <0.0001 跳到 0.0625(不再顯著,雖然方向仍是 6:0:5 一面倒偏向 treatment,只是樣本數太小加上多重比較校正,證據強度不夠);FeatureBench 的 resolution 更明顯,22 個 repo 裡只有 1 個支持 treatment、21 個平手(pHolm=1,完全沒訊號)。**真正在兩個檢定層級都穩定顯著的,只有 SWE-bench Pro。**

**論文對這個現象的正面解讀**(6.2 節,站得住腳的論點):「We cannot know at the start of a long task whether context will bind. Treatment produced large gains when it did, while observed performance remained close on Verified and Pro when context remained ample. This pattern supports enabling the treatment from the start.」——你事先不知道任務會不會撞到 context 上限,Treatment 在「會撞」時大賺、「不會撞」時打平不虧,所以從風險管理角度,預設開啟是合理的,即使它平均而言不是什麼突破,更接近「一個安全網」。

### 4.4 FeatureBench 是唯一的例外

三個 benchmark 裡,只有 FeatureBench 在 context 完全不受限時**依然保留差距**:

```
FeatureBench,262,144-token,183 題:
  F2PF:  23.9% → 30.7%
  task-level sign test:      p = 0.00022(顯著)
  repository-level sign test: p = 0.0963(不顯著)
  complete solutions:  5 → 5(完全沒變)
```

即使 context 不受限,Treatment 依然讓模型修好更多測試,但完全解決的任務數一個都沒多。論文沒有解釋為什麼 FeatureBench 跟另外兩個 benchmark 不一致,只是誠實地把這個矛盾攤出來。

---

## 5. 跨模型遷移結果(Table 3)

**要驗證的問題**:前面所有結果都只在單一模型(Qwen3.6-35B-A3B)上跑出來。作者把同一套**凍結不變、完全沒重新調參**的 Treatment 設定,套用到三個架構完全不同的模型上,驗證效果是不是 Qwen3.6 專屬的巧合。原文(Section 5):「no harness-code fork or treatment retuning.」

Table 3 原文 caption:「Paired outcomes on the same 169-task SWE-bench Verified cohort at 20,480 tokens and a fixed 480-second attempt budget... Parentheses give the absolute gain and T/C multiplier; F2PF gains are percentage points.」——注意:**這批實驗只測了 tight context(20,480 tokens)這一種設定**,完全沒測寬鬆 context 下遷移模型的優勢會不會像 Qwen3.6 一樣消失。

```
model        設計                    F2PF (C→T,增益;倍數)         solutions (C→T,增益;倍數)
Qwen3.6      DeltaNet/attention MoE   28%→49% (+21pp; 1.8×)       43→72 (+29; 1.7×)
Devstral     dense transformer       17%→37% (+20pp; 2.1×)       22→53 (+31; 2.4×)
Nemotron     Mamba-2/attention MoE   12%→18% (+6pp;  1.5×)       16→25 (+9;  1.6×)
Qwen3.8      dense DeltaNet/attention 20%→35% (+15pp; 1.7×)      32→54 (+22; 1.7×)
```

四個模型,F2PF 跟 solutions 都一致朝同一個方向進步——Treatment 的效果方向性不是 Qwen3.6 專屬的巧合。**但 Nemotron 的 resolution 差異(McNemar p = 0.0636)沒有達到 0.05 顯著門檻**,是四個模型裡唯一一個 resolution 沒有顯著證據支持的案例。

**這裡論文有一個重要的揭露缺口**:遷移實驗完全沒有公布這四個模型各自的 model turns / prompt tokens / wall time。4.2 節已經確認 Qwen3.6 的巨大提升裡,有很大一部分可能來自運算量差距(2~4倍)——**這個「運算量混淆」的疑慮,在遷移模型上完全沒辦法檢查**,因為沒有對應的資源消耗數字可查證。

---

## 6. 值得帶走的東西(按耐久度排序)

這篇論文本身的方法沒有新穎性,真正的收穫是讀論文過程中釐清、但脫離這篇論文也成立的通用觀念:

1. **評估任何「新機制帶來大幅提升」的宣稱時,第一件要檢查的事是「兩邊有沒有用一樣多的運算量」**。運算量沒對齊,提升就可能只是「多做工」而非「做得聰明」——這是這篇論文提供的最強懷疑框架,可以直接套用到任何 agent/harness 系統的評估上。搭配的具體反事實檢查:「單純加大資源(例如把 context window 開大),能不能達到同樣效果?」如果答案接近「能」,那所謂的智慧型機制,價值就要大打折扣。

2. **p value 的正確理解**:p 值是「假設沒有差異時,觀察到這組(或更極端)資料的機率」,顯著不等於證明為真,只是「這個結果不太像純粹運氣」的機率化判斷。而且**换一個樣本定義方式(例如從「任務」換成「來源/群組」),同一組底層資料的顯著性可能會翻盤**——看到任何顯著性宣稱,都該多問一句「用什麼單位算的」。

3. **Repository-level(廣義來說是 cluster-level)敏感度分析**:當樣本之間可能不是互相獨立的(同一個專案、同一個使用者、同一個來源產生的多筆資料),task-level 的顯著性可能是被少數幾個「來源」灌水撐起來的假象。遇到配對/分組資料要做顯著性檢定時,先問「我的樣本真的互相獨立嗎?」,不獨立就該用更保守的分組層級重新驗證一次。

4. **McNemar / Sign test 的決策規則**:遇到配對比較,先問資料是二元還連續,再選檢定方法(完整決策表見 [核心概念 D])。

5. **Resolution(二元終局判定) + F2PF(連續部分完成度)雙尺度評分設計**:當終局指標是二元、樣本又少、容易看不出訊號時,補一個連續型的「部分完成度」指標,可以在不改變終局判定標準的情況下榨出更多訊號。這個設計模式可以直接遷移到任何「怎麼設計中間層評估指標」的情境。

6. **卡關偵測的三類症狀分類框架**:重複失敗指令 / 重複錯誤訊息 / 空轉重讀無編輯。雖然論文沒揭露具體判定規則,但這個分類本身是可以直接套用到其他 agent harness 設計上的通用觀念。

---

## 核心概念深入解析

### [A] F2P / F2PF / P2P 是什麼

一個 coding 任務底下,evaluator 會把跟這次修 bug 相關的測試分成不同類別:

```
F2P (Fail-to-Pass)：修 patch 之前失敗、修完之後「應該」要通過的測試
                    → 用來檢查「有沒有真的把 bug 修好」

P2P (Pass-to-Pass)：修 patch 之前本來就通過、修完之後也應該繼續通過的測試
                    → 用來檢查「修 bug 時有沒有把別的地方改壞」
```

> **範圍澄清**:P2P 這個詞**這篇論文正文完全沒有出現過**,是 SWE-bench 系列 benchmark 的標準協定背景知識,用來幫助理解「F2P 為什麼要被特別圈出來」。論文只用到 F2P,完全沒有討論或報告 P2P / 改壞其他測試 這件事。

**F2PF(F2P Fraction)** 則是從 F2P 這堆測試裡算出來的一個比例:

```
F2PF = (F2P 測試中,修完後變成通過的數量) / (F2P 測試的總數)
```

具體例子(對應 Figure 5,原文 caption:「The ten-test example. The patch fixes seven target tests, so its F2PF is 0.70. Three target tests still fail, so the task is not resolved.」):

```
F2P 測試(10 個):
  修前: ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗
  修後: ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✗ ✗ ✗

F2PF = 7 / 10 = 0.70
Resolution = 否(還有測試沒過,不算完全解決)
```

三者關係一句話:F2P 是「一組測試的集合」,P2P 是「另一組測試的集合(這篇論文沒用到)」,F2PF 是「從 F2P 這組測試算出來的一個比例數字」。

**這個指標是論文自己發明的嗎?**——一半一半。原文:「Evaluators define fail-to-pass (F2P) tests as tests that fail before a patch and should pass after it. **We call** the share of this set that passes after the patch the F2P fraction, or F2PF.」F2P 測試分類本身是既有評分器(SWE-bench 系列)的標準協定,不是這篇論文發明的;但把它包裝成一個連續型「比例」指標並命名為 F2PF,是這篇論文自己的呈現方式。

### [B] F2PF 這個指標為什麼要存在

如果只用二元的 resolution(解決了嗎?是/否)當指標,會有一個弱點:resolution 的變化量通常很小、樣本又少,統計上容易看不出差異。論文自己的數據就是最好的示範(Table 2):

```
FeatureBench(183 個任務):
  complete solutions(resolution):  2 → 3    (幾乎看不出東西)
  mean per-task F2PF:            10.5% → 19.6%  (幾乎翻倍,訊號清楚很多)
```

如果只報 resolution,FeatureBench 上「Treatment 有沒有用」這件事幾乎完全看不出來(2 vs 3,樣本太小)。但用 F2PF 補進去,可以看到雖然完全解決的任務數沒什麼變,**部分修復的程度**卻有系統性的進步。

論文原文的邏輯(3.4 節):「F2PF measures how much of the required behavior a patch repaired, **including on tasks that did not fully resolve**.」——F2PF 存在的意義,就是在 resolution 判定為「失敗」的任務裡繼續榨出訊號,而不是把「改對7成」跟「一題都沒改對」的任務粗暴地歸成同一類「失敗」。Resolution 回答「完全解決了嗎」,F2PF 回答「往解決的方向前進了多少」,兩者互補。

### [C] Context 半衰期縮減規則的完整運作機制

**啟動時機**:不是一開始就縮減。只有當「預估的完整 prompt」達到設定 context window 的 **50%** 時,縮減規則才會啟動(原文:「Once the estimated full prompt reaches 50% of the configured window」)。在跨過這條線之前,不管一筆結果多舊,都完整顯示、放著不管。

**Age 的定義**:age 指的是「這筆工具結果之後,又出現了幾筆更新的工具結果」,age 越大代表越舊。可以寫成:

```
age(R) = k_now - k_R
```

其中 `k_R` 是 R 這筆工具結果建立時是第幾次工具呼叫,`k_now` 是目前累積到第幾次工具呼叫。(這個符號記法是為了方便說明而整理的,底層定義來自論文原文「age is the number of newer tool results that have arrived」。)

**縮減規則**(對應 Figure 2,原文 caption:「The treatment's working-view rule. The treatment starts shortening only after the estimated full prompt reaches half the configured window. The newest four tool results remain full. Older results keep their beginning and end within the printed caps, while the in-memory result remains complete.」):

```
age 分級          字元上限
最新 4 筆          完整保留(verbatim)
age 4–7           最多 4,096 字元
age 8–15          最多 2,048 字元
age 16–31         最多 1,024 字元
age 32–63         最多   512 字元
age 64+(更舊)      最多   256 字元
```

規律:**age 每翻一倍(4→8→16→32→64),字元上限就砍半**——這就是「半衰期(half-life)」命名的由來,借用「自變數翻倍、應變數呈指數遞減」這個數學形狀上的類比,沒有更深的物理意義。縮減後的結果保留開頭、保留結尾,中間用省略標記取代,讓模型還能看出這次工具呼叫大致在做什麼。

**真實案例完整走查(任務 `django_django-11211`,對應 Figure 4,原文 caption:「A real Verified treatment trace. The lower-left panel shows an excerpt from the exact 512-character view of a 26,684-character tool result. The full result remained saved. The lower-right panel shows assembled prompt tokens before and after shortening began at turn 60.」)**:

```
k_now   age    落在哪一級      上限     R 實際顯示長度
  5      0    最新4筆內       完整     26,684(逐字)★論文真實資料點
  9      4    age 4–7        4,096     4,096
 13      8    age 8–15       2,048     2,048
 21     16    age 16–31      1,024     1,024
 37     32    age 32–63       512        512
 60     55    age 32–63       512        512   ★論文真實資料點
```

> **資料來源標註**:表中 k=5(建立時,26,684 字元)跟 k=60(呈現時,512 字元)是論文真實公布的兩個快照數字。其餘 k_now 節點(9、13、21、37)是套用論文明講的 age 分級規則、對這兩點之間做的機械式計算,用來讓遞減節奏更清楚,不是論文逐輪公布的資料。

在 k_now=60 這個真實快照裡:實際顯示內容是開頭幾行程式碼(`from collections import defaultdict...`)+「26,172 字元已省略,完整結果仍保留在存檔中」的提示 + 結尾(`return GenericRelatedObjectManager`)。512(顯示)+ 26,172(省略)= 26,684(原始),數字對得上。

**這是本篇筆記最重要的機制細節,務必記住**:縮減規則**不是每個 turn 都在跑漸進式的縮減**。Figure 4 右下角那張圖(assembled prompt tokens vs turn)顯示:turn 45 到 60 之間,prompt tokens 一路往上爬(約 22,500 → 30,500),完全沒有縮減痕跡;直到 turn 60 那一瞬間才**斷崖式下降**到約 20,500。這是因為縮減規則要等到「整體 prompt 佔用率跨過 50% 門檻」才會**一次性地**把當下所有舊結果依照各自的 age 套上對應上限——「要不要開始壓」是由整體佔用率決定的獨立開關,「壓到多短」才是由單筆結果自己的 age 決定,兩者是分開的兩件事。

### [D] McNemar Test vs Sign Test

**決策規則**:

```
配對比較資料
        │
        ├── 結果是二元(是/否、成功/失敗)
        │       → McNemar test
        │       一句話記憶:「兩邊都贏或都輸的配對不算數,只看誰單獨贏」
        │
        └── 結果是連續值(比例、分數)
                → Sign test
                一句話記憶:「只數正負號,完全不管贏多少」
```

**McNemar 具體怎麼算**(用論文真實數字,Table 7,Verified 20,480-token window,原文報「T-only : C-only = 34 : 5, p<0.0001」):

```
                        control 通過
                     是          否
treatment  是    [兩邊都過,不算]   34   ← treatment 單獨救回來的
           否      5      [兩邊都沒過,不算]
```

McNemar 只看「一邊贏、一邊輸」的配對(不一致配對),兩邊都成功或都失敗的配對直接丟掉不算,因為這些配對無法告訴你「誰比較強」。34 贏 5,懸殊到 p<0.0001。

**Sign test 具體怎麼算**(Table 8,同一個 window,原文報「42:6:121」):169 題裡,42 題 treatment 的 F2PF 較高、6 題 control 較高、121 題平手(直接排除)。只比 42 跟 6 這兩個非平手數字,懸殊到 p<0.0001。

論文選 Sign test 而非 Wilcoxon signed-rank test 或配對 t-test 的原因:研究問題只關心方向、不關心贏多少,且不想對資料分布做假設(不需要常態或對稱分布)。

### [E] p value 到底是什麼意思

**正確定義**:p value 是「**假設虛無假設為真**(也就是兩個方法其實一樣強、沒有差異),觀察到現在這組資料、或比現在更極端的資料的機率」。

**最常見的誤解**:「p 值很小 → 代表虛無假設不成立」。這句話是錯的,而且是全世界統計教學裡最常見的誤解。

**為什麼是錯的**:可以類比反證法,但要看清楚差在哪裡。反證法的邏輯是——假設 P 為真 → 推導出邏輯矛盾 → 所以 P 不成立,這是**確定性推論**,矛盾就是矛盾。但假設檢定的邏輯是——假設虛無假設為真 → 算出「觀察到這組資料」的機率很低 → 所以虛無假設「可能」不成立,這只是**機率上的傾向**。機率很低的事情不代表不可能發生,只是比較少見。p < 0.0001 代表「如果虛無假設是真的,這組數據大概每一萬次裡才會出現一次這麼極端的結果」,但那一次還是有可能真的發生。研究者拒絕虛無假設時,永遠帶著一個「萬一正好碰上小機率巧合」的風險,這個風險有名字,叫 **Type I error(第一型錯誤)**。

**具體代入論文的數字**:Sign test 給出「42:6:121,p < 0.0001」,正確的講法是:「**如果**treatment 跟 control 真的一樣強,那麼在 169 題裡隨機決定誰贏誰輸,出現『42 題 treatment 贏、只有 6 題 control 贏』這麼懸殊、或比這更懸殊的比例,機率低於萬分之一」——因為這個機率低到不合理,研究者選擇拒絕「兩者一樣強」的假設,但這個決定本身永遠保留了一個判斷錯誤的可能性,不是邏輯上的鐵證。

**顯著性會因為樣本單位的選擇而翻盤**,這是這個概念最實用的延伸應用,見下方 [核心概念 F]。

### [F] Repository-level 敏感度分析是什麼

**Repository(程式碼庫)**指的是任務來自哪一個開源專案。SWE-bench 系列 benchmark 的任務都是從真實 GitHub 專案的歷史 issue 挑出來的,論文的 169 個 Verified 任務集中在 **11 個** repository 裡(平均一個 repository 貢獻約 15 題),Pro 也是 11 個,FeatureBench 是 22 個。

**要檢查的問題**:前面所有 sign test / McNemar test 都把「每一個任務」當作獨立樣本。但同一個 repository 底下的多個任務可能共享相似的程式碼風格、bug 類型——它們不見得是統計上真正獨立的樣本。如果 Treatment 剛好對某個 repository 的程式碼風格特別合拍,task-level 統計會把這個 repository 裡的每一題都算成一次獨立的「贏」,顯著性可能被少數幾個合拍的專案灌水撐起來。

**具體做法**:把同一個 repository 裡所有任務的差值先平均成一個數字,變成「以 repository 為單位」的一筆資料,再重新做 sign test。示範計算(以下為說明用的簡化範例,非論文原始資料):假設某個 repository 底下有 5 題,F2PF 差值分別是 +0.40、+0.30、+0.20、+0.10、+0.00,repository-level 做法會先平均成 (0.40+0.30+0.20+0.10+0.00)/5 = 0.20,這個 repository 最終只貢獻**一筆**「正」的資料,而不是 5 筆。

**論文真實結果**(附錄 Table 12/13):

```
比較項目                    task-level p值        repository-level p值(Holm校正)
Verified F2PF                <0.0001               0.0469(勉強顯著)
Verified resolution          <0.0001               0.0625(不顯著)
Pro F2PF                     <0.0001               0.00586(依然強顯著)
Pro resolution                <0.0001               0.00586(依然強顯著)
FeatureBench F2PF            <0.0001               0.00586(依然顯著)
FeatureBench resolution      1                      1(完全沒訊號)
```

**這組結果要怎麼解讀**:除了 FeatureBench F2PF 那組有 2 個 repository 反過來偏向 control 之外,其餘所有比較裡「control 贏」的 repository 數量都是 0——也就是說,顯著性的消失**主要不是因為方向出現分歧**(不是有些 repo 撐 treatment、有些撐 control),而是樣本數從 169 壓縮到 11~22 個之後,單純沒有足夠的樣本量把這個(仍然一致的)方向訊號推過統計顯著的門檻,加上 Holm 多重比較校正又進一步拉高了門檻。真正在兩個檢定層級都穩定顯著的,只有 SWE-bench Pro;Verified 跟 FeatureBench 的 resolution 提升,證據強度比 task-level 數字表面上看起來要弱得多。