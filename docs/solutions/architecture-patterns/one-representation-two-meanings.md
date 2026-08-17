---
title: "一個表示承載兩種語意：閘門顆粒度錯位的共同形狀"
date: 2026-08-06
category: docs/solutions/architecture-patterns/
module: cross-engine
problem_type: design_smell
component: validation
severity: high
applies_when:
  - 一個 fail-closed 閘門擋掉的東西看起來大部分是好的
  - 想放寬或收緊某個驗證，但兩個方向都會壞
  - 同一個常數被套用在兩種來源／節奏不同的資料上
  - catch 之後回傳空值，而空值同時是合法結果
  - 修法讓警報消失得「太乾淨」
  - date-only 的值被貼上時區，而產生它的那一端用的是另一個時區
tags:
  - fail-closed
  - fail-soft
  - validation
  - granularity
  - engine-b
  - engine-c
  - engine-d
  - design-smell
---

# 一個表示承載兩種語意

## 為什麼把這四件事寫在一起

2026-08-05 一個 session 內修掉四個表面完全無關的缺陷：LSE 標的行情永遠 quarantine、
歐洲標的整份行情被一根 bar 廢掉、人工 runway 觀測永遠過期、待辦池無法得知項目已
完成。分屬 Engine B／C／D，症狀從「資料進不來」到「事情做完了沒人知道」。

它們是同一個形狀：**某個表示同時承載兩種語意，下游被迫二選一。**

認出這個形狀比記住四個 bug 有用得多，因為二選一的兩邊都是錯的——這正是它們難修
的原因，也是它們能存活很久的原因。

## 實例

| # | 表示 | 混在一起的兩種語意 | 二選一的代價 |
|---|---|---|---|
| 1 | `currency` 欄位 | 交易所**報價單位**（GBp）／ISO **結算幣別**（GBP） | 收 GBp → 價格 100 倍；改成 GBP → 價格仍 100 倍但無警報 |
| 2 | `market_history_row_invalid` | 值**缺席**（未結算）／值**損毀**（超出範圍） | 一律擋 → 1 根壞 bar 廢掉 59 根；一律放 → 破洞資料進決策 |
| 3 | `financial_freshness_days` | 每日刷新快照的 staleness／**財報週期**的 staleness | 用 14 天 → 人工 runway 永遠打不開；放寬 → 自動快照失去保護 |
| 4 | collector 回傳 `[]` | 成功執行但**沒有結果**／**執行失敗** | 當成完成 → 斷線清空整池；當成失敗 → 永遠無法結案 |
| 5 | `identity.status` | 身分**解析成功**／欄位**齊全** | 看 `resolved` 就走 → 建出永遠沒有錨點的 cohort；要求全齊 → 未上市公司無法追蹤 |
| 6 | 行情 `as_of` | 交易日**日期**（日線 bar 標當地午夜）／**觀測時刻** | 當時刻算小時 → 決策出生即 stale；當日期放寬 → 真過期也混過去 |
| 7 | shadow `unavailable` | 這檔**沒有行情**／這次**抓取壞了** | 當成沒行情 → 永不修復；當成抓壞了 → 對 registry 缺列無限重試 |
| 8 | 財務 `as_of`（date-only） | **本機時區**的日曆日／**UTC** 的精確 instant | 貼 UTC 午夜 → 台北早班每天判 future 並整份 quarantine；不比 → 隔日資料混進決策 |

### 2026-08-08 新增的三個（5–7）

第 5 個最值得記：`co:meta` 的凍結 identity payload 同時是
`"status": "resolved"` 與 `["market_currency_missing", "execution_currency_missing",
"execution_venue_missing"]`。下游只看 `status` 就往前走，三個 `*_missing` 就在旁邊
卻無人理會，於是建出一個**永遠沒有價格錨點的 cohort**——而該標的隨後自追蹤 +6.4%，
`co:axt` 同型失敗的那筆則是 +107%。

第 6 個是第 1 個的時間版：日線 bar 的 `as_of` 標的是交易日當地午夜，代表的卻是當天
收盤（美股約 20:00 UTC）。拿它當觀測時刻做小時級減法，36 小時上限實際只剩約 16 小時
真實鮮度——實測三筆決策在**凍結當下即已 stale**，而 stale 直接封鎖 paper lane。
修法同樣是「先分開再各自定規則」：行情改以**交易日**計，FX 與 financial 維持時間單位
（連續報價／財報週期本來就不是以交易日為心跳）。

第 7 個的下游影響見
[`reconstructible-vs-point-in-time.md`](reconstructible-vs-point-in-time.md)：
失敗原因塌成單一 `unavailable` 之後，就分不出「該修」與「修不了」，因而也決定不了
該加重試還是該加回填。

### 2026-08-17 新增的第 8 個

第 8 個是第 6 個的**時區版**，而且它連續兩天讓 daily routine 的財務層整份歸零
（2026-08-14、08-17）。`financial_snapshots.snapshot_date` 由 `date.today()` 產生，
是**本機時區的日曆日**；`engine_d_runtime.adapters._safe_timestamp` 卻一律把
date-only 值貼上 **UTC 午夜**。產生端與解釋端用了不同時區，於是憑空把 as_of 推到
未來最多一個時區位移——台北 06:30 的 routine 拿到 `as_of=今日 00:00Z`、
`evaluation_at=昨日 22:5xZ`，`_normalize_financial` 判 `financial_timestamp_future`
並 quarantine 整份財務。**台北 00:00–08:00 之間結構上必中，不是偶發**；閘門攔下的
是時區寫法，不是未來資料（L15：gate 攔的若是格式，該修的是它問問題的方式）。

修法是讓兩端用同一個時區：`date.today()` 產生的日曆日，就用**本機**當日 00:00 當它
的最早 instant（`.astimezone()`）。UTC 機器上行為不變（對稱），genuinely future
的隔日日期仍晚於 now 而被擋，且 as_of 比原本早一個時區位移、14 天 stale 窗反而更嚴。

第 3 個最能說明問題：`runway_inputs` 這個欄位存在的唯一理由，就是替
`derive_runway` 補上「沒有任何地方提供 manual_runway」那條缺掉的走廊。走廊蓋好
了，門口卻裝著為別種資料設計的鎖——財報落後季末 30-45 天，AXT Q2 季末
2026-06-30、8-K 申報 2026-07-30，**文件公開當天資產負債表就已超窗**。這條路徑對
絕大多數公司在任何時點都不可能通過。

## 修法的形狀永遠一樣

不是放寬，也不是收緊，是**先把兩種語意分開，再各自定規則**：

1. `identity/currency.py` — 報價單位 → (結算幣別, factor)，換算只做一次
2. row 迴圈分成「缺席且在序列末端＝未結算」與「超出範圍＝損毀」
3. `financial_runway_freshness_days` 與 `financial_freshness_days` 各管各的
4. `SourceCollection(rows, healthy)` — 空結果與失敗不再同形
5. date-only as_of 用**產生它的那個時區**解釋，完整 timestamp 維持精確 instant

分開之後，每一邊都可以套用比原本更嚴格的規則，而不是更寬鬆。#2 修完仍然擋掉序列
中間的破洞、負值與無法定位的 row；#4 修完仍然不自動 resolve，只標記候選。**顆粒度
變細不等於防線變弱**——恰恰相反，混在一起時你只能取兩者的下限。

## 怎麼提早認出來

**訊號一：兩個修法方向都會壞。** 這是最強的訊號。如果「放寬」和「收緊」都能舉出
具體災難，那多半不是參數沒調好，是有兩件事被壓在同一個表示裡。

**訊號二：fail-closed 擋掉的東西看起來大部分是好的。** 59:1 是很誇張的比例，但
比例本身不是重點——重點是「大部分是好的」意味著判準抓錯了維度。

**訊號三：一個常數被套用在兩種節奏的資料上。** 每日刷新與每季申報之間差了一個
數量級，任何單一窗口都會偏袒其中一邊。看到同一個 `*_freshness_*` 被兩個來源共用
就該起疑。

**訊號四：修法讓警報消失得太乾淨。** #1 的第二種修法（registry 直接改 ISO code）
會通過所有驗證、清掉所有 blocker，然後餵給決策層一個差 100 倍的價格——比原本
「整份 quarantine」危險得多。同型體悟見 L11（自己引用的事實要套跟圖裡 claim
同一套追源紀律）：方向剛好對、剛好嵌得進既有敘事時，最該起疑。

**訊號五：`except` 之後回傳的值，同時是合法結果。** `return []`、`return None`、
`return 0` 都是常見形式。fail-soft 本身通常是對的，錯的是讓失敗與空結果同形。

## 一個不完全相同、但相鄰的毛病

同一天還修了 `action_card` 的 `blockers` 少放 `core_blockers`：`action` 是由
`core_blockers`（assessment ∪ coverage）判成 REVIEW 的，但 card 只把
`assessment_blockers` 放進自己的 `blockers`。於是**驅動結論的原因不在結論的證據
裡**，待辦池據此推導出「重新 reassess 即可」——與真正的缺口（一筆待填的 runway
觀測）完全無關，而且會誘導人去跑一個不改變任何東西的 reassess。

這不是兩種語意混在一起，是**因果被截斷**：下游拿到了結論卻拿不到理由，只好從殘
餘資訊裡猜一個。判準相近——**任何會改變輸出的輸入，都必須出現在該輸出自己的證據
欄位裡**。

## 相關

- [`external-market-data-normalization-boundary.md`](external-market-data-normalization-boundary.md)：
  #1 與 #2 的完整追查、換算契約與測試
- [`closed-vocabulary-registry.md`](closed-vocabulary-registry.md)：分開之後，
  新的那一半該住 config 還是 code（taxonomy vs contract）
- [`lifecycle-terminal-verbs.md`](lifecycle-terminal-verbs.md)：相鄰但不同的形狀——
  那裡的字彙定義乾淨、下游處理正確，混淆發生在**呼叫端**挑錯值（`--terminal-status`
  的四個值裡有一個不終止 lifecycle）。判準也不同：不是「先分開再各自定規則」，而是
  「沒有值精確符合意圖時，選最少斷言的那個」
- AGENTS.md 的 L4（屬性歸位三分）是同一判準在 schema 上的版本：換掉關係另一端會
  不會變、會不會隨時間變、講的是物理現實還是證據強度——三問也是在逼你把混在一起
  的語意拆開
