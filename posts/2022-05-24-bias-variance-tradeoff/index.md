---
title: 機器學習基本觀念：Bias-Variance Tradeoff
date: '2022-05-24T09:23:31'
lastmod: '2022-07-15T01:24:06'
slug: bias-variance-tradeoff
draft: false
categories:
- 機器學習基礎觀念
tags:
- Deep Learning
- Machine Learning
description: 前言 當模型訓練完之後，我們會透過測試資料集來衡量模型的效能，計算模型的 Error。模型的 Error「包含」 Bias 與 Variance，我們希望模型的
  Bias 與 Variance 兩者都愈小愈好，然而「魚與熊掌，不可兼得」，通常降低 Bias 就會提升 Variance，降低了 Variance 就會提高
  Bias。 在本文中，我們將介紹什麼是 Model 的 Bias 與 Variance、兩者的關係，以及應該訓練模型到什麼地步才能達到兩者的平衡。 在閱讀本文之前，讀者應該要對於「什麼是機器學習」、「機器學習的模型、訓練與推論」以及「機器學習五步驟」有基本的認知。
  AD Model 的 Bias 當我們拿到訓練資料集後，我們就會開始拿這些資料訓練模型。訓練模型的意義其實就是在調整模型中的參數，使得我們輸入資料到模型後，模型的輸出可以愈接近正確答案
  (Label) 愈好。換句話說，模型其實就是一個 Function，將輸入資料對應 (Mapping) 到一個輸出資料。 我們舉一個非常簡單的訓練資料集為例，資料集中包含了
  5 個樣本，每一個樣本都有「身高」與「體重」資料。我們希望輸入「身高」到模型中，模型輸出「體重」，也就是透過身高來預測體重。 資料集中的每一個樣本用 (x, y)
  來表示，x 表示「身高」，y 表示「體重」： (160, 60) (163, 70) (165, 72) (168, 75) (170, 70) 如果我們將這個資料集中的每一個樣本繪製在
  2 […]
aliases:
- /machine-learning-basic-concept/bias-variance-tradeoff/
original_url: http://54.150.87.240/machine-learning-basic-concept/bias-variance-tradeoff/
wp_id: 858
images:
- images/5-simples-dataset.jpg
- images/bias-variance-tradeoff.png
- images/error-in-linear-regression.jpg
- images/linear-regression.jpg
- images/overfitting-model.jpg
- images/underfiting-and-overfitting.png
---

![bias variance tradeoff](images/bias-variance-tradeoff.png)

source: http://scott.fortmann-roe.com/docs/BiasVariance.html

## 前言

當模型訓練完之後，我們會透過測試資料集來衡量模型的效能，計算模型的 Error。模型的 Error「包含」 Bias 與 Variance，我們希望模型的 Bias 與 Variance 兩者都愈小愈好，然而「魚與熊掌，不可兼得」，通常降低 Bias 就會提升 Variance，降低了 Variance 就會提高 Bias。

在本文中，我們將介紹什麼是 Model 的 Bias 與 Variance、兩者的關係，以及應該訓練模型到什麼地步才能達到兩者的平衡。

在閱讀本文之前，讀者應該要對於「[什麼是機器學習](http://54.150.87.240/machine-learning-basic-concept/what-is-machine-learning/)」、「[機器學習的模型、訓練與推論](http://54.150.87.240/machine-learning-basic-concept/model-training-inference/)」以及「[機器學習五步驟](http://54.150.87.240/machine-learning-basic-concept/machine-learning-define-problem/)」有基本的認知。

AD

## Model 的 Bias

當我們拿到訓練資料集後，我們就會開始拿這些資料[訓練模型](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-training/)。訓練模型的意義其實就是在調整模型中的參數，使得我們輸入資料到模型後，模型的輸出可以愈接近正確答案 (Label) 愈好。換句話說，模型其實就是一個 Function，將輸入資料對應 (Mapping) 到一個輸出資料。

我們舉一個非常簡單的訓練資料集為例，資料集中包含了 5 個樣本，每一個樣本都有「身高」與「體重」資料。我們希望輸入「身高」到模型中，模型輸出「體重」，也就是透過身高來預測體重。

資料集中的每一個樣本用 (x, y) 來表示，x 表示「身高」，y 表示「體重」：

1. (160, 60)
2. (163, 70)
3. (165, 72)
4. (168, 75)
5. (170, 70)

如果我們將這個資料集中的每一個樣本繪製在 2 維的平面上：

![5 simples dataset](images/5-simples-dataset.jpg)

一個簡單的訓練資料集

假設我們利用這一個資料集，訓練出一個模型，如下圖的紅線所示：

![linear regression](images/linear-regression.jpg)

利用這 5 個樣本訓練出來的模型

我們可以發現當我們輸入身高 = 163 到模型中時，模型輸出的體重不為 70。當輸入身高為 165、168 與 170 時，也有相同的狀況。

**模型的輸出與正確答案的誤差稱之為 Bias**，如下圖的灰色框框所示：

![error in linear regression](images/error-in-linear-regression.jpg)

框框呈現的是模型的輸出與正確答案的誤差

當模型的 Bias 很大時，表示模型訓練得不夠徹底，或是模型的複雜度太低，使得模型沒有從訓練資料集中學到正確的知識，也就是模型根本沒有理解輸入資料與輸出之間的關係。當我們輸入一個身高資料給模型時，模型就可能給出一個錯得離譜的體重數據。這時候，我們會稱這個模型為 **Underfitting**。

## Model 的 Variance

那麼這時候你一定會想到：「那不如用一個很複雜的模型，然後訓練模型到可以精準的預測每一筆樣本」。那麼你可能會訓練出這樣的模型：

![overfitting model](images/overfitting-model.jpg)

訓練模型精準的預測每一個樣本

這個模型看起來真的太棒了，因為它可以完美的預測訓練資料集中的每一筆數據。然而，當我們輸入身高 = 169 到模型中時，模型的輸出可能會落在 72 附近；當我們輸入身高 = 170 到模型中時，模型的輸出為 70：當我們輸入身高 = 175 到模型中時，模型的輸出可能變成 60。

由此我們可以發現，當我們輸入不同的身高數值時，模型的輸出有很大的變化。**針對不同的輸入資料，模型輸出的變化 (變異性) 分佈稱之為 Variance**。

AD

當模型的 Variance 很大時，表示模型把訓練資料集中所有東西都學進去了，包含一些「雜訊」。以上圖的模型來說，通常身高愈高，也會使得體重愈重，因此第 5 個樣本可以當作一個雜訊。當模型也把這個雜訊學進去時，就會以為「隨著身高愈高，體重愈重，但是身高超過 168 時，體重就會驟降」。

換句話說，模型根本沒有理解輸入資料與輸出之間的關係，而是硬生生的把每一筆樣本的輸入與輸出的關係記下來。當我們輸入一個「模型從未見過」的身高資料時，模型就可能給出一個錯得離譜的體重數據。這時候，我們會稱這個模型為 **Overfitting**。

## Bias-Variance Tradeoff

![underfiting and overfitting](images/underfiting-and-overfitting.png)

Bias-Variance 與 Underfitting-Overfitting 的關係 [source: Towards Data Science]

當模型非常的「複雜」(參數量很大) 時，能夠完全記下訓練資料集中所有的樣本，模型的 Variance 會很高、Bias 會很低，稱之為 Overfitting；當模型過於「簡單」(參數量很小) 時，完全沒有辦法從訓練資料集中學到任何東西時，模型的 Bias 會很高、Variance 會很低，稱之為 Underfitting。

還記得一開始所提到的，一個模型的 Total Error 包含了 Bias 與 Variance，因此必須在兩者之間權衡，才能達到 Total Error 最低的模型，稱之為 Bias-Variance Tradeoff。

下圖呈現的是 Bias-Variance Tradeoff 的意義：

![bias variance tradeoff](images/bias-variance-tradeoff.png)

source: http://scott.fortmann-roe.com/docs/BiasVariance.html

從上圖可以發現，單純只有考慮 Bias 或 Variance，都沒有辦法使得模型的 Total Error 最小。在考量兩者的情況下，我們希望訓練出一個 Total Error 最小的模型！

AD

## 參考

- [Understanding the Bias-Variance Tradeoff | by Seema Singh | Towards Data Science](https://towardsdatascience.com/understanding-the-bias-variance-tradeoff-165e6942b229)
- [What is the tradeoff between Bias and Variance? (educative.io)](https://www.educative.io/edpresso/what-is-the-tradeoff-between-bias-and-variance)
