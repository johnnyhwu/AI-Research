---
title: PyTorch 支援 Apple Silicon GPU (Mac M1)
date: '2022-05-22T03:00:44'
lastmod: '2022-06-18T15:22:18'
slug: pytorch-support-apple-silicon-gpu-mac-m1
draft: false
categories:
- 其他
tags:
- Classification
- Deep Learning
- Feedforward Neural Network
- macOS
- Python
- PyTorch
description: 前言 在 2022 年 5 月18 日的這一天，PyTorch 在 Official Blog 中宣布：在 PyTorch 1.12 版本中將可以使用
  Apple Silicon 中的 GPU，也就是說如果你的 MacBook Air 或 MacBook Pro 的處理器是使用 M1 晶片而非 Intel 晶片，那麼你利用
  PyTorch 框架所建立的 Neural Network，將可以使用 GPU 進行訓練 (過去只有 TensorFlow 可以)！ 在本篇文章中，我們介紹如何安裝支援
  M1 GPU 的 PyTorch，並透過一個簡單的分類問題，來測試 CPU 與 GPU 的效能。 AD 確認 MacOS 版本 在安裝 PyTorch 之前，必須先確保
  MacOS 版本大於或等於 […]
aliases:
- /others/pytorch-support-apple-silicon-gpu-mac-m1/
original_url: http://54.150.87.240/others/pytorch-support-apple-silicon-gpu-mac-m1/
wp_id: 826
images:
- images/miniconda-installer.jpg
- images/pytorch.jpeg
- images/training-time.jpg
- images/vgg16-on-cifar10.jpg
---

![pytorch](images/pytorch.jpeg)

pytorch

## 前言

在 2022 年 5 月18 日的這一天，[PyTorch 在 Official Blog 中宣布](https://pytorch.org/blog/introducing-accelerated-pytorch-training-on-mac/)：在 PyTorch 1.12 版本中將可以使用 Apple Silicon 中的 GPU，也就是說如果你的 MacBook Air 或 MacBook Pro 的處理器是使用 M1 晶片而非 Intel 晶片，那麼你利用 PyTorch 框架所建立的 Neural Network，將可以使用 GPU 進行訓練 (過去只有 TensorFlow 可以)！

在本篇文章中，我們介紹如何安裝支援 M1 GPU 的 PyTorch，並透過一個簡單的分類問題，來測試 CPU 與 GPU 的效能。

AD

## 確認 MacOS 版本

在安裝 PyTorch 之前，必須先確保 MacOS 版本大於或等於 12.3，因為最新版的 PyTorch 底層使用 [Apple’s Metal Performance Shaders (MPS)](https://developer.apple.com/documentation/metalperformanceshaders) 。

打開 Terminal 並輸入以下指令，查看自己的 MacOS 版本：

```
sw_vers
```

## 安裝 Miniconda

在進行 Python 程式的開發時，不同專案需要不同的套件，比較好的做法是替每一個專案建立一個虛擬環境，讓專案與專案之間的套件彼此不受影響。

在 Python 中，管理套件的輔助工具有很多種，我們選擇使用 [Anaconda](https://www.anaconda.com/) 來管理我們的套件。但是在 Anaconda 中包含太多其他的工具，我們選擇安裝簡化版的 Anaconda —— [Miniconda](https://docs.conda.io/en/latest/miniconda.html)。

Miniconda 在許多作業系統中都可以使用，我們要安裝支援 MacOS M1 的版本，也就是 [Miniconda3 macOS Apple M1 ARM 64-bit bash](https://repo.anaconda.com/miniconda/Miniconda3-py38_4.12.0-MacOSX-arm64.sh)。

下載完成之後，開啟 Terminal 找到這個 script 檔案：

![miniconda installer](images/miniconda-installer.jpg)

miniconda installer

透過 chmod 確保這個檔案能夠被執行：

```
sudo chmod +x Miniconda3-py38_4.12.0-MacOSX-arm64.sh
```

接著，執行這個 script：

```
./Miniconda3-py38_4.12.0-MacOSX-arm64.sh
```

跟著指令操作完成 Miniconda 的安裝。

## 建立 PyTorch 虛擬環境

一樣打開 Terminal，建立一個名為「pytorch-m1」的虛擬環境，並指定 Python 版本為 3.8。

```
conda create --name pytorch-m1 python=3.8
```

接著，啟用這個虛擬環境：

```
conda activate pytorch-m1
```

透過 pip 安裝所需要的套件：

```
pip3 install --pre torch torchvision --extra-index-url https://download.pytorch.org/whl/nightly/cpu
```

等待大約 1 分鐘完成所有套件的安裝後，就大功告成囉！

## 在 PyTorch 中使用 M1 GPU

過去我們在 PyTorch 中如果要使用 Nvidia 的 GPU 時，可以透過：

```
device = torch.device("cuda")
```

如果要使用 M1 GPU 只需要將 cuda 改為 mps，剩下的操作都和原本是一樣的 (將 Tensor 與 Model 移動到 Device 上)：

```
device = torch.device("mps")
```

AD

## M1 CPU vs M1 GPU (1)

接著，我透過一個簡單的分類問題 —— MNIST Digit Classification，來比較使用 MacBook Air 2020 上 M1 CPU 與 M1 GPU 所需要的訓練時間。

我使用 [GitHub 上 pytorch/examples](https://github.com/pytorch/examples/blob/main/mnist/main.py) 所提供的程式碼，分別使用 CPU 與 GPU 對模型進行訓練。皆訓練 5 個 Epochs 且 Batch Size 設為 64。

下圖為兩者的時間差異：

![Training Time of M1 CPU vs M1 GPU on MNIST](images/training-time.jpg)

Training Time of M1 CPU vs M1 GPU on MNIST

M1 CPU 一個 Epoch 大約花了 28.96 秒，M1 GPU 一個 Epoch 約花了 18.26 秒，時間上**減少了 36.95%**。

## M1 CPU vs M1 GPU (2)

上面透過一個很簡單的模型與資料集來比較 CPU 與 GPU 的效能，[sebastianraschka](https://sebastianraschka.com/blog/2022/pytorch-m1-gpu.html) 在其部落格上還比較了不同硬體裝置使用 CIFAR-10 資料集訓練 VGG16 模型的效能：

![VGG16 on CIFAR10](images/vgg16-on-cifar10.jpg)

VGG16 on CIFAR10 [source: sebastianraschka.com]

若單純比較 M1 Pro CPU 與 M1 Pro GPU 可以發現 GPU 的時間比 CPU **減少了 44.54%**！

## 結語

本文說明如何在 PyTorch 中使用 M1 GPU，並比較 M1 CPU 與 M1 GPU 的效能差異。然而，儘管 PyTorch 可以支援 M1 GPU，但是使用筆電 (MacBook Air 或 MacBook Pro) 作為訓練神經網路的主要裝置，仍然是個不切實際的想法！畢竟訓練大型的神經網路，所需要的訓練時間更長，將會使得筆電長時間過熱，而造成壽命減短。
