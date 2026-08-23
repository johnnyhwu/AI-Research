---
title: '平行程式設計模型 : Distributed Memory Model'
date: '2022-03-01T14:38:08'
lastmod: '2022-03-01T14:38:08'
slug: parallel-programming-distributed-memory-model
draft: false
categories:
- 其他
tags:
- Parallel Programming
description: 前言 & 概述 在前一篇文章中，我們介紹了 Parallel Programming Model 中的第一種模型 —— Shared Memory
  Model，透過此模型經常會開發出所謂的 Multi-Thread 程式。本篇文章將會介紹第二種模型 —— Distributed Memory Model，並比較其與前者的差別。
  什麼是 Distributed Memory Model 在介紹 Shared Memory Model 時，我們將一個 Program 視為 Main Memory
  中的一個 Process。然而，實作 Distributed Memory Model 時，通常會開發出所謂的「Multi-Process」程式。在 Multi-Process
  Program 中，一個 Program 由許多 Process 組成，每一個 Process 之間彼此獨立，擁有自己獨立的 Memory，每一個 Process
  也同時被不同的 Core/Processor 執行。 如上圖所示，一個 Program 中包含 3 […]
aliases:
- /others/parallel-programming-distributed-memory-model/
original_url: http://54.150.87.240/others/parallel-programming-distributed-memory-model/
wp_id: 690
images:
- images/distributed-memory-model-example-1.jpg
- images/distributed-memory-model-example-2.jpg
- images/distributed-memory-model-example.jpg
- images/distributed-memory-model.jpg
- images/message-passing-interface.jpg
---

![distributed memory model](images/distributed-memory-model.jpg)

Distributed Memory Model 示意圖

## 前言 & 概述

在前一篇文章中，我們介紹了 Parallel Programming Model 中的第一種模型 —— [Shared Memory Model](http://54.150.87.240/others/%e5%b9%b3%e8%a1%8c%e7%a8%8b%e5%bc%8f%e8%a8%ad%e8%a8%88%e6%a8%a1%e5%9e%8b-shared-memory-model/)，透過此模型經常會開發出所謂的 Multi-Thread 程式。本篇文章將會介紹第二種模型 —— Distributed Memory Model，並比較其與前者的差別。

## 什麼是 Distributed Memory Model

在介紹 Shared Memory Model 時，我們將一個 Program 視為 Main Memory 中的一個 Process。然而，實作 Distributed Memory Model 時，通常會開發出所謂的「Multi-Process」程式。在 Multi-Process Program 中，一個 Program 由許多 Process 組成，每一個 Process 之間彼此獨立，擁有自己獨立的 Memory，每一個 Process 也同時被不同的 Core/Processor 執行。

![distributed memory model](images/distributed-memory-model.jpg)

Distributed Memory Model 示意圖

如上圖所示，一個 Program 中包含 3 個 Process，分別在 3 個 Processor 上執行。在我們的電腦中，作業系統 (OS) 會將每一個 Process 視為獨立的個體，彼此互不干預與影響，擁有自己的 Memory。當然，Process A 也不能去存取 Process B 的資料。如此一來，一個 Program 中的 Process 彼此應該如何溝通呢？

## Message Passing Interface

在 Distributed Memory Model 中，不同的 Process 可以透過「訊息傳遞」(Message Passing) 的方式溝通。Message Passing 就像是現實生活中的「寄信」，由一個人「Send」一封信，另外一個人則會「Receive」這封信。同樣的，在電腦上由一個 Process「Send」資料，由另外一個 Process「Receive」資料。

我們可以發現，不同於 Shared Memory Model 中「Implicit」的溝通方式，Distibuted Memory Model 使用「Explicit」的溝通方式，也就是在實作上真的會有「Send」與「Receive」的動作。

在電腦上，Message Passing 的實作方式有很多種，為了減輕程式開發者的負擔，通常會使用函式庫所提供的 Messaging Passing Interface (MPI) 實現 Process 之間的溝通。

![message passing interface](images/message-passing-interface.jpg)

透過 Message Passing Interface 實現 Process 之間的溝通 [source: Parallel Programming Course from NYCU]

如上圖所示，透過 MPI 程式開發者不需要煩惱實際 Process 之間是如何溝通的，僅需要明確寫出哪一個 Process Send 什麼資料，並由哪一個 Process Receive。

## Distributed Memory Model 範例

了解 Distributed Memory Model 的基本觀念後，我們透過一個非常簡單的範例，了解 Distributed Memory Model 可能遇到的問題。

![distributed memory model example](images/distributed-memory-model-example.jpg)

Distributed Memory Model 範例

如上圖所示，我們有一個 Array 包含了兩個元素 A1 與 A2。我們希望將這兩個元素經過 f Function 的運算後再總和起來得到 S。

假設目前電腦中有 2 個 Processor，因此我們可以透過 Distributed Memory Model 的概念，寫出一個 Two-Process Program。由 Processor 1 執行 Process 1 對 A1 進行運算；由 Processor 2 執行 Process 2 對 A2 進行運算。

![distributed memory model example](images/distributed-memory-model-example-1.jpg)

兩個 Processor 分別處理各自的元素，並將結果寄給另外一個 Processor [source: Parallel Programming Course from NYCU]

基於上述的想法，上圖呈現 2 個 Processor 執行任務時的虛擬碼。2 個 Processor 分別運算自己負責的元素，並存於 xlocal 中。再將 xlocal 寄 (send) 給另為一個 Processor，並接收 (receive)。

## Deadlock

上圖的虛擬碼看似沒什麼大問題，然而其實存在一個非常嚴重的 Bug，會使得電腦運行該程式時陷入 Deadlock！Deadlock 是學習作業系統 (OS) 時，必學的觀念。簡單來說，Deadlock 就是電腦中存在一組 Process 彼此互相等待，無法繼續執行。

以生活中的例子來比喻的話，Deadlock 就像是「我」和「我的同學」一起上美術課，製作自己的作品。做到一半時，我發現「我」需要「他」手上的剪刀才能繼續做下去；「他」發現「他」需要「我」手上的膠水才能繼續做下去。假設我們兩個都堅持握著自己的資源，而等待對方的資源。最後，我們兩個都會無法繼續製作，而停留在原地。

如果你想更深入的理解作業系統中的 Deadlock，可以參考[本篇文章](https://wangwilly.github.io/willywangkaa/2018/07/10/Operating-System-Deadlock/)！

![distributed memory model example](images/distributed-memory-model-example-1.jpg)

兩個 Processor 分別處理各自的元素，並將結果寄給另外一個 Processor [source: Parallel Programming Course from NYCU]

同理，在上圖中，Processor 1 執行 **send xlocal, proc2** 時，會將 xlocal 寄給 Processor 2。此時，必須等到 Processor 2 接收訊息，也就是 Processor 2 執行 **receive xremote, proc1** 後，Processor 1 才會繼續執行程式碼。

然而，如果兩個 Processor 非常巧合地同時寄送訊息給對方，也就是在同一個時間點，Processor 1 執行 **send xlocal, proc2**，Processor 2 執行 **send xlocal, proc1**。如此一來，兩個 Processor 就會一直在等待對方接收 (receive) 訊息，而無法繼續執行後續的程式碼。

![distributed memory model example](images/distributed-memory-model-example-2.jpg)

兩個 Processor 不要同時 Send 與 Receive 解決可能發生的 Deadlock [source: Parallel Programming Course from NYCU]

解決上述 Deadlock 最簡單的方式，即是確保兩個 Processor 不要同時傳送 (send) 訊息。因此，上圖將 Processor 2 的 send 與 receive 順序對調。

## Shared Memory vs Message Passing

在 Shared-Memory Model 中，不同的 Thread 透過 「Shared Memory」互相溝通；在 Distributed-Memory Model 中，不同的 Process 透過「Message Passing」互相溝通。然而，哪一中方法比較好呢？！

**It depends !** 兩種方法沒有誰優誰劣，必須視情況而定。以下簡單整理兩種方法的優缺點：

- **Shared Memory 優點**
  - Implicit Communication : 透過 Shared Memory，兩個 Thread 不需要真的 Send/Receive 資訊，而是在 Shared Memory 中 Load/Store 資訊
  - Low Overhead when Cached : 在有 Cache 的系統中，Processor 存取 Cache 中的資料遠遠快於 Main Memory
- **Shared Memory 缺點**
  - Require Syncronization Operation : 需要大量的同步機制，確保這個 Thread Load Data 前，另外一個 Thread 已經將最新的 Data Store 進去
  - Hard to Control Data Placement in Caching System : 正是所謂的「成也 Cache，敗也 Cache」！有了 Cache，能夠加速 Data 的讀取速度，但是卻產生另一個問題 —— False Sharing。False Sharing 雖然不會導致程式的結果錯誤，但是卻會大大降低程式的效能，完全犧牲掉平行化帶來的好處。
- **Message Passing 的優點**
  - Explicit Communication : 有時候透過 Explicit 的方式 (Send/Receive) 溝通，更能避免程式出錯。因此沒有哪一種溝通方式最棒 —— It depends !
  - Easy to Control Data Placement in Caching System
- **Message Passing 的缺點**
  - High Overhead : 相較於 Shared Memory，Process 之間的 Send/Receive Data 有更高的時間成本
  - Complex to Program

## 結語

在本篇文章中，我們介紹了第二種 Parallel Programming Model，並比較 Shared Memory 與 Message Passing 兩種 Communication 的優點與缺點。
