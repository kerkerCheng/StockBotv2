# 抽取 review — `nvda_8k_ex992_20260826_q2fy27_cfo_commentary.json`

- **reviewer：** Claude Code session 2026-08-27
- **判準依據：** AGENTS.md L4（屬性三分）／L6 Gap 4（類別詞不得推斷具體實體）／L8（sole_source 需客戶端或第三方印證）／L11（措辭精度）／L15（先解析身分再查權限）。

> 本檔記錄自動抽取（`extract.py`，model=claude-sonnet-4-6）產出後，人工 review 移除或修正了什麼。
> `loader/validate.py` 對以下每一項都回報通過——它驗的是 schema 形狀，不是 claim 是否有原文支持（L15）。

## 移除／修正

- **邊 `tech:ai_cloud_platform -depends_on-> tech:nvidia_ai_infrastructure` 帶 `sole_source: true`、`substitutability: 5`：整條移除。**
  這是本輪最嚴重的一項。原文完全沒有陳述 AI cloud 只能使用 NVIDIA 基礎設施。更關鍵的是，本文件是
  **NVIDIA 自己的 CFO commentary**——依 L8，供應商自稱 sole_source 至多只能是 `verified_by_absence`（weak，≤0.5），
  必須由客戶端或第三方印證才可能升級。直接標 `sole_source: true` 同時違反「原文支持」與「來源獨立性」兩道判準。
- **邊 `co:nvidia -depends_on-> tech:hbm` 帶 `substitutability: 4`、`qualification_status: qualified`：整條移除。**
  issuer 逐字只寫 "procurement of memory"，未出現 HBM。由類別詞 memory 推斷具體型態 HBM 屬 L6 Gap 4；
  可替代性與認證狀態則原文全無討論。
- **邊 `tech:ai_compute_buildout -depends_on-> tech:datacenter_land_power_capacity` 帶 `substitutability: 5`：移除。** 憑空填值。
- **邊 `co:nvidia -invests_in-> tech:datacenter_land_power_capacity`：移除。** 原文寫的是「協助 select customers 取得」
  land/power/capacity 的安排，不是 NVIDIA 對某個技術類別投資；且 `invests_in` 指向 TechNode 語意不成立。
- **邊 `tech:hbm -constrained_by-> prod:blackwell_workstation`：移除。** 方向與原文無關；原文只說消費 PC 銷售受
  記憶體價格拖累，不是 HBM 被工作站限制。
- **節點 `tech:hbm` 的 `ramp_difficulty_intrinsic: 4`：移除。** 原文無支持，且 `tech:hbm` 是圖中既有節點，
  單份抽取不得覆寫既有屬性。
- **節點 `tech:nvidia_ai_infrastructure`／`tech:ai_cloud_platform`／`tech:datacenter_land_power_capacity`：移除。**
  皆為本份新造的抽象容器節點，與既有節點語意重疊或無獨立結構意義。
- **本份最終不建任何 edge。** 它的價值在 claim 與逐字 quote，不在圖結構——誠實的結論優於湊出邊。

## 保留的核心價值

- **措辭精度差異已寫入 cl1：** 同一季，10-Q Note 10 寫 "primarily memory and manufacturing facilities"，
  CFO commentary 寫 "primarily related to the procurement of memory"。後者明確指向記憶體採購。
  兩者不得互相代換（L11）。
- **cl2 是方向性反向訊號：** 依 AGENTS.md alpha 判準 3，客戶掏錢綁供應商＝真瓶頸；
  **供應商出錢幫客戶＝不是瓶頸**。本段揭露的是 NVIDIA 出手協助客戶取得 land／power／capacity 並參與 revenue share，
  且 issuer 自陳客戶「growing faster than their balance sheets and long-term credit profiles can support」。
  這條必須以原方向記錄，不得被讀成 NVIDIA 稀缺性的佐證。

## 狀態

- 已通過 `python -m loader.validate`。
- **尚未入圖**：graph admission 需使用者明確核准（AGENTS.md 人工 gate）。
