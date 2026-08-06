# PyTorch 支援 Apple Silicon GPU (Mac M1)

## 前言

2022 年 5 月 18 日這天，[PyTorch 在官方部落格宣布](https://pytorch.org/blog/introducing-accelerated-pytorch-training-on-mac/)：從 PyTorch 1.12 版本開始，可以直接使用 Apple Silicon 上的 GPU 來訓練模型。換句話說，如果你的 MacBook Air 或 MacBook Pro 用的是 M1 晶片而不是 Intel 晶片，那麼用 PyTorch 建立的 Neural Network 就能吃到 GPU 的加速（在這之前，Mac 上想用 GPU 訓練只有 TensorFlow 這條路）。

![PyTorch 官方宣布支援 Apple Silicon GPU 的宣傳圖。](img-001)
*PyTorch 於官方部落格宣布支援 Apple Silicon GPU*

本文會走完整套流程：從確認系統版本、安裝 Miniconda、建立虛擬環境並裝好支援 M1 GPU 的 PyTorch，最後用一個簡單的分類問題實際量一下 M1 CPU 與 M1 GPU 的訓練時間差多少。

（這篇文章寫於 M1 GPU 支援還在 nightly build 的時期，因此下面裝的是 nightly 版本；該功能後來已隨 PyTorch 1.12 正式進入 stable 版本。）

## 確認 macOS 版本

安裝 PyTorch 之前，先確認 macOS 版本大於或等於 12.3。這個門檻不是隨便訂的，因為新版 PyTorch 的 GPU 加速底層是走 [Apple's Metal Performance Shaders (MPS)](https://developer.apple.com/documentation/metalperformanceshaders)，而完整的 MPS 後端要 macOS 12.3 以上才有。

打開 Terminal 輸入以下指令，就能查看自己的 macOS 版本：

```
sw_vers
```

## 安裝 Miniconda

開發 Python 專案時，不同專案往往需要不同版本的套件。比較好的做法是替每個專案各建一個虛擬環境，讓專案之間的套件互不干擾，才不會為了裝新東西反而弄壞舊專案。

Python 管理套件的工具有很多種，這裡選擇用 [Anaconda](https://www.anaconda.com/) 來管理。不過 Anaconda 本身包山包海，裝下去一堆用不到的工具，所以我們改裝精簡版的 [Miniconda](https://docs.conda.io/en/latest/miniconda.html)。

Miniconda 支援的作業系統很多，要挑對應 M1 的版本，也就是 [Miniconda3 macOS Apple M1 ARM 64-bit bash](https://repo.anaconda.com/miniconda/Miniconda3-py38_4.12.0-MacOSX-arm64.sh)。這裡的眉角是別誤下載 x86 版本，否則整個環境都會跑在 Rosetta 轉譯之下，效能會打折。

下載完成之後，開啟 Terminal 找到這個 script 檔案：

![在 Terminal 中以指令列出目錄內容，可以看到下載回來的 Miniconda 安裝 script 檔案。](img-002)
*在 Terminal 中找到下載回來的 Miniconda 安裝 script*

透過 chmod 確保這個檔案能夠被執行：

```
sudo chmod +x Miniconda3-py38_4.12.0-MacOSX-arm64.sh
```

接著執行這個 script：

```
./Miniconda3-py38_4.12.0-MacOSX-arm64.sh
```

跟著畫面上的指示操作，就能完成 Miniconda 的安裝。

## 建立 PyTorch 虛擬環境

一樣打開 Terminal，建立一個名為「pytorch-m1」的虛擬環境，並指定 Python 版本為 3.8：

```
conda create --name pytorch-m1 python=3.8
```

接著啟用這個虛擬環境：

```
conda activate pytorch-m1
```

透過 pip 安裝所需要的套件：

```
pip3 install --pre torch torchvision --extra-index-url https://download.pytorch.org/whl/nightly/cpu
```

等待大約 1 分鐘完成所有套件的安裝後，就大功告成囉！

## 在 PyTorch 中使用 M1 GPU

過去在 PyTorch 中要使用 Nvidia 的 GPU，我們會這樣指定 device：

```
device = torch.device("cuda")
```

要改用 M1 GPU，只需要把 cuda 換成 mps，其他寫法完全一樣，一樣是把 Tensor 與 Model 都 `.to(device)` 搬到這個 device 上：

```
device = torch.device("mps")
```

也就是說，原本寫好的 CUDA 訓練腳本，通常只要動這一行就能在 Mac 上跑起來。

## M1 CPU vs M1 GPU (1)

接著我用一個簡單的分類問題 MNIST Digit Classification，來比較在 MacBook Air 2020 上用 M1 CPU 與 M1 GPU 各自需要多少訓練時間。

我直接使用 [GitHub 上 pytorch/examples](https://github.com/pytorch/examples/blob/main/mnist/main.py) 提供的程式碼，分別用 CPU 與 GPU 訓練同一個模型，兩邊都訓練 5 個 Epochs 且 Batch Size 設為 64，唯一的變因就是 device。

下圖為兩者的時間差異：

![長條圖比較 MNIST 訓練中 M1 CPU 與 M1 GPU 每個 Epoch 所花費的時間，GPU 明顯較短。](img-003)
*Training Time of M1 CPU vs M1 GPU on MNIST*

M1 CPU 一個 Epoch 大約花了 28.96 秒，M1 GPU 一個 Epoch 約花了 18.26 秒，時間上**減少了 36.95%**。

## M1 CPU vs M1 GPU (2)

上面的測試用的是很小的模型與資料集，參考價值有限。[sebastianraschka](https://sebastianraschka.com/blog/2022/pytorch-m1-gpu.html) 在他的部落格上做了規模更大的比較：用 CIFAR-10 資料集訓練 VGG16，並橫向比較多種硬體裝置。

![長條圖比較不同硬體裝置上以 CIFAR-10 訓練 VGG16 所需的時間，包含 M1 CPU、M1 GPU 與其他裝置。](img-004)
*VGG16 on CIFAR10 [source: sebastianraschka.com]*

若單純比較 M1 Pro CPU 與 M1 Pro GPU，可以發現 GPU 的時間比 CPU **減少了 44.54%**。模型愈大，GPU 拉開的差距也愈明顯。

## 結論

本文說明了如何在 PyTorch 中啟用 M1 GPU，安裝上的重點是 macOS 12.3 以上加上 arm64 版本的環境，程式碼上則只要把 device 從 `cuda` 換成 `mps` 即可。效能方面，MNIST 上省下約 37% 的訓練時間，VGG16 on CIFAR-10 則約 44%。

不過老實說，即使 PyTorch 支援了 M1 GPU，拿筆電（MacBook Air 或 MacBook Pro）當作訓練神經網路的主力裝置仍然不太實際。訓練大型網路動輒數小時起跳，筆電長時間滿載過熱，對機器壽命並不友善。把它當成本機除錯、跑小實驗的工具會更合適。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "PyTorch 於官方部落格宣布支援 Apple Silicon GPU",
    "why_used": "作為文章開頭的主視覺，點出本文主題是 PyTorch 對 Apple Silicon GPU 的支援。",
    "agent_match_hint": "一張以 PyTorch 為主體的宣傳圖或 logo 圖。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "在 Terminal 中找到下載回來的 Miniconda 安裝 script",
    "why_used": "示範安裝 Miniconda 的步驟中，如何在 Terminal 裡定位到下載回來的 script 檔案。",
    "agent_match_hint": "一張 Terminal 視窗截圖，列出目錄內容並可看到 Miniconda3-py38_4.12.0-MacOSX-arm64.sh 這個檔案。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Training Time of M1 CPU vs M1 GPU on MNIST",
    "why_used": "支撐 MNIST 實測中 M1 GPU 較 M1 CPU 減少 36.95% 訓練時間的段落。",
    "agent_match_hint": "一張比較兩者訓練時間的長條圖，兩根長條分別代表 M1 CPU 與 M1 GPU，數值約為 28.96 秒與 18.26 秒。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "VGG16 on CIFAR10 [source: sebastianraschka.com]",
    "why_used": "引用外部部落格在 CIFAR-10 上訓練 VGG16 的跨硬體效能比較，佐證 M1 Pro GPU 較 CPU 減少 44.54% 時間。",
    "agent_match_hint": "一張橫跨多種硬體裝置的訓練時間比較圖，包含 M1 Pro CPU、M1 Pro GPU 等項目。"
  }
]
```
