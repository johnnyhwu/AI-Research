# Python 中的 IF、ELIF 與 ELSE

## 前言

本篇是 Python 程式語言入門教學的第 6 篇文章。在前一篇「流程控制以及布林 (Boolean) 資料類型」中，我們談過流程控制的概念，也認識了布林值。這篇文章就接著把概念落到實際語法上：在 Python 裡，流程控制靠的是 `if`、`elif`、`else` 這三個關鍵字。

讀完之後，你會知道一段流程控制是由哪些零件組成的、這三個關鍵字各自負責什麼，以及一個很容易踩到的雷：連續的 `if` 和連續的 `elif`，執行結果其實完全不一樣。

## 流程控制的組成

![一張生活化的流程圖，從「Is raining ?」開始分支，依序判斷是否下雨、有沒有帶傘，並指向不同的行動。](img-001)
*生活中的流程圖*

在前一篇文章中，我們了解到所謂的「流程控制」就是流程圖中的「Is raining ?」或是「Have umbrella ?」這種判斷點。而一段流程控制通常由兩部分組成：「條件」與「條件成立時的任務」。

以「Is raining ?」為例，「Is raining」本身就是條件；如果這個條件滿足，會沿著 Yes 的方向走，來到「Have umbrella ?」。此時，「Have umbrella ?」就是「條件成立時的任務」。同樣的道理，「Have umbrella ?」自己也是一個條件，滿足時會沿著 Yes 走到「Wait a while.」，那就是它成立時要做的事。

![示意圖，將流程控制拆解成「條件」與「條件成立時執行的任務」兩個組成部分。](img-002)
*流程控制就是由「條件」與「條件成立時執行的任務」所組成*

簡單來說，程式裡的「流程控制」就是這兩個零件：「條件」與「條件成立時的任務」。

在 Python 中，「條件」指的是最終可以變成一個布林值 (Boolean Value) 的 Expression。以下每一個 Expression 都可以拿來當流程控制的條件，因為它們算出來的結果都是 `True` 或 `False`：

```python
1 == 2
10 <= 20
20-1 != 19
'apple' == 'apple'
```

## Python 中流程控制的語法

了解流程控制的組成後，接著看 Python 實際提供的三個關鍵字：

- **if**
- **elif**
- **else**

Python 就是靠這三個關鍵字寫出流程控制，以下一一介紹。

## IF 語法

IF 語法是流程控制的第一步，要在程式中寫流程控制，第一個用到的一定是 `if`。直接看以下的程式碼片段：

```python
if 2+3 == 5:
    print('YES')
```

這段程式碼的意思是：如果 2+3 是 5，就印出 `YES`。對照前面的拆解，「2 + 3 == 5」是條件，「print('YES')」則是條件成立時的任務。

聰明的你一定發現了，「2 + 3」的結果本來就是 5，所以「2 + 3 == 5」這個 Expression 算出來一定是 `True`。也就是說，上面那段程式碼等同於：

```python
if True:
    print('YES')
```

當程式執行到這個流程控制時，因為條件的結果一定是 `True`，「print('YES')」一定會被執行。

當然，把條件寫死成 `True` 在實務上沒什麼意義。我們經常會在條件中放入變數，讓判斷更有彈性：

```python
if name == 'Alice':
    print('Hi, ' + name)
```

這段程式碼所對應的流程圖為：

![一張流程圖，以「name == 'Alice'」作為判斷條件，條件成立時執行印出問候語的動作，不成立時直接往下走。](img-003)
*上述程式碼所對應到的流程圖 [source: Automate the Boring Stuff with Python]*

了解 IF 語法怎麼寫之後，有兩個小細節要特別注意，也是初學者最常噴錯誤的地方：

- 「條件」後方要加上「冒號」
- 「條件成立時的任務」要縮排

## ELIF 語法

上面的例子中，我們只判斷了 name 這個變數是不是等於 `'Alice'`。但如果想判斷更多不同的條件呢？例如 name 是不是等於 `'Johnny'`？這時候就輪到 ELSE IF 語法登場。直接看程式碼：

```python
name = 'Johnny'

if name == 'Alice':
    print('Hi, '+ name)
elif name == 'Johnny':
    print('How are you ' + name)
```

可以發現 Python 用的關鍵字是 `elif`，這就是它的 ELSE IF 寫法。針對 name 這個變數，我們用了 2 種不同的條件 (Alice 與 Johnny)，電腦會從第一個條件開始依序往下判斷，只要遇到滿足的條件，就執行對應的內容。在這個例子中，被執行的是「print('How are you ' + name)」。

這裡的眉角是「只要遇到第一個滿足的條件就停下來」。多看幾個例子會更清楚。

以下這段程式碼，你覺得輸出會是什麼呢？

```python
name = 'Alice'

if name == 'Alice':
    print('Hi, '+ name)
elif name == 'Alice':
    print('How are you ' + name)
```

輸出會是「Hi, Alice」。如同前面所說，當電腦遇到一連串的 IF 與 ELSE IF 語法時，會從第一個條件依序往下判斷，只要遇到滿足的條件就執行對應的程式碼，後面的 ELSE IF 連判斷都不會判斷了。

那如果改成下面這樣呢？

```python
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

原因在於這兩個條件都是用 IF 語法寫的，所以兩個條件「完全獨立」，不管第一個條件成不成立，電腦都會再去判斷第二個。這也是 `if` 接 `elif` 和 `if` 接 `if` 最關鍵的差別：前者是一組互斥的選擇題，後者是兩題各自作答。

了解 ELSE IF 語法怎麼寫之後，一樣有兩個小細節要注意：

- 「條件」後方要加上「冒號」
- 「條件成立時的任務」要縮排

## ELSE 語法

我們已經知道怎麼用 IF 與 ELSE IF 寫出「條件」以及「條件成立時對應的任務」。那如果「所有條件」都不滿足，卻還是想執行一些程式碼呢？這時候就用 ELSE 語法。

舉例來說：

```python
name = 'Johnny'

if name == 'Alice':
    print('Hi, '+ name)
elif name == 'Tim':
    print('How are you ' + name)
else:
    print('What is your name ?')
```

上述程式碼的執行結果為：「What is your name ?」。因為當所有的 IF 與 ELSE IF 條件都不成立時，電腦就會執行 ELSE 裡的程式碼。也因此，ELSE 語法是不需要指定條件的，它扮演的是「以上皆非」的那條路。

ELSE 語法要注意的細節同樣有兩個：

- `else` 後方要加上「冒號」（因為沒有條件，冒號直接接在關鍵字後面）
- 「條件不成立時要執行的任務」一樣要縮排

## 結論

這篇文章把 Python 的流程控制語法走過一遍：`if` 負責第一個判斷，`elif` 接續判斷其他條件，`else` 處理所有條件都不成立的情況。同時也要記得，一連串的 `if`/`elif` 只會執行第一個成立的分支，而連續好幾個獨立的 `if` 則會每一個都判斷。

熟悉這三個關鍵字，程式就能依照不同狀況走不同的路，而不是只能從頭執行到尾。下一篇文章，我們會接著介紹程式中 Loop 的概念。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "生活中的流程圖",
    "why_used": "用生活中的下雨、帶傘情境當開場，讓讀者先直覺理解「流程控制」在流程圖上長什麼樣子。",
    "agent_match_hint": "一張生活化流程圖，含有「Is raining ?」、「Have umbrella ?」等判斷方塊與 Yes／No 分支箭頭。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "流程控制就是由「條件」與「條件成立時執行的任務」所組成",
    "why_used": "支撐「流程控制由條件與條件成立時的任務兩部分組成」這個核心拆解，把抽象說明變成一眼可見的結構圖。",
    "agent_match_hint": "一張拆解示意圖，把一段流程控制標示成「條件」與「條件成立時執行的任務」兩個區塊。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "上述程式碼所對應到的流程圖 [source: Automate the Boring Stuff with Python]",
    "why_used": "把前面 name == 'Alice' 的 if 程式碼對應回流程圖，讓讀者看見程式碼與流程圖之間的對照關係。",
    "agent_match_hint": "一張流程圖，中間是菱形判斷方塊「name == 'Alice'」，True 分支接到印出問候語的動作方塊。"
  }
]
```
