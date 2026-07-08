# Agent Gap Analysis — 現在的 Engine vs 理想 Agent

> 記錄 2026-07-08 SIVE onboarding 過程中，Claude 做了哪些 engine 做不到的事，
> 以及「理想投資研究 agent」和「現在 engine」之間的差距。

---

## 現在 Engine 能做什麼（已驗證）

```
你給文件 → extract.py → Neo4j 圖 → graph_context.py → Lane Memo
              (結構化)      (儲存)      (查詢)           (LLM 合成)
```

- PDF/txt → nodes/edges/claims（被動處理）
- Schema validate → Neo4j MERGE（可靠）
- 財務數據 ETL（yfinance → SQLite）
- 5 項財務核驗清單 gate
- Lane Memo 生成（給 context 就能跑）
- L9 前置條件 gate
- company_id 過濾查詢（2 跳子圖）

**關鍵限制：engine 是管道，不是 agent。你給它什麼，它才能處理什麼。**

---

## Gap 清單 — Claude 做了但 Engine 做不到

### G1 — 公司識別（Ticker Disambiguation）
**發生：** 你說 `$SIVE`，我知道是 `Sivers Semiconductors AB`，知道是瑞典公司，知道做 InP 雷射，知道跟 CPO 有關。
**Engine：** 只能 lookup ticker，不理解公司是誰、做什麼、在哪個市場。
**需要什麼：** 公司 profile 資料庫 or LLM company lookup layer（但有幻覺風險）。

### G2 — 文件頁面選擇（Relevance Filtering）
**發生：** 86 頁年報，我看 TOC 後判斷第 4-7、10-13、14-18 頁是 CPO 相關，跳過財務報表和法律條文。
**Engine：** 沒有「選頁」能力。全丟 → 噴 token；全略 → 資訊不足。
**需要什麼：** 文件結構解析 + 主題相關性過濾（可以用 embedding 或 LLM TOC 解析）。

### G3 — 輸入錯誤修正（Input Correction）
**發生：** 我下 `--source-type annual_report`，extract.py 報錯，我自動改成 `filing`。
**Engine：** 直接 fail，沒有 fallback 或引導。
**需要什麼：** Source-type 自動對應表，或 LLM 選 source-type。

### G4 — 財務異常解讀（Financial Anomaly Interpretation）
**發生：** 看到 EV/Rev 44.9x + 毛利 -2.4% + 分析師目標 -75%，我知道這代表「市場定價的是遠期期權，不是現在的基本面」。
**Engine：** 數字存進 SQLite，checklist 只看「有沒有值」，不懂含義。
**需要什麼：** 財務異常偵測 layer（如：EV/Rev > 20x + 負毛利 → 觸發警告 + 解讀模板）。

### G5 — 來源偏誤識別（Source Bias Detection）
**發生：** 我注意到「Sivers 年報說 Sivers 是關鍵供應商」= L8 自我報告偏誤，主動警告。
**Engine：** extract.py 照單全收，`origin_entity` 欄位存在，但 validate.py 不檢查「所有 source 都來自同一家公司」這個條件。
**需要什麼：** 在 validate.py 加 L8 檢查：若全部 source_ids 的 origin_entity 相同 → 警告。

### G6 — 文件搜尋（Document Discovery）
**發生：** 我知道去哪找獨立來源（O-Net 6963.HK、POET IR、OFC 論文、Coherent 法說會）。
**Engine：** 完全不知道去哪找文件，只有 `fetchers/edgar.py`（只限美股）。
**需要什麼：** Engine B（SNS 爬蟲）部分功能 + 一個「對這個 thesis，你還缺哪些來源」的 advisor layer。

### G7 — 對話式查詢（Conversational Query）
**發生：** 你問「SIVE 在 CPO 的獨佔性」，我能引導你問更具體的問題（是哪個層？對哪個客戶？）。
**Engine：** 只有兩個模式：全圖 Lane Memo 或公司 2 跳子圖。沒有「針對問題的 Cypher 查詢 + 直接回答」。
**需要什麼：** Text2Cypher layer（自然語言 → Cypher → 直接回答），或 conversational graph QA。

### G8 — 節點重要性判斷（Node Significance）
**發生：** Extract 出 O-Net、POET、LIGHTIUM 三個節點，我知道 O-Net 是 OEM 合作方（重要），LIGHTIUM 是初創（存疑），POET 有公開 IR（可查獨立來源）。
**Engine：** 三個節點在圖裡地位完全相同，沒有「這個節點值得深挖」的機制。
**需要什麼：** 節點重要性評分（可從 edge 數量、evidence_tier、公司規模組合）。

### G9 — ROI 判斷（Build vs. Skip）
**發生：** 你問「要不要做非美股 fetcher」，我評估了成本/效益後說不。
**Engine：** 完全沒有這個判斷能力。
**需要什麼：** 這個 gap 不該由 engine 填——這是 product/roadmap 判斷，永遠需要人。

### G10 — 跨文件實體解析（Cross-Document Entity Resolution）
**發生：** Sivers 年報裡出現「Broadcom」，Coherent 法說會裡也出現「Broadcom」。我知道這是同一個 Broadcom，也知道 Broadcom 是 CPO switch 的主要買家。
**Engine：** `co:broadcom` 已存在，MERGE 會自動合併——這個 gap 部分已解決。但如果 extract 出「Broadcom Inc.」和「AVGO」兩個不同 id，圖就分裂了。
**需要什麼：** Entity alias resolution（`aliases[]` 欄位已設計，但 extract prompt 沒有強制使用）。

---

## 理想 Agent 的形狀（目標架構）

```
你：「評估 SIVE 在 CPO 的瓶頸性」
         ↓
[理解層] 識別公司 + 拆解問題（瓶頸 = sole_source? substitutability? ramp?）
         ↓
[資料層] 圖裡有沒有 SIVE？ → 有：查詢 / 沒有：onboarding
         ↓
[來源層] 現有來源夠不夠？origin_entity 多樣性？L8 偏誤？
         ↓
[搜尋層] 不夠 → 主動找：客戶法說會、第三方報告、競品資料
         ↓
[分析層] Cypher 查詢 + 財務數據 + 來源可信度 → 合成回答
         ↓
你：得到直接回答 + 信心度 + 哪些事情還不確定
```

**現在系統完成了中間的「資料層」，其他層幾乎都是 Claude 在臨時扮演。**

---

## Gap 優先度與難度

| Gap | 重要性 | 工程難度 | 推薦時機 |
|---|---|---|---|
| G5 L8 偏誤 validate | 高 | 低 | 下次 ce-work |
| G2 文件頁面過濾 | 高 | 中 | Milestone C（批次化前） |
| G7 對話式查詢 (Text2Cypher) | 高 | 高 | Milestone D |
| G6 文件搜尋 advisor | 高 | 高 | Engine B 啟動時 |
| G4 財務異常解讀 | 中 | 中 | Engine C v2 |
| G1 公司識別 | 中 | 中 | 批次 onboarding 前 |
| G10 Entity alias resolution | 中 | 中 | 多文件衝突出現時 |
| G3 輸入錯誤修正 | 低 | 低 | 隨時可加 |
| G8 節點重要性評分 | 低 | 中 | 圖夠大後才有意義 |
| G9 ROI 判斷 | — | — | 永遠是人工 |

---

## 結論

**現在的系統最接近「結構化文件處理管道」，離「投資研究 agent」還差三層：**

1. **理解層**（G1 G7 G8）— 懂問題、懂公司、懂節點重要性
2. **主動層**（G6）— 自己去找資料，不等人餵
3. **判斷層**（G4 G5）— 知道數字背後的含義，知道來源的偏誤

這三層都需要 LLM 在管道裡扮演更主動的角色，不只是「處理你給的輸入」。
G7（Text2Cypher）是其中最有槓桿的單點——解鎖後你就能直接問圖問題，不用每次都出整篇 Lane Memo。
