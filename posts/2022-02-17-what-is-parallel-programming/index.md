---
title: 什麼是平行程式設計
date: '2022-02-17T01:55:02'
lastmod: '2022-02-21T03:39:26'
slug: what-is-parallel-programming
draft: false
categories:
- 其他
tags:
- Parallel Programming
description: 前言 & 概述 本篇文章將會說明什麼是「平行程式設計」(Parallel Programming)，並說明其與原來的 (非平行) 程式設計模式有何不同。此外，我們也會了解為什麼需要用到平行程式設計。
  單線程程式設計 在了解「平行程式設計」(Parallel Programming) 之前，我們需要先回顧一下原始的 (非平行) 程式設計。 我們從小到大在寫程式時，通常是以「單線程」(Single-Thread)
  的角度在撰寫的；也就是說，我們在寫 Code 時，通常是預期處理器會「由上而下」的「一行一行」執行我們的 Code，也就是 Serial Computing 的概念。
  更具體來說，在更早的年代，大概是電腦還處於單核心的遠古時期，軟體工程師在寫程式時，通常會將「問題」分解為一系列的「指令」，並預期這些指令會 one-by-one
  的被處理器執行。(如下圖所示) 即使現今隨便的一台電腦上就有 4 個或 8 個以上的 core，但是因為我們都是以「單線程」(Single-Thread) 的角度在寫程式，使得在「同一時間」永遠只有
  1 個 core 在執行我們的程式，其餘的 core 的運算資源就被閒置，而白白浪費了！ 平行化程式設計 平行程式設計 (Parallel Programming)
  則是則是在寫 Code 階段加入一些特別的技術，使得程式可以在「同一時間」被多個 core 執行。進行平行程式設計時，軟體工程師通常會將問題拆分成「多組」一系列的「指令」，並把每一組指令交付給一個
  core 來執行。 進行平行程式設計時，我們將不同組的指令交給不同的 core 執行，必須先確保不同組的指令之間不具有「相依性」。也就是說，不可以一定要先執行完某一組的指令才能執行另外一組。
  「同一時間」執行的概念 在前面的解釋中，我們提到 Parallel Programming […]
aliases:
- /others/what-is-parallel-programming/
original_url: http://54.150.87.240/others/what-is-parallel-programming/
wp_id: 524
images:
- images/feature-image-13.jpg
- images/parallel-programming-vs-distributed-programming.jpg
- images/parallel-programming.jpg
- images/serial-program.jpg
---

![](images/feature-image-13.jpg)

source: Pixabay

## 前言 & 概述

本篇文章將會說明什麼是「平行程式設計」(Parallel Programming)，並說明其與原來的 (非平行) 程式設計模式有何不同。此外，我們也會了解為什麼需要用到平行程式設計。

## 單線程程式設計

在了解「平行程式設計」(Parallel Programming) 之前，我們需要先回顧一下原始的 (非平行) 程式設計。

我們從小到大在寫程式時，通常是以「單線程」(**Single-Thread**) 的角度在撰寫的；也就是說，我們在寫 Code 時，通常是預期處理器會「由上而下」的「一行一行」執行我們的 Code，也就是 **Serial Computing** 的概念。

更具體來說，在更早的年代，大概是電腦還處於單核心的遠古時期，軟體工程師在寫程式時，通常會將「問題」分解為一系列的「指令」，並預期這些指令會 one-by-one 的被處理器執行。(如下圖所示)

![serial program](images/serial-program.jpg)

一個程式被拆解為一連串的指令被處理器執行

即使現今隨便的一台電腦上就有 4 個或 8 個以上的 core，但是因為我們都是以「單線程」(Single-Thread) 的角度在寫程式，使得在「同一時間」永遠只有 1 個 core 在執行我們的程式，其餘的 core 的運算資源就被閒置，而白白浪費了！

## 平行化程式設計

平行程式設計 (Parallel Programming) 則是則是在寫 Code 階段加入一些特別的技術，使得程式可以在「同一時間」被多個 core 執行。進行平行程式設計時，軟體工程師通常會將問題拆分成「多組」一系列的「指令」，並把每一組指令交付給一個 core 來執行。

![parallel programming](images/parallel-programming.jpg)

Parallel Programming 即是一個程式同時由多個處理器執行

進行平行程式設計時，我們將不同組的指令交給不同的 core 執行，必須先確保不同組的指令之間不具有「相依性」。也就是說，不可以一定要先執行完某一組的指令才能執行另外一組。

## 「同一時間」執行的概念

在前面的解釋中，我們提到 Parallel Programming 可以使得程式在「同一時間」被許多 core 執行。然而，在資訊工程中針對「同一時間」的執行又分成很多種。

- **Concurrent Computing**

指的是一個 Program 被拆成很多小的 Task，每一個 Task 都是處於「處理中」的狀態，但是其實這些 Task 並不是「同時」正在被執行，而是以「穿插」(Interleave) 的方式在執行。舉例來說，Task A 與 Task B 都是處於正在被執行的階段，然而 core 是執行完 Task A 的某一部份時，切換到執行 Task B。

- **Parallel Computing**

指的是一個 Program 被拆成很多小的 Task，每一個 Task 都是處於「處理中」的狀態，但是這些 Task 理論上是「同時」正在被執行。

- **Distributed Computing**

上述的兩種 Computing 都是在「一台電腦」上所發生的。Distributed Computing 則是「多台電腦」的分散運算。以下圖為例，在 Parallel Computing 中，通常是「一台電腦」中有多個 Processor，這些 Processor 會有共用 Memory 進行溝通。在 Distributed Computing 中，則是有「多台電腦」(每一台電腦可以視為一個 node)，每一個 node 中都有自己的 Processor 與 Memory，不同的 node 透過 Network 來溝通。

![parallel computing vs distributed computing](images/parallel-programming-vs-distributed-programming.jpg)

Parallel Computing 與 Distributed Computing 的差別

## 為什麼需要平行程式設計

對於 Parallel Programming 有概念後，我們接下來說明為什麼需要這個技術呢！

- **縮短程式執行時間**

最直覺的原因就是可以縮短程式的執行時間。將原來的問題拆分成很多 Task。以 Concurrent 或是 Parallel Computing 理論上會比 Serial Computing 來得更快速 (需視問題性質而定)。更短的執行時間，也許能夠為公司帶來更多的收入。

- **應用程式的需要**

在 Big Data 的世代，每天產生的資料量已經遠超過過去數十年的累積。有些應用程式需要載入大量的資料，我們無法將這些資料都載入一台電腦的 Memory 中，透過 Distributed Computing，就可以將資料分散道不同的 Node 上。

- **硬體架構的改變**

在以前，電腦大多僅有一顆核心 (Single Core)。提升程式運算效能的方法就是提高 Core 的 Clock Rate。伴隨著物理上的限制，我們無法再大幅提升單個 Core 的 Clock Rate，因此開始朝著 Multi-Core 的方向前進。現今的電腦中，大多搭載 4 個或 8 個以上的 Core，如果程式是以非平行化、單線程的方式設計的，那麼將會使得許多硬體資源閒置，就浪費了這些硬體資源。因此，必須透過 Parallel Programming 的方式，使得每個 Core 都可以發會最大的效能。

## 結語

在本篇文章中，我們介紹了 Parallel Programming 的基本概念，與原來單線程程式設計的差別，以及為什麼需要用到 Parallel Programming。下一篇文章，我們將會透過一個簡單的例子，說明 Parallel Programming 的運作方式。
