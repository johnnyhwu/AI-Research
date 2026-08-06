# 什麼是平行程式設計？

## 前言

本篇文章會說明什麼是「平行程式設計」(Parallel Programming)，它跟我們一直以來熟悉的 (非平行) 程式設計模式差在哪，以及為什麼今天的軟體工程師需要用到這個技術。內容從最基本的單線程程式開始談起，不需要任何平行運算的背景知識。

## 單線程程式設計

要理解平行程式設計，得先回頭看看原本的 (非平行) 程式是怎麼跑的。

我們從小到大在寫程式時，通常是以「單線程」(**Single-Thread**) 的角度在思考的。也就是說，寫 Code 的時候，我們預期處理器會「由上而下」、「一行一行」執行我們寫的東西，這就是 **Serial Computing** 的概念。

更具體一點：在電腦還處於單核心的遠古時期，軟體工程師寫程式時，會把「問題」分解成一系列的「指令」，並預期這些指令會被處理器 one-by-one 地執行完。

![一個程式被拆解成一連串依序排列的指令，交由單一處理器由上而下逐一執行的示意圖。](img-001)
*一個程式被拆解為一連串的指令被處理器執行*

問題來了。現今隨便一台電腦上都有 4 個或 8 個以上的 core，但只要我們還是用「單線程」的角度在寫程式，那麼在「同一時間」永遠只有 1 個 core 在幫我們做事，其餘 core 的運算資源就這樣被閒置、白白浪費掉了。

## 平行化程式設計

平行程式設計 (Parallel Programming) 就是在寫 Code 的階段加入一些特別的技術，讓程式可以在「同一時間」被多個 core 一起執行。做平行程式設計時，軟體工程師通常會把問題拆分成「多組」一系列的「指令」，再把每一組指令交付給一個 core 去跑。

![一個程式被拆成多組指令，分別交給多個處理器在同一時間平行執行的示意圖。](img-002)
*Parallel Programming 即是一個程式同時由多個處理器執行*

這裡有個很現實的前提：把不同組的指令丟給不同 core 執行之前，必須先確保這些組別之間不具有「相依性」。也就是說，不能出現「一定要先跑完某一組才能跑另外一組」的情況。舉例來說，把一個 100 萬筆資料的陣列切成 4 段分別加總，各段之間互不影響，就很適合平行化；但如果是計算費氏數列，每一項都得等前一項算完，那再多 core 也幫不上忙。

## 「同一時間」執行的概念

前面提到 Parallel Programming 可以讓程式在「同一時間」被許多 core 執行。不過在資訊工程裡，「同一時間」這件事其實還分成好幾種，值得分清楚。

- **Concurrent Computing**

指的是一個 Program 被拆成很多小的 Task，每一個 Task 都處於「處理中」的狀態，但這些 Task 並不是真的「同時」在被執行，而是以「穿插」(Interleave) 的方式輪流執行。舉例來說，Task A 與 Task B 都在進行中，然而 core 是執行完 Task A 的某一部份後，切換去執行 Task B。

- **Parallel Computing**

指的是一個 Program 被拆成很多小的 Task，每一個 Task 都處於「處理中」的狀態，而且這些 Task 理論上是「同時」正在被執行。跟 Concurrent 的差別就在這裡：前者是快速輪流，後者是真的一起跑。

- **Distributed Computing**

上述兩種 Computing 都是在「一台電腦」上發生的事。Distributed Computing 則是「多台電腦」的分散運算。以下圖為例，在 Parallel Computing 中，通常是「一台電腦」裡有多個 Processor，這些 Processor 共用 Memory 來溝通；在 Distributed Computing 中，則是有「多台電腦」(每一台電腦可以視為一個 node)，每一個 node 都有自己的 Processor 與 Memory，不同 node 之間透過 Network 溝通。

![左側為單一電腦中多個處理器共用記憶體的平行運算架構，右側為多台電腦各自擁有處理器與記憶體、透過網路連接的分散式運算架構對照圖。](img-003)
*Parallel Computing 與 Distributed Computing 的差別*

## 為什麼需要平行程式設計

對 Parallel Programming 有概念之後，接著談談為什麼會需要這個技術。

- **縮短程式執行時間**

最直覺的原因就是可以縮短程式的執行時間。把原來的問題拆分成很多 Task，以 Concurrent 或 Parallel Computing 的方式處理，理論上會比 Serial Computing 來得快 (實際能快多少，還是要看問題本身的性質)。對商業服務來說，更短的執行時間也可能直接反映在收入上。

- **應用程式的需要**

在 Big Data 的世代，每天產生的資料量已經遠超過過去數十年的累積。有些應用程式需要載入大量資料，多到根本塞不進一台電腦的 Memory 裡。透過 Distributed Computing，就可以把資料分散到不同的 node 上處理。

- **硬體架構的改變**

以前的電腦大多只有一顆核心 (Single Core)，提升效能的方法就是拉高 Core 的 Clock Rate。但受限於物理上的限制 (發熱與功耗)，單顆 Core 的 Clock Rate 已經無法再大幅提升，於是業界轉向 Multi-Core 的方向發展。現今的電腦大多搭載 4 個或 8 個以上的 Core，程式如果還是以非平行化、單線程的方式設計，就等同於讓大部分硬體資源閒置在那邊。要讓每個 Core 都發揮最大效能，Parallel Programming 是繞不開的一步。

## 結論

本篇文章介紹了 Parallel Programming 的基本概念、它與單線程程式設計的差別，也釐清了 Concurrent、Parallel、Distributed 這三種「同一時間」執行的定義，最後說明了為什麼需要用到 Parallel Programming。下一篇文章，我們會用一個簡單的例子，實際說明 Parallel Programming 的運作方式。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "一個程式被拆解為一連串的指令被處理器執行",
    "why_used": "說明單線程 (Serial Computing) 的執行模型：程式被拆成一連串指令，由單一處理器依序執行。",
    "agent_match_hint": "一張流程示意圖，程式方塊分解為依序排列的多個指令，全部指向同一個處理器。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Parallel Programming 即是一個程式同時由多個處理器執行",
    "why_used": "支撐說明平行程式設計把問題拆成多組指令、分別交給不同 core 同時執行的段落。",
    "agent_match_hint": "一張流程示意圖，程式方塊分解為多條並排的指令序列，分別指向多個處理器。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Parallel Computing 與 Distributed Computing 的差別",
    "why_used": "對照單機多處理器共用記憶體與多台電腦透過網路溝通兩種架構，支撐 Distributed Computing 的說明段落。",
    "agent_match_hint": "一張左右對照圖，一側是單機內多個 Processor 共用一塊 Memory，另一側是多個 node 各有 Processor 與 Memory 並以網路連線。"
  }
]
```
