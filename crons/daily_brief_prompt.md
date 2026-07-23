# Daily Approval Brief — Cloud Routine Prompt

> 這份 prompt 由 claude.ai 的 cloud routine 每日觸發執行（台北時間 06:30，錯開週掃 06:00）。
> 執行環境是 Anthropic 雲端沙盒：有整份 repo 的 **pushed clone**、有 web search、有
> `stockbotv2-graph` MCP connector。**連不到使用者本機檔案／Engine C／Decision Store**——
> 決策佇列一律走 MCP 工具 `get_decision_brief`；leads baseline／config／lifecycle 讀 clone。
> 設計出處：`docs/plans/2026-07-22-002-feat-daily-approval-loop-plan.md`（U5）。

## 定位（先讀這段）

本 routine 是**每日心跳與聚合**，不是研究、也不是狀態寫入。它把四件事聚合成一份
action-first 的 GitHub Issue，讓使用者一眼看到「今天要不要動作」：

1. **新 leads**（harvest＋triage，只在 Issue 呈現）
2. **今日決策佇列**（MCP `get_decision_brief`）
3. **等 apply 的 Research Actions**（MCP `get_research_action_status`）
4. **到期 thesis**（讀 clone 的 `thesis/lifecycle.json`，唯讀 surface）

**鐵律（KTD1／KTD4）：cloud 只讀不寫。** 本 routine 不回寫 `pending_leads.json`、不改
`thesis/lifecycle.json`、不建 decision、不下單、不入圖、不 commit／push。所有狀態變更
（leads triage 落地、lifecycle 更新、入庫）都在使用者本機 `/daily-brief` skill 或明確
動作時發生。Issue 是 view，本機檔案／Decision Store 才是 state。

## 執行流程

### Stage 0 — 前置與降級判定

1. 讀 clone 的 `crons/harvest_config.json`（feeds＋edgar_watch）與 `library/leads/pending_leads.json`
   baseline（使用者上次 push 的狀態；用來去重，只呈現 baseline 沒有的新項）
2. 讀 `skills/signal-triage/SKILL.md`——triage 判準全在裡面
3. 呼叫 MCP `get_decision_brief` 確認連線；**連不上不要卡住**——決策佇列段標「MCP 不可用、
   決策佇列今日降級」，其餘（leads／RA／lifecycle）照常從 clone／web 產出

### Stage 1 — Harvest（web，零 token）

- **RSS**：抓 config 內每個 feed（如 `https://aleabitoreddit.substack.com/feed`，channel
  標題是 "Serenity"）。**解析失敗 ≠ 無新文**：失敗時退回 `site:<domain>` web search，
  並在 Issue 註明用了 fallback
- **EDGAR watch**：對 config 的 tickers 查有無新 filing（8-K／10-K／10-Q／Form 4）；只記
  metadata（form／日期／URL），不下載全文
- 與 baseline 去重（URL-hash）；只有 baseline 沒有的才算「今日新增」

### Stage 2 — Triage（照 signal-triage skill，只呈現不寫回）

對每則今日新增材料跑五要素判斷（關聯性、新穎性、可引用性、潛在新 origin_entity、
矛盾／反證）。新穎性用 MCP `get_graph_context`／`run_read_query` 比對圖（連不上就寬鬆放行
並註明）。**公司 ID 不憑名猜**（先查 clone 的 registry／`COMPANY_IDS_CYPHER`）。go／no-go
與理由只寫進 Issue——**不呼叫任何寫入、不回寫 pending_leads.json**（單一寫入者是本機）。
no-go 也要列出理由。

### Stage 3 — 決策佇列（MCP，唯讀）

- `get_decision_brief` → 今日 `NO ACTION / REVIEW / TRADE / HEDGE` 與九欄 DTO（含
  Sheet-only／legacy holding 反向比對）
- `get_research_action_status`（空 ID）→ 列等 apply 的 Research Actions
- 一般波動不得當 thesis disproof；`NO ACTION` 是正式結果

### Stage 4 — 到期 thesis（唯讀 surface）

讀 clone 的 `thesis/lifecycle.json`，列出到期需核查的 thesis（`next_check` <= 今天，或
`status = review_required`）。對到期者可做一次**輕量** disproof leading-indicator web
search，把發現寫進 Issue；`review_required` 觸發跡象在 Issue 開頭標 ⛔。
**不改 lifecycle.json**——正式的狀態更新（`last_checked`／`next_check`／`status`）由 weekly
scan 的 PR 或使用者本機處理（見下方分工）。

### Stage 5 — 組當日 Issue（心跳）

開一個 GitHub Issue，**title 含日期**（`Daily Brief <YYYY-MM-DD>`）、label `daily-brief`。
版面 exception-first、繁中：

```
# Daily Brief <YYYY-MM-DD>

## 今日新增（需要你判斷）
（今日新增 leads 的 triage go 項＋理由＋research 動詞；決策佇列 REVIEW／TRADE／HEDGE；
  等 apply 的 RA；到期 thesis —— 各附一句理由與可回覆動詞）

## Carry-over（第 N 天）
（前一日 Issue 未處理的項目，標第幾天；久未 push 的重複 leads 落這裡，不淹沒新料）

## 低優先（摺疊）
（EDGAR Form 4 與較舊 filing；no-go leads 一行數量）

## 無事項目
（一行帶過：thesis 無到期／paper 無異動／MCP 降級與否）

---
動詞（在本機 session 回覆）：research <n> ｜ apply <ra_id> ｜ park <n> ｜ skip
```

**心跳規則：** Issue 以日期命名——日期出現空洞＝routine 漏跑的可鑑證據，weekly scan 作
backstop。前一日 `daily-brief` Issue 若無人動作 → 自動 close，並在今日 Issue 的 Carry-over
段註記帶過（第 N 天）。

## 與本機 /daily-brief 及 weekly scan 的分工

- **本機 `/daily-brief` skill 才是寫入端**：使用者在本機以 URL-hash 冪等重新落地同批 leads、
  真正 triage 寫回、回動詞 dispatch（research／apply／park）、更新狀態並 commit＋push。
  雲端看得到、寫不進。
- **Weekly scan**（`crons/weekly_scan_prompt.md`）：topic discovery 深度聚類、系統健康審查、
  Stage 0 legacy PR gate，以及 **thesis lifecycle 的正式狀態更新**（PR 寫 `lifecycle.json`）。
  本 daily routine 只**唯讀 surface** 到期 thesis 供即時可見，不做正式更新。

## 鐵律

- 繁體中文輸出
- cloud 只讀不寫：不回寫 leads／lifecycle、不建 decision、不下單、不入庫、不 commit／push
- 決策命令（record-choice／record-fill）永遠只在本機；遠端只能唯讀看建議
- 找不到任何值得說的事 → Issue 照開一行 `NO ACTION ＋日期`（心跳不能斷）
- MCP 連不上只降級決策佇列；leads／RA／lifecycle 照常，並在 Issue 標明降級範圍

## 上線 checklist（人工步驟）

1. 先 push 現有 master backlog（routine 讀 pushed clone）
2. 在 claude.ai 建 daily routine，貼本 prompt，排程台北 06:30
3. 連續跑 3 天，每天把摩擦點記在當日 Issue 留言
4. 第 3 天把觀察彙整回寫 plan 的「上線觀察」節或 docs/solutions
