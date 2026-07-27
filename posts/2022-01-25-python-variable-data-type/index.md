---
title: Python 中的變數與資料類型
date: '2022-01-25T21:45:21'
lastmod: '2022-06-18T02:19:30'
slug: python-variable-data-type
draft: false
categories:
- Python 基礎教學
tags:
- Python
description: '前言 & 概述 本篇為 Python 程式語言入門教學的第 3 篇文章。在前一篇文章中，我們透過 Python 程式碼實現生活中的數學運算。在這篇文章中，我們將會了解
  Python 中「變數」(Variable) 的概念以及資料類型 (Data Type)。 如果你喜歡透過影片學習： Python 中的資料類型 在前一篇文章中，我們了解到
  Expression 其實就是由 Value 與 Operator 所組成的，且可以被 Evaluate 成單一個 Value。所謂的「資料型態」(Data Type)
  指的就是 Value 所屬的類別。每一個 Value 都有自己的 Data Type。例如，上圖中「2」的 Data Type 即為 Integer。 Python
  中最基本的三種 Data Type 為：Integer、Floating-Point 與 String。以下分別介紹這三種 Data Type 的觀念。 Integer
  : 縮寫為「int」，指的是「整數」。如上圖中的 1, 2, […]'
aliases:
- /python-tutorial/python-variable-data-type/
original_url: http://54.150.87.240/python-tutorial/python-variable-data-type/
wp_id: 93
images:
- images/basic-data-type-in-python.jpg
- images/expression.jpg
- images/python-variable-1.jpg
- images/python-variable.jpg
- images/syntax-error-1.jpg
- images/type-error-1.jpg
- images/type-error.jpg
---

![python variable](images/python-variable.jpg)

Python 中 Variable 的觀念

## 前言 & 概述

本篇為 Python 程式語言入門教學的第 3 篇文章。在前一篇文章中，我們透過 [Python 程式碼實現生活中的數學運算](http://54.150.87.240/python-tutorial/python-expression/)。在這篇文章中，我們將會了解 Python 中「變數」(Variable) 的概念以及資料類型 (Data Type)。

如果你喜歡透過影片學習：

## Python 中的資料類型

![expression](images/expression.jpg)

Expression 就是由 Value 與 Operator 所組成

在前一篇文章中，我們了解到 Expression 其實就是由 Value 與 Operator 所組成的，且可以被 Evaluate 成單一個 Value。所謂的「資料型態」(Data Type) 指的就是 Value 所屬的類別。每一個 Value 都有自己的 Data Type。例如，上圖中「2」的 Data Type 即為 Integer。

![basic data type in python](images/basic-data-type-in-python.jpg)

Python 中最基本的資料類型

Python 中最基本的三種 Data Type 為：Integer、Floating-Point 與 String。以下分別介紹這三種 Data Type 的觀念。

- **Integer** : 縮寫為「int」，指的是「整數」。如上圖中的 1, 2, -4, 0, 12, 700 等等。
- **Floating-Point** : 縮寫為「float」，指的是帶有「小數點」的數字。如上圖中的 -12.5, 13.7, 77.89, 34.567 等等。
- **String** : 縮寫為「str」，指的是「字串」，由英文中的「單引號」或「雙引號」包覆起來。如上圖中的 ‘a’, ‘apple’, ‘bb’, ‘python’ 等等。

## 字串的基本運算

在前一篇文章中，我們透過 Python 程式碼實現生活中的數學運算，主要是針對 Integer 與 Floating-Point 的運算。在 Python 中，我們也可以對字串進行「加法」與「乘法」運算。

- **字串加法 (String Concatenation)**字串的加法就是將兩個字串相接在一起，在下方程式碼中，將字串 ‘app’ 與字串 ‘le’ 相加後，將會得到字串 ‘apple’。

```
'app' + 'le'
```

- **字串乘法 (String Replication)**  
  字串的乘法就是將同一個字串重複數次，在下方程式碼中，將字串 ‘apple’ 與整數 2 相乘後，將會得到字串 ‘appleapple’。

```
'apple' * 2
```

## Syntax Error 與 Type Error

![syntax error](images/syntax-error-1.jpg)

字串必須由成對的「引號」包起來，否則產生 Syntax Error

在前一篇文章中，我們透過 Expression 提到 Syntax Error 的意義。在 Python 中，字串 (String) 必須由「成對」的引號包覆起來，如果少了任一邊的引號，電腦就無法確定這個字串的範圍在哪裡，同樣也會產生 Syntax Error。

![type error](images/type-error.jpg)

String 與 Integer 相加將會導致 Type Error

此外，在進行字串的加法 (String Concatenation) 與乘法 (Replication) 時，必須確保 Data Type 的正確性，否則會產生 Type Error 的錯誤。如上圖所示，進行 String Concatenation 時，必須是兩個 String 的相加，如果其中一個不是 String 就會產生 Type Error。

![type error](images/type-error-1.jpg)

String 與 Float-Point Number 相乘也會導致 Type Error

同樣的，在進行 String Replication 時，必須是一個 String 乘以一個 Integer，如果將 Integer 改成 Floating-Point，當然也會產生 Type Error。

## Python 中的變數

「變數」的英文為 Variable，是程式中重要的角色。變數在程式中所扮演的角色像是一個「箱子」，我們可以將一個 Value 放到箱子中。在前面提到，Python 中 Value 的 Data Type 主要為 Integer、Floating-Point 與 String。因此，我麼可以將一個 String (‘apple’) 放入箱子中，也可以將一個 Integer (100) 放入箱子中，當然也可以將一個 Floating-Point (13.5) 放入箱子中。  
將一個 Value 放入箱子中，也就是將一個 Value 存在變數中的過程稱為「Assignment」。在程式中，Assignment 是透過「等號」來完成。

![python variable](images/python-variable-1.jpg)

Python 中的變數可以想成一個「箱子」，能夠存放一些值 [source: source: AUTOMATE THE BORING STUFF WITH PYTHON]

以上圖為例，我們將 Integer (42) 存入 spam 這一個變數中，在 Python 中的寫法為：

```
spam = 42
```

表示將 Integer (42) Assign 到 Variable (spam) 中。我們在 Colab 的 Cell 中執行變數的名稱，就會顯示「目前」這格變數中所存放的數值。

```
spam
```

我們再多新增一個變數：

```
num = 130
```

並將這兩個變數相加，即會顯示兩個變數中存放的數值相加後的結果。

```
spam + num
```

我們也可以將相加後的結果存放到原來的變數中：

```
spam = spam + num
```

如此一來，spam 變數原來存放的數值將會取代掉，變成新的數值。

```
spam
```

由上述的例子我們可以發現，當一個變數「第一次」被 Assign 一個 Value 時，該變數 (箱子) 就會被創造出來。在之後的程式中，我們可以不斷替換這個變數 (箱子) 中所存放的數值。

## 變數名稱

在前面的例子中，我們新增了兩個變數，名字分別為 ‘spam’ 與 ‘num’。在 Python 中，針對變數的名稱有三個限制條件：

1. **必須是一個 word 不能包含 space**  
   例如，’apple’、’abc’、’animal’ 都可以是變數名稱。 ‘app le’ 就不可以。
2. **word 中僅使用字母、數字與底線**  
   例如，’apple\_abc1′ 是可以接受的。 ‘apple!?’ 就不可以。
3. **不可以是數字開頭**  
   例如，’a3′ 是可以的。 ‘3a’ 是不可以接受的。

## 結語

在本篇文章中，我們學習了 Python 中 Value 的 Data Type 以及變數 (Variable) 的概念，也學會進行字串的運算 (Concatenation 與 Replication)。在下一篇文章中，我們將會學習[撰寫第一個完整的程式](http://54.150.87.240/python-tutorial/first-python-program/)，將可以接受使用者的輸入，並根據使用者的輸入進行運算後再顯示出來。
