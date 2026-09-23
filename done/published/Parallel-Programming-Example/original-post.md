---
title: 平行程式設計的簡單範例
date: '2022-02-18T07:18:16'
lastmod: '2022-02-21T03:39:01'
slug: parallel-programming-example
draft: false
categories:
- 其他
tags:
- Parallel Programming
description: 前言 & 概述 了解平行程式設計 (Parallel Programming) 的基本概念後，本篇文章，將透過簡單的程式碼範例，更深入的理解平行程式的運作原理。最後，我們也會提到撰寫平行程式的「兩個方向」與「三個元素」。
  為什麼「必須」平行程式設計 前一篇文章，我們已經提到「為什麼需要平行程式設計」的三個原因。在這裡，我們先探討「為什麼『必須』平行程式設計」。   如上圖所示，四條線由上而下分別表示
  Transistor 數量、Clock Speed、Power 與 ILP。根據 Moore’s Law 我們可以發現電晶體的數量呈現逐年成長 (綠線)；然而，單個
  CPU 的 Clock Speed (深藍線) 卻已經趨緩下來；ILP (紫色線) 也是呈現趨緩的現象。 ILP 的全名為 Instruction-Level
  Parallelism，指的是即使只有 Single Core 的情況下，仍然可以透過 Compiler 與 CPU Architecture 達到指令層級的平行化運作，來加速程式的執行。
  由於單個 Core 的 Clock Speed 與 ILP 皆以達到極限，也就是說我們難以再仰賴單個 Core 來提升程式的效能，因此必須在軟體本身著手，透過平行化的程式設計，使得程式可以善加利用多個
  Core 的資源。 平行程式的簡單範例   假設我們有一個 […]
aliases:
- /others/parallel-programming-example/
original_url: http://54.150.87.240/others/parallel-programming-example/
wp_id: 551
images:
- images/cpu-performance.jpg
- images/distribute-task-in-parallel-programming.jpg
- images/feature-image-13.jpg
- images/parallel-programming-1.jpg
- images/reduction.jpg
- images/simple-parallel-program.jpg
- images/simple-program.jpg
---

![](images/feature-image-13.jpg)

source: Pixabay

## 前言 & 概述

了解[平行程式設計 (Parallel Programming) 的基本概念](http://54.150.87.240/others/what-is-parallel-programming/)後，本篇文章，將透過簡單的程式碼範例，更深入的理解平行程式的運作原理。最後，我們也會提到撰寫平行程式的「兩個方向」與「三個元素」。

## 為什麼「必須」平行程式設計

[前一篇文章](http://54.150.87.240/others/what-is-parallel-programming/)，我們已經提到「為什麼需要平行程式設計」的三個原因。在這裡，我們先探討「為什麼『必須』平行程式設計」。

![cpu performance](images/cpu-performance.jpg)

Intel CPU 各項指標的趨勢變化 [source: Computer Science Stack Exchange]

如上圖所示，四條線由上而下分別表示 Transistor 數量、Clock Speed、Power 與 ILP。根據 Moore’s Law 我們可以發現電晶體的數量呈現逐年成長 (綠線)；然而，單個 CPU 的 Clock Speed (深藍線) 卻已經趨緩下來；ILP (紫色線) 也是呈現趨緩的現象。

ILP 的全名為 Instruction-Level Parallelism，指的是即使只有 Single Core 的情況下，仍然可以透過 Compiler 與 CPU Architecture 達到指令層級的平行化運作，來加速程式的執行。

由於單個 Core 的 Clock Speed 與 ILP 皆以達到極限，也就是說我們難以再仰賴單個 Core 來提升程式的效能，因此必須在軟體本身著手，透過平行化的程式設計，使得程式可以善加利用多個 Core 的資源。

## 平行程式的簡單範例

![simple program](images/simple-program.jpg)

一段簡單的範例程式碼 [source: Parallel Programming Course from NYCU]

假設我們有一個 Array，Array 中有 n 個元素，每一個元素彼此之間沒有相依性，我們希望對每一個元素進行一些運算後，將結果加總起來。我們可以透過上圖的程式，完成這項任務。

![simple parallel program](images/simple-parallel-program.jpg)

每個 core 計算自己負責哪些元素，並將結果存在 my\_sum 中 [source: Parallel Programming Course from NYCU]

因為 Array 中的每一個元素彼此沒有相依性，因此我們可以透過 Parallel Programming 的技巧，將 Array 中的所有元素平均分配給所有的 Core。

舉例來說，假設我們的電腦上目前有 p 個 Core，且 Array 中有 n 個元素。那麼可以平均的分給每一個 Core n/p 個元素。如此一來，原本只有一個 Core 負責 n 個元素，現在由多個 Core 平均分擔，加速程式的執行。

![distribute task in parallel programming](images/distribute-task-in-parallel-programming.jpg)

將所有數字平均分配給多個 core 執行 [source: source: Parallel Programming Course from NYCU]

我們以真實數字進行更具體的說明！如上圖所示，假設 Array 中有 24 個數字，且電腦上有 8 個 Core，我們平均分配 3 個數字給每一個 Core。

![parallel programming](images/parallel-programming-1.jpg)

每個 core 將自己計算的結果存起來 [source: Parallel Programming Course from NYCU]

每一個 Core 都會算出自己的結果，存於 “my\_sum” 變數當中。最後，再由一個 Master Core 負責將所有的 Core 的結果加總起來。透過 Parallel Programming，原來只由 Master Core 負責 24 個數字的運算，現在由 8 個 Core 同時處理自己的部分，再由 Master Core 把大家的結果集合在一起。

## 平行化 Reduction 的過程

在上述的例子中，我們知道最後是由 Master Core 統一將所有 Core 的結果加總在一起。因此，Master Core 必須將 8 個數字加總在一起形成 1 個數字。由原來的「很多元素」經過運算後變成「很少元素」的過程稱為 Reduction。Reduction 通常可以再進行平行化處理。

![reduction](images/reduction.jpg)

reduction 的過程：原本有 8 個數字最後減少為 1 個數字 [source: Parallel Programming Course from NYCU]

舉例來說，我們可以利用 Core 0 加總 Core 1、Core 2 加總 Core 3、Core 4 加總 Core 5、Core 6 加總 Core 7。如此一來，在時間點 A 時，同時就有 4 個 Addition 發生。將 Reduction 過程以 Parallel Programming 改寫後，原來由 Master Core (Core 0) 進行 7 個 Addition，現在只需要進行 3 個 Addition。

## 平行化程式設計的兩個方向

針對原有單線程的程式進行平行化處理時，有兩個方向可以進行：Task-Parallelism 與 Data-Parallelism。

- Task-Parallelism

將原來的問題拆分成多個不同的 Task，每一個 Core 都會處理自己的 Task。舉例來說，假設餐廳有 3 個師傅要做 300 個蛋糕。由每一個師傅負責每一個蛋糕的某些步驟，因此每一個師傅所做的事情都會不同。

- Data-Parallelism

將原來的問題中涉及資料處理的部分，分配給每一個 Core 處理部分資料。以上述蛋糕師傅的例子，每一個師傅即是負責 100 個蛋糕。因此，每一個師傅所做的事情會相同。

## 平行化程式設計的三個元素

針對原有的單線程程式進行平行化處理時，有三個元素需要考慮：Communication、Load Balancing 與 Synchronization。

- Communication

平行化程式中經常會用到多個 Core，這些 Core 彼此應該如何傳遞訊息。

- Load Balancing

如何讓每一個 Core 都能平均分擔一些任務。在上面的例子中，我們將所有的資料量平均分給每一個 Core。然而，有些清況不同類型資料所需的處理時間也不同，若依照數量進行分配，可能導致某些 Core 還在執行，某些 Core 已經閒置下來。

- Synchronization

有些情況，我們希望某些 Core 要等待其他 Core 執行完後才繼續執行。

上述 3 點中，Communication 與Synchronization 是為了確保 Parallel Program 與原來的 Serial Program 執行的結果相同；Load Balancing 則是為了最佳化 Parallel Program 的效能。

## 結語

本文中，我們了解到「為什麼『必須』平行程式設計」也透過簡單的範例程式，了解平行化的概念。最後，我們也提到撰寫平行化程式的 2 個方向：

- Task-Parallelism
- Data-Parallelism

以及平行化程式中必須注意的 3 個元素：

- Communication
- Load Balancing
- Synchronization
