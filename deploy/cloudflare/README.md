# StockBot Web App — Cloudflare 部署（重用既有 Tunnel）

> **狀態（2026-09-07 實測）：已上線並可從外部使用。**
> Access 應用程式、DNS、ingress 三步都已完成；未登入時 `https://stockbot.minatoyukina.uk`
> 回 **302 導向 Access 登入頁**，登入後可看到判讀清單。既有 `mcp.` 與 `neo4j.` 未受影響。
> **Google 登入也已生效**——Access event analytics 顯示 `Identity provider = google`。
> ⚠ **不是照下方步驟 0 手動設的**：新版 Cloudflare One 在建立 Access 應用程式的流程中
> 已自動把 Google 加成 identity provider。**步驟 0 仍然保留**，但它現在的用途是
> 「沒有被自動加上時該怎麼做」，不是必經路徑。
> **開機自啟也已完成**（見下方「開機自啟」）。
>
> ⚠ **介面名稱：Cloudflare 已把 Zero Trust 主控台改名為 Cloudflare One，側欄整組重排。**
> 下方路徑是 **2026-09-07 在實際畫面上確認過的**；標「未實地驗證」的那幾條還沒有。

## 一句話

```
iPhone Safari／桌機瀏覽器
    → https://stockbot.minatoyukina.uk
    → Cloudflare Access（外部認證邊界）
    → 既有的 Cloudflare Tunnel（d3074ec2-…，與 MCP 同一條）
    → cloudflared → http://127.0.0.1:8790（本機 StockBot APP）
```

**APP 本身沒有帳號密碼系統，這是刻意的**（Step 5 scope：第一版不自己做認證）。
它只綁 `127.0.0.1`，唯一入口是 tunnel 轉進來的流量；認證由 Cloudflare Access 負責。

## 重用了什麼（不新建平行 deployment stack）

| 元件 | 現況 | 本次動作 |
|---|---|---|
| Cloudflare 帳號／網域 `minatoyukina.uk` | 已有（2026-07-11 註冊，DNS 由 Cloudflare 管理） | 重用 |
| Tunnel `d3074ec2-c2a3-4782-9c54-8604289b5fd3` | 已有，`cloudflared` 開機自啟 | **重用同一條**，只加一條 ingress |
| `~/.cloudflared/cert.pem`、credentials JSON | 已有 | 重用，**不進 Git** |
| `neo4j.minatoyukina.uk`、`mcp.minatoyukina.uk` | 運作中 | **一個字都不動** |
| 開機自啟 `stockbotv2-graph-services.vbs` | 已有（Neo4j＋cloudflared＋MCP） | 可選：加一行啟動 APP（見下方「開機自啟」） |

⚠ **不得破壞既有 MCP hostname／route。** 下方 ingress 是**新增一條規則**，
`mcp.minatoyukina.uk` 那條連同它的 `httpHostHeader` 改寫原封不動。

## 本機先跑起來（不需要 Cloudflare 也能用）

```bash
python -m webapp materialize COHR LYC.AX 6324.T IQE.L   # 唯一會跑模型的一步（約 4 秒／檔）
python -m webapp serve                                   # http://127.0.0.1:8790/
```

`serve` **不會**重建任何東西。要更新判讀就重跑 `materialize`——這是刻意分成兩條責任鏈。

環境變數（都有安全預設，通常不必設）：

| 變數 | 預設 | 說明 |
|---|---|---|
| `STOCKBOT_APP_PORT` | `8790` | MCP 是 8788，刻意錯開 |
| `STOCKBOT_APP_HOST` | `127.0.0.1` | 改成別的介面**必須**同時設 `STOCKBOT_APP_ALLOW_PUBLIC_BIND=1`，否則程式拒絕啟動 |
| `STOCKBOT_APP_ARTIFACT_DIR` | `library/private/app/analyst_view` | artifact 目錄（在 ignored 的 private 樹下） |
| `STOCKBOT_APP_STATE_DIR` | `library/private/app/state` | 跨標的 state artifact 目錄（`ranking`；同在 ignored 的 private 樹下） |
| `STOCKBOT_APP_MAX_AGE_HOURS` | `24` | 超過就標 `stale`；**stale 不會觸發重建** |

---

## 部署步驟（步驟 1–3 已於 2026-09-07 完成；步驟 0 可選、尚未做）

### 步驟 0 — Google OAuth ✅ *2026-09-07 實測已生效（由新版介面自動設定，未手動執行本步驟）*

> **先確認你需不需要做這一步。** Cloudflare One → `Insights & Logs → Dashboards →
> Access event analytics`，看「Identity provider」那一格。若已經是 `google`，
> 這整段可以跳過。以下是**沒有被自動加上時**的手動程序。

> **兩個都設起來。** Google 是日常入口（一鍵，不用等信），一次性 PIN 是備援
> （Google 設定壞掉時還進得去）。多一個登入方法不增加風險——原則仍然只允許同一個 email。
>
> ⚠ **下面每個欄位都標了「中文（English）」。** Cloudflare 與 Google 的中文化都不完整，
> 同一頁常常一半中文一半英文；兩個名字都給，你看到哪個就對哪個。

**先拿到 team domain：** Cloudflare One 主控台 → 側欄最下面的 **設定（Settings）**
→ 頁面第一段 **Team name and domain**，`Team domain` 那一格就是
`<team-name>.cloudflareaccess.com`。下一步的重新導向 URI 要用它。
✅ *2026-09-07 實地確認*

**A. Google Cloud Console（<https://console.cloud.google.com>，右上角可切「繁體中文」）**

1. 左上角建立新專案，例如 `stockbot-access`。
2. 左側 **API 和服務（APIs & Services）→ OAuth 同意畫面（OAuth consent screen）**
   ⚠ 新版介面已改叫 **Google 驗證平台（Google Auth Platform）**，欄位散在四個分頁裡：

   | 新版分頁 | 舊版位置 | 要填什麼 |
   |---|---|---|
   | **品牌宣傳（Branding）** | 同意畫面上半部 | 應用程式名稱 `StockBot`；使用者支援電子郵件、開發人員聯絡資訊填你的信箱 |
   | **目標對象（Audience）** | 同意畫面「使用者類型」 | 使用者類型選 **外部（External）**——個人 Gmail 沒有「內部」，那是 Google Workspace 專屬；測試使用者（Test users）加自己 |
   | **資料存取權（Data Access）** | 同意畫面「範圍」 | **什麼都不要加**。Cloudflare 只要 `openid`／`email`／`profile`，那是非敏感的預設範圍 |
   | **目標對象（Audience）** 頁上方 | — | ⚠ 最後按 **發布應用程式（PUBLISH APP）**，把發布狀態由「測試中（Testing）」切成「正式版（In production）」 |

3. 左側 **憑證（Credentials）→ 建立憑證（Create Credentials）→ OAuth 用戶端 ID（OAuth client ID）**
   （新版在 **用戶端（Clients）→ 建立用戶端（Create client）**）
   - 應用程式類型（Application type）：**網頁應用程式（Web application）**
   - 名稱（Name）：`Cloudflare Access`
   - **已授權的重新導向 URI（Authorized redirect URIs）**——**一字不差**：
     `https://<team-name>.cloudflareaccess.com/cdn-cgi/access/callback`
   - 建立後記下 **用戶端 ID（Client ID）** 與 **用戶端密碼（Client secret）**

**B. Cloudflare One → 側欄 整合（Integrations）→ 身分識別提供者（Identity providers）
→ 新增（Add new）→ Google**

⚠ **這一頁在新版介面搬家了。** 舊版是 `Zero Trust → Settings → Authentication → Login methods`，
**新版在「整合（Integrations）」底下**（同一區還有 Cloud & SaaS、Service providers）。
找不到就用左上角的 **Quick search（`Ctrl + K`）** 打 `identity`。
✅ *2026-09-07 實地確認位置；Google IdP 本身尚未設定*

| 欄位 | 值 |
|---|---|
| App ID | 上面的**用戶端 ID** |
| Client secret | 上面的**用戶端密碼** |

存檔後按 **測試（Test）**——這一步會直接告訴你重新導向 URI 對不對，**不要跳過**。
同一頁確認 **一次性 PIN（One-time PIN）** 是啟用的（Cloudflare 內建，不需任何設定）。

### 步驟 1 — 建立 Cloudflare Access 應用程式（**必須在 DNS 之前**）

Cloudflare One 主控台 → **存取控制（Access controls）→ 應用程式（Applications）**
→ 右上角 **Create new application**
→ 上排分頁 **Self-hosted and private** → 下排選 **Public DNS**
→ **Continue with Self-hosted and private**
✅ *2026-09-07 實地確認*

**下排那四個選項在問「這個應用程式住在哪種目的地」，選錯會連不上：**

| 選項 | 適用 | 我們 |
|---|---|---|
| Private destinations | 只能透過 WARP 用戶端連的私有資源 | ❌ 要用手機瀏覽器直接開 |
| Workers | 應用程式本體是 Cloudflare Worker | ❌ APP 跑在本機 |
| **Public DNS** | **對外可解析的主機名，流量經 Cloudflare 進來** | ✅ `stockbot.minatoyukina.uk` |
| Service auth | 只給機器用、沒有人登入（service token） | ❌ 要人登入 |

| 欄位 | 值 |
|---|---|
| 應用程式名稱（Application name） | `StockBot` |
| **工作階段持續時間（Session Duration）** | **選下拉選單裡最長的（`1 個月` / `1 month`）** |
| 子網域（Subdomain）／網域（Domain） | `stockbot` ／ `minatoyukina.uk` |
| 路徑（Path） | 留空（保護整個 hostname） |
| 身分識別提供者（Identity providers） | 勾 **Google** ＋ **一次性 PIN（One-time PIN）** |

原則（Policies）：

| 欄位 | 值 |
|---|---|
| 原則名稱（Policy name） | `owner-only` |
| 動作（Action） | **允許（Allow）** |
| 包含（Include）→ 電子郵件（Emails） | `c3035281@gmail.com` |
| **工作階段持續時間（Session Duration）** | **同樣設 `1 個月`** |

⚠ **原則層的工作階段持續時間會覆寫應用程式層。** 兩邊都設，否則你會發現
「明明設了 1 個月卻天天要登入」——那不是 bug，是另一層的預設值在生效。

> **為什麼這一步必須排在 DNS 之前：** DNS 記錄一建立，hostname 就會開始解析。
> 若那時還沒有 Access 原則，這個網址在建立到設定完成之間是**公開可讀**的。
> 順序反過來就是把 private 研究內容短暫公開，沒有理由冒這個險。

### 步驟 2 — 建立 DNS 記錄（一行指令）

```bash
cloudflared tunnel route dns stockbotv2-neo4j stockbot.minatoyukina.uk
```

它會用 `~/.cloudflared/cert.pem` 的授權建立一筆指向 tunnel 的 CNAME。

### 步驟 3 — 加一條 ingress 並重啟 cloudflared

編輯 `C:\Users\Cheng\.cloudflared\config.yml`，**在 `- service: http_status:404` 這條 catch-all
之前**插入 StockBot 那一段（完整檔案見同目錄的 [`config.yml.example`](config.yml.example)）：

```yaml
  - hostname: stockbot.minatoyukina.uk
    service: http://localhost:8790
```

⚠ **順序有意義**：cloudflared 由上往下比對，catch-all `http_status:404` 必須永遠在最後一條。

然後重啟 cloudflared：

```powershell
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process -FilePath "C:\Program Files (x86)\cloudflared\cloudflared.exe" `
  -ArgumentList 'tunnel','run','stockbotv2-neo4j' -WindowStyle Hidden
```

⚠ **只重啟 cloudflared 一個行程**，不要雙擊 `stockbotv2-graph-services.vbs`——
那支會連 Neo4j 與 MCP server 一起再啟動一次（雖然會因 port 佔用自然退出、無害，但沒必要）。

⚠ 重啟期間 `mcp.minatoyukina.uk` 與 `neo4j.minatoyukina.uk` 會短暫中斷（數秒）。
挑一個沒有排程在跑的時間做。

### 驗收（2026-09-07 實跑結果）

| 檢查 | 實際輸出 | 判讀 |
|---|---|---|
| `nslookup stockbot.minatoyukina.uk` | `104.21.83.81`／`172.67.217.216`（＋IPv6） | ✅ CNAME 已建立且走 Cloudflare 代理 |
| `curl -sI https://stockbot.minatoyukina.uk/api/v1/health` | **`302`** → `bold-…cloudflareaccess.com/cdn-cgi/access/login/…` | ✅ **未登入拿不到研究內容**（最重要的一條） |
| 瀏覽器登入後 | 四檔判讀清單 | ✅ 使用者實測 |
| `curl -sI https://mcp.minatoyukina.uk/` | `404` | ✅ **正常**——MCP 的網址含 40 字元 path token，沒帶就是 404，不是被打壞 |
| `curl -s http://127.0.0.1:8790/api/v1/health` | `{"status":"ok",…}` | ✅ 本機直連未受影響 |

### 驗收指令（重跑用）

```bash
# 1. 本機直連仍然可用
curl -s http://127.0.0.1:8790/api/v1/health

# 2. 未登入時，Cloudflare Access 應該把你導向登入頁（而不是回你的研究內容）
curl -sI https://stockbot.minatoyukina.uk/api/v1/health | head -3
#    預期看到 302 → cloudflareaccess.com；**若直接回 200 ＋ JSON，代表 Access 沒生效，立刻停用 DNS**

# 3. 既有 MCP 沒被打壞
curl -sI https://mcp.minatoyukina.uk/ | head -1

# 4. 手機：Safari 開 https://stockbot.minatoyukina.uk → Access 登入 → 清單頁
```

---

## 多久要 renew 一次？（三件不同的事，不要混在一起）

| 什麼 | 會不會過期 | 怎麼調長 |
|---|---|---|
| **Access 登入工作階段**（決定你多久要重登一次） | **會**——由工作階段持續時間決定 | 下拉選單**最長 1 個月**；應用程式層與原則層**兩邊都要設**（原則層會覆寫應用程式層） |
| **Google 用戶端 ID／用戶端密碼** | **不會過期**，不需要定期更換 | 除非你自己在 Google Cloud Console 輪換密碼；輪換後要回 Zero Trust 更新 |
| **Google 同意畫面的發布狀態** | 「測試中（Testing）」有 7 天限制 | **按「發布應用程式（PUBLISH APP）」切到「正式版（In production）」**——只用 `openid`／`email`／`profile` 這類非敏感範圍時，**Google 不需要審查**，按下去就生效 |

**建議設定：工作階段持續時間 = `1 個月`（應用程式層與原則層都設）。** 那是 Cloudflare 給的上限；
沒有「永不過期」這個選項，而那其實是好事——手機掉了之後，最壞情況有一個自然的到期日，
不必依賴你記得去撤銷。

⚠ **關於「測試中」vs「正式版」的實際差別：** 留在「測試中」也「能用」，但每次登入會出現
Google 的「這個應用程式未經驗證」警告畫面，而且該模式的 refresh token 7 天到期。
Cloudflare Access 的 session 是它自己簽發的 cookie、不靠 Google 的 refresh token，
所以 7 天限制**不會**縮短你的 Access session；但那個警告畫面每次都要多點兩下，沒必要忍。

⚠ **手機上若比設定值更早要求重登，那是瀏覽器行為不是設定錯誤。** Safari 對 cookie 有自己的
保存政策，實測才知道會不會比 1 個月短。**先照上面設，再看實際行為**——不要一開始就為了
「可能會提早」去改設計（那是還沒量測就先加機制，本專案記過的形狀）。

**要立刻踢掉所有已登入 session**（例如手機遺失）：
Cloudflare One → **團隊與資源（Team & Resources）→ 使用者（Users）** → 選自己 →
**撤銷工作階段（Revoke sessions）**。⚠ *未實地驗證；找不到就用 `Ctrl + K` 搜 `users`。*

---

## 開機自啟 ✅ 已完成（2026-09-07）

現有的 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\stockbotv2-graph-services.vbs`
（原本負責 Neo4j＋cloudflared＋MCP）**已在檔尾追加兩行**，讓 APP 也隨登入啟動：

```vbs
' StockBot Web App（Phase 2 Step 5，2026-09-07）——read-only serve。
' 只放 serve，絕對不要放 materialize：那會在每次開機時跑模型、連 Neo4j、讀 private ledger。
' CurrentDirectory 必須先切到 repo root——python -m webapp 靠 cwd 找到 webapp 套件。
' 放在最後一行，所以上面三個 Run 不受工作目錄變更影響。
ws.CurrentDirectory = "C:\Users\Cheng\code\StockBotv2"
ws.Run """C:\Users\Cheng\code\StockBotv2\.venv\Scripts\python.exe"" -m webapp serve", 0, False
```

**三個設計決定：**

1. **用 `ws.CurrentDirectory` 而不是 `cmd /c cd /d … &&`。** `python -m webapp` 需要 cwd 是 repo root
   才找得到 `webapp` 套件；設屬性比多起一個 `cmd.exe` 乾淨。
2. **放在檔尾。** `CurrentDirectory` 是行程層的狀態，放前面會影響上面三個 `ws.Run`。
3. **只放 `serve`。** ⚠ **絕對不要在自啟腳本裡放 `materialize`**——那會在每次開機時跑模型、
   連 Neo4j、讀 private ledger。更新判讀應該由你在互動 session 明確執行。

**驗收（2026-09-07 實跑）：** 把新增的兩行抽成獨立 vbs 單獨執行（不碰 Neo4j／cloudflared／MCP），
結果——APP 起得來（`/api/v1/health` 回 `ok`）、**沒有任何可見視窗**、
`Get-NetTCPConnection -LocalPort 8790` 顯示 **`LocalAddress = 127.0.0.1`**（不是 `0.0.0.0`，
確認安全預設生效）。原檔備份在同目錄 `stockbotv2-graph-services.vbs.bak-2026-09-07`；
`diff` 確認除了檔尾那 6 行之外**一個位元組都沒動**。

**要停用：** 把那兩行（與上面四行註解）刪掉，或直接還原備份。

## 安全邊界（分層，與 MCP 同一套思路）

1. **本機綁定**：APP 只聽 `127.0.0.1:8790`；家用路由器零入站、對外不知道你的 IP。
   綁其他介面需明示 `STOCKBOT_APP_ALLOW_PUBLIC_BIND=1`，否則程式**拒絕啟動**。
2. **Cloudflare Access**：外部認證邊界。未通過 policy 的請求到不了 tunnel。
3. **只讀**：沒有任何 POST／PUT／PATCH／DELETE 路由（路由層直接 405）；
   request path 沒有 LLM、沒有 authority write、沒有外部抓取、沒有模型執行
   （`tests/test_webapp_request_path.py` 用四種互相獨立的方式證明）。
4. **無任意檔案存取**：ticker → 檔名走**字元 allowlist**（不是過濾），static 檔案是三個檔名的
   allowlist，路徑解析後仍必須在 artifact 目錄內。
5. **private 路徑不出門**：materialize 階段就把 `library/private/...` 與 Windows 絕對路徑
   換成 `«private-authority»`；API 回應與錯誤訊息都不含檔案路徑、stack trace 或 credential。
6. **回應 header**：`no-store`（不讓中介或瀏覽器留下私人研究內容）、`frame-ancestors 'none'`、
   `nosniff`、CSP 只允許 same-origin（前端零外部資源）。
7. **credential 不進 Git**：`~/.cloudflared/` 的 cert 與 tunnel credentials 從來不在 repo 裡；
   本目錄的 example 只有 hostname 與 port，**沒有任何 token**。

## 殘餘風險（誠實列出）

- **Access session 綁在瀏覽器上。** 手機遺失時要到 Zero Trust → Access → 撤銷 session。
- **Cloudflare 本身看得到流量**（TLS 在它那裡終止）。這與既有 MCP／Neo4j hostname 的姿態一致，
  不是本次新增的暴露面。
- **APP 沒有第二層 token。** 若日後想要 defence in depth，加一個 path token（與 MCP 同做法）
  是最小改動；本版刻意不做，因為 Access 已經是明確的認證邊界，兩套認證會讓「誰擋下了這個請求」
  變得難以回答。
