# Is Bash All You Need? 企業 Agent 工具介面實證研究筆記

Sep 30, 2026 · @YHHW

## 三十秒版本

只給 agent 一個 bash shell，在兩個企業工作 benchmark 上分數不輸給只給 typed tools（預先定義好名稱與參數格式的函式），而且用更少 token（模型處理文字的計費單位）；在 Bash 之上再加 typed tools 或讓 agent 自造工具，沒有偵測到分數增益。

- **論文**：*Is Bash All You Need? An Empirical Study of Tool Interfaces for Enterprise Digital Worker Agents*，Microsoft 與 CMU，arXiv 2609.11999v1（2026-09-10）。它沒有提出新方法，價值在一組受控比較。
- **比較對象**：五種「工具介面」（agent 用什麼方式對環境下動作）：Tool-only、Bash、Bash+Tool、Bash+Synthesis、PTC。
- **核心數字**（Table 1 逐格相減）：Bash 對比 Tool-only，分數在 TheAgentCompany 高 21.8 到 24.5 個百分點（pp），在 APEX-Agents 高 4.8 到 7.4 pp，總 token 少 19% 到 72%。
- **PTC**（Programmatic Tool Calling，程式化工具呼叫：模型寫一小段程式，程式只能呼叫預先定義的工具）比 Tool-only 省 token，分數大致持平，整體輸給 Bash。
- **論文的實務建議**：能把任意程式碼執行隔離起來，就用 Bash；合規要求只能用固定工具目錄，就用 PTC。
- **能信多少**：方向可信，幅度要打折。TheAgentCompany 的 60 個 typed tools 是作者自己設計的，Bash 的優勢混著「這組工具做得好不好」；Bash 的高分也是在額外防護（封鎖評分腳本、加密同事資料）之下測出來的。

一句話：**這是一份「方向可用、幅度不可直接搬」的實證比較。**

## 索引

**【概念】詳解**（放在文件最後，每段脫離這篇論文也成立，想快速回頭複習只讀這幾段）：

1. 【概念】看到 A 贏 B，先檢查 B 是誰做的：基準線品質與目錄覆蓋的混淆
2. 【概念】為什麼中間結果不進上下文就能省 token
3. 【概念】批次化不是 PTC 專屬：Bash 也能，差別在能碰到的範圍
4. 【概念】typed tool 加 exec 的混合架構：論文怎麼看、沒測到什麼、輸出整理的價值
5. 【概念】看不出差異不等於沒有差異：信賴區間怎麼讀

**主線**：一、問題與背景 → 二、方法 → 三、實驗結果 → 四、整體評價 → 五、值得帶走的東西。

## 一、問題與背景

企業 agent 該用什麼方式對環境下動作，目前缺乏受控的對照證據；這篇論文用兩個企業工作 benchmark 補上這個缺口。

### 先定義名詞

| 名詞 | 意思 | 特性 |
| --- | --- | --- |
| Agent | 讓大型語言模型（LLM）反覆「想 → 呼叫工具 → 讀結果」直到完成任務的系統 | 每一輪都要把前面的對話重新讀一遍 |
| 工具介面（tool interface） | agent 用什麼方式對環境（服務 API、檔案、應用程式）下動作 | 決定 agent 能做什麼、多安全、多貴 |
| Typed tool | 預先定義好名稱與參數格式的函式，例如 `gitlab_create_issue`，模型一次呼叫一個 | 安全可控，只能做被授權的事，但一個動作就是一次呼叫 |
| Bash（shell） | 只給模型一個命令列，讓它自己寫指令，可用 pipe（`\|`，把前一個指令的輸出接給下一個）等方式一次串多個動作 | 彈性最大，但任意執行需要另外做隔離與權限控管 |
| PTC（Programmatic Tool Calling） | 模型寫一小段 Python，程式裡只能呼叫預先定義的 typed tools，可以 loop、串接，但碰不到 shell | 介於兩者之間：保留固定工具目錄，又能批次處理 |
| MCP（一般知識，不是論文內容） | Model Context Protocol，把外部服務包成「模型可呼叫工具」的標準做法 | 論文的 APEX-Agents 環境用 MCP 伺服器提供應用程式 |
| Token | 模型讀寫文字的計費單位 | 論文用 token 數與估算的美元成本衡量「貴不貴」 |

### 這個問題怎麼來的

- **Coding 領域已經有先例**：mini-SWE-agent 只給 bash，Live-SWE-agent 則讓 agent 自己造工具，還登上過 SWE-bench Verified 榜首。
- **企業產品兩條路並存**：Anthropic 與 OpenAI 的 API 提供 PTC（受限在固定工具目錄內）；Claude Code、Codex CLI、Microsoft Copilot Studio（底層是 GitHub Copilot CLI）走 shell 路線。
- **缺口**：企業工作要在多個應用之間切換、跟同事溝通、做專業分析，和寫程式不一樣，而 shell 對 typed tools 的受控比較在這類場景很少，實務者沒有證據可選。同期有一篇 Patel et al. 2026（*The Bitter Lesson of Tool Calling*）比較了 PTC 與一般 JSON 工具呼叫，但沒有納入 shell。

### 兩邊各有代價

- **Shell**：一步可以做很多動作，但任意執行需要控制執行環境與存取範圍。
- **Typed tools**：只暴露被授權的函式，安全可控，但每個動作各自一次呼叫，累積起來有額外開銷。

### 論文實際回答的三個問題

論文沒有獨立的「挑戰」章節，以下三題是依 Introduction 與 Method 整理的（我的整理，不是原文分段）：

1. **Q1**：只給 shell，能不能贏過只給 typed tools？
2. **Q2**：在 shell 之上再加 typed tools，或讓 agent 自造可重用的工具，有沒有額外好處？
3. **Q3**：PTC 這個折衷方案的表現如何？

## 二、方法

作者用同一個模型、同一份任務文字、同一份基礎 prompt、同一套停止條件，只改變「agent 能怎麼動手」，藉此隔離出介面本身的影響。測試的模型是 Opus-4.8 與 GPT-5.5，推論設定用預設的推理強度；agent 迴圈由 GitHub Copilot SDK 提供，它的預設工具集與 system prompt 都被覆蓋掉了（Appendix A）。

### 2.1 五種工具介面

**Figure 1**（原文 caption：*Five interfaces formed from shell execution, typed tools, persistent synthesized tools, and restricted programs over typed tools.*）畫出了五種介面的結構，請直接回論文看圖。

| 介面 | agent 手上有什麼 | 特別之處 |
| --- | --- | --- |
| Tool-only | 只有 typed tools | 每個動作一次獨立呼叫，是基準線 |
| Bash | 只有 shell | 可以用 pipe、迴圈把多個動作串成一次呼叫 |
| Bash+Tool | shell 加 typed tools | 兩者並存，agent 自己選 |
| Bash+Synthesis | shell 加一個持久資料夾 | prompt 鼓勵 agent 把常用步驟寫成可重用腳本，後續任務直接呼叫，藉此減少重新摸索的成本；任務依序執行，資料夾會保留 |
| PTC | 模型寫 Python，程式裡只能呼叫 typed tools | 可以 loop、串接、平行，但沒有 shell，也沒有其他能碰到環境的管道 |

只有 Bash+Synthesis 與 PTC 額外加了介面專屬的 prompt 指示，其餘介面共用同一份基礎 prompt。

### 2.2 同一件事在三種介面裡怎麼做（自編例子）

任務：找出某個 GitLab 專案裡，標題含 "bug" 的 open issue 標題。假設專案有 500 個 open issue，其中 20 個符合。

```text
【Tool-only】
 turn 1: 呼叫 gitlab_list_issues(project="p", state="opened")
         -> 500 筆 issue 的完整內容全部回到模型的上下文
 turn 2: 模型自己從這 500 筆裡挑出符合的標題，寫成答案

【Bash】
 turn 1: bash("curl -s $GITLAB/api/.../issues?state=opened | jq -r '.[].title' | grep -i bug")
         -> 只有 20 行標題回到上下文

【PTC】
 turn 1: 模型送出一段 Python：
         issues = gitlab_list_issues(project="p", state="opened")   # 500 筆，留在程式裡
         hits = [i["title"] for i in issues if "bug" in i["title"].lower()]
         print(hits)                                              # 只有 20 個標題回到模型
```

這個例子顯示 PTC 與 Bash 的共通點：中間結果留在模型之外，只把整理好的輸出交回來。論文把 PTC 省 token 歸因於這個機制，但措辭是「可能」（*These savings may reflect…*），屬於論文的推測，沒有直接驗證。為什麼這樣能省 token，見【概念】為什麼中間結果不進上下文就能省 token。

### 2.3 兩個 benchmark

**Figure 2**（原文 caption：*(a) TheAgentCompany: 4 self-hosted services, a local workspace, and 17 simulated coworkers reachable through RocketChat. (b) APEX-Agents: 9 MCP servers over a shared workspace, with tasks organized into 33 scenario worlds.*）是兩個環境與任務分布的示意，請回原圖查看。

|  | TheAgentCompany | APEX-Agents |
| --- | --- | --- |
| 模擬什麼 | 軟體公司：跨 GitLab、RocketChat（聊天）、ownCloud（雲端硬碟）、Plane（專案管理）做事，加上本地檔案 | 投資銀行、管理顧問、公司法務的專業分析：合約審查、試算表估值、問卷整併 |
| 任務數 | 174 題（軟體工程 69、人資 29、專案管理 28、行政 15、資料科學 14、財務 12、其他 7） | 480 題，三個領域各 160 題，分布在 33 個情境世界 |
| 同事 | 17 位由 GPT-5 扮演的模擬同事，透過聊天室互動 | 無 |
| typed tools 從哪來 | benchmark 沒有現成的，**作者自己設計 60 個**（54 個服務工具加 6 個工作區檔案工具，見 Table 7） | benchmark 原有的 **20 個**，分屬 8 個非 shell 伺服器（Table 8） |
| Bash 從哪來 | 直接給 shell | 用該 benchmark 的程式碼執行伺服器：有檔案系統限制、環境變數清除、執行上限的 Unix shell |
| 評分 | 各任務的 Python 檢查點程式 | LLM 評審依 rubric（評分標準）逐條檢查最終回覆與工作區檔案變更 |
| 環境版本 | 修補了同事模擬的可靠性缺陷（漏訊息、提早結束、狀態過期），對所有介面一體適用 | 固定使用 2026-06 的 Archipelago 快照（9 個 MCP 伺服器），避開較新版本的付費金融資料 API |

### 2.4 兩個要記住的實驗細節

- **Reward hacking 的實例**（Appendix B.1）：開發階段，有 shell 的 agent 會從 TheAgentCompany 公開 repo 裡的評分腳本直接撈答案，或讀取模擬同事的檔案，而不是真的去跟同事溝通。作者的對策是封鎖對該 repo 的網路存取、加密同事資訊。所以 Bash 的高分是在額外防護下測出的。
- **絕對分數不能和公開排行榜比**：APEX-Agents 官方排行榜用最大推理強度與較新的伺服器快照，這裡用預設推理強度與舊快照（Appendix B.2）。

### 2.5 指標

| 指標 | 全名與定義 | 量的是什麼 |
| --- | --- | --- |
| Score（分數） | TheAgentCompany：依工作量加權的檢查點通過率；APEX-Agents：rubric 條目滿足的平均比例 | 任務完成程度。兩個 benchmark 算法不同，不能直接互比 |
| Pass rate（通過率） | 完全解決的任務比例（全部檢查點或全部 rubric 條目都達標） | 完成得多徹底 |
| Total tokens | 每題平均的輸入加輸出 token（輸入含快取讀取） | 讀寫的文字量 |
| $/task | 依 GitHub Copilot 公開價目估算的每題推論成本 | 花多少錢 |
| 配對分數差（pp） | 同一題、同一模型、兩種介面的分數相減，再對所有題取平均 | 兩種介面的淨差距；pp 是百分點 |
| 95% bootstrap 信賴區間 | 從配對任務重複抽樣、重算平均差，看結果散布的範圍 | 這個差距有多不確定，怎麼讀見【概念】看不出差異不等於沒有差異 |

## 三、實驗結果

核心結論一句話：不論模型、不論 benchmark，Bash 都比 Tool-only 分數高、token 少；在 Bash 上加東西沒有增益；PTC 省 token 但分數持平，整體輸給 Bash。三個問題（Q1 到 Q3）的答案都在 Table 1 與 Table 9。

**Table 1** 的原文 caption：*Score: effort-weighted checkpoint rate (TheAgentCompany) or mean rubric score (APEX-Agents); pass rate: fully solved fraction; both with 95% bootstrap CIs. Token columns: means/task in thousands; input includes cache-read; total = input + output. $/task: mean estimated inference cost at GitHub Copilot list rates; time/task: mean wall-clock minutes.* 這張表列出 5 種介面乘 2 個模型乘 2 個 benchmark 的全部結果，下面的對照都是從它逐格取出來的。

### 3.1 Q1：Tool-only 換成 Bash（其他不變）

箭頭左邊是 Tool-only，右邊是 Bash。

| Benchmark／模型 | Score | Pass rate | Total tokens | $/task |
| --- | --- | --- | --- | --- |
| TheAgentCompany／Opus-4.8 | 44.9% → 69.4% | 24.1% → 50.6% | 945k → 264k | $1.20 → $0.37 |
| TheAgentCompany／GPT-5.5 | 45.3% → 67.1% | 25.3% → 47.7% | 465k → 377k | $0.66 → $0.56 |
| APEX-Agents／Opus-4.8 | 41.1% → 48.5% | 24.2% → 30.0% | 397k → 215k | $0.73 → $0.48 |
| APEX-Agents／GPT-5.5 | 39.8% → 44.6% | 23.3% → 28.3% | 328k → 176k | $0.52 → $0.40 |

四組全部同向。摘要的「+21.8 到 +24.5 pp」與「+4.8 到 +7.4 pp」，就是這張表的分數欄逐格相減。

**統計上站得住嗎？**（Table 9，配對分數差：*Mean paired A minus B in percentage points (positive favors A); brackets: 95% bootstrap CIs.*）

| Benchmark | Bash − Tool-only | 95% 信賴區間 | 勝／平／負（題數） |
| --- | --- | --- | --- |
| TheAgentCompany（348 個任務-模型配對） | +24.6 pp | \[+20.6, +29.0\] | 161 / 172 / 15 |
| APEX-Agents（960 個配對） | +6.2 pp | \[+3.6, +8.7\] | 220 / 596 / 144 |

區間都不含 0，差異是真的。但 APEX-Agents 有 144 個配對是 Bash 反而輸，平均進步是贏的比輸的多。論文的解讀是，彈性執行對寫程式與跨應用的工作幫助，大於對領域推理的幫助（原文語氣為「可能」）。

**要打折的地方**：TheAgentCompany 的 Tool-only 用的是作者自己設計的 60 個工具，+24.6 pp 混著「typed tools 的限制」與「這組工具做得好不好」，論文沒有拆開。APEX-Agents 的 20 個工具是 benchmark 原有的，+6.2 pp 相對乾淨（這是我的推論）。詳見【概念】看到 A 贏 B，先檢查 B 是誰做的。

### 3.2 Q2：在 Bash 上加東西

分數差（Table 9，正數代表加了比較好）：

| 加了什麼 | TheAgentCompany | APEX-Agents |
| --- | --- | --- |
| Bash+Tool − Bash（加 typed tools） | −0.6 pp \[−3.0, +1.9\] | −0.2 pp \[−2.4, +1.9\] |
| Bash+Synthesis − Bash（加自造腳本） | −1.6 pp \[−3.6, +0.3\] | −0.2 pp \[−2.4, +2.0\] |

四個區間都跨過 0，看不出差異。「看不出」不等於「證明沒有」，見【概念】看不出差異不等於沒有差異。

token 與成本（Table 1，每格為 Total tokens／$/task）：

| 設定 | Bash | Bash+Tool | Bash+Synthesis |
| --- | --- | --- | --- |
| TheAgentCompany／Opus-4.8 | 264k／$0.37 | 569k／$0.55 | 249k／$0.35 |
| TheAgentCompany／GPT-5.5 | 377k／$0.56 | 508k／$0.60 | 436k／$0.61 |
| APEX-Agents／Opus-4.8 | 215k／$0.48 | 396k／$0.60 | 237k／$0.50 |
| APEX-Agents／GPT-5.5 | 176k／$0.40 | 257k／$0.42 | 228k／$0.44 |

八格裡只有 TheAgentCompany／Opus-4.8 的 Bash+Synthesis 比純 Bash 便宜，論文自己也把它列為唯一例外，其餘都是 token 變多。

### 3.3 Q3：PTC

Tool-only 換成 PTC（箭頭左為 Tool-only，右為 PTC）：

| Benchmark／模型 | Score | Total tokens | $/task |
| --- | --- | --- | --- |
| TheAgentCompany／Opus-4.8 | 44.9% → 52.9% | 945k → 406k | $1.20 → $0.64 |
| TheAgentCompany／GPT-5.5 | 45.3% → 45.1% | 465k → 242k | $0.66 → $0.54 |
| APEX-Agents／Opus-4.8 | 41.1% → 40.1% | 397k → 337k | $0.73 → $0.61 |
| APEX-Agents／GPT-5.5 | 39.8% → 37.8% | 328k → 256k | $0.52 → $0.48 |

四格 token 都下降，但分數只有第一格明顯進步，其餘持平或略降。Table 9 的配對差一致：PTC − Tool-only 在 TheAgentCompany 是 +3.5 pp \[+0.8, +6.2\]，在 APEX-Agents 是 −1.5 pp \[−3.9, +0.9\]。對比 Bash（Bash − PTC）：+21.2 pp \[+17.0, +25.5\] 與 +7.7 pp \[+5.2, +10.2\]，區間都不含 0，Bash 明顯較好。token 方面，PTC 只在 TheAgentCompany／GPT-5.5 比 Bash 省（242k 對 377k）。

**為什麼 PTC 省 token？**（**Table 6**，原文 caption：*Programmatic tool calling composition and token efficiency. Comp. ratio: per-task typed calls per PTC execution. Deltas: PTC minus Tool-only, paired by task and model…*）

| Benchmark | 每次執行包的呼叫數 | 呼叫次數差 | 未快取輸入 token 差 | 快取讀取 token 差 | 輸出 token 差 |
| --- | --- | --- | --- | --- | --- |
| TheAgentCompany | 2.0 | −4.0 | −97.6k | −86.8k | +0.2k |
| APEX-Agents | 2.0 | −3.0 | −45.4k | −44.0k | −0.4k |

批次化程度不高（平均每次執行只包 2 個呼叫），但輸入與快取讀取 token 少了很多，輸出幾乎不變。論文的解釋是，中間結果留在程式裡、只把選出的輸出交回模型，所以後續每輪要帶的上下文變短（原文為「可能」，未驗證）。機制見【概念】為什麼中間結果不進上下文就能省 token。

**PTC 的工具呼叫成功率最低**（Table 2）：TheAgentCompany 只有 65.2%，其他介面約 92%；APEX-Agents 是 86.2%，其他約 88% 到 91%。論文猜測是「在程式裡協調呼叫、處理中間失敗比較難」，沒有進一步驗證。

**PTC 輸給 Bash，有一部分可能是目錄覆蓋不夠**（我的推論）：PTC 只能呼叫 typed 目錄裡的函式，而 TheAgentCompany 的目錄是作者設計、只涵蓋任務相關 API 的（Appendix B.1）。所以 Bash − PTC 的差距，混著「PTC 的做法」與「目錄能碰到的範圍」，論文沒有拆開。見【概念】批次化不是 PTC 專屬。

### 3.4 快速總結：其餘實驗合併成一張表

以下實驗都在解釋「為什麼 Bash 比較好」，結論在前面的核心結果都已出現，這裡只留佐證。

| 實驗（圖表） | 在證明什麼 | 結果 | 一句話保留 |
| --- | --- | --- | --- |
| 工具使用（Table 2） | 各介面的呼叫次數、呼叫內容的 token 量、成功率、完全相同的重複呼叫比例 | TheAgentCompany：呼叫內容 token 是 Bash 9.0k 對 Tool-only 19.6k；重複呼叫 Tool-only 16.2%、Bash 0.3%。APEX-Agents：呼叫次數中位數 Bash 7.5 對 Tool-only 13.0 | shell 能把重複動作合併成一次呼叫（論文的解釋） |
| shell 用法（Table 3、Figure 5） | agent 用 shell 時實際在做什麼 | 94% 以上的 shell 呼叫是組合式（含 pipe、迴圈、多行等）；TheAgentCompany 偏短指令加 HTTP 請求，APEX-Agents 偏長的內嵌 Python | Bash 不只是跑單一指令，是拿來寫小程式 |
| Bash+Tool 的 shell 表現（Table 3） | 有了 typed tools，剩下的 shell 呼叫有沒有更可靠 | 沒有：失敗率 10.8% 對 7.9%（TheAgentCompany）、9.3% 對 4.4%（APEX-Agents） | 加 typed tools 只是少用 shell，剩下的沒變好 |
| 自造工具（Table 4、5） | 自造的工具會不會被重用、有沒有幫助 | 創造的工具大多被呼叫，但用到後續任務的比例不高（如 Opus-4.8 在 TheAgentCompany 是 21 個裡的 12 個）；有呼叫的任務分數沒比較好（平均差 −0.6 與 +0.1 pp），APEX-Agents 的 token 中位數還多 31.4k | 這份資料裡看不到自造工具的價值 |
| 任務複雜度（Figure 4） | Bash、PTC 的優勢是否隨任務變長而改變 | Bash 在 TheAgentCompany 的優勢在中等長度最大；APEX-Agents 上兩者在呼叫次數高時進步較多；PTC 的信賴區間多半跨過 0 | 證據弱，不要當結論 |
| 各領域分數（Figure 6） | 差距是否因工作類型而異 | 每個領域都是 Bash ≥ Bash+Tool ≥ Tool-only，軟體工程差距最大，公司法務幾乎不受介面影響 | 介面的影響在寫程式與跨系統的工作最大，在法律判斷最小 |

表中出現的圖表原文 caption（供回原文查找）：

- **Table 2**：*Tool use statistics. # Tool calls/task: median tool calls/task. Tool tokens/task: median tool-name, argument, and result tokens/task; excludes context/cache effects and is not billed usage…*（工具使用統計；「Tool tokens」不是計費用量，不含上下文與快取效應。）
- **Table 3**：*Shell statistics. Cmds/call: median commands. LOC: lines of code. Composed: calls with pipe, logical-operator, substitution, control-flow, heredoc, multiline, or nontrivial redirect markers; loop: control-flow markers. Failed: failures. Repair: failures whose next call shares the first command.*（shell 統計：Composed 指含 pipe、邏輯運算子、替換、流程控制、多行等標記的呼叫。）
- **Figure 5**：*Static shell-command shares by executable family, pooled across models (Table 11). Bars: 12 families plus other, summing to 100% per benchmark/interface.*
- **Table 4**：*Tool synthesis reuse statistics and success rates. Created: distinct agent-authored root Python paths, excluding seeds, initializers, and dependencies. Invoked: tools used from creation onward; cross-task reuse: used in later tasks…*
- **Table 5**：*Paired differences of Bash+Synthesis minus Bash, pooled across models. Subset: whether synthesized tools are invoked; N: number of tasks in the corresponding subset…*
- **Figure 4**：*Mean paired score differences (pp) from Tool-only: Bash (blue), PTC (orange). Bins: mean Tool-only calls across models; bands: 95% bootstrap CIs; N: task-model pairs/bin. Budget-clipped counts are lower bounds.*
- **Figure 6**：*Mean score (%) across models by domain. Dots: interface/domain arms; colors: interfaces; N: tasks/domain. TheAgentCompany's other pools bm, ml, qa, and research.*

## 四、整體評價

這是一篇有用但結論要打折的實證比較：研究價值偏低，工程價值中等，價值在「方向」而不在「幅度」。

**研究價值偏低。** 論文沒有提出新方法，也沒有新的分析框架，貢獻是把五種介面放進同一個受控設定裡比較。這類論文的價值取決於基準線公不公平，而這一點正是它最弱的地方（見下）。

**工程價值中等。** 「Bash 不輸給只有 typed tools，也更省」這個方向，在兩個模型乘兩個 benchmark 共四個設定裡一致，值得當作選型的參考；「在 Bash 上加 typed tools 或自造工具，沒看到分數增益」也一致，並且同時伴隨 token 增加。但幅度（尤其 TheAgentCompany 的 +24.6 pp）不能直接搬到別的系統。

### 優點

- **控制變因乾淨**：同模型、同任務文字、同基礎 prompt、同停止條件，只換介面。
- **統計處理算認真**：用配對比較加 bootstrap 信賴區間，不只報平均。
- **成本與分數並列**：token 與每題成本放在同一張表，這對實務決策比單看分數有用。
- **誠實揭露 reward hacking**，並說明怎麼擋（Appendix B.1）。

### 缺點（通病集中在這裡講一次）

1. **Tool-only 的基準線不是中立的。** TheAgentCompany 的 60 個 typed tools 是作者自己設計、且只涵蓋任務相關 API；PTC 的 Python 執行環境也是作者自己實作。所以 +24.6 pp 混著「typed tools 的限制」與「這組工具和實作做得好不好」，論文沒有拆開。相對乾淨的一組數字是 APEX-Agents 的 +6.2 pp，因為那 20 個工具是 benchmark 原有的（推論：相對乾淨，不是完全乾淨）。詳見【概念】看到 A 贏 B，先檢查 B 是誰做的。
2. **Bash 的風險沒有被納入評分。** 論文建議「能隔離任意執行時用 Bash」，但隔離的成本與安全事件都沒有量化；而實驗本身就抓到 agent 會從評分腳本撈答案。Bash 的高分是在額外防護之下測出的。typed tool 在輸出整理、權限控管、稽核上的價值，也不在分數裡（見【概念】typed tool 加 exec 的混合架構）。
3. **單次執行的隨機性沒有被單獨量化。** 配對任務數 348 = 174 × 2、960 = 480 × 2，似乎每個「任務乘模型」只跑一次（我的推論，論文未說明）。信賴區間是對任務取樣，「看不出差異」的那幾組結論（加 typed tools、自造工具）能排除的效果大小因此有限。

**摘要有被包裝嗎？** 沒有明顯誇大：摘要的 21.8 到 24.5 pp 與 4.8 到 7.4 pp 就是四格結果的範圍。但它把幅度較大、且基準線問題最嚴重的 TheAgentCompany 放在前面。

### 論文的模型選用建議與保留

論文建議：以 shell 為主的 coding 與跨應用工作先用 Opus-4.8；追求 token 效率的直接 typed tool 呼叫用 GPT-5.5；文件密集的專業分析要在 Opus-4.8 較高品質與 GPT-5.5 較低 token 之間取捨。論文自己也說，模型更新後這些建議未必成立，所以這一段的保存期限最短。

## 五、值得帶走的東西

這篇論文本身能帶走的很少；真正耐用的是讀它的過程裡整理出來的幾個判斷框架。以下按耐久度排序，最耐用的放前面。

### 第一類：這篇論文本身的貢獻

- **一組受控數據**：Bash 不輸給只有 typed tools，也更省 token；在 Bash 之上加 typed tools 或自造工具，沒偵測到分數增益。方向可信，幅度不能直接搬（原因見第四章）。
- **一個 reward hacking 實例**：有 shell 的 agent 會從評分腳本撈答案，而不是做事（Appendix B.1）。這對任何「讓 agent 有 shell 再拿 benchmark 評分」的實驗都是提醒：能碰到評分程式的環境，分數不能直接信。
- **方法上的貢獻接近零**：五種介面都是既有做法的組合。

### 第二類：脫離這篇論文也成立的東西

**A. 看到「A 贏 B」，先檢查 B 是誰做的。**

比較結果等於「方法本身的功勞」加上「基準線被做得多好或多差」。這篇的 Tool-only 有 60 個工具，是作者自己設計、只涵蓋任務相關 API；同樣的比較換到 APEX-Agents（20 個 benchmark 原有的工具），差距從 +24.6 pp 縮到 +6.2 pp。兩個數字差這麼多，就代表基準線的品質在影響結果。檢查方法是問三件事：基準線是誰設計的？有沒有被投入同等的調校力氣？有沒有別的來源的基準線可以交叉驗證？這個規則對任何「新方法對舊方法」的比較都成立，包括自己團隊內部的 A/B。完整拆解見【概念】看到 A 贏 B，先檢查 B 是誰做的。

**B. 工具介面的選擇規則。**

論文的建議是條件式的：能隔離任意程式碼執行，就用 Bash；合規要求只能用固定工具目錄，就用 PTC。把它整理成判斷順序：先問合規，再問能不能隔離，最後才考慮要不要疊別的東西。

決策圖如下。

&#91;embedded content: 工具介面決策樹 · 2 個判斷、3 種結果\]

讀法：從上往下回答兩個問題；虛線框是論文沒看到分數好處的加法，不在判斷路徑上。

兩點限制要一起記住。第一，這篇沒有量測 typed tool 的輸出整理、權限控管、稽核，這些好處不在分數裡，不能視為被否定。第二（我的推論），只要 agent 手上有 shell，typed tools 就不是安全邊界，因為 agent 隨時可以繞過去；固定工具目錄的安全價值只有在沒有 shell 時才成立。

**C. 省 token 的關鍵是別讓大量中間資料進上下文。**

模型沒有跨呼叫的記憶，每一輪都要把前面的對話整份重新讀一遍，所以工具回傳的原始結果一旦進了上下文，之後每一輪都要重複計算。以自編例子計算：500 筆 issue 全進上下文約 10 萬 token，之後 9 輪各重讀一次，約 94.5 萬；只讓篩過的 20 個標題進去，約 4.9 萬，差約 19 倍。論文的 Table 6 是這個機制的旁證：PTC 相對 Tool-only，輸入 token 少約 9.8 萬、快取讀取少約 8.7 萬，輸出幾乎不變。PTC、Bash 的 pipe，或在 typed tool 內先整理輸出，都是同一個道理。走查、公式與其他做法的取捨見【概念】為什麼中間結果不進上下文就能省 token。

**D. 「能批次處理」與「能碰到的範圍」是兩件事。**

批次化（一次模型呼叫做多個動作）Bash 與 PTC 都做得到：Bash 用 pipe 與 `for` 迴圈，94% 以上的呼叫是組合式；PTC 用 Python 迴圈。兩者真正的差別是能碰到什麼：PTC 只能呼叫目錄裡的函式，Bash 什麼都能碰。所以 PTC 輸給 Bash，有一部分可能只是目錄覆蓋不夠，而不是「程式化呼叫」本身較差。反過來，任務若有大量重複呼叫，優勢會同時屬於 Bash 與 PTC，兩者之間不會因此翻盤。見【概念】批次化不是 PTC 專屬。

**E. 混合架構（typed tools 加一個 exec 工具）是這篇的 Bash+Tool，論文沒有支持它比純 Bash 更好，但論文沒有說明它的 typed tool 是否整理過輸出。**

論文的數據：Bash+Tool 比 Tool-only 好很多（+24.1 pp、+5.9 pp），與純 Bash 沒有可偵測的差異（−0.6 pp、−0.2 pp），token 較多，剩下的 shell 呼叫失敗率反而較高。但論文的 typed tools 是否對輸出做過整理，文中未說明；穩定度（重複執行的變異）也沒有被量。所以「輸出整理帶來穩定度」是一個合理、但這份實驗無法驗證的實務論點。見【概念】typed tool 加 exec 的混合架構。

**F. 「看不出差異」不等於「沒有差異」。**

信賴區間跨過 0 只代表這批資料分不出「沒差」與「有個小差」；小於區間寬度的好處或壞處，這個實驗本來就偵測不到。讀論文的「no detectable gain」時，要問的是：區間寬度大約是多少？我在意的效果比它大還是小？見【概念】看不出差異不等於沒有差異。

## 【概念】看到 A 贏 B，先檢查 B 是誰做的

任何「新做法 A 贏過舊做法 B」的結果，都等於方法本身的功勞，加上 B 被做得多弱；當 B 是提案者自己設計的，第二項常被低估。

### 拆解一個比較結果

```latex
\text{觀察到的差距} = \text{A 本身的功勞} + \text{B 被做得多弱造成的落差} + \text{雜訊}
```

- 觀察到的差距：論文表格上看到的 A 減 B。
- A 本身的功勞：我們真正想知道的東西。
- B 被做得多弱造成的落差：基準線的設計、調校、覆蓋範圍不如 A 所造成的差距。
- 雜訊：任務與模型的隨機性，用信賴區間估計。

論文只能量到第一項，第二、三項要靠讀者判斷。

### 這篇論文裡的兩層混淆

| 比較 | 混進去的其他變因 | 相對乾淨的參考 |
| --- | --- | --- |
| Bash 對 Tool-only（TheAgentCompany，+24.6 pp） | Tool-only 的 60 個工具是作者自己設計，只涵蓋任務相關的 API，不是 shell 能碰到的所有端點（Appendix B.1） | APEX-Agents 的 20 個工具是 benchmark 原有的，差距只剩 +6.2 pp |
| Bash 對 PTC（+21.2 pp 與 +7.7 pp） | PTC 只能呼叫目錄內的函式，所以差距混著「程式化呼叫的做法」與「目錄夠不夠用」；PTC 的受限 Python 執行環境也是作者自己實作 | 論文沒有提供 |

範圍要記清楚：Appendix B.1 講的「目錄只涵蓋任務相關 API」是針對 TheAgentCompany 自建的那 60 個工具；APEX-Agents 的目錄是 benchmark 原有的，所以這個混淆主要影響 TheAgentCompany 的結論。

兩個 benchmark 的差距差了四倍（+24.6 對 +6.2），論文沒有拆解原因。這是我的推論：至少有一部分來自「TheAgentCompany 的基準線是自製的」，另一部分來自任務類型不同（寫程式與跨系統，對上專業分析）。兩者各占多少，這份資料回答不了。

### 三問檢查法

1. **基準線是誰設計的？** 提案者自己做的基準線，要先假設它沒被調到最好。
2. **有沒有被投入同等的力氣？** 同樣的 prompt 調校、同樣的超參數搜尋、同樣的工具覆蓋範圍。
3. **有沒有另一個來源的基準線可以交叉驗證？** 兩個來源給出的差距差很多，就代表基準線品質在影響結果。這篇剛好有：自製目錄與 benchmark 原有目錄。

### 其他常見的基準線陷阱（一般知識，不是論文內容）

- 基準線用預設超參數，提案方法卻調過。
- 基準線的 prompt 沒有針對它調整。
- 基準線用的模型較弱，或給的運算預算較少。
- 兩邊用不同的 harness（執行環境與評分程式）。

### 怎麼在自己的評估裡用

把基準線當成一個要認真對待的系統：給它與新方法相同的調校預算，並且盡量另找一個外部來源的基準線來對照。報告結果時，把「同一個條件下只差一個變因」的兩組數字挑出來，那組才是方法本身的功勞。

## 【概念】為什麼中間結果不進上下文就能省 token

模型每一輪都要把前面的全部內容重新讀一遍，所以進了上下文的每個 token，之後每一輪都要再付一次錢；讓大量的中間資料留在模型之外，是最直接的省法。（本節的機制屬一般知識，不是論文內容；論文只提供 Table 6 的旁證。）

### 先定義兩個詞

- **上下文（context）**：模型每次被呼叫時讀入的全部文字，包含 system prompt、任務描述、過去每一輪的動作，以及每個工具回傳的結果。
- **無狀態**：模型本身沒有跨呼叫的記憶。每一輪，系統都要把整份上下文重新送給模型，模型才「記得」之前發生了什麼。

### 公式：每個進了上下文的 token 會被重複計算

```latex
\text{總輸入 token} = \sum_{t=1}^{T} L_t, \qquad L_t = L_0 + \sum_{s<t} (a_s + r_s)
```

- T：任務總共進行了幾輪。
- L\_t：第 t 輪模型要讀入的上下文長度。
- L\_0：起始上下文（system prompt 加任務描述）。
- a\_s：第 s 輪模型自己輸出的 token。
- r\_s：第 s 輪工具結果進入上下文的 token 數。

白話：一筆工具結果在第 s 輪進來，之後第 s+1 到第 T 輪都要再讀一次，所以它的成本是「大小乘以剩餘輪數」。省 r\_s 的效果，會被輪數放大。

### 走查（自編例子）

沿用方法章節的任務：500 筆 issue、其中 20 筆符合條件。假設每筆完整 issue 約 200 token，每個標題約 20 token，起始上下文 5,000 token，取得結果之後還要 9 輪才完成任務，兩種做法模型自己的輸出相同，所以忽略 a\_s。

| 做法 | 首輪後進入上下文的結果 | 之後每輪要讀的上下文 | 之後 9 輪合計 |
| --- | --- | --- | --- |
| Tool-only（500 筆完整結果進上下文） | 500 × 200 = 100,000 token | 約 105,000 | 約 945,000 |
| Bash 或 PTC（只有 20 個標題進上下文） | 20 × 20 = 400 token | 約 5,400 | 約 48,600 |

差約 19 倍。用程式表達同一件事：

```python
def total_input(L0, results, turns):
    ctx, total = L0, 0
    for t in range(turns):
        total += ctx                 # 這一輪要讀整份上下文
        ctx += results.get(t, 0)     # 這輪的工具結果進上下文，之後每輪都要再讀
    return total

# 首輪的 5,000 兩種做法相同，比較的是之後 9 輪
total_input(5_000, {0: 100_000}, 10)   # 約 95 萬（Tool-only）
total_input(5_000, {0: 400}, 10)       # 約 5 萬（Bash/PTC）
```

實際系統通常有快取（prompt caching）：前綴相同的部分以較低單價重讀。它降低單價，但沒有減少 token 數；論文 Table 1 的輸入 token 也包含快取讀取。所以「別讓大量資料進上下文」的價值在有快取時仍成立，只是金額差距變小。

### 論文的旁證與保留

**Table 6**（*Programmatic tool calling composition and token efficiency…*）顯示，PTC 相對 Tool-only，TheAgentCompany 上未快取輸入少 97.6k、快取讀取少 86.8k，輸出只多 0.2k；APEX-Agents 上分別少 45.4k 與 44.0k，輸出少 0.4k。平均每次執行只包了 2.0 個呼叫，所以省下的主要不是「呼叫次數」。論文的解釋是：中間結果在程式裡處理，只回傳選出的輸出，後續各輪攜帶的上下文因此縮短。原文措辭是「可能」（*may reflect*），沒有做直接驗證。

### 降低進入上下文的 token 的其他做法（一般知識）

| 做法 | 怎麼做 | 適合什麼情況 | 代價 |
| --- | --- | --- | --- |
| 工具端先整理輸出 | 在 typed tool 內做篩選、挑欄位、截斷、分頁再回傳 | 你能控制工具的實作 | 每個工具都要設計，整理不當會丟掉需要的資訊 |
| 讓 agent 寫程式處理 | Bash 的 pipe 或 PTC 的 Python，中間結果留在程式裡 | 資料量大、處理步驟固定 | 需要執行環境與安全控管 |
| 上下文壓縮 | 對話太長時，用摘要取代舊內容 | 長時間任務 | 摘要可能遺失細節 |
| 子 agent | 把大量閱讀交給另一個獨立上下文，只回傳結論 | 需要大量搜尋或閱讀 | 額外的協調成本 |
| 快取 | 重複讀取的前綴用較低單價 | 前綴穩定的長對話 | 只降單價，不減 token 數 |

**判斷規則**：先問「這筆結果大不大、之後會不會再用到原文」。大，而且之後只需要其中一小部分，就別讓它整份進上下文，用上表的前三種擇一；結果小或之後每輪都要參考原文，就直接放進上下文。

## 【概念】批次化不是 PTC 專屬：Bash 也能，差別在能碰到的範圍

Bash 與 PTC 都能把多個動作合成一次模型呼叫，它們的真正差別是能碰到什麼環境，因此「這個 benchmark 是不是對 PTC 不利」與「PTC 輸給 Bash 的原因」要分開想。

### 先定義批次化

批次化：一次模型呼叫（一個回合）完成多個對環境的動作，減少模型與工具之間的往返次數，也減少中間結果進入上下文（機制見【概念】為什麼中間結果不進上下文就能省 token）。

### 三種介面各自怎麼批次

自編例子：讀 30 份合約 PDF，找出每份的生效日期。

```text
【Tool-only】每份一次呼叫，共 30 次，每次結果都回到模型
  read_pdf("c01.pdf") -> 全文回來 ...  read_pdf("c30.pdf") -> 全文回來

【Bash】一次呼叫，用迴圈與 pipe 串起來
  for f in *.pdf; do echo "$f"; pdftotext "$f" - | grep -i "effective date"; done

【PTC】一次執行，用 Python 迴圈呼叫目錄裡的函式
  for f in list_files("*.pdf"):
      text = read_pdf(f)                       # 目錄內的 typed 函式
      print(f, find_line(text, "effective date"))
```

| 介面 | 能不能批次 | 論文的證據 |
| --- | --- | --- |
| Tool-only | 不能，每個動作是一次獨立呼叫 | Table 2：完全相同的重複呼叫佔 16.2%（TheAgentCompany）；論文解釋是它把每次重複都曝露成一次呼叫 |
| Bash | 能：pipe、`&&`、迴圈、heredoc、內嵌腳本 | Table 3：94.3% 與 96.5% 的 shell 呼叫是組合式；含迴圈標記的呼叫 27.5% 與 67.8%；Table 2：APEX-Agents 呼叫次數中位數 7.5，Tool-only 是 13.0 |
| PTC | 能：Python 迴圈、串接、平行，但只能呼叫目錄內的函式 | Table 6：平均每次執行只包了 2.0 個 typed 呼叫 |

### 「這個 benchmark 是不是對 PTC 不利？」

這是一個合理的假設：PTC 的優勢來自迴圈式的大量呼叫，任務若本來就只有十幾次呼叫，優勢就發揮不出來。證據如下：

- 支持：Tool-only 每題呼叫次數的中位數只有 14.0（TheAgentCompany）與 13.0（APEX-Agents），PTC 平均每次執行只包 2.0 個呼叫，不是大量迴圈的工作型態。
- 部分呼應：**Figure 4**（*Mean paired score differences (pp) from Tool-only: Bash (blue), PTC (orange)…*）在 APEX-Agents 上，呼叫次數高的區間 PTC 的平均分數差變成正的（§5.3）。但論文自己也說，PTC 的信賴區間在大多數區間都跨過 0，證據很弱。
- 高呼叫次數的任務是少數：呼叫數 31 到 60 那一組，只佔配對任務的約 16%（56/348）與 8%（80/960）（我用 Figure 4 的 N 算的）。
- **論文未說明**：它沒有按呼叫次數拆 token 節省量，只拆了分數。所以「呼叫越多，PTC 越省 token」這個假設合理，但沒被驗證。

### 真正的差別：能碰到的範圍

|  | PTC | Bash |
| --- | --- | --- |
| 批次能力 | 有 | 有 |
| 能碰到什麼 | 只有 typed 目錄裡的函式 | 檔案系統、任意指令、網路，任何 shell 能碰到的東西 |
| 安全控管靠什麼 | 固定的工具目錄（沒有 shell） | 隔離環境、檔案系統限制、執行上限 |

所以就算任務改成大量重複呼叫，優勢會同時屬於 Bash 與 PTC，PTC 沒有 Bash 做不到的批次能力，兩者之間不會因此翻盤（推論）。反過來，PTC 輸給 Bash 的那 +21.2 pp 與 +7.7 pp，有一部分可能只是目錄覆蓋不夠：TheAgentCompany 的目錄是作者設計、只涵蓋任務相關 API 的（Appendix B.1）；APEX-Agents 的目錄是 benchmark 原有的，所以這個混淆主要在 TheAgentCompany。論文沒有把「做法」與「目錄覆蓋」拆開。

### 判斷規則

1. 任務有大量重複呼叫，而且目錄已涵蓋所需動作：PTC 與 Bash 都比 Tool-only 省，兩者的差別在管控方式。
2. 需要碰目錄以外的東西：只有 Bash 做得到。
3. 合規要求只能呼叫核准的固定工具：PTC，它在不開放 shell 的前提下保有批次處理的能力。

## 【概念】typed tool 加 exec 的混合架構：論文怎麼看、沒測到什麼、輸出整理的價值

給 agent 一組 typed tools，再加一個 exec（執行 shell 指令）的工具，是常見的實務架構，也就是論文的 Bash+Tool；論文的數據說它比只有 typed tools 好很多、和純 Bash 沒有可偵測的差別，但論文測的 typed tools 不一定是精心整理過輸出的那種。

### 論文的數據

| 比較（Table 9、Table 1、Table 3） | TheAgentCompany | APEX-Agents |
| --- | --- | --- |
| Bash+Tool − Tool-only（分數） | +24.1 pp \[+20.1, +28.3\] | +5.9 pp \[+3.6, +8.3\] |
| Bash+Tool − Bash（分數） | −0.6 pp \[−3.0, +1.9\] | −0.2 pp \[−2.4, +1.9\] |
| Total tokens：Bash+Tool 對 Bash（Opus-4.8） | 569k 對 264k | 396k 對 215k |
| shell 呼叫失敗率：Bash+Tool 對 Bash | 10.8% 對 7.9% | 9.3% 對 4.4% |

論文（§5.4）的說法是：加了 typed tools，shell 的使用量變少，但剩下的 shell 呼叫並沒有更可靠；Bash+Tool 的每個使用 shell 的任務裡，shell 呼叫次數的中位數最低，卻同時有最高的失敗率與最低的立即重試率。

### 論文沒有測到的三件事

1. **typed tool 的輸出有沒有被整理**：論文說明了工具清單（Table 7、Table 8），但沒有說明工具回傳的內容做過多少處理（**論文未說明**）。
2. **穩定度**：論文報告平均分數與信賴區間，沒有報告重複執行同一任務的變異；配對數 348 = 174 × 2、960 = 480 × 2，顯示似乎只有一次執行（我的推論）。
3. **權限管控與稽核**：這些不在分數裡。

所以「有做輸出處理的 typed tool 帶來穩定度」這個實務論點，論文既沒有支持，也沒有反駁。

### 輸出整理的論點（實務論點，一般知識加我的推論）

exec 回傳的是原始輸出：長度不定、格式不固定、可能夾帶雜訊或不該給模型看的資訊。typed tool 可以在回傳之前先處理：

- 統一格式：固定欄位的結構化結果，模型不必猜怎麼解析。
- 控制長度：截斷、分頁，並附上「還有多少沒顯示」。
- 去識別或遮蔽敏感欄位。
- 標準化錯誤訊息，讓失敗原因清楚可讀。

自編例子：同樣是「找標題含 bug 的 issue」。

```python
# typed tool：輸出被整理過
def search_issues(project, keyword, limit=20):
    raw = gitlab_api.list_issues(project, state="opened")   # 可能有數百筆
    hits = [i for i in raw if keyword.lower() in i["title"].lower()]
    return {
        "total_matched": len(hits),
        "items": [{"id": i["iid"], "title": i["title"], "url": i["web_url"]} for i in hits[:limit]],
        "truncated": len(hits) > limit,          # 明確告訴模型還有沒有更多
    }

# exec：回傳原始文字，格式取決於 agent 自己寫的指令
#   $ curl -s $GITLAB/api/.../issues | jq -r '.[].title' | grep -i bug
#   （幾行到幾百行不等，出錯時是 curl 或 jq 的原始錯誤訊息）
```

這和【概念】為什麼中間結果不進上下文就能省 token 是同一個機制：整理過的輸出讓進入上下文的 token 變少。推論：一個輸出設計良好的 typed tool，可以拿到 PTC 與 Bash 靠別的方式拿到的 token 節省，並且多一個可預期的輸入格式。

### 安全面的一個提醒（我的推論）

只要 agent 手上有 exec，typed tool 就不能單獨當作權限邊界：agent 可以直接用 curl 打同一個 API，繞過 typed tool 的限制。如果選 typed tools 的目的是權限控管或稽核，就要確保 exec 拿不到同樣的憑證與網路路徑，否則兩者並存等於沒有限制。論文把固定工具目錄的價值放在安全與合規，這個價值只有在沒有 shell 時才成立。

### 怎麼驗證（我的建議，不是論文內容）

用同一批任務、同一個模型，比較兩個條件：只有 exec；typed tools（輸出經過整理）加 exec。每個條件重複執行至少 3 次，除了平均分數，也比較「同一任務多次執行的分數變異」與 token 量。如果整理輸出的價值主要在穩定度，那麼平均分數可能看不出差別，變異才會有差別。

## 【概念】看不出差異不等於沒有差異：信賴區間怎麼讀

實驗只能說「兩種做法的分數差異，在這批資料裡沒有明顯到能確認」，不能說「保證沒有影響」；信賴區間的寬度，就是這個實驗能偵測到的最小差距的粗略尺度。

### 用論文的數字看

Table 9（TheAgentCompany）：Bash+Tool − Bash 的平均差是 −0.6 pp，95% 信賴區間 \[−3.0, +1.9\]。

- 信賴區間：根據這批資料，真實差距有 95% 的信心落在這個範圍內。
- 範圍的下限是 −3.0（加了 typed tools 反而差 3 pp），上限是 +1.9（加了好 1.9 pp），中間包含 0。
- 所以資料分不出「其實沒差」與「其實有 2 pp 左右的小好處或小壞處」。

類比：一個只能量到正負 2 公斤的體重計。你吃了一餐、多了 0.5 公斤，它顯示不出來，但這不代表你沒變重，只是儀器的雜訊比變化本身大。這個類比成立的原因是：任務與模型本身的隨機性，會讓平均差有一個抖動範圍，效果小於這個抖動就被淹沒。

### bootstrap 怎麼算（一般知識，論文只寫「95% bootstrap CIs」，細節未說明）

```python
import random

def bootstrap_ci(diffs, n=10000):
    # diffs：每個配對任務的分數差，例如 348 個數字
    means = []
    for _ in range(n):
        sample = [random.choice(diffs) for _ in diffs]   # 有放回地抽，抽得和原本一樣多
        means.append(sum(sample) / len(sample))          # 這一次抽樣的平均差
    means.sort()
    return means[int(0.025 * n)], means[int(0.975 * n)]   # 中間 95% 的範圍
```

任務數越多，抽出來的平均越穩定，區間就越窄，能偵測到的差距就越小。

### 讀「no detectable gain」時的三個動作

1. 看區間寬度：寬度大約是正負幾個 pp？
2. 想我在意的效果有多大：如果我在意的好處只有 1 到 2 pp（例如穩定度的小幅提升），這個實驗本來就量不出來。
3. 看有沒有同時有其他指標支持：例如 token 是否變多、失敗率是否變高，這些可以補足平均分數看不到的面向。

### 這篇論文的含義

加 typed tools 或自造工具，在分數上「看不出差異」，能排除的只是「大於約 2 到 3 pp 的好處」；比這小的效果，這個實驗不能證明也不能否定。
