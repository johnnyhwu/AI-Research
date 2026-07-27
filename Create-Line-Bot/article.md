# 在 LINE Developers 上建立 LINE Bot

## 前言

LINE 是台灣使用率極高的社群 App，很多商家都會用「[官方帳號](https://tw.linebiz.com/)」經營線上通路，跟客戶保持聯繫。這種官方帳號本質上就是一隻跑在 LINE 上的機器人：它可以自動回覆使用者傳來的訊息，也可以主動推播資訊給使用者。背後撐起這件事的技術，就是 LINE Messaging API。

不過在開始寫程式之前，有一段前置作業跑不掉：註冊 LINE Developers 帳號、建立 Provider 與 Channel，還要把幾個預設開著的自動回覆功能關掉，你的程式才有機會接手回話。這篇文章就是把這段前置流程走完，從零建立一隻 LINE Bot，並做好後續串接程式所需要的設定。

## LINE Messaging API 是什麼

![LINE Bot 與使用者之間透過 LINE Platform 互相傳送訊息的互動流程示意圖。](img-001)
*LINE Bot 與 User 的互動方式 [source: LINE]*

LINE Messaging API 是 LINE 提供給開發者的訊息發送與回覆介面。流程上可以拆成三方：使用者在 LINE App 裡傳訊息給 Bot，訊息會先送到 LINE Platform，LINE Platform 再把這個事件轉發到我們自己的伺服器；我們的程式決定要回什麼，再透過 Messaging API 把回覆送回 LINE Platform，最後才顯示在使用者的聊天室裡。

換句話說，LINE Bot 並不是一個住在 LINE 裡面的程式，而是我們自己架的服務。LINE 只負責把訊息收進來、把回覆送出去。想更完整了解這套 API 的行為，可以參考 [LINE 官方文件](https://developers.line.biz/zh-hant/docs/messaging-api/overview/#line-official-account-plan)。

有了這個概念之後，就可以開始動手了。以下 Step 1 到 Step 4 的流程參考自 LINE 官方教學。（LINE Developers Console 的介面這幾年有改版過，選單位置可能與截圖略有出入，但欄位名稱與流程大致相同。）

## Step 1：申請 LINE Developers 帳號

先到 [LINE Developers](https://developers.line.biz/en/) 網站申請帳號，或直接用既有的 LINE 帳號登入。第一次登入 [LINE Developers Console](https://account.line.biz/login?redirectUri=https%3A%2F%2Fdevelopers.line.biz%2Fconsole%2F) 時，會要求填一些基本資訊（名稱、Email），填完就會進到 Console 主頁。

![LINE Developers Console 的首頁畫面。](img-002)
*LINE Developer Console 頁面 [source: LINE Developer]*

## Step 2：建立 Provider

接著建立一個新的 Provider，這一步只需要輸入名稱。Provider 指的是「提供服務的主體」，可以填你的名字，也可以填公司名稱。它的角色比較像是一個容器：同一個 Provider 底下可以放很多個 Channel，之後要管理多隻 Bot 時會方便很多。

![在 LINE Developers Console 中建立 Provider、輸入 Provider 名稱的畫面。](img-003)
*建立 Provider [source: LINE Developer]*

## Step 3：建立 Channel

Provider 建好之後，在它底下建立 Channel，類型選擇 **Messaging API**。這個 Channel 就可以直接想成是我們的 LINE Bot 本體。

這裡填的 Channel icon 與 Channel name 會直接出現在使用者的 LINE App 裡，也就是使用者看到的頭像與名稱，建議一開始就填成你真正想用的內容。

![建立 Channel 的表單畫面，包含 Channel 類型、名稱與圖示等欄位。](img-004)
*建立 Channel [source: LINE Developer]*

## Step 4：Channel 建立完成

Channel 建立完成後，回到 Console 頁面就會看到剛剛建立好的 Channel。（下圖中我已經建立過兩個 Channel，所以列表裡有兩筆。）

![LINE Developers Console 中列出已建立的 Channel 清單畫面。](img-005)
*建立好的 Channel [source: LINE Developer]*

## Step 5：修改 LINE Bot 初始設定

點進剛剛建立的 Channel，就可以對這隻 LINE Bot 做設定。先切到 **Messaging API** 分頁。

![Channel 設定頁面上方的分頁列，游標指向 Messaging API 分頁。](img-006)
*點選 Messaging API*

滑到頁面最下方，找到 **Allow bot to join group chats** 這個欄位，點 **Edit**。

![Messaging API 設定頁最下方的 Allow bot to join group chats 欄位與 Edit 按鈕。](img-007)
*設定 LINE Bot 進入群組的權限*

進到新頁面後，在「功能切換」區塊把「不接受」LINE Bot 被邀請進入多人群組。開發初期先關掉群組權限比較單純：Bot 一旦進了群組，會收到群組裡所有人的訊息事件，除錯的時候雜訊會多很多。之後真的需要群組功能，隨時可以再打開。

![功能切換區塊中，將 LINE Bot 加入群組的設定選為「不接受」。](img-008)
*不允許 LINE Bot 被加入群組*

接著回到原來的頁面，在 **Auto-reply messages** 欄位點 **Edit**。新頁面裡會看到針對這隻 LINE Bot 的「基本設定」與「進階設定」兩大區塊。

在「基本設定」中，「回應模式」選「聊天機器人」，「加入好友的歡迎訊息」選「停用」。

![基本設定區塊中，將「加入好友的歡迎訊息」切換為停用。](img-009)
*停用「加入好友的歡迎訊息」*

在「進階設定」中，「自動回應訊息」選「停用」，「Webhook」選「啟用」。

這兩個開關是整段設定裡最關鍵的地方。LINE 預設會用內建的罐頭訊息幫你回覆使用者，如果不把「自動回應訊息」停用，使用者傳訊息過來時收到的會是那則罐頭訊息，而不是我們程式產生的內容。而「Webhook」則是 LINE Platform 把訊息事件轉發到我們伺服器的管道，沒啟用的話，我們的程式根本收不到任何訊息。

![進階設定區塊中，「自動回應訊息」設為停用、「Webhook」設為啟用。](img-010)
*停用「自動回應訊息」、啟用「Webhook」*

## Step 6：加入 LINE Bot 作為好友

基本設定都完成後，在 Messaging API 頁面可以找到這隻 LINE Bot 的 QR Code。用手機掃描它就會自動開啟 LINE App，把剛剛建立好的 Bot 加為好友。

![Messaging API 設定頁面上顯示的 LINE Bot QR Code，可用手機掃描加為好友。](img-011)
*將 LINE Bot 加為好友*

加完好友後可以先做個簡單的驗收：傳一則訊息給這隻 Bot，如果訊息顯示「已讀」，就代表訊息確實送達 LINE Platform 了。這時候 Bot 不會回話是正常的，因為我們已經把罐頭回覆關掉，而接手回話的程式還沒寫。

## 結論

這篇文章把建立 LINE Bot 的前置作業走了一遍：申請 LINE Developers 帳號、建立 Provider 與 Channel，再把群組權限、自動回應訊息與 Webhook 這幾個開關調整成適合開發的狀態。同時也認識了 LINE Messaging API 在整個流程中扮演的角色：它是我們的伺服器與使用者聊天室之間的橋樑。

Bot 的殼已經有了，接下來就是撰寫程式接收使用者傳來的訊息，並依照服務的目的回覆對應的內容。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "LINE Bot 與 User 的互動方式 [source: LINE]",
    "why_used": "說明使用者、LINE Platform 與開發者伺服器三方之間的訊息流向，支撐「LINE Messaging API 是什麼」一節的解釋。",
    "agent_match_hint": "一張訊息流程示意圖，呈現使用者、LINE Platform 與 Bot 伺服器之間的訊息往返，帶有 LINE 品牌色。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "LINE Developer Console 頁面 [source: LINE Developer]",
    "why_used": "讓讀者確認登入 LINE Developers 後應該看到的畫面，對應 Step 1 的操作結果。",
    "agent_match_hint": "LINE Developers Console 網站首頁的螢幕截圖。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "建立 Provider [source: LINE Developer]",
    "why_used": "對應 Step 2 建立 Provider 並輸入名稱的操作步驟。",
    "agent_match_hint": "建立 Provider 的表單截圖，畫面上有一個 Provider name 輸入欄位。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "建立 Channel [source: LINE Developer]",
    "why_used": "對應 Step 3 建立 Messaging API 類型 Channel、填寫 icon 與名稱的操作步驟。",
    "agent_match_hint": "建立 Channel 的表單截圖，含 Channel type、Channel icon、Channel name 等欄位。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "建立好的 Channel [source: LINE Developer]",
    "why_used": "呈現 Step 4 完成後 Console 中的 Channel 列表，讓讀者確認 Channel 已建立成功。",
    "agent_match_hint": "Console 頁面截圖，列出兩個已建立的 Channel 方塊。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "點選 Messaging API",
    "why_used": "指出 Step 5 開始設定時要切換到的分頁位置。",
    "agent_match_hint": "Channel 設定頁上方的分頁列截圖，Messaging API 分頁被標示出來。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "設定 LINE Bot 進入群組的權限",
    "why_used": "標示出 Allow bot to join group chats 欄位與 Edit 按鈕的位置，避免讀者在長頁面中找不到。",
    "agent_match_hint": "Messaging API 設定頁下方的截圖，含 Allow bot to join group chats 欄位與 Edit 連結。"
  },
  {
    "id": "img-008",
    "references_manifest_caption": "不允許 LINE Bot 被加入群組",
    "why_used": "呈現「功能切換」區塊中選擇「不接受」加入群組後的正確狀態。",
    "agent_match_hint": "官方帳號後台「功能切換」設定畫面截圖，群組邀請選項設為不接受。"
  },
  {
    "id": "img-009",
    "references_manifest_caption": "停用「加入好友的歡迎訊息」",
    "why_used": "呈現基本設定中回應模式與歡迎訊息應調整成的狀態。",
    "agent_match_hint": "官方帳號「基本設定」畫面截圖，歡迎訊息選項切換為停用。"
  },
  {
    "id": "img-010",
    "references_manifest_caption": "停用「自動回應訊息」、啟用「Webhook」",
    "why_used": "呈現整段設定中最關鍵的兩個開關狀態，是後續程式能收發訊息的前提。",
    "agent_match_hint": "官方帳號「進階設定」畫面截圖，自動回應訊息為停用、Webhook 為啟用。"
  },
  {
    "id": "img-011",
    "references_manifest_caption": "將 LINE Bot 加為好友",
    "why_used": "指出 QR Code 在設定頁中的位置，對應 Step 6 加好友的操作。",
    "agent_match_hint": "Messaging API 設定頁截圖，畫面中含一個可掃描的 QR Code 區塊。"
  }
]
```
