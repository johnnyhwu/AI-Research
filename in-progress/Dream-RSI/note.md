# Dream-RSI 筆記:用歷史探索紀錄做 Off-Policy 策略改良

**論文**:Dream-RSI: Recursive Self-Improvement through Evolving Worlds
**作者/機構**:Tong Zheng et al., Google(合作單位含 University of Maryland、Google DeepMind、University of Virginia)
**arXiv**:2609.14858v1,2026年9月14日
**Code**:github.com/zhengkid/Dream-RSI

---

## 30秒版本

Dream-RSI 想解決的問題:用 AI agent 做「科學/演算法發現」時,需要一個「探索策略」來決定要往哪個方向深挖、什麼時候平行展開、什麼時候該停手。這個策略本身也想要能自我改良,但改良一次就要真的跑一整輪昂貴的線上探索才知道好不好——這讓策略的自我改良變得又慢又貴。

Dream-RSI 的解法:把「已經跑完的探索歷史」(discovery tree)直接當成一個可以重播的資料庫。想測試一個新策略好不好,不用真的重新執行任何程式碼,只要讓這個新策略去讀取歷史紀錄裡「如果換一種走法會揭露哪些節點」,就能算出一個分數——這個重播評分幾乎是免費的,可以一口氣測試成千上萬個候選策略版本,篩出最好的一個才真的部署上線。

**帶走的判斷**:這是一個工程紮實、但敘事包裝過頭的論文。它把自己類比成「World Model」(像 Dreamer 那樣),但真正的 world model 是一個訓練出來、能泛化到沒見過狀態的函數;Dream-RSI 的「模擬器」只是原封不動重播已發生的紀錄,沒辦法評估任何原本沒探索過的分支——比較準確的定位是一套精緻的 off-policy replay 評估機制。三個實驗領域裡,真正的貢獻幾乎都集中在「用更少運算資源達到同等品質」,不是「品質突破」。這篇論文真正的價值,其實在 Appendix 那份 270 行的 policy 改良 prompt 裡的工程細節——那裡藏著幾個值得學的通用設計模式(詳見第10節)。

---

## 目錄

**論文主線**
1. 核心問題與動機
2. Dream-RSI 方法
   - 2.1 三階段迴圈總覽
   - 2.2 Discovery Tree 形式化定義
   - 2.3 Online Rollout vs Offline Replay
   - 2.4 Replay Objective 公式
   - 2.5 Policy 改良與選擇流程
   - 2.6 Appendix 深挖:Replay-Based Policy 改良 Prompt
3. 實驗結果摘要

**核心觀念整理(獨立於論文本身,本筆記最高價值段落,建議優先閱讀)**
4. Dreamer 的 World Model 到底是什麼
5. 為什麼不能每一步都用 World Model 搜尋?(Planning vs Policy Learning)
6. 累積歷史會不會讓 Context 爆炸?(論文沒處理的洞)
7. Replay 到底在 Replay 什麼?(policy vs task solution 的區分)
8. Replay-to-Real Gap 的兩個獨立來源
9. Failure Classification 框架,及其在 Agent Tool-Calling 設計上的應用

**收尾**
10. 值得帶走的東西

---

## 1. 核心問題與動機

用 AI agent 做「科學/演算法發現」(scientific/algorithmic discovery)的場景裡,agent 不斷重複「提出候選解 → 執行/評估 → 根據回饋修正 → 再提出」的循環(例如用 LLM 寫程式碼去解最佳化問題,像 AlphaEvolve 那類系統)。隨著任務變難,這個循環要跑得很長很廣,有時要跑到數千次提案-評估循環。這時候「怎麼安排這些循環怎麼跑」本身就決定了效率高低,論文把負責這個決策的東西稱作 **exploration policy(探索策略)**:決定要往哪個方向繼續深挖、哪些候選要平行展開、什麼時候該停手換方向。

**問題一:固定策略學不會東西**。現有做法多半是人工設計一套規則,整個發現過程都不會變,沒辦法從累積的經驗學習,可能一直把資源浪費在早就證明沒用的方向上。

**問題二:讓策略上線學習,又卡在兩個瓶頸**:
- **Meta 層級回饋又慢又貴**:評估「一個候選解好不好」可以很快,但評估「一個探索策略好不好」沒辦法這麼快——要讓策略實際指揮完整輪(可能上百上千次)的發現循環,才知道整體帶出什麼結果
- **候選策略空間很大**:新策略可能表現很差,得試很多版本才找得到好的

兩者疊加:**每個候選策略都要跑一次完整、昂貴的線上探索才能拿到回饋**,讓「持續改良探索策略」這件事變得很難做。

**Dream-RSI 的解法方向**:與其每次改策略都重新跑一次真的探索,不如把已經跑過的發現歷史直接拿來當可重播的模擬環境。因為每一次線上探索的過程,本來就已經把「在哪個節點分支、產生什麼結果、分數多少」全部記錄成一棵樹(discovery tree)。理論上,評估「換一種走法結果會不會不一樣」只需要讀這棵樹裡的紀錄,不用真的重新執行程式碼。

---

## 2. Dream-RSI 方法

### 2.1 三階段迴圈總覽

Dream-RSI 在「線上探索」跟「離線做夢(dreaming)」之間交替,對應原文 **Figure 1**(整個系統透過三個核心階段運作一個遞迴自我改良迴圈——①Online Explore:目前的探索策略指揮一個 coding agent 展開 discovery tree 並記錄歷史軌跡;②Construct Replay Simulator:把產生出的 discovery tree 轉換成可重複使用的模擬器庫;③Dreaming-based Policy Improvement:agent 在腦中"做夢"出大量候選策略,把它們餵進模擬器裡模擬執行、取得快速回饋,持續精煉策略。改良後的策略接著重新部署,進行下一輪線上探索):

```
[1] Online Explore(線上探索)
    -> 用目前的 exploration policy 指揮 coding agent 跑真實發現循環
    -> 把每次嘗試記錄成一棵 discovery tree

[2] Construct Replay Simulator(建構重播模擬器)
    -> 把這棵樹收進歷史庫(simulator pool),庫會越滾越大

[3] Dreaming-based Policy Improvement(做夢式策略改良)
    -> 在歷史庫裡想像出大量候選策略
    -> 把每個候選策略拿去重播已存的樹,算出分數
    -> 挑出表現最好的版本,變成下一輪真的要部署的策略

-> 回到 [1],用改良後的策略開始新一輪
```

只有 exploration policy 的程式碼在變;底層的 coding agent(真的解題的模型)、evaluator(評分機制)、執行介面全部固定不動——這種「凍結大部分東西、只動一個小的可控元件」的設計思路本身值得注意。

### 2.2 Discovery Tree 形式化定義

每個節點代表一次「生成-評估」嘗試,樹的結構記錄了「這次嘗試接著哪一次繼續」。

```
符號:
  r      = 根節點,代表最初的工作空間狀態
  v      = 樹上一個非根節點,代表一次嘗試
  parent = v 的父節點(可以是 r,也可以是另一個 v)
           -> agent 產生 v 時,從 parent 存下來的工作空間繼續,
              並參考 parent 累積的觀察紀錄當上下文
  s_v    = v 這次嘗試的分數(越大越好)
```

節點裡存的不只是分數,還包含檔案系統快照、產生的成果、評估診斷資訊——每個節點都是一次嘗試「完整、可事後重看」的紀錄。

**決策介面**(online 和 offline 共用):

```
A(T) = {r} ∪ {目前樹 T 裡所有葉節點}
```

任何時刻,「可以繼續往下接」的節點有兩種:根節點 r(開一條全新分支),或現有葉節點(延續某條已在走的分支)。

```
W = 平行 worker 數量
C = policy 這一輪選出的批次,C ⊆ A(T),且 |C| ≤ W
```

**走一次具體例子**(W=2):

```
第0輪: T⁰={r}, A(T⁰)={r}, 選 C⁰={r}
       -> 產生 v1(0.42), T¹={r,v1}

第1輪: A(T¹)={r,v1}, 選 C¹={r,v1}(批次大小=2,用滿W)
       -> r 開新分支產生 v2(0.55)
       -> v1 延續產生 v1a(0.51)
       T²={r,v1,v2,v1a}   (v1不再是葉節點)

第2輪: A(T²)={r,v2,v1a}
       選 C²={v2,v1a}
       ...依此類推
```

> **論文沒交代清楚的地方**:形式化定義裡,批次 C 是一個集合,代表同一輪根節點 r 最多只能被選一次——要「同時開10條平行分支」按這個定義得一輪一輪慢慢堆起來。但論文 §4 描述 baseline 策略時卻說它「一開始就平行開了10個或32個獨立 workspace」,聽起來像是一開局就直接平行開好幾條。這兩處怎麼銜接,論文沒有明講——是形式化只是抽象框架、具體實作另外處理,還是省略了細節,不確定。

### 2.3 Online Rollout vs Offline Replay

這是整篇論文能省錢的根本機制,兩者共用同一套「選節點、湊批次」規則,但運作邏輯不同。

**Online rollout(真的在跑,且是隨機的)**:

```
第 t 輪外層迭代:
  用目前的 policy π_t,從 T⁰_t={r} 開始蓋一棵全新的樹
  最多跑 K1 輪內部決策:
    每一輪:π_t 選批次 C^k_t
           coding agent 真的產生新候選解,evaluator 真的評分
           -> 這步是隨機的:同起點,這次跑跟下次跑結果可能不同
    新節點接上樹
  直到選了空批次,或跑滿K1輪,結束
  最終樹記為 T_t,存進歷史:H_t = H_{t-1} ∪ {T_t}
```

H_{t-1}(之前所有輪次的樹)會在這輪被讀出來當上下文餵給 coding agent 參考,但跟這輪正在蓋的新樹是分開的兩件事。

**Offline replay(不是跑,是讀,而且是決定性的)**:offline 階段會把目前累積的**所有**樹(T_1到T_t)都拿來重播一遍,評估同一個候選 policy 版本在全部歷史上的表現(不是只重播最新那棵)。

| | Online rollout | Offline replay |
|---|---|---|
| 節點內容從哪來 | coding agent 現場生成、evaluator 現場評分 | 直接讀 T_i 裡早就存好的內容 |
| 同一動作,結果會變嗎 | 會(隨機) | 不會(決定性) |
| 選根節點 r 時,回傳哪個小孩 | 現場生一個全新分支 | 一定是 T_i 裡"最早被創造出來、還沒揭露"的那個小孩(順序鎖死) |
| 選某已展開節點 v 時 | 現場生一個全新小孩 | 直接回傳 T_i 裡存好的那個小孩 |

**走一次完整例子**,假設真實線上探索存下的完整歷史樹 T_1 長這樣(W=2):

```
T_1(依創造順序):
  r
  ├─ v1 (round1創造, score=0.42)
  │   └─ v1a (round2創造, score=0.51)
  │        └─ v1a1 (round3創造, score=0.58)
  └─ v2 (round2創造, score=0.55)
       └─ v2a (round3創造, score=0.60)
```

用一個替代策略 π^m 去 replay:

```
Round1: T^{m,0}={r}, 選 C={r}
        -> 回傳r最早創造、未揭露的小孩=v1(0.42)
        T^{m,1}={r,v1}

Round2: A={r,v1}, 選 C={r,v1}
        -> r: 回傳下一個未揭露小孩=v2(0.55)
        -> v1: 回傳唯一小孩=v1a(0.51)
        T^{m,2}={r,v1,v2,v1a}

Round3: A={r,v2,v1a}, r已無小孩可揭露
        選 C={v2,v1a}
        -> v2: 回傳v2a(0.60)
        -> v1a: 回傳v1a1(0.58)
        T^{m,3}=全部揭露完畢 -> 停止
```

3輪就把整棵樹揭露完,且每輪都塞滿 W=2——如果原本線上探索是一輪一輪慢慢展開、平行度沒用滿,這個替代策略重播出來的結果就顯示:早知道就該更積極批次處理。**這正是 replay 有意義的地方:不用真的重新執行任何程式碼,只是換一種讀取既有紀錄的順序/分組方式,就能看出不同策略的效率差異。**

> **一個具體限制,直接讀自形式化定義,不是推論**:選 r 時回傳的小孩順序固定照原始創造順序(v1先、v2後)。replay 沒辦法測試「如果當初先開 v2 這條分支會怎樣」——這條路徑在 replay 裡完全不可能被還原出來評估。替代策略能自由決定的是要不要開新分支、開幾條、何時開、怎麼批次組合、深入哪條分支多深、何時停,但不能決定"分支開啟先後順序不同會怎樣"。

> **關於 context 大小的隱憂(論文完全沒討論到的空白)**:Appendix B.1 的探索 prompt 明文要求 coding agent 每次提案前,必須讀完每一個 sibling attempt 底下的 proposal、以及完整歷史 H_{t-1} 裡的每一筆紀錄——不是抽樣、不是只看最近幾輪。但 H_{t-1} 是累積的:輪數越多,要讀的歷史就越大。論文報的效率指標全程只用「discovery-agent calls 的次數」當成本,完全沒有算進「每次 call 因為 context 變長而變貴」這件事。論文全文沒有看到任何關於 context 管理、摘要、檢索式讀取的機制——這是論文沒處理過的問題,不是含糊帶過(詳細討論見第6節)。

### 2.4 Replay Objective 公式

公式要解決的問題:光看「replay 揭露出來的最高分」不夠,因為只要把整棵樹逛光就一定能拿到這棵樹的全域最佳分——量不出「有效率地找到好結果」跟「暴力逛完」的差別。

```
V_i^m = max{ s_v : v 屬於 T_i^{m,k*} }        <- 第一項: discovery quality
        - β1 * N_i^m                          <- 第二項: execution cost
        + β2 * N_i^m / max(1, k_i^{m,*})       <- 第三項: parallelism bonus

符號:
  i          = 第幾棵歷史樹(共t棵)
  m          = 第幾個候選policy版本
  T_i^{m,k*} = policy m 在樹 i 上 replay 到停止時,最終揭露出的子樹
  k_i^{m,*}  = 該次replay跑了幾輪"非空批次"才停止
  N_i^m      = |T_i^{m,k*}| - 1(揭露的非根節點數)
  β1, β2     = 固定權重係數(論文沒有在正文或附錄給出實驗實際用的具體數值)
```

- **quality項**:整趟replay看過的所有節點裡分數最高的那個
- **cost項**:揭露越多節點扣越多分,避免"贏家永遠是把樹逛光的策略"
- **parallelism bonus**:平均每輪揭露幾個節點,獎勵懂得批次平行處理的policy

**帶入 2.3 那棵樹,算一次具體數字**(β1=0.05, β2=0.1,這是示範用數值,不是論文真實設定):

```
Policy A(保守、序列式,揭露v1,v1a,v1a1):
  quality = max(0.42,0.51,0.58) = 0.58
  N=3, k*=3(每輪只選1個)
  V_A = 0.58 - (0.05×3) + (0.1×3/3) = 0.58-0.15+0.10 = 0.53

Policy B(積極、有批次,揭露全部5個節點):
  quality = max(...) = 0.60
  N=5, k*=3(round2、3各選2個)
  V_B = 0.60 - (0.05×5) + (0.1×5/3) = 0.60-0.25+0.1667 = 0.5167
```

雖然 Policy B 的 quality 更高(0.60>0.58)、平行度bonus也更高(0.1667>0.10),但因為多揭露2個節點被cost項多扣,最後 **V_A(0.53) > V_B(0.5167)** ——"保守但精準"贏過"積極但浪費"。這示範了 objective 的核心用意:不是單純找最高分,而是在「找多好」跟「花多少」之間權衡,**天平完全由 β1、β2 決定**。

**跨所有歷史樹取平均**:

```
V^m = (1/t) × Σ(i=1到t) V_i^m
```

一個候選 policy 版本的最終得分,是它在 t 棵歷史樹上各自算出的 V_i^m 加總除以 t——不能只在一棵樹上評分,否則選出的 policy 可能只是剛好很適合那棵樹的特殊結構。

### 2.5 Policy 改良與選擇流程

```
第t輪 offline 階段開始,歷史 H_t={T_1,...,T_t} 固定不動:

  m=0: π_t^0 = π_t(目前用的policy,原封不動)
       -> 在T_1...T_t全部replay -> 算出V^0

  m=0->1: 【policy-development agent(LLM)】讀π_t^0的replay紀錄
          -> 改寫程式碼 -> 產生π_t^1
          -> replay -> 算出V^1

  ...重複到m=M-1,共產生M個版本

  選擇: m* = argmax V^m
        π_{t+1} = π_t^{m*}  <- 下一輪真的部署的policy
```

**保底機制**:候選版本一定包含 π_t^0(原始版本),所以 max V^m ≥ V^0——保證 π_{t+1} 的 replay 分數絕不會比 π_t 差,最壞情況是這M次改寫都沒改進,那就繼續用原本的,不會因為亂改而倒退。這叫 **monotonic non-regression(單調不退步)**,任何"LLM自己改自己邏輯"的系統都可以檢查有沒有做這個保底(詳見第10節)。

> **這個保底有一個容易被忽略的限制**:它保證的是"replay分數不退步",不等於"真實線上表現不退步"。這個落差就是 replay-to-real gap,第8節會完整拆解。

**完整演算法裡三個角色的LLM分工**:

| 角色 | 用哪份prompt | 產出什麼 | 何時動 | 成本 |
|---|---|---|---|---|
| Discovery agent | Appendix B.1 | 任務的候選解內容 | 只在Online Explore階段 | 貴(真的要解題) |
| Evaluator | (論文未交代是否為LLM) | 分數s_v | 只在Online Explore階段 | 通常便宜(跑程式量測) |
| Policy-development agent | Appendix B.2 | 探索策略的程式碼 | Dreaming階段,每輪跑M次 | 中等(改程式碼,不用真的解任務) |
| Replay本身 | (無prompt,純程式邏輯) | 分數V_i^m | Dreaming階段,每個候選版本都跑 | 幾乎免費(純讀表) |

真正貴的LLM呼叫只發生在角色1(有限次)跟角色3(每輪只跑M次,通常個位數到十位數),而replay評分本身完全不含LLM——這是"上千次候選策略評估不會產生上千次昂貴API call"的原因。

### 2.6 Appendix 深挖:Replay-Based Policy 改良 Prompt(B.2)

這份 ~270 行的 prompt,是全篇工程含金量最高的地方,指導【policy-development agent】怎麼改寫探索策略程式碼。以下是幾個核心機制:

**Prefix-only 限制**:policy 的每個決策,只能用「目前為止這次replay自己已主動揭露過的節點」,不能用還沒揭露節點的分數、budget統計、或任何"上帝視角"資訊。這避免了作弊(先掃過整棵樹找最高分、假裝一路探索剛好找到)——真實線上部署時沒有這種作弊空間,因為線上的樹根本還沒長出來。這種「決策只能用當下已知資訊,不能偷看未來/全局」的限制,在RL和online algorithms領域是標準要求,叫 **causality constraint**,不是Dream-RSI獨創(off-policy evaluation也是同樣邏輯)。

**Batch決策的Portfolio概念**:每輪最多選W個候選,prompt要求拆成三種角色湊:
```
Exploitation(利用) = 目前最有希望的正常refinement
Exploration(探索)  = 開新root,或深入還沒探索夠的branch
Recovery(搶救,最多1個) = 一個真的可修復的失敗嘗試
```
這是經典的 multi-armed bandit explore-exploit tradeoff,但多了 Recovery 這個bandit框架裡沒有的第三角色——因為這裡的"失敗"可能只是實作bug,不代表方向本身壞掉。規則:recovery最多佔1個名額、不能搶走exploitation名額或讓worker閒置;不能用固定配額,要根據prefix證據動態決定;禁止隨機抽樣、禁止"因為某候選很明顯就只選它"。

**失敗分類機制**(完整框架見第9節,這裡只列論文用的四類):
```
hard-unrecoverable          = 硬性不可能修好
repairable implementation failure = 想法可能沒問題,是實作bug
weak-but-underexplored      = 分數普通但還沒試夠深
repeatedly unpromising      = 已有足夠證據顯示這方向真的不行
```
一個容易忽略的細節:`valid==False` 不等於"失敗"——一次嘗試可能程式碼順利跑完、沒有拋出錯誤,但產出的解不滿足正確性條件,這不算"失敗",是正常評估出一個較弱的解,不該被當成"可修復失敗"去重試。而且任何分類都不是永久的:即使一條分支被判定成hard-unrecoverable,只要之後真的出現一次成功結果,就要重新打開這條分支,不能因早期失敗紀錄就永久鎖死。

**Beta:探索策略內部的保守/積極旋鈕**(此處只簡述,不深入):Prompt裡的 `beta` 是策略程式碼內部的一個超參數,決定策略行為多寬容/多保守,跟正文公式(1)的 β1、β2 不是同一組東西——論文正文用 β1/β2,Appendix實作用 beta 搭配 `pareto.reward`、`pareto.auc`、`lambda` 這組不同符號,兩者對應關係論文沒有交代清楚。

**Grid Planning**:在一輪全新線上探索開始前,還有一個更早的決策——要開幾條root分支(width)、每條分支最多延伸幾層(depth)。這由獨立的 `plan_grid()` 方法負責,一樣不能偷看這一輪還沒發生的結果,只能根據過去幾輪的history決定。判斷規則:很多方向早期有起色但深入後停滯→加width;高分要refine很多層才出現且集中少數方向→加depth;都試夠深了還停滯但有未試過的方向類型→加width;反覆硬性失敗或方向高度重複→width、depth都保守縮小。

> Dream-RSI的自適應機制是分層的:最外層是grid(場地大小)、中間層是beta(玩法保守/積極)、最內層是逐輪的具體決策邏輯(prefix-only、batch portfolio、failure classification)。這個「把可調整的東西按時間尺度分層」的架構思路,即使脫離這篇論文,也是設計"要跨迭代自我調整"系統時可以參考的模式。

---

## 3. 實驗結果摘要

三個領域,略讀,重點抓「贏在哪個維度」:

| 領域 | 比較基準 | Dream-RSI贏在哪 | 品質本身有提升嗎 |
|---|---|---|---|
| 演算法工程(Lasso) | sklearn/glmnet/SimpleTES/Recursive Fixed Exploration | 同等或更好runtime,少很多discovery-agent calls(對SimpleTES少兩個數量級) | 有,三領域裡最明顯 |
| 數學優化(Sum-Diff/Autocorrelation/Circle Packing) | AlphaEvolve系列、SimpleTES等多個系統 | 遠少於SimpleTES的generation數(<1000 vs 51,200)達到相近分數 | 幾乎沒有——多數差距在小數點後三四位,Circle Packing甚至所有方法收斂到同一值 |
| GPU kernel(KernelBench 4個task) | Recursive Fixed Exploration | 同性能下少用generation(1.79x~2.43x),或同預算下性能更高(1.44x~2.09x) | 效率提升,非絕對性能突破 |

**具體圖表對照(供之後回頭查證)**:
- **Table(Figure 3a)**:「Final performance」——Lasso在六個held-out下游資料集上的最終wall-clock runtime比較,含sklearn、glmnet、SimpleTES、Recursive Fixed Exploration、Dream-RSI(不同backbone)
- **Figure 3(b)**:「Recursive Discovery Dynamics」——下游runtime隨累積discovery compute變化的軌跡圖,標出各個recursive round的位置
- **Table 1**:數學發現任務(Sum Diff數值越高越好、Auto Correlation越低越好、Circle Packing越高越好)的多系統比較,最佳結果加粗
- **Figure 4**:GPU kernel四個任務(VGG16, LayerNorm, ConvDiv, ConvMax)的performance vs generation數曲線
- **Figure 5**:history當replay simulator vs 當純prompt guidance的消融比較(ConvDiv任務)
- **Figure 6**:探索行為隨recursive round演化——(a)每輪最佳表現,(b)每輪評估的嘗試數

**§5.1消融實驗(全篇最有方法論價值的部分)**:對照「歷史當replay simulator主動測試」vs「歷史只摘要成文字提示塞進prompt」,結果兩種paradigm(Dream-RSI和Recursive Fixed Exploration)加了文字提示都表現更差——論文解讀是長時間、多線並行探索裡,把方向性建議寫死在prompt裡會過度限縮搜尋空間、抑制探索多樣性。這個結果值得注意的地方:它跟同樣處理「經驗記憶」問題的 ReasoningBank、WikiSkill 那類「把經驗摘要成文字知識再注入」的路線形成對比——至少在探索策略這個場景下,證據指向"結構化、可執行的重播"優於"文字摘要式提示",但這只是一組場景下的消融結果,不能直接推論成"摘要式記憶方法整體不如結構化重播"。

**沒有列進上面表格的具體caveat(inline,不做成瑕疵總表)**:
- Table 1把Gemini-2.0、Qwen3-8B、GPT-OSS-120B、Gemini-3.0-Pro、Gemini-3.1-Pro全部放在同一張表比分數,模型能力本身是個大變因,不是乾淨對照
- Autocorrelation上SimpleTES的分數其實比Dream-RSI好(1.453675 < 1.456375,越低越好),論文自己承認這點
- Figure 4只有圖沒有表,具體數字沒法回頭核對
- 整套自適應機制(beta schedule、grid planning、batch portfolio)綁在一起驗證,沒有個別消融

---

## 4. Dreamer 的 World Model 到底是什麼

**先鋪RL基礎**:Reinforcement Learning的基本迴圈——agent不斷「觀察狀態(state) → 選動作(action) → 環境給回饋(reward+新狀態) → 迴圈」。目標是學出一個policy:看到什麼狀態該採取什麼動作,讓長期累積reward最大。

**兩條路線分岔**:

**Model-free(無模型)**:agent完全靠實際跟環境互動、試錯,慢慢學"在這個狀態採取這個動作長期而言好不好",不去學"環境本身怎麼運作"。類比:學騎腳踏車靠肌肉記憶,不需要懂牛頓力學。

**Model-based(有模型)——world model的位置**:agent額外學一個"環境動態模型":輸入"目前狀態+動作",輸出"下一個狀態+reward"。這個模型就是world model。有了它,不用真的跟環境互動,只要不斷問模型"如果我這樣做接下來會怎樣",就能在模型內部一路模擬。類比:西洋棋高手腦中推演接下來五步棋,靠的是對"棋怎麼走"這個規則的理解模型。

**為什麼有價值**:真實環境互動往往慢、貴、有風險。有了夠準的world model,可以在模型裡用標準RL方法(policy gradient/actor-critic)大量便宜地"練習",因為每步是模型的一次前向運算,不是真的執行動作。這是model-based RL樣本效率通常比model-free高的根本原因。

**關鍵前提**:world model要有用,必須能泛化到"還沒真的走過的狀態/動作組合",不然只能在模型裡重演已發生的事,沒有意義。

**Dreamer具體怎麼做**:

1. **先壓縮成潛在狀態**:面對高維度輸入(遊戲畫面),不直接在pixel空間預測,而是訓練一個encoder把每幀壓縮成低維抽象向量z(latent state),隱含編碼了對決策有用的精華資訊
2. **在壓縮空間裡學動態模型**:學一個函數"目前z+動作a → 預測下一個z'+reward",這個函數(常叫RSSM, Recurrent State-Space Model)就是world model的核心,用真實互動收集的資料訓練
3. **Dreaming = 完全在latent空間滾動未來**:從某個z開始,重複"用policy決定動作a → 用動態模型預測z' → 再決定下一動作",滾出一整條"想像出來的未來軌跡"——完全不碰真正環境,也不解碼回真實畫面

```
真實環境互動 -> 收集(畫面,動作,reward)資料
            -> 訓練encoder+動態模型(world model)
            -> 從任意起點在latent空間"想像"很多條未來軌跡(dreaming)
            -> 用這些想像軌跡訓練/改進policy
            -> 部署改進後的policy到真實環境,收集新資料
            -> 迴圈回到最上面
```

**為什麼能泛化**:動態模型是神經網路,本質是學到一個連續函數,對"沒有一模一樣見過但相似"的z和a組合通常也能給出合理預測——這是"generalize到沒見過狀態"的能力。

**這正是Dream-RSI跟真正world model的落差所在**:Dream-RSI的discovery tree replay是把已發生節點原封不動存起來重播,沒有任何函數在做泛化或內插——如果某分支從沒被探索過,replay就是空的,不會有任何預測值可以評估。用「World Model」這個詞來包裝Dream-RSI,有一定程度的過譽。

**判斷力遷移**:之後看到任何論文說自己用了"simulator"、"world model"、"imagination"這類詞,第一個該問的問題是——**它能不能評估從沒發生過的可能性?** 能,才是真正的模型;不能,就是重播機制,價值仍然存在,但上限被"已經發生過的事"鎖死。

---

## 5. 為什麼不能每一步都用 World Model 搜尋?(Planning vs Policy Learning)

一個自然的疑問是:如果已經有一個能泛化的world model,為什麼不在每個state直接試各種action、選reward最大的,每步都這樣,不就能找到reward最大的trajectory?

這個做法真實存在,叫 **Planning**,具體技術如 **MPC(Model Predictive Control)** 或 **CEM(Cross-Entropy Method)**:每個timestep用world model對好幾種action序列做前向模擬,選累積reward最高的那串,執行第一步,下個timestep重新再搜一次。Dreamer的前身PlaNet論文,就是用CEM這種方式直接在latent space裡規劃,沒有另外學一個policy。Dreamer後來改成學policy,是有具體理由的:

**問題一:連續動作空間裡,不存在"試過所有action"**。Dreamer鎖定的場景(機器人控制、Atari連續操作)裡action常是連續值,頂多能取樣幾十幾百個候選,已經不是"找到最優解",是"用取樣逼近"。

**問題二:搜尋計算量隨horizon指數爆炸**。假設每步試10種動作(離散化近似),規劃未來15步:10^15種組合——這是每個真實timestep都要重算一次的量,即時反應場景完全不可行。(MCTS用啟發式剪掉大部分無意義分支,但即使加了剪枝,計算量還是比"訓練好policy網路、決策時只做一次前向運算"貴很多)

**問題三:往遠處規劃,model的預測誤差會累積放大**。規劃15步,代表拿"第1步已有誤差的預測"去餵給模型算第2步、再拿誤差更大的結果算第3步……誤差一路放大,搜得越深反而越可能被逐漸失真的模型誤導。

**Dreamer的解法:把搜尋成本攤還到訓練階段**。訓練一個policy+一個value function,兩者都用大量想像軌跡去訓練。訓練時想像的軌跡不用很長,因為value function本身承擔"這條路後面大概還有多少價值"的估計工作(bootstrapping技巧,不用真的模擬到最後才知道好不好)。訓練好之後,真正部署時決策只是把目前z丟進policy網路做一次前向運算——不用在真實世界每個timestep都重新搜尋。搜尋成本被搬到背景訓練階段,決策當下變得便宜。

**可遷移的比較表**:

```
做法                            | 決策時怎麼選action              | 優點                                | 缺點                                | 代表方法
Planning                       | 每步用model重新搜尋/模擬        | 不需另外學policy,更"誠實"利用model | 連續動作空間搜不動、決策計算量大、長horizon誤差累積 | PlaNet, MPC, CEM
Policy Learning in Imagination | 決策時只做一次policy前向運算    | 決策當下便宜,value function用bootstrapping處理長期回報 | policy品質受限於world model準不準;多一組要訓練的網路 | Dreamer(v1~v4)
兩者混合                        | 用policy/value當先驗縮小搜尋範圍,再做較淺搜尋 | 結合兩邊優點,搜尋有引導不會亂槍打鳥 | 系統複雜度最高                      | MuZero、AlphaZero
```

**可遷移的判斷規則**:動作空間小/離散、單步model算得快、能接受決策時多花點運算(回合制棋類遊戲)→傾向純planning/混合法;動作空間連續、需即時反應、horizon很長→傾向像Dreamer把搜尋成本攤還到訓練期。

---

## 6. 累積歷史會不會讓 Context 爆炸?(論文沒處理的洞)

Appendix B.1的探索prompt明文要求:agent提出新方案前,必須讀完每一個sibling attempt底下的proposal.md、以及`$history_dir`(對應正文完整歷史H_{t-1})裡的每一筆紀錄,特別強調"不是抽樣、不是只看最近幾輪、不是只看目前這條分支"。

**具體算一次規模**(用論文Table(Figure 3a)報的數字):Gemini-3.7-Flash在Lasso任務,每輪線上探索是32個平行workspace × 最多20步refinement = 640次discovery-agent calls,總共跑5輪,Dream-RSI累積用了1879次calls。

問題在於H_{t-1}是累積的——第5輪開始時,H_4裡已經裝了前4輪全部產生的節點(可能上千個proposal.md)。如果第5輪任何一次新嘗試都要把這上千份proposal全部讀過一遍才能動筆,那:

- 每次API call的context長度會隨輪數增加而線性成長(甚至更快,因為同輪內sibling節點也要互讀)
- 越後面的輪次,每次call的成本跟延遲都越來越貴

但論文用來衡量效率的指標全程只用「discovery-agent calls的次數」當cost(§4.1開頭就這樣定義),完全沒算進"每次call本身因context變長而變貴"這件事。**全文沒有看到任何關於context管理、摘要、檢索式讀取、或設定讀取上限的機制**——這是論文完全沒討論到的空白,不是含糊帶過。

**推論(明確標註,論文沒這樣說)**:可能的原因是論文用的Gemini系列模型context window本來就很大(百萬token等級),加上實驗規模(幾百到不到兩千次calls,單份proposal應該不會太長)可能還沒真的把這個問題逼出來,所以報告的實驗裡沒爆掉。但這不代表機制本身沒有這個上限——輪數拉更長、或換context window較小的模型,這個"讀全部歷史"策略遲早會撞到牆。

**更通用的問題**:agent要不要把全部歷史塞進context,還是改用檢索式(只挑相關的)、摘要式(先壓縮再放進去)、或分層式(wiki式、分級管理)的記憶機制——這是任何長期運作agent系統都要面對的設計選擇,論文自己在Related Work裡都引用了ReasoningBank這類做法,卻沒有把同樣的顧慮套用在自己exploration prompt的歷史讀取設計上,是一個值得留意的不一致。

---

## 7. Replay 到底在 Replay 什麼?(policy vs task solution的區分)

容易混淆的地方:「在一個節點上,policy不可能採取不同的action」——這個直覺是對的,但要弄清楚"action"指的是什麼。

**「action」不是指"在某節點v上決定生出什麼內容"**——這件事是凍結的,v的小孩內容早在真實線上探索時生成好、存進樹裡了,replay不會重新生成。

**真正的「action」是每輪決策時,policy從A(T)裡選哪些節點放進批次C**——選誰、選幾個一起、什麼順序、什麼時候選空批次收手,這是唯一會變動、不同policy間真正不一樣的地方。

**白話**:樹的"內容"是死的(誰的小孩是誰、分數多少全部固定),但"你打算怎麼逛這棵樹"是活的——這才是policy在做的事。

**兩種容易混淆的程式碼,一定要分清楚**:

| | 是什麼 | 由誰產生 | 由哪份prompt指導 | 作用範疇 |
|---|---|---|---|---|
| Exploration policy | 決定怎麼逛discovery tree的程式碼(`OptimalPolicy.solve()`) | policy-development agent(LLM) | B.2 replay改良prompt | RSI迴圈層級——管理要不要開新分支、批次多大、何時停 |
| Task solution(例如論文Appendix C的Lasso solver) | discovery tree上某一個節點裡真正的候選解內容 | discovery agent(真正解題的coding agent) | B.1探索prompt | 單一節點層級——這次嘗試具體生出了什麼 |

論文Appendix C展示的Lasso solver程式碼,是整個Dream-RSI跑完後discovery tree裡分數最高那個節點的內容,跟"探索策略"完全無關,是任務本身的答案,不是"怎麼逛樹"的邏輯。

**對照兩個不同policy重播同一棵樹,看差異在哪**(沿用第2.3節那棵樹):

Policy A(保守、深度優先、從不批次):3輪揭露v1、v1a、v1a1,最佳分數0.58,全程沒用平行度。
Policy B(積極、會批次、廣度優先):3輪揭露全部5個節點,最佳分數0.60,每輪都用滿平行度。

**沒有任何一步是重新生成內容**——B揭露出的v2、v1a、v2a、v1a1,內容跟A如果也選到同樣節點揭露出來的,會是一模一樣的(都是讀同一份存好的紀錄)。差別純粹在"選誰、順序、批次大小、何時停"這個決策層面。

**這樣做的好處**:如果A、B各在真實世界跑一次線上探索,要花真的兩次昂貴的coding agent生成+evaluator評分(可能上百次API call、真的跑程式碼)。但拿同一棵已存在的樹比較A跟B誰的"逛法"有效率,兩次replay加起來可能幾毫秒就跑完——只是在讀記憶體裡的樹結構。這讓你可以便宜地測試成千上萬種"逛法策略",篩出效率最好的,再只把最終選出的那一個真的拿去線上部署。

**哪些policy會被拿去replay**:在第t輪offline階段,先用目前正在用的policy π_t當π^0_t,replay一次拿到基準分數。接著policy-development agent看這次replay表現細節,改寫程式碼,產生π^1_t,一樣replay評分。重複M次,從π^0_t~π^{M-1}_t裡挑replay分數最高的,變成下一輪部署的π_{t+1}。

**不是只在一棵樹上跑**:每個候選policy版本是分別在歷史裡每一棵樹T_1,...,T_t上各自獨立跑一次replay,拿到t個分數再平均,才是這個policy版本的最終評估分數(對應第2.4節的公式)。如果只在一棵樹評分,選出的policy可能只是恰好很適合那棵樹的特殊結構,換一棵就不管用了。

---

## 8. Replay-to-Real Gap 的兩個獨立來源

Dream-RSI的保底機制(第2.5節)只保證"replay分數不退步",不代表"真實線上表現也不退步"——這個落差有兩個**各自獨立、不是因果關係**的來源,容易被混成一件事,拆開來看更精確:

**來源一:beta(β1/β2)設定不一定反映真實在乎的東西**。就算replay能看到宇宙裡每一種可能走法,如果β1設太大(過度懲罰成本),被選出的policy還是會被推向"揭露越少越好"的保守方向,即使這在真實世界其實是次佳選擇。這個gap來自"這個分數公式測量的東西,是不是真的等於我們在乎的東西",跟樹涵不涵蓋歷史無關。

**來源二:replay情境都是歷史情境,不是真實環境**。就算β調到完美,replay依然只能在"已經被走過的分支"裡選,沒辦法評估任何沒被探索過的可能性。這個gap不會消失,因為它跟beta準不準完全無關,純粹來自"這個模擬器的世界有多大"。

**思考實驗驗證兩者獨立**:假設beta調到完美但樹還是歷史樹——gap依然存在(來自來源二)。反過來假設樹能涵蓋所有可能分支(理想化)但beta沒調好——gap仍存在(來自來源一)。兩個假設情境裡,拿掉一個變因,另一個gap都不會消失,證明兩者是平行存在、互不影響的問題。

**論文對兩者的處理程度不同**:
- 針對"beta沒設對":論文有嘗試補救——Appendix B.2設計了beta sweep+adaptive default beta規則,用上一輪真實線上表現回頭校正下一輪要用的β預設值,某種程度是拿真實回饋去修正objective function本身
- 針對"replay只能看歷史":論文沒有特別的補救機制,唯一能讓這個gap縮小的方式是靠RSI大迴圈本身——每跑一輪線上探索就多存一棵樹進歷史庫,模擬器能重播的世界會越滾越大,但這只能事後擴大"已知的世界",沒辦法解決"這一輪決策當下,模擬器看不到還沒發生的可能性"這個當下限制

這個拆解本身是個可遷移的判斷框架:任何"用歷史資料做off-policy評估"的系統,都可以問自己這兩個問題——(1)評分公式測的東西,是不是真的等於我在乎的東西?(2)歷史資料涵蓋的範圍,是不是真的接近我要決策的真實情境?兩個問題的答案分別對應不同的補救方式,不能混為一談用同一套方法解決。

---

## 9. Failure Classification 框架,及其在 Agent Tool-Calling 設計上的應用

### 9.1 論文用到的框架

B.2 prompt要求policy-development agent把失敗分類邏輯寫進探索策略程式碼裡:

```
hard-unrecoverable          = 硬性、不可能修好的失敗
repairable implementation failure = 想法本身可能沒問題,是實作上的bug
weak-but-underexplored      = 分數普通,但還沒試夠深,不能太早下定論
repeatedly unpromising      = 已有足夠證據(嘗試夠多次)顯示這方向真的不行
```

**哪些錯誤"通常"算可修復**:output/correctness mismatch(輸出對不上)、shared-memory/resource limits(資源超限)、variable/code錯誤、mask/layout/shape錯誤。明確警告:不能因為看到"compile_other"這種泛用錯誤標籤就直接判定永久沒救——這只是一次性編譯問題標籤,不代表方向本身有問題。

**一個容易誤判的細節**:`valid==False` 不等於"失敗"。一次嘗試可能程式碼順利跑完、沒有拋出任何錯誤(`fail_class=="ok"`, `error is None`),但產出的解不滿足正確性條件——這種情況不算"失敗",是正常評估出一個較弱的解,不該被塞進"可修復失敗"這個籃子重試,因為根本沒有東西可修。

**分類不是永久性判決**:即使一條分支被判定hard-unrecoverable或repeatedly unpromising,只要之後真的出現一次成功結果,就要重新打開這條分支的可能性,不能因早期失敗紀錄就永久鎖死。

### 9.2 這套框架的更大脈絡:Transient vs Permanent(分散式系統的經典二分法)

這個問題最早、最系統化被討論的地方是**分散式系統/雲端服務**領域(這是這個詞彙的原生領域,不是AI領域的通用術語)。

```
Transient(暫時性失敗):
  - 網路連線短暫斷掉、伺服器暫時過載、request timeout
  - 特徵:"再試一次"很有可能就成功,錯誤跟"這個request本身有沒有問題"無關
  - 例子:HTTP 503(伺服器忙碌)、網路封包遺失

Permanent(永久性失敗):
  - request本身就是錯的、格式不對、權限不足、資源真的不存在
  - 特徵:"再試一百次"結果都一樣,問題不在運氣,在"這個request的內容"
  - 例子:HTTP 404(資源不存在)、HTTP 401(沒有權限)
```

實務上最常見的判斷方式是看HTTP狀態碼分類:5xx(伺服器端問題)通常當transient,值得重試;4xx(客戶端請求本身的問題)通常當permanent,重試沒有意義。

**配套的重試技巧**:
```
Exponential Backoff(指數退避):第一次失敗等1秒再試,第二次等2秒,第三次等4秒...
  -> 避免"伺服器剛過載,你還馬上再打一次",反而讓過載更嚴重

Jitter(抖動):backoff等待時間加一點隨機擾動
  -> 避免"1000個client同時失敗、然後完全同時重試"造成新一波集體過載
     (這個問題有個名字叫thundering herd)

Circuit Breaker(斷路器):同一個對象連續失敗太多次,直接"跳開"暫停一段時間不再嘗試
  -> 對應Dream-RSI的"repeatedly unpromising"分類:
     累積夠多失敗證據後,先不要再浪費資源在這個方向
```

### 9.3 AI/Agent場景多出來的第三種情況

傳統transient/permanent二分法預設"重試的結果不會因為多試幾次而累積出新資訊"——網路斷線重試10次,不會因此更了解這條網路線。但在Dream-RSI這種生成式、探索式的場景裡,還有第三種狀態(這是推論,不是論文或業界標準術語,是觀察歸納出來的):

```
"證據還不夠"(weak-but-underexplored):
  - 不是"暫時性錯誤"(沒有壞掉、只是分數普通)
  - 也不是"永久性失敗"(沒有證據說這條路走不通)
  - 而是"樣本數太少,還沒累積足夠證據下判斷"
  -> 更接近統計裡"假設檢定樣本不足",不是傳統retry邏輯裡的"錯誤類型"
```

Dream-RSI在這塊的設計,其實是把兩個不同領域的邏輯疊在一起:失敗有沒有bug(工程/分散式系統的retry邏輯)+這個方向值不值得繼續投入(比較接近科學實驗裡的證據累積邏輯)。

**可遷移的決策表**:

```
情境特徵                                          | 屬於哪類            | 該怎麼處理
失敗跟"這次運氣"有關,重試內容不變也可能成功         | Transient          | 直接重試,搭配exponential backoff
失敗是"request/方向的內容"本身有問題,重試不變結果不變 | Permanent           | 不重試,直接放棄或改變輸入內容
沒有失敗,但結果不夠好,且嘗試次數還很少             | 證據不足            | 不是重試同一件事,用不同方式/角度再探索深一點
同一類失敗已經反覆出現很多次                        | 該用Circuit Breaker | 暫停繼續投入這個方向,把資源挪去別處
```

**可遷移的判斷規則**:設計任何"自動決定要不要重試/繼續投入"的系統,先問(1)這次負面結果跟"執行過程"有關還是跟"這件事本身"有關(對應transient vs permanent);(2)如果是"這件事本身"的問題,現在手上的證據量足夠下這個結論嗎(對應要不要先歸類到"證據不足"而非直接判死刑)。這兩個問題分開問,比只用一個籠統的"失敗/成功"二分法,能避免"太早放棄有潛力的方向"跟"死纏爛打浪費資源在沒救的方向"這兩種常見錯誤。

### 9.4 應用到 Agent Tool-Calling 錯誤處理的設計

Tool call的"重試"跟網路請求的"重試"不完全一樣——傳統分散式系統裡"重試"通常是"送一模一樣的request再試一次",但agent的tool call是**LLM生出來的**,代表除了"要不要重試"這個選項,還有更豐富的光譜:

```
1. 原封不動重試(只對真正的transient錯誤有意義)
2. 修正參數後重試(工具本身沒問題,是LLM填錯參數)
3. 換一個工具/換個做法(這個方向本身可能就不對)
4. 放棄、上報給使用者(重複失敗、判斷該停損了)
```

**建議的分工:哪些該讓harness(程式邏輯)直接處理,哪些該丟給LLM判斷**:

```
Harness層(結構性、不需要LLM判斷,自動處理):
  - Rate limit(429)、伺服器暫時不可用(503/timeout)
    -> 自動retry+exponential backoff,LLM甚至不需要知道發生過這件事
       (除非重試次數用完,才把"這個工具目前不可用"回報給LLM)
  - Schema驗證錯誤(缺必填欄位、型別不對)
    -> 送出前就能被harness擋下並直接要求LLM重新生成參數,
       不用真的打API才發現

LLM判斷層(需要理解語意,harness沒辦法用規則寫死):
  - "這個參數邏輯上錯了"(不是格式錯,是語意錯)
  - "這個工具用起來一直失敗,是不是該換個工具/換個做法"
  - "這個方向嘗試了幾次都拿不到有用結果,是不是該放棄改問使用者"
```

**System prompt該給"判斷原則",不是窮舉式的錯誤碼對照表**:真實世界的工具錯誤訊息五花八門,不可能窮舉完。更穩健的做法(借鏡B.2 prompt的寫法——它給的是判斷原則加舉例特徵,不是逐字比對表)是:

```
system prompt裡放判斷原則,例如:
  "如果錯誤訊息顯示是參數/格式問題,先嘗試修正參數重試一次;
   如果連續兩次修正後仍失敗,考慮這個工具本身是否適用,
   或改用其他工具/回報使用者"

同時harness要確保:
  真正呼叫LLM判斷時,一定要把"實際的原始錯誤訊息"帶進context,
  不要只給LLM一個抽象的"失敗了"——LLM才有東西可以推理
```

**具體場景走一次**:

```
情境:agent呼叫內部API查詢客戶資料,回傳400 Bad Request,
     訊息是"invalid date format, expected YYYY-MM-DD"

Harness層先判斷:
  -> 400不是rate limit/timeout,不屬於"自動retry"範疇
  -> 錯誤訊息看起來是"參數格式問題",不是"工具本身不可用"
  -> 把這個具體錯誤訊息(連同"這是第幾次嘗試")丟回給LLM

LLM看到後(system prompt給的是判斷原則,不是逐條規則):
  -> 讀懂"date format錯了",判斷屬於"參數層級可修復",
     修正日期格式重新呼叫

如果同一個tool連續3次都失敗(不管修正幾次參數):
  -> 觸發"circuit breaker"式的原則:
     不要無限重試,改成"跟使用者確認"或"換一個資料來源"
```

**副作用**:如果每次tool call失敗都貼上結構化標籤(transient/repairable-with-correction/needs-different-approach/circuit-broken),這些標籤本身之後也能變成很好的trace分析素材——回頭看一段agent執行紀錄時,能快速篩出"這次失敗是工具不穩定"還是"agent自己判斷力有問題",不用每次都重新肉眼讀log。

---

## 10. 值得帶走的東西

### 10.1 這篇論文本身的貢獻

**核心貢獻**:把「已完成的探索歷史」重新框架成一個可以拿來做off-policy評估的資料結構(discovery tree),用來低成本篩選exploration policy的改良版本,取代昂貴的線上試錯。這個工程巧思是真實的,§5.1的消融實驗也確實證明它比單純把歷史摘要成文字提示更有效。

**但貢獻的份量,誠實講不多**:
- 品質提升幾乎不存在(數學優化任務多數差距在小數點後三四位,Circle Packing甚至完全打平);真正貢獻集中在"用更少運算資源達到同等品質",是效率貢獻,不是能力突破
- "World Model"這個框架包裝,跟真正的world model(能泛化到沒見過狀態)有實質落差——它更準確的定位是一套精緻的off-policy replay評估機制
- 整套自適應機制(beta schedule、grid planning、batch portfolio)是綁在一起驗證的,沒有個別消融,不知道拆開哪一塊會掉多少分
- 論文正文的β1/β2公式跟Appendix實作的beta/pareto.auc/lambda,對應關係沒交代清楚

**一句話總結**:工程紮實、包裝過譽,是個值得學的技巧,不是典範轉移。

### 10.2 脫離這篇論文也成立的東西(這是這份筆記真正的重點)

**辨識"假的world model"的能力**:真正的world model是一個訓練出來、能對沒見過狀態做泛化預測的函數;單純把歷史紀錄存起來原封重播,是log replay/off-policy evaluation,不是world model。之後看到任何論文說自己用了simulator、world model、imagination這類詞,先問它能不能評估從沒發生過的可能性——能才是真正的模型,不能就是重播機制,價值仍在,但上限被"已經發生過的事"鎖死(完整推導見第4節)。

**Planning vs Policy Learning的分岔,和背後的成本轉嫁邏輯**:與其每次決策都用world model現場搜尋(連續動作空間會撞到指數爆炸和誤差累積),不如把搜尋成本攤還到訓練期,訓練出policy+value function,決策時只做一次便宜的前向運算。這個"把貴的運算搬到背景、讓即時決策變便宜"的思路是通用的系統設計原則,不限於RL(完整推導見第5節)。

**Replay-to-real gap是兩個獨立的問題,不是一件事**:(a)評分公式的權重有沒有反映真實在乎的東西,和(b)模擬環境本身能不能涵蓋所有可能性,是兩個各自獨立、互不影響的gap來源,需要分開診斷、分開補救,不能混為一談用同一套方法解決(完整推導見第8節)。

**Monotonic non-regression的保底設計模式**:候選集裡永遠保留"不改"的原始版本,用客觀分數選最好的一個,保證自我改良系統不會因為亂改而變差。任何"LLM自己改自己邏輯"的系統都可以檢查有沒有做這個保底,這是判斷一個自我改良機制穩不穩健的簡單指標。

**Prefix-only / causality constraint**:離線評估一個序列決策系統時,只能用"當下已經揭露的資訊"做判斷,不能偷看未來或全局——這是RL off-policy evaluation和online algorithms領域的標準要求,不是Dream-RSI獨創。設計任何"用歷史資料離線評估一個線上決策系統"的機制時,都要檢查有沒有守住這條線。

**Batch portfolio設計(exploitation/exploration/recovery)**:本質是multi-armed bandit的explore-exploit tradeoff,但因為場景是生成式/coding agent,多了傳統bandit沒有的第三角色——recovery,因為這裡的"失敗"可能只是實作bug,不代表方向本身壞掉。任何需要在多個候選方向間分配有限資源的系統,都可以參考這個三分法。

**Failure classification框架**:Transient(值得retry) vs Permanent(retry無意義)是分散式系統/SRE領域的經典二分法(exponential backoff、jitter、circuit breaker是配套技巧);但生成式/探索式場景還有第三種狀態——"證據不足"(不是失敗,只是樣本數還太少,不能直接判死刑)。判斷規則:先問"這次負面結果跟執行過程有關、還是跟這件事本身有關",再問"如果是這件事本身的問題,證據夠不夠下結論"。這套框架直接可以應用到agent tool-calling的錯誤處理設計:結構性、可規則化的錯誤(rate limit、schema驗證)交給harness自動處理,不需要LLM介入;需要語意判斷的錯誤(參數邏輯錯、要不要換工具)才丟給LLM,而且system prompt該給"判斷原則"而不是窮舉式的錯誤碼對照表,同時要確保原始錯誤訊息真的被帶進context讓LLM有東西可推理(完整推導與具體場景見第9節)。

---

*筆記完*