# AWS ML Service 介紹

## 前言

![AWS 機器學習服務的主視覺，以 AWS 標誌搭配機器學習相關的圖示呈現。](img-001)
*Machine Learning on AWS [source: AWS Machine Learning Foundation Course on Udacity]*

AWS (Amazon Web Service) 上跟機器學習有關的服務大致可以分成兩層。一層是 [AWS AI Services](https://aws.amazon.com/tw/machine-learning/ai-services/)，這類服務已經把模型訓練好了，開發者直接呼叫 API 就能把影像辨識、語音轉文字這類能力接進自己的應用程式，不必碰任何模型細節。另一層則是 AWS ML Services，代表性的產品是 [Amazon SageMaker](https://aws.amazon.com/tw/sagemaker/)，它服務的對象是要自己準備資料、自己訓練模型的人，目標是把建置、訓練到部署這一整串流程簡化掉。

本文介紹的是後者，並挑三個工具當代表：Amazon SageMaker Studio、Amazon SageMaker Distributed Training 與 Amazon SageMaker Clarify。（本文寫於 2022 年，AWS 這幾年對 SageMaker 的介面與功能命名有過調整，實際操作時請以官方文件為準。）

## Amazon SageMaker Studio

說白了，[Amazon SageMaker Studio](https://aws.amazon.com/tw/sagemaker/studio/) 就是一個專為機器學習打造的 IDE。機器學習的完整流程包含資料集預處理、模型選擇與建立、模型訓練以及模型部署，過去這些步驟往往散落在不同工具裡；SageMaker Studio 把它們統合在同一個介面中，減少在工具之間切換的成本。

- **便利的使用與分享 Notebook**  
  開發機器學習模型時，Jupyter Notebook 幾乎是標準配備。SageMaker Studio 也不例外，只要簡單幾個點擊就能建立 Notebook 開發環境並分享給其他人，而且底層的運算資源會自動調配，不需要自己開機器、裝環境。

- **結構化整理實驗數據**  
  模型建好之後，接下來就是一輪一輪的實驗，可能是改動模型架構，也可能是換一份資料集。SageMaker Studio 會自動把這些實驗的結果排序、統整，用結構化的表格呈現出來，省下自己拿試算表記錄「這次改了什麼、分數是多少」的功夫。

- **內建模型與解決方案**  
  SageMaker Studio 上提供超過 150 種開源的機器學習模型，以及超過 15 種使用情境的解決方案 (例如：Fraud Detection)。如果需求剛好落在這些情境裡，短短幾分鐘內就能把模型建立起來。

- **彈性選擇開發環境**  
  目前主流的深度學習框架主要有三個：TensorFlow、PyTorch 與 MXNet，每個框架又有多種版本可以選。SageMaker Studio 提供多種已經建好的開發環境，當然也可以依自己的喜好建立環境，再把它分享出去。

- **框架效能的最佳化**  
  為了加速模型訓練，通常需要一連串繁複的設定，框架才有辦法真正吃滿電腦的硬體資源 (GPU)。SageMaker Studio 會自動根據可用的硬體資源，替開發者所使用的框架做最佳化。

## Amazon SageMaker Distributed Training

現今所謂 state-of-the-art 的深度學習模型，參數量動輒超過數百萬，不少模型甚至超過數十億。以 2020 年 5 月發布的自然語言模型 GPT-3 為例，它包含了 1750 億個參數。這種規模的模型幾乎不可能塞進單一顆 GPU 訓練，只能透過平行化的技術把工作分散到多顆 GPU 上，也就是所謂的「分散式訓練」(Distributed Training)。

問題是，分散式訓練本身就有技術門檻：資料怎麼切、梯度怎麼同步、節點之間怎麼通訊，每一項都要處理。Amazon SageMaker Distributed Training 的優勢就在這裡，開發者只需要在既有的訓練程式中置入幾行程式碼，就能自動地進行分散式訓練。

它背後靠的是兩種平行化技術，差別在於「切的是什麼」：

- **資料平行化 (Data Parallelism)**：把非常大的資料集拆開，每個 GPU 拿到完整的模型與一部分資料，以 Concurrent 的方式同時訓練，藉此提升訓練速度。
- **模型平行化 (Model Parallelism)**：把非常大的模型拆成許多小部分，分散到多個 GPU 上訓練。當模型大到單顆 GPU 的記憶體放不下時，這是必要手段。

## Amazon SageMaker Clarify

訓練資料的組成，對模型訓練完的品質有很大的影響。舉例來說，如果模型要針對「不同年齡層」的人做預測，而訓練資料中多數是「壯年人」，那麼模型對「老年人」或「孩童」的預測準確率就會明顯偏低。這就是 Imbalanced Data 造成的 Model Bias，讓模型的預測結果帶有「偏見」。

Amazon SageMaker Clarify 要解決的正是這件事：幫開發者看見資料與模型中存在的 Bias，藉此更理解模型實際上的行為。它從兩個方向切入。

針對「訓練資料」，Clarify 結合 Amazon SageMaker Data Wrangler 辨識資料集中的 Bias。我們可以指定想觀察的 Attribute (例如年齡、性別)，Clarify 就會針對它進行分析，並以報表的形式呈現分析結果。

針對「模型」，Clarify 則結合 Amazon SageMaker Experiments，分析訓練完的模型在測試資料集中不同 Attribute 上產生的 Bias。例如：模型是不是特別容易把「老年人」的樣本分到某一個特定類別。最後同樣以視覺化的報表把分析結果呈現出來。

## 結論

本文簡單說明了 AWS ML Services 是什麼，並以三項工具作為代表：

- **Amazon SageMaker Studio**：在一個專為機器學習打造的 IDE 中，完成開發的各項流程。
- **Amazon SageMaker Distributed Training**：用資料平行化與模型平行化處理大規模的資料集與模型。
- **Amazon SageMaker Clarify**：觀察資料集與模型中存在的 Bias。

這三項工具剛好對應到機器學習專案裡最容易卡關的三個環節：環境、算力，以及資料品質。如果手上的專案已經開始遇到這幾類問題，可以從對應的服務先看起。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Machine Learning on AWS [source: AWS Machine Learning Foundation Course on Udacity]",
    "why_used": "作為文章開場的主視覺，點出本文主題是 AWS 上的機器學習服務。",
    "agent_match_hint": "一張課程用的主視覺圖，以 AWS 標誌搭配機器學習相關元素構成，取自 Udacity 的 AWS Machine Learning Foundation 課程。"
  }
]
```
