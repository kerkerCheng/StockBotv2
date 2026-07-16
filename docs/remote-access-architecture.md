# 遠端存取架構 — 資料流與安全邊界

> 2026-07-11 建立（U7a/U7d）。這份是活文件：任何改動 tunnel、MCP server、connector 的人都應同步更新。
> 相關計畫：[`docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md`](plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md) 的 U7a/U7d。

## 一句話

**知識圖譜（Neo4j）留在本機常開機器上，透過 Cloudflare Tunnel + 自建 MCP server，讓手機 App、網頁對話、cloud routine 都能安全地讀圖／經核准後寫圖。**

---

## 本機常駐的三個行程

| 行程 | 角色 | 網路姿態 |
|------|------|---------|
| Neo4j | 圖資料庫本體 | 只聽 localhost 7474（HTTP）/ 7687（Bolt），無對外 |
| cloudflared | Cloudflare Tunnel 客戶端 | **向外撥出**長連線到 Cloudflare；本機零入站埠、路由器零設定 |
| `mcp_server/graph_mcp.py` | 自建 MCP server（約 200 行 Python） | 只綁 127.0.0.1:8788，唯一入口是 tunnel 轉進來的流量 |

**開機自動啟動：** `shell:startup`（`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`）裡的 `stockbotv2-graph-services.vbs` 會在登入時以隱藏視窗啟動 **Neo4j + cloudflared + MCP server** 三者。刪除該檔即停用。手動重啟：直接雙擊該 `.vbs`。

Neo4j 的啟動細節：使用者的 Neo4j 是 **Desktop 2 附帶的 Enterprise 版**（最小權限帳號的 RBAC 依賴 Enterprise，**不可換成 Community zip**）。啟動不開 Desktop GUI，而是由 `C:\Users\Cheng\.Neo4jDesktop2\start-dbms-headless.cmd` 直接對 Desktop 管理的 DBMS 跑 `neo4j console`（JAVA_HOME 以萬用字元自動抓 Desktop 快取的最新 zulu JRE，Desktop 更新 runtime 不會斷）。若 DBMS 已在跑（例如 Desktop 先開了），重複啟動會因 port 佔用自然退出，無害。

---

## Tunnel 是什麼（為什麼不用 port forwarding）

家用電腦在路由器/防火牆後面，外部無法主動連入——這是預設安全姿態。Tunnel 把方向反過來：**cloudflared 從本機主動向外撥一條長連線到 Cloudflare 並保持不斷**（出站流量永遠是通的）。外部要連 `*.minatoyukina.uk` 時，DNS 指向 Cloudflare（不是家用 IP），Cloudflare 沿著那條已建立的連線把請求送回來。

比喻：先打電話給總機不掛斷；別人找你都打給總機，由總機沿已接通的線轉接。**外界自始至終不知道你的號碼（家用 IP），你家也從沒開放任何入站。**

Hostname 映射（`C:\Users\Cheng\.cloudflared\config.yml`）：

| Hostname | 轉給 | 備註 |
|----------|------|------|
| `neo4j.minatoyukina.uk` | localhost:7474 | Neo4j HTTP Query API（U7a 驗證用，日常不對外使用） |
| `mcp.minatoyukina.uk` | localhost:8788 | MCP server；ingress 有 `httpHostHeader: 127.0.0.1:8788` 改寫（MCP SDK 的 DNS-rebinding 防護只認 localhost Host，不改寫會回 421） |
| 其他任何 hostname | 404 | |

網域 `minatoyukina.uk` 註冊於 Cloudflare（2026-07-11），DNS 由 Cloudflare 管理。子網域 CNAME 由 `cloudflared tunnel route dns` 建立（授權憑證在 `C:\Users\Cheng\.cloudflared\cert.pem`，來自一次性的 `cloudflared tunnel login`）。

---

## MCP 是什麼、LLM 跑在哪

MCP（Model Context Protocol）= Anthropic 制定的開放協議，標準化「Claude 如何呼叫你自家的工具」。分工：

```
你的手機/瀏覽器  = 顯示對話的窗口（無 LLM）
Anthropic 雲端   = LLM 本體——思考、決定何時呼叫工具
本機 graph_mcp   = 純執行器（無 LLM、不需 ANTHROPIC_API_KEY、零 API 成本）
本機 Neo4j       = 資料
```

對話中的實際流程：使用者提問 → 雲端 LLM 判斷需要圖譜 → 發 JSON-RPC 工具呼叫（HTTPS）→ `mcp.minatoyukina.uk` → Cloudflare → tunnel → cloudflared → graph_mcp → Neo4j → 結果原路回 → LLM 讀進上下文後以自然語言回答。

**MCP server 不能對本機下任意指令。** 它只有七個寫死的工具（見下），沒有 shell、沒有 client-controlled path、沒有任意代碼執行。檔案只可落在固定 provenance/report roots，Git 只用 argv-list 精確 pathspec。要擴充能力必須改 code 重啟。

---

## 七個工具與其應用

| 工具 | 讀/寫 | 應用場景 |
|------|------|---------|
| `get_graph_context` | 讀 | 「SIVE 研究狀態如何」——公司子圖/產業全圖的 LLM-ready 摘要（重用 `query/graph_context.py`） |
| `run_read_query` | 讀 | 精確查詢/稽核：「列出所有 sole_source 邊」「數 origin_entity」。Session 以 READ access mode 開啟，寫入語句會被 Neo4j 拒絕（已實測） |
| `get_financial_checklist` | 讀 | 查 Engine C 五項財務清單、最新客觀 analyst coverage 與當前 `policy_version` 的即時 view；不暴露 SQL、不持久化 crowding 分類 |
| `get_extraction_rules` | 讀 | 回傳 `prompts/extract_system.md` + `schema/vocab.json` + `prompts/intake_protocol.md` 原文（路徑寫死）。**任何遠端抽取前必讀**——含 storage permission、conflict 與 finalize 協定 |
| `get_source_trace_manual` | 讀 | 回傳 `skills/source-trace/SKILL.md` 原文。手機／網頁收到推文、轉述、截圖或未驗證消息時先讀，依市場路由追原文；tier 3–4 未果只留 lead，不進抽取／寫圖 |
| `load_extraction` | **寫** | 一份文件一呼叫。驗 permission/schema/canonical hash，filesystem-first no-clobber 保存 extraction/raw，再冪等寫圖與重投影受影響 conflicts；失敗可用相同 payload 重試 |
| `finalize_research_action` | **寫 + Git push** | 以成功 load 的 doc_ids manifest 建報告、精確 stage、單一 commit、push。非 master／staged index／HEAD 不同步／local_only 全部 fail closed；預設 kill switch 關閉 |

**Connector 權限設定（claude.ai → Settings → Connectors → stockbotv2-graph）：** 五個讀工具設「允許」；`load_extraction` 與 `finalize_research_action` 都保持「**Needs approval**」。後者不會繼承前者的設定，新增／重建 connector 時必須逐一檢查。

---

## 安全邊界（分層）

1. **URL 路徑 token**（`.env` 的 `GRAPH_MCP_TOKEN`，40 字元隨機）——不知道完整 URL 連端點都碰不到（錯誤 token → 404）。**Connector URL 本身就是鑰匙：含 URL 的截圖/設定頁不要外流**
2. **最小權限 Neo4j 帳號**——MCP server 用 `cloud_routine` 帳號（`routine_writer` 角色：MATCH + CREATE + SET PROPERTY + SET LABEL；無 DELETE、無 schema、無 admin）。最壞情況是圖被亂寫，不是被刪
3. **READ mode 強制**——`run_read_query` 在 session 層面拒絕寫入交易
4. **驗證與 no-clobber 閘門**——`load_extraction` 先驗 schema/permission/URL/canonical hash，內容衝突不碰圖、不覆寫檔案
5. **Finalize fail-closed**——只在 master、index 無 staged、fetch 成功且 `HEAD == origin/master` 時，精確提交本次 manifest
6. **人工核准 + server kill switch**——兩個寫工具設 Needs-approval；Git push 另要求 `ENABLE_REMOTE_FINALIZE=true`，預設 false
7. **本機綁定**——MCP server 只綁 127.0.0.1，唯一入口是 tunnel

> **尚未解除的 P0：** `ENABLE_REMOTE_FINALIZE=false` 仍是部署預設，原因不只一項：Needs-approval 是 client-side UX，持有完整 MCP bearer URL 的直接呼叫者可繞過；`doc_ids` 由 client/session 累積，server 尚未簽發一次性 action receipt，因此久置 session 可能帶入過期 action state；`report_markdown` 仍是 client 組成的自由文字，server 能驗證 manifest，卻無法證明其中沒有轉述 `local_only` 內容；push 失敗後也尚無窄化的遠端 retry primitive。啟用前應改成 server-owned action ID + 一次性 capability、server-rendered structured report，以及只允許既有 commit 的 ancestry/pathspec 驗證後重推。未完成前，不把這個工具開給遠端使用。

遠端 MCP 目前定位為「查研究資料、載入已核准證據」；部位 sizing 與 paper-portfolio append 尚未暴露成遠端工具。本機 Claude/Codex 可直接呼叫 Python 模組，手機／網頁端只能讀 `get_financial_checklist`，不能假裝已執行完整政策或模擬交易流程。

Token 或 Neo4j 密碼要輪換時：改 `.env` → 重啟 MCP server → 到 claude.ai 更新 connector URL。

第一次部署或新增 SourceDoc 欄位後，須由 admin 重跑 `schema/neo4j_setup.cypher`。setup 會建立後立即刪除 sentinel，預註冊 `storage_permission`／`permission_basis` property-name tokens；`cloud_routine` 不需要、也不應取得 `CREATE NEW PROPERTY NAME` 權限。

setup 最後也會寫入 `GraphSchemaState.version=2026-07-16-u3b`。`load_extraction` 在每次圖寫入前會用 routine 帳號讀取該版本，並確認沒有未投影 canonical edge、legacy 無 `edge_key` domain edge、或缺 `CITES` 的 Claim／EdgeAssertion；不通過時只留下可重試的 `pending_graph` provenance，不會繼續寫圖或取得 finalize receipt。

---

## 資料流範例

**讀（例：「SIVE 的 thesis 還缺什麼？」）**
→ 雲端 LLM 呼叫 `get_graph_context` → 本機被查詢幾個唯讀 Cypher → 圖無任何變動。

**讀財務（例：「SIVE 財務清單」）**
→ `get_financial_checklist("SIVE.ST")` → 本機 Engine C 回五項清單與原始覆蓋數 → 查詢層套當前 policy；DB 無任何變動。

**寫（例：手機上入圖）**
→ 貼新聞給 App → `get_source_trace_manual` 追原文 → `get_extraction_rules` 讀 storage/intake 協定 → 一份文件一次 `load_extraction` → App 核准 → 本機先 no-clobber 保存 provenance，再寫圖／project conflict → 累積成功且 eligible 的 doc_ids → 行動結束一次 `finalize_research_action` → 再次 App 核准 → preflight → 報告 + 單一 commit + push。任一步失敗都回 pending／not_committed，不假裝完成。

**不碰本機（例：「CPO 最近有什麼新聞？」）**
→ 純 web search，全程雲端，本機三個行程無感。

**核心規律：讀圖 = 無副作用；載入 = 人工核准 + filesystem-first + 自動驗證；Git 收尾 = 另一個人工核准 + server kill switch + 同步 preflight。**

---

## 各介面拿 codebase 的方式（易混淆點）

| 介面 | codebase 存取 | 圖譜存取 |
|------|--------------|---------|
| 本機 Claude Code session | 本來就在 repo 裡 | 直連 localhost |
| Cloud routine（U7） | GitHub 連接後每次執行 **clone 整份 repo**（走 GitHub，不走 tunnel） | MCP connector |
| 手機/網頁 App 對話 | **刻意不給**（只由 `get_source_trace_manual`／`get_extraction_rules` 回傳寫死的規則檔） | MCP connector |

---

## 已知限制與踩坑記錄

- **Pro 方案的 cloud routine sandbox 出站網路不可自訂**（U7a 四次實測：Trusted 403、Additional allowed domains 無效、All domains 無效）。claude.ai Capabilities 的網路設定只管聊天 code-execution 沙盒，管不到 routine。這是走 MCP 路線的原因
- MCP SDK 的 DNS-rebinding 防護會對非 localhost 的 Host 回 421 → tunnel ingress 用 `httpHostHeader` 改寫解決
- cloudflared 預設日誌不記錄個別請求；驗證流量用本機 metrics 端點 `127.0.0.1:20241/metrics` 的 `cloudflared_tunnel_total_requests` 計數器
- 無 watchdog：行程若 crash 不會自動重啟（開機自啟只在登入時跑一次）。目前接受此風險
- Neo4j Python driver 的 write result 是 lazy：loader 必須 `consume()` 才能在 MCP 呼叫內暴露權限／commit 錯誤；`tests/test_sourcedoc.py` 固定此行為
