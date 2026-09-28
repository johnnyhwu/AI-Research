# 機器學習基本知識：維度 (Dimension) 的兩種意義

## 前言

在讀線性代數或深度學習的教材時，很快就會碰到一組說法：純量 (Scalar) 是 0 維、向量 (Vector) 是 1 維、矩陣 (Matrix) 是 2 維，超過 3 維就統稱為張量 (Tensor)。（Scalar、Vector 與 Matrix 其實也都可以視為 Tensor，只是軸數比較少而已）

但同一本書再往下翻幾頁，看到像 `[1, 2, 3, 4, 5]` 這種包含 5 個數字的 Vector 時，作者又會說它是一個「5 維的向量」。

一下 1 維、一下 5 維，Vector 到底是幾維？這篇文章會先把 Scalar、Vector、Matrix 與 Tensor 的關係整理清楚，再回頭回答這個問題。先講結論：Dimension 這個詞在上面兩句話裡，指的根本不是同一件事。

## 純量 (Scalar)、向量 (Vector)、矩陣 (Matrix) 與張量 (Tensor)

要回答前面的問題，得先把這四個名詞放在同一個框架下看。TensorFlow 的說法最直接：它們全都是 Tensor，差別只在於有幾個「軸」(Axes)。

![Scalar、Vector 與 Matrix 三者的對照示意圖，分別以單一數值、一列數值、二維表格呈現，並標出各自的 shape。](img-001)
*Scalar、Vector 與 Matrix 的對照 [source: TensorFlow]*

- **Scalar** 就是一個數字 (Single Value)，它的 shape 中沒有任何元素，也就是沒有任何軸，可以稱它為 Rank-0 的 Tensor。
- **Vector** 是一串數字 (List of Values)，它的 shape 中有一個元素，代表它具有一個軸，也就是 Rank-1 的 Tensor。
- **Matrix** 由兩個軸的元素組成，因此 shape 中有兩個元素，也就是 Rank-2 的 Tensor。

「軸」聽起來抽象，換個角度想就很好懂：要從這個結構裡取出一個數字，需要幾個索引？Scalar 不需要索引，Vector 需要一個（`v[2]`），Matrix 需要兩個（`m[1][2]`）。索引的個數就是 Rank。

軸再往上加，就不再另外取名字了。

![三個軸的 Tensor 示意圖，數值方塊以立方體的形式堆疊排列，shape 由三個元素構成。](img-002)
*三個軸以上的 Tensor [source: TensorFlow]*

當軸數來到 3 個以上時，我們就通稱為 Tensor，此時的 shape 中有 3 個元素，也可以稱其為 Rank-3 的 Tensor。這種形狀在實務上很常見，例如一張 RGB 圖片就是（高、寬、通道）三個軸。

## 維度 (Dimension)：「軸」的個數 or 「向量中元素」的個數

由此可知，當我們說 Scalar 是 0-Dimension、Vector 是 1-Dimension、Matrix 是 2-Dimension 時，這裡的 Dimension 指的是「軸」的數量。

然而，如果我們只聚焦在 Vector 上，意思就換了一個。描述一個 Vector 的 Dimension 時，其實是在描述它所處的「向量空間」(Vector Space) 有幾維，也就是這個 Vector 裡有幾個元素。舉例來說：

- [1, 2, 3] 處在 3-Dimension Vector Space
- [-1, -5, 4, 5, 8] 處在 5-Dimension Vector Space
- [0, 0, 0, 0, 0, 0, 0] 處在 7-Dimension Vector Space

由此可知，**Dimension 有兩種意義**：

- Vector 中的**元素數量**（代表這一個 Vector 所處的 Vector Space）
- Tensor 的**軸數**（代表這一個 Tensor 的 Rank）

回到開頭那個問題：`[1, 2, 3, 4, 5]` 說它是 1 維或 5 維都沒錯，因為兩種說法在數的東西不一樣。它只有一個軸，所以是 Rank-1、1-Dimension 的 Tensor；同時它有 5 個元素，落在 5 維的向量空間中，所以也是一個 5 維向量。

實際判斷時看上下文就行：談的是資料的「形狀」還是「內容」？在 NumPy、PyTorch 這類框架裡講 dimension，通常是 shape、rank 那一種（例如 `ndim`）；在線性代數的脈絡裡講 dimension，多半指的是向量空間的維度。

## 結論

Scalar、Vector、Matrix 與 Tensor 的差別，說白了就是軸數的多寡。而 Dimension 這個詞會依脈絡指向兩件不同的事：Tensor 的軸數 (Rank)，或是一個 Vector 內含多少元素（也就是它所處向量空間的維度）。下次看到「1 維向量」跟「5 維向量」同時出現時，先確認對方是在數軸還是在數元素，大部分的混淆就解開了。

### 參考資料

- [matrices – why do people say "x dimensional vector" when vectors have only one dimension? – Mathematics Stack Exchange](https://math.stackexchange.com/questions/2152360/why-do-people-say-x-dimensional-vector-when-vectors-have-only-one-dimension)
- [Introduction to Tensors | TensorFlow Core](https://www.tensorflow.org/guide/tensor)
- [核心開發者親授！PyTorch 深度學習攻略](https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code=9135738)

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Scalar、Vector 與 Matrix 的對照 [source: TensorFlow]",
    "why_used": "支撐說明 Scalar、Vector、Matrix 三者差別在於軸數多寡的段落，讓讀者對照 shape 與 Rank 的關係。",
    "agent_match_hint": "一張三欄對照圖，由左至右分別是單一數值、一列數值、二維表格，並標註各自的 shape。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "三個軸以上的 Tensor [source: TensorFlow]",
    "why_used": "說明軸數增加到 3 個以上之後就統稱為 Tensor，補足前一張圖沒有涵蓋的高軸數情況。",
    "agent_match_hint": "一張立體示意圖，數值方塊以立方體形式堆疊，呈現具有三個軸的 Tensor。"
  }
]
```
