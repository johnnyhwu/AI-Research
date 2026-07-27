---
title: Python 中的 IF, ELIF, ELSE
date: '2022-01-26T04:22:13'
lastmod: '2022-06-18T02:21:29'
slug: python-if-elif-else
draft: false
categories:
- Python 基礎教學
tags:
- Python
description: 前言 & 概述 本篇為 Python 程式語言入門教學的第 6 篇文章！在前一篇文章中，我們介紹了流程控制以及布林 (Boolean) 資料類型。本篇文章則是基於這兩項觀念，學習實際在
  Python 中撰寫流程控制的語法。 如果你喜歡透過影片學習： 流程控制的組成 在前一篇文章中，我們了解到所謂的「流程控制」就是在流程圖中的「Is raining
  ?」或是「Have umbrella ?」。「流程控制」通常由兩部分所組成：「條件」與「條件成立時的任務」。 以「Is raining ?」為例，「Is raining」本身即是條件，如果這個條件滿足，會沿著
  Yes 的方向走，來到「Have umbrella ?」。此時，「Have umbrella ?」則為「條件成立時的任務」。再以「Have umbrella ?」為例，「Have
  umbrella ?」本身即是條件，如果這個條件滿足，會沿著 Yes 的方向走，來到「Wait a while.」。此時，「Wait a while.」則為「條件成立時的任務」。
  簡單來說，在程式裡的「流程控制」由兩部分所組成，分別為「條件」與「條件成立時的任務」。 在 Python 中，「條件」就是最終可以變成一個布林值 (Boolean
  Value) 的 Expression。舉例來說，在下圖中的每一個 Expression 都可以作為流程控制的條件，因為他們的結果都是一個布林值 (Boolean
  Value)。 1 == 2 10 […]
aliases:
- /python-tutorial/python-if-elif-else/
original_url: http://54.150.87.240/python-tutorial/python-if-elif-else/
wp_id: 162
images:
- images/feature-image-3.jpg
- images/flow-control-chart.jpg
- images/python-flow-control-1.jpg
- images/python-flow-control.jpg
---

![feature image](images/feature-image-3.jpg)

source: Pixabay

## 前言 & 概述

本篇為 Python 程式語言入門教學的第 6 篇文章！在前一篇文章中，我們介紹了[流程控制以及布林 (Boolean) 資料類型](http://54.150.87.240/python-tutorial/python-boolean-operator/)。本篇文章則是基於這兩項觀念，學習實際在 Python 中撰寫流程控制的語法。

如果你喜歡透過影片學習：

## 流程控制的組成

![flow control chart](images/flow-control-chart.jpg)

生活中的流程圖

在[前一篇文章](http://54.150.87.240/python-tutorial/python-boolean-operator/)中，我們了解到所謂的「流程控制」就是在流程圖中的「Is raining ?」或是「Have umbrella ?」。「流程控制」通常由兩部分所組成：「條件」與「條件成立時的任務」。

以「Is raining ?」為例，「Is raining」本身即是條件，如果這個條件滿足，會沿著 Yes 的方向走，來到「Have umbrella ?」。此時，「Have umbrella ?」則為「條件成立時的任務」。再以「Have umbrella ?」為例，「Have umbrella ?」本身即是條件，如果這個條件滿足，會沿著 Yes 的方向走，來到「Wait a while.」。此時，「Wait a while.」則為「條件成立時的任務」。

![python flow control](images/python-flow-control.jpg)

流程控制就是由「條件」與「條件成立時執行的任務」所組成

簡單來說，在程式裡的「流程控制」由兩部分所組成，分別為「條件」與「條件成立時的任務」。

在 Python 中，「條件」就是最終可以變成一個布林值 (Boolean Value) 的 Expression。舉例來說，在下圖中的每一個 Expression 都可以作為流程控制的條件，因為他們的結果都是一個布林值 (Boolean Value)。

```
1 == 2
```

```
10 <= 20
```

```
20-1 != 19
```

```
'apple' == 'apple'
```

## Python 中流程控制的語法

了解流程控制的組成後，接著是 Python 程式語言中流程控制的實際語法：

- **if**
- **elif**
- **else**

Python 提供這三種關鍵字，來撰寫流程控制的語法，我們將一一介紹。

## IF 語法

IF 語法是流程控制的第一步，當我們要在程式中撰寫流程控制的語法時，第一步就是使用 IF！我們直接觀察以下的程式碼片段：

```
if 2+3 == 5:
    print('YES')
```

上述的程式碼的意思為：如果 2+3 是 5，則印出 “YES”。我們可以了解「2 + 3 == 5」是條件，「print(‘YES’)」 則是條件成立時的任務。

聰明的你一定發現到，「2 + 3」的結果就是 5 呀！因此，如果把「2 + 3 == 5」當作條件的話，這個 Expression 最後的結果一定會是 True。因此我們也可以將上述程式碼改寫為：

```
if True:
    print('YES')
```

當程式執行到這一個流程控制的語法時，因為條件的結果一定是 True，因此「print(‘YES’)」一定會被執行。

我們經常會在條件中放入變數，讓條件的判斷更有彈性：

```
if name == 'Alice':
    print('Hi, ' + name)
```

這段程式碼所對應的流程圖為：

![python flow control](images/python-flow-control-1.jpg)

上述程式碼所對應到的流程圖 [source: Automate the Boring Stuff with Python]

了解 IF 語法如何撰寫後，我們必須特別注意兩個小細節：

- 「條件」後方的「冒號」
- 「條件成立時的任務」要縮排

## ELIF 語法

在上面的例子中，我們判斷了 name 這一個變數是否等於 ‘Alice’；但是如果我們希望判斷更多不同的條件呢？例如，name 變數是不是等於 ‘Johnny’？此時，就可以透過 ELSE IF 語法來實現。 我們直接看以下的程式碼：

```
name = 'Johnny'

if name == 'Alice':
    print('Hi, '+ name)
elif name == 'Johnny':
    print('How are you ' + name)
```

在上面的程式碼中，我們可以發現 Python 使用了「elif」關鍵字來表示 ELSE IF 語法。針對 name 這一個變數，我們使用了 2 種不同的條件 (Alice 與 Johnny)，電腦會由第一個條件依序向下判斷，只要遇到滿足的條件，就會執行相對應的內容。在此例子中，「print(‘How are you ‘ + name)」會被執行。

讓我們再多看幾個例子，釐清 IF 與 ELSE IF 語法的邏輯概念。

在以下這段程式碼中，你覺得程式的輸出會是什麼呢？

```
name = 'Alice'

if name == 'Alice':
    print('Hi, '+ name)
elif name == 'Alice':
    print('How are you ' + name)
```

程式的輸出會是「Hi, Alice」。如同上面所說的，當電腦遇到一連串的 IF 與 ELSE IF 語法時，會由第一個條件依序向下判斷，只要遇到滿足的條件，就會執行相對應的程式碼，然後後面的 ELSE IF 就不會再判斷了！

如果是以下的程式碼，程式的輸出會是什麼呢？

```
name = 'Alice'

if name == 'Alice':
    print('Hi, '+ name)

if name == 'Alice':
    print('How are you ' + name)
```

程式的輸出會是：

```
Hi, Alice
How are you Alice
```

原因在於這兩個條件都是使用 IF 語法進行判斷。所以兩個條件是「完全獨立」的，不管第一個條件是否滿足，電腦都會去判斷第二個條件。

了解 ELSE IF 語法如何撰寫後，我們必須特別注意兩個小細節：

- 「條件」後方的「冒號」
- 「條件成立時的任務」要縮排

## ELSE 語法

我們已經知道如何透過 IF 與 ELSE IF 語法撰寫「條件」以及「條件成立時相對應的任務」。那如果在「所有條件」皆不滿足的情況下，我們想要執行一些程式碼呢？此時就可以透過 ELSE 語法來達到這個目的。

舉例來說：

```
name = 'Johnny'

if name == 'Alice':
    print('Hi, '+ name)
elif name == 'Tim':
    print('How are you ' + name)
else:
    print('What is your name ?')
```

上述程式碼的執行結果為：「What is your name ?」。因為當所有的 IF 與 ELSE IF 條件皆不成立時，電腦就會執行 ELSE 中的程式碼。因此，我們可以發現 ELSE 語法是不需要指定條件的！

了解 ELSE 語法如何撰寫後，我們必須特別注意兩個小細節：

- 「條件」後方的「冒號」
- 「條件成立時的任務」要縮排

## 結語

在本篇文章中，我們學習了如何在 Python 中撰寫流程控制的語法，熟悉 IF、ELIF 與 ELSE 語法能夠幫助我們撰寫出更有互動性的程式！在下一篇文章中，我們將學習程式中 [Loop 的概念](http://54.150.87.240/python-tutorial/python-loop/)！
