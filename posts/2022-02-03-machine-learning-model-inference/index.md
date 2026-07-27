---
title: '使用機器學習解決問題的五步驟 : 模型推論'
date: '2022-02-03T06:21:24'
lastmod: '2022-02-21T03:44:21'
slug: machine-learning-model-inference
draft: false
categories:
- 機器學習基礎觀念
tags:
- Deep Learning
- Machine Learning
description: '前言 & 概述 本篇為機器學習基礎觀念的第七篇文章，歷經了定義問題、建立資料集、模型訓練與模型評估後，終於來到了最後一步 —— 模型推論
  (Model Inference)。在本篇文章中，將會介紹什麼是「模型推論」以及其與「模型訓練」的差異。 模型推論的意義 模型推論 (Model Inference)
  實際上描述的就是模型已經完成訓練與評估，並將模型部署到實際的目標硬體中，將資料輸入到模型中，並由模型預測結果的過程。 以生活化的例子而言，模型推論就像是一位經過長期訓練的士兵，通過了各種測驗，終於能夠獨當一面的作戰。
  說到這裡，可能還是有些疑問。畢竟，在「模型訓練」的過程中，我們也會輸入樣本到模型中，並由模型產生預測結果。難道模型完成訓練後，只需要將模型「複製」到目標的裝置上運行，就算是模型推論了嗎
  ? 模型訓練與模型推論的差異 當然不是的！「模型訓練」的重點在於最小化損失函數 (Loss Function) 替模型找到一組最佳的參數。在此階段的模型可能會相當複雜，包含了成千上萬的參數在裡頭。
  然而，「模型推論」的重點在於將模型部署到目標硬體裝置或是生產線上，實際開始應用模型來解決問題。既然已經要實際應用模型於現實生活中，那麼模型的大小與運算量就會被慎重考慮！因為模型的大小與運算量攸關到記憶體的用量、運算所需時間、所需電力等因素。
  舉例來說，如果我們訓練出一個「人臉辨識」模型並將其部署到「空拍機」上，為了增強空拍機的續航力，模型的運算過程勢必不能消耗太多電力；或者我們要將模型部署到「自駕車」上，那麼模型的運算速度一定要夠快，慢了一秒都可能發生意外。
  因此，「模型推論」不單單只是輸入資料並產生預測的過程，還必須最佳化模型的效能、速度與能耗。常見的最佳化方法有兩種 : Pruning 與 Quantization。
  Pruning 與 Quantization 我們在這裡簡單說明 Pruning 與 Quantization 的概念，如果想更深入學習模型效能、速度與能耗的最佳化問題，可以參考
  TensorFlow 的官方文件。 Pruning : 全名為 Weight Pruning，中文稱為「權重修剪」。透過觀察模型中哪些參數對於模型的預測過程較沒有影響，將這些參數移除，達到降低模型複雜度與運算量的目的。
  Quantization : 中文稱為「量化」。模型中的參數如果是 32-bit 的浮點數，將其轉為 8-bit。透過簡化模型中參數的「精確程度」達到降低模型體積並提高運算速度的目的。
  不管是 Pruning 或是 Quantization，都是希望夠在簡化模型複雜度、提升運算速度並降低能源與時間消耗的同時，保持模型原來的預測準確度。 結語 在本篇文章中，我們介紹了模型推論的概念，並比較其與模型訓練的差異。也提到了
  […]'
aliases:
- /machine-learning-basic-concept/machine-learning-model-inference/
original_url: http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-inference/
wp_id: 315
images:
- images/model-inference.jpg
- images/model-training-vs-model-inference.jpg
---

![model training vs model inference](images/model-training-vs-model-inference.jpg)

模型訓練 (Model Training) 與模型推論 (Model Inference)

## 前言 & 概述

本篇為[機器學習基礎觀念](http://54.150.87.240/topics/machine-learning-basic-concept/)的第七篇文章，歷經了[定義問題](http://54.150.87.240/machine-learning-basic-concept/machine-learning-define-problem/)、[建立資料集](http://54.150.87.240/machine-learning-basic-concept/machine-learning-prepare-dataset/)、[模型訓練](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-training/)與[模型評估](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-evaluate/)後，終於來到了最後一步 —— 模型推論 (Model Inference)。在本篇文章中，將會介紹什麼是「模型推論」以及其與「模型訓練」的差異。

## 模型推論的意義

![model inference](images/model-inference.jpg)

模型推論即是直接使用模型進行預測，

**模型推論 (Model Inference)** 實際上描述的就是模型已經完成訓練與評估，並將模型部署到實際的目標硬體中，將資料輸入到模型中，並由模型預測結果的過程。

以生活化的例子而言，模型推論就像是一位經過長期訓練的士兵，通過了各種測驗，終於能夠獨當一面的作戰。

說到這裡，可能還是有些疑問。畢竟，在「[模型訓練](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-training/)」的過程中，我們也會輸入樣本到模型中，並由模型產生預測結果。難道模型完成訓練後，只需要將模型「複製」到目標的裝置上運行，就算是模型推論了嗎 ?

## 模型訓練與模型推論的差異

**當然不是的！**「[模型訓練](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-training/)」的重點在於最小化損失函數 (Loss Function) 替模型找到一組最佳的參數。在此階段的模型可能會相當複雜，包含了成千上萬的參數在裡頭。

然而，「模型推論」的重點在於將模型部署到目標硬體裝置或是生產線上，實際開始應用模型來解決問題。既然已經要實際應用模型於現實生活中，那麼**模型的大小**與**運算量**就會被慎重考慮！因為模型的大小與運算量攸關到記憶體的用量、運算所需時間、所需電力等因素。

舉例來說，如果我們訓練出一個「人臉辨識」模型並將其部署到「空拍機」上，為了增強空拍機的續航力，模型的運算過程勢必不能消耗太多電力；或者我們要將模型部署到「自駕車」上，那麼模型的運算速度一定要夠快，慢了一秒都可能發生意外。

因此，「模型推論」不單單只是輸入資料並產生預測的過程，還必須**最佳化模型的效能、速度與能耗**。常見的最佳化方法有兩種 : **Pruning** 與 **Quantization**。

## Pruning 與 Quantization

我們在這裡簡單說明 Pruning 與 Quantization 的概念，如果想更深入學習模型效能、速度與能耗的最佳化問題，可以參考 [TensorFlow 的官方文件](https://www.tensorflow.org/model_optimization/guide)。

Pruning : 全名為 Weight Pruning，中文稱為「權重修剪」。透過觀察模型中哪些參數對於模型的預測過程較沒有影響，將這些參數移除，達到降低模型複雜度與運算量的目的。  
Quantization : 中文稱為「量化」。模型中的參數如果是 32-bit 的浮點數，將其轉為 8-bit。透過簡化模型中參數的「精確程度」達到降低模型體積並提高運算速度的目的。  
不管是 Pruning 或是 Quantization，都是希望夠在簡化模型複雜度、提升運算速度並降低能源與時間消耗的同時，保持模型原來的預測準確度。

## 結語

在本篇文章中，我們介紹了模型推論的概念，並比較其與模型訓練的差異。也提到了 Pruning 與 Quantization 兩種模型最佳化的方法！在下一篇文章中，我們將以一個完整的例子，重新複習這五個步驟 ([定義問題](http://54.150.87.240/machine-learning-basic-concept/machine-learning-define-problem/)、[建立資料集](http://54.150.87.240/machine-learning-basic-concept/machine-learning-prepare-dataset/)、[模型訓練](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-training/)、[模型評估](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-evaluate/)與模型推論)。
