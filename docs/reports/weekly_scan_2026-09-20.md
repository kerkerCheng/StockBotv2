# StockBotv2 Weekly Scan — 2026-09-20

- 事件探索窗：2026-09-13～2026-09-20（Asia/Taipei；每個 active theme 以 2–3 組查詢為度）
- 風險比較基準：2026-09-13 上一份已提交週報。
- 本輪邊界：只做 topic discovery、Stage 2 triage、read-only health／lifecycle／risk audit、edge-conflict proposal 與 unified pq2 登錄；沒有 source-trace、extract、ingest、graph write、thesis mutation、Engine C observation、live 或 lifecycle 狀態變更。

## 30 秒 brief

- 本週唯一新登記的 PASS 是 Open CPX Specification 1.0：6.4T／7.2T 的可插拔 CPO／NPO 共同規格同時容納 external laser、module-integrated laser 與 copper mixed-media，並把多家供應商放進同一規格面。這不是「外置雷射已被取代」，而是單一 proprietary／external-laser 路徑的結構性 counter-path；已停在 `triaged_go`，沒有追源或抽取。
- 三個同窗重要事件已被 daily 管線先捕捉，本輪不重複建 lead：GlobalFoundries–Marvell 擴大 SiGe 產能協議；Tower–NewPhotonics 開始 800G／1.6T laser-integrated PIC 高量產出貨、6.4T 預計 1H27；Agility Digit 5 公布超過 USD 300m 的有條件多年訂單與 2027 上市時程。
- Coherent CPO thesis 已於 2026-09-19 因「NVIDIA 外部光源出現第二供應商」反證觸發而轉為 `review_required`；本輪只以 [636] 提醒複查，沒有改寫 thesis 或 lifecycle。
- Health audit 仍有 Vistara 同 URL 重複 SourceDoc；open edge conflict 由 2 個增為 4 個。既有 Coherent OCS 兩項仍由 [568]／[569] 等核准；新增 WIN→Sivers 與品類層 CPO→external laser stale resolution proposal，分別登錄 [634]／[635]。四項均未 approve／project。
- 風控沒有 hard block：總曝險 1.085x；槓桿 ETF 投入資本占 NAV 7.38%、換算曝險 17.09%；已提款貸款占 NAV 5.04%，combined effective 22.12%；alpha 1.60%；TSMC partial 已知至少 29.86%。
- 完整 owner-context test suite：`2790 passed, 1 skipped, 1 warning`。classification active unclassified = 0；harvest failure = 0。

## 1. Topic Digest

### 1.1 新 PASS — Open CPX Specification 1.0

- 來源：[Open CPX MSA 官方頁面](https://www.opencpxmsa.org/)（2026-09-17 發布 Specification 1.0）
- Lead：`lead_cbde672c50d2693ebb5f5d1118446a7c`
- 狀態：`triaged_go`，tier 1，`structural_fact / candidate_set`，`contradiction=true`、`novelty=true`、`independent=true`。
- 原子訊號：官方 MSA 公布共同機械與效能規格，連線能力涵蓋 6.4T／7.2T，並在同一 form factor 中容納 external laser、module-integrated laser 與 copper mixed-media。
- 研究意義：這會把候選集合從單一 proprietary 路徑擴成多供應商、可替換 module 與多種光源／介質路徑；若實作成熟，會降低「某一 external-laser 供應商必然獨占」的結構確定性。
- 限制：規格發布與會員名單不等於量產互通、客戶採用或供應份額；本輪沒有追源、抽取或入圖。

### 1.2 已被 daily 捕捉，不重複登記

1. **GlobalFoundries–Marvell SiGe capacity agreement**
   - [GlobalFoundries 官方新聞稿](https://gf.gcs-web.com/news-releases/news-release-details/globalfoundries-and-marvell-expand-collaboration-next-generation)於 2026-09-17 公布多年擴產協議，支援 pluggable、NPO 與 CPO。
   - 事件已在 daily 的 `lead_27bf534a...` composite lead 中；該 lead 仍是 `pending`，Weekly 不替 daily backlog 重做 triage。
2. **Tower–NewPhotonics high-volume shipment**
   - [Tower Semiconductor Form 6-K](https://ir.towersemi.com/static-files/58a7678f-6a6b-4915-b30c-546d35307c89)披露 800G／1.6T laser-integrated serviceable optical-engine PIC 已開始高量產出貨，6.4T CPX-MSA chipset 預計 1H27 進入 volume shipment。
   - 同一事件也在 `lead_27bf534a...`；既有 NewPhotonics prepared RA [570] 已被 `source_cleared` 標記，但 Weekly 不據此建議關閉。
3. **Agility Digit 5**
   - [Agility 官方發布](https://www.agilityrobotics.com/content/agility-unveils-digit-5-humanoid-robot-built-for-cooperatively-safe-work-at-scale)披露 65,000 小時 operation、超過 USD 300m 的有條件多年訂單、2027 年 early access／general availability 與 10:1 run-to-charge ratio。
   - daily 已建 `lead_0f87443a...` 並以 `structural_fact / candidate_set` PASS，現為 `parked`；Weekly 不重複登記。

### 1.3 Sivers／CW laser

- 7 日官方搜尋沒有找到未被現有 lead／watch 涵蓋、又足以改變 Sivers qualification 的新文件。
- Digitimes recognition、CIOE channel check 與 100m+ capacity buildout 已被既有 `lead_dcbd8601...`、`lead_e6f2bbd1...` 與 Glasgow 擴產材料涵蓋。
- 真正未解的門仍是 `qualification_status: sampling → qualified／designed_in`；[632] 已綁定 event watch 等公司期中／年報或客戶具名，本輪沒有改狀態。

### 1.4 Humanoid／客戶端商業承諾

- Digit 5 是 material delta，但已被 daily 捕捉；其 USD 300m 數字仍是供應商自報、附 contractual milestones，具名客戶與營收認列條件仍未公開。
- 其餘搜尋沒有找到新的客戶付款、預付款、最低採購量或已實際 deployment 的未捕捉事件。
- 本週沒有新的實體系統需求錨，因此不新增 `decompose-propose` 題目。

## 2. Thesis 核查（read-only）

| thesis | status | last checked | next check | 本輪結論 |
|---|---|---|---|---|
| AXT InP | active | 2026-09-17 | 2026-11-15 | 無 7 日新材料觸發既有 disproof；Q3 財報／10-Q 仍是 10/30、11/13 的估計檢核點 |
| Coherent CPO | review_required | 2026-09-19 | 2026-10-15 | NVIDIA 客戶端資料已證明 Lumentum、Sumitomo、Coherent 同列外部光源供應商；sole_source 已降級，thesis 等待人工重估，見 [636] |
| Sivers | active | 2026-08-29 | 2026-09-28 | 尚未到期，但只剩 8 天；沒有新客戶端文件讓 CW DFB／DWDM laser array 越過 sampling |

本輪沒有直接修改 `thesis/lifecycle.json`。Coherent 的 `review_required` 是 2026-09-19 已存在的 authority 狀態；Weekly 只讓 `todo sync` 鑄成 [636]，`go` 也只授權本機複查，不含自動改 lifecycle、入圖或 live。

## 3. 系統健康審查（修前／修後）

### 3.1 綠項

- `sole_source` L8 weak：0。
- Claim／EdgeAssertion 缺 CITES：0。
- Graph schema：圖與 repo 皆為 `2026-07-16-u3b`。
- TICKER_MAP 缺漏：0。
- L7 欄位、memo freshness：0 問題。
- Engine C freshness：73 檔、閾值 7 日，owner context 為 0 問題。
- 財務核驗清單可跑性、待 publish RA、skills 同步：0 問題。
- `classification-health`：0 筆 active unclassified；`harvest-health`：0 unresolved failure。

### 3.2 紅項 A — Vistara 同 URL 重複 SourceDoc（未變）

- URL：`https://aisystemcodesign.github.io/papers/isca26/vistara_camera_ready.pdf`
- doc_id：`meta_vistara_isca_2026`、`meta_vistara_isca_2026_counter_path`
- 本輪未修：canonical doc、CITES／source refs 重接與重複節點移除都是 A1 mutation；現有 Weekly 沒有核准過的 deterministic consolidation corridor。

### 3.3 紅項 B — 4 個 open edge conflicts

| edge／attribute | 狀態 | 本輪處置 |
|---|---|---|
| Coherent→OCS `qualification_status` | active thesis 引用；stale resolution | 既有 proposal hash 仍 live；[568]，未 approve |
| Coherent→OCS `ramp_execution` | active thesis 引用；3→4→3 無法決勝 | 既有 unknown proposal hash 仍 live；[569]，未 approve |
| WIN Semiconductor→Sivers `qualification_status` | stale resolution；`none` vs `qualifying` | 新 proposal 維持 `qualifying`；[634]，未 approve |
| CPO→external laser source `qualification_status` | stale resolution；Lumentum `qualifying` vs Sivers `sampling` | 新 proposal 維持 `unknown`；[635]，未 approve |

新增兩份 proposal：

- `docs/reports/weekly_scan_2026-09-20_win_sivers_qualification.proposal.json`
- `docs/reports/weekly_scan_2026-09-20_cpo_external_laser_qualification.proposal.json`

兩份都已對 live conflict 跑 `_validate_decision_against_conflict`，驗證 `conflict_id`、`candidate_set_hash`、assertion/source IDs 通過；本輪沒有執行 `approve` 或 `project`。

### 3.4 修前／修後

| 項目 | 修前 | 本輪後 |
|---|---|---|
| sandbox 內 owner-only 檢查 | Engine C fail closed、risk snapshot fatal、pytest collection 被拒 | owner context 重跑後全部可讀；不是 repo／ledger 故障 |
| active lead classification | 0 未分類 | 維持 0；新增 lead 含封閉字彙 classification |
| open edge conflicts | 4 | 仍為 4；新增 2 份 current-hash proposal 與 [634]／[635]，未越過人工 gate |
| Coherent lifecycle | `review_required`，但尚無 unified pq2 item | `todo sync` 新增 [636]；lifecycle 本體未變 |
| Vistara duplicate | 1 組 | 未變；無安全已授權 corridor |

## 4. 投組風險完整快照與較前次趨勢

快照時間 2026-09-20 04:17 +08:00，policy `2026-08-29.1`，NAV USD 468,665.88。`--no-refresh` top-level status 為 `degraded`，原因是台股行情 freshness；authority 與 risk snapshot 可讀，hard blocks = 0。

| 指標 | 2026-09-13 | 2026-09-20 | 約略變化 |
|---|---:|---:|---:|
| NAV | USD 464,796 | USD 468,666 | +USD 3,870 |
| 總曝險 | 1.083x | 1.085x | +0.002x |
| 槓桿 ETF 投入資本占 NAV | 7.18% | 7.38% | +0.20pp |
| 槓桿 ETF 換算曝險 | 16.66% | 17.09% | +0.43pp |
| 已提款貸款／NAV | 5.10% | 5.04% | -0.06pp |
| combined effective | 21.76% | 22.12% | +0.36pp |
| Alpha／NAV | 1.54% | 1.60% | +0.06pp |
| TSMC 已知至少曝險 | 29.49% | 29.86% | +0.37pp；coverage 仍為 partial |
| 共同可投資現金 | USD 30,708 | USD 30,657 | -USD 51 |
| 未動用貸款額度 | USD 165,997 | USD 165,287 | -USD 710 |

- 已提款貸款約 USD 23,612，估計月息約 USD 61；未動用額度不計入 NAV／cash／allocation。
- 自有資本歸零門檻對應指數跌幅約 92.17%；總曝險 cap 1.75x。
- TSMC 29.86% 只能寫「已知至少」；issuer look-through 未建模 `00981A.TW`、`DRAM`、`LON:VWRA`、`QQQ`、`SOXX`、`TQQQ`。
- Alpha 與 Beta 仍高度共用 AI／photonics 因子；兩個 sleeve 不是兩個獨立賭注。

## 5. Triage 稽核

### 5.1 本輪結果

| 結果 | 數量 | 說明 |
|---|---:|---|
| 新 PASS | 1 | Open CPX Specification 1.0；停在 `triaged_go` |
| 新 FILTER lead | 0 | 重複／已被 daily 捕捉的事件不另建 lead，不能把「未重複登記」算成 FILTER |
| 已有 daily coverage | 3 clusters | GF–Marvell、Tower–NewPhotonics、Digit 5 |
| source-trace／extract／ingest | 0 | 明確超出 Weekly 邊界 |

### 5.2 Engine B 現況

| status | 數量 |
|---|---:|
| `triaged_no_go` | 547 |
| `triaged_go` | 13 |
| `parked` | 475 |
| `action_prepared` | 1 |
| `pending` | 1 |
| `applied` | 83 |

- Trace backlog：59 筆；31 `watching`、28 `stalled`、12 `poll_eligible`、31 `auto_trigger_reachable`、0 `requires_user`。
- Trace status：38 `partial`、12 `isolated_tier_3`、6 `awaiting_named_disclosure`、3 `lead_only_tier_4`。

## 6. 建議 onboard 候選

`onboard-candidates` 目前輸出 106 個 deterministic nominations（74 cashtag、32 manual）。這只是「PASS lead 逐字點名但 registry 未登記」的機械清單，不是 onboard 建議、投資排序或 evidence quality；cashtag 有明顯同名／誤識別風險，manual 名稱也尚未做語意合併。

### 6.1 提名次數最高

| 候選 | lead 數 | 偵測 | 樣本脈絡 |
|---|---:|---|---|
| AMZN | 17 | cashtag | 電商／機器人與 AI infrastructure composite posts |
| SPCX | 7 | cashtag | memory／CW laser composite posts |
| BE | 6 | cashtag | 高 beta／AI infrastructure composite posts |
| SMTC | 5 | cashtag | CW agreement／optical component shortage |
| CXMT | 3 | cashtag | memory／IPO composite posts |
| EWY | 3 | cashtag | memory composite posts；可能是 ETF 而非公司候選 |
| FORM | 3 | cashtag | CPO test／measurement discussion |
| LPK | 3 | cashtag | composite post；identity 待確認 |
| QCOM | 3 | cashtag | Amazon warrant／AI infrastructure |

### 6.2 與現行 CPO 研究較直接相關的 manual nominations

| 候選 | lead 數 | 樣本脈絡 |
|---|---:|---|
| Fabrinet (NYSE: FN) | 2 | CPO OSA／switch ODM 分工未知 |
| Advantest (6857.T) | 1 | photonics wafer test／known-good-die |
| AIXTRON (AIXA.DE) | 1 | CW laser epi／MOCVD 設備 |
| ASMPT | 1 | sub-micron／high-throughput bonding |
| FormFactor (FORM) | 1 manual + 3 cashtag | photonics wafer-level test |
| GIGALIGHT | 1 | socket-based 1.6T NPO 量產障礙 |
| NewPhotonics | 1 | laser-integrated 6.4T CPX/NPO counter-path |
| SENKO Advanced Components | 1 | detachable optical connector |

本週新建的 Open CPX lead 沒有另加 manual company nomination；MSA 會員名單很長，若沒有具體 bottleneck／customer event，不把「會員」本身轉成 onboard 候選。

## 7. unified pq2（穩定編號，只揭露不處置）

### 卡在你：8 項

- [541] RV reducer claim 更正。
- [568] Coherent OCS `qualification_status` stale resolution。
- [569] Coherent OCS `ramp_execution` unknown proposal。
- [576] MALE 軍用無人機 decompose 選題。
- [578] COHR 多年賭注／FY28 view 改寫。
- [634] WIN Semiconductor→Sivers `qualification_status` 維持 `qualifying`。
- [635] CPO→external laser source `qualification_status` 維持 `unknown`。
- [636] Coherent CPO thesis `review_required` 複查。

### 系統在做：1 項

- [592] VPEC 獨立來源 work order 已 queued；不需使用者動作。

### 明確在等世界：2 項

- [586] 上詮 fiber attach substitutability：等客戶端／法定文件具名。
- [632] Sivers CW DFB／DWDM qualification：等量產或客戶具名揭露。

### `source_cleared`，待互動 session 查 ground truth：25 項

- [200]、[276]、[279]、[348]、[362]、[407]、[421]、[458]、[461]、[472]、[492]、[493]、[494]、[495]、[522]、[552]、[558]、[561]、[562]、[570]、[593]、[598]、[619]、[621]、[622]。
- Pool ground truth：active 36；`source_cleared` 25；`waiting_on` 16；`deferred_at` 16；其中 14 項同時有 `source_cleared` 與 `waiting_on`。因此「來源本輪不再產出」不能直接推成完成或應 drop。
- 查證命令：

```powershell
$pool = Get-Content library\leads\todo_pool.json -Raw | ConvertFrom-Json
$pool.items | Where-Object { -not $_.resolved_at } | Select-Object n,title,source_cleared,waiting_on,deferred_at
```

Weekly 只發現、不處置；本節不輸出 `go`／`drop` 建議。

## 8. 驗證

- Owner-context health：`.venv\Scripts\python.exe query\health_audit.py --local` → exit 0；Engine C 73/73 freshness 綠，紅項只有 1 組 duplicate SourceDoc、4 個 open conflicts 與 Coherent `review_required`。
- Edge projection dry-run：520 edges、359 materialized attrs、4 open conflicts、26 derived conflicts、22 valid resolutions。
- 兩份新 proposal 均通過 live `_validate_decision_against_conflict`。
- Full suite：`2790 passed, 1 skipped, 1 Starlette/httpx deprecation warning`，耗時 384.99s。
- `classification-health`：0 active unclassified；`harvest-health`：0 unresolved failure。

## 建議摘要

- [634] WIN Semiconductor→Sivers：current-hash proposal 延續既有 `qualifying` 判斷；待互動 session 檢視是否核准 deterministic replacement。
- [635] CPO→external laser source：品類層混合不同供應商階段，proposal 維持 `unknown`；待互動 session 檢視。
- [636] Coherent CPO thesis：反證已觸發 `review_required`；需要完整複查，但本週不改結論。
- [568]／[569]：Coherent OCS 兩個既有 conflict 仍 open；proposal hash 仍有效。
- Vistara duplicate SourceDoc：確認為真實 health 紅項，仍沒有安全且已授權的 consolidation corridor。

可直接複製的批次指令：無（Weekly 只發現、不處置；請在互動 session 檢視 [634]、[635]、[636]，並一併確認 [568]、[569]）
