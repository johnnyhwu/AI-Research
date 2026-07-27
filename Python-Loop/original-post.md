---
title: Python 中的迴圈 (Loop) 觀念
date: '2022-01-27T06:18:52'
lastmod: '2022-06-18T15:25:11'
slug: python-loop
draft: false
categories:
- Python 基礎教學
tags:
- Python
description: "前言 前一篇文章中，我們學習了如何在 Python 中撰寫流程控制的語法，透過 if、elif 與 else 關鍵字能夠在程式中加入「條件的判斷」，並執行相對應的程式碼。在本篇文章中，我們將延伸流程控制中「條件」的概念，來解釋程式中的「迴圈」(Loop)\
  \ 。 如果你喜歡透過影片學習： AD 迴圈 (Loop) 是什麼 在前一篇文章中，我們介紹過上篇這張圖。所謂的「流程控制」，就是由「條件」與條件成立時要執行的「任務」所組成。因此，電腦在執行此程式時，會先對條件進行判斷，依照判斷結果執行相對應的程式碼，整個程式才算是執行結束。\
  \ 假如我們希望電腦在執行此程式時，可以「重複」進行條件的判斷呢？如下圖所示，在執行完相對應程式碼後，程式並沒有結束，而是「重新」回到條件的判斷\b。 你注意到了嗎？「重複」、「重新」或是「再一次」指的就是「迴圈」(Loop)。在程式的世界中，「迴圈」的概念相當常見，只要我們希望『符合某一條件，就「重複」執行某段程式碼』，就會透過迴圈的概念來實作。\
  \ Python 中的迴圈語法 如下方的列表所示，在 Python 與大多數的程式語言中，迴圈的語法通常會透過兩種關鍵字來實現，分別是「while」與「for」。兩種關鍵字所寫出來的迴圈，就稱為「while\
  \ loop」與「for loop」。 for → for loop while → while loop 其中，while loop 的觀念就是我們上面對迴圈的介紹，因此我們先從\
  \ Python 中的 while loop 語法開始介紹。 AD Python 中的 while loop 我們直接觀察以下的程式碼： num = 0 while\
  \ num < 3:   print(‘number: […]"
aliases:
- /python-tutorial/python-loop/
original_url: http://54.150.87.240/python-tutorial/python-loop/
wp_id: 168
images:
- images/feature-image-4.jpg
- images/loop-1.jpg
- images/loop.jpg
- images/python-flow-control.jpg
---

![feature image](images/feature-image-4.jpg)

source: Pixabay

## 前言

前一篇文章中，我們學習了如何在 [Python 中撰寫流程控制](http://54.150.87.240/python-tutorial/python-if-elif-else/)的語法，透過 **if**、**elif** 與 **else** 關鍵字能夠在程式中加入「條件的判斷」，並執行相對應的程式碼。在本篇文章中，我們將延伸流程控制中「條件」的概念，來解釋程式中的「迴圈」(Loop) 。

如果你喜歡透過影片學習：

AD

## 迴圈 (Loop) 是什麼

![python flow control](images/python-flow-control.jpg)

流程控制就是由「條件」與「條件完成後的任務」所組成

在[前一篇文章](http://54.150.87.240/python-tutorial/python-if-elif-else/)中，我們介紹過上篇這張圖。所謂的「流程控制」，就是由「條件」與條件成立時要執行的「任務」所組成。因此，電腦在執行此程式時，會先對條件進行判斷，依照判斷結果執行相對應的程式碼，整個程式才算是執行結束。

假如我們希望電腦在執行此程式時，可以「重複」進行條件的判斷呢？如下圖所示，在執行完相對應程式碼後，程式並沒有結束，而是「重新」回到條件的判斷。

![loop](images/loop.jpg)

執行完相對應的程式碼後，再回到條件的判斷

你注意到了嗎？「重複」、「重新」或是「再一次」指的就是「迴圈」(Loop)。在程式的世界中，「迴圈」的概念相當常見，只要我們希望『符合某一條件，就「重複」執行某段程式碼』，就會透過迴圈的概念來實作。

## Python 中的迴圈語法

如下方的列表所示，在 Python 與大多數的程式語言中，迴圈的語法通常會透過兩種關鍵字來實現，分別是「**while**」與「**for**」。兩種關鍵字所寫出來的迴圈，就稱為「**while loop**」與「**for loop**」。

- **for** → for loop
- **while** → while loop

其中，while loop 的觀念就是我們上面對迴圈的介紹，因此我們先從 Python 中的 while loop 語法開始介紹。

AD

## Python 中的 while loop

我們直接觀察以下的程式碼：

```
num = 0

while num < 3:
    print('number: ' + str(num))
    num = num + 1
```

在程式碼中，我們使用了 **while** 關鍵字，並在關鍵字後方加上**條件與冒號**，滿足條件的程式碼則是**換行並縮排**。

下方為此程式的輸出，我們可以發現迴圈中的程式碼總共被執行了三次。

```
number: 0 
number: 1 
number: 2
```

我們必須注意到在上方程式碼中，一定是「先」確定條件成立，「後」執行迴圈內部的程式碼。接著，讓我們深入了解上述程式碼的執行流程：

- 第 1 個 Loop
  - 判斷條件 num < 3。因為此時 num 為 0，故條件成立。
  - 執行迴圈內的程式碼。「number: 0」被顯示出來，num 被加上 1，變成 1。
- 第 2 個 Loop
  - 判斷條件 num < 3。因為此時 num 為 1，故條件成立。
  - 執行迴圈內的程式碼。「number: 1」被顯示出來，num 被加上 1，變成 2。
- 第 3 個 Loop
  - 判斷條件 num < 3。因為此時 num 為 2，故條件成立。
  - 執行迴圈內的程式碼。「number: 2」被顯示出來，num 被加上 1，變成 3。
- 第 4 個 Loop
  - 判斷條件 num < 3。因為此時 num 為 3，故條件**不成立**。

從上面的執行流程，我們可以清楚觀察到：「迴圈條件」被執行了 **4** 次；「迴圈內部的程式碼」被執行了 **3** 次。

接著，我們再透過一個程式範例，熟悉 while loop 的撰寫。下方的程式碼，透過 while loop 計算 1 到 100 的總和：

```
sum = 0
num = 1

while num <= 100:
    sum += num
    num += 1

print(f'sum: {sum}')
```

下方為程式實際的執行流程：

- 第 1 個 Loop
  - 判斷 Loop 條件「num <= 100」。此時 num 為 1，故條件成立。
  - 執行 Loop 程式碼「sum += num」，相當於「sum = sum + num」，此時 sum 為 **1**、num 為 2。
- 第 2 個 Loop
  - 判斷 Loop 條件「num <= 100」。此時 num 為 2，故條件成立。
  - 執行 Loop 程式碼「sum += num」，相當於「sum = sum + num」，此時 sum 為 **1 + 2**、num 為 3。
- 第 3 個 Loop
  - 判斷 Loop 條件「num <= 100」。此時 num 為 3，故條件成立。
  - 執行 Loop 程式碼「sum += num」，相當於「sum = sum + num」，此時 sum 為 **1 + 2 + 3**、num 為 4。
- 第 4 個 Loop
  - 判斷 Loop 條件「num <= 100」。此時 num 為 4，故條件成立。
  - 執行 Loop 程式碼「sum += num」，相當於「sum = sum + num」，此時 sum 為 **1 + 2 + 3 + 4**、num 為 5。

…

- 第 100 個 Loop
  - 判斷 Loop 條件「num <= 100」。此時 num 為 100，故條件成立。
  - 執行 Loop 程式碼「sum += num」，相當於「sum = sum + num」，此時 sum 為 **1 + 2 + 3 + 4 + … + 100**、num 為 101。
- 第 101 個 Loop
  - 判斷 Loop 條件「num <= 100」。此時 num 為 101，故條件**不成立**。

由此我們可以清楚的觀察到 while loop 由 1 加到 100 的過程。

需要特別補充的是最後一行的 **print()** 函式。除了透過「字串加法」將字串與變數合起來之外，我們也可以透過 **f string** 的方式將變數插入到字串中。

```
# 字串加法：
print('sum: ' + str(sum))

# f string
print(f'sum: {sum}')
```

當我們使用 f string 的寫法時，需要在字串前方加上 f，並在字串中需要插入變數的地方透過｛｝將變數包起來。透過 f string 可以更簡單的將字串與變數和在一起。

## break 與 continue

提到迴圈 (Loop) 的觀念時，break 與 continue 兩個角色一定會被介紹到。

- **break：立即離開迴圈**

當迴圈的條件成立後，電腦會執行回圈內部的程式碼。我們可以在迴圈內加上 break，當電腦執行到這一行時，就會直接離開迴圈。

```
sum = 0
num = 1

while num <= 100:
    sum += num
    num += 1
    break

print(f'sum: {sum}')
```

在上述的程式碼中，最終的 sum 會是 1。因為當電腦第一次進入迴圈後，遇到 break 時，就會馬上離開迴圈。如果直接在迴圈內部的程式碼加上 break 就會失去迴圈「重複」執行的目的。因此，我們通常會透過 **if** 進行判斷，如果條件滿足，才透過 break 離開迴圈。

```
sum = 0
num = 1

while num <= 100:
    sum += num
    num += 1

    if sum > 1000:
        break

print(f'sum: {sum}')
```

在上面這段程式碼中，我們判斷如果「sum > 1000」才執行 break。

- **continue：直接回到迴圈條件判斷**

當迴圈的條件成立後，電腦會執行回圈內部的程式碼。我們可以在迴圈內加上 continue，當電腦執行到這一行時，就會直接回到迴圈的條件進行判斷。

```
sum = 0
num = 1

while num <= 100:
    sum += num
    num += 1
    print(f'sum: {sum}')
```

在上面這段程式碼中，每一次迴圈的最後都會將 sum 的數值顯示出來。但是如果我們希望只有當 sum > 4000 時才顯示，我可以透過 continue 直接忽略迴圈內剩下的程式碼，回到迴圈條件判斷的地方：

```
while num <= 100:
    sum += num
    num += 1

    if sum < 4000:
        continue

    print(f'sum: {sum}')
```

只要 sum < 4000，電腦就會執行到 continue 這行程式碼，馬上結束這一個迴圈，回到迴圈條件判斷的階段。

這邊需要特別注意的是，break 與 continue 只能寫在**迴圈內部**，也就是只能用在 while loop 與 for loop 當中。

## Python 中的 for loop

了解完 while loop 後，我們接著學習 Python 中的 for loop。如下圖所示，while loop 是以「條件」來決定目前的迴圈是否要執行；for loop 則是透過「次數」決定好要執行幾次迴圈。

![loop](images/loop.jpg)

while loop 是以「條件」決定迴圈是否要執行

![loop](images/loop-1.jpg)

for loop 是以「次數」決定總共執行幾次迴圈

在 Python 中，我們經常會透過 **range()** 函式，指定 for loop 要執行的次數。

```
for num in range(10):
    print('Hello World')
```

上方程式碼為 Python 中基本的 for loop 範例。Python 中 for loop 的語法通常由下列元素所組成：

- for 關鍵字
- 變數名稱 → 上方使用 num
- in 關鍵字
- 序列 (Sequence) 或可迭代的物件 (Iterable Object) → 上方使用 range(10)

「**序列 (Sequence) 或可迭代的物件 (Iterable Object)**」這一個名詞實在是看起來很可怕，但是對於初學著的我們而言，我們可以先把它想成「一連串的物件」。如下方列出很多「一連串的物件」：

- [1, 2, 3, 4, 5, 6, 7, 8]
- [“apple”, “orange”, “132”, “456”, “789”]
- [-1, -6, 65, 32]
- [2.5, 3.0, 5.2, 3.1]

因此，**range(10)** 我們可以先把它想成 **[0, 1, 2, 3, 4, 5, 6, 7, 8, 9] (注意是 0 到 9，不是 1 到 10)**。**for num in range(10)** 則變成 **for num in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]。**按照字面上的意思，每一次的迴圈中 num 都會「依序」對應到 [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] 中的每一個數字。因此，透過 range(10) 指定迴圈總共執行 10 次。

```
for num in range(10):
    print(f'num: {num}')
```

上方程式碼直接將 num 每一次對應到的數字顯示出來。

我們一樣可以在 for loop 中使用 break 與 continue 等關鍵字：

```
for num in range(10):

    if num == 5:
        break

    print(f'num: {num}')
```

在上方程式碼中，如果 num 為 5 時，就直接離開迴圈。

接著，我們再透過一個程式範例，熟悉 for loop 的撰寫。下方的程式碼，透過 for loop 計算 1 到 100 的總和：

```
sum = 0

for num in range(101):
    sum += num

print(f'sum: {sum}')
```

## range() 的進階用法

在上文中，我已經了解到 range() 函式的基礎用法。實際上，range() 函式可以接受 3 個參數，分別表示：

- 起始位置 (start)
- 終止位置 (end)
- 步伐長度 (step)

在上文中，我們都只有提供一個參數給 range() 函式，其實我們提供的就是 stop。

```
range(10)
```

上方的程式碼中，我們指定 range() 的 stop 參數為 10，相當於：

```
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
```

如果我們提供 2 個參數給 range()，其實表示的是 start 與 stop：

```
range(10, 20)
```

上方程式碼表示 start 為 10，stop 為 20，相當於：

```
[10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
```

必須特別注意的是 stop 的那一個位置，是不會被包含進去的！

當然，range() 最多可以提供 3 個參數，第 3 個參數表示步伐的長度 (step)：

```
range(10, 20, 2)
```

上方程式碼所建立的序列相當於：

```
[10, 12, 14, 16, 18]
```

你可以發現序列中的數字彼此的差為 2。

AD

## 結語

在本篇文章中，我們學習了迴圈 (Loop) 的觀念，以及如何在 Python 中撰寫 for loop 與 while loop 的語法。此外，我們也學習到迴圈的好朋友「break」與「continue」的作用。在下一篇文章中，我們將會正式學習[「函式」(Function) 的概念](http://54.150.87.240/python-tutorial/python-function/)。
