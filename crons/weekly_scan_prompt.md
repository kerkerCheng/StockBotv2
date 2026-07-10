# Weekly Theme Scan — Cron Prompt

> 這份 prompt 由 CronCreate 定期觸發（每周一次）。
> 觸發後，Claude 執行以下流程並將結果寫入 Claude memory，通知用戶。

## 觸發指令

```
/last30days <theme_keywords>
```

按 `config/themes.txt` 的主題清單逐一掃描。

## 執行流程

### Step 1 — 讀取主題清單

讀 `config/themes.txt`，提取所有 active 主題的關鍵字清單。

### Step 2 — 執行 /last30days 掃描

對每個主題執行 `/last30days` skill，搜尋過去 30 天內：
- 法說會提及核心公司
- 供應鏈/設計窗口/產能變化消息
- 競爭者/替代技術動向
- 可能觸發 disproof_condition 的訊號
- **下游客戶 M&A**：搜 `<known_customers> acquired OR merger` — M&A 往往揭露供應鏈重要性
- **新命名客戶**：搜 `<company> partnership OR design win OR customer` — 找圖中尚未收錄的客戶關係
- 比對搜尋結果與圖中現有節點：有新公司名出現 → 標記為「待 onboard 候選」

### Step 3 — 分級輸出

**30 秒 Brief（若發現高訊號事件）：**
格式：
```
⚡ 本周高訊號事件

1. [公司] — [一句話描述] — 重要性: [高/中]
2. ...

一鍵動作：回覆 "研究 [公司]" 開始 onboarding，或 "忽略" 跳過
```
若本周無高訊號事件，跳過此格式。

**週報摘要（每周必出）：**
```
## 本周 AI 主題掃描 — <日期>

### CPO / 矽光子
- [若有新發展]
- [若無重大變化，一句話說明]

### SIVE / InP 雷射
- [若有新發展]
- [若無重大變化，一句話說明]

### Thesis 健康狀況
- [列出 active thesis 的 disproof_condition 是否有觸發跡象]

### 值得追蹤的新訊號
- [0-3 條，若無則說明]
```

### Step 4 — 寫入 memory

將結果寫入：
`C:/Users/Cheng/.claude/projects/C--Users-Cheng-code-StockBotv2/memory/weekly_scan_<YYYY-MM-DD>.md`

格式：
```markdown
---
name: weekly-scan-<YYYY-MM-DD>
description: 每周 AI 主題掃描 — <日期>
metadata:
  type: project
---

<週報內容>
```

同時更新 `memory/MEMORY.md` 最後一行（若已有上週條目，替換之）：
```
- [Weekly Scan <日期>](weekly_scan_<YYYY-MM-DD>.md) — <一句最重要的發現>
```

### Step 5 — 推送通知

若發現高訊號事件，用 PushNotification 通知用戶（若可用）。
否則，結果在用戶下次開啟 Claude Code 時會從 memory 自動載入。

---

## 輸出 tone

- 繁體中文
- 每條有投資意涵的訊號附「為何重要」一句話
- 不確定的訊號標 "？"，不要假裝確定
- 若某主題本周沒有新發展，直接說「本周無重大動向」，不要湊字數
