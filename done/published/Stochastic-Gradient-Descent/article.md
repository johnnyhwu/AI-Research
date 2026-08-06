# Stochastic Gradient Descent 介紹

## 前言

在上一篇「Deep Learning 基本功：Gradient Descent 介紹」中，我們談到如何透過 Gradient Descent 更新參數 v，讓 Cost Function C(v1, v2, v3, …) 的數值不斷下降。計算 Cost Function 的 Gradient 給了我們參數的「更新方向」，設定 Learning Rate 則決定參數的「更新大小」。

不過把 Gradient Descent 直接套到 Neural Network 的參數更新上，會遇到一個很現實的問題：參數更新得太慢。Stochastic Gradient Descent 就是為了解決這件事而出現的改良版。本文會說明什麼是 Stochastic Gradient Descent、它和原本的 Gradient Descent 差在哪，以及 Mini-Batch、Batch Size、Epoch 這幾個常聽到的名詞各自代表什麼。

## 利用 Gradient Descent 更新 Neural Network 中的參數

在進入 Stochastic Gradient Descent 之前，先複習一下 Gradient Descent 是怎麼更新 Neural Network 裡的參數的。

在「Deep Learning 基本功：認識 MNIST 資料集與損失函數」一文中我們提過，Cost Function 的用途是評估目前 Neural Network 中參數（包含 Weight 與 Bias）的好壞：Cost 愈小，代表這組參數讓模型的輸出愈接近正確答案。

![Cost Function 接收 Neural Network 的 Weight 與 Bias，輸出一個評估參數好壞的數值。](img-001)
*利用 Cost Function 評估 Neural Network 中參數的好壞*

而在介紹 Gradient Descent 的那篇文章中，我們已經知道怎麼更新參數 v 來讓 Cost Function 的數值下降。到了 Neural Network，做法完全一樣，只要依樣畫葫蘆，把 v 換成 Neural Network 中的 Weight 與 Bias 就好：

![Weight 與 Bias 的更新公式，兩者分別減去 Learning Rate 乘上 Cost Function 對該參數的偏微分。](img-002)
*依樣畫葫蘆，更新 Neural Network 中的 weight 與 bias*

每套用一次這個規則，Weight 與 Bias 就往讓 Cost Function 變小的方向挪一步。反覆做下去，Cost Function 的數值就會愈來愈小。

## Gradient Descent 的缺點

Gradient Descent 已經算是很好用的方法了，但它有個結構性的缺點，問題出在 Cost 是怎麼被平均出來的。

前面提到的 Cost Function，其形式為 **C = (1/n) × ∑x Cx**。其中 **Cx** 表示模型針對一筆訓練資料所計算出來的 Cost（也就是模型的這一筆輸出與正確答案的誤差），我們會將每一筆訓練資料的 Cost 加總再除以訓練資料的數目，得到平均每一筆訓練資料的 Cost。

Gradient 也是同樣的算法：先用一筆訓練資料的 Cost 算出一個 Gradient（∇Cx），再把所有訓練資料的 Gradient 加總後除以訓練資料的數量，得到平均每一筆訓練資料的 Gradient：**∇C = (1/n) × ∑x ∇Cx**。

問題就在這裡：模型必須看過整個訓練資料集，才算得出一個 Gradient，也才能更新一次參數。以 MNIST 這種有 60000 張圖像的資料集來說，跑完一整輪才換來一次參數更新，訓練當然快不起來。

## Stochastic Gradient Descent 是什麼

Stochastic Gradient Descent 的出現正是為了加速訓練，讓參數的更新頻率高一些。用它更新參數時，模型不需要看完訓練資料集中的所有樣本才計算一次 Gradient，而是看過其中「部分樣本」就算一次 Gradient、更新一次參數。

舉個具體的例子。假設訓練資料集中有 100 筆資料：用 Gradient Descent，模型要看完 100 筆才算得出一個平均的 Gradient；用 Stochastic Gradient Descent，模型可能只看 10 筆就算出一個平均的 Gradient 並更新參數。同樣是看過 100 筆訓練資料，前者只能更新模型**一次**，後者卻能更新**十次**。

你可能會問，一定要是 10 筆嗎？20 筆或 5 筆行不行？

當然可以。在 Stochastic Gradient Descent 中，這種「部分資料」稱為 **Mini-Batch**，而一個 Mini-Batch 裡訓練資料的數量則稱為 **Batch Size**。Batch Size 和上一篇提到的 Learning Rate 同樣屬於 Hyperparameter，都要由我們（人類）手動設定，沒辦法像模型參數那樣自動被更新。

Batch Size 該設多大，本文先不深入討論，但有個原則值得先記住。我們之所以隨機抽出一部分資料組成 Mini-Batch，是為了讓參數被更新更多次、加快訓練速度；可是如果「更新的方向」不對，更新再多次模型也收斂不了（也就是 Cost Function 的數值還是降不下來）。所以 Batch Size 要夠大，大到只用這一個 Mini-Batch 算出來的平均 Gradient，就能夠近似整個訓練資料集算出來的平均 Gradient：

![以 m 筆 Mini-Batch 資料計算的平均 Gradient 與以全部訓練資料計算的平均 Gradient 兩式並列的近似關係。](img-003)
*左式為 m 筆訓練資料計算出來的平均 Gradient，右式為所有訓練資料計算出來的平均 Gradient。左式應該愈接近右式愈好*

換句話說，Mini-Batch 是拿「一小份抽樣」去估計「全體的平均 Gradient」。抽樣抽得太少，估出來的方向就會偏掉。

## 利用 Stochastic Gradient Descent 更新 Neural Network 中的參數

回到 Neural Network。用 Stochastic Gradient Descent 更新時，Weight 與 Bias 的更新方式為：

![Weight 與 Bias 的更新公式，梯度項改為對 Mini-Batch 中 m 筆資料的 Gradient 加總後除以 m。](img-004)
*利用 Stochastic Gradient Descent 更新 Neural Network 中的參數*

也就是說，每一次都從整個訓練資料集中「隨機」抓出一個 Mini-Batch 的資料，假設 Batch Size 為 m，那就是 m 筆資料。把這 m 筆資料的 Gradient 加總後除以 m，得到平均的 Gradient。有了這個平均的 Gradient，我們就知道參數的更新方向，再透過 Learning Rate（也就是前面提到控制「更新大小」的那個 Hyperparameter）調整這一步要跨多大。

完成這一次 Weight 與 Bias 的更新後，再從訓練資料集中「隨機」抓出另一個 Mini-Batch，用同樣的方式更新參數。等到整個訓練資料集中的所有資料都被模型看過一遍，就表示模型完成了一個 **Epoch** 的訓練。

實務上訓練一個模型會跑很多個 Epoch，每個 Epoch 內又切成許多個 Mini-Batch。所以「Batch Size 設多少」直接決定了一個 Epoch 裡參數會被更新幾次：資料量 n 除以 Batch Size m，就是這一輪的更新次數。

## 結論

本文介紹了 Stochastic Gradient Descent，以及 Mini-Batch、Batch Size 與 Epoch 的概念。它與 Gradient Descent 的差別只有一句話：不必看完整個訓練資料集才更新一次參數，而是看過一個 Mini-Batch 就更新一次，用更頻繁的更新換取更快的訓練速度。

代價則是每一步的方向不再是「全體資料的平均 Gradient」，而是一份抽樣的估計值，因此 Batch Size 不能太小，否則方向失準，模型反而收斂不了。這個「更新頻率」與「梯度準確度」之間的取捨，正是實際調參時最常碰到的權衡。

### 參考資料

- [Neural networks and deep learning](http://neuralnetworksanddeeplearning.com/chap1.html)
- [Stochastic gradient descent – Wikipedia](https://en.wikipedia.org/wiki/Stochastic_gradient_descent)
- [深度學習中的 batch 大小對學習效果有何影響？ – 知乎](https://www.zhihu.com/question/32673260)
- [Difference Between a Batch and an Epoch in a Neural Network (machinelearningmastery.com)](https://machinelearningmastery.com/difference-between-a-batch-and-an-epoch/)
- [What is batch size in neural network? – Cross Validated](https://stats.stackexchange.com/questions/153531/what-is-batch-size-in-neural-network)

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "利用 Cost Function 評估 Neural Network 中參數的好壞",
    "why_used": "複習 Cost Function 的角色，說明它負責評估 Neural Network 中 Weight 與 Bias 的好壞，作為後續討論 Gradient 的基礎。",
    "agent_match_hint": "一張示意圖，呈現 Neural Network 的參數輸入 Cost Function 後得到一個評估數值。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "依樣畫葫蘆，更新 Neural Network 中的 weight 與 bias",
    "why_used": "支撐把 Gradient Descent 的更新規則套用到 Neural Network 參數上的段落，呈現 Weight 與 Bias 的更新式。",
    "agent_match_hint": "兩行數學公式，w 與 b 分別減去 Learning Rate 乘上 Cost Function 的偏微分。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "左式為 m 筆訓練資料計算出來的平均 Gradient，右式為所有訓練資料計算出來的平均 Gradient。左式應該愈接近右式愈好",
    "why_used": "說明 Batch Size 要夠大的原則：Mini-Batch 算出的平均 Gradient 必須近似全體訓練資料的平均 Gradient。",
    "agent_match_hint": "一個近似等式，左邊是對 m 筆資料的 Gradient 求和除以 m，右邊是對全部 n 筆資料的 Gradient 求和除以 n。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "利用 Stochastic Gradient Descent 更新 Neural Network 中的參數",
    "why_used": "呈現 Stochastic Gradient Descent 版本的 Weight 與 Bias 更新公式，對照前面 Gradient Descent 的更新式差異。",
    "agent_match_hint": "兩行數學公式，梯度項是對 Mini-Batch 中 m 筆資料的偏微分加總後除以 m。"
  }
]
```
