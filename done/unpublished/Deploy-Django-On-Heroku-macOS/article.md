# 在 macOS 上將 Django App 部署到 Heroku

![Heroku 平台的品牌主視覺，作為本篇部署教學的開場圖。](img-001)
*將 Django App 部署到 Heroku（圖片來源：Heroku）*

## 前言

在本地端 (Local Server) 把網站寫完之後，下一步通常就是把它公開出去，讓其他人都能連進來看。問題是，自己租一台機器、裝好作業系統、設定網頁伺服器與資料庫，這一整套流程對只想把作品放上網的開發者來說負擔不小。

為了把這段路縮短，市面上出現了不少「平台即服務」(Platform as a Service, PaaS) 的工具，讓你只要把程式碼推上去，剩下的環境建置交給平台處理。本文以 Heroku 為例，從建立虛擬環境開始，一步步把一個全新的 Django App 部署到雲端上。整篇教學都在 macOS 上操作，指令可以直接照著打。

## Heroku 是什麼

![Heroku 平台服務的品牌示意圖。](img-002)
*Heroku 是以容器為基礎的 PaaS 平台（圖片來源：Heroku）*

Heroku 是一個以「容器」(Container) 為基礎的「平台即服務」(Platform as a Service, PaaS)。開發者可以快速的將應用程式部署到 Heroku 上，並透過 Heroku 來管理應用程式的資源使用。如此一來，軟體開發者可以不需要直接接觸硬體資源的管理，降低部署軟體的難度。

說白了，你要做的事情只有兩件：把程式碼整理成一個 Git repo，然後告訴 Heroku「這個 App 需要哪些套件、要用什麼指令跑起來」。Heroku 讀到這些資訊後，會自己幫你把執行環境建好。

## 將 Django App 部署到 Heroku

了解 Heroku 的基本概念後，接著就實際走一次完整流程。我們會從透過 conda 建立虛擬環境開始，整個流程大致可以分為 6 個步驟：

1. 建立虛擬環境
2. 安裝必要套件
3. 建立 Django 專案
4. 新增 Heroku 需要的檔案
5. 建立 Local Repo
6. 推上 Heroku 完成部署

## Step 1：透過 conda 建立虛擬環境

為了確保專案與專案之間的獨立與區隔，我們透過 conda 建立一個虛擬環境，在該虛擬環境中僅會包含 Django 與 Heroku 必要的套件。這件事在後面的 Step 4 會變得很重要：我們會用 `pip freeze` 把環境裡的套件清單交給 Heroku，如果直接用系統的 Python 環境，那份清單就會混進一堆跟這個專案無關的套件。

在 conda 所建立的虛擬環境中，我們仍是透過 pip 安裝所需套件，因此如果你沒有安裝 conda 也沒關係，一樣可以用 [virtualenv](https://pypi.org/project/virtualenv/) 建立虛擬環境，後續步驟完全相同。

首先，打開 terminal 後輸入以下指令，建立一個名為 DjangoHeroku、Python 版本指定為 3.9 的虛擬環境。

```bash
conda create --name DjangoHeroku python=3.9
```

接著，進入這個虛擬環境中。

```bash
conda activate DjangoHeroku
```

此時，我們的 terminal 輸入指令的位置最前面應該會多出 `(DjangoHeroku)`。這個前綴就是你之後判斷「現在人在不在虛擬環境裡」最直接的依據。

## Step 2：安裝必要套件

在此步驟中，我們必須透過 pip 安裝一些必要套件，使得 Django App 能夠成功部署到 Heroku 上。首先，檢查目前 pip 的版本資訊以及出處。

```bash
pip --version
```

我們可以看到以下結果：

```text
pip 21.2.4 from /Users/xxxxx/miniforge3/envs/DjangoHeroku/lib/python3.9/site-packages/pip (python 3.9)
```

這裡要注意的是路徑中間那段 `envs/DjangoHeroku`，它代表你現在用的確實是虛擬環境裡的 pip，而不是系統的那一套。如果路徑不對，回頭確認一下有沒有 `conda activate`。

接著，安裝 django 套件。

```bash
pip install django
```

安裝 gunicorn 套件。gunicorn 是正式環境用的 WSGI 伺服器，Heroku 會用它來跑我們的 App，而不是用 Django 內建的開發用伺服器。

```bash
pip install gunicorn
```

緊接著，我們要安裝的套件中將會包含 PostgreSQL driver for Python (psycopg2)，為了確保成功安裝，必須先在電腦上安裝 PostgreSQL。因此，可以到 [PostgreSQL Download](https://postgresapp.com/downloads.html) 下載並安裝。接著，輸入以下指令安裝 Postgres CLI。

```bash
sudo mkdir -p /etc/paths.d && echo /Applications/Postgres.app/Contents/Versions/latest/bin | sudo tee /etc/paths.d/postgresapp
```

這行指令的作用是把 Postgres.app 裡的執行檔路徑加進系統的 PATH，之後才能在 terminal 直接呼叫 `psql`。完成後，請重新開啟 terminal，並確保 PostgreSQL 已經安裝成功。

```bash
which psql
```

出現以下的結果，即表示安裝成功：

```text
/Applications/Postgres.app/Contents/Versions/latest/bin/psql
```

因為我們已經重新開啟 terminal，必須再次進入虛擬環境中。

```bash
conda activate DjangoHeroku
```

進到虛擬環境後，再安裝 django-heroku 套件。這個套件會一次幫我們把資料庫連線、靜態檔案、logging 等 Heroku 環境需要的設定都配置好，省下手動改一堆 settings 的工夫。（這個套件目前已經停止維護，當年跟著這篇做沒有問題，但如果你是現在才要開新專案，可以留意一下替代方案。）

```bash
pip install django-heroku
```

最後，檢查必要的套件是否都安裝完成。

```bash
pip list
```

會出現以下結果，顯示已經安裝的套件：

```text
Package         Version
--------------- -------
asgiref         3.4.1
dj-database-url 0.5.0
Django          3.2.7
django-heroku   0.3.1
gunicorn        20.1.0
pip             21.2.4
psycopg2        2.9.1
pytz            2021.1
setuptools      58.0.3
sqlparse        0.4.1
wheel           0.37.0
whitenoise      5.3.0
```

可以看到我們只手動裝了四個套件，清單卻長了不少，那是因為 django-heroku 順帶把 dj-database-url、psycopg2、whitenoise 這些相依套件一起帶進來了。

## Step 3：建立 Django 專案

安裝完必要的套件後，我們需要建立一個 Django 專案，才能將其部署到 Heroku 上。首先，切換目前的目錄到 Desktop。

```bash
cd ~/Desktop
```

在 Desktop 中建立一個 Django 專案，名為 MyFirstProject。

```bash
django-admin startproject MyFirstProject
```

切換目前的目錄到這個 Project 中。

```bash
cd MyFirstProject
```

在目前的 Project 中新增新的 Application，名為 myapp。

```bash
python manage.py startapp myapp
```

這裡順帶說明一下 Django 的用語：Project 是整個網站，Application 則是網站底下一個功能模組，一個 Project 可以掛很多個 App。目前 MyFirstProject 的結構如下：

![Django 專案資料夾的樹狀結構，可以看到 MyFirstProject 底下有 manage.py、同名的設定資料夾與新建立的 myapp 資料夾。](img-003)
*目前專案資料夾中的檔案（建立 MyFirstProject 與 myapp 之後）*

接著，我們要針對 MyFirstProject/MyFirstProject 資料夾中的 settings.py 進行一些修改。首先，在第 13 行左右，再 import 兩個 package。

```python
import os
import django_heroku
```

在第 35 行左右的 INSTALLED_APPS list 中，新增我們剛剛建立的 app。少了這一行，Django 不會認得 myapp。

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myapp'  # add this line
]
```

在第 124 行左右新增 STATIC_ROOT 路徑。這是 Django 收集靜態檔案時的輸出目錄，部署到 Heroku 時一定要設定，否則 CSS 與圖片會找不到。

```python
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
```

最後，在 settings.py 的最後方加上這行，讓 django-heroku 覆寫成 Heroku 環境需要的設定：

```python
django_heroku.settings(locals())
```

在 Django 中，所有的圖片、CSS 與 JS 檔案會存放在 static 資料夾中，因此在 MyFirstProject/MyFirstProject 與 MyFirstProject/myapp 中都新增 static 資料夾。

```bash
mkdir MyFirstProject/static
mkdir myapp/static
```

最後，我們將 Database 更新同步。前者會依照 model 的定義產生 migration 檔，後者才真正把變更套用到資料庫上。

```bash
python manage.py makemigrations
```

```bash
python manage.py migrate
```

做到這裡，我們已經完成 Django 專案的建立，可以透過以下指令，在本地端 (local server) 看到我們的網站。

```bash
python manage.py runserver
```

會出現以下結果：

![Terminal 畫面，顯示 Django 開發伺服器啟動後的訊息與監聽的本機位址。](img-004)
*執行 Django 中的伺服器*

在瀏覽器中，輸入以下網址就可以看到 Django 預設頁面。

```text
http://127.0.0.1:8000/
```

![瀏覽器中的 Django 預設歡迎頁面，顯示安裝成功的訊息與火箭圖示。](img-005)
*Django 預設首頁*

看到這個頁面就可以確定我們的 Django 專案是建立正確的。在 Terminal 按下 Ctrl + C 來關閉 local server。

## Step 4：新增 Heroku 需要的檔案

成功建立 Django 專案後，我們還需要準備一些檔案，讓 Heroku 知道需要安裝什麼套件，或是在我們的 App 上執行什麼 Command。這一步是本地開發與雲端部署之間的橋樑：在你的電腦上這些資訊都藏在虛擬環境裡，Heroku 看不到，所以要寫成檔案交給它。

首先，確認目前的專案架構：

![Django 專案資料夾的樹狀結構，此時尚未包含 Procfile、requirements.txt 與 runtime.txt。](img-006)
*目前專案資料夾中的檔案（新增 Heroku 所需檔案之前）*

接著，執行以下指令，生成 Procfile 檔案。Procfile 由 `<process type>: <command>` 組成，告訴 Heroku 應該替我們的 App 執行什麼指令。這裡的 `web` 表示這是一個對外接收 HTTP 請求的行程，後面接的就是用 gunicorn 啟動 MyFirstProject 的 WSGI 應用。

```bash
echo 'web: gunicorn MyFirstProject.wsgi' > Procfile
```

此外，我們還需要告訴 Heroku 我們的 App 用到了哪些套件。`pip freeze` 會把虛擬環境中所有套件連同版本一起寫進 requirements.txt，Heroku 建置時會照著這份清單安裝。

```bash
pip freeze > requirements.txt
```

最後，還要告訴 Heroku 我們所使用的 Python 版本。

```bash
python --version
```

得到：

```text
Python 3.9.7
```

產生 runtime.txt 在裡頭標上 Python 版本。注意格式是 `python-` 加上版本號，而不是直接把上面的輸出貼進去。

```bash
echo 'python-3.9.7' > runtime.txt
```

再次確認目前的專案架構，應該會多出剛剛產生的三個檔案：

![Django 專案資料夾的樹狀結構，此時已多出 Procfile、requirements.txt 與 runtime.txt 三個檔案。](img-007)
*目前專案資料夾中的檔案（新增 Procfile、requirements.txt 與 runtime.txt 之後）*

## Step 5：建立 Local Repo

產生 Heroku 所需要的必要檔案後，我們需要將整個 Django App Project 設定為 Local Repo。Heroku 的部署方式就是「推 Git」，所以之後每次在 Project 中有任何修改，只要把 Repo 重新 push 上去就會觸發重新部署。（如果有安裝新的套件，記得要重新產生 requirements.txt，否則 Heroku 那邊不會知道多了什麼相依套件。）

初始化 Local Repo：

```bash
git init
git add .
git commit -m "create django app"
```

## Step 6：將 Django App 部署到 Heroku

最後一個步驟中，我們要將 Local Repo push 到 Heroku 平台上的 Remote Repo 中，完成 Django App 的部署。

首先，需要到 [Heroku](https://signup.heroku.com/) 建立一個帳號。（原文寫的是免費帳號，不過 Heroku 已於 2022 年 11 月終止免費方案，現在需要付費才能實際跑起來。）接著，一樣在 Terminal 中登入 Heroku。

```bash
heroku login
```

按下 Enter 後，即可在瀏覽器中登入。接著，在 Heroku 上創建一個 App，名為 my-first-project-django。要注意的是，Heroku 的 App 名稱在全平台是唯一的，所以你得換一個沒被用過的名字，後續指令與網址也要跟著換。

```bash
heroku create my-first-project-django
```

接著，要設定 Local Repo 究竟要上傳到哪裡。

```bash
heroku git:remote -a my-first-project-django
```

得到：

```text
set git remote heroku to https://git.heroku.com/my-first-project-django.git
```

最後，將我們的 Local Repo push 上去。

```bash
git push heroku master
```

此時，Heroku 會根據 Local Repo 中的 Procfile、requirements.txt 與 runtime.txt 建立環境。整個建置過程會直接印在 terminal 上，如果哪個套件裝不起來，這裡就會看到錯誤訊息。最後，會得到我們的 App 部署在 Heroku 中對應的 URL：

```text
https://my-first-project-django.herokuapp.com/
```

在開啟網頁之前，還必須設定至少 1 個 dyno 來執行這個 App。dyno 是 Heroku 用來跑你的 App 的容器，數量為 0 的話 App 等於沒有在運作。

```bash
heroku ps:scale web=1
```

設定完成後，在瀏覽器中輸入網址，如果呈現以下頁面，就表示我們成功將 Django App 部署到 Heroku 上囉！這正是前面在 `127.0.0.1:8000` 看到的同一個 Django 預設首頁，差別只在於它現在是跑在雲端、任何人都連得到的網址上。

![瀏覽器中的 Django 預設歡迎頁面，顯示安裝成功的訊息與火箭圖示。](img-005)
*Django 預設首頁*

## 結論

本篇文章從 conda 虛擬環境開始，經過安裝套件、建立 Django 專案、補上 Heroku 需要的 Procfile / requirements.txt / runtime.txt，最後用 Git push 完成部署，走完了一次把 Django App 送上 Heroku 的完整流程。

真正的關鍵其實只有一個觀念：Heroku 看不到你電腦裡的環境，所以你得把「要裝什麼、怎麼跑、用哪個 Python 版本」全部寫成檔案交給它。掌握這件事之後，換成其他 PaaS 平台也是同樣的思路。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "將 Django App 部署到 Heroku（圖片來源：Heroku）",
    "why_used": "作為文章開場的主視覺，點出本篇主題是把 Django App 部署到 Heroku。",
    "agent_match_hint": "一張 Heroku 品牌風格的橫幅圖，紫色系為主，屬於文章的封面圖。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Heroku 是以容器為基礎的 PaaS 平台（圖片來源：Heroku）",
    "why_used": "搭配「Heroku 是什麼」段落，替讀者建立對這個 PaaS 平台的第一印象。",
    "agent_match_hint": "另一張 Heroku 官方風格的服務示意圖，與封面圖同一系列但構圖不同。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "目前專案資料夾中的檔案（建立 MyFirstProject 與 myapp 之後）",
    "why_used": "讓讀者對照自己執行 startproject 與 startapp 之後的資料夾結構是否正確。",
    "agent_match_hint": "一張檔案總管或 tree 指令的資料夾結構截圖，可以看到 manage.py、MyFirstProject 與 myapp。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "執行 Django 中的伺服器",
    "why_used": "呈現 python manage.py runserver 成功啟動後的 terminal 輸出，作為本地端跑起來的驗證點。",
    "agent_match_hint": "一張 terminal 截圖，內容是 Django 開發伺服器的啟動訊息與監聽位址。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "Django 預設首頁",
    "why_used": "同一張圖在文中出現兩次，先驗證本地端專案建立成功，最後再驗證雲端部署成功。",
    "agent_match_hint": "一張瀏覽器截圖，畫面是 Django 安裝成功的預設歡迎頁，含火箭插圖。"
  },
  {
    "id": "img-006",
    "references_manifest_caption": "目前專案資料夾中的檔案（新增 Heroku 所需檔案之前）",
    "why_used": "作為新增 Heroku 設定檔前的對照組，凸顯下一步會多出哪些檔案。",
    "agent_match_hint": "一張資料夾結構截圖，內容與建立專案後相同，尚未出現 Procfile。"
  },
  {
    "id": "img-007",
    "references_manifest_caption": "目前專案資料夾中的檔案（新增 Procfile、requirements.txt 與 runtime.txt 之後）",
    "why_used": "確認 Procfile、requirements.txt 與 runtime.txt 三個檔案都已正確產生在專案根目錄。",
    "agent_match_hint": "一張資料夾結構截圖，比前一張多出 Procfile、requirements.txt、runtime.txt 三個檔案。"
  }
]
```
