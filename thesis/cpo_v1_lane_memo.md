# Directional Lane Memo — CPO / 矽光子供應鏈
**版本：Draft v1 ｜ 分類：方向備忘錄（非投資建議）**

---

## 1. 一句 Thesis

**Coherent 因 InP 垂直整合與 NVIDIA sole-source 地位，在 CPO 放量的 H2 2026–2027 週期中成為供應鏈不可繞過的關鍵節點。**

> **Variant Perception（初步）：**
> 當前市場隱含的假設是「CPO 是早期利基市場，供應鏈仍有充裕競爭者」；本 thesis 認為 ELS/CW DFB 雷射的 InP 製造瓶頸遠比市場定價嚴苛，Coherent 在 NVIDIA 端的 sole-source designed-in 狀態將使其在 2026–2027 的定價能力被嚴重低估。催化劑：Coherent H2 FY26 法說會首次揭露 CPO 規模出貨數字，或 NVIDIA 次世代 AI 網路架構公告明確採用 CPO。
>
> ⚠️ *Variant perception 的估值量化面（P/E、EV/Sales 區間、客戶集中度財務影響）需 Engine C 基本面引擎補充後才能完整填寫。*

---

## 2. 需求驅動

- **AI 訓練/推論叢集擴建直接 ENABLES CPO 需求**：超大規模資料中心為因應 AI 算力密度上升，正加速部署 Co-Packaged Optics 以解決 switch I/O 頻寬瓶頸。`(source: s5, s6)`

- **CPO 成為資料中心 switch / scale-up 網路的核心元件**：AI 叢集建設同步驅動 Data-center switch 與 scale-up 網路需求，而 CPO 是其中的光學傳輸介面，需求具有結構性而非週期性特徵。`(source: s1, s5)`

- **OCS（光電路交換）與多軌連結同步受惠**：除 CPO 外，AI 訓練/推論叢集建設同時驅動 Optical Circuit Switching 及 Multi-rail connectivity solutions 需求，加總擴大了 Coherent 的可服務市場規模，其中 CPO+OCS 總可服務市場估計逾 $19B。`(source: s6, s13, s20)`

- **放量時間軸明確**：Coherent 已公開指引，scale-out CPO 收入將於 H2 Calendar 2026 開始放量，scale-up CPO 收入則於 H2 Calendar 2027 接力，需求曲線的陡峭度在未來兩年將顯著提升。`(source: s9)`

---

## 3. Stack 摘要

供應鏈結構性變化集中在兩個 abstraction level：**元件製造層（Component）** 與 **模組整合層（Module / Sub-system）**。

在元件層，InP 基板 → CW DFB 雷射 → External Laser Source (ELS) 的垂直鏈條正在從「分散多供」向「高度集中」過渡；InP 基板對 CW DFB 雷射的 substitutability 評分為 1（圖中最低），且目前無 sole_source=True 確認，顯示此層雖競爭形式上存在，實際轉換成本極高。`(source: s3)`

在模組整合層，Coherent 幾乎涵蓋所有 CPO 光學子元件（CW 雷射、隔離器、TEC、ELS 模組、Fiber Attach Unit、透鏡陣列、PM 光纖），垂直整合程度形成進入壁壘，使模組層的過渡比元件層相對順暢——但也意味著若任一子元件出問題，風險無法轉移。`(source: s16, s18, s19)`

---

## 4. 主瓶頸

### 首要瓶頸：High-power CW DFB 雷射對 InP 基板的依賴

| 指標 | 數值 / 狀態 | Source |
|---|---|---|
| substitutability（InP 基板） | **1**（圖中最低） | s3 |
| sole_source（InP 對 CW DFB）| False（目前圖中未確認） | s3 |
| Coherent Sherman 廠定性 | 全球最先進 InP 生產基地 | s1, s2 |
| Coherent 6-inch InP fab substitutability | 5（幾乎不可替代） | s1, s3 |

**為何是瓶頸：**
High-power CW DFB 雷射是 ELS 的核心元件，而 ELS 是 CPO 的關鍵子系統。CW DFB 雷射製造強依賴 InP 基板（substitutability=1），且 InP 晶圓製程的良率控制、磊晶品質要求極高，產能擴增需要長達 26–30 週交期（以 ELS 供應商資料推算）。`(source: s3, s4)`

Coherent 的 Sherman, Texas 6-inch InP fab 目前是此鏈條的核心放量場所。圖中 sole_source=False，**意味著目前資料尚未確認 InP 基板端為單一來源**，此為資料缺口，需進一步驗證其他 InP 磊晶供應商的量產能力。`(source: s1, s2)`

### 次要瓶頸：ELS 模組層的認證週期

| 供應商 | qualification_status | lead_time_weeks | substitutability |
|---|---|---|---|
| Coherent | sampling | 30 週 | 2 |
| Lumentum | qualifying | 26 週 | 2 |

ELS 在 CPO 系統中 substitutability=2，且兩家供應商均尚在 sampling/qualifying 階段，尚未達到量產 qualification，代表短期（H1 2026）內供給彈性極低。`(source: s4)`

### NVIDIA 端的 Sole-Source 地位

Coherent 在 NVIDIA 的供應關係為圖中唯一明確標注 `sole_source=True` 且 `qualification_status=designed_in` 的邊，substitutability=5。這是圖中最高確信度的壟斷供應節點。`(source: s7, s8)`

---

## 5. 最強證據

- **[s1, s2]** *「Coherent's Sherman, Texas facility is the world's most advanced indium phosphide production site and is central to ramping CW laser supply for CPO.」*（confidence: 0.90）

- **[s7, s8]** *Coherent SUPPLIES_TO NVIDIA，sole_source=True，qualification_status=designed_in，substitutability=5。* 即 Coherent 是 NVIDIA CPO 光學供應鏈中目前唯一已認證設計進入的供應商。（confidence: 0.90）

- **[s9]** *「Coherent expects initial scale-out CPO revenue to begin ramping in H2 calendar 2026, and scale-up CPO revenue in H2 calendar 2027.」*（confidence: 0.90）

- **[s16, s18, s19]** *「Coherent is vertically integrated across nearly all CPO optical ingredients (CW laser, isolators, TECs, ELS module, fiber attach unit, lens arrays, PM fiber), reducing dependency on third-party suppliers.」*（confidence: 0.90）

---

## 6. 什麼會推翻這個 Thesis（Disproof Conditions）

- **若 Coherent 錯過 H2 2026 scale-out CPO 放量時程**，或主要超大規模雲端業者延後 CPO 部署計畫，則放量斜率假設需重設，thesis 主時間軸需降評。`(source: s9)`

- **若 CPO 採用率停滯、可插拔光模組（pluggable）持續保持主導地位**，或 ELS 出現可快速認證的第二供應來源且認證週期顯著縮短，則 ELS 瓶頸主張降級，Coherent 的定價能力假設需修正。`(source: s2, s4)`（此條同時對應圖中 [inferred] claim 的 disproof condition）

- **若 Coherent Sherman 廠喪失關鍵客戶資格認證**，或另一 InP 製造場所達到同等或更高產量與製程節點，則 InP 垂直整合壁壘的核心主張應降級，重新評估競爭格局。`(source: s1, s2)`

---

## 7. 接下來盯什麼（Leading Indicators / Catalysts）

- **🔵 Coherent 季度法說會 CPO 收入揭露**（每季觀測）：H2 Calendar 2026 首次出現 CPO 規模收入貢獻是最關鍵的確認點。若收入低於預期或指引被下修，直接否定 thesis 時間軸。`(source: s9)`

- **🔵 NVIDIA AI 網路架構公告與 CPO 供應商指定**（每次客戶公告）：NVIDIA 在次世代 AI 訓練/推論叢集中正式公開採用 CPO、並維持 Coherent 為 sole-source 供應商，是最強的 thesis 確認信號。`(source: s7, s8)`

- **🟡 Lumentum ELS 認證進度**（每季法說會）：若 Lumentum 從 `qualifying` 升級至 `qualified`，代表 ELS 層出現第二供應，瓶頸壓力緩解，Coherent 溢價空間受壓。`(source: s4)`

- **🟡 InP 6-inch 產能競爭者動態**（每月產業新聞 / 競爭者法說會）：觀察是否有其他 InP 晶圓廠宣布 6-inch 量產計畫或取得超大規模客戶認證，作為 Sherman 廠壟斷地位受挑戰的預警指標。`(source: s1, s2, s3)`

---

*本備忘錄為方向性研究文件，不構成任何買賣建議、目標價設定或持倉建議。財務核驗（客戶集中度、毛利率、backlog、稀釋壓力、估值區間）為 Watchlist 升格的必要條件，需由 Engine C 基本面引擎另行完成。*