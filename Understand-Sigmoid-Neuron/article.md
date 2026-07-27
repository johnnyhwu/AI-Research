# Perceptron 的改良版：了解什麼是 Sigmoid Neuron

## 前言

在前一篇「了解什麼是 Perceptron」中，我們認識了最古老的人造神經元 (Artificial Neuron)：感知器 Perceptron，也看過它的數學算式以及它與 NAND Gate 之間的關係。但 Perceptron 並不是現代神經網路 (Modern Neural Network) 實際在用的神經元。

這篇文章要介紹一種「更接近」現代神經網路的神經元：Sigmoid Neuron。我們會從「神經網路到底怎麼學習」講起，看看 Perceptron 卡在哪裡，再說明 Sigmoid Neuron 做了什麼修改、為什麼這個修改剛好解決問題，最後談談它的輸出該怎麼解讀。沒讀過前一篇也不影響閱讀，需要的觀念這裡都會補上。

## 神經網路如何學習

Perceptron 之所以不只是 NAND Gate 的化身，關鍵在於「學習演算法」(Learning Algorithm) 的存在，它讓神經元能自己把參數 (weight 與 bias) 調到對的數值。在真的動手設計 Learning Algorithm 之前，先用比較直觀的方式理解神經網路 (Neural Network) 是怎麼學會輸出正確答案的。

拿一個很具體的任務來想：有一個 Neural Network，輸入是一張手寫數字的照片，輸出是這張照片代表的數字。

![一張手寫數字的照片輸入 Neural Network 後，輸出對應數字的示意圖。](img-001)
*透過一個 Neural Network 辨識「手寫數字照片」的實際數字*

Neural Network 一開始的參數是隨機產生的，所以剛開始的輸出通常慘不忍睹。例如輸入一張手寫的 4，它卻認成 6。為了輸出正確結果，它必須不斷調整自己的參數。

這裡我們會希望有一個很理想的性質：每次對參數做「些微」的調整，輸出結果也只跟著「微幅」變動。

![某個參數 w 加上一個微小的 ∆w 後，Neural Network 的輸出也只變動一個微小的 ∆output 的示意圖。](img-002)
*「微幅」調整參數數值，使得輸出結果也「微幅」變動 [source: Neural Networks and Deep Learning]*

如上圖，我們把 Neural Network 中的某個參數 w 加上一個很小的 ∆w，輸出就跟著加上一個很小的 ∆output。這件事若真的成立，學習就簡單多了：假設輸入「手寫數字 9」的照片得到輸出「8」，我們只要找出每個參數該往哪個方向調 (變大還是變小)，然後小小地調一點，就可以預期輸出也會小小地往正確的方向移動。一直這樣調下去，直到輸出變成 9 為止。

換句話說，「參數微調 → 輸出微動」這個性質，是整個學習過程能夠穩定收斂的前提。

## Perceptron 帶來的問題

問題是，Perceptron 並不具備這個性質。回到 Perceptron 的基本結構：

![Perceptron 的示意圖，左側多個二元輸入 x1、x2、x3 經過神經元後產生一個二元輸出。](img-003)
*Perceptron 接收多個 Binary Value 並輸出一個 Binary Value*

Perceptron 接收多個二元數值作為輸入，輸出也是一個二元數值。所謂「二元數值」就是不是 0 就是 1，中間沒有灰色地帶。

麻煩就出在這裡。在一個由許多 Perceptron 組成的 Neural Network 中，就算只是「微幅」調整其中一個 Perceptron 的 weight，也可能讓這個 Perceptron 的輸出直接翻面，從 0 變成 1。而這個 Perceptron 的輸出又是後面其他 Perceptron 的輸入，一路傳下去，整個 Neural Network 的輸出就變得難以捉摸。

具體一點：輸入「手寫數字 9」的照片得到「8」，我們反覆微調參數，終於讓它正確輸出 9。但在這個過程中，網路裡許多 Perceptron 的 output 已經整個翻掉 (0 變 1、1 變 0)，於是原本被分類正確的其他照片，這時再輸入進去，答案可能就跟著壞掉了。修好一個、弄壞一片，學習根本無從累積。

## Sigmoid Neuron 登場

為了讓神經元的 output 能夠被「微幅」變動，一種新的人造神經元被提出來，稱為 Sigmoid Neuron。它其實不是砍掉重練，而是在原本的 Perceptron 上做了一點修改。

Sigmoid Neuron 的外型和 Perceptron 一模一樣 (可以對照上一張 Perceptron 示意圖)：接收多個輸入 x1、x2、x3，產生一個 output。真正不一樣的地方，在於這些數值的「型態」。

在 Perceptron 中，輸入只能是不連續的二元數值，也就是 0 或 1。但在 Sigmoid Neuron 中，輸入是 0 到 1 之間連續分佈的任意數字，例如 0.2556 或 0.6398。每個輸入一樣會乘上各自的 weight 後加總，再加上一個 bias，得到最終的數值。

![Perceptron 簡化後的數學算式，以 w·x + b 與門檻值比較後輸出 0 或 1。](img-004)
*Perceptron 簡化後的數學算式 [source: Neural Networks and Deep Learning]*

如上圖，Perceptron 拿這個最終數值去比一個門檻，output 就是 0 或 1。Sigmoid Neuron 則不同：它的 output 和輸入一樣，是 0 到 1 之間連續分佈的任意數字。更精確地說，Sigmoid Neuron 會把最終的數值 (w·x + b) 再通過一個 Sigmoid 函數才輸出，所以它的輸出是 σ(w·x + b)。

這個「σ」的名字就是 Sigmoid Function，完整算式如下：

![Sigmoid Function 的數學算式，形式為 1 除以 1 加上 e 的負 z 次方。](img-005)
*Sigmoid Function*

整理一下 Sigmoid Neuron 的計算流程：先把所有輸入 x 與對應的 weight 相乘並加總，再加上 bias，得到 z = w·x1 + w·x2 + w·x3 + ··· + bias；接著把 z 丟進 Sigmoid Function，最後輸出 σ(z)。

## Sigmoid Neuron 與 Perceptron 的相似之處

剛認識 Sigmoid Neuron 時，很容易覺得多了一個 Sigmoid Function，輸出應該會跟 Perceptron 差很多。實際上剛好相反，兩者的行為在大部分情況下非常接近。

假設 z = w·x + b 是一個很大的正數，那麼 e^(-z) 會趨近於 0，算下來 σ(z) 會趨近於 1。也就是說，z 很大時 Sigmoid Neuron 輸出 1，跟 Perceptron 一致。

反過來，當 z = w·x + b 是一個很小的負數，e^(-z) 會趨近於無限大，σ(z) 就趨近於 0，一樣和 Perceptron 一致。

真正會不一樣的，只有 z 不大也不小、落在中間那一段的時候。而這段「模糊地帶」正是 Sigmoid Neuron 的價值所在：它把原本 0 與 1 之間的懸崖，鋪成了一道緩坡。

## Sigmoid 函數最重要的特性：平滑

我們不會深入推導 Sigmoid 算式的細節，重點放在它最關鍵的特性：**平滑**。

![Sigmoid 函數畫在二維平面上的曲線，呈平滑的 S 形，由 0 連續上升到 1。](img-006)
*sigmoid function [source: Neural Networks and Deep Learning]*

上圖是 Sigmoid 函數畫在二維平面上的樣子。把它跟 Step 函數擺在一起看，會發現 Sigmoid 函數其實就是 Step 函數的「平滑版」：

![Step 函數畫在二維平面上的圖形，在門檻處由 0 垂直跳到 1，形成一個直角階梯。](img-007)
*step function [source: Neural Networks and Deep Learning]*

這個對照也解釋了兩種神經元的關係：如果把 Sigmoid Neuron 的 σ 換成 Step 函數，它就退化成 Perceptron，因為輸出會是 w·x + b 通過 Step 函數後得到的 0 或 1。

而平滑之所以重要，是因為它讓前面那個理想性質真的成立：參數 (weight 與 bias) 經過微幅調整後，輸出真的也只會微幅變動。

![Δoutput 由 Δw 與 Δb 分別乘上對應偏微分後相加而成的算式。](img-008)
*output 的變動來自於 weight 與 bias [source: Neural Networks and Deep Learning]*

上圖表達的是 Sigmoid Neuron 的輸出變動 (Δoutput) 如何來自參數的變動 (Δw 與 Δb)。Δw 表示 weight 的變動，Δb 表示 bias 的變動，兩者並不是單純相加，而是各自再乘上一個偏微分。

第一次看到偏微分可能會覺得卡，可以先簡單把它想成：一個多變數函數對某一個變數的「改變率」。也就是說，w 加上 5 (Δw = 5) 時，output 不一定就跟著加 5，而是要再乘上 output 對 w 的改變率 (w 每變動 1，output 會變動多少)。

再白話一點，可以把上面的算式當成一個簡單的線性函數：Δw 乘一個常數，加上 Δb 乘另一個常數，等於 Δoutput。既然是線性的，Δw 與 Δb 只做微幅變動時，Δoutput 自然也只會微幅改變。這正是 Perceptron 做不到、而 Sigmoid Neuron 做得到的事。

## 如何解讀 Sigmoid Neuron 的輸出

Sigmoid Neuron 的輸出不再只有 0 或 1，而是 0 到 1 之間的任意數字，可能是 0.2123、0.5698 或 0.9652。這帶來一個新問題：這個數字到底該怎麼讀？

假設我們用一個 Sigmoid Neuron 來判斷手寫數字圖像，輸入「圖像 9」，我們希望它的輸出告訴我們這張圖「是數字 9」或「不是數字 9」。但輸出已經不像 Perceptron 那樣用 0 與 1 直接對應 False 與 True 了。

實務上的做法是把輸出視為「機率」。Sigmoid Neuron 的輸出必定落在 0 到 1 之間，剛好符合機率的性質，所以可以很直覺地拿 0.5 當作分類的門檻：輸出 0.6 大於 0.5，表示它認為這張圖「是數字 9」；輸出 0.4 小於 0.5，就表示它認為「不是數字 9」。

## 結論

這篇文章介紹了更接近現代神經網路所使用的神經元：Sigmoid Neuron。它的結構幾乎照抄 Perceptron，差別在於輸入與輸出都改成 0 到 1 的連續數值，並且在最後多套了一層 Sigmoid Function。

關鍵在於 Sigmoid 函數的「平滑」特性：它讓參數微調時輸出也只微幅變動，避免了 Perceptron 那種輸出直接翻面、牽一髮動全身的困境，學習才有辦法一步一步累積。而連續的輸出也帶來額外的好處，可以直接被解讀成機率，用 0.5 當門檻做分類。

本篇與前一篇「了解什麼是 Perceptron」都聚焦在單一個人工神經元 (Artificial Neuron) 上。下一篇文章會把視角拉高，進入人工神經網路 (Artificial Neural Network) 的介紹，看看這些神經元串接起來之後會發生什麼事。

### 參考資料

- [Neural networks and deep learning](http://neuralnetworksanddeeplearning.com/chap1.html)
- [Sigmoid function – Wikipedia](https://en.wikipedia.org/wiki/Sigmoid_function)
- [Partial Differentiation Tutorial](http://ind.ntou.edu.tw/~metex/Calculus/SecondTerm/CH7.pdf)

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "透過一個 Neural Network 辨識「手寫數字照片」的實際數字",
    "why_used": "以手寫數字辨識這個具體任務，帶出「神經網路如何學習」這一節要討論的場景。",
    "agent_match_hint": "一張流程示意圖，左邊是一張手寫數字圖片，經過中間的 Neural Network 方塊後輸出一個數字。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "「微幅」調整參數數值，使得輸出結果也「微幅」變動 [source: Neural Networks and Deep Learning]",
    "why_used": "圖示「參數微調則輸出微動」這個理想性質，是後面推導 Perceptron 問題與 Sigmoid Neuron 價值的前提。",
    "agent_match_hint": "一張神經網路示意圖，其中一條連線標示 w + ∆w，輸出端標示 output + ∆output。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Perceptron 接收多個 Binary Value 並輸出一個 Binary Value",
    "why_used": "回顧 Perceptron 的基本結構，說明它的輸入與輸出都是二元數值，因此輸出只能整個翻面而無法微幅變動。",
    "agent_match_hint": "一張單一神經元示意圖，左側三個輸入 x1、x2、x3 以箭頭指向中央圓形，右側一個 output 箭頭。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Perceptron 簡化後的數學算式 [source: Neural Networks and Deep Learning]",
    "why_used": "呈現 Perceptron 以 w·x + b 與門檻比較後輸出 0 或 1 的算式，作為對照 Sigmoid Neuron 輸出型態的基準。",
    "agent_match_hint": "一段數學算式，以 w·x + b 是否小於等於或大於 0 分成兩種情況，分別輸出 0 與 1。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Sigmoid Function",
    "why_used": "給出 σ 的完整定義，讓讀者知道 Sigmoid Neuron 最後套上的那一層函數究竟長什麼樣子。",
    "agent_match_hint": "一行數學算式，σ(z) 等於 1 除以 1 加上 e 的負 z 次方。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "sigmoid function [source: Neural Networks and Deep Learning]",
    "why_used": "用函數圖形直觀呈現 Sigmoid 的平滑特性，並鋪陳它與 Step 函數的對照。",
    "agent_match_hint": "一張二維座標圖，曲線呈平滑的 S 形，由接近 0 連續上升到接近 1。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "step function [source: Neural Networks and Deep Learning]",
    "why_used": "與 Sigmoid 函數圖形對照，說明把 σ 換成 Step 函數後 Sigmoid Neuron 就退化為 Perceptron。",
    "agent_match_hint": "一張二維座標圖，圖形在門檻處由 0 垂直跳到 1，呈直角階梯狀。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "output 的變動來自於 weight 與 bias [source: Neural Networks and Deep Learning]",
    "why_used": "支撐說明 Δoutput 是 Δw 與 Δb 分別乘上偏微分後相加的段落，解釋平滑為何能保證輸出只微幅變動。",
    "agent_match_hint": "一行數學算式，Δoutput 等於對各個 w 的偏微分乘 Δw 的總和，再加上對 b 的偏微分乘 Δb。"
  }
]
```
