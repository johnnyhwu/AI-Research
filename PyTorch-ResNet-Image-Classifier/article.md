# 利用 PyTorch 的 ResNet 快速建立一個圖像分類器

## 前言

![利用 PyTorch 的 ResNet 快速建立一個圖像分類器 文章題圖。](img-001)
*利用 PyTorch 的 ResNet 快速建立一個圖像分類器 文章題圖 [source: Pixabay]*

這篇文章要做的事很單純：用 PyTorch 的 TorchVision 函式庫載入一個「已經訓練好」的模型，直接拿來做模型推論 (inference)，不自己訓練任何東西。

我們要解決的問題是「圖像分類」，所以會從 TorchVision 載入 Residual Neural Network (ResNet)，餵幾張自己挑的圖片進去，看它分得對不對。整個流程從載入模型、定義圖像預處理、送圖片進模型，一路做到把模型輸出的數字翻譯成人看得懂的類別名稱。

閱讀之前，建議先有機器學習中「模型訓練」與「模型推論」的基本概念，本站另有專文介紹；如果想更進一步理解 Neural Network 怎麼分類圖片，也可以參考「Neural Network 如何進行圖像分類」那篇。

完整程式碼放在 [Colab](https://colab.research.google.com/drive/1V60OaghA1pW5SkqKrvtCtLXkojkyZqIA?usp=sharing) 與 [GitHub](https://github.com/johnnyhwu/data-science-practice/blob/main/pytorch-resnet-image-classification/main.ipynb)，可以邊看邊跑。

## 載入函式庫

TorchVision 中有許多已經開源的模型，而且許多模型都已經事先透過 ImageNet 資料集訓練過，因此我們可以不必從頭開始訓練模型，直接使用訓練好的模型，體驗「模型推論」的概念。

這件事的價值在於成本：ImageNet 有一百多萬張標註好的圖片，從零訓練一個模型要耗掉大量的 GPU 時間，而載入別人訓練好的權重只要一行程式碼。

首先，載入我們在這個小專案中會使用到的函式庫：

```python
import torch
from torchvision import models
from torchvision import transforms

import json
from PIL import Image
```

## 查看 TorchVision 中的模型

想知道 TorchVision 到底提供了哪些模型，用 `dir()` 把 `models` 這個 module 底下的名稱列出來就好：

```python
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

大寫表示 Python 中的類別 (Class)，小寫表示 Python 中的函式 (Function)。舉例來說，我們可以直接使用「ResNet」Class 建立該模型。

但是如果我們希望取得一些客製化 ResNet 模型，例如：101 層的 ResNet，則可以呼叫「resnet101」函式；18 層的 ResNet，則可以呼叫「resnet18」函式。換句話說，函式名稱後面的數字就是網路的層數，層數越多、模型越大，準確度通常也越高，但推論也越慢。

## 載入事先訓練過的 ResNet 模型

從 TorchVision 中載入 ResNet 模型時，我們也將「pretrained」設為 True，確保模型中的參數已經事先訓練過（在較新版本的 TorchVision 中，`pretrained` 已被 `weights` 參數取代，但概念相同）：

```python
resnet = models.resnet101(pretrained=True, progress=True)
```

`progress=True` 只是讓它在下載權重檔的時候顯示進度條，第一次執行會需要等一下。

並顯示 ResNet 的模型架構：

```python
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

光看這份被截斷的架構就知道，ResNet 是一個相當「深」的模型。ResNet 之所以這麼有名，是因為它提出了一些技巧，讓層數很大的模型也能夠更容易被訓練起來。

仔細觀察 ResNet 模型的最後一層，是一個 Linear Layer，輸出的向量長度為 1000。表示我們輸入一張圖片到 ResNet 後，ResNet 會輸出一個 1000 維的向量（向量中包含 1000 個元素），每一個元素都表示這張圖片屬於這個類別的分數。這個 1000 不是隨便挑的數字，而是 ImageNet 所定義的類別數量，後面處理輸出時還會再遇到它。

接著，我們計算 ResNet 模型中的參數數量：

```python
sum([param.numel() for param in resnet.parameters()])
```

可以發現 ResNet 中的參數量高達 4454 萬個！然而這些參數都已經事先透過 ImageNet 訓練資料集訓練過，替我們省去了一個麻煩事。

## 定義圖像預處理的方式

在實際輸入圖像到 ResNet 之前，我們必須先對圖像進行預處理。也就是說，我們不是隨便拿一張圖片就可以直接丟到 ResNet 模型中，我們所輸入的圖片必須符合 ResNet 的規定，才能有最佳的預測結果。

道理很直接：模型當初是在「被處理成某種固定格式」的圖片上訓練出來的，推論時如果餵進格式不同的圖片，模型看到的數值分佈就跟訓練時不一樣，結果自然會歪掉。

我們可以透過 TorchVision 中的 transforms 進行圖像的預處理：

```python
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

`Compose` 的意思就是「把這幾個步驟串成一條 pipeline」，呼叫一次 `preprocess(img)` 就會依序跑完上面四個動作。至於 `Normalize` 裡那組 `mean` 與 `std`，是 ImageNet 資料集在 RGB 三個 channel 上的統計值，照抄就對了。

在輸入圖像到 ResNet 之前，我們就會先讓圖像進行上述步驟的預處理，才將處理過後的圖像輸入到 ResNet 中。

## 下載 & 讀取圖片

接著，我們需要到網路上隨便找一些感興趣的圖片，並將其下載後存放於工作目錄中。

在我們的程式碼範例中，我們透過 curl 下載三張圖片：

```
!curl https://www.princeton.edu/sites/default/files/styles/half_2x/public/images/2022/02/KOA_Nassau_2697x1517.jpg?itok=iQEwihUn > dog.jpg
!curl https://images.theconversation.com/files/443350/original/file-20220131-15-1ndq1m6.jpg > cat.jpg
!curl https://static.onecms.io/wp-content/uploads/sites/28/2020/02/brussels-airlines-smurfs-plane-PLANEPAINT0418.jpg > plane.jpg
```

（開頭的 `!` 是 Jupyter／Colab 的語法，表示這一行要交給 shell 執行，不是 Python 程式碼。）

分別對應以下三張圖片：

![一隻黃金獵犬的照片，作為第一張測試圖片。](img-002)
*測試用圖片之一：狗 [source: www.princeton.edu]*

![一隻虎斑貓的照片，作為第二張測試圖片。](img-003)
*測試用圖片之二：貓 [source: images.theconversation.com]*

![一架彩繪塗裝客機的照片，作為第三張測試圖片。](img-004)
*測試用圖片之三：飛機 [source: static.onecms.io]*

我們希望 ResNet 可以正確地將這三張圖片進行分類！

接著，我們透過 PIL 套件，載入我們剛剛所下載的三張圖片：

```python
img1 = Image.open("dog.jpg")
img2 = Image.open("cat.jpg")
img3 = Image.open("plane.jpg")
```

如果你在 Jupyter 環境中執行，你可以直接呼叫 display 函式顯示圖片：

```python
display(img3)
```

## 對圖片進行預處理

在這個步驟中，我們利用我們剛剛定義的 preprocess，對圖像進行預處理：

```python
img1 = preprocess(img1)
img2 = preprocess(img2)
img3 = preprocess(img3)
```

並觀察他們的 shape：

```python
print(f"img1 shape: {img1.shape}")
print(f"img2 shape: {img2.shape}")
print(f"img3 shape: {img3.shape}")
```

可以發現全部都變成了 3 × 224 × 224。三張原本尺寸各不相同的圖片，經過同一條 pipeline 之後被壓成一樣的形狀，這正是後面能把它們打包成一個 Batch 的前提。

## 將圖像輸入到 ResNet 中

開始進行模型推論之前，需要先將模型轉為「eval」模式：

```python
resnet.eval()
```

這一行不能省略。模型裡有些層（例如 BatchNorm、Dropout）在訓練時和推論時的行為並不一樣，`eval()` 就是告訴 PyTorch「現在是推論，不是訓練」。

我們有三張圖片，我們希望一次輸入這三張圖片，而不是一張張輸入。因此，我們要將這三張圖片打包成為一個 Batch。

```python
inp_batch = torch.stack([img1, img2, img3])
```

`torch.stack` 會在最前面多疊一個維度出來，三張 3 × 224 × 224 的圖片就變成一個 3 × 3 × 224 × 224 的 Tensor，第一個 3 就是 batch size。

並將他們輸入到 ResNet 中：

```python
out_batch = resnet(inp_batch)
```

查看 ResNet 的輸出 Shape：

```python
out_batch.shape
```

```
torch.Size([3, 1000])
```

由模型的輸出結果可以了解到，模型針對每一張圖片都輸出一個 1000 個維度的向量（也就是有 1000 個數值），每一個數值都表示該張圖片屬於這一個類別的分數。

## 處理模型的輸出

然而，雖然我們已經知道模型的輸出包含 1000 個類別的分數，但是卻不知道實際的類別名稱。因為我們所下載的 ResNet 是事先訓練於 ImageNet 資料集上，因此他的輸出格式是符合 ImageNet 所定義的 1000 個類別。

換句話說，模型只會告訴你「第 207 個類別分數最高」，至於第 207 個類別是什麼，得自己去查對照表。

下載 ImageNet 所定義的 1000 個類別：

```
!curl https://raw.githubusercontent.com/xmartlabs/caffeflow/master/examples/imagenet/imagenet-classes.txt > imagenet-classes.txt
```

將 txt 檔案中的資料取出：

```python
with open("/content/imagenet-classes.txt", 'r') as f:
    labels = [line.strip() for line in f.readlines()]
```

labels 中將會存放 1000 個類別的實際名稱：

```python
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

```python
_, index = torch.max(out_batch, dim=1)
```

`torch.max` 會同時回傳「最大值」與「最大值的位置」，這裡我們只在乎位置，所以第一個回傳值直接用 `_` 丟掉。`dim=1` 表示沿著那條長度 1000 的類別軸去找最大值。

```python
index
```

```
tensor([207, 281, 404]
```

index 是一個 3 個維度的 Tensor，207 表示第一張圖片所屬的類別、281 表示第二張圖片所屬的類別、404 則表示第三張圖片所屬的類別。

我們可以透過剛剛建立的 labels，將數字類別轉為實際名稱：

```python
for idx in index:
    print(labels[idx.item()])
```

輸出結果：

```
golden retriever
tabby, tabby cat
airliner
```

我們可以發現，模型確實正確地將三張圖片進行分類，第一張圖片為「黃金獵犬」、第二張圖片為「虎斑貓」、第三張圖片則是「飛機」。而且它給的答案比我們預期的還細：不只答對是狗，還答出是黃金獵犬；不只答對是貓，還答出是虎斑貓。

## 結論

在本篇文章中，我們學會如何透過 TorchVision 載入已經訓練好的 ResNet 模型，並進行模型推論。整條流程其實只有五個動作：載入模型、定義預處理、讀圖、打包成 Batch 送進模型、把輸出的 index 對回類別名稱。

除了圖像分類之外，在其他許多人工智慧的應用上我們都可以善用別人訓練好的模型。因為有時候我們沒有辦法取得那麼大量的資料集，或是沒有辦法訓練這麼龐大的模型，因此我們可以基於別人幫我們用龐大資料集訓練好的模型，再使用我們自己準備的資料集對模型進行訓練。

這樣可以大幅降低我們訓練模型的成本，而這樣的技巧又稱為 [Transfer Learning](https://en.wikipedia.org/wiki/Transfer_learning)。而我們在使用我們自己所準備的資料集訓練模型時，通常資料集不會太大，也只會針對模型的一部份參數進行訓練，這樣的訓練過程又稱為 Fine Tune。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "利用 PyTorch 的 ResNet 快速建立一個圖像分類器 文章題圖 [source: Pixabay]",
    "why_used": "原文的文章題圖，放在前言開頭作為視覺開場。",
    "agent_match_hint": "原始貼文最上方的橫幅題圖，來自 Pixabay 的圖庫照片。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "測試用圖片之一：狗 [source: www.princeton.edu]",
    "why_used": "對應程式碼中透過 curl 下載的第一張測試圖片 dog.jpg，讓讀者看到模型實際輸入的內容。",
    "agent_match_hint": "一張狗的照片，後續被 ResNet 分類為 golden retriever。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "測試用圖片之二：貓 [source: images.theconversation.com]",
    "why_used": "對應程式碼中透過 curl 下載的第二張測試圖片 cat.jpg。",
    "agent_match_hint": "一張貓的照片，尺寸較小，後續被 ResNet 分類為 tabby cat。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "測試用圖片之三：飛機 [source: static.onecms.io]",
    "why_used": "對應程式碼中透過 curl 下載的第三張測試圖片 plane.jpg。",
    "agent_match_hint": "一張客機的照片，帶有彩繪塗裝，後續被 ResNet 分類為 airliner。"
  }
]
```
