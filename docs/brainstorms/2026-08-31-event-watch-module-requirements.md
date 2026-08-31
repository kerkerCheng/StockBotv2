# Event Watch 模組（brainstorm，2026-08-31）

> 使用者定調：①等待事件整理成一塊 module；②**觸發不經使用者**——agent 自己發現、自己
> 喚醒；③沒有確定日期的事件可以主動輪詢（web search），但**輪詢力度必須可調**——
> token 少的時候調低照樣運作，不會卡住。
> 整併對象：trigger audit 的 F1-F3（[`docs/reports/trigger_audit_2026-08-31.md`](../reports/trigger_audit_2026-08-31.md)）
> ＋截圖 brainstorm 的 `fact_verification`。
>
> ✅ **已實作（2026-08-31，[306]＋[315]）**：registry＋三 kind＋T0/T1 sync 喚醒＋T2 sweep
> （K 旋鈕）＋計數器＋喚醒目標二選一（pq2｜hypothesis）＋consume CLI；無人值守 sweep 已過
> sandbox review 放行。落點：`engine_b/event_watch.py`、`config/event_watch.json`、
> `docs/OPERATIONS.md`「Event Watch」節。**刻意不做**：trace 引擎搬家。本檔轉為設計依據存檔。

## 為什麼要模組化

稽核發現系統有**五套**「以後要回來看」的機制（trace 引擎、pq2 waiting、RA expiry、
thesis lifecycle、catalyst calendar），成熟度極不均：trace 端有封閉字彙＋consumed-marker
＋死件自標，pq2 端的 `until` 甚至沒人比對日期。每新增一類等待（fact_verification、
S-4 生效、非上市公司事件）都在最弱的那端疊 workaround。整併成一個 watch registry，
所有等待條件用同一套字彙、同一個引擎檢查、同一個計數器現形。

## 核心設計：三層檢查成本階梯（輪詢力度可調的本體）

| 層 | 檢查方式 | token 成本 | 涵蓋 |
|---|---|---|---|
| **T0 被動** | 既有 harvest 流（EDGAR/MOPS watch、X since_id）落地的新 lead 自動比對具名標的——現行 trace 引擎原樣升格為模組核心 | **零**（harvest 本來就在跑） | 上市公司 filing、被追蹤帳號的推文 |
| **T1 日期** | sync 時比對 `until`／財報日／catalyst calendar | 近零 | 有確定日期的一切 |
| **T2 主動輪詢** | daily routine 的 bounded「watch sweep」：每輪最多 K 個 watch 各做一次 WebSearch，由優先序選誰輪到 | 花 token，**K 可調** | 無確定日、又不在被動流裡的（S-4 生效、非上市公司公告、產業事件） |

**退化路徑就是把 K 調到 0**：模組退回 T0+T1 純被動運作，什麼都不會卡——等待項只是
回到「靠 harvest 撞到」的現況，且計數器會誠實顯示「T2 停用中，N 項僅被動可達」。

## Watch registry（單一儲存）

每筆 watch：

```
{
  watch_id, created_at, expires_at（必填——無限期等待會腐爛）,
  condition:  # 封閉字彙，三選一
    {kind: entity_filing_signal, entities: [...], doc_hint}    # T0
    {kind: date, until: YYYY-MM-DD}                            # T1
    {kind: fact_verification, fact, 對照欄位, 時窗, 方向}        # T0（財報落地時對照）
  wake_target: {pq2: N} | {lead: id} | {hypothesis: id},
  poll: {eligible: bool, priority: 1-3, last_checked, query_hint},  # T2 屬性
  consumed: [...], source_credibility_ref
}
```

- 現行 trace 的 `related_entity_signal`／`primary_source_signal` 原樣併入（不重寫，
  搬家＋掛 registry）；consumed-marker、primary 分流、死件自標全部保留。
- pq2 waiting 項改為建 watch 而不是只寫散文；散文 `trigger` 保留給人讀（現行契約不變）。

## 觸發後的自主權邊界（為什麼「不經使用者」成立）

**喚醒是簿記＋研究，不碰四個 authority gate**：
- 喚醒 pq2 項 → 翻回 `user_decision` 現形（不自動 go）；
- 喚醒 trace → 重排 bounded pq1（現行行為）；
- fact 對照命中 → 自動做 bounded research、把 filing 逐字準備成 RA packet。
**只有入圖那一刻回到 pq2**——使用者核准的是 admission，從來不是「醒來」。
所以 agent 自己 trigger、自己研究、自己 prepare，全程不需請示；這與現行
「go＝推進到下一個 gate」語意完全一致，只是把「發現該推進了」也自動化。

## T2 sweep 的優先序與預算

- 每輪選 K 個：`優先序 = what-if 影響 × 已等天數 × 距上次檢查時間`；剛檢查過的沉底。
- config（`config/event_watch.json`，tracked）：`sweep_budget_per_run: K`、
  `min_recheck_days`、`enabled`。改 K 不改行為語意——只是改「多快發現」。
- 無人值守排程要跑 T2 需做 sandbox impact review（unattended WebSearch surface）；
  互動 session／自主迴圈可直接 sweep，不受此限。

## 驗收（L14）

- baseline：waiting 3 項機器可達 0 → 模組上線後 3/3（[134] AAOI guidance→fact_verification
  ＋T1 財報日；[200] Agility S-4→entity_filing_signal＋T2；[81] until→T1）。
- daily 首屏常駐：「watch N 筆（T0 可達 a／T1 排程 b／T2 輪詢 c／死件 d）」。
- T2 命中率記錄（sweep 找到事件的次數/總 sweep 數）——低於閾值代表 query_hint 品質差
  或該 watch 該降級，不是加大 K。

## 動工切法

1. **W1**：registry＋T1（until 比對）＋計數器——最小可用，先讓鬧鐘會響。
2. **W2**：pq2 接 T0（entity_filing_signal 複用 trace 引擎）＋fact_verification。
3. **W3**：T2 sweep（含 config knob＋sandbox review）。
4. trace 引擎搬家最後做（風險最高、現況又最健康，不急）。
