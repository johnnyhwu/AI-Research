---
title: Deep Learning 基本功：認識 MNIST 資料集與損失函數
date: '2022-03-03T12:06:05'
lastmod: '2022-06-27T15:13:17'
slug: mnist-dataset-and-cost-function
draft: false
categories:
- 深度學習核心觀念
tags:
- Classification
- Deep Learning
- Gradient Descent
- Supervised Learning
description: 前言 在上一篇文章中，我們針對「手寫數字圖像」的分類問題，設計了一個 Neural Network，並站在 Neural Network
  的角度感受其如何理解圖像：Input Layer 象徵圖像中每一個像素，Hidden Layer 學習捕捉圖像中重要的特徵，Output Layer 再依據捕捉到的特徵進行圖像的分類。
  在接下來的幾篇文章中，我們將理解 Neural Network 如何透過以下 3 元素： 訓練資料集 (Training Dataset) 損失函數 (Cost
  Function) 最佳化演算法 (Optimizer) 調整 Neural Network 中的參數 (weight 與 bias) 使得 Neural Network
  的輸出愈來愈準確。 本篇文章將介紹訓練資料集 (Training Dataset) 與損失函數 (Cost Function) 的觀念。 MNIST 資料集介紹
  想要訓練一個 Neural Network，不可缺少的是一大堆的訓練資料。針對「手寫數字圖像」分類問題，最有名的資料集是 MNIST 資料集 (MNIST Dataset)，MNIST
  中包含了上萬張的手寫數字圖像以及每一張圖像正確的標籤 […]
aliases:
- /deep-learning-core-concept/mnist-dataset-and-cost-function/
original_url: http://54.150.87.240/deep-learning-core-concept/mnist-dataset-and-cost-function/
wp_id: 677
images:
- images/Deep-Learning-Cost-Function-1.jpg
- images/MNIST-Dataset.jpg
- images/feature-image.jpg
- images/one-hot-vector.jpg
---

![feature image](images/feature-image.jpg)

source: Pixabay

## 前言

在[上一篇文章](http://54.150.87.240/deep-learning-core-concept/neural-network-classify-handwritten-digit-image/)中，我們針對「手寫數字圖像」的分類問題，設計了一個 Neural Network，並站在 Neural Network 的角度感受其如何理解圖像：Input Layer 象徵圖像中每一個像素，Hidden Layer 學習捕捉圖像中重要的特徵，Output Layer 再依據捕捉到的特徵進行圖像的分類。

在接下來的幾篇文章中，我們將理解 Neural Network 如何透過以下 3 元素：

- 訓練資料集 (Training Dataset)
- 損失函數 (Cost Function)
- 最佳化演算法 (Optimizer)

調整 Neural Network 中的參數 (weight 與 bias) 使得 Neural Network 的輸出愈來愈準確。

本篇文章將介紹訓練資料集 (Training Dataset) 與損失函數 (Cost Function) 的觀念。

## MNIST 資料集介紹

想要訓練一個 Neural Network，不可缺少的是一大堆的訓練資料。針對「手寫數字圖像」分類問題，最有名的資料集是 MNIST 資料集 (MNIST Dataset)，MNIST 中包含了上萬張的手寫數字圖像以及每一張圖像正確的標籤 (Label)。

MNIST 是 **M**odified **N**ational **I**nstitute of **S**tandards and **T**echnology database 的縮寫，其為 [NIST](https://www.nist.gov/) 機構所建立的兩個資料集的修改版本。

下圖為 MNIST 資料集中的幾張範例圖片：

![MNIST Dataset](images/MNIST-Dataset.jpg)

MNIST 資料集中的圖片 [source: Neural Networks and Deep Learning]

MNIST 資料集中包含 2 個部分，分別為訓練資料以及測試資料。訓練資料中包含 60000 張手寫數字圖像，這些圖像為 250 個人的字跡，其中 50% 是高中生，另外 50% 則是人口普查局的員工，確保訓練資料中的手寫數字圖像盡可能包含許多不同的字跡風格與特徵。

測試資料中包含 10000 張手寫數字圖像，這些圖像同樣是來自美國高中生與人口普查局，然而是另外不同的 250 個人所留下的字跡。如此一來，我們就能夠用測試資料來判斷 Neural Network 是否知的能夠對圖像進行正確的分類。

在 MNIST 資料集中，所有圖像都是由 28 × 28 個像素組成的「灰階」(Grayscale) 圖像，且每一張圖像都有對應的標籤 (Label) 說明圖像中代表的數字為何。

在 [Neural Network 設計](http://54.150.87.240/deep-learning-core-concept/neural-network-classify-handwritten-digit-image/)一文中，我們提到 Input Layer 中會包含 784 個 Neuron。因為我們是設計最初階、最基本的 Neural Network，因此在實作上我們會將每一張圖像由 28 × 28 的 2 維矩陣 (Matrix) 轉為 784 個元素的 1 維向量 (Vector)，並用 **x** 象徵要輸入到 Neural Network 中的圖像 (因此 x 會是一個 784 個維度的向量)。

我們會使用 **y(x)** 象徵該圖像所對應的實際數字。比較特別的是，y(x) 並不是一個數字，而是 10 個維度的向量。如下圖所示：

![one hot vector](images/one-hot-vector.jpg)

用 10 個維度的向量表示數字 0 到 9

如果圖像中的數字是 0，則 10 維向量中的第 1 個數字是 1 其餘都是 0，以此類推。這樣子的 y(x) 比較符合我們對 Neural Network 中 [Output Layer 的設計](http://54.150.87.240/deep-learning-core-concept/neural-network-classify-handwritten-digit-image/)。

將數字 0 到數字 9（這 10 種類別）分別用上述那種向量來表示，是在機器學習領域中，針對類別型資料常見的編碼（Encoding）方式，又稱為 [One-Hot Encoding](https://en.wikipedia.org/wiki/One-hot)。

## Neural Network 的目標：最小化損失函數 (Cost Function)

有了 MNIST 訓練資料集後，我們希望 Neural Network 能夠透過這些訓練資料，學習到正確的參數 (weight 與 bias)。換句話說，我們希望輸入一張圖像 x (一個 784 個維度的向量) 到 Neural Network 中，Neural Network 能夠輸出一個 y (一個 10 個維度的向量)，而且這個 y 與 y(x) (x 所對應的實際數字，也是一個 10 個維度的向量) 愈接近愈好。

而 Neural Network 正是透過一個最佳化演算法 (Optimizer) 來「調整」參數。這個最佳化演算法 (Optimizer) 也是 Deep Learning 中最有趣、最有價值的部分，我們將會在後續的文章深入介紹。

如果我們希望 Optimizer 可以好好的調整 Neural Network 中的參數，那我們總需要一種方法來判斷 Neural Network 中目前「參數的好壞」。這個方法所使用的工具稱為「損失函數」(Cost Function)。

![Deep Learning Cost Function](images/Deep-Learning-Cost-Function-1.jpg)

損失函數 (Cost Function) 的樣子 [source: Neural Networks and Deep Learning]

如上圖所示，Cost Function C 是一個函數，會接受兩個數值：w 與 b。w 象徵 Neural Network 中所有的 weight； b 則象徵 Neural Network 中所有的 bias。給定 w 與 b，C (Cost Function) 會計算一個數值，表示這組 w 與 b 的好壞程度。上圖算式中的 x 表示一筆訓練資料 (一張圖像)；y(x) 表示該圖像對應到的實際數字；a 則是將 x 輸入到 Neural Network 後的輸出；‖v‖ 則用來表示這個向量 (y(x)-a) 的距離。

a 取決於 x (目前輸入的圖像) 與 w, b (Neural Network 中的參數)。一個好的 Neural Network，會由好的參數 (w 與 b) 組成，輸入大多數的 x，都能產生接近 y(x) 的 a，使得 ‖ y(x) – a ‖ 的數值愈小。

因此，我們可以透過一個 Cost Function 來橫量參數的好壞：如果 Cost Function 的輸出愈低，表示目前這組參數很好；相反的，Cost Function 的輸出愈高，表示目前這組參數很差。

有了 Cost Function，Optimizer 的目標就相當明確：最小化 Cost Function。Optimizer 要嘗試去找出一組 w 與 b，「最小化」Cost Function 的輸出。而我們所使用的 Optimizer 稱為 **Gradient Descent**。

## 結語

在本文中我們了解訓練資料集 (Training Dataset) 與損失函數 (Cost Function) 在 Deep Learning 中所扮演的角色，也了解到所謂 Neural Network 的「學習」，就是透過一個最佳化演算法 (Optimizer) 找到一組 weight 與 bias 最小化 Cost Function 的輸出。

在下一篇文章中，我們會學習 Deep Learning 中 Optimizer 的觀念，我們將從最基本的 Optimizer —— [Gradient Descent](http://54.150.87.240/deep-learning-core-concept/deep-learning-gradient-descent/) 開始談起。

## 參考

- [Neural networks and deep learning](http://neuralnetworksanddeeplearning.com/chap1.html)
- [MNIST database – Wikipedia](https://en.wikipedia.org/wiki/MNIST_database)
- [One-hot – Wikipedia](https://en.wikipedia.org/wiki/One-hot)
