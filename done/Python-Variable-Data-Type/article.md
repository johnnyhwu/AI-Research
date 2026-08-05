# Python 中的變數與資料類型

## 前言

本篇是 Python 程式語言入門教學的第 3 篇文章。前一篇我們用 Python 程式碼實作了生活中的數學運算，知道一段 Expression 可以被算成一個結果。這篇要補上兩個更基礎、也更常用的觀念：Python 中的「資料類型」(Data Type) 與「變數」(Variable)。

這兩件事說白了就是：資料類型決定「這個值是什麼東西、能拿來做什麼運算」，變數則決定「這個值之後還能不能被拿出來用」。搞懂它們之後，程式才有辦法從一行算式長成一支真正會做事的程式。

![Python 變數觀念的標題示意圖，畫面上是 Python 與 Variable 的主題圖像。](img-001)
*Python 中 Variable 的觀念*

## Python 中的資料類型

![Expression 的組成示意圖，顯示一段算式由 Value 與 Operator 兩種元素構成。](img-002)
*Expression 就是由 Value 與 Operator 所組成*

在前一篇文章中，我們了解到 Expression 其實就是由 Value 與 Operator 所組成的，而且可以被 Evaluate 成單一個 Value。所謂的「資料類型」(Data Type) 指的就是 Value 所屬的類別，每一個 Value 都有自己的 Data Type。以上圖為例，「2」的 Data Type 就是 Integer。

為什麼要在意 Data Type？因為 Python 會依照 Value 的類別，決定這個值可以做什麼運算。同樣一個加號，套在兩個數字上是相加，套在兩個字串上卻是把字接起來，這件事等一下就會看到。

![Python 三種基本資料類型的整理圖，分別列出 Integer、Floating-Point 與 String 的範例值。](img-003)
*Python 中最基本的資料類型*

Python 中最基本的三種 Data Type 為 Integer、Floating-Point 與 String：

- **Integer**：縮寫為「int」，指的是「整數」。如上圖中的 1, 2, -4, 0, 12, 700 等等。
- **Floating-Point**：縮寫為「float」，指的是帶有「小數點」的數字。如上圖中的 -12.5, 13.7, 77.89, 34.567 等等。
- **String**：縮寫為「str」，指的是「字串」，由「單引號」或「雙引號」包覆起來。如上圖中的 'a', 'apple', 'bb', 'python' 等等。

這裡有個很容易踩到的地方：`100` 和 `'100'` 在 Python 眼中是兩個完全不同的東西，前者是 Integer，後者是 String。

## 字串的基本運算

前一篇文章的運算都是針對 Integer 與 Floating-Point。在 Python 中，字串同樣可以做「加法」與「乘法」，只是意義不太一樣。

- **字串加法 (String Concatenation)**

  字串的加法就是把兩個字串接在一起。下方程式碼把字串 `'app'` 與字串 `'le'` 相加，會得到字串 `'apple'`。

```python
'app' + 'le'
```

- **字串乘法 (String Replication)**

  字串的乘法就是把同一個字串重複數次。下方程式碼把字串 `'apple'` 與整數 2 相乘，會得到字串 `'appleapple'`。

```python
'apple' * 2
```

## Syntax Error 與 Type Error

![Python 直譯器出現 Syntax Error 的畫面，字串少了一邊的引號因而報錯。](img-004)
*字串必須由成對的「引號」包起來，否則產生 Syntax Error*

在前一篇文章中，我們透過 Expression 提到 Syntax Error 的意義：程式的「寫法」本身不合文法。字串就是個典型例子。在 Python 中，字串 (String) 必須由「成對」的引號包覆起來，少了任一邊，電腦就無法確定這個字串的範圍到哪裡結束，於是拋出 Syntax Error。

![Python 直譯器出現 Type Error 的畫面，String 與 Integer 相加因而報錯。](img-005)
*String 與 Integer 相加將會導致 Type Error*

另一種常見的錯誤是 Type Error，發生在寫法沒問題、但 Data Type 兜不起來的時候。做 String Concatenation 時，必須是兩個 String 相加；如果其中一個不是 String，就會產生 Type Error。

![Python 直譯器出現 Type Error 的畫面，String 與 Floating-Point 相乘因而報錯。](img-006)
*String 與 Floating-Point Number 相乘也會導致 Type Error*

同樣的道理，做 String Replication 時，必須是一個 String 乘以一個 Integer。把 Integer 換成 Floating-Point 一樣會產生 Type Error——畢竟把一個字串重複 2.5 次，本來就沒有合理的答案。

分清楚這兩種錯誤，除錯會快很多：Syntax Error 是「句子寫壞了」，回頭檢查引號、括號有沒有成對；Type Error 是「句子沒寫壞，但東西放錯種類」，回頭檢查參與運算的值分別是什麼 Data Type。

## Python 中的變數

「變數」的英文為 Variable，是程式中非常重要的角色。變數在程式中扮演的角色像是一個「箱子」，我們可以把一個 Value 放進箱子裡。前面提到 Python 中 Value 的 Data Type 主要為 Integer、Floating-Point 與 String，所以箱子裡可以放一個 String (`'apple'`)、一個 Integer (`100`)，當然也可以放一個 Floating-Point (`13.5`)。

把一個 Value 放入箱子中，也就是把一個 Value 存到變數裡的過程，稱為「Assignment」。在程式中，Assignment 是透過「等號」來完成。

![變數概念示意圖，用一個貼著 spam 標籤的箱子裝著數值 42。](img-007)
*Python 中的變數可以想成一個「箱子」，能夠存放一些值 [source: AUTOMATE THE BORING STUFF WITH PYTHON]*

以上圖為例，我們把 Integer (42) 存入 spam 這一個變數中，在 Python 中的寫法為：

```python
spam = 42
```

意思是把 Integer (42) Assign 到 Variable (spam) 中。要注意等號在這裡不是數學上的「相等」，而是「把右邊的值放進左邊的箱子」。我們在 Colab 的 Cell 中執行變數的名稱，就會顯示「目前」這個變數中所存放的數值。

```python
spam
```

再多新增一個變數：

```python
num = 130
```

把這兩個變數相加，就會顯示兩個變數中存放的數值相加後的結果。

```python
spam + num
```

也可以把相加後的結果存放回原來的變數中：

```python
spam = spam + num
```

這行是理解 Assignment 的關鍵：Python 會先算出右邊的 `spam + num`，再把結果放回 spam 這個箱子。如此一來，spam 變數原來存放的數值就會被取代掉，變成新的數值。

```python
spam
```

由上述的例子可以發現，當一個變數「第一次」被 Assign 一個 Value 時，該變數 (箱子) 就會被創造出來；在之後的程式中，我們可以不斷替換這個箱子裡存放的數值。

## 變數名稱

在前面的例子中，我們新增了兩個變數，名字分別為 `spam` 與 `num`。在 Python 中，變數的名稱有三個限制條件：

1. **必須是一個 word，不能包含 space**

   例如 `apple`、`abc`、`animal` 都可以當變數名稱，`app le` 就不行。

2. **word 中僅能使用字母、數字與底線**

   例如 `apple_abc1` 是可以接受的，`apple!?` 就不行。

3. **不可以是數字開頭**

   例如 `a3` 是可以的，`3a` 是不可以接受的。

除了這些硬性規定之外，還有個實務上的建議：變數名稱盡量取得看得懂。`spam`、`num` 拿來當教學範例沒問題，但真的在寫程式時，`total_price` 會比 `a1` 好維護太多。

## 結論

本篇文章介紹了 Python 中 Value 的三種基本 Data Type (Integer、Floating-Point、String)，以及字串的兩種運算 (Concatenation 與 Replication)，也說明了 Syntax Error 與 Type Error 的差別。後半段則帶到「變數」的概念：把變數想成箱子，用等號做 Assignment，並記得變數第一次被 Assign 時才會被建立出來。

下一篇文章將會撰寫第一個完整的程式：它可以接受使用者的輸入，根據輸入進行運算之後，再把結果顯示出來。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Python 中 Variable 的觀念",
    "why_used": "文章開頭的主題圖，點出本篇的核心主題是 Python 的變數概念。",
    "agent_match_hint": "一張標題式的主題圖，畫面上有 Python 與 Variable 字樣。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Expression 就是由 Value 與 Operator 所組成",
    "why_used": "承接前一篇文章的 Expression 概念，說明 Value 才是 Data Type 的載體。",
    "agent_match_hint": "一張拆解算式的示意圖，把一段 Expression 標示成 Value 與 Operator 兩部分。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Python 中最基本的資料類型",
    "why_used": "支撐介紹 Integer、Floating-Point 與 String 三種基本 Data Type 的段落，圖中列有各類型的範例值。",
    "agent_match_hint": "一張分類整理圖，列出三種資料類型與各自的範例數值或字串。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "字串必須由成對的「引號」包起來，否則產生 Syntax Error",
    "why_used": "示範引號沒有成對時 Python 實際回報的 Syntax Error，讓讀者認得這個錯誤長什麼樣子。",
    "agent_match_hint": "一張程式執行畫面截圖，字串少了一邊引號，下方顯示 SyntaxError 訊息。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "String 與 Integer 相加將會導致 Type Error",
    "why_used": "示範 String Concatenation 時型別不一致所產生的 Type Error。",
    "agent_match_hint": "一張程式執行畫面截圖，字串與整數相加，下方顯示 TypeError 訊息。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "String 與 Floating-Point Number 相乘也會導致 Type Error",
    "why_used": "示範 String Replication 時乘數必須是 Integer，換成 Floating-Point 就會出錯。",
    "agent_match_hint": "一張程式執行畫面截圖，字串乘以帶小數點的數字，下方顯示 TypeError 訊息。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Python 中的變數可以想成一個「箱子」，能夠存放一些值 [source: AUTOMATE THE BORING STUFF WITH PYTHON]",
    "why_used": "用箱子的比喻具象化變數與 Assignment 的關係，對應 spam = 42 這個範例。",
    "agent_match_hint": "一張比喻示意圖，一個標示 spam 的箱子裡裝著數字 42。"
  }
]
```
