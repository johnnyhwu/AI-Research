---
title: Python 中的函式 (Function) 觀念 (Part 1)
date: '2022-02-24T07:05:44'
lastmod: '2022-06-18T02:23:48'
slug: python-function
draft: false
categories:
- Python 基礎教學
tags:
- Python
description: "前言 在前幾篇的 Python 教學文章中，我們介紹到了函式 (Function) 這一個名詞，並使用了一些 Python 中的內建函式\
  \ (Built-in Function)。例如：print()、len() 與 input()。在本篇文章中，我們將會理解 Python 中函式的概念，並學習定義自己的函式。\
  \ 如果你喜歡透過影片學習： Python 中的函式 (Function) 我們首先觀察以下的程式碼： def first_function():     print(‘Hello\
  \ World’) first_function() 上方的程式碼中，我們定義了一個名為「first_function」的函式，並呼叫這一個函式。我們接著理解\
  \ Python 中函式的組成元素。 首先，在上方程式碼的第 1 行中，使用「def」關鍵字，表示我們正在「定義」一個函式。跟在 def 之後的「first_function」是這一個函式的「名稱」。名稱之後之後還需要加上一個「括號」，我們等一下會解釋它的用途。\
  \ 當我們撰寫好「def」、「函式名稱」與「括號」時，我們還需要說明函式內部應該要執行什麼樣的程式碼。類似 for loop 與 while loop 的語法，我們會在後方加上一個「冒號」，函式內部的程式碼則必須「縮排」。當函式被呼叫時，函式內部的程式碼就會被執行。在上方的程式碼中，函式內部僅包含「print(‘Hello\
  \ World’)」。 在上方程式碼區塊的最後一行，我們呼叫了\b這一個函式。呼叫函式的方式很簡單，僅需要撰寫「函式名稱」與「括號」，即可以呼叫該函式。 在「括號」中，我們可以提供一些參數給這一個函式。例如，當我們使用\
  \ Python 的內建函式「print()」時，我們就會將我們想要顯示的字串放到括號中： print(‘Hello World’) 當電腦執行到「呼叫函式」的程式碼時，就會跳到該函式的內部程式碼的第一行，並開始執行。當電腦執行完函式中所有的程式碼之後，又會再回到剛剛「呼叫函式」的程式碼，並繼續執行後續的程式碼。\
  \ 舉例來說： def first_function():     print(‘Hello […]"
aliases:
- /python-tutorial/python-function/
original_url: http://54.150.87.240/python-tutorial/python-function/
wp_id: 590
images:
- images/feature-image-15.jpg
---

![](images/feature-image-15.jpg)

source: Pixabay

## 前言

在前幾篇的 [Python 教學文章](http://54.150.87.240/topics/python-tutorial/)中，我們介紹到了函式 (Function) 這一個名詞，並使用了一些 Python 中的內建函式 (Built-in Function)。例如：print()、len() 與 input()。在本篇文章中，我們將會理解 Python 中函式的概念，並學習定義自己的函式。

如果你喜歡透過影片學習：

## Python 中的函式 (Function)

我們首先觀察以下的程式碼：

```
def first_function():
    print('Hello World')

first_function()
```

上方的程式碼中，我們定義了一個名為「first\_function」的函式，並呼叫這一個函式。我們接著理解 Python 中函式的組成元素。

首先，在上方程式碼的第 1 行中，使用「def」關鍵字，表示我們正在「定義」一個函式。跟在 def 之後的「first\_function」是這一個函式的「名稱」。名稱之後之後還需要加上一個「括號」，我們等一下會解釋它的用途。

當我們撰寫好「def」、「函式名稱」與「括號」時，我們還需要說明函式內部應該要執行什麼樣的程式碼。類似 [for loop 與 while loop 的語法](http://54.150.87.240/python-tutorial/python-loop/)，我們會在後方加上一個「冒號」，函式內部的程式碼則必須「縮排」。當函式被呼叫時，函式內部的程式碼就會被執行。在上方的程式碼中，函式內部僅包含「print(‘Hello World’)」。

在上方程式碼區塊的最後一行，我們呼叫了這一個函式。呼叫函式的方式很簡單，僅需要撰寫「函式名稱」與「括號」，即可以呼叫該函式。

在「括號」中，我們可以提供一些參數給這一個函式。例如，當我們使用 Python 的內建函式「print()」時，我們就會將我們想要顯示的字串放到括號中：

```
print('Hello World')
```

當電腦執行到「呼叫函式」的程式碼時，就會跳到該函式的內部程式碼的第一行，並開始執行。當電腦執行完函式中所有的程式碼之後，又會再回到剛剛「呼叫函式」的程式碼，並繼續執行後續的程式碼。

舉例來說：

```
def first_function():
    print('Hello World')

first_function() #1
print('執行完 1 次') #2
first_function() #3
print('執行完 2 次') #4
```

如同上述程式碼所示，我們在第一次呼叫 first\_function (#1) 之後，電腦會來到 first\_function 的第一行程式碼，並執行「print(‘Hello World’)」，執行完 first\_function 中的所有程式碼後，又會再回到剛剛呼叫的地方 (#1)，並繼續執行後方的程式碼。最終的輸出為：

```
Hello World
執行完 1 次
Hello World
執行完 2 次
```

## Python 中帶有參數的函式

走到 [Python 程式語言基礎教學](http://54.150.87.240/topics/python-tutorial/)的第 7 篇文章，相信你已經非常熟悉如何透過 print() 函式，顯示我們想要的字串，我們在括號中所放的字串稱為 Argument，Argument 會在我們呼叫該函式的過程傳入該函式中。

舉例來說：

```
def second_function(name):
    print(f'Hello, {name}')

second_function('Johnny')
```

在函式名稱 second\_function 的後方括號中，我們放入一個變數「name」，這一個變數又稱為 Parameter，表示這個函式可以接受什麼參數傳入。因此，我在呼叫該函式的地方傳入了一個字串 ‘Johnny’，最後的顯示結果為：

```
Hello, Johnny
```

看到這裡也許你已經被 Parameter 與 Argument 搞得暈頭轉向，其實我們不需要太糾結於這些專有名詞，僅需了解它的意義：

- Parameter : 在「定義函式」階段，規定這一個函式能夠接受哪些東西。例如，上方程式碼中的「name」
- Argument : 在「呼叫函式」階段，實際上傳入函式的東西。例如，上方程式碼中的「’Johnny’」。

需要特別注意的是，函式所接受的 Parameter 在函式的內部可以當作一邊變數使用，然而當函式執行完畢之後，這一個變數也會被消滅掉，因此我們無法在函式的外部使用這一個變數。

舉例來說，我們在 second\_function(‘Johnny’) 的下方加上一行：

```
def second_function(name):
    print(f'Hello, {name}')

second_function('Johnny')
print(name)
```

執行的結果為：

```
NameError: name 'name' is not defined
```

原因在於，name 這一個變數在 second\_function 函式執行完畢之後就會被消滅，因此無法在函式的外面使用這一個變數。

## Python 中帶有回傳值的函式

除了 print() 函式之外，我們也經常使用 len() 函式來取得字串的長度。

舉例來說：

```
name = 'Johnny'
length = len(name)
print(length)
```

上述程式碼將會顯示 name 這一個字串的長度。len() 函式呼叫後，會回傳一個整數，我們將這一個整數存到 length 變數中。

如果希望函式在執行後，能夠回傳數值到原來呼叫的地方，則必須使用「return」關鍵字。舉例來說：

```
def third_function(name):
    return f'Hello, {name}'

output = third_function('Johnny')
print(output)
```

在 third\_function 中，我們透過 return 關鍵字回傳一個字串。因此，third\_function(‘Johnny’) 執行完的結果會是 “Hello, Johnny”，並存到 output 變數中。

需要特別注意的是，當函式執行到「return」關鍵字時，則表示該函式執行結束，「return」之下的東西將不會被執行。

```
def fourth_function(name):
    return f'Hello, {name}'
    print('under return keyword')

output = fourth_function('Johnny')
print(output)
```

這段程式碼的執行結果將會與原來的相同。因為在 fourth\_function 中，print(‘under return keyword’) 在 return 之後，因此將不會被執行。

## Python 中的 NoneType 與 None

在[Python 中的變數與資料類型](http://54.150.87.240/python-tutorial/python-variable-data-type/)文章中，我們介紹過 Python 中基本的資料型態，有 Integer、String 與 Floating-Point Number 等類型。

今天我們要再介紹一種新的 Data Type 稱為 **NoneType**，NoneType 只有唯一一個數值，稱為「None」。一個 Type 裡頭只包含 1 個或 2 個數值並不奇怪，我們之前學到的 [Boolean Type](http://54.150.87.240/python-tutorial/python-boolean-operator/) 裡頭就只有 True 與 False 兩種數值。

那為什麼我們需要多學習 NoneType 這種神奇的 Data Type 呢？原因與函式的回傳值有關係！

實際上，每一個函式都應該要有回傳值，也就是每次呼叫函式過後必須都可以得到一個數值。例如，呼叫 third\_function()、fourth\_function() 與 len() 函式都可以得到一個數值。如果函式要有回傳值，就必須在函式的最後加上一個「return …」，然而我們並不是每一次都會在函式的最後加上這個東西。

為了解決這一個問題，只要我們在 Python 中所定義的函式沒有「return …」的話，那麼 Python 就會自動幫我們加上一個「return None」。我們再回來看看 first\_function()：

```
def first_function():
    print('Hello World')

output = first_function()

if(output == None):
    print(f"output is None")
```

我們將 first\_function() 的執行結果存到 output 變數中，並判斷 output 是不是等於 None。最後的輸出為：

```
Hello World
output is None
```

由此我們可以理解，即使在 first\_function() 中我們沒有回傳任何數值，也就是沒有使用「return …」，Python 仍會自動幫我們加上「return None」，使得函式最終的回傳值為 None。

## 結語

在本篇文章中，我們學習 Python 中函式的基本觀念，我們從最基本的函式開始，又來到帶有參數的函式，最後則是帶有回傳值的函式，並說明 Python 中的 NoneType 與 None 的觀念。

在[下一篇文章](http://54.150.87.240/python-tutorial/python-function-part2/)中，我們會介紹 Python 中函式更深入的觀念，學習函式的範疇 (Function Scope)。
