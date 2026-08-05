---
title: Google Colaboratory 介紹
date: '2022-01-25T21:02:11'
lastmod: '2022-06-18T02:16:57'
slug: google-colaboratory
draft: false
categories:
- Python 基礎教學
tags:
- Colab
- Python
description: "前言 & 概述 本篇為 Python 程式語言入門教學的第一篇文章。今天的文章中，將會介紹 Google Colaboratory (Colab)\
  \ 是什麼，如何透過 Colab 學習 Python 程式語言。本文將會以 6 個問題切入了解 Colab。開始學習 Python 程式語言之前，讓我們先好好了解\
  \ Colab 吧！ 如果你喜歡透過影片學習： 問題 1 : Google Colab 是什麼 Google Colaboratory 又稱為 Colab 是\
  \ Google 提供服務，讓任何人都可以透過瀏覽器撰寫以及執行 Python 程式碼。程式初學者透過 Colab 學習 Python 語言，可以省去架設環境的困擾。Colab\
  \ 是基於 Jupyter Notebook 的開發環境且許多常用的套件都已經先安裝好了，因此非常適合作為資料科學\b開發環境。Colab 也提供免費的運算資源\
  \ (GPU)，讓我們可以加速機器學習模型的訓練。 問題 2 : Google Colab 有什麼限制嗎 當然！因為 Colab […]"
aliases:
- /python-tutorial/google-colaboratory/
original_url: http://54.150.87.240/python-tutorial/google-colaboratory/
wp_id: 81
images:
- images/feature-image-1.jpg
- images/google-colab-1.jpg
- images/google-colab-cell.jpg
- images/google-colab.jpg
- images/google-drive.jpg
---

![feature image](images/feature-image-1.jpg)

source: Pixabay

## 前言 & 概述

本篇為 Python 程式語言入門教學的第一篇文章。今天的文章中，將會介紹 Google Colaboratory (Colab) 是什麼，如何透過 Colab 學習 Python 程式語言。本文將會以 6 個問題切入了解 Colab。開始學習 Python 程式語言之前，讓我們先好好了解 Colab 吧！

如果你喜歡透過影片學習：

## 問題 1 : Google Colab 是什麼

Google Colaboratory 又稱為 Colab 是 Google 提供服務，讓任何人都可以透過瀏覽器撰寫以及執行 Python 程式碼。程式初學者透過 Colab 學習 Python 語言，可以省去架設環境的困擾。Colab 是基於 [Jupyter Notebook](https://jupyter.org/) 的開發環境且許多常用的套件都已經先安裝好了，因此非常適合作為資料科學開發環境。Colab 也提供免費的運算資源 (GPU)，讓我們可以加速機器學習模型的訓練。

## 問題 2 : Google Colab 有什麼限制嗎

當然！因為 Colab 是免費的服務，所以在資源的供應上是有限制的。首先，Colab 提供的免費硬體設備 (CPU 與 GPU) 當然不是最好的，因此在程式的運行效能上，可能比不上你手上的電腦，但是對於資料科學領域的初學者而言已經是相當夠用的！此外，Colab 提供的記憶體 (RAM) 當然也是有限的，如果模型的參數太多或是資料集太大，就會出現記憶體不足的錯誤發生。

## 問題 3 : 如何開啟 Google Colab

對於 Colab 有基本的了解後，我們可以開始使用 Colab 囉！  
首先，**進入到自己的 Google Drive 頁面**：  
接著，**在畫面中點選「右鍵」後，選擇「更多」，再點擊「Google Colaboratory」**。

![google drive](images/google-drive.jpg)

Google Drive 的資料夾頁面

點擊後，就會進入到 **Colab 頁面**囉！

![google colab](images/google-colab.jpg)

Google Colab 頁面

## 問題 4 : 如何執行 Python 程式碼

Colab 中每一個「格子」都是一個 Cell，我們可以在 Cell 中輸入程式碼，並按下 Shift+Enter，就可以執行程式碼，並新增一個新的 Cell。如果是剛開啟 Colab 環境，則必須先等待資源分配完成後，才能執行程式碼！

![google colab cell](images/google-colab-cell.jpg)

Google Colab 中的 Cell

## 問題 5 : Colab 中要認識的基本介面有哪些

接下來，讓我們來認識 Colab 中基本的介面與功能！

![google colab](images/google-colab-1.jpg)

介紹 Google Colab 中的基本元件

1. **檔案名稱**：在此區塊我們可以命名這個 Colab 檔案。Colab 因為是基於 Jupyter 所以也是一個 Notebook 的形式，因此副檔名為 .ipynb。（如果是一般的 Python 檔，副檔名會是 .py）
2. **工具列**：工具列區塊中有非常多功能可以使用，常用的有：檔案、編輯、插入與執行階段。
   - 檔案：在此下拉選單中，我們可以透過「在雲端硬碟中尋找」找尋此 Colab 在雲端硬碟中的位置，或是透過「上傳筆記本」從雲端硬碟、電腦或是 GitHub 中上傳筆記本到 Colab 中。最後，我們也可以透過「下載」將此 Colab 下載為 .py 檔或是 .ipynb 形式。
   - 編輯：在此下拉選單中，我們可以「復原刪除的儲存格」、「刪除所選的儲存格」或是透過「筆記本設定」選擇硬體加速器。預設情況不使用硬體加速器，如果在訓練模型時可以選擇 GPU 加速模型的訓練。
   - 插入：在此下拉選單中，我們可以插入「程式碼儲存格」或是「文字儲存格」。
   - 執行階段：在此下拉選單中，我們可以決定要執行哪些儲存格，或是透過「重新啟動執行階段」將我們的 Colab 環境重新啟動 (Colab 有時會當掉)，或是「變更執行階段類型」來選擇是否使用硬體加速器。最後，也可以透過「管理工作階段」查看目前正在執行的 Colab 檔案。
3. **儲存格 (Cell)**：Colab 就像是一個 Notebook 一樣，由一個又一個的「儲存格」所組成。儲存格可以是「程式碼」或是「文字」。若是程式碼儲存格，怎可以輸入 Python 程式碼；文字儲存格則必須透過 Markdown 語法來撰寫。
4. **留言與共用**：Colab 的一大特色就是可以分享你的 Notebook 給其他人，讓其他人也能夠在同一份 Colab 上編輯。
5. **連線狀態**：Colab 背後使用的是 Google 提供的運算資源，因此要正常使用 Colab 必須確保已經正常連線到遠端的硬體資源。此外，也能夠顯示目前 RAM 與硬碟的用量。
6. **側邊工具欄**：側邊工具欄為 Colab 上較為進階的功能，由上而下依序為：目錄、文字尋找與取代、程式碼片段與檔案。
   - 目錄：顯示目前 Colab 中所有 Cell 的架構。我們理解 Colab 是由很多個 Cell 所組成，Cell 底下又可以包含很多 Cell。因此，透過目錄可以清楚觀察 Cell 之間的階層關係。
   - 文字尋找與取代：單純的文字尋找與取代。
   - 程式碼片段：我們可以在此搜尋一些常用的程式碼片段，直接複製到 Colab 中使用。例如：如果要從 Colab 中使用 Google Drive 的檔案，就可以在此搜尋「Google Mount」找到如何將 Google Drive 引入 Colab 環境中。
   - 檔案：Colab 的環境就像是在一台虛擬電腦上，在此區塊中可以看到 Colab 目前所在的根目錄。

## 問題 6 : Colab 中基本的快捷鍵有哪些呢

在 Colab 中有非常多的快捷鍵可以使用，我們也可以在「上方工具列」>「工具」>「鍵盤快速鍵」中，針對每一個功能設定快捷鍵。然而，對於程式初學者而言，我們不需要知道這麼多，僅需熟悉最常用的幾個快捷鍵，來加速程式的開發。  
首先，最基本兩種操作是將 Cell 進行轉換。Colab 中的 Cell 有兩種模式：Code 與 Markdown。在 Code 模式中，我們可以在 Cell 中撰寫 Python 程式碼；在 Markdown 模式中，我們則是在 Cell 中撰寫 Markdown 語法，形成註解或是說明。如果對於 Markdown 語法不了解的話，可以參考[此篇文章](https://wcc723.github.io/development/2019/11/23/ten-mins-learn-markdown/)，或是不管什麼 Markdown 語法，直接打上你想留下的說明文字就可以囉！

- 將 Cell 轉成 Code 區塊：⌘/Ctrl + m + y
- 將 Cell 轉成 Markdown 區塊：⌘/Ctrl + m + m

有時，我們也需要將整個 Cell 刪除或是復原，可以透過以下快捷鍵：

- 將 Cell 刪除：⌘/Ctrl + m + d
- 將 Cell 復原：⌘/Ctrl + m + z

當我們在 Cell 中寫好 Python 程式碼後，我們可能想要執行，可以透過兩種方式：

- 執行此 Cell：⌘/Ctrl + enter
- 執行此 Cell 再下向新增一個 Cell：Shift + enter

想要將目前的焦點移動到別的 Cell 上，但是卻懶得用滑鼠點擊：

- 聚焦上一個 Cell：⌘/Ctrl + p
- 聚焦下一個 Cell：⌘/Ctrl + n

當程式碼愈來愈多，要找某一個變數變的愈來愈困難，這時就可以透過「側邊工具欄」中的「文字尋找與取代」功能：

- 尋找某一段文字：⌘/Ctrl + h

最後也是最重要的，在 Colab 中編輯時，不忘「手動」儲存一下吧！(Colab 基本上會自動儲存新的變更)

- 儲存 Colab：⌘/Ctrl + s

## 結語

在本篇文章中，我們認識了 Colab 環境的基本觀念，對於如何使用 Colab 也有了概念。當然，我們不需要將上面的資訊通通記在腦袋中，需要使用卻忘記時，就回來看看吧！Colab 仍有許多進階的操作，我們將會在其他文章中另外介紹！在下一篇文章中，我們將開始學習 [Python 語法](http://54.150.87.240/python-tutorial/python-expression/)！
