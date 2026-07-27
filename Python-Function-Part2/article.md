# Python 中的函式 (Function) 觀念 (Part 2)

## 前言

在「Python 中的函式 (Function) 觀念 (Part 1)」中，我們從最基本的函式開始，一路看到帶有參數的函式、帶有回傳值的函式，也順帶說明了 Python 中 `None` 與 `NoneType` 的概念。

這篇文章接著往下講三個實務上天天會用到的觀念：Default Argument (預設值參數)、Keyword Argument (關鍵字參數)，以及 Scope (範圍)。前兩個決定了「呼叫函式時可以怎麼傳參數」，最後一個則決定了「函式裡建立的變數活多久、誰看得到它」。

## Python Function 的 Default Argument

先用一個簡單的例子回顧上一篇的內容：

```python
def say_hello(name):
    print(f'hello, {name}')
```

上方程式碼定義了一個 `say_hello` 函式，這個函式接受一個參數。呼叫時傳入一個字串：

```python
say_hello('Tom')
```

字串 "Tom" 就會對應到 `name` 這個參數。

問題來了，假如呼叫 `say_hello` 時什麼都不傳：

```python
say_hello()
```

電腦會顯示錯誤訊息：

```text
TypeError: say_hello() missing 1 required positional argument: 'name'
```

原因很單純：我們在定義 `say_hello` 時就講明了它會接受一個參數，呼叫時卻沒有傳任何東西進去，電腦不知道要把 `name` 替換成什麼數值，只好報錯。

順著這個想法，如果希望呼叫 `say_hello` 時就算沒傳東西也不要跳錯誤，我們可以替參數 `name` 加上一個**預設值**：

```python
def say_hello(name="Johnny"):
    print(f'hello, {name}')

say_hello()
```

這樣一來，就算呼叫時沒傳任何東西，電腦也知道要把 `name` 當成 "Johnny" 來用。當然，如果有傳入數值，傳入的數值就會蓋掉預設值。

說白了，「Default Argument」指的就是帶有「預設值」的參數。

## 混用「有」預設值與「沒有」預設值的參數

定義函式時，如果參數有些有預設值、有些沒有，一定要確保：**沒有預設值的參數要放在左邊**。

舉例來說：

```python
def say_hello(age, name="Johnny"):
    print(f'I am {name}')
    print(f'I am {age} years old')
```

`say_hello` 接受 `age` (沒有預設值) 與 `name` (有預設值) 兩個參數，`age` 就必須寫在 `name` 的左邊。如果放錯邊：

```python
def say_hello(name="Johnny", age):
    print(f'I am {name}')
    print(f'I am {age} years old')
```

程式在定義的當下就會出錯，連呼叫都輪不到：

```text
SyntaxError: non-default argument follows default argument
```

## Python Function 的 Keyword Argument

呼叫函式時，我們傳入的資訊是靠「位置」對應到函式的參數的。

以上面定義的 `say_hello` 函式為例：

```python
def say_hello(age, name="Johnny"):
    print(f'I am {name}')
    print(f'I am {age} years old')
```

因為 `name` 有預設值，呼叫時可以傳一個參數，也可以傳兩個。如果只傳一個：

```python
say_hello(100)
```

這個參數 (100) 會對應到 `say_hello` 的 `age` 參數，`name` 則沿用預設值 "Johnny"。當我們傳入兩個參數：

```python
say_hello(100, Tom)
```

傳入的**第一個**參數 (100) 對應到 `say_hello` 的**第一個**參數 `age`；傳入的**第二個**參數 (Tom) 對應到**第二個**參數 `name`。順序一旦搞混，值就會跑到錯的參數上。

除了靠「位置」對應，我們也可以直接用「關鍵字」指定要塞給哪一個參數：

```python
say_hello(age=100, name="Tom")
```

用關鍵字指定之後，傳入參數的順序就可以任意變動，寫成這樣結果完全一樣：

```python
say_hello(name="Tom", age=100)
```

參數一多的時候，這種寫法的可讀性會好非常多，光看呼叫的那一行就知道每個數值是幹嘛的，不用回頭去翻函式的定義。

## print( ) 函式的 Keyword Argument

Keyword Argument 不是自己寫的函式才有，我們天天在用的 `print()` 其實也吃好幾個參數。舉例來說，`print()` 顯示完一段字串後，預設會在結尾補上一個「換行符號」，所以下一個 `print()` 印出來的東西會跑到下一行：

```python
print('Hello')
print('Johnny')
```

執行後的結果，Hello 在第一行、Johnny 在第二行：

```text
Hello
Johnny
```

如果希望 Johnny 不要換行、直接接在 Hello 後面，可以透過 `end` 這個 Keyword Argument 指定要附加在字串最後面的字元。

例如，在 Hello 字串的最後方不要附加任何字元：

```python
print('Hello', end="")
print('Johnny')
```

此時顯示的結果為：

```text
HelloJohnny
```

或者，在 Hello 字串的最後方附加「一個空格」：

```python
print('Hello', end=" ")
print('Johnny')
```

此時顯示的結果為：

```text
Hello Johnny
```

換句話說，平常看到的換行只是 `end` 的預設值剛好是換行符號而已，不是 `print()` 寫死的行為。

## Python 中的 Scope 觀念

在上一篇文章中我們提過，如果在函式「外部」存取函式「內部」的變數，電腦會跳出錯誤訊息。舉例來說：

```python
def say_hello(age, name="Johnny"):
    print(f'I am {name}')
    print(f'I am {age} years old')

print(age)
```

```text
NameError: name 'age' is not defined
```

因為 `age` 這個變數只存在於 `say_hello` 函式內部，所以在函式外部存取不到。一個函式會有自己的「範圍」、自己的「界線」，這就是程式語言中的 **Scope** 觀念。

## Local Scope 與 Global Scope

Scope 可以分為 Local Scope 與 Global Scope：函式內部會形成一個 Local Scope，函式外部則屬於 Global Scope。在 Local Scope 中建立的變數稱為 **Local Variable (區域變數)**；在 Global Scope 中建立的變數稱為 **Global Variable (全域變數)**。一個變數只能擁有一個身份，不是 Local Variable 就是 Global Variable，不可能兩者兼具。

```python
a = 5
b = 10

def example():
    c = 15
    d = 20

e = 25
```

以上述程式碼為例，變數 a、b 與 e 都在 Global Scope 中，屬於 Global Variable；變數 c 與 d 寫在函式裡，在 Local Scope 中，屬於 Local Variable。

相信聰明的你已經發現：函式內部的變數就是 Local Variable，函式外部的變數就是 Global Variable。一個程式可以有很多個 Local Scope (有幾個函式就可能有幾個)，但是只會有一個 Global Scope。

## Python 中變數的生命週期

知道變數分成 Local Variable 與 Global Variable 之後，接著要看的是這兩種變數各自「活多久」。

當一個**「函式」**被執行時，屬於這個函式的 Local Scope 也會被建立，函式中所建立的變數都會存放在這個 Local Scope 裡。當函式執行結束，這個 Local Scope 隨之被消滅，存放在裡面的區域變數當然也跟著消失。這也解釋了為什麼前面 `print(age)` 會拿不到東西：函式跑完，`age` 就不存在了。

當一個完整的**「程式」** (.ipynb 或 .py) 開始執行時，屬於這個程式的 Global Scope 也會被建立，程式中所建立的變數都會存放在這個 Global Scope 裡。當程式執行結束，這個 Global Scope 隨之被消滅，存放在裡面的全域變數也會跟著消失。

## Python 中 Scope 的重要性質

了解 Local Scope 與 Global Scope 之後，可以整理出 Scope 的四項重要性質：

- 在 Global Scope 中的程式碼，不可以存取 Local Scope 中的變數 (Local Variable)
- 在 Local Scope 中的程式碼，可以存取 Global Scope 中的變數 (Global Variable)
- 在 Local Scope 中的程式碼，不可以存取其他 Local Scope 中的變數 (Local Variable)
- 假設兩個變數處在不同的 Scope 中，這兩個變數可以使用相同的名字

## 結論

這篇文章介紹了 Python 函式中的 Default Argument 與 Keyword Argument，讓我們在定義與呼叫函式時更有彈性；也說明了 Scope 的概念，以及 Local Variable (區域變數) 與 Global Variable (全域變數) 各自的生命週期。

最後列出的四項 Scope 性質，是理解「變數為什麼有時候讀得到、有時候讀不到」的關鍵。下一篇文章 (Python 中的函式 (Function) 觀念 Part 3) 會針對這四項性質逐一說明它們的意義。

```figure-map
[]
```
