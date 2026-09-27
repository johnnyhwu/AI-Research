# 簡單 5 步驟，美化你的 Terminal (macOS)

## 前言

身為一個 Programmer/Developer，Terminal 大概是每天開機第一個打開、最後一個關掉的工具。然而 macOS 內建的 Terminal 相當陽春，一片白底黑字，連自己現在站在哪個目錄、在哪個 Git branch 上都要自己 `pwd` 一下才知道，打 Code 的心情也跟著被消磨掉。

網路上這類美化教學不少，但很多寫得跳步驟，照著做常常在字型或設定檔那一關卡住，跑出一堆問號和方框。這篇文章用 5 個步驟走完整套流程 (Zsh + Oh My Zsh + Powerlevel10k)，並盡量說明每個步驟在做什麼、為什麼需要它，最後再補上 VS Code 內建 Terminal 的設定。

## 步驟 1：下載 Z Shell

Z shell 簡稱 Zsh，是一個基於 Bourne again shell (Bash) 所打造的 Shell，也是現在 macOS 上預設的 shell。整套美化的基礎都建立在 Zsh 上，所以第一步先確認你手上的 Terminal 用的是哪一個 shell：

```bash
echo $SHELL
```

如果輸出是 Zsh (`/bin/zsh`)，那麼可以直接跳過這步；如果不是的話，可以透過 Homebrew 下載 Zsh：

```bash
brew install zsh
```

## 步驟 2：下載 Oh My Zsh

[Oh My Zsh](https://ohmyz.sh/) 是一個用來管理 Zsh 設定的開源框架。說白了，它幫你把主題 (theme) 與外掛 (plugin) 的載入邏輯都寫好了，你只要在設定檔裡填上想用的名字，不必自己手刻一堆 shell script。接下來的主題就是靠它套上去的。

輸入以下指令，下載 Oh My Zsh：

```bash
sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

如果出現以下畫面，就代表下載成功啦！

![Terminal 中顯示 Oh My Zsh 安裝完成的 ASCII 字樣畫面。](img-001)
*下載 Oh My Zsh*

安裝過程中 Oh My Zsh 會幫你把原本的 `~/.zshrc` 備份起來，並產生一份它自己的設定檔，等一下步驟 3 要改的就是這個檔案。

## 步驟 3：下載 Zsh 主題

[Powerlevel10k](https://github.com/romkatv/powerlevel10k) 是一個 Zsh 的主題，也是這篇文章要套用的主角。它會把當前目錄、Git 狀態、指令執行時間這些資訊直接畫在提示字元 (prompt) 上，一眼就能看完。

首先，將 Powerlevel10k 這個 GitHub Repo 下載 (clone) 到 Oh My Zsh 的自訂主題資料夾 (`/Users/user_name/.oh-my-zsh/custom/themes/`) 中。這個路徑是 Oh My Zsh 約定好會去掃描的位置，放對地方它才找得到：

```bash
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k
```

接著，修改 `~/.zshrc` 設定檔，替 Zsh 加入自訂主題：

```bash
nano ~/.zshrc
```

找到 `ZSH_THEME` 這一行並將其改為我們剛剛下載的主題 (powerlevel10k)：

```bash
...

# ZSH_THEME="robbyrussell"
ZSH_THEME="powerlevel10k/powerlevel10k"

...
```

改完存檔離開 (在 nano 中是 `control + O` 存檔、`control + X` 離開)。

## 步驟 4：下載適用 Powerlevel10k 的字型

如果要讓 Powerlevel10k 主題完全發揮其實力，也就是所有的樣式都可以顯示出來的話，我們必須使用特定的字型：Nerd Fonts。

原因在於 Powerlevel10k 的 prompt 用了大量圖示 (資料夾、Git 分支、箭頭等等)，這些符號並不在一般字型的字元集裡。字型沒換的話，畫面上就會出現一堆問號或空白方框，看起來反而比美化前更慘。

首先，下載 [MesloLGS NF Regular.ttf](https://github.com/romkatv/dotfiles-public/raw/master/.local/share/fonts/NerdFonts/MesloLGS%20NF%20Regular.ttf) 字型。接著，我們要將這個字型載入到 macOS 系統中。只需要開啟 Font Book (你可以直接用 Spotlight 找到)，點選「+」將剛剛下載的字型載入：

![macOS Font Book 視窗，左上角的「+」按鈕用來加入新字型。](img-002)
*透過 Font Book 將字型載入到 macOS 系統中*

將我們下載的字型載入到 macOS 系統後，我們就可以在 Terminal 中選擇使用該字型。首先打開 Terminal，並在最上方的工具列點擊「Terminal」後打開「Preferences」(macOS Ventura 之後這個選項改名為「Settings」)。點選「Profiles」後，在「Font」的區塊中更換字型：

![Terminal 偏好設定的 Profiles 分頁，Font 區塊中可以更換字型。](img-003)
*在 Terminal 中更換字型*

這裡選的是 MesloLGS NF。完成字體的更換之後，請將 Terminal 關閉，讓下一步從一個乾淨的 session 開始。

## 步驟 5：在 Terminal 中設定 Powerlevel10k

來到了最後一個步驟～在最後一步中，我們重新開啟 Terminal，Powerlevel10k 會用「回答問題」的方式，一題一題問你想要什麼樣的 prompt，再依照你的答案產生設定。

![Powerlevel10k 的互動式設定精靈，在 Terminal 中詢問字型圖示是否正常顯示。](img-004)
*Powerlevel10k 設定*

前幾題會先請你確認畫面上的圖示 (菱形、鎖頭等等) 有沒有正常顯示，這其實就是在驗收步驟 4 的字型有沒有裝對；後面則是問你喜歡哪種樣式，照著自己的喜好選就好。

如果你在開啟 Terminal 之後，卻沒有出現上述的「問題」，可以輸入以下指令手動叫出設定精靈：

```bash
p10k configure
```

一旦回答完所有問題之後，Terminal 的主題也已經完成設定。如果之後看膩了或不喜歡，隨時都可以再輸入這一個指令重新設定一次。

## 補充：VS Code 中的 Terminal 設定

如果你像我一樣是使用 Visual Studio Code (VS Code) 作為日常開發的編輯器，那麼還需要在 VS Code 中多做一個設定。原因跟步驟 4 一樣：VS Code 內建的 Terminal 有自己的字型設定，不會跟著系統 Terminal 走，沒改的話一樣會看到那堆問號。

首先，開啟 VS Code 後，在最上方的工具列點擊「Code」，並點擊「Preferences」後再點擊「Settings」(較新版本的 VS Code 已簡化成 Code > Settings)。在搜尋欄位輸入「terminal.integrated.fontFamily」並在框框中寫上「MesloLGS NF」：

![VS Code 設定畫面，搜尋 terminal.integrated.fontFamily 並填入 MesloLGS NF。](img-005)
*VS Code 字型設定*

存檔後重開 VS Code 的 Terminal，樣式就會跟系統的 Terminal 一致了。

## 結論

這篇文章用 5 個步驟走完 macOS Terminal 的美化流程：確認 shell 是 Zsh、安裝 Oh My Zsh 這個設定管理框架、clone 並套用 Powerlevel10k 主題、裝上 Nerd Fonts 字型，最後跑一次互動式設定。其中最容易踩雷的是字型那一步，畫面出現問號或方框幾乎都是字型沒裝好或沒選到，回頭檢查步驟 4 通常就能解決。

有了漂亮又資訊完整的 Terminal，開發的心情也會跟著美麗起來！

### 參考資料

- [Mac OS Sierra support #185](https://github.com/powerline/fonts/issues/185)
- [iTerm2 + zsh + oh-my-zsh The Most Power Full Terminal on macOS (2021 Guide + macOS Big Sur)](https://chamikakasun.medium.com/iterm2-zsh-oh-my-zsh-the-most-power-full-terminal-on-macos-2021-guide-macos-big-sur-5bb498976dc9)
- [oh my zsh showing weird character '?' on terminal](https://stackoverflow.com/questions/42271657/oh-my-zsh-showing-weird-character-on-terminal)
- [Icons not showing #310](https://github.com/romkatv/powerlevel10k/issues/310)
- [Install and validate fonts in Font Book on Mac](https://support.apple.com/guide/font-book/install-and-validate-fonts-fntbk1000/mac#:~:text=Install%20fonts,in%20the%20dialog%20that%20appears)

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "下載 Oh My Zsh",
    "why_used": "確認 Oh My Zsh 安裝成功的畫面，讓讀者知道跑完指令後應該看到什麼。",
    "agent_match_hint": "一張 Terminal 截圖，顯示 Oh My Zsh 安裝完成後的 ASCII art 字樣與提示訊息。"
  },
  {
    "id": "img-002",
    "references_manifest_caption": "透過 Font Book 將字型載入到 macOS 系統中",
    "why_used": "示範如何用 Font Book 把下載好的 Nerd Font 載入系統，這是步驟 4 的操作重點。",
    "agent_match_hint": "一張 macOS Font Book 應用程式的視窗截圖，可看到字型清單與左上角的「+」按鈕。"
  },
  {
    "id": "img-003",
    "references_manifest_caption": "在 Terminal 中更換字型",
    "why_used": "指出 Terminal 偏好設定裡更換字型的位置，避免讀者在 Profiles/Font 分頁中找不到。",
    "agent_match_hint": "一張 Terminal 偏好設定視窗截圖，停留在 Profiles 分頁，畫面中有 Font 區塊與字型選擇按鈕。"
  },
  {
    "id": "img-004",
    "references_manifest_caption": "Powerlevel10k 設定",
    "why_used": "呈現 Powerlevel10k 互動式設定精靈的樣子，說明最後一步的「回答問題」是什麼情況。",
    "agent_match_hint": "一張 Terminal 截圖，顯示 Powerlevel10k 設定精靈的提問畫面，含圖示是否正常顯示的確認題與選項。"
  },
  {
    "id": "img-005",
    "references_manifest_caption": "VS Code 字型設定",
    "why_used": "示範在 VS Code 設定中填入 terminal.integrated.fontFamily 的位置，補足內建 Terminal 的字型設定。",
    "agent_match_hint": "一張 VS Code Settings 畫面截圖，搜尋欄位為 terminal.integrated.fontFamily，下方輸入框填著 MesloLGS NF。"
  }
]
```
