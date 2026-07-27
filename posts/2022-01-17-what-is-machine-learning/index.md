---
title: 什麼是機器學習 ?
date: '2022-01-17T13:44:34'
lastmod: '2022-02-21T04:27:32'
slug: what-is-machine-learning
draft: false
categories:
- 機器學習基礎觀念
tags:
- Machine Learning
description: "前言 & 概述 Machine Learning 是一種軟體技術也是實現人工智慧 (AI) 的方法之一。透過 AI 的技術，我們不需要寫死程式碼，教導電腦解決問題。而是提供大量數據，讓電腦自己從數據中發掘解決問題的方法。在本篇文章中，將會介紹什麼是\
  \ Machine Learning、Machine Learning 中又包含哪些類別，以及 Machine Learning 與 Traditional Programming\
  \ 又差在哪呢！ 什麼是機器學習   「機器學習」是一種可以讓電腦從資料中學習，發現資料中的規律與模式，並進行預測的演算法。機器學習也是「人工智慧」(Artificial\
  \ Intrlligence) 的一種實現方式。至於什麼是人工智慧呢？人工智慧指的是電腦能夠像是擁有人類般的智慧一樣來解決問題。 機器學習底下有非常多的演算法，可以幫助機器\
  \ (電腦) 從資料中學習，上圖的 Deep Learning (深度學習) 即屬於其中一種特別的演算法。當然，深度學習中又包含了非常多的演算法，但這不在此篇文章的教學目標中。\
  \ 機器學習中包含什麼演算法 如同前面所說的，機器學習中包含了非常多的演算法，然而大致可以將這些演算法區分為三種類別：Supervised Learning、Unsupervised\
  \ Learning 與 Reinforcement Learning。這三種類別底下當然包含很多演算法，這三種類別也有其各自的特性！ \bSupervised\
  \ Learning 第一種為 Supervised Learning，中文稱為「監督式學習」。爲什麼稱為「監督式」呢？因為這類的學習方法像是有一個監督者在電腦旁邊監督它學習一樣。通常會準備非常多的「資料」以及這些資料的「標籤」，\b\
  電腦在看了資料後必須說出這個資料的標籤。即使電腦說錯了，因為早就有準備正確的標籤，所以電腦可以知道正確的標籤是什麼。 這就像是小孩子在學習英文字母的過程中，有一個老師在旁邊聽小孩子的發音，如果小孩子念錯了，老師就會立刻糾正，告訴小孩子正確的發音。\
  \ Unsupervised Learning 第二種為 Unsupervised Learning，中文稱為「非監督式學習」。相較於監督式學習，這類型的學習方式就沒有一個監督者站在電腦旁邊告訴他正確答案。電腦必須自己去摸索，找到正確的規律。也就是說，我們會準備很多「資料」給電腦，然而卻沒有這些資料的標籤。電腦必須自己觀察這些資料找到他們的相同以及不同之處，發現他們存在的某種模式。\
  \ 這就像是小嬰兒在分類綠豆和紅豆的過程，他並不知道誰是綠豆誰是紅豆，而是依據他的觀察把「綠的」放一邊，把「紅的」放另外一邊。 Reinforcement Learning\
  \ 第三種為 Reinforcement […]"
aliases:
- /machine-learning-basic-concept/what-is-machine-learning/
original_url: http://54.150.87.240/machine-learning-basic-concept/what-is-machine-learning/
wp_id: 18
images:
- images/AI-vs-ML-vs-DL.jpg
- images/algorithm-in-ML.jpg
- images/machine-learning-vs-traditional-programming.jpg
---

## 前言 & 概述

Machine Learning 是一種軟體技術也是實現人工智慧 (AI) 的方法之一。透過 AI 的技術，我們不需要寫死程式碼，教導電腦解決問題。而是提供大量數據，讓電腦自己從數據中發掘解決問題的方法。在本篇文章中，將會介紹什麼是 Machine Learning、Machine Learning 中又包含哪些類別，以及 Machine Learning 與 Traditional Programming 又差在哪呢！

## 什麼是機器學習

![AI vs ML vs DL](images/AI-vs-ML-vs-DL.jpg)

AI、ML 與 DL 之間的關係 [source: Nvidia]

「機器學習」是一種可以讓電腦從資料中學習，發現資料中的規律與模式，並進行預測的演算法。機器學習也是「人工智慧」(Artificial Intrlligence) 的一種實現方式。至於什麼是人工智慧呢？人工智慧指的是電腦能夠像是擁有人類般的智慧一樣來解決問題。  
機器學習底下有非常多的演算法，可以幫助機器 (電腦) 從資料中學習，上圖的 Deep Learning (深度學習) 即屬於其中一種特別的演算法。當然，深度學習中又包含了非常多的演算法，但這不在此篇文章的教學目標中。

## 機器學習中包含什麼演算法

![algorithm in machine learning](images/algorithm-in-ML.jpg)

MachineLearning 底下的演算法主要分為三種類別

如同前面所說的，機器學習中包含了非常多的演算法，然而大致可以將這些演算法區分為三種類別：**Supervised Learning**、**Unsupervised Learning** 與 **Reinforcement Learning**。這三種類別底下當然包含很多演算法，這三種類別也有其各自的特性！

- ****Supervised Learning****

第一種為 Supervised Learning，中文稱為「監督式學習」。爲什麼稱為「監督式」呢？因為這類的學習方法像是有一個監督者在電腦旁邊監督它學習一樣。通常會準備非常多的「資料」以及這些資料的「標籤」，電腦在看了資料後必須說出這個資料的標籤。即使電腦說錯了，因為早就有準備正確的標籤，所以電腦可以知道正確的標籤是什麼。

這就像是小孩子在學習英文字母的過程中，有一個老師在旁邊聽小孩子的發音，如果小孩子念錯了，老師就會立刻糾正，告訴小孩子正確的發音。

- **Unsupervised Learning**

第二種為 Unsupervised Learning，中文稱為「非監督式學習」。相較於監督式學習，這類型的學習方式就沒有一個監督者站在電腦旁邊告訴他正確答案。電腦必須自己去摸索，找到正確的規律。也就是說，我們會準備很多「資料」給電腦，然而卻沒有這些資料的標籤。電腦必須自己觀察這些資料找到他們的相同以及不同之處，發現他們存在的某種模式。

這就像是小嬰兒在分類綠豆和紅豆的過程，他並不知道誰是綠豆誰是紅豆，而是依據他的觀察把「綠的」放一邊，把「紅的」放另外一邊。

- **Reinforcement Learning**

第三種為 Reinforcement Learning，中文稱為「強化學習」。相較於前面兩種學習方式，這類型的學習方式更像「人類」會有兩個重要的元素：代理人 (Agent) 與環境 (Environment)。代理人會觀察目前週遭的環境並做出一個「行為」。環境則會依據代理人行為的好壞給予這個行為一個「獎勵」。代理人的最終目的就是要獲得最多的獎勵。為了要達到目的，代理人就會學習去表現得更好。

實際上，對於這種學習方法我們再熟悉不過了。我們在學校、職場上會因為做對事情收到褒獎，因為做錯事情受到責罰，我們因此而更懂的拿捏分寸，更知道如何把事情做好。

## Machine Learning vs Traditional Programming

![machine learning vs traditional programming](images/machine-learning-vs-traditional-programming.jpg)

Machine Learning 與 Traditional Programming 的差別 [source: Udacity]

在傳統軟體開發的領域中，通常是由「人類」分析數據，透過數據我們可以更了解問題是什麼，進而發想一個解決方案，再透過程式碼將解決方案轉化為一個程式。  
例如：我經常忘記看天氣預報，所以下雨天時常忘記帶雨傘，淋得全身濕濕的。根據這個問題，可能的解決辦法是透過一個程式自動抓取明天的天氣預報，如果預報中指出明天會下雨，就發送 Line 通知到我的手機上。有了這套解決辦法的思路，就能透過爬蟲、Line Bot API 等技術寫出一個程式，進而解決問題。  
然而，有些問題沒有辦法透過很明確的方法來解決。

例如：辨識一張相片中是貓咪還是狗狗。貓咪和狗狗在身型上就有很多特徵的差異，光是狗狗或貓咪自己也有很多種類的差別，每個種類也要考慮很多特徵進行區分。此外，照片當時拍攝的光線、視角也會影響照片中物體的樣子。如果要將這些特徵全部寫在程式中，大概一輩子也寫不完。  
Machine Learning 的優勢正是能夠解決這類問題。在 Machine Learning 的演算法中，我們通常會準備以下三個元素：

1. 大量資料
2. 模型
3. 訓練模型的方法

透過「大量資料」以及「訓練模型的方法」我們訓練出一個能夠辨識圖片是貓咪還是狗狗的「模型」。也就是說，將這張圖片輸入模型中，模型會輸出一個結果：是貓咪與是狗狗的機率分別是多少。透過 Machine Learning 的技術解決 Traditional Programming 無法解決的問題。

## 結語

在本篇文章中，對 Machine Learning 有了初步的認識，了解 Machine Learning 底下的三種類別的演算法，並區分 Machine Learning 與 Traditional Programming 的區別。此文章屬於 AWS ML Foundation 的第一篇文章，在[下一篇文章](http://54.150.87.240/machine-learning-basic-concept/model-training-inference/)中，將會介紹 Machine Learning 中的「模型」以及「訓練的方法」。
