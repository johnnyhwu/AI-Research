---
title: 'LINE Bot 教學 : 打造第一個 Echo Bot'
date: '2022-02-09T11:54:54'
lastmod: '2022-06-18T03:22:07'
slug: create-first-line-bot
draft: false
categories:
- 其他
tags:
- ChatBot
- Django
- Heroku
- LINE
- Python
description: '前言 & 概述 LINE 在全台擁有超過 2000 萬的使用者，商家與企業更是透過 LINE Bot 強化線上銷售通路。本文將帶著初學者打造第一個
  LINE 聊天機器人 —— Echo Bot，Echo Bot 將會 Echo 使用者所說的話！看似簡單的 LINE Bot，當中卻包含許多實作的細節。 我們將以
  Python 實作，以 Django 作為後端，並將應用程式部署到 Heroku 上，讓任何人都可以與 LINE Bot 互動。因此，在開始本文之前，別忘了先：
  建立 Django 環境且成功部署到 Heroku 成為 LINE Developer 並建立 Messaging API Channel Step 1 : 安裝
  line-bot-sdk 套件 完成了上述兩步驟後，相當於完成了 Coding 的前置作業。首先，我們需要在虛擬環境中安裝開發 LINE Bot 的必要套件。
  pip […]'
aliases:
- /others/create-first-line-bot/
original_url: http://54.150.87.240/others/create-first-line-bot/
wp_id: 481
images:
- images/LINE-Messaging-API.jpeg
- images/feature-image-10.jpg
- images/qrcode.jpeg
- images/webhook-setting.jpeg
---

![](images/feature-image-10.jpg)

source: Pixabay

## 前言 & 概述

LINE 在全台擁有超過 2000 萬的使用者，商家與企業更是透過 LINE Bot 強化線上銷售通路。本文將帶著初學者打造第一個 LINE 聊天機器人 —— Echo Bot，Echo Bot 將會 Echo 使用者所說的話！看似簡單的 LINE Bot，當中卻包含許多實作的細節。

我們將以 Python 實作，以 Django 作為後端，並將應用程式部署到 Heroku 上，讓任何人都可以與 LINE Bot 互動。因此，在開始本文之前，別忘了先：

- [建立 Django 環境且成功部署到 Heroku](http://54.150.87.240/others/deploy-django-on-heroku-macos/)
- [成為 LINE Developer 並建立 Messaging API Channel](http://54.150.87.240/others/create-line-bot/)

## Step 1 : 安裝 line-bot-sdk 套件

完成了上述兩步驟後，相當於完成了 Coding 的前置作業。首先，我們需要在虛擬環境中安裝開發 LINE Bot 的必要套件。

```
pip install line-bot-sdk
```

## Step 2 : 取得 LINE Channel Secret 與 Access Token

接著，為了讓 LINE Bot API 能夠正常運作，我們需要取得前面所建立的 Channel 的 Secret 與 Access Token。進入 LINE Developer 頁面登入 Console 後，我們可以看到我們已經新增的 Channel。點選 Channel 進入設定頁面，滑到頁面最下方，我們可以看到 **Channel Secret** 的資訊。請將 Channel Secret 複製下來。

接著，回到 Django 專案，打開 settings.py。在第 25 行左右，可以看到 **SECRET\_KEY** 變數。請在下方新增一個變數來存放 **LINE Channel Secret**。

```
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'YOUR_KEY'
LINE_CHANNEL_SECRET = 'YOUR_KEY' # Add this line
```

接著，進入 Messaging API 分頁。

![LINE Messaging API](images/LINE-Messaging-API.jpeg)

LINE Messaging API 頁面

滑到頁面最下方，找到 **Channel access token**，如果還沒 issue 需要先 issue。並將生成的 Channel access token 複製下來。回到 settings.py，再新增一個變數來儲存 Channel access token。

```
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'YOUR_KEY'
LINE_CHANNEL_SECRET = 'YOUR_KEY'
LINE_CHANNEL_ACCESS_TOKEN = 'YOUR_KEY' # Add this line
```

AD

## Step 3 : 指定 Webhook URL

同樣在 Messaging API 的分頁下，我們可以看到設定 Webhook URL 的欄位：

![webhook setting](images/webhook-setting.jpeg)

Webhhok 設定

當我們[將 Django App 部署到 Heroku](http://54.150.87.240/others/deploy-django-on-heroku-macos/) 後，會得到一個 URL 來存取我們的 Django App。我們將這個 URL 後面再加上 “callback” 作為 Webhook URL。當 LINE Bot 收到訊息後，會將 Data “POST” 到這個 URL。因此，我們需要將此 URL Map 到一個 Function 來處理 LINE Bot POST 的資料。

## Step 4 : 指定 “callback” URL 所對應到的 Function

接著，打開 urls.py，並多 import 以下套件，記得將 “myapp” 換成自己建立的 app 名稱。

```
from django.contrib import admin
from django.urls import path
from django.conf.urls import url # Add this line
from myapp import views # Add this line
```

接著，在 urlpatterns list 中指定 “callback” URL 下對應到 views.py 中的 “callback” Function。

```
urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^callback', views.callback) # Add this line
]
```

## Step 5 : 新增 “callback” Function

最後，我們要在 views.py 中新增 “callback” Function，來處理 LINE Bot 所 POST 的 Data。首先，在 views.py 中載入以下套件：

```
from django.conf import settings from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextSendMessage
```

接著，利用我們在 settings.py 中定義的 LINE\_CHANNEL\_SECRET 與 LINE\_CHANNEL\_ACCESS\_TOKEN 建立 LineBotApi 與 WebhookParsr Object。

```
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
```

最後，新增 “callback” Function：

```
@csrf_exempt
def callback(request):
    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')

        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()

        for event in events:
            if isinstance(event, MessageEvent):
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=event.message.text))

        return HttpResponse()

    else:
        return HttpResponseBadRequest()
```

在上述程式碼中，主要先取得 LINE Bot 所 POST 的 Data，並透過 parser 解析其中所包含的「事件」。如果事件屬於 MessageEvent，也就是使用者向 LINE Bot 傳送訊息，LINE Bot 則回傳一段文字。內容即為使用者所傳送的訊息。

AD

## Step 6 : 將 Django 重新部署到 Heroku 上

最後一步，我們需要將我們的所有修改部署到 Heroku 上！因為我們有另外安裝 line-bot-sdk 套件，所以必須重新產生 requirements.txt。

```
pip freeze > requirements.txt
```

再將整個專案 push 到 Heroku 上！

```
git push heroku master
```

最後，透過這個 LINE Bot 的 QR Code 將 LINE Bot 加為好友，並向他傳送訊息，如果他回覆一模一樣的訊息，則表示成功囉！以下是我所建立的範例 Echo Bot：

![](images/qrcode.jpeg)

掃描 QR Code 將 LINE Bot 加為好友

## 結語

在本文中，我們學習如何建立第一個 LINE Bot —— Echo Bot，重複使用者所傳送的訊息。Echo Bot 功能簡單，是學習 LINE Bot 的第一個起手式！
