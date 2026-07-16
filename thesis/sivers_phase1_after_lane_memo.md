<!-- output_type: [Research Note] | ticker: SIVE.ST | checklist_pass: False | l9_pass: False | evidence_manifest_pass: True | evidence_gate_pass: False -->

# SIVE CPO／ELS Directional Lane Memo

## 1. 一句 thesis

Sivers 已從『自稱有 CPO 機會』前進到由 Enablence 公告的三方 ELS 實體整合，但客戶 qualification 與量產營收轉換仍未獲確認，因此現階段是可追蹤的供應鏈選擇權，不是已證實的 sole-source 瓶頸。[E1][E2]

## 2. 需求驅動

- Enablence 已公開宣布與 Sivers、O-Net 開發面向 AI datacenter／HPC 的 8-channel ELS，並明列 Sivers laser arrays 是 OEM 整合內容；這是目前最強的非 Sivers 自報產品整合證據。[E1][E2]
- Sivers 自身年報稱 800G 往 1.6T／3.2T 過渡可能造成 CW laser 短缺；方向合理，但 origin 仍是 Sivers，不能單獨當作需求已落地的確認。[E5]
- 競爭供給不會立刻消失：Lumentum 表示新 Greensboro InP fab 約六季後才開始貢獻，顯示新增 InP capacity 有長週期，但這只支持產能時程，不證明 Sivers 因而取得訂單。[E6]

## 3. Stack 摘要

目前已能從 InP laser array 元件層，追到 O-Net OEM 整合與 8-channel ELS 模組層；Enablence 的公告使這段 stack 不再只靠 Sivers 自述。[E1][E2] 另一條 GlobalFoundries SCALE 路徑仍只是 Sivers 公告的 reference-design／platform availability，尚非 customer design win，必須分開看待。[E7]

## 4. 主瓶頸

圖中目前沒有足夠證據確認 Sivers 是 sole source。真正待驗證的 chokepoint 是『能否把 DFB array 經 foundry 與 module partner 穩定放大量產』。WIN Semiconductor → Sivers 的 qualification_status 同時存在 qualified 與 qualifying 候選；可用的逐字證據只支持 Sivers 自稱合作有助於 high-volume production，故本 memo 把該屬性列為未決，而不是挑一個值覆蓋。[E4]

## 5. 最強證據

- Enablence 官方公告三方共同開發 8-channel ELS，且明列 O-Net、Sivers、Enablence 的元件與整合分工。[E1]
- Enablence-origin EdgeAssertion 將 Sivers laser arrays 連到具體 8-channel ELS module，qualification_status 為 designed_in。[E2]
- Lumentum 對新增 InP fab 的六季時程提供獨立的產能長週期參照，但不直接證明 Sivers 的需求。[E6]
- 反向證據不可忽略：POET 的 OFC 展示未確認包含 Sivers，且二手來源記錄 POET 聲稱其 Blazar 成本較 DFB 低一個數量級。[E3]

## 6. 什麼會推翻 thesis

- 若 POET／Ayar／其他 ELS 平台確認採用非 Sivers laser，或替代架構在成本與 qualification 上勝出，Sivers 的 CPO 內容量假設需降評。[E3]
- 若 WIN 的 qualification 長期停留在未決或量產 ramp 未發生，『可擴產瓶頸受益者』的核心鏈條失效。[E4]
- 若 GF reference design 在 12–18 個月內沒有轉成 customer design win，GF 路徑只能保留為合作訊號，不能算收入證據。[E7]
- FY2025 group gross margin 已為負；若 production ramp 後 raw-material／external manufacturing 成本沒有改善，規模增加也未必創造股東價值。[E8]

## 7. 接下來盯什麼

- 每次 Sivers 季報：找具名 customer qualification、production order、出貨與 Photonics gross-margin 變化；只有 partnership 重述不升級證據。[E4][E8]
- 每次 O-Net／Enablence／終端客戶公告：確認 8-channel ELS 是否通過 customer evaluation 並開始量產。[E1][E2]
- 下一次 POET 更新：確認 OFC 展示品是否含 Sivers arrays，以及 Blazar 是否替代 DFB BOM。[E3]
- 未來六季的同業 capex／qualification：追蹤 Lumentum 新 InP capacity 是否提早或如期進場，重新評估供給稀缺窗口。[E6]

## 8. Variant Perception

Engine C 現有 checklist 記錄 EV/Revenue 約 44.9x、forward P/E 為負，顯示定價已隱含高度的未來營收與獲利轉換；但即時市場 snapshot 因本機缺 yfinance 而不可用，這個推論只能視為暫定。市場隱含 X 是合作與 design-in 將順利轉成高價值量產，本 thesis 的 Y 是外部來源已確認產品整合、但 customer qualification、WIN ramp 與 margin conversion 仍是三個獨立 gate；催化劑 Z 必須是具名客戶量產／出貨與 Photonics margin 改善，而不是新增一份供應商新聞稿。[E1][E2][E4][E8]

## Evidence Gate Notes
- ⛔ [E4] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⚠ [E4] edge:15d7af33e42502ce404ed699c4f17c1e284456f025964460a1d7f71a960681e8 的 qualification_status 有未決證據衝突 (`open_conflict`)
- ⛔ [E5] SourceDoc sivers_ar_2025_photonics_excerpt 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)
- ⛔ [E8] SourceDoc sivers_ar_2025_financials 正在可信度審查：2026-07-12: Ningi Research revenue-recognition allegations, going-concern concern, and pending financial restatement; review_by=2026-08-27; evidence=GitHub Issue #2 and thesis/sivers_v2_lane_memo.md (`source_under_audit`)

本報告因上述 evidence gate 未通過，維持 Research Note。
