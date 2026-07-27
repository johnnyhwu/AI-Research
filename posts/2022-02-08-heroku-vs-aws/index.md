---
title: Heroku 是什麼 ?! 與 AWS 的差異 ?
date: '2022-02-08T04:59:40'
lastmod: '2022-07-15T01:22:08'
slug: heroku-vs-aws
draft: false
categories:
- 其他
tags:
- AWS
- Heroku
description: 前言 & 概述 在本地端完成應用程式的開發後，你總會希望更多人都可以使用到你所開發出來的服務，此時你需要將你的應用程式部署到伺服器上。然而，一大堆問題就在此時出現！應該自己維護伺服器的硬體設備嗎？如何確保伺服器的網路安全？如何維護使用者的資訊安全？
  就在你 Google 這些問題的解答時，你發現了 Heroku！Heroku 似乎能夠幫助你迅速部署你的應用程式，同時免去所有的維護麻煩事 … 在本文中，我們將會以簡單的觀點了解
  Heroku 是什麼以及其與 AWS 的差異。 AD Heroku 是什麼 Heroku 是一個能讓你快速部署應用程式的平台。說到「平台」你一定不陌生，Medium
  是一個文章平台，你可以將自己的文章發布在 Medium 上，讓其他人都能看到你的文章。Shopee 也是一個平台，你可以將你的產品放在 Shopee 上，其他人則可以購買。
  同樣的，回到 Heroku 上！Heroku 也是一個平台，當你辛辛苦苦開發出一個軟體後，你希望大家都能使用到該服務，你可以將你的軟體放到 Heroku 上。如此一來，大家就可以像瀏覽網站一樣，在瀏覽器中輸入
  URL 就可以存取到你所提供的服務。 Dyno 是什麼 在本地端 (也就是你的電腦上)，你將滑鼠移動到你想要開啟的應用程式上，點兩下後，應用程式立即開啟，你可以開始使用這個應用程式所提供的服務。我們都知道應用程式的開啟速度、執行效率與使用者體驗很大一部份取決於你「電腦效能」。如果你的電腦是台老古董，那勢必用起來會非常不快樂！
  同樣的，為了讓你的應用程式能夠正常的運作，Heroku 也必須準備 (虛擬的)「電腦」，我們稱之為 Dyno。在 Heroku 上，我們可以將 Dyno 想成虛擬機器，這些虛擬機器將會為你的應用程式提供運算資源，好讓他能夠被正常執行。
  為了討好你的使用者，讓他們使用你的應用程式時更順暢。你可以選擇提升每一個 Dyno 的效能，或是使用更多 Dyno 來服務你的應用程式。Heroku 正是透過
  Dyno 的使用情形，來向你收費。 特別的是，我們以為我們是將應用程式部署在 […]
aliases:
- /others/heroku-vs-aws/
original_url: http://54.150.87.240/others/heroku-vs-aws/
wp_id: 461
images:
- images/aws-certificate.jpg
- images/feature-image-5.jpg
- images/feature-image-8.jpg
- images/heroku-dashboard.jpg
---

![](images/feature-image-8.jpg)

source: Heroku

## 前言 & 概述

在本地端完成應用程式的開發後，你總會希望更多人都可以使用到你所開發出來的服務，此時你需要將你的應用程式部署到伺服器上。然而，一大堆問題就在此時出現！應該自己維護伺服器的硬體設備嗎？如何確保伺服器的網路安全？如何維護使用者的資訊安全？

就在你 Google 這些問題的解答時，你發現了 Heroku！Heroku 似乎能夠幫助你迅速部署你的應用程式，同時免去所有的維護麻煩事 …

在本文中，我們將會以簡單的觀點了解 Heroku 是什麼以及其與 AWS 的差異。

AD

## Heroku 是什麼

![](images/feature-image-5.jpg)

source: Heroku

[Heroku](https://dashboard.heroku.com/login) 是一個能讓你快速部署應用程式的平台。說到「平台」你一定不陌生，[Medium](https://medium.com/) 是一個文章平台，你可以將自己的文章發布在 Medium 上，讓其他人都能看到你的文章。[Shopee](https://shopee.tw/) 也是一個平台，你可以將你的產品放在 Shopee 上，其他人則可以購買。

同樣的，回到 Heroku 上！Heroku 也是一個平台，當你辛辛苦苦開發出一個軟體後，你希望大家都能使用到該服務，你可以將你的軟體放到 Heroku 上。如此一來，大家就可以像瀏覽網站一樣，在瀏覽器中輸入 URL 就可以存取到你所提供的服務。

## Dyno 是什麼

在本地端 (也就是你的電腦上)，你將滑鼠移動到你想要開啟的應用程式上，點兩下後，應用程式立即開啟，你可以開始使用這個應用程式所提供的服務。我們都知道應用程式的開啟速度、執行效率與使用者體驗很大一部份取決於你「電腦效能」。如果你的電腦是台老古董，那勢必用起來會非常不快樂！

同樣的，為了讓你的應用程式能夠正常的運作，Heroku 也必須準備 (虛擬的)「電腦」，我們稱之為 Dyno。在 Heroku 上，我們可以將 Dyno 想成虛擬機器，這些虛擬機器將會為你的應用程式提供運算資源，好讓他能夠被正常執行。

為了討好你的使用者，讓他們使用你的應用程式時更順暢。你可以選擇提升每一個 Dyno 的效能，或是使用更多 Dyno 來服務你的應用程式。Heroku 正是透過 Dyno 的使用情形，來向你收費。

特別的是，我們以為我們是將應用程式部署在 Heroku 上；然而實際上，我們的應用程式是被部署到 [AWS (Amazon Web Service)](https://aws.amazon.com/tw/) 上。

## 為什麼不直接使用 AWS

相信你一定有這個問題：既然應用程式實際上是被部署到 AWS 上，那何不一開始就使用 AWS，尬麻還要經過 Heroku 呢？

解答這個問題之前，我們需要先了解 AWS 是什麼！AWS 是一個「基礎設施即服務」(Infrastructure as a Service, IaaS) 的提供商，IaaS 的提供商經常會在世界各地購買大面積的土地，興建「資料中心」(Data Center)。資料中心就是我們常說的「雲端」(Cloud)。當我們將資料上傳到 Google 雲端時，實際上是將資料儲存到 Google 的資料中心。

因為有這些 IaaS 提供商，我們在儲存檔案時不需要自己購買儲存設備，只需要「上傳到雲端」即可。

AD

然而，Google、AWS、Azure 這些 IaaS 提供商，他們的業務重點在於管理並提供這些「基礎建設」的硬體資源，而不是在開發者使用這些硬體資源的體驗上，使得開發者如果要「親自」使用這些 IaaS 時，往往需要許多先備知識。

![aws certificate](images/aws-certificate.jpg)

AWS 的相關證照 [source: AWS]

如上圖所示，AWS 為他們所提供的服務，提供了多項證照與課程。可想而知，要使用這些服務也需要花費許多時間學習。

Heroku 正是扮演開發者與 IaaS 之間的橋樑！如下圖所示，當我們將應用程式「部署」(你知道實際上是部署到 AWS) 到 Heroku 上後，我們可以透過更簡單的 CLI 與更精美的 Dashbaord 來管理我們的應用程式。

![heroku dashboard](images/heroku-dashboard.jpg)

Heroku Dashboard [source: Heroku]

Heroku 正是由一群精通 AWS 的「軟體工程師」打造給「軟體工程師」使用的平台。因為 Heroku 是基於 AWS (IaaS) 所建立的平台，我們可以稱 Heroku 為「平台即服務」(Platform as a Service) 的提供商。

AD

## 結語

在本篇文章中，我們了解到 Heroku (PaaS) 幫助我們不必直接去使用 AWS (IaaS) 的服務，使我們部署應用程式的過程更簡單與更快速。了解完 Heroku 後，接著學習如何[在 M1 上將 Django 部署到 Heroku](http://54.150.87.240/others/deploy-django-on-heroku-macos/)！
