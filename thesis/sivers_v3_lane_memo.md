<!-- output_type: [Research Note] | ticker: SIVE.ST | checklist_pass: False | l9_pass: False | evidence_manifest_pass: True | evidence_gate_pass: False -->

# Directional Lane Memo — Sivers Semiconductors (SIVE.ST)
> **[Research Note]** 財務核驗清單未全通過（客戶集中度與 Backlog 待補），本備忘錄為方向性參考，不構成可操作投資建議。倉位數字需待 Gate 全通過後由獨立財務引擎填寫。

---

## 1. 一句 Thesis

**Sivers Semiconductors 因 CPO 架構對外部雷射陣列的結構性需求，疊加 GF/O-Net/Enablence 平台路線進入採樣→量產過渡窗口，有望在 2026–2027 年實現 Photonics 營收實質放量——但毛利率深度負值與 InP 供應鏈競爭格局，構成上行路徑的關鍵不確定性。**

### Variant Perception

**市場現在信什麼（X）：** SIVE.ST 現價 SEK 33.48，EV/Revenue 達 36.5x，毛利率為 -2.4%——以現價買入者必須相信 Photonics 收入將在 2-3 年內實現數倍增長、且毛利率將快速翻正，使公司最終具備高倍數合理性。換言之，市場（股價）已把「CPO 雷射龍頭成功兌現」的樂觀情境大幅 price in。分析師目標價均值 SEK 9.95（N=4），遠低於現價——代表賣方認為現價隱含假設過於樂觀，**股價比賣方共識樂觀約 3.4 倍**。

**本 thesis 認為（Y）：** Sivers 目前核心產品（CW DFB 雷射、DWDM 陣列）仍處於「sampling」階段，ELS 模組 production readiness 目標為年底 2026，GF SCALE 平台整合為 reference design 尚未轉化為付費訂單 [E6][E7][E8]。實際可見的 Photonics 收入（FY2025：SEK 93.4M，YoY +17%）在集團中佔比僅約 30%，主要獲利來源仍是 SATCOM/國防 Wireless 業務 [E1]。毛利率 -0.7%（FY2025）且原材料成本 YoY +116% [E2]，顯示量產前期成本曲線尚未到達拐點。**本 thesis 認為「成功」的概率方向正確，但時間表與毛利率恢復速度比市場股價所暗示的更緩慢、更不確定。**

**催化劑（Z）：** H2 2026 ELS production readiness 確認、首個非 Ayar 平台的付費量產訂單（特別是來自 GF SCALE 或 O-Net 下游客戶），以及毛利率轉正的季度財報——任何一項若落後於 2026 年底，將對現有估值構成重新定價壓力。

---

## 2. 需求驅動

- **CPO 的結構性功耗優勢**推動超大規模資料中心採用：外部雷射源（ELS）相比傳統插拔式收發器顯著降低功耗，是 CPO 架構的關鍵組件 [E3]。隨 AI 訓練叢集從 800G 向 1.6T/3.2T 過渡，CW 雷射需求預計在未來幾年出現供應缺口 [E4]。

- **Scale-up 算力架構強化 DWDM 雷射陣列需求**：Sivers 的 DWDM 雷射陣列與矽光子 chiplet 結合，被定位為 AI 資料中心短距光互連的策略性關鍵輸入 [E5]。

- **平台化路線拉動採樣管線**：Sivers 雷射陣列進入 GF 矽光子參考設計並納入 SCALE CPO 平台，建立了一條不依賴單一終端客戶的路線到市場管道 [E6][E7]；同時 Sivers-O-Net-Enablence 三方 ELS 模組在 OFC 2026 公開揭露，進一步擴大接觸點 [E8]。

- **Lumentum 超額供需缺口（InP 層）創造替代機會**：Lumentum InP 晶圓廠產能已全滿，EML 供需缺口超過 30%，且新 Greensboro 廠需約 6 個季度以上才能貢獻收入 [E9][E10]——此結構性短缺為能快速出貨的替代供應商（包含 Sivers）提供市場空間，但 Sivers 目前仍處於 sampling 而非正式量產。

---

## 3. Stack 摘要

**晶片製造層（Tier 3 Foundry）**：Win Semiconductor 與 Sivers 的合作已進入 qualifying 狀態，為量產佈局提供高產能底座 [E11]；GF 矽光子平台整合 Sivers 雷射陣列於 SCALE 模組，使 Sivers 在 foundry 整合層取得位置，但仍為 reference design 而非已確認的付費量產訂單 [E6]。

**模組整合層（ELS/Light Engine）**：此層正在發生最顯著的結構性重組——Sivers-O-Net-Enablence 三方聯盟、Sivers-POET 合作（sampling 階段，ramp_execution=3）[E12]、以及 Sivers-LIGHTIUM AG TFLN 整合（qualifying）[E13] 均在此層推進。多路並行的合作結構有助分散風險，但也意味著無任何單一通道已確定量產。

**客戶端（hyperscaler/switch OEM）**：目前 Sivers 在已知 CPO 客戶生態中最具可信度的節點為 Ayar Labs SuperNova（designed_in，有第三方貿易媒體佐證）[E14]；GF SCALE 平台整合為間接通路，尚未有已命名的終端超大規模客戶確認設計。競爭者 Coherent 與 Lumentum 均已出現在 NVIDIA CPO 生態系統名單，Sivers 則尚未見於同一名單。

---

## 4. 主瓶頸

**目前資料尚未確認圖中存在指向 Sivers 的 sole_source=✓ 邊**，所有相關邊的 `sole_source` 欄位均未填寫或明確標示為 False（Ayar Labs 邊）。以下依 substitutability 與 qualification 狀態識別最關鍵的執行瓶頸：

**主要執行瓶頸：ELS 模組的 production readiness 交付（Sivers → O-Net → 下游 CPO 客戶）**

- **為何是瓶頸**：ELS 模組是 Sivers Photonics 收入放量的核心觸發點，production readiness 目標為 2026 年底 [E15]；目前 qualification_status 為 qualifying、ramp_execution=3，表示仍有顯著執行風險。
- **競爭壓力加劇替代風險**：POET 在 OFC 2026 現場展示其 Blazar ELS 產品，並聲稱成本比 DFB 雷射低一個數量級 [E16]——雖 Marvell/Celestial AI 已取消對 POET 的訂單 [E17]，但 POET 自述仍在服務其他客戶，且 Blazar 的成本定位構成對 Sivers DFB 陣列的潛在替代威脅。
- **Lumentum 競爭動態**：silicon_matter 報導指出 Lumentum 於 2024 年挖角 Ayar Labs 前雷射部門 VP 出任 CTO，以強化 CPO 市場佈局 [E18]——此舉意味 Sivers 在 Ayar 生態系統的既有位置可能受到挑戰，但目前圖中無主要文件確認 Lumentum 已替代 Sivers 於 Ayar SuperNova。
- **資料缺口**：圖中無 Sivers 的 backlog 或 LTA（長期協議）資料，難以評估需求能見度。財務核驗清單中 Backlog/訂單能見度項目為 manual_required，需人工補充。

---

## 5. 最強證據

- [E2] Sivers FY2025 毛利率 -0.7%，原材料成本 YoY +116%，生產前期擴張中（Tier 1 財報，origin: Sivers Semiconductors，source_under_audit=True）
- [E1] Photonics 收入 SEK 93.4M（YoY +17%），無單一客戶超過集團收入 10%；Wireless 三大客戶佔集團收入 >50%（Tier 1 財報，origin: Sivers Semiconductors，source_under_audit=True）
- [E14] Semiconductor Today（2023-07-03）獨立報導確認 Sivers 獲 Ayar Labs 100 萬美元訂單，DFB 雷射陣列為 SuperNova 提供光源（Tier 2 貿易媒體，非 Sivers 自述）
- [E8] Enablence/Sivers/O-Net OFC 2026 聯合公告：8 通道 ELS 模組三方合作具體化，O-Net 為 OEM 整合方（Tier 2 官方公告，origin: Enablence Technologies）

---

## 6. 什麼會推翻這個 Thesis（Disproof Conditions）

- 若 **2026 年底 ELS production readiness 未達成**（Sivers-O-Net 合作未能如期推進客戶驗證），且 Photonics 收入增速在 2026 全年持平或下滑，則 Photonics 放量時間表需全面後移，估值壓力將顯著加劇（推導，非圖中明確主張）。

- 若 **Ayar Labs 公開確認替代雷射陣列供應商**（例如 Lumentum 或其他進入 SuperNova 設計），或 Sivers 主動披露失去 Ayar 計畫，則 Sivers 在 CPO 生態系統中最具公開可信度的 designed_in 節點消失，thesis 的技術差異化基礎需降評 [E14][E18]。

- 若 **原材料與外部製造成本在 2026-2027 量產爬坡後仍未下降**，毛利率無法轉正，則 Photonics 收入增長無法轉化為盈利能力改善，thesis 的財務路徑失效（來自 `sivers_ar_2025_financials_cl2` 的 disproof_condition）[E2]。

---

## 7. 接下來盯什麼（Leading Indicators / Catalysts）

- **ELS production readiness 確認**（觀測頻率：每季法說會 + 每次客戶公告）：Sivers-O-Net 是否在 2026 年底前宣布完成 ELS 量產就緒，或首個付費 ELS 訂單落地。這是 Photonics 收入從「採樣」進入「量產」最直接的確認信號 [E15]。

- **GF SCALE 平台的首個終端客戶設計採用**（觀測頻率：每次客戶公告 / GF 法說會）：目前 Sivers-GF 合作停留在 reference design 與 qualifying 階段，任何已命名超大規模客戶或 switch OEM 採用 SCALE 平台的公告，將把這條路線從「平台機會」轉化為「已確認需求」[E6][E7]。

- **Photonics 季度毛利率趨勢**（觀測頻率：每季財報）：集團毛利率是否從 -2.4%（最新）開始回升，是量產爬坡是否壓低單位成本的最早財務信號。若 2026 H2 毛利率仍為負值，執行風險旗標需升級 [E2]。

- **POET Blazar 或其他 DFB 替代技術的客戶採用公告**（觀測頻率：每次競爭對手公告）：POET 聲稱 Blazar 成本比 DFB 低一個數量級 [E16]；若有已命名客戶確認採用 Blazar 替代 DFB 陣列，將直接衝擊 Sivers 的技術差異化論點，需作為 thesis 降評觸發點監測。

## Evidence Gate Notes
- ⛔ [E1] SourceDoc sivers_ar_2025_financials 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E2] SourceDoc sivers_ar_2025_financials 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E3] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E4] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E5] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E10] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E11] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E12] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E13] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E15] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)

本報告因上述 evidence gate 未通過，維持 Research Note。
