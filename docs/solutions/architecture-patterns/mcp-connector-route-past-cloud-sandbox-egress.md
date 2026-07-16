---
module: mcp_server
date: 2026-07-11
problem_type: architecture_pattern
component: tooling
severity: high
applies_when: "讓 claude.ai 雲端介面（cloud routine、手機 App、網頁對話）存取本機資源（如 Neo4j 知識圖譜），特別是在 Pro 個人方案上"
symptoms:
  - "cloud routine 內 curl 自訂網域回 curl (56) CONNECT tunnel failed, response 403"
  - "claude.ai Capabilities 的 Additional allowed domains 與 All domains 對 routine sandbox 完全無效"
  - "Managed Agents API 建的 limited-networking 環境對 routine 系統回 environment_not_found"
tags:
  - claude-code
  - cloud-routine
  - mcp
  - cloudflare-tunnel
  - network-egress
  - neo4j
related_components:
  - database
  - development_workflow
---

# Cloud sandbox 出站網路封死時，用自建 MCP connector 當正門

## Context

U7 自動化管線需要 cloud routine 讀寫本機 Neo4j（使用者機器常開、圖不搬雲端）。原設計是 Cloudflare Tunnel 暴露 Neo4j HTTP 端點、routine 直連。動工前把「連得到」當假設驗證（brainstorm 明訂 U7a 為硬性前置），結果假設全滅。

## What Didn't Work（四次實測，Pro 個人方案）

| 嘗試 | 結果 |
|------|------|
| 預設環境（Trusted 白名單）直連 tunnel 網域 | `curl (56) CONNECT tunnel failed, response 403`——Anthropic 出站 proxy 直接拒絕 |
| claude.ai Capabilities 加 Additional allowed domains | 無效（等 20+ 分鐘排除設定延遲後重測，仍無效） |
| Capabilities 切 All domains | 仍無效——該設定只管聊天 code-execution 沙盒，管不到 routine sandbox，是兩套獨立體系 |
| 用 `ANTHROPIC_API_KEY` 走 Managed Agents API 建 limited-networking 環境 | 環境建得起來，但 routine 系統看不到它（`environment_not_found`）——API 環境與訂閱帳號的 routine 系統不互通 |

結論：**Pro 方案上 routine sandbox 的出站白名單不可自訂**；「domain whitelisting」在官方文件中列於 Enterprise 段落。這不是 bug，是方案分層。

驗證手法備忘：cloudflared 預設日誌不記錄個別請求，用本機 metrics 端點（`127.0.0.1:20241/metrics` 的 `cloudflared_tunnel_total_requests` 計數器）判定流量有沒有進來，比翻日誌可靠。

## Guidance

**MCP connector 的流量走 Anthropic 伺服器轉發，不經過 sandbox 的出站 proxy**——這是繞過（實為「走正門」）的關鍵。模式：

1. 本機寫一個小 MCP server（Python `mcp` SDK，streamable HTTP），只暴露窄工具——本案從最初四個演進為九個固定工具；寫入以 server-owned Research Action prepare/status/apply 包住，remote surface 不含 Git
2. 走既有 Cloudflare Tunnel 加一個 hostname 暴露它；**tunnel ingress 必須加 `httpHostHeader: 127.0.0.1:<port>` 改寫**——MCP SDK 內建 DNS-rebinding 防護，非 localhost 的 Host 一律回 421 Misdirected Request
3. 認證用 URL 路徑內嵌 token（custom connector 表單只有 URL + 選填 OAuth，path token 是個人場景的務實解）
4. 掛成 claude.ai custom connector 後，**routine、手機 App、網頁對話全部同時獲得存取**——比原本只給 routine 的直連設計覆蓋面更廣
5. 防護分層：path token（碰不到端點）→ 最小權限 DB 帳號（Enterprise RBAC；MERGE/SET 可、DELETE/schema 不可）→ 唯讀工具用 READ access mode session 強制 → prepare 凍結完整 payload + digest → apply 逐文件冪等 checkpoint → connector 權限把 apply 設 Needs-approval。Needs-approval 是 UX gate，不取代 server auth；Git 只留在本機 maintenance command

## Why This Matters

- 不驗證假設就動工的話，會蓋完整條 pipeline 才發現連不上（L2/U7a 的價值展示：先撞假設，撞出的洞才是真需求）
- MCP 路線不是降級——它把「遠端存取」從單一消費者（routine）擴大成所有 claude.ai 介面，且窄工具面比裸資料庫端點安全
- 附帶發現（另一個坑）：**GitHub App 以使用者本人身分開的 PR/Issue，GitHub 不會通知本人**——依賴「routine 開 PR → GitHub 通知我」的可靠性設計要另找通知管道（claude.ai routine 自身通知、或 GitHub Action 外發）

## When to Apply

- 任何「claude.ai 雲端介面需要碰自架/本機資源」的需求，且方案不是 Enterprise
- 想讓手機上的 Claude 對話讀寫本機資料庫/服務
- 反例：資源本來就在公網上有正式 API（直接用 web fetch 即可），或可接受把資料搬進雲端託管服務

## 遠端入圖硬化清單（2026-07-12，首批手機入圖實戰撞出）

核心教訓：**遠端起草者（手機/雲端的 Claude）唯一的 context 就是規則書**——本機管線裡靠慣性和外部注入補齊的細節，規則書沒寫它就一定會漏。首批四份手機入圖撞出的坑與修法：

- **規則書必須自足**：claim `id`、來源 id 全域格式、`origin_entity` 顯示名格式、`url`/`published_at` 必填——這些在 CLI 流程由 caller 注入或範例暗示，遠端流程全靠規則書明文。撞一個補一個，最終全部進了 `prompts/extract_system.md`
- **驗證器不能在組錯誤訊息時炸掉**：eager f-string（`c['id']`）讓 schema 正確抓到的錯誤變成 KeyError 穿透；MCP 工具層也要把驗證器異常包成可讀拒載
- **遠端載入必須落地**：`load_extraction` 成功後同步寫 `extractions/<doc_id>.json`，否則掃磁碟的 L8 計數器看不到遠端文件（治本方案是 SourceDoc 節點進圖，issue #4）
- **relationship type 要預註冊**：最小權限帳號不能建新 type；用 admin 把 vocab 全部 type 預註冊進 token 表（建一條刪一條，token 永存），達成「vocab 白名單 = DB 可用集合」且零權限擴張
- **connector 的 Needs-approval 回應是 "No approval received."**——這是平台權限層的訊息，不是 server 端的；遠端 Claude 會誤判成伺服器機制，UX 上要知道核准按鈕在使用者的 App 畫面上
- **服務用分離行程跑**（`Start-Process -WindowStyle Hidden`），不要當 Claude Code session 子行程——否則 session 一關遠端全斷

## Examples

現行實作與操作細節（活文件）：`docs/remote-access-architecture.md`。
決策過程與逐步驗證紀錄：`docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md` U7a/U7d。
Server 本體：`mcp_server/graph_mcp.py`（九工具）+ `mcp_server/research_actions.py`（durable approval state）+ `mcp_server/action_publisher.py`（local-only Git）。
遺留 backlog：issue #3（重複邊）、#4（L8 改以圖為準）、#5（Engine C 遠端開放）。
