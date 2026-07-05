# Directional Lane Memo
## CPO／矽光子供應鏈：外部雷射源與 InP 垂直整合

---

### 1. 一句 Thesis

**Coherent 與 Lumentum 因掌握 CPO 不可繞過的 InP 外部雷射源，在 AI 算力集群大規模建設的浪潮下（H2 2026–H2 2027）將成為供應鏈定價權節點。**

> **Variant Perception：** 當前市場共識將 CPO 受益者聚焦於 Broadcom（交換晶片 sole_source 設計定案）與 NVIDIA（算力需求方），對外部雷射源環節的定價能力關注不足。本 thesis 認為，InP 雷射產能（而非光子整合晶片設計）是 H2 2026 規模出貨的真實卡點，Coherent 的多年期 NVIDIA 協議與 InP 產能擴充將成為重新定價的催化劑。
>
> ⚠️ *Variant perception 中的估值隱含假設（本益比／EV-Revenue 溢價幅度）需 Engine C（基本面引擎）補充估值資料後才能完整填寫。*

---

### 2. 需求驅動

- **AI training/inference cluster buildout → CPO 需求：** AI 訓練與推理集群的規模化建設直接拉動 CPO 需求，並同時推動光學電路交換（OCS）、scale-up 光互聯等元件採購。
  `(source: coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s3, lumentum_q2fy26_cpo_s2)`

- **CPO → 資料中心交換機/Scale-up 網路：** CPO 作為關鍵元件嵌入資料中心交換機與 scale-up 網路，同時資料中心網路需求又反過來驅動 CPO 採購，形成相互強化的正向循環。
  `(source: Broadcom_q2fy26_cpo_s1, coherent_q2fy26_cpo_s14)`

- **超大型雲端與 AI 原生客戶（Anthropic、OpenAI、Meta、Google）大規模採購 Broadcom XPU：** Broadcom 同時供應 Google、Meta、OpenAI、Anthropic 的 AI XPU 與 CPO 解決方案，需求集中化使 CPO stack 的每一層壓力同步放大。
  `(source: Broadcom_q2fy26_cpo_s10, Broadcom_q2fy26_cpo_s5)`

- **Blackwell 架構 GPU 平台落地 → scale-out CPO 先行，scale-up CPO 接棒：** AI 算力建設支撐 Blackwell 架構的規模化部署，CPO 被預期於 H2 2026 開始 scale-out 收入，H2 2027 進入 scale-up ramp。
  `(source: Nvidia_q1fy27_s5, coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s3)`

---

### 3. Stack 摘要

**需求層（end_demand）** 集中度高但過渡平順：NVIDIA、Google、Meta、Anthropic、OpenAI 等超大型客戶已在圖中確認為 Broadcom 下游，需求可見性強，短期不存在結構性中斷風險。

**平台整合層（CPO 系統設計）** 出現明顯集中：Broadcom 在 CPO 系統設計層擁有 sole_source=True、substitutability=5、qualification_status=designed_in 的地位，意味著此層替換成本極高，平台鎖定已形成。

**關鍵元件層（外部雷射源 → InP 基板）** 是供應鏈中結構性瓶頸最為集中之處：External Laser Source 的 substitutability=2（難以替代），High-power CW DFB laser 對 InP 基板的依賴度達 substitutability=1（圖中最低值），且 InP 晶圓的 6 吋產線擴充進度直接決定 H2 2026 能否如期出貨，此層正在發生最顯著的供應鏈結構性緊縮。

---

### 4. 主瓶頸

#### 一級瓶頸：InP 基板 → High-power CW DFB Laser

| 屬性 | 數值 |
|---|---|
| substitutability | **1**（圖中最低，極難替代） |
| sole_source | False（目前資料未確認單一壟斷供應商） |
| 依賴路徑 | InP substrate → High-power CW DFB laser → External Laser Source → Co-Packaged Optics |

InP 基板的 substitutability=1 表示在目前技術路徑下，High-power CW DFB laser 幾乎無法以非 InP 材料替代。High-power CW DFB laser 本身亦依賴 6 吋 InP 晶圓產線（substitutability=4，`source: coherent_q2fy26_cpo_s2, coherent_q2fy26_cpo_s5`），而此產線的擴充速度直接決定雷射供應能否跟上 CPO ramp 節奏。

> ⚠️ **資料缺口說明：** InP 基板供應商層面，圖中 sole_source=False，**目前資料尚未確認是否存在單一壟斷 InP 晶圓供應商，需進一步驗證**（例如：確認 AXT、Sumitomo 等 InP substrate 廠商是否已有供應關係節點）。

#### 二級瓶頸：External Laser Source（Lumentum、Coherent 雙主供）

| 供應商 | substitutability | sole_source | lead_time_weeks | qualification_status |
|---|---|---|---|---|
| Lumentum → External Laser Source | 2 | False | **26 週** | qualifying |
| Coherent → External Laser Source | 2 | False | **30 週** | sampling |
| Lumentum → UHP laser | 5 | **True** | — | designed_in / qualifying |
| Coherent → NVIDIA | 5 | **True** | — | designed_in |

Lumentum 在 Ultra-High-Power (UHP) laser 供應 NVIDIA 路徑上已確認 sole_source=True，qualification_status 同時出現 designed_in（`lumentum_q2fy26_cpo_s14, s15, s27`）與 qualifying（`lumentum_q3fy26_cpo_s2`），兩個狀態並存，暗示跨世代（scale-out → scale-up）的資格認證仍在推進中，ramp 不確定性尚未完全消除。

Coherent 對 NVIDIA 的供應同樣確認 sole_source=True、designed_in（`coherent_q3fy26_cpo_s7, s8`），並持有橫跨 scale-out 與 scale-up 的多年期多十億美元協議（`coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s6`）。

External Laser Source 對 CPO 的依賴關係標示 substitutability=2（`source: s2`），確認此層是整個 CPO stack 中替換難度最高的非壟斷環節。

---

### 5. 最強證據

- **coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s6**
  「Coherent has a multibillion-dollar, multi-product CPO development and supply agreement with NVIDIA spanning through the end of this decade, covering both scale-out and scale-up CPO.」
  （confidence: **0.75**，confirmed）

- **coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s3 + s20**
  「Coherent expects first CPO revenue in the second half of calendar year 2026 (scale-out), with scale-up CPO ramp beginning in the second half of 2027.」
  （confidence: **0.75**，guided）

- **coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s8**
  「Coherent is doubling its indium phosphide manufacturing capacity in 2025, with further expansion planned for 2026.」
  （confidence: **0.75**，guided）

- **lumentum_q2fy26_cpo_s14, lumentum_q2fy26_cpo_s15, lumentum_q2fy26_cpo_s27**
  「Lumentum SUPPLIES_TO Ultra-High-Power (UHP) laser：sole_source=True, qualification_status=designed_in, substitutability=5。」
  （confidence: **0.90**）

---

### 6. 什麼會推翻這個 Thesis（Disproof Conditions）

- **若 NVIDIA 取消或大幅縮減與 Coherent 的多年期 CPO 採購協議，或將 CPO 採購轉移至競爭供應商**，則 Coherent 在 sole_source 雷射供應鏈的定價節點地位將瓦解，thesis 需降評退場。
  `(source: coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s6，disproof_condition)`

- **若 Coherent 的 InP 產能倍增計畫（2025）延誤、取消，或實際產出未能如期翻倍**，則 H2 2026 scale-out CPO 出貨時程將直接受阻，外部雷射源成為真實出貨瓶頸的論點將需重估。
  `(source: coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s8，disproof_condition)`

- **若 CPO 量產時程滑移至 H2 2026 之後（scale-out）或 H2 2027 之後（scale-up）**，或超大型雲端客戶轉向替代光互聯架構（如持續擴大可插拔光模組比重而非擁抱 CPO），則需求拉力假設需重新定錨，thesis 核心邏輯承壓。
  `(source: coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s3, s20，disproof_condition；推導部分標注：推導，非圖中明確主張)`

---

### 7. 接下來盯什麼（Leading Indicators / Catalysts）

- **Coherent 季度法說會（每季）：InP 產能利用率與 CPO 收入確認**
  觀測 Coherent 是否於 H2 CY2026 正式認列 CPO 收入（scale-out），以及 InP 產能是否按計畫完成 2025 倍增目標。若 CPO 收入時程延後，或管理層下修 InP 擴廠進度，視為 thesis 負向訊號。
  `(source: coherent-corp-cohr-discusses-photonics-innovation-and-data-center-communications-at-ofc_march_17_s3, s8)`

- **Lumentum 季度法說會（每季）：UHP laser qualification 進展與 lead time 變化**
  Lumentum UHP laser 目前同時存在 designed_in 與 qualifying 兩種狀態，需確認 scale-up 路徑的客戶認證是否完成。lead_time=26 週的縮短或延長，是供需緊張度的直接溫度計。
  `(source: lumentum_q2fy26_cpo_s14, lumentum_q3fy26_cpo_s2)`

- **NVIDIA / Broadcom 客戶公告或 AI 基礎設施採購計畫更新（每次重大公告）**
  AI 訓練與推理集群建設是整個 CPO demand pull 的根源。NVIDIA Blackwell 架構的部署進度、Broadcom XPU 客戶（Anthropic、OpenAI、Google、Meta）的 capex 指引，是 CPO ramp 可見度的領先指標。
  `(source: Nvidia_q1fy27_s5, Broadcom_q2fy26_cpo_s10)`

- **InP 晶圓供應商產能公告或 Coherent/Lumentum 的 InP 垂直整合動作（不定期，關注每季財報附註與行業展會）**
  由於 InP 基板 substitutability=1 為圖中最低值，任何上游 InP 晶圓廠商的產能限制公告、或 Coherent/Lumentum 宣布進一步垂直整合 InP 製造，均將顯著影響外部雷射源供應的天花板，是本 thesis 最需持續監測的結構性變數。
  `(source: lumentum_q2fy26_cpo_s20, coherent_q3fy26_cpo_s1)`

---

> **免責聲明：** 本備忘錄為方向性研究備忘錄，不構成可操作的投資建議，不含目標價、買賣建議或持倉大小建議。財務核驗（客戶集中度、毛利率、backlog、稀釋風險、估值壓力測試）為 Watchlist 升格的必要條件，需由 Engine C 基本面引擎另行完成。