# StockBotv2 Weekly Scan — 2026-09-13

- 事件探索窗：2026-09-06～2026-09-13（Asia/Taipei；每個主題 2–3 組查詢）
- 風險比較基準：2026-08-30 上一份已提交週報。中間沒有 2026-09-06 週報，因此趨勢欄是約兩週差額，不冒充七日變化。
- 本輪邊界：只做 topic discovery、Stage 2 triage、read-only health／lifecycle／risk audit、conflict proposal 與 pq2 登錄；沒有 source-trace、extract、ingest、graph write、thesis mutation、Engine C observation、live 或 lifecycle 狀態變更。

## 30 秒摘要

- 7 日內值得進 pq1 的新材料只有兩筆，皆在 CPO／NPO counter-path：GIGALIGHT 指出 socket-based 1.6T NPO 的 Flip-Chip 熱膨脹與 socket 壓合一致性是百萬級量產障礙；NewPhotonics 發布 laser-integrated、serviceable 6.4T NPO 光引擎。兩筆都已註冊並 triage 為 `go`，但仍只是供應商自報，沒有抽取或入圖。
- Sivers／CW laser 沒有新的 7 日官方材料足以越過現有 CIOE channel-check 與價格 claims；humanoid 也沒有新的客戶付款、訂單、預付款或產能承諾。既有 Agility Robotics S-4 lead 已在 watch，未重複登錄。
- 完整 owner-context health audit 有兩類紅項：Vistara 同一 PDF 被建成兩個 SourceDoc；Coherent OCS 同一條 edge 的 `qualification_status` 與 `ramp_execution` 有未處置衝突。後者已形成可驗證 proposal 並登錄 [568]、[569]，沒有直接核准或改圖。
- 風控沒有 hard block。總曝險由 1.03x 升至 1.083x，主因是已動用貸款 USD 23,714；槓桿 ETF 投入資本占 NAV 由 7.8% 降至 7.18%，換算槓桿曝險由 18.1% 降至 16.66%，但加上貸款後 combined effective 為 21.76%。
- 全套測試：`2370 passed, 1 skipped, 1 warning`。分類健康為 0 筆 active unclassified；harvest health 無未恢復失敗。

## 1. Topic Digest

### 1.1 CPO／NPO：兩條新 counter-path 線索

#### PASS A — GIGALIGHT socket-based 1.6T NPO

- 來源：[GIGALIGHT 官方新聞稿，2026-09-07](https://www.gigalight.com/news-events/news-10808.html)
- Lead：`lead_2cdf807d54bf8f6febf46cb966914c41`
- 狀態：`triaged_go`，tier 1，`structural_fact / ranking`，`contradiction=true`、`novelty=true`。
- 原子訊號：公司稱 socket-based 1.6T NPO 工程樣品可出貨，但把 Flip-Chip 材料熱膨脹係數差異與 socket 壓合一致性列為百萬級量產障礙。
- 研究意義：這不是「socket 已解決可維修性」的單向利多；它把瓶頸移到熱機械可靠度與大規模組裝一致性，可能改變 CPO／NPO 架構與先進封裝層的排序。
- 限制：來源與被評估公司同一 origin_entity；`tier 1` 表示可逐字核對的一手材料，不代表獨立印證。

#### PASS B — NewPhotonics laser-integrated 6.4T NPO

- 來源：[NewPhotonics 公司發布稿，2026-09-09](https://www.einpresswire.com/article/939190081/newphotonics-expands-near-package-optics-pic-series-with-laser-integrated-serviceable-high-density-6-4t-optical-engine)
- Lead：`lead_000275f922a2d61a09af0e0fe9047318`
- 狀態：`triaged_go`，tier 2，`structural_fact / ranking`，`contradiction=true`、`novelty=true`。
- 原子訊號：NPC50506 Open-CPX 為 socketed、laser-integrated、serviceable DR32 NPO 光引擎；公司宣稱 2026 Q3 提供樣品、Q4 提供 reference design。
- 研究意義：若之後有客戶端或第三方驗證，它是 external-laser／CW DFB 路徑的直接 counter-path，可能讓「外置光源必然是唯一瓶頸」的判斷失效。
- 限制：目前仍是公司發布稿；時程是前瞻聲明，不等於量產、客戶採用或營收。

兩筆 lead 均補上 `onboard_candidate_names`，因此 GIGALIGHT 與 NewPhotonics 已能被 deterministic `onboard-candidates` 看見；這只是候選浮出，不是 registry admission。

### 1.2 Sivers／CW laser

- 7 日搜尋沒有找到比既有材料更新、且能改變 Sivers thesis／ranking 的官方文件。
- 2026-09-03 Glasgow USD 30m expansion 在本輪窗口外，且已被既有 lead 捕捉；CIOE channel-check、CW laser 價格與供應 claims 也已在現有 pq1／watch，未重複登錄。
- 結論：本主題 0 新 PASS、0 新 FILTER 登錄；不是「沒有消息」，而是沒有未被現有管線涵蓋的 material delta。

### 1.3 Humanoid／客戶端商業承諾

- 7 日內未找到新的具名訂單、預付款、最低採購量、產能保留或其他付錢方向的客戶端承諾。
- Figure／Nscale 類 compute 基礎設施消息不是 humanoid 客戶購買機器人的證據，且主要事件在窗口外；不將融資或算力採購冒充 deployment demand proof。
- Agility Robotics 的 S-4 線索已存在於 `lead_f1cf...` 與 pq2 [200] 的公開申報 trigger，未重複登錄。
- 結論：0 新 PASS、0 新需求錨；本週不新增 decompose 選題。

## 2. Stage 2 與 Engine B 健康

### 2.1 本輪 triage

| 結果 | 數量 | 說明 |
|---|---:|---|
| PASS | 2 | GIGALIGHT、NewPhotonics；均停在 `triaged_go` |
| FILTER | 0 | 重複、窗口外或無 material delta 的結果不另建 lead |
| source-trace／extract／ingest | 0 | 明確超出 weekly 邊界 |

### 2.2 目前狀態計數

| status | 數量 |
|---|---:|
| `triaged_no_go` | 517 |
| `triaged_go` | 2 |
| `parked` | 468 |
| `applied` | 83 |

- `classification-health`：`ok`，active unclassified = 0。
- `harvest-health`：`[]`，沒有仍未恢復的 harvest 失敗。
- `trace-backlog`：63 筆；34 `watching`、28 `stalled`、13 `poll_eligible`、34 `auto_trigger_reachable`、0 `requires_user`。其餘 1 筆沒有歸入上述兩個 wake state；週報只揭露，不做 lifecycle 處置。

### 2.3 Deterministic onboard candidates

以下只是「已通過 triage 的 lead 逐字點名、但 registry 未登記」的確定性清單，不是 onboard 建議，更不是投資排序：

| 候選 | 被不同 lead 點名數 | 偵測方式 |
|---|---:|---|
| AMZN | 17 | cashtag |
| SPCX | 7 | cashtag |
| BE | 5 | cashtag |
| SMTC | 4 | cashtag |
| CXMT | 3 | cashtag |
| FORM | 3 | cashtag |
| AMKR | 2 | cashtag |
| Fabrinet (NYSE: FN) | 2 | manual |
| AIXTRON SE (AIXA.DE) | 1 | manual |
| GIGALIGHT | 1 | manual，本輪新增 |
| NewPhotonics | 1 | manual，本輪新增 |

同一公司可能以 cashtag 與 manual 名稱各出現一次，這份輸出未做語意合併；計數是 nomination frequency，不是 evidence quality。

## 3. Thesis／Lifecycle read-only 核查

| thesis | status | last checked | next check | 本輪結論 |
|---|---|---|---|---|
| AXT InP | active | 2026-08-04 | 2026-11-15 | 無新 7 日材料觸發既有 disproof；Q3 財報估 10/30、10-Q 估 11/13 |
| Coherent CPO | active | 2026-07-17 | 2026-10-15 | lifecycle 未到期，但 active thesis 引用的 OCS edge 有 conflict，canonical attribute 必須 fail closed；見 [568]、[569] |
| Sivers | active | 2026-08-29 | 2026-09-28 | 無新 material delta；Q3 報告 11/26、ELS readiness 12/31 |

本輪沒有直接修改 lifecycle。Coherent 的 edge conflict 是 evidence resolution gate，不自動等同 thesis retire／revise；若 resolution 改變 thesis 才另走 thesis mutation gate。

## 4. 完整本機健康審查

### 4.1 綠項

- `sole_source` L8 weak：0。
- Claim／EdgeAssertion 缺 CITES：0。
- Graph schema：圖與 repo 皆為 `2026-07-16-u3b`。
- TICKER_MAP 覆蓋：0 缺漏。
- Thesis 到期：0。
- L7 欄位、memo freshness：0 問題。
- Engine C freshness：73 檔、閾值 7 日，0 問題（owner context 驗證）。
- 財務核驗清單可跑性、待 publish RA、skills 同步：0 問題。

### 4.2 紅項 A — 同 URL 重複 SourceDoc

- URL：`https://aisystemcodesign.github.io/papers/isca26/vistara_camera_ready.pdf`
- doc_id：`meta_vistara_isca_2026`、`meta_vistara_isca_2026_counter_path`
- Repo 證據顯示第二份是對同一 paper 的 counter-path 再抽取，不是不同原始文件。
- 本輪未修：安全修復需要決定 canonical SourceDoc、重接 CITES／source refs 並移除重複節點；這是 A1 mutation，現有 weekly 沒有「同 URL SourceDoc consolidation」的已核准 deterministic corridor。直接刪或 merge 會跨 authority gate。

### 4.3 紅項 B — Coherent OCS edge conflicts

同一條 `co:coherent -> tech:ocs`、edge key `edge:0e25fcc6381a52f5a51a303e8cc856dcc17ed07058d66d5e5251c44d8a8f224c`：

1. `qualification_status`：既有 resolution 因新增候選而 stale。四筆時間序為 2024-03 `qualifying`、2026-02 `qualifying`、2026-03 `qualifying`、2026-05 `qualified`。proposal 維持較晚的 `qualified`，但明示這仍是 extraction judgment，不提高 evidence tier。
   - conflict：`conflict_76dd421e889a8dd284dde2e45346fc4f1dd70393f95defabee2119a5caf1a098`
   - candidate set：`e599ebce6a9bf2dd474e9245948dc349e1b342de0c1fbc0c5a2ea78b0a102ee6`
   - proposal：`docs/reports/weekly_scan_2026-09-13_coherent_ocs_qualification.proposal.json`
   - pq2：[568]
2. `ramp_execution`：三份 Coherent 自報依時間為 `3 → 4 → 3`，沒有標準化量尺、單向 supersession 或獨立客戶端量產／良率／出貨資料。proposal 將 canonical 值留為 `unknown`，保留所有 assertion。
   - conflict：`conflict_8dde8f2e54b0f02a30173ea09419f952149dac99c5e0ba3e4bce75ff4e1458a6`
   - candidate set：`84ea68f41fab9d3aea29efa459a9fe7f5d76369c216a89b1f29f5c65cd735526`
   - proposal：`docs/reports/weekly_scan_2026-09-13_coherent_ocs_ramp_execution.proposal.json`
   - pq2：[569]

兩份 proposal 都已對 live conflict 走 `_validate_decision_against_conflict` 驗證通過；本輪沒有執行 `approve` 或 `project`。這是 `evidence-conflict-resolution` 規則要求的停止點。

### 4.4 修前／修後

| 項目 | 修前 | 本輪後 |
|---|---|---|
| Engine C ACL | sandbox 內 verifier fail closed | owner context 重跑後綠；確認是 sandbox 權限邊界，不是 ledger ACL 壞掉 |
| active lead classification | 0 未分類 | 維持 0；新增兩筆均有封閉字彙 classification |
| Coherent conflicts | 2 個 open、沒有 current proposal／pq2 | 仍 open；新增 2 份 live-hash proposal 與 [568]、[569]，未越過人工 gate |
| Vistara duplicate SourceDoc | 1 組 | 未變；無安全已授權的 deterministic merge corridor |

## 5. Portfolio／Risk read-only 快照

快照時間 2026-09-13 04:22 +08:00，policy `2026-08-29.1`，NAV USD 464,796。`--no-refresh` 的 top-level status 為 `degraded`，原因是行情 refresh／TWSE freshness 不可用；authority、allocation 與 risk snapshot 本身可讀，沒有 hard block。

### 5.1 核心風險

| 指標 | 2026-08-30 | 2026-09-13 | 變化 |
|---|---:|---:|---:|
| 總曝險 | 1.03x | 1.083x | +0.053x |
| 槓桿 ETF 投入資本占 NAV | 7.8% | 7.18% | -0.62pp |
| 槓桿 ETF 換算槓桿曝險 | 18.1% | 16.66% | -1.44pp |
| 已動用貸款／NAV | 0% | 5.10% | +5.10pp |
| combined effective | 18.1% | 21.76% | +3.66pp |
| Alpha／NAV | 1.5% | 1.54% | +0.04pp |
| TSMC 已知至少曝險 | 31.8% | 29.49% | -2.31pp；coverage 仍為 partial |
| 共同可投資現金 | USD 30,710 | USD 30,708 | -USD 2 |
| 未動用貸款額度 | USD 189,705 | USD 165,997 | -USD 23,708 |

- 已動用貸款 USD 23,713.92，估計月息 USD 61.26；合約欄位完整。未動用額度不計入 NAV／cash／allocation。
- 估算 wipeout index drawdown 為 92.38%；總曝險 cap 1.75x，hard blocks = 0。
- 警告：`drawn_debt_present`、TSMC issuer concentration、look-through partial、未分類持股按 unlevered direct issuer 降級。TSMC 的 29.49% 是「已知至少」，不可冒充完整曝險。
- Alpha 與 Beta 高度共用 AI／photonics 風險因子；分成兩個 sleeve 不代表兩個獨立賭注。

### 5.2 配置差距（只呈現，不排序、不換算金額）

| sleeve | actual | target | gap | state |
|---|---:|---:|---:|---|
| beta_core | 33.47% | 40% | -6.53pp | below band |
| beta_tilt | 30.29% | 25% | +5.29pp | above band |
| beta_tilt_active | 3.28% | 3% | +0.28pp | on target |
| beta_leverage | 7.70% | 10% | -2.30pp | on target |
| large_cap_tilt | 23.60% | 12% | +11.60pp | above band |
| alpha | 1.66% | 10% | -8.34pp | below band |

`band` 是容忍區間，不是投入 gate；本表不提供金額、次序或部位尺寸。

## 6. Unified pq2（穩定編號，只揭露不處置）

### 卡在你：9 項

- manual：[541] RV reducer claim 更正；[565] 3363.TWO target_pe abstention；[566] CRWV target_pe abstention；[567] AEVA target_pe abstention；[568] Coherent OCS qualification；[569] Coherent OCS ramp_execution。
- decision review：[558] Unitree 估值錨（已 defer）；[562] IQE 獨立來源。
- Engine C observation：[561] GFS debt maturity／covenants。

### 系統在做：0 項

### 在等世界：16 項

- [200] Agility S-4；[276] Broadcom；[279] Micron；[348] NVIDIA MRM yield；[362] TSMC Q3 shipment；[407] Hyperlight；[421] Proterial；[458] GOOGL ETL；[461] Soitec named counterparty；[472] Aeva financial；[492] Niron filing；[493] Ewellix disclosure；[494] Nabtesco customer；[495] Schaeffler AR2026；[522] Nidec 9/30 filing；[552] AXT financial。
- 以上觸發前不需動作；weekly 不給 `go`／`drop` 建議。

### 已完成待關：0 項

## 7. 驗證

- Owner-context：`.venv\Scripts\python.exe query\health_audit.py --local` → exit 0；所有 owner-only 項可讀，紅項只有 duplicate SourceDoc 與兩個 open conflicts。
- Edge projection dry-run：525 edges、344 materialized attrs、2 open conflicts、26 derived attrs、24 valid resolutions。
- Targeted tests：138 passed（health、conflict、todo、lifecycle、triage、classification、risk）。
- Full suite：2370 passed、1 skipped、1 Starlette deprecation warning，耗時 440.22s。
- `classification-health`：0 active unclassified；`harvest-health`：0 unresolved failure。

## 建議摘要

- [568] Coherent OCS `qualification_status`：已備妥「沿時間序維持 qualified」的 stale-resolution 重審 proposal；等互動 session 檢視 authority 邊界後決定。
- [569] Coherent OCS `ramp_execution`：已備妥「3→4→3 無法決勝，canonical 留 unknown」的 proposal；等互動 session 決定。
- Vistara duplicate SourceDoc：確認為真實 health 紅項，但本週沒有安全且已授權的合併走廊；不做破壞性修復。

可直接複製的批次指令：無（weekly 只發現、不處置；請在互動 session 檢視 [568]、[569] 後再決定）
