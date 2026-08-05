---
title: Backpropagation 介紹 —— 看懂如何透過 Backpropagation 計算 Gradient
date: '2022-07-15T03:43:07'
lastmod: '2022-07-15T05:55:19'
slug: backpropagation-explain
draft: false
categories:
- 深度學習核心觀念
tags:
- Deep Learning
- Gradient Descent
- Machine Learning
description: 前言 在前面幾篇文章中，我們已經了解到如何透過 Gradient Descent 與 Stochastic Gradient Descent
  更新 Neural Network 中的參數，然而我們都只是在概念上描述 Weight 與 Bias 的 Gradient 如何被計算出來，而沒有介紹到它們實際的運算方式。因此，在本篇文章中我們將介紹如何透過
  Backpropagation 演算法計算出 Neural Network 中所有參數的 Gradient。 AD Backpropagation 是什麼 Backpropagation
  是一種能夠快速計算 Gradient 的演算法。為什麼我們需要它呢？試著想想，現在的 Neural Network 隨隨便便就有上千萬個參數，每次要更新參數時，就必須計算一次這個參數的
  Gradient（Cost Function 對該參數的偏微分），如果不透過一個有效率、更快速的方法來計算所有參數的 Gradient，那麼將會導致 Neural
  Network 的訓練時間非常的久，使得 Deep Learning 變得不可行。 Backpropagation 演算法早在 1970 年代久已經出現，但是一直到
  David Rumelhart、Geoffrey Hinton、Ronald Williams 等人於 1986 年共同發表了 […]
aliases:
- /deep-learning-core-concept/backpropagation-explain/
original_url: http://54.150.87.240/deep-learning-core-concept/backpropagation-explain/
wp_id: 1107
images:
- images/backpropagation-formula-1.png
- images/backpropagation-formula-2.png
- images/backpropagation-formula-3.png
- images/backpropagation-formula-4.png
- images/backpropagation-formula.png
- images/calculate-activation-2.png
- images/calculate-activation.png
- images/explain-backpropagation-formula-1.png
- images/feature-image.jpg
- images/neural-network-with-activation.png
- images/neural-network-with-bias.png
- images/neural-network-with-weight-1.png
- images/neural-network.png
- images/understand-backpropagation-2.png
- images/understand-backpropagation-formula-1-1.png
- images/understand-backpropagation-formula-2-1.png
- images/understand-backpropagation-formula-2-3.png
- images/understand-backpropagation-formula-2-4.png
- images/understand-backpropagation-formula-2-5.png
- images/understand-backpropagation-formula-2.png
- images/understand-backpropagation-formula-3.png
- images/understand-backpropagation-formula-4.png
- images/understand-backpropagation.png
- images/weighted-input-of-neuron.png
---

![feature image](images/feature-image.jpg)

source: Pixabay

## 前言

在前面幾篇文章中，我們已經了解到如何透過 [Gradient Descent](http://54.150.87.240/deep-learning-core-concept/deep-learning-gradient-descent/) 與 [Stochastic Gradient Descent](http://54.150.87.240/deep-learning-core-concept/stochastic-gradient-descent-%e4%bb%8b%e7%b4%b9/) 更新 Neural Network 中的參數，然而我們都只是在概念上描述 Weight 與 Bias 的 Gradient 如何被計算出來，而沒有介紹到它們實際的運算方式。因此，在本篇文章中我們將介紹如何透過 Backpropagation 演算法計算出 Neural Network 中所有參數的 Gradient。

AD

## Backpropagation 是什麼

**Backpropagation 是一種能夠快速計算 Gradient 的演算法**。為什麼我們需要它呢？試著想想，現在的 Neural Network 隨隨便便就有**上千萬個參數**，每次要更新參數時，就必須計算一次這個參數的 Gradient（Cost Function 對該參數的偏微分），如果不透過一個有效率、更快速的方法來計算所有參數的 Gradient，那麼將會導致 Neural Network 的訓練時間非常的久，使得 Deep Learning 變得不可行。

Backpropagation 演算法早在 1970 年代久已經出現，但是一直到 David Rumelhart、Geoffrey Hinton、Ronald Williams 等人於 1986 年共同發表了 [Learning representations by back-propagating errors](https://www.nature.com/articles/323533a0) 論文之後，Backpropagation 演算法才受到重視。這篇論文主要在描述利用 Backpropagation 演算法讓 Neural Network 學的更快，讓我們可以進一步使用 Neural Network 來解決問題。

在本篇文章中我們將一步步介紹 Backpropagation 演算法是什麼，幫助你更了解 Neural Network 中的參數是如何被更新的。然而，因為 Backpropagation 演算法的觀念較為複雜，也許沒有辦法看一次就完全明白，尤其當你是第一次試著理解 Backpropagation 演算法時，經常會迷失在一大堆的數學符號與數字當中。因此，看一次不懂沒關係，透過多次的消化理解就能掌握 Backpropagation 演算法的意義。

即使如此，我們還是可以記住一個大原則：**Backpropagation 就是一種能夠快速計算 Gradient 的演算法，也就是如何快速的算出 ∂C/∂w 與 ∂C/∂b。**有了 ∂C/∂w 與 ∂C/∂b，我們就能夠知道當 Weight (w) 與 Bias (b) 變化時，Cost Function 的數值會增加還是減少，增加多少以及減少多少。

## 計算 Neural Network 的輸出

在了解 Backpropagation 演算法之前，讓我們先確定你已經了解 Neural Network 的輸出是如何計算出來的，也順便定義一些在本篇文章中會使用到的數學符號。

![三層神經網路](images/neural-network.png)

有 3 個 Layer 的 Neural Network

如上圖所示，這是一個有 3 個 Layer 的 Neural Network，我們用「小寫 L」來表示第幾個 Layer。

![利用 w 來表示 Neural Network 中的 Weight](images/neural-network-with-weight-1.png)

利用 w 來表示 Neural Network 中的 Weight

我們利用 w 來表示 Neural Network 中的 Weight，其形式為 L – 1 Layer 中的第 k 個 Neuron 連接到 L Layer 中第 j 個 Neuron 的 Weight。

![Neural Network 中的 Bias](images/neural-network-with-bias.png)

用 b 來表示 Neural Network 中的 Bias

我們利用 b 來表示 Neural Network 中的 Bias，其形式為 L Layer 中的第 k 個 Neuron 的 Bias。

![利用 a 表示 Neural Network 中的 Activation](images/neural-network-with-activation.png)

利用 a 表示 Neural Network 的 Activation

我們利用 a 來表示 Neural Network 中的 Activation，其形式與 Bias 相同，都是指 L Layer 中的第 k 個 Neuron。

![計算 Neural Network 中的 Activation](images/calculate-activation.png)

計算 Neural Network 中的 Activation

Activation 的計算方式如上圖所示：前一個 Layer Activation 的 Weighted Sum 再加上 Bias，最後經過一個 Activation Function（我們這裡使用 [Sigmoid Function](http://54.150.87.240/deep-learning-core-concept/understand-sigmoid-neuron/)）。

為了方便起見，我們可以用 Matrix 或是 Vector 來表示整個 Layer 的資訊。例如，我們用 wl 表示 L Layer 中的所有 Weight，wljk則是 wl 中第 j 個 Row、第 k 個 Col 的元素；用 bl 表示 L Layer 中的所有 Bias；al 表示 L Layer 中的所有 Activation。透過 Matrix 與 Vector 的形式，我們可以如此表示 Activation 的計算方式：

![用 Vector 與 Matrix 表示 Activation 的計算](images/calculate-activation-2.png)

用 Vector 與 Matrix 表示 Activation 的計算

用這樣的方式我們可以更清楚地發現，原來這一個 Layer 的 Activation 其實就是前一個 Layer 的 Activation 乘以 Weight 後再加上 Bias，最後通過 Sigmoid Function。是不是變得相當簡單呀！

AD

為了方便下文的介紹，我們再定義一個符號。我們將上圖 Activation 算式中 Sigmoid Function 裡面的內容定義為 z。換句話說，zl ≡ wl al-1 + bl。我們可以將 zl 想成是 L Layer 中 Neuron 的 Weighted Input。有了 zl，我們又可以更進一步簡化 Activation 的計算：al = σ(zl)（如下圖所示）。

![用 z 表示 Neuron 的 Weighted Input](images/weighted-input-of-neuron.png)

用 z 表示 Neuron 的 Weighted Input

## Backpropagation 中四個重要的公式

到這裡，我們已經完成的大腦的暖身（希望你的思緒還相當清晰）！還記得我們在一開使提過，Backpropagation 演算法的目的就是要快速的計算 Neural Network 中每一個參數的 Gradient（Cost Function 對該參數的偏微分）。Backpropagation 演算法主要包含以下四個重要的公式，正是透過這四個公式計算出所有的 **∂C/∂w 與 ∂C/∂b：**

![Backpropagation 演算法四大公式](images/backpropagation-formula.png)

Backpropagation 演算法四大公式

別急，現在的你一定看不懂這四個公式，但是我保證只要你靜下心來，認真的看完整篇文章，你一定會完全了解這四個公式的意義！不過，在開始介紹這四個公式之前，我們先憑「直覺」簡單觀察這些公式。

首先，BP(3) 與 BP(4) 都是在計算 Cost Function 會 Neural Network 中參數 (Weight 與 Bias) 的偏微分，不就是我們希望計算的 Gradient 嗎？！此外，我們也發現他們都與 **δ** 相關。再回頭看看 BP(1) 與 BP(2)，我們發現他們都是在計算 **δ**。

究竟 **δ** 是什麼東西，為什麼在 Backpropagation 中四個重要的公式中都有它的存在呢？因此，在開始詳細介紹 BP(1) 到 BP(4) 之前，我們先來了解 **δ** 的意義。

![想像 Neural Network 中住著一個小精靈](images/understand-backpropagation.png)

想像 Neural Network 中住著一個小精靈

我們想像在 Neural Network 中住著一個小精靈，如上圖所示，小精靈住在第二個 Layer 的第二個 Neuron。

![調皮的小精靈在 Neuron 的輸入加料](images/understand-backpropagation-2.png)

調皮的小精靈在 Neuron 的輸入加料

這個小精靈非常調皮，會將這一個 Neuron 的輸入「加料」，使得這一個 Neuron 最終的輸出 (Activation) 由 σ(z) 變成 σ(z + Δz)。因為這一個 Neuron 的輸出改變了，使得後面的 Neuron 的輸出也會跟著改變，導致最後計算出來的 Cost Function 數值也會改變。Cost Function 的改變量為：z 的 Gradient 乘以 z 的變化量，即 **∂C/∂z × Δz**。

幸運的是，這一個小精靈雖然調皮但是生性善良，它希望透過加入正確的料（Δz**）**，使得 Cost Function 的數值愈小愈好。如果 ∂C/∂z 是一個正數，表示 z 變大 C 也跟著變大，此時小精靈就會讓 Δz 是一個負數；如果 ∂C/∂z 是一個負數，表示 z 變大 C 會變小，此時小精靈就會讓 Δz 是一個正數。簡單來說，**小精靈只要讓 Δz 的方向（正負號）與 ∂C/∂z 相反，就可以讓 Cost Function 的數值下降**。**如果 ∂C/∂z 已經趨近於 0，就表示小精靈已經不需要再替這一個 Neuron 的輸入加料**。

仔細想想，小精靈是如何替 Neuron 的輸入加料呢？不就是調整這一個 Neuron 的 Weight 與 Bias！當 ∂C/∂z 已經趨近於 0，小精靈就不需要再替這一個 Neuron 的輸入加料，也就是不需要再更改這一個 Neuron 的 Weight 與 Bias。言下之意，就是這一個 Neuron 的 Weight 與 Bias 已經很棒了！

AD

因此，我們用 **δ** 來表示 **∂C/∂z****，表示 Neuron 目前的 Error：**如果 δ 很大（不管是「正」的方向還是「負」的方向），表示這一個 Neuron 的 Weight 與 Bias 仍需要調整；相反的，如果 δ 趨近於 0，表示這一個 Neuron 的 Weight 與 Bias 已經不需要調整。

![Backpropagation 演算法四大公式](images/backpropagation-formula.png)

Backpropagation 演算法四大公式

再回顧 Backpropagation 演算法的四個公式，你可以發現其實他們都是圍繞著 **δ**，也就是根據 Neuron 的 Error，計算出 Cost 對 Weight 與 Bias 的偏微分，影響了參數會如何被更新。

看到這裡如果都還可以接受的話，恭喜你已經完成了「了解 Backpropagation 中四個重要的公式」的前置作業。接下來，讓我們繼續學習 Backpropagation 的第一號公式。

## Backpropagation 公式 1（BP 1）

Backpropagation 演算法中的第一個公式為：

![Backpropagation 公式 1](images/backpropagation-formula-1.png)

Backpropagation 公式 1

BP(1) 是用來計算 Neural Network 中最後一個 Layer**（Output Layer）中 Neuron 的 Error**。

![Output Layer 中 Neuron 的 z (Weighted Input)、a (Activation) 與 C (Cost Function) 的計算](images/understand-backpropagation-formula-1-1.png)

Output Layer 中 Neuron 的 z (Weighted Input)、a (Activation) 與 C (Cost Function) 的計算

上圖呈現的是 Output Layer 中的第一個（也是唯一一個）Neuron 的 Weighted Input (z) 與 Activation (a) 的計算方式。因為這是 Output Layer 的 Neuron，因此 Neuron 的輸出又可以與正確答案比對，計算出目前的 Cost。

我們已經知道 **δ (BP1 的左式)** 就是 **∂C/∂z**，然而在計算 C 的式子中，我們並沒有看到 z（因爲 z 包含在 a 中），因此沒有辦法直接對 z 計算偏微分。然而，根據微積分的 [Chain Rule](https://zh.wikipedia.org/zh-tw/%E9%93%BE%E5%BC%8F%E6%B3%95%E5%88%99)，「C 對 z 的偏微分」等於「C 對 a 的偏微分」乘以「a 對 z 的偏微分」：

![透過 Chain Rule 計算 C 對 z 的偏微分](images/explain-backpropagation-formula-1.png)

透過 Chain Rule 計算 C 對 z 的偏微分

如此一來，我們就理解了 Backpropagation 演算法中的第一個公式是怎麼來的！**透過 BP(1) 我們可以計算一個 Neural Network 中 Output Layer 裡的 Neuron 的 Error**。

AD

## Backpropagation 公式 2（BP 2）

Backpropagation 演算法中的第二個公式為：

![Backpropagation 公式 2](images/backpropagation-formula-2.png)

Backpropagation 公式 2

由 BP(1) 我們已經知道如何計算 Output Layer 中 Neuron 的 Error，BP(2) 則是根據目前 Layer 中 Neuron 的 Error，來計算前一個 Layer 中 Neuron 的 Error。透過 BP(1) 與 BP(2)，我們就能夠計算出 Neural Network 中所有 Neuron 的 Error。

![利用 BP(2) 我們可以根據 L=3 的 Error 推算 L=2 的 Error ](images/understand-backpropagation-formula-2.png)

利用 BP(2) 我們可以根據 L=3 的 Error 推算 L=2 的 Error

如上圖所示，透過 BP(1) 我們已經計算出 L=3 的 Error，BP(2) 說明如何透過 L=3 的 Error 回推 L=2 的 Error。

![第二個 Layer 中第一個 Neuron 的 z 與 Cost 的關係](images/understand-backpropagation-formula-2-1.png)

第二個 Layer 中第一個 Neuron 的 z 與 Cost 的關係

在第二個 Layer（L = 2）中有兩個 Neuron，我們就聚焦在第一個 Neuron，理解這個 Neuron 的 Error 是如何計算出來的。在上圖的四個公式（① ~ ④）呈現的是這個 Neuron 的 z 與 Cost Function 的關係（②～④ 在 BP(1) 已經介紹過）。

![透過 Chain Rule 計算 Cost 對 Hidden Layer 中 Neuron 的 z 的偏微分](images/understand-backpropagation-formula-2-3.png)

透過 Chain Rule 計算 Cost 對 Hidden Layer 中 Neuron 的 z 的偏微分

因為 Cost Function 沒有辦法直接對這個 Neuron 的 z 計算偏微分，因此同樣必須透過微積分中的 [Chain Rule](https://zh.wikipedia.org/zh-tw/%E9%93%BE%E5%BC%8F%E6%B3%95%E5%88%99)，幫助我們計算（如上圖所示）。

![③ 乘以 ④的結果我們在 BP(1) 時就算出來了](images/understand-backpropagation-formula-2-4.png)

③ 乘以 ④的結果我們在 BP(1) 時就算出來了

又因為 ③ 乘以 ④的結果我們在 BP(1) 時就算出來了，因此可將算式改寫（如上圖所示）。

![計算 ① 與 ② 的偏微分](images/understand-backpropagation-formula-2-5.png)

計算 ① 與 ② 的偏微分

根據 ① 與 ② 的算式，我們可以輕鬆計算出其偏微分！到這裡，我們再回頭看看 Backpropagation 的第二個公式：

![Backpropagation 公式 2](images/backpropagation-formula-2.png)

Backpropagation 公式 2

其實我們已經解釋完 BP(2) 的公式，然而你可能覺得有點對不起來。主要是因為在上圖公式中是用「矩陣」與「向量」的形式表達，實際的運算原理是完全相同的！如此一來，我們就理解了 Backpropagation 演算法中的第二個公式是怎麼來的！**透過 BP(2) 我們可以計算一個 Neural Network 中 Hidden Layer 裡的 Neuron 的 Error**。

換言之，透過 BP(1) 與 BP(2) 我們就可以計算出整個 Neural Network 所有 Layer、所有 Neuron 的 Error，BP(3) 與 BP(4) 則是再利用這些 Error 算出我們最後想的東西：**∂C/∂w 與 ∂C/∂b**。

AD

## Backpropagation 公式 3（BP 3）

Backpropagation 演算法中的第三個公式為：

![Backpropagation 公式 3](images/backpropagation-formula-3.png)

Backpropagation 公式 3

BP(3) 說明了 Cost Function 對 Bias 的偏微分其實就是這個 Neuron 的 Error 啊！為什麼呢？

![透過 Chain Rule 計算 Cost 對 Bias 的偏微分](images/understand-backpropagation-formula-3.png)

透過 Chain Rule 計算 Cost 對 Bias 的偏微分

如上圖所示，算式 ① ～ ③ 呈現的是 Output Layer 中第一個 Neuron 的 Bias 與 Cost 的關係。與前面 BP(2) 的概念相同，C 無法直接對這個 Bias 偏微分，因此透過 Chain Rule 來計算。由 Chain Rule 最後的計算結果，我們發現 **∂C/∂b 其實就是 δ**。

透過 BP(3) 我們可以計算 Cost Function 對 Neural Network 中所有的 Bias 的偏微分，進而了解應該如何更新 Bias。

AD

## Backpropagation 公式 4（BP 4）

Backpropagation 演算法中的第四個公式為：

![Backpropagation 公式 4](images/backpropagation-formula-4.png)

Backpropagation 公式 4

終於來到了最後一個公式！BP(4) 說明 Cost Function 對 Weight 的偏微分這個 Neuron 的 Error 再乘以「輸入的 Activation」。

![透過 Chain Rule 計算 Cost 對 Weight 的偏微分](images/understand-backpropagation-formula-4.png)

透過 Chain Rule 計算 Cost 對 Weight 的偏微分

如上圖所示，算式 ① ～ ③ 呈現的是 Output Layer 中第一個 Neuron 的第一個 Weight 與 Cost 的關係。因為 C 無法直接對這個 Weight 偏微分，因此透過 Chain Rule 來計算。你可以發現 Chain Rule 的計算過程基本上與 BP(3) 一樣！

透過 BP(4) 我們可以計算 Cost Function 對 Neural Network 中所有的 Weight 的偏微分，進而了解應該如何更新 Weight。

AD

## 結語

恭喜你！我們已經介紹完了 Backpropagation 演算法的原理，相信讀到這邊的你再看一次這張圖已經能夠每一個公式的意義：

![Backpropagation 演算法四大公式](images/backpropagation-formula.png)

Backpropagation 演算法四大公式

如果還是有不懂的地方，千萬不要覺得氣餒，畢竟你願意深入理解 Neural Network 的更新過程，就已經超越許多「呼叫套件學 AI」的人了！如果你是深度學習領域的初學者，勢必要反覆閱讀多次，才能完全理解 Backpropagation 演算法的運算過程的。

## 參考

- [Neural networks and deep learning (CH2)](http://neuralnetworksanddeeplearning.com/chap2.html)
