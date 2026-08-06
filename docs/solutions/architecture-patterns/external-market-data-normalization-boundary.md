---
title: "外部行情正規化邊界：報價單位不是結算幣別，值缺席不是值損毀"
date: 2026-08-05
category: docs/solutions/architecture-patterns/
module: engine-c
problem_type: data_normalization
component: market-data
severity: high
applies_when:
  - 新增非美國交易所的標的（LSE／TWSE／TASE／JSE／Frankfurt…）
  - Engine D snapshot 出現 market_malformed／fx_malformed／market_currency_invalid
  - 想放寬或收緊行情的 fail-closed 驗證
  - provider 回傳的 currency 不是 3 碼大寫 ISO code
  - 一個標的的整份行情被 quarantine，但看起來大部分資料都是好的
tags:
  - market-data
  - currency
  - fail-closed
  - normalization
  - engine-c
  - engine-d
  - yfinance
  - multi-market
  - taxonomy-vs-contract
---

# 外部行情正規化邊界

## 事發

2026-08-05 追 pq2 待辦的 blocker 時發現：`co:iqe` 與 `co:sivers_semiconductors` 的
Engine D current-authority snapshot 長期 `market_malformed`，而同一時間 `co:axt`
與 `co:applied_optoelectronics` 完全正常。

逐層拆下去是**兩個彼此獨立、卻剛好都只打非美國交易所**的問題。這種巧合很危險：
它讓人以為只有一個根因，修掉一個之後另一個還在，就會誤判成「修法沒用」。

| | 美股 AXTI／AAOI／META | 非美股 IQE.L／SIVE.ST／2DG.F |
|---|---|---|
| 報價單位 | USD（ISO） | GBp（便士）／SEK／EUR |
| 2026-08-04 那根 bar | close 正常 | **close = NaN，volume 非零** |

## 問題一：報價單位與結算幣別被塞進同一個欄位

LSE 以便士報價，Yahoo 對 `.L` 標的回傳的 `currency` 就是字串 `GBp`。而系統裡散落
**6 處**寫死的同一個驗證式：

```python
if not isinstance(currency, str) or len(currency) != 3 or not currency.isupper():
```

`GBp` 不合格，於是整份行情 quarantine；FX 那側 `GBp/USD` 同樣被 `fx_pair_invalid`
擋掉。

陷阱在於**兩種直覺修法都會壞**，而且第二種壞得更安靜：

1. 放寬驗證式接受 `GBp` → 下游把 44.8 當成 44.8 GBP，價格膨脹 100 倍。
2. 把 registry 改成 `GBP` → 驗證通過、FX 正常、看起來全好了，但價格仍然是 44.8
   而非 0.448。**沒有任何 blocker 會響**，因為每一層都認為單位是對的。

真正的判準是：**這是兩個不同的概念，不是一個欄位的格式問題。**

- **報價單位（quote unit）** — 交易所實際掛出的價格單位，可能是某個幣別的 minor
  unit。是 provider 的事實，該照實記錄。
- **結算幣別（settlement currency）** — ISO-4217，FX、NAV、曝險計算唯一該用的東西。

### 修法

單一正規化入口 `identity/currency.py` ＋ `config/currency_units.json`：

```
quote_code → (ISO 結算幣別, factor)
GBp → (GBP, 0.01)    GBX → (GBP, 0.01)    ILA → (ILS, 0.01)    ZAc → (ZAR, 0.01)
```

比對順序決定了這個設計能不能吸收「以後只會越來越多」：

1. registry 命中（**大小寫敏感**）
2. 未命中但 `upper()` 後形如 `^[A-Z]{3}$` → 視為 ISO 結算幣別、factor 1
3. 都不是 → fail closed，出 `market_quote_unit_unregistered`

第 2 條是重點：**TWD／JPY／HKD／SEK 這類以 ISO code 報價的新市場，零 config 改動
就能用。** 只有 minor unit 才需要加一列。這符合封閉字彙登記表的 taxonomy 判準——
世界會長出新市場，字彙留鬆放 `config/`。

大小寫敏感是刻意的，而且是這張表最容易被「順手優化」掉的一行：`GBp` 與 `GBP`
只差一個字母大小寫，先折疊大小寫會讓**結算幣別 GBP 被當成便士而多除 100**。

### 各層職責

| 層 | 拿到什麼 | 責任 |
|---|---|---|
| `config/company_identity.json` | — | 寫**交易所實際報價的單位**（維持現實） |
| `identity/registry.py` | config 原值 | 對外給結算幣別 `*_currency`，原始單位存 `*_quote_unit` |
| `engine_c/market_data.py` | 報價單位 | 換算**一次**：`quote_price × factor`；留下 `quote_currency`／`quote_price`／`quote_factor` |
| FX | 結算幣別 | `GBp/USD` 一律正規化成 `GBP/USD`，**不得再折第二次**（倍率已在價格側套用） |

`adv20` 是股數，不隨報價單位換算——這是實作時最容易一起乘下去的地方。

`unit_status` 維持 `"ok"`：已登記且已套用的換算就是**已驗證**的單位處理，退化成
`market_unit_unverified` 會讓修好的東西看起來還是壞的。

## 問題二：一根未結算的 bar 廢掉整個序列

`build_tradeability_snapshot` 原本對每一列 history 做同一套檢查，任何一列不合格就
`status: quarantined`。yfinance 對非美國交易所會先開出當日 row、close 還沒發佈
（NaN），於是 **1 根未結算的 bar 廢掉 59 根有效資料**。

fail-closed 本身是對的，錯的是**判準顆粒度**：它沒有區分兩種長得一樣的情況。

| 現象 | 意義 | 處理 |
|---|---|---|
| close/volume **缺席**（None／NaN），且落在序列**末端** | 資料還太年輕 | 丟棄該列並計數 |
| close/volume 缺席，但落在序列**中間** | 真的有破洞 | quarantine |
| close ≤ 0 或 volume < 0（**值有寫出來但超出範圍**） | 資料損毀 | quarantine |
| `as_of` 無法解析 | 定位不了，無法判斷屬於上面哪一種 | quarantine |

「末端」的定義刻意嚴格：該列的 `as_of` 必須晚於**所有有效列**的最新時間。這讓放寬
只作用在真正的尾端。

**沒有引入「最多可丟幾根」的上限。** 丟太多會自動撞上既有的 20-session 門檻，再往
前則被下游 `market_stale` 接住——既有的兩道閘門已經涵蓋，多一個魔術數字只會多一個
要維護的判準。

快照多帶 `unsettled_trailing_rows`，解釋為什麼 `as_of` 不是 provider 回傳的最後一根。
缺了這個欄位，未來會有人看到「as_of 是前天」而重新去查一次已經解決的問題。

## 通用判準

1. **provider 回傳的欄位名不等於它的語意。** `currency` 這個 key 底下裝的可能是報價
   單位。正規化邊界要建在 provider adapter，不是散在每個消費端。
2. **同一個 validator 出現在第 3 個檔案時，它就該變成一個模組。** 六份寫死的
   `len()==3 and isupper()` 是這次問題能拖這麼久的直接原因——修一處不會讓另外五處
   跟著好。
3. **fail-closed 要收在正確的顆粒度上。** 「有問題就全部擋掉」在資料量小的時候看起來
   很安全，實際上會讓真正的訊號被雜訊淹沒（此例是 59:1）。收緊的對象應該是**判準**，
   不是**範圍**。
4. **「值缺席」與「值損毀」是兩件事。** 缺席可能只是時間問題；寫出來卻超出範圍代表
   上游已經錯了。把兩者合併成「invalid」會逼你在「太鬆」與「太緊」之間二選一。
5. **修法會讓錯誤變安靜時，優先度要往上調。** 問題一的第二種修法（直接改 ISO code）
   會通過所有驗證、清掉所有 blocker、然後餵給決策層一個差 100 倍的價格。這比原本
   「整份 quarantine」危險得多——見 L11（自己引用的事實要套跟圖裡 claim 同一套追源
   紀律）的同型體悟：看起來修好了，最該起疑。

## 驗證

`tests/test_currency_units.py`（25 項）釘住正規化與換算；`tests/test_market_context.py`
新增 6 項釘住 trailing bar 的邊界——中間破洞仍擋、負值仍擋、無法定位仍擋、20-session
門檻不可繞過、同 session 的完整列取代 NaN 列。

實測（2026-08-05，真實 provider 資料）：

```
co:iqe    IQE.L  0.407 GBP (40.70 GBp)  unsettled_trailing_rows: 1
co:sivers SIVE.ST 31.18 SEK  exec 2DG.F 2.80 EUR   work orders: []
co:axt    AXTI  65.27 USD    work orders: []
co:meta   META  587.94 USD   work orders: [graph_coverage_deficit]
```

## 相關

- [`one-representation-two-meanings.md`](one-representation-two-meanings.md)：本篇的
  兩個問題與同日另外兩個缺陷（runway freshness 窗口、collector 的空結果與失敗同形）
  是同一個形狀；那篇收錄提早認出它的五個訊號
- 判準源頭：AGENTS.md 的「報價單位 ≠ 結算幣別」與 L10（早期資料庫以 correctness
  優先，不背錯誤相容包袱）
- [`closed-vocabulary-registry.md`](closed-vocabulary-registry.md)：`config/currency_units.json`
  為何屬於「可自由擴充」那一格，以及新增 config 必須補 `.gitignore` 白名單
- [`engine-d-content-addressed-decision-context.md`](engine-d-content-addressed-decision-context.md)：
  為何換算事實要留在 frozen context 而不是只留在 log
