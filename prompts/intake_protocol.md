# Remote Intake & Finalize Protocol

這份協定與 `prompts/extract_system.md`、`schema/vocab.json` 一起由
`get_extraction_rules` 端出。遠端 chat／routine 不得只產合法 JSON；還必須正確保存
provenance、處理 evidence conflict，並完成或誠實回報 Git 收尾。

## 1. 先 Trace，再 Extract

收到推文、轉述、截圖、搜尋摘要或二手報導，先呼叫 `get_source_trace_manual`。
tier 3–4 追不到原文時只留 lead/backlog，不產 extraction。只有取得逐字 quote，或符合
tier 1–2 誠實 passthrough，才讀本協定並進抽取。

## 2. Storage permission 依授權，不依價格

每份新文件必填 `storage_permission` 與非空 `permission_basis`：

| permission | 何時使用 | 可傳內容 | finalize |
|---|---|---|---|
| `repo_full` | public domain、官方原始文件，或條款／授權明確允許 private-cloud 完整保存 | `raw_text`（最多 200,000 chars），或 URL + excerpt | eligible |
| `repo_excerpt` | 只允許研究所需的有限節錄 | canonical `raw_url` + 有限 `raw_excerpt`；禁止全文 | eligible |
| `local_only` | 授權不明、禁止第三方雲端保存，或只允許本機私人使用 | 可交本機隔離保存；不得進 GitHub | **not eligible** |

「已付費」不等於可上傳；「免費可看」也不等於可重新保存。basis 只寫 paid/free 會被拒。
`local_only` 是授權不明時的 fail-closed 預設，也不自動代表來源可以送給其他第三方 LLM。

## 3. 不可信 URL／credential

- 不得把 cookie、Authorization header、session token 或其他 credential 當 provenance 傳入。
- URL 不得含 username/password。
- server 會移除 fragment 與 `token`、`access_token`、`key`、`sig`、`signature`、
  `auth`、`X-Amz-*`、`X-Goog-*` 等 secret query；不要依賴帶密鑰 URL 作永久來源。
- 只有 URL 沒有逐字 excerpt，不足以保存 repo-eligible raw artifact。

## 4. `load_extraction` 協定

一份文件一個呼叫：

```text
load_extraction(
  extraction_json,
  storage_permission,
  permission_basis,
  raw_text? | raw_url? + raw_excerpt?
)
```

server 順序是 filesystem-first：驗證 → canonical hash/no-clobber publish → 冪等寫圖 →
重投影受影響 edge attributes。依回傳處理：

- `loaded_or_already_complete`：文件與圖完成。只有 `finalize_eligible=true` 才把 doc_id
  加進本次行動 manifest。
- `pending_graph`：檔案已保存但圖／projector 未完成；**不可**加入 finalize manifest。
  用完全相同 payload 重試。不要改字、不要加版本後綴。
- `rejected`：schema、permission、URL、doc_id 或 canonical content 衝突；不可重送不同內容
  覆蓋同 doc_id。

`open_conflict_ids` 非空不代表文件載入失敗。它表示新 assertion 讓某個 edge attribute
成為 open/stale。遠端只把 conflict IDs 與候選證據列入報告；不得自行挑最大 confidence、
不得直接改 resolution JSON／canonical edge。後續由本機 `$evidence-conflict-resolution`
產 proposal，使用者人工核准。

## 5. 行動結束必 Finalize

累積本次所有成功且 eligible 的 doc_ids，最後只呼叫一次：

```text
finalize_research_action(
  report_markdown,
  action_slug,
  commit_headline,
  doc_ids
)
```

- `action_slug` 只能是小寫 ASCII `[a-z0-9_-]`，1–64 字元；不可傳路徑。
- `commit_headline` 是一行、說明研究價值，不放 shell 指令。
- `doc_ids` 只來自本次成功 load 回應；不可傳 client path。
- server 會重新讀 storage permission、要求 master/index/HEAD 與 origin/master 同步，只 stage
  manifest paths + 本次報告，形成一個 commit 後 push。
- `committed_not_pushed` 不等於完成；保留 local commit，回報使用者，讓 session digest
  浮現。不得再開另一個 finalize 把舊 commit 順手推出。
- 工具預設被 `ENABLE_REMOTE_FINALIZE` server-side kill switch 關閉；即使啟用，也必須在
  connector 設定為 **Needs approval**。

## 6. Report 最小骨架

```markdown
# <研究行動標題>

## 為何此時入圖
本次訊號與既有 thesis／disproof 的關係。

## 文件清單
每個 doc_id、canonical URL、storage permission 與簡短 permission basis。

## 搜尋過程摘要
依 source-trace 手冊實際走過的登記表、query、未果路徑與反向證據。

## L8 確認備註
origin_entity／origin_event 如何計數、哪些仍是單源／自報。

## Evidence conflicts
列 open_conflict_ids、候選 assertion/source；沒有則寫「無」。不得在此遠端決議。
```

server 會另補 UTC 入圖時間與重新驗證過的 provenance manifest。
