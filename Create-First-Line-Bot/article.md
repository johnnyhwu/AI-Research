# LINE Bot 教學：打造第一個 Echo Bot

## 前言

LINE 在全台擁有超過 2000 萬的使用者，商家與企業也普遍透過 LINE Bot 強化線上的銷售通路。這篇文章會帶著初學者做出第一個 LINE 聊天機器人 —— Echo Bot，也就是你傳什麼，它就回你什麼。

功能聽起來很陽春，但要讓這句話真的從手機送到伺服器再回到手機，中間該接的東西一個都不能少：SDK、Channel 憑證、Webhook、以及一個能接住 LINE 打過來的 HTTP 請求的 Function。把 Echo Bot 跑通，等於一次把 LINE Bot 的骨架摸過一遍，之後要做的功能都是在這個骨架上長出來的。

實作上會用 Python 搭配 Django 當後端，並把應用程式部署到 Heroku，讓任何人都能跟這個 Bot 互動。開始之前，有兩件前置作業要先完成（前幾篇文章有寫）：

- 建立 Django 環境，並且成功部署到 Heroku（Heroku 的免費方案已於 2022 年底終止，現在需要付費方案或改用其他 PaaS）
- 成為 LINE Developer，並建立一個 Messaging API Channel

## Step 1：安裝 line-bot-sdk 套件

上面兩件事做完，Coding 的前置作業就算準備好了。首先在虛擬環境中安裝開發 LINE Bot 的必要套件：

```bash
pip install line-bot-sdk
```

這個套件是 LINE 官方提供的 Python SDK，後面用到的 API 呼叫、簽章驗證、訊息物件都由它包好，不需要自己刻 HTTP 請求。

## Step 2：取得 LINE Channel Secret 與 Access Token

LINE Bot API 要能正常運作，得先拿到前面建立的那個 Channel 的兩把鑰匙：Channel Secret 與 Channel access token。前者用來驗證「這個請求真的是 LINE 發出來的」，後者則是我們主動呼叫 LINE API（例如回訊息）時的身分證明。

進入 LINE Developers 頁面登入 Console，可以看到已經新增的 Channel。點進去後滑到頁面最下方，就會看到 **Channel Secret**，把它複製下來。

回到 Django 專案打開 `settings.py`，在第 25 行左右可以找到 `SECRET_KEY` 變數，在它下方新增一個變數存放 LINE Channel Secret：

```python
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'YOUR_KEY'
LINE_CHANNEL_SECRET = 'YOUR_KEY' # Add this line
```

接著回到 Console，進入 Messaging API 分頁。

![LINE Developers Console 中 Messaging API 分頁的設定畫面](img-001)
*LINE Messaging API 頁面*

滑到頁面最下方找到 **Channel access token**，如果還沒 issue 過就先按下 issue，再把生成的 token 複製下來。回到 `settings.py`，同樣新增一個變數來存放它：

```python
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'YOUR_KEY'
LINE_CHANNEL_SECRET = 'YOUR_KEY'
LINE_CHANNEL_ACCESS_TOKEN = 'YOUR_KEY' # Add this line
```

這兩個值等同於 Bot 的帳號密碼，實務上建議放進環境變數而不是直接寫死在 `settings.py` 裡，尤其專案要 push 到公開的 repository 時。

## Step 3：指定 Webhook URL

同樣在 Messaging API 分頁下，可以看到設定 Webhook URL 的欄位：

![LINE Messaging API 分頁中填寫 Webhook URL 的欄位](img-002)
*Webhook 設定*

把 Django App 部署到 Heroku 之後，會拿到一個可以存取這個 App 的 URL。我們在這個 URL 後面加上 `callback`，當成 Webhook URL 填進去。當 LINE Bot 收到使用者的訊息，LINE 的伺服器就會把資料 POST 到這個 URL。

換句話說，Bot 不是主動去問 LINE「有沒有新訊息」，而是 LINE 主動把事件推過來。所以我們接下來要做的，就是把這個 URL map 到一個 Function，讓它負責處理 LINE POST 過來的資料。

## Step 4：指定 callback URL 所對應到的 Function

打開 `urls.py`，多 import 以下套件，記得把 `myapp` 換成自己建立的 app 名稱：

```python
from django.contrib import admin
from django.urls import path
from django.conf.urls import url # Add this line
from myapp import views # Add this line
```

接著在 `urlpatterns` list 中，指定 `callback` 這個 URL 對應到 `views.py` 裡的 `callback` Function：

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^callback', views.callback) # Add this line
]
```

## Step 5：新增 callback Function

最後要在 `views.py` 中新增 `callback` Function，來處理 LINE Bot POST 過來的資料。先載入需要的套件：

```python
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextSendMessage
```

接著用剛剛在 `settings.py` 中定義的 `LINE_CHANNEL_SECRET` 與 `LINE_CHANNEL_ACCESS_TOKEN`，建立 `LineBotApi` 與 `WebhookParser` 物件：

```python
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
```

然後新增 `callback` Function：

```python
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

這段程式碼的重點是先取得 LINE Bot POST 過來的資料，再透過 `parser` 解析出其中包含的「事件」。如果事件屬於 `MessageEvent`，也就是使用者向 LINE Bot 傳送了訊息，Bot 就回傳一段文字，內容正是使用者剛剛傳來的訊息，Echo 的行為就是這樣來的。

幾個細節值得先知道，之後除錯會少走冤枉路：

- `@csrf_exempt`：請求是 LINE 的伺服器打進來的，不會帶 Django 的 CSRF token，不加這行會直接被擋掉。
- `HTTP_X_LINE_SIGNATURE` 與 `parser.parse()`：LINE 會用 Channel Secret 對請求內容簽章，`parse()` 驗不過就丟 `InvalidSignatureError`，這裡直接回 403。這道檢查是為了防止別人偽造請求打你的 endpoint。
- `event.reply_token`：回覆訊息用的一次性 token，只能用一次，而且有時效，所以要在收到事件的當下就回覆。

## Step 6：將 Django 重新部署到 Heroku 上

最後一步是把所有修改部署上去。因為多裝了 `line-bot-sdk` 套件，所以必須重新產生 `requirements.txt`：

```bash
pip freeze > requirements.txt
```

再把整個專案 push 到 Heroku：

```bash
git push heroku master
```

部署完成後，透過 LINE Bot 的 QR Code 把它加為好友，並傳一則訊息給它。如果它回覆一模一樣的內容，就表示整條路都通了。以下是範例 Echo Bot 的 QR Code：

![範例 Echo Bot 的加好友 QR Code](img-003)
*掃描 QR Code 將 LINE Bot 加為好友*

如果沒有收到回覆，最常見的原因有三個：Webhook URL 沒有打開「Use webhook」的開關、URL 結尾少了 `callback`、或是 Channel Secret／access token 貼錯。可以先到 Heroku 看 log 確認請求有沒有真的進到 Django。

## 結論

這篇從安裝 SDK、設定 Channel 憑證、指定 Webhook URL，一路做到寫出 `callback` Function 並重新部署，完成了第一個 LINE Bot —— Echo Bot。它會把使用者傳來的訊息原封不動回傳。

Echo Bot 的功能很簡單，但整條「LINE 推事件進來、Django 驗簽章、解析事件、回覆訊息」的流程已經完整走過一次。之後要做的各種 LINE Bot 功能，差別多半只在於 `callback` 裡怎麼判斷事件、回什麼樣的訊息而已，這個起手式會一直用得到。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "LINE Messaging API 頁面",
    "why_used": "指出 Channel access token 是在 LINE Developers Console 的 Messaging API 分頁取得，讓讀者知道該往哪一頁找。",
    "agent_match_hint": "LINE Developers Console 後台的畫面截圖，頁面標題為 Messaging API 的設定分頁。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Webhook 設定",
    "why_used": "對應設定 Webhook URL 的步驟，讓讀者確認自己找到的是同一個欄位。",
    "agent_match_hint": "後台截圖，畫面中有一個可填入 Webhook URL 的輸入欄位與相關開關。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "掃描 QR Code 將 LINE Bot 加為好友",
    "why_used": "提供範例 Echo Bot 的加好友入口，讓讀者可以直接實測成果。",
    "agent_match_hint": "一張黑白方塊的 QR Code 圖片，用於加 LINE 好友。"
  }
]
```
