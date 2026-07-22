---
name: investment-research
description: >
  對知識圖譜（Neo4j）+ 財務資料（SQLite）提問，產出有根據的投資研究回答。
  當使用者問關於標的的瓶頸性、競爭地位、供應鏈位置、thesis 狀態、或說「評估XXX」、
  「分析XXX的競爭位置」、「XXX 在 CPO 供應鏈的地位」、「thesis 還成立嗎」、
  「建議買嗎」、「怎麼看XXX」、「幫我分析$TICKER」時，使用本 skill。
  研究 agent（Claude Code / Codex）是分析引擎；圖譜是跨 session 的持久記憶；本 skill 定義如何接取這份記憶並組成回答。
  觸發詞：評估、分析、怎麼看、建議、thesis、CPO、瓶頸、供應鏈、$TICKER。
---

# 投資研究 Skill

## ⚠️ 定位先讀（別跳過）

**這個系統的核心不是自動化，是記憶。**

研究 agent（Claude Code / Codex）是分析引擎，知識圖譜（Neo4j）是持久的、跨 session 的研究筆記本。
使用者問問題 → agent 從圖取 context → 結合財務數據 → 合成有根據的回答。

**圖譜能做的事：**
- 記住哪些公司在哪個供應鏈位置
- 記住哪些主張有哪些來源支撐（可追溯）
- 記住 `sole_source`、`substitutability`、`ramp_difficulty` 等瓶頸屬性
- 記住 thesis 與可證偽條件（`disproof_condition`）

**圖譜不能做的事：**
- 不能替你判斷分析好不好（這是研究 agent 的工作）
- 不能自動更新（需要你餵新文件進去）
- 不能驗證自己的來源是否偏誤（你要問研究 agent）

---

## 系統架構（你手上有什麼）

```
使用者問題
    ↓
[本 skill — 研究 agent 分析]
    ↓                        ↓
Neo4j 圖                  SQLite 財務數據
query/graph_context.py    engine_c/checklist.py
    ↓                        ↓
供應鏈結構 + 主張 + 來源   財務快照 + Watchlist Gate
    ↓                        ↓
         合成回答（agent）
```

**指令參考：**
```powershell
# 一條 Signal 到 zero-size／funded（依 intent）Action Card
python -m decision_lab evaluate-signal "<Signal>" --ticker <TICKER> --intent research --format markdown

# 重新讀取 authorities 並建立新 decision（不改寫舊 decision）
python -m decision_lab reassess <decision_id> --assessment <assessment.json> --intent paper --format markdown

# 今天是否需要動作（純讀、on-demand）
python -m decision_lab today --format markdown

# 取公司子圖 context（2 跳供應鏈）
python query/graph_context.py --company-id co:<ticker_lower>

# 取全圖 context（Lane Memo 用）
python query/graph_context.py

# 財務核驗清單
python engine_c/checklist.py <TICKER>

# 生成 Lane Memo（需要 context 輸入）
python thesis/generate_lane_memo.py --company-id co:<ticker_lower>
```

---

## 問題分流（三類）

### 類型 1 — 快速事實查詢

**觸發：** 單一具體問題，不需要完整 thesis。
- 「SIVE 在 CPO 是 sole_source 嗎？」
- 「Coherent 的 CPO 相關節點有哪些？」
- 「圖裡有哪些公司的 `substitutability < 2`？」

**流程：**
1. 執行 `python query/graph_context.py --company-id co:<ticker>` 取子圖
2. 直接從 context JSON 找相關屬性/邊
3. 回答時標明 evidence_tier 和 source_ids（讓使用者知道根據來自哪）
4. 明確說出圖裡沒有的資訊（不要自己推斷填補空缺）

**格式：** 2-5 段直接回答 + 來源品質標注（tier 幾、哪份文件）+ 什麼是圖裡沒有的

---

### 類型 2 — Thesis 評估

**觸發：** 使用者想知道某個方向是否成立、是否要進場/出場。
- 「SIVE 值得繼續持有嗎？」
- 「CPO 供應鏈的瓶頸 thesis 還成立嗎？」
- 「我應該評估哪些公司？」

**流程：**
0. 若使用者提供新 Signal，先呼叫 `evaluate-signal ... --intent research` 做 wide capture；若問題是
   「我現在是否該動作」，先呼叫 `python -m decision_lab today --format json`，再對相關 decision 呼叫
   `python -m decision_lab card <decision_id>`。以 structured result 的
   `action / urgency / weakest_link / paper / live / blockers / next_action` 為決策主幹；本 skill
   只補研究解釋，不重算部位、不同 lane 的 Gate 或 freshness。
1. 執行 `python query/graph_context.py --company-id co:<ticker>` 取子圖
2. 執行 `python engine_c/checklist.py <TICKER>` 取財務快照
3. 評估以下四個維度（這是研究 agent 的判斷，不是自動化）：

| 維度 | 要問的問題 |
|------|-----------|
| **供應鏈位置** | 這家公司在哪個 abstraction_level？role 是什麼？有幾條邊？ |
| **瓶頸性** | `sole_source` 有多少？`substitutability` 分布？替代路徑存在嗎？ |
| **來源品質** | 最強主張是 tier 幾？origin_entity 有幾個？有無 L8 偏誤？ |
| **財務錨點** | 毛利率趨勢？EV/Revenue？估值隱含什麼假設？ |

4. 套 L8 偏誤檢查：若所有關鍵主張的 source_ids 都是同一家公司的文件 → 主動警告
5. 回答要包含：現在知道什麼 / 還不確定什麼 / 什麼資訊能改變看法
6. 若研究結果要進入 Decision Lab，產生五軸 assessment JSON；每個非 `unknown` 軸只能引用這次
   bounded graph／Engine C／market context 的 stable refs。呼叫 `reassess` 讓 Python 驗 refs、freeze、
   Coverage、Confidence／sizing 與 audit trail；skill 不自行算 ceiling、supported range 或 paper target。

**格式：** 結構化評估（位置 → 瓶頸 → 來源品質 → 財務） + 信心度 + 知識缺口

---

### 類型 3 — 完整 Lane Memo

**觸發：** 使用者明確說要 Lane Memo，或首次深度評估某個 thesis。
- 「幫我出一份 SIVE 的 Lane Memo」
- 「生成 CPO 的 thesis 文件」

**流程（對話式，主路線）：**
1. 執行 L8 gate 檢查：
   ```bash
   python -c "from thesis.generate_lane_memo import _check_source_diversity; ctx,p=_check_source_diversity('co:<slug>'); print(ctx)"
   ```
   若 gate 未過 → 說明缺哪類文件，**不繼續**。若用戶確認 override → 繼續並在 memo 標注。
2. 取圖 context：`python query/graph_context.py --company-id co:<slug>`
3. 取 Engine C 數據：`python engine_c/checklist.py <TICKER>` + `python engine_c/market_data.py <TICKER>`（若 ticker 已知）
4. **研究 agent 在對話裡直接生成 Lane Memo**，依 `prompts/lane_memo_system.md` 格式
5. 生成後逐項核查（agent 自己做）：
   - `variant_perception` 有沒有？格式是否「股價隱含 X → 本 thesis 認為 Y → 催化劑 Z」？
   - `disproof_condition` 有沒有？附沒附核查頻率和觸發後 48h 動作？
6. 缺 `variant_perception` 數字 → 標 `[TODO: 待 Engine C 估值數字補齊]`
7. 請用戶確認後，寫入 `thesis/<company>_v<N>_lane_memo.md`

**備用路線（自動�� / cron）：**
```bash
python thesis/generate_lane_memo.py --company-id co:<slug> --ticker <TICKER> --override-gate --override-reason "<理由>"
```
需要 `.env` 的 `ANTHROPIC_API_KEY`。日常對話不需要跑這條路線。

**格式：** 完整 Lane Memo 文件（存 `thesis/`）+ 升格 Watchlist 所需缺口清單

---

## 公司不在圖中時（Onboarding 觸發）

若 `query/graph_context.py --company-id co:<ticker>` 回傳空圖或「公司不在圖中」：

**不要自己從 training data 回答。** 訓練資料是舊的、無法追溯。

正確做法：
1. 告知使用者：「圖裡還沒有這家公司的資料，需要先 onboarding」
2. 引導走 `docs/onboarding-sop.md` 流程（5 步：EDGAR/手動取文件 → extract → validate → load → 驗證）
3. 如果使用者只想快速評估（不想 onboarding），可以：
   - 用 training data 給初步看法，**但必須明確標示「非圖內資料，無法追溯」**
   - 列出「若要入圖，最值得找的 3 種一手來源」

---

## 來源品質標注（每次回答都要做）

回答投資相關問題時，必須附上來源品質說明：

```
根據圖內資料：
- [主張A]：來源 coherent_q3fy26_s2（tier 1 — 法說會逐字稿，Coherent 2026Q3）
- [主張B]：來源 sivers_ar2024_s7（tier 1 — 年報，Sivers 2024），⚠️ 自我報告（L8）
- [主張C]：無圖內來源 — 以下為推斷，請自行驗證
```

**L8 偏誤自動觸發條件：** 若節點的主要 claims 的 source_ids 裡 `origin_entity` 全是同一家公司 → 加 ⚠️ 警告：「供應商自稱，缺獨立佐證」

**來源缺口識別：** 若 sole_source=True 但所有來源都是供應商自己的文件 → 標注 `sole_source_evidence_quality: weak`，並建議找客戶端或第三方文件

---

## 知識缺口的正確處理

當圖內資料不足以回答問題時，**明確說出缺什麼**，比猜測填補更有價值：

```
目前圖內缺口：
- 未見客戶端確認 SIVE 的 sole_source 地位（只有 Sivers 自稱）
- 無 POET Technologies 的詳細技術比較（尚未入圖）
- 財務數據缺 backlog 資訊（需手動輸入）

建議的下一步（按優先序）：
1. 找 Coherent 2025 法說會——他們是 SIVE 的客戶，可確認或否認獨佔
2. 取 O-Net 6963.HK 最近財報——競爭者，可評估替代威脅
3. 更新 Engine C backlog 手動欄位
```

---

## 類型 4 — 個人倉位建議（需 Google Sheets 資料）

**觸發：** 使用者問「我該投多少」、「這檔值不值得加倉」、「我的 AI bucket 還有空間嗎」。

**流程：**
0. Probe／既有持股的「現在是否動作」先跑 `python -m decision_lab today --format json`，再讀相關
   Action Card；兩者都是純讀。新 Signal 用 `evaluate-signal`，新 evidence／price／FX／holdings／policy
   用 `reassess`。只有使用者明確指定 `paper`／`live` intent 才評估相應 lane；live 仍須使用者明確
   `record-choice`、自行下單，再用 `record-fill` 回報，任何一步都不得由 recommendation 推定。
   只有已正式升格的部位才走下列 formal policy 流程。
1. 執行 `python fetchers/gsheets.py --ticker <TICKER>` 取持倉資料
2. 執行 `python fetchers/gsheets.py --summary` 取 ai_theme bucket 使用率
3. 查 Engine C 估值數據：`python engine_c/checklist.py <TICKER>`
4. 執行 `thesis.preconditions.check_all(<TICKER>)`；五項清單含 `manual_required` 或 `missing` 時，不得給倉位數字，只列待補項
5. 全部 gate 通過後，呼叫 `thesis.investment_policy.calculate_position_limit(...)`；不可在 skill 內抄寫百分比或自行算另一套
6. 檢查 `check_factor_exposure(...)`，並在回答附 `policy_version`、原始 analyst coverage 與 query-time coverage view

conviction 由 thesis 評分（`thesis/scoring_rubric.md`）和 L8 來源品質共同決定。規則語意見 `docs/investment-sop.md`；當前數字唯一權威是 `config/investment_policy.json`。`crowding` 不寫入 Engine C。

**輸出格式：**
```
## 倉位建議（個人化）

持倉狀態：[已持有 / 尚未持倉]
AI 主題 bucket 使用率：XX%（建議上限 50%）

Conviction 評估：[分數 / 理由]
建議倉位：ai_theme bucket 的 X-Y%（相當於若 bucket 為 $N，建議 $N×X%）
政策版本：<policy_version>

⚠ 注意：
- [若已持倉：說明是否建議加倉/持倉/減倉]
- [若 L8 不足：提醒 Lane Memo 不能生成，建議先補文件]
- [若估值過高：提醒估值風險]

這是研究框架下的方向建議，不是買賣指令。最終決策由你做。
```

**GSHEETS 未設定時：**
若 `GSHEETS_SPREADSHEET_ID` 未設定，告知使用者：
「需要設定 Google Sheets 連接才能提供個人化倉位建議。
 請在 `.env` 設定 `GSHEETS_SPREADSHEET_ID` 和 `GSHEETS_SERVICE_ACCOUNT_JSON`。
 可先參考 `fetchers/gsheets.py` 的欄位格式建立工作表。」

---

## 投資建議的邊界

本系統是**研究工具，不是投資顧問**：

- **Lane Memo**：方向性備忘，說「thesis 是否成立」，不說「買多少」
- **Watchlist**：thesis 通過 + 財務核驗後升格，說「值得深研」，不說「何時買」
- **Underwrite Sheet**：具體標的深挖，仍需使用者自行決策部位大小

升格到 Watchlist 的三個前置條件（L9）：
1. Lane Memo 評分通過（`thesis/scoring_rubric.md`）
2. `variant_perception` 已明確寫出（股價隱含假設 X → 本 thesis 認為 Y → 催化劑 Z）
3. 財務核驗清單 5 項完成（`engine_c/checklist.py`）
4. 最小投資規則已定義：見 [`docs/investment-sop.md`](../../docs/investment-sop.md)（`thesis/preconditions.py` 的 L9 gate 依賴此檔）

---

## 與其他 skill 的分工

| 情況 | 用哪個 skill |
|------|-------------|
| 丟進來一條推文/新聞/小道消息，要入庫 | `skills/lead-intake` |
| 已有 thesis，要找反駁角度 | `skills/blind-spot-audit` |
| 問關於某公司/市場的投資研究問題 | 本 skill |

---

## 與既有系統的接點

- Engine D operational workflow：`python -m decision_lab evaluate-signal`／`reassess`／`today`／`card`
- Explicit live facts：`python -m decision_lab record-choice`／`record-fill`（不連 broker、不寫 Sheet）
- 取圖 context：`query/graph_context.py`
- 財務快照：`engine_c/etl_yfinance.py`、`engine_c/checklist.py`
- Lane Memo 生成：`thesis/generate_lane_memo.py`
- Lane Memo 評分：`thesis/scoring_rubric.md`
- 新公司 onboarding：`skills/company-onboard/SKILL.md`
- 個人持倉資料：`fetchers/gsheets.py`（需 `.env` 設 GSHEETS_*）
- 來源分類標準：`AGENTS.md`「來源登記表」+ 證據四階

## 已知限制（v0，等真實流量撞）

- **variant_perception 需要估值數字**：Engine C 目前只有 yfinance 快照，缺 forward P/E 分析師估值細節時只能標 TODO
- **圖只有 CPO/矽光子 + SIVE**：其他主題暫時沒有圖內資料
- **sole_source 缺獨立確認**：目前 SIVE 的關鍵主張多為自我報告（L8），需要客戶端文件補強
- **backlog 和客戶集中度需手動輸入**：不是 yfinance 能自動抓的欄位
