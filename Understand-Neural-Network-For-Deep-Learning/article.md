# Deep Learning 第一站：Neural Network 名詞介紹

## 前言

在前一篇談 Sigmoid Neuron 的文章中，我們把焦點放在「單一顆神經元」上：它跟 Perceptron 哪裡像、哪裡不同，以及 Sigmoid 函數最重要的「平滑」特性。正因為輸出是平滑變化的，人工神經網路 (Artificial Neural Network) 才有辦法一點一點調整參數，讓結果愈來愈接近正確答案。

這篇文章把視角拉高一層。我們不再看單一個人工神經元 (Artificial Neuron)，而是看整個 Neural Network：它由哪些部分組成、Input 與 Output Layer 該怎麼設計，以及 Feedforward 和 Recurrent 這兩種架構差在哪裡。這些名詞是後續所有深度學習 (Deep Learning) 內容的共同語言，先把它們弄清楚，之後看到任何模型架構圖都不會卡住。

## Neural Network 的基本組成元素

![一個三層的神經網路示意圖，左邊是輸入層的神經元，中間一層隱藏層，右邊是輸出層，層與層之間以連線相接。](img-001)
*3 個 Layer 的 Neural Network [source: Neural Networks and Deep Learning]*

一個最基本的 Neural Network 大致就長成上圖這樣：一排一排的圓圈 (Neuron)，由左往右用線連起來。

依照慣例，我們會把最左邊的輸入也用圈圈包起來，讓它看起來像一顆 Neuron，稱為 Input Neuron；這些 Neuron 自然形成一層，就是 **Input Layer**。最右邊的那一層稱為 **Output Layer**，裡頭的 Neuron 稱為 Output Neuron。夾在中間的則統稱 **Hidden Layer**。

Hidden Layer 這個名字聽起來有點神秘，其實沒那麼玄。它想表達的只有一件事：這一層既不是 Input 也不是 Output，如此而已。

上圖的 Neural Network 中，Input、Output、Hidden Layer 各只有一層。而現代大部分的 Neural Network 會堆上很多層 Hidden Layer，形成一個很「深」的網路，這也是 **Deep Neural Network** 這個稱呼的由來。讓 Deep Neural Network 透過 Learning Algorithm 反覆調整內部參數、慢慢輸出正確結果的整個過程，就叫做 **Deep Learning**。

![另一個神經網路示意圖，由一層輸入層、兩層隱藏層與一層輸出層組成，相鄰兩層之間的神經元互相連接。](img-002)
*Neural Network 的基本組成：Input Layer、Output Layer 與 Hidden Layer [source: Neural Networks and Deep Learning]*

上圖是另一個例子，這次擁有兩層 Hidden Layer。

這裡有個名詞要特別提醒：這種由很多層堆疊而成的 Neural Network，經常被稱為 Multilayer Perceptron，簡稱 MLP。但前一篇介紹 Sigmoid Neuron 的文章已經提過，現代神經網路裡的 Neuron 通常並不是 Perceptron。為了避免觀念混淆，本系列文章一律稱它為 Neural Network，不使用 Multilayer Perceptron 這個講法。

## Input 與 Output Layer 的設計

比起 Hidden Layer，Input 與 Output Layer 的設計直觀許多，因為它們幾乎是由問題本身直接決定的。拿一個經典任務來看：手寫數字圖像分類。輸入一張手寫數字的圖片，網路要輸出這張圖片屬於 0 到 9 之中的哪一個數字。

Input Layer 最直觀也最常見的做法，是把圖片中每一個像素 (Pixel) 的數值都當成一個 Input Neuron。以一張 28 × 28 的灰階圖片為例，灰階 (Grayscale) 表示這張圖只由一個通道 (Channel) 組成，不像一般看到的彩色圖片是由 Red、Blue、Green 三個 Channel 組成。因此整張圖總共有 28 × 28 = 784 個數值，每個數值都代表圖片中某一個位置的資訊。把每個數值各配一個 Neuron，就得到一個包含 784 個 Neuron 的 Input Layer。

Output Layer 則看你希望網路回答什麼。這個任務的答案是 0 到 9，所以讓每個數字各對應一個 Output Neuron，總共 10 個。當 Neural Network 認為這張圖是「8」時，代表「8」的那個 Output Neuron 數值就應該大於 0.5。這樣就得到一個包含 10 個 Neuron 的 Output Layer。

至於 Hidden Layer 的設計，就複雜多了。要疊幾層、每層放幾個 Neuron，往往夾雜著作者的想法與技術，甚至帶有一點「藝術」的氣息，很難單純用幾條規則總結。本系列後續的文章也會介紹一些常見的設計方法。

## Feedforward 與 Recurrent Neural Network

到目前為止討論的 Neural Network，不管用的是 Perceptron 還是 Sigmoid Neuron，都有一個共同特性：前一層的輸出就是下一層的輸入，資訊只往前走，不回頭。這種網路稱為 **Feedforward Neural Network**。

換個角度來看：假設 Feedforward Neural Network 裡有一顆 Sigmoid Neuron (A)，因為網路中沒有任何「Feedback Loop」，A 這一刻算出來的輸出只會往下一層送，不會繞回自己身上。

另一種 Neural Network 則刻意包含了 Feedback Loop，讓資訊也能夠向後 (往 Input Layer 的方向) 傳遞，這種網路稱為 **Recurrent Neural Network**。同樣假設裡面有一顆 Sigmoid Neuron (A)：A 這一刻的輸出會往後傳，等到下一刻，它會連同新的輸入一起再度成為 A 的輸入。結果就是 A 下一刻的輸出，會受到自己上一刻輸出的影響。

兩者的差別整理如下：

| | Feedforward Neural Network | Recurrent Neural Network |
|---|---|---|
| 有無 Feedback Loop | 沒有 | 有 |
| 資訊流向 | 只往前 (Input → Output) | 往前，也能往回傳 |
| 這一刻的輸出 | 只受這一刻的輸入影響 | 還會受到上一刻輸出的影響 |

## 參考資料

- [Neural networks and deep learning](http://neuralnetworksanddeeplearning.com/chap1.html)
- [Multilayer perceptron – Wikipedia](https://en.wikipedia.org/wiki/Multilayer_perceptron)
- [Feed Forward Neural Network Definition | DeepAI](https://deepai.org/machine-learning-glossary-and-terms/feed-forward-neural-network)
- [Feedforward neural network – Wikipedia](https://en.wikipedia.org/wiki/Feedforward_neural_network)

## 結論

這篇文章把視角從單一顆 Artificial Neuron 拉到了整個 Neural Network：認識 Input Layer、Hidden Layer 與 Output Layer 這三個基本組成，看過 Input 與 Output Layer 如何依照問題本身來設計，也弄清楚 Feedforward 與 Recurrent Neural Network 最關鍵的差別就在於有沒有 Feedback Loop。

下一篇文章一樣站在整個 Neural Network 的角度，說明一個完整的 Neural Network 是如何解決「手寫數字圖像分類」這個問題的。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "3 個 Layer 的 Neural Network [source: Neural Networks and Deep Learning]",
    "why_used": "作為介紹 Input Layer、Hidden Layer、Output Layer 三種基本組成元素的視覺依據，讀者可以對照圖上的位置理解每一層的名稱。",
    "agent_match_hint": "一張最基本的神經網路示意圖，共三層：左邊輸入層、中間一層隱藏層、右邊輸出層，神經元以圓圈表示並互相連線。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Neural Network 的基本組成：Input Layer、Output Layer 與 Hidden Layer [source: Neural Networks and Deep Learning]",
    "why_used": "示範一個擁有兩層 Hidden Layer 的 Neural Network，帶出多層堆疊 (也就是常被稱為 MLP) 的情況與命名上的注意事項。",
    "agent_match_hint": "一張神經網路示意圖，比前一張多一層隱藏層，總共是輸入層、兩層隱藏層與輸出層的全連接結構。"
  }
]
```
