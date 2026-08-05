---
title: 簡單 5 步驟，美化你的 Terminal (macOS)
date: '2022-04-02T05:25:30'
lastmod: '2022-07-12T14:02:18'
slug: beautify-terminal-on-macos
draft: false
categories:
- 其他
tags:
- macOS
- Tool
description: '前言 身為一個 Programmer/Developer，Terminal 是我們經常會使用到的工具。然而，醜醜又原始的 Terminal
  實在會破壞打 Code 的好心情。在網路上有許多相關的教學文章，看起來容易但實際上操作起來不僅麻煩還會遇到許多作者沒遇到的坑。 因此在本篇文章中，我將用簡單 5
  步驟，教你打造一個美麗的 Terminal，並盡可能地說明每一個步驟的意義！ AD 步驟 1 : 下載 Z Shell Z shell 簡稱 Zsh 是一個基於
  Bourne again shell (Bash) 所打造的 Shell，也是 macOS 上預設的 shell。我們可以在 Terminal 中，查看 Terminal
  所使用預設的 shell。 echo $SHELL 如果是使用 Zsh (/bin/zsh) 那麼可以直接跳過這步，如果不是的話，可以透過 Homebrew 下載
  Zsh： brew install zsh 步驟 2 : 下載 Oh […]'
aliases:
- /others/beautify-terminal-on-macos/
original_url: http://54.150.87.240/others/beautify-terminal-on-macos/
wp_id: 771
images:
- images/Powerlevel10k-setting.jpg
- images/VS-Code-Font-Setting.jpg
- images/change-font-in-terminal.jpg
- images/feature-image.jpg
- images/font-book.jpg
- images/oh-my-zsh.jpg
---

![feature image](images/feature-image.jpg)

打造一個美麗的 Terminal

## 前言

身為一個 Programmer/Developer，Terminal 是我們經常會使用到的工具。然而，醜醜又原始的 Terminal 實在會破壞打 Code 的好心情。在網路上有許多相關的教學文章，看起來容易但實際上操作起來不僅麻煩還會遇到許多作者沒遇到的坑。

因此在本篇文章中，我將用簡單 5 步驟，教你打造一個美麗的 Terminal，並盡可能地說明每一個步驟的意義！

AD

## 步驟 1 : 下載 Z Shell

Z shell 簡稱 Zsh 是一個基於 Bourne again shell (Bash) 所打造的 Shell，也是 macOS 上預設的 shell。我們可以在 Terminal 中，查看 Terminal 所使用預設的 shell。

```
echo $SHELL
```

如果是使用 Zsh (/bin/zsh) 那麼可以直接跳過這步，如果不是的話，可以透過 Homebrew 下載 Zsh：

```
brew install zsh
```

## 步驟 2 : 下載 Oh My Zsh

[Oh My Zsh](https://ohmyz.sh/) 是一個用來管理 Zsh 設定的開源框架，我們將會透過 Oh My Zsh 替我們的 Zsh 加上主題，讓我們的 Terminal 看起來很漂亮。輸入以下指令，下載 Oh My Zsh：

```
sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

如果出現以下畫面，就代表下載成功啦！

![oh my zsh](images/oh-my-zsh.jpg)

下載 Oh My Zsh

## 步驟 3 : 下載 Zsh 主題

[Powerlevel10k](https://github.com/romkatv/powerlevel10k) 是一個 Zsh 的主題，我們將下載這個主題，並透過 Oh My Zsh 將這個主題套用到 Zsh 上。首先，將 [Powerlevel10k](https://github.com/romkatv/powerlevel10k) (GitHub Repo) 下載 (clone) 到 Oh My Zsh 的自訂主題資料夾 (/Users/user\_name/.oh-my-zsh/custom/themes/) 中。

```
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k
```

接著，修改 ~/.zshrc 設定檔，替 Zsh 加入自訂主題：

```
nano ~/.zshrc
```

找到 ZSH\_THEME 並將其改為我們剛剛下載的主題 (powerlevel10k)：

```
...

# ZSH_THEME="robbyrussell"
ZSH_THEME="powerlevel10k/powerlevel10k"

...
```

AD

## 步驟 4 : 下載適用 Powerlevel10k 的字型

如果要讓 Powerlevel10k 主題完全發揮其實力，也就是所有的樣式都可以顯示出來的話，我們必須使用特定的字型 —— Nerd Fonts。

首先，下載 [MesloLGS NF Regular.ttf](https://github.com/romkatv/dotfiles-public/raw/master/.local/share/fonts/NerdFonts/MesloLGS%20NF%20Regular.ttf) 字型。接著，我們要將這個字型載入到 macOS 系統中。只需要開啟 Font Book (你可以直接用 Spotlight 找到)，點選「+」將剛剛下載的字型載入：

![font book](images/font-book.jpg)

透過 Font Book 將字型載入到 macOS 系統中

將我們下載的字型載入到 macOS 系統後，我們就可以在 Terminal 中選擇使用該字型。首先打開 Terminal，並在最上方的工具列點擊「Terminal」後打開「Preferences」。點選「Profiles」後，在「Font」的區塊中更換字型。

![change font in terminal](images/change-font-in-terminal.jpg)

在 Terminal 中更換字型

完成字體的更換之後，請將 Termial 關閉！

## 步驟 5 : 在 Terminal 中設定 Powerlevel10k

來到了最後一個步驟～在最後一步中，我們重新開啟 Terminal，並透過「回答問題」的方式，讓 Powerlevel10k 了解我們想要如何美化我們的 Zsh。

![Powerlevel10k setting](images/Powerlevel10k-setting.jpg)

Powerlevel10k 設定

如果你在開啟 Terminal 之後，卻沒有出現上述的「問題」，可以輸入以下指令：

```
p10k configure
```

當然，一旦回答完所有問題之後，Terminal 的主題也已經完成設定，如果你不喜歡，隨時都可以再輸入這一個指令重新設定。

## 補充：VS Code 中的 Terminal 設定

如果你像我一樣是使用 Visual Studio Code (VS Code) 作為日常開發的編輯器，那麼我們還需要在 VS Code 中進行一些設定，才能讓 VS Code 裡的 Terminal 呈現正確的樣式。

首先，開啟 VS Code 後，在最上方的工具列點擊「Code」，並點擊「Preferences」後再點擊「Settings」。在搜尋欄位輸入 「terminal.integrated.fontFamily」並在框框中寫上「MesloLGS NF」。

![VS Code Font Setting](images/VS-Code-Font-Setting.jpg)

VS Code 字型設定

AD

## 結語

在本篇文章中，我們學習如何透過 Oh My Zsh 與 Powerlevel10k 來美化我們的 Terminal (Zsh)。有了漂亮的 Terminal，也能讓我們開發的心情更加美麗！

## 參考

- [Mac OS Sierra support #185](https://github.com/powerline/fonts/issues/185)
- [iTerm2 + zsh + oh-my-zsh The Most Power Full Terminal on macOS (2021 Guide + macOS Big Sur)](https://chamikakasun.medium.com/iterm2-zsh-oh-my-zsh-the-most-power-full-terminal-on-macos-2021-guide-macos-big-sur-5bb498976dc9)
- [oh my zsh showing weird character ‘?’ on terminal](https://stackoverflow.com/questions/42271657/oh-my-zsh-showing-weird-character-on-terminal)
- [Icons not showing #310](https://github.com/romkatv/powerlevel10k/issues/310)
- [Install and validate fonts in Font Book on Mac](https://support.apple.com/guide/font-book/install-and-validate-fonts-fntbk1000/mac#:~:text=Install%20fonts,in%20the%20dialog%20that%20appears)
