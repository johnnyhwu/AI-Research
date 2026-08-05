# Backpropagation 介紹：看懂如何透過 Backpropagation 計算 Gradient

## 前言

在前面幾篇文章中，我們已經知道可以透過 Gradient Descent 與 Stochastic Gradient Descent 來更新 Neural Network 中的參數。不過那時候只在概念上說「把 Weight 與 Bias 往 Gradient 的反方向調整」，至於這些 Gradient 實際上是怎麼被算出來的，一直沒有交代。

這篇文章要補的就是這一塊：Backpropagation 演算法如何把 Neural Network 中所有參數的 Gradient 一次算出來。內容會從符號定義開始，接著介紹 Backpropagation 的四個核心公式，並逐一說明每個公式是怎麼推導出來的。

## Backpropagation 是什麼

**Backpropagation 是一種能夠快速計算 Gradient 的演算法**。為什麼需要它？現在的 Neural Network 隨隨便便就有上千萬個參數，而每次更新參數時，都必須先算出這個參數的 Gradient（也就是 Cost Function 對該參數的偏微分）。如果沒有一個夠有效率的方法把這上千萬個 Gradient 算出來，訓練時間會拉長到不切實際的程度，Deep Learning 也就無從談起。

Backpropagation 演算法早在 1970 年代就已經出現，但一直到 David Rumelhart、Geoffrey Hinton、Ronald Williams 等人於 1986 年共同發表了 [Learning representations by back-propagating errors](https://www.nature.com/articles/323533a0) 論文之後，才真正受到重視。這篇論文說明了如何利用 Backpropagation 讓 Neural Network 學得更快，也讓 Neural Network 從此變成一個真的能拿來解問題的工具。

老實說，Backpropagation 的觀念不算好啃，第一次讀的人很容易迷失在一大堆數學符號與下標裡。看一次不懂沒關係，這是很正常的事，多消化幾次就會慢慢清晰。

在被符號淹沒之前，先記住一個大原則：**Backpropagation 就是一種能夠快速計算 Gradient 的演算法，也就是如何快速的算出 ∂C/∂w 與 ∂C/∂b。**有了 ∂C/∂w 與 ∂C/∂b，我們就能夠知道當 Weight (w) 與 Bias (b) 變化時，Cost Function 的數值會增加還是減少，以及增加或減少多少。整篇文章的推導，最後都是為了回答這件事。

## 計算 Neural Network 的輸出

在進入 Backpropagation 之前，先確認你已經了解 Neural Network 的輸出是怎麼算出來的，同時把後面會用到的數學符號一次定義清楚。這一節的符號如果沒有先建立起來，後面的公式會很難讀。

![一個由輸入層、隱藏層、輸出層構成的三層神經網路示意圖](img-001)
*有 3 個 Layer 的 Neural Network*

如上圖所示，這是一個有 3 個 Layer 的 Neural Network，我們用「小寫 L」來表示第幾個 Layer。

![神經網路示意圖，標示出連接兩個 Neuron 之間的 Weight 符號 w 及其上下標的意義](img-002)
*利用 w 來表示 Neural Network 中的 Weight*

我們利用 w 來表示 Neural Network 中的 Weight，其形式為 L – 1 Layer 中的第 k 個 Neuron 連接到 L Layer 中第 j 個 Neuron 的 Weight。這裡的下標順序（先 j 後 k）很容易記反，後面看公式時可以回頭對照這張圖。

![神經網路示意圖，標示出每個 Neuron 各自的 Bias 符號 b 及其上下標的意義](img-003)
*用 b 來表示 Neural Network 中的 Bias*

我們利用 b 來表示 Neural Network 中的 Bias，其形式為 L Layer 中的第 k 個 Neuron 的 Bias。

![神經網路示意圖，標示出每個 Neuron 的輸出 Activation 符號 a 及其上下標的意義](img-004)
*利用 a 表示 Neural Network 的 Activation*

我們利用 a 來表示 Neural Network 中的 Activation，其形式與 Bias 相同，都是指 L Layer 中的第 k 個 Neuron。

![Activation 的計算式，前一層 Activation 的加權總和加上 Bias 後再送入 Sigmoid Function](img-005)
*計算 Neural Network 中的 Activation*

Activation 的計算方式如上圖所示：前一個 Layer Activation 的 Weighted Sum 再加上 Bias，最後經過一個 Activation Function（我們這裡使用 Sigmoid Function，細節可以參考〈Perceptron 的改良版：了解什麼是 Sigmoid Neuron〉那篇文章）。

一個一個 Neuron 寫下去會很囉唆，所以我們用 Matrix 或 Vector 把整個 Layer 的資訊包起來。例如，我們用 wl 表示 L Layer 中的所有 Weight，wljk 則是 wl 中第 j 個 Row、第 k 個 Col 的元素；用 bl 表示 L Layer 中的所有 Bias；al 表示 L Layer 中的所有 Activation。透過 Matrix 與 Vector 的形式，我們可以如此表示 Activation 的計算方式：

![以向量與矩陣形式表示的 Activation 計算式](img-006)
*用 Vector 與 Matrix 表示 Activation 的計算*

寫成這樣就清楚多了：這一個 Layer 的 Activation 其實就是前一個 Layer 的 Activation 乘以 Weight 後再加上 Bias，最後通過 Sigmoid Function。整個 Layer 的運算縮成一行。

為了方便後面的介紹，我們再定義一個符號。我們將上圖 Activation 算式中 Sigmoid Function 裡面的內容定義為 z，換句話說，zl ≡ wl al-1 + bl。我們可以將 zl 想成是 L Layer 中 Neuron 的 Weighted Input，也就是「還沒經過 Activation Function 之前」的那個值。有了 zl，Activation 的計算就能再進一步簡化成 al = σ(zl)（如下圖所示）。

![以 z 表示 Neuron 的 Weighted Input，並將 Activation 化簡為 σ(z) 的算式](img-007)
*用 z 表示 Neuron 的 Weighted Input*

## Backpropagation 中四個重要的公式

到這裡，大腦的暖身已經完成（希望你的思緒還相當清晰）。還記得一開始提過，Backpropagation 演算法的目的就是要快速計算出 Neural Network 中每一個參數的 Gradient（Cost Function 對該參數的偏微分）。這件事主要靠以下四個公式完成，所有的 **∂C/∂w 與 ∂C/∂b** 都是從這四條式子算出來的：

![Backpropagation 的四大公式 BP(1) 到 BP(4)，並列在同一張圖中](img-008)
*Backpropagation 演算法四大公式*

別急，現在的你一定看不懂這四個公式，這很正常。在逐條拆解之前，先用「直覺」觀察一下它們的長相。

BP(3) 與 BP(4) 都是在計算 Cost Function 對 Neural Network 中參數 (Weight 與 Bias) 的偏微分，那不就正是我們想要的 Gradient 嗎？而且它們都跟 **δ** 有關。再回頭看 BP(1) 與 BP(2)，會發現這兩條式子都是在計算 **δ**。

換句話說，四個公式其實分成兩組：前兩條負責算出 δ，後兩條負責把 δ 轉換成我們要的 Gradient。那麼 **δ** 到底是什麼東西？在拆解 BP(1) 到 BP(4) 之前，先把 δ 的意義弄懂。

![神經網路示意圖，第二層的第二個 Neuron 上畫著一個小精靈](img-009)
*想像 Neural Network 中住著一個小精靈*

我們想像在 Neural Network 中住著一個小精靈，如上圖所示，小精靈住在第二個 Layer 的第二個 Neuron。

![小精靈在 Neuron 的 Weighted Input 上加入 Δz，使輸出由 σ(z) 變成 σ(z + Δz) 的示意圖](img-010)
*調皮的小精靈在 Neuron 的輸入加料*

這個小精靈非常調皮，會將這一個 Neuron 的輸入「加料」，使得這一個 Neuron 最終的輸出 (Activation) 由 σ(z) 變成 σ(z + Δz)。因為這一個 Neuron 的輸出改變了，後面的 Neuron 輸出也會跟著改變，一路影響到最後算出來的 Cost Function 數值。Cost Function 的改變量為：z 的 Gradient 乘以 z 的變化量，即 **∂C/∂z × Δz**。

幸運的是，這一個小精靈雖然調皮但是生性善良，它希望透過加入正確的料（Δz），讓 Cost Function 的數值愈小愈好。如果 ∂C/∂z 是一個正數，表示 z 變大 C 也跟著變大，此時小精靈就會讓 Δz 是一個負數；如果 ∂C/∂z 是一個負數，表示 z 變大 C 會變小，此時小精靈就會讓 Δz 是一個正數。簡單來說，**小精靈只要讓 Δz 的方向（正負號）與 ∂C/∂z 相反，就可以讓 Cost Function 的數值下降**。而如果 ∂C/∂z 已經趨近於 0，就表示小精靈已經不需要再替這一個 Neuron 的輸入加料了。

仔細想想，小精靈是怎麼替 Neuron 的輸入加料的？不就是調整這一個 Neuron 的 Weight 與 Bias 嗎！所以當 ∂C/∂z 趨近於 0，代表不需要再更改這一個 Neuron 的 Weight 與 Bias，言下之意就是：這一個 Neuron 的 Weight 與 Bias 已經很棒了。

因此，我們用 **δ** 來表示 **∂C/∂z**，代表這個 Neuron 目前的 Error：如果 δ 很大（不管是「正」的方向還是「負」的方向），表示這一個 Neuron 的 Weight 與 Bias 仍需要調整；相反的，如果 δ 趨近於 0，表示這一個 Neuron 的 Weight 與 Bias 已經不需要調整。

![Backpropagation 的四大公式 BP(1) 到 BP(4)，並列在同一張圖中](img-008)
*Backpropagation 演算法四大公式*

帶著 δ 的意義再回頭看這四個公式，就會發現它們全部圍繞著 δ 打轉：先算出每個 Neuron 的 Error，再依據這個 Error 算出 Cost 對 Weight 與 Bias 的偏微分，最後決定參數要怎麼更新。

看到這裡如果都還可以接受，那麼前置作業就完成了。接下來從第一號公式開始。

## Backpropagation 公式 1（BP 1）

Backpropagation 演算法中的第一個公式為：

![Backpropagation 公式 BP(1)，計算 Output Layer 中 Neuron 的 Error δ](img-011)
*Backpropagation 公式 1*

BP(1) 是用來計算 Neural Network 中最後一個 Layer（Output Layer）中 Neuron 的 Error。整條推導鏈的起點就在這裡：先把最後一層的 Error 算出來，才有東西可以往回傳。

![Output Layer 中 Neuron 的 z、a 與 C 三者計算關係的算式](img-012)
*Output Layer 中 Neuron 的 z (Weighted Input)、a (Activation) 與 C (Cost Function) 的計算*

上圖呈現的是 Output Layer 中的第一個（也是唯一一個）Neuron 的 Weighted Input (z) 與 Activation (a) 的計算方式。因為這是 Output Layer 的 Neuron，它的輸出可以直接與正確答案比對，算出目前的 Cost。

我們已經知道 **δ（BP(1) 的左式）**就是 **∂C/∂z**。問題是，在計算 C 的式子裡並沒有出現 z（因為 z 被包在 a 裡面），沒辦法直接對 z 做偏微分。這時候就輪到微積分的 [Chain Rule](https://zh.wikipedia.org/zh-tw/%E9%93%BE%E5%BC%8F%E6%B3%95%E5%88%99) 上場：「C 對 z 的偏微分」等於「C 對 a 的偏微分」乘以「a 對 z 的偏微分」。

![以 Chain Rule 展開 ∂C/∂z 為 ∂C/∂a 乘以 ∂a/∂z 的推導算式](img-013)
*透過 Chain Rule 計算 C 對 z 的偏微分*

如此一來，第一個公式是怎麼來的就清楚了。**透過 BP(1) 我們可以計算一個 Neural Network 中 Output Layer 裡的 Neuron 的 Error**。

## Backpropagation 公式 2（BP 2）

Backpropagation 演算法中的第二個公式為：

![Backpropagation 公式 BP(2)，由後一層的 Error 回推前一層 Neuron 的 Error](img-014)
*Backpropagation 公式 2*

由 BP(1) 我們已經知道如何計算 Output Layer 中 Neuron 的 Error，BP(2) 則是根據目前 Layer 中 Neuron 的 Error，往回計算前一個 Layer 中 Neuron 的 Error。有了 BP(1) 與 BP(2)，就能像骨牌一樣從最後一層一路往回推，把 Neural Network 中所有 Neuron 的 Error 都算出來。Backpropagation（誤差反向傳播）這個名字也正是從這裡來的。

![示意圖，箭頭由 L=3 的 Error 指向 L=2 的 Error，表示誤差往回傳遞](img-015)
*利用 BP(2) 我們可以根據 L=3 的 Error 推算 L=2 的 Error*

如上圖所示，透過 BP(1) 我們已經計算出 L=3 的 Error，BP(2) 說明如何透過 L=3 的 Error 回推 L=2 的 Error。

![四條標號 ① 到 ④ 的算式，呈現第二層第一個 Neuron 的 z 一路連到 Cost 的關係](img-016)
*第二個 Layer 中第一個 Neuron 的 z 與 Cost 的關係*

在第二個 Layer（L = 2）中有兩個 Neuron，我們就聚焦在第一個 Neuron，理解這個 Neuron 的 Error 是如何計算出來的。上圖的四個公式（① ~ ④）呈現的是這個 Neuron 的 z 與 Cost Function 的關係（其中 ② ~ ④ 在 BP(1) 已經介紹過）。

![以 Chain Rule 將 Cost 對 Hidden Layer Neuron 的 z 偏微分展開成連乘形式的算式](img-017)
*透過 Chain Rule 計算 Cost 對 Hidden Layer 中 Neuron 的 z 的偏微分*

跟 BP(1) 遇到的狀況一樣，Cost Function 沒有辦法直接對這個 Neuron 的 z 計算偏微分，所以同樣要靠 [Chain Rule](https://zh.wikipedia.org/zh-tw/%E9%93%BE%E5%BC%8F%E6%B3%95%E5%88%99) 幫忙（如上圖所示）。

![改寫後的算式，將 ③ 乘以 ④ 的部分直接代換為 BP(1) 已算出的結果](img-018)
*③ 乘以 ④ 的結果我們在 BP(1) 時就算出來了*

又因為 ③ 乘以 ④ 的結果我們在 BP(1) 時就算出來了，因此可以直接代換進來，把算式改寫成上圖的樣子。這也是 Backpropagation 之所以快的關鍵：後面算過的東西不必重算，直接拿來用。

![計算 ① 與 ② 兩式偏微分的推導過程](img-019)
*計算 ① 與 ② 的偏微分*

剩下的 ① 與 ② 都是很單純的式子，偏微分可以直接算出來。到這裡，我們再回頭看看 Backpropagation 的第二個公式：

![Backpropagation 公式 BP(2)，由後一層的 Error 回推前一層 Neuron 的 Error](img-014)
*Backpropagation 公式 2*

推導其實已經做完了，但你可能覺得跟上圖有點對不起來。那是因為上圖的公式是用「矩陣」與「向量」的形式表達，我們剛才則是針對單一個 Neuron 展開，實際的運算原理完全相同。**透過 BP(2) 我們可以計算一個 Neural Network 中 Hidden Layer 裡的 Neuron 的 Error**。

換言之，透過 BP(1) 與 BP(2) 我們就可以算出整個 Neural Network 所有 Layer、所有 Neuron 的 Error。接下來的 BP(3) 與 BP(4)，則是利用這些 Error 算出我們真正想要的東西：**∂C/∂w 與 ∂C/∂b**。

## Backpropagation 公式 3（BP 3）

Backpropagation 演算法中的第三個公式為：

![Backpropagation 公式 BP(3)，Cost 對 Bias 的偏微分等於該 Neuron 的 Error δ](img-020)
*Backpropagation 公式 3*

BP(3) 說明了 Cost Function 對 Bias 的偏微分其實就是這個 Neuron 的 Error。連乘都不用，直接相等。為什麼會這麼乾淨？

![以 Chain Rule 推導 Cost 對 Bias 偏微分的算式，標號 ① 到 ③](img-021)
*透過 Chain Rule 計算 Cost 對 Bias 的偏微分*

如上圖所示，算式 ① ～ ③ 呈現的是 Output Layer 中第一個 Neuron 的 Bias 與 Cost 的關係。跟前面 BP(2) 的做法相同，C 無法直接對這個 Bias 偏微分，所以透過 Chain Rule 來計算。展開之後會發現，z 對 b 的偏微分剛好是 1，整條式子收斂成 **∂C/∂b 其實就是 δ**。

透過 BP(3) 我們可以計算 Cost Function 對 Neural Network 中所有 Bias 的偏微分，進而知道每個 Bias 該往哪個方向更新。

## Backpropagation 公式 4（BP 4）

Backpropagation 演算法中的第四個公式為：

![Backpropagation 公式 BP(4)，Cost 對 Weight 的偏微分等於前一層的 Activation 乘以該 Neuron 的 Error](img-022)
*Backpropagation 公式 4*

終於來到最後一個公式。BP(4) 說明 Cost Function 對 Weight 的偏微分，就是這個 Neuron 的 Error 再乘以「輸入的 Activation」。

![以 Chain Rule 推導 Cost 對 Weight 偏微分的算式，標號 ① 到 ③](img-023)
*透過 Chain Rule 計算 Cost 對 Weight 的偏微分*

如上圖所示，算式 ① ～ ③ 呈現的是 Output Layer 中第一個 Neuron 的第一個 Weight 與 Cost 的關係。因為 C 無法直接對這個 Weight 偏微分，所以一樣透過 Chain Rule 來計算。你會發現整個過程基本上與 BP(3) 一模一樣，差別只在最後一步微分出來的不是 1，而是前一層的 Activation。

透過 BP(4) 我們可以計算 Cost Function 對 Neural Network 中所有 Weight 的偏微分，進而知道每個 Weight 該如何更新。

## 結論

Backpropagation 演算法的原理到這裡就介紹完了。整套流程可以濃縮成兩句話：先用 BP(1) 算出 Output Layer 的 Error，再用 BP(2) 把 Error 一層一層往回傳；有了每個 Neuron 的 Error，BP(3) 與 BP(4) 就能直接換算出 Cost 對每個 Bias 與 Weight 的偏微分，交給 Gradient Descent 去更新參數。

相信讀到這邊的你，再看一次這張圖，應該已經能夠讀懂每一個公式的意義：

![Backpropagation 的四大公式 BP(1) 到 BP(4)，並列在同一張圖中](img-008)
*Backpropagation 演算法四大公式*

如果還是有不懂的地方，千萬不要覺得氣餒。畢竟你願意深入理解 Neural Network 的更新過程，就已經超越許多「呼叫套件學 AI」的人了。這個主題本來就需要反覆讀幾次才能完全消化，過幾天再回來看一次，感受會很不一樣。

### 參考資料

- [Neural networks and deep learning (CH2)](http://neuralnetworksanddeeplearning.com/chap2.html)
- [Learning representations by back-propagating errors](https://www.nature.com/articles/323533a0)

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "有 3 個 Layer 的 Neural Network",
    "why_used": "建立全文的討論對象，讓讀者先看到這篇文章要拆解的三層 Neural Network 長什麼樣子，並帶出用小寫 L 表示 Layer 的符號約定。",
    "agent_match_hint": "一張三層神經網路示意圖，圓形 Neuron 分層排列並以線段相連，標示 L 的編號。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "利用 w 來表示 Neural Network 中的 Weight",
    "why_used": "定義 Weight 符號 w 的上下標意義，是後面 BP(2) 與 BP(4) 公式能讀懂的前提。",
    "agent_match_hint": "神經網路示意圖，其中一條連線被標上 w 及其上下標 (L、j、k)。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "用 b 來表示 Neural Network 中的 Bias",
    "why_used": "定義 Bias 符號 b 的上下標意義，對應後面 BP(3) 對 Bias 的偏微分。",
    "agent_match_hint": "神經網路示意圖，Neuron 旁標示 b 及其上下標。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "利用 a 表示 Neural Network 的 Activation",
    "why_used": "定義 Activation 符號 a，與 Bias 採相同的下標形式，供後續算式引用。",
    "agent_match_hint": "神經網路示意圖，Neuron 的輸出端標示 a 及其上下標。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "計算 Neural Network 中的 Activation",
    "why_used": "呈現 Activation 的原始計算式（Weighted Sum 加 Bias 後通過 Sigmoid），是後面所有推導的起點。",
    "agent_match_hint": "一張數學算式圖，內容為前一層 Activation 的加權總和加上 Bias 再套上 σ()。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "用 Vector 與 Matrix 表示 Activation 的計算",
    "why_used": "說明如何把整層的運算寫成矩陣與向量形式，讓後面四大公式的矩陣寫法不至於突兀。",
    "agent_match_hint": "一張算式圖，以粗體的矩陣 w、向量 a 與 b 表示整層 Activation 的計算。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "用 z 表示 Neuron 的 Weighted Input",
    "why_used": "引入 Weighted Input 符號 z，並把 Activation 化簡成 σ(z)，這是 δ ≡ ∂C/∂z 定義的基礎。",
    "agent_match_hint": "一張算式圖，定義 z 為 Sigmoid Function 內部的內容，並寫出 a = σ(z)。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Backpropagation 演算法四大公式",
    "why_used": "全文的核心圖，先整體呈現 BP(1) 到 BP(4)，後續在解釋完 δ 的意義與全文結尾時再次回顧同一張圖。",
    "agent_match_hint": "一張並列四條數學公式的圖，分別標註 BP(1)、BP(2)、BP(3)、BP(4)。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "想像 Neural Network 中住著一個小精靈",
    "why_used": "用小精靈的比喻開場，把抽象的 δ 轉成讀者能想像的畫面。",
    "agent_match_hint": "神經網路示意圖，第二層的某個 Neuron 上畫著一隻卡通小精靈。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "調皮的小精靈在 Neuron 的輸入加料",
    "why_used": "圖解小精靈對 Weighted Input 加上 Δz 之後，輸出如何由 σ(z) 變成 σ(z + Δz)，帶出 Cost 改變量與 ∂C/∂z 的關係。",
    "agent_match_hint": "神經網路示意圖，Neuron 旁標示 Δz，輸出由 σ(z) 改寫為 σ(z + Δz)。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "Backpropagation 公式 1",
    "why_used": "單獨呈現 BP(1)，作為 Output Layer Error 計算的討論起點。",
    "agent_match_hint": "一張只有一條公式的圖，內容為 Output Layer 的 δ 計算式，標註 BP(1)。"
  },
  {
    "id": "img-012",
    "references_manifest_caption": "Output Layer 中 Neuron 的 z (Weighted Input)、a (Activation) 與 C (Cost Function) 的計算",
    "why_used": "把 Output Layer 中 z、a、C 的關係攤開，說明為什麼 C 無法直接對 z 偏微分。",
    "agent_match_hint": "數條標號算式，依序寫出 Output Layer Neuron 的 z、a 以及 Cost 的計算方式。"
  },
  {
    "id": "img-013",
    "references_manifest_caption": "透過 Chain Rule 計算 C 對 z 的偏微分",
    "why_used": "呈現 BP(1) 的推導核心：用 Chain Rule 把 ∂C/∂z 拆成 ∂C/∂a 乘以 ∂a/∂z。",
    "agent_match_hint": "一張推導算式圖，將 ∂C/∂z 展開為兩個偏微分相乘的形式。"
  },
  {
    "id": "img-014",
    "references_manifest_caption": "Backpropagation 公式 2",
    "why_used": "單獨呈現 BP(2)，在小節開頭引入誤差往回傳的公式，並在推導結束後再次回顧以對照矩陣形式。",
    "agent_match_hint": "一張只有一條公式的圖，內容為由 L+1 層的 δ 推得 L 層 δ 的算式，標註 BP(2)。"
  },
  {
    "id": "img-015",
    "references_manifest_caption": "利用 BP(2) 我們可以根據 L=3 的 Error 推算 L=2 的 Error",
    "why_used": "用圖示說明誤差反向傳遞的方向，讓讀者對「往回推」有具體畫面。",
    "agent_match_hint": "神經網路示意圖，箭頭由第三層指回第二層，兩層分別標示 Error。"
  },
  {
    "id": "img-016",
    "references_manifest_caption": "第二個 Layer 中第一個 Neuron 的 z 與 Cost 的關係",
    "why_used": "把 Hidden Layer 中單一 Neuron 的 z 一路連到 Cost 的算式列出來，作為後續 Chain Rule 展開的依據。",
    "agent_match_hint": "四條以 ① 到 ④ 標號的算式，串起 Hidden Layer Neuron 的 z 與 Cost。"
  },
  {
    "id": "img-017",
    "references_manifest_caption": "透過 Chain Rule 計算 Cost 對 Hidden Layer 中 Neuron 的 z 的偏微分",
    "why_used": "呈現 BP(2) 的推導核心，說明 Hidden Layer 的 δ 同樣要靠 Chain Rule 展開。",
    "agent_match_hint": "一張推導算式圖，將 Cost 對 Hidden Layer z 的偏微分展開成多個偏微分連乘。"
  },
  {
    "id": "img-018",
    "references_manifest_caption": "③ 乘以 ④ 的結果我們在 BP(1) 時就算出來了",
    "why_used": "支撐「後面算過的結果可以直接重複利用」這個 Backpropagation 效率的關鍵論點。",
    "agent_match_hint": "一張算式改寫圖，將原本兩項的乘積代換成 BP(1) 已求得的 δ。"
  },
  {
    "id": "img-019",
    "references_manifest_caption": "計算 ① 與 ② 的偏微分",
    "why_used": "補完 BP(2) 推導的最後一步，說明剩下兩項的偏微分可以直接算出。",
    "agent_match_hint": "一張推導算式圖，分別對兩條標號算式取偏微分並寫出結果。"
  },
  {
    "id": "img-020",
    "references_manifest_caption": "Backpropagation 公式 3",
    "why_used": "單獨呈現 BP(3)，帶出 Cost 對 Bias 的偏微分等於 δ 這個結論。",
    "agent_match_hint": "一張只有一條公式的圖，內容為 ∂C/∂b 等於 δ，標註 BP(3)。"
  },
  {
    "id": "img-021",
    "references_manifest_caption": "透過 Chain Rule 計算 Cost 對 Bias 的偏微分",
    "why_used": "呈現 BP(3) 的推導過程，解釋為什麼結果會乾淨地收斂成 δ。",
    "agent_match_hint": "以 ① 到 ③ 標號的算式，透過 Chain Rule 展開 Cost 對 Bias 的偏微分。"
  },
  {
    "id": "img-022",
    "references_manifest_caption": "Backpropagation 公式 4",
    "why_used": "單獨呈現 BP(4)，帶出 Cost 對 Weight 的偏微分等於 Error 乘以輸入 Activation。",
    "agent_match_hint": "一張只有一條公式的圖，內容為 ∂C/∂w 等於前一層 Activation 乘以 δ，標註 BP(4)。"
  },
  {
    "id": "img-023",
    "references_manifest_caption": "透過 Chain Rule 計算 Cost 對 Weight 的偏微分",
    "why_used": "呈現 BP(4) 的推導過程，並對照出它與 BP(3) 只差在最後一步微分結果。",
    "agent_match_hint": "以 ① 到 ③ 標號的算式，透過 Chain Rule 展開 Cost 對 Weight 的偏微分。"
  }
]
```
