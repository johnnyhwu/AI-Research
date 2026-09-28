# TriAttention：在旋轉之前就讀懂注意力，把長推理的 KV Cache 砍到極限

## 前言

如果你讓一個大語言模型做一道要想很久的數學題，它常常得先在腦中「碎碎念」上萬個 token 才會給出答案。這種長鏈式推理（Chain-of-Thought）很吃記憶體：模型每生成一個字，都要把它的 Key 和 Value 向量存進 GPU 記憶體裡的 KV Cache，推理越長，這個快取就越肥大，遲早會把顯示卡的 VRAM 塞爆。

過去幾年出現了不少 KV Cache 壓縮方法，思路都差不多：邊生成邊觀察每個 Key 最近得到的注意力分數高不高，分數低的就丟掉。問題是，這些方法都是在「旋轉位置編碼（RoPE）」套用之後的空間裡做觀察，而 RoPE 的旋轉會讓分數隨著距離週期性地起伏——一個 Key 這一刻分數低，不代表它真的不重要，可能只是剛好轉到了波形的谷底，之後又會轉回高點。

傳統方法看不到這個「之後」，於是把很多其實還有用的 Key 提前刪掉了，等到後面真的需要用到時，早就找不回來。

這篇筆記要介紹的 TriAttention，走的是完全不同的路：它不在旋轉之後的混亂空間裡瞎子摸象，而是退回到旋轉之前的原始向量空間。作者發現，同一個 Attention Head 產生的 Query 和 Key 向量，即使輸入的文字千變萬化，方向也會高度集中在固定的中心點附近。這個「集中現象」讓整個問題出現了數學上的捷徑：把隨機變數換成固定的期望值，注意力分數就能簡化成一條只跟「相對距離」有關的三角函數曲線，在 Key 剛被寫入快取的那一刻就能預先算出它未來會不會被需要。

接下來的內容會照著這個邏輯走一遍：先搞懂 KV Cache 和 RoPE 到底在做什麼、傳統方法為什麼會失手，再看 TriAttention 怎麼利用幾何集中現象把預測問題變簡單，怎麼把數學公式落地成能跑在 GPU 上的演算法，最後用論文的實驗數據驗證這套想法到底有沒有用。中間會夾雜不少推導和公式，但每個公式出現前，都會先講清楚它背後在解決什麼實際問題。

---

## 一、KV Cache：用空間換時間的自迴歸生成

### 1.1 逐字生成，也逐字累積負擔

大語言模型輸出文字的方式是「自迴歸解碼（Autoregressive Decoding）」：模型一次只吐出一個 token，要生成第 $t+1$ 個字時，必須先看過前面第 $1$ 到第 $t$ 個字，理解它們的語意與彼此的關聯，才能決定下一個字是什麼。

如果每次生成都從頭開始算，情況會很糟。標準的 Self-Attention 運算，要為第 $t+1$ 個字重新把前面 $t$ 個字整批送進模型，重新做一次線性投影與注意力矩陣相乘。序列每變長一點，運算量就跟著呈平方成長，也就是 $O(t^2)$——生成到第一萬個字時，光是「複習前面說過什麼」這件事，運算量就是生成到第一千個字時的一百倍。這種算法在長文本場景下完全跑不動。

### 1.2 KV Cache：把算過的東西存起來，別再算第二次

工程上的解法是 KV Cache（鍵值快取），核心邏輯很直白：**用 GPU 記憶體的空間，換取重複運算的時間**。

在第 $t$ 步，模型的輸入只有剛生成的那一個 token 向量 $x_t$，把它投影成三種角色：

$$
q_t = x_t W_Q, \quad k_t = x_t W_K, \quad v_t = x_t W_V
$$

算出 $k_t$、$v_t$ 之後不丟棄，而是接到已經存在記憶體裡的歷史矩陣尾端：

$$
\text{Cache}_K \leftarrow \text{concat}(\text{Cache}_K, k_t), \qquad \text{Cache}_V \leftarrow \text{concat}(\text{Cache}_V, v_t)
$$

當前的 Query 只要跟這個累積起來的 $\text{Cache}_K$ 做內積、再跟 $\text{Cache}_V$ 加權求和，就能得到這一步的注意力輸出：

$$
a_t = \text{softmax}\!\left(\frac{q_t (\text{Cache}_K)^T}{\sqrt{d_k}}\right)\text{Cache}_V
$$

> **為什麼可以這樣做？** 模型的投影矩陣 $W_K, W_V$ 是固定的，歷史 token 也不會變，所以同一個歷史 token 每次算出來的 Key、Value 都完全相同——沒有必要重算。KV Cache 就是把這些「算過就不會變」的結果直接存起來，讓每一步的運算複雜度從 $O(t^2)$ 降到 $O(t)$。

### 1.3 空間換來了，但空間本身也會用完

KV Cache 解決了算力問題，卻換來另一個現實限制：GPU 的 VRAM 是有限的。像 AIME 這種數學競賽題，模型光是推理過程就可能寫到 32K token，KV Cache 矩陣的長度 $t$ 也跟著線性暴增，一旦超過 VRAM 上限，服務就會直接 OOM（記憶體不足）當掉。

於是工程上得替 KV Cache 設一個硬性的**目標記憶體預算 $B$**（例如 $B = 2048$ 個 token）。一旦生成長度超過這個預算，系統就必須啟動「斷捨離」：替快取裡每一個 Key 評個重要性分數，只留下分數最高的前 $B$ 個，其餘的永久刪除。這個「怎麼評分、丟誰留誰」的演算法，就是各家 KV Cache 壓縮方法真正在比拚的地方，也是 TriAttention 這篇論文的主戰場。

TriAttention 最後端出來的成績單很直接：在 AIME25 上，跟完全不壓縮的 Full Attention 打平準確率（40.8%）的前提下，吞吐量提升了 2.5 倍，KV 記憶體則縮減到十分之一（10.7 倍）。

![AIME25 上的效能權衡圖，左圖顯示 TriAttention 在同樣準確率下吞吐量是 Full Attention 的 2.5 倍，右圖顯示同樣準確率下 KV 記憶體只需十分之一。](img-001)
*圖 1 — Qwen3-8B 在 AIME25 上的效能權衡：(A) 吞吐量 vs. 準確率，(B) KV 記憶體佔用 vs. 準確率。*

這個結果要怎麼做到，得先搞懂兩件事：一是大模型怎麼靠 RoPE 認識「位置」，二是傳統壓縮方法為什麼會被 RoPE 的旋轉騙倒。

---

## 二、RoPE：用旋轉角度幫注意力裝上座標

### 2.1 Attention 天生不知道誰在誰前面

標準的縮放點積注意力 $\text{softmax}(QK^T)V$，本質上只是在算向量之間的相似度，完全不管 token 在句子裡的先後順序——它分不出「狗咬人」和「人咬狗」的差別。這是 Self-Attention 與生俱來的「排列無關性」問題，模型需要額外的機制告訴它「這是第幾個字」。

早期的做法是把一個位置向量直接加到輸入特徵上（絕對位置編碼），但這種做法外推性很差：如果訓練時只看過長度 512 的序列，推論時遇到第 1000 個位置，模型會因為沒看過對應的位置向量而表現失常。真正好用的位置編碼，得讓 Query 和 Key 的內積結果只跟兩者的「相對距離」有關，跟它們各自的絕對位置無關——這正是 RoPE（Rotary Position Embedding，旋轉位置編碼）要解決的問題。

### 2.2 用旋轉取代加法

RoPE 放棄了加法，改用「旋轉」把位置資訊注入向量。它不動原始輸入 $x$，也不動負責語意的 Value 向量，只對用來配對比較的 Query 和 Key 動手——這樣語意內容才不會被位置資訊干擾。

在最基礎的二維空間裡，一個位於序列第 $m$ 個位置的向量 $q$，會被乘上一個旋轉角度為 $m\theta$ 的旋轉矩陣：

$$
q'_m = \mathbf{R}_{\theta, m}\, q = \begin{pmatrix}\cos(m\theta) & -\sin(m\theta) \\ \sin(m\theta) & \cos(m\theta)\end{pmatrix}\begin{pmatrix}q_1 \\ q_2\end{pmatrix}
$$

位置越靠後的 token，向量被轉的角度就越大，等於是幫每個 token 在座標平面上「貼上」了一個獨一無二的指針方向。

### 2.3 旋轉之後，內積只剩下「距離」

RoPE 真正巧妙的地方，在於證明了這種旋轉可以精準地讓內積結果只剩下相對距離。位置 $m$ 的 Query 跟位置 $n$ 的 Key 做內積，推導過程是：

1. **展開內積**：$\langle q'_m, k'_n \rangle = (\mathbf{R}_{\theta,m} q)^T (\mathbf{R}_{\theta,n} k) = q^T \mathbf{R}_{\theta,m}^T \mathbf{R}_{\theta,n} k$
2. **轉置等於逆旋轉**：$\mathbf{R}_{\theta,m}$ 代表順時針轉 $m\theta$，它的轉置矩陣 $\mathbf{R}_{\theta,m}^T$ 就是逆矩陣，等於逆時針轉 $m\theta$。
3. **兩次旋轉疊加**：先逆時針轉 $m\theta$、再順時針轉 $n\theta$，淨效果就是順時針轉 $(n-m)\theta$，也就是 $\mathbf{R}_{\theta,m}^T \mathbf{R}_{\theta,n} = \mathbf{R}_{\theta, n-m}$。
4. **最終結果**：$\langle q'_m, k'_n \rangle = q^T \mathbf{R}_{\theta, n-m}\, k$

這個結果的意義很直接：不管兩個 token 在文章的第幾頁，只要它們的相對距離 $\Delta = n - m$ 不變，內積運算所經歷的旋轉角度就完全一樣。這就是相對位置編碼的核心——距離解耦。

### 2.4 一個頻率不夠用，那就疊上 64 個

只用單一頻率 $\theta$ 會有個麻煩：當相對距離 $\Delta$ 大到讓 $\Delta \cdot \theta$ 剛好繞完一整圈（$2\pi$ 的整數倍），旋轉角度就會繞回原點，模型會分不清楚「距離很近」跟「距離很遠但剛好多轉了一圈」有什麼不同。

RoPE 的解法是把高維向量兩兩一組拆成多個二維平面（例如 128 維拆成 64 組），每一組各自分配不同的旋轉頻率：

$$
\theta_i = \theta_0^{-\frac{2(i-1)}{d}}, \quad i \in \{1, 2, \dots, 64\}
$$

（其中 $\theta_0$ 通常取 10000 或更大的常數。）

這可以想成時鐘的指針：高頻的那幾組平面轉得快，對位置變化非常敏感，負責抓住鄰近字詞的順序；低頻的平面轉得極慢，要數萬個 token 才轉一小圈，負責維持長距離的整體記憶。64 個不同頻率疊加起來，幾乎不可能在合理的序列長度內產生完全重複的旋轉模式。

這套機制解決了位置編碼的問題，卻也埋下了下一章要講的隱患：這 64 個頻率各自的旋轉週期，會讓觀察角度不對的壓縮演算法，把還有用的 Key 誤判成沒用。

---

## 三、傳統壓縮方法的死角：Post-RoPE 空間裡的旋轉盲區

在講 TriAttention 的創新之前，得先弄清楚為什麼現有的壓縮方法一遇到長推理鏈就會出包。癥結只有一句話：**傳統方法全都是在「旋轉之後（Post-RoPE）」的空間裡做觀察與淘汰決策。**

### 3.1 以 H2O、SnapKV 為例：被動觀測的四個步驟

傳統方法本質上是一種被動的動態觀測，不去研究矩陣本身的幾何偏好，只靠歷史注意力分數做統計。整個流程可以拆成四步：

1. **取得已旋轉的特徵**：在時間步 $t$，拿到已經套用 RoPE 的當前 Query $q'_t = \mathbf{R}_t q_t$，以及快取裡已旋轉的歷史 Key 矩陣。
2. **計算真實注意力分數**：$a_{t,j} \propto \exp\!\left(\dfrac{q_t^T \mathbf{R}_{t-j}\, k_j}{\sqrt{d_k}}\right)$，其中 $j$ 跑過所有歷史位置。
3. **累加分數**：維護一張分數表 $S$，每前進一步就把當前分數加進去（或只統計最近一個觀察窗口內的平均值）：$S[j] \leftarrow S[j] + a_{t,j}$
4. **淘汰決策**：快取超出預算 $B$ 時，把 $S$ 排序，砍掉分數最低的那些 Key。

### 3.2 旋轉燈塔：分數為什麼會忽高忽低

問題就出在第二步的內積項 $q_t^T \mathbf{R}_{t-j}\, k_j$ 裡。可以把當前的 Query 想像成一座旋轉燈塔，歷史的 Key 是海面上的礁石——因為旋轉矩陣 $\mathbf{R}_{t-j}$ 會隨著時間推進不斷改變角度，燈塔的光束其實是在海面上一直掃來掃去的。

內積的底層是餘弦函數 $\cos(\omega_f \Delta + \phi_f)$。同一把已經存進快取的 Key，$k_j$ 本身不會變，但隨著時間步從 $t$ 走到 $t+100$，相對距離 $\Delta$ 一直在變，這把 Key 拿到的分數自然會跟著出現週期性的波峰與波谷。換句話說，**一個分數很低的 Key，未必是真的不重要，很可能只是恰好被旋轉轉進了函數的波谷。**

### 3.3 短期觀察窗口造成的致命誤殺

為了控制運算開銷，傳統方法通常只看最近一小段觀察窗口（例如最近 32 步）來評估 Key 的重要性。這種「短期統計」疊加「週期性震盪」，會在長推理場景下釀成無法挽回的錯誤：

- 如果一把關鍵的 Key，剛好在這 32 步的觀察窗口內處於波谷，它拿到的分數會長期趨近於 0；
- 傳統演算法判定它沒用，永久刪除；
- 但當生成再往前推進 500 步，旋轉角度理應讓這把 Key 轉回波峰、與未來的 Query 產生強烈共振——可惜它已經在初期被誤殺，未來的 Query 永遠檢索不到它了。

論文把這種暫時沒被關注、但之後仍有價值的 Key 稱為「冬眠 Key（Dormant Keys）」。在數學推導或 DFS 回溯這類任務裡，很多關鍵的中間條件都會先進入冬眠狀態，之後才被重新用到。傳統方法識別不出冬眠與真正沒用的差別，一律砍掉，結果就是推理鏈半路斷裂。

![Post-RoPE 空間中不同輸入序列的 Q/K 向量呈弧形散落分佈，特徵被打散成毫無規律的形狀。與 Pre-RoPE 空間裡向量高度集中的樣貌形成強烈對比。](img-002)
*圖 2 — Q/K 集中現象與其對注意力的影響：(A) Pre-RoPE 空間中同一個 Head 的 Q/K 向量高度集中；(B) 旋轉之後（Post-RoPE）向量呈弧形散落；(C) 集中度指標 $R$ 在絕大多數 Head 上都趨近 1；(D) 集中度與注意力重建品質的相關性。*

上圖的 (B) 就是傳統方法實際觀察的樣子：向量被旋轉打散成一圈一圈的弧形，完全沒有穩定的統計規律可循。這也是為什麼傳統方法注定會在長序列上栽跟頭——它們觀察的空間本身就是混亂的。那有沒有辦法退回到旋轉發生之前，看看向量原本的樣子？答案就在下一章。

---

## 四、破局點：Pre-RoPE 空間裡的 Q/K 集中現象

TriAttention 的作者把觀測視角整個倒轉過來：與其在混亂的 Post-RoPE 空間裡硬找規律，不如回到套用旋轉之前的原始空間看看向量長什麼樣子。結果他們發現了一件過去很少被認真討論的事。

### 4.1 什麼是 Q/K 集中現象

這裡不再看已經旋轉過的 $q'_t = \mathbf{R}_t q_t$，而是直接看線性投影出來、還沒被旋轉的原始向量 $q_t$ 和 $k_j$。

作者發現，對於某一個特定的 Attention Head 來說，即使輸入了成千上萬個語意完全不同的 token（名詞、動詞、數字、標點……），這些 token 投影出來的 $q$、$k$ 向量並不會在空間裡四處亂飛。相反地，有高達八到九成的維度，會死死地聚集在一個固定、非零的中心點附近。

換個比喻：如果把每個 token 的 Query 向量想成廣場上的一根指針，Post-RoPE 空間看到的畫面，是一萬根指針因為被賦予不同旋轉角度，均勻散佈在 360 度的圓盤上（如上圖 (B)）；而 Pre-RoPE 空間看到的，卻是這一萬根指針幾乎完美疊在一起，穩穩地指向同一個方向（如上圖 (A)）。這個現象就是論文所稱的 **Q/K Concentration**。

### 4.2 怎麼量化「集中」這件事：平均結果長度 $R$

光憑肉眼看 2D 投影圖不夠嚴謹，作者借用了方向統計學（Directional Statistics）裡的經典指標——平均結果長度（Mean Resultant Length），記作 $R$。對於某個頻率 $f$，集中度定義為：

$$
R_f = \frac{\|\mathbb{E}[q_f]\|}{\mathbb{E}[\|q_f\|]}
$$

這個公式的分子和分母代表兩種不同的幾何操作，值得拆開來看：

| 項目 | 計算順序 | 代表意義 |
|---|---|---|
| 分母 $\mathbb{E}[\|q_f\|]$ | 先算每個向量的長度，再取平均 | 這群向量的「平均力量」 |
| 分子 $\|\mathbb{E}[q_f]\|$ | 先把向量兩兩相加，再量總和向量的長度 | 向量相加後有沒有「累積」起來 |

當所有向量方向完全一致時，向量相加會產生完美的相長干涉，長度直接疊加不抵消，此時分子等於分母，$R \to 1$。反過來，當向量指向四面八方時，正負方向會互相抵消（相消干涉），加總後的向量長度趨近於 0，$R \to 0$。所以 $R$ 值越接近 1，代表這個 Head 的向量方向共識越高。

### 4.3 這不是巧合，是模型訓練完就固定下來的物理屬性

作者對 Qwen3-8B、Llama 3 等當代大模型做了大規模的 $R$ 值測量，結果相當驚人：

- Qwen3-8B 裡，高達約 **90% 的 Attention Head，$R$ 值都大於 0.95**——集中現象不是特例，而是普遍規律。
- 更關鍵的是，這個集中度跟**輸入的內容無關**：不管餵給模型的是數學公式、程式碼還是日常對話，同一個 Head 算出來的 $R$ 值與中心點位置幾乎完全一致，數值穩定在 0.977 到 0.980 之間。

![三種不同架構的 DeepSeek-R1 蒸餾模型（Qwen3、DS-Llama、DS-Llama-8B）上，注意力重建 Pearson 相關係數的分佈直方圖，平均值都落在 0.6 以上。](img-003)
*圖 3 — 不同架構的 LLM 上，注意力重建相關性的分佈都集中在中高相關區間。*

這說明集中現象並不是某個特定架構的偶然巧合，而是不同模型、不同架構都會出現的通性。背後的原因也不難理解：每一個 Attention Head 在訓練收斂之後，其實都變成了一個高度特化的「專家」——有的專門盯代名詞、有的專門檢索遠距離的名詞。這種專家的視角與幾何偏好，一旦訓練完成就已經**寫死在投影矩陣 $W_Q, W_K$ 裡**，成為模型的固有物理屬性，不會因為輸入文本不同而改變。

> **這一章是整篇論文能成立的地基。** 正因為 Pre-RoPE 空間裡的 $q_t$、$k_j$ 在方向與長度上幾乎不隨輸入變化，我們才能大膽把它們當成常數處理。一旦變數變成常數，原本令人頭痛的旋轉矩陣，就有機會被數學公式馴服——這正是下一章要做的事。

---

## 五、核心理論：三角級數預測與雙軌評分

有了「Pre-RoPE 向量高度集中」這個前提，TriAttention 徹底放棄了傳統的被動觀測，改走一條主動預測的路：在 Key 剛寫入快取的那一刻，就用數學公式預先算出它未來的整條「命運曲線」。

![論文提出的方法總覽圖，由左至右展示離線校準計算 Q 分佈中心，接著推論時原始注意力被拆解成雙軌評分並保留分數最高的前 B 個 Key。](img-004)
*圖 4 — TriAttention 方法總覽：離線校準求出 Q/K 中心點，推論時用雙軌評分決定每把 Key 的去留。*

### 5.1 把隨機變數換成常數中心點

標準的 RoPE 內積分數，是由三個變數共同決定的：當下的 Query（$q_t$）、歷史的 Key（$k_j$），以及相對距離（$\Delta = t - j$）。因為 $q_t$、$k_j$ 會隨著輸入文本不斷變化，這條分數曲線在傳統框架下完全無法預測。

但既然前一章證明了同一個 Head 的向量高度集中，我們就可以大膽做一次期望值替換：把隨機變數 $q_t$ 換成離線統計出來的中心點 $\bar{q} = \mathbb{E}[q]$，把 $k_j$ 換成 $\bar{k} = \mathbb{E}[k]$。原本的內積 $q_t^T \mathbf{R}_\Delta k_j$，就近似成 $\bar{q}^T \mathbf{R}_\Delta \bar{k}$——這個新式子裡，$\bar{q}$、$\bar{k}$ 都是已知常數，唯一剩下的未知數只有相對距離 $\Delta$。

### 5.2 三角級數：每個 Head 都有自己的「注意力—距離曲線」

把這個常數代入 RoPE 的 64 組不同頻率平面展開，對任意距離 $\Delta$，預期的注意力分數可以寫成：

$$
\text{logit}(\Delta) \approx \sum_{f} \|\bar{q}_f\|\, \|\bar{k}_f\| \cos(\omega_f \Delta + \bar{\phi}_f)
$$

用三角函數展開後，等價於：

$$
\text{logit}(\Delta) \approx \sum_{f} \big[a_f \cos(\omega_f \Delta) + b_f \sin(\omega_f \Delta)\big]
$$

這是標準的三角級數（Trigonometric Series）。它的意義是：每一個 Attention Head 其實都天生擁有一條屬於自己的「注意力—距離關係曲線」——64 個頻率的正餘弦波疊加起來，就像傅立葉合成一樣，決定了這個 Head 究竟偏好近距離（局部頭）、偏好某個特定的遠距離（檢索頭），還是對所有距離一視同仁（全局頭）。

### 5.3 評分軌道一：三角級數分數 $S_{trig}$

在推論階段，我們手上有 Key 真實的向量 $k$，但不知道未來的 Query 長什麼樣子，於是用離線校準出來的 Query 中心點 $\mathbb{E}[q]$ 當作「未來的代理人」。第一條評分公式就是：

$$
S_{trig}(k, \Delta) = \sum_{f} \|\mathbb{E}[q_f]\|\, \|k_f\| \cos(\omega_f \Delta + \phi_f)
$$

（其中相位差 $\phi_f = \arg(\mathbb{E}[q_f]) - \arg(k_f)$。）

可以把這條公式想成「發射器與收音機的共振預測」：根據這把 Key 真實的角度與強度 $\|k_f\|$，推算當未來的 Query 出現在距離 $\Delta$ 處時，旋轉角度是不是剛好能讓兩者對準頻率（$\cos$ 值接近 1，產生相長干涉）。如果預測會產生強共振，這把 Key 就該保留。

### 5.4 評分軌道二：語意模長分數 $S_{norm}$

$S_{trig}$ 有個先天限制：如果某個 Head 的 Q/K 集中度本來就偏低（向量方向變異大），純靠角度共振的預測就會失準。另外，有些極度關鍵的 token（例如系統提示詞、數學題目裡的關鍵條件）之所以重要，純粹是因為語意強度夠大（向量的模長夠大），跟它跟未來 Query 的相對距離沒什麼關係。

為了補上這個缺口，作者設計了第二條完全不看距離的評分：

$$
S^{(0)}_{norm}(k) = \sum_{f} \mathbb{E}[\|q_f\|] \cdot \|k_f\|
$$

這條公式拿掉了 $\cos$ 旋轉項，等於在說：「不管未來距離多遠、角度有沒有對準，只要這把 Key 本身的語意力道 $\|k_f\|$ 夠強，而且這個頻道又是未來 Query 喜歡聽的（$\mathbb{E}[\|q_f\|]$ 大），這把 Key 就有絕對保留的價值。」是一種「大喇叭效應」——聲音夠大，不管站在哪個角度都聽得到。

### 5.5 用集中度 $R_f$ 自動調節兩條分數的權重

最後一個問題是：$S_{trig}$（技巧型的共振分）跟 $S_{norm}$（絕對力量分）該怎麼融合？人為設一個固定的超參數，顯然沒辦法適應成千上萬個個性各異的 Attention Head。

作者巧妙地借用了第四章算出來的集中度指標 $R_f$，讓它自動扮演調節開關：

$$
S_{norm}(k) = \sum_{f} (1 - R_f) \cdot \mathbb{E}[\|q_f\|] \cdot \|k_f\|
$$

當某個頻率的方向極度集中（$R_f \to 1$）時，$(1-R_f)$ 趨近於 0，$S_{norm}$ 被壓到幾乎沒有貢獻，系統這時完全信任 $S_{trig}$ 的幾何距離預測；當方向變異較大（$R_f$ 偏低）時，$(1-R_f)$ 權重放大，$S_{norm}$ 介入補上一張「語意安全網」，彌補角度預測可能出現的誤差。最終把兩條軌道加起來，就是完整的評分公式：

$$
S(k, \Delta) = S_{trig}(k, \Delta) + S_{norm}(k)
$$

![真實的注意力圖對照，展示四個階段：計算 Q/K 中心點、三角級數評分捕捉距離偏好的對角線結構、加入語意模長分數後的整合結果，以及裁剪後仍保留關鍵注意力模式的效果。](img-012)
*圖 5 — 結合真實注意力圖的方法視覺化，對應論文圖 4 的架構示意，可以看到裁剪後的注意力圖仍精準保留了原始模式的關鍵結構。*

上圖用真實的注意力圖驗證了這套雙軌設計確實有效：裁剪之後的注意力模式，跟裁剪前的原始模式相比，關鍵結構幾乎沒有流失。接下來要處理的是工程問題——這套公式要怎麼在 GPU 上高效跑起來。

---

## 六、走向實用：工程落實與優化

有了完美的評分公式 $S(k, \Delta)$，要把它實裝成高效的 GPU 程式碼，還得解決三個現實問題：未來長度未知、逐字計算太頻繁、以及現代大模型常用的 GQA 架構會讓多個 Query Head 共用同一把 Key。

### 6.1 未來偏移量的幾何等比採樣

淘汰決策時有個邏輯悖論：公式需要代入相對距離 $\Delta$，但沒人知道快取裡這把 Key 究竟會在第幾步之後被用到——可能是第 10 步，也可能是第 10,000 步。

TriAttention 的解法是不賭單一時間點，而是把整條未來時間軸都納入考量，計算未來的平均期望分數：

$$
\tilde{S}(k) = \frac{1}{|\mathcal{D}|}\sum_{\delta \in \mathcal{D}} S(k, \Delta_0 + \delta)
$$

（$\Delta_0$ 是當下的距離，$\delta$ 是未來的偏移量。）

如果對未來 65,536 步逐一線性計算（$\delta = 1, 2, 3, \dots$），運算量是 $O(N)$，系統扛不住。作者改用幾何等比採樣：

$$
\mathcal{D} = \{1, 2, 4, 8, 16, \dots, 2^{16} = 65536\}
$$

評估跨度長達 6.5 萬步，實際只需要算 **17 次**。這個設計跟 RoPE 的多頻率結構天生契合：近處的高頻維度旋轉劇烈、分數變化快，需要密集採樣；遠處只剩低頻維度緩慢變化，分數波動很小，稀疏採樣就夠了。

這個「求平均」的動作，同時也是 TriAttention 不會重蹈傳統方法「週期性誤殺」覆轍的關鍵防線：即使當下（$\delta=0$）這把 Key 剛好落在波谷、分數很低，只要它在未來某個觀測點（比如 $\delta = 2048$）會迎來波峰，這個未來的高分就會在求平均時被捕捉進來，拉高整體評分 $\tilde{S}(k)$。結合 64 個頻率的波形疊加，系統能看穿單一頻率的週期性噪聲，抓到真正代表長期偏好的「波包」。

![未來偏移量消融實驗：上半部比較不同最大距離下的準確率，下半部比較線性採樣與幾何等比採樣的準確率差異，幾何採樣以 45.8% 大幅領先線性採樣的 28.7%。](img-016)
*表 1 — 未來偏移量設計的消融實驗：擴大評估距離、以及改用幾何等比採樣，兩者都能顯著提升準確率。*

數據說明了兩件事：把最大評估距離從 128 拉長到 4096，準確率從 41.7% 提升到 48.8%；而在距離固定的前提下，把線性間隔換成幾何等比間隔，準確率從 28.7% 一口氣衝到 45.8%。幾何採樣策略不是錦上添花，而是這套方法能成立的必要條件。

### 6.2 窗口化剪枝：不用每個字都重新算一次

如果每生成一個 token 就觸發一次全域評分、排序、裁剪，GPU 記憶體搬移會非常頻繁，拖慢整體延遲。TriAttention 的做法是設一個批次觸發窗口 $\beta = 128$：平時讓 KV Cache 正常增長，只有當累積生成滿 128 個 token、且總快取超過預算 $B$ 時，才觸發一次全局重新評分與裁剪。

重新評分時還有一個省算力的巧思：$S_{norm}$ 是 Key 寫入當下就固定的靜態語意特徵，不需要重算；只有 $S_{trig}$ 因為 Key「變老了」（相對距離 $\Delta_0$ 變遠）需要更新。這種動靜分離的設計，讓每次重新評分的線上開銷降到很低。

### 6.3 GQA 架構下的分數衝突：Z-Score 標準化加最大池化

當今主流大模型（Llama 3、Qwen 等）普遍採用 Grouped-Query Attention（GQA）架構：為了省 VRAM，$G$ 個獨立的 Query Head 會共用同一個 Key-Value Head。

這帶來一個衝突：快取裡同一把 Key，會被 $G$ 個中心點各不相同的「專家」同時打分，產生 $G$ 個尺度不一致的分數。如果直接加總，數值天生比較大（Norm 較大）的 Head 會完全蓋過數值小的 Head 的判斷，等於變相剝奪了某些專家的發言權。

TriAttention 用「先標準化、再池化」兩步解決這個問題：

**第一步：Z-Score 標準化。** 對每個 Query Head $g$，用它自己打出的所有分數算出均值 $\mu_g$ 與標準差 $\sigma_g$，把分數拉回標準常態分佈：

$$
\hat{S}^{(g)}(k) = \frac{\tilde{S}^{(g)}(k) - \mu_g}{\sigma_g}
$$

這一步消除了不同專家之間的「音量差異」，讓分數在跨 Head 比較時具有可比性。

**第二步：最大值池化。** 標準化之後，用 $\max$ 彙整所有 Head 的意見：

$$
S_{final}(k) = \max_{g \in \{0, \dots, G-1\}} \hat{S}^{(g)}(k)
$$

這是一種很保守的保護策略：在共用這把 Key 的 $G$ 個專家裡，只要**任何一個**專家認為這把 Key 在未來極度重要，系統就會把它留下來。這種「一票保存」的邏輯，避免了取平均時犧牲掉少數特定專家（例如專門負責遠距離檢索的 Head）發現的關鍵線索。

---

## 七、實驗驗證：數據怎麼說

前面幾章推導了一整套理論，接下來看這套方法在真實模型上究竟表現如何。論文用四個場景檢驗 TriAttention：極限長推理、記憶體回溯能力、跨領域穩定性，以及通用長文本任務。

### 7.1 AIME 數學基準：長推理鏈結的極限測試

數學競賽題是檢驗長鏈式推理最好的試金石——模型通常得生成上萬個 token 才能得出答案。論文在 Qwen3-8B 上，把生成長度設到 32K token 進行測試。

在同樣 40.8% 的 AIME25 準確率下（也就是前面圖 1 展示的那個平衡點），TriAttention 用比 Full Attention 少 10.7 倍的 KV 記憶體達成了同樣的成績。更值得注意的是跟同類壓縮方法的直接對比：在另一個更嚴苛的固定記憶體預算下，依賴動態觀測的 R-KV 演算法準確率暴跌到 17.5%，TriAttention 卻還能撐住 32.9%——差距接近一倍。

| 方法 | AIME24（Qwen3-8B） | AIME25（Qwen3-8B） |
|---|---|---|
| Full Attention | 57.1 | 40.8 |
| SnapKV | 34.6 | 20.0 |
| R-KV | 25.4 | 17.5 |
| **TriAttention** | **42.1** | **32.9** |

![AIME24 和 AIME25 上四種模型的準確率對照表，TriAttention 在絕大多數欄位都優於 SnapKV 與 R-KV，且最接近 Full Attention 的表現。](img-005)
*表 2 — AIME24／AIME25 準確率對照（粗體為最佳，底線為次佳）。*

![MATH 500 資料集上，KV 預算為 512 時四種模型的準確率對照，TriAttention 在四個模型上都取得最高或接近最高的分數。](img-006)
*表 3 — MATH 500 準確率對照（KV 預算 512）。*

這種差距背後的原因，正是第三、四章討論過的「冬眠 Key」問題：長推理過程中，最初設立的方程式或條件變數常常會在中間幾千步運算中進入冬眠狀態（暫時不被關注，但最終結果需要靠它）。R-KV 這類動態觀測方法看不到它未來會被用到，直接刪掉；TriAttention 的預測機制則因為「預見」了它在遙遠未來的共振波峰，成功把這些冬眠 token 保護下來。

![三個數學推理基準（MATH500、AIME24、AIME25）上，準確率隨 KV 快取預算變化的折線圖，TriAttention 在各個預算下都優於 R-KV，並附帶記憶體保留基準隨遞迴深度變化的曲線圖。](img-007)
*圖 6 — (A–C) 三個數學推理基準上，準確率 vs. KV 快取預算；(D) 記憶體保留基準隨 DFS 遞迴深度變化的準確率曲線。*

上圖 (A–C) 顯示，不管把 KV 預算調到多低，TriAttention 都穩定壓過 R-KV，差距在預算越吃緊時越明顯。至於 (D) 這條曲線，講的是另一個更嚴苛的測試，下一節細看。

### 7.2 DFS 遞迴記憶體測試：回溯能力的終極考驗

這是論文設計得最巧妙、也最能直指「記憶體保留」核心的實驗：作者構造了一個遞迴狀態查詢（Recursive State Query）基準測試，要求模型執行深度優先搜尋（DFS）式的圖形走訪。

**為什麼 DFS 是最殘酷的試金石？** DFS 演算法本質上依賴堆疊與回溯：當模型在第 20 層遞迴走到死路時，必須精準地從記憶體裡取出第 2 層遞迴留下的分支點狀態，才能正確回溯。任何一個中間節點的狀態遺失，都會引發級聯錯誤，讓最終結果整個崩潰。

![左圖展示完整記憶下所有中間狀態都被保留、正確值層層傳遞的成功案例；右圖展示某個中間狀態遺失後，錯誤如何逐層傳遞、最終導致結果出錯的失敗案例。](img-011)
*圖 7 — 用遞迴模擬評估記憶保留能力：左邊是完整記憶下正確值逐層傳遞的情況，右邊是某個中間狀態遺失後錯誤逐層擴散、拖垮最終結果的情況。*

這張圖把問題具體化了：假設遞迴到第 3 層時某個狀態被誤刪（圖右），這個錯誤不會只影響當下，而是會隨著回溯逐層往上傳染，最終讓整條推理鏈的結果都不可信。

實驗結果也印證了這個風險確實會發生。遞迴深度在 16 以內時，TriAttention 的準確率曲線幾乎完全貼合 Full Attention，甚至在深度 8、12 時還微幅領先（這暗示 Full Attention 本身可能夾雜了一些干擾推理的冗餘噪聲，反而被 TriAttention 的評分機制濾掉了）。但 R-KV 在深度到達 16 時發生了災難性的性能坍塌：準確率從深度 14 的 61% 直接墜落到 31%（見前面圖 6 的 (D) 曲線）。

TriAttention 能撐住這個測試，靠的正是雙軌評分裡 $S_{norm}$ 與 $S_{trig}$ 的長距離預測能力——即使一個關鍵的回溯錨點暫時沒被查詢，只要它未來某個時間點會被用到，$\tilde{S}(k)$ 的長距離平均就能把它保護下來，不會像 R-KV 那樣因為短期沒被關注就永久刪除。

### 7.3 跨領域校準：離線統計出來的中心點，會不會過擬合？

工程部署最讓人擔心的問題是：離線校準算出來的 Q/K 中心點，會不會跟校準當時用的資料綁得太緊，換一批資料就失靈？

論文做了兩組實驗回答這個問題：

- **跨領域校準**：用程式碼（Coding）資料校準，拿去測數學推理（AIME24）任務。結果程式碼校準出來的準確率（44.2%）跟直接用數學資料校準（42.1%）幾乎打平，甚至還略高一點。
- **極端品質測試**：用品質很低的 Google 首頁 HTML 原始碼做校準，最終準確率（46.2%）跟用高品質的 ShareGPT 對話資料校準（46.7%）幾乎沒有統計上的顯著差異。

![三個面板的消融實驗表：(A) 拿掉三角級數分數對準確率的影響、(B) 拿掉集中度加權對準確率的影響、(C) 跨領域校準（用程式碼資料校準後測數學推理）與同領域校準的準確率對比。](img-008)
*表 4 — 消融實驗：(A) 三角級數分數的效果、(B) 集中度加權的效果、(C) 跨領域校準的效果。*

![校準資料的敏感度測試表：上半部比較不同資料量（5萬、20萬、96萬 token）下的準確率，下半部比較不同品質資料（低品質 HTML、中品質程式碼、高品質對話）下的準確率，各組之間差異都很小。](img-017)
*表 5 — 校準資料的量與品質敏感度測試，準確率在不同設定間幾乎沒有明顯波動。*

這組數據其實給出了整篇論文裡最有工程價值的結論：**Attention Head 的幾何距離偏好，是硬編碼在模型投影矩陣裡的固有物理屬性，不會因為校準資料換了就跟著漂移。** 它就像相機鏡頭的焦距，一旦模型訓練完成就固定下來，不會因為你拍的對象不同而改變。這代表工業界部署時，工程師幾乎可以做到「零負擔」校準——不需要為每個不同的使用情境準備特化的校準資料集，隨便一批資料校準出來的中心點，效果都差不多。

### 7.4 通用長文本基準：不只是數學題會用到

為了證明這套方法不是只對數學推理有效，論文也在通用長文本理解任務上做了驗證。

在涵蓋問答、摘要、少樣本分類、檢索、計數與程式碼共 16 個子任務的 LongBench 基準上，TriAttention 拿到最高平均分（48.1），贏過 SnapKV 等傳統觀測方法。

![LongBench 16 個子任務的完整結果表，涵蓋問答、摘要、少樣本、檢索、計數、程式碼六大類，TriAttention 在多數子任務上表現最佳或接近最佳。](img-013)
*表 6 — LongBench 完整結果（Qwen3-8B，50% KV 預算），涵蓋 QA、摘要、少樣本分類、檢索、計數、程式碼六大類任務。*

在專門測試「大海撈針」式檢索能力的 RULER（4K 上下文）測試中，TriAttention 平均得分 66.1，對比 SnapKV 的 55.6，優勢相當明顯。

![RULER 檢索基準測試結果表，比較 SnapKV、PyramidKV、StreamingLLM 與 TriAttention 四種方法的平均分數，TriAttention 以 66.1 分大幅領先。](img-014)
*表 7 — RULER 檢索結果對照（Qwen3-8B，50% KV，4K 上下文）。*

論文還額外跟 H2O 這個需要 $O(n^2)$ 記憶體、沒辦法用 FlashAttention 加速的方法比較。在 H2O 能塞進 48GB GPU 記憶體的 12 個 LongBench 子任務上，TriAttention 贏了其中 10 個。

![H2O 與 TriAttention 在 H2O 能塞進 48GB GPU 記憶體的 12 個 LongBench 子任務上的準確率對照表，TriAttention 在絕大多數子任務上都取得更高分數。](img-015)
*表 8 — 與 H2O 的對照（Qwen3-8B，50% KV 預算，僅列 H2O 記憶體可容納的子任務）。*

這幾組數據合起來說明一件事：Pre-RoPE 幾何先驗預測不是數學競賽題的特例解法，而是在處理各種長距離依賴（不管是精準檢索單一資訊，還是整合全局脈絡做摘要）時，都比 Post-RoPE 的被動觀測更準、更穩定。

---

## 八、範式轉移：從被動觀測到主動預測

看完理論推導與實驗數據，可以退一步用更宏觀的視角，重新理解這項技術帶來的系統設計啟發。TriAttention 的出現，不只是一次演算法的迭代，更代表 KV Cache 壓縮領域從「動態觀測」走向「先驗預測」的一次範式轉移。

### 8.1 兩種設計哲學的對決

| | 傳統觀測派（經驗主義） | TriAttention 預測派（理性主義） |
|---|---|---|
| 運作邏輯 | 即時民意調查：邊解碼邊統計「當前 Query 投給了哪些歷史 Key 最高分」 | 第一性原理：Key 寫入快取的那一刻，就用真實特徵向量與離線算好的 Q 中心點，數學上「預畫」出它未來的命運曲線 |
| 系統硬傷 | 極度依賴短期觀察窗口，RoPE 旋轉造成分數動態震盪，過去的高分不保證未來、低分也未必代表無用 | 解除了對即時動態的依賴，能一次掌握每把 Key 在未來 6.5 萬步內的潛在價值 |
| 典型失敗場景 | 冬眠 Key 被短視地永久淘汰，長推理鏈中途斷裂 | 幾乎不受影響，長距離平均能捕捉到未來的共振 |

### 8.2 同樣是餘弦函數，為什麼 TriAttention 不會重蹈覆轍？

這是個很刁鑽但很切中核心的問題：注意力運算底層都建立在 $\cos$ 函數上，為什麼傳統方法會被波谷坑殺，TriAttention 卻不會？

答案在於觀測視角與頻率處理方式的差異。第一，傳統方法只看當下這一個時間點的分數——餘弦曲線上的一個孤立點，如果剛好落在波谷就被判定無用；TriAttention 則透過幾何等比採樣，對未來 17 個關鍵距離做平均，等於對未來的整條波形做了一次數值積分，即使當下處於低谷，未來的波峰共振也會在積分過程中被捕捉、拉高整體平均分。第二，傳統方法在 Post-RoPE 空間拿到的是 64 個頻率混在一起、又經過 Softmax 壓縮的單一黑盒數值，沒辦法分辨噪聲跟真訊號；TriAttention 在 Pre-RoPE 空間把 64 個頻率分開計算，讓不同頻率的波形能夠產生真正的物理干涉，合成出一條有明確指向性、不再無盡震盪的「波包」曲線。

### 8.3 動靜分離：一個值得抄的工程模式

從演算法工程師的角度看，TriAttention 處理 $S_{trig}$ 與 $S_{norm}$ 這兩條分數時的「動靜分離」設計，是很值得記下來的架構思路，甚至可以脫離這篇論文本身，套用到其他系統上。

$S_{norm}$（語意模長分）是 Key 的本質屬性：在 Key 寫入快取的那一刻，它的值就固定了，可以只算一次就快取起來，之後完全不佔算力。$S_{trig}$（距離共振分）則是 Key 的時效性屬性：隨著新 token 不斷生成，Key 跟最新 Query 的相對距離會變遠，導致 $\cos$ 項的相位偏轉，這部分必須重新計算。透過把不變的常數項抽離出來，再搭配批次處理（每生成 128 步才觸發一次重算），TriAttention 把原本極度複雜的高維注意力矩陣運算，降維成只需要更新一個純量距離 $\Delta$ 的輕量運算——這種「找出真正需要重算的最小子集」的思路，在任何需要頻繁增量更新的系統裡都用得上。

---

## 結論

《TriAttention: Efficient Long Reasoning with Trigonometric KV Compression》這篇論文，針對大語言模型在長文本、長推理鏈場景下的 KV Cache 記憶體瓶頸，提出了一套兼具數學美感與工程實用性的解法，核心脈絡可以濃縮成四點：

1. **找出旋轉盲區**：傳統壓縮方法在 Post-RoPE 空間裡做觀察，會被 RoPE 旋轉造成的週期性震盪誤導，把還有用的冬眠 Key 提前殺掉，切斷長推理鏈。
2. **發現幾何集中**：透過方向統計學指標 $R$，證明了 Pre-RoPE 空間中 Q/K 向量高度集中在固定中心點附近，而且這是模型訓練完就固定下來的物理屬性，跟輸入內容無關。
3. **推導三角級數預測**：把隨機變數換成常數中心點，推導出只跟相對距離相關的三角級數評分 $S_{trig}$，再搭配語意模長分數 $S_{norm}$ 與集中度加權 $(1-R_f)$，組成一套不需要人工調超參數的雙軌評分系統。
4. **落地成可執行的工程系統**：靠幾何等比採樣把未來預測的運算量從 $O(N)$ 壓到 17 次、用窗口化批次裁剪降低頻繁重算的開銷、再用 Z-Score 標準化加最大池化解決 GQA 架構下的多對一評分衝突。

實驗數據也證實了這套設計確實有用：在跟 Full Attention 打平準確率的前提下，吞吐量提升 2.5 倍、KV 記憶體縮減 10.7 倍；在 DFS 回溯這種最考驗記憶保留能力的極端測試裡，R-KV 這類傳統方法會在深度 16 直接崩盤，TriAttention 卻能跟 Full Attention 保持同步；就連校準資料的品質與領域大幅變動，準確率也幾乎不受影響。

比起這篇論文的跑分本身，更值得所有做系統優化的工程師記住的，或許是它背後的思維方式：面對一個看似只能靠「拉長觀察窗口」這種修補手段解決的問題，TriAttention 選擇退回去問「這個系統的數學與物理本質到底是什麼」，找到 Q/K 集中這個被長期忽略的幾何規律，再依此重新設計整套預測模型。這種回到第一性原理、從系統本質出發的設計思路，比任何單一演算法的分數提升，都更值得帶到下一個要解決的問題上。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1. Performance trade-offs on AIME25 (Qwen3-8B). (A) At",
    "why_used": "在前言之後、正式進入技術細節之前，先用這張圖具體展示 TriAttention 最終達成的效能與記憶體權衡，讓讀者知道後面一大段推導最終換來了什麼。",
    "agent_match_hint": "兩張並排的散佈圖，左圖 X 軸是吞吐量、右圖 X 軸是 KV 記憶體佔比，Y 軸都是準確率，圖上標有 2.5X Faster 與 10.7X Smaller 的紅色箭頭標註。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2. Q/K concentration and its implications for attention. (A) Pre-RoPE Q/K vectors at the dominant frequency band are highly",
    "why_used": "放在第三章結尾、第四章開頭之間，同時呈現傳統方法觀察到的 Post-RoPE 混亂散佈（面板 B）與 TriAttention 依據的 Pre-RoPE 集中現象（面板 A），讓讀者一眼看到問題與解法的對比。",
    "agent_match_hint": "四個並排的子圖，左邊兩張是 2D 散佈圖（一張高度集中、一張弧形散落），右邊兩張分別是集中度分佈直方圖與注意力重建相關性折線圖。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 3. Attention reconstruction correlation across three DeepSeek-R1 distilled LLMs, including Qwen3 (Qwen Team, 2025),",
    "why_used": "支撐「集中現象在不同模型架構下都成立」這個論點，緊接在介紹完 R 指標與集中現象普遍性之後出現。",
    "agent_match_hint": "三個並排的直方圖，各自標題是不同模型名稱，X 軸是注意力重建 Pearson 相關係數。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Figure 4. Method overview. From left to right: offline calibration computes Q distribution centers; then during inference, original attention",
    "why_used": "作為第五章（核心理論）的開場圖，讓讀者在看一連串公式推導之前，先建立整套方法從離線校準到雙軌評分的完整資料流輪廓。",
    "agent_match_hint": "一張由左至右排列的流程示意圖，包含向量分佈圖、公式方塊與矩陣熱力圖，箭頭連接各個處理階段。"
  },
  {
    "id": "img-012",
    "references_manifest_caption": "Figure B. Method visualization with real attention maps, corresponding to the schematic in Figure 4. Top row: The four stages of TriAttention. (1) We compute the Q/K centers E[q], E[k] from pre-RoPE distributions. (2) Using the trigonometric series, we compute Strig which scores keys based on distance preference. (3) We add the norm-based score Snorm, weighted by concentration, to obtain the final score ¯S(k). (4) We retain top-scoring keys and evict the rest. Bottom row: Real attention maps illustrating the scenario described in Figure 4. From left to right: original attention pattern showing distance preference; Strig visualization capturing the diagonal structure; combined score ¯S incorporating norm information; attention after KV cache pruning, preserving the essential pattern.",
    "why_used": "放在第五章末尾，用真實的注意力熱力圖具體驗證前面推導的雙軌評分公式，讓抽象的 S_trig、S_norm 公式有一個看得到的對照結果。",
    "agent_match_hint": "上下兩排的示意圖／熱力圖，上排是四個流程步驟的圖示，下排是四張顏色深淺不一的注意力矩陣熱力圖。"
  },
  {
    "id": "img-016",
    "references_manifest_caption": "Table E. Future offset ablation on Qwen3-8B (AIME24). Top: effect of offset range. Bottom: spacing strategy comparison (17 offsets,",
    "why_used": "放在第六章討論幾何等比採樣設計之後，用消融實驗數據證明「拉長評估距離」與「改用幾何間隔」這兩個工程決策都確實提升了準確率。",
    "agent_match_hint": "一張分成上下兩部分的表格，上半部有 Max Dist、#Offsets、Acc 三欄，下半部比較 Linear spacing 與 Geometric spacing 兩列。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Table 1. Reasoning performance on AIME24 and AIME25. Best results are in bold, second best are underlined. All methods are compared",
    "why_used": "放在第七章第一節，具體列出 Full Attention、SnapKV、R-KV、TriAttention 在 AIME24／25 上針對四種模型的準確率，支撐文中提到的具體數字對比。",
    "agent_match_hint": "一張表格，欄位是四種模型（Qwen3-8B、DS-Llama、DS-Qwen、GPT-OSS）分別在 AIME24 與 AIME25 下的分數，列是四種方法。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 2. Reasoning performance on MATH 500 with KV budget",
    "why_used": "緊接在 Table 1 之後，補上 MATH 500 資料集的準確率對照，讓讀者看到 TriAttention 的優勢不只限於 AIME 這一個基準。",
    "agent_match_hint": "一張表格，欄位是四種模型在 MATH 500 上的分數，列是 Full Attention、SnapKV、R-KV、TriAttention 四種方法。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Figure 5. Performance comparison on Qwen3-8B. (A–C) Accuracy vs. KV cache budget on three mathematical reasoning benchmarks. TriAttention consistently outperforms R-KV across all budget levels. (D) Memory retention on Recursive State Query benchmark. Depth refers to DFS recursion depth; deeper recursion requires retaining more intermediate states, increasing memory pressure.",
    "why_used": "放在第七章第一節末尾，用三條準確率對 KV 預算的折線圖，把前面提到的「預算越吃緊優勢越明顯」具體畫出來，並預告第 (D) 子圖會在下一節的 DFS 測試中細講。",
    "agent_match_hint": "四張並排的折線圖，前三張 X 軸是 KV 快取預算、Y 軸是準確率，標題分別是三個數學基準名稱；第四張 X 軸是遞迴深度。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Figure A. Evaluating memory via recursive simulation. Left: With complete memory, all intermediate states are retained and correct values propagate upward. Right: When an intermediate state is lost (State2), the error propagates through all subsequent return values, corrupting the final result.",
    "why_used": "放在第七章第二節說明 DFS 回溯測試原理時，用具體的成功／失敗案例圖示，讓讀者理解「中間狀態遺失」為什麼會拖垮整條推理鏈的結果。",
    "agent_match_hint": "左右並排兩組遞迴呼叫的樹狀示意圖，左邊每一層都是綠色勾選的正確結果，右邊某一層標紅色叉號並向上擴散錯誤。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Table 3. Ablation studies on Qwen3-8B with KV budget of 2048. (A) Effect of removing trigonometric series score Strig. (B) Effect of",
    "why_used": "放在第七章第三節，用三個並排的消融實驗子表，具體支撐「拿掉三角級數分數」「拿掉集中度加權」「跨領域校準」這三項分析各自的數字依據。",
    "agent_match_hint": "一張橫向排列三個子表格的圖，每個子表都有 Method、AIME24、AIME25 三欄。"
  },
  {
    "id": "img-017",
    "references_manifest_caption": "Table F. Calibration data sensitivity on Qwen3-8B (AIME24). Top: effect of calibration data size. Bottom: effect of calibration data",
    "why_used": "緊接在跨領域校準的討論之後，補上校準資料量與品質的敏感度測試數據，佐證「幾乎零負擔校準」這個結論。",
    "agent_match_hint": "一張分成上下兩部分的表格，上半部列出不同 token 數量下的準確率，下半部列出不同品質資料來源下的準確率。"
  },
  {
    "id": "img-013",
    "references_manifest_caption": "Table B. LongBench results (Qwen3-8B, 50% KV budget). 16 subtasks spanning QA, summarization, few-shot classification, retrieval,",
    "why_used": "放在第七章第四節，作為通用長文本任務驗證的第一份完整數據，支撐「TriAttention 不只在數學題有效」的論點。",
    "agent_match_hint": "一張很寬的表格，橫跨問答、摘要、少樣本、檢索、計數、程式碼六個分類，共 16 個子任務欄位，最後一欄是平均分。"
  },
  {
    "id": "img-014",
    "references_manifest_caption": "Table C. RULER retrieval results (Qwen3-8B, 50% KV, 4K context). Bold = best among compression methods.",
    "why_used": "緊接在 LongBench 結果之後，補上專門測試檢索能力的 RULER 分數，讓「通用長文本任務」的驗證更完整。",
    "agent_match_hint": "一張簡單的兩欄表格，Method 與 RULER Avg，列出四種方法的平均分數。"
  },
  {
    "id": "img-015",
    "references_manifest_caption": "Table D. Comparison with H2O on LongBench subtasks where H2O fits in 48GB GPU memory (Qwen3-8B, 50% KV). H2O requires",
    "why_used": "放在第七章第四節末尾，補上與 O(n^2) 記憶體方法 H2O 的直接對照，完整涵蓋論文在通用長文本任務上比較過的所有基準方法。",
    "agent_match_hint": "一張表格，欄位是 LongBench 的 12 個子任務名稱，列是 H2O 與 TriAttention 兩種方法的準確率。"
  }
]
```
