# Python 中的迴圈 (Loop) 觀念

## 前言

前一篇「Python 中的 IF、ELIF 與 ELSE」談的是流程控制：用 `if`、`elif`、`else` 在程式中加入「條件的判斷」，再依照判斷結果執行對應的程式碼。這篇文章把「條件」的概念再往前推一步，講程式裡另一個天天都會用到的東西：迴圈 (Loop)。

讀完之後，你會知道迴圈到底在重複什麼、Python 裡 `while` 與 `for` 兩種寫法各自適合什麼場合、`break` 與 `continue` 分別怎麼改變迴圈的流向，以及 `range()` 的三個參數要怎麼用。

## 迴圈 (Loop) 是什麼

![流程控制示意圖，標示出一段流程控制由「條件」與條件成立後要執行的「任務」兩個部分組成。](img-001)
*流程控制就是由「條件」與「條件完成後的任務」所組成*

上面這張圖在前一篇文章中出現過。所謂的「流程控制」，就是由「條件」與條件成立時要執行的「任務」所組成。電腦執行這段程式時，會先判斷條件，依照結果執行相對應的程式碼，然後整個程式就結束了。

那如果我們希望電腦「重複」進行條件的判斷呢？如下圖所示，執行完相對應的程式碼後，程式並沒有結束，而是「重新」回到條件的判斷，形成一個繞回去的環。

![流程示意圖，執行完任務後箭頭沒有結束，而是繞回到條件判斷，形成一個循環。](img-002)
*執行完相對應的程式碼後，再回到條件的判斷*

你注意到了嗎？「重複」、「重新」或是「再一次」指的就是「迴圈」(Loop)。在程式的世界中，迴圈的概念相當常見，只要我們希望『符合某一條件，就「重複」執行某段程式碼』，就會用迴圈來實作。

## Python 中的迴圈語法

在 Python 與大多數的程式語言中，迴圈的語法通常透過兩種關鍵字來實現，分別是「**while**」與「**for**」。兩種關鍵字寫出來的迴圈，就稱為「while loop」與「for loop」。

- `for` → for loop
- `while` → while loop

其中，while loop 的觀念就是我們上面對迴圈的介紹：條件成立就繼續跑。所以先從 while loop 的語法開始。

## Python 中的 while loop

我們直接觀察以下的程式碼：

```python
num = 0

while num < 3:
    print('number: ' + str(num))
    num = num + 1
```

在程式碼中，我們使用了 `while` 關鍵字，並在關鍵字後方加上**條件與冒號**，滿足條件時要執行的程式碼則是**換行並縮排**。這個縮排不是排版好看而已，Python 是靠縮排來判斷哪幾行屬於迴圈內部的。

下方為此程式的輸出，我們可以發現迴圈中的程式碼總共被執行了三次。

```text
number: 0 
number: 1 
number: 2
```

這裡有個很關鍵的順序：一定是「先」確定條件成立，「後」執行迴圈內部的程式碼。把上面這段程式的執行流程攤開來看會更清楚：

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

從上面的執行流程可以清楚觀察到：「迴圈條件」被判斷了 **4** 次，「迴圈內部的程式碼」則只執行了 **3** 次。條件多判斷的那一次，就是用來決定要不要離開迴圈的。

順帶一提，這也是為什麼 `num = num + 1` 這行不能忘記寫。少了它，num 永遠是 0，條件永遠成立，程式就會卡在一個停不下來的無窮迴圈裡。

接著再看一個範例，熟悉 while loop 的寫法。下方的程式碼用 while loop 計算 1 到 100 的總和：

```python
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

由此可以清楚觀察到 while loop 由 1 加到 100 的過程。

最後一行的 `print()` 函式也值得補充一下。除了透過「字串加法」把字串與變數接起來之外，也可以用 **f string** 的方式把變數直接插進字串裡：

```python
# 字串加法：
print('sum: ' + str(sum))

# f string
print(f'sum: {sum}')
```

使用 f string 時，要在字串前方加上 `f`，並在需要插入變數的地方用 `{}` 把變數包起來。變數多的時候，f string 會比一路 `+` 下去好讀很多，也省掉呼叫 `str()` 轉型的麻煩。

## break 與 continue

講到迴圈，`break` 與 `continue` 這兩個角色一定會被提到。它們的共通點是都會打斷迴圈原本的節奏，差別在於一個是直接走人，一個是跳過這一輪。

- **break：立即離開迴圈**

當迴圈的條件成立後，電腦會執行迴圈內部的程式碼。我們可以在迴圈內加上 `break`，當電腦執行到這一行時，就會直接離開迴圈。

```python
sum = 0
num = 1

while num <= 100:
    sum += num
    num += 1
    break

print(f'sum: {sum}')
```

在上述的程式碼中，最終的 sum 會是 1。因為當電腦第一次進入迴圈，遇到 `break` 就馬上離開了。像這樣把 `break` 直接寫在迴圈內部，等於讓迴圈失去「重複」執行的意義。實務上，我們通常會搭配 `if` 進行判斷，條件滿足才 `break`。

```python
sum = 0
num = 1

while num <= 100:
    sum += num
    num += 1

    if sum > 1000:
        break

print(f'sum: {sum}')
```

在上面這段程式碼中，我們判斷如果「sum > 1000」才執行 `break`。

- **continue：直接回到迴圈條件判斷**

同樣是在迴圈內部，`continue` 的行為則是跳過這一輪剩下的程式碼，直接回到迴圈的條件重新判斷。

```python
sum = 0
num = 1

while num <= 100:
    sum += num
    num += 1
    print(f'sum: {sum}')
```

在上面這段程式碼中，每一次迴圈的最後都會把 sum 的數值顯示出來，也就是會印出一百行。但如果我們希望只有當 sum > 4000 時才顯示，就可以用 `continue` 忽略迴圈內剩下的程式碼，回到迴圈條件判斷的地方：

```python
while num <= 100:
    sum += num
    num += 1

    if sum < 4000:
        continue

    print(f'sum: {sum}')
```

只要 sum < 4000，電腦執行到 `continue` 這行就會馬上結束這一輪，回到迴圈條件判斷的階段，後面的 `print()` 自然就跳過了。

這邊要特別注意的是，`break` 與 `continue` 只能寫在**迴圈內部**，也就是只能用在 while loop 與 for loop 當中。

## Python 中的 for loop

了解 while loop 之後，接著來看 Python 中的 for loop。兩者的差別在於「誰決定迴圈跑幾次」：while loop 是以「條件」來決定目前的迴圈是否要繼續執行；for loop 則是事先用「次數」決定好要跑幾輪。

![流程示意圖，for loop 依照事先決定好的次數逐次執行迴圈內的程式碼。](img-003)
*for loop 是以「次數」決定總共執行幾次迴圈*

在 Python 中，我們經常透過 `range()` 函式來指定 for loop 要執行的次數。

```python
for num in range(10):
    print('Hello World')
```

上方程式碼為 Python 中基本的 for loop 範例。Python 中 for loop 的語法通常由下列元素組成：

- `for` 關鍵字
- 變數名稱 → 上方使用 num
- `in` 關鍵字
- 序列 (Sequence) 或可迭代的物件 (Iterable Object) → 上方使用 range(10)

「序列 (Sequence) 或可迭代的物件 (Iterable Object)」這個名詞看起來實在有點嚇人，但對初學者來說，可以先把它想成「一連串的物件」。下面這些都算是「一連串的物件」：

- [1, 2, 3, 4, 5, 6, 7, 8]
- ["apple", "orange", "132", "456", "789"]
- [-1, -6, 65, 32]
- [2.5, 3.0, 5.2, 3.1]

因此，`range(10)` 可以先把它想成 **[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]（注意是 0 到 9，不是 1 到 10）**，而 `for num in range(10)` 就相當於 `for num in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]`。按照字面上的意思，每一次的迴圈中 num 都會「依序」對應到這串數字中的每一個，所以 `range(10)` 就等於指定迴圈總共執行 10 次。

```python
for num in range(10):
    print(f'num: {num}')
```

上方程式碼直接把 num 每一次對應到的數字顯示出來，跑起來會依序印出 num: 0 到 num: 9。

在 for loop 中一樣可以使用 `break` 與 `continue`：

```python
for num in range(10):

    if num == 5:
        break

    print(f'num: {num}')
```

在上方程式碼中，num 為 5 時就直接離開迴圈，所以只會印到 num: 4。

接著再看一個範例，熟悉 for loop 的寫法。下方的程式碼用 for loop 計算 1 到 100 的總和，跟前面 while loop 的版本比起來短了不少，因為「跑幾次」這件事已經交給 `range()` 處理了：

```python
sum = 0

for num in range(101):
    sum += num

print(f'sum: {sum}')
```

## range() 的進階用法

上文中我們已經看過 `range()` 的基礎用法。實際上，`range()` 函式可以接受 3 個參數，分別表示：

- 起始位置 (start)
- 終止位置 (stop)
- 步伐長度 (step)

前面的例子都只提供一個參數給 `range()`，其實我們提供的就是 stop。

```python
range(10)
```

上方的程式碼中，我們指定 `range()` 的 stop 參數為 10，相當於：

```python
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
```

如果提供 2 個參數給 `range()`，表示的則是 start 與 stop：

```python
range(10, 20)
```

上方程式碼表示 start 為 10，stop 為 20，相當於：

```python
[10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
```

必須特別注意的是，stop 的那一個位置是不會被包含進去的！這也是為什麼前面要算 1 到 100 的總和時，寫的是 `range(101)` 而不是 `range(100)`。

當然，`range()` 最多可以提供 3 個參數，第 3 個參數表示步伐的長度 (step)：

```python
range(10, 20, 2)
```

上方程式碼所建立的序列相當於：

```python
[10, 12, 14, 16, 18]
```

你可以發現序列中的數字彼此的差為 2。

## 結論

這篇文章把迴圈 (Loop) 的觀念走過一遍：迴圈就是讓程式在條件成立時重複執行同一段程式碼。Python 裡有 while loop 與 for loop 兩種寫法，前者由「條件」決定要不要繼續，後者由「次數」決定總共跑幾輪。

我們也認識了迴圈的兩個好朋友 `break` 與 `continue`：`break` 直接離開迴圈，`continue` 則是跳過這一輪回到條件判斷。最後補上 `range()` 的 start、stop、step 三個參數，for loop 的次數就能控制得很細。下一篇文章，我們會正式進入「函式」(Function) 的概念。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "流程控制就是由「條件」與「條件完成後的任務」所組成",
    "why_used": "沿用前一篇流程控制的圖，先幫讀者複習「條件 + 任務」的結構，再從這個結構延伸出迴圈的概念。",
    "agent_match_hint": "一張流程控制拆解示意圖，標示出「條件」與條件成立後要執行的「任務」兩個區塊。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "執行完相對應的程式碼後，再回到條件的判斷",
    "why_used": "用來說明迴圈與一般流程控制的差別：任務執行完後箭頭不是結束，而是繞回條件判斷。",
    "agent_match_hint": "一張流程圖，任務方塊執行完後有一條箭頭往回接到條件判斷，形成一個明顯的循環。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "for loop 是以「次數」決定總共執行幾次迴圈",
    "why_used": "對照 while loop 由條件決定的作法，說明 for loop 是事先由次數決定要跑幾輪。",
    "agent_match_hint": "一張 for loop 流程示意圖，強調依照預先決定好的次數逐次執行迴圈內的程式碼。"
  }
]
```
