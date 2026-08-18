---
date: 2026-08-18
topic: alpha-live-user-sized
status: direction-frozen（使用者已選定方向；實作未開始）
承接: 2026-08-13-capital-expression-direction §4 第 5 項、AGENTS.md「Alpha 呈現契約」
---

# Alpha live：尺寸由使用者定，Engine D 只做歸因

> **起因（2026-08-18）：** 「繼續探討 alpha 池子擴大後該怎麼實踐 live 的策略」。
>
> **本檔刻意短。** `2026-08-02-confidence-axes` 膨脹到 61KB 的成因是每輪加章節而不更新數字；
> 本檔只寫方向、擋路者、驗收條件三件事。

---

## 1. 擋路者不是 gate，是一個結構矛盾

`decision_lab/store.py:1769-1771`：

```python
lower, upper = payload["sizing"]["live_supported_range"]
if selected_weight > float(upper) + 1e-12 and not force_override:
    raise ValueError("live selected weight exceeds supported cap")
```

而現行 `live_supported_range` 上界最高 **0.002（0.2% NAV）**。

同時 `AGENTS.md`「Alpha 呈現契約」（2026-08-15 使用者定案）已經定了：
**系統不對使用者呈現尺寸，買多少由使用者決定。**

兩者一起的後果：**使用者按自己判斷買任何有意義的金額，每一筆都必須走 `force_override`。**
設計成例外的路徑變成唯一的路徑。

這是 L12 的形狀：`selected_weight` 一個欄位承載兩種語意——「使用者接受了系統推薦的尺寸」
與「使用者用自己的判斷定了尺寸」。gate 只認前者，於是後者無路可走。
`record_live_choice` 的 `choice_type`（`accepted`／`below_range`／`skipped`／`override`）
全部是相對於系統區間定義的，**字彙裡沒有「系統沒有意見」這個選項**。

**修法形狀照 L12：不是放寬也不是收緊，是先分開再各自定規則。**

---

## 2. 方向（使用者 2026-08-18 選定）

新增第五種 `choice_type = user_sized`：

| 面向 | system-sized（現況，保留不動） | user_sized（新增） |
|---|---|---|
| 尺寸來源 | 系統 `live_supported_range` | **使用者** |
| 與 supported_range 比較 | 硬性上限 | **不比較**，但**記錄**當時的 `system_supported_upper` |
| 5% 單筆上限 | 硬擋 | **硬擋**（不放寬） |
| ETF 槓桿 nominal／effective cap | 硬擋 | **硬擋**（不放寬） |
| 總曝險 cap | 硬擋 | **硬擋**（不放寬） |
| 研究完整度／五軸／coverage blocker | 歸零 | **不適用**——那是研究進度，不是風險判斷（D2） |
| explicit 人工確認 | 必要 | 必要 |
| reason | 選填 | **必填** |

**下游完全不用改。** `record_live_fill` 只要求「有一筆 `selected_weight > 0` 的 choice」
＋幣別符合執行身分＋時序正確；那三項全部保留。

### 為什麼是 B 不是「把 axis_ceilings 調大」

1. **與 2026-08-15 剛定的契約一致**，不必推翻三天前的決定。
2. **不違反 D7（先量測後放閘）。** 調大 ceiling 是放閘；本方案不動任何 ceiling，
   只承認尺寸的來源本來就不是系統。ROADMAP 那條「不得因為閘門修好了就順手調大
   `axis_ceilings`」仍然完整有效。
3. **paper 記分板保持可比。** ceiling 若被調過，前後期 paper target 就不能互比，
   而 paper 是 outcome 量測的唯一資料來源。
4. `record-choice` 的 supported_range gate 是為「系統推薦尺寸」的世界設計的，
   **那個世界使用者已經明確否決了。**

### 明說這個交換放棄什麼（D7 要求）

**使用者會在事後證明錯的 thesis 上真的虧錢，而且系統不會攔。** 這是正確的交換，
但必須是被明說的選擇。系統保留的唯一防線是三個 deterministic 資本上限，
不是研究品質判斷。

---

## 3. 支撐這個決定的量測（2026-08-18 新增）

`2026-08-13-capital-expression-direction` §2.7 建立了「系統選標的準不準」的第一份證據。
ROADMAP「進行中」同時標了一條**從未被驗過**的警告：錨點日＝cohort 建立日，
若 lead 是因為「股價已經在動」才通過 triage，超額就是追高而非判斷力。

**2026-08-18 首次實測，該偏誤方向與擔心的相反：**

| | 錨點前 30 日 | 錨點後 |
|---|---|---|
| 中位數（n=10） | **-9.2%** | **+15.0%** |
| 追高形狀（前 > 後） | **1 / 10**（僅 AEVA） | — |

極端值：AXTI 錨點前 -39.0% → 後 +124.4%；SIVE.ST 錨點前 -61.6% → 後 +31.9%。
已核原始收盤序列：AXTI $70 → $45.86 → 錨在 $42.76 → 現在 $95.97，V 型是真的。

⚠ **本項只排除「追動能」，不排除「高 beta ＋剛好在 sector 底部做研究」。**
同期 SOXX 是 -16.7% → +13.8%，**同一天見底**。扣掉 SOXX 後仍是 8/10 為正、
中位超額約 +11%，代表不只是 beta——但 n=10、單一時窗、單一 AI 光通訊主題
（§5 共移問題）。**這是訊號，不是證明。**

**已做成常駐欄位**（`scripts/outcome_if_settled_today.py` 的「追高檢查」段落），
理由見 `capital-expression-direction` §6：檢查點住在要人主動想起來去讀的文件裡就會失效。

---

## 4. 驗收條件

照 L14 第 1 條，每項都是「現有資料有幾筆真的變了」，不是「這一步有沒有跑成功」。

| # | 動作 | 驗收條件（可證偽） |
|---|---|---|
| 1 | `store.record_live_choice` 支援 `user_sized` | `live_choices` **0 → ≥1**，且該筆 `choice_type='user_sized'`、`selected_weight` 大於當時 `system_supported_upper` |
| 2 | 三個資本上限對 `user_sized` 仍硬擋 | 測試：超過 5% 單筆上限的 `user_sized` choice **被拒絕**；剛好等於上限的**被接受** |
| 3 | 研究完整度 blocker 對 `user_sized` 不生效 | 測試：一個 `axis_ceiling=0`／`live_lane_blockers` 非空的 decision 仍可記錄 `user_sized` choice |
| 4 | 端到端走通一次 | `live_execution_reports` **0 → ≥1**，且該 fill 可由 `decision_id` 回溯到 cohort 與 thesis |
| 5 | 歸因可回答 | outcome 報表能分辨「有 live fill 的 cohort」與「只有 paper 的 cohort」，並各自算報酬 |

**第 4 項是真正的驗收。** 前三項全部通過而 `live_execution_reports` 仍是 0，
就代表管子只接了一頭（L13：驗收條件是產出出現在下游消費者手上，不是這一步回傳成功）。

---

## 5. 明確不做

- **不動 `axis_ceilings`、不動任何 blocker 的嚴重度分類。**
- **不自動下單、不連 broker。** fill 永遠是使用者手動下單後回報。
- **不寫 Google Sheet。** live inventory 唯一權威仍是 Sheet，由使用者自己維護。
- **不替 beta 例行投入建 decision。** ROADMAP「看起來像缺口但不是」那段的理由完整有效。
- **不回寫既有 frozen decision。** point-in-time 契約不變。

---

## 6. 待決（實作前要問使用者的）

1. **`user_sized` 是否需要 `prepare_action` ＋ native approval 兩段式？**
   現行 `override` 走兩段（prepare → apply）。兩段比較安全，但也比較煩；
   考量到這是**每次真實下單都會走**的路徑，一段式（explicit flag ＋必填 reason）可能更合理。
2. **第一筆要拿哪一檔試？** 建議 AXTI 或 LITE——兩者 paper 都是 ELIGIBLE、
   財務 gate 已過、且 Shadow 錨點與價格序列都健康，回溯歸因最乾淨。
