# Procedural Graphs：讓 LLM Agent 的執行流程自我演化——論文筆記

Oct 15, 2026 · @YHHW

## 三十秒版本

這篇論文把 agent 的「做事流程」存成一張可編輯的有向圖，推論時只取目前所在位置附近的一小段轉成提示，並讓另一個 LLM 離線自動修改這張圖。論文：*Procedural Graphs: Self-Evolving Execution Structures for LLM Agents*（arXiv 2609.09153v1，Google，2026-09）。

- **做法：** 節點是工具或步驟，邊是「這步之後可以接哪一步」，每條邊附三段文字：condition（何時走這條邊）、guidance（怎麼做）、pitfalls（要避開什麼）。推論時，先找出 agent 剛做完圖上哪個節點，取往後 2 跳的子圖，由另一個 LLM（Ψ）翻成當下的提示，附加到 solver 的 prompt。
- **圖怎麼來：** 離線演化。refiner 讀成功與失敗的軌跡，提出對圖的修改；候選圖在獨立驗證集上不比舊圖差才採用，被拒的記下來，下一輪給 refiner 看。
- **結果：** 增益真實但不均勻。同一個模型、同一個 solver，對比無記憶 ReAct，24 格中有 23 格為正。HotpotQA 幾乎沒有增益（最大 +1.7）；其餘五個 benchmark 多在 +3.5 到 +22.4 之間。
- **壞的先驗會傷人：** 手寫專家圖在 MultiChallenge 上比無圖少答對 16 題（共 56 題），演化後回到比無圖多 3 題。
- **成本：** 每一步多一次 LLM 呼叫，token 約為無圖的 1.33 到 1.85 倍（Table 3，Gemini 3.5 Flash）。
- **最耐久的是改進迴圈，不是圖：** 提案、用獨立驗證集把關、被拒的記錄回灌給提案者。這個迴圈可以套在任何可編輯的文字資產上。

## 索引

主線依序是：問題、方法（三段）、實驗（三個）、值得帶走的東西。文末有六個獨立的【概念】段，每一段脫離主線也讀得懂，是最容易再忘、也最值得回頭翻的地方：

1. 【概念】定位與子圖：上一步動作怎麼對到圖上的節點，2 跳子圖怎麼取
2. 【概念】Ψ 與 solver 的輸入輸出對照：兩個 LLM 各看到什麼、各產出什麼
3. 【概念】一個 benchmark 一張圖：refiner 不選圖也不新增圖，異質任務共存的問題
4. 【概念】refiner 的輸入、訓練軌跡與 H\_rejected：每一輪到底餵了什麼、記了什麼
5. 【概念】七個 baseline：各自存什麼、推論時怎麼用
6. 【概念】分批演化與一次大改的差別

## 問題

ReAct 式 agent 每一步都要從一份越來越長的「動作＋觀察」流水帳，自己推出下一步，所以長任務裡容易忘記目標、亂序呼叫工具、重複無效動作。ReAct 是 agent 的常見迴圈：想一步、呼叫一個工具、看結果、再想。現有補救各缺一塊：文字記憶與反思（Reflexion、ExpeL）是自由文字，solver 還得自己判斷它如何限制後面的步驟；條件式指引（AutoGuide）彼此沒連起來；手寫工作流與狀態機要人工設計；自動搜尋工作流（AFlow）只在離線優化結構。論文要同時做到四件事：結構夠強以擋掉無效行為、保留推理彈性、隨目前進度調整、能從經驗改進。

核心類比請直接看 **Figure 1**。原 caption：「From knowledge to procedure. A Knowledge Graph organizes facts into triplets that answer what-is questions. A Procedural Graph organizes task procedures into triplets that answer what-to-do questions.」

## 方法一：圖的長相

PG 是一張有向、帶屬性的圖：節點是步驟，邊是「這步之後可以接哪一步」，每條邊再附三段文字說明怎麼接（論文 Section 3.1）。

```latex
G = (V,\, R,\, E,\, \Phi), \qquad E \subseteq V \times R \times V
```

- V：節點集合。每個節點代表一個工具函式、一個技能、一個內部推理步驟，或一個任務狀態。
- R：關係種類的詞彙表。實際只有四種：LEADS\_TO、TRIGGERS、PROVIDES\_INPUT\_FOR、CONVERGES\_TO（Appendix B.4）。
- E：邊的集合。每條邊是 (u, r, v)，意思是「在 u 之後，可以依關係 r 接 v」。
- Φ：把每條邊對應到一組文字欄位。論文用三個：condition（什麼時候該走這條邊）、guidance（怎麼做）、pitfalls（要避開什麼）。

**論文自己的例子（Section 3.1）：** 邊是 (cash\_flow\_forecast, LEADS\_TO, fund\_raising\_request)，也就是「做完現金流預測之後，可以接提出募資申請」。

| 欄位 | 內容 |
| --- | --- |
| condition | 預估的資金跑道低於安全緩衝時 |
| guidance | 要提早送出申請，因為資金到位有延遲 |
| pitfalls | 已有一筆申請還在等待時，不要再疊一筆 |

這三句話，就是推論時 Ψ 要翻譯給 solver 的原料。

**規模：** 實際用的圖很小。除了 BFCL v3 因為對應龐大的函式目錄而有 131 個節點、265 條邊，其餘每張圖都是 7 到 17 個節點、7 到 27 條邊。請直接看 **Table 7**，原 caption：「Sizes of the Procedural Graphs used in the main experiments.」

圖可以從專家手寫的版本起步，也可以從只有 Start → End 兩個節點的空圖起步，兩種起點的比較在實驗三。

## 方法二：線上推論（定位、取子圖、生成提示、選動作）

每一步決策前，先判斷 agent 剛做完圖上哪個節點，只取那個節點往後 2 跳的小圖，由另一個 LLM 轉成一小段「現在該做什麼、要避開什麼」的文字，附加到 solver 的 prompt。推論時圖是凍結的，不會更新（Section 3.2）。

兩個角色先定義清楚：**solver** 是實際選下一步動作的 LLM，也就是 ReAct 迴圈裡的 agent 本人；**Ψ（guidance model）** 是另一個 LLM，負責把子圖翻成提示，論文說它和 solver 用同一個底層模型（Section 4）。

**一步的流程：**

&#91;1\] 上一步動作 a\_{t-1} -> \[2\] 比對到圖上的節點 u\_t，取 2 跳子圖 G\_t -> \[3\] Ψ 讀 G\_t、問題 q、最近 3 步軌跡，寫出提示 g\_t -> \[4\] g\_t 填進 solver prompt 的 `Procedural Graph Guidance:` 欄位 -> \[5\] solver 輸出 Thought 與 Action -> \[6\] 環境執行並回傳觀察 -> \[7\] 接進軌跡，進入下一步

**第一部分：定位與取子圖（Eq. 2 前半）**

```latex
u_t = \mathrm{Match}(a_{t-1},\, V), \qquad G_t = \begin{cases} N_h(u_t), & u_t \neq \emptyset \\ G, & \text{otherwise} \end{cases}
```

- t：目前是第幾個決策步。起點約定 a\_0 = Start，所以第一步一定定位在 Start 節點。
- a\_{t-1}：agent 上一步的動作，例如一次工具呼叫。
- Match：把 a\_{t-1} 和節點集合 V 比對，論文寫的是「exactly matching」。
- u\_t：比對到的節點，也就是 agent 現在在圖上的位置；比對不到就是空集合。
- N\_h(u\_t)：從 u\_t 出發，沿著往外的邊最多展開 h 步所得的子圖。實驗用 h = 2。
- G\_t：這一步交給 Ψ 的圖。比對失敗時退回整張圖 G。

**論文自己的例子（Appendix B.5，HotpotQA 的 Serialized Local Graph Context，節錄）：** 上一步動作是 first\_hop\_retrieve，定位到 First\_Hop\_Retrieve；第 1 跳是 First\_Hop\_Retrieve → Scan\_Index，第 2 跳是 Scan\_Index → Bridge\_Extract；兩條邊連同各自的 condition、guidance、pitfalls 一起交給 Ψ。細節與比對機制見文末【概念】定位與子圖。

**第二部分：生成提示並選動作（Eq. 2 後半與 Eq. 3）**

```latex
g_t = \Psi\big(G_t,\, q,\, T_{t-w:t}\big), \qquad a_t \sim P_{\text{solver}}\big(\cdot \mid q,\, T_t,\, g_t\big)
```

- g\_t：第 t 步的情境化提示，一段自然語言。
- Ψ：guidance model。
- q：使用者的原始問題。
- T\_{t-w:t}：最近 w 步的軌跡，實驗用 w = 3。
- T\_t：到目前為止完整的軌跡，是動作與觀察交錯的序列。
- a\_t：solver 這一步要做的動作。實驗全部用 greedy decoding（每次取機率最高者），所以實際上是確定的。

Ψ 的指令（Appendix B.5 的 Guidance Generation Prompt）要求它依邊上的 condition、guidance、pitfalls，說清楚下一步做什麼、要避開什麼、最近失敗後怎麼補救，並帶上圖裡寫到的具體指令格式、工具與參數。兩個 LLM 各自看到什麼、輸出什麼，整理在文末【概念】Ψ 與 solver 的輸入輸出對照。

**三個要記得的性質：**

- **只是偏向，不是強制。** 論文摘要說提示 biases the solver's next action without dictating it。論文沒有任何機制檢查 solver 的動作是否真的走在圖上。
- **每一步多一次 LLM 呼叫（Ψ 本身），成本一定比不用圖高。** 數字見實驗二。
- **比對失敗退回整張圖的代價高。** 實驗二顯示整張圖加生成式提示是最差的設定，但論文沒給比對失敗的頻率（論文未說明），所以不知道這條路徑實際被走到多少次。另外，Appendix B.5 說 serializer 不會把關係標籤印給 Ψ，所以至少在這個序列化下，四種關係種類在推論時不起作用，Ψ 只看到節點、箭頭方向和三段文字。

圖的整體流程請直接看 **Figure 2**，重點是 Middle 那一欄。原 caption：「Overview of the Procedural Graph framework. Left: procedural triplets define G. Middle: the framework localizes u\_t and retrieves its 2-hop neighborhood G\_t (or the full graph if matching fails); a guidance LLM translates it into guidance g\_t for the solver. Right: the refiner proposes edits from execution trajectories. Structurally valid candidates are committed when validation performance does not decrease; rejected candidates inform subsequent proposals through rejection memory.」

## 方法三：離線自我演化（refiner、驗證閘門、拒絕記憶）

先讓 solver 在訓練題上跑一批，留下成功與失敗的軌跡；refiner（專門改圖的 LLM，與 solver 同一個底層模型）讀軌跡，輸出一份修改清單，套用到圖的副本得到候選圖；候選圖在獨立驗證集上不比目前的圖差才採用，被拒的記下來，下一輪給 refiner 看（Section 3.3、Algorithm 1）。

**一輪（第 k 輪）的流程：**

&#91;1\] 用目前保留的圖 G\_{k-1}，在一批訓練題上跑 solver，記錄軌跡與分數（0 到 1）-> \[2\] refiner 比對高分與低分軌跡：在失敗軌跡找反覆出現的錯誤迴圈，在成功軌跡找可借用的捷徑 -> \[3\] refiner 輸出修改清單 ΔG\_k -> \[4\] 套用到圖的副本，得到候選圖 -> \[5\] 結構檢查，沒過就丟，不跑驗證 -> \[6\] 在驗證集上算分，與舊圖比 -> \[7\] 不比舊圖差就採用；否則退回舊圖，並把這次的候選記進拒絕記憶

### 提出修改：refiner 輸出什麼

```latex
G_k^{cand} = G_{k-1} \oplus \Delta G_k
```

- G\_{k-1}：上一輪保留下來的圖。被拒絕的候選不會成為下一輪的起點。
- ΔG\_k：refiner 提出的修改清單。
- ⊕：把修改套用到圖的副本；若設定要求，還會自動修掉環。
- G\_k^{cand}：候選圖。

修改只有兩種：**Add**（補節點或邊，例如補驗證步驟）與 **Delete**（刪掉老是把軌跡帶進失敗的節點或邊）。改邊的屬性，就是刪掉再用新屬性加回去。refiner 的實際輸出是一個 JSON，四個陣列：`add_nodes`、`delete_nodes`、`add_edges`、`delete_edges`（Appendix B.5 的 Refiner Prompt）。套用時先刪後加；`delete_edges` 會刪掉該起點到終點之間的所有邊，不分關係種類，想留其中幾條要在 `add_edges` 重加。

**論文實例（Appendix E.3）：** Round 1 從只有 Start → End 的空圖，一次長出整條主線；Round 7 刪掉 `pass_action`（什麼都不做）節點及其邊；Round 8 把 fund\_raising\_request → book\_closing 換成直接連到 End。拓樸演化請直接看 **Figure 5**，原 caption：「Topological evolution of the CFO Procedural Graph. Green nodes/edges \[+\] denote additions; red dashed nodes/edges \[-\] denote deletions/pruning.」

**結構檢查（Appendix B.6）：** 邊的端點必須存在、節點與關係型別合法、每個節點都有路徑走得到終點（出度為 0 的節點）。沒通過的候選直接丟掉。注意：refiner prompt 要求 ACTION 節點必須是真實工具名，但驗證器不檢查這點，只靠 prompt 約束；refiner 若編出不存在的工具節點，結構檢查擋不住，只能靠下一步的驗證分數擋。

### 驗證閘門：決定改圖會不會越改越糟

```latex
S_{val}(G) = \frac{1}{|D_{val}|} \sum_{(q,y) \in D_{val}} S\big(f_{solver}(q \mid G),\, y\big)
```

```latex
G_k = \begin{cases} G_k^{cand}, & S_{val}(G_k^{cand}) \ge S_{val}(G_{k-1}) \\ G_{k-1}, & \text{otherwise} \end{cases}
```

- D\_val：驗證集，和訓練批、測試集都分開。
- (q, y)：一題問題和它的標準答案。
- f\_solver(q | G)：用圖 G 時 solver 的輸出。S：單題分數。S\_val(G) 就是驗證集上的平均分。
- 是 ≥：持平也收（Algorithm 1 第 17 行）。舊圖的分數是快取的，不重跑。
- 為什麼要獨立的驗證集：refiner 是看過訓練軌跡才提出修改的，在訓練批上有效不代表真的有效。

**十輪的走法（Appendix E 的 Table 11，EnterpriseArena 上的自我演化，Gemini 3.5 Flash）。** 規則：新圖的驗證存活率不低於目前保留圖的存活率就收，否則丟。分母：驗證集 20 個 episode，1 個 episode = 5 個百分點。存活率指撐滿 132 個月沒破產的比例。

| 輪次 | 新圖存活率 | 要比的對象（目前保留圖） | 結果 | 這輪之後保留的圖 |
| --- | --- | --- | --- | --- |
| R1 | 45.0% (9/20) | 0.0%（起始空圖） | 收 | R1 |
| R2 | 80.0% (16/20) | 45.0% | 收 | R2 |
| R3 | 65.0% (13/20) | 80.0% | 丟 | R2 |
| R4 | 75.0% (15/20) | 80.0% | 丟 | R2 |
| R5 | 結構檢查沒過，沒跑驗證 | 80.0% | 丟 | R2 |
| R6 | 65.0% (13/20) | 80.0% | 丟 | R2 |
| R7 | 80.0% (16/20) | 80.0% | 持平，收 | R7 |
| R8 | 90.0% (18/20) | 80.0% | 收 | R8 |
| R9 | 90.0% (18/20) | 90.0% | 持平，收 | R9 |
| R10 | 85.0% (17/20) | 90.0% | 丟 | R9 |

最右欄是重點：保留的圖只會往前走，不會倒退。R3 到 R6 全被丟，所以那四輪結束時手上的圖都還是 R2。R10 的訓練存活率是 90.0%，驗證只有 85.0%，被擋下的就是只在訓練批上有效的改動（Appendix E.2）。請直接看 **Table 11**，原 caption：「PG self-evolution across ten rounds with Gemini 3.5 Flash. The Δ rows report metric changes relative to the previous best validation checkpoint. Gray rows mark rounds without a committed graph update.」

兩個提醒：

- **論文沒寫這個實驗的 S\_val 用哪個指標（論文未說明）。** Table 11 的決策只對得上存活率：R4 的平均分比 R2 高，存活率卻較低，被丟；R9 的平均分比 R8 低，存活率持平，卻被收。Appendix E.2 解釋 R10 被拒時提到平均分下降，但 R9 平均分也下降仍被採用，所以不會是平均分。**推論：** 閘門實際看存活率。
- **驗證集太小時，接受與拒絕大半是雜訊。** 20 個 episode 差 1 個就是 5 個百分點，論文自己說單次決策只繫於一兩個 episode，應視為搜尋軌跡，不是顯著性檢定（Section 5.4）。持平也收，所以雜訊也可能把圖往前推。

類比（一般知識，不是論文內容）：這整套機制是爬山法，只接受不比現在差的改動，所以分數只升不降，但走不出需要先變差才能到達的更好設計。

### 拒絕記憶：記下被丟的修改

```latex
\Delta G_{k+1} \sim P_{refiner}\big(\cdot \mid G_k,\, C_{k+1},\, H_{rejected}\big)
```

- G\_k：目前保留的圖。
- C\_{k+1}：下一輪的訓練軌跡，超過長度上限 L\_max 就砍掉開頭、保留結尾。
- H\_rejected：被拒絕過的候選的歷史，當作「別再提這種」的負面證據。

每筆記錄放什麼、refiner 實際看到哪些，見文末【概念】refiner 的輸入、訓練軌跡與 H\_rejected。被拒之後的處理很簡單：圖不變，記一筆，下一輪用同一張圖在下一批訓練題上重跑，再讓 refiner 重新提修改；迴圈固定跑 K 輪，不會因為被拒而提早停止。論文實例（Appendix E.2）：R3 把觸發募資的現金門檻調低，在訓練種子上有效，在驗證集上卻造成過早稀釋與現金不足，驗證存活率從 80.0% 掉到 65.0%，被丟。

## 方法整合總表

七個零件，線上階段三個、離線階段三個，加上兩階段共用的圖本身：

| 零件 | 一句話 | 輸入 | 輸出 | 時機 |
| --- | --- | --- | --- | --- |
| 圖 G | 步驟與可接關係，邊上附 condition / guidance / pitfalls | - | - | 兩階段共用 |
| 定位＋取子圖 | 找出目前節點，取 h=2 跳子圖 | 上一步動作、G | 子圖 G\_t | 線上 |
| Ψ（guidance model） | 把子圖翻成當下提示 | G\_t、q、最近 3 步 | g\_t（文字） | 線上 |
| solver | 選下一步動作 | q、完整軌跡、g\_t | Thought＋Action | 線上 |
| refiner | 看軌跡提出改圖清單 | 目前圖、訓練軌跡、分數、H\_rejected | 修改清單 ΔG（JSON） | 離線 |
| 驗證閘門 | 候選圖在驗證集分數不低於舊圖才收 | 候選圖、驗證集 | 收或丟 | 離線 |
| 拒絕記憶 | 記下被丟的修改 | 被丟的候選與其證據 | 供下一輪 refiner 參考 | 離線 |

## 實驗一：主結果（Table 1）與乾淨對照

論文宣稱 PG 在 24 個「模型 × benchmark」格子中，有 21 格排第一或並列第一；改成只和無記憶 ReAct 比較（同模型、同 solver），24 格中有 23 格為正，但 HotpotQA 幾乎沒有增益。

**設定（Section 4）：** 4 個 LLM（Claude Sonnet 4.6、Gemini 3.1 Pro、Gemini 3.5 Flash、Grok 4.1 Fast），6 個 benchmark，7 個對照做法（見文末【概念】七個 baseline）。所有方法共用同一個 ReAct solver，只差經驗怎麼存、怎麼用。guidance model 與 refiner 和 solver 用同一個 LLM；全部用 greedy decoding。

**六個指標與測試題數（Table 5）：** 題數決定一題值幾分，GDPval 只有 44 題，一題約 2.3 分，小差距很容易是雜訊。

| Benchmark 與指標 | 測什麼 | 測試題數 |
| --- | --- | --- |
| HotpotQA Acc. | 多跳問答的答案是否正確（LLM 評審判斷與標準答案等價） | 1,000 |
| MultiChallenge Acc. | 多輪對話中，是否記得並遵守先前的指令（LLM 評審的整體成功率） | 166 |
| GDPval Rubric Score | 專業交付物按每題評分表打分的平均 | 44 |
| ALFWorld Success | 虛擬家庭任務的成功率，動作順序要求嚴格 | 134 |
| τ-bench Pass@1 | 客服情境，最後資料庫狀態是否等於標準答案的比例 | 115 |
| BFCL v3 Acc. | 多輪函式呼叫的準確率 | 100 |

**論文的宣稱（Section 5.1）：** 對每格最強的 baseline，PG 19 勝、2 平、3 敗。3 敗是 Claude 的 HotpotQA、Grok 的 ALFWorld 與 τ-bench；2 平是 Claude 與 Gemini 3.5 Flash 的 MultiChallenge。最大的領先幅度是 BFCL v3 配 Gemini 3.5 Flash（67.00 對 58.00）、GDPval 配 Gemini 3.1 Pro（78.78 對 71.37）、τ-bench 配 Gemini 3.1 Pro（80.00 對 73.04）。

**乾淨對照：PG 減去無記憶 ReAct，同一個模型、同一個 solver，單位是分：**

| 模型 | HotpotQA | MultiChallenge | GDPval | ALFWorld | τ-bench | BFCL |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Sonnet 4.6 | -0.10 | +6.03 | +5.26 | +6.71 | +7.82 | +6.00 |
| Gemini 3.1 Pro | +1.40 | +7.83 | +22.39 | +5.22 | +7.83 | +7.00 |
| Gemini 3.5 Flash | +1.40 | +10.24 | +5.09 | +11.19 | +13.05 | +11.00 |
| Grok 4.1 Fast | +1.70 | +18.68 | +13.96 | +13.43 | +3.48 | +8.00 |

- 24 格中 23 格為正，唯一為負的是 Claude 的 HotpotQA（-0.10）。
- HotpotQA 幾乎沒有增益，最大只有 +1.7，小於該列的信賴區間寬度。其餘五個 benchmark 是 +3.48 到 +22.39。
- 「贏 baseline」要打折：不少 baseline 本身比無記憶還差。例如 Gemini 3.1 Pro 的 ALFWorld，無記憶是 94.78，MemoryBank 是 85.07，RAP 是 80.60。所以 19 勝有一部分是對手退步，和無記憶的對照才看得出 PG 本身的貢獻。
- 一個潛在混淆（推論，不是論文承認的）：論文說所有學習型 baseline 吃同樣的訓練軌跡，但 PG 的驗證閘門額外用了驗證集（HotpotQA 1,000 題、MultiChallenge 100 題，Appendix B.1），論文沒說 baseline 能不能用驗證集。

請直接看 **Table 1**。原 caption：「Main results across LLMs and benchmarks. Brackets give 95% confidence intervals; the best value is highlighted.」

## 實驗二：使用方式消融（Table 3）

局部子圖加生成式提示，在三個 benchmark 上都是最高；整張圖會傷害，尤其是需要嚴格動作順序的 ALFWorld。這是唯一直接檢驗核心設計（局部取子圖、再由 Ψ 翻成提示）的實驗（Section 5.5）。

**設定：** 同一張圖、同一個模型（Gemini 3.5 Flash），只改兩件事：給 agent 看整張圖還是局部子圖，以及圖是原文塞進去，還是先讓 Ψ 翻成提示。比較四種組合：

- 無圖：不用 PG
- 整張圖＋原文塞入：整張圖序列化後直接放進 prompt，不經 Ψ
- 整張圖＋生成式：整張圖交給 Ψ 翻成提示
- 局部子圖＋生成式：論文的完整做法

兩個成本指標：Avg. Tok 是每題平均用掉的 token 數（包含 Ψ 的呼叫），Avg. Step 是每題 solver 平均走幾步，兩者都是越低越好。

**準確率（單位：分，越高越好）：**

| 設定 | MultiChallenge | GDPval | ALFWorld |
| --- | --- | --- | --- |
| 無圖 | 80.27 | 54.80 | 72.58 |
| 整張圖＋原文塞入 | 86.60 | 57.17 | 70.34 |
| 整張圖＋生成式 | 87.35 | 56.75 | 54.48 |
| 局部子圖＋生成式 | 89.31 | 63.99 | 81.53 |

**成本：token 相對無圖的倍數**（由 Table 3 的原始 token 數計算）：

| 設定 | MultiChallenge | GDPval | ALFWorld |
| --- | --- | --- | --- |
| 整張圖＋原文塞入 | 1.53 倍 | 0.96 倍 | 1.17 倍 |
| 整張圖＋生成式 | 2.18 倍 | 1.63 倍 | 5.34 倍 |
| 局部子圖＋生成式 | 1.85 倍 | 1.33 倍 | 1.55 倍 |

**三件事：**

1. 局部子圖在三個 benchmark 都最高，比各自第二名高 1.96、6.82、8.95 分。
2. 整張圖會傷害。ALFWorld 從 72.58 掉到 54.48，同時 token 是無圖的 5.34 倍。推論：ALFWorld 要求嚴格動作順序，整張圖裡不相干的分支，Ψ 還是會把它們寫進提示（論文只給結果，沒給機制）。
3. 成本一直比無圖高。局部子圖的 token 是無圖的 1.33 到 1.85 倍。步數則在 GDPval（28.20 到 18.57）與 ALFWorld（21.84 到 18.80）下降，MultiChallenge 反而從 3.87 升到 4.22。

請直接看 **Table 3**。原 caption：「PG usage ablation with Gemini 3.5 Flash. On fixed subsets, we report MultiChallenge accuracy, GDPval rubric score, and ALFWorld success rate (all ↑), alongside average tokens and solver steps per sample (both ↓).」

## 實驗三：建構模式（Table 2）

這個實驗檢驗自我演化有沒有用，以及能不能修好壞掉的專家圖。穩的訊號有兩個：壞的專家圖會讓成績崩掉，而演化救得回來；至於空圖起步能不能追平專家圖，MultiChallenge 的資料分不出來（Section 5.3）。

**設定：** 同一個模型（Gemini 3.5 Flash，Appendix D.3），改變「圖從哪來、怎麼更新」，比較五種組合（Appendix D.2）：

| 模式 | 起點 | 更新方式 | 驗證閘門 |
| --- | --- | --- | --- |
| 1 | 手寫專家圖 | 不更新 | 無 |
| 2 | 手寫專家圖 | 跑完整個訓練集後一次大改 | 無 |
| 3 | 手寫專家圖 | 分批演化 | 有 |
| 4 | 空圖（Start → End） | 一次大改 | 無 |
| 5 | 空圖 | 分批演化 | 有 |

「分批演化」與「一次大改」的差別見文末【概念】分批演化與一次大改的差別。

**指標與分母：**

- Ans EM（Exact Match）：答案字串和標準答案完全相同才算對，只測最終答案。論文同時報 Ans F1（答案與標準答案的字詞重疊程度，比 EM 寬鬆），趨勢相同，這裡只看 EM。
- MultiChallenge Overall：LLM 評審判斷整段對話的指令是否都遵守的成功率。MultiChallenge 另有四個子指標（Inference Memory、Instruction Retention、Reliable Versioned Editing、Self Coherence），這裡只看 Overall。
- 分母：HotpotQA 測試 1,000 題，1 題 = 0.1 分。MultiChallenge 在這張表只用 56 題（Appendix B.1），1 題 = 1.79 分。

**結果：**

| 模式 | HotpotQA EM | 和無圖差 | MultiChallenge Overall | 和無圖差 |
| --- | --- | --- | --- | --- |
| 無圖 | 58.8 | - | 87.50 (49/56) | - |
| 1 手寫專家圖 | 62.8 | +4.0 | 58.93 (33/56) | -16 題 |
| 2 專家圖＋一次大改 | 63.8 | +5.0 | 53.57 (30/56) | -19 題 |
| 3 專家圖＋分批演化 | 63.1 | +4.3 | 92.86 (52/56) | +3 題 |
| 4 空圖＋一次大改 | 55.4 | -3.4 | 89.29 (50/56) | +1 題 |
| 5 空圖＋分批演化 | 66.3 | +7.5 | 91.07 (51/56) | +2 題 |

**三個結論：**

1. **HotpotQA：只有模式 5 明顯最好。** 比無圖多答對 75 題。模式 4 和 5 都從空圖出發，EM 差 10.9，比無圖還差的模式 4 則少 34 題。
2. **專家圖起點時，演化沒有額外加分。** 模式 3（63.1）只比不更新的模式 1（62.8）高 0.3，還低於模式 2（63.8）。
3. **MultiChallenge：穩的訊號是「壞專家圖會讓成績崩掉，而且演化救得回來」。** 模式 1、2 比無圖少 16、19 題，模式 3 從模式 1 的 33 題回到 52 題，和論文的 +33.93 對得上。但模式 3、4、5 彼此只差 1 題、和無圖只差 1 到 3 題，不能據此說誰比誰好，也不能說「空圖起步追平專家圖」。

**乾淨對照（方法本身的貢獻）：** 同樣從專家圖出發，加上演化與閘門，HotpotQA 只多 +0.3 EM，MultiChallenge 多 19 題。同樣從空圖出發，加上演化與閘門，HotpotQA 多 10.9 EM，MultiChallenge 只多 1 題。

請直接看 **Table 2**。原 caption：「PG construction modes on HotpotQA and MultiChallenge. All metrics are higher-is-better.」

## 值得帶走的東西

**改進迴圈：提案、獨立驗證集把關、被拒記錄回灌。** 讓 LLM 提出對某份文字資產（prompt、規則、skill、圖）的修改，用一組它沒看過的資料量化新舊版本，沒變差才採用，被拒的記下來，下一次提案時一併給它看。這個做法與圖無關，任何可編輯的文字資產都能套。

```text
asset = 初始版本;  rejected = []
score_asset = evaluate(asset, VAL)            # 只算一次，快取
for round in 1..K:
    traces   = run(asset, TRAIN_BATCH[round]) # 用目前版本跑新一批訓練資料
    proposal = LLM_propose(asset, traces, rejected)
    cand     = apply(asset, proposal)
    if not valid(cand): rejected.append(proposal); continue
    score_cand = evaluate(cand, VAL)
    if score_cand >= score_asset: asset, score_asset = cand, score_cand
    else: rejected.append((proposal, cand, score_cand))
```

使用時要記得的三個限制：

- **它是爬山法（一般知識）：** 分數只升不降，但走不出需要先變差才能到達的更好設計。
- **驗證集太小時，接受與拒絕大半是雜訊：** 論文的驗證集只有 20 個 episode，持平也收，雜訊也可能把版本往前推。
- **約束只寫在 prompt、驗證器不檢查，就等於沒有約束：** 例如 refiner 編出不存在的工具節點，結構檢查擋不住。

選擇規則（一般知識）：先用這種貪心閘門；只有驗證分數連續多輪不動、而且驗證資料夠大時，才考慮能接受較差版本或同時保留多個候選的做法。

## 【概念】定位與子圖：上一步動作怎麼對到圖上的節點

一句話：每一步先用「agent 上一步的動作」在圖上找出目前位置，再沿著往外的邊展開固定步數，只把這一小段圖交給後面使用。這一段解釋 Eq. 2 前半（Match 與 N\_h）實際在做什麼。

**上一步動作 a\_{t-1} 從哪來？** 不是另外算出來的，就是 solver 上一步自己寫出的那行 Action。solver prompt 規定每一步只輸出一個 Thought 和一個 Action，格式是 `Action: <tool_name>(arg1=val1, ...)`（Appendix B.5），這行會原樣記進軌跡。所以 a\_{t-1} 就是軌跡裡最後一個動作，例如 `fund_raising_request(type='equity', amount=50000000)`。

**「exactly matching」到底比什麼？** 論文只寫「exactly match」，細節沒有交代（論文未說明）：

- 比整行（含參數）還是只比工具名？沒說。
- 節點也可以是推理步驟或任務狀態（Section 3.1），例如 Decide\_Capital、Month\_Start，它們不對應任何工具呼叫，怎麼比對？沒說。
- **推論：** 比的應該是工具名，因為 refiner prompt 規定 ACTION 節點必須和可用工具名一致（Appendix B.5 的 Rule 1）。但 Appendix B.5 範例裡節點叫 First\_Hop\_Retrieve、工具叫 first\_hop\_retrieve，大小寫不同，所以「exact」大概先做過正規化。

論文也只展示了比對後的結果（序列化範例裡的 Active Cognitive Node），沒有展示比對這一步。

**論文實際寫了什麼，與一般實作的名稱**

| 論文原文有寫 | 論文沒寫（一般知識或推論） |
| --- | --- |
| 把最近一個動作「exactly match」到圖上的一個節點，得到 u\_t | 用什麼資料結構比對。常見做法是字典查表：節點名稱對到節點，查得到就是 u\_t，查不到就是空 |
| 從 u\_t 沿著往外的邊，最多展開 h 步，收集走到的節點和邊 | 這個展開常稱為廣度優先走訪（BFS）：先收完同一層，再往下一層 |
| 比對不到就用整張圖；實驗 h=2 | 比對失敗的頻率 |

字典查表與 BFS 只是常用的程式名稱，不是論文內容。比對只看字串吻合，不用 embedding、不算相似度，所以結果確定。

**手動走一遍。** 邊清單：前兩條來自 Appendix B.5 的 HotpotQA 節錄，後兩條是自編例子。

1. First\_Hop\_Retrieve → Scan\_Index
2. Scan\_Index → Bridge\_Extract
3. Bridge\_Extract → Second\_Hop\_Retrieve（自編）
4. Second\_Hop\_Retrieve → Answer（自編）

agent 上一步的動作是 first\_hop\_retrieve，h = 2：

&#91;1\] 找節點：清單裡有名字對得上的，First\_Hop\_Retrieve，這就是 u\_t -> \[2\] 第 1 步：找「起點是 u\_t」的邊，得到第 1 條，收進 Scan\_Index -> \[3\] 第 2 步：找「起點是 Scan\_Index」的邊，得到第 2 條，收進 Bridge\_Extract -> \[4\] h = 2，停止，第 3、4 條不收 -> \[5\] G\_t = 第 1、2 條邊，連同各自的 condition、guidance、pitfalls

比對失敗時（上一步的動作在圖上找不到），G\_t 就是這四條邊全部。Appendix B.5 的序列化範例按「Hop 1」「Hop 2」分組列出邊，和這個做法一致。

**展開的三個細節：**

- **只沿出邊走，也就是順著箭頭方向。** 走過來的節點不在子圖裡，那段歷史由最近 w = 3 步的軌跡視窗補。
- **遇到分岔，同一層的所有出邊一起收。** 例如 EnterpriseArena 後期的圖，Decide\_Capital 後面接 fund\_raising\_request 和 book\_closing，兩條都在第 1 跳。
- **自編例子：** 用 EnterpriseArena 的主線 Month\_Start → check\_cash\_in\_bank → cash\_flow\_forecast\_calculation → save\_note → check\_market\_data → Decide\_Capital，若 u\_t = check\_cash\_in\_bank、h = 2，收進 cash\_flow\_forecast\_calculation（第 1 跳）與 save\_note（第 2 跳），到此停；check\_market\_data 是第 3 跳，不收。

**為什麼要沿結構取，而不是依相似度取？** Section 3.2 的論點：獨立做 top-k 相似度檢索，可能漏掉步驟之間的連接。例如檢索 submit 的指引卻沒有前面的 check\_answer 轉移，就可能漏掉讓提交變得合理的驗證步驟。沿結構取出鄰域，同時帶出動作和它的程序前提。

## 【概念】Ψ 與 solver 的輸入輸出對照

一句話：推論時有兩個 LLM 各司其職。Ψ（guidance model）讀圖，寫出一小段提示；solver 看不到圖，只讀 Ψ 寫的提示，然後選動作。以下只列論文實際給出的（Appendix B.5 的兩個 prompt 模板），沒寫清楚的另外標示。

|  | Ψ（guidance model） | solver |
| --- | --- | --- |
| 角色 | 把子圖翻成當下的提示 g\_t | 選下一步動作 a\_t |
| 看到的圖 | 序列化後的局部子圖：節點 ID、類型、描述，加上每條邊的 condition / guidance / pitfalls，按 Hop 1、Hop 2 分組 | 看不到圖，只看到 Ψ 寫的 g\_t |
| 看到的軌跡 | 最近 w=3 步 | 完整軌跡 T\_t |
| 任務描述 | 有（模板的 task\_description 欄位） | 在 system\_prompt 裡（推論） |
| 使用者問題 q | 有（模板的 query 欄位，見下方第 2 點） | 模板沒有獨立欄位，推論在 system prompt 或軌跡裡 |
| 指令 | 依邊上三個屬性，寫出清楚可執行的建議：下一步做什麼、要避開什麼、失敗後怎麼補救，並帶上圖裡寫到的具體指令格式、工具、參數 | 固定格式：每次只輸出一個 Thought 和一個 Action，不准自己寫 Observation |
| 輸出 | g\_t：自由文字，論文沒規定格式 | `Thought: ...` 加 `Action: tool_name(arg=val, ...)` |

**資料流：**

&#91;1\] 上一步動作 a\_{t-1} -> \[2\] 定位節點、取子圖 -> \[3\] Ψ 輸出 g\_t -> \[4\] g\_t 填進 solver prompt 的 `Procedural Graph Guidance:` 欄位 -> \[5\] solver 輸出 Action -> \[6\] 環境執行並回傳觀察 o\_t -> \[7\] (a\_t, o\_t) 接進軌跡，進入下一步

**三個容易誤會的點：**

1. **solver 完全看不到圖本身。** 圖的資訊只透過 Ψ 的文字進來，所以 Ψ 寫得好不好，直接決定圖有沒有用。
2. **Ψ 的 query 欄有兩種讀法，論文沒有釐清。** Appendix B.5 的 prompt 把它描述成「current active query / observation」，Eq. 2 則寫成使用者問題 q。如果是原始問題，Ψ 每一步看到的都是同一句話；如果是最新的觀察，Ψ 就會針對剛發生的結果反應。後者比較能解釋 Figure 2 裡「avoid: repeating search」這類提示，但這是推論。
3. **Ψ 的實際輸出全文，論文沒有完整展示。** Figure 2 中間欄的 g\_t 只是示意。

**一個自編的 g\_t 例子**（根據 Appendix B.5 那兩條邊的 guidance 與 pitfalls 想像的輸出，不是論文原文）：「你剛取回第一批證據。下一步請掃描這些段落，找出連接到問題目標的橋接實體，例如出生日期或地點。不要略過細節，漏掉橋接實體的名稱會讓第二跳搜尋失敗。」

## 【概念】一個 benchmark 一張圖：refiner 不選圖，也不新增圖

一句話：論文裡每個 benchmark 只有一張圖，演化就是把這一張圖從 G\_0 改到 G\_K；refiner 的輸入只有一張圖、輸出只有四種零件修改，所以沒有「選哪一張圖」或「要不要新增一張圖」的決策。

**為什麼說只有一張圖。** Table 7 每一欄是一個 benchmark，各有一組節點數與邊數。refiner 的輸入欄位是目前保留的那一張圖（Appendix B.5 的 current\_graph\_json）；輸出格式只有 add\_nodes、delete\_nodes、add\_edges、delete\_edges，全是改這一張圖的零件，沒有建立新圖的操作。

**「從零開始」是怎麼回事。** 它指的是起始圖只有 Start → End 兩個節點（Appendix D.2 的模式 4、5）。refiner 的做法仍然是對這張空圖 add\_nodes 與 add\_edges，EnterpriseArena 的 Round 1 就是這樣一次補出整條主線（Appendix E.3）。所以「從零生成」本質上還是修改既有的圖。

**一個 benchmark 裡任務很多樣怎麼辦？** 論文用同一張圖服務整個 benchmark，例如 GDPval 涵蓋不同職業的任務，也只有一張 15 個節點的圖，再靠定位機制讓每一步只取圖上的一小段。論文沒有討論依任務類型切換不同的圖，也沒有驗證過多張圖或異質任務的情況（論文未說明）。

**如果同一張圖裡有互不相關的子圖，不該有連接怎麼辦？** 論文沒有討論這個情境，也沒分析過同一張圖放互不相關子圖會怎樣。左欄是論文有寫的，右欄是我由此推出來的：

| 論文有寫 | 推論 |
| --- | --- |
| 結構檢查只列出兩個條件：邊的端點存在、每個節點走得到終點。沒列出整張圖連通，或從 Start 可達（Appendix B.6） | 不該連的子圖可以保持分離，只要 refiner 不去加連接邊 |
| 第 1 步固定從 Start 定位，取 2 跳子圖（Eq. 2） | Start 要連到各子圖的入口，所以第 1 步的子圖會把各類任務的前兩層混在一起，靠 Ψ（它有看到任務描述與 query）自己篩 |
| 定位只看上一步動作對到哪個節點（Eq. 2） | 圖沒有路徑記憶：同一個節點，不管任務是哪一類，都吐出同一個鄰域 |
| 閘門比驗證集平均分，不低於舊圖就收（Eq. 5） | 改動若對 A 類有利、對 B 類有害，只要平均不降就會被收；論文沒按任務類型拆開分析 |

**共用節點的例子（自編）：** 兩類任務都會呼叫 search。A 類 search 後要 verify，B 類 search 後要 summarize。圖上只有一個 search 節點，兩條出邊都會進鄰域，Ψ 只能靠 q 和最近 3 步軌跡猜該用哪一條。

論文確實顯示過「無關的圖內容有害」：Table 3（Gemini 3.5 Flash）裡，整張圖加生成式提示是最差設定，ALFWorld 成功率 54.48，局部子圖是 81.53。局部取子圖是它的緩解辦法，但只有在定位成功、鄰域本身不混雜時才成立。

**結論：** 論文沒處理異質任務，一個 benchmark 一張圖，互不相關的任務如何共存沒有說明。它靠「上一步動作 → 節點」的定位加上 Ψ 這個 LLM 過濾，沒有任務類型路由。**推論：** 它在流程相近的任務上最說得通，例如 EnterpriseArena 每個月跑同一條主線；異質任務混在一張圖上是否有效，沒有被驗證。

## 【概念】refiner 的輸入、訓練軌跡與 H\_rejected

一句話：refiner 每一輪看到的是「目前這張圖、這批訓練軌跡、被拒絕過的歷史」，外加任務背景；H\_rejected 每筆記的是「上次改了什麼、改出什麼圖、為什麼被拒」。

**先定義：訓練軌跡是什麼。** 它是 solver 在訓練題上實際跑出來的完整過程記錄：一題從開始到結束，每一步的動作和環境回傳的觀察，再加上最後的分數（Section 3.3 Step 1）。

```latex
E_k = \{ (q_i,\, T_i^{(k)},\, S_i^{(k)}) \}_{i=1}^{|B_k|}
```

- B\_k：第 k 輪從訓練集抽出的一批題目。
- q\_i：第 i 題的問題。
- T\_i^{(k)}：solver 解這題的軌跡，也就是 (a\_1, o\_1, a\_2, o\_2, ...)，動作與觀察交錯排列。
- S\_i^{(k)}：這題的最終分數，範圍 0 到 1；二元任務就是成功或失敗。

白話：一批題各留一筆「題目、解題過程、得幾分」，refiner 拿這批資料比對高分與低分的過程。論文的公式只寫動作與觀察，但 solver prompt 的 Current Trajectory 欄位和 Appendix C.3 的 trace 都有 Thought，推論 T 也包含 Thought。

**refiner 的輸入**

| # | 輸入 | 內容 | 出處 |
| --- | --- | --- | --- |
| 1 | 目前保留的圖 | G\_{k-1}，序列化成 JSON | Eq. 6、Algorithm 1 第 9 行、Appendix B.5 的 current\_graph\_json |
| 2 | 這一輪的訓練軌跡 C\_k | 用 G\_{k-1} 在這批訓練題上跑出的軌跡串接起來，超過 L\_max 就砍開頭留結尾 | Section 3.3 Step 1 與 Step 4、B.5 的 attempts\_block |
| 3 | 每題分數 | 每題的最終分數 S\_i，供 refiner 比對高分與低分軌跡 | Algorithm 1 第 9 行 |
| 4 | 被拒絕的歷史 | H\_rejected 經 SerializeRejections 整理後的內容 | Eq. 6、B.5 的 rejected\_block |
| 5 | 任務描述 | 這個 benchmark 在做什麼 | 只出現在 B.5 的 prompt 模板 |
| 6 | 可用工具清單 | agent 能執行的工具名稱，ACTION 節點必須對得上 | 只出現在 B.5 的 prompt 模板 |
| 7 | 模式 | static\_onetime、static\_incremental、scratch\_onetime、scratch\_incremental 之一 | 只出現在 B.5 的 prompt 模板 |

Eq. 6 只寫了 1、2、4，是簡化版；5 到 7 要看 Appendix B.5 才有。

**H\_rejected 每一筆記什麼**

每筆記一次「被丟的候選」，分兩種情況（Algorithm 1）：

| 欄位 | 驗證沒過（第 19 行） | 結構檢查沒過（第 12 行） |
| --- | --- | --- |
| ΔG\_k：refiner 當輪輸出的修改清單（JSON） | 有 | 有 |
| G\_cand\_k：套用修改後的候選圖 | 有 | 可能不存在（Appendix B.6） |
| E\_k：當輪的訓練軌跡（用被拒之前的圖 G\_{k-1} 跑出來的） | 有 | 有 |
| 結果 | 驗證分數 S\_cand\_k | 錯誤診斷 d\_k（沒有分數） |

H\_rejected 一開始是空的，之後只增不減。注意：存進去的軌跡是用被拒之前的那張圖 G\_{k-1} 跑出來的，refiner 就是看了這批軌跡才提出那份被拒的修改；候選圖本身在驗證集上跑出的軌跡不會存，只留下分數。所以記錄的是「當初為什麼這樣改」的證據。

**真正餵給 refiner 的是哪一部分，論文有兩種說法，沒有判定：**

| 位置 | 說法 |
| --- | --- |
| Section 3.3 Step 4 | 整筆都進 H\_rejected，refiner 收到 H\_rejected |
| Appendix B.6 | SerializeRejections 只交「候選圖加驗證分數（或結構錯誤診斷）」，訓練軌跡留在記錄裡，沒提 ΔG |

**推論：** 實際餵進去的大概是 B.6 的版本，因為那是實作層的描述。這樣舊軌跡不會重複佔 context，但 ΔG 沒給，refiner 得自己拿被拒圖和現在的圖比對，才看得出上次改了什麼。

**會不會 context 爆炸？** 論文沒處理這個問題，但在它的實驗規模下大概不會。論文有限制長度的只有訓練軌跡 C\_k（超過 L\_max 就砍開頭，L\_max 的數值論文沒給）；H\_rejected 本身沒有上限、摘要或淘汰機制，Algorithm 1 只有 append，從不清空。增長多快取決於每筆實際放什麼：只放候選圖與分數時，一筆約等於一張小圖（除 BFCL 外每張圖只有 7 到 27 條邊）；連軌跡也餵時，增長會快很多。實際筆數也很少，EnterpriseArena 在 R10 開始前只累積 4 筆。**推論：** 增長是線性的；輪數很多、或圖像 BFCL 那麼大時，要自己加上限，例如只留最近 N 筆，或只留修改清單不留整圖，論文沒驗證過。

## 【概念】七個 baseline：各自存什麼、推論時怎麼用

一句話：七個對照做法裡，1 個是不用任何記憶的 ReAct，其餘 6 個是學習型做法。它們都用同一個 ReAct solver，差別只在「從訓練軌跡存下什麼」和「推論時怎麼放進 prompt」（Section 4、Appendix B.3）。順序依論文的「結構程度」由低到高。

| 方法 | 存什麼 | 推論時怎麼用 |
| --- | --- | --- |
| Vanilla ReAct | 什麼都不存 | 無，這是起點 |
| MemoryBank | 每題的經驗摘要，並依遺忘機制淘汰舊的 | 依相關度（偏重近期）取出，放在 prompt 最前面 |
| RAP | 完整的歷史軌跡 | 找最相似的幾條軌跡，當範例放進 prompt |
| ExpeL | 比對成功與失敗軌跡後，歸納出的自然語言心得 | 心得放進 system prompt，另附取回的成功範例 |
| AutoGuide | 「在狀態 X，做 Y」形式的條件式指引，也是從成功與失敗的對比中抽出 | 每步先概括當前狀態，再取出符合的指引 |
| AWM | 從成功軌跡歸納出的工作流（文字描述加動作序列） | 工作流放進 prompt |
| KnowAgent | 可用動作與「哪個動作後可接哪個」的文字規則 | 整份當固定前綴放進 prompt，每步都一樣 |

請直接看 **Table 6**。原 caption：「Memory mechanisms compared in the main experiments.」

**和 PG 最近的兩個：**

- **AutoGuide：** 論文自己說最接近（Appendix A.4）。同樣是「情境對應動作」，也是每步檢索。差別是 AutoGuide 的指引彼此獨立，PG 把它們連成圖。
- **KnowAgent：** 它存的「動作轉移規則」，概念上就是 PG 的邊，但它是一份靜態文字，沒有圖結構，也不會依當前位置只取一段。

這兩個如果贏過 PG，最值得看，因為它們最接近 PG 宣稱的新東西。

## 【概念】分批演化與一次大改的差別

**一次大改：**

&#91;1\] 用起點圖跑完整個訓練集 -> \[2\] refiner 讀全部軌跡，一次輸出大幅修改 -> \[3\] 直接採用，結束

**分批演化：**

&#91;1\] 用目前圖跑第 1 批 -> \[2\] refiner 提修改 -> \[3\] 驗證集把關，收或丟 -> \[4\] 用（可能已更新的）圖跑第 2 批 -> 重複到最後一批
