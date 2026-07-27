---
title: 利用 PyTorch 的 ResNet 快速建立一個圖像分類器
date: '2022-06-15T01:07:34'
lastmod: '2022-06-18T03:16:03'
slug: pytorch-resnet-image-classifier
draft: false
categories:
- PyTorch 教學
tags:
- Classification
- Deep Learning
- Feedforward Neural Network
- Hands-On
- Machine Learning
- Python
- Residual Network
- Supervised Learning
description: 前言 在本篇文章中，我們要學習使用 PyTorch 中 TorchVision 函式庫，載入已經訓練好的模型，進行模型推論。 我們要解決的問題為「圖像分類」，因此我們會先從
  TorchVision 中載入 Residual Neural Network (ResNet)，並使用該模型來分類我們指定的圖片。 在閱讀本篇文章之前，你應該先了解機器學習中「模型訓練」與「模型推論」的概念，也可以更深入的理解
  Neural Network 如何進行圖像分類。 程式碼：Colab、GitHub。 載入函式庫 TorchVision 中有許多已經開源的模型，而且許多模型都已經事先透過
  ImageNet 資料集訓練過，因此我們可以不必從頭開始訓練模型，直接使用訓練好的模型，體驗「模型推論」的概念。 首先，載入我們在這個小專案中會使用到的函式庫：
  import torch from torchvision import models from torchvision import transforms import
  json from PIL import Image 查看 TorchVision 中的模型 dir(models) 輸出結果： [‘AlexNet’, ‘ConvNeXt’,
  ‘DenseNet’, ‘EfficientNet’, ‘GoogLeNet’, ‘GoogLeNetOutputs’, ‘Inception3’, ‘InceptionOutputs’,
  ‘MNASNet’, ‘MobileNetV2’, […]
aliases:
- /pytorch-%e6%95%99%e5%ad%b8/pytorch-resnet-image-classifier/
original_url: http://54.150.87.240/pytorch-%e6%95%99%e5%ad%b8/pytorch-resnet-image-classifier/
wp_id: 898
images:
- images/cat-300x221.jpg
- images/dog-1024x576.jpg
- images/feature-image-4.jpg
- images/plane-1024x640.jpg
---

![](images/feature-image-4.jpg)

source: Pixabay

## 前言

在本篇文章中，我們要學習使用 PyTorch 中 TorchVision 函式庫，載入已經訓練好的模型，進行模型推論。

我們要解決的問題為「圖像分類」，因此我們會先從 TorchVision 中載入 Residual Neural Network (ResNet)，並使用該模型來分類我們指定的圖片。

在閱讀本篇文章之前，你應該先了解機器學習中「[模型訓練](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-training/)」與「[模型推論](http://54.150.87.240/machine-learning-basic-concept/machine-learning-model-inference/)」的概念，也可以更深入的理解 [Neural Network 如何進行圖像分類](http://54.150.87.240/deep-learning-core-concept/neural-network-classify-handwritten-digit-image/)。

程式碼：[Colab](https://colab.research.google.com/drive/1V60OaghA1pW5SkqKrvtCtLXkojkyZqIA?usp=sharing)、[GitHub](https://github.com/johnnyhwu/data-science-practice/blob/main/pytorch-resnet-image-classification/main.ipynb)。

## 載入函式庫

TorchVision 中有許多已經開源的模型，而且許多模型都已經事先透過 ImageNet 資料集訓練過，因此我們可以不必從頭開始訓練模型，直接使用訓練好的模型，體驗「模型推論」的概念。

首先，載入我們在這個小專案中會使用到的函式庫：

```
import torch
from torchvision import models
from torchvision import transforms

import json
from PIL import Image
```

## 查看 TorchVision 中的模型

```
dir(models)
```

輸出結果：

```
['AlexNet',
'ConvNeXt',
'DenseNet',
'EfficientNet',
'GoogLeNet',
'GoogLeNetOutputs',
'Inception3',
'InceptionOutputs',
'MNASNet',
'MobileNetV2',
'MobileNetV3',
'RegNet',
'ResNet',
'ShuffleNetV2',
'SqueezeNet',
'VGG',
'VisionTransformer',
'_GoogLeNetOutputs',
...
'resnet',
'resnet101',
'resnet152',
'resnet18',
'resnet34',
'resnet50',
'resnext101_32x8d',
'resnext50_32x4d',
'segmentation',
'shufflenet_v2_x0_5',
'shufflenet_v2_x1_0',
'shufflenet_v2_x1_5',
'shufflenet_v2_x2_0',
'shufflenetv2',
'squeezenet',
'squeezenet1_0',
'squeezenet1_1',
'vgg',
'vgg11',
'vgg11_bn',
'vgg13',
'vgg13_bn',
'vgg16',
'vgg16_bn',
'vgg19',
...]
```

從上方的輸出可以發現有些為大寫字母，有些則為小寫。

大寫表示 Python 中的類別 (Class)，小寫表示 Python 中的函式 (Function)。舉例來說，我們可以直將使用「ResNet」Class 建立該模型。

但是如果我們希望取得一些客製化 ResNet 模型，例如：101 層的 ResNet，則可以呼叫「resnet101」函式；18 層的 ResNet，則可以呼叫「resnet18」函式。

## 載入事先訓練過的 ResNet 模型

從 TorchVision 中載入 ResNet 模型時，我們也將「pretrained」設為 True，確保模型中的參數已經事先訓練過：

```
resnet = models.resnet101(pretrained=True, progress=True)
```

並顯示 ResNet 的模型架構：

```
resnet
```

```
ResNet(
(conv1): Conv2d(3, 64, kernel_size=(7, 7), stride=(2, 2), padding=(3, 3), bias=False)
(bn1): BatchNorm2d(64, eps=1e-05, momentum=0.1, affine=True, track_running_stats=True)
(relu): ReLU(inplace=True)
(maxpool): MaxPool2d(kernel_size=3, stride=2, padding=1, dilation=1, ceil_mode=False)
(layer1): Sequential(
    (0): Bottleneck(
        (conv1): Conv2d(64, 64, kernel_size=(1, 1), stride=(1, 1), bias=False)
        (bn1): BatchNorm2d(64, eps=1e-05, momentum=0.1, affine=True, track_running_stats=True)
        (conv2): Conv2d(64, 64, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1), bias=False)
        (bn2): BatchNorm2d(64, eps=1e-05, momentum=0.1, affine=True, track_running_stats=True)
        (conv3): Conv2d(64, 256, kernel_size=(1, 1), stride=(1, 1), bias=False)
        (bn3): BatchNorm2d(256, eps=1e-05, momentum=0.1, affine=True, track_running_stats=True)
        (relu): ReLU(inplace=True)
        (downsample): Sequential(
            (0): Conv2d(64, 256, kernel_size=(1, 1), stride=(1, 1), bias=False)
            (1): BatchNorm2d(256, eps=1e-05, momentum=0.1, affine=True, track_running_stats=True)
        )
    )
    (1): Bottleneck(
        (conv1): Conv2d(256, 64, kernel_size=(1, 1), stride=(1, 1), bias=False)
        (bn1): BatchNorm2d(64, eps=1e-05, momentum=0.1, affine=True, track_running_stats=True)
        (conv2): Conv2d(64, 64, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1), bias=False)
        (bn2): BatchNorm2d(64, eps=1e-05, momentum=0.1, affine=True, track_running_stats=True)
        (conv3): Conv2d(64, 256, kernel_size=(1, 1), stride=(1, 1), bias=False)
        (bn3): BatchNorm2d(256, eps=1e-05, momentum=0.1, affine=True, track_running_stats=True)
        (relu): ReLU(inplace=True)
    )
...
)
...
(avgpool): AdaptiveAvgPool2d(output_size=(1, 1))
(fc): Linear(in_features=2048, out_features=1000, bias=True)
)
```

我們可以發現 ResNet 是一個相當「深」的模型！ResNet 之所以這麼有名，這是他提出了一些技巧使得很深也就是層數很大的模型，能夠更容易被訓練起來。

仔細觀察 ResNet 模型的最後一層，是一個 Linear Layer，輸出的向量長度為 1000。表示我們輸入一張圖片到 ResNet 後，ResNet 會輸出一個 1000 維的向量（向量中包含 1000 個元素），每一個元素都表示這張圖片屬於這個類別的分數。

接著，我們計算 ResNet 模型中的參數數量：

```
sum([param.numel() for param in resnet.parameters()])
```

可以發現 ResNet 中的參數量高達 4454 萬個！然而這些參數都已經事先透過 ImageNet 訓練資料集訓練過，替我們省去了一個麻煩事。

## 定義圖像預處理的方式

在實際輸入圖像到 ResNet 之前，我們必須先對圖像進行預處理。也就是說，我們不是隨便拿一張圖片就可以直接丟到 ResNet 模型中，我們所輸入的圖片必須符合 ResNet 的規定，才能有最佳的預測結果。

我們可以透過 TorchVision 中的 transforms 進行圖像的預處理：

```
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])
```

在上方的 transforms.Compose 中，我們定義了以下圖像預處理的方式：

- transforms.Resize(256)：將圖像尺寸轉為 256 × 256
- transforms.CenterCrop(224)：將圖像裁切為 224× 224
- transforms.ToTensor()：將圖像轉為 PyTorch Tensor
- transforms.Normalize：將圖像中的每一個維度進行標準化

在輸入圖像到 ResNet 之前，我們就會先讓圖像進行上述步驟的預處理，才將處理過後的圖像輸入到 ResNet 中。

## 下載 & 讀取圖片

接著，我們需要到網路上隨便找一些感興趣的圖片，並將其下載後存放於工作目錄中。

在我們的程式碼範例中，我們透過 curl 下載三張圖片：

```
!curl https://www.princeton.edu/sites/default/files/styles/half_2x/public/images/2022/02/KOA_Nassau_2697x1517.jpg?itok=iQEwihUn > dog.jpg
!curl https://images.theconversation.com/files/443350/original/file-20220131-15-1ndq1m6.jpg > cat.jpg
!curl https://static.onecms.io/wp-content/uploads/sites/28/2020/02/brussels-airlines-smurfs-plane-PLANEPAINT0418.jpg > plane.jpg
```

分別對應以下三張圖片：

![dog](images/dog-1024x576.jpg)

source: https://www.princeton.edu

![cat](images/cat-300x221.jpg)

source: https://images.theconversation.com

![plane](images/plane-1024x640.jpg)

source: https://static.onecms.io

我們希望 ResNet 可以正確地將這三張圖片進行分類！

接著，我們透過 PIL 套件，載入我們剛剛所下載的三張圖片：

```
img1 = Image.open("dog.jpg")
img2 = Image.open("cat.jpg")
img3 = Image.open("plane.jpg")
```

如果你在 Jupyter 環境中執行，你可以直接呼叫 display 函式顯示圖片：

```
display(img3)
```

## 對圖片進行預處理

在這個步驟中，我們利用我們剛剛定義的 process，對圖像進行預處理：

```
img1 = preprocess(img1)
img2 = preprocess(img2)
img3 = preprocess(img3)
```

並觀察他們的 shape：

```
print(f"img1 shape: {img1.shape}")
print(f"img2 shape: {img2.shape}")
print(f"img3 shape: {img3.shape}")
```

可以發現全部都變成了 3 × 224 × 224。

## 將圖像輸入到 ResNet 中

開始進行模型推論之前，需要先將模型轉為「eval」模式：

```
resnet.eval()
```

我們有三張圖片，我們希望一次輸入這三張圖片，而不是一張張輸入。因此，我們要將這三張圖片打包成為一個 Batch。

```
inp_batch = torch.stack([img1, img2, img3])
```

並將他們輸入到 ResNet 中：

```
out_batch = resnet(inp_batch)
```

查看 ResNet 的輸出 Shape：

```
out_batch.shape
```

```
torch.Size([3, 1000])
```

由模型的輸出結果可以了解到，模型針對每一張圖片都輸出一個 1000 個維度的向量（也就是有 1000 個數值），每一個數值都表示該張圖片屬於這一個類別的分數。

## 處理模型的輸出

然而，雖然我們已經知道模型的輸出包含 1000 個類別的分數，但是卻不知道實際的類別名稱。因為我們所下載的 ResNet 是事先訓練於 ImageNet 資料集上，因此他的輸出格式是符合 ImageNet 所定義的 1000 個類別。

下載 ImageNet 所定義的 1000 個類別：

```
!curl https://raw.githubusercontent.com/xmartlabs/caffeflow/master/examples/imagenet/imagenet-classes.txt > imagenet-classes.txt
```

將 txt 文件中的資料取出：

```
with open("/content/imagenet-classes.txt", 'r') as f:
    labels = [line.strip() for line in f.readlines()]
```

labels 中將會存放 1000 個類別的實際名稱：

```
labels
```

```
['tench, Tinca tinca',
'goldfish, Carassius auratus',
'great white shark, white shark, man-eater, man-eating shark, Carcharodon carcharias',
'tiger shark, Galeocerdo cuvieri',
'hammerhead, hammerhead shark',
'electric ray, crampfish, numbfish, torpedo',
'stingray',
'cock',
'hen',
'ostrich, Struthio camelus',
'brambling, Fringilla montifringilla',
'goldfinch, Carduelis carduelis',
'house finch, linnet, Carpodacus mexicanus',
'junco, snowbird',
'indigo bunting, indigo finch, indigo bird, Passerina cyanea',
'robin, American robin, Turdus migratorius',
'bulbul',
'jay',
'magpie',
'chickadee',
'water ouzel, dipper',
'kite',
'bald eagle, American eagle, Haliaeetus leucocephalus',
'vulture',
'great grey owl, great gray owl, Strix nebulosa',
'European fire salamander, Salamandra salamandra',
'common newt, Triturus vulgaris',
'eft',
'spotted salamander, Ambystoma maculatum',
'axolotl, mud puppy, Ambystoma mexicanum',
'bullfrog, Rana catesbeiana',
'tree frog, tree-frog',
'tailed frog, bell toad, ribbed toad, tailed toad, Ascaphus trui',
'loggerhead, loggerhead turtle, Caretta caretta',
'leatherback turtle, leatherback, leathery turtle, Dermochelys coriacea',
'mud turtle',
'terrapin',
'box turtle, box tortoise',
'banded gecko',
'common iguana, iguana, Iguana iguana',
'American chameleon, anole, Anolis carolinensis',
'whiptail, whiptail lizard',
'agama',
'frilled lizard, Chlamydosaurus kingi',
'alligator lizard',
'Gila monster, Heloderma suspectum',
'green lizard, Lacerta viridis',
'African chameleon, Chamaeleo chamaeleon',
'Komodo dragon, Komodo lizard, dragon lizard, giant lizard, Varanus komodoensis',
'African crocodile, Nile crocodile, Crocodylus niloticus',
'American alligator, Alligator mississipiensis',
'triceratops',
'thunder snake, worm snake, Carphophis amoenus',
'ringneck snake, ring-necked snake, ring snake',
'hognose snake, puff adder, sand viper',
'green snake, grass snake',
'king snake, kingsnake',
...
]
```

接著，針對每一張圖片我們要取出分數最大的那一個類別，也就是模型認為該張圖片的所屬類別：

```
_, index = torch.max(out_batch, dim=1)
```

```
index
```

```
tensor([207, 281, 404]
```

index 是一個 3 個維度的 Tensor，207 表示第一張圖片所屬的類別、281 表示第二張圖片所屬的類別、404 則表示第三張圖片所屬的類別。

我們可以透過剛剛建立的 label，將數字類別轉為實際名稱：

```
for idx in index:
    print(labels[idx.item()])
```

輸出結果：

```
golden retriever
tabby, tabby cat
airliner
```

我們可以發現，模型確實正確地將三張圖片進行分類，第一張圖片為「黃金獵犬」、第二張圖片為「虎斑貓」、第三張圖片則是「飛機」。

## 結語

在本篇文章中，我們學會如何透過 TorchVision 載入已經訓練好的 ResNet 模型，並進行模型推論。

除了圖像分類之外，在其他許多人工智慧的應用上我們都可以善用別人訓練好的模型。因為有時候我們沒有辦法取得那麼大量的資料集，或是沒有辦法訓練這麼龐大的模型，因此我們可以基於別人幫我們用龐大資料集訓練好的模型，再使用我們自己準備的資料集對模型進行訓練。

這樣可以大幅降低我們訓練模型的成本，而這樣的技巧又稱為 [Transfer Learning](https://en.wikipedia.org/wiki/Transfer_learning#:~:text=Transfer%20learning%20(TL)%20is%20a,when%20trying%20to%20recognize%20trucks.)。而我們在使用我們自己所準備的資料集訓練模型時，通常資料集不會太大，也只會針對模型的一部份參數進行訓練，這樣的訓練過程又稱為 Fine Tune。
