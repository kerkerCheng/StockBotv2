<!-- output_type: [Watchlist Candidate] | ticker: SIVE.ST | checklist_pass: True | l9_pass: True | evidence_manifest_pass: True | evidence_gate_pass: True -->

# Directional Lane Memo — Sivers Semiconductors (SIVE.ST) v4

> **Thesis 狀態：`revised`（本 memo 為 2026-08-28 revise 決議的執行；lifecycle 轉回 `active` 待 mutation 核准）**
> **v4 改版原因（2026-08-27 Q2 分辨點已裁決）：** Ningi Research 指控的核心——營收不當認列 ~97M SEK／31%——被 Q2 報告隨附的重編結果證偽：2025 年營收重編僅減少 **SEK 4.314M（約 1.4%）**，且正式報告未出現 going-concern 惡化敘述。原 retire gate 未觸發。信用風險大幅下修後，thesis 的主要矛盾從「數字可不可信」轉移到「執行時間表與稀釋」。
> **核查頻率：** 30 天 ＋ 每季財報；關鍵核查點 **2026-11-26（Q3 報告）**、2026 年底（ELS production readiness）、2027（Jabil 1.6T qualification→ramp）。
> **觸發後 48h 動作：** 任一 disproof 條件觸發 → 48 小時內人工決策 revise 或 retire。

---

## 1. 一句 Thesis

**CPO／光互連對外部 CW 雷射的結構性需求為真，Sivers 以多通道平台路線（GF SCALE、O-Net/Enablence ELS、Jabil 1.6T、Ayar SuperNova）進入 2027 量產過渡窗口；審計信用風險已由 8/27 重編實質解除（-1.4% vs 指控 -31%），但 NRE 收縮使營收先下後上、關鍵 ramp 全數壓在 2027，pipeline 明示 non-binding——thesis 由「審計存疑的深度價值選項」轉為「執行時間表壓過信用疑慮的 pre-ramp 執行股」。**

### Variant Perception

**市場現在信什麼（X）：** Q2 期間股價由 SEK 10.71 漲至 63.15（約 6 倍；4/16 雙重上市評估公告當日 +30%），8 月回落至 36.16（8/27 收盤，Q2 報告發布前；8/28 交易時段於 Yahoo 尚未結算、當日成交逾 2,000 萬股，待官方確認）。以 356,740,332 股（7/31 官方公告 355,081,317 ＋ 8/13 認股權 1,659,015）計市值約 SEK 12.9B。TTM 營收約 SEK 282M（H2 2025 約 166.3M ＋ H1 2026 115.7M）→ P/S 約 46x。**對照 v3（2026-07-19，股價 33.48、36.5x）：股價繞了一整圈回到原點，但因股數 +11% 且營收下滑，估值倍數反而更高**——市場仍然把「2027 產品放量成功」大幅 price in，資訊差窗口比 v3 時更窄而非更寬。

**本 thesis 認為（Y）：** 執行仍在 pre-ramp。Q2 淨銷售 SEK 53.8M（yoy -12%），產品／HW 營收 +13%（匯率調整 +18%）[E6]——方向正確但整體營收被 NRE 主動收縮拖累；Jabil 1.6T 的 qualification／production ramp 已推遲至 2027；USD 1.2B pipeline（較 2025 年底 +268%）在報告中明示為 non-binding；毛利率尚未翻正 [E2]。真相分辨點（重編）已過且結果偏多，但下一個分辨點——**付費量產訂單**——尚未出現：photonics 端至今可驗證的付費訂單仍以 Wireless 的 ALL.SPACE USD 8.2M BFIC 生產訂單為最大單筆 [E9]。

**催化劑（Z）：** Q3 報告（11-26）的毛利率與 photonics 分項；ELS production readiness 年底確認 [E7]；GF SCALE 平台首個具名終端客戶；Jabil 1.6T qualification 進度。任一項落空將觸發重新定價，任一項兌現將把「平台機會」轉為「已確認需求」。

---

## 2. 需求驅動

- **CW 雷射供給缺口的結構性論述**：光互連產業向 CPO／高速 pluggable 過渡，Sivers 自評 CW 雷射未來數年將供不應求 [E4]（issuer 自報，L8 折扣）；獨立佐證是 Lumentum 側的供給約束——其新 Greensboro InP 廠約六個季度以上才貢獻營收 [E12]，短缺窗口為替代供應商創造空間。
- **DWDM 雷射陣列作為 CPO 策略輸入**：與矽光子 chiplet 結合的短距光互連定位 [E5]。
- **平台化路線拉動採樣管線**：CW DFB 雷射正向多家 pluggable 收發器製造商採樣、部分預期 2026 進入量產決策 [E6]；O-Net／Enablence 三方 8 通道 ELS 模組（OFC 2026 公開）[E8]；GF 矽光子合作與 SCALE 平台整合為不依賴單一終端客戶的通路。

## 3. Stack 摘要

**晶片製造層**：Win Semiconductor 代工合作（qualifying）；GF 合作雙軌——PARTNERSHIP（AI 矽光子方案開發）＋ SCALE 平台整合（reference design，非付費量產訂單）。
**模組整合層**：O-Net／Enablence ELS 三方聯盟 [E8]、Jabil 1.6T pluggable 模組合作（qualification→2027 ramp）、SemiNex USD 3.4M 次世代 InP 光源程式（2026-08 期後事項）、LIGHTIUM TFLN 整合。多路並行分散風險，但**無任何單一通道已確定量產**。
**客戶端**：最具公開可信度的 designed-in 節點仍是 Ayar Labs SuperNova（第三方貿易媒體佐證）；NVIDIA CPO 生態名單至今只點名 Lumentum 等，未見 Sivers [E14]。
**Wireless（現金流基本盤）**：ALL.SPACE USD 8.2M Ka-band BFIC 生產訂單（2027 交付，客戶付錢方向）[E9]、NEMC EW STAR Year-2 USD 6.6M [E10]、Tachyon USD 1.5M 開發合作 [E11]。集團營收超過一半來自三大 Wireless 客戶 [E1]，最大客戶 ALL.SPACE 佔 25.9% [E3]——photonics thesis 的下行保護與集中度風險並存。

## 4. 主瓶頸

**主要執行瓶頸不變：ELS 模組 production readiness（目標 2026 年底）與付費量產訂單的轉化 [E7]。**

- **時間表風險已實質化**：Jabil qualification／ramp 推遲至 2027（Q2 報告揭露）；「2026 年底 production readiness」現在是硬檢核點而非緩衝目標。
- **NRE→產品轉型的營收空窗**：公司主動收縮 NRE 使 Q1 -22%、Q2 -12%，轉型成效「預計 Q4 2026 開始可見、2027 加速」——這句話本身就是可證偽的時間表。
- **競爭壓力**：Lumentum CW DFB 以窄規格一致性搶 hyperscaler 收發器良率敘事 [E13]；POET 的 Marvell/Celestial 訂單雖已全數取消 [E15]，但 POET 自述仍服務其他客戶 [E16]，低成本 ELS 替代威脅未消失。
- **資金與稀釋**：H1 2026 營運現金流 -SEK 119.2M（Q1 -49.2M、Q2 -70.0M）；SEK 825M 增發＋Bootstrap $12M 轉股（合計稀釋逾 10%）換來「healthy balance sheet」與約兩年以上 runway——資金不再是近期瓶頸，但代價已付。

## 5. 最強證據

- [E9] ALL.SPACE USD 8.2M 生產訂單：客戶付錢方向、2027 交付——目前最強的「付費承諾」證據（惟屬 Wireless 非 photonics）。
- [E8] Sivers/O-Net/Enablence 三方 ELS 模組公告（origin：Enablence，非 Sivers 自報）。
- [E6] CW DFB 向多家 pluggable 製造商採樣中、部分預期 2026 量產決策（issuer 自報）。
- [E1][E2][E3] FY2025 財務結構（Wireless 集中度、毛利率 -0.7%、ALL.SPACE 25.9%）——**注意：這批 claim 的來源文件 `sivers_ar_2025` 仍掛 `source_under_audit`；8/27 重編結果（-4.3M SEK）已實質回答審查疑慮，hold 的解除為獨立人工決策，本 memo 不自行視為已解除。**
- 重編結果本身（2026-08-27，Q2 報告隨附）：2025 營收重編 -SEK 4.314M，遠小於 Ningi 指控的 ~97M/31%——此為 lifecycle mutation `tm_b498950b` 的裁決依據（時變財務事實，屬 Engine C 範疇，不入圖）。

## 6. 什麼會推翻這個 Thesis（Disproof Conditions）

1. **ELS 時間表**：2026 年底前未確認 ELS production readiness，且 2027-H1 前 photonics 無任何付費量產訂單（非 NRE）→ 放量時間表全面後移，48h 內決策降評或退場。
2. **Jabil 通道**：1.6T 合作於 2027 未進入 qualification 完成／ramp，或合作終止 → 平台通路論點降評。
3. **Ayar 節點**：Ayar Labs 公開替換雷射供應商或 Sivers 披露失去該計畫 → 最具可信度的 designed-in 證據消失。
4. **資金螺旋**：毛利率至 2027 年中仍深度為負且需再次大額增發 → 稀釋侵蝕 per-share thesis，降評。
5. **信用重開**：任何新的收入認列質疑、審計調整超過營收 1%，或 going-concern 敘述惡化 → credibility hold 重啟，回 `review_required`。

## 7. 接下來盯什麼

- **Q3 報告（2026-11-26）**：毛利率方向、photonics 分項、轉型成效是否如公司所稱「Q4 開始可見」。
- **ELS production readiness 公告**（年底前，每次公司公告）。
- **GF SCALE 具名終端客戶**（每次 GF/Sivers 公告）——把 reference design 轉為已確認需求的關鍵一步。
- **Jabil 1.6T qualification 進度**（每季）。
- **競品動態**：Lumentum CW DFB 產能／客戶、POET Blazar 具名客戶採用 [E16]。
- **現金消耗率**（每季）：以 H1 節奏推算 runway，825M 募資約可支撐至 2028；若消耗加速須提前重估。
