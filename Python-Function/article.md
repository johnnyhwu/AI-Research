# Python 中的函式 (Function) 觀念 (Part 1)

## 前言

![Python 中的函式 (Function) 觀念系列文章的題圖。](img-001)
*Python 中的函式 (Function) 觀念 文章題圖 [source: Pixabay]*

在前幾篇的 Python 教學文章中，我們已經用過「函式」(Function) 這個詞，也實際呼叫過幾個 Python 的內建函式 (Built-in Function)，像是 `print()`、`len()` 與 `input()`。不過到目前為止，我們都只是「使用別人寫好的函式」。

這篇文章要把這件事翻到另一面：函式到底是什麼、為什麼要有函式，以及怎麼定義自己的函式。內容會從最基本的函式寫法開始，接著談帶有參數的函式、帶有回傳值的函式，最後補上一個常常讓初學者卡住的觀念 —— NoneType 與 None。

說白了，函式就是把一段「會重複用到、或是有明確任務」的程式碼包成一包，給它一個名字，之後想用的時候喊一聲名字就好，不必把同樣的程式碼再抄一次。

## Python 中的函式 (Function)

先看以下這段程式碼：

```python
def first_function():
    print('Hello World')

first_function()
```

這段程式碼做了兩件事：定義一個名為 `first_function` 的函式，然後呼叫它。我們把它拆開來看組成元素。

第 1 行的 `def` 是關鍵字，表示我們正在「定義」一個函式。跟在 `def` 之後的 `first_function` 就是這個函式的「名稱」，之後要呼叫它就靠這個名字。名稱後面還要再加上一組「括號」，括號的用途等一下會解釋。

寫好 `def`、函式名稱與括號之後，還得說明函式內部要執行哪些程式碼。這裡的語法和 for loop、while loop 一樣：行尾加上一個「冒號」，函式內部的程式碼則必須「縮排」。縮排的這幾行就是函式的內容，只有在函式被呼叫時才會執行。以上面的例子來說，函式內部就只有 `print('Hello World')` 這一行。

程式碼區塊的最後一行 `first_function()` 就是在「呼叫」這個函式。呼叫的方式很簡單，寫出「函式名稱」加上「括號」即可。

那括號到底是做什麼的？括號裡可以提供一些參數給這個函式。例如我們用內建的 `print()` 函式時，就是把想顯示的字串放進括號中：

```python
print('Hello World')
```

至於執行的順序，可以這樣理解：當電腦執行到「呼叫函式」那一行時，會先跳到該函式內部的第一行開始執行；等函式裡的程式碼全部執行完，再跳回剛剛呼叫的地方，繼續往下執行後面的程式碼。

舉例來說：

```python
def first_function():
    print('Hello World')

first_function() #1
print('執行完 1 次') #2
first_function() #3
print('執行完 2 次') #4
```

第一次呼叫 `first_function` (#1) 之後，電腦會跳進 `first_function` 執行 `print('Hello World')`，執行完函式內所有程式碼後，再回到 #1 的位置，繼續執行 #2、#3、#4。所以最終的輸出為：

```
Hello World
執行完 1 次
Hello World
執行完 2 次
```

注意 `Hello World` 出現了兩次，但我們只寫了一次 `print('Hello World')`。這就是函式最直接的好處：同一段邏輯只寫一次，要用幾次就呼叫幾次。

## Python 中帶有參數的函式

一路用到現在，你應該已經很習慣透過 `print()` 顯示想要的字串。我們放在括號中的那個字串稱為 **Argument**，它會在呼叫函式的當下被傳進函式裡面。

自己定義的函式當然也能接收 Argument：

```python
def second_function(name):
    print(f'Hello, {name}')

second_function('Johnny')
```

在函式名稱 `second_function` 後方的括號中，我們放入一個變數 `name`，這個變數稱為 **Parameter**，用來規定這個函式可以接受什麼東西傳進來。因此呼叫時我傳入字串 `'Johnny'`，顯示結果為：

```
Hello, Johnny
```

看到這裡，也許你已經被 Parameter 與 Argument 搞得暈頭轉向。其實不必太糾結這兩個專有名詞，只要記得它們分別出現在哪個階段：

- **Parameter**：在「定義函式」階段，規定這個函式能夠接受哪些東西。例如上方程式碼中的 `name`。
- **Argument**：在「呼叫函式」階段，實際上傳進函式的東西。例如上方程式碼中的 `'Johnny'`。

有一件事要特別注意：函式所接受的 Parameter 在函式內部可以當作一般變數使用，但函式執行完畢之後，這個變數就會被消滅，所以在函式外面是拿不到它的。

舉例來說，我們在 `second_function('Johnny')` 的下方加上一行 `print(name)`：

```python
def second_function(name):
    print(f'Hello, {name}')

second_function('Johnny')
print(name)
```

執行的結果為：

```
NameError: name 'name' is not defined
```

原因就在於 `name` 這個變數在 `second_function` 執行完畢之後就被消滅了，因此無法在函式的外面使用它。

## Python 中帶有回傳值的函式

除了 `print()` 之外，我們也很常用 `len()` 函式取得字串的長度：

```python
name = 'Johnny'
length = len(name)
print(length)
```

這段程式碼會顯示 `name` 這個字串的長度。這裡的關鍵是：`len()` 被呼叫之後會「回傳」一個整數，我們才有辦法把它存進 `length` 變數中。這和 `print()` 不一樣 —— `print()` 只是把東西顯示在畫面上，並沒有交還什麼可以拿去用的結果。

如果希望自己寫的函式在執行完之後，也能回傳數值到原來呼叫的地方，就必須使用 `return` 關鍵字：

```python
def third_function(name):
    return f'Hello, {name}'

output = third_function('Johnny')
print(output)
```

在 `third_function` 中，我們透過 `return` 回傳一個字串。因此 `third_function('Johnny')` 執行完的結果會是 `Hello, Johnny`，並存進 `output` 變數中。

另外要注意的是，當函式執行到 `return` 時，就代表這個函式結束了，`return` 之後的程式碼不會被執行：

```python
def fourth_function(name):
    return f'Hello, {name}'
    print('under return keyword')

output = fourth_function('Johnny')
print(output)
```

這段程式碼的執行結果會與前一段完全相同。因為在 `fourth_function` 中，`print('under return keyword')` 位在 `return` 之後，所以永遠不會被執行到。

## Python 中的 NoneType 與 None

在先前介紹 Python 變數與資料類型的文章中，我們提過 Python 的基本資料型態，例如 Integer、String 與 Floating-Point Number。

今天要再介紹一種新的 Data Type，稱為 **NoneType**。NoneType 很特別，它只有唯一一個數值，就是 `None`。一個 Type 裡頭只包含 1 個或 2 個數值其實並不奇怪，我們之前學過的 Boolean Type 裡頭就只有 `True` 與 `False` 兩種數值。

那為什麼要多學 NoneType 這種看起來有點神奇的型態？原因和函式的回傳值有關。

在 Python 中，每一個函式都會有回傳值，也就是每次呼叫函式之後都一定會得到一個數值。呼叫 `third_function()`、`fourth_function()` 與 `len()` 都可以得到一個數值，這很直覺。但問題是，如果函式要有回傳值就必須寫 `return ...`，而我們並不是每次都會寫這一行 —— 像本文最開頭的 `first_function()` 就沒有。

Python 的處理方式是：只要我們定義的函式裡沒有 `return ...`，Python 就會自動幫我們補上一個 `return None`。回頭看看 `first_function()`：

```python
def first_function():
    print('Hello World')

output = first_function()

if(output == None):
    print(f"output is None")
```

我們把 `first_function()` 的執行結果存到 `output` 變數中，再判斷 `output` 是不是等於 `None`。最後的輸出為：

```
Hello World
output is None
```

由此可以確認：即使 `first_function()` 中沒有回傳任何數值，也就是沒有寫 `return ...`，Python 仍然會自動補上 `return None`，使得函式最終的回傳值是 `None`。這也是為什麼把 `print()` 的結果存進變數再印出來，看到的會是 `None` 而不是剛剛顯示的那串字。

## 結論

這篇文章從最基本的函式定義開始，一路走到帶有參數的函式、帶有回傳值的函式，並且說明了 Python 中 NoneType 與 None 的觀念。掌握這幾點之後，你已經可以把重複的程式碼包成函式，讓程式碼變得更好讀、也更好維護。

不過還有一個問題還沒回答：函式裡面的變數到底「活」在哪個範圍？下一篇文章 (Part 2) 會介紹函式更深入的觀念，也就是函式的範疇 (Function Scope)。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Python 中的函式 (Function) 觀念 文章題圖 [source: Pixabay]",
    "why_used": "原文的文章題圖，放在前言開頭作為整篇文章的視覺開場，沒有承擔任何技術說明的功能。",
    "agent_match_hint": "一張來自 Pixabay 的通用示意／裝飾用題圖，非程式碼截圖，也非流程示意圖。"
  }
]
```
