---
name: theme-scan
description: >
  題材掃描：在互動 session 裡掃「watch 清單以外」的新公司、新題材與新需求錨，只到 Topic Digest 與提名，
  不追源、不抽取、不入圖、不對 pq2 編號給 go／drop。weekly 排程已於 2026-09-24（Phase 1 Step 1.9）退役，
  掃描改由使用者發起；心跳段 3 與 session 開頭每天提醒「距上次掃題材 N 天」。
  觸發詞：掃題材、找新題材、有什麼新趨勢、theme scan。
---

# Theme Scan Skill（題材掃描）

## 定位一句話

**只發現、不處置。** 它回答「watch 清單外有沒有值得研究的新東西」，把答案變成 lead、onboard 提名或新錨提案；
研究、追源、抽取、入圖、thesis 判斷全部不在這裡——那些各自有入口與人工 gate（AGENTS 四個 gate）。

它取代的是 `crons/weekly_scan_prompt.md`（逐字封存於 `docs/archive/2026-09-24-weekly-scan-prompt-v1.2.md`）。
weekly 原本另外三段——完整健康審查、thesis 唯讀提醒、投組風險快照——已由 Windows daily 接手（⑭、心跳段 2、④），
這裡**不重做**。

## 什麼時候跑

- 使用者說「掃題材」「找新題材」「有什麼新趨勢」「theme scan」。
- 心跳段 3 或 session 開頭說「距上次掃題材 N 天」且已達門檻（`config/daily_routine.json` 的 `theme_scan.nudge_after_days`）
  ——那是提醒，**不是授權**：要不要掃由使用者決定。
- 不進任何無人值守排程（`/last30days` 與 WebSearch 都只限互動）。

## Stage 0 — 前置（只讀）

1. 讀 `config/themes.txt`（主題、核心公司、關鍵字、替代／反證關鍵字）。
2. 讀上一份報告：`docs/reports/theme_scan_<日期>.md`，沒有就讀最新的 `docs/reports/weekly_scan_<日期>.md`
   （舊名，同一條管道）。`python -c "from engine_b.theme_scan import last_scan; print(last_scan())"` 會告訴你是哪一份、幾天前。
3. 跑 `python -m engine_b.cli onboard-candidates`：lead 逐字點名、但 registry 沒有的標的（確定性提名，先於語意探索）。
   心跳段 2 的「今天第一次被點名、registry 沒有的名字」是同一份資料依首次點名時間排的切片。

## Stage 1 — 探索

- 每個 active theme 搜尋過去 7 天（或自上一份報告以來）的新事件，**每個主題 2–3 次 WebSearch 為度**。
- 可選：`/last30days <主題>` 看社群與市場的近 30 天（**只限互動**）。
- X／EDGAR／MFN／MOPS 已由 daily harvest 覆蓋——這裡只找 daily watch 外的聚類與新題材，**不按單則貼文建項**。
- 對材料套 signal-triage 五要素（`skills/signal-triage/SKILL.md`）；同一事件聚成一個 topic。
- 每個 topic：摘要、來源連結、影響、為何值得研究、建議 `research`／`onboard`／`FYI`。
- **到此停止**：不跑 source-trace、不抽 claim、不 prepare／apply Research Action。

## Stage 2 — 落地（只有兩種寫入）

1. **值得研究的 topic → 註冊 lead**（進 pq1，不占 pq2 編號）：

   ```
   python -m engine_b.cli register --source theme_scan:<主題> --url <url> --title "<事情>"
   ```

   來源標籤 `theme_scan:<主題>` 跟著 lead 走到 outcome（帳號計分表按來源計分）。舊 lead 的 `weekly:<主題>` 是同一條管道的歷史名稱，不改。
2. **新需求錨 → decompose 提案**（鑄 `manual` 型 pq2；**選題是使用者**，`go` 只授權跑 system-decompose）：
   本次 topic 裡出現一台實體系統，其需求錨不在 `config/sector_anchors.json` 各組、也不在圖裡時：

   ```
   python -m engine_b.cli decompose-propose --system "<實體>" --anchor <tech:x> --why "<為什麼是新錨>" --lead <id>
   ```

   命令自己會擋深度題、drop 過的題與 open>2。

`onboard` 候選只提名、不 onboard：onboarding 改 registry（authority），走 `skills/company-onboard`，由使用者點名。

## Stage 3 — 報告

存 `docs/reports/theme_scan_<YYYY-MM-DD>.md`（心跳與 hook 靠這個檔名算「距上次掃題材 N 天」）：

```text
# 題材掃描 — <日期>
## 30 秒 brief
## Topic Digest（每個 topic：摘要／來源／影響／為何值得研究／research｜onboard｜FYI）
## 建議 onboard 候選（ticker＋被點名次數＋樣本標題；只提名）
## 新錨提案（已鑄的 decompose 提案編號；只列，不評）
## 本次註冊的 lead（lead_id＋來源標籤）
```

報告留檔，但**不是 current-state truth**（AGENTS）：它是當次的 point-in-time 發現，不是 leads／todo／lifecycle 的狀態源。

## 鐵律

- 全程繁體中文；不確定就標不確定；找不到值得說的事也照樣出一份稀疏報告（「沒發生」與「沒看」不得同形）。
- **只發現、不處置**：掃描報告**不得**對 pq2 編號輸出 `go`／`drop` 建議——處置建議只由讀得到 pool 現值的
  daily／互動 session 給出（AGENTS）。疑似 stale 的編號至多列成「待互動 session 驗證」並附 ground-truth 查證命令。
- 不追源、不抽取、不入圖、不改 lifecycle 結論、不替使用者填真實持倉、不動 registry。
- 不自己推論「來源已停止產出」：要說之前先讀 pool JSON 的 `source_cleared`／`waiting_on`／`deferred_at` 實值。
