---
title: Python 中的函式 (Function) 觀念 (Part 3)
date: '2022-05-14T14:01:44'
lastmod: '2022-06-18T02:24:56'
slug: python-function-part3
draft: false
categories:
- Python 基礎教學
tags:
- Python
- Python Function
description: 前言 在 Python 中的函式 (Function) 觀念 (Part 2) 一文中，我們了解到 Python 函式中的 Default
  Argument、Keyword Argument 與 Scope 的觀念，也介紹到 Local Variable (區域變數) 與 Global Variable
  (全域變數) 的生命週期。在文章的最後，我們也提到 Python Scope 的重要性質： 在 Global Scope 中的程式碼，不可以存取 Local Scope
  中的變數 (Local Variable) 在 Local Scope 中的程式碼，可以存取 Global Scope 中的變數 (Global Variable)
  在 Local Scope 中的程式碼，不可以存取其他 Local Scope 中的變數 (Local Variable) […]
aliases:
- /python-tutorial/python-function-part3/
original_url: http://54.150.87.240/python-tutorial/python-function-part3/
wp_id: 813
images:
- images/feature-image-1.jpg
- images/python-scope.jpg
- images/python-scope.png
---

![feature image](images/feature-image-1.jpg)

source: Pixabay

## 前言

在 [Python 中的函式 (Function) 觀念 (Part 2)](http://54.150.87.240/python-tutorial/python-function-part2/) 一文中，我們了解到 Python 函式中的 Default Argument、Keyword Argument 與 Scope 的觀念，也介紹到 Local Variable (區域變數) 與 Global Variable (全域變數) 的生命週期。在文章的最後，我們也提到 Python Scope 的重要性質：

- 在 Global Scope 中的程式碼，不可以存取 Local Scope 中的變數 (Local Variable)
- 在 Local Scope 中的程式碼，可以存取 Global Scope 中的變數 (Global Variable)
- 在 Local Scope 中的程式碼，不可以存取其他 Local Scope 中的變數 (Local Variable)
- 假設兩個變數處在不同的 Scope 中，這兩個變數可以使用相同的名字

在本篇文章中，我們將針對這四項性質做更深入的介紹！

如果你喜歡透過影片學習：

## 在 Global Scope 中的程式碼，不可以存取 Local Scope 中的變數 (Local Variable)

舉例來說，如果執行下方的程式碼：

```
def say_hello():
    text = "hello"

say_hello()
print(text)
```

將會出現以下錯誤訊息：

![python scope](images/python-scope.png)

表示「text」這個變數並沒有被宣告過

這個錯誤訊息的意思為「text」這一個變數並沒有被宣告過，因此電腦根本不知道他是什麼。但是我們明明就有在 say\_hello( ) 函式中定義呀？！

原因在於 say\_hello( ) 函式會形成一個 Local Scope，在 Local Scope 中的變數 (text) 為 Local Variable。只有當我們在第四行呼叫 say\_hello( ) 函式時，這個 text 變數才會存在。也就是說，當電腦執行到第五行程式碼時，text 變數早就已經不存在，因此才會出現錯誤訊息。

## 在 Local Scope 中的程式碼，可以存取 Global Scope 中的變數 (Global Variable)

舉例來說，如果執行以下程式碼：

```
def say_hello():
    print(text)

text = "hello"
say_hello()
```

將會輸出：

```
hello
```

因為在呼叫 say\_hello( ) 函式之前，我們已經先定義了「text」這一個變數，text 這一個變數是定義在 Global Scope 中，因此屬於 Global Variable，只有當整個程式都執行完畢時，text 變數才會被消滅。

## 在 Local Scope 中的程式碼，不可以存取其他 Local Scope 中的變數 (Local Variable)

舉例來說，如果執行以下程式碼：

```
def say_hello1():
    text1 = "hello1"

def say_hello2():
    text2 = "hello2"
    print(text1)

say_hello2()
```

將出現以下錯誤訊息：

![python scope](images/python-scope.jpg)

text1 這個變數並沒有被定義過

這個錯誤訊息的意思為當電腦在執行 say\_hello2( ) 函式時，發現「text1」變數並沒有被宣告過。然而，我們不是已經在 say\_hello1( ) 函式中宣告過了嗎？

原因在於每一個函式所形成的 Local Scope 都是彼此獨立互不影響的，也就是說在 say\_hello2( ) 函式中，完全不知道 say\_hello1( ) 函式中發生了什麼事情。因此當我們嘗試顯示 text1 變數的內容時，就會發生錯誤！

## 假設兩個變數處在不同的 Scope 中，這兩個變數可以使用相同的名字

如同上一點所說的，「在 say\_hello2( ) 函式中，完全不知道 say\_hello1( ) 函式中發生了什麼事情」因此我們當然可以在兩個函式 (Local Scope) 中使用相同的變數名稱，如下方程式碼所示：

```
def say_hello1():
    text = "hello1"

def say_hello2():
    text = "hello2"

say_hello2()
```

say\_hello1( ) 與 say\_hello2( ) 兩個函式中的內容彼此不會影響。

## 結語

在本篇文章中，我們了解到 Python 中關於 Scope 的重要觀念。在下一篇文章中，我們將會介紹如果電腦在執行 Python 程式時遇到非預期的狀況，除了中斷程式的執行，產生錯誤訊息之外，我們還可以怎麼處理這些情況。
