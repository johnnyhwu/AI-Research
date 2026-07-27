---
title: '使用機器學習解決問題 : 探索書籍風格'
date: '2022-02-05T03:34:54'
lastmod: '2022-02-21T03:43:46'
slug: book-clustering
draft: false
categories:
- 機器學習基礎觀念
tags:
- Clustering
- K-Means
- Machine Learning
description: '前言 & 概述 本篇為機器學習基礎觀念的第 9 篇文章。在前一篇文中，我們說明如何透過機器學習五步驟 (定義問題、建立資料集、模型訓練、模型評估與模型推論)
  解決「房價預測」的問題。 房價預測屬於監督式學習 (Supervised Learning)，在本篇文章中將會以「探索書籍風格」作為非監督式學習 (Unsupervised
  Learning) 的例子。 Step 1 : 定義問題 假設你是一間大型書店的店長，你想探索過去一年來書店售出的所有書籍的風格。雖然每一本書籍都有其分類，例如：英文證照、程式語言、自然科學，等等。然而，你想了解的不單單只是「大方向」的風格，而是希望能夠掌握更深入的細節。
  如果去年書店業績不好，只賣出了 10 本書，也許你可以毛起來把這十本書讀完，就能夠大致了解客人的喜好。然而，如果銷量超過了 1000 本該怎麼辦呢？此時，我們就可以透過機器學習的技術，幫助我們找出這
  1000 本書籍的潛在風格。 我們假設每一本書籍都附有摘要，可以概括的理解書籍的內容。我們會輸入這 1000 本書籍的摘要到模型中，模型根據這些摘要探索其中的風格，並將風格類似的書籍歸屬在同一個群組中。
  在上述的過程中，我們只有輸入每本書籍的摘要到模型，並沒有先定好每一份摘要的風格，風格將由模型自己探索。因為我們沒有提供正確答案 (標籤) 給模型，因此屬於「非監督式學習」。
  此外，模型會根據書籍的摘要找出書籍與書籍之間的潛在關係，將關係較為接近的書籍歸屬在同一個群組中，因此屬於「分群 (Clustering) 任務」。 Step 2
  : 建立資料集 建立資料集的過程主要可以分為以下階段： 收集資料 (Data Collection) 收集資料的方法相當多元，我們可以聘請工讀生把每一本書籍的摘要在電腦上打出來，或是以爬蟲的方式在網路上收集這些書籍的摘要。
  資料探索 (Data Exploration) 與資料清理 (Data Cleaning) 在此階段中，我們會深入理解我們所收集到的資料，並將資料處理為適合輸入模型的形式。舉例來說，我們所準備的資料為「摘要」，由許多句子所組成。句子中可能包含許多不重要的元素，我們可以先將其剔除，以英文語句來說：
  刪除標點符號 (, . ! […]'
aliases:
- /machine-learning-basic-concept/book-clustering/
original_url: http://54.150.87.240/machine-learning-basic-concept/book-clustering/
wp_id: 329
images:
- images/define-problem-1.jpg
- images/feature-image-2.jpg
- images/find-k-in-k-means-algorithm.jpg
- images/k-means.jpg
- images/text-preprocessing.jpg
---

![](images/feature-image-2.jpg)

分群 (Clustering) 的概念

## 前言 & 概述

本篇為[機器學習基礎觀念](http://54.150.87.240/topics/machine-learning-basic-concept/)的第 9 篇文章。在前一篇文中，我們說明如何透過機器學習五步驟 ([定義問題](http://54.150.87.240/machine-learning-basic-concept/machine-learning-define-problem/)、[建立資料集](http://54.150.87.240/machine-learning-basic-concept/machine-learning-prepare-dataset/)、[模型訓練](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-training/)、[模型評估](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-evaluate/)與[模型推論](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-inference/)) 解決「房價預測」的問題。

房價預測屬於監督式學習 (Supervised Learning)，在本篇文章中將會以「探索書籍風格」作為非監督式學習 (Unsupervised Learning) 的例子。

## Step 1 : 定義問題

![define problem](images/define-problem-1.jpg)

定義「探索書籍風格」屬於什麼問題

假設你是一間大型書店的店長，你想探索過去一年來書店售出的所有書籍的風格。雖然每一本書籍都有其分類，例如：英文證照、程式語言、自然科學，等等。然而，你想了解的不單單只是「大方向」的風格，而是希望能夠掌握更深入的細節。

如果去年書店業績不好，只賣出了 10 本書，也許你可以毛起來把這十本書讀完，就能夠大致了解客人的喜好。然而，如果銷量超過了 1000 本該怎麼辦呢？此時，我們就可以透過機器學習的技術，幫助我們找出這 1000 本書籍的潛在風格。

我們假設每一本書籍都附有摘要，可以概括的理解書籍的內容。我們會輸入這 1000 本書籍的摘要到模型中，模型根據這些摘要探索其中的風格，並將風格類似的書籍歸屬在同一個群組中。

在上述的過程中，我們只有輸入每本書籍的摘要到模型，並沒有先定好每一份摘要的風格，風格將由模型自己探索。因為我們沒有提供正確答案 (標籤) 給模型，因此屬於「非監督式學習」。

此外，模型會根據書籍的摘要找出書籍與書籍之間的潛在關係，將關係較為接近的書籍歸屬在同一個群組中，因此屬於「分群 (Clustering) 任務」。

## Step 2 : 建立資料集

建立資料集的過程主要可以分為以下階段：

- **收集資料 (Data Collection)**  
  收集資料的方法相當多元，我們可以聘請工讀生把每一本書籍的摘要在電腦上打出來，或是以爬蟲的方式在網路上收集這些書籍的摘要。
- **資料探索 (Data Exploration) 與資料清理 (Data Cleaning)**
  - 在此階段中，我們會深入理解我們所收集到的資料，並將資料處理為適合輸入模型的形式。舉例來說，我們所準備的資料為「摘要」，由許多句子所組成。句子中可能包含許多不重要的元素，我們可以先將其剔除，以英文語句來說：
  - 刪除標點符號 (, . ! ?)
  - 刪除不重要的字詞 (a, an, the)
  - 將大寫轉為小寫 (White => white)
  - 將動詞的時態統一轉為現在式 (did => does)
  - 將資料進行清理過後，必須將資料由「字串類型」轉為「數值類型」才能輸入到模型中，這個過程稱為 **Data Vectorization**。

![text preprocessing](images/text-preprocessing.jpg)

將文字進行預處理

## Step 3 : 模型訓練

[建立資料集](http://54.150.87.240/machine-learning-basic-concept/machine-learning-prepare-dataset/)後，進入模型的建立以及訓練階段。在[定義問題](http://54.150.87.240/machine-learning-basic-concept/machine-learning-define-problem/)中，我們已經知道「探索書籍風格」任務屬於「分群 (Clustering) 問題」，解決 Clustering 問題最常見的模型為 K-Means。在本篇文章中，我們不會深入介紹 K-Means 的原理。

![k means](images/k-means.jpg)

K-Means 演算法示意圖

如同上圖所示，每一個點點都代表一本書籍的摘要，透過 K-Means 模型，我們可以將這些點點 (書籍) 分成多個群組。當我們指定 k=2 時，會將所有點點分成兩個群組 (如上圖左)；設定 k=3 時，則會將所有的點點分成三個群組 (如上圖右)。

## Step 4 : 模型評估

在模型評估階段，我們可以透過多種統計的指標 (metrics) 評估模型的好壞。如上圖所示，我們希望找到最適合的 Cluster 數目 (k)，使得所有類似的書籍都能夠被歸類到同一個群組。我們可以使用 **silhouette coefficient** 幫助我們找到最適合的 k。

![find k in k means algorithm](images/find-k-in-k-means-algorithm.jpg)

K-Means 演算法中不同的 K 值象徵不同的

透過 silhouette coefficient，我們可以觀察不同的 k 之下，模型的好壞。如下圖所示，最佳的 k 值為 19。當我們找到最適合的 k 後，我們就可以去觀察最大的 Cluster，也就是包含最多樣本 (書籍) 的 Cluster。透過該 Cluster 中的書籍摘要，就可以更深入的了解最熱門的書籍風格。

## Step 5 : 模型推論

在模型推論階段，我們可以開始使用模型。輸入新的書籍摘要到模型中，觀察這個摘要被分到哪一個 Cluster，或是觀察其他 Cluster 中的書籍摘要，了解在同一個 Cluster 中的書籍存在著什麼樣的類似風格，而被機器學習模型歸類為同一個群組。

## 結語

在本篇文章中，我們透過[機器學習五步驟](http://54.150.87.240/topics/machine-learning-basic-concept/)，解決「探索書籍風格」這個非監督式學習的例子，也了解到 **K-Means Model** 與 **silhouette coefficient** 指標的應用。在下一篇文章中，我們將會介紹更厲害的模型 (Neural Network) 解決更困難的問題。
