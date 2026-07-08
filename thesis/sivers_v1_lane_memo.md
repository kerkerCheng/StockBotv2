<!-- output_type: [Watchlist Candidate] | ticker: SIVE.ST | checklist_pass: True | l9_pass: True -->

<!-- gate_override: onboarding 驗證，單一來源（Sivers 自身年報） -->

# Directional Lane Memo — Sivers Semiconductors (SIVE.ST)
**CPO 外置雷射源（ELS）供應鏈瓶頸研究方向**
*Draft · 僅供內部方向討論，非可操作投資建議*

---

## 1. 一句 Thesis

**Sivers Semiconductors 因 CPO 規模化拉動的 CW DFB 雷射短缺而具備瓶頸供應商潛力，但 2026–2027 年客戶認證轉化率是決定性驗證點。**

> **Variant Perception（錨點）**
> - **市場現在信 X**：SIVE.ST 目前 EV/Revenue = 44.9×、毛利率 = −2.4%、分析師目標價均值 $9.95（N=4，相對當前股價 $40.20 隱含 −75% 下行空間）。市場定價反映的隱含假設是：Sivers 的 sampling 管線不會在近期有意義地轉化為量產訂單，且公司持續虧損、無法達到正毛利，估值溢價難以支撐。
> - **本 Thesis 認為 Y**：若 CW 雷射供給在 800G→1.6T→3.2T 過渡期間確實出現結構性短缺，且 Sivers 與 O-Net 的 ELS 組件成功通過 H1 2026 客戶 prototype 評估、進入 2027 量產計劃，則公司的 revenue 可見度將發生非線性跳躍，市場將被迫重新對「sampling 轉 backlog 轉量產」的時間軸定價。
> - **催化劑 Z**：① H1 2026 客戶 prototype 驗證結果公告（go/no-go 事件）；② 可插拔光模組廠商中有任一家簽署 2027+ 量產意向；③ 公司毛利率轉正或出現明顯改善的季度數據。
> - ⚠ **警告**：上述 variant perception 框架基於 Sivers 自身年報（單一來源，override-gate 已標注）；估值壓力分析需 Engine C（基本面引擎）補充第三方 revenue 預測與 backlog 數據後才能完整填寫。

---

## 2. 需求驅動

- **AI 算力擴張推升高速光互連需求**：光互連行業正從 800G 向 1.6T、3.2T 頻寬演進，這一過渡直接拉動對 CW DFB 雷射的需求量，Sivers 自身預判此過程中 CW 雷射供給將出現短缺。
  `(source: sivers_ar_2025_photonics_excerpt_s8)`

- **CPO 架構天然依賴外置雷射源（ELS）**：下一代 CPO 以外置雷射源作為關鍵元件，相較傳統可插拔光模組可顯著降低功耗，驅動超大規模資料中心（hyperscaler）採購偏好向 CPO 遷移。
  `(source: sivers_ar_2025_photonics_excerpt_s5, sivers_ar_2025_photonics_excerpt_s20)`

- **DWDM 雷射陣列成為矽光子 CPO 的關鍵投入**：Sivers 的 DWDM DFB 雷射陣列被推斷為 CPO 結合矽光子 chiplet 用於 AI 資料中心 scale-up 組網的策略性關鍵投入。
  `(source: sivers_ar_2025_photonics_excerpt_s10)`

- **CPO 市場規模提供宏觀需求錨點**：Coherent 估計 CPO 可服務市場（SAM）至 2030 年將達 **150 億美元**，為 ELS 供應鏈提供長週期需求背景。
  `(source: coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s13)`

---

## 3. Stack 摘要

從供應鏈抽象層次來看，**元件層（雷射晶片 / InP 磊晶）** 正在經歷最顯著的結構性緊張：InP 基板與 CW DFB 雷射的合格供應商數量有限，認證週期長，短期內產能擴張難度高，導致此層出現潛在集中風險。**模組整合層**（可插拔光模組廠、CPO 模組廠如 O-Net Technologies）目前過渡相對有序，已有廠商與 Sivers 進行聯合開發，以達成 2026 年底的量產就緒目標 `(source: sivers_ar_2025_photonics_excerpt_s5, sivers_ar_2025_photonics_excerpt_s12)`。**系統層**（交換器 ASIC / AI 加速器廠商）對 CPO 的需求牽引方向明確，但尚未在本圖譜的 context 中確認具體採購承諾，構成供應鏈上下游資訊不對稱的主要缺口。

---

## 4. 主瓶頸

**瓶頸候選：CW DFB 雷射 / 外置雷射源（ELS）供給端**

| 項目 | 狀態 |
|---|---|
| 技術節點 | InP 基 CW DFB 雷射、DWDM DFB 雷射陣列 |
| Sole Source 確認 | **⚠ 目前 context 中未出現 sole_source=✓ 標注**，圖中無法確認 Sivers 為唯一供應商 |
| Substitutability | 圖中未提供明確的 1–5 分值；但主張指出認證週期長、短期難以擴充合格供應商數量，隱含替代難度較高 `(source: sivers_ar_2025_photonics_excerpt_s8)` |
| Ramp 難度 | 供給短缺預判已為 guided 主張（confidence: 0.75），但目前仍處 sampling 階段，量產承諾預計落在 2027 年之後 `(source: sivers_ar_2025_photonics_excerpt_s9, sivers_ar_2025_photonics_excerpt_s16)` |
| Qualification 進度 | Sivers 與 O-Net 目標 2026 年底達到量產就緒，H1 2026 進行客戶 prototype 展示 `(source: sivers_ar_2025_photonics_excerpt_s5, sivers_ar_2025_photonics_excerpt_s12)` |

> **資料缺口說明**：圖中未確認 sole_source，亦未提供競爭供應商的資格化狀態（如其他 InP 雷射廠的 CPO 認證進度）。在未取得多來源驗證之前，「Sivers 為唯一瓶頸供應商」的結論**不應作為主要論點**。需進一步調查 Lumentum、II-VI 等潛在競爭方在同一認證路徑的進展，才能確認瓶頸的排他性。

---

## 5. 最強證據

- `sivers_ar_2025_photonics_excerpt_s5 / s20`：「External laser sources are a critical component for next-generation CPO, enabling significantly lower power consumption compared with traditional pluggable transceivers.」（confidence: 0.90）

- `sivers_ar_2025_photonics_excerpt_s5 / s12`：「Sivers and O-Net Technologies are targeting production readiness of high-performance ELS for CPO by year-end 2026, with customer prototype demonstrations in H1 2026.」（confidence: 0.85）

- `sivers_ar_2025_photonics_excerpt_s9 / s16`：「Sivers is sampling CW DFB lasers to multiple pluggable transceiver manufacturers worldwide, with a subset expected to commit to production plans in 2027 and beyond.」（confidence: 0.85）

- `sivers_ar_2025_photonics_excerpt_s8`：「CW laser supply will be in shortage within the next few years as the optical interconnect industry transitions from 800G to 1.6T and 3.2T bandwidths.」（confidence: 0.75）

> ⚠ **來源局限**：上述所有 Tier 1 引用均來自 **Sivers 自身年報**（單一來源），系統已標注 override-gate。在引用強度上應視為 **Tier 2**（公司指引），而非獨立第三方確認。

---

## 6. 什麼會推翻這個 Thesis（Disproof Conditions）

- **若 H1 2026 客戶 prototype 評估失敗，或量產就緒里程碑滑入 2027 年之後**，則 Sivers–O-Net ELS 路線的量產可見度歸零，thesis 需降評。
  `(source: sivers_ar_2025_photonics_excerpt_s5, sivers_ar_2025_photonics_excerpt_s12)`

- **若多家合格 CW 雷射供應商以規模化產能進入市場**（如現有競爭者通過 CPO 客戶認證），或頻寬過渡時間軸顯著延遲，則「供給短缺」的瓶頸主張降級，Sivers 的議價能力消失。
  `(source: sivers_ar_2025_photonics_excerpt_s8)`

- **若可插拔光模組的功耗效率提升至可與 CPO 競爭，或 CPO 架構轉向片上整合雷射**（on-chip integrated laser），則外置雷射源的需求邏輯根本性動搖，整個 thesis 需退場。
  `(source: sivers_ar_2025_photonics_excerpt_s5, sivers_ar_2025_photonics_excerpt_s20)`
  *(第三條亦屬圖中明確 disproof_condition，非推導。)*

---

## 7. 接下來盯什麼（Leading Indicators / Catalysts）

- **【每季法說會 / 重大公告】H1 2026 客戶 prototype 評估結果**：Sivers 是否公告任何客戶通過 prototype 驗收，或出現明確的 design-win 聲明。這是 2026 年最高優先級的 go/no-go 事件，直接決定 2027 量產訂單的可信度。
  `(source: sivers_ar_2025_photonics_excerpt_s5, sivers_ar_2025_photonics_excerpt_s12)`

- **【每季法說會】Sampling 管線轉生產承諾的比例**：追蹤「正在 sampling 的可插拔光模組廠商中，承諾 2027+ 量產計劃」的廠商數量從目前的「subset（部分）」擴大或縮小的動態。任何具體客戶名稱或 LOI 的揭露均為正向催化。
  `(source: sivers_ar_2025_photonics_excerpt_s9, sivers_ar_2025_photonics_excerpt_s16)`

- **【每季財報】毛利率走向**：目前毛利率為 −2.4%。監測毛利率是否出現轉正趨勢（即量產規模效益開始體現），是估值重新定價的必要但非充分條件。若毛利率持續惡化，EV/Rev = 44.9× 的溢價將更難維持。
  *(觀測頻率：每季財報；數據錨點來自市場定價數據區塊)*

- **【不定期，業界展會/客戶公告】競爭者 InP 雷射認證進度**：監測其他 InP 雷射廠商（圖中 context 提及 Lumentum 作為相關主體 `(source: sivers_ar_2025_photonics_excerpt_s9)`）是否在 CPO ELS 路徑取得客戶認證突破，若有則需重新評估 Sivers 的瓶頸排他性假設。

---

*本備忘錄基於結構化知識圖譜節點，主要來源為 Sivers Semiconductors 2025 年報（單一來源，已標注 override-gate）。所有論點在升格 Watchlist 前需經多來源交叉驗證（客戶法說會、第三方研究、競爭者 filing）及 Engine C 基本面引擎的財務核驗。*