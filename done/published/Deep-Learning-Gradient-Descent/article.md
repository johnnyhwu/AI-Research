# Deep Learning 基本功：Gradient Descent 介紹

## 前言

在「Deep Learning 原理：Neural Network 如何分類圖像」一文中，我們以「手寫數字圖像」的分類問題為例，站在 Neural Network 的角度感受它如何理解一張圖像。接著我們也知道，Neural Network 要靠以下 3 個元素來調整內部的參數 (weight 與 bias)，讓輸出愈來愈接近正確答案：

- 訓練資料集 (Training Dataset)
- 損失函數 (Cost Function)
- 最佳化演算法 (Optimizer)

前兩個元素在「Deep Learning 基本功：認識 MNIST 資料集與損失函數」一文中已經介紹過，本文要談的是第三個元素：最佳化演算法 (Optimizer)，而且是其中最基本、也最重要的一種——Gradient Descent。讀完本文，你會知道 Gradient Descent 到底在做什麼、它背後的數學長什麼樣子，以及 Learning Rate 在裡面扮演什麼角色。

## 訓練 Neural Network 到底在訓練什麼

在進入演算法之前，先把「訓練」這件事講清楚。訓練 Neural Network，說白了就是把網路裡的參數 (weight 與 bias) 調整到一組好的數值，讓網路的輸出愈接近正確答案愈好。

那「好」與「不好」怎麼衡量？靠的就是 Cost Function。

![Cost Function C(w, b) 的數學算式，用來衡量目前這組 weight 與 bias 的好壞。](img-001)
*Cost Function 的算式*

Cost Function 會把「目前這組參數表現得如何」濃縮成一個數字：值愈小，代表網路的輸出愈接近正確答案。所以訓練 Neural Network 的過程，其實就是調整 w (weight) 與 b (bias)，使得 C (Cost Function) 的值最小。

一句話總結：**訓練 Neural Network ⇒ 調整參數 (w 與 b)，使得 Cost Function 變小**。

問題來了，該怎麼調整 w 與 b，才能讓 Cost Function 愈來愈小？這就要靠 Gradient Descent 這個演算法。

## 先用「山谷」與「球」理解 Gradient Descent

為了把概念講清楚，我們先把問題簡化。暫時忘掉 Neural Network、Cost Function、weight 與 bias 這些名詞。

現在手上只有一個函數 C(v)，其中 v = v1, v2, …，表示 C 這個函數可以接受任意數量的參數。目標很單純：透過 Gradient Descent 調整每一個 v，讓 C(v) 的值愈來愈小。

為了方便視覺化，我們假設 C 只接受兩個參數 v1 與 v2，也就是 C(v1, v2)。輸入不同的 v1 與 v2 會得到不同的數值，如果把所有 (v1, v2) ⇒ C(v1, v2) 的情況都畫出來，這些點會在 3 維空間中形成一個面：

![C(v1, v2) 在三維空間中形成的曲面，起伏像一座山谷，谷底即為函數的最小值所在。](img-002)
*C(v1, v2) 在三維空間中形成的面 [source: Neural Networks and Deep Learning]*

單看上面這張圖，你大概一眼就能看出最小值在哪裡。但實務上一個 Neural Network 動輒好幾千萬個參數，不可能這樣用眼睛看出來。這正是 Gradient Descent 派上用場的地方。

在講數學之前，先換個更貼近真實世界的角度：把 C(v) 函數想成一座「山谷」，而我們自己是山谷上的一顆「球」。球會怎麼移動？當然是沿著山壁往下滾，直到滾進谷底才停下來。

![地勢起伏錯綜複雜的山谷地形照片，用來比喻參數空間的樣貌。](img-003)
*在一座地勢錯綜複雜的山谷上，我們是一顆球 [source: sciencesprings.wordpress.com]*

這裡的眉角是：我們是一顆停在山壁上的球，而這座山谷地勢錯綜複雜（如上圖），我們看不到谷底在哪裡，只知道自己「目前所在位置」附近的地勢怎麼變化。

既然如此，要抵達谷底就只能靠一個土法煉鋼的辦法：感受一下四面八方哪個方向是「下坡」，朝那個方向走一步；到了新位置後，再感受一次哪個方向是下坡，再走一步……如此反覆，直到四面八方都是平地、找不到下坡方向為止。那時我們就在谷底了。

## Gradient Descent 的數學

有了「山谷與球」的比喻，接著把數學補上。這裡不會深入到數學系的程度，只需要一點偏微分的概念就夠了。

回到剛剛的 C(v) = C(v1, v2)。球的起始位置落在哪裡，取決於 v1 與 v2 的初始數值。因為我們把自己當成球，看不到整座山谷的全貌，也就看不到 C(v1, v2) 的最低點在哪，只能看到所處位置的狀態。

假設我們已經決定要往某個方向前進（用向量 Δv 表示），可以把這一步拆成先朝 v1 方向移動 Δv1、再朝 v2 方向移動 Δv2，也就是 Δv ≡ ( Δv1 , Δv2 )T（T 是 Transpose 的意思）。

朝 Δv 走一步之後，C(v1, v2) 的變化量稱為 ΔC，可以寫成下面這個算式：

![ΔC 的算式：C 對 v1 的偏微分乘上 Δv1，加上 C 對 v2 的偏微分乘上 Δv2。](img-004)
*往 Δv 前進一步，對 ΔC 造成的影響*

偏微分的概念在「Perceptron 的改良版：了解什麼是 Sigmoid Neuron」一文中介紹過，這裡可以簡單把它視為：一個多變數函數對於某一個獨立變數的「改變率」。舉例來說，當 v1 加上 5 時 (Δv1 = 5)，對 C 的影響不一定就是加上 5 (ΔC 不一定等於 5)，而是要再乘上 C 對 v1 的改變率（v1 變動 1 時，C 變動多少）。

接著，我們把 ΔC 算式中偏微分的部分抽出來，給它一個新符號 ∇C，稱為「Gradient of C」：

![∇C 的定義：由 C 對各個參數的偏微分所組成的向量。](img-005)
*將偏微分部分取出，並給他一個新的定義*

第一次看到 ∇ 這個符號不用緊張。∇ 通常用來表示 Gradient Vector，而 Gradient Vector 也不是什麼了不起的東西，就是一個向量，裡頭每一個元素都是一個偏微分（函數對某個特定參數的微分）。

有了 Δv 與 ∇C，原來的 ΔC 算式就可以改寫成：

![ΔC 約等於 ∇C 與 Δv 相乘的算式。](img-006)
*將 ΔC 改寫*

從這個算式可以看得更清楚：ΔC（函數的變化量）取決於 Δv（每一個參數的變動量）與 ∇C（每一個參數變動一單位時對 C 造成的影響）兩者相乘。

別忘了我們的目的。我們是一顆球，希望移動 Δv 之後 C(v1, v2) 的數值變小，也就是 ΔC ≤ 0。那要怎麼挑 Δv？只要設定 **Δv = −η ∇C**，代入後會得到 ΔC ≈ −η ∇C ⋅ ∇C = −η |∇C|²。因為 |∇C|² 一定大於等於 0，所以 ΔC 一定小於等於 0——這一步保證不會走上坡。

到這裡，我們已經知道每一步該怎麼走了。當球目前位於 v，要移動到新位置 v'：

![參數更新規則：新位置 v' 等於舊位置 v 減去 η 乘上 ∇C。](img-007)
*我們知道每一步應該怎麼走*

依照這個規則，每要移動一步就重新計算一次 ∇C（Gradient Vector），每移動一次 C(v1, v2) 就變小一點。一步一步走下去，直到抵達谷底，也就是 C(v1, v2) 的最小值。這整個過程就叫做 Gradient Descent。

## η (Learning Rate) 是什麼

上面的算式裡還有一個符號沒交代：η。η 在機器學習中代表 Learning Rate。

要理解 Learning Rate 的意義，先回頭看 ∇C（也就是前面提到的 Gradient Vector）在做什麼。∇C 裡記錄的是函數對各參數的偏微分；在 C 只有一個參數 v 的情況下，其實就是在算切線斜率，而斜率告訴我們每個參數該往哪個方向移動。如果 C 對 v 的偏微分是「負值」，代表 v 變大時 C 會「減少」；如果偏微分是「正值」，代表 v 變大時 C 會「增加」。

所以分工很清楚：∇C 決定每一個參數的「移動方向」，η (Learning Rate) 決定「移動的大小」。

η 在 Deep Learning 中屬於一種超參數 (Hyperparameter)，意思是它必須由我們自己設定、自己調整，沒辦法透過 Neural Network 的學習過程自動調出來。

而設定 Learning Rate 的數值也是一門學問，兩個方向都會出問題：

- Learning Rate 太大：v 一次改變太多，某些情況下反而會讓 ΔC 大於 0，C 函數的數值愈跑愈大。用山谷的比喻來說，就是一步跨太大，直接從這側山壁跨到對面山壁上去了。
- Learning Rate 太小：v 每次只改變一點點，雖然方向沒錯，但要花非常多步、非常多時間才走得到最小值。

## Gradient Descent：從兩個變數到多個變數

前面都是用兩個變數的 C(v1, v2) 在說明。實際的 Neural Network 當然沒這麼單純，但好消息是：如果上面的內容你都懂了，那 Gradient Descent 如何應用在 Deep Learning 上，你其實也已經懂了。

差別只在於變數變多：兩個變數的 Cost Function C(v1, v2) 換成多個變數的 C(v1, v2, v3, v4, …)。當我們移動 Δv 後，一樣會產生 ΔC 的改變，兩者的關係也跟前面完全相同：

![多變數情況下 ΔC 與 Δv 的關係算式，形式與兩個變數時相同。](img-006)
*在多變數的情況下，ΔC 與 Δv 的關係仍舊相同*

只不過現在的 Δv 包含了更多元素：Δv ≡ ( Δv1 , Δv2 , Δv3 , Δv4 , … )T，∇C 也同樣從兩個元素變成了多個：

![多變數情況下的 ∇C，向量中包含 Cost Function 對每一個變數的偏微分。](img-008)
*Gradient Vector 中包含了 Cost Function 對所有變數的偏微分*

在兩個變數的例子中，我們每一步都選 Δv = −η ∇C；在多個變數的情況下，一樣這樣選，也一樣用前面那條規則更新 v，讓 Cost Function 的數值愈來愈小。整套邏輯完全沒變，只是向量變長了而已。

## 結論

本文介紹了 Gradient Descent 的觀念。說穿了，**Gradient Descent 就是透過計算一個函數的 Gradient Vector，得知參數的更新方向，讓函數的數值愈來愈小**。

我們也談到 Learning Rate：它是一種必須事先設定好的超參數 (Hyperparameter)。計算 Gradient 讓我們掌握參數的「更新方向」，Learning Rate 則讓我們決定參數的「更新大小」，兩者缺一不可。

理解了 Gradient Descent 之後，下一篇文章會接著說明它在實務上的變形：Stochastic Gradient Descent。

### 參考資料

- [Gradient descent – Wikipedia](https://en.wikipedia.org/wiki/Gradient_descent)
- [Neural networks and deep learning](http://neuralnetworksanddeeplearning.com/chap1.html)
- [Gradient Descent Algorithm — a deep dive | by Robert Kwiatkowski | Towards Data Science](https://towardsdatascience.com/gradient-descent-algorithm-a-deep-dive-cf04e8115f21)
- [Gradient Descent — ML Glossary documentation (ml-cheatsheet.readthedocs.io)](https://ml-cheatsheet.readthedocs.io/en/latest/gradient_descent.html)
- [An overview of gradient descent optimization algorithms (ruder.io)](https://ruder.io/optimizing-gradient-descent/)

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Cost Function",
    "why_used": "呈現 Cost Function 的算式，支撐「訓練 Neural Network 就是調整 w 與 b 讓 C 變小」這個核心定義。",
    "agent_match_hint": "一行數學公式，是以 w 與 b 為變數的 Cost Function C(w, b) 定義式。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "C(v1, v2) 在三維空間中形成的面 [source: Neural Networks and Deep Learning]",
    "why_used": "讓讀者看到雙變數 Cost Function 在三維空間中的樣子，是後面「山谷與球」比喻的基礎。",
    "agent_match_hint": "一張三維座標圖，兩個水平軸為 v1、v2，垂直軸為 C，曲面呈現凹下去的山谷形狀。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "在一座地勢錯綜複雜的山谷上，我們是一顆球 [source: sciencesprings.wordpress.com]",
    "why_used": "用真實山谷地形強化比喻，說明球只看得到附近地勢、看不到谷底位置的處境。",
    "agent_match_hint": "一張起伏複雜的山谷地形圖或照片，可以看到多處高低起伏而非單一平滑凹槽。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "往 △v 前進一步，對 △C 造成的影響",
    "why_used": "呈現 ΔC 的展開式，作為後續抽出偏微分項、定義 ∇C 的起點。",
    "agent_match_hint": "一行數學公式，ΔC 約等於 ∂C/∂v1 乘 Δv1 加上 ∂C/∂v2 乘 Δv2。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "將偏微分部分取出，並給他一個新的定義",
    "why_used": "定義 Gradient Vector ∇C，讓讀者知道 ∇ 符號代表的就是一堆偏微分組成的向量。",
    "agent_match_hint": "一行定義式，∇C 等於由 ∂C/∂v1、∂C/∂v2 組成的向量（含 Transpose 記號）。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "將 △C 改寫",
    "why_used": "呈現改寫後的 ΔC ≈ ∇C ⋅ Δv，說明函數變化量由移動量與 Gradient 相乘決定；在多變數章節再次引用以強調形式不變。",
    "agent_match_hint": "一行簡短公式，ΔC 約等於 ∇C 與 Δv 的內積。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "我們知道每一步應該怎麼走",
    "why_used": "呈現參數更新規則 v' = v − η ∇C，也就是 Gradient Descent 每一步實際做的事。",
    "agent_match_hint": "一行更新式，v 箭頭指向 v'，v' 等於 v 減去 η 乘上 ∇C。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Gradient Vector 中包含了 Cost Function 對所有變數的偏微分",
    "why_used": "說明變數擴充到多個時，∇C 只是把更多偏微分放進同一個向量，整套規則不變。",
    "agent_match_hint": "一行公式，∇C 等於由 ∂C/∂v1、∂C/∂v2、∂C/∂v3、∂C/∂v4 等多個偏微分組成的長向量。"
  }
]
```
