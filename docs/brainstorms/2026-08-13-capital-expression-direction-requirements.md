---
date: 2026-08-13
topic: capital-expression-direction
status: direction-frozen（方向已定案；實作未開始）
承接: 2026-08-02-confidence-axes-restructure §6「未實作」、§8.3「判準」
---

# 資本表達層的方向定案（2026-08-13）

> **起因：** 使用者問「AXTI／LITE／COHR／SIVE 兩週漲 30%，是什麼讓我們沒有認為它當時的
> 價值可以入場？我們的系統缺了什麼？」以及後續三個追問：「我們到底有幾條決策規則？」、
> 「取最小值是 argument 太多還是實作缺陷？」、「你怎麼判斷一個 blocker 是真的有用的？」
>
> **本檔的角色：** 這是**方向文件**，不是診斷文件。診斷已經寫過四次（見 §0）。
> 這一份要做的是把方向凍結、把今天的數字凍結，讓未來的 audit 能做 diff 而不是做判斷。

---

## 0. 為什麼這不是第五份診斷

同一個結論已被正確寫下四次：

| 時間 | 位置 | 寫了什麼 | 之後發生什麼 |
|---|---|---|---|
| 2026-08-02 | `confidence-axes` §2–§4 | 五軸全在問「證據多強」、取 min 等於最弱文件決定一切 | 只改了 `coverage_cap` 一行 |
| 2026-08-02 | `blocker_severity.py:37-39` 註解 | 「研究不完整**不該歸零資本**…等到每一項都補齊，alpha 通常也已經被市場定價完畢」 | 分類只接到 `coverage.blockers` |
| 2026-08-08 | `confidence-axes` §8.2 | `execution_intent: research` 是 9/9 的瓶頸 | paper 接通了（0.1% NAV），live 沒有 |
| 2026-08-08 | `confidence-axes` §8.3 | 「改完之後，現有 cohort 有幾個的 `supported_range` 真的變了？答案是 0 就代表沒改到 binding constraint」 | 五天後新增 14 筆 decision，live range 仍全為 0 |

**這四次的共同形狀：診斷正確 → 局部修正正確 → 沒有持續量測 → 帳面「已實作」而實際供給為零。**
這是 L13 的操作版，也是 `blind-spot-audit` 的 D14 lens。

**所以本檔不重複診斷。** 本檔只做三件事：宣告方向（§1）、凍結 baseline（§2）、
定義檢驗方式（§6）。新的實測發現放 §3，是為了支撐方向，不是為了再診斷一次。

⚠ **`2026-08-02-confidence-axes-restructure-requirements.md` 已達 61KB 且仍在成長。**
它已經變成「正確診斷的堆積場」。本檔刻意保持短；要加新一輪脈絡時，先問這一輪有沒有
改變任何一筆現有資料——沒有就不要加章節，加一行到 §2 的 baseline 表即可。

---

## 1. 方向宣告

> 這是本檔最重要的部分。未來的 audit 要檢驗的是「有沒有往這些方向走」，
> 不是「有沒有做完清單」。清單會過時，方向不會。

### D1 — 系統的目的是投資獲利，研究是手段不是目的

「Engine A/B/C 研究輸入 + Engine D 決策責任」的定位沒有變，但**優先序要明確**：
研究品質好而資本表達不了，等於零。反過來，資本表達得了但研究是垃圾，是負值。
兩者都要，但**當兩者衝突時，不得再用「研究還不完整」當作不表達的理由**——
那正是過去四次失效的機制。

判準：使用者的感受「我們搞得有點像在做科研，不是為了投資獲利」是**有效訊號**，
不是情緒。它對應的可量測事實是 §2 的 baseline。

### D2 — 不確定性用尺寸承擔，不用 gate 禁止參與

這句話已經寫在 `blocker_severity.py:37-39`，但只接到了一條路徑。方向是把它變成
**全系統的預設**：任何「功課沒做完 / 資料還沒到 / 對方不揭露」都只能縮小尺寸，
不能歸零。

**下限不是 0。** 階梯的最低階若是 0，配上 `min()`，任一軸缺席就全滅——這是數學上的
必然，不是參數沒調好。

### D3 — 診斷與閘門分離

49 種 blocker 全部保留當**診斷訊息**（它們讓今天這場對話成為可能，這是真價值）；
但**只有講得出因果機制的才有資本否決權**。

機制的定義：能用一句話說明「這個 blocker 亮起時，這檔標的更可能變壞」。
講不出來的，是行政流程假扮風控。

預期落點：可歸零的**不超過 8 個**（現況：49 個裡有 44 個是資料／管線／研究進度，
只有 `policy_cap` 4 ＋ `execution` 1 是真正的風險判斷）。

### D4 — 證據標準校準到個人投資者可達成的補救手段

L8（來源獨立性：供應商自報不算獨立佐證）這個**原則保留**，但補救標準要重訂。

現況實例：`source_reliability` 要求「Casela 或 Coherent **客戶端獨立證實**採購」。
上市公司幾乎不會在財報裡點名基板供應商——這不是「很難達成」，是**構造上不可能達成**。
機構用 channel check／專家網路／付費供應鏈資料庫解決；個人投資者沒有這些。

**正確結論不是降低 L8，是：對方永遠不會揭露 → 該軸永久停在 tier-2 → 永久縮小尺寸，
而不是永久歸零。**

附帶的不對稱：機構的證據標準有一部分服務的是**可辯護性**（要向投委會／合規解釋），
而非決策品質。本專案是單人自用，沒有投委會。**稽核完整性有價值且應保留，
但稽核用的欄位不該有資本否決權。**

### D5 — alpha 需要 baseline，就像 beta 已經有的那樣

`AGENTS.md`（2026-08-01 定案）：beta 的 `signal.baseline_pace` 是**不受訊號影響的例行
投入下限**，訊號只能在其上加碼；理由是三次回測證明以訊號 gate 投入輸給無腦定投 8.5%。

**同一個修法形狀在 alpha 側從未 port 過來。** alpha 只有 gate，沒有 baseline。
方向：通過 thesis 層閘門（Lane Memo PASS ＋ variant perception ＋ 財務核驗五項）的標的
應有一個**非零且在經濟上有意義的**下限尺寸，由真正的風險判斷（D3 的那 ≤8 個）與
資本上限決定，不由資料完整度決定。

⚠ **baseline 的具體數字是使用者的決定，本檔不預設。** 現況 0.2% 與 policy 允許的
單筆 5% 之間有很寬的中段。

### D6 — 任何機制未經量測不得享有默認信任，**包括 gate 本身**

2026-08-01 對技術訊號執行過這條（0 勝 3 敗，於是訊號被移出資本路徑）。
**同一標準必須套用到 gate。** 目前 49 個 blocker 沒有一個被驗證過——它們享有的信任
與 RSI 在被回測打爛之前一模一樣。

推論：**在 outcome 量測建立之前，不得以「更嚴格比較安全」為由新增或收緊任何 gate。**
fail closed 是好的預設，但它不是免於驗證的理由。

### D8 — Gate 與語言處理要有分工，不要被自己的 gate 卡死（2026-08-14 使用者定調）

> 「不全然相信 gate，我們只相信 gate 的存在意義對我們的目標有幫助。如果不明確，
> 我們 leverage LLM 的語言處理能力去解決，不必被自己的 gate 卡死。」

多數 gate 實際上是用**機械代理**（字串相等、日期比較、集合包含）去回答一個**語意
問題**。代理答錯時，被擋下的是格式而不是風險——實測 22 次的引用格式歸零就是這個
形狀。**gate 的正當性來自它對目標有幫助，不來自它存在或它比較嚴格。**

分工線：**語意交給語言處理，權限永遠 deterministic；LLM 可以解析與提議，不可以授權。**
順序固定「先解析身分 → 再查權限」，反過來就是讓引用去尋找能通過的權威（L8／L11）。
且**放寬解析必須伴隨判準變嚴**——分開之後每一邊都能比混在一起時更嚴（L12）。

完整判準已升格為 `AGENTS.md` **L15**（本檔 §7 的原則：實測驗證過的才升格為政策；
本條有 2026-08-13～14 的實測與落地實作，故升格）。

### D7 — 順序不可顛倒：先量測，後放閘

現行設計有一個真實優點：它永遠不會因為爛研究賠錢——因為它永遠不下注。
**先放寬 gate、後建量測 = 拆掉煞車而沒裝儀表板，嚴格來說比現狀更糟。**

同時要誠實說出這個交換放棄什麼：**訂 baseline 部位意味著會在事後證明錯的 thesis 上
真的虧錢。** 這是正確的交換，但必須是被明說的選擇，不能夾帶通過。

---

## 2. Baseline 凍結（2026-08-13）

> 未來的 audit 拿這張表做 diff。**不要憑感覺判斷「有沒有往對的方向走」——比數字。**

### 2.1 資本表達

| 指標 | 2026-08-13 值 | 想要的方向 |
|---|---|---|
| `system_decisions` 總數 | 72 | — |
| `live_supported_range` 非零筆數（既有 frozen decision） | **0 / 72** | 依 point-in-time 契約**不回寫**，此列永遠是 0 |
| ├ 以真實 calculator 對既有 context 重算（§4 第 3 項後） | **0 → 8**（54 筆可重建者；19 筆 context 無法重建） | 新產生的 decision 應非零 |
| ├ live binding constraint 分布 | 舊：`live_lane_blockers` 71/72（近乎全部）<br>新：`live_lane_blockers` 44、**`weakest_axis` 31**、`coverage_gate` 19、`execution_adv_1pct` 12 | 應為信心或風險，不是管線 |
| `axis_ceiling` 的歷史值域 | `{0.0: 37, 0.002: 35}`，**從未達 0.005** | 出現 > 0.002 |
| `action` 分布 | `DATA_NEEDED` 59、`HOLD_PAPER` 7、`FUND_PAPER` 4、`SHADOW_ONLY` 2 | `DATA_NEEDED` 佔比下降 |
| paper 實際部位 | 4 檔 × 0.1% NAV（META／AXT／AAOI／SIVE） | 單筆有經濟意義 |
| 已量測 outcome（`outcome_envelopes.absolute_return` 非 null） | **0 / 8** | > 0 |
| ├ 唯讀報表已算出的報酬（不寫 Decision Store） | **7 / 7**（2026-08-13，§2.7） | — |
| `live_choices` / `live_execution_reports` / `prepared_actions` | 0 / 0 / 0 | — |

### 2.2 哪些 constraint 真的 binding（72 筆）

```
live_lane_blockers    71   ← 資料／intent
paper_lane_blockers   59   ← 資料／intent
paper_context         59   ← 資料
weakest_axis          48   ← 研究完整度
coverage_gate         34   ← 研究完整度
execution_adv_1pct    24   ← 流動性（真風險）
single_probe_cap       0   ← 0.5% 上限，從未 binding
single_position_cap    0   ← 5% 上限，從未 binding
probe_book_remaining   0   ← 2% 總量上限，從未 binding
```

**三個真正的資本上限一次都沒有 binding 過。100% 的歸零由資料與研究完整度造成。**

### 2.3 Blocker 觸發率與清除率

清除率＝同一 cohort 連續 reassess 之間被清掉的比率（AXTI 重評 23 次、AAOI 17、SIVE 9、META 8）。

| blocker | 觸發率 | 清除率 | 性質 |
|---|---|---|---|
| `execution_intent_research_only` | **80.6%** | 10% | 牆（且機制欄為「無」） |
| `holdings_unconfirmed` | **66.7%** | 16% | 牆（且機制欄為「無」） |
| `disproof_missing` | 37.5% | **55%** | 真閘門 |
| `financial_runway_manual_required` | 34.7% | 11% | 牆 |
| `counter_path_missing` | 26.4% | 14% | 牆 |
| `catalyst_missing` | 25.0% | **55%** | 真閘門 |
| `execution_intent_paper_only` | 16.7% | **0%** | 牆 |
| `identity_unresolved` | 8.3% | **0%** | 致命，正確 |
| 行情品質類（ticker／price／unit…） | 6.9% | **60%** | 真閘門 |

### 2.4 軸的等級分布（72 筆）

```
valuation_payoff        unknown 33 / bounded 39 / corroborated  0   ← 從未 corroborated
source_reliability      unknown 19 / bounded 52 / corroborated  1
commercial_maturity     unknown 24 / bounded 47 / corroborated  1
financial_resilience    unknown 20 / bounded 45 / corroborated  7
technical_causal_link   unknown 22 / bounded 18 / corroborated 32
```

`corroborated + missing_data` 的組合出現 **0 次**——不是沒遇到，是評估者已學會迴避
（見 §3.3）。

### 2.5 事件本身（Engine C `financial_snapshots`）

| Ticker | 07-28 | 08-13 | 漲幅 | forward P/E |
|---|---|---|---|---|
| AXTI | $47.88 | $78.47 | **+63.9%** | 61.5 → **35.3（變便宜）** |
| AAOI | $97.82 | $138.08 | +41.2% | 20.5 → 30.0 |
| SIVE.ST | 30.70 | 42.52 | +38.5% | n/m |
| COHR | $271.31 | $355.64 | +31.1% | 32.7 → 42.5 |
| LITE | $711.96 | $932.47 | +31.0% | 38.8 → **30.1（變便宜）** |

**兩檔在上漲 30–64% 的同時 forward P/E 反而下降**——獲利預估上修快於股價。
「已被 price in」的敘事式判斷在此被實時證偽（但 n=2，見 §5 待驗證項）。

### 2.7 §4 第 1 項結果：若今天結算（2026-08-13）

`scripts/outcome_if_settled_today.py`（唯讀，不寫任何 authority）。錨點 = Shadow 價格
（Decision Store 的追蹤起點 authority），現價 = provider 最新已收盤 bar，兩端經
`identity.currency` 正規化成結算幣別。

| 標的 | 錨點日 | 絕對報酬 | QQQ | **超額（QQQ）** |
|---|---|---|---|---|
| AXTI | 07-28 | +83.5% | +7.1% | **+76.4%** |
| AAOI | 07-24 | +37.9% | +5.8% | **+32.1%** |
| SIVE.ST | 07-23 | +35.4% | +4.6% | **+30.9%** |
| IQE.L | 08-03 | +21.6% | +3.4% | **+18.2%** |
| COHR | 07-21 | +12.1% | +2.1% | **+10.0%** |
| LITE | 07-21 | +11.3% | +2.1% | **+9.3%** |
| META | 07-31 | +4.0% | +5.2% | **−1.2%** |

**7 / 7 全部可量測。6 個 `unavailable` shadow 的 cohort 仍無錨點。**

**這改變了什麼：** 系統的**選標的**能力第一次有了證據——7 檔有 6 檔跑贏 QQQ，中位超額
約 +30%，且不是單一標的帶動。**這使「gate 擋掉的是雜訊」這個辯護站不住**：被擋在
0.2% 的那批，事後看方向是對的。同時它也不構成「放寬 gate 就會賺」的證明——n=7、
單一時間窗、全部同屬 AI 光通訊主題（§5 的共移問題），且**這是追蹤起點而非建議買點**。

⚠ **`outcome_envelopes` 仍是 0/8，本項刻意不寫入**：寫 outcome 需 `close_probe`，而
關閉 cohort 會關掉仍在跑的 thesis（AXT 的 expiry 比催化劑早三個月，見 `confidence-axes`
§10.1）。量測與退場必須分開——**這正是 §2.1 拆成兩列的原因**。

**同時撞出一個 Engine C 資料問題**（已進 ROADMAP 未排程）：`financial_snapshots.snapshot_date`
不是行情交易日，而是跑 ETL 的日期——收盤後跑的批次被標成隔天，盤中跑的存盤中價。
一個欄位三種語意（L12）。本報表因此改用 provider 的收盤序列取現價。

### 2.8 §4 第 4 項：`unknown` 的兩種語意（2026-08-14）

重跑 2026-08-08 §8.2 指定的那張表（該節明訂「再有人想動 `axis_ceilings.unknown`，
先重跑一次上表」）。結論：**該節的禁令維持有效，但它的理由是錯的。**

原理由是「unknown 只集中在未上市的 Agility」。73 筆重跑後不成立——LITE 5.0/5、
NVDA 5.0/5、COHR 4.0/5 都是上市公司。真正的分布是：

| 類別 | 筆數 | 該不該歸零 |
|---|---|---|
| 五軸全 unknown（＝還沒做研究） | 18 | ✅ 該。沒有評估就沒有東西可 size |
| 部分 unknown（做了研究但某軸缺） | 20 | ⚠ 這才是 `min()` 傷害的地方 |

而那 20 筆裡的 33 個 unknown 軸，**22 個是被配線改寫的，只有 11 個是研究者宣告的**：

```
被改寫 22：valuation_payoff 10、technical_causal_link 5、commercial_maturity 4、
           source_reliability 2、financial_resilience 1
宣告   11：valuation_payoff 6、commercial_maturity 3、financial_resilience 2
```

逐筆追下去，改寫有兩個成因，**都不是「我們不知道」**：

1. **引用字串格式不符。** 研究者寫 `yfinance://history`，index 的 key 是
   `yfinance://history/AAOI`。少一個 ticker 後綴 → 整筆決策資本歸零。
2. **判準是 `any(失敗)` 而非「至少一個合格」。** META 的 `technical_causal_link`
   有 `co:meta` 與 `meta_vistara_isca_2026` 兩個合格引用，只因多附一個
   `prod:vistara` 就整軸歸零；AXTI 的 `financial_resilience` 有合格的
   `yfinance.info`，卻因多附兩份 8-K 脈絡而歸零。

**因此不動 `axis_ceilings.unknown`**（宣告的 unknown 歸零是對的），改修上述兩點：
引用先做**無歧義**解析（exact → 去尾斜線 → 唯一前綴；兩個以上候選就不解析，
寧可報 mismatch 也不挑一個），且只要有**至少一個**合格引用即成立；不合格的改列
`context_only_refs` 現形供稽核。**零個合格引用仍歸零**——那才是 authority
laundering。⚠ 解析只認身分不看 authority，順序固定「先解析身分 → 再查 authority」，
否則等於讓引用去尋找能通過的權威（L8／L11）。

### 2.6 pipeline

`pending` 33、`triaged_go` **62**（最舊 2026-07-25，19 天）、`applied` 22、
`parked` 81、`triaged_no_go` 396。`drain_limit_per_run` = 5。

---

## 3. 2026-08-13 的新發現（支撐方向，不重複診斷）

### 3.1 嚴重度分類沒有接到真正 binding 的兩行

`decision_lab/sizing.py:301`：
```python
    if paper_blockers:
        trace.append(_constraint("paper", "paper_lane_blockers", 0.0, ...))
        paper_max = 0.0
```
`decision_lab/sizing.py:386`：
```python
    live_range = (live_floor, live_max) if not live_blockers else (0.0, 0.0)
```

**兩行都沒有經過 `fatal_blockers()`。** 任何 lane blocker，不分嚴重度，無條件歸零。

`fatal_blockers()` 全 repo 有 6 個呼叫點（`coverage.py` ×3、`sizing.py` ×1、
`store.py` ×1、`action_card.py` ×1），**全部套在 `coverage.blockers` 上**。
分類被套用在 binding 34 次的路徑，沒被套用在 binding 59 次與 71 次的兩條路徑。

這正是 §8.1 修過一次的同一形狀——當時補了 coverage／store／action_card，**漏了 sizing
自己的 lane 那兩行**。

### 3.2 兩套 blocker 分類系統互不知道

- `config/decision_blockers.json`：49 種（另 2 已淘汰）、12 個 category、3 個
  `resolution_mode`。細緻，**給人看的**。
- `blocker_severity.INCOMPLETE_COVERAGE_BLOCKERS`：硬編碼 4 個 pattern ＋ 5 個
  checklist 前綴，二元。**決定資本的**。

兩者不互相引用。又一次 L12（一個概念兩套表示，下游被迫二選一）。

### 3.3 `min()` 的問題不是 argument 太多

5 個 argument 不多。缺陷是**三件事同時成立**，任一單獨出現都還能活：

1. **階梯最低階是 0。** `unknown → 0.0` ＋ `min()` ＝ 任一軸缺席就全滅。
2. **最高階拿不到。** `sizing.py:110`：`corroborated` 要求 `missing_data == []`，
   而誠實的研究永遠有待補項。所以三階梯實際只有兩階：0 或 0.002。
   **非單調**——宣告較高信心並列出待補項（ceiling 0）比保守宣告 `bounded_hypothesis`
   並列出同一批待補項（ceiling 0.002）更差。**誠實被懲罰**，實測 0 次出現該組合即為證據。
3. **五軸不可通約。** 混了三個不同問題：證據多強（`source_reliability`／
   `technical_causal_link`）、生意多好（`commercial_maturity`／`financial_resilience`）、
   價格多好（`valuation_payoff`）。對三類取 min 是範疇錯誤——「好生意爛價格」與
   「爛生意好價格」會被 min 成同一個答案，但該做的事相反。

第 3 點與 2026-08-02 §2 的診斷一致，但當時的處方（合併成兩軸）**沒有處理第 1、2 點**，
而那兩點才是讓 ceiling 恆為 0.002 的直接原因。

### 3.4 probe sandbox 變成了整棟建築

`config/investment_policy.json` 同時住著兩套 sizing：

- `conviction_coefficients {3: 0.08, 4: 0.10, 5: 0.15}`，由 `single_position_nav_cap: 0.05`
  壓到 5%。唯一消費者是 `paper_portfolio/ledger.py`——已被 `decision_lab` 取代的舊模組，
  `library/private/` 下沒有它的狀態目錄。
- `probe_lane.axis_ceilings.corroborated: 0.005` ＋ `probe_book_nav_cap: 0.02`。現行。

**歷史推測（可證偽）：** 原始設計要做 5% 的真實部位；重寫成 `decision_lab` 時先蓋了
一個有完整稽核的 probe sandbox；然後 sandbox 變成整棟建築。**沒有任何一次是有人判斷
「單筆上限應該是 0.2%」——它是架構升級的副作用。**

反證方式：若能找到明確決定把上限降到 probe 尺度的紀錄（plan／brainstorm／commit
message），則本節推測作廢，該尺度是刻意的。

### 3.5 判斷 blocker 有沒有用的三個測試（不需 outcome）

| 測試 | 判準 | 為什麼有效 |
|---|---|---|
| **恆亮** | 觸發率接近 100% → 零鑑別力 | 永遠亮的閘門不篩選任何東西，定義上如此 |
| **不會滅** | 清除率接近 0 → 那不是閘門，是牆 | 閘門的行為是「亮起 → 做功課 → 滅掉」 |
| **講不出機制** | 說不出「亮起時標的更可能變壞」→ 行政流程假扮風控 | 成本最低，今天就能對 49 個全跑一遍 |

第四個測試——**「會滅但沒用」**（亮起、清除、而清除與未清除兩組的結果分布相同，
即 RSI 那種失效）——**需要 outcome，現在測不了**。這是 §4 第 1 項排第一的理由。

**反例（避免學到錯誤教訓）：** SIVE 的 audit hold 擋掉了 +38.5%，長得跟沒必要的牆
一模一樣。它不是——因果機制存在（PCAOB 重編＋董事會出走＋做空報告 → 所有財務數字
可能失效）且損失分布不對稱。**判準不能是「被擋掉的東西後來漲了沒」，而是
「這個 blocker 的存在是否預測了不同的結果分布，特別是左尾」。**

---

## 4. 下一步（含驗收條件）

每一步的驗收條件都是「**現有資料有幾筆真的變了**」，不是「這一步有沒有執行成功」。
這是 §8.3 的判準，本檔把它變成每一項的必填欄。

| # | 動作 | 驗收條件（可證偽） | 依賴 |
|---|---|---|---|
| ~~**1**~~ ✅ | **對 7 個有 shadow 錨點的 cohort 補跑 outcome 量測** | ✅ **7/7 可量測**，AXTI +83.5%（見 §2.7）。`scripts/outcome_if_settled_today.py` | 無 |
| ~~**2**~~ ✅ | **逐項分類 blocker** | ✅ 使用者 2026-08-13 核可。67 條登記：`fatal` 27 ＋ `fatal(live)` 7 ＋ `fatal(paper)` 1、`sizing` 24、`diagnostic` 8；2 條已淘汰刪除。可歸零仍是 **8 個概念**，code 數較多是因為 identity 家族與 `market_` 家族被拆開 | 無 |
| ~~**3**~~ ✅ | **把 lane blockers 接進 `fatal_blockers()`** 並讓兩套分類系統合一（§3.2） | ✅ 真實 calculator 全量重算：**live 非零 0 → 8**（54 筆可重建者），binding 由 `live_lane_blockers` 71/72 變成 `weakest_axis` 31 為主。`severity` 現住 config，`blocker_severity.py` 讀它，硬編碼 frozenset 消滅 | 2 |
| ~~**4**~~ ✅ | **修 §3.3 的第 2 點＋引用解析**（第 1 點經重跑資料後**否決**，理由見下） | ✅ 重算：`axis_ceiling` 0 的筆數 **23 → 17**（6 筆由 0 變 0.002）。⚠ 原驗收條件「出現 > 0.002」**不可能由歷史資料成立**——那需五軸全 `corroborated`，而 `corroborated + missing_data` 歷史上出現 0 次（評估者早已學會迴避）。單調性改由 `tests/test_probe_sizing.py::test_declaring_corroborated_never_yields_less_than_bounded_hypothesis` 鎖住 | 3 |
| **5** | **決定 alpha baseline 尺寸**（使用者決定，見 D5） | — | 1、3 |
| ~~**6**~~ ✅ | `lifecycle.json` 加 `catalyst_checkpoints`，到期取 `min(cadence, 最近催化劑)` | ✅ AXT 生效複查日 **2026-11-15 → 2026-10-30**（Q3 財報）。新增 `thesis/lifecycle_schedule.py` 為唯一判準——先前 `crons/thesis_freshness_check.py` 與 `query/health_audit.py` 各有一份只讀 `next_check` 的實作。推估日期照樣排程但標明 `date_confidence` 與 `basis`，不得讓推估看起來像已公告 | 無 |

**第 1 項必須排在第 3、4 項之前**（D7：先量測後放閘）。第 2 項可與第 1 項並行，
因為它只產出待核可清單、不改行為。

---

## 5. 明確待驗證，尚不得當結論

- **`valuation_payoff` 這一軸到底有沒有用。** §2.5 顯示 AXTI／LITE 被判「已被 price in」
  而 forward P/E 反而下降——但 **n=2**。完整檢驗方式：取出所有歷史
  `valuation_payoff` 判斷，對照該日之後 30 天實際報酬，比較「判貴」與「判不貴」兩組。
  資料已足夠（每檔 20–22 筆 `financial_snapshots`）。**在跑之前不得視為已證偽**——
  這正是 2026-08-01 訊號那三次做對的事。
- **§3.4 的「sandbox 變建築」是推測**，反證方式見該節。
- **§2.6 的 pipeline throughput 是否為真問題。** 需先算 `triaged_go → applied` 的實際
  延遲分布；若中位數 < 3 天，此項應撤回。
- **主題／籃子層級曝險。** `config/themes.txt` 的 `cpo:` 明列 COHR／LITE／AVGO／NVDA，
  但那是 Engine B 的 weekly topic discovery 輸入，Engine D 無對應概念；
  且 factor caps 已於 2026-07-29 整套移除（`config/decision_blockers.json:291` 註記）。
  **最小版提案是唯讀共移警示（只呈現，不動 sizing）**，但在 outcome 量測前無法判斷
  它是否值得做。

---

## 6. 這個 flow 本身的失效模式與防呆

使用者提出的 flow：**寫方向 → 做 → 回來用 `blind-spot-audit` 檢驗有沒有往方向走。**

方向正確，但**它五天前就以 §8.3 的形式存在過，然後失效了**。失效原因不是判準錯，
而是：

> **檢查點住在一份要人主動想起來去讀的文件裡。**

這是 D16（只有入口沒有出口）的變體——入口是使用者的一次動作，出口卻也要求使用者記得。

### 防呆（必須與 §4 一起做，否則本檔會變成第五份被堆積的正確診斷）

1. ✅ **daily brief 增加兩個常駐計數器**（2026-08-14 已實作）：
   ```
   - 資本表達：非零 live 區間 0/73 筆｜已量測 outcome 0/8 筆
     ⚠ 系統至今從未輸出過可入場區間　⚠ 判斷準不準仍無法用證據回答
   ```
   `store.capital_expression_counters()` ＋ `brief.render_today_markdown`。
   只要還是 0，每天都會看見，不需要任何人記得；一旦有產出，警語自動消失
   （要刺眼到不被略過，但不該每天喊）。這兩個數字直接對應 §2.1 的前兩列。

   ⚠ **計數器讀的是既有 frozen decision，依 point-in-time 契約不回寫**，所以
   `live_range_nonzero` 會維持 0 直到**新的** decision 產生。這是刻意的：它量的是
   「系統實際輸出過什麼」，不是「如果重算會是什麼」。

   **2026-08-14 這個 caveat 立刻造成一次假陰性，已修：** 一個 daily session 讀到
   「0/73」後推論「gate 還是壞的，做完那三件事若仍是 0 就停下來重新診斷」。它的紀律
   是對的（正是 L14 第 1 條），但那個 0 不會動——**不是因為修法無效，是因為既有
   decision 永不回寫**。計數器把「機制從未產出」與「gate 改過但尚無新 decision」壓在
   同一個 0 上——**我自己犯的 L12**。
   已拆開：`calculator_version` bump 到 `probe-limit-v3`，計數器另回
   `decisions_current_calculator` 與 `live_range_nonzero_current`，brief 在現行骨架
   尚無 decision 時明說「此數字現在不代表修法有效或無效」。
   同時修掉一個真的契約違反：**今天改了 sizing 語意卻沒 bump `calculator_version`**，
   等於讓同一個版本標籤底下有兩套規則。

2. **audit 檢驗時比 §2 的表，不比感覺。** 「有沒有往想要的方向走」＝ 這些數字有沒有動。
   若一輪工作後 §2.1 沒有任何一列改變，那一輪就是**沒改到 binding constraint**，
   不論改動本身多正確。

3. **本檔不接受「加一個章節」式的更新。** 有新一輪脈絡時，先問：這一輪改變了 §2 的
   哪一個數字？沒有 → 加一行到 baseline 表；有 → 更新該列並註記日期。
   `2026-08-02-confidence-axes` 之所以膨脹到 61KB，是因為每一輪都加章節而沒有更新任何
   數字。

---

## 7. 與既有文件的關係

- **`AGENTS.md`** 仍是政策 SSOT。本檔的 D1–D7 是**方向**，尚未成為政策；
  §4 執行到有實測結果後，值得升格的部分再寫進 `AGENTS.md`。
  **不要在實測前把方向寫成政策**——那正是 gate 當初被引入的方式。
- **`2026-08-02-confidence-axes-restructure-requirements.md`** 的 §4（三類軸：
  否決／信心／賠率）方向仍然有效，且與本檔 D2／D3 一致。但該檔 §7 的判準
  「先跑一兩週看樣本品質」已於 §8 被執行並得到 0/9；**本檔 §4 的順序取代它**。
- **`docs/ROADMAP.md`** 的「已 brainstorm 但未實作」段落應在 §4 開工時同步更新，
  指向本檔而非只指向 `confidence-axes`。
- **`skills/blind-spot-audit`** 的 D 類 lens 在本輪全部命中（D13 空機制／D14 修法有效性／
  D15 一表兩義／D16 無出口／D17 可重建卻凍結），無需修改審查表。
