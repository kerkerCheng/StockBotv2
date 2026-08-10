# Confidence 五軸重構需求（2026-08-02）

> 起因：使用者在 AXT 決策複查後提出兩個問題——「我們很常卡在 source gate，但如果 gate
> 真的過了，alpha 是不是也沒了？」以及「是不是該用減法：有人提出觀點，如果沒有任何證據
> 否定它，就假設有機率成立？」本檔記錄診斷、被否決的方案、被採納的方向，以及已實作到
> 哪一步。要動工先讀完本檔，不要重新發明。

## 1. 觸發本次討論的實測

AXT（AXTI）2026-07 的時間線：

| 日期 | 事件 | 股價 |
|---|---|---|
| 2026-07-26 | 與 Lumentum 簽六年 InP 產能保留協議 | — |
| 2026-07-29 | 8-K 揭露該協議（首期 US$43.5M deposit） | — |
| 2026-07-30 | Q2 財報：營收 +164% YoY、GAAP 毛利率 44.9% | $36.97 |
| 2026-08-02 | 系統首次把上述全部吸收進決策 | $60.43 |

三個交易日 +63%。而系統在 2026-08-02 完成五軸重評後的結論仍是 `DATA_NEEDED`、
supported range `(0, 0)`。**證據補齊的速度慢於價格重定價的速度**，這不是研究做得不夠
勤，而是 gate 的結構決定的。

## 2. 診斷：五軸其實是同一種東西

`decision_lab/sizing.py` 的五軸——`source_reliability`、`technical_causal_link`、
`commercial_maturity`、`financial_resilience`、`valuation_payoff`——全部在問同一個問題：
**證據有多強**。沒有任何一軸在問「如果對能賺多少、如果錯會賠多少」。

後果有二：

1. **高度相關 + 取 min = 最弱那份文件決定一切。** 一份好文件同時抬高數軸，一個缺口同時
   壓低數軸。AXT 的 `technical_causal_link` 是 `corroborated`，但因為取最小值，它對結果
   的貢獻是零——這個軸在實務上只有拖累的可能、沒有幫助的可能，除非它是最弱的一個，
   而它幾乎永遠不會是。
2. **系統只能用「不參與」來表達不確定性。** 沒有賠率維度，就沒有別的旋鈕可以轉。

`valuation_payoff` 名字像賠率，但它的等級一樣是 `unknown` / `bounded_hypothesis` /
`corroborated`，實際衡量的仍是「估值證據夠不夠」，不是「賠率好不好」。

## 3. 被否決的方案：「沒有否證就假設成立」

使用者提出的減法框架方向正確（不該等證據完備），但**具體做法會壞在否證證據的供給
不對稱**：

- 沒有公司會發新聞稿說「我們沒有跟 AXT 簽約」或「我們的良率沒有改善」。
- 空頭報告極罕見——要花錢做、還可能被告。

因此「找不到否定證據」在絕大多數情況下不帶任何資訊：它反映的是這個世界不生產那種
文件，不是反映主張的真假。實務上這個框架會退化成**把「我沒查」誤讀成「查不到反面」**。

Sivers 是完整的反例：若沒有 Ningi 那份罕見的做空報告，它所有說法都會是「沒有被否定」。
而實際情況（公司自揭 going-concern material uncertainty、2023–25 PCAOB 重編、董事會
出走）是主動追一手文件才挖出來的，不是否證證據自己找上門。參見 L11（自己引用的事實
要套跟圖裡 claim 同一套追源紀律）與 L8（來源獨立性：供應商自報不算獨立佐證）。

## 4. 採納的方向：把「證據強度」與「部位大小」解耦

不是「證據不夠就不能動」，而是「證據不夠就只能小注，但可以動」。對應的結構是把現在
的五軸拆成三類，各用不同的數學：

### 4.1 否決類（二元，一票否決，不打折）

會歸零的東西：going concern、審計保留意見、財務造假、流動性斷裂、監管禁令、公司身分
無法解析。這些不是「還沒被證實的好消息」，而是「還沒被排除的災難」，賠付結構不對稱。

現況：散落在 `source_reliability` 與 `financial_resilience` 裡，與時效性的缺口混在一起。

### 4.2 信心類（序數，取 min）

證據強度，即現在五軸做的事，但可收斂成兩軸：

- **主張可信度**：`source_reliability` + `technical_causal_link` + `commercial_maturity`
  合併，三者本來就在問「這件事是真的嗎」。
- **財務承受力**：公司會不會在 thesis 兌現前先死。

### 4.3 賠率類（連續數值，乘法）

目前**完全不存在**的維度：如果對能賺多少倍、如果錯會賠多少。這應該是乘數而非 gate。

最終部位 = 賠率決定的基準尺寸 × 信心折扣，再被否決類一票否決。

## 5. 已實作（2026-08-02）：coverage 嚴重度分類

沒有一次動軸的結構，先改真正把資本打成零的那一行。原本：

```python
coverage_cap = probe["single_probe_nav_cap"] if coverage.status == "analyzable" else 0.0
```

只要有任何一個 coverage blocker，資本上限就是 0，五軸算出的 `axis_ceiling` 完全不作數。
AXT 就是被單一個「算不出 runway」打成零的。

改法是把 blocker 分成兩類（`decision_lab/coverage.py` 的 `fatal_blockers`）：

- **致命（仍歸零）**：`identity_unresolved`、`graph_company_missing`、`best_source_missing`、
  `causal_path_missing`、`financial_missing/unavailable/quarantined`、`disproof_missing`、
  `expiry_invalid`。這些讓決策無法稽核或事後檢驗。
- **研究不完整（只降尺寸，讓 `axis_ceiling` 生效）**：`independent_source_missing`、
  `counter_path_missing`、五項財務核驗清單的各種缺漏、`financial_runway_manual_required`、
  `catalyst_missing`。

兩個判準值得記住：

- **`disproof_missing` 刻意留在致命類。** 不是因為它是災難風險，而是 L7（thesis 生命週期：
  disproof 條件要附核查頻率與觸發後 48 小時動作）的整個紀律建立在它上面。允許沒有證偽
  條件就下注，等於允許一個永遠不會響的警報。`catalyst_missing` 則不致命——可以先小注
  再補。
- **未分類的 blocker 一律 fail closed。** 新增 blocker 時 `tests/test_coverage_severity.py`
  會失敗，強迫做出分類決定，而不是靠預設安靜放行。

實測效果：AXT 的 `coverage_gate` 從 `cap=0.0 / blocked` 變成 `cap=0.005 / available`，
`axis_ceiling` 0.002 得以生效。改動不碰任何軸的定義，不影響既有 frozen decision。

## 6. 未實作，以及動工前要知道的事

### 改動成本（2026-08-02 查證）

- **數值已可 config。** `config/investment_policy.json` 的 `probe_lane` 已含 `axis_ceilings`、
  `rubric_version`、`calculator_version`。調數字零程式改動。
- **軸定義寫死但範圍窄。** `decision_lab/sizing.py` 的 `AXES`、`LEVELS`、
  `AXIS_REFERENCE_AUTHORITIES`；引用處只有它自己、`decision_lab/workflow.py` 一處迴圈、
  與測試。**`skills/` 完全沒有寫死軸名**，改軸不波及研究流程文件。
- **不需要資料遷移。** 每筆決策凍結自己的 `rubric_version` 與 `policy_version`，舊決策永遠
  用舊骨架解讀，新舊共存。

⚠ [`docs/solutions/architecture-patterns/closed-vocabulary-registry.md`](../solutions/architecture-patterns/closed-vocabulary-registry.md)
把五軸／三級列為「刻意凍結（不要打開）」，理由是「評分骨架，已凍進所有既有 decision
payload」。**該理由已因版本化機制而失效**，但登記表尚未更新。真正該保持嚴格的是
`AXIS_REFERENCE_AUTHORITIES`（它擋的是「拿 Engine A 文件冒充 Engine C 財務證據」），
不過嚴格與 config 化並不衝突——`config/authority_tokens.json` 已是先例。動工時一併修
登記表，否則下一個 session 會以為不能碰。

### config 化的邊界

沿用專案既有的 taxonomy 對 contract 判準：

- **可 config（會隨策略演化）**：軸有哪些、每軸接受哪些 authority、各級 ceiling、賠率如何
  換算成基準尺寸。
- **不該 config（改了等於換系統）**：聚合方式（取 min 還是相乘）、否決類的一票否決語意、
  「舊 decision 引用原 digest 不回寫」。

關於使用者提出的「強制只讀不改除非我同意」：**不建議另建權限系統**。`config/*.json` 是
tracked，agent 的改動會出現在 git diff，push 前看得到；且 `policy_version` 凍進每筆決策，
改 config 不會污染舊決策。禁止寫入反而讓提案要繞路。若日後需要更硬的保護，再考慮在
config 加 `approved_by` 欄位讓未簽名版本不被 sizing 採用。

### 尚未決定

- 賠率該怎麼量化才不會變成另一個「看起來精確的錯誤答案」（隱含上漲空間／下檔風險的
  比值？期望值？），以及它的輸入從哪個 authority 來。
- 合併三軸為「主張可信度」後，各來源類型的 authority 對照要怎麼重寫而不放寬 L8。
- 否決類要不要獨立成 Engine C 的一個欄位（目前 `litigation_and_audit_flags` 已存在，
  但沒有任何軸強制讀它）。

## 7. 下一步的判準

先讓 coverage 分類跑一兩週，看實際 daily brief 裡有多少標的從「零」變成「小注可評估」，
以及那些小注的品質。**若多數變成可評估的標的其實不值得看，問題就不在 gate 而在 pq1
的選題**，屆時重構三類軸也救不了。有實際樣本再決定是否動軸結構。

---

## 8. 第二回合（2026-08-08）：§5 的修正六天內沒有產生任何效果

§7 的判準終於被執行了。答案是 **0 / 9**：沒有任何一個 cohort 因為 §5 的分類從
「歸零」變成「小注可評估」。原因分兩層。

### 8.1 分類只有一個消費者真的套用

§5 改的是 `sizing.py` 的 `coverage_cap`。但同一份 blocker 清單另有四個消費者，
它們各自用 `status == "analyzable"`（⟺ 零 blocker）或整份 `core_blockers` 這種更粗的
判準，把放寬在下游完整抵銷：

| 消費者 | 原本的判準 | 後果 |
|---|---|---|
| `sizing.calculate_probe_limits` | `fatal_blockers()` | ✅ 唯一正確 |
| `store.get_coverage_result` | `status == "analyzable"` | lane 直接 not ready |
| `coverage.assess_coverage` | 同上 | 同上 |
| `coverage.apply_execution_intent` | 同上 | **覆寫** store 剛算對的值 |
| `action_card.build_action_card` | 整份 `core_blockers` | 強制 REVIEW＋「去把研究做完」 |

物理成因：分類住在 `coverage.py`，而 `coverage` 依賴 `store`，於是 `store` 想用就會
循環 import。**它沒有一個所有層都拿得到的家，所以只有一層用得到它。**

已修（2026-08-08）：抽出 `decision_lab/blocker_severity.py`，五處統一呼叫；
`action_card` 另加 `research_incomplete_blockers` 欄位讓「不阻擋、只縮小尺寸」看得見。
`tests/test_coverage_severity.py` 新增「所有消費者共用同一份分類」的整合測試——
§5 之所以能靜默失效六天，就是因為當時只測分類本身、沒測有沒有人用它。

### 8.2 真正的 binding constraint 不是 coverage

修好一致性之後仍然是 0/9，因為卡住的根本是別的東西：

| 實際瓶頸 | 佔比 | 性質 |
|---|---|---|
| `execution_intent: research` | **9 / 9** | research intent 從不 request paper lane，所以連 coverage 全乾淨的 4 個 cohort 也永遠 range 0 |
| `disproof_missing` | 4 / 9 | 系統第一大單一 blocker，而它只是**一句話**，不依賴任何外部證據 |
| `financial_missing` | 3 / 9 | Engine C 對那些 ticker 沒有資料 |

三者沒有一個是「證據不夠強」。第一個是工作流程從未接線，第二個是研究產出規格
缺一欄，第三個是資料覆蓋。**§2–§4 診斷的軸結構問題是真的，但它目前排在第四順位。**

補充實測：九份既有 assessment 的軸幾乎全部落在 `bounded_hypothesis`，只有
Agility（SPAC 未上市）有大量 `unknown`。因此**不要放寬 `axis_ceilings.unknown`**——
`unknown → 0` 在真實案例裡是對的，五軸不是當前瓶頸。這個念頭在 2026-08-08 被提出、
被資料否決；再有人想動它，先重跑一次上表。

### 8.3 給下一輪的判準

**不要再「憑理論修 gate、不驗證端到端」。** §5 與 8.1 是同一個錯誤犯了兩次：
診斷正確、局部修正正確、沒有量測，於是帳面「已實作」而實際供給為零。

任何對 gate 的改動，落地時必須同時回答：**改完之後，現有 cohort 有幾個的
`supported_range` 真的變了？** 答案是 0 就代表沒改到 binding constraint，
不論那個改動本身多正確。

`paper` lane 從未被寫過這件事本身也值得記：paper ledger 的用途是累積反事實戰績，
用來事後回答「系統的判斷準不準」。一個從不被寫入的模擬帳本是純成本、零效益，而且
它讓「這系統值不值得留」永遠無法用證據回答。

---

## 9. 第三回合（2026-08-08）：收斂 memo／cohort 模型與退場機制

> 起因：使用者問「Lane Memo / Watchlist / Underwrite 三層有需要嗎？中間那層可以移除嗎？」
> 以及「我們是不是做了太多寫死的 if/else，讓資訊消失在系統裡？是不是該開始減量？」
> 本節記錄收斂結果與實測依據。**動工前讀完 §9，不要重新發明。**

### 9.1 目標模型：一個 `go` = 一份 memo + 一到多個 cohort

```
Lane Memo（方向／敘事，可含多家公司，有版本）
    └─→ 每點名一家公司 × 一條主張 = 一個 Cohort（可下注的單位）
            └─→ Engine D 狀態：shadow → paper → live-eligible
```

**memo : cohort 不是 1:1，是 1:N。** 精確地說
`thesis : memo 版本 : cohort = 1 : N : M`。理由是 Lane Memo 的單位本來就是「方向」
而非公司——`cpo_v1_lane_memo.md` 涵蓋整個 CPO lane、
`amat_lrcx_mature_node_v1_lane_memo.md` 同時涵蓋 AMAT 與 LRCX，而
`sivers_v1/v2/v3` 是同一 thesis 的三個版本。

**這正是三層階梯的收斂點：** Watchlist 原本定義為「thesis 成立後才給名字」——那不是
一層，那就是 **memo → cohorts 的展開動作**。名字給出來的那一刻就是 cohort 誕生的那一刻；
之後「夠不夠格」由 Engine D 的 shadow／paper／live 狀態連續表達，不需要「升格」這個
離散事件。Lane Memo 保留（它有 Engine D 沒有的 variant perception），Underwrite Sheet
保留（產出格式），**Watchlist 降級為 cohort 集合的查詢視圖**。

**現況與目標的落差：memo 與 cohort 之間資料上零連結。**
`decision_cohorts` 只有 `cohort_id / dedupe_key / company_id / research_ticker`，沒有
memo 欄位；memo 檔也不知道自己對應哪個 cohort。實際狀態是三個互不重疊的集合：

| 有 memo、無 cohort | 有 cohort、無 memo | 兩者皆有 |
|---|---|---|
| `amat_lrcx_mature_node_v1`、`cpo_v1` | AAOI、Meta、IQE、Lumentum、2 個 unresolved | AXT、Coherent、Sivers |

**待補：`decision_cohorts.memo_ref`。** 沒有它，paper 部位無法歸因到 thesis，而歸因
正是 paper ledger 存在的唯一理由。

### 9.2 Cohort 粒度維持 per-claim（實測駁回 per-company）

`dedupe_key = sha256({identity_token, atomic_claim, direction, expiry})`，所以 cohort 的
單位是「公司 × 主張 × 方向 × 有效期」，不是公司。使用者提議改成以股票為單位以減少物件數。
**實測顯示這個成本不存在：**

- 9 個 cohort／7 家公司，**每個 cohort 恰好 1 個 `qualified_signal`**
- `workflow_reassessment_delta` 共 43 筆；AAOI 累積 54 個 event、AXT 64 個，但各自只有 1 個 signal
- 意即：同一家公司後續進來的多份文件（10-Q、8-K…）**走 `reassess`，不走 `capture_signal`**，
  不會另開 cohort

（先前推測「35 條 triaged lead 可能變成 35 個 cohort」是錯的，已由上述資料推翻；
「帳本不可逆成長」這條顧慮應同步降級。）

**不改成 per-company 的理由**（成本為零時應保留較強的設計）：

1. **五軸取 min 會跨 thesis 互相拖累。** 五軸問的是「這條主張是否為真」。若 AAOI 的
   800G thesis（`technical_causal_link: corroborated`）與 pump laser thesis（僅
   select-customer sampling）合併成一個 cohort，就只能有一組軸，而 sizing 取 min ——
   弱 thesis 會讓強 thesis 無法下注。這是 §2 問題的跨 thesis 升級版。
2. **`disproof_condition` 與 `expiry` 都是單一欄位。** 兩條 thesis 共用一句證偽條件，
   L7 的「觸發後 48h 動作」就失去對象；兩者時間跨度不同，expiry 也無法共用。
3. **歸因會永久失效。** 「三個月後這筆賺了，是哪條 thesis 對了」是 paper ledger 唯一
   要回答的問題；合併後永遠答不出來。LLM 能同時 handle 多條 thesis 是 agent 的能力，
   不是帳本的能力。

### 9.3 只有入口沒有出口：cohort 從不自動退場

- `store.list_operational_cohorts` 是 `SELECT ... FROM decision_cohorts`，**沒有 WHERE**，
  回傳所有曾建立的 cohort。
- `brief.py` 會濾掉 `promoted／rejected／expired`，所以待辦清單眼前不會爆。
- **但只有人工呼叫 `close_probe()` 能設成 terminal。`expiry` 到期不會自動 expire、
  `review_due_at` 到期也不會自動轉 `review_required`。**

實證：IQE 的 `expiry = 2026-08-07`（前一日）仍為 `active`；兩個 unresolved cohort 的
`expiry = 2026-08-02`，逾期六天仍為 `active`。

**這才是「越用越折磨」的實際機制**——不是資料量，是每個 cohort 都需要人主動關，
而系統從不提醒。接線後每個 `go` 都會產生一個這種物件。

**待做：`expiry` 到期自動轉 `expired`。** 欄位早已存在（`coverage.expiry`，且
`expiry_invalid` 已是致命 blocker），只是沒有任何地方拿它做過期判定。

### 9.4 Expiry 的訂定規則：催化劑驅動，不是固定期間

`catalyst / disproof / expiry` 是一組：「我預期 X 在 T 之前發生；沒發生就代表時序假設
錯了。」因此 expiry 回答的是**「證據最晚什麼時候該到」**，只能由催化劑的時鐘決定。

現況多數並非如此：

| Cohort | expiry | catalyst 實際時點 | |
|---|---|---|---|
| Sivers | 2026-08-28 | 2026-08-27 Q2 report | ✅ 催化劑 +1，唯一訂對 |
| **AXT** | 2026-08-09 | **2026-11 初** Q3 10-Q | ❌ 比自己的催化劑早三個月 |
| AAOI | 2026-08-09 | 2026 下半年財報 | ❌ 同上 |
| Meta | 2026-08-09 | 無明確日期 | ⚠ |
| IQE／Coherent／Lumentum／2×unresolved | 均已過期 | catalyst 空 | ❌ |

AXT 是最清楚的錯誤：催化劑不可能在有效期內發生，這種 expiry **保證產生一次假到期**。

**規則：**

- 催化劑有明確日期 → `expiry = 該日 + 1–2 週緩衝`（涵蓋財報延期）
- 催化劑無明確日期 → 用「下一個可能揭露的時點」，通常是下一次財報
- **硬規則：`expiry` 不得早於催化劑的預期時點**（AXT 現況違反）

### 9.5 Memo 核查頻率：thesis 驅動，不固定 90 天

`thesis/lifecycle.json` 的 `check_interval_days` **已存在且已訂對**：

```
axt_inp       90   （disproof 是產能擴張／出口許可，慢變數）
coherent_cpo  90
sivers        30   （disproof 是現金 runway，快變數）
```

問題只在 `crons/thesis_freshness_check.py` 寫死 `STALE_DAYS = 90` 而忽略它。
**核查頻率應跟著該 thesis 的 disproof 條件走（L7 本來就要求 disproof 附核查頻率），
不該被抹平成固定 90。** 改成讀 `check_interval_days` 即可。

### 9.6 Freshness「出生即過期」

`market_freshness_hours: 36`，但日線 bar 的 `as_of` 是**交易日當地午夜**
（`2026-08-05T00:00`），它代表的卻是**當天收盤**（美股約 20:00 UTC）。freshness 拿它
當觀測時刻做小時級減法，等於憑空多算約 20 小時的假過期——36 小時上限實際只容許
約 16 小時真實鮮度。

實例（AXT，2026-08-08 實測）：

```
決策凍結     2026-08-06 12:41 UTC
凍入行情     as_of = 2026-08-05 00:00（最後一個完整交易日）
上限         2026-08-05 00:00 + 36h = 2026-08-06 12:00
→ 決策在出生當下就已超時 41 分鐘
```

AAOI／AXT／Meta 三筆現在都帶 `market_stale_since_decision`。接線後的實際體驗不是
「偶爾過期」，而是**每天所有 paper 部位都是 `DATA_NEEDED`、refresh 完仍是紅的**，
直接毀掉 daily brief 的訊噪比。

**修法：不要把 36 調大**（那會讓真正的過期也混過去）。正解是與 beta monitor 對齊——
日線資料的 freshness 判準應為「**凍入的 bar 是否為最新的完整交易日**」，以交易日為單位
而非小時。這樣週末與盤中都不會誤判。FX 與 financial 兩個維度維持現狀。

這是 L12 的又一個實例：`as_of` 同時承載「交易日日期」與「觀測時刻」兩種語意。

### 9.7 兩套 lifecycle 分裂（已知，本輪不修）

系統存在兩套彼此不知道對方的 lifecycle，實測交叉引用次數皆為 0：
`decision_lab/` 讀 `thesis/lifecycle.json` **0 次**；`thesis/`、`engine_b/`、`crons/`
碰 Engine D lifecycle **0 次**。

| Thesis | `thesis/lifecycle.json` | Engine D `current_lifecycle` |
|---|---|---|
| Sivers | `review_required`（使用者 2026-07-12 人工決議的 8/27 hold） | **`active`** |
| Coherent | `active` | **`expired`** |
| AXT | `active` | `active` ✓ |

三個重疊項有兩個矛盾，且方向相反。

**本輪不修的理由：** 有一個成立的反論——**paper 本來就應該無視人工 hold**。paper 的
用途是記錄「若我未介入，系統會怎麼做」；若人工 hold 也壓住 paper，paper 就只是使用者
判斷的鏡子，永遠學不到「系統是對的、那次 hold 錯了」。**live 反映使用者判斷，paper
反映系統未經過濾的判斷，兩者不同步是設計而非缺陷。** 分裂真正有害處只在**呈現**
（daily brief 會同時聲稱 Coherent thesis active 而 Engine D 已 expired），屬報告矛盾，
非資本安全問題。

若日後要修，方向建議 **Engine D 讀 `thesis/lifecycle.json` 作為 hold 來源**（thesis 層是
人工判斷的家，Engine D 是系統執行狀態；應為「人的決定約束系統」而非平行真相），
而非把兩者合併（單位不同：thesis vs cohort，合併需對映規則且工程量大）。

### 9.8 已知重複，但本輪刻意不動

`engine_c/checklist.py:247` 的 `gate_pass = all(status in ("ok","manual_reviewed"))` 與
`coverage.assess_coverage` 的逐項 blocker，是**同一個判準掃同樣五項、跑兩次**，卻得出
相反語意的結論：前者二元「不准升格 Watchlist」，後者連續「可以小注」。這是 L12 的形狀。

**不現在刪的理由：** AXT 現況是 Lane Memo `Watchlist Candidate`、四道 gate 全過、
Engine D coverage 零 blocker、supported range **仍為 0**（唯一原因是 `intent: research`）。
**全綠而無事發生——刪掉重複的 gate 不會改變這個結果。** 等 paper 開始累積，才會知道
兩套 gate 哪一套真有預測力；那時候刪是有證據的刪，現在刪是再一次憑理論動手（§8.3）。

（另註：`thesis/generate_lane_memo.py` 與 `thesis/preconditions.py` 的 L9 gate **並非死碼**。
AXT 2026-08-04 的 memo 帶有該 script 的 header 與 `.evidence.json` sidecar，L9 gate 通過，
`Watchlist Candidate` 確實產出過。曾一度誤判為 vestigial，此處更正。）

### 9.9 接線範圍與前置順序

**接線內容（使用者 2026-08-08 核准方向）：**

| # | 項目 | 說明 |
|---|---|---|
| 1 | intent `research` → `paper` | routine 產生 decision 時改用 paper intent，開始累積反事實戰績。live 仍 100% 人工 |
| 2 | `disproof` 列入 pq1 研究產出規格 | 解掉第一大 blocker（4/9）。那句話隨 packet 進 pq2 由使用者核准——由「想證明 thesis 成立」的同一個 agent 自寫證偽條件有 L8 形狀的自我報告偏誤 |
| 3 | live 轉綠時主動通知 | `live_status == ELIGIBLE` 已會產 `action=TRADE, urgency=user_decision`，只需確保它出現在 Daily Brief 首屏 |
| 4 | cohort 只由使用者 `go` 建立 | 不讓 triage PASS 自動建，增長速度由人控制 |

**不動：** live 100% 人工、Google Sheet 唯讀、graph admission 原 gate、既有 frozen
decision 不回寫。

**前置條件（必須先做，否則接完就是每日假警報）：**

0. **修復並回填 shadow（§9.11）——建議排最前面**，它最便宜且立刻能量化 gate 的代價
1. `expiry` 到期自動轉 `expired`（§9.3、§9.4）
2. freshness 改以交易日為單位（§9.6）
3. `thesis_freshness_check` 讀 `check_interval_days`（§9.5）

**接線後的已知代價：**

- **memo 不對稱：** AAOI、AXT、Meta 三筆會產生 paper 部位，但只有 AXT 有 lane memo。
  「一個 `go` = 一份 memo」是往後的規則，不回頭補既有 cohort——要嘛補兩份，要嘛接受。
- **樣本仍薄：** 3 個 paper 部位不足以回答「系統準不準」，只是開始累積。

### 9.10 Sivers 個案（記錄判斷，不是通則）

使用者問：能否基於 CW 雷射產品的不可取代性手動加 Sivers。拆解後：

- **系統已同意該論點。** `technical_causal_link` 是 Sivers 五軸中唯一的 `corroborated`
  （「Sivers lasers 與 O-Net／Enablence、GlobalFoundries reference-design 路徑有多個
  來源支持」）。
- **擋住它的是另外兩件不同性質的事：** `valuation_payoff: unknown`（五軸取 min → ceiling 0），
  以及使用者自己 2026-07-12 設的 8/27 分辨點。**技術不可取代 ≠ 公司撐得到那天 ≠
  現在的價格值得買**——正是 L12 要求分開的三件事。
- **`valuation_payoff: unknown` 的成因已消失。** 當初理由是「SIVE.ST research-market
  observation 被 quarantine」；2026-08-08 實測 `status=observed / unit_status=ok /
  blockers=[] / price 40.18 SEK`。該 `unknown` 是**過期的資料問題，不是真的證據缺口**。

**三條路：**

- **A. Revise thesis** — 走 `thesis_mutation` → pq2 → `todo complete-thesis-mutation`。
  副作用：epoch +1、舊 decision 不再授權交易。**這是設計上的正解**，因為用 override 開
  部位會讓 thesis 永遠停在 `review_required`——持有部位而警報永遠響著，正是 L7 要防的事。
- **B. 補 valuation 軸** — 系統自列缺兩項，其一（市場快照）已自行修復，其二
  （以 pipeline conversion 與毛利率為基礎的 downside case）是分析工作。
- **C. `live_override`** — 逃生門確實存在且**刻意保留**。實測 `store.apply_live_override`
  **不檢查 lifecycle**，只要求 exact `selected_weight`、明確 `reason`、未過期的 prepared
  action 與一次 native 核准，並留下 receipt。系統不代下單。

**本輪決議：B 現在做但 reassess 留到 8/27；A 等 8/27 重編財務到位。**
順序本身即可保護使用者設定的分辨點——B 只產出 assessment JSON，**部位是 reassess 才
產生的**，因此不需要先修 §9.7 的 lifecycle 分裂。

### 9.11 Shadow 與 Paper 不可合併，而 Shadow 目前 78% 是壞的

使用者問「shadow 跟 paper 現在還需要分嗎？感覺是同一個東西」。**不能合，而且 shadow
是更重要的那個。**

| | Shadow | Paper |
|---|---|---|
| 內容 | 訊號進來那一刻的**價格錨點**（price／as_of／currency／source） | 有 **weight** 的模擬部位 |
| 有部位 | 沒有 | 有 |
| 需通過 gate | **不需要**，訊號一進來就記 | 需要（coverage ＋ 五軸） |
| 回答 | 「從我們知道這件事開始，股價走了多少」＝**資訊價值** | 「照系統 sizing 下注，績效如何」＝**決策品質** |

**關鍵：訊號可以是對的（股價漲），而系統把它 size 成 0（paper 什麼都沒有）。只有
shadow 記錄「我們看到了但沒動作」。** 這正是本檔 §1 的 AXT 案例，也是本輪討論的核心
問題「被 gate 擋住的代價有多大」——**shadow 是唯一能量化這個代價的東西**。合併就永遠
只剩「我做了的決定準不準」，失去「我沒做的決定虧了多少」。

#### 現況：9 個 cohort 有 7 個沒有 shadow 價格

```
co:coherent    COHR     建立 07-22  unavailable
co:lumentum    LITE     建立 07-22  unavailable
co:sivers      SIVE.ST  建立 07-26  observed  31.32  (as_of 2026-07-23T22:00Z)
co:aaoi        AAOI     建立 07-26  observed 100.15  (as_of 2026-07-24T04:00Z)
co:axt         AXTI     建立 07-29  unavailable   ← 就是本檔 §1 的那一筆
co:meta        META     建立 08-02  unavailable
co:iqe         IQE.L    建立 08-04  unavailable
2 × unresolved          —           unavailable
```

`outcomes._market_outcome` 明訂：shadow 非 `observed` 或 price 為 None →
`market_return_status = "unknown"`。因此那 7 個的 `performance_since_tracked`
**永遠是 null**。**shadow 最該發揮作用的那一次（AXT），它失敗了。**

#### 傳導機制：shadow 沿用 decision 的行情快照，失敗即永久遺失

`workflow.py:403` 以 `_StaticMarketObserver(snapshot.market)` 建立 shadow——
它**不自行抓價，而是直接沿用該次 decision 的 `AuthoritySnapshot.market`**。
因此 cohort 建立當下那一次行情若不可用，shadow 錨點就永久遺失：**靜默、無重試、
無回填**。

`intake.capture_signal` 的 `except Exception: market_observation =
MarketObservation(status="unavailable")` 讓失敗原因完全消失，屬 L12 的「一個表示承載
兩種語意」：`unavailable` 同時代表「這檔沒有行情」與「這次抓取壞了」。

#### 根因不是單一的，也**不是 Codex sandbox**

> ⚠ 本小節曾一度寫成「本機環境行情抓取間歇失敗，與 2026-08-07 的 `etl_yfinance`
> sandbox 失敗同一類事件」。**該推論已被自己的資料推翻，勿再沿用。**

**沙箱相關性檢定（2026-08-08）：** 比對各 cohort 建立時刻與當日
`~/.codex/.sandbox/sandbox.<date>.log` 的 `FAILURE` 數，**相關性是反的**——
shadow 成功的 2026-07-26 時段有 3 次 sandbox FAILURE，而失敗的 07-22 與 08-04
時段各為 0 次。

逐一取出各 cohort 首筆 decision 的凍結 `market` 區段後，實際是**至少四種不同成因**：

| Cohort | 建立當下 market 狀態 | 根因 |
|---|---|---|
| **LITE** | `market_missing` | registry entry 當時**缺 `market_currency`**。cohort 建於 2026-07-22 23:44（台北）；該欄位由 `8e4a4865` 於 07-23 07:08 補上——**晚 7.4 小時** |
| **META** | `market_missing` | 同上。cohort 建於 2026-08-02 10:15；該欄位由 `b5abbd3e`（即 2026-08-05 的幣別分離修正）於 08-05 11:34 補上——**晚 3 天** |
| **COHR** | `market_timestamp_future` | `as_of` 落在 `fetched_at` 之後，`_validate_market` 的 `fetched_at < as_of` 直接判 unavailable。**即 §9.6 的 `as_of` 語意 bug** |
| **IQE** | `market_adv_invalid` ＋ currency | GBp 未正規化；2026-08-05 幣別修正之前的舊帳 |
| **AXT** | `market_unavailable` | **唯一一筆真正的抓取失敗** |
| 2 × unresolved | `market_missing` | identity 未解析，預期內 |

（Sivers／AAOI 成功。兩者 bundle 顯示 `market_stale`，但 stale 不影響 shadow——
shadow 用的是正規化**前**的原始 `snapshot.market`，`stale` 是 bundle 正規化後才貼上的。）

**結論：六筆失敗中，五筆是 repo 內部的資料問題，一筆是外部抓取失敗，零筆是 sandbox。**
這個區別決定解法方向——若是 sandbox 就該改環境；實際上解法在程式碼裡。

**也解釋了為什麼「加重試」不是解法：** LITE 與 META 重試一百次都會失敗，因為缺的
不是網路，是 `config/company_identity.json` 的那一列。

#### 更深一層：兩個可獨立文件化的形狀

**形狀一（L12 的新實例）：`identity.status` 同時承載兩種語意。**
META 的凍結 identity payload 是：

```json
{"status": "resolved", "company_id": "co:meta", "research_ticker": "META",
 "market_currency": null, "execution_currency": null, "execution_venue": null,
 "blockers": ["market_currency_missing", "execution_currency_missing",
              "execution_venue_missing"]}
```

`status` 一個欄位同時表示「身分解析成功」與「欄位齊全」。下游看 `status == "resolved"`
就往前走，三個 `*_missing` blocker 明明就在旁邊卻無人理會。**應併入
`docs/solutions/architecture-patterns/one-representation-two-meanings.md` 作為新實例。**

**形狀二（不是 L12，值得新開一篇）：把可重建的資料當成 point-in-time 凍結。**
這裡的資訊**一點都不模糊**——系統完整記錄了自己缺什麼；問題是沒有任何東西阻止或
修復它，而後果不可逆。核心判準：

> **先分清楚哪些資料是「只有當下才有的真相」，哪些是「隨時可重建的事實」。
> 後者被當成前者凍結時，一次瞬時故障就會造成永久損失。**

對照本專案：

| 資料 | 性質 | 現況 |
|---|---|---|
| decision context bundle | 真 point-in-time | ✅ 正確地不可回寫 |
| **shadow 錨點** | **某個已知日期的收盤價，可完整重建** | ❌ 被當成 point-in-time，一次故障即永久遺失 |

這也是為什麼解法是**回填**而不是**重試**。

**已排除的假設（勿重查）：**

- ❌ **時序條件**（`intake.py` 的 `as_of > observed_at` 或落後 > 4 天）：對失敗案例逐一
  推算皆應通過。
- ❌ **幣別不匹配**（`_validate_market` 的 `observation.currency != expected_currency`）：
  2026-08-08 實測七檔 registry `market_currency` 與 provider `currency` **全部 MATCH**，
  含 IQE 的 GBp→GBP 正規化。
- ❌ **建立路徑不同**：AAOI（成功）與 AXT（失敗）的 `raw_signal` 都是「入圖後自動追蹤」，
  同一條路徑、不同結果。
- ❌ **時間分界**（曾誤判「某時點後全壞」）：7/26 兩筆成功，其前（7/22）與其後
  （7/29、8/02、8/04）皆失敗，非chronological。

#### Shadow 可以被正確回填（與 decision 不同）

Decision 必須 point-in-time 凍結、不得回寫；但 **shadow 只是某個已知日期的歷史收盤價，
可用歷史資料完整重建，不損及稽核性**。2026-08-08 實測回填結果：

| Ticker | 錨點日 | 錨點價 | 2026-08-07 | 變化 |
|---|---|---|---|---|
| **AXTI** | 2026-07-29 | 36.97 | 88.58 | **+139.6%** |
| COHR | 2026-07-22 | 312.19 | 379.13 | +21.4% |
| LITE | 2026-07-22 | 829.70 | 890.17 | +7.3% |
| META | 2026-07-31 | 556.71 | 592.10 | +6.4% |
| IQE.L | 2026-08-04 | 44.80 | （最新列為 NaN，待查） | — |

AXTI 已驗證無 split，量價齊揚（7/31 成交量 2,962 萬股），催化劑為已記錄的 Lumentum
六年 InP 產能協議。

**這個數字要正確解讀：** probe sizing 本來就極小，`single_probe_nav_cap` 為 0.5%、
`bounded_hypothesis` 的 `axis_ceiling` 為 0.2%。即使 gate 全開，+139.6% 對 NAV 的貢獻
約 +0.3%～+0.7%。**所以損失不在金額，在資訊**——系統的 pq1 選題選對了，而它對這件事
**零紀錄**。沒有 shadow，「這系統選股行不行」這個問題連樣本都沒有。

#### 待做（建議排在 paper 接線之前）

1. **回填既有 7 筆 shadow**（歷史收盤，可完整重建）
2. **加一條 fallback，而不是改成完全獨立抓價。** 沿用 `snapshot.market` 有其價值——
   它保證 shadow 與 decision 看到**同一個價格**；改成獨立抓取會讓兩者可能不一致，
   反而更難稽核。正確做法是：`snapshot.market` 可用時照舊；不可用時改以**歷史收盤
   回填**（shadow 是某個已知日期的價格，不是 point-in-time 敏感資料，回填不損稽核性）。
3. **失敗時保留 `failure_class`**，不要讓 `market_timestamp_future`、
   `market_unavailable`、`market_missing` 全部塌成同一個 `unavailable`——上表能區分出
   四種成因，正是因為 decision 那側保留了 blocker，而 shadow 這側沒有。
4. **加入修復路徑**：shadow 為 unavailable 時，於後續 reassess 嘗試回填。
5. **`ensure_shadow_for_company` 不應在 `identity.blockers` 含 `market_currency_missing`
   時逕自建立 cohort**——那等於明知會壞還先做，並讓錯誤不可逆。

### 9.12 文件化待辦（本輪產出，尚未寫入）

以下三項是本輪確認、但**刻意延後**到實作完成後再寫的沉澱：

1. **併入既有 L12 文件**（不新增檔案）：`identity.status = "resolved"` 卻同時帶著三個
   `*_missing` blocker，是「一個表示承載兩種語意」的新實例。
   目標：`docs/solutions/architecture-patterns/one-representation-two-meanings.md`
2. **新開一篇 solutions**：「可重建的資料不該被當成 point-in-time 凍結」
   （§9.11 形狀二）。與 L12 的差別在於資訊並不模糊，缺的是**修復路徑**；
   判準是先分類 point-in-time vs reconstructible，後者必須可回填。
   目標：`docs/solutions/architecture-patterns/` 新檔。
3. **L13 候選（延後決定）**：上述形狀二夠格成為 AGENTS.md 的判準，但 AGENTS.md
   每個 session 全量載入，新增一段是永久 context 成本。**建議等它第二次咬到我們
   再升格**——這正是 L12 自己的誕生方式（一個 session 內撞到四次同形狀才成為判準）。
   在那之前只留 solutions 文件與本節紀錄。

**理由是它比 paper 便宜且更早見效：** 不需要 coverage、不需要五軸、不需要 disproof，
訊號進來記一個價即可；且既有 cohort 可立即回填，不必等三個月累積樣本。

---

## 10. 第四回合（2026-08-08 下午）：從「診斷」到「系統第一次能評估自己」

> §9 收斂完模型後的實作與紅隊。本節記錄**做了什麼、量到什麼、以及三個當天犯下並
> 更正的錯誤**。commit 只留下結果，脈絡在這裡。

### 10.1 執行順序與實測效果（§8.3 判準：改完有幾筆資料真的變了）

| # | 動作 | 現有資料改變數 |
|---|---|---|
| 0 | Shadow 回填 | **5 筆**（AXTI／COHR／LITE／META／IQE.L）→ `performance_since_tracked` 首次可用 |
| 1 | Expiry 呈現（不自動關） | 3 筆逾期現形；**刻意不自動關**——co:axt 的 expiry 比自己的催化劑早三個月，自動關會關掉一個 +107% 且仍在跑的 thesis |
| 2 | Freshness → 交易日 | 對新 decision 生效；舊 decision 用自己凍結的 legacy policy 評估 |
| 3 | `check_interval_days` | 90 只留給無 lifecycle entry 的 memo |
| 4 | intent → paper（接線） | **paper ledger 首次被寫入**：META／AXT／AAOI 各 0.1% NAV |

**接線的另外兩項查證後未動程式**：`live 轉綠通知` 早已存在（`TRADE` 在
`_ACTION_PRIORITY` 排第二）；`cohort 只由 go 建立` 早已成立（唯一入口是入圖完成後的
`_ensure_shadow_for_completion`）。**查證後不改，比為了完成清單而改更有價值。**

### 10.2 紅隊（審查表本身先更新，見 `skills/blind-spot-audit`）

舊版 skill 的 description 明寫「不審軟體架構與程式碼品質」——而當天每一個 binding
constraint 都落在那個被排除的區域。用它去審會得出「投資邏輯很嚴謹」，而那正是問題
所在：**邏輯沒錯，管線把它靜默歸零。** 已改 scope 並新增 D 類五個 lens（空機制／
修法有效性／L12／無出口／可重建卻被凍結），各錨定一個已發生的實例。

紅隊三大發現與處置：

1. **`benchmark_return` 在 production 寫死 `None`** → `classification == "beta"` 程式上
   不可達（實測 23 筆 0 個 beta）。系統因此無法區分「thesis 對了」與「大盤漲了」。
   → 已接上（10.4）。
2. **outcome attribution 產出 2 筆、皆 `unknown`**，且 `close_probe` **根本沒有 CLI
   入口**——不是沒人想關，是關不了。→ 新增 `decision_lab close`。
3. **live 半邊四張表全 0 筆**。→ 實測發現**它是通的，只缺使用者的持倉聲明**（10.5）。

### 10.3 AXT 的 provenance：不是好運，但也不是預測

追蹤起點（Shadow 錨 2026-07-28）的觸發物是 `ra_a09b6e59`「AXT／Casela 2027 InP 長約」：
AXT 2026-06-17 的 8-K 首次點名 Casela 為 InP 客戶，揭露**具預付款與最低採購保障**的
2027 長期供應協議。隔天（07-29）Lumentum Capacity Reservation Agreement 8-K
（US$43.5M deposit）——**結構上是同一個模式的更大實例**；再隔天 Q2 營收 +164%。

所以系統是先讀到了建立該模式的公開文件，市場在同模式放大時才重新定價。**但三點必須
誠實**：(a) 那份 8-K 早在 06-17 就公開，edge 在「比市場早消化已公開文件」而非預見未來；
(b) cohort 的 `atomic_claim` 是空的、`evidence_tier: 4`，實質內容在圖裡不在 cohort，
所以「當初的判斷」沒有被寫成一句可回頭檢驗的話；(c) **n=1**，模式辨識與幸運排序分不出來。

### 10.4 Benchmark：選擇由實際持倉決定，不由論證決定

先前手動用 QQQ 算超額報酬其實沒有依據。查實際持倉後：

```
VWRA 26.5%（beta core）  QQQ 家族 19.1% 名目／約 24% 換算  2330.TW 17.6%  0050 家族 16.3%
```

**alpha 主基準定為 QQQ**：alpha 標的全是科技／半導體，拿含金融、能源的全球指數當基準
會系統性美化結果；QQQ 家族換算曝險約 24%，是這筆錢真實的替代去處。**VWRA 是 beta
sleeve 的基準，不是 alpha 歸因的基準**——先前把這兩個角色混在一起。半導體標的可經
registry 覆寫成 SOXX。**不採 provider 推斷的 sector**：那正是幣別那條路教過的錯誤。

兩個錨點各配一個對齊的 benchmark（`excess_since_tracked` 錨在 Shadow、
`excess_since_decision` 錨在決策）。用同一個 benchmark 減兩個不同起點會產生看起來精確的
錯誤答案。

**⚠ 原始超額報酬，未做風險調整。** 用一檔十天能漲 107%、也能跌 40% 的小型股贏過指數，
不必然是技巧。n=5、窗口兩週，算 beta 太早；不算，但輸出必須標明未調整。

### 10.5 Live lane：它是通的，只缺一句聲明

實測真實 authority：Sheet 回得出 24 列／NAV 425,629／digest 算得出來；co:axt 與 co:meta
的 identity resolved、execution 同 symbol 同幣別（execution_market 複用、execution_fx
為 None）、行情 observed 有 price 與 adv20。

**唯一缺口是 `holdings_confirmations`——「這確實是我的持倉」的使用者聲明，不由 agent
代簽。** 使用者確認後（`hc_d80a0459`），Sivers 的 blocker 從 5 個收斂到 1 個，只剩
`valuation_payoff_unknown`（軸本身，非資料管線）。

補了兩個測試鎖住 production 形狀（既有 e2e 走的是 Sivers 跨市場形狀，與投組多數標的
不同），其中一個專門鎖「**live 是等你一句話，不是等系統修東西**」——兩者輸出長得像，
下一步完全不同。

### 10.6 當天犯下並更正的三個錯誤

**這三個都是自己撞上的，記下來比記下成果重要。**

1. **alpha/beta 用錯窗口。** `_alpha_beta` 比的是決策錨點那一組，而決策錨點會被
   reassess 重設——等於讓分類窗口可以被自己的操作縮短到零。實測 co:axt 在 reassess
   兩小時後被判 `beta`（自決策 +0.0% vs QQQ −1.2%），而它自追蹤以來 +107%、超額 +101pp。
   改用 Shadow 錨點後：co:meta 仍是 `beta`（超額 +0.6%，確實只跟著大盤），
   co:axt／co:aaoi 變成 `mixed_or_unknown`——**超額很大但證據沒變，誠實地說「不知道
   是 thesis 對了還是動能」**。

2. **FX 留在小時制，理由是「FX 是連續報價」。** 由 Sivers live 實跑撞出 `fx_stale` 後
   才查 provider：`source=yfinance://fx/SEKUSD=X`、`as_of=2026-08-07T00:00:00+01:00`
   ——**同一個日線 bar、同一個午夜標籤**。我是**按概念推理而沒查資料源實際回傳什麼**，
   正是這一整天在修的同一種錯誤，只是這次是自己犯的。

3. **在 `decision_lab` 直接 import `engine_c.market_data`。**
   `tests/test_engine_d_runtime.py` 立刻擋下——具體 current-state 依賴只能住在
   `engine_d_runtime`。**改的是程式，不是測試**；加了 `WorkflowDataProvider.benchmark_return`
   seam。一整天在修「邊界沒被遵守」造成的問題，不該自己再破一個。

（另外一次：把 `beta_policy` 的 `fx_max_age_hours` 一併改名，弄壞 42 個測試——那是
資本換匯的獨立設定、不同消費者，且 fixture 依賴很深。還原後改在呼叫點換算。
**改名的成本與它的收益不成比例時，就不要改名。**）

### 10.7 兩個「記錄了自己缺什麼、卻沒人行動」的修補

- **`missing_data` 從未被消費。** 軸判 `unknown` 時會誠實記下缺什麼，但實測該欄位只被
  `sizing` 驗證格式、被 card 顯示，**沒有任何地方問「這項現在拿得到了嗎」**。co:sivers 的
  `valuation_payoff` 因行情 quarantine 判 unknown，quarantine 在 2026-08-05 已解除，
  卻又卡了三天——而使用者實際持有該標的。
  修法不解析自由文字（會變成猜測），改用既有軸→authority 對應做確定性比對。
  實測抓到 co:sivers（valuation_payoff）與 co:iqe（五軸全部）。

- **10/10 個 cohort 的 `atomic_claim` 全是空的。** 成因是「入圖後自動追蹤」這條唯一入口
  從不帶 thesis——系統性，非個案。而 `dedupe_key` 含 `atomic_claim`，**空 claim 一旦
  建立就永久補不回來**。已改為帶 applied lead 的 title；**既有 10 個是不可逆損失**。

### 10.8 現在能回答與仍不能回答的

**能回答了：** 從我們知道一件事開始股價走了多少（Shadow）；扣掉 benchmark 還剩多少
（超額）；系統照自己的規則會下多大（paper）；哪些軸現在可以重評估。

**仍不能回答：** 系統選股準不準。n=5、窗口兩週、零失敗樣本、未做風險調整——
**這個數字現在只夠說「值得繼續累積」，不夠說「會賺」。**

**下一輪的判準不變（§8.3）：任何 gate 改動落地時必須回答「現有 cohort 有幾個的
`supported_range` 真的變了」。** 而新增一條：**任何「機制不生效」的修法，必須同時回答
「它現在產出過幾筆」**——否則就是又蓋了一個空機制。

### 10.9 兩個由「處理四則推文」撞出的結構問題

**（一）pq1 排序只看標題第一個 cashtag，且完全不看實際持股**

`engine_b/priority.py` 的算分：

```
score = (5 − tier) + 5.0 矛盾 + 4.0 thesis_impact + 3.0 獨立來源
      + 2.0 新穎 + 5.0 使用者指定 + 5.0 campaign
```

`thesis_impact` 由 `lead_ticker()` 判定，而它取的是**標題裡第一個 `$XXX`**。實例：

> "Wow, there's gem after gem in **$AAOI** earnings for **$SIVE** + other laser player readthrough."

第一個 cashtag 是 `$AAOI`，於是整則推文只用 AAOI 判斷重要性——但該則的實質重點是
SIVE（使用者實際持有 FRA:2DG），且同時提到 LITE／AVGO／COHR／NVDA。
**而 `engine_b/entities.py` 的抽取早就把五家都解析出來了**：

```
entities: ['co:applied_optoelectronics', 'co:lumentum',
           'co:broadcom', 'co:coherent', 'co:nvidia']
```

**抽取抓到五個，排序只用一個。** 這是既有資料沒被下游使用，不是資訊不足。

第二層：`tracked_tickers` 由「非 retired lifecycle ＋ 未結案 Decision cohort」導出，
**不含 Google Sheet 持股**。因此**實際持有但尚未建 cohort 的標的，在研究排序上零加權**。

實測後果（2026-08-08 的 drain 前五名）：三則機器人題材各 13.0 排在前面——而它們對應的
三個 Agility cohort 至今 identity 仍是 `unresolved`、無 ticker、無法下注；關於使用者持股
的那則排第四（10.0）。**每日只有 5 個 pq1 額度，先花在不能行動的東西上。**

修法方向（未實作）：`thesis_impact` 改用 `lead.entities.company_ids` 全集合而非第一個
cashtag；另加一個 holdings 維度（Sheet 持股 ⊂ 加權來源）。⚠ 加權不等於自動研究，
pq2 人工 gate 不變。

**（二）`graph_commercial` 是宣告存在、卻無人生產的 authority**

`sizing.AXIS_REFERENCE_AUTHORITIES` 宣告 `commercial_maturity` 可由三種證據支持：

```python
"commercial_maturity": {"graph_commercial", "engine_c_backlog", "engine_c_customer"}
```

但 `graph_commercial` 對應 evidence payload 的 `commercial_assertions`，而全 repo 只有
**消費端**（`context.py:397` 讀它），**沒有任何生產端**——`engine_d_runtime` 的 `_read_graph`
產出 entities／edges／claims／assertions／sources／causal_paths／counter_paths，就是沒有
`commercial_assertions`。

於是宣告的三條路實際只有兩條，且兩條都要求 Engine C 有 `manual_reviewed` 的客戶集中度與
backlog 觀測（`manual_required` 時 `source` 為 None，不會進 reference index）。

**這造就一個看起來軟、實際上硬的閘門**：任何公司只要缺那兩筆人工觀測，
`commercial_maturity` 恆為 `unknown`；五軸取 min ⇒ **supported range 恆為 0**。

實測：co:iqe 於 2026-08-08 補齊四軸與 L7 證偽條件後仍是 `SHADOW_ONLY`，唯一原因就是該軸
結構上無法被填；co:aaoi 能有 paper 部位，是因為它**剛好**已有那兩筆人工觀測。

這是 D13（空機制）的新實例，且比先前幾個更隱蔽——它不是「蓋好沒人用」，是
**「宣告了但從未存在」**，而宣告本身讓人以為有三條路可走。

修法方向（未實作，二擇一）：讓 graph adapter 真的產出 `commercial_assertions`
（來源是圖中 `supplies_to`／backlog 類 edge 的 assertion），或把 `graph_commercial`
從 `AXIS_REFERENCE_AUTHORITIES` 移除並在文件明寫「本軸只能由 Engine C 人工觀測滿足」。
**兩者都可接受，不可接受的是維持現狀**——現狀讓閘門的真實高度與宣告不符。

### 10.10 這兩個核驗項該不該硬擋？——`manual_required` 又是一個表示兩種語意

使用者問：「customer concentration 跟 backlog，如果沒追到會怎麼樣，就硬擋？這兩軸該
怎麼看待？」這直接連回本檔起點的問題（gate 全過時 alpha 也沒了）。

**先更正一個推理錯誤。** 本節作者一度說「這兩件都不是 blocking」，理由是四個 cohort
都有部位。那是**倖存者偏誤**——那四個正是通過閘門的那些。查完整名單後相關性是 100%：

| Ticker | customer_concentration | backlog | commercial_maturity | 部位 |
|---|---|---|---|---|
| AAOI／AXTI／META／SIVE.ST／COHR | `manual_reviewed` | `manual_reviewed` | `bounded_hypothesis` | 有 |
| **IQE.L** | `manual_required` | `manual_required` | **`unknown`** | **0** |
| **LITE** | `manual_required` | `manual_reviewed` | — | 會卡 |

諷刺的是 `skills/blind-spot-audit` 的 A3 lens 明寫要防「倖存者偏誤：只研究還活著的
贏家」，而該 skill 當天稍早才剛被更新。**紅隊判準寫下來不等於自己會套用。**

#### 這道閘門的真實形狀

新公司走到有部位的完整路徑：

```
lead → pq1 → 入圖核准（pq2）→ cohort → **客戶集中度觀測（pq2）**
     → **backlog 觀測（pq2）** → 五軸 assessment → reassess → 部位
```

中間那兩步在任何 skill 流程文件裡都不是以「不做就永遠是 0」的形式出現——它們看起來
像五項核驗清單裡的兩項，像選填。

#### 該不該硬擋：不該，但也不該拿掉

`manual_required` 目前同時代表兩件事：

1. **「我們還沒查」** —— 該擋。你真的不知道。
2. **「查了，公司不揭露」** —— **不該擋。它本身就是一個發現。**

第二種非常常見（很多公司從不揭露 contracted backlog）。要求它等於**用揭露習慣篩公司，
而不是用風險篩公司**。而揭露豐富的公司通常較大、分析師覆蓋較多、較不容易被錯價——
**所以這道閘門會系統性地把系統推向 alpha 最不可能存在的地方。** 這就是「gate 全過時
alpha 也沒了」的可指認機制，不是抽象擔憂。

**反面必須同時記住：Sivers 是反例。** 它的 `commercial_maturity` 寫著「$799M 只是
opportunity pipeline，未揭露 contracted backlog」——那個「未揭露」本身就是 thesis 的
核心弱點。不做這個功課，會把 $799M 當成訂單。**功課有價值，即使答案是「查不到」。**

#### 結論與待做

保留功課，但讓兩種狀態分開——這與 `blocker_severity` 是同一個形狀：

- `manual_required`（沒查）→ 軸 `unknown` → 歸零（維持現狀）
- **新增**「查了、公司不揭露」狀態 → 軸可為 `bounded_hypothesis`，reason 記載
  「公司不揭露 contracted backlog，成長可見度只能由 guidance 與產能推論」→ **降尺寸而非歸零**

⚠ Engine C 目前字彙只有 `ok`／`missing`／`manual_required`／`manual_reviewed`，
**無法表達第二種**。新增狀態屬 closed-vocabulary 變更（見
`docs/solutions/architecture-patterns/closed-vocabulary-registry.md`），需同步
`engine_c/observation_fields.py`、checklist、以及 coverage 的 blocker 分類；
本輪只做到「讓閘門可見」（commit `586bfaf`），未動閘門本身。

**動工前先確認一件事：** 新狀態必須要求 receipt——「查了但沒揭露」若不附追源紀錄，
就會退化成「我沒查」的同義詞，那比現狀更糟（現狀至少誠實地擋著）。

#### 補充（同日追問撞出的第三層）：「查了沒揭露」若沒有重查觸發，比現狀更糟

使用者追問：「沒查到之後，還有東西會 trigger 我們再去查嗎？還是就變成新的 cohort？」
兩者皆非，且查證後發現問題比 §10.10 原本描述的更深。

**（a）不是新 cohort。** cohort 與 Engine C 觀測是兩個獨立物件——前者記「我在追這條
主張」，後者記「這家公司的客戶集中度是多少」。事後補觀測是往同一個 cohort 補資料。

**（b）沒有任何東西會重觸發。** 全 repo 搜 `next_check`／`recheck`／`re_verify`／
觀測到期 —— **零結果**。人工觀測寫進 append-only ledger 後：沒有 `as_of` 以外的到期
概念；`financial_freshness_days`（14 天）只管自動抓的財務快照、不管人工觀測；
`manual_required` 就是永遠的 `manual_required`，直到有人主動去填。

**因此「查了但沒揭露」若只新增一個狀態、不加重查觸發，會比現狀更危險**——現狀是
「永遠卡著」（誠實地擋著），加了狀態卻沒出口則變成「永遠標著查過了」，而後者看起來
像已完成。這正是 D16（只有入口沒有出口）的形狀。

**而「不揭露」是會變的**：公司下一份年報可能就開始揭露，或簽下第一筆長約後必須揭露
backlog。自然的觸發點很明確——**下一份財報**。系統本來就在追 EDGAR、本來就知道每家
公司的 `financial.as_of`，**資料在，只是沒被拿來當觸發器**。這與 §10.7 的 `missing_data`
是同一個形狀：系統精確記下自己缺什麼，那份紀錄只被顯示、不被行動。

#### 修正後的完整修法（三件，缺一不可）

| # | 內容 | 狀態 |
|---|---|---|
| 1 | 新增「查了但公司不揭露」狀態，**必須附追源 receipt** | 未做 |
| 2 | **該狀態必須帶「下次重查觸發條件」** | 未做（本次追問才發現） |
| 3 | 觸發器綁下一份財報（`financial.as_of` 前進，或該 ticker 有新 filing 進 harvest） | 未做 |

**只做 1 不做 2、3 等於把「永遠卡著」換成「永遠標著查過了」。**

#### 本輪另外修掉的一個自造矛盾

§10.7 的 `reassessable_axes` 用 **section 層級**（`financial.status == observed`）判定
authority 是否恢復，對 `commercial_maturity` 太粗——財務快照有了不等於那兩筆觀測有了。
實測 co:iqe 同時被標成「commercial_maturity 可重評估」與「缺 customer_concentration／
backlog」，**同一份 brief 兩個欄位互相打臉**。已改為該軸直接檢查 checklist item 狀態。

判準：**當一個軸的 authority 是「特定幾筆資料」而非「整個 section」時，可用性檢查必須
下探到那幾筆**，否則會產出看起來精確的錯誤提示。
