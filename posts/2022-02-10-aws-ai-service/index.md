---
title: AWS AI Service 介紹
date: '2022-02-10T14:09:09'
lastmod: '2022-02-21T03:40:09'
slug: aws-ai-service
draft: false
categories:
- 其他
tags:
- AWS
description: 前言 & 概述 AWS 全名為 Amazon Web Service，是一個雲端運算平台。向世界提供許多雲端技術與應用。其中，在機器學習方面，更是有許多厲害的工具。從上圖我們可以發現，AWS
  在 Machine Learning 領域的產品大致可以分為五個面向：AI Services、ML Services、ML Infrastructure、Frameworks
  與 “Getting Sarted”。 在本文中，我將聚焦於 AWS 所提供的 AI Services！ AWS AI Services 如上圖所示，AWS 所提供的
  AI Services 主要分為 13 個應用領域。透過 AWS 的 AI Services，開發者不需要經過「機器學習五步驟」就能直接使用 AI 的服務。使其應用程式增添智慧！
  在接下來的文章中，我們將會依序了解每一個使用情境的意義！ HEALTH AI 如果你有過看病的經驗，不知道有沒有印象，醫生每次在幫你看診時，同時手指不停的在敲鍵盤。實際上，醫生會將診斷內容打成文字檔，作為開藥的依據。Amazon
  Transcrbe Medical 正是為了解決這項問題。Amazon Transcrbe Medical 透過 Speech Recognition 的技術，將醫生與病人的聲音轉為文字檔，讓醫生省去打鍵盤記錄的工作，將注意力放在病人身上。
  INDUSTRIAL AI 在工業方面，Amazon […]
aliases:
- /others/aws-ai-service/
original_url: http://54.150.87.240/others/aws-ai-service/
wp_id: 492
images:
- images/aws-au-service.jpeg
- images/feature-image.jpeg
- images/machine-learning-on-aws.jpeg
---

![](images/feature-image.jpeg)

source: AWS

## 前言 & 概述

![machine learning on aws](images/machine-learning-on-aws.jpeg)

AWS 在機器學習領域的產品大致分為 5 個面向 [source: AWS Machine Learning Foundation Course on Udacity]

AWS 全名為 Amazon Web Service，是一個雲端運算平台。向世界提供許多雲端技術與應用。其中，在機器學習方面，更是有許多厲害的工具。從上圖我們可以發現，AWS 在 Machine Learning 領域的產品大致可以分為五個面向：AI Services、ML Services、ML Infrastructure、Frameworks 與 “Getting Sarted”。

在本文中，我將聚焦於 AWS 所提供的 AI Services！

## AWS AI Services

![aws ai service](images/aws-au-service.jpeg)

AWS 所提供的 AI 服務以上這些 [source: AWS Machine Learning Foundation Course on Udacity]

如上圖所示，AWS 所提供的 AI Services 主要分為 13 個應用領域。透過 AWS 的 AI Services，開發者不需要經過「[機器學習五步驟](http://54.150.87.240/topics/machine-learning-basic-concept/)」就能直接使用 AI 的服務。使其應用程式增添智慧！

在接下來的文章中，我們將會依序了解每一個使用情境的意義！

- **HEALTH AI**

如果你有過看病的經驗，不知道有沒有印象，醫生每次在幫你看診時，同時手指不停的在敲鍵盤。實際上，醫生會將診斷內容打成文字檔，作為開藥的依據。[Amazon Transcrbe Medical](https://aws.amazon.com/tw/transcribe/medical/) 正是為了解決這項問題。[Amazon Transcrbe Medical](https://aws.amazon.com/tw/transcribe/medical/) 透過 Speech Recognition 的技術，將醫生與病人的聲音轉為文字檔，讓醫生省去打鍵盤記錄的工作，將注意力放在病人身上。

- **INDUSTRIAL AI**

在工業方面，[Amazon Monitron](https://aws.amazon.com/tw/transcribe/medical/) 透過 Sensor 與 Data Analysis Platform 預測機器什麼時候會發生問題。若能提前預測機器 Crash 的時間，將能夠事先採取措施，避免公司因為機器問題而增加成本。

- **ANOMALY DETECTION**

“Anomaly” 中文稱文「異常」，也就是「異常偵測」。[Amazon Lookout for Metrics](https://aws.amazon.com/tw/lookout-for-metrics/) 可以用來偵測商業數據 (EX. 銷售數據、顧客滿意度) 中的「異常」。

- **CHATBOT**

透過 [Amazon Lex](https://aws.amazon.com/tw/lex/) 可以快速的在應用程式中導入聊天機器人。

- **PERSONALIZATION**

在個人化的精準推薦領域，[Amazon Personalize](https://aws.amazon.com/tw/personalize/) 讓開發者建立一個精準的推薦系統。常用的領域包含零售、娛樂與媒體平台。

- **FORECASTING**

[Amazon Forecast](https://aws.amazon.com/tw/forecast/) 提供更精準的時間序列預測服務，幫助企業預測未來數據的變化。舉例來說，下個季度的銷售額、產品需求量等等。

- **FRAUD**

[Amazon Fraud Detector](https://aws.amazon.com/tw/fraud-detector/) 可用於偵測線上詐騙。線上詐騙類型多樣，便存在於以下過程中：帳戶註冊、線上付款等等。

- **CODE DEVELOPMENT**

[Amazon CodeGuru](https://aws.amazon.com/tw/codeguru/) 幫助開發者提升程式碼的品質，並且找出 “Expensive” Code 來提升程式效能。

- **VISION**

在視覺方面，[Amazon Rekognition](https://aws.amazon.com/tw/rekognition/?blog-cards.sort-by=item.additionalFields.createdDate&blog-cards.sort-order=desc) 能夠迅速定位出照片與影片中的人臉。

- **SPEECH**

[Amazon Polly](https://aws.amazon.com/tw/polly/) 能夠將文字轉成逼真的說話方式。

- **TEXT**

[Amazon Textract](https://aws.amazon.com/tw/textract/) 能夠從照片、掃描後的文檔中萃取出文字。相較於一般的 OCR 技術，Amazon Textract 能夠識別、理解表格中的資料。

- **CONTACT CENTER**

[Contact Lens](https://aws.amazon.com/tw/connect/contact-lens/) 能夠分析客服人員與顧客之間的對話內容，並從對話中分析當時的情緒、問題，最後再將對話內容分類歸檔。

- **SEARCH**

[Amazon Kendra](https://aws.amazon.com/tw/kendra/) 是一項智慧搜尋服務，能幫助使用者快速的從整個網站中，搜尋出問題的答案。

## 結語

在本篇文章中，我簡單介紹 AWS 所提供的 AI Services，並說明每一項 AI Services 的代表性工具與意義。在下一篇文章中，將會介紹 AWS ML Services。
