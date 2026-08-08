---
title: "可重建的事實不該被當成 point-in-time 凍結"
date: 2026-08-08
category: docs/solutions/architecture-patterns/
module: decision_lab
problem_type: design_smell
component: persistence
severity: high
applies_when:
  - 一次瞬時故障造成的空值，之後永遠沒被補上
  - 錯誤原因被記錄下來了，但沒有任何東西阻止或修復它
  - 想加重試，但重試一百次都會失敗
  - 某個欄位長期是 null，而依賴它的下游指標長期不可用
  - 「不可變」被用來拒絕修復，而不是拒絕竄改
tags:
  - immutability
  - repair-path
  - provenance
  - engine-d
  - fail-closed
---

# 可重建的事實不該被當成 point-in-time 凍結

## 一句話

**先分清楚哪些資料是「只有當下才有的真相」，哪些是「隨時可重建的事實」。
後者被當成前者凍結時，一次瞬時故障就會造成永久損失。**

## 事發（2026-08-08）

Engine D 的 Shadow 錨點記的是「訊號第一次進來時的價格」，用來回答**資訊價值**——
從我們知道這件事開始，股價走了多少。它與 paper（有 weight 的模擬部位，量的是
sizing／timing 的決策品質）是兩件事：訊號可以是對的，而系統把它 size 成 0，
**只有 shadow 記得住「我們看到了但沒動作」**。

實測 9 個 cohort 有 **7 個沒有錨點**。`outcomes._market_outcome` 明訂 shadow 非
`observed` 即 `market_return_status = "unknown"`，因此那 7 個的績效指標永遠是 null。
其中包含隨後自追蹤 **+107%** 的 `co:axt`——shadow 最該發揮作用的那一次，它失敗了。

## 為什麼「加重試」是錯的解法

六筆失敗有至少四種成因，只有一筆是真正的抓取失敗：

| Cohort | 成因 | 重試有用嗎 |
|---|---|---|
| LITE／META | cohort 建立時 registry entry 還缺 `market_currency` | ❌ 缺的是 config 那一列 |
| COHR | `market_timestamp_future`（日線 `as_of` 語意） | ❌ 缺的是時間單位定義 |
| IQE | 報價單位未正規化（GBp） | ❌ 缺的是幣別登記 |
| AXT | 真正的抓取失敗 | ✅ 但只有這一筆 |

**系統完整記錄了自己缺什麼，然後照樣往前走，並讓那個缺口變成不可逆。**
META 的凍結 identity payload 同時是 `"status": "resolved"` 與
`["market_currency_missing", ...]`——資訊一點都不模糊，缺的是**修復路徑**。

（這一點與 [`one-representation-two-meanings.md`](one-representation-two-meanings.md)
不同：那篇講的是表示模糊、下游被迫二選一；這裡的表示很清楚，問題在沒人依它行動。）

## 判準：兩類資料，兩套規則

| 類別 | 定義 | 規則 | 本專案的例子 |
|---|---|---|---|
| **Point-in-time** | 只有當下才有；事後無法重建 | 凍結、永不回寫 | decision context bundle、coverage、sizing |
| **Reconstructible** | 由已知時刻＋外部歷史可完整重建 | **必須有修復路徑** | Shadow 錨點（某日收盤價） |

判斷方法：問「如果我今天重新取一次，能不能得到與當時**應該**看到的相同的值？」
能 → reconstructible。Shadow 能（歷史收盤不會變），decision context 不能
（它包含當時的圖狀態、當時的 policy、當時的持倉）。

## 修復不等於竄改：兩道必要限制

既有測試 `test_unavailable_inception_is_immutable_and_never_hindsight_backfilled`
禁止事後回填，這個 invariant **不該被刪**。細看它防的是「用 inception **之後**的
價格覆寫錨點」——那會讓基準點被事後挑選，「從知道這件事開始漲了多少」變成一個
可以往有利方向偷移的數字。

因此修復路徑必須把同一條紀律寫成硬性檢查（`store.backfill_shadow`）：

1. **已 `observed` 的值永不覆寫。** 那是已記錄的觀測，覆寫等於改寫歷史。
2. **回填值的 `as_of` 必須早於 inception。** 這是 hindsight 防線。

外加兩項可稽核性要求：來源標 `backfill://` 以區分**重建**與**即時觀測**
（它是可辯護的重建，不是重播），並留 append-only `shadow_backfilled` 事件。

重建規則本身也要對齊觀測者當時的視野：只採 UTC 日期**嚴格早於**觀測日的 bar——
`co:axt` 觀測於 `2026-07-29T00:59Z`（美東 07-28 晚間），用同日 bar 會把錨點從
42.76 誤設為 36.97，憑空多出 16 個百分點的漲幅。

## 成本

回填後 7 個 cohort 全數取得錨點，`performance_since_tracked` 首次可用：

```
co:axt   +107.2%    co:aaoi  +35.4%    co:coherent +19.5%
co:sivers +17.2%    co:iqe    +6.8%    co:meta      +6.4%    co:lumentum +6.3%
```

**損失不在金額，在資訊。** probe cap 僅 0.2–0.5% NAV，即使 gate 全開，+107% 對 NAV
的貢獻也只有約 +0.3%。真正的代價是：系統的選題選對了，而它對這件事**零紀錄**——
「這系統值不值得留」這個問題連樣本都沒有。一個從不被寫入的模擬帳本是純成本、零效益。
