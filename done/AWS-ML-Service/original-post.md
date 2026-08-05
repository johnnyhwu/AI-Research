---
title: AWS ML Service 介紹
date: '2022-02-11T08:08:16'
lastmod: '2022-02-21T03:39:47'
slug: aws-ml-service
draft: false
categories:
- 其他
tags:
- AWS
- Deep Learning
- Machine Learning
description: '前言 & 概述 AWS (Amazon Web Service) 提供了許多 AI 與 ML Services。透過 AWS AI Services，開發者可以快速的將
  AI 技術引入應用程式中。此外，機器學習領域的開發者也可以透過 AWS ML Services —— Amazon SageMaker 簡化機器學習的建置、訓練與部署的各項流程。本文將會介紹
  AWS ML Services 中的三種工具 : Amazon SageMaker Studio、Amazon SageMaker Distributed Training
  與 Amazon SageMaker Clarify。 Amazon SageMaker Studio 簡單來說，Amazon SageMaker Studio
  是一個專為機器學習所開發的 IDE。在此 IDE 中，我們可以完成機器學習的所有流程，包含資料集預處理、模型選擇與建立、模型訓練與模型部署，將所有機器學習相關的流程都統合在這一個
  IDE 中來提升機器學習模型的開發效率。 便利的使用與分享 Notebook 在進行機器學習模型的開發時，我們經常會使用 Jupyter […]'
aliases:
- /others/aws-ml-service/
original_url: http://54.150.87.240/others/aws-ml-service/
wp_id: 513
images:
- images/machine-learning-on-aws.jpeg
---

![machine learning on aws](images/machine-learning-on-aws.jpeg)

source: AWS Machine Learning Foundation Course on Udacity

## 前言 & 概述

AWS (Amazon Web Service) 提供了許多 AI 與 ML Services。透過 [AWS AI Services](https://aws.amazon.com/tw/machine-learning/ai-services/)，開發者可以快速的將 AI 技術引入應用程式中。此外，機器學習領域的開發者也可以透過 AWS ML Services —— [Amazon SageMaker](https://aws.amazon.com/tw/sagemaker/) 簡化機器學習的建置、訓練與部署的各項流程。本文將會介紹 AWS ML Services 中的三種工具 : [Amazon SageMaker Studio](https://aws.amazon.com/tw/sagemaker/studio/)、[Amazon SageMaker Distributed Training](https://aws.amazon.com/tw/sagemaker/distributed-training/) 與 [Amazon SageMaker Clarify](https://aws.amazon.com/tw/sagemaker/clarify/)。

## Amazon SageMaker Studio

簡單來說，[Amazon SageMaker Studio](https://aws.amazon.com/tw/sagemaker/studio/) 是一個專為機器學習所開發的 IDE。在此 IDE 中，我們可以完成機器學習的所有流程，包含資料集預處理、模型選擇與建立、模型訓練與模型部署，將所有機器學習相關的流程都統合在這一個 IDE 中來提升機器學習模型的開發效率。

- **便利的使用與分享 Notebook**  
  在進行機器學習模型的開發時，我們經常會使用 Jupyter Notebook 作為開發環境。 Amazon SageMaker Studio 也不例外，讓開發者透過簡單幾個點擊就能建立 Notebook 開發環境並與他人分享該 Notebook，且能夠自動地調配運算資源。

- **結構化整理實驗數據**當我們完成模型的建立後，會開始根據我們研究目的進行一些實驗。也許是對模型的架構進行變更或是使用不同的數據集，Amazon SageMaker Studio 會自動地將這些實驗結果進行排序並統整，以結構化的表格呈現出來。

- **內建模型與解決方案**  
  Amazon SageMaker Studio 上提供超過 150 種開源的機器學習模型，與超過 15 種使用情境的解決方案 (例如：Fraud Detection)。因此，我們可以在短短幾分鐘內就建立好模型。

- **彈性選擇開發環境**  
  目前主流的深度學習開發框架主要有三個：TensorFlow、PyTorch 與 MXNet。這些不同的框架又有多種版本可以選擇。Amazon SageMaker Studio 上提供多種以建立好的開發環境，當然開發者也可以依自己的喜好建立自己的開發環境，並將該環境分享出去。

- **框架效能的最佳化**當我們在進行機器學習專案的開發時，為了加速模型的訓練速度，需要經過繁複的設定，才能讓框架善用電腦的硬體資源 (GPU)。Amazon SageMaker Studio 會自動根據可用的硬體資源，最佳化開發者所使用的框架。

## Amazon SageMaker Distributed Training

現今所謂 state-of-the-art 的深度學習模型所包含的參數量動輒超過數百萬，許多模型的參數量甚至超過數十億。舉例來說，於 2020 年 5 月發布的自然語言模型 —— GPT-3 包含了 1750 億個參數。對於如此碩大的模型，我們幾乎不可能把他放在一個 GPU 上訓練，因此必須透過平行化的技術，將模型分配於多個 GPU 上訓練，也就是「分散式訓練」(Distributed Training)。

然而，要進行機器學習模型的分散式訓練，也需要一定的技術門檻。因此，Amazon SageMaker Distributed Training 的優勢在於開法者僅需置入幾行程式碼，就能自動的進行分散式訓練。

Amazon SageMaker Distributed Training 透過「模型平行化」與「資料平行化」的技術來達到分散式訓練的效果。「資料平行化」(Data Parallelism) 將非常大的資料集進行拆分，以 Concurrent 的方式提升模型的訓練速度；「模型平行化」(Model Parallelism) 則是將非常大的模型拆成許多小部分，分散在多個 GPU 上訓練。

## Amazon SageMaker Clarify

當我們在訓練機器學習的模型時，我們準備的訓練資料對模型訓練後的品質會有很大的影響。舉例來說，如果我們模型必須針對「不同的年齡層」的人進行一些預測，如果我們的訓練資料中多數為「壯年人」，那麼模型針對「老年人」或是「孩童」的預測準確率就會明顯較低。這是因為 Imbalanced Data 所導致的 Model Bias，使得模型的預測結果包含「偏見」。

Amazon SageMaker Clarify 正是能幫助機器學習開發者，了解模型與訓練資料中存在的 Bias。藉此，我們能夠更理解模型的行為。

針對「訓練資料」方面，Amazon SageMaker Clarify 結合 Amazon SageMaker Data Wrangler 辨識資料集中的 Bias，我們可以指定想要觀察的 Attribute，Amazon SageMaker Clarify 就可以進行分析，並以報表的形式呈現分析結過。

針對「模型」方面，Amazon SageMaker Clarify 結合 Amazon SageMaker Experiments 分析訓練過後的模型針對測試資料集中不同的 Attribute 所產生的 Bias。例如：模型是否更容易將「老年人」的樣本，分類到某一個特定類別。最後，以視覺化的報表將分析結果呈現給使用者。

## 結語

在本文中，我簡單說明 AWS ML Services 是什麼，並以 Amazon SageMaker Studio、Amazon SageMaker Distributed Training 與 Amazon SageMaker Clarify 等三項工具做為代表。

總結來說：

- 透過 Amazon SageMaker Studio 我們可以在一個專為機器學習打造的 IDE 中，完成機器學習開發的各項流程。
- 透過 Amazon SageMaker Distributed Training 我們可以處理大規模的資料集與模型。
- 透過 Amazon SageMaker Clarify 我們可以觀察資料集與模型中存在的 Bias。
