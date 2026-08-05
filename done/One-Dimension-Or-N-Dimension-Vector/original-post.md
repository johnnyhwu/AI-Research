---
title: 機器學習基本知識：維度 (Dimension) 的兩種意義
date: '2022-06-15T04:54:40'
lastmod: '2022-06-29T08:52:24'
slug: one-dimension-or-n-dimension-vector
draft: false
categories:
- 機器學習基礎觀念
tags:
- Deep Learning
- Machine Learning
description: 前言 在學習線性代數或是深度學習的數學運算時，經常需要對高維度的向量、矩陣進行運算。我們都知道純量 (Scalar) 屬於 0 維、向量
  (Vector) 屬於 1 維、矩陣 (Matrix) 屬於 2 維度，超過 3 維就統稱為張量 (Tensor)。（當然 Scalar、Vector 與 Matrix
  也都可以視為 Tensor） 然而，如果有一個 Vector 包含 5 個數字，例如：[1, 2, 3, 4, 5]，我們又會稱這一個 Vector 是一個 5
  維的向量。 Vector 究竟是 1 維還是 N 維呢？讓我們繼續看下去！ 純量 (Scalar)、向量 (Vector)、矩陣 (Matrix) 與張量 (Tensor)
  首先，我們需要先釐清純量 (Scalar)、向量 (Vector)、矩陣 (Matrix) 與張量 (Tensor)的觀念。 如上圖所示，Scalar 通常就是指一個數字
  […]
aliases:
- /machine-learning-basic-concept/one-dimension-or-n-dimension-vector/
original_url: http://54.150.87.240/machine-learning-basic-concept/one-dimension-or-n-dimension-vector/
wp_id: 926
images:
- images/feature-image.jpg
- images/scalar-vector-matrix.jpg
- images/tensor.png
---

![](images/feature-image.jpg)

source: Pixabay

## 前言

在學習線性代數或是深度學習的數學運算時，經常需要對高維度的向量、矩陣進行運算。我們都知道純量 (Scalar) 屬於 0 維、向量 (Vector) 屬於 1 維、矩陣 (Matrix) 屬於 2 維度，超過 3 維就統稱為張量 (Tensor)。（當然 Scalar、Vector 與 Matrix 也都可以視為 Tensor）

然而，如果有一個 Vector 包含 5 個數字，例如：[1, 2, 3, 4, 5]，我們又會稱這一個 Vector 是一個 5 維的向量。

Vector 究竟是 1 維還是 N 維呢？讓我們繼續看下去！

## 純量 (Scalar)、向量 (Vector)、矩陣 (Matrix) 與張量 (Tensor)

首先，我們需要先釐清純量 (Scalar)、向量 (Vector)、矩陣 (Matrix) 與張量 (Tensor)的觀念。

![scalar, vector and matrix](images/scalar-vector-matrix.jpg)

source: TensorFlow

如上圖所示，Scalar 通常就是指一個數字 (Single Value)，它的 shape 中沒有任何元素，也就是沒有任何「軸」(Axes)，也可以稱其為 Rank-0 的 Tensor。Vector 指的是一個序列的數字 (List of Values)，它的 shape 中有一個元素，也就是其具有一個軸，也可以稱其為 Rank-1 的 Tensor。Matrix 則是由兩個軸的元素所組成，因此 shape 中有兩個元素，也可以稱其為 Rank-2 的 Tensor。

![tensor](images/tensor.png)

source: TensorFlow

當軸數來到 3 個以上時，我們就通稱為 Tensor，此時的 shape 中有 3 個元素，也可以稱其為 Rank-3 的 Tensor。

## 維度 (Dimension)：「軸」的個數 or 「向量中元素」的個數

由此可知，當我們說 Scalar 是 0-Dimension、Vector 是 1-Dimension、Matrix 是 2-Dimension 時，這裡的 Dimension 指的是「軸」的數量。

然而，如果我們只聚焦在 Vector 上，當我們在描述 Vector 的 Dimension 時，其實是在描述他所處的「向量空間」(Vector Space)。舉例來說：

- [1, 2, 3] 處在 3-Dimension Vector Space
- [-1, -5, 4, 5, 8] 處在 5-Dimension Vector Space
- [0, 0, 0, 0, 0, 0, 0] 處在 7-Dimension Vector Space

由此可知，**Dimension 有兩種意義：**

- Vector 中的**元素數量** (代表這一個 Vector 所處的 Vector Space)
- Tensor 的**軸數** (代表這一個 Tensor 的 Rank)

## 結語

在本篇文章，我們簡單介紹純量 (Scalar)、向量 (Vector)、矩陣 (Matrix) 與張量 (Tensor) 的概念，並說明維度 (Dimension) 的兩種意義。

## 參考

- [matrices – why do people say “x dimensional vector” when vectors have only one dimension? – Mathematics Stack Exchange](https://math.stackexchange.com/questions/2152360/why-do-people-say-x-dimensional-vector-when-vectors-have-only-one-dimension#:~:text=at%203%3A02-,1,other%20elements%20of%20the%20space.)
- [Introduction to Tensors  |  TensorFlow Core](https://www.tensorflow.org/guide/tensor)
- [核心開發者親授！PyTorch深度學習攻略](https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code=9135738)
