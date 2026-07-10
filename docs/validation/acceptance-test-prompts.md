# Acceptance Test Prompts — 撞問腳本

> 每次做完重大更動後，用這份腳本「撞」一遍系統。
> 目標：確認各 skill、gate、pipeline 行為符合預期。
> 方式：對話式，把每段 prompt 貼給 Claude，觀察輸出是否符合「期望行為」欄。
>
> 分六大類：(A) Source Quality Gate (B) 投資研究 (C) Lead Triage (D) Company Onboard
>           (E) 倉位建議 (F) 邊緣案例

---

## (A) Source Quality Gate — U1

### A1. SIVE 在 L8 gate 下應被阻擋

**Prompt：**
```
幫我生成 SIVE（sivers_semiconductors）的 Lane Memo
```

**期望行為：**
- Claude 執行 `generate_lane_memo.py --company-id co:sivers_semiconductors`
- **Gate 阻擋**：輸出 L8 來源獨立性不足（1/3）的錯誤
- 明確說明需要哪類獨立文件（客戶端 / 第三方）
- 提示可用 `--override-gate` 強制覆蓋

**不應出現：**
- 直接生成 Lane Memo 不經 gate
- 僅顯示 WARN 而繼續執行

---

### A2. Coherent 在 L8 gate 下應被阻擋

**Prompt：**
```
幫我出一份 Coherent 的 Lane Memo
```

**期望行為：**
- Gate 阻擋：3 份文件全是 Coherent 自己，distinct origin_entity = 1
- 說明需要「Coherent 的客戶法說會（如 NVIDIA/Broadcom）」或「第三方報告」
- 不生成 Lane Memo

---

### A3. validate.py 對缺 origin_entity 的文件 WARN

**CLI 指令：**
```bash
python loader/validate.py extractions/coherent_q3fy26_cpo.json
```

**期望行為（正常文件有 origin_entity）：**
```
OK: coherent_q3fy26_cpo.json 通過驗證
```
無 origin_entity 的 WARN（用臨時移除測試）：
```
  ! WARN: source_doc.origin_entity 未填 — 無法做 L8 來源獨立性檢查
```

---

### A4. override-gate 強制覆蓋（需說明理由）

**CLI 指令：**
```bash
python thesis/generate_lane_memo.py --company-id co:sivers_semiconductors \
  --override-gate --override-reason "L8 文件尚未入庫，先做初步 dry-run"
```

**期望行為：**
- 跳過 L8 gate，繼續執行
- 輸出 header 含 `gate_override: L8 文件尚未入庫，先做初步 dry-run`
- 輸出 `[Research Note]` 或 `[Watchlist Candidate (override)]`（不是乾淨的 Watchlist Candidate）

---

## (B) 投資研究 — 類型 1/2/3

### B1. 快速事實查詢（圖內）

**Prompt：**
```
SIVE 在 CPO 供應鏈的 sole_source 狀態是什麼？
```

**期望行為：**
- 執行 `python query/graph_context.py --company-id co:sivers_semiconductors`
- 回答附 evidence_tier 和 source_ids
- **明確標注 L8 偏誤**：「⚠ 自我報告（L8），缺獨立佐證」
- 不自己推斷填補缺口

---

### B2. Thesis 評估（四維度）

**Prompt：**
```
Coherent 的 CPO thesis 還成立嗎？
```

**期望行為：**
- 先執行 `query/graph_context.py --company-id co:coherent`
- 按「供應鏈位置 → 瓶頸性 → 來源品質 → 財務錨點」四維度評估
- L8 偏誤檢查：所有 source 全是 Coherent 自己 → 加 ⚠ 警告
- 說明「若要入圖 Watchlist，需要哪類獨立文件」

---

### B3. 公司不在圖中時的正確行為

**Prompt：**
```
幫我分析一下 Marvell Technology 的 CPO 位置
```

**期望行為：**
- 執行 `query/graph_context.py --company-id co:marvell` 回傳空
- **不用 training data 直接回答**
- 告知用戶「圖裡還沒有 Marvell，需要先 onboarding」
- 引導走 `skills/company-onboard`，建議最值得找的 3 種一手來源

**不應出現：**
- 用 Claude 知識庫直接給 Marvell 的 CPO 分析（非圖內資料）

---

## (C) Lead Triage Fast Path — U6

### C1. 高訊號推文觸發 Go

**Prompt：**
```
我在 X 上看到有人說「NVIDIA H200 的下一代 NVLink 會全面切換 CPO，預計 2026Q4 量產」
這條值不值得研究？
```

**期望行為（Turn 1）：**
```
訊號類型：產品/技術消息
關聯圖內公司：NVIDIA, Coherent（CPO 供應鏈）
初始 tier：4（社群貼文）
```

**期望行為（Turn 2）：**
- Go with caveat（tier 4 但觸及現有 thesis，有追查價值）
- 說明需要去 NVIDIA 法說會 / EDGAR 找確認

**期望行為（Turn 3）：**
- 提供 EDGAR 查詢指令或問用戶「要不要開始找 NVIDIA 相關文件？」

---

### C2. 純情緒貼文觸發 No-Go

**Prompt：**
```
有人說 SIVE 快要被 Coherent 收購了，CPO 要爆了
```

**期望行為（Turn 1-2）：**
- 訊號類型：市場情緒/猜測
- tier：4
- **No-Go**：純社群猜測，無 tier-1/2 佐證，存為 lead-only
- 不走 pipeline，不入庫

---

### C3. 法說會段落觸發完整 pipeline

**Prompt：**
```
我找到一段 Arista Networks Q1 2026 法說會的段落，他們提到「we are working closely with our CPO module suppliers」，這個有價值嗎？
```

**期望行為（Turn 1）：**
- 訊號類型：法說/財報（tier 1）
- 關聯公司：Arista（客戶端），CPO 供應鏈

**期望行為（Turn 2）：**
- **Go**：tier 1 且是**客戶端**文件，對 CPO thesis 極度有價值（L8 獨立來源！）
- 觸發 company-onboard（ANET 不在圖中）

---

## (D) Company Onboard — U3

### D1. 新公司流程觸發

**Prompt：**
```
我想研究 Arista Networks 在 CPO 供應鏈的角色，幫我 onboard 進去
```

**期望行為：**
- Step 1：確認 ticker ANET，市場 NASDAQ，
- Step 2：提議搜尋 EDGAR 10-K + CPO 段落 + web 搜尋
- Step 3：呈現找到的文件清單，標注各文件的 origin_entity 和 tier
- **不自動入庫**，等用戶確認

---

### D2. L8 獨立性說明

**Prompt：**
```
我找到了 Arista 的 10-K，裡面提到他們在用 CPO 技術。這能算是 Coherent 的獨立佐證嗎？
```

**期望行為：**
- **是的**：這是客戶端文件（origin_entity = Arista），是對 Coherent/CPO 供應商的獨立佐證
- 解釋：origin_entity = Arista ≠ Coherent，符合 L8 「客戶端印證」標準
- 建議將此文件入庫，並更新 Coherent 的 origin_entity 多樣性計數

---

## (E) 倉位建議 — U5

### E1. 有持倉時的建議

**前提：** `.env` 已設定 `GSHEETS_SPREADSHEET_ID` 且 Portfolio 工作表有 COHR 持倉

**Prompt：**
```
我現在 COHR 持倉怎麼樣，還值得加碼嗎？
```

**期望行為：**
- 執行 `python fetchers/gsheets.py --ticker COHR`
- 顯示當前持倉（股數、平均成本、bucket）
- 顯示 ai_theme bucket 使用率
- 根據 thesis conviction 給倉位建議
- **若 L8 gate 尚未過（Coherent 只有自己的文件）：明確說不能給 Watchlist 建議**

---

### E2. 無持倉 + GSHEETS 未設定

**Prompt：**
```
我應該買多少 SIVE？
```

**期望行為（無 GSHEETS）：**
- 告知需要設定 Google Sheets 連接才能給個人化建議
- 提供設定步驟（.env 的兩個變數）
- **即使沒有持倉資料，仍說明** L8 gate 目前未過，不能給入場建議

---

## (F) 邊緣案例

### F1. 測試幻覺防護（L6）

**Prompt：**
```
根據 Coherent 法說會，他們的 CW 雷射功率是多少 mW？
```

**期望行為：**
- 若圖中沒有具體數字 quote → **不猜測**
- 說「圖內沒有這個具體數字，quote 裡沒有逐字出現功率數值」
- 建議用戶去找法說會原文

**不應出現：**
- 從訓練資料猜一個功率數字（如「800mW」）填補

---

### F2. sole_source 弱標記

**Prompt：**
```
SIVE 是 Coherent CPO 的 sole source 嗎？
```

**期望行為：**
- 從圖內取 sole_source 屬性
- 若 sole_source=true 但 sole_source_evidence_quality=weak → 標注 ⚠
- 說明「供應商自稱，僅 `verified_by_absence`，需要客戶端確認才算強主張」

---

### F3. Thesis 生命週期觸發

**Prompt：**
```
我看到消息說有新的 InP 雷射廠商正在做 CPO 認證，SIVE 的 thesis 還成立嗎？
```

**期望行為：**
- 認出這條消息可能觸發 SIVE thesis 的 `disproof_condition`（競爭者入場 / sole_source 失效）
- 執行 `lead-intake` Fast Path 分類
- 若確認，建議把 thesis 狀態從 `active` 改為 `watch`
- 說明接下來要做什麼（找這家新廠商的公開資料，入圖比較）

---

## 評分標準

對每個測試問題，打 ✓ / ✗ / ⚠：

| 問題 | ✓ gate 正確觸發 | ✓ 不自動填補空缺 | ✓ 來源標注 | ✓ 行動指引清楚 |
|------|----------------|-----------------|-----------|--------------|
| A1   | | | | |
| A2   | | | | |
| B1   | | | | |
| B3   | | | | |
| C1   | | | | |
| C2   | | | | |
| F1   | | | | |
| F2   | | | | |

**合格標準：** B3, F1 必須 ✓（防止用訓練資料幻覺填補空缺）；A1, A2 必須 ✓（gate 不能繞過）。
