---
title: 'Deep Learning 第一站 : Neural Network 名詞介紹'
date: '2022-02-09T15:16:01'
lastmod: '2022-02-21T03:40:27'
slug: understand-neural-network-for-deep-learning
draft: false
categories:
- 深度學習核心觀念
tags:
- Deep Learning
- Feedforward Neural Network
- Recurrent Neural Network
description: 前言 在前一篇文章中，我們介紹了一種「更接近」現代神經網路所使用的神經元 —— Sigmoid Neuron，說明了其與 Perceptron
  的相似與不同之處，也提到了 Sigmoid 函數最重要的特性「平滑」，此特性使得人工神經網路 (Artificial Neural Network) 能夠慢慢的調整其參數，慢慢的輸出愈來愈正確的結果。
  在本篇文章中，我們不再聚焦於單一個人工神經元 (Artificial Neuron)，例如 Perceptron 或是 Sigmoid Neuron，而是以整個
  Neural Network 的角度，理解 Neural Network 中的組成元素與專有名詞，是進入深度學習領域 (Deep Learning) 的第一站。
  Neural Network 的基本組成元素   一個基本的 Neural Networt 通常會長得像上方這張圖一樣。在介紹 Perceptron 一文中，我們提過依照慣例通常會將
  Neural Network 最左邊的輸入也用圈圈包起來，讓它看起來像是一個 Neuron，稱為 Input Neuron；最左邊的這些 Neuron 自然而然形成一個
  Layer，稱為 Input Layer。Neural Network 最右邊的 Layer 則稱為 Output […]
aliases:
- /deep-learning-core-concept/understand-neural-network-for-deep-learning/
original_url: http://54.150.87.240/deep-learning-core-concept/understand-neural-network-for-deep-learning/
wp_id: 466
images:
- images/feature-image-9.jpg
- images/neural-network-1.jpg
- images/neural-network.jpg
---

![](images/feature-image-9.jpg)

source: Pixabay

## 前言

在[前一篇文章](http://54.150.87.240/deep-learning-core-concept/understand-sigmoid-neuron/)中，我們介紹了一種「更接近」現代神經網路所使用的神經元 —— Sigmoid Neuron，說明了其與 Perceptron 的相似與不同之處，也提到了 Sigmoid 函數最重要的特性「平滑」，此特性使得人工神經網路 (Artificial Neural Network) 能夠慢慢的調整其參數，慢慢的輸出愈來愈正確的結果。

在本篇文章中，我們不再聚焦於單一個人工神經元 (Artificial Neuron)，例如 [Perceptron](http://54.150.87.240/deep-learning-core-concept/what-is-perceptron/) 或是 [Sigmoid Neuron](http://54.150.87.240/deep-learning-core-concept/understand-sigmoid-neuron/)，而是以整個 Neural Network 的角度，理解 Neural Network 中的組成元素與專有名詞，是進入深度學習領域 (Deep Learning) 的第一站。

## Neural Network 的基本組成元素

![neural network](images/neural-network.jpg)

3 個 Layer 的 Neural Network [source: Neural Networks and Deep Learning]

一個基本的 Neural Networt 通常會長得像上方這張圖一樣。在[介紹 Perceptron 一文](http://54.150.87.240/deep-learning-core-concept/what-is-perceptron/)中，我們提過依照慣例通常會將 Neural Network 最左邊的輸入也用圈圈包起來，讓它看起來像是一個 Neuron，稱為 Input Neuron；最左邊的這些 Neuron 自然而然形成一個 Layer，稱為 **Input Layer**。Neural Network 最右邊的 Layer 則稱為 **Output Layer**，裡頭的 Neuron 則稱為 Output Neuron。介於 Input Layer 與 Output Layer 之間的，則稱為 **Hidden Layer**。Hidden Layer 聽起來似乎是一個很神秘的東西，然而其實 Hidden Layer 就只是用來表示這個 Layer 不是 Input 也不是 Output 而已。

在上圖的 Neural Network 中，Input Layer、Output Layer 與 Hidden Layer 皆各為一個。在現代大部分的 Neural Network 中，通常會包含很多層 Hidden Layer，進而形成一個很「深」的 Neural Network，因此現代的 Neural Network 也稱為 **Deep Neural Network**。Deep Neural Network 透過 Learning Algorithm 進行學習，調整其中的參數，慢慢輸出正確的結果，這一個過程則稱為 **Deep Learning**。

![neural network](images/neural-network-1.jpg)

Neural Network 的基本組成：Input Layer、Output Layer 與 Hidden Layer [source: Neural Networks and Deep Learning]

上圖是另外一個 Neural Network，擁有兩個 Hidden Layer。需要特別注意的是，這些由很多個 Layer 所組成的 Neural Network 又經常被稱為 Multilayer Perceptron，簡稱為 MLP。然而，在[介紹 Sigmoid Neuron 一文](http://54.150.87.240/deep-learning-core-concept/understand-sigmoid-neuron/)中，我們了解到現代神經網路中的 Neuron 通常不是使用 Perceptron。為了避免觀念混淆，在[此系列的文章](http://54.150.87.240/topics/deep-learning-core-concept/)中，我們簡單稱其為 Neural Network 而不使用 Multilayer Perceptron。

## Input 與 Output Layer 的設計

Neural Network 的 Input Layer 與 Output Layer 的設計通常比較直觀，能夠根據問題的種類進行設計。舉例來說，假如我們希望建立一個 Neural Network 進行「手寫數字圖像」的分類，輸入一張圖片到 Neural Network 中，並輸出這張圖片的是屬於哪一個數字。

一個直觀又常見的設計方法，就是將圖片中每一個像素 (Pixel) 的數值都當作一個 Input Neuron。以一張 28 × 28 的灰階圖片來說，灰階 (Grayscale) 圖片表示圖片僅由一個通道 (Channel) 組成，並不是像一般看到的彩色圖片由 3 個 Channel (Red、Blue、Green) 所組成。因此，圖片總共有 28 × 28 = 784 個數值，每一個數值都表示圖片中其中一個位置的資訊。將每一個資訊都當作一個 Input Neuron，則會建立一個包含了 784 個 Neuron 的 Input Layer。

因為 Neural Network 要輸出這張圖片屬於哪一個數字 (0 到 9)，因此我們可以將每一個數字都用一個 Output Neuron 表示，如果 Neural Network 認為這一張圖像屬於「8」，則代表「8」這一個數字的 Otuput Neuron 的數值應該要大於 0.5。如此一來，就會建立一個包含 10 個 Neuron 的 Output Layer。

至於 Hidden Layer 的設計，則相對較為複雜。Hidden Layer 的設計經常包含許多作者的想法與技術，甚至也帶有一點「藝術」的氣息，因此無法單純透過幾個規則就總結 Hidden Layer 的設計。在此[系列的文章](http://54.150.87.240/topics/deep-learning-core-concept/)中，我們也會介紹到一些常見的設計方法。

## Feedforward Neural Network

到目前為止，我們所討論的 Neural Network 不管是使用 Perceptron 或是 Sigmoid Neuron 都有一個共同的特性 —— 前一個 Layer 的輸出會作為下一個 Layer 的輸入。這種 Neural Network 也稱為 Feedforward Neural Network，也就是資訊都是不斷的往前傳遞。換個角度來看，假設 Feedforward Neural Network 中有一個 Sigmoid Neuron (A)，因為 Feedforward Neural Network 中沒有包含「Feedback Loop」，因此資訊都是不停的向前傳遞，Sigmoid Neuron (A) 此刻的輸出會只作為下一個 Layer 的輸入。

有另外一種 Neural Network 中包含了「Feedback Loop」，使得資訊也能夠向後 (往 Input Layer 的方向) 傳遞，這種 Neural Network 稱為 Recurrent Neural Network。同樣的，我們假設 Recurrent Neural Network 中有一個 Sigmoid Neuron (A)，因為 Recurrent Neural Network 中包含有「Feedback Loop」，使得資訊能夠向後 (往 Input Layer 的方向)  傳遞，導致 Sigmoid Neuron (A) 此刻的輸出會往後傳遞。在下一刻時，會連同新的輸入作為 Sigmoid Neuron (A) 的輸入。因此，Sigmoid Neuron (A) 下一刻的輸出就會受到上一刻的輸出所影響。

## 結語

在本篇文章中，我們從單一個 Artificial Neuron 來到了一整個 Neural Network。介紹了 Neural Network 的基本組成與 Input、Output Layer 的設計理念。最後，我們也了解到 Feedforward Neural Network 與 Recurrent Neural Network 的最大差別。

在下一篇文章中，我們仍然會聚焦在 Neural Network 的角度，說明一個完整的 [Neural Network 是如何解決「手寫數字圖像分類」的問題](http://54.150.87.240/deep-learning-core-concept/neural-network-classify-handwritten-digit-image/)。

## 參考

- [Neural networks and deep learning](http://neuralnetworksanddeeplearning.com/chap1.html)
- [Multilayer perceptron – Wikipedia](https://en.wikipedia.org/wiki/Multilayer_perceptron)
- [Feed Forward Neural Network Definition | DeepAI](https://deepai.org/machine-learning-glossary-and-terms/feed-forward-neural-network)
- [Feedforward neural network – Wikipedia](https://en.wikipedia.org/wiki/Feedforward_neural_network)
