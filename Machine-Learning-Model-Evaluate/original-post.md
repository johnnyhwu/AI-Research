---
title: '使用機器學習解決問題的五步驟 : 模型評估'
date: '2022-01-31T09:59:50'
lastmod: '2022-02-21T04:28:16'
slug: machine-learning-model-evaluate
draft: false
categories:
- 機器學習基礎觀念
tags:
- Classification
- Machine Learning
- Regression
description: '前言 & 概述 本篇為機器學習入門觀念的第六篇文章。在「使用機器學習解決問題的五步驟 : 模型訓練」一文中，我們介紹了模型訓練的觀念，並提到常見的模型種類。當模型完成訓練後，我們就可以來評估模型的好壞，也就是看看模型的訓練成果如何，我們稱之為「模型評估」(Model
  Evaluation)。 模型評估的概念 在建立資料集的過程中，我們準備了訓練資料與測試資料，透過訓練資料來訓練模型。評估模型時當然要使用模型沒有看過的資料，也就是測試資料。
  以擬人化的比喻來說，我們在考試之前經常會做一大堆練習題，此時正在經歷「訓練」的步驟。在考試當天，則是在經歷「評估」的步驟，透過考試來評估我們的練習狀況。考試卷上的題型通常與練習題類似。因此，如果在寫練習題時，我們真的搞懂觀念，那在考試階段至少可以拿到基本分！
  如果在寫練習題時，我們是死記硬背的把題目與答案記下來。那麼在考試時，我們當然就不會寫，畢竟要出現一模一樣的題目不容易！ 模型在「訓練」階段做得很棒，但是在「評估」階段卻做得很不理想，稱之為「過度擬合」(
  Overfitting)。也就是說，模型並沒有真的從訓練資料中學習到解決問題的方法，而只是把答案記下來而已。因此，透過「評估模型」階段，我們可以了解模型的好壞。
  模型評估常用的指標 為了評估一個模型的好壞，我們會善用各種指標來計算模型在評估階段得到的分數。以前面「考試」的例子來說，假設每一個題目都是「是非題」，老師批改考卷時，也就是說不是全對就是全錯，沒有對一半或錯一半的情況。則整張考卷得到的分數，取決於總共「對了幾題」。
  同樣的，對「分類圖片」的模型而言，每一張圖片一定有一個正確的類別。我們可以計算模型將幾張圖片「分類正確」而得到一個分數，稱為「準確率」(Accuracy)。 除了
  Accuracy 指標來評估「分類任務」模型的好壞之外，F1 Score 也是常見的評估指標，我們將在未來的文章中和大家介紹。 在「使用機器學習解決問題的五步驟
  : 定義問題」一文中，我介紹了常見的機器學習任務有「分類」與「回歸」。對於「回歸模型」而言，我們該如何評估該模型的好壞呢 ? 比較直觀的方式，就是計算回歸模型預測的數值與正確數值的差距。例如，回歸模型預測房價為
  12300，但是正確的房價為 15000，則這個模型在這個樣本的 Error 為 | 12300 – 15000 | = 2700。將模型在每一個樣本上的 Error
  取絕對值並加總後，再除以總樣本數，就能得到一個平均 Error，稱為 Mean Absolute Error (MAE)。我們也可以做一些「變形」，將每一個樣本的
  Error 取平方，再除以總樣本數，此時得到的 Error 稱為 Mean Square Error (MSE)。   上面兩張圖是在 scikit-learn
  […]'
aliases:
- /machine-learning-basic-concept/machine-learning-model-evaluate/
original_url: http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-evaluate/
wp_id: 257
images:
- images/feature-image-7.jpg
- images/loss-function-for-classification.jpg
- images/loss-function-for-regression.jpg
- images/machine-learning-process-1.jpg
- images/machine-learning-process-2.jpg
---

![feature image](images/feature-image-7.jpg)

source: Pixabay

## 前言 & 概述

![machine learning process](images/machine-learning-process-1.jpg)

用機器學習解決問題的第四步驟：模型評估

本篇為[機器學習入門觀念](http://54.150.87.240/topics/machine-learning-basic-concept/)的第六篇文章。在「[使用機器學習解決問題的五步驟 : 模型訓練](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-training/)」一文中，我們介紹了模型訓練的觀念，並提到常見的模型種類。當模型完成訓練後，我們就可以來評估模型的好壞，也就是看看模型的訓練成果如何，我們稱之為**「模型評估」(Model Evaluation)**。

## 模型評估的概念

在[建立資料集](http://54.150.87.240/machine-learning-basic-concept/machine-learning-prepare-dataset/)的過程中，我們準備了訓練資料與測試資料，透過訓練資料來訓練模型。評估模型時當然要使用模型沒有看過的資料，也就是測試資料。

以擬人化的比喻來說，我們在考試之前經常會做一大堆練習題，此時正在經歷「訓練」的步驟。在考試當天，則是在經歷「評估」的步驟，透過考試來評估我們的練習狀況。考試卷上的題型通常與練習題類似。因此，如果在寫練習題時，我們真的搞懂觀念，那在考試階段至少可以拿到基本分！

如果在寫練習題時，我們是死記硬背的把題目與答案記下來。那麼在考試時，我們當然就不會寫，畢竟要出現一模一樣的題目不容易！

模型在「訓練」階段做得很棒，但是在「評估」階段卻做得很不理想，稱之為**「過度擬合」( Overfitting)**。也就是說，模型並沒有真的從訓練資料中學習到解決問題的方法，而只是把答案記下來而已。因此，透過「評估模型」階段，我們可以了解模型的好壞。

## 模型評估常用的指標

為了評估一個模型的好壞，我們會善用各種指標來計算模型在評估階段得到的分數。以前面「考試」的例子來說，假設每一個題目都是「是非題」，老師批改考卷時，也就是說不是全對就是全錯，沒有對一半或錯一半的情況。則整張考卷得到的分數，取決於總共「對了幾題」。

同樣的，對「分類圖片」的模型而言，每一張圖片一定有一個正確的類別。我們可以計算模型將幾張圖片「分類正確」而得到一個分數，稱為**「準確率」(Accuracy)**。

除了 Accuracy 指標來評估「分類任務」模型的好壞之外，**F1 Score** 也是常見的評估指標，我們將在未來的文章中和大家介紹。

在「[使用機器學習解決問題的五步驟 : 定義問題](http://54.150.87.240/machine-learning-basic-concept/machine-learning-define-problem/)」一文中，我介紹了常見的機器學習任務有「分類」與「回歸」。對於「回歸模型」而言，我們該如何評估該模型的好壞呢 ?

比較直觀的方式，就是計算回歸模型預測的數值與正確數值的差距。例如，回歸模型預測房價為 12300，但是正確的房價為 15000，則這個模型在這個樣本的 Error 為 | 12300 – 15000 | = 2700。將模型在每一個樣本上的 Error 取絕對值並加總後，再除以總樣本數，就能得到一個平均 Error，稱為 **Mean Absolute Error (MAE)**。我們也可以做一些「變形」，將每一個樣本的 Error 取平方，再除以總樣本數，此時得到的 Error 稱為 **Mean Square Error (MSE)**。

![loss function for regression](images/loss-function-for-regression.jpg)

Regression 常用的 Loss Function [source: scikit-learn]

![loss function for classification](images/loss-function-for-classification.jpg)

Classification 常用的 Loss Function [source: scikit-learn]

上面兩張圖是在 [scikit-learn](https://scikit-learn.org/stable/modules/model_evaluation.html#the-scoring-parameter-defining-model-evaluation-rules) 套件中，在評估「分類」與「回歸」模型時，經常用到的指標。

## 結語

![machine learning process](images/machine-learning-process-2.jpg)

模型評估的結果如不佳，可能是前面的某個步驟有問題

在本篇文章中，我們介紹了模型評估 (Model Evaluation) 的概念，依據不同的任務，使用的評估指標也會有所不同。我們也提到 Overfitting 的概念，使得模型在評估階段表現不好。模型評估的結果如果不好，則可能是前面幾個步驟出了問題，也許需要重新定義問題、建立的資料集，或是重新訓練模型。直到進入下一步驟「[使用模型](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-inference/)」之前，我們會不斷的重複前面四個步驟，確保得到一個高品質的模型。
