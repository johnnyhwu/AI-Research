---
title: 條件機率 vs 聯合機率
date: '2022-05-14T07:52:09'
lastmod: '2022-05-14T07:53:40'
slug: conditional-vs-joint-probability
draft: false
categories:
- 機器學習基礎觀念
tags:
- Machine Learning
- Probability
description: 前言 & 概述 在前一篇文章中，我們介紹了機率的基本觀念，包含 表示法 (Notation)、隨機變數 (Random Variable,
  RV)、三種基本的機率類型與乘法法則 (Multiplication Rule)。其中，三種基本機率類型中的「條件機率」與「聯合機率」經常使初學者分不清楚。因此，在本篇文章中，將會以更簡單的方式說明兩者的差別。此外，我們也會了解機率中「AND」、「OR」的概念。
  條件機率 (Conditional Probability) 在前一篇文章中，我們介紹過條件機率的定義。「條件機率」(Conditaionl Probability) 指的是某一個事件發生的「前提」之下，另外一個事件發生的機率。例如，A
  與 B 是兩個不的事件，在 B 事件發生的前提下，A 事件發生的機率為 P(A | B)。 我們也以撲克牌的例子說明：假設 B = 「抽出紅色的卡牌」，A =
  「抽出數字 4 的卡牌」，則 P(A | B) = 2/26 (因為已經先抽出 26 張紅色的卡牌，其中包含兩張數字 4)。 聯合機率 (Joint Probability)
  在前一篇文章中，我們也介紹過聯合機率的定義。「聯合機率」(Joint Probability) 指的是「兩個或多個」事件同時發生的機率。A 與 B 是兩個不同的事件，A
  與 B 同時發生的機率為 P(A ∩ B)。「∩」符號稱為「交集」，就是指兩個都要的意思。 我們也以撲克牌的例子說明：假設 […]
aliases:
- /machine-learning-basic-concept/conditional-vs-joint-probability/
original_url: http://54.150.87.240/machine-learning-basic-concept/conditional-vs-joint-probability/
wp_id: 808
images:
- images/feature-image.jpg
---

![feature image](images/feature-image.jpg)

source: Pixabay

## 前言 & 概述

在前一篇文章中，我們介紹了[機率的基本觀念](http://54.150.87.240/machine-learning-basic-concept/basic-probability-joint-marginal-conditional/)，包含 表示法 (Notation)、隨機變數 (Random Variable, RV)、三種基本的機率類型與乘法法則 (Multiplication Rule)。其中，三種基本機率類型中的「條件機率」與「聯合機率」經常使初學者分不清楚。因此，在本篇文章中，將會以更簡單的方式說明兩者的差別。此外，我們也會了解機率中「AND」、「OR」的概念。

## 條件機率 (Conditional Probability)

在[前一篇文章](http://54.150.87.240/machine-learning-basic-concept/basic-probability-joint-marginal-conditional/)中，我們介紹過條件機率的定義。「條件機率」(Conditaionl Probability) 指的是某一個事件發生的「前提」之下，另外一個事件發生的機率。例如，A 與 B 是兩個不的事件，在 B 事件發生的前提下，A 事件發生的機率為 P(A | B)。

我們也以撲克牌的例子說明：假設 B = 「抽出紅色的卡牌」，A = 「抽出數字 4 的卡牌」，則 P(A | B) = 2/26 (因為已經先抽出 26 張紅色的卡牌，其中包含兩張數字 4)。

## 聯合機率 (Joint Probability)

在[前一篇文章](http://54.150.87.240/machine-learning-basic-concept/basic-probability-joint-marginal-conditional/)中，我們也介紹過聯合機率的定義。「聯合機率」(Joint Probability) 指的是「兩個或多個」事件同時發生的機率。A 與 B 是兩個不同的事件，A 與 B 同時發生的機率為 P(A **∩** B)。「**∩**」符號稱為「交集」，就是指兩個都要的意思。

我們也以撲克牌的例子說明：假設 A =「從一副撲克牌中抽出一張 6」且 B =「從一副撲克牌中抽出一張紅色」，則 P(A **∩** B) = 2/52 (因為一副撲克牌有 52 張，同時是 6 又是紅色的有 2 張)。

## 條件機率 vs 聯合機率

對於第一次接觸機率概念的初學者而言，條件機率與聯合機率的概念還是稍微難以區分。因此，我們接著更深入的討論兩者的區別。

繼續前面撲克牌的例子，假設我們希望計算「抽出一張紅色卡牌且為數字 4」的機率，此機率就是聯合機率，可以表示為 P(Red and 4) = P(Red ∩ 4)。要計算這一個聯合機率，我們可以想像現在桌面上擺放著 52 張撲克牌，而且這些撲克牌都是「蓋上」的，因此我們不知道每張撲克牌實際的顏色與數字。但是，我們知道這 52 張卡牌中，顏色是紅色且數字為 4 的卡牌有 2 張。因此，P(Red and 4) = 2/52。

另外一種情況，假設我們希望計算「抽出一張數字為 4 的卡牌，且已經知道他是紅色」的機率，此機率就是條件機率，可以表示為 P(4 | Red)。要計算這一個條件機率，我們可以想像桌面上擺放著所有的 52 張撲克牌，但是抽出卡牌之前，我們已經事先將所有紅色的卡牌取出，並且攤開在桌上。又 26 張紅色的卡牌中，包含了 2 張數字 4 的卡牌。因此 P(4 | Red) = 2/26 = 1/13。

此外，我們也可以透過乘法法則 (Multiplication Rule) 計算上述的問題。以聯合機率 P(Red and 4) 為例，P(Red and 4) = P(4 and Red) 會等於 P(4 | Red) × P(Red) = 1/13 × 1/2 = 1/26 = 2/52。

*補充：P(Red) = 1/2，因為 52 張撲克牌中有一半是紅色的！*

## AND vs OR

- **AND**  
  在前面的例子中，我們解釋了聯合機率與條件機率的差別。然而，我們卻沒有提到該怎麼計算聯合機率 (Joint Probability)。所謂的聯合機率，即是兩個事件「同時」發生的機率。例如，P(A ∩ B) 即是 A 事件與 B 事件同時發生的機率。以乘法法則的角度出發，P(A ∩ B) = P(A | B) × P(B)。  
    
  我們再以一個生活化的例子說明聯合機率該怎麼算！假設現在我們手中有兩個骰子，A 事件 = 「第一顆骰子為 6」、B 事件 = 「第二顆骰子為 1」。  
    
  根據乘法法則，我們可以先計算 P(A | B) 與 P(B) 而得到 P(A ∩ B)。P(A | B) 指的是在「『第二顆骰子為 1』的前提下，『第一顆骰子為 6』的機率是多少」。聰明的你一定知道，不管第二顆骰子的結果為何，都和第一顆骰子沒有任何關係啊！因此，我們可以說 A 事件與 B 事件互為「獨立事件」。  
    
  當 A 事件與 B 事件互為獨立時，A 事件發生的機率不會受到 B 事件影響，因此 P(A | B) = P(A)。

再回到乘法法則，我們可以得到 P(A ∩ B) = P(A) × P(B) = 1/6 × 1/6 = 1/36。

- **OR**  
  在 AND 時，我們會將所有事件發生的機率「相乘」；在 OR 時，我們會將所有事件發生的機率「相加」。在數學上，會表示為 P(A **∪** B) = P(A) + P(B) – P(A **∩** B)。  
    
  其中，因為 P(A) + P(B) 時，A 與 B 重疊的部分會重複計算，因此需扣掉一次重疊的部分。  
    
  我們再以一個生活化的例子說明 OR 的概念！假設現在我們手中有兩個骰子，A 事件 = 「第一顆骰子為 6」、B 事件 = 「第二顆骰子為 1」。  
    
  則 P(A **∪** B) = 1/6 + 1/6 – 1/36 = 11/36。

## 結語

在本篇文章中，我們更深入的說明條件機率 (Conditional Probability) 與聯合機率 (Joint Probability) 的差別，也說明機率中 AND 與 OR 有什麼差別。若想學習更多機率的觀念，推薦到 Coursera 上報名葉丙成教授的[頑想學概率](https://zh-tw.coursera.org/learn/prob1)！
