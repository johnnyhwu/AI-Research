---
title: '平行程式設計模型 : Shared Memory Model'
date: '2022-02-19T06:32:52'
lastmod: '2022-02-21T03:38:17'
slug: '%e5%b9%b3%e8%a1%8c%e7%a8%8b%e5%bc%8f%e8%a8%ad%e8%a8%88%e6%a8%a1%e5%9e%8b-shared-memory-model'
draft: false
categories:
- 其他
tags:
- Parallel Programming
description: 前言 & 概述 了解什麼是平行程式設計，以及為什麼需要平行程式設計後，我們將會開始學習平行程式設計中三種常見的模型 (Parallel Programming
  Model)。不同的 Parallel Programming Model 有著不同的實作方式與特性。在本篇文章，將會介紹 Shared Memory Model
  的意義與用法！ 什麼是 Shared Memory Model 如果你曾經在程式中使用過 Multi-Threading 的技巧，那們你一定對 Shared Memory
  的概念不陌生。透過 Shared Memory Model 開發平行程式時，通常會開發出所謂的「Multi-Thread Program」。在 Multi-Thread
  Program 中，我們可以將 Program 中性質相同的 Task 交由不同的 Thread 執行。這些 Thread 又能夠同時被不同的 Core 所執行，因此減少
  Program 整體的執行時間。 如果你對於 Thread 與 Process 的概念還相當陌生，可以參考本篇文章。在這裡我們可以先將一個 Program 單純視為
  Main Memory 中的一個 […]
aliases:
- /others/%e5%b9%b3%e8%a1%8c%e7%a8%8b%e5%bc%8f%e8%a8%ad%e8%a8%88%e6%a8%a1%e5%9e%8b-shared-memory-model/
original_url: http://54.150.87.240/others/%e5%b9%b3%e8%a1%8c%e7%a8%8b%e5%bc%8f%e8%a8%ad%e8%a8%88%e6%a8%a1%e5%9e%8b-shared-memory-model/
wp_id: 566
images:
- images/critical-section.jpg
- images/feature-image-14.jpg
- images/shared-memory-model-example-1.jpg
- images/shared-memory-model-example-2.jpg
- images/shared-memory-model-example.jpg
---

![](images/feature-image-14.jpg)

在 Shared Memory Model 之下，每一個 Processor 除了有自己的 Memory 外，也會有一塊共用的 Memory

## 前言 & 概述

[了解什麼是平行程式設計](http://54.150.87.240/others/what-is-parallel-programming/)，以及為什麼需要平行程式設計後，我們將會開始學習平行程式設計中三種常見的模型 (Parallel Programming Model)。不同的 Parallel Programming Model 有著不同的實作方式與特性。在本篇文章，將會介紹 Shared Memory Model 的意義與用法！

## 什麼是 Shared Memory Model

如果你曾經在程式中使用過 [Multi-Threading](https://www.wikiwand.com/zh-tw/%E5%A4%9A%E7%BA%BF%E7%A8%8B) 的技巧，那們你一定對 Shared Memory 的概念不陌生。透過 Shared Memory Model 開發平行程式時，通常會開發出所謂的「Multi-Thread Program」。在 Multi-Thread Program 中，我們可以將 Program 中性質相同的 Task 交由不同的 Thread 執行。這些 Thread 又能夠同時被不同的 Core 所執行，因此減少 Program 整體的執行時間。

如果你對於 Thread 與 Process 的概念還相當陌生，可以參考[本篇文章](https://totoroliu.medium.com/program-process-thread-%E5%B7%AE%E7%95%B0-4a360c7345e5)。在這裡我們可以先將一個 Program 單純視為 Main Memory 中的一個 Process。在 Multi-Thread Program 中，Process 包含了許多 Thread，每一個 Thread 都有自己的 Private Memory (例如 : Local Stack Variable)，所有的 Thread 也有共用的 Shared Memory (例如 : Static Variable 與 Global Heap)。

![](images/feature-image-14.jpg)

在 Shared Memory Model 之下，每一個 Processor 除了有自己的 Memory 外，也會有一塊共用的 Memory

如上圖所示，假設每一個 Processor 正在執行不同的 Thread，這些 Thread 有自己的 Private Memory 存放只有自己需要知道的資訊；所有的 Thread 也有 Shared Memory 可以分享彼此的資訊。

在 Shared Memory Model 中，不同的 Thread 透過「Implicitlt」的方式進行「溝通」。因為在程式碼中，我們並不會直接命令 Thread 去 Send or Receive Data，而是在 Shared Memory 進行讀取 (Read) 與寫入 (Write)，達到不同 Thread 的溝通！

## Shared Memory Model 範例

接著，我們透過一個簡單的問題與程式碼來更深入了解 Shared Memory Model 的概念與可能遇到的問題。

![shared memory model example](images/shared-memory-model-example.jpg)

假設有一個 Array，Array 中有 8 個元素

如上圖所示，假設我們現在有一個 Array，Array 中有 8 個元素。每一個元素都需要丟入 Function f 運算過後，並將全部的結果加總起來。

![shared memory model example](images/shared-memory-model-example-1.jpg)

將前面 4 個元素分給 Thread 1；將後面 4 個元素分給 Thread 2

為了減少 Program 的運行時間，我們在 Program 中建立 2 個 Thread，每一個 Thread 分別負責運算 4 個元素。Thread 1 與 Thread 2 會有自己的 (Private) Local Variable 紀錄 4 個元素經過運算後的總和；也會有一個 (Shared) Static Variable 紀錄整體的總和。

![shared memory model example](images/shared-memory-model-example-2.jpg)

程式碼範例 [source: Parallel Programming Course from NYCU]

若將上面的描述以程式碼來撰寫，程式碼的結構大致如上圖所示。首先是藍色中的框框，透過 fork Function，我們可以建立一個新的 Thread (Thread 1)，並指定該 Thread 要執行的 Function (sum)，並傳入這個 Thread 所負責的 Array 元素 (a[0 : n/2 -1])。下一行程式碼中，則是表示原來的 Main Thread 執行 sum Function，並負責 Array 中後半部的元素 (a[n/2 : n-1])。

如此一來，就形成了 Thread 1 與 Thread 2。Thread 1 與 Thread 2 都是執行 sum Function。主要是透過一個 for loop，將每一個元素丟到 f Function 後，再加入 static variable s 中 (static variable s 為 Thread 1 與 Thread 2 都可以讀取與寫入)。

## Race Condition

然而，若執行上述的程式碼，會發現結果不一定正確！原因在於 Thread 1 與 Thread 2 同時被不同的 Core 所執行，如果在 Thread 1 讀取 s 變數時，Thread 2 卻對 s 變數進行寫入，就會導致最後結果出錯。因為不同的 Core 針對同一塊記憶體空間不同的寫入與讀取速度，所造成的錯誤稱為 **Race Condition**。

舉例來說，如果目前 s = 16，Thread 1 讀取到 s = 16，準備將 f(A[i]) 的結果與 s 相加再寫回 s 中。然而，就在 Thread 1 將結果寫回 s 之前，Thread 2 已經將新的解果寫入 s 中。此時的 s = 20，然而 Thread 1 始終以為 s = 16。

可想而知，Thread 1 在後續進行的運算已經不正確！

## Critical Section

為了解決 Multi-Thread Program 中發生的 Race Condition，我們可以透過 Lock 機制，在 Program 中建立 Critical Section。

![critical section](images/critical-section.jpg)

建立 Critical Section 避免 Race Condition [source: Parallel Programming Course from NYCU]

如上圖程式碼所示，為了「減少」 Race Condiction 發生的機率，在每一個 Thread 中建立自己的 Local Variable (例如：local\_s1 與 local\_s2)，存放自己算出來的總和，最後再將自己算出來的總和與 s 變數相加並寫回 s 變數。

然而，「將自己算出來的總和與 s 變數相加並寫回 s 變數」的過程中，也有可能發生 Race Condition。

因此，為了完全「根絕」Race Condition 發生的可能，可以透過 lock 的機制，使得「將自己算出來的總和與 s 變數相加並寫回 s 變數」的過程變成一個 Critical Section。若該過程變成 Critical Section，則 OS 永遠只會允許一個 Thread 執行那個過程 (那行程式碼)，避免 Race Condition 出現。

最後，上圖中還出現一段紅字：「Why not do lock inside the loop ?」。意思是說，為什麼我們可以如同最原始的程式碼區塊 (上文中沒有 local\_s1 與 local\_s2 的版本)，並在 for loop 中 s = s + f(A[i]) 的程式碼前後加上 Lock 形成 Critical Section，一樣也可以避免 Race Condition 的產生。

原因在於，Lock 的機制是透過 System Call 來實作的，System Call 是一項高成本的指令。如果放在回圈中，反而可能因為呼叫太多次，造成更多的時間成本，而抵消了 Multi-Thread 帶來的優勢。

## 結語

在本篇文章中，我們介紹了 Parallel Programming Model 中的第一個 Model —— Shared Memory Model，並了解在實作上可能遇到 Race Condition 的問題。最簡單的方法，即是透過 Lock 機制形成 Critical Section 來解決 Race Condition 的問題。
