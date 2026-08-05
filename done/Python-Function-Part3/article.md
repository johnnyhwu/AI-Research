# Python 中的函式 (Function) 觀念 (Part 3)

## 前言

在「Python 中的函式 (Function) 觀念 (Part 2)」中，我們介紹了 Python 函式的 Default Argument、Keyword Argument 與 Scope，也說明了 Local Variable (區域變數) 與 Global Variable (全域變數) 各自的生命週期。文章最後列出了 Scope 的四項重要性質：

- 在 Global Scope 中的程式碼，不可以存取 Local Scope 中的變數 (Local Variable)
- 在 Local Scope 中的程式碼，可以存取 Global Scope 中的變數 (Global Variable)
- 在 Local Scope 中的程式碼，不可以存取其他 Local Scope 中的變數 (Local Variable)
- 假設兩個變數處在不同的 Scope 中，這兩個變數可以使用相同的名字

這四句話單獨看有點抽象，實際踩到的時候卻很容易一頭霧水：明明變數就寫在那裡，為什麼電腦說它不存在？這篇文章就針對這四項性質逐一舉例說明，每一項都配上一段可以自己跑跑看的程式碼。

## 在 Global Scope 中的程式碼，不可以存取 Local Scope 中的變數 (Local Variable)

舉例來說，如果執行下方的程式碼：

```python
def say_hello():
    text = "hello"

say_hello()
print(text)
```

將會出現以下錯誤訊息：

![Python 直譯器顯示 NameError 的錯誤訊息畫面，指出 text 這個名稱尚未被定義。](img-001)
*表示「text」這個變數並沒有被宣告過*

這個錯誤訊息的意思是「text」這一個變數並沒有被宣告過，因此電腦根本不知道它是什麼。但是我們明明就有在 `say_hello()` 函式中定義它呀？！

原因在於 `say_hello()` 函式會形成一個 Local Scope，寫在這個 Local Scope 中的變數 (text) 就是 Local Variable。只有當我們在第四行呼叫 `say_hello()` 時，text 這個變數才會被建立；函式一執行完，屬於它的 Local Scope 連同裡面的變數就一起被消滅了。也就是說，當電腦執行到第五行的 `print(text)` 時，text 早就已經不存在，因此才會出現錯誤訊息。

## 在 Local Scope 中的程式碼，可以存取 Global Scope 中的變數 (Global Variable)

反過來的方向就是允許的。舉例來說，如果執行以下程式碼：

```python
def say_hello():
    print(text)

text = "hello"
say_hello()
```

將會輸出：

```text
hello
```

因為在呼叫 `say_hello()` 函式之前，我們已經先定義了「text」這一個變數。text 定義在函式外部，也就是 Global Scope 中，因此屬於 Global Variable，要等到整個程式都執行完畢時才會被消滅。所以當 `say_hello()` 在自己的 Local Scope 裡找不到 text 時，會再往外找到 Global Scope 中的 text，順利印出 "hello"。

## 在 Local Scope 中的程式碼，不可以存取其他 Local Scope 中的變數 (Local Variable)

舉例來說，如果執行以下程式碼：

```python
def say_hello1():
    text1 = "hello1"

def say_hello2():
    text2 = "hello2"
    print(text1)

say_hello2()
```

將出現以下錯誤訊息：

![Python 直譯器顯示 NameError 的錯誤訊息畫面，指出 text1 這個名稱尚未被定義。](img-002)
*text1 這個變數並沒有被定義過*

這個錯誤訊息的意思是，當電腦在執行 `say_hello2()` 函式時，發現「text1」變數並沒有被宣告過。然而，我們不是已經在 `say_hello1()` 函式中宣告過了嗎？

原因在於每一個函式所形成的 Local Scope 都是彼此獨立、互不影響的，也就是說在 `say_hello2()` 函式中，完全不知道 `say_hello1()` 函式裡發生了什麼事情。要注意的是，這裡的問題並不是「呼叫順序不對」，就算先呼叫 `say_hello1()` 再呼叫 `say_hello2()` 也一樣會錯，因為 `say_hello1()` 一結束，text1 就跟著消失了。

## 假設兩個變數處在不同的 Scope 中，這兩個變數可以使用相同的名字

既然「在 `say_hello2()` 函式中，完全不知道 `say_hello1()` 函式裡發生了什麼事情」，我們當然也可以在兩個函式 (兩個 Local Scope) 中使用相同的變數名稱，如下方程式碼所示：

```python
def say_hello1():
    text = "hello1"

def say_hello2():
    text = "hello2"

say_hello2()
```

`say_hello1()` 與 `say_hello2()` 兩個函式中的內容彼此不會影響，這兩個 text 從頭到尾就是兩個不同的變數，只是名字剛好一樣而已。這個性質在實務上其實幫了大忙：寫函式時不必為了避免撞名而把變數取成一長串怪名字，只要管好自己函式裡的命名就好。

## 結論

這篇文章把 Scope 的四項性質各配一段程式碼跑過一遍。抓住一個原則就不太會錯：Local Scope 只在函式執行的那段期間存在，而且只看得到自己和外層的 Global Scope，看不到隔壁函式的內部。前面那兩個 NameError，本質上都是同一件事的不同面貌。

下一篇文章將會介紹，如果電腦在執行 Python 程式時遇到非預期的狀況，除了中斷程式、丟出錯誤訊息之外，我們還可以怎麼處理這些情況。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "表示「text」這個變數並沒有被宣告過",
    "why_used": "佐證「在 Global Scope 中無法存取 Local Variable」這一節，呈現在函式外部存取函式內變數時實際跳出的錯誤訊息。",
    "agent_match_hint": "一張程式執行結果的截圖，內容是 Python 的 NameError 錯誤訊息，提到 text 未被定義。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "text1 這個變數並沒有被定義過",
    "why_used": "佐證「一個 Local Scope 無法存取另一個 Local Scope 的變數」這一節，呈現 say_hello2() 讀取 say_hello1() 內變數時跳出的錯誤訊息。",
    "agent_match_hint": "一張程式執行結果的截圖，內容是 Python 的 NameError 錯誤訊息，提到 text1 未被定義。"
  }
]
```
