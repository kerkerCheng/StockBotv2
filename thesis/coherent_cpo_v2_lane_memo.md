<!-- output_type: [Research Note] | ticker: COHR | checklist_pass: False | l9_pass: False | evidence_manifest_pass: True | evidence_gate_pass: False -->

# Directional Lane Memo — Coherent（CPO 外部雷射 / InP 垂直整合）
**生成日期：** 2026-07-17
**核查頻率與觸發動作：** 每週掃描（weekly 審查）自動監控 disproof 訊號；完整核查每季一次（下次依 `thesis/lifecycle.json`，2026-10-15）。關鍵檢核點：每季 Coherent 法說會（scale-out CPO 營收認列進度）、2026-12 六吋 InP 產能倍增達成與否、NVIDIA 端第二供應商訊號。任一 disproof 條件觸發 → 48 小時內人工 review，決定降評／維持／退場。

## 1. 一句 thesis

NVIDIA 股權＋協議鎖定 Coherent CPO 雷射，InP 垂直整合成 CY2026-27 放量期瓶頸。

> **Variant Perception：** 當前股價 $277.60（Forward P/E 33.7x、EV/Revenue 8.43x、分析師目標均價 $388.95，N=22）隱含的假設 X 是：Coherent 是 datacom 光模組週期的受益者之一，成長由既有 transceiver 業務延續驅動。本 thesis 認為真實情況 Y 是：CPO（$15B+ 增量 TAM）與 OCS（$4B+）是結構性新市場 [E11]，且 Coherent 是圖中唯一有「客戶端文件」證實深度綁定的 CPO 雷射供應商——NVIDIA $2B 股權投資＋multibillion 採購承諾＋capacity rights [E2]——價值將集中於 InP 雷射與垂直整合模組端，而非模組組裝端。催化劑 Z：H2 CY2026 scale-out CPO 首批營收認列與 H2 CY2027 scale-up ramp [E10]，以及六吋 InP 產能於 12 月前倍增的執行進度 [E5]。（註：substitutability=5 的評值仍以供應商自報為主，客戶端行為證據〔股權＋產能鎖定〕屬間接佐證。）

## 2. 需求驅動

- NVIDIA 直接以 $2B 股權投資＋多年供應協議（至 2030）鎖定 Coherent 的 CPO 產品線；客戶端 PR 明載 multibillion 採購承諾與 future capacity rights——需求以合約與資本形式落地，而非僅口頭 forecast [E1][E2]。
- Coherent 管理層估計 CPO 為 $15B+ 增量可服務市場、OCS 上修至 $4B+ [E11]；scale-up（機架內光學化）機會被描述為比 scale-out 大一個數量級，因為現有 rack 內部連線全為電訊號 [E12]。
- 同業 Lumentum 的 OCS backlog 突破 $400M 且分散於三家客戶，印證光學交換／互連需求是產業級現象，而非單一公司敘事 [E13]。
- 風險側：NVIDIA 已把中國資料中心算力營收自 guidance 排除（H200 出口許可不確定），需求總量對出口政策敏感 [E16]。

## 3. Stack 摘要

結構性變化集中在三層：(a) **元件層**——InP 雷射（CW DFB、EML）由三吋轉六吋晶圓，Coherent 於 Sherman 與 Yarfala 兩地平行放量、年底倍增，單晶片成本減半以上 [E5][E6]；(b) **模組層**——ELS、fiber attach unit 等 CPO 週邊由分散外購走向垂直整合單一供應 [E8]；(c) **系統層**——scale-out CPO 先行、scale-up 與 OCS 隨後，過渡窗口集中在 CY2026-27 [E10][E14]。元件層（InP 產能）是目前最緊的一層；模組組裝層過渡相對順暢。

## 4. 主瓶頸

- **公司／技術：** Coherent 的高功率 CW DFB 雷射與其六吋 InP 產線。
- **為什麼：** CW 雷射已進入大額 PO＋NVIDIA 協議產品範圍（designed_in），substitutability=4（衝突決議後：4/5/4 取最新且多數）[E9]；Coherent 自身對六吋 InP 產線的依賴 substitutability=5——物理產能瓶頸，Sherman 為「世界最先進 InP 生產基地」[E6][E7]。
- **Qualification／ramp 現況：** CW laser designed_in；六吋線 qualified 且已出貨首批含六吋元件的 transceiver [E7][E9]；CPO 方案整體 designed_in（Q2 FY26 大額 PO）[E4]。
- **上游依賴：** InP 基板供應商 AXT——Reuters 第三方報導：AXT 為全球第二大 InP 基板廠、Coherent 主要基板供應商；換供應商需長 qualification 週期，且 AXT 自陳出口許可為當前最大挑戰 [E15]。
- **sole_source 面待驗證：** Coherent→NVIDIA 邊的 sole_source=true 目前僅供應商自報（單一 assertion），尚無客戶端逐字確認「唯一供應商」，維持待驗證，不作為本 memo 的已確認論點 [E3]。

## 5. 最強證據

- [E2] NVIDIA $2B 股權投資＋multibillion 採購承諾＋capacity rights（客戶端 PR，origin=NVIDIA——本圖 CPO 依賴鏈唯一客戶端直接確認）。
- [E1] 多年供應協議延伸至 2030、涵蓋高功率 CW laser 等多項 CPO 產品（Coherent Q3 FY26 法說會）。
- [E4]「exceptionally large purchase order」的 CPO 方案設計定案，客戶決策關鍵為六吋 InP 產線（Coherent Q2 FY26 法說會）。
- [E15] Reuters 第三方報導：AXT-Coherent 基板依賴與出口管制風險（origin=Reuters，非自報來源）。

## 6. 什麼會推翻這個 thesis

- 若六吋 InP 產線出現 yield 問題或年底倍增進度大幅落後（12 月檢核點），成本／產能優勢敘事失效，thesis 需降評 [E5]。
- 若另一 InP 設施在產量／製程上超越 Sherman，或 Coherent 在關鍵客戶處失去 qualification，主瓶頸地位不成立，thesis 需降評 [E6]。
- 若 NVIDIA 協議內產品出現第二供應商 qualify 至同一 design，高 substitutability 假設被推翻，thesis 需降評。(推導，非圖中明確主張)
- 若中國 InP 出口管制升級導致 AXT 基板供應中斷、且 Coherent 無法及時 qualify 替代來源，放量計畫受阻，thesis 需降評或退場 [E15][E17]。
- 若 NVIDIA 需求端因出口政策進一步收縮（中國排除已成事實），CPO ramp 斜率低於預期，thesis 需降評 [E16]。

## 7. 接下來盯什麼

- **每季（Coherent 法說會）：** scale-out CPO 營收是否如期於 H2 CY2026 開始認列、scale-up 於 H2 CY2027 啟動 [E10]。
- **12 月檢核點：** 六吋 InP 產能倍增是否達成（Q2 FY26 承諾的年底目標）[E5]。
- **每次客戶公告：** NVIDIA 或其他 hyperscaler 的 CPO 部署進度與任何第二供應商訊號 [E2][E3]。
- **每季（OCS 放量）：** 產能瓶頸移除後的營收斜率（Q3 FY26 稱已突破產能瓶頸、市場上修至 $4B+）[E11][E14]。
- **上游（每季＋事件驅動）：** AXT 出口許可進展；AXT 未來 filing 若揭露 >10% 客戶或具名客戶，即補強供應鏈邊的第三方確認 [E15][E17]。

## Evidence Gate Notes
- ⚠ [E7] 瓶頸主張只由供應方／被分析公司單一自報來源支持 (`single_origin_self_report`)
- ⚠ [E9] 瓶頸主張只由供應方／被分析公司單一自報來源支持 (`single_origin_self_report`)

本報告因上述 evidence gate 未通過，維持 Research Note。
