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

## 3. ~~支撐這個決定的量測~~ → **同日被使用者推翻，保留作紀錄**

> 🔴 **本節原本用來支撐 §2 的方向，當天稍晚被使用者一句話推翻並查證屬實。**
> 方向（§2）不受影響——它本來就不依賴「系統選股準」，只依賴「尺寸來源是使用者」。
> 但**本節不得再被引用為選股能力證據**。理由見 §7。

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

## 6. 實作紀錄（2026-08-18）

**已完成驗收條件 1–3。** 使用者選定**一段式**（`--explicit` ＋必填 `--reason`），
理由是這是**每次真實下單都會走**的路徑而非例外路徑，兩段式的摩擦會讓人乾脆不記錄，
而不被記錄的 fill 等於記分板永遠答不出來。

落點：`decision_lab/store.py`（`_HARD_CAP_BLOCKERS`、`_assert_user_sized_within_capital_caps`、
`record_live_choice(user_sized=...)`）、`execution.py`、`cli.py --user-sized`、
`schema.sql` v7→v8、`scripts/migrate_decision_store_v8.py`。
測試：`tests/test_decision_execution.py` 兩條，全 suite 942 passed / 2 skipped。

### 實作時被實測推翻的一個設計

首版把 **`portfolio_leverage_unavailable` 納入硬擋**，理由是「無法驗證的上限不能宣稱已執行」，
聽起來像正確的 fail-closed。**測試當場推翻**：它在乾淨 fixture 與**每一筆**真實 decision
上都亮——觸發率近 100%，正是 `capital-expression-direction` §3.5 的**恆亮測試**（零鑑別力）。

更關鍵的是它過不了**機制測試**（D3）：說不出「這碼亮起時，這檔標的更可能變壞」。
它實際上是 `sizing.py` 一個寬 except 捕捉到的三種情況之一（NAV 讀不到／beta policy 載入失敗／
component 組不起來），是管線狀態不是風險判斷。附帶理由：ETF 槓桿 cap 管的是 beta sleeve
的組合結構，買一檔 alpha 個股根本不改變槓桿比率——拿算不出來的 beta 控制去擋 alpha 決策，
是把控制掛錯層。

**這件事本身就是 D6 的示範：一個看起來更嚴格、寫進 config 標了 `fatal` 的 blocker，
在第一次被實際量測時就沒通過。** 判斷已用一條測試鎖住，未來想加回去會先撞到理由。

### 還沒做的（驗收條件 4–5）

第 4 項（`live_execution_reports` 0 → ≥1）**必須由一筆真實下單觸發**，不能靠測試偽造。
第 5 項（outcome 報表分辨 live／paper cohort）等有第一筆 fill 之後才有東西可分辨。

**第一筆建議拿 AXTI 或 LITE 試**：兩者 paper 都是 ELIGIBLE、財務 gate 已過、
Shadow 錨點與價格序列健康，回溯歸因最乾淨。實際流程：

```powershell
& '.venv\Scripts\python.exe' -m decision_lab record-choice <decision_id> `
  --selected-weight 0.01 --explicit --user-sized `
  --reason "<為什麼是這個尺寸>" --confirmation-ref "<你自己的紀錄編號>"
& '.venv\Scripts\python.exe' -m decision_lab record-fill <decision_id> `
  --execution-ref "<券商成交編號>" --shares <股數> --price <成交價> --currency USD --explicit
```

⚠ **不得拿既有持股回填。** `record_live_fill` 要求
`executed_at >= max(choice.decided_at, decision.effective_at)`，早於 decision 的成交會被
正確拒絕。就算繞過，回填也**測不到任何東西**——這條鏈路要回答的是「Engine D 的建議準不準」，
而一筆在 Engine D 有意見之前就買好的部位，對這個問題零資訊。既有持股的真相在 Google Sheet，
Engine D 不需要複製它（ROADMAP「看起來像缺口但不是」：第二個真相來源是負值）。

---

## 7. 錨點問題：量測要能成立，錨點必須帶有進場判斷

**2026-08-18 使用者提出、當日查證屬實：**

> 「我們的錨點應該只是剛好我們那時候把系統打通而已？而且建 cohort 通常只是因為入圖，
> 並不是我們覺得那時候可以買？」

查證結果：

1. `decision_cohorts.dedupe_key` **全部**是 `claim:<hash>`——cohort 由入圖建立。
   Shadow 錨點日的語意是「這家公司的 claim 那天進圖」。
2. 10 個 observed 錨點全部落在 `2026-07-21 ~ 08-14`（24 天、4 個日曆週）。
   SOXX 在 07-28 見底，正好在窗口中間。標的幾乎全屬 AI 光通訊。

**結論：有效 n ≈ 1。** 那是一次 sector 移動被相關標的複製 10 次，窗口就是系統建置期。

### 這對本檔 §2 的方向有沒有影響？沒有

§2 的論證從來不是「系統選股準所以可以下真錢」，而是「**尺寸來源本來就是使用者**，
系統的 supported_range 不該當使用者尺寸的上限」。那個論證不依賴選股能力證據。

**但它對「系統值不值得留」這個更大的問題影響很大**——那個問題目前仍然無法回答。

### 修法方向：`user_sized` choice 本身就是缺的那個錨點

`live_choices.decided_at` 是**使用者明確決定買入的時點**，而且必填 `reason`。
它天生就是「進場判斷日」，正是 Shadow 錨點缺的東西。

因此驗收條件 4 的價值比原本寫的更高：它不只是「走通一次管線」，
**它是第一個帶有進場判斷語意的錨點**。量測應改成：

| 錨點 | 語意 | 用途 |
|---|---|---|
| `shadow_observations.as_of` | 入圖日 | 只能答「這批標的在什麼行情位置入圖」 |
| `live_choices.decided_at` | **使用者進場判斷日** | 才能答「判斷準不準」 |

⚠ 兩者不得混用或合併成一欄——那正是 L12。報表應分開呈現，並在 `live_choices` 累積到
足夠筆數（且跨度 > 60 天、跨主題）之前，**不得宣稱系統或使用者的選股能力已被量測**。

### 還缺的：買賣策略（使用者 2026-08-18 提出）

> 「我覺得我們缺的是在池子中［找出哪些有未來性、決定買入賣出策略］這件事。
> 買入的量我決定，然後每天追蹤就好。」

現況盤點：

| 要件 | 現況 |
|---|---|
| 找出候選 | 有（ELIGIBLE cohort），但廣度不足、且使用者反映「都是我早就看到的公司」 |
| **賣出條件** | **欄位有、流程沒有**——`disproof_condition` 是必填，但沒有任何機制每天檢查它是否已觸發。這正是 L7 的原話：「貼了一個永遠不會響的火警警報」 |
| **買入時點** | 不存在。⚠ 且不得直接照搬 beta 的技術訊號——那套 2026-08-01 實測 0 勝 3 敗 |
| 每天追蹤 | 部分有（daily brief 顯示 evidence_delta），但不含 disproof／catalyst 的狀態 |

**最小且不違反 D6 的下一步是賣出側，不是買入側**：`disproof` 與 `catalyst` 已經是
每筆 decision 的必填欄，把它們從卡片上的散文變成**每天被檢查的狀態**
（未觸發／接近觸發／已觸發需 review／催化劑逾期未發生）。這是**條件檢查，不是訊號**——
不需要先證明任何預測能力，因此不受 D7「先量測後放閘」限制。

買入時點則相反：任何「現在該買」的機制都是未經量測的新訊號，依 D6 不得享有默認信任。
誠實的做法是系統只回答**「為什麼是現在、下一個催化劑是什麼、什麼時候」**，
由使用者決定買不買。

---

## 8. 瓶頸鏈排序（2026-08-18 使用者定調；本節是主體）

使用者看過催化劑範例後的回應，重新定義了優先序：

> 「我想像中的 flow 應該是：我跟你對話、或自動列出 cohort 中**真的技術瓶頸**的股票 →
> 看近期催化劑追蹤 → 要不要進場看我自己。其實我最想的可能是第一步，技術瓶頸的部分。」

**這個優先序是對的，理由不是偏好而是差異化：** 財報日曆是商品化的東西，到處都有且免費；
**瓶頸結構不是**。第一步是這套系統唯一無法外購的部分，也正是 Engine A 存在的理由。

### 8.1 使用者的鏈路模型（已對圖驗證通過）

> 「CPO 是 AI SERVER 的瓶頸，InP 是 CPO 的瓶頸，瓶頸相連要能連到真的市場有在放 CapEx 的地方。」
> 「我只是想表達要是真的市場有在投資的點，不然一個沒人用的技術的瓶頸，好像也沒用。」

**判準因此是：瓶頸必須錨定在有人真的在花錢的需求上，否則它只是冷知識。**

圖上實測（2026-08-18）：

```
tech:ai_compute_buildout ─[enables]→ tech:cpo          ← 需求錨點（5 條邊）
tech:ai_switch           ─[enables]→ tech:cpo
      tech:cpo ─[depends_on, sub=5]→ tech:external_laser_source
      tech:uhp_laser / cw_dfb_laser / inp_eml / eml_laser / inp_cpo
                       ─[depends_on, sub=5]→ mat:inp_substrate
      co:coherent / co:lumentum ─[depends_on, sub=5]→ mat:inp_substrate
```

`mat:inp_substrate` 有 **8 條 sub=5 入邊**，是全圖最強收斂點。

**結構關鍵：需求向上、瓶頸向下，用不同邊型。** 向上走 `enables`／`is_component_of`
找需求錨點（這些邊的 `substitutability` 是 None，本來就不該有）；向下走
`depends_on`／`supplies_to` 找 chokepoint，只有向下的腿計權重。**不需要改 schema。**

### 8.2 三層，順序不可反

| 層 | 內容 | 為什麼必須排在前面 |
|---|---|---|
| **L8 修復** | 依 `origin_entity` 判定 sole_source 是否供應商自報 | 見 8.3——不修就會把行銷話術排第一 |
| **瓶頸鏈排序** | 輸出「公司 × 瓶頸邊」，附鏈路與需求錨點 | 主體 |
| **催化劑接入** | 用 `qualification_status` 當瓶頸 thesis 的真催化劑 | 需要前兩層的輸出當輸入 |

排序單位使用者選定為**「公司 × 瓶頸邊」**而非公司：AXT 本身不是瓶頸，
**AXT 在 InP 基板這條邊上**才是；一家公司可出現多列。

### 8.3 L8 檢查從未執行過——實際是 1/3 自報（✅ 2026-08-18 已修）

⚠ **本節初稿寫「4/4 全是供應商自吹」，是錯的，錯因值得記下來。**
初稿是**逐 EdgeAssertion** 判定，而每個 assertion 只引一份文件，於是每一筆看起來都同源。
但 `schema/graph_schema.md` §7 的判定單位是 **canonical edge（`edge_key`）的「所有
source_ids」**——必須跨 assertion 聚合 origin。改用正確單位後結果完全不同：

| sole_source 邊 | 全部 `origin_entity` | 判定 |
|---|---|---|
| co:coherent → co:nvidia | Coherent、**NVIDIA**、Global Semi Research | ✅ **客戶端本人印證**，正是 §7 要求的 `verified_by_search` |
| co:broadcom → tech:cpo | Broadcom、The Next Platform | 🟡 待人工判定（見下） |
| co:lumentum → tech:uhp_laser | 只有 Lumentum | 🔴 自報 → **已降級** |

**已執行：** `scripts/audit_sole_source_independence.py --apply`，
`lumentum_q2fy26_cpo_e9` 與 `lumentum_q3fy26_cpo_e5` 寫入
`sole_source_evidence_quality=weak`、confidence **0.9 → 0.5**，manifest 存於
ignored `library/private/graph_migrations/`。重跑冪等。

### 8.3.1 稽核腳本自己踩到的 L12（已修，值得記）

首版判定式是 `resolved == {subject}`——只要有任何 origin **解析不出 `co:*`**，
集合就不等於 `{subject}`，於是**自動被當成外部佐證放行**。

但 `None` 同時承載兩種相反語意：(a) 真的是第三方媒體（§7 接受）、
(b) 沒解析出來的子公司或別名（§7 不接受）。下游被迫二選一而兩邊都可能錯。
`co:broadcom → tech:cpo` 就是實例：唯一的非本人 origin 是 `The Next Platform`，
它**恰好**真的是第三方媒體，所以首版的結論碰巧正確——**但那是運氣，不是判準**。

已改成三分：解析到不同公司 → `externally_corroborated`；只剩無法解析者 →
`needs_review`（不自動放行）；全是本人 → `self_reported`。

### 8.3.2 更大的問題在 substitutability，不在 sole_source

擴大統計（`--all-bottleneck`）：**58 條帶 `substitutability` 的 canonical edge，
50% 只有供應商自報 origin。** §7 的規則只寫給 `sole_source`（3 條），
但排序主要吃的是 `substitutability`（58 條）——**修了小的、放過大的**。

排名輸出因此必須逐列標示證據等級（自報／外部印證），且**證據等級是排名的上限**：
一條只有供應商自評 sub=5 的邊，不得排在有客戶端印證的 sub=4 之前。

### 8.4 資料現況與已知限制（必須常駐於輸出）

423 條 EdgeAssertion，瓶頸屬性存在 `attributes` JSON blob：

| 屬性 | 覆蓋 | 值分布 |
|---|---|---|
| `qualification_status` | 167（39%） | 最多，但沒接到任何消費者 |
| `substitutability` | 91（22%） | 5:21、4:31、3:19、1:1 |
| `ramp_execution` | 63（15%） | 4:28、3:18、5:1 |
| `sole_source` | 44 | true 僅 4（見 8.3） |
| `structural_lead_time_weeks` | 17 | **16 個是 null，實際只有 1 個真值** |
| `sole_source_evidence_quality` | **0** | 從未填過 |

**覆蓋率 22% 是已知限制，採方案 (a)：先做排序、把限制標在輸出上**，而不是先回頭補 332 條邊。
理由是先看到東西才知道值不值得補、以及該優先補哪些。⚠ 但排名必然偏向「剛好被抽過的邊」，
這個偏誤**必須每次隨排名出現**，不得只寫在文件裡（L14：常駐計數器才是防呆）。

### 8.5 CapEx 錨點：第一版只做結構，不帶金額

使用者澄清 CapEx 的用途是**存在性判準**（「有沒有人真的在花錢」），不是權重來源。
因此第一版只需回答「這條鏈路走不走得到需求錨點」，走不到就降級或不列。
金額（hyperscaler capex 等，目前躺在 leads 裡）若日後要接，走 Engine C observation，
**不進 Engine A**（L4 第 2 問：會隨時間變的不是靜態圖屬性）。

### 8.6 順帶查出、需另案處理的兩件事

1. **188 個 Claim 節點貼著 `:Entity` 標籤**（ID 形如 `<doc_id>_cl1`、name 是 claim 全文）。
   真正的 Entity 有 223 個、**100% 有 type 且前綴與 type 完全一致**。
   所以這不是型別覆蓋缺口，排序只需一行過濾（排除無前綴者）；但
   **任何 `MATCH (n:Entity)` 都會多撈到 188 個 claim**，是會反覆咬人的那種問題，應給 Claim 自己的 label。
2. `comp:humanoid_precision_actuators` 前綴為 `comp:` 但 type 是 `TechNode`——唯一不符前綴慣例者。

### 8.8 紅隊審查結論（2026-08-18，`blind-spot-audit`）

**已撤回一條：** 審查原本報「排名會重現使用者最初的抱怨（sub≥4 有 52% 集中在 InP／光通訊鏈）」。
使用者澄清後撤回——

> 「好像不衝突，我們就是從我們讀到的公司，也就是我們繞了很久的公司之中，挑出最有機會成為
> 瓶頸的。如果還是這幾家那也沒關係。」

原始抱怨是**尺寸沒有資訊量**（全是 0.1%），不是名字太熟。名字熟但系統能說出「卡在哪條邊、
多難繞過、上面接到誰在花錢」，就是新資訊。**排名的任務是排序，不是發現。**

**但這使另一條升級：** 若任務是「在讀過的公司裡排序」，排名就**絕對不能是「我們讀了多少」
的函數**。實測 `co:axt → mat:inp_substrate` 有 4 條邊來自 4 份文件、`co:lumentum` 3 條、
`co:coherent` 2 條；24 條入邊去重後只剩 16 個 `(src, relation)`。
**再 ingest 五份 InP 報導，分數就會上升而世界沒有改變。**
→ 排名必須先以 `(src, relation, dst)` 去重，且**每組取最高 confidence，不做加總**。

其餘未解項（按優先序）：

| # | 發現 | 狀態 |
|---|---|---|
| 1 | 排名分數與 ingestion 量混淆 | ✅ **已解**（`query/bottleneck.py`）：先以 `(src, relation, dst)` 去重，423 assertion → 345 canonical edge（收斂 78 筆）；`documents` 保留但不參與排序 |
| 2 | `user_sized` 沒有入口——daily brief 不提示，`live_choices` 仍 0 筆 | 🔴 未解；修法是 brief 直接印可複製指令 |
| 3 | `user_sized` 的資本上限讀凍結快照，無時效上界 | 🔴 未解；三個月前的 decision 仍可放行，可疊出超過 5% |
| 4 | `ANCHOR_SPAN_WARN_DAYS=60` keyed 在錯的變數 | 🔴 未解；跨度自然增長會讓紅字自己關掉，而語意問題還在。應改 keyed 在「有幾筆錨點來自 `live_choices`」 |
| 5 | `structural_lead_time_weeks` 只有 1 個真值 | 🟡 排名須標明未含 lead time；補它比補 332 條 `substitutability` 更有價值 |
| 6 | 排名列與 cohort 的對應未定義 | 🟡 傾向：排名列是唯讀呈現單位、不建 cohort |

### 8.8.1 排名已實作（`query/bottleneck.py`，2026-08-18）

指令：`python -m query.bottleneck`。25 列「公司 × 瓶頸邊」，前六名：

| # | 標的 | 卡在哪 | 替代難度 | 證據 | 需求錨點 |
|---|---|---|---|---|---|
| 1 | COHR | supplies_to `co:nvidia` | 5/5｜sole_source | 外部印證 | `tech:ai_switch`（2 跳） |
| 2 | COHR | depends_on `mat:inp_substrate` | 5/5 | 外部印證 | `tech:ai_switch`（2 跳） |
| 3 | AVGO | supplies_to `tech:cpo` | 5/5｜sole_source | 待判定 | `tech:ai_switch`（1 跳） |
| 4 | LITE | depends_on `mat:inp_substrate` | 5/5 | 待判定 | `tech:ai_compute_buildout`（3 跳） |
| 5 | **AXTI** | supplies_to `co:coherent` | 4/5 | 待判定 | `tech:ai_switch`（2 跳） |
| 6 | 5802.T | supplies_to `co:lumentum` | 4/5 | 待判定 | `tech:ai_compute_buildout`（3 跳） |

AXT 的鏈路 `tech:ai_switch → tech:cpo → co:coherent → co:axt` 正是使用者的模型。

**排序鍵是明確優先序，不是加權綜合分數**（綜合分數會是未經量測的新機制，D6，
且會把證據強度與瓶頸強度壓成一個數字，L12）：
`(需求可達, 證據等級, substitutability, sole_source, qualification, 距需求端跳數)`。

#### 跑出來才發現的四個 bug（已修，各有一條測試鎖住）

1. **需求鏈是垃圾。** 首版用「往上走最長路徑、端點即錨點」，圖裡有環於是繞回目標本身
   （`… → tech:ai_compute_buildout → co:lumentum`），端點常是 `tech:semicon_manuf_equipment`
   這種上游設備而非需求。**看起來結構化、實際無意義的欄位比沒有這一欄危險。**
   改成明確列舉 `DEMAND_ANCHORS` ＋ BFS 最短路徑，**走不到就回 None，不用最近節點充數**。
2. **AXT 整個從排名消失。** 收斂時「取 confidence 最高那份 assertion 的全部屬性」，
   若該份沒填 `substitutability` 就整條邊丟值。改成**逐屬性**取最佳 confidence——
   語意是「對這個屬性發言過的文件裡，最可信的那份怎麼說」。覆蓋率也從假掉的 16% 回到 17%。
3. **向上索引漏了 `supplies_to`。** `A supplies_to B` ⇒ B 需要 A，需求要沿它往上傳；
   漏掉導致任何「瓶頸目標是一家公司」的列都顯示無錨點。`supplies_to` 同時在向下
   （帶 substitutability）與向上（需求傳遞）兩個索引裡是正確的——同一條有方向的供需邊，
   兩邊問的問題不同。
4. **需求鏈從瓶頸節點走而非從公司走。** 於是 LITE 那列的鏈路繞經 Coherent——對
   `mat:inp_substrate` 正確，但不是那一列在問的問題（「這家公司的產出有沒有人在花錢買」）。

⚠ **`DEMAND_ANCHORS` 是封閉字彙，目前只有四個 AI/光通訊節點。** 圖擴到別的領域時它會靜默
地讓新領域全部顯示「無錨點」——擴充改那個常數，不要改演算法。

### 8.9 反向使用：用瓶頸目標驅動研究優先序（使用者 2026-08-18 提出）

> 「未來決定何者先做研究的方向，也可以先訂找瓶頸這個目標。那為了達成這個目標，
> 我們要怎麼抓新公司進來做研究？」

**這把箭頭反過來，是本輪最有價值的想法。** 圖已經知道 chokepoint 在哪
（`mat:inp_substrate`，8 條 sub=5 入邊），也知道目前掛在上面的供應商只有
AXT／Sumitomo／JX Advanced Metals／Casela。**「這條 chokepoint 上還有誰沒被研究過」
是一個精準的 harvest 目標**，比通用抓取好得多，而且它直接回答 ROADMAP「廣度」那條
（現況：清 pq1 積壓、擴 harvest 來源——都是無方向的）。

迴圈形狀：

```
瓶頸排名（讀過的公司）→ 找出供應商覆蓋不完整的 chokepoint
   → 產生具名的 research target → onboard → 回到排名
```

⚠ 這條迴圈**尚未設計，也不在本輪 scope**。登記在此以免流失；動工前必須先解 8.8 的第 1 項，
否則「覆蓋不完整」的判定會跟排名分數犯同一個錯（把「我們讀得少」當成「供應商少」）。

### 8.7 買賣資訊的方向性（使用者提出）

> 「這些催化劑是看多看空？然後真的成了是好是壞？這些能一起揭露給我嗎？」

現況：每筆 decision 強制有 `disproof_condition`（什麼會殺死 thesis），
**但沒有對稱的 confirmation 欄位**，所以系統只能說何時該賣、不能說何時變更好；
催化劑文字目前一律寫成「揭露 X」，方向中性。

同時使用者觀察到「這些好像都是財報的催化劑」——**屬實且成因可診斷**：
skill 要求催化劑「可觀測、有門檻、有日期」，財報是最容易同時滿足三條的東西，
於是起草者每次都選它。但瓶頸 thesis 的真催化劑是圖事件（第二供應商合格、產能擴張、
design-win），而 `qualification_status` 正是「第二供應商合格了沒」的追蹤器——
**填得最多（167 筆）卻沒接到任何地方**。8.2 第三層要接的就是它。
