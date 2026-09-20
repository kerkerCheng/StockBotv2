# 各 Phase 的 completion gate 逐項核對（逐字封存）

> 2026-09-20 從 [`docs/ROADMAP.md`](../ROADMAP.md) 搬出來的**原文**，一字未刪。
> 這裡是 Phase 1／3／5／6 **當初怎麼驗收的**逐項記錄，含每一項的查證命令與實測數字。
>
> **八項 gate 的定義本身留在 ROADMAP**（那是判準，不會腐壞）；
> 這些逐項核對是**歷史記錄**（那些數字是當時的實測值，不隨現況更新）。

### Phase 5 completion gate 逐項核對（2026-09-19；每項附查證命令）

⚠ **結論先寫：八項 gate 全過、驗收行四項全綠，Phase 5 於 2026-09-19 標 ✅。**

**驗收行那句話的讀法，2026-09-19 使用者定案：取「有賭注的檔都要有對稱的下檔」**
（原話「走後者吧」）。判準因此是**成對**而不是一份固定名單——
今天 payoff 與 downside 都是 AXTI／COHR／LITE **3/3**，沒有一檔有賭注卻缺下檔。
⚠ 另一個讀法（COHR ＋ 另外三檔＝4 檔，缺 SIVE.ST）**已被明確排除**：
SIVE.ST 今天連賭注都還沒寫，要它有下檔等於要求「沒下注也要說認錯值多少」。
**未來新寫賭注的檔，一樣要同時有下檔**——這條判準不隨名單變動而腐壞。
查證：`python -c "import json,glob;print(sorted(t.split(chr(92))[-1][:-5] for t in glob.glob('library/private/app/analyst_view/*.json') if not t.endswith('.meta.json') and ((json.load(open(t,encoding='utf-8')).get('view') or {}).get('downside') or {}).get('absence_kind') is None))"`
——應與有 payoff 的那組**完全相同**。

~~卡住的不是機制而是研究端的資料填寫~~（[631] 核准後已補齊；下面那段是當時的記錄，保留）
——與 Step 7.2 的 `multiple_horizon` 完全同形（L14-1：機制交付而下游真實資料只變了幾筆，
代表 binding constraint 不在這裡）。

| # | 項目 | 結論 | 依據 |
|---|---|---|---|
| 1 | Historical regression suite pass | **過** | golden **19 passed**（`python -m pytest -k golden`）；全套 **2,771 passed／1 skipped** |
| 2 | Runtime invariant audit pass | **過** | FAIL 0／PASS 13／檢查 **4,242 筆**（`python -m audit invariants`） |
| 3 | No unexplained semantic diff | **過（但有兩筆要講清楚）** | ①**新增**：`positions.json` 的 `bet_convergence` 鍵、`gap_closure.value` 的 `bet_since`、`consensus_progress` 的 `gap_at_start`；既有欄位一個都沒改名或改語意。②**既有值確實變了一筆，而它是修正不是漂移**：LITE 的 variant `closed_fraction` **+1.26% → missing**——那 +1.26% 來自 2026-09-14 的共識上修，比賭注寫下日早四天（INV-6）。③⚠ **順帶撈到一筆與本 Phase 無關的既有不一致**（`closure_terminal` 在 artifact 裡回不出第三種終局，APP 把 4 檔「等財報」標成「還沒做」）——**已記進 backlog 並寫出兩個方案，所以它不是 unexplained**；本輪沒修 |
| 4 | No new dual authority | **過** | V4 是**純消費端**：`bet_convergence()` 只吃已經算好的 `gap_closure`，**一個數字都不重算**；寫的是 ignored derived artifact。起算日的 SSOT 是 overlay 假設自己的 `created_at`（`bet_recorded_on()` 讀它，不另存一份「賭注日」欄位）。容忍窗的 SSOT 仍是 `alpha.fx.FX_AS_OF_TOLERANCE_DAYS`，心跳那行 **import 它而不重寫那個 3** |
| 5 | No silent-drop path | **過** | `bet_convergence` 逐項報 `scanned`／`n_bets`／`measurable`／`toward_us`／`away_from_us`／`unchanged`／`direction_undefined`／`not_yet_observable`／`no_bet`。⚠ 沒下注的檔**只進計數不進 rows**（19 筆空列會把 3 筆真資料淹掉），那是**不印不是不算**。artifact 是 V4 之前產的也**不得長得像空集合**——`artifact_state=stale_schema` 明說要重跑 materialize。查證：讀 `outcome_aggregate.json` 的 `bet_convergence` |
| 6 | Point-in-time tests pass | **過（本 Phase 的核心就是它）** | V4 修的正是一個 PIT 錯誤：賭注那條線先前用**判斷日**當起點，而賭注永遠晚於判斷（三檔沒有一檔同日）。修後起算日＝overlay 生效假設的**最晚** `created_at`；答不出來時誠實 `missing`，**不以判斷日頂替**（INV-6：不得靜默回傳當前值）。`PointInTime` audit PASS；守門測試 `tests/test_bet_convergence.py` 8 條 |
| 7 | All migrated lifecycle objects reachable | **過** | `QueueLiveness`／`QueueSegments` PASS。readiness 那一項的實證：由 research 層 settled 的檔數 **0 → 2**（012330.KS／NOVT），且兩檔的 `open_panels` 是空的、`settled_panels` 只有 `research`——**沒有那個 abstention 它們的 `terminal` 就是 `None`，永遠卡住**。查證：`python -c "from alpha.providers.closure import collect_backlog;import collections;print(collections.Counter(r.terminal for r in collect_backlog()[0]))"` |
| 8 | critical historical failure 已有 executable protection | **過** | 本 Phase 動到的形狀全部有可執行保護，不是文字保護：**L12（一表兩義）**——`unchanged`／`not_yet_observable`、`scanned`／`n_bets`、`window_days`／`days_waiting` 三對各有一條斷言（`tests/test_bet_convergence.py`）；**INV-6（PIT）**——起算日取最晚 override、缺席不頂替，兩條；**INV-5（不得憑空挑參數）**——`gap_at_start` 用攤開分母取代門檻，一條；**L16（SSOT 要跟著資料走）**——心跳的 FX 那行必須 import `alpha.fx` 的容忍窗，`tests/test_heartbeat.py` 斷言那個值出現在輸出裡 |

**驗收行核對（Phase 表第 5 欄逐字：「COHR 與三檔初始標的各有這些格；`outcome_aggregate.json` 多三個統計量」）：**

| 驗收項 | 現況 | 查證 |
|---|---|---|
| `outcome_aggregate.json` 多三個統計量 | **✅ 達標**（`power_law` 三量 2026-09-18 交付；本輪再多一個 `bet_convergence`） | 讀 `library/private/decision_lab/outcome_aggregate.json` 的鍵 |
| 歸零旗標「各有這些格」 | **✅ 達標：73/73 檔都有 `wipeout.lanes`**——它是機械算的，不需要研究 | `python -c "import json,glob;print(sum(1 for f in glob.glob('library/private/app/analyst_view/*.json') if not f.endswith('.meta.json') and ((json.load(open(f,encoding='utf-8')).get('overview') or {}).get('wipeout') or {}).get('lanes')))"` |
| 賭注（payoff）「各有這些格」 | **🔶 3 檔**（COHR／LITE／AXTI），70 檔 `not_yet_recorded` | 同上，讀 `overview.payoff.absence_kind` |
| **「判斷錯了值多少」（downside）「各有這些格」** | ~~🔴 只有 2 檔（AXTI／LITE）~~ **✅ 2026-09-19 [631] 核准後交付：3 檔（AXTI／COHR／LITE），與 payoff 完全對稱**；其餘 70 檔 `not_yet_recorded` | 讀 `view.downside.absence_kind`（⚠ 不是 `overview.downside`，那一格恆為 null） |

**✅ [631] 已執行（2026-09-19）：COHR 的 downside overlay。** 一手依據是同一份 8-K EX-99.1
（EDGAR 0001193125-26-346860）的 Q1 FY2027 指引**區間下緣**——而 variant 用的是**同一個區間的上緣**。
⚠⚠ **一跑就顯出這組假設的內部一致性**：三個 scenario 正好是那個區間的三個點——
**下緣 −0.00058（downside）／中點 +0.0221（base 取整為 +0.025）／上緣 +0.0437（variant 取整為 +0.045）**。
實測：downside EPS **7.9015**、fair value **197.54**、payoff **−37.8%**；首屏那把尺四個數到齊
（現價 317.36／沒賭對 223.60／賭對 243.97／**判斷錯了 197.54**）。
⚠ **寫的過程踩到一次 L15，值得逐字留著**：第一版引用了
`graph://edge/co:sumitomo_electric/supplies_to/co:nvidia`——那條邊確實存在且 externally_corroborated，
但**不在 COHR 的 ResearchContext 內**（context 以本檔為中心建），整筆因而被判 `unresolved_evidence` 拒用，
而 `downside` section 仍然 `status=available`、數字逐位等於 base、`overrides` 空——**看起來就像「還沒寫」**。
改引用 COHR 自己那條 `supplies_to co:nvidia`（它的 `sole_source` 已由 [627] 降為 false，
**那才是 disproof[1] 真正的載體**）之後才生效。
**同一個 change 修掉那個同形**：`build_fundamental_model` 現在把「還沒寫」與「寫了但一條都沒生效」
分成兩句話，後者逐字列出被拒的 `assumption_id` 與理由（守門測試 `tests/test_downside_overlay.py`）。
⚠ **驗收行還有一個歧義要使用者一句話定**：「COHR 與三檔初始標的」如果指 COHR＋另外三檔（＝4 檔），
那今天是 3/4（缺 SIVE.ST）；如果指「有賭注的檔都要有對稱的下檔」，今天是 **3/3 達標**。
**建議取後者**——D2 的對稱講的是「賭注與下檔成對」，而不是某個固定名單。

~~⚠ **D2 的對稱在程式碼結構上做完了，在資料上還沒有。**~~ 下面這段是 [631] 核准前的記錄，保留：
這不是把 gate 放寬就能過的——
寫 COHR 的 downside 需要那一檔自己的一手依據（`downside` 與 `variant` 套**同一組**型別層規則：
只能是核心 driver、必須 `independent`、必須至少一條 supporting 證據，**那第三條正是「這不是 bear case」的閘門**）。
而 COHR 的材料其實已經到位——它的 thesis 自 [629] 起是 `review_required`（disproof[1] 已觸發），
**重新評估本身還沒做**。所以這一格的下一步是研究不是開發，已鑄 pq2 編號請求核准。


### Phase 6 completion gate 逐項核對（2026-09-17；每項附查證命令）

| # | 項目 | 結論 | 依據 |
|---|---|---|---|
| 1 | Historical regression suite pass | **過** | golden 19 passed；全套 **2,620 passed／1 skipped** |
| 2 | Runtime invariant audit pass | **過** | FAIL 0／PASS 13／檢查 **4,160 筆**（`python -m audit invariants`） |
| 3 | No unexplained semantic diff | **過** | 新增一張 Engine C 表與一個 harvest 來源型別；既有表、既有 harvest 來源、既有 artifact 逐位未動（`python -m webapp status`） |
| 4 | No new dual authority | **過** | 月營收是**可重建的 ETL 表**（L10：MOPS 歷史頁按年月永久可查），不是 append-only judgment ledger、不需 pq2；重訊只 `register` lead，不自動 triage、不入圖、不寫 Engine C。台股清單的 SSOT 仍是 registry（`registry_taiwan_tickers()` 唯一來源） |
| 5 | No silent-drop path | **過** | `select_tickers` 逐列報 `input／accepted／filtered`，且把「沒有你的公司」與「代號解析不出來」**分成兩個計數**（版型變了才看得出來）；`harvest_mops` 對解析不出市場的 ticker 記 `parse_failed` 而不是跳過 |
| 6 | Point-in-time tests pass | **過** | `published_at` 永遠 NULL 且由 `published_at_basis` 自己宣告為什麼（MOPS 的「出表日期」是產表日不是公告日，`AGENTS.md` 明令不得冒充）；`disclosure_deadline` 是可機械推導的上界。`PointInTime` audit PASS；`test_report_date_never_becomes_published_at` |
| 7 | All migrated lifecycle objects reachable | **過** | **這正是本 Phase 第三件的內容**：黑洞 **3 → 0**，且「無到期的等待 N」成為心跳第 3 段的常駐計數器。`QueueLiveness`／`QueueSegments`／`Expiry` 全 PASS |
| 8 | critical historical failure 已有 executable protection | **過** | 本 Phase 動到兩個形狀：**F-31（Engine A 無 as-of）**——月營收的 `published_at`／`report_date`／`disclosure_deadline` 三欄分開，測試鎖住不得互相冒充；**L13-1（管子只接了一頭）**——`parked_without_expiry()` 的黑洞由計數器每天現形。**本 Phase 沒有新增任何 🔴** |

**結論：八項全部過，驗收行逐條達標，Phase 6 標 ✅。**

### Phase 3 completion gate 逐項核對（2026-09-17，五欄 amendment 核准後；每項附查證命令）

| # | 項目 | 結論 | 依據 |
|---|---|---|---|
| 1 | Historical regression suite pass | **過** | golden 19 passed（`python -m pytest -k golden`）；全套 2,617 passed／1 skipped |
| 2 | Runtime invariant audit pass | **過** | FAIL 0／PASS 13／檢查 4,154 筆（`python -m audit invariants`） |
| 3 | No unexplained semantic diff | **過** | 本 Phase 只新增 `account_scorecard` 這個 state kind 與 `Metric.revisit_after` 一欄；既有 artifact 逐位未動（`python -m webapp status` 其餘 kind 的 digest 不變） |
| 4 | No new dual authority | **過** | 計分表是**純消費端**：只讀 `pending_leads.json` 與 `config/signal_sources.json`，寫的是 ignored derived cache。tier 的寫入端**刻意不存在**（模組沒有寫入函式，測試斷言之），升降走一季一次的 pq2 manual |
| 5 | No silent-drop path | **過** | 每一欄都帶 `input／accepted／filtered／reasons`（`lead_filter`、`excess_return_filters`、`prior_30d_filter`）。查證：讀 `state/account_scorecard.json` 的 `lead_filter.reasons`（實測 `no_named_company 120`／`ticker_without_registry_company_id 40`） |
| 6 | Point-in-time tests pass | **過** | 每則點名以**貼文當天**的收盤價蓋章、超額報酬以 `called_on + horizon` 取價；`point_in_time` 欄位隨 artifact 落地。`PointInTime` audit PASS |
| 7 | All migrated lifecycle objects reachable | **過** | 兩種缺席都有明確終局：`insufficient_sample` 帶 `revisit_after`（實測 2026-09-27）、`capability_absent` 指出要建什麼。`QueueLiveness`／`QueueSegments` 全 PASS |
| 8 | critical historical failure 已有 executable protection | **過** | 本 Phase 動到的是 **F-20 的形狀**（截斷／缺席被當成 0）：守門測試 `test_time_bound_absence_carries_a_revisit_date_and_capability_absence_does_not` 鎖住「要建能力的缺席不得假裝只是等時間」，`tests/test_account_scorecard.py` 另有 22 條。**本 Phase 沒有新增任何 🔴** |

**結論：八項全部過，Phase 3 標 ✅。** ⚠ 與 Phase 1 相反——Phase 1 是八項全過但驗收行未達標所以不標；
Phase 3 是八項全過**且**驗收行（改寫後）逐條達標。

### Phase 1 completion gate 逐項核對（2026-09-17，Step 1.3；每項附查證命令）

| # | 項目 | 結論 | 依據（現跑，不抄） |
|---|---|---|---|
| 1 | Historical regression suite pass（golden fixtures） | **過** | `tests/fixtures/golden/` 14 份 fixture＋`tests/test_golden_fixtures.py` 在全套內綠。查證：`python -m pytest tests/test_golden_fixtures.py -q` |
| 2 | Runtime invariant audit pass | **過** | FAIL 0｜PASS 13｜檢查 4,087 筆。查證：`python -m audit invariants` |
| 3 | No unexplained semantic diff（old/new dual run） | **過** | Step 1.0 對 218 條「公司→向下」邊做過舊解析器 vs 新解析器 dual run：39 條改判全部有分類（升 31 條每條指得出一個解析到非主詞 registry 公司的 origin，違規 0；降 8 條全是主詞自家文件被括號註解污染成第三方的歸位）→ 0 筆 unexplained。Step 1.1／1.2 是**純新增**（新抓取器、新 SourceDoc、新邊），不改既有輸出路徑，依 §8「純新增不需 dual run」。⚠ 誠實補一句：當時的舊實作副本放在**未追蹤**的 `.pytest_tmp/old_bottleneck.py`，**那次 dual run 今天已不可重跑**，只剩 commit `69c8388` 的逐筆紀錄 |
| 4 | **No new dual authority** | **過** | 三樣新東西都沒有建立第二個 current-state authority：抓取器只寫 `library/raw/`，不落任何快取表；`product_line_revenue_share` 登記在 `config/engine_c_observation_fields.json` 由 Engine C 承擔，且**刻意不覆寫** `segment_revenue_share`（決策 D2——報導部門占比與產品線占比是兩個語意，不是同一真相的兩份）；`config/source_routes.json` 是 how-to 不是事實。查證：`python -c "import json;d=json.load(open('config/engine_c_observation_fields.json',encoding='utf-8'));print([f['field_name'] for f in d['fields'] if f['field_name']=='product_line_revenue_share'])"` |
| 5 | No silent-drop path | **過（本 Phase 的範圍內）** | 兩支新抓取器逐則報 input／accepted／filtered／reasons（`fetchers/mfn.py:165`、`fetchers/rns.py:165`，CLI 印到 stderr）；排序的 as-of 投影由 `AsOfProjection.reasons()` 報 `published_after_as_of`／`undated`（`query/bottleneck.py:630`）。⚠ **門檻 4 的 filter 在 CLI 上今天只印覆蓋率、不印逐檔 reasons——那是 Phase 4 的驗收項**；本次收尾以唯讀重量補出逐檔報表（見下） |
| 6 | Point-in-time tests pass | **過** | `audit invariants` 的 PointInTime：SourceDoc `published_at` 202/215（94.0%）、EdgeAssertion 可定日 657/674（97.5%）；13 份未定日**逐份列名**且擋住的邊有計數（L11-5 留 null 不猜）。三份新文件 `published_at` 皆 ≤ `retrieved_at`。查證：`python -m audit invariants --only PointInTime` |
| 7 | All migrated lifecycle objects reachable | **過** | audit 的 Lifecycle 598 筆／Expiry 85 筆（進行中的等待全部有到期日）／QueueLiveness 31 筆／QueueSegments 1,760 筆全 PASS；[579]–[585] 六個編號全部帶 `action/digest/commit/cohort` receipt 結案，池中無本 Phase 未決編號。查證：`python -m engine_b.todo list` |
| 8 | **critical historical failure 已有 executable protection** | **過（但編號對照不成立，見上）** | 本 Phase 實際動到的是**排序的證據分級**（F-20 截斷集合被當全集）與**新來源的定日**（F-31 Engine A 無 as-of）。兩筆在 §1 都已是 ✅：`alpha.contracts.RankedList` 強制帶 `full_ids`、`contains()` 只讀它，突變測試會紅；`PointInTimeUnsupported`＋`PointInTime` audit 今天 PASS。**本 Phase 沒有新增任何 🔴**。⚠ 未清掉也不在本 Phase 範圍的 🔴 仍有 7 筆（含 F-03） |

**結論：八項全部過，但 Phase 1 仍不標 ✅**——completion gate 過不等於驗收行達標。
驗收行明訂「可投資排序的 TW／TWO／ST 檔數仍為 0 就不得標完成」，2026-09-17 實測**仍是 0**。

#### 第 5 項的逐檔報表：門檻 4 的 filter（INV-3，2026-09-17 唯讀重量）

`input 222｜accepted 37｜filtered 185`——filtered 的理由只有三種：
`substitutability` 未填 **162**、`substitutability=3` **15**、`substitutability=2` **8**。
**沒有任何一檔是因為走不到需求錨被濾掉**（所有 TW／TWO／ST 公司的向下邊都接得到錨）。

| 公司 | 向下邊 | 現況 | **缺哪一份文件**（不得靠放寬門檻取代） |
|---|---|---|---|
| 上詮 `co:foci`（3363.TWO） | 1 → `tech:fiber_attach_unit` | sub 未填、自報·filing | Himax 或長約對手方的**客戶端具名確認**。一手只有自述目標（「長期目標係成為 CPO 光纖陣列元件之主要及重要供應商」）與產能投資；Hunterbrook 是媒體，依決策 C1 維持待判定 |
| 聯亞 `co:landmark_optoelectronics`（3081.TWO） | 1 → `tech:cw_dfb_laser` | **sub=3**（2026-09-17 新填） | 2026-08-26 四年長約的**條款**（最低採購量／獨家性／價格）。對照組是 IQE→Tower 判 4：雙向最低採購承諾逐字可讀。條款只可能由**對手方**（未具名的美國客戶）的法定文件揭露 |
| 華星光 `co:luxnet`（4979.TWO） | 1 → `tech:cw_dfb_laser` | sub=2 | **對照組，本 Phase 明訂不得改判**；2026-09-17 複查未動 |
| 全新 `co:vpec`（2455.TW） | 2 → `tech:cw_dfb_laser`、`tech:photodiode` | sub=2 ×2（本輪補邊） | 客戶端具名＋替代難度的正面證據。**現有一手證據方向相反**：全新在自家年報點名聯亞與 IQE 是同層競爭者 |
| IET-KY `co:intelliepi`（4971.TWO） | 2 → `tech:vcsel`、`tech:photodiode` | sub=2 ×2（本輪補邊） | 同上；英特磊自家年報點名全新與 IQE |
| Sivers `co:sivers_semiconductors`（SIVE.ST） | **15，其中 14 條 sub 未填** | `prod:els_8ch_module` 那條**已外部印證但 sub 未填**——這是最接近進榜的一格 | Ayar Labs 自家文件（`ayarlabs.com` 對本機 UA 回 403）；`tech:wdm_laser_16ch` 要它才能由供應商自報回到雙方聯合 |
| **穩懋 `co:win_semiconductor`（3105.TWO）** | 1 → `co:sivers_semiconductors` | **已是外部印證、sub 未填** | ⚠ **2026-09-17 收尾新發現，不在 Step 1.2 的七家工單裡**。證據等級已經夠，缺的只有 `substitutability` 的判讀依據 |
| Aehr `co:aehr_test_systems`（AEHR） | 1 → `tech:cpo_full_stack_test` | sub 未填；~~該 tech 節點**走不到任何需求錨**~~（2026-09-18：**已可達**，錨 `tech:ai_switch` 3 跳） | ~~先補「`tech:cpo_full_stack_test` → `tech:cpo`／`tech:ai_switch`」那條邊，否則補了 sub 仍然排序不可見~~ **2026-09-18 實測推翻：那條邊一直都在圖裡**（`tech:cpo --constrained_by--> tech:cpo_full_stack_test`），缺的是 traversal 不是邊——已隨 Phase 4 ①放閘修好。**現在缺的只有 `substitutability` 的判讀依據**，補了就進榜（what-if：第 27 名） |

查證：`python -m query.bottleneck --top-n 60`（表內不會出現任何 `.TW`／`.TWO`／`.ST`）。



