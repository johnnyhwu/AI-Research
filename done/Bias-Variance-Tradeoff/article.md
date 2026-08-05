# 機器學習基本觀念：Bias-Variance Tradeoff

## 前言

模型訓練完之後，我們會用測試資料集來衡量它的效能，也就是計算模型的 Error。這個 Error 其實由兩個部分組成：Bias 與 Variance。理想上兩個都愈小愈好，但現實是「魚與熊掌不可兼得」，降低 Bias 往往會讓 Variance 變高，反過來壓低 Variance 又會把 Bias 拉上去。

本文會說明什麼是模型的 Bias 與 Variance、兩者為什麼會互相拉扯，以及模型該訓練到什麼程度才算取得平衡。

閱讀之前，建議先對「什麼是機器學習」、「機器學習的模型、訓練與推論」以及「機器學習五步驟」這幾個主題有基本的概念（本系列前幾篇文章都有介紹）。

## Model 的 Bias

拿到訓練資料集之後，我們就會開始用這些資料訓練模型。所謂訓練，講白了就是不斷調整模型裡的參數，讓資料丟進去之後，模型的輸出愈接近正確答案 (Label) 愈好。換個角度看，模型就是一個 Function，負責把輸入資料對應 (Mapping) 到某個輸出。

用一個很小的訓練資料集來說明。資料集裡只有 5 個樣本，每個樣本都有「身高」與「體重」兩個數值。我們希望把「身高」輸入模型，模型吐出「體重」，也就是用身高預測體重。

每個樣本用 (x, y) 表示，x 是身高，y 是體重：

1. (160, 60)
2. (163, 70)
3. (165, 72)
4. (168, 75)
5. (170, 70)

把這 5 個樣本畫在 2 維平面上，長這樣：

![5 個樣本的身高與體重資料點分佈在 2 維座標平面上的散佈圖。](img-001)
*一個簡單的訓練資料集*

假設我們用這個資料集訓練出一個模型，也就是下圖中的那條紅線：

![同一組資料點上多了一條紅色直線，代表用這 5 個樣本訓練出來的模型。](img-002)
*利用這 5 個樣本訓練出來的模型*

這時候會發現一件事：輸入身高 = 163，模型輸出的體重並不是 70。輸入 165、168、170 也一樣，模型給的答案都跟正確答案有落差。

**模型的輸出與正確答案之間的誤差，就稱為 Bias**，也就是下圖中灰色框框標示出來的距離：

![資料點與紅色回歸線之間以灰色框框標示出誤差距離的示意圖。](img-003)
*框框呈現的是模型的輸出與正確答案的誤差*

當模型的 Bias 很大，代表它要嘛訓練得不夠徹底，要嘛複雜度太低，總之就是沒有從訓練資料集裡學到該學的東西，根本沒搞懂輸入與輸出之間的關係。這種模型拿到一筆身高資料，可能會給出一個錯得離譜的體重。我們會說這個模型 **Underfitting**。

## Model 的 Variance

看到這裡，你八成會想到一個解法：「那我用一個超級複雜的模型，一路訓練到每一筆樣本都預測得分毫不差不就好了？」照這個思路做下去，你大概會得到這樣的模型：

![一條高度彎曲的曲線精準穿過全部 5 個資料點的示意圖。](img-004)
*訓練模型精準的預測每一個樣本*

這條曲線看起來完美，訓練資料集裡的每一筆數據它都命中。問題出在沒看過的資料上：輸入身高 = 169，模型的輸出可能落在 72 附近；輸入身高 = 170，模型輸出 70；輸入身高 = 175，模型的輸出卻可能掉到 60。

明明身高只差幾公分，模型的輸出卻上下劇烈跳動。**針對不同的輸入資料，模型輸出的變化（變異性）分佈就稱為 Variance**。

Variance 很大，代表模型把訓練資料集裡的所有東西都硬吞了進去，連「雜訊」也一起學。以上面那條曲線為例，一般來說身高愈高、體重也會愈重，所以第 5 個樣本 (170, 70) 相對於前面的趨勢就可以視為雜訊。模型把這筆雜訊也學起來之後，就會得出一個荒謬的結論：「身高愈高體重愈重，但只要超過 168，體重就會突然暴跌」。

說穿了，這種模型同樣沒有理解輸入與輸出之間的關係，只是把每一筆樣本的對應關係死背下來。一旦餵給它一筆從沒見過的身高，它照樣可能給出錯得離譜的答案。這種模型我們稱為 **Overfitting**。

## Bias-Variance Tradeoff

到這裡兩個極端都出現了：模型太簡單會 Underfitting，太複雜會 Overfitting。這兩者跟 Bias、Variance 的對應關係，可以用下圖來理解：

![以射靶方式呈現 Bias 與 Variance 高低組合的示意圖，並對應到 Underfitting 與 Overfitting 兩種情況。](img-005)
*Bias-Variance 與 Underfitting-Overfitting 的關係 [source: Towards Data Science]*

模型非常「複雜」（參數量很大）時，有能力把訓練資料集裡的每個樣本都記下來，此時 Variance 很高、Bias 很低，也就是前面說的 Overfitting；模型過於「簡單」（參數量很小）時，根本學不到東西，此時 Bias 很高、Variance 很低，也就是 Underfitting。

回到開頭那句話：模型的 Total Error 同時包含 Bias 與 Variance。既然壓低其中一個就會推高另一個，我們就必須在兩者之間權衡，找出讓 Total Error 最低的那個點，這就是 **Bias-Variance Tradeoff**。

下圖把這件事畫得很清楚：

![Bias 與 Variance 隨模型複雜度變化的兩條曲線，以及兩者相加後呈 U 型的 Total Error 曲線。](img-006)
*Bias-Variance Tradeoff 的意義 [source: scott.fortmann-roe.com]*

橫軸是模型複雜度，Bias 隨著複雜度上升而下降，Variance 則反過來上升，兩條線相加得到的 Total Error 呈現 U 型。只盯著 Bias 或只盯著 Variance 調整，都不會落在 U 型的谷底。實務上要找的，就是那個讓 Total Error 最小的甜蜜點。

## 結論

模型的 Error 由 Bias 與 Variance 組成：Bias 大代表模型沒學到輸入與輸出的關係，屬於 Underfitting；Variance 大代表模型把訓練資料連雜訊一起背了起來，屬於 Overfitting。兩者會隨模型複雜度往相反方向移動，所以調模型時真正該追的不是把某一項壓到最低，而是讓 Total Error 落在 U 型曲線的谷底。

下次在調整模型架構或訓練輪數時，不妨先判斷目前卡在哪一端：訓練誤差就降不下來，多半是 Bias 的問題；訓練表現好、測試表現差，那就是 Variance 在作祟。

### 參考資料

- [Understanding the Bias-Variance Tradeoff | by Seema Singh | Towards Data Science](https://towardsdatascience.com/understanding-the-bias-variance-tradeoff-165e6942b229)
- [What is the tradeoff between Bias and Variance? (educative.io)](https://www.educative.io/edpresso/what-is-the-tradeoff-between-bias-and-variance)

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "一個簡單的訓練資料集",
    "why_used": "呈現文中舉例的 5 筆身高體重樣本在 2 維平面上的分佈，讓讀者先看到資料長什麼樣子，後面談 Bias 才有依據。",
    "agent_match_hint": "一張 2 維散佈圖，橫軸身高、縱軸體重，圖上只有 5 個資料點。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "利用這 5 個樣本訓練出來的模型",
    "why_used": "說明訓練出來的模型是一條直線，並鋪陳出模型輸出與正確答案有落差這件事。",
    "agent_match_hint": "同樣的 5 點散佈圖，多了一條穿過資料點的紅色直線。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "框框呈現的是模型的輸出與正確答案的誤差",
    "why_used": "把 Bias 的定義視覺化，直接標出每個樣本的預測值與正確答案之間的差距。",
    "agent_match_hint": "散佈圖加紅色直線，資料點與直線之間以灰色方框標示誤差。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "訓練模型精準的預測每一個樣本",
    "why_used": "呈現一個完美擬合所有訓練樣本的複雜模型，作為導入 Variance 與 Overfitting 的例子。",
    "agent_match_hint": "散佈圖上一條劇烈彎曲的曲線，剛好通過全部 5 個資料點。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Bias-Variance 與 Underfitting-Overfitting 的關係 [source: Towards Data Science]",
    "why_used": "整理 Bias、Variance 的高低組合，並對應到 Underfitting 與 Overfitting 兩種狀況。",
    "agent_match_hint": "常見的射靶式示意圖或對照圖，分別呈現高低 Bias 與高低 Variance 的組合。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Bias-Variance Tradeoff 的意義 [source: scott.fortmann-roe.com]",
    "why_used": "說明 Bias 與 Variance 隨模型複雜度反向變化，Total Error 因此呈 U 型，存在一個最小值。",
    "agent_match_hint": "折線圖，橫軸為模型複雜度，包含遞減的 Bias 曲線、遞增的 Variance 曲線與 U 型的 Total Error 曲線。"
  }
]
```
