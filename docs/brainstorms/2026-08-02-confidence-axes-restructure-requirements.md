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

| Cohort | 建立當下 market 狀態 | 性質 |
|---|---|---|
| **COHR** | `market_timestamp_future` | **即 §9.6 的 `as_of` 語意 bug**——日線 bar 時戳被判成「在未來」 |
| **IQE** | `market_adv_invalid` ＋ currency | GBp 未正規化；屬 2026-08-05 幣別修正之前的舊帳 |
| **AXT** | `market_unavailable` | 唯一一筆真正的抓取失敗 |
| LITE／META | `market_missing` | **未定**。凍結 bundle 顯示 currency 為 None，但兩者 2026-07-22 即已在 `config/company_identity.json`；可能只是 payload schema 版本差異，**尚無確證，不下結論** |

**結論：多數不是環境問題，是 repo 內部的資料語意問題。** 這個區別決定解法方向——
若是 sandbox 就該改環境；實際上解法在程式碼裡，而且其中兩項已經或即將被既有排程
修掉（§9.6 的交易日 freshness、2026-08-05 的幣別正規化）。

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

**理由是它比 paper 便宜且更早見效：** 不需要 coverage、不需要五軸、不需要 disproof，
訊號進來記一個價即可；且既有 cohort 可立即回填，不必等三個月累積樣本。
