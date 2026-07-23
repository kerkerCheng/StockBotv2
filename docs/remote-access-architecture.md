# 遠端存取架構 — 資料流與安全邊界

> 2026-07-11 建立（U7a/U7d），2026-07-16 更新為 server-owned Research Action。這份是活文件：任何改動 tunnel、MCP server、connector 的人都應同步更新。
> 相關計畫：[`docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md`](plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md) 的 U7a/U7d。

## 一句話

**知識圖譜（Neo4j）留在本機常開機器上，透過 Cloudflare Tunnel + 自建 MCP server，讓手機 App、網頁對話、cloud routine 都能安全地讀圖／經核准後寫圖。**

---

## 本機常駐的三個行程

| 行程 | 角色 | 網路姿態 |
|------|------|---------|
| Neo4j | 圖資料庫本體 | 只聽 localhost 7474（HTTP）/ 7687（Bolt），無對外 |
| cloudflared | Cloudflare Tunnel 客戶端 | **向外撥出**長連線到 Cloudflare；本機零入站埠、路由器零設定 |
| `mcp_server/graph_mcp.py` | 自建 Graph MCP server | 只綁 127.0.0.1:8788，唯一入口是 tunnel 轉進來的流量 |

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

MCP（Model Context Protocol）是開放協議，標準化支援它的模型介面如何呼叫自家工具。分工：

```
你的手機/瀏覽器  = 顯示對話的窗口（無 LLM）
Claude／OpenAI 雲端 = LLM 本體——思考、決定何時呼叫工具
本機 graph_mcp   = 純執行器（無 LLM、不需 ANTHROPIC_API_KEY、零 API 成本）
本機 Neo4j       = 資料
```

對話中的實際流程：使用者提問 → 雲端 LLM 判斷需要圖譜 → 發 JSON-RPC 工具呼叫（HTTPS）→ `mcp.minatoyukina.uk` → Cloudflare → tunnel → cloudflared → graph_mcp → Neo4j → 結果原路回 → LLM 讀進上下文後以自然語言回答。

**MCP server 不能對本機下任意指令。** 它只有十個寫死的工具（見下），沒有 shell、沒有 client-controlled path、沒有任意代碼執行。檔案只可落在固定 action/provenance/report roots；遠端工具完全沒有 Git 能力。要擴充能力必須改 code 重啟並讓 connector 重新掃描工具。

---

## 十個工具與其應用

| 工具 | 讀/寫 | 應用場景 |
|------|------|---------|
| `get_graph_context` | 讀 | 「SIVE 研究狀態如何」——公司子圖/產業全圖的 LLM-ready 摘要（重用 `query/graph_context.py`） |
| `run_read_query` | 讀 | 精確查詢/稽核：「列出所有 sole_source 邊」「數 origin_entity」。Session 以 READ access mode 開啟，寫入語句會被 Neo4j 拒絕（已實測） |
| `get_financial_checklist` | 讀 | 查 Engine C 五項財務清單、最新客觀 analyst coverage 與當前 `policy_version` 的即時 view；不暴露 SQL、不持久化 crowding 分類 |
| `get_decision_brief` | 讀 | 「今天需要動作嗎」——回 `decision_lab today` 的 redacted public DTO（九欄 action-first）。Decision Store 是本機 private runtime、永不進 git，這是手機／雲端看決策佇列的唯一視窗；純讀，不 freeze／不建 decision／不下單，runtime 未就緒回明確 `unavailable`、不洩私有路徑 |
| `get_extraction_rules` | 讀 | 回傳 `prompts/extract_system.md` + `schema/vocab.json` + `prompts/intake_protocol.md` 原文（路徑寫死）。**任何遠端抽取前必讀**——含 storage permission、conflict 與 Research Action 協定 |
| `get_source_trace_manual` | 讀 | 回傳 `skills/source-trace/SKILL.md` 原文。手機／網頁收到推文、轉述、截圖或未驗證消息時先讀，依市場路由追原文；tier 3–4 未果只留 lead，不進抽取／寫圖 |
| `load_extraction` | **寫** | legacy weekly/local primitive：一份文件一呼叫。驗 permission/schema/canonical hash，filesystem-first no-clobber 保存 extraction/raw，再冪等寫圖與重投影 conflicts；手機 ad hoc flow 不直接使用 |
| `prepare_research_action` | **私有 staging 寫** | 驗證完整 1–10 文件 action，server 簽發 ID + digest + expiry + review packet；不寫 ledger、不寫圖、不跑 Git |
| `get_research_action_status` | 讀 | 空 ID 回 recent actionable 摘要；完整 ID 回 frozen review + recovery state；永不回 raw/extraction body |
| `apply_research_action` | **寫** | 以 ID + 完整 digest 套用使用者核准的 immutable action；逐文件 checkpoint、partial retry、permission-sensitive report；永不跑 Git |

**Connector 權限設定：** 七個 read tools 與 `prepare_research_action` 可設「允許」；`apply_research_action` 與 legacy `load_extraction` 保持「**Needs approval**」。工具權限不會自動繼承，新增／重建／Refresh connector 時逐一檢查。Claude mobile/web 可用同一 remote MCP；ChatGPT web 只有在帳號方案具 full MCP write 權限時能完成 apply。OpenAI 官方目前把 custom MCP apps 限在 web，ChatGPT mobile 不是手機入口。

---

## 安全邊界（分層）

1. **URL 路徑 token**（`.env` 的 `GRAPH_MCP_TOKEN`，40 字元隨機）——不知道完整 URL 連端點都碰不到（錯誤 token → 404）。**Connector URL 本身就是鑰匙：含 URL 的截圖/設定頁不要外流**
2. **最小權限 Neo4j 帳號**——MCP server 用 `cloud_routine` 帳號（`routine_writer` 角色：MATCH + CREATE + SET PROPERTY + SET LABEL；無 DELETE、無 schema、無 admin）。最壞情況是圖被亂寫，不是被刪
3. **READ mode 強制**——`run_read_query` 在 session 層面拒絕寫入交易
4. **Server-owned approval artifact**——prepare 對完整 normalized payload 算 SHA-256 digest；apply 必須帶 action ID + 完整 digest，任何 stale／tampered／expired payload 在新 graph mutation 前拒絕
5. **驗證與 no-clobber 閘門**——prepare/apply 共用 schema/permission/URL/canonical hash gate；內容衝突不碰圖、不覆寫檔案
6. **容量、生命週期與敏感資料邊界**——單 action 5 MiB／10 文件、最多 50 個非終態 action／100 MiB staging、ready 30 天過期；status list 不回 report prose，所有 status 都不回 raw/extraction body
7. **人工核准 + idempotent checkpoint**——`apply_research_action` 設 Needs-approval；每份圖完成後留下 exact extraction hash receipt，response loss／partial failure 用同 ID + digest 續跑
8. **遠端無 Git**——MCP enumeration 沒有 finalize／commit／push；Git credential 不在 path bearer 的 blast radius。本機 publisher 才驗 master、空 index、ancestry、action trailer 與 exact pathset
9. **本機綁定**——MCP server 只綁 127.0.0.1，唯一入口是 tunnel

> **殘餘安全邊界：** digest 是 integrity，不是 authentication；Needs approval 是 client UX，不是 server auth。持有完整 MCP bearer URL 的直接呼叫者仍位於既有 graph-write 信任邊界內，可準備／載入錯誤資料，但拿不到 Git 能力。OAuth 2.1、短效且 audience-bound token 仍是後續安全升級；現階段先以最小 Neo4j 權限、路徑 token、action quota 與無 remote Git 壓低 blast radius。

遠端 MCP 目前定位為「查研究資料、看今日決策、載入已核准證據」；部位 sizing 的**執行**與 paper-portfolio append 仍不暴露成遠端寫入工具。手機／網頁端可讀 `get_financial_checklist` 與 `get_decision_brief`（今日決策佇列的 redacted DTO），但 `record-choice`／`record-fill` 等決策寫入永遠只在本機以明確輸入執行——遠端能看建議，不能替使用者接受 choice 或回報 fill。

Token 或 Neo4j 密碼要輪換時：改 `.env` → 重啟 MCP server → 到 claude.ai 更新 connector URL。

第一次部署或新增 SourceDoc 欄位後，須由 admin 重跑 `schema/neo4j_setup.cypher`。setup 會建立後立即刪除 sentinel，預註冊 `storage_permission`／`permission_basis` property-name tokens；`cloud_routine` 不需要、也不應取得 `CREATE NEW PROPERTY NAME` 權限。

setup 最後也會寫入 `GraphSchemaState.version=2026-07-16-u3b`。`load_extraction`／Research Action apply 在每次圖寫入前會用 routine 帳號讀取該版本，並確認沒有未投影 canonical edge、legacy 無 `edge_key` domain edge、或缺 `CITES` 的 Claim／EdgeAssertion；不通過時只留下可重試的 `pending_graph` provenance，不會把 action 標成 applied。

---

## 資料流範例

**讀（例：「SIVE 的 thesis 還缺什麼？」）**
→ 雲端 LLM 呼叫 `get_graph_context` → 本機被查詢幾個唯讀 Cypher → 圖無任何變動。

**讀財務（例：「SIVE 財務清單」）**
→ `get_financial_checklist("SIVE.ST")` → 本機 Engine C 回五項清單與原始覆蓋數 → 查詢層套當前 policy；DB 無任何變動。

**寫（例：手機上入圖）**
→ 貼新聞給 App → `get_source_trace_manual` 追原文 → `get_extraction_rules` 讀 storage/action 協定 → session 完成 research + 多文件 extraction + structured report → `prepare_research_action` 驗證並凍結 → App 顯示 exact review packet、停下來討論 → 使用者明確核准該 action ID → `apply_research_action` 觸發一次 native approval → server 鎖 digest、逐文件 filesystem-first／graph checkpoint、產 permission-safe report → 回 `applied` 或可續跑的 `partial`。全程不碰 Git。

**本機補帳（例：週末開 Codex）**
→ 說「補提交入圖」→ `python scripts/commit_pending_intake.py --dry-run` → 驗 master／空 index／origin ancestry → 每 action 一個 exact-path commit（ID + digest trailers）→ 整批一次 push。push 失敗保留 commits；下次由 ancestry + trailers 復原，不會掃入無關 working-tree files。

**清理過期草稿**
→ `python scripts/commit_pending_intake.py --cleanup-expired` → 只壓縮已過 30 天且從未套用的 private action payload；不碰圖與 Git。

**不碰本機（例：「CPO 最近有什麼新聞？」）**
→ 純 web search，全程雲端，本機三個行程無感。

**核心規律：研究／抽取 = session model；核准物 = server-owned immutable action；入圖 = 一次人工核准 + filesystem-first + 冪等 checkpoint；Git = 只在可信本機 session 延後批次發布。**

---

## 各介面拿 codebase 的方式（易混淆點）

| 介面 | codebase 存取 | 圖譜存取 |
|------|--------------|---------|
| 本機 Claude Code session | 本來就在 repo 裡 | 直連 localhost |
| 本機 Codex session | 本來就在 repo 裡 | 直連 localhost／讀 private action files |
| Cloud routine（U7） | GitHub 連接後每次執行 **clone 整份 repo**（走 GitHub，不走 tunnel） | MCP connector |
| Claude 手機／網頁 App 對話 | **刻意不給**（只由 rule/status tools 回傳必要規則與 action packet） | MCP connector |
| ChatGPT web（full MCP 方案） | **刻意不給** | 同一 remote MCP app；tool snapshot 更新後需 Refresh |
| ChatGPT mobile | 不適用 | OpenAI 目前不支援 custom MCP apps on mobile |

---

## 已知限制與踩坑記錄

- **Pro 方案的 cloud routine sandbox 出站網路不可自訂**（U7a 四次實測：Trusted 403、Additional allowed domains 無效、All domains 無效）。claude.ai Capabilities 的網路設定只管聊天 code-execution 沙盒，管不到 routine。這是走 MCP 路線的原因
- MCP SDK 的 DNS-rebinding 防護會對非 localhost 的 Host 回 421 → tunnel ingress 用 `httpHostHeader` 改寫解決
- cloudflared 預設日誌不記錄個別請求；驗證流量用本機 metrics 端點 `127.0.0.1:20241/metrics` 的 `cloudflared_tunnel_total_requests` 計數器
- 無 watchdog：行程若 crash 不會自動重啟（開機自啟只在登入時跑一次）。目前接受此風險
- Neo4j Python driver 的 write result 是 lazy：loader 必須 `consume()` 才能在 MCP 呼叫內暴露權限／commit 錯誤；`tests/test_sourcedoc.py` 固定此行為
- [OpenAI 官方目前說明](https://help.openai.com/en/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta)：ChatGPT custom MCP apps 是 web-only；full write MCP 方案與 UI 仍在 beta。這不影響 action artifact 的 provider-neutral 設計，但手機前門現階段仍是 Claude App
- ChatGPT workspace 會保存已核准 tool schema 的 frozen snapshot；server 新增／修改工具後必須由 admin Refresh actions（或依方案重建 app），否則 call 可能因 schema drift 失敗
