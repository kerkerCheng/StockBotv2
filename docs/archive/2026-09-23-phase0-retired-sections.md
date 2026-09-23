# Phase 0 退役章節逐字封存（2026-09-23，Step 0b.4 3/3）

> 由活文件（`docs/OPERATIONS.md`、`docs/ARCHITECTURE.md`）搬來的原文，**逐字**、不更新；活文件原位置只留退役 stub。
> 這些機制已於 Phase 0（ROADMAP 退役清單 A–H 組；決定紀錄 G1–G12）退役，本檔只供稽核與考古，不是現況。

## docs/OPERATIONS.md — OPERATIONS：`decision_review` 的 `go` 是全函數（原位於「Private authority 備份」節末）

**`decision_review` 的 `go` 是全函數（2026-08-26 起）——你只要下 `go`，不必分辨它屬於哪一類。**
`engine_b.todo.advance_decision_review` 依實際狀態自動選路；下面三條是它內部做的事，
**列出來是為了讓輸出可讀，不是要你自己選**：

| 狀態 | `go` 實際做什麼 |
|---|---|
| 有 research work order | dispatch 回 pq1（`outcome=dispatched`） |
| 無 work order、無 `user_decision` blocker | 以原 intent reassess，下次 sync 自動結案（`outcome=reassessed`） |
| 無 work order、仍有 `user_decision` blocker | 先 reassess，再以 `assessment_gap:<cohort>` 排入 pq1 並印出研究範圍（`outcome=queued_assessment_gap`） |

⚠ **四個 authority gate 不受影響**：graph admission、Engine C ledger 寫入、thesis mutation、
live 資本仍各走 `complete-*` 與 exact 人工核准。`go` 只自動化「研究要不要開始」這件可逆的事。

⚠ `assessment_gap:` 的 dispatch **沒有** Decision Store work order（work order 只在
`coverage_pending` 時建立，而 `assessment_blockers` 是 sizing 階段才算出來的），
`checkpoint_decision_review` 會跳過 work-order transition，但 terminal 仍須 receipt。
慣例同 `source_trace_review` 的 `lead:<id>` ref。

歷史：改成全函數之前，`go` 只覆蓋第一種情況，其餘一律拒絕——實測 9 個 REVIEW 有 **4 個**
會死在這裡（本機 Codex 與 Claude Code 各自獨立撞到）。兩條內部路徑是：

- **coverage 有 blocker** → `dispatch <n>` 派回 pq1 做 bounded research，完成後 `work <n> --to ...` checkpoint。
- **coverage 無 blocker、REVIEW 來自凍結 context 過期** → 直接
  `python -m decision_lab reassess <cohort_id> --intent <原 intent>` 產生新 decision，**下一次 `todo sync`
  會自己把該編號結掉**，不需要任何 verb。

⚠ **`--intent` 沿用該 cohort 上一筆 decision 的值**，讓評估條件不因呼叫端習慣而跳動。
（原本還有一個更強的理由：對先前是 `paper` 的 cohort 跑 `--intent research` 會讓研究完整度
由 `READY` 退成 `DATA_NEEDED`，純由參數造成。**那個陷阱已於 2026-08-29 從源頭修掉**——
`sizing.py` 改用嚴重度分類，diagnostic 級的 `execution_intent_research_only` 不再有改判權。）
查證：
`select json_extract(payload_json,'$.request.execution_intent') from system_decisions where cohort_id=? order by rowid desc limit 1`。

---

## docs/OPERATIONS.md — Engine D 決策

### Engine D 決策
```powershell
& '.venv\Scripts\python.exe' -m decision_lab evaluate-signal "<Signal>" --ticker <T> --intent research --format markdown
& '.venv\Scripts\python.exe' -m decision_lab reassess <decision_id|cohort_id> --assessment <a.json> --intent research --format markdown
& '.venv\Scripts\python.exe' -m decision_lab today --format markdown
& '.venv\Scripts\python.exe' -m decision_lab card <decision_id>
```

只有使用者明確要求才用 `--intent paper`／`live`；live 另加 `--confirm-holdings`。決策命令只在本機執行；遠端 chat 看決策才用 MCP 唯讀 `get_decision_brief`。

---

## docs/OPERATIONS.md — Sandbox impact review 結論（2026-09-09，研究閉環 P5：Daily 吃機械段）

### Sandbox impact review 結論（2026-09-09，研究閉環 P5：Daily 吃機械段）

五步：

1. **path＋side effect＋capability**：
   - `-m engine_b.cli consume-fired`：讀寫 `library/leads/pending_leads.json`／`event_watches.json`（同目錄 tempfile 原子替換）。無網路、無憑證、無 identity／ACL、無 private authority → **sandbox 內，不需 rule**（同 `event_watch sweep` 先例）。
   - `-m engine_b.todo reassess-stale --run`：讀 brief（Neo4j／Engine C／Sheet readonly）判候選；對候選跑 `decision_lab.workflow.reassess`（append 新 decision 到 private Decision Store，舊筆不動）；寫 `todo_pool.json`。→ **exact rule**。
   - `-m engine_b.todo standing-go --run`：同上資源；對 authorized 類型執行 `advance_decision_review`／`dispatch_source_trace_review`（與使用者 `go` 同一段程式）；寫 `todo_pool.json`、`pending_leads.json`、Decision Store work order。→ **exact rule**。
   - `-m webapp materialize --registry-listed`：既有 rule 的 prefix 已涵蓋（多一個旗標、同一組資源、多 43 檔 Neo4j／SQLite 讀取，寫 ignored derived cache）。
2. **canonical skill／prompt／本檔**：`crons/daily_brief_prompt.md` 步驟 3 加三支、步驟 8 加旗標、brief 加「今日自動清了」計數器；`skills/daily-brief/SKILL.md` Step 3／Step 7／模板同步；本節。
3. **最窄 rule**：`.codex/rules/stockbot-automations.rules` 由 17 條增為 **19** 條（`engine_b.todo reassess-stale`、`engine_b.todo standing-go`）。**相鄰不放行**：`engine_b.todo dispatch`／`resolve`（使用者動詞）、`engine_b.cli consume-fired`（不需要）、`-m engine_b.todo`（整包）。
4. **permission contract test**：`tests/test_codex_daily_permissions.py::test_mechanical_queue_segments_are_split_by_capability_not_by_convenience` 斷言三件事：consume-fired 不得出現在任何 pattern、兩條新 rule 存在、dispatch／resolve 仍不在；並斷言 prompt／skill 帶三支命令與 `--registry-listed`。
5. **smoke test**：三支命令以 exact 字串在本機各跑一次（2026-09-09：consume-fired requeued 0／reactivated 0；reassess-stale 候選 0；standing-go 候選 0——都是首跑清完後的穩態）。⚠ Codex sandbox 本身無法從互動 session 觸發：**真正的端到端驗收是下一次 06:30 排程的 brief 首屏出現「今日自動清了 N」那一行**——出現＝管子兩頭接上；沒出現＝rule 未載入或 prompt 沒跑到，依「Sandbox／private authority 排錯」處理。

不放寬：四個人工 gate 一個不動；`standing-go` 只對 config 明列的注意力 gate 類型動作，使用者明示 pending 與在等世界的一律跳過；付費永遠 exact 核准。

---

## docs/OPERATIONS.md — Sandbox impact review 結論（2026-09-05，Causal Fundamental Model）

### Sandbox impact review 結論（2026-09-05，Causal Fundamental Model）

| 入口 | side effect | OS／network capability | 判定 |
|---|---|---|---|
| `engine_c\etl_yfinance.py`（既有 fixed entry） | 同一次 `yf.Ticker` 多讀 `earnings_estimate`／`revenue_estimate` 兩個屬性，寫入新表 `consensus_estimates`（同一 SQLite authority） | **無新增**：同一網路主機（yfinance）、同一 DB、同一命令字串；解析不出會計行事曆的期間只印 WARN 不寫列 | rule 未動、fixed entry 數量未變 |
| `python -m alpha assumptions <T> --add/--retract` | append `library/private/alpha/assumptions/<T>.jsonl`（研究判斷，A3） | 本機檔案；private 目錄 | **互動專用**，不進 unattended rule（假設是 session 的判斷，排程不得自己寫） |
| `scripts/record_mechanical_observation.py --field fiscal_year_results／company_guidance` | 既有 mechanical 走廊，兩個新登記欄位 | 無新增 | 既有判定不變（mechanical 不需 pq2，但仍是互動寫入） |
| `python -m briefing alpha-card`／`decision_lab today` 的 Alpha Card 摘要 | 多讀 `consensus_estimates`＋兩個 ledger 欄位＋假設 ledger，執行純函式模型 | 無新增（同一 Engine C 連線、本機檔案） | 命令字串未變 |

查證（新入口不該出現在 rules）：
```powershell
Select-String -Path .codex\rules\stockbot-automations.rules -Pattern 'assumptions|record_mechanical'
```

---

## docs/OPERATIONS.md — OPERATIONS：Valuation Model／Base-case Implied Return／Entry Logic 的 sandbox review 與「怎麼跑」（六小節）

### Sandbox impact review 結論（2026-09-06，Valuation Model v1／Step 1）

| 入口 | side effect | OS／network capability | 判定 |
|---|---|---|---|
| `python -m alpha valuation <T> --list／--add／--retract` | append `library/private/alpha/valuation/<T>.jsonl`（估值判斷，A3）；`--list` 唯讀 | 本機檔案；private 目錄 | **互動專用**，不進 unattended rule（估值假設是 session 的判斷，排程不得自己寫） |
| `python -m briefing valuation <T> [--scenario …] [--as-of]` | 唯讀：與 `alpha-card` 相同的來源＋估值 ledger；情境只在記憶體疊事件，**不寫任何 authority** | 與 `alpha-card` 相同的本機資源；無新增網路主機、憑證或 identity／ACL | **互動專用**。新 CLI 名稱，不進 unattended rule |
| `python -m briefing alpha-card`／`decision_lab today` 的 Alpha Card 摘要（既有） | 多讀估值 ledger＋跑純函式 `build_valuation`；多一個 `valuation` section、精簡卡 `valuation` 欄與卡表一欄 | 無新增（同一 Engine C 連線、本機檔案） | 命令字串未變 |

查證（新入口不該出現在 rules）：
```powershell
Select-String -Path .codex\rules\stockbot-automations.rules -Pattern 'valuation'
```

### Valuation Model：怎麼跑（互動）

```powershell
# 1) 明示估值假設（session 寫；evidence_refs＝supporting，必須解析到 alpha-card evidence index；共識／市場倍數只能放 calibration_refs）
python -m alpha valuation COHR --add spec.json      # spec：period_end／value／basis／accounting_basis（gaap|non_gaap）／rationale／evidence_refs／calibration_refs／review_conditions
# 賭注（V0，2026-09-15）：營運或估值假設的 spec 加 "scenario": "variant" 即成 overlay——只寫有差異的核心 driver，
# 其餘沿用 base；型別層要求 derivation=independent ＋ 至少一條 supporting。範例：library/private/alpha/specs/cohr_variant_operating_margin.json
python -m alpha assumptions COHR --add spec.json    # {"scenario":"variant","driver":"operating_margin_delta",...}；--list 以〔variant〕標記
# 投資人短評（2026-09-15）：七格前因後果，文字 session 寫、數字 placeholder；範例 library/private/alpha/specs/cohr_brief.json
python -m alpha brief COHR --add spec.json          # 七格缺一不可；禁字與未登記 placeholder 會被拒；之後 materialize 才會上首屏
python -m alpha brief COHR --list
python -m webapp materialize --basket              # 籃子（V3）：只讀 ranking／positions／單檔三份 artifact 做 join；要排在它們之後跑
python -m alpha valuation COHR --list
python -m alpha valuation COHR --retract va_xxx --rationale "..."
# 2) 看結果（read model 第 13 節：方法／內部 EPS／假設／fair value／現價／gap／算式／敏感度／認識論分解／refresh state）
python -m briefing valuation COHR
python -m briefing valuation COHR --format json | python -c "import json,sys;v=json.load(sys.stdin);print(v['meta']['status'], v['fair_value']['value'], v['fair_value_gap']['value'])"
# 3) 情境與歷史視角
python -m briefing valuation COHR --scenario price_only      # fair value current、gap recalculate
python -m briefing valuation COHR --scenario graph_edge      # 引用該邊的估值／營運假設 review_required → fair value review_required
python -m briefing valuation COHR --as-of 2026-09-05         # 估值假設寫於 09-06 → created_after_as_of → missing
```

⚠ 沒有生效的估值假設就是 `missing`（不補 default）；口徑／期間與內部 EPS 不合是 `missing`＋「不合」理由；gap **不是**
expected return／upside／entry signal（型別沒有那些欄位，section 每次列 `gap_is_not`）。

**虧損公司（forward EPS 非正）改用 `ev_to_sales`（2026-09-09 P6，使用者定案）：** 同一個形狀——內部指標 × 明示倍數——
內部指標換成目標期間總營收，`fair_value = (internal_revenue × target_ev_to_sales − net_debt) / diluted_shares`；
淨負債取 Engine C 最新快照（`total_debt − cash_and_equivalents`，**現況近似**，公式字串會寫明），稀釋股數取 fundamental
model 生效的 `diluted_shares[total]` 假設。任一缺就 missing，不補 0。read model 自動選方法：本益比法回
`method_not_applicable` 且 ledger 有 `ev_to_sales` 假設才改跑；沒有假設就維持「方法不適用」並在理由裡說該寫哪一筆。
```powershell
# spec：period_end／value／basis／rationale／evidence_refs／calibration_refs，method 與 parameter 明寫，accounting_basis 固定 not_applicable
python -m alpha valuation AEVA --add spec.json     # {"method":"ev_to_sales","parameter":"target_ev_to_sales","accounting_basis":"not_applicable","value_date_convention":"target_period_end",...}
python -m briefing valuation AEVA                  # method=ev_to_sales；步驟多 net_debt／diluted_shares 兩格
```
兩桿拆解（EPS vs 倍數）對 EV/S 無定義，`eps_contribution`／`multiple_contribution` 會 missing 並說明原因。

### Sandbox impact review 結論（2026-09-06，Base-case Implied Return v1／Step 2）

| 入口 | side effect | OS／network capability | 判定 |
|---|---|---|---|
| `python -m alpha horizon <T> --list／--add／--retract` | append `library/private/alpha/horizon/<T>.jsonl`（horizon 判斷，A3）；`--list` 唯讀 | 本機檔案；private 目錄 | **互動專用**，不進 unattended rule（horizon 是 session 的判斷，排程不得自己寫、不得補 12 個月） |
| `python -m alpha valuation <T> --add`（既有） | spec 多一個可選欄位 `value_date_convention`（spot／target_period_end）；仍只 append private ledger | 無新增 | 既有判定不變（互動專用） |
| `python -m briefing implied-return <T> [--scenario …] [--as-of]` | 唯讀：與 `alpha-card` 相同的來源＋估值／horizon ledger；情境只在記憶體疊事件，**不寫任何 authority** | 與 `alpha-card` 相同的本機資源；無新增網路主機、憑證或 identity／ACL | **互動專用**。新 CLI 名稱，不進 unattended rule |
| `python -m briefing alpha-card`／`decision_lab today` 的 Alpha Card 摘要（既有） | 多讀 horizon ledger＋跑純函式 `build_implied_return`；`expected_return` section 改名 `implied_return`、估值 section 多 `value_date` 格、精簡卡多 `implied_return` 欄；**卡表欄位不變** | 無新增（同一 Engine C 連線、本機檔案） | 命令字串未變 |

查證（新入口不該出現在 rules）：
```powershell
Select-String -Path .codex\rules\stockbot-automations.rules -Pattern 'horizon|implied'
```

### Base-case Implied Return：怎麼跑（互動）

```powershell
# 0) 先確認估值假設有宣告時點語意（沒有就 append 一筆 supersede：spec 加 "value_date_convention": "target_period_end" 或 "spot"）
python -m alpha valuation COHR --list --format json | python -c "import json,sys;print([(r['assumption_id'], r['value_date_convention']) for r in json.load(sys.stdin)['records']])"
# 1) 明示 horizon 判斷（session 寫；period_end＝估值目標期間結束日、horizon_end＝明示實現日期；evidence_refs 必須解析到 alpha-card evidence index）
python -m alpha horizon COHR --add spec.json        # spec：period_end／horizon_end／basis／rationale／evidence_refs／calibration_refs／review_conditions
python -m alpha horizon COHR --list
python -m alpha horizon COHR --retract ha_xxx --rationale "..."
# 2) 看結果（read model 第 13a 節：現價／fair value／value_date／horizon／區間／simple／年化／total return／認識論分解／refresh state）
python -m briefing implied-return COHR
python -m briefing implied-return COHR --format json | python -c "import json,sys;r=json.load(sys.stdin);print(r['meta']['status'], r['price_return']['value'], r['annualized_price_return']['value'], r['horizon_window']['value'])"
# 3) 情境與歷史視角
python -m briefing implied-return COHR --scenario price_only    # 只有 implied_return recalculate；fair value／horizon current
python -m briefing implied-return COHR --scenario graph_edge    # 估值假設 review_required → fair value／implied_return review_required
python -m briefing implied-return COHR --as-of 2026-09-05       # 估值假設 v2 與 horizon 皆寫於 09-06 → created_after_as_of → missing
```

⚠ 四個輸入缺一就是 `missing`（現價含 bar_date、fair value 同單位、fair value 的 value-date 語意、生效的 horizon 判斷），**不補 12 個月、
不補下一會計年度**；horizon 到期即 stale，要新的判斷。它是 **base-case 隱含價格報酬**：不是機率加權期望報酬（沒有機率）、不是 total
return（沒有股利預測）、不是 entry signal（型別沒有那些欄位，section 每次列 `is_not`）。

**兩桿拆解（2026-09-09）：** 同一份輸出多三格 `eps_contribution`／`multiple_contribution`／`return_attribution`
（`alpha/implied_return/attribution.py`；恆等式 `(1+R) = (內部 EPS／共識 EPS) × (目標倍數／市場對共識付的倍數)`）。
拆不出來（沒有同期同口徑的 EPS 共識）就 `missing`＋`absence_kind`，**報酬本身不受影響**。讀法：負的報酬先看是哪一桿——
EPS 桿是圖該產生的東西；倍數桿依 `AGENTS.md`「隱含報酬的兩個桿」要指得出 re-rating 證據。
```powershell
python -m briefing analyst-view COHR --format json | python -c "import json,sys;v=json.load(sys.stdin);h={l['key']:l['datum']['value'] for l in v['headline']['lines']};print(h['price_return'], h['eps_contribution'], h['multiple_contribution'])"
```

### Sandbox impact review 結論（2026-09-06，Entry Logic v1／Step 3）

| 入口 | side effect | OS／network capability | 判定 |
|---|---|---|---|
| `python -m alpha entry-criterion <T> --list／--add／--retract` | append `library/private/alpha/entry_criteria/<T>.jsonl`（**投資人政策**，不是研究判斷）；`--list` 唯讀 | 本機檔案；private 目錄 | **互動專用**，不進 unattended rule。⚠ 這是全系統唯一會寫這個 ledger 的入口，且只由使用者執行——**排程不得替使用者決定要求幾 % 報酬** |
| `python -m briefing entry <T> [--sandbox-hurdle] [--scenario …] [--as-of]` | 唯讀：與 `alpha-card` 相同的來源＋估值／horizon／判準 ledger；`--sandbox-hurdle` 只在記憶體疊一筆 `author=sandbox` 的判準，**不寫任何 authority**（ledger 的 append 入口明文拒收 sandbox） | 與 `alpha-card` 相同的本機資源；無新增網路主機、憑證或 identity／ACL | **互動專用**。新 CLI 名稱，不進 unattended rule |
| `python -m briefing alpha-card`／`decision_lab today` 的 Alpha Card 摘要（既有） | 多讀判準 ledger＋跑純函式 `build_entry_assessment`；`entry_logic` 插座由 `NotModeledSection` 換成 `EntryLogicSection`、精簡卡多 `entry_logic` 欄；**卡表欄位不變** | 無新增（同一 Engine C 連線、本機檔案） | 命令字串未變 |

查證（新入口不該出現在 rules；十六條 fixed entry 數量未變）：
```powershell
Select-String -Path .codex\rules\stockbot-automations.rules -Pattern 'entry-criterion|briefing entry|hurdle'
```

### Entry Logic：怎麼跑（互動）

```powershell
# 0) 先看有沒有判準（沒有就是 missing——那是「投資門檻尚未宣告」，不是資料缺口）
python -m alpha entry-criterion COHR --list
# 1) 非持久驗算：只在記憶體疊一筆 hurdle 看門檻價會落在哪，**不寫任何 authority**
python -m briefing entry COHR --sandbox-hurdle 0.15
# 2) 真的要宣告成政策才寫 ledger（spec：value／basis＝investor_policy／rationale＋可選 reference_refs／supersedes_id）
python -m alpha entry-criterion COHR --add spec.json
python -m alpha entry-criterion COHR --retract ec_xxx --rationale "..."
# 3) 看結果（read model 第 13c 節：判準／要求報酬／現價／fair value／horizon／年化隱含／門檻價／gap／comparison／assessment）
python -m briefing entry COHR
python -m briefing entry COHR --format json | python -c "import json,sys;r=json.load(sys.stdin);print(r['meta']['status'], r['entry_price']['value'], r['hurdle_comparison']['value'])"
# 4) 情境與歷史視角
python -m briefing entry COHR --sandbox-hurdle 0.15 --scenario price_only   # entry_assessment recalculate；判準 current
python -m briefing entry COHR --sandbox-hurdle 0.15 --scenario graph_edge   # 上游 review 傳播；判準仍 current
python -m briefing entry COHR --as-of 2026-09-05                            # 上游缺 → missing
```

⚠ 它是 **analytical entry threshold**：`meets_analytical_hurdle` 只表示「現價 ≤ 門檻價」這個算術事實，
**不是 buy／sell、不是部位尺寸、不是資本許可**（型別裡沒有那些欄位，section 每次列 `is_not`）。
沒有明示判準就是 `missing`，**不補 10%／15%／20%**；`value_date` 與 `horizon_end` 不一致時算術照列但
`assessment=review_required`，不得當成 clean 的門檻價。

---

## docs/ARCHITECTURE.md — 6.2 Causal Fundamental Model（`alpha/fundamental/`，2026-09-05 Phase 2 v1）

### 6.2 Causal Fundamental Model（`alpha/fundamental/`，2026-09-05 Phase 2 v1）

**角色一句話：根據我們知道的，我們對這門生意明確假設了什麼，那些假設推得出什麼數字，
跟同期共識差多少。** 它回答的是「StockBot 的內部預測」，**不是**估值、預期報酬或進場邏輯
（那三者仍 `not_modeled`）。

```
Engine A 證據 ─┐                                  Engine C（A2，唯讀）
               ├─► OperatingAssumption[]（A3，private append-only ledger）   fiscal_year_results（基期）
session 判斷 ──┘        │ select_assumptions(as_of)                          company_guidance（指引，證據）
                        ▼                                                    consensus_estimates（FY 別共識）
                 build_bridge（確定性算術）◄──────────────────────────────── 基期觀測
                        ▼
                 ModeledMetric[]（revenue／operating_margin／operating_income／net_income／eps）
                        ▼ verify_consensus_basis ＋ compare_metric
                 ExpectationComparison[]（只在同期、同口徑、同幣別時有數字）
                        ▼
                 briefing/alpha_view（只選取）→ internal_fundamentals／earnings_bridge／expectation_gap
```

**誰擁有什麼（authority 分工，不得混）：**

| 東西 | 擁有者 | 住哪 |
|---|---|---|
| 假設（值、basis、rationale、evidence、created_at） | A3 研究判斷，session 明示 | `library/private/alpha/assumptions/<TICKER>.jsonl`（append-only；`python -m alpha assumptions`） |
| 算術（revenue → margin → EPS） | A3，`alpha/fundamental/bridge.py` | 純函式，版本 `fundamental-bridge/v1` |
| 基期實際、指引、FY 別共識 | A2 Engine C | `manual_observations`（`fiscal_year_results`／`company_guidance`，mechanical）、`consensus_estimates`（ETL） |
| 口徑核實與比較 | A3，`alpha/fundamental/compare.py` | 純函式 |
| 組裝 | `briefing/alpha_view`（read model） | 不算任何數字 |

**認識論分界（本模型最重要的一條）：** 「FY27 D&C 營收成長 +60%」是 session 判斷；
「FY27 分部營收 ＝ 基期 × (1 + 成長)」是確定性算術。每個輸出都同時帶
`calculation="deterministic"` 與 `input_dependency`（最弱輸入假設的知識種類）；LLM 不得直接
吐 EPS，只能寫假設。缺任何一條假設就是 `missing`，不補 0 成長、0% 利潤率。

**會計期間與口徑是身分：** `FiscalPeriod.end` 才是身分，`FY2027` 只是結束年命名慣例；
provider 的 `0y`／`+1y` 在 ETL 抓取當下解析成絕對日期（`shared/fiscal.py`）。EPS 共識的
GAAP／non-GAAP 口徑不靠慣例，靠 `year_ago_actual` 與一手財報稀釋 EPS 機械核對（COHR：5.61 ＝
non-GAAP，≠ GAAP 4.12）；核不出來就 `unverified`，不得相減。

**PIT 三道門：** 假設 `created_at <= T`、觀測 `recorded_at <= T`、共識 `captured_at <= T`；
builder 另核對 model 的 `as_of` 與 context 相符，不符拒收。歷史時點沒有假設就是 `missing`，
不偷用現在的假設重建過去的 gap。

**刻意不做（下一階段）：** DCF／reverse DCF、目標價、預期報酬、下檔、進場價、opportunity
ranking、毛利率／營業費用拆分、FCF、季度期間。`rank_bottlenecks()` 仍是唯一排序權威。

---

## docs/ARCHITECTURE.md — ARCHITECTURE：§6.4 Valuation Model／§6.5 Base-case Implied Return／§6.6 Entry Logic

### 6.4 Valuation Model（`alpha/valuation/`，2026-09-06 Phase 2 Step 1 v1）

**角色一句話：根據我們自己的內部 EPS 與我們自己明示的目標倍數，這門生意值多少；跟現價差多少。**
它回答的是「StockBot 的 fair value」，**不是**預期報酬、horizon、進場價、買賣、機率加權情境（Step 2 以後）。

```
alpha/fundamental（內部 FY 目標期間 EPS，含 input_dependency）─┐
ValuationAssumption[]（A3，private append-only ledger）─ select(as_of) ─┼─► build_valuation ─► ValuationResult
Engine C 現價（A2，唯讀；`build.context.market`）──────────────────────┘        │
                                                                    fair_value ＝ internal_eps × target_pe（不含現價）
                                                                    gap ＝ fair_value vs current_price（同單位才算）
                                                                    ▼
                                                  briefing/alpha_view（只選取）→ valuation section／精簡卡 valuation 欄
```

**方法選擇（audit 2026-09-06，用資料證明）：** 內部可靠的 forward metric 只有 FY 目標期間的稀釋 EPS（橋 v1）；沒有內部
FCF、D&A、EBITDA、資本支出、營運資金，`financial_snapshots` 的 `total_debt`／`cash` 也沒有會計年度身分——所以 EV/EBITDA、
FCF／DCF、reverse DCF **沒有資料可餵，不為完整硬做**。v1 唯一 method＝`forward_earnings_multiple`（parameter `target_pe`），
method／parameter 是封閉字彙（`alpha/valuation/contracts.py::METHOD_PARAMETERS`），多一個 method 就要多一段算術。

**誰擁有什麼：**

| 東西 | 擁有者 | 住哪 |
|---|---|---|
| 估值假設（method／parameter／值／basis／rationale／證據角色／created_at／supersede／retract／review_conditions） | A3 研究判斷，session 明示 | `library/private/alpha/valuation/<TICKER>.jsonl`（append-only；`python -m alpha valuation`） |
| fair value 算術＋gap | A3，`alpha/valuation/model.py` | 純函式，版本 `valuation-model/v1`；公式字串唯一定義處 `FAIR_VALUE_FORMULA`／`GAP_FORMULA` |
| 內部 EPS | `alpha/fundamental`（§6.2） | 估值層**照抄** `ModeledMetric`，不重算 |
| 現價 | A2 Engine C | `build.context.market`（已依 as-of 過濾）；報價單位取自 registry |
| 組裝 | `briefing/alpha_view`（valuation section） | 不含任何估值公式（`tests/test_valuation_model.py` 以竄改＋import／token 掃描守著） |

**與 `OperatingAssumption` 同一套 epistemic system（刻意）：** 同一組 `basis` 字彙、同一組 ref 角色（supporting／calibration／
comparison；**同期共識與市場倍數只能是 calibration**）、同一種 append-only／as-of／supersede 語意，**連選取器都是同一支**
（`select_assumptions` duck-typed）。差別只有三處：id 前綴 `va_`、`driver` 換成 `method`＋`parameter`、`accounting_basis`
必填且只能 gaap／non_gaap。它**不是**橋的 driver——倍數不是財務橋的一段算術，所以住自己的型別與 ledger。

**四條規則：** ① **沒有 hidden default**：ledger 沒生效倍數→`missing`；內部 EPS 缺→`missing`；不補、不由 LLM 補。
② **同期、同口徑才乘**：估值假設的 period／accounting_basis 必須與內部 EPS 相同，不合是「口徑不合」不是「缺假設」。
③ **price 不進 fair value**：現價只進 gap；依賴層 fair value 的 refs 不含現價 ref，policy 表 `fair_value` 沒有
`market_price`，所以 price-only 變化只讓 gap `recalculate`。④ **gap 不是 expected return**：型別沒有 horizon／報酬欄位，
read model 每次都列 `gap_is_not` 四條。

**Refresh 整合（沿用 `alpha/refresh`，不另建 freshness）：** 新 change class `valuation_assumption`（policy 表對 Q1–Q5
一格都不動）；新 artifact type `valuation_assumption`（判斷型，規則同營運假設）／`fair_value`／`fair_value_gap`
（確定性）；傳播沿 `assumption_ids` 一層，上游可以是 `oa_*` 或 `va_*`。實跑 COHR：內部 EPS 假設被取代→fair value
`recalculate`；估值假設被取代→`recalculate`；估值假設的 supporting edge 變了→假設 `review_required`→fair value／gap
`review_required`（`propagated_from` 指名）；price-only→fair value `current`、gap `recalculate`。

**PIT：** 估值假設 `created_at <= T`；內部 EPS 沿用 fundamental 的三道門；fundamental 的 `as_of` 與估值視角不符一律拒用
（INV-6）。實跑 COHR `--as-of 2026-09-05`：EPS 8.94 在、估值假設（09-06）`created_after_as_of`→`missing`；
`--as-of 2026-08-15`：無基期觀測→`missing`，JSON 內無任何 `va_*` id。

**認識論（回答「fair value 裡多少是算術、多少是判斷」）：** 算術＝橋＋乘法＋基期實際值（Engine C mechanical 觀測）；
判斷＝內部 EPS 底下的 7 條營運假設（COHR：3 session_judgment＋4 heuristic_proxy）＋1 條估值假設（session_judgment）。
給定內部 EPS，**整個 gap 就是 `target_pe / implied_multiple_at_price − 1`**——即「我們的倍數 vs 市場對我們 EPS 付的倍數」；
EPS 的判斷藏在 implied multiple 與市場對共識 EPS 付的倍數之差裡。`ValuationResult.epistemics` 把這個分解機器可讀化。

**刻意不做（Step 2 以後）：** entry logic、buy／sell、portfolio、機率加權情境、逐情境目標估值、
多 method（EV/EBITDA／DCF 要先有內部現金流）、跨標的比較、consumer UI。**horizon 與報酬語意自 2026-09-06 起住 §6.5。**

### 6.5 Base-case Implied Return（`alpha/implied_return/`，2026-09-06 Phase 2 Step 2 v1）

**角色一句話：從哪一天（現價的 bar_date）到哪一天（明示的 horizon_end），在什麼假設下（內部 EPS 的營運假設＋目標倍數＋
value-date 語意＋realization horizon），現價走到 fair value 的 base-case 隱含價格報酬是多少。**
名稱刻意用 **implied** 不用 expected：「expected」在統計上是機率加權期望值，本層沒有任何機率。

```
alpha/valuation（fair value、value_date、input_dependency）─┐
HorizonAssumption[]（A3，private append-only ledger）─ select(as_of) ─┼─► build_implied_return ─► ImpliedReturnResult
Engine C 現價（A2，唯讀；含 bar_date）─────────────────────────────┘        price_return ＝ fair_value / current_price − 1
                                                                        days ＝ horizon_end − bar_date
                                                                        annualized ＝ (1 + r) ** (365.25 / days) − 1
                                                                        ▼
                                                     briefing/alpha_view（只選取）→ implied_return section／精簡卡 implied_return 欄
```

**先回答 Step 1 沒回答的問題：223.60 是哪一天的值？** v1 估值契約只有 `target_period`（EPS 屬於哪一年）與 `as_of`（知識視角），
**答不出**「今天的 fair value（A）」還是「未來某日的 target value（B）」——兩種讀法算術相同、報酬語意完全不同。修法是最小擴充：
`ValuationAssumption.value_date_convention`（封閉字彙 `spot`／`target_period_end`，**沒有預設**；舊紀錄讀成 `unspecified`，
content-addressed id 不變）→ `ValuationResult.value_date`／`value_date_semantics`（`VALUE_DATE_FORMULA` 唯一定義處）。
fair value 的算術一格不動；**時點未宣告時報酬層拒算**（不猜）。COHR 的 25x 宣告為 `target_period_end`：223.60 是 2027-06-30 的值。

**誰擁有什麼：**

| 東西 | 擁有者 | 住哪 |
|---|---|---|
| horizon 判斷（目標期間／`horizon_end`／basis／rationale／證據角色／created_at／supersede／retract／review_conditions） | A3 研究判斷，session 明示 | `library/private/alpha/horizon/<TICKER>.jsonl`（append-only；`python -m alpha horizon`） |
| value-date 語意 | A3，估值假設宣告 | `ValuationAssumption.value_date_convention`（§6.4 ledger） |
| 報酬算術＋年化 | A3，`alpha/implied_return/model.py` | 純函式，版本 `implied-return-model/v1`；公式字串唯一定義處 `PRICE_RETURN_FORMULA`／`ANNUALIZED_RETURN_FORMULA`／`HOLDING_PERIOD_FORMULA` |
| fair value | `alpha/valuation`（§6.4） | 報酬層**照抄**，不重算 |
| 現價 | A2 Engine C | 與估值層共用同一個 `CurrentPrice`（`bar_date` 是 horizon 起點） |
| 組裝 | `briefing/alpha_view`（implied_return section） | 不含任何報酬公式（`tests/test_implied_return.py` 以竄改＋import／token 掃描守著） |

**與營運／估值假設同一套 epistemic system（刻意）：** `HorizonAssumption` 用同一組 `basis` 字彙、同一組 ref 角色、同一種
append-only／as-of／supersede 語意、**同一支選取器**；id 前綴 `ha_`；`period` 是它服務的估值目標期間（估值換期間，horizon 就是
`other_period`，不沿用）；`horizon_end` 是明示日期，不是「12 個月」這種相對量；寫下時已過去的 horizon 契約拒收（INV-2）。

**五條規則：** ① **四個輸入缺一就 `missing`**：現價（含 bar_date）、fair value（同單位）、value-date 語意、生效 horizon；沒有 hidden
default。② **horizon 已過就不是報酬**（`horizon_end <= bar_date` → missing＋「需要新的 horizon 判斷」）。③ **只有 price return**：
`total_return_status` 恆 `not_modeled`（無股利／分配預測能力），不得冒充。④ **沒有機率**：型別裡沒有 probability-weighted 欄位。
⑤ **算術確定、輸入是判斷**：`calculation=deterministic`；`input_dependency`＝fair value 的輸入依賴與 horizon basis 中最弱者。
另有 `alignment`（`aligned`／`horizon_after_value_date`／`horizon_before_value_date`／`spot_value_realized_over_horizon`）只現形不阻擋。

**Refresh 整合（沿用 `alpha/refresh`）：** 新 change class `horizon_assumption`（Q1–Q5 與假設層一格不動）；新 artifact
`horizon_assumption`（判斷型，帶 `expires_at=horizon_end`——`ArtifactDependency.expires_at` 是本步新增的絕對到期欄位，到期即
`stale`）／`implied_return`（確定性；policy `{market_price, financial_actual}`；依賴＝fair value 的依賴＋現價 ref＋horizon）。
傳播上游泛化到 `ASSUMPTION_ARTIFACT_TYPES`（`oa_*`／`va_*`／`ha_*`）。實跑 COHR：price-only→只有 implied_return `recalculate`；
估值假設 review→implied_return `review_required`（`propagated_from` 指名）；horizon 被取代→`recalculate`；到期→horizon `stale`
→報酬 `stale`；無關的圖變化→`current`。

**PIT：** horizon `created_at <= T`；估值的 `as_of` 與報酬視角不符一律拒用（INV-6）；horizon 起點是現價的 `bar_date`（≤ T）。
實跑 COHR `--as-of 2026-09-05`：估值假設 v2 與 horizon 皆 `created_after_as_of` → `missing`，JSON 無 `ha_*`。

**認識論：** 算術＝報酬／年化／持有期間／估值／橋；判斷＝營運假設＋估值假設（含 value-date 語意）＋horizon；觀測＝現價＋基期實際值。
`ImpliedReturnResult.epistemics.one_sentence` 把「從哪天、到哪天、在什麼假設下」機器組成一句話。

**刻意不做（v1 限制）：** buy-sell／portfolio／consumer UI／機率加權情境／Valuation v2（historical normalized
multiple、peer multiple、growth durability、margin／ROIC quality、cycle position——backlog 不遺失）／total return／跨標的比較。
**Entry Logic 自 2026-09-06 起住 §6.6。**

### 6.6 Entry Logic（`alpha/entry/`，2026-09-06 Phase 2 Step 3 v1）

**角色一句話：已知現價、fair value（含時點語意）、明示 horizon 與**明示的要求報酬判準**，回答
「什麼價格以下才滿足這個報酬門檻」，以及現價相對那個門檻價在哪裡。**
它**不是** buy／sell、不是部位尺寸、不是資本許可——名稱刻意叫 **analytical entry threshold**。

```
alpha/implied_return（現價、fair value、value_date、horizon、年化隱含報酬）─┐
EntryCriterion[]（投資人政策 ledger）── select(as_of) ────────────────────┼─► build_entry_assessment ─► EntryAssessmentResult
                                                                            │   entry_price ＝ fair_value / (1 + h) ** (days / 365.25)
                                                                            │   gap ＝ current_price / entry_price − 1
                                                                            ▼   comparison ＝ current_price <= entry_price ? meets : above
                                              briefing/alpha_view（只選取）→ entry_logic section（第 13c 節）／精簡卡 entry_logic 欄
```

**先回答「hurdle 是誰的？」（動工前的 authority 盤點，2026-09-06）：** required return **不是公司事實**
（A1／A2 不擁有它）、**不是研究對公司的信念**（A3 的內容是「我們相信這家公司會怎樣」，不含「我要求幾 %」）、
**也不是資本決策**（A5 是「當時憑什麼決定、使用者選了什麼」，append-only 且 live 100% 人工——宣告一個 hurdle
不授權任何資本、不建立任何決策紀錄）。它回答的是「**我的資本**要求多少報酬才值得」，主詞是投資人。
結論：新增第三種知識種類 **`investor_policy`**，在本層與 A2 現價同一種地位——**注入的輸入**，只讀、不猜、
不補預設、不自動改。**沒有把 capital permission 偷塞進 Alpha。**

| 東西 | 擁有者 | 住哪 |
|---|---|---|
| 要求報酬判準（`convention`／值／`basis`／rationale／`reference_refs`／`created_at`／supersede／retract） | **投資人政策**（使用者明示） | `library/private/alpha/entry_criteria/<TICKER>.jsonl`（append-only；`python -m alpha entry-criterion`） |
| 門檻價／gap／comparison 算術 | A3 確定性導出，`alpha/entry/model.py` | 純函式，版本 `entry-model/v1`；公式字串唯一定義處 `ENTRY_PRICE_FORMULA`／`PRICE_TO_ENTRY_GAP_FORMULA`／`HURDLE_COMPARISON_RULE` |
| fair value／horizon／年化隱含報酬 | `alpha/implied_return`（§6.5） | 本層**照抄**，不重算 |
| 「該不該買、買多少」 | **使用者**（成為資本動作時才是 A5） | 本層型別裡**沒有那個欄位** |

**六條規則：** ① **兩個輸入缺一就 `missing`**：可用的 implied return、生效的判準；兩者的理由**分開寫**——
判準缺席是「**缺投資門檻判斷**，不是資料 ETL 缺口」，**不 invent 10%／15%／20%**。② **判準是注入的輸入**：
`basis` 封閉字彙只有 `investor_policy`（開放它就等於讓 hurdle 變成「對公司的判斷」）；`criterion_basis` 與
研究側的 `input_dependency` **分兩格**，不混。③ **判準刻意沒有 `period`**——要求報酬不隨估值換會計年度而失效；
也**刻意不共用 `select_assumptions`**（那支以會計期間為身分並要求證據解析到公司 evidence index，而投資人的
機會成本本來就不在那裡；硬套會製造「換了年度 hurdle 就 other_period」的假失效）。④ **alignment 不對齊不得
冒充 clean**：`aligned`／`spot`（明示）→ `clean`；`horizon_before/after_value_date` → 算術照列但
`assessment=review_required`＋理由，型別層擋住「不對齊卻標 clean」。⑤ **只有算術比較，沒有 action**：
`meets_analytical_hurdle` 就是 `current_price <= entry_price`（等號歸 meets——門檻價的定義就是「恰好滿足」）。
⑥ **型別層在 import 當下擋住資本語意**：`_assert_no_capital_fields` 掃描 `FORBIDDEN_POSITION_TOKENS` ＋
buy／sell／order／action／trade／permission，長出那種欄位是 import 失敗不是 lint 警告。

**Refresh 整合（沿用 `alpha/refresh`）：** 新 change class `entry_criterion`（Q1–Q5、假設層、fair value、
implied return **一格不動**——投資人政策變了不代表對公司的看法變了）；新 artifact `entry_criterion`（判斷型，
**`refs` 為空**：判準沒有 supporting evidence，所以結構事件／共識／指引都不會動它）／`entry_assessment`
（確定性；policy `{market_price, financial_actual}`；依賴＝implied return 的依賴＋criterion）。
實跑 COHR：price-only→`entry_assessment` `recalculate`、判準 `current`；graph_edge／consensus／new_actual／
disproof→上游 review 傳播成 `review_required`，**判準始終 `current`**；horizon 到期→整條 `stale`。
⚠ **criterion 同時列在 `refs` 與 `assumption_ids`，但今天只有 refs 那條會發動**（突變實測）：判準不可能變成
`review_required`／`invalidated`，第二輪傳播對它是 no-op——`assumption_ids` 留著是為了依賴宣告完整，
**不是一道已量測的守衛**（L14 同樣適用於自己寫的守衛）。

**PIT：** 判準 `created_at <= T`；上游 implied return 的 `as_of` 與本層視角不符一律拒用（INV-6）。
實跑 COHR `--as-of 2026-09-05`／`2026-08-15`：上游缺 → `missing`；`--as-of 2026-09-06` → available。

**Sandbox 驗算：** `python -m briefing entry <T> --sandbox-hurdle 0.15` 只在**記憶體**疊一筆 `author=sandbox`
的判準（`persisted=false`、warning 標明），**不寫任何 authority、不進變更偵測**；ledger 的 append 入口
明文拒收 `author=sandbox`——**demo 好看不是寫入 authority 的理由**。

**刻意不做（v1 限制）：** buy／sell／hold、position size／capital allocation／order、portfolio permission、
多 convention（total return hurdle、IRR、風險調整後門檻都要先有各自的算術與資料）、跨標的比較、
判準的到期語意（今天沒有 `expires_at`）；Analyst Consumer 已於 Step 3.5 交付（§6.7），APP／API 仍未做。

---

---

## docs/ARCHITECTURE.md — 6.10 賭注：variant scenario → payoff（`scenario` overlay，2026-09-15 V0）

### 6.10 賭注：variant scenario → payoff（`scenario` overlay，2026-09-15 V0）

**角色一句話：base 回答「市場把 base case 定價成怎樣」，賭注回答「如果我們的差異看法對了，值多少」。**
兩者並排，差額就是這個賭注本身的價值。

```
OperatingAssumption／ValuationAssumption ledger（同一本 JSONL，多一個 scenario 欄位：base／variant）
        │  select_scenario_assumptions：base 的生效假設 ← 同 key 的 variant 生效假設覆蓋（overlay）
        ▼
build_fundamental_model(scenario=variant) → build_valuation(scenario=variant) → build_implied_return
        │  **同一條橋、同一套估值與報酬算術**——差別只在餵進去的假設集合
        ▼
PayoffScenarioSection（read model 第 13d 節）→ AnalystView.bet（optional panel）→ APP 結論卡「如果我們的賭注對了」
```

**四條規則（型別層強制，不是自律）：**
1. **variant 只能是核心 driver**（`revenue_growth`／`operating_margin_delta`）且 `derivation=independent`：
   由共識反解或抄公司指引的值結構上不可能與市場不同，寫成 variant 就是把佔位冒充成賭注。
2. **至少一條 supporting 證據**（calibration 不算）。「如果對了」必須指得出什麼在支撐「對」。
3. **overlay 不是取代**：base 與 variant 各自獨立選取（各自 as-of／supersede／證據解析），寫入端擋跨 scenario
   的 supersede。既有紀錄沒有 `scenario` 欄位 → 讀成 base；`scenario` 只在非 base 時參與 content-addressed id，
   所以**既有 ledger 的每一個 id 一個位元都不變**。
4. **它是條件句，不是機率加權**：沒有 bull／bear、沒有機率；`PAYOFF_IS_NOT` 逐字寫在 section 裡。
   沒寫賭注是 optional 缺席（`not_yet_recorded`），readiness 不變差，也不得補一個 bull case。
   ⚠ 2026-09-16 D2：多一個**對稱** overlay——「判斷錯了值多少」＝反證觸發後的假設套同一條橋（同一套算術、
   同樣的型別層證據要求），與 variant 並排；它**仍不是 bear case、仍沒有機率**。
   **2026-09-18 已交付**：`ASSUMPTION_SCENARIOS` 加第三個值 `downside`，`OVERLAY_SCENARIOS`
   ＝`(variant, downside)`，上面四條規則**逐條套用到兩者**（型別層的三條由
   `OperatingAssumption`／`ValuationAssumption` 共同強制）。
   落地點：`_payoff_section(copy=...)` 一個函式兩個實例、`_overlay_panel()` 一組 lines 兩個 panel、
   read model 的 `downside` 由 `NotModeledSection` 換成 `PayoffScenarioSection`、
   APP 結論卡與尺各多一端。⚠ **`PayoffScenarioSection` 的欄位名因此改成中性的
   `scenario_internal_eps`／`scenario_fair_value`**——欄位名是結構、`Datum.key` 才是身分，
   兩者脫鉤，所以 analyst view 的 line key（`variant_fair_value` 等）與 APP 一個字都沒動。
   ⚠ **刻意不強制 downside 假設指名某一條 disproof**：反證住在 `AlphaSignal.disproof_conditions`
   （A3，可重算、沒有穩定 id），從 append-only 的假設 ledger 指過去會造出一個會斷的跨 authority
   引用。要求「指得出什麼在支撐這個值」的閘門由 `supporting_refs` 承擔——它是同一件事的可機械驗證版本。

**為什麼不做成第二本 ledger：** 賭注就是「同一條假設的另一個值」，它的身分（driver／scope／period）與 base 完全相同，
差的只有值與證據；分成兩本會讓 as-of／supersede／證據解析長出兩份規則（L16）。Abstention 分開是因為它**結構上不能帶值**；
variant 恰好相反，它就是一個值。

**入口：** `python -m alpha assumptions <T> --add spec.json`（spec 帶 `"scenario": "variant"`；估值假設同）；
`--list` 以 `〔variant〕` 標記。read model／analyst view／APP 自動長出賭注段，不需要另跑任何東西。

~~**刻意不做（留給 V1–V4，見 ROADMAP）：** 催化劑連到 variant 假設、gap-closure 時序、`realized` 出口、
籃子頁與 filter 式首選、variant 收斂納入 outcome。~~
（V1–V3 已於 2026-09-15 交付，見 §6.13；V4「variant 收斂納入 outcome」併入 ROADMAP Phase 5 的量測項，2026-09-16。）

---

## docs/ARCHITECTURE.md — 6.13 賭注 V1–V3：熟成度、市場承認、籃子（2026-09-15）

### 6.13 賭注 V1–V3：熟成度、市場承認、籃子（2026-09-15）
| 件 | 住哪 | 一句話 |
|---|---|---|
| 熟成度（V1） | `Catalyst.resolves` → builder 的 `catalyst_quantitative_link` | 催化劑指名它裁決哪幾條假設；state＝只看事件日期與 ledger created_at（resolved／due／pending／unlinked），不解析散文 |
| 市場承認了嗎（V2） | `alpha/gap_closure.py` → `expectation_gap.gap_closure`／`consensus_series` | 共識自判斷日以來朝我們移了幾成；起點等於我們的值時 None 不是 0；量測不是訊號 |
| 目標價比較（V2） | `implied_return.target_reached` | 現價 ≥ 目標價＝「高於」，同時涵蓋市場比我們樂觀與該收割；只表示該重看，不是賣出 |
| 兌現出口（V2b） | `thesis/pending_lifecycle.py::ALLOWED_TRANSITIONS`＋`lifecycle_schedule.is_due` | `realized`：active／watch → realized → retired／revised；恆視為到期。進入由人提案（thesis mutation gate），`target_reached` 只提醒 |
| 籃子（V3） | `webapp/basket.py` → state kind `basket` → `#/basket` | ranking 去重順序 × overview × positions 的 join；首選＝filter（有賭注、payoff 為正、裁決點在目標價日期前），INV-3 逐檔報理由 |
⚠ **首選是 filter 不是分數。** 排序權威仍是 `rank_bottlenecks()`；籃子只在那個順序上套三條可機械驗證的條件。沒有一檔通過就 `top_pick=null`＋理由計數——今天正是如此。
⚠ 2026-09-16 D3：`realized` **降為提醒，不觸發出場**——出場只認反證；lifecycle 字彙不動，改的是它的後果（ROADMAP Phase 5）。
⚠ 2026-09-16 D11：首選的三條條件排定換成漏斗條件（覆蓋家數上限、市值上限、瓶頸業務占營收下限、至少一條外部印證的瓶頸邊、
入圖前 30 天漲幅上限、12 個月內指名假設的催化劑；ROADMAP Phase 4）；落地前沿用三條。籃子空就空，不得放寬。
⚠ **`basket` 必須在 ranking／positions／單檔之後 materialize**（它只讀那三份 artifact，不連 DB）；daily 收尾命令已加 `--basket` 在最後。

---
