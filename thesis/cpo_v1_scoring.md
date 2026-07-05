# CPO 垂直切片 v1 — Thesis 評分記錄

日期：2026-07-05
版本：cpo_v1_lane_memo.md（8 份文件：Coherent Q2/Q3/OFC、Lumentum Q2/Q3、Broadcom Q2、NVIDIA Q1FY27、學術論文）

---

## 評分

| 維度 | 分數 | 評語 |
|---|---|---|
| 可信度 | 4/5 | 主要論點都有 Tier 1 法說會來源；最強證據欄以 Tier 2（OFC 發言稿，confidence 0.75）為主力，略低於 Tier 1 逐字稿，但尚可接受。Coherent 多年期 NVIDIA 協議是最強單一引用。 |
| 瓶頸清晰度 | 5/5 | InP substrate(sub=1) → CW DFB laser → ELS → CPO 兩層瓶頸結構清晰，有 substitutability 數字支撐；Sole_source 真偽分別明確標注；資料缺口（InP substrate 端供應商未確認）有主動揭露。 |
| 可證偽性 | 4/5 | 三條 disproof condition 具體可觀測（NVIDIA 協議取消、InP 產能延誤、CPO 時程滑移）；缺「核查頻率」與「觸發後 48 小時動作」（per L7），扣 1 分。 |
| 洞見密度 | 4/5 | 非顯性洞見：「InP 雷射產能（非光子晶片設計）是 H2 2026 真實卡點」，與市場共識（關注 Broadcom/NVIDIA）形成實質對比。Lumentum UHP laser designed_in + qualifying 並存的跨世代細節是多文件才能看出的 gap。Leading indicators 可立即啟動監控。 |
| 完整性 | 5/5 | 7 段全部有實質內容；需求（hyperscaler CapEx → Broadcom XPU → CPO）、供應（Coherent/Lumentum InP 垂直整合）、技術（device_chip → materials_substrate 層）三維全覆蓋。 |
| 市場差異度 | 4/5 | X/Y/Z 三段式架構清晰：X=市場共識聚焦 Broadcom/NVIDIA；Y=InP 雷射產能是真實卡點；Z=Coherent H2 2026 CPO 收入認列。X 為定性描述而非從 P/E 或 EV/Sales 數字推斷（需 Engine C），故 4 分而非 5 分。 |
| **總分** | **26/30** | |

---

## 最弱環節

**可證偽性（4/5）：** Disproof condition 寫了「什麼會推翻」，但缺少「多久核查一次」和「觸發後立即做什麼」。下一版應在 disproof 條件後補上：核查頻率（例：每季法說會）+ 觸發後動作（例：48 小時內重新評估 InP 產能假設，降評 thesis 到 `watch` 狀態）。

**市場差異度（4/5）：** Variant perception 的估值層面（股價隱含 P/E、分析師共識 EV/Sales 是多少）需要 Engine C 補充。目前是「市場低估了 InP 瓶頸」的定性主張，缺乏「股價目前 implied 的 CPO 收入貢獻假設是 X，本 thesis 認為實際是 Y」的量化鎖定。

---

## 整體評估

**PASS — 可進入 Watchlist 升格流程**

- 總分 26/30 ≥ 22 ✅
- 可信度 4 ≥ 3 ✅
- 可證偽性 4 ≥ 3 ✅
- 市場差異度 4 ≥ 2 ✅

---

## 升格前必做（財務核驗 5 項）

升格 Watchlist 前需 Engine C 完成：
- [ ] 客戶集中度（COHR：NVIDIA 佔比；LITE：top 3 客戶佔比）
- [ ] 毛利率趨勢（COHR / LITE 最近 4 季 gross margin，是否隨 CPO mix 提升）
- [ ] Backlog 能見度（COHR 多年期 NVIDIA 協議金額；LITE OCS backlog $400M+ 確認）
- [ ] 稀釋壓力（COHR / LITE 近期 SBC、可轉債、增資動作）
- [ ] 估值壓力（COHR / LITE 當前 EV/Sales vs. 歷史均值；implied CPO 收入貢獻）

→ 以上 5 項全部完成後，Variant perception 的「X/Y」估值量化才能填寫，Lane Memo 方可升格。

---

## 後續行動

1. **立即：** Engine C（基本面引擎）規劃啟動，重點先完成 COHR + LITE 財務核驗 5 項
2. **每季：** 對照 leading indicators 核查 disproof conditions（Coherent、Lumentum 法說會季度觀測）
3. **下版 Lane Memo（v2）：** 補 disproof condition 的核查頻率 + 觸發後動作；補 variant perception 估值量化
