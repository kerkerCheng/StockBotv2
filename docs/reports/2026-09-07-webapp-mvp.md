# StockBot Web App／API MVP（Phase 2 Step 5）— 交付報告

> 2026-09-07｜標的＝COHR／LYC.AX／6324.T／IQE.L（Coverage Pilot 四檔）
> 判定：**原判 CONDITIONAL GO → 條件已於同日解除 → GO**（見 §14）
> 上一站：[Coverage Pilot](2026-09-07-coverage-pilot.md)｜[Full-chain Adversarial Acceptance](2026-09-07-full-chain-adversarial-acceptance.md)

---

## 0. 一句話

**做出了第一版真正可日常使用的 StockBot：瀏覽器打開一檔股票，看到的是系統已經形成的判讀，
而「點一下不會重跑任何研究」現在是四種互相獨立的機械證明，不是一句自律。**

```
authority（Neo4j／Engine C／三本 private ledger）
     │  python -m webapp materialize        ← 唯一會跑模型的地方（實測 4.2 秒／檔）
     ▼
AlphaInvestmentView → AnalystView → artifact JSON（atomic write，兩個 digest）
     │  python -m webapp serve              ← 純讀：open → json.loads → validate
     ▼
GET /api/v1/{health,meta,stocks,stocks/{ticker}} ＋ responsive Web App
     ▼
Cloudflare Tunnel（既有那條）→ Cloudflare Access → iPhone Safari／桌機 Chrome/Edge
```

實測對比：**materialize 4.2 秒／檔 vs API 讀取 4–8 毫秒**——差三個數量級，
而那正是「request path 是不是真的只是一次讀檔」最直白的證據。

---

## 1. Serving architecture（audit 先行：沒有新增任何平行架構）

**先盤點，不預設技術棧。** 實測 repo 現況：

| 需要什麼 | repo 已有什麼 | 決定 |
|---|---|---|
| HTTP server | `starlette` 1.3.1 ＋ `uvicorn` 0.51（`mcp>=1.28` 的相依，已安裝） | **重用**——本次 `requirements.txt` 一行未加 |
| web UI／static serving | 無 | 新增 `webapp/static/`（vanilla JS，零建置工具鏈、零外部資源） |
| MCP 可重用的 hosting primitive | `mcp_server/graph_mcp.py`（127.0.0.1:8788，走 tunnel） | **模式重用不是程式重用**：同樣的「只綁 localhost、唯一入口是 tunnel」姿態；APP 不 import `mcp_server`（核心不得依賴 peripheral） |
| Cloudflare／tunnel | tunnel `d3074ec2-…`、網域 `minatoyukina.uk`、`cert.pem`、開機自啟 vbs | **重用同一條 tunnel**，只加一條 ingress |
| materialization／cache | 無（`analyst-view --format json -o` 只是使用者自己指定的輸出檔） | 新增 `webapp/`（contracts／store／materialize） |

**不引 FastAPI／Flask／React 的理由不是偏好：** APP 要做的事是「讀一份已經算好的 JSON 並排版」。
它不需要 ORM、不需要第二層 schema 驗證（artifact 驗證住 `webapp/contracts.py`）、不需要前端建置。
那些只會多一套要維護的平行架構——而重構期間的硬約束第 1 條與 L1 講的是同一件事的兩面：
**選型優化能力與可觀測性，不優化「看起來現代」**。

**新檔案：**

```
webapp/
  contracts.py      artifact 契約：必要欄位、兩個 digest、freshness、fail-closed 驗證
  store.py          atomic write ＋ fail-closed read（serve 端唯一的 I/O）
  materialize.py    唯一會跑模型的模組：AnalystView → artifact，含 private path 遮蔽與 overview 投影
  api.py            read-only Starlette app（GET only；無任何寫入路由）
  __main__.py       materialize / serve / status / verify
  static/           index.html · app.js · styles.css（responsive；CSP 只允許 same-origin）
alpha/absence.py            缺席語意封閉字彙（零相依）
alpha/abstention/           「刻意不主張」的 append-only authority
alpha/providers/abstentions.py
deploy/cloudflare/          README（含尚未完成的人工步驟）＋ config.yml.example
```

---

## 2. Materialization contract

**責任鏈刻意分成兩條**，理由不是效能：**點一下就重跑一次研究會讓 request path 有能力改變
（或看起來改變）系統對一家公司的認知**，而「使用者剛才看到的是哪一版判斷」就再也答不出來。

一份 artifact（`library/private/app/analyst_view/<TICKER>.json`，在 ignored 的 private 樹下）帶：

| 欄位 | 作用 |
|---|---|
| `schema_version` | `stockbot-app/analyst-view/1`。讀取端**硬性比對**，不符即 fail closed（artifact 可重建，不背相容包袱，L10） |
| `analyst_view_schema_version`／`source_schema_version` | 上游兩層的版本 |
| `ticker`／`company_id`／`company_label` | 身分。檔名與內容 ticker 不一致 → 拒收 |
| `generated_at`（UTC）／`as_of`／`point_in_time_mode` | 何時算的、以什麼視角算的 |
| `research_context_digest` | 這份判讀站在哪一份研究 context 上 |
| **`content_digest`** | 整份內容的 SHA-256。偵測**半份寫入**與**寫入後被改** |
| **`freshness_identity`** | 只對**認知狀態**取雜湊（as-of／context digest／read model 版本／readiness／refresh overall） |
| `readiness`／`refresh` | 直接抄 `AnalystView` |
| `overview` | 清單卡片的投影（**純選取，零算術**） |
| `view` | 完整 `AnalystView.to_dict()` |
| `materializer` | 版本與「這是 derived cache 不是 authority」的自述 |

**為什麼是兩個 digest 而不是一個：** 價格每天都動，但那**不代表我們的認知變了**。
共用一個訊號就會讓其中一件永遠讀不出來（L12：一個表示不得承載兩種語意）。
`freshness_identity` 相同 ＝ 視角、研究 context、read model 版本、readiness、refresh 狀態都沒變。

**四條硬要求，逐條有測試：**

1. **atomic write** — 先寫 `.<name>.tmp` 再 `os.replace`；`test_write_is_atomic_and_leaves_no_temp_files`
   斷言目錄裡只剩下最終檔。
2. **malformed／partial fail closed** — 解析失敗／版本不符／digest 不合／缺必要欄位一律
   `ArtifactUnavailable`。實測把檔案砍半 → `JSON 解析失敗`，**不回半份**。
3. **cache 不是 authority** — 刪掉重跑就回來；`materializer.note` 把這句話寫在資料裡。
4. **stale 是狀態不是錯誤** — 超過 `STOCKBOT_APP_MAX_AGE_HOURS`（預設 24h）標 stale，
   **照樣回內容，絕不重建**。`test_stale_artifact_is_served_not_rebuilt` 同時斷言「回了內容」
   與「磁碟一格未動」。

**private path 在 materialize 端遮蔽一次。** read model 的理由句會寫出 authority 的檔案路徑
（IQE.L 的 `research` 段逐字寫「找不到 session 判斷檔（library/private/alpha/judgments/…）」）。
那對開發者有用，但它是 private filesystem 結構。遮成 `«private-authority»`，**其餘文字逐字保留**。
實測：四份 artifact 裡 `library/private` 出現 **0 次**，IQE.L 有 **18 處**被遮。
⚠ 在 materialize 端做一次，而不是讓每個消費端各自記得要遮（L16）。

**overview 是選取不是計算。** `test_overview_contains_no_arithmetic_on_the_numbers` 用 `is` 比對
每一格與來源 `Datum` 的值——只要 overview 自己算一次（哪怕結果一樣）就會紅。
單位原樣帶著走：`dependencies.quote_unit` 是**欄位**不是要 parse 的句子
（GBp 與 GBP 差 100 倍，字串解析正是 Coverage Pilot §3.1 那個 100 倍陷阱的近親）。

---

## 3. API endpoints / schema

版本化前綴 `/api/v1`。**只有 GET**——任何寫入動詞在路由層就是 405（實測 POST／PUT／PATCH／DELETE
對三個路徑共 12 組全部 405）。

| Endpoint | 回什麼 |
|---|---|
| `GET /api/v1/health` | `status`／`api_version`／`artifact_schema_version`／`materialized_count`／request-path 自述。**不透露研究內容、不透露 artifact 目錄路徑** |
| `GET /api/v1/meta` | 封閉字彙（`absence_kinds` 11 種、`settled_absence_kinds`、`accounting_basis_display`、六個消費者問句、`weak_input_rules`、readiness 三態）＋ freshness 規則 ＋ **`not_offered`（本 APP 明確不做什麼）**。字彙由 materialize 端寫成 `.meta.json`——**APP 不維護第二份對照表**（L16） |
| `GET /api/v1/stocks` | 清單：每檔一份 `overview` ＋ `freshness`；壞掉的 artifact 進 `unavailable` 陣列**帶理由與修法**（INV-3：不靜默丟棄）；＋ `correlation_warning` |
| `GET /api/v1/stocks/{ticker}` | 完整 artifact ＋ `freshness` ＋ `correlation_warning`。讀不到 → **503**＋`{kind, ticker, reason, remedy, note}` |

**API 回傳與 artifact 是 semantic equivalent，不是第二份投影。**
`test_api_response_is_semantically_equal_to_the_artifact` 斷言：回應的 key 集合 ＝ artifact 的 key 集合
**加上剛好兩個**（`freshness`／`correlation_warning`），且每一個共同 key 逐值相等。

**九種語意不得被壓成一句 unavailable。** overview 的每一格帶
`{value, status, absence_kind, unit, as_of, reason}`；readiness 帶 `blockers`（字串，給人讀）
**與** `blocker_details`（欄位化，給機器讀），型別層強制兩者一一對應——長度不同就是兩份判斷。

---

## 4. Web App 資訊階層

清單（`#/`）→ 明細（`#/<TICKER>`）。純 hash 路由，無框架、無外部資源。

**清單卡片**（每檔）：ticker ＋ 公司名 ＋ readiness 徽章（＋stale 徽章）→
現價（含報價單位）／Future target（**有才顯示**）／隱含報酬（**有才顯示**，年化在副標）→
最重要的一條 blocker／flag（含缺席語意徽章；還有幾項另外標明）。

**明細頁**（依 Analyst Consumer hierarchy，首屏就要回答那五個問題）：

| 順序 | 區塊 | 回答什麼 |
|---|---|---|
| 0 | **判讀狀態** | blocked 時逐條寫「**卡在哪一層 ＋ 為什麼**」，不是只放紅燈 |
| 1 | **① 頭條** | 現價 → future target → 隱含報酬（simple／年化）；缺席時把「為什麼沒有」放在跟數字一樣顯眼的位置；authority 自組的那句話（註明出處） |
| 2 | **② 內部 vs 共識** | 我們的預測／同期可比共識／兩者落差（前三組直接展開；其他期間與市場脈絡收進 drill-down） |
| 3 | **③ 為什麼／最弱假設** | 脆弱輸入清單（每條寫出它被哪一條**宣告好的列入規則**挑進來） |
| 4 | **④ 研究現況** | thesis／lifecycle／disproof（含核查頻率與觸發後動作）／催化劑／五軸 |
| 5 | **⑤ Entry（optional）** | 有判準才有門檻價；沒有就明說「optional，不影響 readiness」 |
| 6 | 新鮮度 | materialize 時間、視角、refresh 整體狀態、兩個 digest |
| 7 | 「這份判讀不是什麼」 | 直接列 `limits` |

formula／provenance／evidence／epistemics／算式逐格／敏感度**全部收進 `<details>` drill-down**——
229KB 的完整卡不是拿來「看懂一檔」的東西。

**UI 只改資訊階層，不產生新的 summary judgment：**
- 頭條那句話取自 `implied_return.epistemics.one_sentence`，並在畫面上註明「authority 自組，不是本畫面造的句子」。
- 缺席語意的中文說明來自 `/api/v1/meta`；前端只有一份**縮寫標籤**對照（畫面寬度所需），完整說明一律來自 API。
- `test_frontend_contains_no_arithmetic_on_research_numbers` 掃描 `app.js`：沒有 `fair_value /`、
  `/ price`、`Math.pow`、`365.25`、`** (`……唯一的數值動作是排版與 `×100` 的百分比呈現。
- `test_frontend_never_hardcodes_a_hurdle_or_target_multiple`：`0.10`／`0.15`／`0.20`／`target_pe` 一個都不在。

---

## 5. 四檔實際呈現（runtime canonical data，2026-09-07 實跑）

| | COHR | LYC.AX | 6324.T | IQE.L |
|---|---|---|---|---|
| 公司 | Coherent Corp. | Lynas Rare Earths Ltd. | Harmonic Drive Systems Inc. | IQE plc |
| readiness | **ready** | **ready** | **blocked** | **blocked** |
| 現價 | **281.86 USD**（bar 09-04） | **15.62 AUD**（bar 09-07） | **5,970 JPY**（bar 09-07） | **47.518 GBp**（bar 09-07） |
| Future target | **223.6 USD** @ 2027-06-30 | **9.949 AUD** @ 2027-06-30 | **無**（刻意） | **無** |
| 隱含報酬 | **−20.7%**（年化 −24.6%） | **−36.3%**（年化 −42.7%） | 無 | 無 |
| 缺席語意 | — | — | **`deliberate_abstention`（settled）** | **`upstream_unavailable`** |
| 口徑（raw → 呈現） | `non_gaap` → 公司調整後 | `gaap` → As reported（法定財報口徑） | `gaap` → As reported | `non_gaap` → 公司調整後 |
| entry | `missing`（optional，不進 blockers） | 同左 | 同左 | 同左 |
| artifact 大小 | 193,768 B | 181,981 B | 158,187 B | 91,701 B |
| API 回應 | 139,324 B / 7.2 ms | 131,812 B / 6.4 ms | 122,114 B / 5.5 ms | 65,550 B / 4.1 ms |

**與 prompt 給的 baseline 逐項對照：** COHR ✅（281.86 → 223.60 @ 2027-06-30，−20.7%）；
LYC.AX ✅（A$15.62 → A$9.95，−36.3%）；6324.T ✅ blocked at valuation，
且畫面**同時**顯示 internal EPS 47.32 與 implied multiple 126.2x（在 ② 與 ③ 區）
——**沒有為了讓 UI 有 target 而補任何倍數**；IQE.L ✅ GBp 正確呈現為 `47.518 GBp`，
**沒有**與 GBP 混為同尺度。

> ⚠ **一處必須說清楚的差異：prompt 寫 IQE.L 是「blocked at model applicability」，
> runtime 實際回報的是 `upstream_unavailable`。兩者都不是錯的，但只有後者是今天可證的。**
> Coverage Pilot §2.3 確立的「唯一登記的 method 要求正 forward EPS，而共識兩年皆虧損」是**結構事實**；
> 但 IQE.L **刻意沒有建立任何 operating assumption**（研究決定：流動性／going-concern 未評估，pq2 [486]），
> 所以內部 EPS 本身就缺席，估值鏈**在方法適用性被檢查之前就停住了**——
> `method_applicability()` 收到 `None` 時回 `None`，缺料走它自己的路徑（那是 Step 3.2 刻意的分野）。
> 把 UI 標成「方法不適用」會是**一個系統今天推導不出來的結論**，正是 L11-2 記過的
> 「對外部 claim 嚴、對自己引用鬆」。所以畫面誠實寫：**上游缺料——內部 eps 缺席：缺 nci_attribution 假設**。
> `method_not_applicable` 這個語意**存在且已測**（`test_method_applicability_is_still_a_separate_semantic_from_missing_data`），
> 只是 IQE.L 今天走不到那一格。等 [486] 完成、operating assumption 建立之後，這一檔會自動往下走一層
> 並停在方法層——**那時 UI 上的字會自己改變，不需要改任何呈現程式碼**。

---

## 6. Intentional absence 怎麼表示（語意債 A）

**新增 `absence_kind`：與 `status` 正交的第二個語意軸**（`alpha/absence.py`，封閉字彙 11 種）。
`status` 回答「這一格能不能用」，`absence_kind` 回答「它**為什麼**沒有」。

**由產生缺席的那段程式自己宣告**，消費端不得 parse 理由句去猜（L16）：

```
build_valuation 走到哪個分支 → ValuationResult.absence_kind
        ↓ 上游缺席時**繼承**，不降級成「還沒寫」
build_implied_return          → ImpliedReturnResult.absence_kind
        ↓
Datum.absence_kind / SectionMeta.absence_kind（read model）
        ↓ 宣告好的挑選規則（第一個 status 等於 panel status 的來源 section）
AnalystPanel.absence_kind / AnalystBlocker（consumer）
        ↓
overview.future_target.absence_kind / readiness.blocker_details[].absence_kind（API）
        ↓
畫面上的徽章：「刻意不主張」（紫）／「還沒寫」／「上游缺料」／「方法不適用」
```

⚠ **`not_applicable` 的預設刻意是 `not_applicable_unspecified`**：它今天同時被 PIT 與方法層使用，
猜任何一邊都是替 authority 造一個它沒說過的區別。知道自己是哪一種的呼叫端要**明示**。

**「刻意不主張」需要一筆 append-only 紀錄，不能在呈現層打標籤。**
新增 `alpha/abstention/`（`library/private/alpha/abstentions/<TICKER>.jsonl`），三條型別層強制：

1. **結構上不可能攜帶數字** — `_assert_no_value_fields` 在 import 當下掃描欄位名，長出
   `value`／`target_pe`／`multiple`／`fair`／`estimate` 之類的欄位是 **import 失敗**，不是 lint 警告。
2. **`reason` 與 `revisit_when` 都必填** — 沒有「什麼證據出現才會改寫」的 abstention 是一個
   永遠不會響的火警警報（L7：disproof 要附核查頻率與觸發後動作）。
3. **`layer`／`subject` 是封閉字彙** — v1 只有 `valuation.forward_earnings_multiple.target_pe`，
   否則它會變成「任何一格都可以宣布自己是刻意留白」的萬用擋箭牌。

**它不是第二份 ValuationAssumption authority。** 後者擁有「目標倍數是幾」；它只擁有「我們不主張」。
**宣告之後 fair value 仍然缺席、readiness 仍然 `blocked`**——`settled` 只回答「該不該花力氣去補」，
不讓判讀變好（`test_settled_absence_does_not_make_readiness_better`）。

**實際寫入（pq2 [487]，go）：** `ab_fc42c0f42c2df1ce`，6324.T／`forward_earnings_multiple.target_pe`／
FY2027（至 2027-03-31）。`reason` 與 `revisit_when` **逐字引自已提交的**
[`2026-09-07-coverage-pilot.md`](2026-09-07-coverage-pilot.md) §2.2 與 §6——
本次不新增任何知識主張，只把既有研究結論從散文改成機器可讀。
授權：使用者在 Step 5 prompt §5A 明示「6324.T 的 valuation 沒有結果不是忘了填，而是刻意不 assert」，
依 AGENTS「使用者主動指示＝已授權」，鑄號僅為稽核、受理時即 resolve。

**實測效果：** 6324.T 的 headline blocker 由
`missing / not_yet_recorded`（「尚未寫入任何估值假設」）
→ `missing / deliberate_abstention`（「刻意不主張目標倍數：126.2x 錨不住…｜什麼會改寫它：FY2029+ 獲利能力證據…｜宣告於 2026-09-07（ab_fc42…）」）。
**readiness 一格未動**（仍 `blocked`），fair value 仍 `None`。

---

## 7. Accounting basis 怎麼表示（語意債 B）

**不改字彙**：`ACCOUNTING_BASES = ("gaap", "non_gaap", "not_applicable", "unverified")` 是
**contract identity**——它是三本 private append-only ledger 每一筆紀錄身分的一部分，
改字彙等於改既有紀錄的身分（L10）。

**加一層呈現別名**（`ACCOUNTING_BASIS_DISPLAY`），且 label **一律不含準則名稱**：

| raw（contract，稽核用） | label（面向使用者） |
|---|---|
| `gaap` | **As reported（法定財報口徑）** |
| `non_gaap` | **公司調整後（adjusted，非法定口徑）** |
| `not_applicable` | 不適用（這一格沒有口徑語意） |
| `unverified` | 口徑未確認 |

畫面上 `gaap` 那一列同時顯示註記：**「系統只記錄『法定財報 vs 公司調整後』這個區別，不主張它是
US GAAP／IFRS／AASB／日本基準——authority 裡沒有那一格，猜一個就是造一個沒人宣告過的事實。」**

`raw` 永遠一併輸出（畫面寫「口徑 As reported（法定財報口徑）（contract 值 gaap）」）。
未登記的值**原樣顯示、不編故事**；`None` 顯示「未宣告」。
測試 `test_display_alias_never_claims_a_standard_the_authority_cannot_support` 逐個 label 掃
`US GAAP`／`IFRS`／`AASB`／`日本基準`／`J-GAAP`／`台灣 IFRS` 六個字串。

**順帶修掉一個相鄰的呈現缺陷：** `company_label` 一直是 `co:coherent（COHR）`——
把內部 ID 當人看的名字，正是 AGENTS 明文禁止的「假設使用者能從 `co:*` 自行還原主詞」。
registry 新增 `display_name`（**只是名字，不是新的知識主張**——任何人讀一次公司財報封面都得到同一個字串，
屬 AGENTS 的 mechanical 判準），四檔各補一筆。**沒登記就退回 `co:*（ticker）`，不從 ID 猜名字**
（`co:iqe` → 「Iqe」是編出來的）。

---

## 8. Freshness ／ cache invalidation

| 使用者看到 | 意思 | 下一步 |
|---|---|---|
| `ready` | 核心四段都有內容，且沒有被標記需要動作 | — |
| `ready · 有旗標` | 有內容，但至少一段 stale／review_required／not_applicable | 看旗標那一條寫什麼 |
| `blocked` | 至少一段核心缺內容 | **看 `absence_kind`**：`還沒寫` 去研究／`刻意不主張` 不用動作／`方法不適用` 補資料解不掉／`上游缺料` 去補上游 |
| `stale` 徽章 | artifact 年齡 > 24h（可調） | 重跑 `python -m webapp materialize` |

**兩個時間軸刻意分開：**
- **artifact 年齡**（`freshness`）＝「這份快照多舊」。純算術：`now − generated_at` vs 宣告好的門檻。
- **`refresh.overall`**＝「什麼變了、哪些研究成果需要重看」。由 refresh 引擎在 materialize 當下算好並寫進
  artifact，**不是**由 APP 在 request 時判斷。

**cache invalidation 是明確動作，不是自動行為。** 沒有 TTL 自動重建、沒有背景 worker、
沒有 cache-miss fallback。`test_cache_miss_returns_503_instead_of_rebuilding` 同時斷言
「回 503」與「磁碟一格未動」與「檔案沒被建立」。

---

## 9. Request path 如何證明「no LLM / no write / no recomputation」

四種**互相獨立**的證明（`tests/test_webapp_request_path.py`，25 條）。任何一種單獨都會被繞過：

| # | 方法 | 擋什麼 | 實測 |
|---|---|---|---|
| 1 | **import 靜態掃描** | serve 端三個模組的 import 是 allowlist（只有 stdlib ＋ starlette ＋ `.contracts`／`.store`） | `alpha.*`／`briefing.*`／`neo4j`／`yfinance`／`anthropic`／`engine_c`／`decision_lab` **一個都不在** |
| 2 | **runtime 模組哨兵** | **函式內的延遲 import**（靜態掃描擋不掉） | 打完 9 條 request，`sys.modules` 對 20 個禁止前綴的新增量 ＝ **0** |
| 3 | **檔案系統快照** | **寫入** ＋ **cache-miss 自動重建**（兩者都會改檔案） | request 前後對 artifact 目錄與 `library/private/` 取樹狀雜湊，**完全相等**。另有「守衛的守衛」證明雜湊真的會因任何改動而變 |
| 4 | **socket 封殺** | **抓現價／共識** ＋ **連 Neo4j bolt** | request 期間 `socket.connect`／`create_connection` 直接 raise，回應**照樣完整正確**（−0.2 的隱含報酬照回、清單照回、503 照回） |

⚠ 第 4 條攔的是 `connect` 而不是 socket 建構子：TestClient 的 event loop 自己要用一對 loopback socket，
攔建構子會攔到測試腳手架而不是被測物（L15-1：gate 攔下的必須是它想攔的東西）。
且**先自我量測**——`with pytest.raises(AssertionError): socket.create_connection(...)` 證明封殺真的生效，
否則「網路關掉還是綠的」可能只是因為根本沒關掉（L14）。

**加上：** 沒有任何寫入路由（12 組 method×path 全部 405）；`ArtifactStore.write` 不被 `api.py` 呼叫；
`test_api_response_is_semantically_equal_to_the_artifact` 證明回傳與 artifact 逐值相等——
**沒有在 request 時重組任何東西**。

---

## 10. Cloudflare deployment 狀態

**重用了什麼：** 既有 tunnel `d3074ec2-c2a3-4782-9c54-8604289b5fd3`、網域 `minatoyukina.uk`、
`~/.cloudflared/cert.pem` 與 credentials、開機自啟 `stockbotv2-graph-services.vbs`。
**`neo4j.minatoyukina.uk` 與 `mcp.minatoyukina.uk` 兩條 ingress（含 MCP 的 `httpHostHeader` 改寫）
一個字都沒動。**

**規劃的 hostname：** `stockbot.minatoyukina.uk` → `http://localhost:8790`（MCP 是 8788，刻意錯開）。

**已完成（本機，全部實測）：**
- `python -m webapp serve` 在 `127.0.0.1:8790`（預設）跑得起來，四檔全部可讀。
- 綁非 loopback 介面必須明示 `STOCKBOT_APP_ALLOW_PUBLIC_BIND=1`，否則**程式拒絕啟動**並說明理由。
- `deploy/cloudflare/config.yml.example`：加入 StockBot 之後的**完整** ingress（新增一段在 catch-all 之前）。
- `deploy/cloudflare/README.md`：逐步程序、驗收指令、安全邊界、殘餘風險。

**⚠ 還沒做的三步（需要使用者本人操作，本報告不偽造完成）：**

1. **Cloudflare Zero Trust → Access → 建立 self-hosted application**
   （`stockbot.minatoyukina.uk`，policy allow `c3035281@gmail.com`，登入方式最省事是內建的
   One-time PIN，**不需要任何 OAuth 設定**）。
2. **`cloudflared tunnel route dns d3074ec2-… stockbot.minatoyukina.uk`**（建立 CNAME）。
3. **編輯 `C:\Users\Cheng\.cloudflared\config.yml` 加一條 ingress 並重啟 cloudflared**
   （重啟期間 MCP／Neo4j hostname 會中斷數秒，挑沒有排程的時間）。

> **步驟 1 必須排在步驟 2 之前。** DNS 一建立 hostname 就開始解析；那時若還沒有 Access policy，
> 這個網址在建立到設定完成之間是**公開可讀**的。順序反過來就是把 private 研究內容短暫公開。
> 這也是本次**刻意不代為建立 DNS 記錄**的理由（`cert.pem` 在本機、指令跑得動，但那一步的
> 安全前提不在我這邊）。

**驗收指令已寫在 README**，其中最關鍵的一條：未登入時 `curl -sI https://stockbot.minatoyukina.uk/api/v1/health`
應該回 302 導向 Cloudflare Access；**若直接回 200 ＋ JSON，代表 Access 沒生效，要立刻停用 DNS**。

**token／credential：** `git ls-files | grep -i cloudflared` 為空；
`deploy/cloudflare/` 只有 hostname 與 port，沒有任何 token。

---

## 11. Security boundary

| 層 | 內容 |
|---|---|
| **本機綁定** | 只聽 `127.0.0.1:8790`；家用路由器零入站。綁其他介面需明示環境變數，否則拒絕啟動 |
| **外部認證** | Cloudflare Access（第一版**不自己做帳號密碼系統**，這是 scope 決定不是疏漏） |
| **只讀** | 無 POST／PUT／PATCH／DELETE 路由；request path 無 LLM、無 authority write、無外部抓取、無模型執行（四種證明） |
| **無任意檔案存取** | ticker → 檔名走**字元 allowlist**（不是過濾——前者要窮舉攻擊面，後者不用）＋ 解析後仍須在 artifact 目錄內；static 檔案是三個檔名的 allowlist。實測 `..%2f..%2fetc`／`/static/../api.py`／`/static/.meta.json` 全部 404 |
| **private path 不出門** | materialize 端遮蔽；實測 API 三個端點的回應中 `library/private` 出現 0 次 |
| **錯誤回應** | 固定形狀 JSON。`HTTPException` 走 `_SAFE_MESSAGES`；未預期例外走 catch-all，**只回 `request failed`**，不回 `str(exc)`（它可能含檔案路徑或查詢內容）。實測：把 store 弄成 raise 一個含完整 private 路徑的例外，回應裡 `boom`／`library` 皆 0 次 |
| **回應 header** | `Cache-Control: no-store`、`X-Frame-Options: DENY`、`nosniff`、`Referrer-Policy: no-referrer`、CSP `default-src 'self'` ＋ `frame-ancestors 'none'`（前端零外部資源，所以 CSP 可以收到最緊） |

**四個人工 gate 不因為多了一個畫面而放寬**：graph admission／Engine C 觀測寫入／thesis mutation／
live choice-fill 全部不經過 APP，APP 也沒有任何路徑可以觸發它們。

---

## 12. Latency ／ artifact ／ API size（只證明是廉價 read path，不做 premature optimization）

| 量測 | 值 |
|---|---|
| **materialize（跑完整條鏈）** | **4.20–4.31 秒／檔**（四檔實測；含 Neo4j＋Engine C＋三本 ledger＋四個模型＋refresh） |
| **API 讀取延遲（localhost，含 curl 開銷）** | `health` **1.6 ms**｜`meta` **1.4 ms**｜`stocks`（清單，4 檔）**16.5–17.4 ms**｜單檔明細 **4.1–8.4 ms** |
| **artifact 大小** | COHR 189 KB｜LYC.AX 178 KB｜6324.T 155 KB｜IQE.L 90 KB |
| **API 回應大小** | 清單 **11.8 KB**（4 檔）｜單檔明細 65–139 KB（無縮排，比 artifact 小約 28%） |
| **靜態資源** | `index.html` 904 B｜`app.js` 27.6 KB｜`styles.css` 7.0 KB（**零外部請求**） |

**結論：4.2 秒 vs 4–8 毫秒，差三個數量級。** 這就是「request 是廉價 read path」的全部證據；
不做任何進一步優化（清單 16 ms 對一個單人自用 APP 沒有任何問題，
而過早優化會讓「只是讀一個檔」這件簡單的事變複雜）。

---

## 13. 驗收（tests / mutation / audit / golden）

| 項 | 之前 | 之後 |
|---|---|---|
| **pytest** | 1,884 passed／1 skipped | **1,989 passed／1 skipped**（＋105：webapp materialize 26、request path 25、API 24、absence semantics 30） |
| **突變非空跑** | 163 個、空跑 0 | **180 個、空跑 0**（新增 17，逐一實跑證明會紅） |
| **`audit invariants`** | FAIL 0｜PASS 12｜SKIPPED 0 | **FAIL 0｜PASS 12｜SKIPPED 0**（共檢查 2,100 筆） |
| **golden fixtures** | 14/14 | **14/14；漂移 1（EXPECTED_CHANGE）** |
| **既有測試需調整** | — | **2 處**（兩條 import allowlist，見下） |

**golden 漂移逐項解釋（EXPECTED_CHANGE）：** 只有 `normal_company`，且 diff 只有**一行**——
registry entry 多了 `"display_name": "Coherent Corp."`。這是 §7 的呈現修正，不是行為回歸。

**兩處既有測試調整（放行與收緊同時發生，L15）：**
`briefing/alpha_view/contracts.py` 原本被要求「純 stdlib」，現在多 import 一個 `alpha.absence`
（缺席語意的封閉字彙 SSOT）。**放行的同時補了一條斷言**：那一支自己也必須零相依
（`_imports(absence) <= {"__future__", "typing"}`）——否則這條例外會變成把整個 `alpha` 拖進呈現層的後門。
允許它的理由是**不要在呈現層複製第二份字彙表**，而那正是 L16 記過三次的形狀。

**17 個新突變逐條守著什麼**（全部實跑「改一行 → 測試變紅 → 還原」）：

| 突變 | 守的是 |
|---|---|
| 缺席語意猜 `not_applicable` 是哪一種 | 猜任一邊都是替 authority 造一個它沒說過的區別 |
| 「刻意不主張」被當成待辦（settled 集合清空） | 使用者必須分得出「該去補」與「這已經是答案」 |
| abstention 不必說什麼會改寫它 | 沒有 revisit 條件 ＝ 永遠不會響的火警警報（L7） |
| abstention 長出可裝數字的欄位 | 繞過 ValuationAssumption 的估值後門 |
| 估值層不宣告自己走了哪個缺席分支 | 消費端只能回頭 parse 散文（L16） |
| 撤回 abstention 之後語意沒有回復 | 撤回若不生效就是按下去沒反應的按鈕（L13-2） |
| 口徑別名替 authority 宣稱 US GAAP | 替 authority 主張它沒有的東西 |
| artifact digest 檢查被拿掉 | 被改過／半份的 artifact 被當成正常判讀 |
| artifact 缺欄位也照服務 | partial write 必須 fail closed |
| artifact 讀不到卻回成正常的 200 | 「讀不到」與「沒有研究結論」不得同形（L12） |
| ticker 檔名改成過濾而不是 allowlist | arbitrary file access |
| serve 端 import 了會重跑模型的東西 | 「點一下不重跑研究」的第一道證明 |
| private 路徑遮蔽被關掉 | private filesystem 結構經 HTTP 外洩 |
| overview 把缺席補成 0 | Missing != Zero（0 看起來比空白「完整」） |
| 安全 header 被拿掉 | private 內容被中介快取／被別站嵌入 |
| APP 綁到所有介面而不需明示 | 裸露 origin ＝ 把 private 研究內容公開 |
| 錯誤回應吐出內部訊息 | 例外訊息可能含檔案路徑或查詢內容 |

> ⚠ **其中一條原本是空跑，已修**：「錯誤回應吐出內部訊息」第一版指向
> `test_errors_never_leak_paths_tracebacks_or_credentials`，但那條只走 404／503（`HTTPException` 處理器），
> **catch-all 處理器沒有任何測試看得到**。補了一條專門觸發未預期例外的測試
> （並用 `raise_server_exceptions=False` 取得真實用戶端會看到的回應）之後才通過。
> 這是 L14 的直接應用：**未被量測的守衛不得享有默認信任，我自己寫的守衛也不例外。**

**Baseline 回歸（Coverage Pilot 的硬性驗收：每加一層，既有那幾檔的數字必須 0 格改變）：**
COHR 核心 10 格**一格未動**——
內部 FY2027 EPS **8.9441**／共識 **9.4163**／Q4 **weak 0.25 current**／fair value **223.6034**／
現價 **281.86**／value_date **2027-06-30**／simple **−20.67%**／年化 **−24.64%**／
entry `missing` 不進 blockers／readiness **ready**；`judged_context_matches` **True**、
refresh overall **current**。

---

## 14. 判定：原判 **CONDITIONAL GO**，條件已於同日解除 → **GO**

> **2026-09-07 稍晚更新（原判定逐字保留在下方，不改寫）：** 使用者已完成 Cloudflare 端步驟，
> **`https://stockbot.minatoyukina.uk` 已可從外部使用**，prompt Goal 的那條路徑成立。
>
> | 檢查 | 實際輸出 |
> |---|---|
> | DNS | `stockbot.minatoyukina.uk` → `104.21.83.81`／`172.67.217.216`（Cloudflare 代理） |
> | **未登入** | **`302` → `bold-…cloudflareaccess.com/cdn-cgi/access/login/stockbot.minatoyukina.uk`** |
> | 登入後 | 四檔判讀清單（使用者實測「能開」） |
> | `mcp.minatoyukina.uk` | `404`——**正常**（path token 未帶），既有 MCP 未被打壞 |
> | `~/.cloudflared/config.yml` | 新增一條 `stockbot` ingress；`neo4j`／`mcp` 兩條（含 `httpHostHeader`）一字未動；catch-all 仍在最後；備份 `config.yml.bak` 存在 |
> | 本機直連 | `http://127.0.0.1:8790/api/v1/health` → `{"status":"ok",…}` |
>
> **仍未做、但不影響判定的一項：** Google OAuth（步驟 0）。目前登入方式是 Cloudflare 內建的
> 一次性 PIN，**認證邊界一樣是 Access、原則一樣只放行單一 email**——Google 只是把「等信收驗證碼」
> 換成「一鍵」，屬 UX 不屬安全邊界。位置已確認在 **Integrations → Identity providers**（新版介面
> 把它從 `Settings → Authentication → Login methods` 搬走了）。
>
> ⚠ **介面路徑已回填 `deploy/cloudflare/README.md`**：Cloudflare 已把 Zero Trust 主控台改名
> **Cloudflare One** 並重排側欄，本報告初版寫的是舊版路徑。實地確認過的三條已標 ✅，
> 未驗證的（撤銷 session）明確標成「未實地驗證」——**不把猜測寫成事實**。

### 原判定（2026-09-07 交付當下，逐字保留）

**GO 的部分（本機，全部實測完成）：**
- 四檔 materialize ＋ serve ＋ 瀏覽器實際渲染（headless Edge dump-DOM 驗證清單頁與三張明細頁）。
- USD／AUD／JPY／GBp 四種報價單位正確呈現，GBp 未與 GBP 混為同尺度。
- ready／blocked、intentional absence、Missing != Zero、entry optional 不影響 readiness——全部實測。
- 6324.T／IQE.L **沒有任何假的 fair value**。
- request path 四種獨立證明全綠；安全邊界逐條實測。
- 全套測試、突變、audit、golden 全部通過，baseline 0 格改變。

**CONDITIONAL 的部分：Cloudflare 端三個人工步驟未執行**（§10）。
在那之前，APP 只能在本機 `http://127.0.0.1:8790/` 使用——
**iPhone 從外面連不到，而 prompt 的 Goal 明寫「iPhone → private Cloudflare hostname → APP」。**
所以本 Step 不宣稱那條路徑已完成。三步做完後跑 README 的四條驗收指令即可轉 GO。

**⚠ 一個誠實的邊界：** 目前只 materialize 了四檔。要看別的公司必須先跑一次 materialize；
APP **不會**替你補（那正是它不做的事）。全 cohort 的 materialize 排程是下一輪的事，
且它需要先走 sandbox impact review——本 Step 刻意不做。

**刻意不做（scope exclusion 逐項確認）：** runtime chatbot／LLM、broker、買賣、部位尺寸、
Portfolio 排序、FY2028 model 擴充、Valuation v2、Post-MVP Graph Alpha Edge（A–H 一項都沒碰）、
[486] IQE going-concern 研究、全 cohort 覆蓋擴充、原生 iOS／Android app。

---

## 15. 本次寫入的 authority（稽核清單）

| 什麼 | 在哪 | 授權 |
|---|---|---|
| `ab_fc42c0f42c2df1ce`（6324.T 估值 abstention） | `library/private/alpha/abstentions/6324.T.jsonl`（private，append-only） | pq2 **[487] go**，receipt `authority:abstention_ledger;ref:ab_fc42c0f42c2df1ce`。理由與 revisit 條件逐字引自已提交的 coverage-pilot 報告 |
| `display_name` ×4（Coherent／Lynas／Harmonic Drive／IQE） | `config/company_identity.json`（tracked） | mechanical（公司自己的名字，任何人重讀都得到同一個字串），不需 pq2 |
| materialized artifacts ×4 ＋ `.meta.json` | `library/private/app/analyst_view/`（ignored） | **derived cache 不是 authority**，刪掉重跑就回來 |

**沒有動的：** 圖（零新增節點／邊）、Engine C ledger、thesis／lifecycle、Decision Store、
資本或部位、`ACCOUNTING_BASES` 字彙、既有三本假設 ledger 的任何一行。
