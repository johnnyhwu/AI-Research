# Google Colaboratory 介紹

## 前言

本篇是 Python 程式語言入門教學的第一篇文章。學程式最容易卡關的地方，往往不是語法本身，而是還沒開始寫就先被環境搞死：Python 該裝哪個版本、pip 裝套件又跳出一堆錯誤，最後熱情都消磨在安裝上了。

Google Colaboratory（以下簡稱 Colab）正好可以繞過這一關。它是一個開在瀏覽器裡就能直接寫、直接跑 Python 的環境，不用安裝任何東西。這篇文章會用 6 個問題把 Colab 講清楚：它是什麼、有什麼限制、怎麼開、怎麼跑程式、介面上有哪些東西要認識，以及初學者該記哪幾個快捷鍵。

## 問題 1：Google Colab 是什麼？

Colab 是 Google 提供的服務，讓任何人都可以透過瀏覽器撰寫以及執行 Python 程式碼。對程式初學者來說最大的好處，就是省去架設環境的困擾——打開瀏覽器、登入 Google 帳號，就可以開始寫了。

它底層是基於 [Jupyter Notebook](https://jupyter.org/) 的開發環境，而且許多常用的套件（NumPy、pandas 這類）都已經先裝好，因此非常適合作為資料科學的開發環境。Colab 也提供免費的運算資源 (GPU)，讓我們可以加速機器學習模型的訓練。（免費 GPU 的可用額度近年已經比 2022 年當時緊縮不少，但拿來練習仍然夠用。）

## 問題 2：Google Colab 有什麼限制嗎？

當然有。免費的服務，資源供應上一定會有限制。

第一個限制是硬體規格。Colab 免費提供的 CPU 與 GPU 不會是最好的那一批，程式的運行效能可能比不上你手上的電腦，但對資料科學領域的初學者而言已經相當夠用。

第二個限制是記憶體 (RAM)。如果模型的參數太多或是資料集太大，就會出現記憶體不足的錯誤。實務上遇到這種情況，通常是先想辦法縮小批次大小或改讀部分資料，而不是硬撐。

## 問題 3：如何開啟 Google Colab？

對 Colab 有基本的了解後，就可以開始使用了。第一步，**進入到自己的 Google Drive 頁面**；接著，**在畫面空白處點選「右鍵」，選擇「更多」，再點擊「Google Colaboratory」**。

![Google Drive 資料夾頁面，在空白處按右鍵後展開「更多」選單，其中列出 Google Colaboratory 選項。](img-001)
*Google Drive 的資料夾頁面*

點擊後，就會進入到 **Colab 頁面**囉！這個檔案會直接存在你的 Google Drive 裡，之後從雲端硬碟點兩下就能再打開。

![Google Colab 的編輯頁面，上方是檔案名稱與工具列，中間是一個空白的程式碼儲存格。](img-002)
*Google Colab 頁面*

## 問題 4：如何執行 Python 程式碼？

Colab 中每一個「格子」都是一個 Cell，我們可以在 Cell 中輸入程式碼，並按下 Shift + Enter 執行，執行完還會自動幫你新增一個新的 Cell。如果是剛開啟的 Colab 環境，則必須先等待資源分配完成後，才能執行程式碼。

![Colab 中的一個程式碼儲存格，左側有執行按鈕，下方顯示程式的執行結果。](img-003)
*Google Colab 中的 Cell*

## 問題 5：Colab 中要認識的基本介面有哪些？

Colab 的畫面元素不多，先把下面這 6 個區塊認熟，之後看到任何教學都不會迷路。

![Google Colab 介面示意圖，以編號標示出檔案名稱、工具列、儲存格、留言與共用、連線狀態與側邊工具欄六個區塊。](img-004)
*介紹 Google Colab 中的基本元件*

1. **檔案名稱**：在此區塊我們可以命名這個 Colab 檔案。Colab 因為是基於 Jupyter，所以也是一個 Notebook 的形式，副檔名為 `.ipynb`。（如果是一般的 Python 檔，副檔名會是 `.py`）
2. **工具列**：工具列區塊中有非常多功能可以使用，常用的有：檔案、編輯、插入與執行階段。
   - 檔案：可以透過「在雲端硬碟中尋找」找出此 Colab 在雲端硬碟中的位置，或是透過「上傳筆記本」從雲端硬碟、電腦或是 GitHub 上傳筆記本到 Colab 中。也可以透過「下載」把此 Colab 存成 `.py` 檔或 `.ipynb` 檔。
   - 編輯：可以「復原刪除的儲存格」、「刪除所選的儲存格」，或是透過「筆記本設定」選擇硬體加速器。預設情況不使用硬體加速器，訓練模型時可以在這裡切成 GPU 加速訓練。
   - 插入：可以插入「程式碼儲存格」或是「文字儲存格」。
   - 執行階段：可以決定要執行哪些儲存格，或是透過「重新啟動執行階段」把 Colab 環境重開（Colab 有時會當掉），也可以用「變更執行階段類型」選擇是否使用硬體加速器。最後，「管理工作階段」可以查看目前正在執行的 Colab 檔案。
3. **儲存格 (Cell)**：Colab 就像是一個 Notebook，由一個又一個的「儲存格」所組成。儲存格可以是「程式碼」或是「文字」：程式碼儲存格用來輸入 Python 程式碼，文字儲存格則是透過 Markdown 語法來撰寫。
4. **留言與共用**：Colab 的一大特色就是可以把你的 Notebook 分享給其他人，讓其他人也能夠在同一份 Colab 上編輯，協作方式跟 Google 文件幾乎一樣。
5. **連線狀態**：Colab 背後使用的是 Google 提供的運算資源，因此要正常使用 Colab，必須確保已經連線到遠端的硬體資源。這一區也會顯示目前 RAM 與硬碟的用量。
6. **側邊工具欄**：側邊工具欄是 Colab 上較為進階的功能，由上而下依序為：目錄、文字尋找與取代、程式碼片段與檔案。
   - 目錄：顯示目前 Colab 中所有 Cell 的架構。Colab 是由很多個 Cell 所組成，Cell 底下又可以包含很多 Cell，透過目錄可以清楚看出 Cell 之間的階層關係。
   - 文字尋找與取代：單純的文字尋找與取代。
   - 程式碼片段：可以在這裡搜尋一些常用的程式碼片段，直接複製到 Colab 中使用。例如要從 Colab 讀取 Google Drive 裡的檔案，就可以搜尋「Google Mount」，找到如何把 Google Drive 掛載進 Colab 環境。
   - 檔案：Colab 的環境就像是一台虛擬電腦，在這一區可以看到 Colab 目前所在的根目錄。

## 問題 6：Colab 中基本的快捷鍵有哪些？

Colab 的快捷鍵非常多，也可以在「上方工具列」>「工具」>「鍵盤快速鍵」中自行設定。不過對初學者而言不需要全部記住，熟悉最常用的那幾個就能明顯加快開發速度。

最基本的兩種操作是切換 Cell 的模式。Colab 的 Cell 有 Code 與 Markdown 兩種模式：Code 模式用來寫 Python 程式碼，Markdown 模式則是用來寫說明或註解。如果對 Markdown 語法不熟，不管語法直接打上你想留下的說明文字也完全沒問題。

- 將 Cell 轉成 Code 區塊：⌘/Ctrl + m + y
- 將 Cell 轉成 Markdown 區塊：⌘/Ctrl + m + m

有時我們也需要把整個 Cell 刪除或復原：

- 將 Cell 刪除：⌘/Ctrl + m + d
- 將 Cell 復原：⌘/Ctrl + m + z

在 Cell 中寫好 Python 程式碼後要執行，有兩種方式：

- 執行此 Cell：⌘/Ctrl + Enter
- 執行此 Cell 再往下新增一個 Cell：Shift + Enter

想把焦點移到別的 Cell，又懶得用滑鼠點：

- 聚焦上一個 Cell：⌘/Ctrl + p
- 聚焦下一個 Cell：⌘/Ctrl + n

當程式碼愈來愈多，要找某一個變數會愈來愈困難，這時就可以用「側邊工具欄」中的「文字尋找與取代」：

- 尋找某一段文字：⌘/Ctrl + h

最後也是最重要的，編輯時不要忘記「手動」存一下（Colab 基本上會自動儲存新的變更，但手動存一次比較安心）：

- 儲存 Colab：⌘/Ctrl + s

## 結論

這篇文章帶著大家認識了 Colab 的基本觀念：它是什麼、免費資源的限制在哪、怎麼從 Google Drive 開一份新的 Notebook、怎麼在 Cell 裡跑程式碼，以及介面與快捷鍵。這些東西不需要一次全部背起來，用到卻想不起來時，再回來翻一下就好。

Colab 還有不少進階操作（掛載 Google Drive、切換 GPU、安裝額外套件等），會在其他文章中另外介紹。下一篇文章，我們就要正式開始學習 Python 語法了。

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Google Drive 的資料夾頁面",
    "why_used": "示範開啟 Colab 的第一步，讓讀者知道要在 Google Drive 的哪個位置按右鍵找到 Google Colaboratory。",
    "agent_match_hint": "一張 Google Drive 檔案總管的截圖，畫面上有右鍵展開的選單，選單中可看到「更多」與 Google Colaboratory 項目。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Google Colab 頁面",
    "why_used": "承接上一步，讓讀者確認點下去之後應該看到什麼樣的畫面。",
    "agent_match_hint": "一張 Colab Notebook 剛開啟時的整頁截圖，上方為檔案名稱與工具列，中間是空白的程式碼儲存格。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Google Colab 中的 Cell",
    "why_used": "搭配說明 Cell 的概念與 Shift + Enter 執行程式碼的操作。",
    "agent_match_hint": "一張聚焦在單一儲存格的截圖，左側有執行的播放按鈕，儲存格下方顯示執行輸出。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "介紹 Google Colab 中的基本元件",
    "why_used": "作為介面導覽的對照圖，讓讀者把文中編號 1 到 6 的說明對應回畫面上的實際位置。",
    "agent_match_hint": "一張 Colab 介面截圖，畫面上以數字標號標出檔案名稱、工具列、儲存格、留言與共用、連線狀態、側邊工具欄等區塊。"
  }
]
```
