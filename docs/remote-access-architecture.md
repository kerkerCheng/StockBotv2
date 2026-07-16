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

**MCP server 不能對本機下任意指令。** 它只有五個寫死的工具（見下），沒有 shell、沒有任意檔案存取、沒有任意代碼執行。要擴充能力必須改 code 重啟。

---

## 五個工具與其應用

| 工具 | 讀/寫 | 應用場景 |
|------|------|---------|
| `get_graph_context` | 讀 | 「SIVE 研究狀態如何」——公司子圖/產業全圖的 LLM-ready 摘要（重用 `query/graph_context.py`） |
| `run_read_query` | 讀 | 精確查詢/稽核：「列出所有 sole_source 邊」「數 origin_entity」。Session 以 READ access mode 開啟，寫入語句會被 Neo4j 拒絕（已實測） |
| `get_extraction_rules` | 讀 | 回傳 `prompts/extract_system.md` + `schema/vocab.json` 原文（路徑寫死）。**任何遠端抽取前必讀**——軟品質規則（L6 逐字引用、L4 屬性歸位）無法靠事後驗證補救 |
| `get_source_trace_manual` | 讀 | 回傳 `skills/source-trace/SKILL.md` 原文。手機／網頁收到推文、轉述、截圖或未驗證消息時先讀，依市場路由追原文；tier 3–4 未果只留 lead，不進抽取／寫圖 |
| `load_extraction` | **寫** | 唯一寫入路徑。先跑 `loader/validate.py` 完整驗證（schema/vocab/參照完整性），通過才呼叫 `loader/load_to_neo4j.py` 寫入。爛資料進不了圖 |

**Connector 權限設定（claude.ai → Settings → Connectors → stockbotv2-graph）：** 四個讀工具設「允許」；`load_extraction` 保持「**Needs approval**」——每次寫圖 App 都會跳確認，**這就是 L8 人工核准閘門的 UI 實體**，不要改成自動允許。

---

## 安全邊界（分層）

1. **URL 路徑 token**（`.env` 的 `GRAPH_MCP_TOKEN`，40 字元隨機）——不知道完整 URL 連端點都碰不到（錯誤 token → 404）。**Connector URL 本身就是鑰匙：含 URL 的截圖/設定頁不要外流**
2. **最小權限 Neo4j 帳號**——MCP server 用 `cloud_routine` 帳號（`routine_writer` 角色：MATCH + CREATE + SET PROPERTY + SET LABEL；無 DELETE、無 schema、無 admin）。最壞情況是圖被亂寫，不是被刪
3. **READ mode 強制**——`run_read_query` 在 session 層面拒絕寫入交易
4. **驗證閘門**——`load_extraction` 內建 schema/vocab 驗證，拒載回傳錯誤清單
5. **人工核准**——connector 權限的 Needs-approval + 對話中的口頭確認，雙重
6. **本機綁定**——MCP server 只綁 127.0.0.1，唯一入口是 tunnel

Token 或 Neo4j 密碼要輪換時：改 `.env` → 重啟 MCP server → 到 claude.ai 更新 connector URL。

---

## 資料流範例

**讀（例：「SIVE 的 thesis 還缺什麼？」）**
→ 雲端 LLM 呼叫 `get_graph_context` → 本機被查詢幾個唯讀 Cypher → 圖無任何變動。

**寫（例：手機上入圖）**
→ 貼新聞給 App → LLM 呼叫 `get_source_trace_manual` → web search 依路由找原文（**純雲端，不碰本機**）→ 找到可逐字來源後呼叫 `get_extraction_rules` → 按規則抽取成 JSON 草稿 → 你口頭同意 → LLM 呼叫 `load_extraction` → **App 跳權限確認，你按允許** → 本機驗證 → 寫入 → 圖長大。

**不碰本機（例：「CPO 最近有什麼新聞？」）**
→ 純 web search，全程雲端，本機三個行程無感。

**核心規律：讀圖 = 無副作用；寫圖 = 兩道人工核准 + 一道自動驗證；其他 = 雲端自理。**

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
