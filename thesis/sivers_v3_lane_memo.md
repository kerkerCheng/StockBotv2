<!-- output_type: [Research Note] | ticker: SIVE.ST | checklist_pass: False | l9_pass: False | evidence_manifest_pass: True | evidence_gate_pass: False -->

# Directional Lane Memo — Sivers Semiconductors (SIVE.ST)

> **[Research Note]** 本備忘錄屬方向性研究，不構成可操作投資建議。財務核驗清單尚有人工待填項目（客戶集中度、Backlog能見度），Watchlist升格須待 Gate 全數通過。

---

## 1. 一句 Thesis

Sivers Semiconductors 因 CPO 外部雷射源需求加速及 GF/O-Net/Enablence 多軌平台落地，其光子產品組合在 2026–2027 年具備從採樣→量產的結構性升級機會；然而毛利率深度負值與 Wireless 高度集中風險形成對沖，thesis 成立的前提是光子段收入佔比於 FY2027 顯著提升。

**Variant Perception：**
市場當前定價（EV/Rev = 36.5×，股價 SEK 33.48，分析師目標價均值 SEK 9.95，N=4）隱含兩種截然對立的解讀：若市場共識傾向悲觀（分析師目標價大幅折價現價），則市場信 X = Sivers 光子業務無法在 2026–2027 年達成有意義量產收入，毛利率持續負值且 Wireless 客戶集中風險惡化，導致股價超漲於基本面。本 thesis 認為 Y = Sivers 透過 GF SCALE™ 平台（qualifying 狀態）[E7]、O-Net/Enablence 8 通道 ELS 模組（designed_in）[E8] 及 Win Semiconductor 量產聯盟（qualifying）[E9]，已在多個關鍵下游通道建立可驗證的技術卡位，若 FY2026 年底 ELS 生產就緒如期達成，光子段毛利結構有機會脫離虧損區間。催化劑 Z = 2026Q4 ELS 生產就緒公告、GF SCALE 首個客戶設計導入（design win）、或 CW DFB 雷射進入任一大型可插拔模組廠量產採購。若上述催化劑落地，市場可能重新評估 EV/Rev 是否反映光子段的長期 TAM 而非現有虧損體質。

> **注意：** Variant Perception 的估值判斷需 Engine C（基本面引擎）補充完整 backlog、客戶集中度及毛利率恢復路徑後才能量化為目標價範圍；現階段僅提供方向性錨點。

---

## 2. 需求驅動

- **CPO 功耗優勢形成結構性替代動力：** CPO 架構每 100G 通道功耗約為傳統可插拔模組的 35%（~5.5W vs 16–18W），資料中心算力擴張直接推升對外部雷射源的需求 [E1]。

- **CW 雷射供給短缺預期明確：** 超大規模雲端業者與可插拔模組廠商的討論顯示，隨行業從 800G 向 1.6T、3.2T 頻寬演進，CW 雷射將在未來數年出現供給短缺 [E2]。

- **DWDM 雷射陣列成為 AI 規模擴展互連的關鍵輸入：** Sivers 的 DWDM 雷射陣列與矽光子小晶片的 Co-Packaged 組合被定位為替代短距銅互連的核心方案，直接受益於 AI 資料中心規模擴展需求 [E3]。

- **ELS 模組成為非主要 CPO 客戶的市場進入貨幣：** 對光學技術較不熟悉的 CPO 客戶，ELS 模組是供應商切入的主要形式，Sivers/O-Net/Enablence 三方組合的 8 通道 ELS 正是針對此市場定位 [E4]。

---

## 3. Stack 摘要

在 **元件層（Component Level）**，InP 基底 CW/DFB 雷射的供給瓶頸已被多家業者（Lumentum、Coherent）確認，Sivers 以 GaAs 代工轉 InP 路線（透過 Win Semiconductor）嘗試填補缺口，但目前仍處於 qualifying/sampling 階段，尚未進入量產收入。在 **模組層（Module Level）**，Sivers-O-Net-Enablence 三方 ELS 及 GF SCALE™ 平台代表從雷射晶片到封裝光引擎的垂直整合嘗試，此層正在發生最明顯的供應鏈結構重組。在 **平台層（Platform/Ecosystem Level）**，GF 矽光子平台提供 Sivers 一條繞開傳統 IDM 壟斷的路徑，但 GlobalFoundries 與 Sivers 的合作目前為 qualifying 狀態，尚無客戶設計導入確認，集中風險尚未解除。

---

## 4. 主瓶頸

**目前資料尚未確認 Sivers 任何供應關係帶有 `sole_source=✓` 屬性；** 圖中 Sivers→Ayar Labs 邊明確標注 `sole_source=False` [E10]，其餘邊未賦予 sole_source 屬性。依硬規則，不自行推斷 sole_source。

以下說明圖中可識別的主要執行風險與瓶頸候選：

1. **Win Semiconductor → Sivers 量產就緒度（ramp_execution=4）** [E9]：Win Semiconductor 作為高產能代工廠的合作已進入 qualifying 狀態，ramp_execution 分數為 4（5 分制，越高越難執行），顯示量產爬坡執行難度偏高。目前 qualification_status = qualifying，尚未達到生產就緒。

2. **Sivers → O-Net ELS 模組（ramp_execution=3，production readiness 目標 2026 年底）** [E5]：ELS 模組的生產就緒目標為 2026 年底，客戶原型展示目標為 2026H1。目前 qualification_status = qualifying，時間視窗緊張。

3. **Sivers → POET 通道已中斷：** Marvell/Celestial AI 取消 POET 所有採購訂單，直接切斷 Sivers→POET→Celestial 的間接需求路徑 [E11]。此為已確認的負面事件，非未決衝突。

4. **Sivers → GF SCALE™（qualifying，無 ramp_execution 評分）** [E7]：GF 合作為 2026 年 6 月 2 日宣布的新合作，尚無客戶設計導入（design win）確認，為平台布局而非確認訂單。

**資料缺口：** 圖中無 Sivers 光子段的具體 backlog 數字、無 ELS 模組的 substitutability 評分、無 CW DFB 雷射在大型可插拔廠的 qualification_status，上述項目需補充後才能完整評估瓶頸嚴重程度。

---

## 5. 最強證據

- [E12] Sivers FY2025 光子段收入 SEK 93.4M（+17% YoY），前三大客戶均屬 Wireless 段，光子段無單一客戶超過集團收入 10%（來源：Sivers FY2025 年報，經審計，Tier 1）

- [E13] Sivers FY2025 集團毛利率 -0.7%（毛損 SEK 2.1M），原材料成本同比增長 +116%，反映量產爬坡前期的成本結構壓力（來源：Sivers FY2025 年報合併損益表，經審計，Tier 1）

- [E5] Sivers 與 O-Net 合作的 ELS 模組原型將於 2026H1 向客戶展示，生產就緒目標為 2026 年底（來源：Sivers FY2025 年報光子段，經審計，Tier 1）

- [E6] 獨立財經媒體 Semiconductor Today（2023-07-03）確認 Sivers 光子部門獲得 $1M 訂單，DFB 雷射陣列為 Ayar Labs SuperNova 提供光源（第三方來源，Tier 2，非 Sivers 自述）

---

## 6. 什麼會推翻這個 Thesis（Disproof Conditions）

- 若 Sivers 的 ELS 生產就緒時間延後至 2027 年後，且同期競爭對手（如 Lumentum）完成自有 ELS 產品的量產認證，則 Sivers 的時間窗口優勢消失，thesis 需降評。（來源：`sivers_ar_2025_photonics_excerpt_cl5` disproof_condition 推導）

- 若原材料及外部製造成本在 FY2026–2027 量產爬坡期間無法下降，毛利率持續負值，Sivers 將面臨資本消耗風險，光子段收入增長無法轉化為盈利能力改善，thesis 核心前提不成立 [E13]。（來源：`sivers_ar_2025_financials_cl2` disproof_condition）

- 若 ALL.SPACE 的美國陸軍 NGTT 計畫訂單大幅削減，Wireless 收入驟降將壓縮整體現金流，在光子段尚未貢獻足夠收入之前形成資金缺口，即使光子 thesis 方向正確也難以為繼 [E14]。（來源：`sivers_ar_2025_financials_cl3` disproof_condition）

---

## 7. 接下來盯什麼（Leading Indicators / Catalysts）

- **ELS 生產就緒公告（目標 2026Q4）**：觀測頻率：每季法說會 + 客戶公告。若 Sivers 於 2026Q3/Q4 法說會確認 ELS 達到生產就緒並獲得首個量產採購訂單，為最強正向確認信號 [E5]。

- **GF SCALE™ 平台首個客戶設計導入（Design Win）**：觀測頻率：每次客戶/GF 公告。目前合作為 qualifying 狀態 [E7]，任何 design win 宣布將標誌 Sivers 從參考設計進入實際客戶採購流程，是估值重定價的關鍵催化劑。

- **CW DFB 雷射採樣客戶轉為量產承諾**：觀測頻率：每季法說會。Sivers 自述預計 2027 年及以後有部分採樣客戶轉為量產計畫 [E15]；若此時間點提前，或採樣客戶數量顯著增加，為需求加速信號。

- **光子段毛利率轉正**：觀測頻率：每季財報。集團毛利率目前為 -0.7%（FY2025），最新季度為 -2.4%，需追蹤光子段能否隨量產爬坡實現單季毛利轉正，此為 Watchlist 升格的財務 gate [E13]。

## Evidence Gate Notes
- ⛔ [E1] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E2] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E3] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E5] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E9] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E12] SourceDoc sivers_ar_2025_financials 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E13] SourceDoc sivers_ar_2025_financials 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E14] SourceDoc sivers_ar_2025_financials 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E15] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)

本報告因上述 evidence gate 未通過，維持 Research Note。
