# 平行程式設計模型：Distributed Memory Model

## 前言

在前一篇「平行程式設計模型：Shared Memory Model」中，我們介紹了平行程式設計的第一種模型，它對應到的通常是 Multi-Thread 程式：多條 Thread 共用同一塊記憶體，靠讀寫同一份資料來互相溝通。

本篇要談的是第二種模型 Distributed Memory Model。它走的是完全相反的路線，每個執行單元都有自己獨立的記憶體，誰也碰不到誰的資料，溝通只能靠明確地「寄訊息」。文章會從模型的基本概念講到 Message Passing Interface (MPI)，接著用一個兩個元素的加總範例，示範這個模型最容易踩到的雷 Deadlock，最後把兩種模型的優缺點擺在一起比較。

## 什麼是 Distributed Memory Model

在 Shared Memory Model 中，我們把一個 Program 視為主記憶體 (Main Memory) 中的一個 Process，程式的平行度來自這個 Process 底下的多條 Thread。Distributed Memory Model 則相反，它做出來的通常是「Multi-Process」程式：一個 Program 由許多 Process 組成，每個 Process 彼此獨立、各自擁有自己的記憶體，並且同時被不同的 Core/Processor 執行。

![Distributed Memory Model 的架構示意圖，多個 Process 各自擁有獨立的記憶體，分別在不同的 Processor 上執行。](img-001)
*Distributed Memory Model 示意圖*

如上圖所示，一個 Program 中包含 3 個 Process，分別在 3 個 Processor 上執行。在我們的電腦裡，作業系統 (OS) 本來就把每一個 Process 視為獨立的個體，彼此互不干預與影響，各自擁有自己的記憶體。也就是說，Process A 沒有辦法直接去存取 Process B 的資料，這是 OS 層級的保護，不是程式寫得不夠聰明。

那問題就來了：同一個 Program 裡的 Process，彼此到底要怎麼溝通？

## Message Passing Interface

在 Distributed Memory Model 中，不同的 Process 透過「訊息傳遞」(Message Passing) 溝通。Message Passing 就像現實生活中的寄信，由一個人「Send」一封信，另外一個人「Receive」這封信。在電腦上也是同一回事：由一個 Process 送出資料，由另外一個 Process 接收資料。

這裡跟 Shared Memory Model 有個關鍵差別。Shared Memory 的溝通是「Implicit」的，兩條 Thread 只是各自對同一塊記憶體 Load/Store，程式碼裡看不到「我在跟誰溝通」這件事；Distributed Memory 的溝通則是「Explicit」的，程式碼裡真的會出現 Send 與 Receive 兩個動作，資料流向白紙黑字寫在那裡。

實務上 Message Passing 的實作方式有很多種，但沒有人會想自己從 socket 開始刻。為了減輕開發者的負擔，通常會直接使用函式庫提供的 Message Passing Interface (MPI) 來實現 Process 之間的溝通。

![MPI 溝通示意圖，兩個 Process 透過 MPI 提供的 Send 與 Receive 介面交換資料。](img-002)
*透過 Message Passing Interface 實現 Process 之間的溝通 [source: Parallel Programming Course from NYCU]*

如上圖所示，有了 MPI，程式開發者不需要煩惱底層實際上是怎麼把資料從一個 Process 搬到另一個 Process 的，只需要明確寫出「哪一個 Process 送出什麼資料」以及「由哪一個 Process 接收」就好。

## Distributed Memory Model 範例

觀念講完了，接著用一個非常簡單的範例，看看這個模型實際寫起來會遇到什麼問題。

![範例的運算流程示意圖，Array 中的 A1 與 A2 各自經過 f Function 運算後加總得到 S。](img-003)
*Distributed Memory Model 範例*

如上圖所示，我們有一個 Array 包含兩個元素 A1 與 A2。目標是把這兩個元素分別經過 f Function 運算後再加總起來，得到結果 S。

假設電腦中剛好有 2 個 Processor，那就可以照 Distributed Memory Model 的概念寫出一個 Two-Process 程式：Processor 1 執行 Process 1 負責運算 A1，Processor 2 執行 Process 2 負責運算 A2。兩邊算完之後，各自把自己那一半的結果送給對方，這樣兩邊手上就都有完整的兩個值可以加總。

![兩個 Processor 各自運算後互相 send/receive 結果的虛擬碼，兩側都是先 send 再 receive。](img-004)
*兩個 Processor 分別處理各自的元素，並將結果寄給另外一個 Processor [source: Parallel Programming Course from NYCU]*

上圖是這個想法寫成虛擬碼的樣子。兩個 Processor 各自運算自己負責的元素，結果存在 xlocal，接著把 xlocal 寄 (send) 給另外一個 Processor，並接收 (receive) 對方寄來的值存進 xremote。

## Deadlock

上面那段虛擬碼看起來沒什麼問題，但它其實藏了一個很嚴重的 Bug，會讓程式直接卡死在 Deadlock。

Deadlock 是學作業系統時一定會碰到的觀念。說白了，Deadlock 就是有一組 Process 彼此互相等待對方手上的資源，結果誰也動不了。

拿生活中的例子來比喻：我和同學一起上美術課做自己的作品，做到一半，我發現我需要「他」手上的剪刀才能繼續，他發現他需要「我」手上的膠水才能繼續。如果我們兩個都堅持握著自己的資源不放，只等著對方先給，那最後兩個人都會停在原地。

如果你想更深入理解作業系統中的 Deadlock，可以參考[這篇文章](https://wangwilly.github.io/willywangkaa/2018/07/10/Operating-System-Deadlock/)。

![兩個 Processor 各自運算後互相 send/receive 結果的虛擬碼，兩側都是先 send 再 receive。](img-004)
*兩個 Processor 分別處理各自的元素，並將結果寄給另外一個 Processor [source: Parallel Programming Course from NYCU]*

回到上面那段虛擬碼。當 Processor 1 執行 **send xlocal, proc2** 時，它會把 xlocal 寄給 Processor 2，而且必須等到 Processor 2 真的執行 **receive xremote, proc1** 把訊息收走，Processor 1 才會往下繼續執行。

問題就出在兩邊的第一個動作都是 send。如果兩個 Processor 非常巧合地在同一個時間點各自執行 send（Processor 1 執行 **send xlocal, proc2**，Processor 2 執行 **send xlocal, proc1**），就會變成兩邊都停在 send 這一行等對方來接收，而對方也同樣卡在自己的 send 上，沒有人有機會走到 receive。程式就這樣停住了。

![調整順序後的虛擬碼，Processor 2 改成先 receive 再 send，與 Processor 1 錯開。](img-005)
*兩個 Processor 不要同時 Send 與 Receive 解決可能發生的 Deadlock [source: Parallel Programming Course from NYCU]*

解法其實很單純：只要確保兩個 Processor 不會同時傳送訊息就好。上圖把 Processor 2 的 send 與 receive 順序對調，變成 Processor 1 先 send、Processor 2 先 receive，兩邊的動作錯開，Deadlock 自然就不會發生。

## Shared Memory vs Message Passing

看到這裡，兩種模型的溝通方式已經很清楚了：Shared Memory Model 中不同的 Thread 透過「共用記憶體」互相溝通；Distributed Memory Model 中不同的 Process 則透過「Message Passing」互相溝通。那哪一種比較好？

**It depends！** 兩種方法沒有絕對的優劣，得看實際的問題與硬體環境而定。以下簡單整理兩種方法的優缺點：

- **Shared Memory 優點**
  - Implicit Communication：透過共用記憶體，兩條 Thread 不需要真的 Send/Receive 資訊，而是在共用記憶體中 Load/Store 資訊
  - Low Overhead when Cached：在有 Cache 的系統中，Processor 存取 Cache 中的資料遠遠快於主記憶體
- **Shared Memory 缺點**
  - Require Synchronization Operation：需要大量的同步機制，確保這條 Thread Load Data 之前，另外一條 Thread 已經把最新的 Data Store 進去
  - Hard to Control Data Placement in Caching System：正是所謂的「成也 Cache，敗也 Cache」。有了 Cache 能加速資料的讀取速度，但也帶來另一個問題 False Sharing。False Sharing 不會讓程式算出錯誤的結果，卻會大幅拉低效能，把平行化帶來的好處整個吃掉
- **Message Passing 優點**
  - Explicit Communication：有時候用 Explicit 的方式 (Send/Receive) 溝通，資料流向一目瞭然，反而更能避免程式出錯
  - Easy to Control Data Placement in Caching System
- **Message Passing 缺點**
  - High Overhead：相較於共用記憶體，Process 之間 Send/Receive 資料的時間成本更高
  - Complex to Program

## 結論

本篇介紹了第二種平行程式設計模型 Distributed Memory Model：Process 之間各自獨立、記憶體互不共用，只能靠 Message Passing 明確地 Send/Receive 來交換資料，而實務上通常交給 MPI 這類函式庫處理。也透過一個兩元素加總的範例，看到只要 send 與 receive 的順序沒有錯開，程式就可能直接卡在 Deadlock。

最後把兩種模型擺在一起比較，可以發現它們的優缺點幾乎是互補的：Shared Memory 溝通成本低但同步麻煩、Cache 行為難掌控；Message Passing 寫起來繁瑣、溝通成本高，但資料流向清楚也好控制。實際選哪一個，還是得回到手上的問題來判斷。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Distributed Memory Model 示意圖",
    "why_used": "支撐說明 Distributed Memory Model 基本架構的段落，讓讀者看到多個 Process 各自擁有獨立記憶體、由不同 Processor 執行的樣子。",
    "agent_match_hint": "一張架構示意圖，並排數個 Process 方塊，每個方塊底下各接一塊獨立的 Memory 與 Processor。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "透過 Message Passing Interface 實現 Process 之間的溝通 [source: Parallel Programming Course from NYCU]",
    "why_used": "說明 Process 之間如何透過 MPI 提供的 Send/Receive 介面溝通，開發者不需處理底層傳輸細節。",
    "agent_match_hint": "一張溝通示意圖，兩個 Process 之間以箭頭標示 send 與 receive 的訊息傳遞方向，中間標註 MPI。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Distributed Memory Model 範例",
    "why_used": "介紹範例題目：Array 中的 A1 與 A2 各自經過 f Function 運算後加總為 S，作為後續拆成兩個 Process 的基礎。",
    "agent_match_hint": "一張運算流程圖，兩個 Array 元素 A1、A2 各自經過 f 運算後匯流相加成 S。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "兩個 Processor 分別處理各自的元素，並將結果寄給另外一個 Processor [source: Parallel Programming Course from NYCU]",
    "why_used": "呈現兩個 Processor 的虛擬碼，先用來說明範例的平行化寫法，之後再回頭用同一張圖指出兩邊都先 send 所造成的 Deadlock。",
    "agent_match_hint": "左右兩欄的虛擬碼對照，兩側都是先 send xlocal 再 receive xremote。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "兩個 Processor 不要同時 Send 與 Receive 解決可能發生的 Deadlock [source: Parallel Programming Course from NYCU]",
    "why_used": "呈現修正後的虛擬碼，說明把 Processor 2 的 send 與 receive 順序對調即可避免 Deadlock。",
    "agent_match_hint": "左右兩欄的虛擬碼對照，Processor 1 先 send 後 receive，Processor 2 改為先 receive 後 send。"
  }
]
```
