---
title: 'Perceptron 的改良版 : 了解什麼是 Sigmoid Neuron'
date: '2022-02-07T01:57:19'
lastmod: '2022-02-21T04:26:51'
slug: understand-sigmoid-neuron
draft: false
categories:
- 深度學習核心觀念
tags:
- Classification
- Deep Learning
- Machine Learning
- Perceptron
- Sigmoid
description: 前言 在前一篇文章中，我們認識了最古老的人造神經元 (Artificial Neuron) —— 感知器 Perceptron，對於 Perceptron
  的數學算式、與 NAND Gate 的關係，有了基本的了解。然而，Perceptron 並不是現代神經網路 (Modern Neural Network) 所使用的神經元。在本篇文章中，我們將會介紹一種「更接近」現代神經網路所使用的神經元
  —— Sigmoid Neuron。 神經網路如何學習 在前一篇文章中，我們提到因為「學習演算法」(Learning Algorithm) 的存在，使得 Perceptron
  不單單只是 NAND Gate 的化身，而是能夠自動學習參數 (weight 與 bias)。在設計 Learning Algorithm 之前，我們可以先用更直觀的方式了解神經網路
  (Neural Network) 如何學習輸出正確的結果。 假設我們有一個 Neural Network 能夠接收「手寫數字照片」，並輸出這張照片所代表的數字。
  如上方的示意圖，Neural Network 會接收一張圖片，圖片中有一個手寫的數字，Neural Network 必須輸出這張圖片所代表的實際數字是什麼。 假設
  Neural Network 的參數一開始是隨機產生的，因此剛開始的輸出結果可能非常糟。例如，輸入一張數字 4 的手寫圖片，但是卻將該圖片辨識為 6。Neural
  Network […]
aliases:
- /deep-learning-core-concept/understand-sigmoid-neuron/
original_url: http://54.150.87.240/deep-learning-core-concept/understand-sigmoid-neuron/
wp_id: 351
images:
- images/feature-image.jpg
- images/handwritten-digit-classification.jpg
- images/output.jpg
- images/perceptron-formula-1.jpg
- images/perceptron.jpg
- images/sigmoid-function-2.jpg
- images/sigmoid-function-3.jpg
- images/step-function.jpg
- images/update-parameter-in-neural-network.png
---

![](images/feature-image.jpg)

source: Pixabay

## 前言

在[前一篇文章](http://54.150.87.240/deep-learning-core-concept/what-is-perceptron/)中，我們認識了最古老的人造神經元 (Artificial Neuron) —— 感知器 Perceptron，對於 Perceptron 的數學算式、與 NAND Gate 的關係，有了基本的了解。然而，Perceptron 並不是現代神經網路 (Modern Neural Network) 所使用的神經元。在本篇文章中，我們將會介紹一種「更接近」現代神經網路所使用的神經元 —— Sigmoid Neuron。

## 神經網路如何學習

在前一篇文章中，我們提到因為「學習演算法」(Learning Algorithm) 的存在，使得 Perceptron 不單單只是 NAND Gate 的化身，而是能夠自動學習參數 (weight 與 bias)。在設計 Learning Algorithm 之前，我們可以先用更直觀的方式了解神經網路 (Neural Network) 如何學習輸出正確的結果。

假設我們有一個 Neural Network 能夠接收「手寫數字照片」，並輸出這張照片所代表的數字。

![handwritten digit classification](images/handwritten-digit-classification.jpg)

透過一個 Neural Network 辨識「手寫數字照片」的實際數字

如上方的示意圖，Neural Network 會接收一張圖片，圖片中有一個手寫的數字，Neural Network 必須輸出這張圖片所代表的實際數字是什麼。

假設 Neural Network 的參數一開始是隨機產生的，因此剛開始的輸出結果可能非常糟。例如，輸入一張數字 4 的手寫圖片，但是卻將該圖片辨識為 6。Neural Network 為了輸出正確的結果，就必須不斷的調整自己的參數 (weight 與 bias)。理想的狀況是，Neural Network 每次對參數進行「些微」的調整，也能夠讓輸出的結果「微幅」的變動。

![update parameter in neural network](images/update-parameter-in-neural-network.png)

「微幅」調整參數數值，使得輸出結果也「微幅」變動 [source: Neural Networks and Deep Learning]

如上圖所示，我們希望將 Neural Network 中的某一個參數 w 進行「微幅」調整 (加上 ∆w)，Neural Network 的輸出也能夠「微幅」的變動 (加上 ∆output)。假設我們所希望的這件事情真的能夠成真，那麽讓 Neural Network 學習輸出正確的結果將會變得更簡單。舉例來說，假設一開始我們輸入「手寫數字 9」的照片到 Neural Network 中，得到的輸出為「8」。我們只需要找到每一個參數應該調整的方向 (變大 or 變小)，然後對該參數進行「微幅」的調整，就能夠預期 Neural Network 的輸出也會「微幅」的調整。不斷的進行微幅的調整，直到 Neural Network 的輸出調整到正確的結果為止。

## Perceptron 所產生的問題

然而，事情總是沒有那麼順利。在[了解什麼是 Perceptron](http://54.150.87.240/deep-learning-core-concept/what-is-perceptron/) 一文中，我們介紹到 Perceptron 的基本概念：

![perceptron](images/perceptron.jpg)

Perceptron 接收多個 Binary Value 並輸出一個 Binary Value

如上圖所示，Perceptron 會接收多個二元數值作為輸入，並輸出一個二元數值作為輸出。所謂的「二元數值」就是該數值不是 0 就是 1。因此，假設我們在一個由很多 Perceptron 組成的 Neural Netowrk 中，「微幅」調整其中一個 Perceptron 的 weight，可能會導致這一個 Perceptron 的輸出「完全顛倒」，也就是由原來的 0 變為 1。這一個 Perceptron 的輸出又會其他 Perceptron 的輸入，如此一來將會導致整個 Neural Network 的輸出結果變的難以捉摸。

舉例來說，如果我們將「手寫數字 9」照片輸入到 Neural Network 中，得到的輸出為「8」。Neural Network 將參數經過多次的微幅調整後，能夠正確的輸出「8」。然而，因為 Neural Netowork 中許多 Perceptron 的 output 已經大幅改變 (由 0 變為 1 或由 1 變為 0)，使得當我們輸入其他原先被分類正確的手寫數字照片到 Neural Network 時，得到的輸出可能變得和原來不一樣。

## Sigmoid Neuron 登場

為了使得 Perceptron 的 output 能夠被「微幅」變動，一種新的人造神經元 (Artificial Neuron) 被發明出來，稱為 Sigmoid Neuron。實際上，Sigmoid Neuron 是在原先的 Perceptron 進行一些修改而形成的。

![perceptron](images/perceptron.jpg)

Sigmoid Neuron 就是將原來的 Perceptron 進行一些修改

如上圖所示，Sigmoid Neuron 的輸入與輸出與 Perceptron 一樣，接收多個輸入 (x1、x2、x3) 並產生一個輸出 (output)。與 Perceptron 不同之處，在於輸入與輸出的數值。

在 Perceptron 中，輸入 (x1、x2、x3) 僅是不連續分佈的二元數值，也就是 0 或 1。但是，在 Sigmoid Neuron 中，輸入是一個 0 到 1 連續分佈的任意數字。例如：0.2556 或 0.6398。每一個輸入的數值同樣會與一個 weight 相乘並總和，再加上一個 bias，得到最終的數值。

![perceptron formula](images/perceptron-formula-1.jpg)

Perceptron 簡化後的數學算式 [source: Neural Networks and Deep Learning]

如上圖所示，根據最終的數值，Perceptron 的 output 可能為 0 或 1。然而，在 Sigmoid Neuron 中，output 與輸入 (x1、x2、x3) 類似，會是一個 0 到 1 連續分佈的任意數字。更精確的說，Sigmoid Neuron 會將最終的數值 (w·x + b) 通過一個 Sigmoid 函數才輸出。因此，Sigmoid Neuron 的輸出為：σ(w·x + b)。

「σ」 的名字為「Sigmoid Function」，其完整的數學算式為：

![sigmoid function](images/sigmoid-function-2.jpg)

Sigmoid Function

簡而言之，Sigmoid Neuron 會將所有的輸入 x 與 weight 相乘並總和再加上一個 bias，得到 z = w·x1 + w·x2 + w·x3 + ··· + bias。再將 z 輸入到 Sigmoid Function 中，最後才輸出 σ(z)。

## Sigmoid Neuron 與 Perceptron 的相似之處

剛開始認識 Sigmoid Neuron 時，可能會覺得它多了 Sigmoid Function，使得它的輸出與 Perceptron 很不一樣。然而，實際上剛好相反，Sigmoid Neuron 的輸出與 Perceptron 仍然非常相似，舉例來說，假設目前 Sigmoid Neuron 計算得到 z = w·x + b 是一個大的正數，則 e-z 會趨近於 0，得 σ(z) 為 1。也就是說，當 z = w·x + b 是一個大的正數時，Sigmoid Neuron 的輸出為 1 (與 Perceptron 一致)。

相反的，當 z = w·x + b 是一個小的負數，則 e-z 會趨近於 ∞，得 σ(z) 為 0。也就是說，當 z = w·x + b 是一個小的負數時，Sigmoid Neuron 的輸出為 0 (與 Perceptron 一致)。只有當 z = w·x + b 不大也不小時，Sigmoid Neuron 的輸出才會與 Perceptron 不一樣。

## Sigmoid 函數的重要特性 —— 平滑

![sigmoid function](images/sigmoid-function-2.jpg)

Sigmoid Function

到目前為止，我們已經對 Sigmoid 函數的算式有了一點印象；在本篇文章中，我們不會深入探討 Sigmoid 算式的細節，我們會著重在探討 Sigmoid 函數重要的特型 —— **平滑**。

![sigmoid function](images/sigmoid-function-3.jpg)

sigmoid function [source: Neural Networks and Deep Learning]

上圖是 Sigmoid 函數繪製在二維平面上的樣子，我們可以發現其實 Sigmoid 函數就是 Step 函數的「平滑版」：

![step function](images/step-function.jpg)

step function [source: Neural Networks and Deep Learning]

實際上，如果我們將 Sigmoid Neuron 的 σ 換成 Step 函數，那麼 Sigmoid Neuron 其實就變成了 Perceptron。因為最終的輸出會是 w·x + b 再通過 Step 函數，最後得到 0 或是 1。

Sigmoid Function 的平滑性是一個重要的特徵，因爲這個特性使得「參數」(weight 與 bias) 經過微幅的調整後，「輸出」(output) 真的也可以微幅的變動。

![output](images/output.jpg)

output 的變動來自於 weight 與 bias [source: Neural Networks and Deep Learning]

上圖呈現的是一個 Sigmoid Neuron 的輸出的變動 (Δoutput) 來自於參數的變動 (Δw 與 Δb) 。其中，Δw 表示 weight 的變動，Δb 表示 bias 的變動，並不是單純將 Δw 與 Δb 相加，而是分別再乘以一個偏微分。

第一次看到偏微分可能會讓人覺得難以理解，我們可以簡單地將偏微分視為：一個多變數函數對於某一個獨立變數的「改變率」。也就是說，當 w 加上 5 時 (Δw = 5)，對 output 的影響不一定是直接加上 5 (Δoutput 不一定等於 5)，而是需要再乘以 output 對於 w 的改變率 (當 w 變動 1 時，output 變動多少)。

我們也可以更簡單的將上述的算式當作一個簡單的線性函數，也就是 Δw 乘以一個常數加上 Δb 乘以另外一個常數得到 Δoutput。如此一來，當 Δw 與 Δb 做一些微幅的變動時，Δoutput 也會產生微幅的改變。

到目前為止，我們已經了解到 Sigmoid Neuron 不僅與 Perceptron 非常像，而且還解決了 Perceptron 所產生的問題。

## 解讀 Sigmoid Neuron 的輸出

來到最後一個小節，相信你已經很清楚 Sigmoid Neuron 的輸出不僅僅是 0 或 1，而是 0 到 1 之間的任一個數字。Sigmoid Neuron  的輸出可以是 0.2123、0.5698 或是 0.9652。

假如我們現在希望透過 Sigmoid Neuron 分類手寫數字的圖像，輸入「圖像 9」到 Sigmoid Neuron 中，Sigmoid Neuron 的輸出表示這張圖像「是數字 9」或「不是數字 9」。因為 Sigmoid Neuron 的輸出已經不像 Perceptron 是 0 或 1，分別代表 True 或 False，那我們應該如何解讀 Sigmoid Neuron 的輸出呢？

我們可以將 Sigmoid Neuron 的輸出視為「機率」。因為 Sigmoid Neuron 輸出的數值一定是介於 0 到 1 之間，滿足機率的特性。因此，我們可以很直覺的使用 0.5 作為分類的依據。在上述的情境上，假如 Sigmoid Neuron 的輸出為 0.6，0.6 大於 0.5，表示 Sigmoid Neuron 認為這一個數字「是數字 9」；反之，當 Sigmoid Neuron 的輸出為 0.4，表示 Sigmoid Neuron 認為這一個數字「不是數字 9」。

## 結語

在本篇文章中，我們介紹了一種「更接近」現代神經網路所使用的神經元 —— Sigmoid Neuron，說明了其與 Perceptron 的相似與不同之處，也提到了 Sigmoid 函數最重要的特性「平滑」。本篇文章與[上一篇文章](http://54.150.87.240/deep-learning-core-concept/what-is-perceptron/)，著重於介紹人工神經元 (Artificial Neuron)，下一篇文章將會進入[人工神經網路 (Artificial Neural Network) 的介紹](http://54.150.87.240/deep-learning-core-concept/understand-neural-network-for-deep-learning/)。

## 參考

- [Neural networks and deep learning](http://neuralnetworksanddeeplearning.com/chap1.html)
- [Sigmoid function – Wikipedia](https://en.wikipedia.org/wiki/Sigmoid_function)
- [Partial Differentiation Tutorial](http://ind.ntou.edu.tw/~metex/Calculus/SecondTerm/CH7.pdf)
