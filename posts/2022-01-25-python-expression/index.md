---
title: Python 中的加減乘除
date: '2022-01-25T21:21:45'
lastmod: '2022-06-18T02:18:12'
slug: python-expression
draft: false
categories:
- Python 基礎教學
tags:
- Python
description: '前言 & 概述 本篇為 Python 程式語言入門教學的第二篇文章。今天的文章中，將會開始撰寫 Python 程式碼！我們學習將生活中簡單的「加減乘除」以
  Python 程式碼實作出來。 如果你喜歡透過影片學習： 開啟並命名 Colab 在前一篇文章中，我們介紹了 Colab 這款好用的線上編輯器。在開始撰寫 Python
  程式碼前，當然要先在我們雲端硬碟中新增一個 Colab 檔案，並給他一個特別的名稱！ 基本的加減乘除運算 首先，讓我們來寫一個簡單的程式 : 計算 123 +
  456 等於多少？相信聰明的你，透過計算機一下就找出正確答案。以 Python 程式碼來說，我們可以這樣撰寫： 123 + 456 在 Colab 的儲存格 (Cell)
  中執行這行程式碼後，我們就可以得到想要的答案。同理，如果我們希望計算 : 907 – 456 等於多少？你一定可以馬上寫出程式： 907 – 456 再來一些簡單的範例！我們希望計算
  1445 x 404 與 1309 ÷ 56 的答案： 1445 * […]'
aliases:
- /python-tutorial/python-expression/
original_url: http://54.150.87.240/python-tutorial/python-expression/
wp_id: 88
images:
- images/expression.jpg
- images/feature-image.jpg
- images/syntax-error.jpg
---

![](images/feature-image.jpg)

source: Pixabay

## 前言 & 概述

本篇為 [Python 程式語言入門教學](http://54.150.87.240/topics/python-tutorial/)的第二篇文章。今天的文章中，將會開始撰寫 Python 程式碼！我們學習將生活中簡單的「加減乘除」以 Python 程式碼實作出來。

如果你喜歡透過影片學習：

## 開啟並命名 Colab

在前一篇文章中，我們介紹了 [Colab](http://54.150.87.240/python-tutorial/google-colaboratory/) 這款好用的線上編輯器。在開始撰寫 Python 程式碼前，當然要先在我們雲端硬碟中新增一個 Colab 檔案，並給他一個特別的名稱！

## 基本的加減乘除運算

首先，讓我們來寫一個簡單的程式 : 計算 123 + 456 等於多少？相信聰明的你，透過計算機一下就找出正確答案。以 Python 程式碼來說，我們可以這樣撰寫：

```
123 + 456
```

在 Colab 的儲存格 (Cell) 中執行這行程式碼後，我們就可以得到想要的答案。同理，如果我們希望計算 : 907 – 456 等於多少？你一定可以馬上寫出程式：

```
907 - 456
```

再來一些簡單的範例！我們希望計算 1445 x 404 與 1309 ÷ 56 的答案：

```
1445 * 404
1309 / 56
```

如果上面的問題你都學會了話，那你已經了解如何寫 Python 程式碼進行四則運算囉！

## 了解 Expression 的概念

接著，讓我們來了解 Expression 的概念！實際上，我們剛剛所撰寫的 Python 程式碼，就是 Expression (表達式)。

![expression](images/expression.jpg)

Expression 的概念

由上圖可以發現，Expression 由兩種東西組成：Value (數值) 與 Operator (運算子)。以更白話的方式理解，Expression 就是數學的「算式」，裡面包含了很多「數值」以及「運算符號」。  
Expression 的特色在於能夠被 Evaluate (運算)，可以從一個很長的「式子」運算成一個「數值」。例如 : 2 + 2 + 2 + 2 + 2 + 2 是一個 Expression 可以被 Evaluate 為 12。  
因此我們可以理解，在上面的程式碼中，我們撰寫一行 Expression 後，並執行這行程式碼，由電腦進行 Evaluate。

```
123 + 456
```

需要特別注意的是，電腦在 Evaluate 的過程中，會遵守「先乘除後加減」以及「括號內的東西先算」這樣的原則，因此我們在撰寫 Expression 時也必須留意，否則會得到非預期的答案。

## 更進階的 Operator : \*\* 、% 與 //

在 Python 中，除了基本的加減乘除外，還有三個比較進階的 Operator。首先是「\*\*」表示「次方」。例如，執行以下程式碼，計算「2 的 3 次方」：  
2 \*\* 3

「%」則是表示「取餘數」。例如，15 ÷ 4 = 3 (商數 3) … 3 (餘數 3)。如果們希望在程式中計算 15 除以 4 的餘數，就可以透過「%」。

```
15 % 4
```

最後，「//」表示「取商數」。例如，15 ÷ 4 = 3 (商數 3) … 3 (餘數 3)。如果們希望在程式中計算 15 除以 4 的商數，就可以透過「//」。

```
15 // 4
```

## Syntax Error !!!

![syntax error](images/syntax-error.jpg)

程式初學者常見的錯誤：Syntax Error

「Syntax Error」是在寫程式時經常會看到的錯誤訊息。「Syntax Error」表示「語法錯誤」，也就是電腦告訴我們：你寫的 Code 語法有問題啦！以上圖而言，我們原本希望計算：

```
1 + 3 * 4
```

然而，卻漏打了 3 變成：

```
1 + * 4
```

加號的後方直接遇到乘號，當然沒有辦法運算！因此電腦就顯示了 Syntax Error 的錯誤訊息。

在撰寫 Code 時，我們經常會在數字與符號之間加入「空白」，這裡的空白並不會造成語法錯誤，只是為了讓程式碼看起來更整齊、簡潔！

## 結語

在本篇文章中，我們學習了 Python 最基礎的語法以及 Expression 的概念。並以 Python 程式碼實作各種不同的數學運算。在下一篇文章中，將會介紹程式中[「變數」的概念](http://54.150.87.240/python-tutorial/python-variable-data-type/)！
