# Dream-RSI:把探索歷史當成免費模擬器,用重播取代真實試錯

## 前言

如果你寫過會自己迭代改善的 agent 系統,大概踩過這個問題:改善邏輯本身也該被改善,但要知道「這次改的版本比較好」,通常得先真的花錢跑一整輪才知道。Dream-RSI(Tong Zheng 等人,Google 與 University of Maryland、Google DeepMind、University of Virginia 合作)想解決的正是這件事——當 AI agent 被用來做科學或演算法發現(想想 AlphaEvolve 那類系統)時,負責決定「往哪個方向深挖、什麼時候平行展開、什麼時候該停手」的探索策略,能不能低成本地自我改良。

論文的解法很直接:把已經跑完的探索歷史直接當成一個可以重播的資料庫。想測試一個新策略好不好,不用真的重跑任何程式碼,讓新策略去讀歷史紀錄裡「換一種走法會揭露哪些節點」,就能算出一個分數,近乎免費地篩選成千上萬個候選版本。這個機制確實聰明,論文自己的消融實驗也證明它比另一種常見做法(把歷史寫成文字摘要塞進 prompt)更有效。但論文把自己包裝成用了「World Model」,這個說法跟它實際在做的事有一段值得拆開來看的落差。這篇文章除了介紹方法本身,也會花一些篇幅講清楚這個落差,以及幾個就算脫離這篇論文也用得上的設計心法。

## 探索策略卡在哪裡

用 AI agent 做科學或演算法發現時,整個流程是「提出候選解 → 執行評估 → 依回饋修正 → 再提出」不斷循環,任務一難,這個循環可能要跑到數千次。誰來決定循環怎麼安排——往哪個方向深挖、哪些候選要平行展開、什麼時候換方向——本身就決定了效率高低,論文把這個決策者稱為 **exploration policy(探索策略)**。

現有做法大多是人工寫死一套規則,整個發現過程不會變,容易一直把資源砸在早就證明沒用的方向上。讓策略自己上線學習聽起來是解法,但會卡在兩個瓶頸上:評估「一個候選解好不好」可以很快,評估「一個探索策略好不好」卻沒辦法這麼快,得讓它實際指揮完一整輪(可能上百上千次)發現循環才知道效果;而且候選策略空間很大,新版本表現可能很差,得試很多版本才找得到好的。兩者疊加,每個候選策略都要跑一次完整、昂貴的線上探索才能拿到回饋,策略的持續改良自然變得又慢又貴。

## 核心想法:把探索歷史變成可重播的模擬器

Dream-RSI 的關鍵觀察是:每一次線上探索的過程,本來就已經把「在哪個節點分支、產生什麼結果、分數多少」全部記錄成一棵樹了。理論上,評估「換一種走法結果會不會不一樣」只需要讀這棵樹裡的紀錄,不需要真的重新執行程式碼。

系統在「線上探索」跟「離線做夢」之間交替,分成三個階段:

![Dream-RSI 的三階段迴圈示意圖:線上探索、建構重播模擬器、做夢式策略改良,三者依序循環。](img-001)
*圖 1 — Dream-RSI 的遞迴自我改良迴圈。目前的探索策略先指揮 coding agent 展開真實探索並記錄歷史軌跡;歷史被轉換成可重複使用的模擬器;agent 接著在模擬器裡「做夢」出大量候選策略、快速評分,挑出最好的重新部署。(來源:原始論文。)*

第一階段(Online Explore)用目前的探索策略指揮一個 coding agent 跑真實的發現循環,把每次嘗試記錄成一棵 discovery tree。第二階段(Construct Replay Simulator)把這棵樹收進歷史庫,庫會越滾越大。第三階段(Dreaming-based Policy Improvement)在歷史庫裡想像出大量候選策略,把每個候選策略拿去重播已存的樹算出分數,挑出表現最好的版本,變成下一輪真的要部署的策略。整個迴圈跑完後回到第一階段,用改良後的策略開始新一輪。

值得注意的是,只有探索策略的程式碼在變動——底層真的解題的 coding agent、負責評分的 evaluator、執行介面全部固定不動。這種「凍結大部分元件、只讓一個小的可控部分自我改良」的設計思路,即使脫離這篇論文,也是拆解「自我改良系統」時值得留意的切入點。

## Discovery Tree:一份可以重播、但不能改寫的歷史

discovery tree 裡的每個節點代表一次「生成—評估」嘗試,節點存的不只是分數,還包含檔案系統快照、產生的成果、評估診斷資訊,是一次嘗試完整、可事後重看的紀錄。任何時刻,「可以繼續往下接」的節點只有兩種:根節點(開一條全新分支)或現有葉節點(延續某條已在走的分支)。

![一棵標示節點分數與父子關係的 discovery tree,搭配一個可重播它、產生不同展開順序的替代探索策略。](img-002)
*圖 2 — 一次線上探索留下的完整歷史,可以被另一個探索策略拿去重播。(來源:原始論文。)*

線上跟離線用的是同一套「選節點、湊批次」規則,但運作邏輯完全不同。**Online rollout** 是真的在跑,而且是隨機的:coding agent 現場生成候選解、evaluator 現場評分,同樣的起點,這次跑跟下次跑結果可能不一樣。**Offline replay** 則是決定性的重播:選到根節點時,一定回傳歷史裡「最早被創造出來、還沒揭露」的那個小孩,順序完全鎖死;選到已展開的節點時,直接回傳歷史裡存好的那個小孩。換句話說,replay 從來不重新生成任何內容,樹的內容是死的,活的只有「你打算怎麼逛這棵樹」——這正是不同探索策略之間唯一會變動的地方。

這也帶出一個直接讀自形式化定義的限制:replay 沒辦法測試「如果當初先開另一條分支會怎樣」,因為根節點小孩的揭露順序照原始創造順序鎖死,那條沒被走過的路徑在 replay 裡完全不可能被還原出來評估。

## 怎麼避免「贏家永遠是把樹逛光的那個」

光看 replay 揭露出來的最高分還不夠——只要把整棵樹逛光,一定能拿到這棵樹的全域最佳分,這樣量不出「有效率地找到好結果」跟「暴力逛完」的差別。論文的 replay 分數因此由三項組成:揭露節點裡的最高分(quality),扣掉揭露節點數乘上一個係數(cost,揭露越多扣越多),再加上平均每輪揭露節點數乘上另一個係數(parallelism bonus,獎勵懂得批次處理的策略)。

一個具體例子最能說明這個設計的用意。假設同一棵樹上有兩種策略:

| | 揭露節點數 | 最高分 | 平行度 |
|---|---|---|---|
| 策略 A(保守、序列式) | 3 個 | 0.58 | 每輪只選 1 個 |
| 策略 B(積極、有批次) | 5 個(全部) | 0.60 | 兩輪都選滿 2 個 |

策略 B 的最高分和平行度都比較高,但因為多揭露了兩個節點,cost 項扣得更多,最後算出來反而是保守的策略 A 分數更高。這正是這個分數公式的核心用意:不是單純找誰的分數最高,而是在「找多好」跟「花多少」之間權衡,天平完全由那兩個係數決定——論文並沒有在正文或附錄交代它們實際用的具體數值。而且候選策略的最終分數,是它在**所有**歷史樹上各自算出分數後取平均,不是只在一棵樹上評分,否則選出的策略可能只是剛好很適合那棵樹的特殊結構。

## 一個「不會變差」的保底機制

每一輪的策略改良流程是這樣的:先讓目前正在用的策略原封不動 replay 一次,拿到一個基準分數;接著讓一個負責改寫程式碼的 policy-development agent(本身也是一顆 LLM)讀這次的 replay 紀錄,改出新版本,一樣拿去 replay 評分;重複這個過程若干輪(次數由系統設定);最後從全部候選版本裡,挑 replay 分數最高的那個,變成下一輪真的要部署的策略。

候選版本裡永遠留著「完全不改」的原始版本,所以挑出來的分數絕不會比原本的差——最壞情況是這幾次改寫都沒改進,那就繼續用原本的,不會因為亂改而倒退。這個設計叫 **monotonic non-regression(單調不退步)**,是任何「LLM 自己改自己邏輯」的系統都可以拿來檢查的一個簡單健檢指標:有沒有在候選集裡保留一個「不改」的選項當底線。

不過這個保底只保證「replay 分數不退步」,不等於「真實線上表現也不退步」,這個落差留到後面「這真的是『World Model』嗎」那節細談。

## 三個實驗場域:省下來的是運算,不是品質

論文在三個領域測試 Dream-RSI:演算法工程(用 Lasso regularization path 當範例)、數學優化(Sum-Difference、Autocorrelation、Circle Packing 三個任務)、GPU kernel 工程(KernelBench 的四個任務)。三個場域有個共通的模式,值得先講在前面:Dream-RSI 贏的維度幾乎都是「用更少運算資源達到同等品質」,不是「品質本身有突破」。

演算法工程場域裡,Dream-RSI 在六個 held-out 下游任務上拿到跟 baseline 相近或更好的 wall-clock runtime,但用掉的 discovery-agent calls 少了一到兩個數量級:

![Lasso 任務的最終效能比較表,以及效能隨累積探索運算量變化的曲線圖。](img-003)
*圖 3 — Lasso regularization-path 的發現結果。(a) 六個 held-out 下游任務上的最終 wall-clock runtime,數值越低越好。(b) 效能隨累積 discovery-agent calls 增加而演化的軌跡。(來源:原始論文。)*

數學優化場域是三者裡「品質幾乎沒有提升」最明顯的一個:

![數學發現任務的多系統效能比較表,包含 Sum Diff、Autocorrelation、Circle Packing 三個指標。](img-004)
*表 1 — 數學發現任務上的效能比較。Sum Diff、Circle Packing 數值越高越好,Autocorrelation 越低越好,最佳結果以粗體標示。(來源:原始論文。)*

Dream-RSI 用遠少於 SimpleTES 的 generation 數(少於 1,000 次,對比 SimpleTES 的 51,200 次)就拿到相近的分數,但真正的分數差距大多落在小數點後三、四位,Circle Packing 上甚至所有方法都收斂到同一個值。誠實地說,Autocorrelation 上 SimpleTES 的分數其實比 Dream-RSI 好一點(1.453675 對比 1.456375,越低越好),論文自己也承認這一點。這張表也把 Gemini-2.0、Qwen3-8B、GPT-OSS-120B、Gemini-3.0/3.1-Pro 放在同一張表裡比分數,模型能力本身就是個變因,不算乾淨的對照。

GPU kernel 工程場域則是效率提升最直接可讀的一個:

![GPU kernel 四個任務(VGG16、LayerNorm、ConvDiv、ConvMax)上,效能隨 generation 數增加而演化的曲線。](img-005)
*圖 4 — GPU kernel 工程結果。在 VGG16 和 LayerNorm 上,Dream-RSI 用少 2.43 倍和 1.79 倍的 generation 數就達到相近效能;在 ConvDiv 和 ConvMax 上,同樣預算下效能高出 2.09 倍和 1.44 倍。(來源:原始論文。)*

把三個場域放在一起看,論文自己的效率指標藏著一個共通的盲點:附錄的探索 prompt 明文要求 coding agent 每次提案前,必須讀完每一個 sibling attempt 的內容、以及完整歷史裡的每一筆紀錄,不是抽樣、不是只看最近幾輪。這個盲點三個場域都適用,只是剛好 Lasso 任務是論文唯一報了具體 call 數的地方,可以抓來算一下規模:Gemini-3.7-Flash 在 Lasso 任務上,每輪線上探索是 32 個平行 workspace、每個最多跑 20 步 refinement,五輪下來累積用了 1,879 次 discovery-agent calls——而第五輪開始時,前四輪已經留下數千份紀錄要讀。輪數一拉長,理論上每次 API call 要讀的 context 只會越來越長、越來越貴,但論文全程用來衡量效率的指標只算「discovery-agent calls 的次數」,沒有算進這件事,全文也沒有看到任何摘要、檢索式讀取、或設定讀取上限的機制。可能的原因是論文用的 Gemini 系列模型 context window 本來就很大,加上實驗規模還沒真的把這個問題逼出來,但這不代表機制本身沒有這個上限——輪數拉更長,或換一個 context window 較小的模型,這個「讀全部歷史」的策略遲早會撞到牆。

## 消融實驗才是全篇最有方法論價值的部分

比起三個主實驗,論文 §5.1 的消融實驗更值得細看:對照「把歷史當成可互動的 replay simulator 主動測試」跟「把歷史只摘要成文字提示塞進 prompt 引導方向」,兩種 paradigm(Dream-RSI 跟另一個 baseline)只要加了文字提示,表現都變差。

![ConvDiv 任務上,使用歷史當互動式重播模擬器 vs. 只當文字引導的效能對照曲線。](img-006)
*圖 5 — ConvDiv 任務上的消融比較。把歷史當成互動式重播模擬器,表現優於只把它當成文字引導。(來源:原始論文。)*

論文的解讀是:長時間、多線並行的探索裡,把方向性建議寫死在 prompt 裡反而會過度限縮搜尋空間、抑制探索的多樣性。這個結果值得放進更大的脈絡看:同樣處理「怎麼利用過去經驗」這個問題,ReasoningBank、WikiSkill 那類方法走的是「把經驗摘要成文字知識再注入」的路線。這組消融結果指向的是「結構化、可執行的重播」在探索策略這個場景下優於「文字摘要式提示」,但這只是一組場景下的結果,不能直接推論成摘要式記憶方法整體不如結構化重播。

## 探索行為怎麼隨著輪次演化

另一個實驗接著追蹤:隨著遞迴輪次一輪一輪跑下去,學出來的探索策略本身行為怎麼變化。

![ConvDiv 任務上,每輪最佳表現與每輪評估嘗試數隨遞迴輪次演化的兩張圖。](img-007)
*圖 6 — ConvDiv 上探索行為的演化。(a) 各輪的最佳表現。(b) 各輪評估的嘗試數。(來源:原始論文。)*

論文觀察到一個清楚的自適應模式:早期表現還在快速進步時,策略傾向保守,把資源花在深挖少數幾條看起來有希望的分支;等表現逐漸逼近瓶頸、進步趨緩,策略反而轉為更積極地開新分支、擴大搜尋廣度。這個「早期收斂、後期發散」的行為不是寫死的規則,而是策略自己從歷史 replay 裡學出來的——某種程度上呼應了論文附錄裡 `plan_grid()` 那套根據歷史動態調整探索寬度、深度的邏輯。

## 這真的是「World Model」嗎

論文把整套機制類比成「World Model」,呼應 Dreamer 那類 model-based RL 系統。但這個類比值得拆開來檢查。

真正的 world model 是一個訓練出來的函數:輸入「目前狀態加動作」,輸出「下一個狀態加 reward」。以 Dreamer 為例,它先把高維輸入(例如遊戲畫面)壓縮成低維的潛在狀態,再學一個函數在這個壓縮空間裡預測下一步,整個「做夢」的過程完全在潛在空間裡滾動想像出的未來軌跡,不碰真實環境。這個機制之所以有價值,關鍵在於它能**泛化**到「還沒真的走過的狀態或動作組合」——不然就只能在模型裡重演已經發生過的事,沒有意義。

Dream-RSI 的「重播模擬器」不具備這個能力。它是把已發生的節點原封不動存起來重播,沒有任何函數在做泛化或內插;如果某條分支從沒被探索過,replay 對它就是空的,不會產生任何預測值可以評估。更準確的定位,它是一套精緻的 off-policy replay 評估機制,而不是能對未知狀態做預測的 world model。

這個落差可以變成一個可攜帶的判斷習慣:之後看到任何論文說自己用了「simulator」「world model」「imagination」這類詞,第一個該問的問題是——**它能不能評估從沒發生過的可能性?** 能,才是真正的模型;不能,就是重播機制,價值仍然存在,但上限被「已經發生過的事」鎖死。

這個落差也直接連到前面提過的保底機制:單調不退步保證的是「replay 分數不會退步」,但 replay-to-real gap 有兩個各自獨立的來源。第一個來源是 replay 分數公式本身的權重(cost 項、parallelism bonus 項的係數)設得對不對——就算 replay 能看到宇宙裡每一種可能走法,係數設錯,選出來的策略還是會被推向不是真正最佳的方向。第二個來源是 replay 情境終究是歷史情境,不是真實環境——就算係數調到完美,replay 依然只能在已經被走過的分支裡選,沒辦法評估任何沒被探索過的可能性,這個限制不會因為調參數而消失。論文對第一個來源有嘗試補救(附錄設計了根據上一輪真實表現回頭校正係數預設值的機制),但對第二個來源沒有特別的解法,只能靠 Dream-RSI 這整個大迴圈本身——每跑一輪就多存一棵樹進歷史庫,模擬器能重播的世界會越滾越大,但這只能事後擴大「已知的世界」,沒辦法解決「這一輪決策當下,模擬器看不到還沒發生的可能性」這個當下限制。

## 附錄裡藏的工程細節,比正文更值得學

論文附錄有一份大約 270 行的 prompt,指導負責改寫探索策略的 policy-development agent。這份 prompt 裡有幾個設計,拆開來看比論文正文的公式更有實用價值。

**Prefix-only 限制**:策略的每個決策,只能用「這次 replay 自己已經主動揭露過的節點」,不能用還沒揭露節點的分數或任何「上帝視角」資訊。這避免了作弊——先掃過整棵樹找最高分、假裝一路探索剛好找到——真實線上部署時沒有這種作弊空間,因為線上的樹根本還沒長出來。這種「決策只能用當下已知資訊,不能偷看未來或全局」的限制,在強化學習和 online algorithm 領域是標準要求,叫 **causality constraint**,不是 Dream-RSI 獨創的東西。任何「用歷史資料離線評估一個線上決策系統」的機制,都可以拿這條線去檢查有沒有守住。

**Batch 決策的三分法**:每輪最多選 W 個候選節點放進批次,prompt 要求拆成三種角色湊——exploitation(目前最有希望的正常延伸)、exploration(開新分支,或深入還沒探索夠的分支)、recovery(最多一個,一個真的可修復的失敗嘗試)。這本質上是經典的 multi-armed bandit explore-exploit 取捨,但多了 recovery 這個傳統 bandit 框架裡沒有的第三角色,因為這裡的「失敗」有可能只是實作上的 bug,不代表方向本身壞掉。規則明確要求 recovery 最多佔一個名額、不能搶走 exploitation 的名額,也不能用固定配額,得根據當下證據動態決定。

**四類失敗分類**:hard-unrecoverable(硬性不可能修好)、repairable implementation failure(想法可能沒問題,是實作 bug)、weak-but-underexplored(分數普通但還沒試夠深)、repeatedly unpromising(已有足夠證據顯示這方向真的不行)。一個容易忽略的細節是,程式碼順利跑完、沒有拋出錯誤,不等於「成功」——產出的解可能就是不滿足正確性條件,這種情況是正常評估出一個較弱的解,不該被塞進「可修復失敗」的籃子裡重試。而且任何分類都不是永久判決,即使一條分支被判定成 hard-unrecoverable,只要之後真的出現一次成功結果,就要重新打開這條分支的可能性。

這套四分類跟分散式系統裡經典的 transient(暫時性失敗,值得重試)/permanent(永久性失敗,重試無意義)二分法很像,但多了一個傳統二分法沒有的狀態:weak-but-underexplored 既不是暫時性錯誤,也不是永久性失敗,而是「樣本數還太少,還沒累積足夠證據下判斷」,更接近統計裡樣本不足的概念,不是傳統 retry 邏輯裡的錯誤類型。這個框架直接可以借去用在 agent 的 tool-calling 錯誤處理設計上:結構性、可規則化的錯誤(rate limit、schema 驗證失敗)適合交給 harness 自動重試或攔下,不需要 LLM 介入判斷;需要語意判斷的錯誤(這個工具用起來一直失敗,是不是該換個做法)才丟給 LLM,而且 system prompt 該給的是判斷原則而不是窮舉式的錯誤碼對照表——這正是 B.2 這份 prompt 本身的寫法。

## 結論

Dream-RSI 的核心工程巧思是真實的:把已完成的探索歷史重新框架成一個可以做 off-policy 評估的資料結構,用來低成本篩選探索策略的改良版本,取代昂貴的線上試錯,而且消融實驗也確實證明它比單純把歷史摘要成文字提示更有效。但這份貢獻的份量沒有論文包裝得那麼大——三個實驗場域裡,真正的提升幾乎都集中在「用更少運算資源達到同等品質」,不是能力上的突破;而「World Model」這個框架,跟真正能泛化到未見狀態的 world model 有實質落差,更準確的定位是一套精緻的 off-policy replay 評估機制。

比起論文本身的貢獻,附錄裡那份 policy 改良 prompt 藏的幾個設計模式更值得記住:候選集裡永遠保留「不改」的原始版本以保證單調不退步、決策只能用當下已揭露資訊的 causality constraint、explore/exploit 之外多一個 recovery 角色的 batch portfolio,以及在「暫時性失敗」「永久性失敗」之外辨識出「證據不足」這第三種狀態的失敗分類框架。這些設計脫離這篇論文本身也成立,是任何想做「自我改良系統」或「agent 錯誤處理」的人都可以直接借用的心法。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1 | Overview of Dream-RSI. The system operates in a recursive self-improvement loop via three core stages: 1O Online Explore, where the current exploration policy guides a coding agent to expand a discovery tree and log historical traces; 2O Construct Replay Simulator, where the generated discovery tree is converted into a reusable simulator pool; and 3O Dreaming-based Policy Improvement, where the agent \"dreams\" up a massive pool of alternative policies in its mind. It then feeds these candidate policies into the replay simulator to simulate executions and derive rapid feedback, continuously refining its strategy (detailed in the Zoom-in box). The updated policy then redeploys for the next round of online exploration.",
    "why_used": "用來說明 Dream-RSI 三階段迴圈的整體架構,是整篇方法介紹的起點。",
    "agent_match_hint": "一張系統架構示意圖,畫出線上探索、建構模擬器、做夢式策略改良三個階段的循環箭頭。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2 | Discovery history as a replay simulator. A deployed policy first explores online to generate a structured discovery tree containing historical execution traces (each node denote an attempt with its full observation). Thousands of candidate policies can then be tested within this simulator—evaluating alternative choices of search branches, exploration orders, concurrency levels, and stopping rules. Since all node outcomes are pre-stored, a single costly online run enables thousands of rapid, zero-execution-cost off-policy evaluations. This enables policy improvement through historical replay: the agent can “dream” over many alternative exploration strategies before redeploying the improved policy online.",
    "why_used": "具體畫出 discovery tree 的節點與父子關係,以及一個替代策略如何重播同一棵樹。",
    "agent_match_hint": "一張樹狀圖,節點標有分數,旁邊畫出另一個策略用不同順序展開同一棵樹的對照。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Figure 3 | Lasso regularization-path discovery results. (a) Final wall-clock runtime on six held-out downstream tasks; lower is better. Compute denotes the cumulative number of discovery-agent calls. (b) Recursive discovery dynamics. Average downstream runtime across six held-out tasks versus",
    "why_used": "支撐演算法工程場域的結果說明,顯示 Dream-RSI 用更少運算量拿到相近或更好的 runtime。",
    "agent_match_hint": "左邊一張效能比較表格,右邊一張效能隨累積運算量變化的折線圖。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Table 1 | Performance comparison on mathematical discovery tasks. Higher is better for Sum Diff and Circle Packing, while lower is better for Auto Correlation. Best results are shown in bold.",
    "why_used": "支撐數學優化場域的結果說明,顯示多數方法在這三個任務上的分數差距其實很小。",
    "agent_match_hint": "一張多系統多欄位的數值比較表格,含 Sum Diff、Auto Correlation、Circle Packing 三個指標欄位。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Figure 4 | GPU kernel engineering results. Discovery performance of Dream-RSI and Recursive Fixed Exploration as a function of the number of generations. On VGG16 and LayerNorm, Dream-RSI reaches comparable performance with 2.43× and 1.79× fewer generations, respectively. On ConvDiv and ConvMax, it achieves 2.09× and 1.44× higher performance under comparable discovery budgets. Higher is better for all tasks.",
    "why_used": "支撐 GPU kernel 工程場域的結果說明,是三個場域裡效率提升最直接可讀的一組數字。",
    "agent_match_hint": "四個子圖,分別畫出 VGG16、LayerNorm、ConvDiv、ConvMax 上效能隨 generation 數增加的曲線。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Figure 5 | Discovery performance on ConvDiv. Us- ing history as an interactive replay simulator out- performs using it only as guidance.",
    "why_used": "支撐消融實驗段落,說明結構化重播優於文字摘要式引導。",
    "agent_match_hint": "ConvDiv 任務上兩條效能曲線的對照圖,一條用歷史當互動模擬器,一條只當文字引導。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Figure 6 | Evolution of exploration behavior on ConvDiv. (a) Round-best performance across re- cursive execution rounds. (b) The number of eval- uated attempts in each round.",
    "why_used": "支撐探索行為演化段落,說明策略隨輪次從保守轉為積極的自適應模式。",
    "agent_match_hint": "兩張並排的長條圖或折線圖,分別顯示每輪最佳表現與每輪評估嘗試數隨輪次的變化。"
  }
]
```
