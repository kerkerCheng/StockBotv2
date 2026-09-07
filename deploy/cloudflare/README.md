# StockBot Web App — Cloudflare 部署（重用既有 Tunnel）

> **這份文件描述的狀態：程式與設定已就緒，Cloudflare 端的三個步驟尚未執行。**
> 下方「還沒做的事」逐項列出需要你在 Cloudflare Dashboard／終端機做什麼，**沒有任何一步被偽造成已完成**。

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
| `STOCKBOT_APP_MAX_AGE_HOURS` | `24` | 超過就標 `stale`；**stale 不會觸發重建** |

---

## 還沒做的事（三步，都需要你本人操作）

### 步驟 1 — 建立 Cloudflare Access 應用程式（**必須最先做**）

Zero Trust Dashboard → **Access → Applications → Add an application → Self-hosted**

| 欄位 | 值 |
|---|---|
| Application name | `StockBot` |
| Session Duration | 建議 `1 month`（手機上不用每次登入） |
| Subdomain / Domain | `stockbot` / `minatoyukina.uk` |
| Path | 留空（保護整個 hostname） |

Policy：

| 欄位 | 值 |
|---|---|
| Policy name | `owner-only` |
| Action | `Allow` |
| Include → Emails | `c3035281@gmail.com` |

登入方式：Zero Trust → **Settings → Authentication** 至少啟用一個 IdP。
最省事的是 **One-time PIN**（Cloudflare 內建，寄驗證碼到上面那個信箱，不需要任何 OAuth 設定）；
想免密碼可另外加 Google OAuth，但那需要在 Google Cloud Console 建 OAuth client——
**第一版不需要**。

> **為什麼這一步必須排在 DNS 之前：** DNS 記錄一建立，hostname 就會開始解析。
> 若那時還沒有 Access policy，這個網址在建立到設定完成之間是**公開可讀**的。
> 順序反過來就是把 private 研究內容短暫公開，沒有理由冒這個險。

### 步驟 2 — 建立 DNS 記錄（一行指令）

```bash
cloudflared tunnel route dns d3074ec2-c2a3-4782-9c54-8604289b5fd3 stockbot.minatoyukina.uk
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
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process
# 重新啟動：雙擊 shell:startup 裡的 stockbotv2-graph-services.vbs
```

⚠ 重啟期間 `mcp.minatoyukina.uk` 與 `neo4j.minatoyukina.uk` 會短暫中斷（數秒）。
挑一個沒有排程在跑的時間做。

### 驗收（每一步都要看到預期輸出才算完成）

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

## 開機自啟（可選）

現有的 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\stockbotv2-graph-services.vbs`
已經負責 Neo4j＋cloudflared＋MCP。要讓 APP 也自動起來，在該檔加一行同形的隱藏視窗啟動：

```vbs
' StockBot Web App（read-only；不 materialize、不寫任何 authority）
WshShell.Run "cmd /c cd /d C:\Users\Cheng\code\StockBotv2 && .venv\Scripts\python.exe -m webapp serve", 0, False
```

⚠ **不要**在自啟腳本裡放 `materialize`——那會在每次開機時跑模型、連 Neo4j、讀 private ledger。
更新判讀應該由你在互動 session 明確執行，或由既有排程機制安排（需先走 sandbox impact review 五步）。

---

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
