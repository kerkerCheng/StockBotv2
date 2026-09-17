# Phase 3：D5 帳號登記表與計分表（2026-09-17 交付）

> **狀態：已交付。** 本檔是 Z3 的 `PLAN_PROPOSAL` ＋ 交付紀錄合併（使用者 2026-09-17 已核准
> 「① 寫 InP 賭注 ② Phase 3」，兩件之間不停）。
> ⚠ 本檔的現況數字會腐壞——每個數字都附了查證命令，**引用前先跑那一條**。

## 1. 為什麼是這一題

漏斗最上游那一題沒有答案：**哪個來源歷史上產出贏家。**
單一帳號兩個月 495 則只有 22 則進圖（4.4%），而「這個帳號值不值得繼續看」從來沒有被量過。
沒有量測就不該有第二個帳號（INV-5）。

## 2. Zoom 判定：Z3

跨 `config/`／`engine_b/`／`crons/`／`webapp/` 四處，新增一組封閉字彙（tier），
並動到 unattended routine 的 executable surface（`crons/harvest_leads.py`、
`python -m webapp materialize` 的 prefix rule）。

**plan 裡沒有需要使用者選的問題**（ROADMAP Phase 3 那一列已定義到可直接執行），
依 AGENTS.md 常規推進授權：plan 照出，不停。

## 3. 四個 Step 與實際落點

| Step | 做什麼 | 落點 |
|---|---|---|
| **3.1** | 帳號登記表加 tier 三級封閉字彙 | `config/signal_sources.json`（schema v2）＋ `engine_b/signal_source_registry.py`（唯一 loader） |
| **3.2** | 回溯計分表五欄＋三個偏差＋貼文蓋章 | `engine_b/account_scorecard.py` |
| **3.3** | 計分表 materialize 進 APP、心跳第 5 段接上 | `webapp/materialize.py`／`webapp/__main__.py`／`webapp/contracts.py`／`crons/heartbeat.py` |
| **3.4** | harvest 每月花費上限 | `crons/harvest_config.json`／`crons/harvest_leads.py`／`engine_b/leads.py` |

## 4. 三個設計判斷（不是偏好，各有理由）

### (a) 蓋章分兩段：harvest 記時間與實體，價格在計分時抓

D5 的「每則貼文自動蓋章（貼文時間＋當日收盤價＋具名實體）」裡，前後兩項 harvest 本來就有
（`published_at`／`entities`），只有收盤價需要外部呼叫。
**把取價放進 harvest 會讓一條「零 LLM、零 token」的管線開始依賴 yfinance**，
而 harvest 失敗會中止整輪 Daily（writer lock 契約）。
所以價格在計分時抓，蓋章落在 artifact 的 `stamps`。
⚠ 代價要講清楚：**第一次是回溯蓋章**，那是後見之明偏差的一部分，已逐字印在 `KNOWN_BIASES`。

### (b) 解析只走 registry 的 `company_ids`，不用抽取出來的 ticker

lead 的 `entities.tickers` 是 `SIVE` 而不是 `SIVE.ST`——拿它直接查價會撞到別家公司（INV-1）。
解析不到的**列進 filtered 與 reasons**，讓「registry 覆蓋不足」這個真實缺口現形。
實測：495 則裡 335 則可計分，濾掉 160（`no_named_company` 120、
`ticker_without_registry_company_id` 40）。

### (c) 去重與不去重**都印，不互相取代**

SIVE 在樣本裡被點名 94 次、LITE 72 次。用全部點名算中位數，量到的是
「這個帳號多常提某一檔」與「那一檔那段期間怎麼走」的乘積。
去重（每檔只取最早一次）之後量的才比較接近「選股」。
**兩個都是資訊**：重複點名是持續追蹤，不是雜訊——所以兩個都印、都標 n（L12）。

## 5. 實測結果（2026-09-17；查證：`python -m webapp materialize --scorecard`）

```
x:aleabitoreddit｜tier probation｜量測 2026-06-29 → 2026-09-16
具名點名 913 則／40 檔（貼文 495、可計分 335、濾掉 160）
```

| 欄 | 全部點名 | 每檔只算最早一次 |
|---|---|---|
| 點名後 30 天 vs QQQ | **−2.03%**（n=617） | **−9.14%**（n=38） |
| 點名後 30 天 vs SOXX | **+3.06%**（n=617） | **+2.14%**（n=38） |
| 點名後 90 天 | 沒有值（`insufficient_sample`） | 同左 |
| 點名前 30 天漲幅 | **−2.28%**（n=913） | **−5.61%**（n=40） |
| 追源成功率 | **37.59%**（n=439） | — |
| 假設命中率 | **沒有值**（`capability_absent`） | — |
| no-go 率 | **64.63%**（n=492） | — |

**三個讀得出來的東西：**

1. **兩個基準給出相反符號。** 對 QQQ 是負的、對 SOXX 是正的——這正是 D5 §6 要求
   「必須同時對 SOXX 算」的理由，而它在第一次量測就發生了。
   只印 QQQ 會得到「這個帳號沒用」，只印 SOXX 會得到「這個帳號有 alpha」，**兩個都是錯的**。
2. **不是追高。** 點名前 30 天漲幅是 **負的**（−2.28%／去重 −5.61%），
   推翻了「都在漲完之後才點名」這個常見假設。
3. **去重之後 vs QQQ 惡化到 −9.14%。** 也就是說：帳號**反覆點名**的那幾檔表現優於
   它第一次點名的標的。合理的解讀是它的第一次點名偏早（點名時標的正在跌），
   要等一段時間才走出來——但**樣本只有 38 檔、2.6 個月，這是觀察不是結論**。

**90 天欄位沒有值是正確行為**：最早的點名是 2026-06-29，到今天 80 天，一次都沒走完。
它宣告 `insufficient_sample` 而不是填 0——「還沒到期」與「報酬是 0」是兩件事。

**假設命中率永遠是 `capability_absent`**，直到有 filing 裁決紀錄為止（§6 已預告算不回來）。

## 6. Sandbox impact review 五步（`--scorecard` 動到 unattended surface）

⚠ **關鍵發現：`python -m webapp materialize` 是 `prefix_rule`**，所以新增的 `--scorecard`
**自動被無人值守放行**——而那條 rule 的 justification 逐字寫著「無新增網路主機或憑證」。

| 步 | 結論 |
|---|---|
| **1 path／side effect／capability** | 讀 `library/leads/pending_leads.json`（tracked，唯讀）＋ `config/signal_sources.json`；寫 `library/private/app/state/account_scorecard.json`（ignored derived cache）。**網路：yfinance 歷史收盤**——主機與 `engine_c/etl_yfinance.py`、`scripts/daily_beta_snapshot.py` 相同，兩支都已在 allowlist、同樣無憑證。不碰 `.git`、不碰 tracked 檔、不寫任何 authority、不入圖、不動 tier。 |
| **2 skill／prompt／本檔** | **刻意不改 daily／weekly prompt**——計分表維持互動觸發（見下）。ROADMAP Phase 3 那一列回填；本檔。 |
| **3 最窄 rule** | **不新增 rule。** 既有 prefix 已涵蓋，但 justification 已更正：明寫 `--scorecard` 會連 yfinance、新增的是請求量不是主機，並記下對應的收緊。 |
| **4 permission contract test** | `test_scorecard_network_surface_has_a_hard_cap_in_code`（斷言 `MAX_PRICED_SYMBOLS` 存在**且真的被 `build_scorecard` 用到**——常數存在不等於閘門存在）＋ `test_scorecard_rule_justification_admits_the_network_call`（斷言 justification 沒有宣稱它不連網）。 |
| **5 端到端 smoke** | `python -m webapp materialize --scorecard` → `account_scorecard.json`（320,314 bytes；1 個帳號／913 則具名點名）；`python -m crons.heartbeat --weekly` 第 5 段印出五欄與三個偏差。 |

**同一個 change 落地的收緊（L15：放行與收緊必須同時發生）：**
`MAX_PRICED_SYMBOLS = 200` 是硬上限，超過就截斷並在 artifact 的 `price_budget`
與 filter reasons 裡現形——帳號變多時會先撞到它並被看見，不會安靜地長成一個沒人注意的爬蟲。

**為什麼不進 daily／weekly prompt（2026-09-17 的保守選擇，不是結論）：**
它是唯一會連外的 materializer，而 Phase 3 的驗收不需要它無人值守。
AGENTS.md：「不得用 broad permission 掩蓋整合缺口」。
心跳第 5 段會印 `計分表 as-of`，所以「它多舊」看得見，不會安靜過期。
**要改成無人值守是一個放寬，那才需要使用者決定。**

## 7. 三個當下修掉的缺陷（都是 L17：機制只認得當初那個案例）

1. **`SourcePolicy(**item)` 讓 additive config 欄位炸掉 26 個測試。**
   `decision_lab/intake.py` 假設 config 的欄位集合永遠等於 dataclass 的欄位集合，
   加一個 `tier` 就 `TypeError`。改成只取自己宣告的欄位——**一份 config 本來就可以有多個
   consumer**，而封閉字彙的驗證在 `engine_b.signal_source_registry` 做，
   所以這裡忽略未知欄位不會讓打錯的 tier 靜默沉底。
2. **`state_only` 是一串手寫的 `or`，新增 `--scorecard` 就漏掉**，
   結果它被當成「沒指定專屬 flag」而重跑了全部 73 檔單檔。改成 `_STATE_FLAGS` 清單，
   並加測試斷言它與 `STATE_KINDS` **集合相等**——所以下次新增 state materializer 忘了加，
   測試會紅。⚠ 順手把 CLI 的 `dest` 改成與 kind 同名，**這樣就不需要一張 flag→kind 的映射表**
   （而映射表正是下一個會忘記更新的東西）。
3. **`budget_exhausted` 差點被塞進 `fetch_failed`。**
   `FAILURE_CLASSES` 全部是「網路／provider 失敗」，而預算用完是**我們自己決定不抓**。
   塞進去會讓 `unresolved_harvest_failures` 每天把正常的預算保護當成待修故障亮一次
   ——**一個永遠亮著的警報等於零鑑別力**（L14-4「恆亮」）。
   立為獨立的 harvest result，並讓心跳第 1 段單獨印它。

## 8. 沒做的與為什麼

| 項 | 為什麼 |
|---|---|
| 新帳號的付費探針（§6 三段停損） | Phase 3 驗收只要求「≥1 個帳號」，而 aleabitoreddit 的 495 則已在本機、零成本。**花錢之前先讓計分表跑起來**才是三段停損的第一段。 |
| tier 升等 | D5 明訂一季一次的 pq2 manual。本輪建表一律 `probation`，**包含已有 495 則樣本的那一個**——由建表的 session 自行升等，正是「量測先於信任」要防的事。 |
| 90 天欄位 | 樣本期只有 2.6 個月。**等時間，不是等工作。** |
| 假設命中率 | 需要 filing 裁決紀錄，本系統今天沒有。已宣告 `capability_absent`。 |
| 計分表進無人值守 | 見 §6。那是放寬，需要使用者決定。 |

## 9. 查證命令

```bash
python -m engine_b.signal_source_registry          # 登記表與 tier 分佈
python -m engine_b.account_scorecard               # 計分表（會抓價格）
python -m engine_b.account_scorecard --no-network  # 不抓價格，看缺席宣告對不對
python -m webapp materialize --scorecard           # 寫進 APP state
python -m crons.heartbeat --weekly                 # 第 5 段
python -m pytest tests/test_account_scorecard.py tests/test_codex_daily_permissions.py -q
python -c "import json;print(json.load(open('crons/harvest_config.json'))['x_accounts']['monthly_spend_cap_usd'])"
```
