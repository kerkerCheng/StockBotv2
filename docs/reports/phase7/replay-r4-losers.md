# Phase 7 Step 7.2 — R4 history lane 輸家驗屍（X4）

> **性質：回放報告（評估檔）。** 規則照 [`registration.md`](registration.md) §2 X4、§7.4：入圖時的圖投影（`query.bottleneck.project_assertions_as_of(<入圖日>)`）
> 說了什麼 vs 之後的一手文件（`published_at` 晚於入圖日）說了什麼；每檔結論封閉三選一：「結構讀錯」／「結構沒錯、是價格路徑」／「證據不足以判」。
> 只引用 id、不改任何 ledger。執行：2026-10-05（台北）；價格取追蹤表（2026-10-02 收盤），圖投影取現在的 Neo4j。

## 一句話

**5 檔全部「證據不足以判」**——入圖後到 10-02 這 5 週裡，沒有任何一份一手文件回頭碰到入圖時的結構主張（四檔是時間太短；Nidec 是入圖時的圖投影本身就是空的）。
所以這 5 檔**不構成** H1／H3 的反例，也不能記成「是價格路徑」（那要有之後的一手說結構沒錯）。

## 描述（不進判讀）

- **5 檔都在追蹤表的「入圖前已漲」**（入圖前 30 天的漲幅大於入圖後）——但對入圖後下跌的檔，這幾乎必然成立，不是發現。真正有內容的是幅度：
  AEVA、MP、Lynas 入圖前 30 天分別 +24.7%、+43.0%、+15.4%，入圖是在消息與漲幅之後。
- **4 檔不在光通訊**（3 檔稀土、1 檔機器人減速機）；稀土三檔同期一起跌（−20.4%、−18.6%、−12.0%）——形狀像主題移動，沒有一手、不判因果。
- **MP 是客戶資本承諾最齊全的一檔**（國防部包銷、Apple 5 億美元），入圖後 5 週 −20.4%——H10 的反向觀察候選，但 5 週的價格窗口太短，不進 H10 判讀。

## 逐檔

### AEVA（`co:aeva`；入圖 2026-08-14）

- **入圖時的圖投影**（`project_assertions_as_of(2026-08-14)`）：全部 1 條，當時可見 **1** 條，排除 {'published_after_as_of': 0, 'undated': 0}
  - `co:aeva` supplies_to `tech:near_package_optics`｜`aeva_8k_ex991_20260805_optical_connectivity`（published 2026-08-05）｜«Signed joint development agreement with major customer to use Aeva's high-power optical source technology in a Near-Packaged Optics (NPO) solution for a hyperscaler with initial deployment targeted fo»
- **入圖後的一手**：EDGAR 非內部人申報 **0 份**（08-14 → 10-02 只有 Form 3／4；`edgar_since.py AEVA 2026-08-01` 列出的 10-Q 08-06、8-K 08-05 都早於入圖日）
- **價格（追蹤表）**：入圖前 30 天 +24.7%；入圖 → 2026-10-02 -36.6%（對追蹤表基準 QQQ 的超額 -39.2%）
- **結論：證據不足以判。** 入圖後沒有任何一手文件回頭碰到那份聯合開發協議（客戶具名、進展或終止都沒有）。價格形狀是「消息日前後漲、之後回吐」：入圖前 30 天的漲幅就是那則 8-K 帶來的。下一個裁決點：AEVA Q3 10-Q（11 月）

### MP（`co:mp_materials`；入圖 2026-08-27）

- **入圖時的圖投影**（`project_assertions_as_of(2026-08-27)`）：全部 8 條，當時可見 **8** 條，排除 {'published_after_as_of': 0, 'undated': 0}
  - `co:mp_materials` supplies_to `mat:rare_earth_magnets`｜`mp_10_k_20260226`（published 2026-02-26）｜«the DoW has guaranteed that the 10X Facility will generate at least $140 million of EBITDA (as defined in the DoW Offtake Agreement, and subject to annual escalation) and has the right to purchase all»
  - `co:mp_materials` supplies_to `mat:rare_earth_magnets`｜`apple_newsroom_mp_magnets_2025_07_15`（published 2025-07-15）｜«Apple has committed $500 million to buying American-made rare earth magnets developed at MP Materials' flagship Independence facility in Fort Worth, Texas.»
  - `co:mp_materials` supplies_to `mat:rare_earth_magnets`｜`fas_dod_mp_partnership_2025_07_15`（published 2025-07-15）｜«DoD is also providing a 100% offtake commitment for the 7,000 MT/year of expanded magnet manufacturing capacity over the first 10 years.»
  - `co:mp_materials` supplies_to `mat:separated_heavy_reo`｜`usgs_mcs2026_rare_earths_heavy`（published 2026-02-01）｜«At least five companies were developing commercial-scale heavy-rare-earth processing and refining capacity and at least one company developed commercial-scale capacity for a specific heavy-rare-earth »
  - `co:mp_materials` supplies_to `mat:rare_earth_magnets`｜`fas_dod_mp_partnership_2025_07_15_substitutability`（published 2025-07-15）｜«A new multibillion dollar partnership between DoD and MP Materials, the only active domestic producer of NdPr, announced on July 10th, seems to be the agency's big bet on a solution.»
  - `co:mp_materials` supplies_to `tech:ndfeb_metal_alloy`｜`mp_10_q_20260807_metal_alloy`（published 2026-08-07）｜«In late 2024, we commissioned electrowinning capabilities at the Independence Facility to produce NdPr metal from NdPr oxide. Additionally, in 2025, we added strip casting capabilities to produce NdFe»
  - `co:mp_materials` supplies_to `mat:rare_earth_magnets`｜`noveon_series_c_2026_01_19`（published 2026-01-19）｜«Noveon was the first company to reshore full-scale production of sintered rare earth magnets to the United States.»
  - `co:mp_materials` supplies_to `mat:rare_earth_magnets`｜`usar_stillwater_phase1a_2026_03_26`（published 2026-03-26）｜«successful commissioning of its commercial magnet production line (Phase 1a) at its facility in Stillwater, Oklahoma»
- **入圖後的一手**：EDGAR 非內部人申報 **0 份**（08-27 → 10-02；10-Q 08-07、8-K 08-06 都早於入圖日）
- **價格（追蹤表）**：入圖前 30 天 +43.0%；入圖 → 2026-10-02 -20.4%（對追蹤表基準 QQQ 的超額 -24.5%）
- **結論：證據不足以判。** 結構主張（國防部包銷與 EBITDA 保證、Apple 5 億美元採購承諾——**客戶資本承諾齊全**，H10 那一類）沒有任何新一手觸及。同期稀土三檔（MP、Lynas、JL Mag）一起跌，形狀像主題移動，但沒有一手、本 Step 不判因果。5 週的價格窗口太短，不進 H10 判讀。下一個裁決點：MP Q3 10-Q（11 月）。⚠ 投影裡的 `noveon_series_c_2026_01_19_e1`、`usar_stillwater_phase1a_2026_03_26_e1` 是**反證**：Noveon、USA Rare Earth 自己的新聞稿（引文沒有 MP），用來把 MP→稀土磁材的 substitutability 由 4 下修到 3（commit `0cfab23c`，2026-09-10 進庫）——**依發表日它們在『08-27 的圖』裡，但入圖當天的圖其實沒有它們**（discovery lookahead，見偏差 ①）；表示法本身記 failure log #14

### LYC.AX（`co:lynas`；入圖 2026-08-30）

- **入圖時的圖投影**（`project_assertions_as_of(2026-08-30)`）：全部 5 條，當時可見 **5** 條，排除 {'published_after_as_of': 0, 'undated': 0}
  - `co:lynas` supplies_to `mat:rare_earth_magnets`｜`lynas_q1_fy26_quarterly_2025_10_30`（published 2025-10-30）｜«the importance of Lynas as the only outside China commercial producer of separated Light and Heavy Rare Earth oxides.»
  - `co:lynas` supplies_to `mat:rare_earth_magnets`｜`miningweekly_lynas_terbium_2025_06_18`（published 2025-06-18）｜«Lynas is delighted to have achieved first production of terbium oxide at the Lynas Malaysia advanced materials plant»
  - `co:lynas` supplies_to `mat:rare_earth_magnets`｜`lynas_q1_fy26_quarterly_2025_10_30_substitutability`（published 2025-10-30）｜«the only outside China commercial producer of separated Light and Heavy Rare Earth oxides»
  - `co:lynas` supplies_to `mat:rare_earth_magnets`｜`lynas_asx_jare_enhanced_2026_03_10`（published 2026-03-10）｜«JARE will provide a firm commitment to purchase 5,000 tonnes NdPr per annum for Japanese industry with an agreed market-linked floor price»
  - `co:lynas` supplies_to `mat:separated_heavy_reo`｜`sojitz_hre_import_2025_10_30`（published 2025-10-30）｜«Sojitz has begun the import of heavy rare earths (HREs) produced by Australia-based Lynas Rare Earths Ltd into Japan.»
- **入圖後的一手**：ASX 公告（交易所清單，`asx.api.markitdigital.com`）：2026-09-25「2026 Annual General Meeting Details」；**2026-09-30 22:39 UTC（雪梨 10-01）「Lynas Rare Earths to Acquire Meteoric Resources」＋「Proposed issue of securities」**——換股收購巴西 Caldeira 稀土專案，資本配置與稀釋，不碰入圖時的結構主張；跌幅多發生在公告之前
- **價格（追蹤表）**：入圖前 30 天 +15.4%；入圖 → 2026-10-02 -18.6%（對追蹤表基準 QQQ 的超額 -23.3%）
- **結論：證據不足以判。** 入圖後唯一的一手是收購公告（資本配置）；「中國以外唯一的分離輕、重稀土商業生產者」與 JARE 確定採購都沒有新文件觸及。下一個裁決點：Lynas 2027 財年第一季季報（10 月底）

### 6594.T（`co:nidec`；入圖 2026-09-01）

- **入圖時的圖投影**（`project_assertions_as_of(2026-09-01)`）：全部 1 條，當時可見 **0** 條，排除 {'published_after_as_of': 0, 'undated': 1}
  - （未定日、被排除）`co:nidec` supplies_to `tech:strain_wave_gear`｜`nidec_dtc_humanoid_flexwave_2026`｜«The Next Generation Nidec FLEXWAVE high precision simple contained assembly and component sub-assembly gear reducers are the ideal choice for these types of applications.»
- **入圖後的一手**：（入圖時的投影是空的，無從比對；未查入圖後的 TDnet 公告）
- **價格（追蹤表）**：入圖前 30 天 -0.8%；入圖 → 2026-10-02 -14.6%（對追蹤表基準 QQQ 的超額 -20.7%）
- **結論：證據不足以判。** 入圖時圖上唯一一條 assertion（`nidec_dtc_humanoid_flexwave_2026`：FLEXWAVE 減速機「the ideal choice for these types of applications」）**沒有發表日**——依 L11-5 從投影排除，入圖當天的圖投影是空的。這一列本身就是 INV-6 的現形：沒有日期的證據，不能拿來說「當時圖上有什麼」

### 6680.HK（`co:jl_mag`；入圖 2026-08-31）

- **入圖時的圖投影**（`project_assertions_as_of(2026-08-31)`）：全部 3 條，當時可見 **3** 條，排除 {'published_after_as_of': 0, 'undated': 0}
  - `co:jl_mag` supplies_to `tech:grain_boundary_diffusion`｜`jlmag_ar2022_hkex`（published 2023-03-31）｜«The production and sales volume of high-performance REPM products of the Company both recorded a historical high. In particular, the production and sales volume of grain boundary diffusion products in»
  - `co:jl_mag` supplies_to `mat:rare_earth_magnets`｜`jlmag_ar2022_hkex`（published 2023-03-31）｜«The production and sales volume of high-performance REPM products of the Company both recorded a historical high. In particular, the production and sales volume of grain boundary diffusion products in»
  - `co:jl_mag` supplies_to `mat:rare_earth_magnets`｜`jlmag_ar2022_hkex_customers`（published 2023-03-31）｜«During the Reporting Period, the Company’s largest customer accounted for approximately 12.71% of the Company’s total revenue. The total revenue from the Company’s five largest customers accounted for»
- **入圖後的一手**：HKEX：期中業績由 08-19 董事會通過（早於入圖日）；入圖後只有 09-25 股東會結果與中期分派——沒有結構性的一手
- **價格（追蹤表）**：入圖前 30 天 +3.5%；入圖 → 2026-10-02 -12.0%（對追蹤表基準 QQQ 的超額 -16.6%）
- **結論：證據不足以判。** 入圖時圖上的三條全來自 **2022 年報**（2023-03-31 發表：高性能稀土永磁產銷創新高、最大客戶占營收 12.71%、晶界擴散）——入圖時的圖用的是三年前的證據；入圖後沒有結構性的一手

## 偏差標註（registration §0.1）

| 偏差 | 本報告的情況 |
|---|---|
| ① discovery lookahead | 投影依 `published_at` 過濾，不是依進庫日——**入圖日之後才進庫、但發表日更早的證據會被算進「當時的圖」**。實例：MP 的兩條反證（Noveon 2026-01-19、USA Rare Earth 2026-03-26 發表）2026-09-10 才進庫，投影卻把它們算進 08-27 的圖；其餘各檔的進庫日未逐筆核對。逐字讀的是現在的版本（更正走廊改寫前的版本不重建） |
| ② 選樣偏差 | **依結果選樣**：五檔是 2026-10-04 快照裡 history lane 跌最深的（proposal §4.3）——不能拿來推論 history lane 整體 |
| ③ 超額基準回溯 | 這五檔不在光通訊組；超額用追蹤表的基準（QQQ），不用光通訊組 |

## 下一次看這五檔

AEVA、MP 的 Q3 10-Q（11 月）；Lynas 2027 財年第一季季報（10 月底）；JL Mag 2026 年報（2027-03）；Nidec——先補一份有日期的 FLEXWAVE 人形機器人供貨一手，投影才有東西可比。

## 附錄：產生程式碼（逐字）

### `r4_probe.py`

```python
"""R4 輸家驗屍探針（唯讀）：每檔在入圖日 T 的圖投影（`query.bottleneck.project_assertions_as_of`，只留 published_at ≤ T 的 assertion）
與 T 之後才發表、現在已在圖上的 assertion。輸出 r4_probe.json＋印摘要。"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(r"C:\Users\Cheng\code\StockBotv2")
sys.path.insert(0, str(ROOT))
from query.bottleneck import fetch_assertions, latest_possible_date, project_assertions_as_of  # noqa: E402
from query.sub_language import fetch_all_quotes  # noqa: E402
from query.structure import _graph_driver  # noqa: E402

LOSERS = {"co:aeva": ("AEVA", date(2026, 8, 14)), "co:mp_materials": ("MP", date(2026, 8, 27)),
          "co:lynas": ("LYC.AX", date(2026, 8, 30)), "co:nidec": ("6594.T", date(2026, 9, 1)),
          "co:jl_mag": ("6680.HK", date(2026, 8, 31))}

drv = _graph_driver()
with drv.session() as s:
    rows, quotes = s.execute_read(lambda tx: (fetch_assertions(tx), fetch_all_quotes(tx)))
drv.close()
print("assertion rows", len(rows), "keys", sorted(rows[0].keys()))
out = {}
for cid, (tk, T) in LOSERS.items():
    mine = [r for r in rows if cid in (r.get("src_id"), r.get("dst_id"), r.get("company_id"), r.get("source"), r.get("target"))
            or cid in json.dumps(r, ensure_ascii=False, default=str)]
    proj = project_assertions_as_of(mine, T)
    kept_ids = {id(r) for r in proj.rows}
    later = [r for r in mine if latest_possible_date(r.get("published_at")) and latest_possible_date(r.get("published_at")) > T]
    undated = [r for r in mine if latest_possible_date(r.get("published_at")) is None]

    def brief(r):
        aid = r.get("assertion_id") or r.get("id")
        q = (quotes.get(aid) or [""])[0] if aid else ""
        return {"aid": aid, "rel": r.get("relation"), "src": r.get("src"), "dst": r.get("dst"),
                "published_at": str(r.get("published_at")), "doc": r.get("source_doc_id"),
                "attrs": r.get("attributes"), "origin": r.get("origin"),
                "quote": str(q)[:300]}
    out[cid] = {"ticker": tk, "T": T.isoformat(), "n_all": len(mine), "n_asof": len(proj.rows), "excluded": proj.reasons(),
                "asof": [brief(r) for r in proj.rows], "later": [brief(r) for r in later], "undated": [brief(r) for r in undated]}
    print(f"== {tk} {cid} T={T}：全部 {len(mine)}｜T 時可見 {len(proj.rows)}｜T 之後發表 {len(later)}｜未定日 {len(undated)}")
    for b in out[cid]["asof"][:8]:
        print("   [T]", b["src"], b["rel"], b["dst"], b["published_at"][:10], b["doc"], "|", b["quote"][:130])
    for b in out[cid]["later"][:6]:
        print("   [後]", b["src"], b["rel"], b["dst"], b["published_at"][:10], b["doc"], "|", b["quote"][:130])
(Path(__file__).parent / "r4_probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
```

### `edgar_since.py`

```python
"""唯讀：某檔在某日之後的 EDGAR 申報清單（fetchers.edgar 的 get_cik＋fetch_submissions＋recent_filings）。
python edgar_since.py <TICKER> <YYYY-MM-DD>"""
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Cheng\code\StockBotv2")
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
from fetchers.edgar import fetch_submissions, get_cik, recent_filings  # noqa: E402

ticker, since = sys.argv[1], sys.argv[2]
cik = get_cik(ticker)
print("CIK", cik)
for f in recent_filings(fetch_submissions(cik), cik):
    d = str(f.get("filed_date") or "")
    if d >= since and f.get("form_type") not in ("3", "4", "5", "144"):
        print(d, f.get("form_type"), f.get("accession"), f.get("primary_doc"), "| items", f.get("items"))
```
