# Historical Failure Matrix — Regression Constitution

> **性質：** Phase 0 產出物。本檔的目的**不是保留舊 patch，是把每次事故背後的 invariant
> 提升成新架構的 domain contract**。
>
> **核心原則：這次 refactor 可以丟掉歷史 implementation，不能丟掉歷史教訓。**
> 目標是讓未來的 agent 即使完全不知道當年發生過什麼，**也沒有辦法再次寫出同一類 bug**。
>
> 資料來源：`AGENTS.md` L1–L16、`docs/archive/roadmap-pre-alpha-refactor.md`「已撤回的診斷」、
> `docs/solutions/`（9 篇）、126 個測試檔的斷言與 docstring、程式碼註解。

## 欄位對照

每筆事故的 11 個要求欄位分佈如下（避免 11 欄表格不可讀）：

| 要求欄位 | 在本檔哪裡 |
|---|---|
| Failure ID／description／symptom／root cause／previous fix | §1 各 class 表的前兩欄 |
| Learned invariant | §1 第三欄，並在 §2 收斂成六條 hard invariant |
| New architecture owner | §1 第四欄 |
| Executable regression test | §1 第五欄（**現況**，非目標） |
| Runtime audit | §3（invariant → `audit invariants` check 對照） |
| Migration risk | §1 第六欄 |
| Status | §1 第六欄的圖示：✅已保護／🟡部分／🔴僅文字 |

**🔴 的定義（本檔最重要的產出）：** 該 lesson **只存在於 Markdown，沒有任何會紅的檢查**。
依 §7 的 completion gate，**🔴 未清零前不得宣稱對應 phase 完成**。

---

## 1. 事故矩陣

### 1.1 F-IDENT — Identity 不一致

> **共同形狀：ticker 被當成 entity identity，而 ticker 是可變的 external identifier。**

| ID | 症狀 → 根因（日期） | Learned invariant | 新 owner | 可執行保護（現況） | 風險／狀態 |
|---|---|---|---|---|---|
| **F-01** | 週掃漏掉 Sivers 的圖內比對。憑公司名猜 `co:sivers`，實際是 `co:sivers_semiconductors`（2026-07-21） | **`co:*` 永遠查 registry，不得由名稱推導。**「ID 沒解析對」與「圖中真無此公司」是兩個不同的 claim，不得默默跳過 | `identity/` （唯一 authority，不隨重構搬家） | `test_identity_registry.py::test_neutral_registry_preserves_known_company_mappings` | 🟡 保護的是 mapping 正確性，**沒有保護「未命中時必須區分兩種原因」** |
| **F-02** | LSE 標的行情永遠 quarantine。`currency` 同時是報價單位（GBp）與結算幣別（GBP）（2026-08-05） | **報價單位 ≠ 結算幣別。**⚠ 而且「修正」成 ISO code 會**通過所有驗證、清掉所有 blocker，卻餵出差 100 倍的價格**——比原本整份 quarantine 危險得多 | `identity/currency.py` ＋ `config/currency_units.json` | ✅ `test_currency_units.py` 11 條，含 `test_registry_fails_closed_on_unregistered_quote_unit`、`test_case_sensitive_lookup_keeps_gbp_and_gbp_pence_distinct` | ✅ 已保護。**這是全 repo 最好的一組 identity 測試，`EvidenceRef`／`InstrumentId` 應照抄它的 fail-closed 形狀** |
| **F-03** | TSMC cohort 恆 `market_missing`／`fx_missing`，被誤診為「ETL universe 缺 TSM」。真因是 registry 缺 `market_currency` → identity 判 partial → 整段 market/fx fetch 被跳過（2026-09-01） | **identity 的部分缺漏不得靜默關掉整條下游管線。** 缺 execution metadata 只該是該 lane 的 blocker | `identity/` ＋ `alpha/providers/` | 🔴 **無**。修法是補兩筆 config，沒有斷言防止下一個欄位再犯 | 🔴 **高**：重構時 `ResearchContext` 會新增 identity 欄位，同一形狀極易復發 |
| **F-04** | 圖 90 家 vs registry 98 家；`co:openlight` 在圖不在 registry＝A→C join-key 契約破口（2026-09-02） | **圖 ∖ registry 必須恆為 0。** registry ∖ 圖 可以非 0（未 onboard／SPAC shell），兩者語意不同不得合併 | `identity/` ＋ `loader/validate.py` | ✅ `health_audit` 硬斷言 ＋ brief 首屏常駐計數器 ＋ prepare 端 fail-closed | ✅ 已保護（三層）。**重構不得只搬 loader 而漏掉那個計數器** |
| **F-05** | Sivers 三層 symbol：研究用 `SIVE.ST`（SEK）、Sheet 用 `FRA:2DG`（EUR）、provider 用 `2DG.F` | **一個 entity 可有多個 external identifier，且分屬不同用途（research／execution／provider），不得互相冒充** | `identity/execution.py` | 🟡 `test_identity_registry.py::test_application_identity_composes_sheet_alias_without_second_mapping` | 🟡 有保護但**沒有「禁止 downstream 自建 normalization」的掃描測試** |

### 1.2 F-LIFE — Lifecycle 不一致

| ID | 症狀 → 根因（日期） | Learned invariant | 新 owner | 可執行保護（現況） | 風險／狀態 |
|---|---|---|---|---|---|
| **F-06** | COHR 的 disproof 觸發時拿不到 `claim_correctness`——cohort 07-25 已 `expired`，再次結案拋 `terminal epoch already has a different outcome`。這是 outcome 長期 0/8 的成因之一（2026-08-19） | **terminal 不等於死亡。** 已終結的 object 仍可能收到新事實，必須有明確的**重開路徑**（append 新 epoch，不覆寫舊的） | Engine D `outcomes.py`（`reopen_lifecycle_epoch`） | 🟡 `test_decision_outcomes.py` 有 epoch 測試 | 🟡 **中**：`AlphaSignal` 也會有 lifecycle，需同樣的重開語意 |
| **F-07** | 三次 `decision_lab close --terminal-status revised` **全部成功回傳**，然後編號原封不動重生。`revised` 在封閉字彙裡刻意**不是**終態（開新 epoch）——程式碼從頭到尾都對，是挑錯了值（2026-08-11） | **參數名對它的所有合法值做了統一斷言時（`terminal_status`／`is_deleted`／`final_state`），必須有一個值不符合那個斷言的檢查。** 操作成功回傳 ≠ 意圖達成 | Engine D | 🔴 **僅文件**（`docs/solutions/lifecycle-terminal-verbs.md`） | 🔴 **高**：新架構會新增多個 lifecycle 字彙，這個形狀必然重現 |
| **F-08** | 兩套 lifecycle 互不知道：`thesis/lifecycle.json`（3 條，L7 五態）vs Decision Store `probe_lifecycle_epochs`（13 epoch，四態）。`catalyst_watch.py` docstring 已載明是「既有的整合縫隙」 | **兩個 lifecycle 並存是允許的，前提是寫下它們各自管什麼、以及誰不管什麼。** 未書面化的並存＝縫隙 | research thesis → `alpha/thesis/`；decision case → Engine D | 🔴 **無**（只有 docstring） | 🟡 **中**：重構正好是把這句話寫下來的時機 |

### 1.3 F-QUEUE — Queue liveness：接了一頭的管子

> **這是本 repo 最高頻的事故類型（8 筆）。共同形狀：元件會動、端到端沒有產出。**
> 對應 L13。**成功與失敗在同一個訊號上同形**——空集合、沒有 in-flight 狀態、回傳 OK
> 都同時代表「成功但無結果」與「根本沒跑」。

| ID | 症狀 → 根因（日期） | Learned invariant | 新 owner | 可執行保護（現況） | 風險／狀態 |
|---|---|---|---|---|---|
| **F-09** | 補上 SIVE／IQE filing watcher，實跑 78 筆 new，宣告「從靠人記得變成有自動監測」——但 78 筆全部躺在 `pending`，排程只 triage 自己當輪抓到的，`pending` 不進 pq1 drain（2026-08-11） | **每個 producer 都必須指得出 consumer，且 consumer 必須真的會被觸發。** 交付前要答得出「這條路徑的產出最後出現在哪裡、誰會消費它」 | 全域（§2 的 QUEUE-LIVENESS invariant） | 🟡 `test_engine_b_todo.py` 有 collector 測試 | 🔴 **高** |
| **F-10** | `build_ranking_view` 交付時 **production 呼叫端 0**，首屏渲染的是「未提供排序資料」；`fetch_nav_exposure` 同樣未被消費（2026-08-28） | 同上 | `alpha/`／`portfolio/` 的 pane builder | 🔴 **無**（靠人回頭發現） | 🔴 **高**：重構會大量新增 builder |
| **F-11** | `GO_AUTHORIZATION` 登記表存在、**消費端 0**（2026-08-29） | 同上 | Engine B `todo.py` | 🔴 **無** | 🟡 |
| **F-12** | `decision_lab/backup.py` 蓋好但 production 呼叫端 **0**，「上次備份是什麼時候」的誠實答案是**沒有備份過**（2026-08-30） | 同上，且**「有沒有人在管」這件事必須做成會自己出現的常駐計數器** | shared infra | ✅ brief 首屏「最後一次備份：N 天前」＋ `test_backup_entrypoint.py` | ✅ 已保護 |
| **F-13** | `onboard-candidates` 偵測器存在，**沒有任何 routine 消費它**（2026-09-02） | 同上（L16：分類有 SSOT 但沒送到需要它的地方） | Engine B | ✅ 已接進 weekly Stage 1 | ✅ |
| **F-14** | `reactivation_event` **只寫不讀**、無 consumed-marker → 每次 sync 都重新喚醒，等待條件永遠黏不住（2026-08-12） | **狀態轉移必須留下「已消費」痕跡**，否則同一事件會無限重放 | Engine B `event_watch.py` | ✅ `test_event_watch.py`（consumed marker） | ✅ |
| **F-15** | trace 的 consumed-marker **沒有到期兜底**，標的用完即靜默沉底。實測 50 筆非終態 backlog **有 10 筆已不可能再被喚醒**，而 `auto_trigger_reachable` 對它們**全回 `true`**——那個欄位只答「有沒有標的可比對」，卻被讀成「還會不會醒」（2026-08-31） | **每個等待都必須有到期。** 且**「可觸發」與「還會醒」是兩個問題**，不得共用一個布林（L12） | Engine B `event_watch.py`（`wake_state` 四態） | ✅ `test_event_watch.py` ＋ `trace-backlog --needs-attention` | ✅ 已保護。⚠ **原設計把搬家排最後並註明「那端現況健康」，而「現況健康」從未被驗證過** |
| **F-16** | 「等事件」項的 `until` **從來沒有任何程式比對過今天**；3 個 waiting 項「機器可達」實際是 **0**（2026-08-31 稽核下修前一天的結論） | **宣稱「機器可達」必須有一條命令能證明它，否則那只是欄位存在** | Engine B `event_watch.py` | ✅ F1/F2/F3 已落地，baseline 0/3 → 3/3 | ✅ |

### 1.4 F-DROP — Silent drop：曾被接受的東西無聲消失

| ID | 症狀 → 根因（日期） | Learned invariant | 新 owner | 可執行保護（現況） | 風險／狀態 |
|---|---|---|---|---|---|
| **F-17** | `todo drop` 對 `sheet_only` 項無效——只清當次編號，sync 依 Sheet 持股重新推導並配**新編號**（[18]-[33] → [46]-[60]，2026-07-29） | **derived item 的 drop 必須改變推導條件，不能只刪除實例**，否則換號重生 | Engine B `todo.py` | ✅ `test_decision_review_churn.py`（`residual_digest` 復活判準） | ✅ |
| **F-18** | `trace_status` 是**自由字串**卻決定 lead 去留 → 打錯不報錯，只是靜默沉底（2026-08-26） | **字彙一旦有行為後果就必須被強制**；寫入端連已淘汰的同義詞都要拒絕（同義詞讓寫的人以為表達了一個沒被記錄的區別） | Engine B `lead_refs.py` | ✅ `test_lead_trace_status_vocab.py` | ✅ |
| **F-19** | lead `refs` 有 **56 個不同鍵名**，`park_reason` vs `parked_reason` 拼錯會成功落盤、所有讀取端只看另一個（2026-08-01） | 同 F-18 | `config/lead_ref_keys.json` | ✅ `test_lead_ref_registry.py` | ✅ |
| **F-20** | ranking DTO 的 rows 只帶前 `limit` 名，直接比對把**排 11 名之後的公司誤判成「不在排序」**（2026-08-29） | **截斷後的集合不得被當成全集**；需要判斷成員資格時必須提供截斷前的完整 id 集合 | `alpha/` ranking DTO | ✅ **Phase 1 已保護**：`alpha.contracts.RankedList` 型別強制同時帶 `full_ids`；`contains()` 只讀它。突變「成員判斷改讀 rows」實測會紅 | ✅ |
| **F-21** | NAV 佔比：多列時全按**第一列**的 `nav_base` 計算；同一檔散在多帳戶時**沒有任何一列顯示真實曝險**（LON:VWRA 拆成 21.7%＋4.4%，真實 26.1%）（2026-08-28／09-02） | **聚合鍵錯了比沒有聚合更危險**——它產生看起來合理但每一列都錯的數字。多值不一致時 **fail closed 回 None**，讓上游渲染「未提供」 | `portfolio/exposure.py` | ✅ `test_nav_exposure.py`（含 `_nav_base` fail-closed） | ✅ |

### 1.5 F-GATE — 多維 gate 的交互作用漏洞（五軸）

> **共同形狀：gate 攔下的不是它想攔的東西。** 對應 L15。
> ⚠ **本 class 的所有測試都必須是 parameterized／property-based**，不能只測當初那個 case
> ——見 §5。

| ID | 症狀 → 根因（日期） | Learned invariant | 新 owner | 可執行保護（現況） | 風險／狀態 |
|---|---|---|---|---|---|
| **F-22** | `assessment_context_mismatch`：研究者寫 `yfinance://history`，index 的 key 是 `yfinance://history/AAOI`——**一個少了 ticker 後綴的字串讓整筆決策的資本歸零，實測 22 次**（佔「做了研究卻有軸 unknown」的三分之二）（2026-08-13） | **gate 問的是字串相不相等，真正要問的是「這個引用指不指向同一份來源」。** 用機械比對當語意問題的代理，攔下的是格式不是風險。**先解析身分，再查權限**，且解析時不得偏好「能通過的答案」（authority laundering） | Engine D `sizing._resolve_reference`（**不搬**）；`alpha/` 產出 `evidence_refs` | ✅ `test_probe_sizing.py` 含 `[missing_ref]` case | 🟡 **中**：`EvidenceRef.ref` 是新的引用字串空間，同形狀會重現 |
| **F-23** | 判準是 `any(失敗)` 而非「至少一個合格」——**多附一個脈絡引用就整軸歸零**（2026-08-13） | **放寬解析不等於放寬判準：分開之後兩邊都要更嚴。**「至少一個合格」＋零個合格仍歸零＋不合格者必須列進 `context_only_refs` 現形供稽核 | 同上 | ✅ `test_probe_sizing.py` | ✅ |
| **F-24** | `research_status`（研究完整度）沿用 `if paper_blockers:` 不分嚴重度 → `coverage.apply_execution_intent` 塞進 diagnostic 級的 `execution_intent_research_only`，於是**任何 `research` intent 的評估恆為 `DATA_NEEDED`**，與研究完不完整無關（2026-08-29） | **嚴重度分類已有 SSOT 時，判準必須讀它**（L16）。改名成「研究完整度」不會自動改判準 | shared `blocker_severity.py` | ✅ `test_coverage_severity.py` | ✅ |
| **F-25** | `weakest_axis` 若用 raw `level` 排序，會漏掉「宣告 corroborated 但引用不成立」的軸——`_validate_assessment` 在 `fatal_axis_blocker` 時把 ceiling 打成 0 卻**不動 level**（2026-08-28，被 characterization 測試三分鐘打臉） | **同一個概念有「宣告值」與「生效值」兩個欄位時，排序／判斷必須用生效值**，且生效值要顯性化（`effective_level`） | `alpha/contracts.py`（五個 score 同構） | ✅ **Phase 1 已保護**：`Score` 拆 `declared`／`effective`＋`downgrade_reason` 必填；`weakest` 與排序 tie-break 各有一條會紅的突變守著 | ✅ |
| **F-26** | 21 個 operational cohort 有 **20 個** `live_supported_range` 是 `[0,0]`，三個真正的資本上限**一次都沒 binding 過**；唯一 binding 的是 `axis_ceiling` 0.002——一個 `measured_outcomes` 2/12、**從未被驗證的機制在決定資本**（2026-08-28，整層移除） | **未經量測的機制不得享有默認信任，gate 也不例外。** 三個免 outcome 測試：**恆亮**（觸發率近 100%＝零鑑別力）、**不會滅**（清除率近 0＝那是牆不是閘門）、**講不出因果機制**（行政流程假扮風控） | 全域（§2 的 MEASURED-GATE invariant） | 🟡 `test_bottleneck_ranking.py`／`test_alpha_event_monitor.py` 有引用 L14，但**沒有一條通用的「gate 觸發率／清除率」稽核** | 🔴 **高**：新架構會新增大量 score 與門檻 |

### 1.6 F-PIT — Point-in-time 語意漏洞

| ID | 症狀 → 根因（日期） | Learned invariant | 新 owner | 可執行保護（現況） | 風險／狀態 |
|---|---|---|---|---|---|
| **F-27** | `snapshot_date`（ETL 執行日，本機時區）被當成行情交易日（2026-08-14 拆出 `bar_date`） | **「我們什麼時候取得」與「這筆事實屬於哪一天」是兩個欄位**，永遠不得共用一個 | Engine C | ✅ `test_engine_c_bar_date.py` | 🟡 `bar_date` 覆蓋只有 1,101/1,858（59%），舊列全空 |
| **F-28** | `_safe_timestamp` 的本機時區測試靠 POSIX `TZ`＋`tzset()`，**在唯一會實際執行這條路徑的平台（Windows）上永遠 skip**。而它守的是：date-only 的 `snapshot_date` 貼 UTC 午夜就會判 `financial_timestamp_future` 並 quarantine 整份財務——**台北 00:00–08:00 結構上必中，而 daily 排程正是 06:30**，2026-08-14／08-17 已實測炸過兩次（2026-08-26 修） | **在目標平台上被 skip 的測試等於不存在。** 時間相關邏輯必須用注入的 tz 物件測，不用 process 全域狀態 | shared infra | ✅ `test_engine_d_runtime.py` 2 skipped → 0 skipped，另加 `test_injected_timezone_matches_process_default` | ✅ 已保護。**全套現況 0 skipped，這個數字本身就是防線** |
| **F-29** | reassess 未帶 `--expiry` 回退成 policy 三天預設，**把財報里程碑改造成假急件**（2026-08-15 修，`300b8e0`） | **預設值不得改變事實的語意。** 缺 expiry 應該 fail 或繼承，不是套一個看起來合理的常數 | Engine D | ✅ `test_operational_workflow.py:399` | ✅ |
| **F-30** | Shadow 錨點：9 個 cohort **7 個沒有錨點**，含隨後 +107% 的 `co:axt`——shadow 最該發揮作用的那一次失敗了。根因是**可重建的事實被當成 point-in-time 凍結**，一次瞬時故障造成永久損失（2026-08-08） | **先分清楚哪些是「只有當下才有的真相」、哪些是「隨時可重建的事實」。** 前者只能 append，後者要有修復路徑。**「不可變」是用來拒絕竄改，不是用來拒絕修復** | Engine D（Shadow）／`alpha/`（ResearchContext 可重算） | 🟡 `test_shadow_backfill.py` | ✅ 這條 invariant 正是 `ResearchContext`（可重算）vs `DecisionContext`（不可重算）分離的理論基礎 |
| **F-31** | **Engine A 完全沒有 point-in-time 能力**（本次 Phase 0 發現，非歷史事故）：canonical edge 零時間欄位，屬性是對**所有** assertion 的當前投影 | **任何被用於歷史研究或回測的 store，都必須能回答「T 時刻我知道什麼」；答不出來就必須明確拒絕，不得靜默回傳當前值** | `alpha/providers/`（as-of 投影） | ✅ **Phase 1 已裝保險絲**：`PointInTimeUnsupported`＋`select_point_in_time_evidence`（未標日期一律排除並計數）＋`ResearchContext` 拒收洩漏的未來證據。⚠ **as-of 圖投影本身仍是 Phase 6** | 🟡 保險絲已在，投影未做 |

### 1.7 F-CROSS — 跨引擎對同一事實解讀不同

| ID | 症狀 → 根因（日期） | Learned invariant | 新 owner | 可執行保護（現況） | 風險／狀態 |
|---|---|---|---|---|---|
| **F-32** | `decision_lab today` footer 的 `live_choices=0` 與 outcome 的 1 筆 live fill 互相矛盾——讀 footer 的人會以為 live 路徑從未走過，**而那正是 2026-08-19 已踩過一次的坑**（2026-09-02，**仍開**） | **同一個 DB 的兩個 surface 對同一問題必須給同一個答案**；若語意不同（本次 run vs 歷史累計）必須在欄位名上分開 | Engine D / `alpha/` pane | 🔴 **無** | 🔴 **高**，且**現在就是紅的** |
| **F-33** | `current_holdings` 用裸 `except Exception` 把「Sheet 真的沒持股」「網路讀不到」「憑證失效」壓成同一個 `holdings_unavailable`；2026-08-17 花了數步才確定是沙箱無 egress（**仍開**） | **失敗原因不得被壓平。** 下游被迫二選一時，兩邊都是錯的 | `engine_d_runtime` → provider | 🔴 **無**（`test_optional_branches.py` 只測有 raise，不分辨三種） | 🔴 |
| **F-34** | `system_paper_return` 的錨點有三種來源（舊 paper decision／當前 decision／Shadow observation），三者不一致（2026-09-02 已收斂） | **同一個指標只能有一個錨點定義**；真要兩種就在欄位名上分開 | Engine D | 🟡 | ✅ 已收斂 |
| **F-35** | `daily-brief` skill 自 2026-08-19 起維護**第二份**三維度判準，就地過期（2026-08-22 發現，改為委派 `alpha-status`） | **清單會腐壞，判準不會。** 任何 repo 裡已有結構化來源的清單，不得在文件裡再抄一份 | 全域 | ✅ `test_daily_brief_skill.py` 契約測試 | ✅ |
| **F-36** | 引用**自家文件**的現況陳述而沒跑查證：「`live_choices` 為 0 筆，這條路徑從未被走過」——使用者前一天才走完全鏈（2026-08-19） | **政策檔陳述現況時必須附查證命令。** 別對外部 claim 嚴、對自家文件鬆 | 全域（文件紀律） | 🟡 部分（ROADMAP 已加查證命令欄） | 🟡 |

---

## 2. 六條新的 hard invariant

> 這六條是 §1 的 36 筆事故收斂後的結果。**它們是 domain contract，不是建議。**
> 每一條都必須落到 types／contracts／tests／runtime audits 至少一項（§3）。

### INV-1 — IDENTITY：ticker 不是 entity identity

```
CompanyId          canonical、永久、由 identity registry 授予（co:*）
InstrumentId       可交易標的，一個 Company 可有多個
Ticker             可變的 external identifier，會被改名、會重複使用
Exchange           Ticker 的命名空間
Alias              歷史／別名 ticker
ExternalProviderId provider 專屬（yfinance symbol、SEC CIK、MOPS 代號）
```

- **禁止 downstream module 私自建立自己的 ticker normalization 邏輯。**
  identity resolution 只有一個 authority（`identity/`）。
- 不同 provider／exchange／歷史 ticker 必須經 resolution 收斂到 canonical entity。
- **未解析必須 fail closed 並區分兩種原因**：「ID 沒解析對」vs「世界上真的沒有這個 entity」。
- 來源：F-01～F-05。

### INV-2 — LIFECYCLE：每個 active object 都要回答得出五個問題

任何有 lifecycle 的 domain object（Signal／Lead／Research Action／Watch／Cohort／
Thesis／Probe／AlphaSignal／Decision／Paper position）必須能回答：

1. 目前 state 是什麼？ 2. 何時進入？ 3. 下一個合法 transition 是什麼？
4. 誰負責 transition？ 5. 什麼條件觸發？（若無下一步，**為什麼**）

**禁止存在四種狀態：**
`active but unreachable`｜`watching but no future consumer`｜`expired but still active`｜
`queued but no processor`。

沒有下一步的 object 必須進入明確的 `terminal`／`blocked`／`superseded`／`expired`。
⚠ **且 terminal 不等於死亡**（F-06）：必須有 append-only 的重開路徑。
- 來源：F-06～F-08、F-15。

### INV-3 — NO SILENT DROP

**任何曾被系統接受的 item，都不得因 filter、scheduler、expiry、migration 或 query
behavior 而無聲消失。**

每個 item 必須有可解釋 disposition：
`active`／`transitioned`／`rejected`／`expired`／`superseded`／`archived`／`blocked`。

**每個 filtering stage 必須能在 debug/audit 模式回答：**
`input count`／`accepted count`／`filtered count`／`filter reasons`／`resulting disposition`。

> **「查不到了」不是合法 lifecycle。**

⚠ 特別包含 **top-N 截斷**（F-20）：截斷後的集合不得被當成全集；
需要判斷成員資格時必須同時提供截斷前的完整 id 集合。
- 來源：F-17～F-21。

### INV-4 — QUEUE LIVENESS：每個 producer 指得出 consumer

對每個 queued／watching item：必須有 consumer｜consumer 必須可被觸發｜必須有
retry／failure disposition｜必須有 terminal disposition｜必須能查詢 stalled items。

**驗收條件寫成「產出出現在下游消費者手上」，不是「這一步回傳成功」。**
⚠ 最危險的是**成功與失敗在同一個訊號上同形**——空集合、沒有 in-flight 狀態、回傳 OK。
要驗就驗那個會因為「真的成功」而改變的東西。
- 來源：F-09～F-16（本 repo 最高頻的事故類型）。

### INV-5 — MEASURED GATE：未經量測的機制不得享有默認信任

任何新增或收緊的 gate／score／門檻，動手前必須答出**「這會讓哪個 baseline 數字變？」**
答不出來就不做。

**三個免 outcome 的失效測試（新 gate 上線後必須跑一次）：**
**恆亮**（觸發率近 100%＝零鑑別力）｜**不會滅**（清除率近 0＝那是牆不是閘門）｜
**講不出因果機制**（說不出「亮起時標的更可能變壞」＝行政流程假扮風控）。

**順序不可顛倒：先量測，後放閘。** 先放寬而沒有量測 ＝ 拆煞車不裝儀表板。
⚠ 且 gate 攔下的必須是它想攔的東西——**若攔的是格式、時區、字串後綴、單位寫法，
它攔錯了**，該修的是它問問題的方式（F-22）。
- 來源：F-22～F-26。

### INV-6 — POINT-IN-TIME & PROVENANCE

- **任何被用於歷史研究或回測的 store，必須能回答「T 時刻我知道什麼」；
  答不出來就必須明確拒絕（`PointInTimeUnsupported`），不得靜默回傳當前值。**
- **「我們什麼時候取得」與「這筆事實屬於哪一天」永遠是兩個欄位。**
- **`published_at is None` 不等於「在 T 之前」**——as-of 模式下必須排除**並計數**。
- **所有重要 conclusion 必須可回溯至 evidence。** `AlphaSignal` 的每個非 None score
  都必須列得出 `EvidenceRef`。
- **可重建的事實 vs 只有當下才有的真相要先分開**：前者要有修復路徑，
  後者只能 append。「不可變」是拒絕竄改，不是拒絕修復。
- 來源：F-27～F-31、F-36。

---

## 3. Runtime invariant audit

新增統一 checker（Phase 1 建骨架，各 Phase 補檢查）：

```
python -m audit invariants                # top-level package（2026-09-04 由 alpha/audit/ 搬出）
```

**必須能對真實 repository / storage / DB state 執行，不只是 unit-test fixture。**
輸出 **fail loudly**：

```
PASS  Identity            registry 98 / graph 92 / leak 0
PASS  Lifecycle           41 cohorts, 0 expired-but-active
FAIL  QueueLiveness       3 watching items have no next consumer
        ew_a1b2  entity_filing_signal  entities=[] → 永遠不會比對到
        ...
PASS  PointInTime         0 as-of queries fell back to current data
FAIL  EvidenceProvenance  2 AlphaSignal scores without EvidenceRef
PASS  GraphFinancialJoin  graph∖registry = 0
```

| Check | 對應 invariant | 對應事故 | 資料來源 |
|---|---|---|---|
| `Identity` | INV-1 | F-01/04/05 | registry × Neo4j × Engine C ticker |
| `Duplicates` | INV-1 | F-04、cohort 重複 | registry alias 碰撞、同公司多 cohort |
| `Lifecycle` | INV-2 | F-06/07/08 | Decision Store epochs、thesis lifecycle、lead 狀態機 |
| `Expiry` | INV-2 | F-15/16 | event watches、RA `expires_at`、cohort expiry |
| `Orphans` | INV-3 | F-17/20 | 無 disposition 的 item |
| `QueueLiveness` | INV-4 | F-09～F-16 | `queued_without_consumer`／`watching_without_next_action`／`expired_still_scheduled`／`blocked_without_reason`／`stalled_over_threshold` |
| `GateDiscrimination` | INV-5 | F-26 | 每個 gate 的觸發率與清除率（恆亮／不會滅偵測） |
| `PointInTime` | INV-6 | F-27/28/31 | as-of fallback 次數、`published_at` 覆蓋率、`bar_date` 覆蓋率 |
| `EvidenceProvenance` | INV-6 | F-36 | 無 `EvidenceRef` 的 score |
| `GraphFinancialJoin` | INV-1 | F-03/04 | A→C join key 兩側對齊 |
| `AlphaLineage` | INV-6 | — | `AlphaSignal` → `ResearchContext` digest 可解析 |
| `DecisionLineage` | INV-6 | — | decision → context bundle digest 可解析 |

⚠ **這個 audit 本身也受 INV-5 約束**：上線後要能回答「它抓到了幾筆」。
抓到 0 筆且長期為 0 的 check 是恆滅的閘門，要嘛拿掉、要嘛承認它只是回歸保險。

---

## 4. Lesson learned 必須 executable

**每個 critical lesson 至少落到以下一項**：schema constraint｜type constraint｜
state-machine constraint｜contract test｜integration test｜property-based test｜
runtime consistency audit｜CI migration gate。

```
Lesson Learned → Domain Invariant → Executable Protection
```

**現況統計（§1 實測）：** 36 筆事故中
**✅ 已有可執行保護 17 筆｜🟡 部分 9 筆｜🔴 僅文字 10 筆。**

🔴 清單（**這 10 筆是本次重構的最高風險**）：

| ID | 缺什麼保護 | 建議落點 |
|---|---|---|
| F-03 | identity 部分缺漏靜默關管線 | `test_identity_contract.py`：缺任一 execution 欄位不得影響 research lane |
| F-07 | terminal 動詞語意 | state-machine constraint：`close()` 對「會開新 epoch 的值」要求 explicit flag |
| F-08 | 兩套 lifecycle 未書面化 | contract test：兩個 lifecycle registry 的 owner 集合必須不相交 |
| F-09/F-10/F-11 | producer 無 consumer | **`QueueLiveness` runtime audit**＋新增 builder 時的 CI 檢查（掃 production 呼叫端） |
| F-20 | 截斷集合被當全集 | type constraint：`RankedList` 型別強制同時帶 `full_id_set` |
| F-26 | gate 鑑別力 | **`GateDiscrimination` runtime audit** |
| F-31 | Engine A 無 as-of | `PointInTimeUnsupported` ＋ `PointInTime` audit |
| F-32 | 兩個 surface 答案矛盾 | cross-boundary contract test（§6） |
| F-33 | 失敗原因被壓平 | 三種情形各一條會 raise 的測試 |

---

## 5. 多維 gate 不得只做 regression example

**若歷史事故涉及多個 axes／conditions 的交互作用，不得只測當初發生問題的單一 case。**

必須使用：parameterized tests｜property-based tests｜boundary tests｜
invalid-combination tests，驗證整個 valid state space。

**目標是防止「修掉已知組合，但另一個組合仍可繞過 invariant」。**

適用對象（現況與新架構）：

| 對象 | 維度 | 狀態空間大小 |
|---|---|---|
| 五軸 assessment | 5 軸 × 3 level × (引用合格/不合格) | 3⁵ × 2⁵ |
| `AlphaSignal` 五 score | 5 score × (None/0..1) × trace 有無 | 同構——**F-25 的形狀會原樣重現** |
| blocker severity × lane | severity 3 × lane 3 × 73 個 code | |
| lifecycle × terminal verb | 5 態 × 4 動詞（其中 1 個不是終態） | F-07 |
| freshness × status | 4 status × 5 個窗 | F-28 |

---

## 6. Cross-boundary contract tests

**至少驗證這條 end-to-end lineage：**

```
Entity Identity → Graph → ResearchContext → AlphaSignal → Portfolio Input → DecisionContext
```

**每個 boundary 必須保持、且不得 silently reinterpret：**
canonical entity identity｜`as_of_date`｜evidence provenance｜source version｜
state semantics｜confidence semantics。

⚠ **「confidence semantics」是本 repo 最容易被 reinterpret 的一個**——
現況有 5 套證據強度字彙（`evidence_tier`／`demand_proof_level`／圖上的
`confidence` 0–1／`EVIDENCE_RANK` 五級／五軸 `level`）。
`EvidenceRef` 把它們**並列**而不是壓成一個分數，正是為了讓 boundary test 抓得到重新詮釋。

---

## 7. Golden fixtures / 歷史回歸套件

建立 `tests/fixtures/golden/`，**refactor 前先保存 expected semantic behavior，
refactor 後用同一批 frozen input 重跑。**

至少涵蓋（每項標註對應事故）：

| Fixture | 對應 |
|---|---|
| 正常公司（COHR：有五軸、有 live fill、有 outcome） | baseline |
| ticker alias / renamed ticker（Sivers 三層 symbol） | F-05 |
| minor-unit 報價（LSE `GBp`） | F-02 |
| missing financial data（Agility：未上市、`research_ticker=null`） | F-03 |
| structural bottleneck（LITE → `tech:uhp_laser`，sub=5＋sole_source） | — |
| multiple substitutes（`mat:inp_substrate` 7 家供應商） | — |
| watching item（`event_watches.json` 的 `stalled` 筆） | F-15 |
| expired cohort（COHR epoch 1 expired ＋ epoch 2 active） | F-06 |
| blocked state（`research_assessment_missing`） | F-24 |
| stale data（runway 觀測超過 100 天窗） | — |
| conflicting evidence（同 edge_key 兩個明確值 → open conflict） | — |
| point-in-time boundary（**6/30 as-of ＋ 7/5 published filing**） | F-31 |
| 截斷邊界（rank 第 11 名） | F-20 |
| 多帳戶同一檔（LON:VWRA 兩列） | F-21 |

---

## 8. Old / New dual run

**critical migration 階段，舊 pipeline 與新 pipeline 對同一 frozen input 並行執行，
產生 semantic diff。** 每個差異必須被分類為：

`EXPECTED_CHANGE`｜`BUG_FIX`｜`INTENTIONAL_REMOVAL`｜`REGRESSION`

**禁止存在 unexplained behavioral diff。
在 unexplained critical diff 歸零之前，不得移除 legacy implementation。**

適用批次（見 `engine-d-decomposition.md` §4）：**B1**（Portfolio/Risk 搬家）、
**B5**（sizing 切三段）、**B6**（brief 拆 pane）——這三批都會改變輸出路徑。
B0／B2／B4 是純新增或純搬移，不需 dual run。

> ⚠ 本 repo 已經有一次 dual-run 成功案例可以照抄：2026-08-29 改 `research_status`
> 判準前，**先對 21 個 operational cohort 套用新判準，量出 3 筆改判**，才動手。
> 那就是 dual run 的最小可行形式。

---

## 9. Migration completion gate

**本次 refactor 不得僅以「tests pass／CLI works／architecture looks cleaner」判定完成。**

每個 phase 的 exit criteria **必須全部包含**以下八項：

1. ☐ Historical regression suite pass（§7 golden fixtures）
2. ☐ Runtime invariant audit pass（§3）
3. ☐ No unexplained semantic diff（§8）
4. ☐ **No new dual authority**（沒有第二套 graph／financial current-state authority）
5. ☐ No silent-drop path（INV-3；每個 filter 都能報 input/accepted/filtered/reasons）
6. ☐ Point-in-time tests pass（INV-6）
7. ☐ All migrated lifecycle objects reachable（INV-2／INV-4）
8. ☐ **Critical historical failures have executable protection**（§4 的 🔴 清單對該 phase 涵蓋的部分歸零）

> **若任一 critical historical lesson 尚未轉化成 executable invariant，
> 不得宣稱該 migration phase 完成。**

### 各 Phase 的 🔴 責任分配

| Phase | 必須清掉的 🔴 |
|---|---|
| 1（contracts） | F-20（`RankedList` 型別）、F-31（`PointInTimeUnsupported`）、F-25（score 宣告值 vs 生效值） |
| 1.5（Portfolio/Risk） | — （F-21 已有保護；本批做 dual run 練習） |
| 2（vertical slice） | F-03（identity contract test）、F-36（AlphaSignal 引用可追溯） |
| 3（Engine D 分解） | F-09/10/11（`QueueLiveness` audit）、F-32、F-33 |
| 4（Expectation Gap） | F-26（`GateDiscrimination` audit） |
| 5（Causal） | F-08（兩套 lifecycle owner 不相交） |
| 6（Backtest） | F-31 完整版（as-of 投影）、F-27（`bar_date` 覆蓋） |
| 7（Portfolio/Risk 完整化） | F-07（terminal 動詞 state-machine constraint） |

---

## 10. 本檔自己的 disproof

⚠ **這份矩陣若只是被讀，它就沒有生效**——那正是 L14 批評的「要人讀的段落」。

**它生效的唯一證據是 §3 的 runtime audit 會紅、§7 的 golden fixture 會紅。**
若之後仍發生「§1 已列的某一類事故重新出現」，代表本檔失敗，
屆時該做的不是把表寫得更長，而是**把那一類的檢查搬進 CI 或 commit-time hook**。

**可量測的成功條件：** 🔴 從 **10 筆 → 0 筆**，且 `audit invariants` 至少抓到過
**1 筆真實問題**（抓到 0 筆的 audit 依 INV-5 是恆滅閘門，沒有資格宣稱有效）。
