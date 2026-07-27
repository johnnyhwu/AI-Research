# Python 中的 Boolean Operator

## 前言

本篇是 Python 程式語言入門教學的第 5 篇。在前一篇「第一個 Python 程式」中，我們寫出了一支能跟使用者互動的程式：程式問問題、使用者輸入答案。但目前的互動還很單薄，因為不管使用者輸入什麼，程式做的事情都一模一樣。

要讓程式「看狀況辦事」，第一步不是急著學 `if` 怎麼寫，而是先搞懂程式怎麼表達「是」與「不是」。這篇文章會從流程控制的概念出發，介紹布林 (Boolean) 這個資料類型、比較運算子 (Comparison Operator)，以及三個布林運算子 `and`、`or`、`not`。

## 程式中的流程控制 (Control Flow)

「讓程式根據不同的狀況 (輸入)，採取不同的行為」，這件事就叫做「流程控制」。這個概念其實一點都不陌生，日常生活中我們每天都在做，只是沒有把它畫出來而已。

![出門前判斷是否下雨與是否有雨傘的流程圖，從 Start 經過兩個判斷節點分岔到不同結果，最後匯集到 End。](img-001)
*流程圖 [source: Automate the Boring Stuff with Python]*

我們從「Start」出發，首先遇到了「Is raining?」的判斷，如果是「Yes」則前往「Have umbrella?」、如果是「No」則前往「Go outside.」。「Have umbrella?」也是同樣的道理，如果是「Yes」會前往「Go outside.」、如果是「No」則會前往「Wait a while.」。

關鍵就在那些菱形的判斷節點。因為流程圖中多了「Is raining?」、「Have umbrella?」這兩個判斷，從「Start」走到「End」就不再只有一條路，而是有多種不同的走法。

把同樣的觀念寫進程式裡，程式就能因應不同的狀況採取不同的行為。而要寫出判斷，我們得先知道怎麼在程式中表示菱形框裡的「Yes」與「No」。

## 布林資料類型

流程圖中的「Is raining?」(現在下雨嗎？) 只會有兩種結果，不是「Yes」就是「No」，不會有第三種答案。

在一般常見的程式語言中，有一種資料類型正好對應這種「非黑即白」的情況，稱為「布林」(Boolean)。Boolean 資料類型的數值只有兩種：`True` 與 `False`。「True」就是代表「Yes」、「False」就是代表「No」。

到目前為止，我們已經接觸了 4 種資料類型，分別是：整數 (Integer)、浮點數 (Floating-Point)、字串 (String) 與布林 (Boolean)。

在 Python 中，建立一個 Boolean 變數也相當簡單，只需要設定這個變數的數值是 True 或是 False。注意 `True` 和 `False` 的第一個字母要大寫，這是 Python 的關鍵字，寫成 `true` 會直接報錯。

```python
x = True
y = False
```

## 「比較」運算子

接著要理解的是程式中的「比較」運算子 (Comparison Operator)。生活中常見的比較有：「等於」、「不等於」、「大於」、「小於」、「大於或等於」與「小於或等於」，數學課上都看過。

在 Python 程式中的對照寫法如下圖所示：

![比較運算子對照表，列出等於、不等於、大於、小於、大於或等於、小於或等於在程式中的符號寫法。](img-002)
*程式中常見的比較運算子*

比較運算子會接受兩個數值，並回傳一個結果，這個結果不是 True 就是 False。換句話說，比較運算子回傳的東西正好就是一個 Boolean，這也是它跟流程控制接得起來的原因。我們可以在 Colab 中撰寫以下程式碼並執行。

```python
1 == 2

10 <= 20

20-1 != 19

'apple' == 'apple'
```

可以發現執行的結果不是 True 就是 False。字串也可以比較，`'apple' == 'apple'` 問的是「這兩個字串長得一樣嗎」，答案是 True。

## 「==」vs 「=」

在上面的比較運算子中，比較兩個數值是否相同用的是「兩個等號」(`==`)。這裡是初學者最常踩雷的地方，千萬不能把 `==` 與 `=` 搞混：

- `==`：是用來詢問兩個數值是否相同
- `=`：是用來將右邊的數值 (Value) 寫入 (Assign) 到左邊的變數 (Variable)

也就是說，`x = 3` 是「把 3 存進 x」這個動作，執行完不會得到 True 或 False；`x == 3` 才是「x 現在是不是 3？」這個問句，執行完會得到一個布林值。

有個簡單的記法：「詢問兩個數值是否相同」與「詢問兩個數值是否不相同」都是使用兩個符號，分別是 `==` 與 `!=`。只要是在「問問題」，符號就是兩個字元。

## 布林運算子

了解完比較運算子後，接著是「布林運算子」。可以把「運算子」想成針對某種資料類型能做的操作，例如整數與浮點數的運算子包含了 `+`、`-`、`*`、`/`、`%`、`//`。

布林運算子則包含 3 種：`and`、`or` 與 `not`。布林運算子接受布林數值，再回傳一個布林數值。下面逐一了解這 3 種運算子的意義。

- **and**：如果兩個布林數值都是 True，則回傳 True；若存在一個 False，則回傳 False。我們可以執行以下 Python 程式碼，了解 and 的意義。

```python
True and True

True and False

False and False
```

下圖為「and」的 Truth Table (真值表)，把「and」所有可能的輸入組合與對應結果都列了出來。真值表是理解邏輯運算最快的方式，不用背，看表就知道：

![and 運算子的真值表，列出兩個布林值所有四種組合與對應的運算結果。](img-003)
*“and” operator 的真值表 (Truth Table) [source: Automate the Boring Stuff with Python]*

- **or**：如果其中一個布林數值為 True，則回傳 True；若兩個都是 False，則回傳 False。我們可以執行以下 Python 程式碼，了解 or 的意義。

```python
True or True

True or False

False or False
```

下圖為 or 的 Truth Table，列出 or 的所有情況：

![or 運算子的真值表，列出兩個布林值所有四種組合與對應的運算結果。](img-004)
*“or” operator 的真值表 (Truth Table) [source: Automate the Boring Stuff with Python]*

- **not**：與 and 和 or 不同的是，not 只會接受「一個」布林數值，並回傳這個布林數值的「相反」。舉例來說，試著執行以下 Python 程式碼：

```python
not True

not False
```

下圖為 not 的 Truth Table，列出 not 的所有情況：

![not 運算子的真值表，列出 True 與 False 兩種輸入以及取相反後的結果。](img-005)
*“not” operator 的真值表 (Truth Table) [source: Automate the Boring Stuff with Python]*

## 「比較運算子」與「布林運算子」混合使用

前面提過，比較運算子執行後得到的結果是布林值。既然布林運算子吃的也是布林值，兩者自然可以串在一起：用布林運算子把多個比較運算子結合起來，最終仍然只會得到一個布林數值。

回到前面的流程圖，「今天有下雨，而且我有帶傘」這種同時包含兩個條件的判斷，寫成程式就是這種混合式的寫法。

舉例來說，執行以下 Python 程式碼：

```python
(2 ==3) and (5 == 6)

(2 < 3) or (5 > 6)

(2 != 3) or (5 <= 6)

not ((2 != 3) or (10 <= 6))
```

以最後一個例子來說明。如下圖所示，程式會從最內層的括號往外算：先執行 `(2 != 3)` 得到 True，再執行 `(10 <= 6)` 得到 False，接著把兩者 or 在一起得到 True，最後再進行最外層的 not，得到 False。

![Boolean Expression 由內而外逐步化簡的計算過程圖，每一層括號的運算結果依序被替換成 True 或 False，最後收斂成單一布林值。](img-006)
*Boolean Expression 的計算過程*

只要照著「由內而外、一層一層換成布林值」的順序推，再長的條件式也拆得開。

## 結論

這篇文章介紹了程式語言中的布林 (Boolean) 資料類型，以及兩類相關的運算子：回傳布林值的比較運算子 (`==`、`!=`、`>`、`<` 等)，以及組合布林值的布林運算子 (`and`、`or`、`not`)。搭配真值表，就能推算出任何一段 Boolean Expression 的結果。

布林是流程控制 (Control Flow) 中最基本的元素，有了它才有「條件」可談。下一篇文章會接著介紹如何在 Python 中撰寫流程控制的語法 (Control Flow Statement)，也就是 `if`、`elif`、`else`。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "流程圖 [source: Automate the Boring Stuff with Python]",
    "why_used": "用一個生活化的流程圖具體呈現「流程控制」的概念，說明判斷節點如何讓程式產生多種不同的執行路徑。",
    "agent_match_hint": "一張流程圖，含 Start/End 節點與 Is raining?、Have umbrella? 兩個菱形判斷框，箭頭以 Yes/No 分岔。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "程式中常見的比較運算子",
    "why_used": "對照日常語言中的「等於、大於、小於」與程式中實際的符號寫法，讓初學者建立符號對應關係。",
    "agent_match_hint": "一張對照表，左欄是比較運算子符號 (==、!=、>、<、>=、<=)，右欄是對應的中文或英文意義。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "“and” operator 的真值表 (Truth Table) [source: Automate the Boring Stuff with Python]",
    "why_used": "列出 and 運算子所有輸入組合與結果，讓讀者不必死背規則，直接查表理解 and 的行為。",
    "agent_match_hint": "一張真值表，四列分別是 True and True、True and False、False and True、False and False 及其結果。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "“or” operator 的真值表 (Truth Table) [source: Automate the Boring Stuff with Python]",
    "why_used": "列出 or 運算子所有輸入組合與結果，與 and 的真值表形成對照。",
    "agent_match_hint": "一張真值表，四列分別是 True or True、True or False、False or True、False or False 及其結果。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "“not” operator 的真值表 (Truth Table) [source: Automate the Boring Stuff with Python]",
    "why_used": "呈現 not 只接受單一布林值並取相反的特性，凸顯它與 and、or 的差異。",
    "agent_match_hint": "一張只有兩列的真值表，not True 對應 False、not False 對應 True。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Boolean Expression 的計算過程",
    "why_used": "以實際的巢狀運算式示範由內而外的求值順序，支撐比較運算子與布林運算子混合使用的段落。",
    "agent_match_hint": "一張逐步化簡的示意圖，一段含括號的布林運算式分成數行，每行把一部分替換成 True 或 False，最後剩下單一結果。"
  }
]
```
