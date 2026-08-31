# 喚醒機制通盤盤點（trigger audit，2026-08-31）

> 使用者提問：「這類目前都有標下次喚醒日期或喚醒事件嗎？喚醒事件怎麼正確運作我也很關注，
> 我怕東西太多，未來根本石沉大海。」
> 本檔是 point-in-time 稽核報告，數字為 2026-08-31 實測值（會過期）；各機制的 SSOT 在
> 對應程式，查證命令附於各節。

## 總表：系統裡所有「以後要回來看」的東西與其喚醒方式

| # | 機制 | 存量（2026-08-31） | 喚醒方式 | 機器會動嗎 | 誰在看 |
|---|---|---|---|---|---|
| 1 | pq2 `pending --until` | 3 項等事件（81/134/200） | `until` 日期 | **❌ 無任何程式比對日期**（缺口 G1） | daily brief 等事件區（人） |
| 2 | pq2 `pending --trigger`（散文） | 同上 3 項 | 人讀散文描述 | ❌（設計如此） | daily brief（人） |
| 3 | pq2 `event_link=decision_evidence_delta` | 0 項綁定中 | 同 cohort material evidence receipt → sync 喚醒 | ✅（有 consumed-marker） | sync |
| 4 | trace backlog（parked lead 重排） | 49 筆非 terminal（312 parked 中其餘已 terminal） | `related_entity_signal`／`primary_source_signal`：新 triage PASS lead 共用具名標的 | ✅（consumed-marker＋primary 分流） | 每次 triage PASS |
| 5 | trace `requires_user` | 1 筆 | `source_trace_review` pq2 編號 | —（本來就等人） | 池子 |
| 6 | trace 死件偵測 | 0 筆 unreachable | `auto_trigger_reachable=false` 標記 | ✅ 標記，但**只在跑 trace_backlog 時可見** | harvest health／weekly |
| 7 | RA 凍結到期 | — | `expires_at` → 讀取時自動轉 `expired` | ✅ | sync（collector 不再產出→催 resolve） |
| 8 | thesis lifecycle `review_by` | — | 日期比對 | ✅ | SessionStart hook＋daily brief |
| 9 | catalyst watch | 覆蓋 calendar 內 cohort | `thesis/catalyst_calendar.json` 結構化日期 | ✅（覆蓋內）；散文 catalyst **測不到**（腳本自報） | daily routine |
| 10 | decision 凍結快照 7 天 | — | 時效硬擋 | ✅（`record_live_choice` fail closed） | gate |
| 11 | runway freshness 100 天 | — | 鮮度窗到期 → blocker 重新現形 | ✅ | reassess |

查證：
- 1-3：`python -c "import json; d=json.load(open('library/leads/todo_pool.json')); print([ (i['n'], i.get('waiting_on')) for i in d['items'] if i.get('waiting_on') and not i.get('resolved_at')])"`
- 4-6：`python -c "from engine_b.leads import load, trace_backlog; rows=trace_backlog(load()); print(len(rows), sum(1 for r in rows if not r['auto_trigger_reachable']))"`

## 誠實評估

**比預期健康的**：trace 端（#4-6）是全系統最成熟的喚醒機制——封閉字彙 kind、
consumed-marker 防無限喚醒（2026-08-12 教訓）、primary_source 分流（「等特定實體的一手
文件」不被隨便一則推文觸發）、死件自我標記。312 parked 中 263 筆已 terminal（正常結案，
不是沉底）；49 筆在等的全部可達。

**三個真缺口**：

- **G1（`until` 沒人看）**：`pending --until` 的日期純展示，無程式比對今天。現況傷害小
  （[81] 實際騎在 RA `expires_at` 上；另兩項只有散文 trigger），但這是「欄位存在≠流程
  存在」的 L7 形狀——使用者以為設了鬧鐘，其實設的是便條紙。
- **G2（pq2 散文 trigger 無機器路徑）**：[134]「AAOI Q3 guidance 公布後」、[200]
  「Agility S-4 生效」等的都是**特定實體的特定文件**——這正是 trace 端
  `primary_source_signal` 已經解決的問題，但 pq2 的 waiting 項接不到那個引擎：
  S-4 真的落地成 EDGAR lead 時，會喚醒相關 trace，**不會喚醒 pq2 [200]**。
  兩套等待、一套引擎閒置。
- **G3（可達性不可見）**：死件標記只在跑 `trace_backlog` 時可見；pq2 等事件項沒有
  任何「等了多久／可不可達」計數。L14 判準：真正的防呆是會自己出現的常駐計數器。

## 修法方向（進 ROADMAP，動工前照例鑄號）

1. **F1**：sync 時比對 `until` vs 今天，到期項自動從「等事件」翻回「等你決定」並標
  `until_expired`——不自動 drop、不自動 go，只是把過期的鬧鐘響出來。
2. **F2**：pq2 waiting 接上 trace 的同一個 trigger 引擎——`event_link` 新增
  `entity_filing_signal {entities:[...]}`：新 triage PASS 的 tier-1 lead 共用具名標的時
  喚醒 pq2 項（回到 user_decision，不自動 dispatch）。與 fact_verification（截圖
  brainstorm 的 B2）共用同一底座。
3. **F3**：daily brief 首屏常駐兩個數字：「等事件 N 項（其中機器可達 M）／trace backlog
  K 筆（死件 J）」——J>0 或 N-M 增長即是警訊。
