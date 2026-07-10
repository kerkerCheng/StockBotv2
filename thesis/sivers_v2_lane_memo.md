<!-- output_type: [Research Note] | ticker: SIVE.ST | checklist_pass: false | l9_pass: false -->
<!-- gate_override: L8 測試用，文件補強中 — 所有主張來源為 Sivers 自報，尚無獨立佐證 -->

# Directional Lane Memo — Sivers Semiconductors (SIVE.ST)
**生成日期：** 2026-07-10
**L8 狀態：** ⚠ Override — 1/3 origin_entity（Sivers 自報），尚無客戶端或第三方獨立來源

### 1. 一句 thesis

Sivers Semiconductors 的 InP DFB 雷射陣列在 CPO 外置雷射源（ELS）市場處於早期 design-in 階段，若 2026 下半年客戶原型驗證成功，可能成為下一代 1.6T/3.2T 光互連的瓶頸供應商——但目前所有正向主張均來自公司自報，缺乏獨立驗證。

**Variant Perception：**
當前股價 40.58 SEK（EV/Revenue 44.9x，Forward P/E -202.9x）隱含市場假設：SIVE 將在 CPO 量產前順利完成多客戶認證並取得設計窗口，且毛利率可在 2-3 年內轉正。本 thesis 認為這個假設的時間表偏樂觀——原型驗證到量產認證通常需 12-24 個月，現在取樣（sampling）距離「committed production plans」仍有重要里程碑未達成。分析師共識目標價 9.95 SEK（N=4），較現價有大幅下修空間，暗示市場定價主要來自散戶的情緒溢價而非機構的基本面共識。**催化劑：** H1 2026 客戶原型展示結果（2026-07 應已出爐或即將公布）。

### 2. 需求驅動

- AI 算力擴張推動資料中心從 800G 往 1.6T、3.2T 光互連過渡，CPO 採外置雷射源以降低功耗，創造結構性需求。(source: sivers_ar_2025_photonics_excerpt_s5)
- CPO 搭配矽光子 chiplet 的 scale-up 組網需要 DWDM 雷射陣列，Sivers 定位為此應用核心輸入。(source: sivers_ar_2025_photonics_excerpt_s10)
- CW 雷射供應預期數年內短缺，認證周期長、新供應商門檻高。⚠ 此主張來自 Sivers 自報，未獨立確認。(source: sivers_ar_2025_photonics_excerpt_s8)

### 3. Stack 摘要

end_demand→module_subsystem 轉換加速，多家超大規模雲廠商承諾 CPO roadmap。在 device_chip 層，ELS 成為關鍵子系統；Sivers 從 materials_substrate（InP）向上整合至 DFB 陣列。module_subsystem→device_chip 銜接點（誰把 SIVE 雷射整進 ELS 模組）是最大缺口；圖中知 O-Net 和 POET 為下游，但其最終客戶連結未驗證。

### 4. 主瓶頸

⚠ 圖中未確認 sole_source 邊，所有 sole_source 欄均為空。

- Sivers 正在向多家全球光收發器製造商取樣 CW DFB 雷射，預計 2027+ 進入量產計畫。(source: sivers_ar_2025_photonics_excerpt_s9)
- Sivers + O-Net 目標 2026 年底 ELS 量產就緒，H1 2026 客戶原型展示。(source: sivers_ar_2025_photonics_excerpt_s12)

**資料缺口：** sole_source 狀態、競爭者 qualification 進度、以及 SIVE 在哪個客戶 BOM 已確定——全部無法從現有圖回答（L8：所有資料來自 Sivers 自報）。

### 5. 最強證據

- [sivers_ar_2025_photonics_excerpt_s5] ELS 是下一代 CPO 關鍵組件，功耗顯著低於可插拔光模組。（confidence: 0.90）⚠ L8
- [sivers_ar_2025_photonics_excerpt_s9] Sivers 向多家全球廠商取樣，部分預計 2027+ 承諾量產。（confidence: 0.85）⚠ L8
- [sivers_ar_2025_photonics_excerpt_s12] Sivers + O-Net 目標 2026 年底量產就緒，H1 2026 原型展示。（confidence: 0.85）⚠ L8
- [coherent-corp-…_s13] Coherent 估 CPO TAM 2030 年達 $15B。（confidence: 0.65，來自 Coherent，獨立 origin_entity）

### 6. 什麼會推翻這個 thesis

- 若 H1 2026 客戶原型展示無任何客戶端公開確認，2027 量產計畫時間表需下修。
- 若插拔式光模組功耗效率在 1.6T 世代持續改進，超大規模雲廠商放棄 CPO 路線。(source: sivers_ar_2025_photonics_excerpt_s5 disproof)
- 若 InP 雷射市場出現新的規模化供應商（中國廠商、Lumentum 自製等），SIVE 潛在 sole_source 地位被稀釋。(source: sivers_ar_2025_photonics_excerpt_s8 disproof)

**核查頻率：** 每季法說會 + 每月 Sivers IR；觸發後 48h 內：重新評估 EV/Revenue，判斷降為 watch 或 retired。

### 7. 接下來盯什麼

- **H1 2026 原型展示結果**（最高優先，2026-07 確認時間點）：找 Sivers PR 或客戶法說會提及 SIVE。
- **O-Net（6963.HK）和 POET Technologies（POET.V）法說會**（每季）：最短 L8 補強路徑。
- **Coherent / Lumentum ELS 策略**（每季法說會）：若 Coherent 宣布排除 SIVE → 最大 disproof 催化劑。
- **SIVE.ST 股數趨勢**（每季）：Pre-revenue 公司增資稀釋風險高，目前 2.95 億股。

---

**升格 Watchlist 所需缺口：**
1. L8：需 ≥2 份獨立文件（O-Net 或 POET 法說會 + 第三方報告）
2. 財務核驗：客戶集中度、Backlog 待人工補填
3. Variant Perception 數字：H1 2026 展示結果出爐後更新
