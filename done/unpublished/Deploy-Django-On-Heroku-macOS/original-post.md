---
title: 將 Django App 部署到 Heroku on Mac
date: '2022-02-06T14:21:39'
lastmod: '2022-06-18T15:23:10'
slug: deploy-django-on-heroku-macos
draft: false
categories:
- 其他
tags:
- Django
- Heroku
- Python
description: '前言 & 概述 在本地端 (Local Server) 完成網站的開發後，我們通常會想將其公開部署，讓大家都可以瀏覽到這個網站。為了加速部署的速度並簡化其流程，許多雲端即服務
  (Platform as a Service, PaaS) 的工具被開發出來。在本文中，我們將以 Heroku 為例，一步步說明如何將 Django App 部署到
  Heroku 雲端平台上。 AD Heroku 是什麼 Heroku 是一個以「容器」(Container) 為基礎的「平台即服務」(Platform as a
  Service, PaaS)。開發者可以快速的將應用程式部署到 Heroku 上，並透過 Heroku 來管理應用程式的資源使用。如此一來，軟體開發者可以不需要直接接觸硬體資源的管理，降低部署軟體的難度。
  將 Django App 部署到 Heroku 了解 Heroku 基本概念後，我們將開始一步步學習如何將 Django App 部署到 Heroku 上。我們將從透過
  conda 建立虛擬環境開始，整個流程大致可以分為 6 個步驟，將會在以下一一說明。 Step 1 : 透過 […]'
aliases:
- /others/deploy-django-on-heroku-macos/
original_url: http://54.150.87.240/others/deploy-django-on-heroku-macos/
wp_id: 382
images:
- images/django-home-page.jpg
- images/feature-image-4.jpg
- images/feature-image-5.jpg
- images/heroku-directory-structure.jpg
- images/project-directory-structure-1.jpg
- images/project-directory-structure.jpg
- images/run-django-server.jpg
---

![](images/feature-image-4.jpg)

source: Heroku

## 前言 & 概述

在本地端 (Local Server) 完成網站的開發後，我們通常會想將其公開部署，讓大家都可以瀏覽到這個網站。為了加速部署的速度並簡化其流程，許多雲端即服務 (Platform as a Service, PaaS) 的工具被開發出來。在本文中，我們將以 Heroku 為例，一步步說明如何將 Django App 部署到 Heroku 雲端平台上。

AD

## Heroku 是什麼

![](images/feature-image-5.jpg)

source: Heroku

Heroku 是一個以「容器」(Container) 為基礎的「平台即服務」(Platform as a Service, PaaS)。開發者可以快速的將應用程式部署到 Heroku 上，並透過 Heroku 來管理應用程式的資源使用。如此一來，軟體開發者可以不需要直接接觸硬體資源的管理，降低部署軟體的難度。

## 將 Django App 部署到 Heroku

了解 Heroku 基本概念後，我們將開始一步步學習如何將 Django App 部署到 Heroku 上。我們將從透過 conda 建立虛擬環境開始，整個流程大致可以分為 6 個步驟，將會在以下一一說明。

## Step 1 : 透過 conda 建立虛擬環境

為了確保專案與專案之間的獨立與區隔，我們透過 conda 建立一個虛擬環境，在該虛擬環境中僅會包含 Django 與 Heroku 必要的套件。在 conda 所建立的虛擬環境中，我們仍是透過 pip 安裝所需套件，因此，如果你沒有安裝 conda 並沒有關係，仍然可以透過 [virtualenv](https://pypi.org/project/virtualenv/) 工具建立虛擬環境。 首先，打開 terminal 後輸入以下指令，來建立一個虛擬環境。這個虛擬環境的名稱為 DjangoHeroku，並指定 Python 版本為 3.9。

```
conda create --name DjangoHeroku python=3.9
```

接著，進入這個虛擬環境中。

```
conda activate DjangoHeroku
```

此時，我們的 terminal 輸入指令的位置最前面應該會多出 : (DjangoHeroku)。

## Step 2 : 安裝必要套件

在此步驟中，我們必須透過 pip 安裝一些必要套件，使得 Django App 能夠成功部署到 Heroku 上。 首先，檢查目前 pip 的版本資訊以及出處。

```
pip --version
```

我們可以看到以下結果：

```
pip 21.2.4 from /Users/xxxxx/miniforge3/envs/DjangoHeroku/lib/python3.9/site-packages/pip (python 3.9)
```

接著，安裝 django 套件。

```
pip install django
```

安裝 gunicorn 套件。

```
pip install gunicorn
```

緊接著，我們要安裝套件中將會包含 PostgreSQL driver for Python (psycopg2)，為了確保成功安裝，必須先在電腦上安裝 PostgreSQL。因此，可以到 [PostgreSQL Download](https://postgresapp.com/downloads.html) 下載並安裝。 接著，輸入以下指令安裝 Postgre CLI。

```
sudo mkdir -p /etc/paths.d && echo /Applications/Postgres.app/Contents/Versions/latest/bin | sudo tee /etc/paths.d/postgresapp
```

完成後，請重新開啟 terminal，並確保 PostgreSQL 已經安裝成功。

```
which psql
```

出現以下的結果，即表示安裝成功：

```
/Applications/Postgres.app/Contents/Versions/latest/bin/psql
```

因為我們已經重新開啟 terminal，必須再次進入虛擬環境中。

```
conda activate DjangoHeroku
```

進到虛擬環境後，再安裝 django-heroku 套件。

```
pip install django-heroku
```

最後，檢查必要的套件是否都安裝完成。

```
pip list
```

會出現以下結果，顯示已經安裝的套件：

```
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

## Step 3 : 建立 Django 專案

安裝完必要的套件後，我們需要建立一個 Django 專案，才能將其部署到 Heroku 上。 首先，切換目前的目錄到 Desktop。

```
cd ~/Desktop
```

在 Desktop 中建立一個 Django 專案，名為 MyFirstProject。

```
django-admin startproject MyFirstProject
```

切換目前的目錄到這個 Project 中。

```
cd MyFirstProject
```

在目前的 Project 中新增新的 Application，名為 myapp。

```
python manage.py startapp myapp
```

目前 MyFirstProject 的結構如下：

![project directory structure](images/heroku-directory-structure.jpg)

目前專案資料夾中的檔案

接著，我們要針對 MyFirstProject/MyFirstProject 資料夾中的 settings.py 進行一些修改。 首先，在第 13 行左右，再 import 兩個 package。

```
import osimport django_heroku
```

在第 35 行左右的 INSTALLED\_APPS list 中，新增我們剛剛建立的 app。

```
INSTALLED_APPS = [
'django.contrib.admin','django.contrib.auth',
'django.contrib.contenttypes',
'django.contrib.sessions',
'django.contrib.messages',
'django.contrib.staticfiles',
'myapp' # add this line ]
```

在第 124 行左右新增 STATIC\_ROOT 路徑。

```
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
```

最後，在 settings.py 的最後方加上：

```
django_heroku.settings(locals())
```

在 Django 中，所有的圖片、CSS 與 JS 檔案的會存放在 static 資料夾中，因此在 MyFirstProject/MyFirstProject 與 MyFirstProject/myapp 中都新增 static 資料夾。

```
mkdir MyFirstProject/staticmkdir myapp/static
```

最後，我們將 Database 更新同步。

```
python manage.py makemigrations
```

```
python manage.py migrate
```

做到這裡，我們已經完成 Django 專案的建立，我們可以透過以下指令，在本地端 (local server) 看到我們的網站。

```
python manage.py runserver
```

會出現以下結果：

![run django server](images/run-django-server.jpg)

執行 Django 中的伺服器

在瀏覽器中，輸入以下網址就可以看到 Django 預設頁面。

```
http://127.0.0.1:8000/
```

![django home page](images/django-home-page.jpg)

Django 預設首頁

看到這個頁面就可以確定我們的 Django 專案是建立正確的。在 Terminal 輸入 Ctrl + C 來關閉 local server。

AD

## Step 4 : 新增 Heroku 需要的檔案

成功建立 Django 專案後，我們還需要準備一些檔案，讓 Heroku 知道需要安裝什麼套件，或是在我們的 App 上執行什麼 Command。

首先，確認目前的專案架構：

![project directory structure](images/project-directory-structure.jpg)

目前專案資料夾中的檔案

接著，執行以下指令，生成 Procfile 檔案。Procfile 檔案由 **<process type> : <command>** 組成，告訴 Heroku 應該替我們的 App 執行什麼指令。

```
echo 'web: gunicorn MyFirstProject.wsgi' > Procfile
```

此外，我們還需要告訴 Heroku 我們的 App 用到了哪些套件。

```
pip freeze > requirements.txt
```

最後，還要告訴 Heroku 我們所使用的 Python 版本。

```
python --version
```

得到：

```
Python 3.9.7
```

產生 runtime.txt 在裡頭標上 Python 版本。

```
echo 'python-3.9.7' > runtime.txt
```

再次確認目前的專案架構：

![project directory structure](images/project-directory-structure-1.jpg)

目前專案資料夾中的檔案

## Step 5 : 建立 Local Repo

產生 Heroku 所需要的必要檔案後，我們需樣將整個 Django App Project 設定為 Local Repo。如此一來，每次在 Project 中有任何修改時，只需要將 Repo 重新 Push 即可。(如果有安裝新的套件，仍需要重新產生 requirements.txt) 初始化 Local Repo：

```
git init
git add .
git commit -m "create django app"
```

## Step 6 : 將 Django App 部署到 Heroku

最後一個步驟中，我們要將 Local Repo Push 到 Heroku 平台上的 Remote Repo 中，完成 Django App 的部署。 首先，需要到 [Heroku](https://signup.heroku.com/) 建立一個免費的帳號。接著，一樣在 Terminal 中登入 Heroku。

```
heroku login
```

按下 Enter 後，即可在瀏覽器中登入。接著，在 Heroku 上創建一個 App，名為 my-first-project-django。當然，App 的名字不可以重複！

```
heroku create my-first-project-django
```

接著，要設定 Local Repo 究竟要上傳到哪裡。

```
heroku git:remote -a my-first-project-django
```

得到：

```
set git remote heroku to https://git.heroku.com/my-first-project-django.git
```

最後，將我們的 Local Repo Push 上去。

```
git push heroku master
```

此時，Heroku 會根據 Local Repo 中的 Procfile、requirements.txt 與 runtime.txt 建立環境。最後，會得到我們的 App 部署在 Heroku 中對應的 URL：

```
https://my-first-project-django.herokuapp.com/
```

在開啟網頁之前，還必須設定至少 1 個 dyno 來執行這個 App：

```
heroku ps:scale web=1
```

設定完成後，在瀏覽器中輸入網址，如果呈現以下頁面，就表示我們成功將 Django App 部署到 Heroku 上囉！

![django home page](images/django-home-page.jpg)

Django 預設首頁

AD

## 結語

在本篇文章中，我們學會了如何將 Django App 部署到 Heroku 中！如果這篇文章對你有幫助，別忘了在下方點讚，分享給你的好朋友知道！
