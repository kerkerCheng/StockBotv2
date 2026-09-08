# 呈現責任重切 B1：瓶頸排序搬進 APP（`ranking` state artifact）

**日期：** 2026-09-08　**Zoom／Review：** Z3 zoom-out 定案後，本 Step 以 Z1／R0 實作　**Verdict：** GO

## 1. 背景（為什麼動這一刀）

Daily Brief 誕生時（2026-07-22）沒有 APP，唯一觸及使用者的管道是對話＋Discord，所以每個「使用者需要看得到的
東西」都塞進 daily。實測 2026-08-31 那份 brief：具名 section 共 14,436 字，**持久狀態佔 64%**
（Alpha 四 pane 3,958／Beta 3,434／外部事件 1,117／賣出側 562／無事 126），決策＋研究進度只佔 36%。
使用者要的心跳（今天處理了什麼新資訊、研究走到哪）被昨天和今天一樣的東西包在中間。

判準一句話：**昨天和今天一樣的住 APP（想看時看），今天變了的＋要你決定的住 Daily（你每天讀）。**

使用者定案（2026-09-08）：
1. **pq2 完整四段留在 Daily**——核准載體是對話；APP 無寫入端點，把待核准放 APP 只是多一次摩擦。
2. **Beta 搬 APP**，呈現走常見的資產分布圖＋折線；AGENTS 的 Beta 契約在 Phase C 同一 commit 改。
3. 第一個 Step＝B1（`ranking` kind）。理由：最小的一刀，卻直接測試「一個 pane 從 Daily 搬到 APP 長什麼樣」；
   零 unattended 變更、Daily 照印（不會踩 L13：管子只接一頭）；搬的正是 2026-08-19 事故的主角。

研究方向（pq1 drain 排什麼、research-drain 閉包）與本項正交，一行沒動。

## 2. 做了什麼

| 層 | 變更 |
|---|---|
| `webapp/contracts.py` | `STATE_SCHEMA_VERSIONS`（封閉 kind 字彙，目前只有 `ranking`）、`STATE_REQUIRED_FIELDS`、`state_freshness_identity`、`validate_state_artifact`（與單檔同一套 fail-closed） |
| `webapp/store.py` | `StateArtifactStore`（`library/private/app/state/<kind>.json`）；`resolve_state_dir` 是**唯一**解析規則（明示 > analyst 目錄下的 `state/` > 預設）；atomic write 抽成兩個 store 共用 |
| `webapp/materialize.py` | `build_ranking_artifact`（純函式，每格照抄、沒有算術）＋ `materialize_ranking`（與 `python -m query.bottleneck` 同一個 driver／`fetch_assertions`／registry；支援 `--as-of`，排除計數帶在 artifact 內） |
| `query/bottleneck.py` | 已知限制、兩份排序說明、無需求錨讀法、落差判準（可行動名次比純結構低 ≥2）、空產業組抽成常數／函式——**markdown 與 artifact 同源**（L16） |
| `webapp/api.py` | `GET /api/v1/ranking`（讀不到 503＋remedy；排不出任何一列是 200＋`top_pick=null`＋理由，兩者不同形）；`meta`／`health` 宣告 state kinds；`not_offered` 改為「不重算排序」 |
| `webapp/__main__.py` | `materialize --ranking`、`--state-dir`；`status`／`verify` 列 state artifact 與缺席 kind |
| `webapp/static/` | 導覽「單檔判讀／瓶頸排序」；`#/ranking` 畫面：首選 → 已知限制（不摺疊）→ 可行動排序表 → 純結構排序表（落差欄）→ 產業分組（相關性警告、空組、無錨讀法）→ 需求鏈 → 新鮮度與 authority → 這份排序不是什麼。`sole_source` 三態（true／有第二來源／**未填**）分開顯示 |

## 3. 驗收

| 條件 | 結果 |
|---|---|
| APP 排序表 vs `python -m query.bottleneck` 逐列 diff 0 | ✅ 真實圖 36 列（可行動＋純結構各 36），經 API 讀出後與現算 `rank_bottlenecks()` **逐列逐格 diff 0**，coverage 相同 |
| `rank_bottlenecks` 的 markdown 呈現不因重構改變 | ✅ `python -m query.bottleneck` 13,067 bytes、`--by-sector` 2,533 bytes，改前改後 `cmp` **逐位元組相同** |
| request path 仍是純讀 | ✅ 四種證明（import allowlist／runtime 模組哨兵／檔案系統快照／socket 封殺）已涵蓋 `/api/v1/ranking`；POST／PUT／PATCH／DELETE → 405 |
| 固定文字只有一份 | ✅ artifact 的 limitations／notes 逐字出現在 markdown（`tests/test_webapp_ranking.py`、`tests/test_bottleneck_ranking.py`） |
| 認知狀態 vs 內容分開（L12） | ✅ 多讀一份文件 → `documents`+1、content digest 變、`freshness_identity` 不變；證據等級變 → identity 變 |
| 測試 | 1,989 → **2,034 passed／1 skipped**（新檔 26＋bottleneck 2＋request-path 參數化 1）；`audit invariants` 見 ROADMAP 查證命令 |
| 部署 | `webapp status` state 1 份；`verify` 5/5；常駐 serve 已重啟（只綁 127.0.0.1:8790），`/api/v1/health.state_kinds == ["ranking"]` |

## 4. 誠實邊界／non-blocking debt

- **公司名：** registry 只有 4 家有 `display_name`，36 列裡 25 列顯示 `co:*`。這是 mechanical 資料（公司自己的名字），
  補 `config/company_identity.json` 即可，不需 pq2；本 Step 刻意不順手補（identity registry 改動會動 golden fixture）。
- **每列 disproof 不在本表**——在單檔判讀的「研究現況」。有 materialize 的檔可從排序表點進去；沒有的顯示灰字。
- **Pane 1 的 alpha-card 摘要與純度欄位（市值／analyst_count）未搬**——它們來自 `briefing/alpha_view` 與 Engine C，
  不是 `rank_bottlenecks` 的輸出；屬 B2 或另一種 kind。
- **前端沒有經真正的 JS parser 檢查**（本機無 node）；做了括號／字串平衡的狀態機檢查與經 daemon 取回 200，
  但「畫面在瀏覽器裡長什麼樣」要使用者開 `https://stockbot.minatoyukina.uk/#/ranking` 看一次。
- `sole_source` 未填 15／36 列——那是圖的現況（authority），畫面誠實標「未填」，不壓成 false。

## 5. 下一步（只是建議；GO 只關閉本 Step）

B2：其餘四種 kind（`coverage`／`positions`／`beta`／`watches`），各與對應 CLI 輸出 diff 0；beta 先讀 `dataviz` skill，
做資產分布圖（目標 vs 實際、band 是容忍區間不是 gate）＋自身價格序列折線＋52 週水位，**不得引入 RSI／MACD**。
