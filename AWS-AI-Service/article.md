# AWS AI Service 介紹

## 前言

AWS 全名為 Amazon Web Service，是 Amazon 旗下的雲端運算平台，提供從運算、儲存到機器學習的各種雲端服務。其中機器學習這一塊，AWS 的工具數量多到第一次看會有點眼花。

![AWS 在機器學習領域的產品分類示意圖，由上而下分為五個層級。](img-001)
*AWS 在機器學習領域的產品大致分為 5 個面向 [source: AWS Machine Learning Foundation Course on Udacity]*

從上圖可以看到，AWS 在 Machine Learning 領域的產品大致分成五個面向：AI Services、ML Services、ML Infrastructure、Frameworks 與 Getting Started。這五層由上而下，抽象程度越來越低、要自己動手的部分越來越多。最上層的 AI Services 是包裝好的現成服務，呼叫 API 就能用；越往下走，就越接近自己訓練模型、自己管理運算資源。

本文聚焦在最上層的 AI Services，說明它涵蓋哪些應用領域，以及每個領域的代表性服務在做什麼。

## AWS AI Services

![AWS AI Services 的 13 個應用領域與各自代表服務的一覽圖。](img-002)
*AWS 所提供的 AI Services 一覽 [source: AWS Machine Learning Foundation Course on Udacity]*

如上圖所示，AWS 的 AI Services 依使用情境分成 13 個應用領域。它最大的價值在於：開發者不需要自己走完一遍「機器學習五步驟」（定義問題、準備資料、訓練模型、評估模型、模型推論），就能直接把 AI 的能力接進自己的應用程式裡。模型是 AWS 訓練好的，你要做的只是準備輸入、接收輸出。

說白了，這一層適合的情境是「我的問題別人已經解過了」。如果你的需求是語音轉文字、人臉偵測、商品推薦這類通用任務，自己從頭訓練模型多半不划算；反過來說，如果問題和你的業務資料高度綁定，那才需要往下一層的 ML Services 走。

以下依序看過這 13 個應用領域。

- **HEALTH AI**

如果你有看病的經驗，應該對這個畫面不陌生：醫生一邊問診，手指一邊不停敲鍵盤。醫生必須把診斷內容打成文字檔，作為開藥的依據，注意力因此被鍵盤分走一半。[Amazon Transcribe Medical](https://aws.amazon.com/tw/transcribe/medical/) 就是為了解決這件事，它用 Speech Recognition 技術把醫生與病人的對話轉成文字檔，省去手動記錄的工作，讓醫生把注意力放回病人身上。

- **INDUSTRIAL AI**

在工業場域，[Amazon Monitron](https://aws.amazon.com/tw/monitron/) 透過 Sensor 搭配資料分析平台，預測機器什麼時候會出問題。能提前預測機器 crash 的時間，就能事先安排維修，避免整條產線停擺造成的損失。

- **ANOMALY DETECTION**

Anomaly 中文是「異常」，這個領域講的就是異常偵測。[Amazon Lookout for Metrics](https://aws.amazon.com/tw/lookout-for-metrics/) 可以用來偵測商業數據中的異常，例如銷售數據突然下滑、顧客滿意度突然掉一截。

- **CHATBOT**

透過 [Amazon Lex](https://aws.amazon.com/tw/lex/)，可以快速在應用程式中導入聊天機器人。

- **PERSONALIZATION**

在個人化精準推薦這一塊，[Amazon Personalize](https://aws.amazon.com/tw/personalize/) 讓開發者建立自己的推薦系統，常見的應用領域包含零售、娛樂與媒體平台。

- **FORECASTING**

[Amazon Forecast](https://aws.amazon.com/tw/forecast/) 提供時間序列預測服務，幫助企業預測未來數據的變化，像是下個季度的銷售額、產品需求量。

- **FRAUD**

[Amazon Fraud Detector](https://aws.amazon.com/tw/fraud-detector/) 用於偵測線上詐騙。線上詐騙的型態很多樣，帳戶註冊、線上付款等環節都可能是下手的地方。

- **CODE DEVELOPMENT**

[Amazon CodeGuru](https://aws.amazon.com/tw/codeguru/) 幫助開發者提升程式碼品質，並找出所謂的 "expensive" code，也就是那些拖慢效能的段落。

- **VISION**

視覺方面，[Amazon Rekognition](https://aws.amazon.com/tw/rekognition/) 能夠迅速定位出照片與影片中的人臉。

- **SPEECH**

[Amazon Polly](https://aws.amazon.com/tw/polly/) 能夠把文字轉成逼真的說話聲音。

- **TEXT**

[Amazon Textract](https://aws.amazon.com/tw/textract/) 能夠從照片、掃描後的文件中萃取出文字。相較於一般的 OCR 技術，Textract 的差別在於它看得懂表格結構，能把表格中的資料對應關係一併取出來。

- **CONTACT CENTER**

[Contact Lens](https://aws.amazon.com/tw/connect/contact-lens/) 能夠分析客服人員與顧客之間的對話內容，從對話中判讀當下的情緒與問題，最後再把對話內容分類歸檔。

- **SEARCH**

[Amazon Kendra](https://aws.amazon.com/tw/kendra/) 是一項智慧搜尋服務，能幫助使用者從整個網站中快速找出問題的答案。

一次看完 13 項容易記不住，這裡整理成一張對照表方便日後查找：

| 應用領域 | 代表服務 | 一句話用途 |
|---|---|---|
| HEALTH AI | Amazon Transcribe Medical | 醫療對話轉文字 |
| INDUSTRIAL AI | Amazon Monitron | 機器故障預測 |
| ANOMALY DETECTION | Amazon Lookout for Metrics | 商業數據異常偵測 |
| CHATBOT | Amazon Lex | 聊天機器人 |
| PERSONALIZATION | Amazon Personalize | 個人化推薦系統 |
| FORECASTING | Amazon Forecast | 時間序列預測 |
| FRAUD | Amazon Fraud Detector | 線上詐騙偵測 |
| CODE DEVELOPMENT | Amazon CodeGuru | 程式碼品質與效能檢查 |
| VISION | Amazon Rekognition | 影像與影片人臉偵測 |
| SPEECH | Amazon Polly | 文字轉語音 |
| TEXT | Amazon Textract | 文件文字與表格萃取 |
| CONTACT CENTER | Contact Lens | 客服對話分析 |
| SEARCH | Amazon Kendra | 智慧搜尋 |

（這份清單反映的是 2022 年當時的服務組合，AWS 的 AI 產品線更新頻繁，實際使用前建議再對一次官方文件。）

## 結論

本篇介紹了 AWS 提供的 AI Services，說明這 13 個應用領域各自的代表性服務與適用情境。這一層的重點在於「不用自己訓練模型」，把通用的 AI 能力當成 API 來呼叫。下一篇文章將往下一層走，介紹需要自己處理資料與模型的 AWS ML Services。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "AWS 在機器學習領域的產品大致分為 5 個面向 [source: AWS Machine Learning Foundation Course on Udacity]",
    "why_used": "支撐前言中說明 AWS 機器學習產品分為五個面向的段落，讓讀者先建立整體輪廓，再理解本文聚焦的 AI Services 位在最上層。",
    "agent_match_hint": "一張分層堆疊示意圖，由上而下依序為 AI Services、ML Services、ML Infrastructure、Frameworks 與 Getting Started 五層。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "AWS 所提供的 AI Services 一覽 [source: AWS Machine Learning Foundation Course on Udacity]",
    "why_used": "支撐 AWS AI Services 一節，呈現 13 個應用領域與各自代表服務的全貌，作為後續逐項說明的索引。",
    "agent_match_hint": "一張以格狀排列的服務總覽圖，列出十幾個 AI 應用領域名稱與對應的 Amazon 服務圖示。"
  }
]
```
