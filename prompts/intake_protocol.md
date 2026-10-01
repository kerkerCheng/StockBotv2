# Research Action Protocol（本機）

這份協定與 `prompts/extract_system.md`、`schema/vocab.json` 一起讀——本機 session 直接讀檔。
不得只產合法 JSON；還必須正確追源、保存 provenance、讓使用者核准一個完整且不可變的
Research Action，並誠實回報後續狀態。

> 2026-09-25 起沒有對外的寫入入口（Phase 2 Step 2.1）：手機經 Claude Code Remote Control 連到**同一個本機
> session**，走的就是本協定；舊的遠端協定逐字封存於 `docs/archive/2026-09-25-remote-intake-protocol.md`。

## 1. 先 Trace，再 Research／Extract

收到推文、轉述、截圖、搜尋摘要或二手報導，先讀 `skills/source-trace/SKILL.md`。
tier 3–4 追不到原文時只留 lead/backlog，不產 extraction。只有取得逐字 quote，或符合
tier 1–2 誠實 passthrough，才讀本協定並進研究與抽取。

研究與 extraction 由目前對話中的本機 Claude Code／Codex session 完成；`intake/` 的程式
不呼叫任何模型 API。跨 session 的交接物是 action ID、digest、review packet 與狀態。

## 2. Storage permission 依授權，不依價格

每份新文件必填 `storage_permission` 與非空 `permission_basis`：

| permission | 何時使用 | 可傳內容 | Git publication |
|---|---|---|---|
| `repo_full` | public domain、官方原始文件，或條款／授權明確允許 private-cloud 完整保存 | `raw_text`（最多 200,000 chars），或 URL + excerpt | eligible |
| `repo_excerpt` | 只允許研究所需的有限節錄 | canonical `raw_url` + 有限 `raw_excerpt`；禁止全文 | eligible |
| `local_only` | 授權不明、禁止第三方雲端保存，或只允許本機私人使用 | 可交本機隔離保存；不得進 GitHub | not eligible |

「已付費」不等於可上傳；「免費可看」也不等於可重新保存。basis 只寫 paid/free 會被拒。
`local_only` 是授權不明時的 fail-closed 預設，也不自動代表來源可以送給另一家第三方 LLM；
切換 provider 前仍要遵守來源條款。

## 3. 不可信 URL／credential

- 不得把 cookie、Authorization header、session token 或其他 credential 當 provenance 傳入。
- URL 不得含 username/password。
- 程式會移除 fragment 與 `token`、`access_token`、`key`、`sig`、`signature`、
  `auth`、`X-Amz-*`、`X-Goog-*` 等 secret query；不要依賴帶密鑰 URL 作永久來源。
- 只有 URL 沒有逐字 excerpt，不足以保存 repo-eligible raw artifact。

## 4. 預設流程：Prepare → Review → Approve → Apply

### 4.1 組完整 action，不要逐文件先寫圖

研究與所有 extraction 完成後，把它們放進一個 `research-action/v1`：

```json
{
  "schema_version": "research-action/v1",
  "action_slug": "lowercase-safe-slug",
  "report": {
    "title": "研究行動標題",
    "why_now": "為何此時值得入圖",
    "findings": "本次研究實際發現",
    "search_summary": "走過的一手來源路由、query、未果路徑",
    "l8_notes": "origin_entity／origin_event 獨立性與自報限制",
    "counterevidence_and_gaps": "反向證據、仍未確認處與可證偽缺口"
  },
  "documents": [
    {
      "extraction_json": "{...intermediate-format object...}",
      "storage_permission": "repo_full | repo_excerpt | local_only",
      "permission_basis": "具體授權依據",
      "raw_text": "optional；或改用下方 URL + excerpt",
      "raw_url": "optional canonical URL",
      "raw_excerpt": "optional bounded verbatim excerpt"
    }
  ]
}
```

六個 report 欄位、1–10 份 documents 都必填；未知欄位會 fail closed。每份文件沿用完整
schema/vocab/L6、permission、URL、size 與 no-clobber gate。

### 4.2 prepare，然後停下來給使用者看

```powershell
.venv\Scripts\python.exe scripts\prepare_research_action.py --action-file library\leads\action_drafts\<lead>.json
```

prepare 只會在 ignored private store 建立 action；不寫 provenance ledger、
不寫 Neo4j、不寫 report file、不執行 Git。成功會回：

- action ID
- 完整 64-hex digest
- 30 天 expiry
- 程式產生的 review packet
- 文件與 validation warning 摘要

**必須把原樣 packet 顯示給使用者（進 pq2 `ra_admission`），然後停止。** 不得因為研究看起來合理，
就在同一輪自行 apply。若討論後要改 report、extraction 或文件，重新 prepare 新 action；不可把
舊 action ID 當成已修改版本。

### 4.3 只有明確核准該 ID，才 apply

使用者必須明確核准顯示中的 action ID（pq2 `go`，或「OK，套用 ra_...」）。之後才可在本機 session
用那個 pq2 編號與 prepare／status 回傳的完整 digest 跑**固定入口**（2026-10-01 Phase 4 Step 4.2d；
不再直接呼叫私有函式 `_apply_research_action_impl`）：

```text
python scripts/apply_ra_admission.py --pq2 <編號> --digest <action_digest>
```

入口先過四道 fail closed（編號存在、型別 `ra_admission`、未結案〔drop 永久拒絕〕；編號的 ref_id 是這筆 action；
digest 相符；紀錄 ready 且未過期——或同編號同 digest 中斷在 partial 的重試），通過後把核准戳記
`approval={pq2_n, digest, at}` 寫進紀錄，再 apply。這一次核准套用整個 action；程式會重新驗 digest、
鎖定 action、逐文件 checkpoint、filesystem-first 寫 provenance、冪等寫圖、投影 edge conflicts，最後依
permission 寫報告。它永遠不執行 Git、也不結案（`complete-ra` 會比對戳記上的編號）。

回傳處理：

- `applied`：圖與 report 完成；repo-eligible artifacts 留待本機 publisher 發布（§6）。
- `partial`：至少一個 document 或 report 尚未完成；使用**同一 ID + 同一 digest**重試。
  已有 graph-completion receipt 的文件不會重載。
- `busy`：另一個 apply 持有 live lock；先查 status，不開新 action 規避。
- `expired`：只有尚未開始的 ready action 會在 30 天後過期；重新 research/prepare。
- `rejected`：digest、schema、permission、URL、canonical content 或 receipt 不符；不得改字
  後沿用舊 ID。

`open_conflict_ids` 非空不代表文件載入失敗。apply 只回報 conflict IDs；不得自行挑最大
confidence、不得直接改 resolution JSON／canonical edge。後續由
`$evidence-conflict-resolution` 產 proposal，使用者人工核准。

## 5. 跨 session 查詢

```text
intake.application._get_research_action_status_impl()          # recent actionable summary only
intake.application._get_research_action_status_impl("ra_...")  # exact review packet + recovery state
```

空 ID 只回 action ID、title、state、age、digest prefix、counts 與 next action，不回 report
正文。完整 ID 回同一份 frozen review packet 與 execution state，但兩種模式都不回 raw body
或 extraction JSON。status 是 read-only，不會因查詢而 apply 或 compact。

## 6. Git 只由本機 publisher 做

apply 本身沒有任何 commit／push 能力。圖完成後由本機 session 執行：

```text
python scripts/commit_pending_intake.py --status
python scripts/commit_pending_intake.py --dry-run
python scripts/commit_pending_intake.py --cleanup-expired
python scripts/commit_pending_intake.py
```

local publisher 要求 `master`、空 index 與可驗證的 `origin/master` ancestry；它可以容忍但
絕不 stage 無關的 unstaged/untracked work。每個 action 一個帶 ID + digest trailer 的精確
commit，整批只 push 一次。push 失敗或 commit 後 receipt 尚未回寫，可由 trailer + exact
pathset 安全續跑。

## 7. 單文件直接載入的邊界

`intake.application._load_extraction_impl` 暫時保留給已經有自己人工核准閘門的本機流程；它仍是
一份文件一個呼叫，依 filesystem-first → graph receipt 協定運作。ad hoc intake **不得**
用它繞過整個 Research Action review。（題材掃描只發現、不抽取，不會呼叫它。）
