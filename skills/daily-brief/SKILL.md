---
name: daily-brief
description: >
  每日核准迴路：把 harvest → triage → pq1 研究 drain → 今日決策 → 到期 thesis 聚合成一份
  action-first 的 Daily Approval Brief，使用者用一行批次語法（`1 3 7 go 4 drop 5 6 pending`）
  核准。當使用者說「daily brief」「今天有什麼要處理」「跑每日摘要」「有哪些待判斷」「今天需要
  動作嗎」時使用。三道閘門不放寬：graph admission 必經核准、深挖由 priority/使用者驅動但入圖仍
  核准、live 資本永遠人工。純讀聚合，不自動建 decision、不下單、不自動入圖。觸發詞：daily brief、
  每日摘要、今天有什麼、待判斷、今天需要動作嗎。
---

# Daily Approval Brief Skill（v1.1）

## 定位一句話

**每天一份 action-first brief，使用者回一行批次語法就完成當日核准；貴的研究（pq1）在背景替他消化。**

系統做便宜的事（harvest／triage／聚合）與可自動化的 pq1 drain（到「等你核准」為止）；人工只做
判斷（要不要深挖、要不要入圖）。無事時 brief 是一行 `NO ACTION`。三道閘門永不自動：graph
admission 必經核准 exact 對象、深挖由 priority 排序但入圖仍核准、live 資本永遠人工。

> **介面是對話，不用 GitHub UI。** cloud routine 產 brief → Claude app 推播 → 你在 thread 回批次語法。
> `decision_lab` 決策命令只在本機（雲端 clone 無 private Decision Store）；雲端看決策用 MCP 唯讀
> `get_decision_brief`、改 leads 狀態用 MCP `record_lead_decision`（本機 server 幫你窄 pathset commit+push）。
> pq1／pq2 定義見 CONCEPTS.md。

---

## 執行流程

### Step 1 — Harvest（零 token）

```powershell
python crons/harvest_leads.py
```

抓 RSS＋EDGAR watch 新項，URL-hash 去重。fetch／parse 失敗各記 harvest_log；**解析失敗 ≠ 無新文**，
brief 要標明 failed source 並提示 fallback（如 `site:aleabitoreddit.substack.com` web search）。

### Step 2 — Triage 新 pending leads（依 signal-triage 判準）

```powershell
python -m engine_b.cli list --status pending --by-priority --tracked <已追蹤ticker>
```

對每條**新** pending lead 套 `skills/signal-triage/SKILL.md` 五要素判準。判斷完寫回（本機用 CLI、
雲端用 MCP `record_lead_decision`），並帶上 priority flags（供 pq1 排序）：

```powershell
python -m engine_b.cli triage <lead_id> --go   --tier 3 --reason "<要素>" [--contradiction] [--novelty] [--independent]
python -m engine_b.cli triage <lead_id> --no-go --tier 4 --reason "<為何篩掉>"
```

triage 寬鬆（關聯性與可引用性是硬指標，其餘軟指標命中即 go）；no-go 也記 reason。`tier` 是來源初步
分級，**不是** evidence tier、不影響入圖強度。priority flags（矛盾/反證、新穎、獨立來源）只供 pq1 排序。

### Step 3 — pq1 drain（priority，可續跑）

```powershell
python -m engine_b.cli drain --limit <N> --tracked <已追蹤ticker>
```

列出接下來該研究的 leads（依 priority；pop triaged_go＋researching）。對每則跑 **pq1＝source-trace＋
extraction**（`skills/source-trace`＋`skills/lead-intake` 的研究部分），逐則 checkpoint 狀態：

```powershell
python -m engine_b.cli advance <lead_id> researching        # 開始
python -m engine_b.cli advance <lead_id> action_prepared --ref research_action_id=<ra_id>   # prepare 完
```

pq1 是唯一昂貴階段（web search + 讀文件 + 抽 claim）——priority 決定貴的 token 先花在哪。被 5 小時
限制/中斷後**重跑 drain 從剩下的接**（靠 lead status checkpoint）。drain 到 prepared 為止，**不入圖**。

### Step 4 — 今日決策佇列與到期 thesis

```powershell
python -m decision_lab today --format markdown
```

回今日 `NO ACTION / REVIEW / TRADE / HEDGE`，每個 probe 附**自追蹤變化%**與**evidence_delta**
（material=有觸及 thesis 因果結構的新證據 → 建議 reassess；peripheral=只多週邊 source；none=無變或
純價格波動）。再讀 `thesis/lifecycle.json` 列到期需複查的 thesis。純讀，不建 decision。

### Step 5 — 組 brief（繁中、exception-first、**穩定編號、無顏色**）

把 leads／決策佇列／等 apply 的 RA／到期 thesis／有 material evidence-delta 的 probe 聚成一份，
**跨 section 連續編號**（回覆用），每項附明確指令。無事就一行 `NO ACTION ＋日期`。

```
# Daily Brief <YYYY-MM-DD>

## 需要你動作
[1] REVIEW — co:coherent｜自追蹤 +3.2%｜證據 material  → 有新證據，reassess
[2] TRADE  — 等 apply ra_xxx（Tower TIA 客戶揭露 draft）  → 核准入圖：go 2
...

## 新 leads（依 priority，已 triage）
[3] go  AXTI 8-K ×3（一個月內密集）  → 深挖：go 3
[4] go  aleabitoreddit：Sivers CPO laser  → 深挖：go 4
...

## 低優先（摺疊）
EDGAR Form 4 ×55、較舊 filing——預設摺疊只列數量（要看再展開）

## 無事項目
paper 無異動｜live 無 pending fill｜...

---
回覆：`<編號…> go｜drop｜pending`（例：`3 4 go 5 drop`）
```

**不使用顏色維度**（顏色曾混淆 triage 與優先度）；改用明確指令字串。Form 4 與較舊 filing 一律進
「低優先（摺疊）」只列數量——冷啟動 EDGAR seed 偏 Form 4，別淹沒新訊號。

### Step 6 — 批次 dispatch（type-aware）

使用者回 `1 3 7 go 4 drop 5 6 pending`。用 deterministic parser 解析，不自由心證：

```powershell
python -c "from engine_b.batch import parse_batch_reply; import json,sys; print(json.dumps(parse_batch_reply(sys.argv[1])))" "1 3 7 go 4 drop 5 6 pending"
```

依編號對應的**項目類型** dispatch（type-aware；動詞不新增任何權限語意）：

| 動詞 | lead | 已 prepared 的 RA | 到期 thesis |
|------|------|-------------------|-------------|
| `go` | 進 pq1 深挖（drain/Fast Path） | **apply 入圖**（見下）＋入圖後自動建 Shadow | 引導 reassess/複查 |
| `drop` | park（`advance <lead> parked`／MCP） | 略過該 RA | 標記已看、不複查 |
| `pending` | 維持不動、留到之後 brief | 同左 | 同左 |

**go 一個 prepared RA ＝入圖**：走既有 `apply_research_action`（本機或 MCP native approval，一次確認）
→ `advance <lead> applied --ref focus_company_id=co:x` → **入圖後自動建 Shadow 追蹤**：

```powershell
python -m decision_lab evaluate-signal "入圖後自動追蹤 co:x" --company-id co:x --ticker <T> --intent research
```

（或程式內 `decision_lab.ensure_shadow_for_company`；已有 probe 則不重複建、改走 evidence-delta。）
本機入圖後跑 `scripts/commit_pending_intake.py` 補 provenance 帳本。**live 決策（record-choice／
record-fill）不在批次動詞集合**——永遠本機明確 flags，不得由 recommendation 推定 choice、choice 推定
fill。系統不連 broker。

### Step 7 — 收尾同步

- **本機**：leads 狀態變更後 push（`git ls-files library/private` 應空；leads.json 可 push）；入圖帳本
  `scripts/commit_pending_intake.py`。
- **雲端 chat**：`record_lead_decision` 已由本機 MCP server 窄 pathset commit+push leads.json，cloud 隔天讀到。

---

## 與 cloud routine 的分工

`crons/daily_brief_prompt.md`（每日）先產 brief（心跳、必完成）→ best-effort drain pq1 到 prepared。
cloud **只讀不寫圖/lifecycle**；leads 狀態經 MCP `record_lead_decision`（窄 pathset commit+push）。
weekly（`crons/weekly_scan_prompt.md`）＝健康檢查＋發現未知（horizon 掃描）＋唯讀 lifecycle 到期提醒。

## 已知會壞的地方（v0，撞到回頭修）

- priority 權重是拍腦袋 v0；用真實流量調（可重算所以能迭代）。
- 初期流量稀，brief 常一行 NO ACTION——來源清單問題，非管線問題。
- RSS feed 只曝露最新數篇；長期不開 session 舊文掉出視窗。
- evidence-delta 的 causal-path 精度可能太吵或太鈍，用真實入圖撞。
