# Phase 1 Step 1.6 既有反證補登記（2026-09-24）

> 由 `docs/plans/2026-09-24-001-feat-phase1-waiting-heartbeat-plan.md` §7 執行。表格由 registry 現值產生（不手抄）；
> 「歷史一手交集」＝1.4 回填後 `source_class=primary`、非持股申報的 lead 裡，實體與這條有交集的筆數（B2）；
> 「有一手覆蓋」＝`event_watch.is_reachable`（有沒有任何一手來源會產出帶它實體的 lead）。

## 1. 分母（先列、後登記）

- 三份 thesis 現行 memo「推翻」那一節：AXT §7 **6**、COHR §6 **5**、Sivers §6 **5**＝**16**。條件原文由 `thesis.memo_structure.disproof_items`
  逐字取出；本 Step 修了它的一個缺口：**縮排續行併入前一條**（AXT 第 2 條跨兩行，只取第一行會截在「→ 「防禦性鎖客」」）。
- AXT `### 7b`（不是反證清單，讀過後判定）：有一條反證型條件——**「Q3 2026 營收 ≥ US$60M」**（variant 賭注的推翻條件；
  7b 表格另兩條與 §7 第 1、4 條語意相同）。依 plan **不併入 16、本 Step 不登記**，列進 closeout §15 由使用者決定。
- 兩份現行讀圖（1.0 記下的 id）：
  - `mat:inp_substrate` `sr_bc1ccb568c8886c0`：【disproof 六條】段 ①–⑥＝**6**。
  - `tech:cw_dfb_laser` `sr_caac0acae9a1c1cf`：只說沿用前一份的反證（寫的數字是六條）、**沒有列條文**；它指的是前一份
    `sr_a181641ddb99c69c` 的【disproof】段，而那一段實際是 ①–⑤ **5 條**。照鏈上的原文登記 5 條（L11：自己引用的事實也要追源）；
    讀圖原文依 plan 不改，這個不一致記在這裡。
  - 原文太短（<20 字）的條目帶上同一句的逐字前導；不連續時用「…」標省略，各片段依序都是原文子字串（程式斷言）。
  - 讀圖 ledger 住 `library/private/alpha/structure_readings/`（不進 Git），所以本報告的讀圖列**不抄原文**：
    原文在該節點 ledger 的 v2 紀錄 `disproof[n]`，registry 的 watch 也帶全文。

## 2. thesis 反證（`register-disproof`，16 條）

核查頻率與 48 小時動作取 memo 開頭那兩行原文（程式斷言是 memo 子字串）。到期：
AXT＝lifecycle next_check 2026-11-15＋90（不早於 2026-10-30／11-13 兩個催化劑）；COHR＝next_check 2026-12-01（12 月六吋檢核點）＋90；
Sivers＝條件自己寫的日期（2027-H1／2027 年中／2027）＋90，沒寫日期的＝關鍵核查點 2026-11-26（Q3 報告）＋90——
核查週期取「每季財報」而非 lifecycle 的 30 天（反證多由季報判定；30 天的重問只會在沒有新季報時再問一次）。
COHR 原文「每週掃描（weekly 審查）」照登記，note 註明 weekly 已由 daily＋互動題材掃描取代；AXT「每週掃描」同理。

| watch_id | source_ref | 條件（原文逐字） | 實體 | 到期 | 歷史一手交集 | 有一手覆蓋 |
|---|---|---|---|---|---|---|
| `ew_0096_2026-09-24` | `thesis:thesis/axt_inp_v1_lane_memo.md#1` | **Q3 2026 毛利率維持 44% 以上且公司揭露 ASP 上漲為主因** → 結構解釋勝出，本 thesis 失效。 | co:axt | 2027-02-13 | 9 | 是 |
| `ew_0097_2026-09-24` | `thesis:thesis/axt_inp_v1_lane_memo.md#2` | Q3 10-Q 的 Lumentum 合約 exhibit 顯示含 ASP 下限或長期定價鎖定條款 → 「防禦性鎖客」的解讀被推翻，議價權解讀成立。 | co:axt, co:lumentum | 2027-02-13 | 12 | 是 |
| `ew_0098_2026-09-24` | `thesis:thesis/axt_inp_v1_lane_memo.md#3` | JX 或住友公開下修、遞延或取消擴產計畫 → 第 3 節的供給側論點失效。 | co:jx_advanced_metals, co:sumitomo_electric | 2027-02-13 | 0 | **否** ⚠ |
| `ew_0099_2026-09-24` | `thesis:thesis/axt_inp_v1_lane_memo.md#4` | AXT 取得對美出口許可並揭露積壓訂單出貨 → 短期營收動能優於預期，需上修。 | co:axt | 2027-02-13 | 9 | 是 |
| `ew_0100_2026-09-24` | `thesis:thesis/axt_inp_v1_lane_memo.md#5` | Q3 營收低於 Q2 的 US$47.589M，或毛利率跌回 35% 以下 → Q2 未成為 run-rate（沿用）。 | co:axt | 2027-02-13 | 9 | 是 |
| `ew_0101_2026-09-24` | `thesis:thesis/axt_inp_v1_lane_memo.md#6` | Q3 10-Q 揭露 PE 基金實際贖回累計逾 RMB 200,000,000 [E10]。 | co:axt | 2027-02-13 | 9 | 是 |
| `ew_0102_2026-09-24` | `thesis:thesis/coherent_cpo_v2_lane_memo.md#1` | 若六吋 InP 產線出現 yield 問題或年底倍增進度大幅落後（12 月檢核點），成本／產能優勢敘事失效，thesis 需降評 [E5]。 | co:coherent | 2027-03-01 | 6 | 是 |
| `ew_0103_2026-09-24` | `thesis:thesis/coherent_cpo_v2_lane_memo.md#2` | 若另一 InP 設施在產量／製程上超越 Sherman，或 Coherent 在關鍵客戶處失去 qualification，主瓶頸地位不成立，thesis 需降評 [E6]。 | co:coherent | 2027-03-01 | 6 | 是 |
| `ew_0104_2026-09-24` | `thesis:thesis/coherent_cpo_v2_lane_memo.md#3` | 若 NVIDIA 協議內產品出現第二供應商 qualify 至同一 design，高 substitutability 假設被推翻，thesis 需降評。(推導，非圖中明確主張) | co:coherent, co:nvidia | 2027-03-01 | 13 | 是 |
| `ew_0105_2026-09-24` | `thesis:thesis/coherent_cpo_v2_lane_memo.md#4` | 若中國 InP 出口管制升級導致 AXT 基板供應中斷、且 Coherent 無法及時 qualify 替代來源，放量計畫受阻，thesis 需降評或退場 [E15][E17]。 | co:axt, co:coherent | 2027-03-01 | 15 | 是 |
| `ew_0106_2026-09-24` | `thesis:thesis/coherent_cpo_v2_lane_memo.md#5` | 若 NVIDIA 需求端因出口政策進一步收縮（中國排除已成事實），CPO ramp 斜率低於預期，thesis 需降評 [E16]。 | co:coherent, co:nvidia | 2027-03-01 | 13 | 是 |
| `ew_0107_2026-09-24` | `thesis:thesis/sivers_v4_lane_memo.md#1` | **ELS 時間表**：2026 年底前未確認 ELS production readiness，且 2027-H1 前 photonics 無任何付費量產訂單（非 NRE）→ 放量時間表全面後移，48h 內決策降評或退場。 | co:sivers_semiconductors | 2027-09-28 | 90 | 是 |
| `ew_0108_2026-09-24` | `thesis:thesis/sivers_v4_lane_memo.md#2` | **Jabil 通道**：1.6T 合作於 2027 未進入 qualification 完成／ramp，或合作終止 → 平台通路論點降評。 | co:jabil, co:sivers_semiconductors | 2028-03-30 | 92 | 是 |
| `ew_0109_2026-09-24` | `thesis:thesis/sivers_v4_lane_memo.md#3` | **Ayar 節點**：Ayar Labs 公開替換雷射供應商或 Sivers 披露失去該計畫 → 最具可信度的 designed-in 證據消失。 | co:ayar_labs, co:sivers_semiconductors | 2027-02-24 | 90 | 是 |
| `ew_0110_2026-09-24` | `thesis:thesis/sivers_v4_lane_memo.md#4` | **資金螺旋**：毛利率至 2027 年中仍深度為負且需再次大額增發 → 稀釋侵蝕 per-share thesis，降評。 | co:sivers_semiconductors | 2027-09-28 | 90 | 是 |
| `ew_0111_2026-09-24` | `thesis:thesis/sivers_v4_lane_memo.md#5` | **信用重開**：任何新的收入認列質疑、審計調整超過營收 1%，或 going-concern 敘述惡化 → credibility hold 重啟，回 `review_required`。 | co:sivers_semiconductors | 2027-02-24 | 90 | 是 |

登記後跑了一次 `python -m engine_b.todo sync`：1.5 的對帳**沒有** consume 任何一筆（16 條都指向 lifecycle 的現行 memo）。

## 3. 讀圖反證（兩份 v2 取代紀錄，11 條）

`python -m alpha structure-reading <node> --add <spec>`；`kind`、`reading` 原文、`expires`、`tickers` 與現行那一份相同，`supersedes_id`＝現行 id。
append 前 `--check` 兩節點都是 current（digest 沒變）——快照與原讀圖一致，沒有研究發現要寫。

- `mat:inp_substrate` → **`sr_ad503ae880ceb398`**（v2，6 條；watch 到期＝讀圖到期 2026-12-17＋讀圖有效期 90＝2027-03-17）
- `tech:cw_dfb_laser` → **`sr_d07679979a8e4202`**（v2，5 條；watch 到期＝2026-10-18＋30＝2026-11-17）

核查頻率＝「依讀圖自己的到期重讀」（圖內條件另註由 `structure-reading --check` 現形）；48 小時動作＝重讀本節點、決定維持或改判
（讀圖原文沒有這一欄，這是系統寫的，不是引文）。

| watch_id | source_ref | 條件（原文逐字） | 實體 | 到期 | 歷史一手交集 | 有一手覆蓋 |
|---|---|---|---|---|---|---|
| `ew_0112_2026-09-24` | `reading:sr_ad503ae880ceb398#1` | （原文在 private ledger，不進 Git） | co:axt, co:jx_advanced_metals, co:sumitomo_electric | 2027-03-17 | 9 | 是 |
| `ew_0113_2026-09-24` | `reading:sr_ad503ae880ceb398#2` | （原文在 private ledger，不進 Git） | co:axt, co:jx_advanced_metals, co:sumitomo_electric | 2027-03-17 | 9 | 是 |
| `ew_0114_2026-09-24` | `reading:sr_ad503ae880ceb398#3` | （原文在 private ledger，不進 Git） | co:iqe | 2027-03-17 | 0 | **否** ⚠ |
| `ew_0115_2026-09-24` | `reading:sr_ad503ae880ceb398#4` | （原文在 private ledger，不進 Git） | co:axt, co:jx_advanced_metals, co:sumitomo_electric | 2027-03-17 | 9 | 是 |
| `ew_0116_2026-09-24` | `reading:sr_ad503ae880ceb398#5` | （原文在 private ledger，不進 Git） | co:axt | 2027-03-17 | 9 | 是 |
| `ew_0117_2026-09-24` | `reading:sr_ad503ae880ceb398#6` | （原文在 private ledger，不進 Git） | co:coherent | 2027-03-17 | 6 | 是 |
| `ew_0122_2026-09-24` | `reading:sr_d07679979a8e4202#1` | （原文在 private ledger，不進 Git） | co:coherent, co:landmark_optoelectronics, co:lumentum, co:luxnet, co:sivers_semiconductors, co:vpec | 2026-11-17 | 102 | 是 |
| `ew_0123_2026-09-24` | `reading:sr_d07679979a8e4202#2` | （原文在 private ledger，不進 Git） | co:coherent, co:landmark_optoelectronics, co:lumentum, co:luxnet, co:sivers_semiconductors, co:vpec | 2026-11-17 | 102 | 是 |
| `ew_0124_2026-09-24` | `reading:sr_d07679979a8e4202#3` | （原文在 private ledger，不進 Git） | co:poet_technologies | 2026-11-17 | 9 | 是 |
| `ew_0125_2026-09-24` | `reading:sr_d07679979a8e4202#4` | （原文在 private ledger，不進 Git） | co:coherent | 2026-11-17 | 6 | 是 |
| `ew_0126_2026-09-24` | `reading:sr_d07679979a8e4202#5` | （原文在 private ledger，不進 Git） | co:poet_technologies | 2026-11-17 | 9 | 是 |

1.5 的 hook 在真實資料上第一次跑：反證 watch 登記 11、需求側客戶的 `wake_reading` 登記 5、被取代收掉 0（v1 沒有反證 watch）。

| watch_id | 節點 | 客戶 | 到期 |
|---|---|---|---|
| `ew_0118_2026-09-24` | `mat:inp_substrate` | co:casela_technologies | 2026-12-17 |
| `ew_0119_2026-09-24` | `mat:inp_substrate` | co:coherent | 2026-12-17 |
| `ew_0120_2026-09-24` | `mat:inp_substrate` | co:iqe | 2026-12-17 |
| `ew_0121_2026-09-24` | `mat:inp_substrate` | co:lumentum | 2026-12-17 |
| `ew_0127_2026-09-24` | `tech:cw_dfb_laser` | co:lumentum | 2026-10-18 |

## 4. 計數（`engine_b.disproof.disproof_counts`，登記後）

預期 27｜在盯 27｜**叫不醒 2**｜觸及待處置 0｜未盯 0｜
v1 讀圖散文 0 份｜凍結歷史 32（不盯）｜sidecar 不符 0

叫不醒（登記了但沒有任何一手來源會叫醒它）：
- AXT §7 第 3 條（JX／住友）——plan 預期；兩家都沒有一手 feed。
- `mat:inp_substrate` ③反向路徑（`co:iqe`）——IQE 只有 Yahoo 的二手 feed（`yahoo:iqe-l`，`source_class=secondary`）。

## 5. N15：三份 thesis 引用的 claim 反證

sidecar 的 `evidence_items` 共 47 項＝**claim 39＋edge 8**（plan 寫的「47 個 claim」其實含 8 條 edge）；39 個 claim 去重後仍是 39（三份 thesis 沒有共用），
**39 個全部帶 claim 層級的 `disproof_condition`**（AXT 11、COHR 12、Sivers 16）。本 Step 不登記，進 closeout §15 由使用者決定。
（查法：`extractions/*.json` 的 claim；舊檔的 `id` 是檔內編號，全域 id＝`<source_doc.doc_id>_<id>`——第一次只比 `id` 時 20 個「找不到」是查法錯，不是不存在。）

## 6. 本 Step 看到、不在範圍內的

- 同一次 `todo sync` 叫醒了追源型 `ew_0042`（Sivers Q2 新聞稿 `lead_669171e6…`，由 1.4 回填的 `company_id` 交集）——1.4 的 L11-6 已預告；由 daily ⑨ consume-fired 排回 pq1。
- Sivers 一則一手公告會同時叫醒 7 條語意 watch（thesis 5＋讀圖 2），而預篩每日名額是 10——進 closeout §15（工作量，不是錯）。
