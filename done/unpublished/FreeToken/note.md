# FreeToken 讀論文筆記

> 論文:FreeToken: Efficient Edge-Native MoE Serving with Bandwidth-Adaptive Execution
> 作者:Shuo Yang, Xiaoze Fan 等(UC Berkeley / MIT / Databricks 等機構聯合),arXiv 2608.16157v1(2026年8月)

---

## 📌 30 秒版本

FreeToken 是一個讓「消費級 GPU」也能跑「超大型 MoE 模型」的 serving 系統(例如單張 RTX PRO 6000 跑 753B 參數的 GLM-5.2)。核心問題是:MoE 模型完整的專家(expert)權重太大,裝不進一般人電腦的 GPU 記憶體,必須把大部分放在主機記憶體(CPU 端),GPU 只能放一部分,需要時再搬。

**這篇論文的價值判斷(直接講結論):工程整合價值高,研究原創度低。**

- 用到的每一項底層技巧——雙緩衝(double buffering)、LRU 快取、CUDA Graph 動態化、頻寬平衡——全部是計算機系統裡的經典手法,沒有一項是這篇論文發明的。
- 這篇論文真正的貢獻,是**判斷這些經典技巧該怎麼組合、套用在「MoE + edge 硬體限制」這個特定情境**,並且把整套動態決策邏輯塞進 CUDA Graph(工程含金量最高的部分)。
- 最像「原創計算」的部分——q* 頻寬分配公式——論文自己完全沒有做單獨的消融實驗(ablation),沒辦法回答「這個公式本身」到底貢獻了多少效能,這是這篇論文實驗驗證最薄弱的一環。

如果你只有 30 秒,記住一件事就好:**這篇論文教會你的,與其說是「MoE serving 的新演算法」,不如說是「一套解決『動態決策 vs. 靜態圖執行』矛盾的工程思路」——這個思路可以遷移到很多跟 GPU 平行運算沾邊的場景,遠比 FreeToken 這個系統本身有用。**

---

## 📖 概念補充索引

以下這些段落,是這次討論過程中,順著論文延伸出來、值得獨立閱讀理解的背景概念。每一段都寫成「脫離這篇論文也成立」的形式,可以直接跳讀:

1. [PCIe 與電腦裡的匯流排](#concept-pcie)
2. [MoE 一層裡實際發生的事:不是選 1 個,是選 k 個加權混合](#concept-moe-layer)
3. [Double buffering 隱藏的是延遲,不是消除傳輸量](#concept-double-buffer-limit)
4. [線性 / 遞迴注意力機制(Linear Attention)完整介紹](#concept-linear-attention)
5. [為何 decode 不能比照 prefill 做「跨層」double buffering](#concept-no-cross-layer)
6. [Memory-bound vs. Compute-bound:GPU 算得快 ≠ 處理得快](#concept-membound) ⭐ 全篇最重要的觀念修正
7. [GPU Kernel 與 Kernel Launch:為什麼「叫 GPU 做事」本身要花時間](#concept-kernel)
8. [CUDA Graph 的底層運作:Capture 與 Replay](#concept-cuda-graph)
9. [GPU 上的平行去重:排序 + 相鄰比較](#concept-dedup)
10. [平行 Prefix Sum(Hillis-Steele 演算法)](#concept-prefix-sum)

---

## 一、背景知識(不假設任何先備知識)

### 1.1 什麼是 MoE,一層裡面實際發生什麼事

<a id="concept-moe-layer"></a>
現在的大型語言模型,一層(layer)通常長這樣:輸入先過 self-attention,再過一個前饋網路(FFN)。**MoE(Mixture-of-Experts)架構,是把「一個 FFN」換成「一整組(可能上百個)FFN,每個都叫做一個 expert」**,但每個 token 通過這一層時,不是用全部 expert,而是先經過一個「路由器(router)」,選出分數最高的 **top-k 個 expert**,把這 k 個 expert 各自的輸出做加權平均。

```
輸入 token 的 hidden state
        │
   [Self-Attention]
        │
   [Router 路由器] → 對這個 token 算出對每個 expert 的分數
        │
   選出分數最高的 top-k 個 expert(例如 k=12,總共 64 個 expert 可選)
        │
   E3, E7, E9, ..., E22 (12 個被選中的 expert,各自算一次 FFN)
        │
   把這 12 個 FFN 的輸出,依 router 給的權重加權加總
        │
   輸出 hidden state
```

這代表:雖然每個 token 只碰一小部分 expert(稀疏),但**完整模型要把所有 expert 的權重都存起來**——這正是 MoE 在邊緣裝置(edge)上難以服務的根源:算得動(稀疏),但裝不下(完整專家池很大)。

論文的例子:DeepSeek-V4-Flash 每層 256 個 expert 選 6 個,總共 284B 參數,但單一 token 只用到 13B——但完整的 284B(FP4 精度約 140GB)還是要有地方放。

### 1.2 什麼是 PCIe

<a id="concept-pcie"></a>
PCIe(PCI Express)是電腦主機板上通用的高速匯流排標準,不是專為 CPU-GPU 設計的——SSD、網卡也走 PCIe。但在「獨立顯卡」的場景下,GPU 這張卡是插在 PCIe 插槽上,所以「GPU 記憶體(VRAM)」和「主機記憶體」之間交換資料,走的就是這條通道。**在 MoE serving 的脈絡下,「PCIe 頻寬」可以直接理解成「GPU ↔ CPU 之間搬資料的速度上限」。**

對照組:資料中心的 GPU 之間常用 NVLink 這種更快的專屬互聯,頻寬比消費級 PCIe 高一個數量級以上——這是消費級硬體沒辦法像資料中心那樣處理龐大模型的原因之一。

---

## 二、論文想解決的三個痛點

### 痛點一:Prefill 階段——傳輸量是物理限制,搬不掉

Prefill 是模型一次讀完一大段 prompt、產生 KV cache 的階段(跟一個字一個字生成的 decode 相對)。因為 prompt 裡有成千上萬個 token,各自路由到不同 expert,**整體聯集幾乎會覆蓋這一層「所有」的 expert**——所以 prefill 幾乎要把整個專家池搬過 PCIe 一次。DeepSeek-V4-Flash 的例子:完整專家池(FP4)約 140GB,除以 RTX 5090 的 PCIe 頻寬(~60GB/s),要花 2 秒多——這是硬性的物理限制,沒辦法用排程技巧消除,只能設法別讓 GPU 空等。

<a id="concept-double-buffer-limit"></a>
> **⚠️ 概念澄清(容易搞混的地方):Double buffering 解決的不是「傳輸量太大」,而是「傳輸時間能不能被藏起來」。**
> 傳輸的總資料量沒有變小,140GB 該花的時間還是要花。Double buffering 只是讓 GPU 在等資料的同時,順便去算前一層——把「傳輸時間」和「計算時間」重疊,而不是消除傳輸。論文自己的實驗數字也印證這件事:關掉 double buffering,吞吐量只掉 19-26%(Figure 4a),如果它真的解決了「傳輸量太大」這個根本問題,關掉應該是災難性的下降,而不是兩三成的損失。

### 痛點二:Decode 階段——每一步都可能要臨時搬 expert,且沒有分配原則

Decode 一次只處理一個新 token,每一步只碰 top-k 個 expert。GPU 上放不下全部 expert,所以常會遇到「這步要的 expert 不在 GPU 上」(cache miss)。這時候有兩條路:把 miss 的 expert 搬過去 GPU 算,或是直接在 CPU 上原地算。現有系統(llama.cpp、KTransformers 等)沒有原則性方法決定這兩條路該怎麼分配。

### 痛點三:個人電腦的 GPU 資源不是穩定專屬的

跟資料中心整張卡專屬服務一個任務不同,一般人的電腦上,GPU 常常同時被其他程式(遊戲、瀏覽器)佔用。這代表 serving 引擎能用的 VRAM 額度,在運行過程中會浮動,不是啟動時分配好就固定不變。

---

## 三、方法:Prefill 階段的兩個機制

### 3.1 Full-layer Double Buffering

**做法:VRAM 裡任何時刻只保留「當前層 + 下一層」兩層份的 expert 緩衝區,不是整個模型都塞進去。**

```
時間點 t:
  Buffer A(正在算): layer l 的全部 expert 已在 GPU 上,GPU 正在計算
  Buffer B(正在搬): layer l+1 的全部 expert 正透過 PCIe 搬過來

時間點 t+1(layer l 算完後):角色互換
  Buffer B(正在算): layer l+1,GPU 開始計算
  Buffer A(正在搬): 被清空,開始接收 layer l+2 的全部 expert
```

以 DeepSeek-V4-Flash 為例:完整專家池 140GB ÷ 43 層 ≈ 每層 3.3GB,兩層合計約 6-7GB,即使 8GB VRAM 的筆電顯卡也放得下——這就是為什麼不需要整個模型塞進 GPU。

這個 buffer pool 跟 decode 用的 expert cache 是**共用同一個 slot pool**,不是分開兩套系統——prefill 結束後留在 GPU 上的 expert,可以被 decode 直接沿用。

如果 VRAM 連兩層份的空間都擠不出來(例如同時開著遊戲佔用大量 VRAM),FreeToken 會退回到「按需載入」模式,犧牲 pipeline 的好處換取不爆記憶體。

> **這是誰的貢獻?** Double buffering 本身是計算機系統裡幾十年歷史的通用技巧(FlexGen 等系統早就用在 dense model 上)。論文的貢獻在於:**判斷 MoE prefill 該「整層全搬」(而不是花力氣預測哪些 expert 會被用到,因為反正幾乎全部都會用到),並讓這個 buffer 跟 decode cache 共用記憶體池**——是工程判斷,不是技巧本身的原創。

### 3.2 Semantic-Aware State Cache

**背景概念:線性 / 遞迴注意力機制**

<a id="concept-linear-attention"></a>
前沿模型(Qwen3.6 用 gated DeltaNet、Kimi-K3 用 Kimi Delta Attention)混用了一種跟標準 attention 完全不同的層。這類方法統稱 **linear attention(線性注意力)**,奠基論文是 Katharopoulos et al. 2020《Transformers are RNNs》——核心洞察是:把 attention 用線性化的方式改寫,數學上等價於一個 RNN。DeltaNet 是這個大類別下的具體方法,用「delta rule」(erase-then-write,先局部抹除再寫入)做更新,這個概念借自 1960 年代訊號處理領域的 Widrow-Hoff rule。

標準 attention 的每個 token 的 K、V 向量,是**獨立存放**的(這就是 KV cache),可以事後任意切片重用——這正是 SGLang 的 radix prefix tree 能做「跨請求共享 prefix」的原因。

線性注意力層完全不同:它不存每個 token 的 KV,而是維護一個**固定大小、會不斷演化的狀態矩陣(state)**,新 token 進來時用「舊 state + 新 token」算出「新 state」,舊的被覆蓋。運作方式:

```
狀態 S 是一個固定大小的矩陣(不隨 token 數變大)
每個新 token: S_new = S_old + (k_t 外積 v_t)   ← 外積把向量變成矩陣,疊加進狀態

具體例子(簡化示範,非論文原始數字):
第1個 token: k_1=[1,0], v_1=[3,5] → 外積 [[3,5],[0,0]] 疊加進 S
第2個 token: k_2=[0,1], v_2=[7,2] → 外積 [[0,0],[7,2]] 疊加進 S
此時 S = [[3,5],[7,2]] —— 不管存了幾個 token,S 永遠是這個大小
```

**關鍵性質:資訊被壓縮進同一個矩陣,無法事後單獨抽出某一段的貢獻,也無法從後面的狀態反推更早的狀態。**

**這帶來的問題**:如果想保留某個時間點的狀態,必須在算到那個時間點的當下就額外存一份完整副本(checkpoint),事後補救不了。而 agent 每一輪對話幾乎都會修改 context(刪掉舊的 thinking、舊的 tool 輸出),導致之前的 checkpoint 失效,若沒有可用的 checkpoint,就必須整段重算。

> 論文提到,一份 checkpoint 的成本大約等於幾百個 token 份量的 KV cache,所以只能存少數幾個名額。論文沒有給出這個「幾百倍」的具體推導。一個直覺上合理的解釋方向(非論文原文,僅供理解量級參考):標準 KV 存的是「向量」,大小跟 head 維度成正比;線性注意力的狀態存的是「矩陣」,大小跟 head 維度的平方成正比——形狀從向量變矩陣,量級差距自然被拉開。

> **為什麼只有這類 attention 需要特殊處理,標準 attention 不用?** 標準 KV cache 每個 token 獨立存,砍掉某段 context 直接丟掉對應條目就好,其餘不受影響——這正是既有系統(如 SGLang 的 radix tree)已經解決得很好的問題。線性注意力的狀態是「所有歷史疊加壓縮進同一個矩陣」,砍掉中間一段等於要整個重新疊加——這個問題只長在這類層上。至於前沿模型為何要混用這類層:標準 attention 的計算量和記憶體是隨 token 數平方 / 線性成長,長 context 的 agent 場景下成本會爆炸,這是近年架構界普遍朝「混合式」(少數層標準 attention 保留精確度,大部分層用便宜的線性層)發展的一般性原因,不是這篇論文特有的討論。

**論文的具體解法:Semantic Anchors(語意錨點)**

判斷邏輯:去觀察真實 agent 框架怎麼砍 context——OpenClaw 只留最新的 thinking、OpenCode 用固定佔位符替換舊的 tool 輸出、SWE-agent 只留最後 n 筆觀察結果。**這些框架砍的永遠是「一整個語意區塊」**(一段完整的 thinking、一次完整的 tool call),不會砍到區塊中間,而這些區塊在 token 序列裡是用特殊 token 標記邊界的(如 `<think>...</think>`、`</tool_call>`、`</tool_output>`)。

**解法:checkpoint 存在「每一個」語意區塊的邊界上**,不是只存一個固定位置、也不是預測哪一段會被砍。

```
原始:  [system][reasoning][tool_call][tool_output][answer]
                                     ▲
                         checkpoint 存在這裡(tool_call 結束 /
                         tool_output 開始之前)

被砍後:[system][reasoning][tool_call][✂已刪除][新內容...]
                                     ▲
                         保留的 prefix 剛好在這裡結束
                         → 對得上剛才存的 checkpoint
                         → 只需重算「新內容」那段,不用整段重算
```

因為每個邊界都存了 checkpoint,不管 agent 這一輪實際砍的是哪一段,「保留下來的 prefix 結尾」必然會落在某個曾經存過的邊界上——不需要預測會砍哪裡。Checkpoint 名額用 LRU 回收,跟 KV cache 的 radix tree 是分開管理、獨立運作的兩套機制。

> **論文沒有交代的地方**:這些模型在原生(非 FreeToken)serving 方式下,線性注意力狀態原本是怎麼做 prefix reuse / checkpoint 的,論文完全沒有提到。這是一個值得之後獨立查證的問題。

---

## 四、方法:Decode 階段的兩個機制

### 4.1 LRU Expert Cache

**核心觀察:decode 時,相鄰步驟(同一層、不同 token)選中的 expert 有很高的重疊率**(論文引用的「路由一致性」實證觀察,Liang et al., 2025)。FreeToken 用最普通的 LRU(Least Recently Used)策略管理 GPU 上的 expert cache,不做任何預測。

```
GPU expert cache(容量有限,例如 12 個 slot)

t-1 步(同一層)用到: E3 E7 E9 E12 E17 E24 E5 E22 E48 E51 E60 E33
t   步(同一層)要用: E3 E7 E9 E12 E17 E24 E5 E22 [E31 E40 E56 E62]
                     └──── 這 8 個跟上一步重複 ────┘ └── 這 4 個是新的 ──┘

結果: 8 個 cache hit,4 個 cache miss(m=4)
LRU 順便淘汰最久沒被用到的 4 個 slot,騰出空間
```

> **注意這裡 t-1、t 指的是「同一層、不同解碼步驟(不同 token)」,不是跨層。** 是否能像 prefill 那樣做「跨層」double buffering(提前搬下一層的 expert)?**不行**,原因是資料依賴(data dependency):下一層要選哪個 expert,必須等這一層算出輸出、經過路由器才知道——這跟 prefill「反正幾乎全部都要用到,可以無腦全搬」的情況完全不同,decode 沒辦法「提前知道要搬什麼」。

<a id="concept-no-cross-layer"></a>

**每一層是不是各自獨立的 cache?——是,靠 (layer, expert) 聯合識別碼**

原文明講:cache 裡每個 slot 記錄的是「一個 (layer, expert) 配對」,不是單純「expert 編號」。所以第 1 層的 E5 和第 43 層的 E5 是兩筆完全獨立的記錄,不會互相競爭同一個 slot、不會出現跨層互搶的情況。真正會互相競爭 LRU 名額的,只有「同一層、不同解碼步驟」這個維度。

**論文自己的驗證(Figure 4b,caption:「Decode-time expert miss rate versus cache size (as a percentage of the expert pool) under the three engines' placement policies, replayed on identical routing traces; lines are means over W1–W4, bands the min–max range.」)**——拿同一組真實 routing 記錄,重播三種引擎的 placement 策略,在相同 cache 容量下比較 miss 率:

| Placement 策略 | 更新頻率 | Qwen3.6 miss 率 | DeepSeek-V4-Flash miss 率 |
|---|---|---|---|
| FreeToken(全域 LRU) | 每一步都更新 | 16% | 39% |
| KTransformers(prefill 時更新一次) | 只在 prefill 更新,之後固定 | 41% | 59% |
| llama.cpp(啟動時固定分配) | 從不更新 | 62% | 89% |

**規律:策略跟現實的「脫節程度」越高,miss 率越高。** 因為相鄰 token 的路由高度重疊,「最近用過的 expert」是預測「下一步會不會再用到」最有效的線索,而更新頻率越低,就越無法反映 decode 過程中實際發生的路由變化。

LRU 本身不是新演算法(作業系統分頁替換、CPU cache 幾十年來都在用),論文的貢獻是**觀察到 MoE 路由剛好具備適合 LRU 發揮的時間局部性**。

### 4.2 q* 頻寬分配公式:miss 掉的 expert 怎麼分

LRU cache 沒接住的 m 個 miss,有兩條路:搬去 GPU 算(cache fill,以後留在 cache 裡)、或留在 CPU 原地算(算完就算完,不留存)。

**關鍵洞察:這兩條路徑其實在搶同一個資源——主機記憶體頻寬。** 搬去 GPU 要從 DRAM 讀出來再送過 PCIe;CPU 原地算也要從 DRAM 讀出來才能算——都要跟同一個 host 記憶體頻寬池搶資料。全部走 PCIe 會把主機頻寬吃滿、CPU 反而讀不到資料;全部留 CPU 算,PCIe 完全閒置浪費。

**符號定義:**

| 符號 | 意義 | 單位 |
|---|---|---|
| m | 這一步這一層總共 miss 的 expert 數量 | 個 |
| q | m 個裡面,決定走「搬去 GPU」這條路的數量 | 個 |
| m - q | 剩下走「CPU 原地算」的數量 | 個 |
| S | 一個完整 expert 的權重大小 | bytes |
| B_PCIe | 實測 PCIe 傳輸頻寬 | GB/s |
| B_Host | 實測 CPU 執行 expert 運算的等效頻寬(受限於主機記憶體頻寬) | GB/s |

**推導:**

```
搬 q 個過 PCIe 要花的時間:
   T_fill(q) ≈ q × S / B_PCIe

PCIe 傳輸會佔走部分主機頻寬,CPU 只能用剩下的:
   剩餘頻寬 B_R = max(B_Host - B_PCIe, 0)
   T_cpu(m-q) ≈ (m-q) × S / (B_Host - B_PCIe)

兩條路徑同時進行(concurrent),整體延遲取決於較慢的那條。
最理想狀態是兩條路徑花的時間一樣長,令 T_fill = T_cpu:

   q / (m-q) ≈ B_PCIe / (B_Host - B_PCIe)

解出:
   q* ≈ m × (B_PCIe / B_Host)
```

**帶入論文 Figure 2 的例子(caption 見上方 3.2 節引用)完整走一次:** m=4,圖上標註「profiled: B_PCIe : B_Host ≈ 1:4」

```
q* = m × (B_PCIe / B_Host) = 4 × (1/4) = 1
```

驗證:Figure 2 圖上畫的正是 4 個 miss 裡「1 個走 fill(搬去 GPU)」「3 個走 CPU 原地算」,跟公式算出的 q*=1 吻合。

**邊界情況驗證公式合理性:**
- B_Host 趨近 B_PCIe(兩條路徑速度差不多)→ q* → m,全部搬去 GPU,退化成單純 cache fill
- B_Host 遠大於 B_PCIe(PCIe 是瓶頸)→ q* → 0,幾乎都留 CPU 算

工程細節:q* 算出來取整數,且無論如何至少保留 1 個 fill,讓 cache 持續「暖身」、不會因為某步算出 0 就完全停止更新。

<a id="concept-membound"></a>
> ### ⭐ 概念補充:Memory-bound vs. Compute-bound——這次討論最重要的觀念修正
>
> 第一直覺可能是:「GPU 運算能力遠勝 CPU,為什麼公式算出來反而是大部分 miss 留在 CPU 上算?」
>
> **答案是:q* 這個公式從頭到尾比較的不是「誰算得快」(compute,FLOPS),而是「誰能把資料送到位」(memory bandwidth,頻寬)。** GPU 的浮點運算能力(FLOPS)確實遠超 CPU,這點沒有錯。但 decode 階段有一個關鍵性質:**一個 token 對一個 expert 權重只用一次,不會重複利用來做很多次運算**——這種「讀一次權重、只做一次矩陣運算」的模式,在電腦體系結構裡叫 **memory-bound(記憶體頻寬受限)**:運算單元大部分時間是在「等資料從記憶體送過來」,而不是在「忙著算」,運算能力再強,資料沒到位,也只能空轉等。
>
> 用論文 Table 1(caption:「Test systems. BP is the measured host-to-device expert-transfer bandwidth over PCIe; BH is the measured effective bandwidth of the CPU-side MoE expert kernel.」)的實測數字看差距有多小:
>
> ```
> RTX 5090 顯存自身頻寬: 1-1.8 TB/s   ← 非常快,但這是「顯存內部」頻寬,不是這裡的瓶頸
> PCIe 5.0 x16 實測(B_PCIe): 約 49-53 GB/s   ← 這才是「送資料進 GPU」的瓶頸
> 主機 DDR5 雙通道實測(B_Host): 約 53.8-77.3 GB/s
> ```
>
> B_PCIe 跟 B_Host 其實是**同一個數量級**,B_Host 甚至常常略高。GPU 顯存本身 1-1.8TB/s 的高頻寬完全用不上——因為權重根本還沒送到顯存,就已經卡在 PCIe 這條「窄門」上了。
>
> **一句話收斂:把一個 expert 搬進 GPU、再享受 GPU 高速運算,瓶頸出在「搬」這一步,不是「算」這一步。既然搬跟直接在 CPU 上算,用的是差不多速度的資源(host 頻寬),不如省下 PCIe 這一趟,直接在 CPU 上就地算掉更划算。GPU 算力快,不等於「用 GPU 處理這個 miss」就快——決定速度的是「資料能不能送到手上」,不是「手腳快不快」。**

---

## 五、實作:CUDA Graph 相容的動態決策設計

這是論文工程含金量最高的部分,也是這次討論花最多篇幅釐清的地方。以下從最基礎的背景概念開始鋪,不假設任何 GPU 程式設計經驗。

### 5.1 背景:GPU 運算為什麼需要「CPU 下指令」

<a id="concept-kernel"></a>
**GPU 自己不會主動做事,永遠是「被動等指令」的角色,CPU 才是指揮全局、決定「現在要做什麼」的角色。**

比喻:CPU 像廚房主廚,GPU 像一台超級快的切菜機。主廚每一步都要開口下令:「切菜機,把這把菜切一切」,切菜機才會動作;切完了,主廚要親自檢查、決定下一步,再下一個新指令。

**什麼是 Kernel?** GPU 世界的「kernel」跟作業系統核心(OS kernel)是完全不同的兩個概念,只是借用了同一個英文單字。**GPU 的 kernel 指的是「一段會在 GPU 上,由成千上萬個執行緒同時平行執行的函式」。**

具體例子:把兩個各有 100 萬個元素的陣列逐一相加。

```
CPU 做法(循序): for i in range(1000000): c[i] = a[i] + b[i]
                一個一個算,依序做 100 萬次

GPU 做法: 寫一個 kernel,描述「單一一個元素該怎麼算」:
   __global__ void add_kernel(a, b, c):
       i = 這個執行緒的編號
       c[i] = a[i] + b[i]
   CPU 端下指令:「GPU,啟動 100 萬個執行緒,每個都跑 add_kernel」
   → 這個「啟動」的動作,就叫 kernel launch(核心啟動)
```

**為什麼每次 CPU 下令(kernel launch)本身要花固定的時間成本?** 這條路徑大致是:

```
CPU 準備指令(打包參數、記憶體位置)
    ↓
驅動程式做核對、排程
    ↓
透過 PCIe 把「要做什麼」的訊息送到 GPU(注意:這裡搬的是很小的指令封包,
                                      跟搬 expert 權重那種 GB 等級的資料不同)
    ↓
GPU 收到,排進自己的執行佇列
    ↓
真正開始執行運算
```

**時間成本主要集中在前面幾段(準備、排程、傳遞),不是最後的「真正運算」。** 每次通訊都有一個「起步」的固定延遲,不管傳的資料是 1 byte 還是 1000 bytes,這個起步延遲都差不多存在——這是通訊領域常見的現象,固定延遲跟資料量大小是兩回事(以下屬於一般計算機系統知識、非論文提供的具體數字:單次 kernel launch 的固定開銷量級大約在微秒等級)。

**這解釋了為什麼 decode 特別受傷:** decode 每一步的實際運算量很小(一個 token,一層,只碰 top-k 個 expert),運算本身花的時間可能跟這個「固定起步延遲」是同一個量級——「傳令」的固定成本佔比會被放得很大。相對地,prefill 一次處理幾千個 token,運算量本身很大,固定的傳令成本相對可以忽略。而且一個模型有 43 層,一次生成可能要跑幾百、幾千個 token,每層又不只一個 kernel(QKV 投影、softmax、輸出投影、FFN……),零碎的啟動次數會非常可觀。

### 5.2 CUDA Graph 的底層運作:Capture 與 Replay

<a id="concept-cuda-graph"></a>
**核心想法:與其每次都重新一個一個 kernel 分別下令,不如把整串固定的 kernel 呼叫順序「錄」一次,之後要重複執行時直接「重放」,不用每個 kernel 都重新走一次完整的傳令流程。**

比喻延伸:主廚每天早上都要對切菜機喊同一套指令「切紅蘿蔔→切洋蔥→切馬鈴薯」。與其每天重新喊三次,不如先把這三句話錄成一捲錄音帶,之後每天早上按一次播放鍵,整捲自動依序播完。

**底層具體發生的事(Capture 階段):** 不是錄「程式碼本身」,而是把一連串 kernel launch 各自變成一個「節點(node)」,把它們之間的依賴關係變成「邊(edge)」,組成一個**有向無環圖(DAG, Directed Acyclic Graph)**。

```
簡化例子,假設一層 transformer 有三個 kernel:
節點1: kernel_qkv_projection
節點2: kernel_attention        ← 依賴節點1做完
節點3: kernel_ffn              ← 依賴節點2做完

圖: [節點1] → [節點2] → [節點3]

圖裡記錄的內容包括:
- 每個節點對應哪個 kernel(指向 GPU 上已編譯好程式碼的指標)
- 每個節點要開多少執行緒、用多大的記憶體區塊(launch configuration)
- 每個節點用到的記憶體位址(通常是預先配置好、固定不變的一塊 GPU 記憶體)
- 節點跟節點之間的先後順序關係(邊)
```

這張圖錄製完成後,會被編譯成 GPU 驅動程式看得懂的低階描述,存放在 GPU 這一側。

**Replay 階段省下什麼:** 沒有 Graph 時,每個 kernel launch 都要重新走一次「CPU 準備 → 驅動驗證/排程 → PCIe 傳遞 → GPU 排隊」的完整路徑。**有了 Graph,CPU 只需要送出「一個」指令:「執行編號 X 的這張已編譯好的圖」**,GPU 驅動程式直接按照圖裡記錄好的節點順序依序執行——這個排程過程發生在 GPU 驅動程式這一側,不需要 CPU 每個節點都重新介入。

**為什麼「形狀不能變」是必要條件:** 沒有 Graph 時,驅動程式每次呼叫 kernel 都要重新做一次「合法性驗證」跟「排程規劃」(參數對不對、記憶體位置有沒有衝突、跟前一個 kernel 的依賴關係怎麼安排)——這些驗證跟規劃本身也要花時間,這正是「傳令」開銷裡「驅動程式排程/驗證」那一段。**Graph 的做法是把這些驗證跟規劃的工作,提前在 capture 階段做「一次」,結果存起來重複使用**。之後每次 replay,因為圖的結構(哪些 kernel、什麼順序、什麼依賴關係)保證跟錄製時一模一樣,驅動程式不需要重新驗證,直接照抄之前算好的排程結果執行。**一旦允許形狀改變(這次多插入一個 kernel,或某節點的執行緒數量變了),驅動程式就沒辦法安全地照抄之前的排程結果,必須重新驗證——等於失去了 Graph 想省下來的成本。**

**「分支」是什麼、為什麼 Graph 不能有分支:** 分支指的是「如果發生 A 情況就做 X,如果發生 B 情況就做 Y」這種需要臨時判斷的邏輯:

```
if m == 3:
    做 A 這串 kernel
elif m == 5:
    做 B 這串 kernel(kernel 數量、順序都跟 A 不一樣)

→ 這種「根據臨時算出來的結果,決定要跑哪一串不同的 kernel」,
  CUDA Graph 沒辦法錄,因為每次重放,實際會發生的 kernel 順序都可能不同,
  已經不是「同一張固定的圖」了
```

**這正是這篇論文遇到的矛盾**:decode 每一步,miss 的數量 m、要 fill 幾個(q)、該淘汰哪個 expert,全部要等路由結果出來才知道。**論文自己在 related work 也點名對照組的弱點在這裡:KTransformers 和 llama.cpp 都沒辦法在混合式(CPU+GPU)執行模式下維持 CUDA Graph 重放,因為排程決策留在 CPU 端做。**

### 5.3 論文的解法:把「動態決策」改寫成「固定形狀的資料處理」

**核心策略一句話:不管 m 是多少,每一步永遠固定跑「同一組」kernel,只是這組 kernel 內部處理的資料量、內容不同——用固定大小緩衝區 + 一個「有效數量(valid_count)」標記,取代 if/else 分支。**

```
緩衝區永遠固定配置成「最多 12 個」(top-k=12,一步最多就選 12 個 expert):

  slot: [E31][E40][E56][E62][空][空][空][空][空][空][空][空]
  valid_count = 4     ← 這個數字告訴後面的 kernel:只有前 4 格是真的資料

下一步,假設這次 miss 了 7 個:
  slot: [E10][E15][E22][E33][E48][E51][E9][空][空][空][空][空]
  valid_count = 7     ← 一樣的緩衝區大小,只是這次前 7 格是真的

不管這一步 miss 幾個,緩衝區「形狀」(12 格)永遠一樣
→ 對應的 GPU kernel 呼叫,永遠是同一個 kernel、同樣的執行緒配置
→ 圖的結構完全沒變,只是 kernel 內部讀到的 valid_count 不同
```

論文原文的說法是「dynamic control is represented as data inside a statically captured graph(動態的控制邏輯,被表示成靜態圖裡流動的資料)」——原本會寫成 if/else 分支的邏輯,改寫成「永遠執行、用一個數字欄位標記真正有效的部分是多少」。

**每一層決策具體拆成五步,以下逐步說明。**

#### 步驟一:去重(Deduplication)

**為什麼需要:** MoE 的路由是每個 attention head 各自獨立選 top-k,不同 head 選出的 expert 可能重複。例如 4 個 head 各自選 3 個:

```
Head 1: E5, E12, E31
Head 2: E12, E22, E31    ← E12、E31 跟 Head 1 重複
Head 3: E5, E9, E48
Head 4: E12, E48, E56

聯集(有重複): E5, E12, E31, E12, E22, E31, E5, E9, E48, E12, E48, E56
```

如果不去重,同一個 expert(如 E12)會被檢查 3 次,系統會誤以為需要處理 3 次,實際上只需要 1 次——因為不管幾個 head 用到它,這個 expert 的權重只有一份。

<a id="concept-dedup"></a>
**GPU 上怎麼平行做去重(排序 + 相鄰比較,計算機科學的通用技巧,非論文獨創):**

GPU 的強項是平行,沒有「一個一個依序處理」這種概念;如果用「共用一個集合、大家搶著寫入」的做法會遇到競爭條件(race condition)。標準解法是:**先排序,排序完之後重複的數字會自動變成相鄰,只需要拿每個元素跟前一個比較一次,就能平行判斷是否重複。**

```
去重前(未排序): E5, E12, E31, E12, E22, E31, E5, E9, E48, E12, E48, E56

第一步:排序(GPU 上有現成的高效平行排序演算法,例如 radix sort)
排序後: E5, E5, E9, E12, E12, E12, E22, E31, E31, E48, E48, E56

第二步:每個執行緒平行地跟「前一個位置」比較(完全平行,互不干擾,只讀不搶寫)
位置:      0   1   2   3    4    5    6    7    8    9   10   11
數值:      E5  E5  E9  E12  E12  E12  E22  E31  E31  E48  E48  E56
跟前一個比較: -  同  不同 不同  同   同   不同  不同  同   不同  同   不同
標記:     保留 丟棄 保留 保留  丟棄  丟棄  保留  保留  丟棄  保留  丟棄  保留

第三步:把「保留=1、丟棄=0」做一次前綴和(prefix sum),算出每個保留元素
       最終該落在去重後陣列的第幾個位置(這一步叫 stream compaction)

最終去重結果: E5, E9, E12, E22, E31, E48, E56(7 個,不重複,已排序)
```

這三個步驟(排序、相鄰比較、前綴和)都是「對固定大小的陣列套用同一種運算」,不管原始資料重複了幾次,要跑的「動作」都固定,只是處理的數值內容不同。

<a id="concept-prefix-sum"></a>
**Prefix Sum 怎麼平行運算(Hillis-Steele 演算法,計算機科學通用技巧):**

Prefix sum 定義:第 i 個位置的結果 = 原陣列第 0 到第 i 個全部加總。表面上看起來要循序做(要算第 5 個位置,似乎要先知道第 4 個位置的結果),但可以用「倍增」的方式打破這個限制:**每一輪讓每個位置「往前看的距離」倍增(1→2→4→8...),只需要 log(n) 輪,所有位置就能同時平行拿到正確答案。**

```
初始: 位置 0~7,數值 [1, 0, 1, 1, 0, 0, 1, 0]

第1輪(每個位置加上「前1格」的值):
結果: [1, 1, 1, 2, 1, 0, 1, 1]  (8個位置同時平行計算)

第2輪(每個位置加上「前2格」的值,用第1輪結果來加):
結果: [1, 1, 2, 3, 2, 2, 2, 1]  (同樣8個位置平行計算)

第3輪(每個位置加上「前4格」的值,用第2輪結果來加):
結果: [1, 1, 2, 3, 3, 3, 4, 4]  ← 跟循序累加算出的答案完全一致

8個元素,只花 log₂(8)=3 輪,每輪內所有位置同時平行計算,
沒有「等前一個算完才能算下一個」的循序等待。
```

這個「往前看距離每輪倍增」的安排,用「輪數的對數成長」換掉「逐一累加的線性等待」,是 GPU 平行運算裡的經典技巧。

#### 步驟二:分類 Hit / Miss

去重後拿到一份不重複的 expert 清單,逐一比對「目前 cache 裡有什麼」的對照表(residency table),標記每個是 hit 還是 miss:

```
目前 cache: slot0:E3 slot1:E7 slot2:E9 slot3:E12 slot4:E17 slot5:E24
            slot6:E5 slot7:E22 slot8:E48 slot9:E51 slot10:E60 slot11:E33

這一步需要的 7 個: E5, E9, E12, E22, E31, E48, E56

E5→slot6 HIT   E9→slot2 HIT   E12→slot3 HIT   E22→slot7 HIT
E48→slot8 HIT  E31→不在表裡 MISS   E56→不在表裡 MISS

結果: 5 個 hit, 2 個 miss → m = 2
```

如果對照表是雜湊表或直接定址陣列,每個執行緒可以完全獨立平行檢查「自己負責的那個 expert」是否存在——不需要跟其他執行緒溝通。

#### 步驟三:算出 q

用 q* 公式:`q* = m × (B_PCIe / B_Host)`,是一個純量對純量的四則運算(乘法、除法),不管 m 是 2 還是 200,運算量都一樣小,**這一步本身不需要平行**——這是合理的判斷,GPU 平行運算不是每件事都需要拆給很多執行緒。

**但即使不需要平行,這一步仍然必須留在 GPU 上做,不能丟給 CPU。** 原因不是效能(這一步耗時極短),而是**圖形完整性**:如果讓 CPU 算這個簡單的乘除法,會需要「GPU 算出 m → 傳回 CPU → CPU 算 q → 傳回 GPU」這個來回,這中間會產生同步等待,打斷了整條路徑被完整錄進同一張 CUDA Graph 的可能性。

> **要不要平行是效能考量,要不要放在 GPU 上是圖形完整性(避免任何「GPU 算到一半要跑去問 CPU」的中斷點)的考量——這是兩個獨立的判斷維度。**

#### 步驟四:選 LRU 淘汰候選

要淘汰的數量,恆等於要 fill 的數量 q(一個蘿蔔一個坑:要塞 q 個新 expert 進 cache,就要騰出 q 個空位)。

**問題:如果做法是「淘汰一個→重新掃描找下一個最舊的→再淘汰」,這個「要掃幾遍」的次數會跟著 q 變動,違反「圖的形狀不能隨資料內容改變」的原則。**

**解法:一次排序,找出完整的淘汰候選名次表,之後不管 q 是多少,永遠只需要「讀取排序結果的前 q 名」。**

```
12 個 slot 依 recency(多久沒被用到)由小到大排序,得到完整名次表:
第1名(最該淘汰): slot10   第2名: slot9   第3名: slot8 ...(共12名)

排序這個「貴」的動作,永遠只做一次、固定對12個slot做
之後不管 q=1 還是 q=3,「取前 q 名」只是讀取陣列前面第幾格,
是 O(1) 的讀取,不需要因為 q 變大就重新掃描
```

排序本身可用 GPU 上常見的平行排序法(如 bitonic sort)完成,比較/交換步驟數量不受輸入資料內容影響,形狀固定。

#### 步驟五:轉換成實體 Slot 編號

前四步用的都是 expert 的邏輯編號(像 E31),但 GPU 硬體實際執行運算需要的是「這個 expert 的資料放在 GPU 記憶體的哪個實際位址」。這一步把邏輯編號轉換成具體指令:

```
E5, E9, E12, E22, E48(hit) → 直接標記各自對應的既有 slot,不用動
E31(miss, q=1 選中要 fill) → 標記「從 host 搬進 slot10(原本的 E60 被蓋掉)」
E56(miss, 剩下的留CPU算)  → 標記「CPU_FLAG,不進GPU cache,送去CPU執行」
```

這一步同樣可以完全平行:每個 expert 各自查一次自己該對應到哪個實體位置或標記,彼此獨立。轉換完的結果,就是接下來實際搬資料、實際執行運算的 kernel 要讀取的輸入。

**CPU 那一路,也被納入同一張圖:** GPU 把需要的資料複製到 CPU、透過一個 host function 通知 CPU 開始算、CPU 算完再複製回來——這整條路徑跟 GPU 自己那條路,一起被錄進圖裡同步重放,兩條路徑真正並行,而不是「GPU 做完才輪到通知 CPU」。

### 5.4 一個 Token 生成時,實際發生的事

一整張 CUDA Graph 錄的不只是一層,而是**一個 token 要走完全部層(例如 43 層)的完整流程**:

```
一整張 CUDA Graph(代表「產生下一個 token」需要做的所有事):
第1層: [attention kernel]→[五步驟決策]→[搬資料/GPU算/CPU算]→[合併輸出]
第2層: [attention kernel]→[五步驟決策]→[搬資料/GPU算/CPU算]→[合併輸出]
...
第43層:[attention kernel]→[五步驟決策]→[搬資料/GPU算/CPU算]→[合併輸出]
    ↓
輸出這個 token 的機率分佈
```

**每一個新 token 要生成時,都是「重放(replay)」同一張圖一次**,不是每個 token 都重新錄一次。錄製(capture)只需要在引擎啟動、暖機時做一次;一個回應可能要生成幾百、幾千個 token,每個 token 都重複利用同一張已錄好的圖——這正是這整套設計划算的地方:省下來的是「重放」相對於「一個一個 kernel 重新下令」的開銷。圖的結構(層數、每層固定的 kernel)保持不變,重放時真正變的只是緩衝區裡填的數字內容(這一步的 m、q、要搬哪個 expert)。

> **這整套五步驟決策機制,完全是針對 MoE 架構的「expert 選擇」而設計的,如果模型不是 MoE(是傳統 dense 模型),這套機制不適用。** 這不是論文的疏漏,而是論文一開始就設定好的研究範圍——標題就寫著「Edge-Native **MoE** Serving」。Dense 模型每層是固定的 FFN,沒有「選 expert」這回事,遇到的問題(模型太大裝不下)要用完全不同的技巧(按層分布、量化等,即 §6 提到的 FlexGen、DeepSpeed-Inference 那類系統)解決。

> **論文沒有交代的地方:** prefill 階段的 double buffering kernel 呼叫,是否也被錄進 CUDA Graph,論文完全沒有明講,§4.1 只聚焦在 decode 的五步驟機制上。

---

## 六、彈性記憶體管理(§3.3,簡短)

兩個機制,概念上都是系統工程裡常見的資源管理手法,沒有特別的巧思:

**Runtime cache reconfiguration:** GPU 記憶體要分給 KV cache 跟 expert cache 兩塊,這個劃分「不是啟動時固定的」。在「排程器認定安全的時間點」,FreeToken 可以重新計算兩塊的比例並重建 expert cache 大小,不需要重啟引擎、不需要重新讀取 CPU 端的完整 expert pool——因為 CPU 端那份才是「正確答案的唯一來源」,GPU 上的 cache 只是加速用的副本,重建只影響效能不影響正確性。

> **論文交代不清楚的地方:** 論文明確描述的是「重建 expert cache」的機制,但沒有具體說明重新配置 VRAM 預算時,KV cache 那塊具體怎麼被同步調整——只在背景段落提到兩者共享同一塊可調整的 VRAM 預算、分配「不是啟動時固定的」。

**Fast engine bootstrap:** 讀取硬碟資料時直接讀進最終要用的記憶體格式,省掉一次多餘的搬運;完全不做 GPU warmup,直接開始服務第一個請求,cache 在正常服務過程中自然「變熱」(用的是 decode 階段本來就有的 miss 處理機制)。

---

## 七、實驗結果(精簡)

**實驗設置:** 六台機器(8GB 筆電顯卡到工作站級 RTX PRO 6000),對照組是 llama.cpp、Ollama、KTransformers、MoE-Infinity,用四個真實 agent workload(數學推理、兩種 coding agent、email/calendar agent)測試——不是合成 benchmark,這點是加分項。

**主要結果(RTX 5090):** decode 吞吐量比最強對照組快 1.5–2.3 倍(Qwen3.6 是 77–83 tok/s,DeepSeek-V4-Flash 是 22–25 tok/s)。多輪 agent 場景下吞吐量只比單輪掉 12% 以內,而 KTransformers 在 DeepSeek-V4-Flash 上從單輪到第二輪就已經掉了 31%,印證了「context 被砍要重算」的問題確實拖累對照組。尾端延遲(TTFT)差距更大:FreeToken 最差情況控制在 44 秒內,對照組某些情境拉到 150 秒以上(KTransformers 最差到 946 秒)——長到會被真實 agent 客戶端的逾時機制直接中斷連線。

**三個拆解實驗:**

- **Double buffering 的貢獻**(Figure 4a,caption:「Prefill TPS versus prompt length (RTX 5090, Qwen3.6-35B BF16), with and without FreeToken's pipelined full-layer loading.」):關掉它,prefill 吞吐量在長 prompt 時掉 19–26%,符合「隱藏延遲、非消除延遲」的預期,不是災難性下降。
- **Cache locality 的貢獻**(Figure 4b,見第四節表格):驗證得最乾淨的部分,LRU 在相同容量下 miss 率明顯低於對照組。
- **跨硬體穩定性**(Figure 5,caption:「Coding-agent decode TPS across consumer GPUs (SWE issues via the OpenCode harness), Qwen3.6-35B-A3B. 4060 laptop using NVFP4, the other Qwen3.6 columns BF16. The RTX PRO 6000 column is a separate demonstration: GLM-5.2 (753B-A40B, NVFP4) on the math workload; Ollama is not run there.」):五台不同等級消費機器上,優勢維持在 1.3–2.1 倍,不是只在特定硬體上調校出來的數字。

> **實驗驗證的缺口(值得注意):**
> - **q* 頻寬分配公式從未被單獨拆出來做消融實驗。** 所有端到端數字,永遠是「LRU cache + q* policy」綁在一起報的,無法回答「如果只用 LRU cache、但 miss 全部走 CPU(不做 q* 分配),效能差多少」——這是論文最像原創計算的部分,卻是驗證最薄弱的一環。
> - **論文沒有與 vLLM 比較。** 對照組只有 llama.cpp、Ollama、KTransformers、MoE-Infinity 四個,論文沒有說明原因(vLLM 只在 §4、§6 被提到是 FreeToken 借用其架構理念的基礎,不是效能對照對象)。

---

## 八、值得帶走的東西

### 桶一:這篇論文本身的貢獻

- 核心手法(double buffering、LRU cache、頻寬平衡分配、CUDA Graph 動態化)全部是計算機系統裡的經典技巧,沒有一項是這篇論文發明的。
- 這篇論文真正屬於自己的東西,是**把這些技巧組合起來、套用在「MoE + edge 硬體限制」這個特定情境的工程判斷**——特別是 q* 這個 closed-form 頻寬平衡公式(雖然數學本身很簡單,但「用兩個實測頻寬算出最優分配比例,且輕量到能塞進 CUDA Graph」是有意義的設計選擇),以及把整套動態決策塞進 CUDA Graph 五步驟這件事(工程含金量最高的部分)。
- 但連這個最像原創的部分(q*),論文自己都沒有單獨驗證貢獻有多大——這篇論文的說服力打了折扣,工程整合的完整度優於研究驗證的嚴謹度。

### 桶二:讀這篇論文過程中學到、脫離它也成立的東西

- **Memory-bound vs. compute-bound 的區分:** GPU 算力(FLOPS)遠勝 CPU,不代表「用 GPU 處理某個任務」一定比較快——當瓶頸在「資料能不能及時送到手上」而非「算得快不快」時,運算單元的強弱不是決定性因素。這是這次討論裡最顛覆直覺的觀念,適用範圍遠超過 MoE serving。
- **Kernel launch 的固定開銷,以及 CUDA Graph 用「錄製+重放」把它攤平:** 傳令的固定延遲(跟資料量大小無關)是理解 GPU 效能瓶頸的基礎概念。
- **CUDA Graph 要求形狀固定,逼出的設計模式:「用固定大小緩衝區 + valid_count 標記,取代 if/else 分支」——這是一個可遷移到其他「需要平行化、又有動態行為」場景的通用思路,不限於 GPU 程式設計。**
- **GPU 平行運算的兩個經典技巧:** 排序 + 相鄰比較做去重、Hillis-Steele 平行 prefix sum(用倍增取代逐一累加,log(n) 輪解決)——這兩個是計算機科學裡的通用演算法。
- **標準 KV cache vs. 線性/遞迴注意力狀態的本質差異:** 前者可以事後任意切片重用(每個 token 獨立存),後者是不可逆壓縮、只能靠 checkpoint 補救——這解釋了為什麼「prefix reuse」問題在不同注意力機制下難度完全不同。
- **讀論文 related work 時判斷「地基工具 vs. 窄坑競品」的原則:** 值得記住,某些系統(如 vLLM、SGLang)是整個領域共用的地基,值得單獨花時間深讀;同個 niche 裡的漸進式變體,通常讀 related work 摘要就夠了。