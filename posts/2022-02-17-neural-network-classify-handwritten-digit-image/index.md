---
title: 'Deep Learning 原理 : Neural Network 如何分類圖像'
date: '2022-02-17T13:27:53'
lastmod: '2022-03-03T12:07:27'
slug: neural-network-classify-handwritten-digit-image
draft: false
categories:
- 深度學習核心觀念
tags:
- Classification
- Deep Learning
- Machine Learning
- Supervised Learning
description: 前言 在前一篇文章中，我們認識了 Neural Network 的基本組成與 Input、Output Layer 的設計理念，也認識到
  Feedforward Neural Network 與 Recurrent Neural Network 的差別。 在本篇文章中，我們會以「手寫數字圖像分類」問題出發，了解如何設計
  Neural Network 解決此問題，並站在 Neural Network 的角度，理解它們如何思考圖像中的數字並進行分類。 手寫數字圖像分類問題 「手寫數字圖像分類」問題是
  Deep Learning 領域中相當常見的問題，許多剛踏入 Deep Learning 領域的初學者，也會將解決此問題作為第一個 Deep Learning
  專案。   上圖呈現的就是一張手寫數字的圖像。我們希望訓練一個 Neural Network 能夠精確的辨識其中的每一個數字 —— 504192。以上圖為來說，辨識的過程分為兩個步驟。第一步，必須先進行圖像的分割，也就是將每一個數字分開來。第二步，針對每一個數字圖像進行分類
  (0 ~ 9)。 在本篇文章中，我們不討論第一步 (圖像分割) 的部分，我們聚焦在第二個部分 (圖像分類/辨識)。因此，我們假設目前所有的圖像中都只包含一個數字，而且每張圖像都是相同的尺寸
  (28 × 28)，那麼我們該如何設計一個 Neural Network 來辨識這個數字呢 ? […]
aliases:
- /deep-learning-core-concept/neural-network-classify-handwritten-digit-image/
original_url: http://54.150.87.240/deep-learning-core-concept/neural-network-classify-handwritten-digit-image/
wp_id: 500
images:
- images/feature-image-11.jpg
- images/hanwritten-digit.jpg
- images/mnist-feature.jpg
- images/mnist-top-left-feature.jpg
- images/mnist-zero.jpg
- images/neural-network-2.jpg
---

![](images/feature-image-11.jpg)

source: Pixabay

## 前言

在[前一篇文章](http://54.150.87.240/deep-learning-core-concept/understand-neural-network-for-deep-learning/)中，我們認識了 Neural Network 的基本組成與 Input、Output Layer 的設計理念，也認識到 Feedforward Neural Network 與 Recurrent Neural Network 的差別。

在本篇文章中，我們會以「手寫數字圖像分類」問題出發，了解如何設計 Neural Network 解決此問題，並站在 Neural Network 的角度，理解它們如何思考圖像中的數字並進行分類。

## 手寫數字圖像分類問題

「手寫數字圖像分類」問題是 Deep Learning 領域中相當常見的問題，許多剛踏入 Deep Learning 領域的初學者，也會將解決此問題作為第一個 Deep Learning 專案。

![hanwritten digit](images/hanwritten-digit.jpg)

手寫數字圖像示意圖 [source: Neural Networks and Deep Learning]

上圖呈現的就是一張手寫數字的圖像。我們希望訓練一個 Neural Network 能夠精確的辨識其中的每一個數字 —— 504192。以上圖為來說，辨識的過程分為兩個步驟。第一步，必須先進行圖像的分割，也就是將每一個數字分開來。第二步，針對每一個數字圖像進行分類 (0 ~ 9)。

在本篇文章中，我們不討論第一步 (圖像分割) 的部分，我們聚焦在第二個部分 (圖像分類/辨識)。因此，我們假設目前所有的圖像中都只包含一個數字，而且每張圖像都是相同的尺寸 (28 × 28)，那麼我們該如何設計一個 Neural Network 來辨識這個數字呢 ?

## Neural Network 的設計

在[介紹 Neural Network 組成](http://54.150.87.240/deep-learning-core-concept/understand-neural-network-for-deep-learning/)一文中，我們有討論過這個問題。針對問題本身，我們可以很直觀的設計 Neural Network 的 Input Layer 與 Output Layer。

![neural network](images/neural-network-2.jpg)

Neural Network 的設計 [source: Neural Networks and Deep Learning]

如上圖所示，Input Layer 中的每一個 Neuron 將會代表圖像中每一個 Pixel 的數值。因為圖像的尺寸都是 28 × 28，因此總共會有 784 Pixel。也就是說，Input Layer 中總共會有 784 個 Neuron (在上圖中，我們沒有真的畫出 784 個 Neuron)。此外，因為每一張圖像都是灰階 (Grayscale) 圖像，因此每一個 Pixel 只會擁有一個通道 (Channel) 用來表示這一個 Pixel「有多黑」。例如，如果這一個 Pixel 的數值是 0，表示「全白」；如果是 255，則表示「全黑」；介於 0 與 255 之間的數字，則是白色與黑色組成的灰色。

然而，我們通常不會直接將 Pixel 的原始數值輸入到 Neural Network 中。為了提升 Neural Network 的訓練速度與品質，我們通常會將輸入的數值進行一些轉換，壓縮到 0 到 1 的區間。因此，我們會將每一個 Pixel 數值除以 255，使得 Input Neuron 的數值介於 0.0 到 1.0 之間。

在上圖的 Neural Network 中，我們只用了一個 Hidden Layer，Hidden Layer 中包含了 15 個 Neuron。

Output Layer 則包含了 10 個 Neuron，分別代表數字 0 到 9。舉例來說，如果輸入一張圖片到 Neural Network 中，代表數字 6 的 Neuron 有最大的數值，則表示 Neural Network 認為這張圖像應為「6」。

## Output Layer 為什麼不使用 4 個 Neuron 就好

既然 Neural Network 的 Output Layer 最終只會表示 0 ~ 9 任一個數字，那為什麼不使用 4 個 Neuron 就好？每一個 Neuron 都可以表示 0 或 1，4 個 Neuron 就可以表示 2 × 2 × 2 × 2 = 16 種數字，是相當足夠的。

要回答這一個問題並不容易，因為我們必須把自己當作 Neural Network，了解 Neural Network 如何理解圖像中的資訊。即使如此，我們還是可以透過更務實的方式來解答這個問題：實驗的結果證實，10 個 Neuron 的 Output Layer 比 4 個 Neuron 的 Output Layer 有更好的的辨識結果。

## Neural Network 如何理解圖像資訊

接著，我們來體會 Neural Network 如何理解圖像中的資訊。我們聚焦在 Output Layer 的第 1 個 Neuron，也就是負責「輸出 0」的 Neuron。假設這一個 Neural Network 已經訓練完成，當輸入一張「手寫數字 0」的圖像時，這一個 Neuron 會比同在 Output Layer 的 Neuron 輸出更大的數字才對。

![neural network](images/neural-network-2.jpg)

我們聚焦在 Output Layer 的第一個 Neuron [source: Neural Networks and Deep Learning]

這一個 Neuron 主要就是將 Hidden Layer 中所有 Neuron 的輸出，分別乘以一個 w 並加總在一起。那麼 Hidden Layer 的 Neuron 又是在做什麼事情呢？

Hidden Layer 中的每一個 Neuron 都負責辨識輸入圖像中的某一種特徵。如果輸入圖像中包含該 Neuron 所負責的特徵，那麼該 Neuron 的輸出就會特別大。舉例來說：

![mnist top left feature](images/mnist-top-left-feature.jpg)

數字 0 的左上部分 [source: Neural Networks and Deep Learning]

如果 Hidden Layer 中的第 1 個 Neuron 負責辨識上圖那樣的特徵，那麼這一個 Neuron 在對每一個 Input Neuron 計算權重乘積的總和時，就會給予那一部份的 Input Neuron 特別大的權重，其餘部分的 Neuron 則權重比較小。

同理，下方 3 種特徵分別由 Hidden Layer 的第 2、3 與 4 個 Neuron 負責。

![mnist feature](images/mnist-feature.jpg)

由左而右分別是數字 0 的右上、左下與右下部分 [source: Neural Networks and Deep Learning]

如果將這 4 種特徵合在一起，其實就是一張數字 0 的手寫圖像！

![mnist zero](images/mnist-zero.jpg)

數字 0 的手寫圖像

因此，當我們輸入這張數字 0 的手寫圖像到 Neural Network 中時，Hidden Layer 中的前 4 個 Neuron 分別都會偵測到自己負責的特徵，因此輸出特別大的數字。接著，我們就可以推測 Output Layer 的第一個 Neuron 在對 Hidden Layer 所有 Neuron 計算權重乘積的總和時，勢必會給前 4 個 Neuron 比較大的權重，因為它知道他們 4 個組合在一起就是在辨識數字 0。

了解 Neural Network 如何理解圖像中的資訊之後，我們就可以比較好理解為什麼 Output Layer 中有 10 個 Neuron 而不是 4 個 Neuron。因為當 Output Layer 有 10 個 Neuron 時，每一個 Output Neuron 都會象徵一個數字，每一個 Output Neuron 會不會被激發 (輸出很大的數值) 取決於前面的 Hidden Layer 捕捉到了哪些形狀特徵。然而，當 Output Layer 只有 4 個 Neuron 時，每一個 Output Neuron 則是象徵一個 Bit，Hidden Layer 捕捉到了哪些形狀特徵，與這個 Bit 為 0 或 1 相較比較難以關聯在一起。

## 結語

在本篇文章中，我們進入到 Neural Network 的視角，體會 Neural Network 如何理解圖像中的資訊。在[下一篇文章](http://54.150.87.240/deep-learning-core-concept/mnist-dataset-and-cost-function/)中，我們將理解 「Neural Network 如何學習」，如何調整自己的參數 (weight 與 bias) 使得輸出愈來愈正確。

## 參考

- [Neural networks and deep learning](http://neuralnetworksanddeeplearning.com/chap1.html)
- [Why do we have to normalize the input for an artificial neural network? – Stack Overflow](https://stackoverflow.com/questions/4674623/why-do-we-have-to-normalize-the-input-for-an-artificial-neural-network)
