---
title: Python 中的 Boolean Operator
date: '2022-01-26T03:55:50'
lastmod: '2022-06-18T02:20:50'
slug: python-boolean-operator
draft: false
categories:
- Python 基礎教學
tags:
- Python
description: 前言 & 概述 本篇為 Python 程式語言入門教學的第 5 篇文章！在前一篇文章中，我們成功撰寫了第一個 Python 程式，一個能夠與使用者互動的
  Python 程式。然而，目前的互動性仍然有些不足，我們希望程式可以根據使用者不同的輸入，進行不一樣的處理，變得更有彈性。 如果你喜歡透過影片學習： 程式中的流程控制
  (Control Flow) 實際上，「讓程式根據不同的狀況 (輸入)，採取不同的行為」就是一種「流程控制」的概念。相信你一定對流程控制的概念不陌生！我們以下圖這張流程圖為例：
    我們從「Start」出發，首先遇到了「Is raining?」的判斷，如果是「Yes」則前往「Have umbrella?」、如果是「No」則前往「Go outside.」。「Have
  umbrella?」也是同樣的道理。如果是「Yes」會前往「Go outside」、如果是「No」則會前往「Wait a while.」。 由此我們可以發現，因為在流程圖中多了「Is
  raining?」、「Have umbrella?」這些判斷的時刻，使得我們從「Start」走到「End」可以有多種不同的選擇。 為了撰寫出更具有互動性的程式，我們可以將「流程控制」的觀念寫入程式中，讓程式能夠因應不同的狀況，採取不同的行爲。
  布林資料類型 在學習撰寫 Python 中控制流程的語法 (Control Flow Statement) 之前，我們必須先瞭解如何在程式中表示流程圖中的「Yes」與「No」。
  在流程圖中出現「Is raining?」(現在下雨嗎？) 只會有兩種結果，不是「Yes」就是「No」。 在一般常見的程式語言中，有一種資料類型稱為「布林」(Boolean)，Boolean
  資料類型的數值只有兩種「True」與「False」。「True」就是代表「Yes」、「False」就是代表「No」。 到目前為止，我們已經接觸了 4 種資料類型，分別是：整數
  (Integer)、浮點數 (Floating-Point)、字串 (String) 與布林 (Boolean)。 在 Python 中，建立一個 […]
aliases:
- /python-tutorial/python-boolean-operator/
original_url: http://54.150.87.240/python-tutorial/python-boolean-operator/
wp_id: 151
images:
- images/compare-operator-in-programming.jpg
- images/expression-1.jpg
- images/feature-image-2.jpg
- images/flow-control-chart.jpg
- images/truth-table-for-and-operator.jpg
- images/truth-table-for-not-operator.jpg
- images/truth-table-for-or-operator.jpg
---

![feature image](images/feature-image-2.jpg)

source: Pixabay

## 前言 & 概述

本篇為 Python 程式語言入門教學的第 5 篇文章！在前一篇文章中，我們成功撰寫了[第一個 Python 程式](http://54.150.87.240/python-tutorial/first-python-program/)，一個能夠與使用者互動的 Python 程式。然而，目前的互動性仍然有些不足，我們希望程式可以根據使用者不同的輸入，進行不一樣的處理，變得更有彈性。

如果你喜歡透過影片學習：

## 程式中的流程控制 (Control Flow)

實際上，「讓程式根據不同的狀況 (輸入)，採取不同的行為」就是一種「流程控制」的概念。相信你一定對流程控制的概念不陌生！我們以下圖這張流程圖為例：

![flow control chart](images/flow-control-chart.jpg)

流程圖 [source: Automate the Boring Stuff with Python]

我們從「Start」出發，首先遇到了「Is raining?」的判斷，如果是「Yes」則前往「Have umbrella?」、如果是「No」則前往「Go outside.」。「Have umbrella?」也是同樣的道理。如果是「Yes」會前往「Go outside」、如果是「No」則會前往「Wait a while.」。

由此我們可以發現，因為在流程圖中多了「Is raining?」、「Have umbrella?」這些判斷的時刻，使得我們從「Start」走到「End」可以有多種不同的選擇。

為了撰寫出更具有互動性的程式，我們可以將「流程控制」的觀念寫入程式中，讓程式能夠因應不同的狀況，採取不同的行爲。

## 布林資料類型

在學習撰寫 Python 中控制流程的語法 (Control Flow Statement) 之前，我們必須先瞭解如何在程式中表示流程圖中的「Yes」與「No」。

在流程圖中出現「Is raining?」(現在下雨嗎？) 只會有兩種結果，不是「Yes」就是「No」。

在一般常見的程式語言中，有一種資料類型稱為「布林」(Boolean)，Boolean 資料類型的數值只有兩種「True」與「False」。「True」就是代表「Yes」、「False」就是代表「No」。

到目前為止，我們已經接觸了 4 種資料類型，分別是：整數 (Integer)、浮點數 (Floating-Point)、字串 (String) 與布林 (Boolean)。

在 Python 中，建立一個 Boolean 變數也相當簡單，只需要設定這個變數的數值是 True 或是 False。

```
x = True
y = False
```

## 「比較」運算子

接著，我們要理解的是程式中的「比較」運算子 (Comparison Operator)。相信你也對這個東西不陌生！生活中常見的 Comparison Operator 有：「等於」、「不等於」、「大於」、「小於」、「大於或等於」與「小於或等於」。

在 Python 程式中的對照寫法如下圖所示：

![compare operator in programming](images/compare-operator-in-programming.jpg)

程式中常見的比較運算子

比較運算子會接受兩個數值，並回傳一個結果，這個結果不是「True」就是「False」。因此，比較運算子所回傳的結果就是一個 Boolean。 我們可以在 Colab 中撰寫以下程式碼並執行。

```
1 == 2

10 <= 20

20-1 != 19

'apple' == 'apple'
```

可以發現執行的結果不是「True」就是「False」。

## 「==」vs 「=」

在上面的「比較運算子」中，我們看到了比較兩個數值是否相同是使用「兩個等號」( == )。千萬不能將「==」與「=」兩種搞混在一起！

- ＝＝：是用來詢問兩個數值是否相同
- ＝：是用來將右邊的數值 (Value) 寫入 (Assign) 到左邊的變數 (Variable)

我們可以用簡單的方式來記憶，「詢問兩個數值是否相同」與「詢問兩個數值是否不相同」都是使用兩個符號，分別是「＝＝」與「！＝」。

## 布林運算子

了解完「比較運算子」後，我們接著學習「布林運算子」。實際上，我們可以將「運算子」想成可以對這種資料類型進行的操作。例如：「整數」與「浮點數」的運算子叫包含了「+」、「-」、「\*」、「/」、「%」、「//」。

布林運算子則包含了 3 種：「and」、「or」與「not」。布林運算子與比較運算子一樣，都會接受兩個布林數值，再回傳一個布林數值。我們接著了解這 3 種運算子的意義。

- **and** : 如果兩個布林數值都是 True，則回傳 True；若存在一個 False，則回傳 False。我們可以執行以下 Python 程式碼，了解 and 的意義。

```
True and True

True and False

False and False
```

下圖為「and」的 Truth Table，Truth Table 中列出「and」的所有組合：

![truth table for and operator](images/truth-table-for-and-operator.jpg)

“and” operator 的真值表 (Truth Table) [source: Automate the Boring Stuff with Python]

- **or** : 如果其中一個布林數值為是 True，則回傳 True；若兩個都是 False，則回傳 False。我們可以執行以下 Python 程式碼，了解 or 的意義。

```
True or True

True or False

False or False
```

下圖為 or 的 Truth Table，列出 or 的所有情況：

![truth table for or operator](images/truth-table-for-or-operator.jpg)

“or” operator 的真值表 (Truth Table) [source: Automate the Boring Stuff with Python]

- **not** : 與 and 和 or 不同的是，not 只會接受「一個」布林數值，並回傳這個布林數值的「相反」。舉例來說，試著執行以下 Python 程式碼：

```
not True

not False
```

下圖為 not 的 Truth Table，列出 not 的所有情況：

![truth table for not operator](images/truth-table-for-not-operator.jpg)

“not” operator 的真值表 (Truth Table) [source: Automate the Boring Stuff with Python]

## 「比較運算子」與「布林運算子」混合使用

在程式中執行「比較運算子」得到的結果會是布林，因此我們可以透過「布林運算子」將多個「比較運算子」結合在一起，最終只會得到一個布林數值。

舉例來說，執行以下 Python 程式碼：

```
(2 ==3) and (5 == 6)

(2 < 3) or (5 > 6)

(2 != 3) or (5 <= 6)

not ((2 != 3) or (10 <= 6))
```

我們以最後一個例子來說明。如下圖所示，首先成會先執行 (2 != 3) 得到 True，再執行 (10 <= 6) 得到 False。再將兩者 or 在一起得到 True。最後再進行最外層的 not 得到 False。

![expression](images/expression-1.jpg)

Boolean Expression 的計算過程

## 結語

在本篇文章中，我們學習了程式語言中布林 (Boolean) 資料類型，以及相關的運算子 (Operator)。布林是流程控制 (Control Flow) 中基本的元素，在下一篇文章中將會介紹如何在 [Python 中撰寫流程控制的語法 (Control Flow Statement)](http://54.150.87.240/python-tutorial/python-if-elif-else/)。
