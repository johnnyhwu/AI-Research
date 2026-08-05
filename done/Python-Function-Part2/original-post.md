---
title: Python 中的函式 (Function) 觀念 (Part 2)
date: '2022-04-02T01:54:59'
lastmod: '2022-06-18T02:24:24'
slug: python-function-part2
draft: false
categories:
- Python 基礎教學
tags:
- Python
description: '前言 在 Python 中的函式 (Function) 觀念 (Part 1) 中，我們學習 Python 中函式的基本觀念，我們從最基本的函式開始，又來到帶有參數的函式，最後則是帶有回傳值的函式，並說明
  Python 中的 NoneType 與 None 的觀念。 在本篇文章中，我們將繼續介紹 Python 中的函式 (Function)，了解什麼是 Default
  Argument、Keyword Argument 與 Function Scope 的觀念。 如果你喜歡透過影片學習： Python Function 的 Default
  Argument 在前一篇文章中，我們介紹如何在 Python 中定義一個帶有參數的函式，我們再以一個簡單的範例回顧觀念： def say_hello(name):
  print(f’hello, {name}’) 在上方程式碼中，我們定義了一個 say_hello 的函式，這一個函式接受一個參數。我們在呼叫這一個函式時，可以傳入一個參數：
  say_hello(‘Tom’) 我們傳入一個字串到該函式中，字串 “Tom” 也會對應到 name 這一個參數。 實際上，假如我們在呼叫 say_hello
  函式時，沒有傳入參數： say_hello() 電腦會顯示錯誤訊息： […]'
aliases:
- /python-tutorial/python-function-part2/
original_url: http://54.150.87.240/python-tutorial/python-function-part2/
wp_id: 732
images:
- images/feature-image-2.jpg
---

![feature image](images/feature-image-2.jpg)

source: Pixabay

## 前言

在 [Python 中的函式 (Function) 觀念 (Part 1)](http://54.150.87.240/python-tutorial/python-function/) 中，我們學習 Python 中函式的基本觀念，我們從最基本的函式開始，又來到帶有參數的函式，最後則是帶有回傳值的函式，並說明 Python 中的 NoneType 與 None 的觀念。

在本篇文章中，我們將繼續介紹 Python 中的函式 (Function)，了解什麼是 Default Argument、Keyword Argument 與 Function Scope 的觀念。

如果你喜歡透過影片學習：

## Python Function 的 Default Argument

在前一篇文章中，我們介紹如何在 Python 中定義一個帶有參數的函式，我們再以一個簡單的範例回顧觀念：

```
def say_hello(name):
    print(f'hello, {name}')
```

在上方程式碼中，我們定義了一個 say\_hello 的函式，這一個函式接受一個參數。我們在呼叫這一個函式時，可以傳入一個參數：

```
say_hello('Tom')
```

我們傳入一個字串到該函式中，字串 “Tom” 也會對應到 name 這一個參數。

實際上，假如我們在呼叫 say\_hello 函式時，沒有傳入參數：

```
say_hello()
```

電腦會顯示錯誤訊息：

```
TypeError: say_hello() missing 1 required positional argument: 'name'
```

主要是因為我們在定義 say\_hello 函式時，就定義了這一個函式會接受一個參數，因此如果在呼叫 say\_hello 時沒有傳入任何東西，電腦會不知道應該將 say\_hello 的參數 “name” 替換成什麼數值。

按照這個想法，如果我們希望即使在呼叫 say\_hello 時沒有傳入任何東西，電腦也不要跳出錯誤訊息的話，我們可以替 say\_hello 的參數 “name” 加上一個**預設值**：

```
def say_hello(name="Johnny"):
    print(f'hello, {name}')

say_hello()
```

如此一來，即使我們在呼叫 say\_hello 時沒有傳入任何東西，電腦也知道應該將參數 “name” 替換成什麼數值。

簡單來說，「Default Argument」指的就是帶有「預設值」的參數。

## 混用「有」預設值與「沒有」預設值的參數

如果我們在定義一個函式時，函式所接受的參數有些有預設值、有些沒有，我們一定要確保：**沒有預設值的參數要在左邊**。

舉例來說：

```
def say_hello(age, name="Johnny"):
    print(f'I am {name}')
    print(f'I am {age} years old')
```

當我們定義 say\_hello 函式可以接受 age (沒有預設值) 與 name (有預設值) 兩個參數時，age 必須寫在 name 的左邊。如果放錯邊，將會出現錯誤訊息：

```
def say_hello(name="Johnny", age):
    print(f'I am {name}')
    print(f'I am {age} years old')
```

```
SyntaxError: non-default argument follows default argument
```

## Python Function 的 Keyword Argument

我們在呼叫函式時，經常是透過「位置」來將我們傳入的資訊對應到函式的參數。

以上面定義的 say\_hello 函式為例：

```
def say_hello(age, name="Johnny"):
    print(f'I am {name}')
    print(f'I am {age} years old')
```

當我們在呼叫該函式時，可以傳入一個或兩個參數到函式當中。如果我們只傳入一個：

```
say_hello(100)
```

此參數 (100) 會對應到 say\_hello 的 “age” 參數， “name” 參數則是使用預設值 “Johnny”。當我們傳入兩個參數：

```
say_hello(100, Tom)
```

傳入的**第一個**參數 (100) 會對應到 say\_hello 的**第一個**參數 (age)；傳入的**第二個**參數 (Tom) 會對應到 say\_hello 的**第二個**參數 (name)。

除了透過「位置」來將我們傳入的資訊對應到函式的參數，我們也可以透過「關鍵字」指定：

```
say_hello(age=100, name="Tom")
```

當我們透過關鍵字指定時，呼叫函式時所傳入的參數的順序就可以任意變動：

```
say_hello(name="Tom", age=100)
```

## print( ) 函式的 Keyword Argument

實際上，我們經常使用的 print( ) 函式，也有其他的參數可以傳入。舉例來說，通常 print( ) 函式在顯示一段字串後，會在結尾加上「換行符號」，使得下一個 print( ) 函式所顯示的東西會在下一行：

```
print('Hello')
print('Johnny')
```

當我們執行上述程式碼後，會顯示以下結果：Hello 在第一行，Johnny 在第二行。

```
Hello
Johnny
```

如果我們希望 Johnny 不要換到下一行而是跟在 Hello 之後，我們可以在 print( ) 函式中透過「end」這一個 Keyword Argument 指定附加在字串最後面的字元。

例如，在 Hello 字串的最後方不要附加任何字元：

```
print('Hello', end="")
print('Johnny')
```

此時顯示的結果為：

```
HelloJohnny
```

或者，在 Hello 字串的最後方不要附加「一個空格」：

```
print('Hello', end=" ")
print('Johnny')
```

此時顯示的結果為：

```
Hello Johnny
```

## Python 中的 Scope 觀念

在 [Python 中的 (Function) 觀念 Part 1](http://54.150.87.240/python-tutorial/python-function/) 中，我們介紹到如果在函式「外部」存取函式「內部」的變數，電腦會跳出錯誤訊息。舉例來說：

```
def say_hello(age, name="Johnny"):
    print(f'I am {name}')
    print(f'I am {age} years old')

print(age)
```

```
NameError: name 'age' is not defined
```

因為 age 這一個變數是只存在於 say\_hello 函式內部，因此無法在函式的外部存取。一個函式會有一個自己的「範圍」、自己的「界線」，這就是程式語言中的 **Scope** 觀念。

## Local Scope 與 Global Scope

Scope 可以分為 Local Scope 與 Global Scope，在函式內部會形成一個 Local Scope，在函式外部則屬於 Global Scope。在 Local Scope 中建立的變數稱為 **Local Variable (區域變數)**； 在 Global Scope 中建立的變數稱為 **Global Variable (全域變數)**。一個變數只能擁有一個身份，也就是它不是 Local Variable 就是 Global Variable，也不可以兩者兼具。

```
a = 5
b = 10

def example():
    c = 15
    d = 20

e = 25
```

以上述程式碼為例，變數 a、b 與 e 都在 Global Scope 中，因此屬於 Global Variable；而變數 c 與 d 在 Local Scope 中，因此屬於 Local Variable。

相信聰明的你已經發現：函式內部的變數就是 Local Variable；函式外部的變數就是 Global Variable。一個程式可以有很多 Local Scope，但是只會有一個 Global Scope。

## Python 中變數的生命週期

學到這裡，我們已經清楚知道 Python 程式中的變數，可以分為 Local Variable (區域變數) 與 Global Variable (全域變數)。兩種變數都有其各自的生命週期。

當一個**「函式」**被執行時，屬於這個函式的 Local Scope 也會被建立。在這個函式中所建立的變數，都會存放在這一個 Local Scope 中。當這個函式執行結束之後，這一個 Local Scope 也隨之被消滅。當然，存放在這一個 Local Scope 裡的變數 (區域變數) 也會隨之消失。

當一個完整的**「程式」** (.ipynb 或 .py) 開始執行時，屬於這個程式的 Global Scope 也會被建立。在這個程式中所建立的變數，都會存放在這一個 Global Scope 中。當這個程式執行結束之後，這一個 Global Scope 也隨之被消滅。當然，存放在這一個 Global Scope 裡的變數 (全域變數) 也會隨之消失。

## Python 中 Scope 的重要性質

了解 Local Scope 與 Global Scope 的觀念後，接著讓我們談談 Scope 的重要性質：

- 在 Global Scope 中的程式碼，不可以存取 Local Scope 中的變數 (Local Variable)
- 在 Local Scope 中的程式碼，可以存取 Global Scope 中的變數 (Global Variable)
- 在 Local Scope 中的程式碼，不可以存取其他 Local Scope 中的變數 (Local Variable)
- 假設兩個變數處在不同的 Scope 中，這兩個變數可以使用相同的名字

## 結語

在本篇文章中，我們了解到 Python 函式中的 Default Argument、Keyword Argument 與 Scope 的觀念，也介紹到 Local Variable (區域變數) 與 Global Variable (全域變數) 的生命週期。

在本文的最後，我們提到 Python 中 Scope 的重要觀念。[下一篇文章](http://54.150.87.240/python-tutorial/python-function-part3/)中，我們會更深入的說明這四項性質的意義。
