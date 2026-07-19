# 成熟製程設備切片 v1 — Thesis 評分記錄

日期：2026-07-19
版本：amat_lrcx_mature_node_v1_lane_memo.md
文件基礎（7 份，皆 Tier 1 一手 filing）：
- AMAT FY2025 10-K、Q2 FY2026 10-Q、Q1 FY2026 10-Q（origin: Applied Materials）
- LRCX FY2025 10-K、Q3 FY2026 10-Q、Q2 FY2026 10-Q（origin: Lam Research）
- GlobalFoundries FY2025 20-F（origin: GlobalFoundries）← 客戶端 L8 獨立印證

主題：**非 AI／非 CPO** — 成熟製程（trailing-edge / ICAPS / 200mm）晶圓廠設備 capex 週期。
AMAT／LRCX 的 AI／HBM／先進邏輯收入在 memo 中被 segment 分拆，不作為論點。

---

## 評分

| 維度 | 分數 | 評語 |
|---|---|---|
| 可信度 | 4/5 | 主論點（ICAPS/非前沿結構、200mm 併入、中國 37%→30%、export-controls substitutability=1、GF 設備依賴）皆 Tier 1 filing 直接支撐，且含**客戶端非供應商自報**來源（GF 20-F）。扣 1 分：核心瓶頸的「中國國產設備商吃 trailing-edge 份額」為產業推論，尚未由圖中一手／第三方文件確認。 |
| 瓶頸清晰度 | 3/5 | 成熟製程 thesis 的瓶頸在**需求/份額**（中國國產替代 + 出口管制 TAM 壓縮）而非乾淨的供給卡點；export-controls 邊 `substitutability=1` 有支撐，但「國產替代」leg 缺圖中證據，且無 `sole_source` 邊指向具體零件。資料缺口已主動揭露，故給 3 非更低。 |
| 可證偽性 | 4/5 | 3 條 disproof 具體可觀測（中國佔比 ≥35% 且非前沿 WFE 連 2 季 guide up／國產替代停滯／市場重估全書）；前兩條均附 L7 要求的**核查頻率 + 觸發後 48h 動作**。第三條為推論。 |
| 洞見密度 | 4/5 | 非顯性洞見：市場用單一 leading-edge 倍數承保「AI 成長軌 + 成熟製程衰退軌」兩條混在同一 segment 的營收；把兩軌分拆、單獨承保成熟／中國基座，是多文件交叉才看得出的 gap。Leading indicators 可立即啟動監控。 |
| 完整性 | 4/5 | 8 段全部有實質內容，需求／stack／瓶頸／證據／disproof／指標／variant 全覆蓋；部分 leg 靠推論，且成熟製程收入的精確佔比未量化（財報未單獨拆出非前沿金額）。 |
| 市場差異度 | 4/5 | X/Y/Z 三段清晰，**X 由估值倍數反推**（Forward P/E 31.6x、EV/Revenue 14.46x，非用分析師 $623 目標價），符合 variant perception 正確操作定義。扣 1 分：股價隱含的「成熟製程收入貢獻」未鎖定到精確數字（需 Engine C 拆分佔比才能量化 X 的 implied 假設）。 |
| **總分** | **23/30** | |

---

## 最弱環節

**瓶頸清晰度（3/5）：** 「中國本土設備商於 trailing-edge 節點吃 AMAT/LRCX 份額」是本 thesis 的核心 alpha，但目前只有 AMAT 自我揭露的風險因子 + 產業推論，圖中沒有一手／第三方確認。下一步：補中國設備商（AMEC／Naura／SiCarrier）qualification 的一手或第三方文件，或客戶端（SMIC／UMC／GF）揭露的供應商切換證據，把此瓶頸從「推論」升級為「圖中確認」。

**市場差異度（4/5）：** X 已從倍數反推（優於 CPO v1 的定性描述），但仍缺「股價目前 implied 的成熟製程收入貢獻假設 = 具體 %，本 thesis 認為實際 = 具體 %」的量化鎖定。需 Engine C 把非前沿營收佔比拆出後才能完成。

---

## 整體評估

**PASS — second-slice gate 通過（解鎖 L9 前置條件 #1）**

- 總分 23/30 ≥ 20 ✅
- 可信度 4 ≥ 3 ✅
- 可證偽性 4 ≥ 3 ✅
- 市場差異度 4 ≥ 2 ✅

主題確為**非 AI／非 CPO**（成熟製程 capex 週期），跑通相同 extract → validate → load → thesis → scoring 流程；AI/HBM/先進邏輯收入已在 memo 中 segment 分拆。

---

## 升格 Watchlist 前必做（財務核驗 5 項；本 memo 維持 Research Note）

升格前需 Engine C 完成（AMAT／LRCX）：
- [ ] 客戶集中度（前兩大客戶佔比；10-K 揭露有 CustomerOne/CustomerTwo concentration）
- [ ] 毛利率趨勢（近 4 季 gross margin，AMAT 最新 49%）
- [ ] Backlog 能見度（AMAT 10-K 揭露 backlog $15.0B，其中 ~31% 12 個月外）
- [ ] 稀釋壓力（SBC、庫藏股、可轉債）
- [ ] 估值壓力（EV/Sales 14.46x vs 歷史；**非前沿營收佔比拆分以量化 variant perception 的 implied X**）

---

## 後續行動

1. **立即：** 補「中國國產設備替代」的一手／第三方證據，升級主瓶頸證據等級（見最弱環節）。
2. **每季：** 對照 leading indicators 核查 disproof（中國營收佔比、非前沿 WFE 語調、國產替代里程碑）。
3. **下版（v2）：** Engine C 拆出非前沿營收佔比，量化 variant perception 的 implied X；補 LRCX 對稱的獨立客戶端來源。
