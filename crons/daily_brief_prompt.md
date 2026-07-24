# Daily Approval Brief — Cloud Routine Prompt（v1.1）

> 這份 prompt 由 claude.ai 的 cloud routine 每日觸發執行（台北時間 06:30，錯開週掃 06:00）。
> 執行環境是 Anthropic 雲端沙盒：有整份 repo 的 **pushed clone**、有 web search、有
> `stockbotv2-graph` MCP connector。**連不到使用者本機檔案／Engine C／Decision Store**——
> 決策佇列走 MCP `get_decision_brief`；leads 讀 `get_pending_leads`、改狀態用
> `record_lead_decision`（本機 MCP server 幫忙窄 pathset commit+push）。
> **不使用 GitHub Issue/PR。** 本 routine 的輸出（brief）直接呈現在 Claude app，推播給使用者；
> 使用者在同一 thread 用批次語法回覆。設計出處：`docs/plans/2026-07-24-001-...-v1-1-plan.md`。

## 定位（先讀這段）

每日**心跳＋聚合＋best-effort 研究 drain**。先產一份 action-first brief（心跳，必完成），
再用剩餘預算 best-effort drain pq1（研究）到「等你核准」為止。

**鐵律（KTD1/KTD3/KTD4）：cloud 只讀不寫圖/lifecycle。** 不建 decision、不下單、不入圖、不改
`thesis/lifecycle.json`。leads 狀態變更**只**經 MCP `record_lead_decision`（窄 pathset）。入圖
（apply）與 live 決策永遠是使用者的人工 gate。

## 執行流程

### Stage 0 — 前置與降級

1. 讀 clone 的 `crons/harvest_config.json` 與 `library/leads/pending_leads.json` baseline（去重用）
2. 讀 `skills/signal-triage/SKILL.md`（triage 判準）
3. 呼叫 MCP `get_decision_brief` 確認連線；**連不上不卡住**——決策佇列段標「MCP 不可用、今日降級」，
   leads／harvest／lifecycle 照常

### Stage 1 — Harvest（web；雲端受 egress 限制，預設走 WebSearch）

> **已知環境限制（2026-07-24 實測）：** Anthropic 雲端沙盒直連 `aleabitoreddit.substack.com` 與
> `www.sec.gov` 會被 **proxy 403（policy denial）**，`crons/harvest_leads.py` 與 `WebFetch` 在雲端都
>跑不動。**不要重試直連**（policy denial 重試無用、只燒時間）——直接用 `WebSearch` fallback，並在
> brief 標明「harvest 走 fallback、覆蓋不完整」。完整覆蓋由使用者本機執行 harvest 補上。

用 `WebSearch` 掃 config 內來源的近期新項（如 `site:aleabitoreddit.substack.com`、watch 清單各
ticker 的新 filing 公告）；與 baseline 去重，只留今日新增。**不得因覆蓋不完整就假裝窮盡**——
brief 要明說哪些來源沒查到、本機補跑什麼命令。

### Stage 2 — Triage（照 signal-triage，寫回經 MCP）

對今日新增材料跑五要素判斷。go/no-go 用 MCP `record_lead_decision`（op=triage，帶 tier、reason 與
priority flags：contradiction/novelty/independent_source）寫回——本機 MCP server 會窄 pathset
commit+push leads.json，使用者本機隔天讀到最新。**公司 ID 不憑名猜**（查 clone registry / 圖）。

### Stage 3 — 決策佇列（MCP，唯讀）

- `get_decision_brief` → 今日 `NO ACTION / REVIEW / TRADE / HEDGE`，每個 probe 附**自追蹤變化%**與
  **evidence_delta**（material=觸及 thesis 因果結構的新證據 → 建議 reassess；peripheral／none）
- `get_research_action_status`（空 ID）→ 等 apply 的 Research Actions（pq2）
- 一般價格波動不得當 thesis disproof；`NO ACTION` 是正式結果

### Stage 4 — pq1 drain（best-effort，心跳之後）

**brief 產出後**，用剩餘預算 drain pq1：讀 `get_pending_leads`（priority 排序）取最高分的 triaged_go，
逐則跑 source-trace＋extraction，經 MCP `prepare_research_action` 產出 prepared RA，並用
`record_lead_decision`（op=advance）逐則 checkpoint（researching→action_prepared）。**被限制打斷就停，
下次從剩下的接**（靠 lead status）。drain **到 prepared 為止，不入圖**。別讓 drain 挾持心跳——brief 一定先完成。

### Stage 5 — 到期 thesis（唯讀 surface）

讀 clone 的 `thesis/lifecycle.json`，列到期（next_check<=今天 或 review_required）的 thesis，附輕量
disproof web 掃描發現。**不改 lifecycle.json**——正式狀態更新由使用者本機手動（見分工）。

### Stage 6 — 產出 brief（Claude app，穩定編號、批次語法）

把上述聚成一份 action-first brief 作為**本 routine 的輸出**（呈現在 Claude app、推播）。**跨 section
連續編號**、每項附明確指令、**不用顏色**、Form 4／舊 filing 摺疊只列數量。結尾附批次語法說明：

```
# Daily Brief <YYYY-MM-DD>

## 需要你動作
[1] REVIEW — co:x｜自追蹤 +X%｜證據 material  → 有新證據，reassess
[2] TRADE  — 等 apply ra_xxx  → 核准入圖：go 2
## 新 leads（依 priority）
[3] go  <lead 摘要>  → 深挖：go 3
## 低優先（摺疊）
EDGAR Form 4 ×N、舊 filing
## 無事項目
...

回覆：`<編號…> go｜drop｜pending`（例：`1 2 go 3 drop`）——go 對 lead=深挖、對 prepared=入圖；
決策/live 動作請本機執行。
```

**心跳＝每日輸出。** 使用者在此 thread 接續回批次語法即可操作（thread 帶 MCP+web）。找不到值得說的
事 → 照樣輸出一行 `NO ACTION ＋日期`（心跳不能斷）。

## 與本機 /daily-brief 及 weekly 的分工

- **本機 `/daily-brief` skill**：使用者本機以 URL-hash 冪等重跑、批次 dispatch、入圖 apply＋
  `commit_pending_intake`、live 決策；是圖與 Git provenance 帳本的寫入端。
- **Weekly**（`crons/weekly_scan_prompt.md`）：健康檢查＋發現未知（horizon 掃描）＋**唯讀** lifecycle
  到期提醒。lifecycle 正式狀態更新由使用者本機手動（cloud/weekly 都不寫）。

## 鐵律

- 繁體中文輸出
- cloud 只讀不寫圖/lifecycle；leads 狀態只經 MCP `record_lead_decision`（窄 pathset）
- 入圖（apply）與 live 決策（record-choice/fill）永遠人工、只在本機以明確輸入
- MCP 連不上只降級決策佇列；leads／harvest／lifecycle 照常並標明降級
- brief 先於 pq1 drain 完成（心跳可靠），drain best-effort、可續跑

## 上線 checklist（人工）

1. push 現有 master backlog（routine 讀 pushed clone）
2. 在 claude.ai 建 daily routine，貼本 prompt，排台北 06:30，確認輸出推播到 app
3. 連續數天 bake：撞 priority 權重、drain 節奏、evidence-delta 精度、批次語法手感；摩擦點回寫 plan
