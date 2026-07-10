# Thesis Lifecycle Monitor — Cron Prompt

> 這份 prompt 由 CronCreate 每季觸發（約每 90 天）。
> 作用：確認每條 active thesis 的 disproof_condition 是否有觸發跡象；強制 review 機制（L7）。

## 觸發指令

每季跑一次（建議：每年 1/1, 4/1, 7/1, 10/1）

## 執行流程

### Step 1 — 讀取所有 active thesis

掃描 `thesis/` 目錄，找所有 Lane Memo（*.md），檢查 header 中的 `output_type` 和 thesis 狀態。

### Step 2 — 逐一核查 disproof_condition

對每條 active thesis，執行：

1. 讀出 `disproof_condition`（Lane Memo 裡的可證偽條件）
2. 執行 `/last30days` 搜尋過去 90 天內有無觸發跡象
3. 同時執行 `python engine_c/checklist.py <TICKER>` 看財務指標有無惡化

### Step 3 — 分級狀態更新

每條 thesis 根據以下規則分級：

| 情況 | 狀態 | 行動 |
|------|------|------|
| disproof_condition 無觸發跡象，財務健康 | `active` | 記錄「已核查 <日期>，正常」 |
| 有一條 leading indicator 朝 disproof 方向移動 | `watch` | 提高監控頻率，下次 check 提前 30 天 |
| disproof_condition 已明確觸發 | `review_required` | **立刻通知用戶**，48h 內必須人工決策 |
| 用戶已確認 thesis 失效 | `retired` | 記錄推翻原因，建議出場 |

### Step 4 — 生成季度核查報告

格式：
```
## Thesis 季度核查 — <日期>

### CPO 供應鏈 thesis
**狀態：** active ✓
**Disproof Condition：** [原文]
**核查結果：** [無觸發跡象 / 有跡象，詳見下方]
**下次核查：** <日期>

---

### SIVE / InP 雷射 thesis
**狀態：** watch ⚠
**Disproof Condition：** [原文]
**觸發跡象：** [具體描述]
**建議動作：** [在下次法說會前，注意 XXX 指標]
**下次核查：** <日期>（提前至 30 天後）

---

### 摘要
- Active: <N> 條
- Watch: <N> 條（需要加強監控）
- Review Required: <N> 條（⛔ 需要用戶立刻決策）
```

### Step 5 — 寫入 memory + 通知

將報告寫入：
`C:/Users/Cheng/.claude/projects/C--Users-Cheng-code-StockBotv2/memory/thesis_monitor_<YYYY-MM-DD>.md`

若有 `review_required` 的 thesis → 用 PushNotification 立刻通知（若可用）。
若全部 `active` → 靜默寫入，用戶下次開啟時自動從 memory 載入。

---

## L7 鐵律提醒（每次都要遵守）

**Thesis 生命週期定義（CLAUDE.md L7）：**
- `active`：thesis 成立，定期核查 disproof 條件
- `watch`：有 leading indicator 朝 disproof 方向移動，升高監控頻率
- `review_required`：disproof 條件已觸發，**強制 review，不能繼續持有不檢查**
- `retired`：確認 thesis 失效，出場並記錄推翻原因
- `revised`：修正後的 thesis 成立，重新進入 `active`，更新 disproof 條件

**一條 thesis 有 `disproof_condition` 但沒有「核查頻率」和「觸發後 48h 動作」= 沒裝的火警。**
生成 Lane Memo 時確保這兩個欄位存在。

---

## 對用戶的輸出格式

觸發後，在用戶下次開啟時顯示：

```
📋 Thesis 季度核查完成 — <日期>

所有 thesis 狀態正常 ✓（若全 active）
or
⚠ 有 <N> 條 thesis 需要注意（若有 watch/review_required）

回覆 "thesis 狀態" 查看詳細報告
```
