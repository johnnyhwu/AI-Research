# 開始深度學習之前，先了解什麼是「感知器」(Perceptron)

## 前言

自 2012 年 AlexNet 在 [ILSVRC](https://www.image-net.org/challenges/LSVRC/) 贏得冠軍後，深度學習 (Deep Learning) 逐漸成為顯學，人工神經網路 (Artificial Neural Network) 開始被拿來處理傳統演算法搞不定的問題，包含電腦視覺 (Computer Vision) 與自然語言處理 (Natural Language Processing)。

不過在跳進那些深度學習的核心觀念之前，值得先花點時間從神經網路的始祖「感知器」(Perceptron) 看起。本篇文章會說明 Perceptron 是什麼、它的數學算式怎麼寫、為什麼一個 Perceptron 等價於一個 NAND Gate，以及多個 Perceptron 串起來之後為什麼能表達任何運算。這些概念是後面所有神經網路知識的地基。

## 什麼是感知器 (Perceptron)

感知器 (Perceptron) 是 [Frank Rosenblatt](https://en.wikipedia.org/wiki/Frank_Rosenblatt) 在 1957 年基於生物神經細胞的概念發明的「人造神經元」(Artificial Neuron)，本質上是一種簡單的「二元線性分類器」。

這裡要先講清楚一件事：現代發表的神經網路 (Neural Network) 模型裡用的神經元其實已經不是 Perceptron，而是另一種叫「Sigmoid Neuron」的東西。那為什麼還要學 Perceptron？因為 Sigmoid Neuron 的原理幾乎是站在 Perceptron 上長出來的，先掌握 Perceptron，後面看 Sigmoid Neuron 才會覺得理所當然。

![一個感知器示意圖，左側有 x1、x2、x3 三個輸入箭頭指向中間的圓形神經元，右側輸出一個 output 箭頭。](img-001)
*感知器 (Perceptron) 接收「多個」二元數值並輸出「一個」二元數值*

如上圖所示，Perceptron 能夠接收多個輸入，並且輸出一個數值。其中 x1、x2、x3 與 output 都是「二元數值」，也就是它們的值不是 0 就是 1。

Rosenblatt 也提出一個很直接的方法來計算 Perceptron 的 output：把每一個輸入 x 乘上各自對應的參數 w，再把這些乘積加總起來；如果總和大於某一個門檻 (threshold) 就輸出 1，否則輸出 0。**w** 與 **threshold** 就是這一個 Perceptron 的參數。

寫成數學算式的話會長這樣：

![以不等式表示的感知器數學算式，當各輸入與權重乘積的總和小於等於門檻時輸出 0，大於門檻時輸出 1。](img-002)
*以數學形式表示 Perceptron 的運作 [source: Neural Networks and Deep Learning]*

## 用簡單的例子理解 Perceptron 的運作

上面的算式看起來有點抽象，換個生活中的例子會好懂很多。我們可以把 x1、x2、x3 想成不同的「因素」，output 則是最後的「決定」。

舉例來說，假設這個週末朋友約你出去玩，你很猶豫要不要去，因為你還在考慮以下三件事情：

- 週末是不是晴天 (討厭雨天)
- 出去玩的成員中有沒有異性 (想順便認識新朋友)
- 能不能搭別人的汽車過去 (不想自己搭火車)

這三個「因素」就是 Perceptron 的 x1、x2、x3，最後「決定」要不要去就是 output。如果週末是晴天，x1 為 1；是雨天則 x1 為 0。如果成員中有異性，x2 為 1，否則為 0。x3 也是同樣的概念。

因為你對這三件事的「重視程度」不一樣，x1、x2、x3 在 Perceptron 中也會對應到不同的參數 w。假設你真的非常在意「成員中有沒有異性」，只要有異性，即使週末註定下大雨、也註定沒車可搭，你還是會決定要去，那 w2 的數值就會明顯大於 w1 與 w3。

把三項因素的重視程度排序成「成員中有沒有異性」>「週末會不會下雨」=「能不能搭別人的汽車過去」之後，w 的數值可能會是 w1 = 3、w2 = 6、w3 = 3。

除了 w 之外，Perceptron 還有 threshold 這個參數，在這個例子中我們把它設為 5。這樣一來，就算「週末會下雨」(x1 = 0)、「不能搭別人的汽車過去」(x3 = 0)，只要「成員中有異性」(x2 = 1)，總和 6 仍然大於 5，最後的決定 (output) 還是 1。反過來說，如果把 threshold 設成一個很大的數字 (例如 100)，那麼即使三個因素全部符合你的期待，總和 12 還是過不了門檻，你最終也會決定不去。

從這個例子可以看出 Perceptron 兩個參數各自的角色：調整 w 等於調整每個輸入的權重，也就是你對各項因素的重視程度；調整 threshold 則像是在調整你有多想做出正向的決定，也就是 output 有多容易是 1。

## 多個 Perceptron 形成一個 Network

一個 Perceptron 能處理的問題複雜度其實相當有限，畢竟它只做了「加權相加、跟門檻比大小」這一件事。要解決現實世界中比較複雜的問題，就得把很多個 Perceptron 接起來，形成一個神經網路 (Neural Network)。

![由多個圓形神經元組成的神經網路示意圖，分為數層，每一層的神經元都以箭頭連接到下一層的每個神經元。](img-003)
*多個 Perceptron 形成一個 Neural Network [source: Neural Networks and Deep Learning]*

上圖把 8 個 Perceptron 組織成一個 Neural Network。第 1 層有 3 個 Neuron，每一個都會把輸入乘上權重 (w) 後加總，再依總和有沒有超過門檻 (threshold) 輸出 1 或 0。換句話說，這一層等於一口氣做了三種不同的決定。下一層的 Neuron 則是根據前一層的輸出 (決定) 再做決策，所以愈後面的層所做的決定會愈複雜、愈抽象。這也是為什麼實務上處理困難的問題時，我們經常會搭出層數非常多的神經網路。

你可能會覺得奇怪：一開始不是說 Perceptron 只有一個 output 嗎？為什麼上圖裡的 Perceptron 卻畫出好幾個輸出箭頭？其實它仍然只有一個 output，只是這個 output 同時被送進了下一層的多個 Neuron 當輸入，所以才畫成多個箭頭。

## 簡化 Perceptron 的數學算式

前面那個原始算式老實說又臭又長，實務上我們會做兩個小改寫把它縮短。

第一，**∑wx** 是每個輸入與權重相乘後的總和，這正好就是「[內積](https://zh.wikipedia.org/wiki/%E7%82%B9%E7%A7%AF)」，可以直接寫成 **w ⋅ x**，其中 w 與 x 都是向量。第二，把 threshold 從不等式的右邊移到左邊，會得到 **−threshold**，這個寫法一樣冗長，所以我們用 **b** 來代表它。

![簡化後的感知器數學算式，以 w 與 x 的內積加上 b 是否大於 0 來決定輸出 0 或 1。](img-004)
*Perceptron 簡化後的數學算式 [source: Neural Networks and Deep Learning]*

在深度學習的世界中，w 通常被稱作 **weight**，b 則被稱作 **bias**，兩者都是神經網路模型的參數。接下來的文章也都會用 weight 與 bias 來描述神經網路中的參數。

bias 的概念常常讓人覺得有點抽象，但只要記得它的前身是 threshold 就好懂了：它代表這個 Neuron 的輸出有多容易是 1。用生物學的角度來想，bias 就是這個 Neuron 被「激活」的難易度。如果某個 Neuron 的 bias 是很大的正數 (例如 100)，那不管輸入 x 是什麼，最後的輸出都很可能是 1 (Neuron 被激活)；反之，bias 是很小的負數 (例如 -1) 時，輸出就很可能是 0。

## Perceptron 相當於 NAND Gate

到目前為止我們都把 Perceptron 當成「做決定」的東西，但它其實也可以直接當作一個「Logical Function」來看。最單純的 Logical Function 就是數位電路設計課裡教的「[邏輯閘](https://en.wikipedia.org/wiki/Logic_gate)」，也就是 AND、OR、NOT Gate 那一類。

![一個接收 x1 與 x2 兩個輸入的感知器，兩條輸入連線上標示權重 -2，神經元內部標示 bias 為 3。](img-005)
*Perceptron 也可以運作得像 NAND Gate 一樣*

如上圖所示，這個 Perceptron 接受兩個輸入 (x1 與 x2)，兩個輸入的權重 (w1 與 w2) 都是 -2，bias 為 3。輸入 00 (x1=0、x2=0) 時，(0 × -2) + (0 × -2) + 3 = 3，輸出為 1；輸入 01 與 10 的結果同樣是 1。但如果輸入 11，(1 × -2) + (1 × -2) + 3 = -1，輸出就變成 0。把這四種情況列出來，會發現它的真值表和 NAND Gate 完全相同。

講到「NAND Gate」，修過數位電路相關課程的人應該馬上會想到：NAND Gate 是一個「Universal Gate」。也就是說，光靠 NAND Gate 就能搭出任何你想要的 Logical Function。

![由多個 NAND 邏輯閘互相連接組成的加法器電路圖。](img-006)
*僅透過 NAND Gate 搭建一個加法器 [source: Wikimedia Commons]*

上圖就是一個只用 NAND Gate 搭出來的加法器 (Half Adder)。既然 Perceptron 可以當作 NAND Gate 使用，那圖中所有的 NAND Gate 自然也能通通換成 Perceptron。

![與前一張加法器結構相同的電路圖，但所有的 NAND 邏輯閘都換成了感知器符號，連線上標示著權重 -2 與 bias 3。](img-007)
*將加法器中的 NAND Gate 都替換成 Perceptron [source: Neural Networks and Deep Learning]*

替換完之後，原本的電路圖瞬間變成了一個 Neural Network。仔細看會發現一個怪怪的地方：最左邊的 Neuron 有兩條輸出同時接到同一個 Neuron，這在前面介紹 Perceptron 時沒有出現過。解法其實很簡單，把那兩條輸入合併成一條，權重由 -2 改成 -4，整個 Neural Network 的運作結果完全不變。

![加法器的感知器版本電路圖，原本兩條權重 -2 的連線被合併成一條權重 -4 的連線。](img-008)
*將「兩條 -2」換成「一條 -4」[source: Neural Networks and Deep Learning]*

除此之外，我們通常也會把 Neural Network 最左邊的輸入用「Perceptron 的符號」畫出來：

![加法器的神經網路圖，最左邊多了一層以感知器符號表示的輸入節點 x1 與 x2。](img-009)
*將 Neural Network 最左邊的輸入以 Perceptron 表示形成一個 Layer [source: Neural Networks and Deep Learning]*

當輸入 (x1 與 x2) 也用 Perceptron 畫出來之後，最左邊看起來就像是多了一層 (Layer)，這一層通常被稱為「輸入層」(Input Layer)。

你可能又會覺得奇怪：為什麼 Input Layer 的 Perceptron 沒有輸入？為了避免這個疑惑，比較好的理解方式是不要把 Input Layer 裡的 Neuron 當成真正的 Perceptron，而是把它們視為一種特別的 Neuron，單純用來表示整個 Neural Network 的輸入。

## Perceptron 可以表達任何的運算

把前面兩件事串起來：Perceptron 相當於 NAND Gate，而 NAND Gate 是 Universal Gate 可以表達任何運算，所以用 Perceptron 組成的 Neural Network 同樣可以表達任何運算。

「Perceptron 可以表達任何的運算」這句話聽起來很厲害，代表我們能用它組出非常強大的運算裝置。但換個角度想又有點令人失望，畢竟這樣的 Perceptron 說白了就是 NAND Gate 的化身而已。

不過先別急著對 Perceptron、Neural Network 或 Deep Learning 失去信心。後來許多學者為 Perceptron 加上了其他元素，其中最關鍵的就是「學習演算法」(Learning Algorithm)。有了 Learning Algorithm，Perceptron 可以「自己」調整參數 (weight 與 bias)。

這就是 Perceptron 和 NAND Gate 真正拉開差距的地方：我們不需要親手把一個個 Perceptron 拼成 Neural Network 再手動設定裡面的每個參數，而是讓整個 Neural Network 自己去把參數調到對的位置。

## 參考資料

- [Neural networks and deep learning](http://neuralnetworksanddeeplearning.com/chap1.html)
- [Perceptron – Wikipedia](https://en.wikipedia.org/wiki/Perceptron)
- [NAND and NOR Gate as Universal Gate – Digital Electronics](https://sites.google.com/site/tanglindigitalelectronics/home/nand-and-nor-gate-as-universal-gate)
- [Logic gate – Wikipedia](https://en.wikipedia.org/wiki/Logic_gate)

## 結論

本篇文章介紹了 Perceptron 的基本概念，包含它如何把輸入加權相加後跟門檻比大小，以及把 threshold 改寫成 bias 之後的簡化算式。接著透過 Perceptron 與 NAND Gate 的等價關係，說明為什麼多個 Perceptron 組成的 Neural Network 足以表達任意運算。最後提到 Learning Algorithm 才是讓 Perceptron 不只是 NAND Gate 化身、而能自己學習的關鍵。

下一篇文章會介紹更接近現代 Neural Network 所使用的 Neuron：Sigmoid Neuron。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "感知器 (Perceptron) 接收「多個」二元數值並輸出「一個」二元數值",
    "why_used": "在介紹 Perceptron 定義的段落，先讓讀者看到一個 Perceptron 的長相：多個二元輸入、一個二元輸出。",
    "agent_match_hint": "單一神經元示意圖，左側 x1、x2、x3 三個輸入箭頭指向中央圓形，右側一個 output 箭頭。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "以數學形式表示 Perceptron 的運作 [source: Neural Networks and Deep Learning]",
    "why_used": "把「加權相加後與門檻比大小」的文字說明對應到實際的數學算式。",
    "agent_match_hint": "一段數學算式，以大括號分成兩種情況，依 ∑wx 與 threshold 的大小關係輸出 0 或 1。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "多個 Perceptron 形成一個 Neural Network [source: Neural Networks and Deep Learning]",
    "why_used": "支撐說明單一 Perceptron 能力有限、需要多層多個 Neuron 組成網路的段落。",
    "agent_match_hint": "多層神經網路示意圖，圓形神經元分層排列並以箭頭全連接到下一層。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Perceptron 簡化後的數學算式 [source: Neural Networks and Deep Learning]",
    "why_used": "呈現以內積與 bias 改寫後的算式，讓讀者對照原始版本理解 weight 與 bias 的由來。",
    "agent_match_hint": "簡化版數學算式，含 w ⋅ x + b 與 0 的大小比較，分成輸出 0 與輸出 1 兩種情況。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Perceptron 也可以運作得像 NAND Gate 一樣",
    "why_used": "搭配權重 -2、bias 3 的計算過程，說明單一 Perceptron 的真值表等同 NAND Gate。",
    "agent_match_hint": "一個雙輸入感知器示意圖，兩條輸入連線標示 -2，神經元標示 bias 3。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "僅透過 NAND Gate 搭建一個加法器 [source: Wikimedia Commons]",
    "why_used": "作為 NAND Gate 是 Universal Gate 的具體例證，帶出後續把邏輯閘換成 Perceptron 的推論。",
    "agent_match_hint": "數位電路圖，數個 NAND 邏輯閘符號互相連接組成加法器。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "將加法器中的 NAND Gate 都替換成 Perceptron [source: Neural Networks and Deep Learning]",
    "why_used": "呈現把加法器的邏輯閘全部換成 Perceptron 後、電路圖變成 Neural Network 的結果。",
    "agent_match_hint": "與加法器結構相同的電路圖，但邏輯閘符號改為圓形神經元，連線標示權重 -2 與 bias 3。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "將「兩條 -2」換成「一條 -4」[source: Neural Networks and Deep Learning]",
    "why_used": "說明兩條重複連線可以合併成單一權重 -4 的連線，而網路行為不變。",
    "agent_match_hint": "同一張感知器版加法器圖，其中一組雙連線被合併，標示由 -2 改為 -4。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "將 Neural Network 最左邊的輸入以 Perceptron 表示形成一個 Layer [source: Neural Networks and Deep Learning]",
    "why_used": "說明把輸入也畫成 Perceptron 符號後，最左邊會形成所謂的 Input Layer。",
    "agent_match_hint": "感知器版加法器圖，最左側多出一層以神經元符號表示的輸入節點 x1、x2。"
  }
]
```
