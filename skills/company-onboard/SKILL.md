---
name: company-onboard
description: >
  把一家新公司加入知識圖譜（Engine A）。
  當使用者說「onboard XXX」、「把 XXX 加入圖」、「我想研究 XXX 但圖裡還沒有」、
  「幫我找 XXX 的文件」、「XXX 還沒入圖」時，使用本 skill。
  觸發詞：onboard、加入圖、入圖、找文件、onboarding。
---

# Company Onboard Skill

## 定位一句話

**找文件 → 用戶確認來源獨立性 → extract → validate → load → 驗收。**

Claude 是搜尋與格式化引擎；用戶是獨立性的最終判官（L8 不能自動化）。

---

## 流程總覽（5 步）

```
Step 1 — 確認公司基本資料（ticker / 市場 / 是否上市）
Step 2 — 自動發現文件（EDGAR + Web + 學術）
Step 3 — 用戶確認來源清單（L8 獨立性審查）
Step 4 — extract → validate → load（自動化）
Step 5 — 驗收：圖中節點/邊是否存在 + L8 gate 是否通過
```

---

## Step 1 — 確認公司基本資料

**問題：**
- 公司名稱 / 常見 ticker（如有）
- 上市市場（美股 / 台股 / 瑞典 / 未上市）
- 在哪個 supply chain 位置（已知的話）

**更新 TICKER_MAP：**
若是上市公司，在 `loader/load_to_neo4j.py` 的 `TICKER_MAP` 補上 ticker：
```python
"co:<company_slug>": "TICKER",   # 美股直接用 ticker
"co:<company_slug>": "TICK.XX",  # 非美股加交易所後綴（如 .ST .KS .TW）
"co:<company_slug>": None,       # 私人公司明確設 None
```

---

## Step 2 — 自動發現文件

依上市市場走不同搜尋路徑，目標：找 ≥ 3 個不同 `origin_entity` 的一手來源。

### 美股（有 EDGAR）

```bash
# 1. SEC EDGAR 最新 10-K / 10-Q
python fetchers/edgar.py --ticker <TICKER> --type 10-K --max-chars 60000
python fetchers/edgar.py --ticker <TICKER> --type 10-Q --max-chars 60000

# 2. 近期 8-K（重大事件）
python fetchers/edgar.py --ticker <TICKER> --type 8-K --max-chars 30000
```

**額外搜尋（獨立來源，不是公司自己的文件）：**
- 客戶 / 夥伴公司的法說會 → 搜 `<company_name> site:sec.gov OR earnings transcript`
- 第三方產業報告 → 搜 `<company_name> supply chain OR sole source OR design win`
- 學術論文 → 搜 arXiv / Semantic Scholar（若是技術公司）
- **下游客戶 M&A** → 搜 `<company_name> customer acquisition OR "<known_customer> acquired"` — M&A 往往揭露供應鏈關係
- **Partnership / design-win 公告** → 搜 `<company_name> partnership OR collaboration OR design win 2025 2026`
- **第三方聚合分析**（SubStack / Seeking Alpha / SemiAnalysis）→ 搜 `<company_name> analysis OR deep dive` — 這類文章通常已彙整多個一手來源，是找命名客戶的最短路徑
- 每搜到一個新的命名客戶 → 立刻補到「命名客戶清單」，確認是否已在圖中

### 台股

```bash
# MOPS 公開資訊觀測站月營收、法說會
# 人工下載後放 library/raw/<company>_<period>.txt
```

搜尋建議：
- MOPS 財報、法說會逐字稿
- 上下游上市公司交叉驗證（客戶/供應商在台股的法說會）

### 瑞典（Nasdaq First North）/ 其他歐股

EDGAR 無資料。路徑：
- 公司 IR 頁面（investor relations）下載年報 / 半年報
- 上下游美股客戶法說會（EDGAR 可搜）
- 第三方報告（Mordor Intelligence / IDC / LightCounting 等，若可免費取得）

### 私人公司

- 搜尋客戶/供應商在法說會中提到此公司的 quotes
- LinkedIn / 公司官網技術文件 / 業界媒體報導
- 專利（USPTO / Espacenet）

---

## Step 3 — 用戶確認來源清單（L8 獨立性審查）

找到文件後，**必須呈現給用戶審查**，不自動入庫。格式：

```
發現以下 <N> 份文件，請確認 origin_entity 多樣性：

1. [文件名] origin_entity=<誰發出> evidence_tier=<tier> — <一句描述>
2. [文件名] origin_entity=<誰發出> evidence_tier=<tier> — <一句描述>
...

L8 獨立性狀態：
- 不同 origin_entity 數量：<N>/3（需 ≥ 3 才能生成 Lane Memo）
- 自我報告文件（供應商自己說）：<列出>
- 獨立來源（客戶/第三方）：<列出>

建議：<若不足，建議找哪類文件>

確認入庫？(Y/n) 或 說明哪份文件不應入庫
```

**L8 判準提醒（每次都要說）：**
- 供應商自己的法說會 / 年報 = 自我報告（`origin_entity` = 供應商本身）
- 客戶法說會提到此供應商 = 獨立佐證
- 第三方產業報告 = 獨立佐證（medium tier）
- `sole_source` 主張需客戶端或第三方確認；供應商自稱 → `verified_by_absence`（弱）

---

## Step 4 — Extract → Validate → Load

用戶確認後，逐一處理每份文件：

### 4a. 確認 raw 文件在 library/raw/

若文件是 txt/pdf 摘要，放 `library/raw/<doc_name>.txt`。
若是 EDGAR 直接下載，edgar.py 已輸出到 `library/raw/`。

### 4b. Extract（對話式，主路線）

把文件內容貼給 Claude（或請 Claude 用 Read 工具讀取），說：
> 「請依照 prompts/extract_system.md 的格式抽取這份文件，doc_id 用 `<doc_id>`，origin_entity 是 `<誰發出>`」

Claude 會：
1. 讀 `prompts/extract_system.md` 取得完整抽取規則
2. 按格式生成中介 JSON
3. 寫入 `extractions/<doc_id>.json`
4. 立刻自我檢查：具體型號/公司名是否逐字出現在 quote（L6 幻覺防護）

**備用路線（批次 / 自動化）：**
```bash
python extract.py library/raw/<doc_name>.txt --out extractions/<doc_id>.json
```
需要 `.env` 的 `ANTHROPIC_API_KEY`。日常對話不需要這條路線。

### 4c. Validate

```bash
python loader/validate.py extractions/<doc_id>.json
```

- 有 hard error → 修 JSON 後重跑
- 有 WARN: origin_entity 未填 → 手動補填
- 全 OK → 繼續

### 4d. Load

```bash
python loader/load_to_neo4j.py extractions/<doc_id>.json
```

---

## Step 5 — 驗收

```bash
# 1. 確認公司節點存在 + ticker 已注入
python query/graph_context.py --company-id co:<company_slug>

# 2. 確認 L8 gate 狀態
python -c "
from thesis.generate_lane_memo import _check_source_diversity
ctx, passes = _check_source_diversity('co:<company_slug>')
print(ctx)
"

# 3. (選用) 試 dry-run Lane Memo（不呼叫 API，只確認 gate）
python thesis/generate_lane_memo.py --company-id co:<company_slug> --dry-run 2>&1 | head -20
```

**驗收標準：**
- [ ] `graph_context.py` 回傳非空 context（節點 + 邊 + claims）
- [ ] `origin_entity` 多樣性：distinct count 顯示，若 < 3 說明哪類文件還缺
- [ ] Isolated nodes 檢查：`MATCH (n:Entity) WHERE NOT (n)-[]-() AND NOT n:Claim RETURN n.id` 應為空

---

## 常見問題

### 法說會逐字稿不在 EDGAR

EDGAR 只有 SEC 申報文件（10-K/10-Q/8-K），法說會逐字稿通常在：
- Seeking Alpha（付費，人工摘錄）
- 公司 IR 頁面（部分公司公開 PDF / webcast replay）
- Rev.com / Motley Fool / The Street（可 web search 找摘要）

策略：用 WebSearch 搜 `"<company name>" earnings transcript Q<N> <year>` 找可公開取得的版本。找到段落引文即可（不需要全文）。

### 文件是 PDF

用 Claude 直接讀 PDF（Read tool），摘錄關鍵段落放 `library/raw/<doc>.txt`，再走 extract 流程。

### origin_entity 不確定怎麼填

`origin_entity` = **誰發出這份文件**（不是被分析的公司）。

| 文件類型 | origin_entity 範例 |
|---------|------------------|
| Coherent 法說會 | `Coherent` |
| Lumentum 提到 Coherent 的法說會 | `Lumentum` |
| arXiv 論文 | `Third-party Research` |
| 券商報告（Bernstein 等）| `Third-party Research` |
| 客戶公司年報提到供應商 | `<客戶公司名>` |

---

## 與其他 skill 的分工

| 情況 | 用哪個 skill |
|------|-------------|
| 新公司入圖、找文件、跑 pipeline | 本 skill |
| 公司已在圖、問投資問題 | `skills/investment-research` |
| 丟進來一條推文/新聞要入庫 | `skills/lead-intake` |
| 找既有 thesis 的反駁角度 | `skills/blind-spot-audit` |
