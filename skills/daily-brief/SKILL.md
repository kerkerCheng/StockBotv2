---
name: daily-brief
description: >
  每日核准迴路：把 harvest → triage → 今日決策 → thesis 到期 聚合成一份 action-first
  的 Daily Approval Brief，使用者用封閉動詞（research／apply／park／skip）一句話核准。
  當使用者說「daily brief」「今天有什麼要處理」「跑每日摘要」「有哪些待判斷」「今天需要
  動作嗎」時使用。本 skill 不放寬任何入圖或資本閘門：graph admission 必經使用者核准
  exact ID、深挖研究必經點名、live 資本永遠人工。純讀聚合，不自動建 decision、不下單、
  不自動入圖。觸發詞：daily brief、每日摘要、今天有什麼、待判斷、今天需要動作嗎。
---

# Daily Approval Brief Skill

## 定位一句話

**每天一份 action-first brief，使用者只需回一句封閉動詞就完成當日核准。**

系統做便宜的事（harvest／triage／聚合），使用者做判斷（要不要深挖、要不要入庫）。
無事時 brief 是一行 `NO ACTION`。三道閘門永不自動：**graph admission 必經核准 exact
ID、深挖研究必經點名、live 資本永遠人工**。本 skill 純讀聚合——不 freeze context、
不建 decision、不下單、不自動入圖。

> **只在本機執行。** `decision_lab` 與 leads 狀態依賴本機 private runtime／檔案；雲端
> session 的 clone 沒有 Decision Store，跑決策命令會開出空 store（產出無效）。雲端要看
> 今日決策請用 MCP 的 `get_decision_brief`（唯讀）。

---

## 執行流程（依序）

### Step 1 — Harvest（零 token，純 script）

```powershell
python crons/harvest_leads.py
```

抓 RSS＋EDGAR watch 的新項目，以 URL-hash 去重（重複無害）。fetch／parse 失敗會各自
記進 harvest_log，**解析失敗 ≠ 無新文**——若 brief 要呈現某 feed，先看它今天是 ok 還是
failed；failed 時在 brief 標明並提示 fallback（如 `site:aleabitoreddit.substack.com`
web search）。harvest 不 triage、不入庫。

### Step 2 — Triage 新 pending leads（依 signal-triage 判準）

列出待判斷：

```powershell
python -m engine_b.cli list --status pending
```

對每條**新** pending lead，完整套用 `skills/signal-triage/SKILL.md` 的五要素判準
（關聯性、新穎性、可引用性、潛在新 origin_entity、矛盾／反證價值）做 go／no-go 判斷。
判斷是語意工作由你做；判斷完用 CLI 寫回狀態（不要手改 JSON）：

```powershell
python -m engine_b.cli triage <lead_id> --go   --tier 3 --reason "<哪一要素觸發放行>"
python -m engine_b.cli triage <lead_id> --no-go --tier 4 --reason "<為何篩掉>"
```

triage 刻意寬鬆：關聯性與可引用性是硬指標，其餘軟指標任一命中就 go。**no-go 也要記
reason**（使用者事後稽核篩選是否太嚴的唯一依據）。這裡的 `tier` 只是來源初步分級，
**不是** evidence tier、不影響入圖強度——真正 evidence tier 由 source-trace／lead-intake 決定。

### Step 3 — 今日決策佇列

```powershell
python -m decision_lab today --format markdown
```

回今日 `NO ACTION / REVIEW / TRADE / HEDGE` 與九欄 action-first 契約（含 Sheet-only／
legacy holding 反向比對）。純讀，不建 decision。

### Step 4 — Thesis 生命週期到期

讀 `thesis/lifecycle.json`，列出到期需核查的 thesis（active／watch／review_required 依
其核查頻率）。到期項是「需要動作」的一種，列入 brief。

### Step 5 — 組四佇列 brief（繁中、exception-first）

無事就一行 `NO ACTION ＋日期`。有事按下列版面：

```
# Daily Brief <YYYY-MM-DD>

## 需要你動作
（決策佇列 today 的 REVIEW／TRADE／HEDGE 項；thesis 到期核查項；
  等 apply 的 Research Actions —— 各附一句理由與可回覆的動詞）

## 新 leads（已 triage）
（triaged_go 優先在前，附一句放行理由與 research 動詞；
  no-go 摺疊成一行數量＋可展開）

## 低優先（摺疊）
（EDGAR Form 4 與較舊 filing —— 冷啟動偏多，預設摺疊、不淹沒新料）

## 無事項目
（thesis 無到期／paper 無異動／live 無 pending fill —— 一行帶過）

---
動詞：research <n> ｜ apply <ra_id> ｜ park <n> ｜ skip
```

Form 4 與舊 filing 預設進「低優先（摺疊）」——冷啟動 EDGAR seed 偏 Form 4，不要讓歷史
內部人交易淹沒真正的新訊號。

### Step 6 — 動詞 dispatch

使用者回封閉動詞後，對應到既有流程（不新增任何權限語意）：

| 動詞 | 動作 |
|------|------|
| `research <n>` | 該 lead 進 source-trace＋`skills/lead-intake`（先 `advance <lead_id> triaged_go` 若尚未、再 `advance <lead_id> researching`）；深挖是使用者點名才跑的花錢步驟 |
| `apply <ra_id>` | 走既有 Research Action 核准流程（使用者核准 exact ID＋一次 native approval），本機 session 再跑 `scripts/commit_pending_intake.py`；lead 對應 `advance <lead_id> applied` |
| `park <n>` | `python -m engine_b.cli advance <lead_id> parked` |
| `skip` | 不動作，當日略過 |

決策類動作（接受／縮小 live choice、回報 fill）**不在本 skill 的動詞集合**——它們永遠
以 `python -m decision_lab record-choice` / `record-fill` 在本機用明確 flags 執行，
不得由 recommendation 推定 choice、由 choice 推定 fill。系統不連 broker。

### Step 7 — 收尾 commit＋push

當日若有狀態變更（leads triage／advance、入庫）：先 sanity check 私有隔離，再依邏輯
commit 並 push（cloud routine 讀 pushed clone 的新鮮度靠這個）：

```powershell
git ls-files library/private   # 必須為空
git add library/leads/pending_leads.json <本次其他變更>
git commit -m "<描述>"
git push origin master
```

---

## 與 cloud routine 的分工

`crons/daily_brief_prompt.md` 的每日 cloud routine 做同樣的 harvest＋triage 呈現，但
**只在 GitHub Issue 上呈現、不回寫本機狀態**（單一寫入者原則）。本機 session 跑
`/daily-brief` 時以 URL-hash 冪等重新落地同批 leads 並重 triage——雲端看得到、寫不進，
狀態 authority 只在本機。日到期核查、系統健康與 topic discovery 深掃仍歸 weekly scan。

## 產出物（一次跑完應該有）

1. harvest_log（哪些 source ok／failed）
2. 新 leads 的 triage 決定（go／no-go＋reason，no-go 不得悄悄消失）
3. 四佇列 brief（繁中、action-first、動詞說明在尾）
4. （使用者回動詞後）對應既有流程的執行與收尾 commit／push

## 已知會壞的地方（v0，撞到回頭修）

- 初期流量稀，brief 常是一行 NO ACTION——這是來源清單問題，不是管線問題。
- RSS feed 只曝露最新數篇；長期不開 session 舊文會掉出視窗，只剩雲端 Issue 紀錄可撿。
- triage 判準寬鬆度是拍腦袋 v0，用真實流量調。
