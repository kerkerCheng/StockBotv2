# Phase 7 Step 7.2 — R2 parked 回查（X2）

> **性質：回放報告（評估檔）。** 樣本與抽樣規則照 [`registration.md`](registration.md) §7.3／附錄 C（36 則，程式重算逐則相同）；「證實」照 §1 H2 的定義：
> **之後的一手文件補上了當初 park 理由所缺的那一樣**，只有二手不算（L11-3）。只引用 id、不改任何 ledger。執行：2026-10-05（台北）；量測終點 2026-10-02。

## 一句話

36 則裡**證實 1 則**（CCXI 的 S-4 補上了 Agility 歷史財報）、未證實 11、無法判 2（registry 沒寫 park 理由）、**不適用 22**（park 理由本來就不是缺證據——例行 Form 4、行事曆、重複、非上市標的）。
**H2（X2 的部分）＝不足**（證實 1 則 < 4，registration §1 H2「不足」）；依層母體加權的證實比例 **1.9%**（全樣本為分母）／
12.9%（排除不適用與無法判）——照印，不判方向。H2 要與 P3（7.4）合併判。

⚠ **與登記的偏離**：registration §7.3（「之後有沒有一手證實」）與 plan §8 驗收（「每則有證實日或『未證實』」）只有兩類；「無法判」「不適用」是回查時加的。照登記的二分法這兩類都算未證實——
證實數（1）、H2 判讀（不足）與全樣本為分母的 1.93% 都不變；只有「排除不適用與無法判」那個比例是額外的數字，不進判讀。

## 各層

| 層 | 母體 | 樣本 | 證實 | 未證實 | 無法判 | 不適用 | 層內證實比例（全樣本為分母） | 層內證實比例（排除不適用、無法判） |
|---|---|---|---|---|---|---|---|---|
| EDGAR | 237 | 10 | 0 | 0 | 1 | 9 | 0.0% | —（沒有可判的列） |
| X | 67 | 10 | 1 | 6 | 0 | 3 | 10.0% | 14.3% |
| 公司／新聞 feed | 36 | 8 | 0 | 0 | 1 | 7 | 0.0% | —（沒有可判的列） |
| decompose | 4 | 4 | 0 | 3 | 0 | 1 | 0.0% | 0.0% |
| 圖內部 | 2 | 2 | 0 | 1 | 0 | 1 | 0.0% | 0.0% |
| 題材掃描 | 2 | 2 | 0 | 1 | 0 | 1 | 0.0% | 0.0% |

- 加權（registration §7.3：合併任何比例時依層的母體大小加權）：全樣本為分母 **1.93%**；排除不適用與無法判 **12.91%**。
- ⚠ EDGAR 層 10 則裡 9 則是「不適用」：parked × `original_obtained` 的 237 則 EDGAR 多半是例行申報——**這個母體量到的主要是「例行申報被正確 park」**，不是「保守擋掉了真東西」。

## 唯一一則證實的價格（H2 的量法）

`lead_6e6000e1`（X 帳號點名 XPEV 機器人分拆、Agility 估值）：park 日 2026-08-24（triage decided_at）→ 證實日 2026-09-04（S-4）→ 量測日 2026-10-02。
標的取 CCXI（Agility 的 SPAC）：**park→證實 -4.9%、證實→量測 -10.5%**（絕對報酬）。機器人鏈沒有主題等權組——超額寫「組未定義」，不拿別的組代替（registration §0.1）。
n＝1，不進判讀線。

## 逐則

| 層 | lead | park 日 | 來源 | 標題（節錄） | 裁決 | 缺的那一樣與之後的一手 | park 理由今天 |
|---|---|---|---|---|---|---|---|
| EDGAR | `lead_06a8ab21` | 2026-07-31 | `edgar:GFS` | GFS 4 filed 2026-07-31 | **不適用** | 例行 Form 4（稅務代扣） | 站得住 |
| EDGAR | `lead_29afe4c0` | 2026-07-31 | `edgar:GFS` | GFS 4 filed 2026-07-31 | **不適用** | 例行 Form 4（RSU 歸屬） | 站得住 |
| EDGAR | `lead_51262d08` | 2026-08-30 | `edgar:MP` | MP 10-Q filed 2026-08-07 [000048] | **不適用** | 10-Q 素材已由 [316] 涵蓋（重複） | 站得住 |
| EDGAR | `lead_6648e5f5` | 2026-08-21 | `edgar:MRVL` | MRVL 4 filed 2026-07-16 | **不適用** | 例行 Form 4 | 站得住 |
| EDGAR | `lead_79e1eada` | 2026-09-10 | `edgar:LRCX` | LRCX 4 filed 2026-09-10 [000011] | **不適用** | 例行 Form 4；LRCX 非本圖候選 | 站得住 |
| EDGAR | `lead_7f15a5aa` | 2026-08-30 | `edgar:TSM` | TSM 6-K filed 2026-08-11 | **不適用** | 例行 6-K | 站得住 |
| EDGAR | `lead_8449bc60` | 2026-07-31 | `edgar:GFS` | GFS 4 filed 2026-07-31 | **不適用** | 例行 Form 4（董事稅務代扣、RSU）——park 理由是「沒有結構事實」，沒有可被補上的缺口 | 站得住 |
| EDGAR | `lead_91a73c29` | 2026-08-11 | `edgar:CCXI` | CCXI 8-K filed 2026-08-10 [086928] | **不適用** | SPAC 向 sponsor 發行營運資金票據，無圖增量 | 站得住 |
| EDGAR | `lead_e590eca7` | 2026-07-25 | `edgar:AAOI` | AAOI 8-K filed 2026-06-16 | **無法判** | registry 沒有 park 理由、也沒有觸發條件（AAOI 8-K 2026-06-16）——判不了「缺的那一樣」 | — |
| EDGAR | `lead_f1b02f22` | 2026-08-21 | `edgar:MRVL` | MRVL 4 filed 2026-07-16 | **不適用** | 例行 Form 4 | 站得住 |
| X | `lead_043e94a0` | 2026-08-11 | `x:aleabitoreddit` | Nikkei - $JD E-Commerce Giant CEO warns "Robots Will Replace 700,000 D | **不適用** | JD 以機器人取代外送員——不在圖與主題範圍 | 站得住 |
| X | `lead_1b7d39eb` | 2026-07-30 | `x:aleabitoreddit` | Just some takeaways from $META ／ $MSFT earnings calls: Microsoft: - Ex | **未證實** | 缺「後續 10-Q／earnings 具名供應商的 qualification 揭露」——到 10-04 沒找到（MSFT、META 的下一份 10-Q 在 10 月底） | 站得住 |
| X | `lead_2c061488` | 2026-08-07 | `x:aleabitoreddit` | I just realized Boston Dynamics CEO shared the same sentiment: “Roboti | **未證實** | 缺「國家機器人戰略立法、IFR 新數據、獨立的 Agility 供應商清單」——沒找到（S-4 揭露的是客戶與財報，不是供應商清單） | 站得住 |
| X | `lead_3df060cf` | 2026-08-10 | `x:aleabitoreddit` | Just some near term events: - OCP APAC tomorrow (Ayar, Lightmatter, $A | **不適用** | 行事曆型貼文，沒有主張 | 站得住 |
| X | `lead_5b6c52c2` | 2026-08-04 | `x:aleabitoreddit` | $SIVE: "Intent to complete the [NASDAQ] listing process over the next  | **未證實** | 缺「Sivers 遞交 Nasdaq 申請／註冊文件，或公告完成、延後、取消」——EDGAR 2026-07 起 F-1／DRS／20-F／6-K 0 份；庫內 Q2 報告摘錄沒有上市字樣（摘錄不是全文，「找不到」≠「不存在」，L11-5） | 站得住 |
| X | `lead_6e6000e1` | 2026-08-24 | `x:aleabitoreddit` | $XPEV carves out its robotics unit and raises >$900M at $6.3B+ valuati | **證實** | 缺「Agility 歷史財報（要等 S-4）」——**CCXI S-4 2026-09-04**（accession 0001213900-26-097764）的財報索引含「Audited Financial Statements of Agility Robotics, Inc.」（2025、2024 年資產負債表與損益表）；S-4/A 09-30 | 缺口已補：當時 park（等 S-4）是對的；S-4/A 已由 EDGAR feed 在 10-04 入圖（[683]），這則 X lead 本身仍 parked、沒被接回（見「這次回查本身撞到的事」） |
| X | `lead_798000da` | 2026-08-11 | `x:aleabitoreddit` | Looks like there's a high power cylindrical cell / BBU cell shortage ( | **不適用** | BBU 電芯短缺——當時不在任何追蹤主題（新題材候選）；與 P3 相關但各自回答（registration §7.3） | 站得住 |
| X | `lead_7bbf1d13` | 2026-07-25 | `aleabitoreddit_rss` | Sivers: The Undiscovered CPO Laser Chokepoint + Customer Mapping | **未證實** | 缺「Ayar／Marvell／Sivers／WIN 一手更新供應商、合格或量產狀態」——**有一手更新但方向相反**：穩懋 2026-09-09 簡報把 CW-DFB 標「Ongoing Qualification」（[682]），沒有證實量產 | 站得住 |
| X | `lead_ba473b6b` | 2026-08-07 | `x:aleabitoreddit` | So Jensen himself went out to do damage control with $NVDA delays repo | **未證實** | 缺「公開的 Morgan 報告，或 NVIDIA／客戶申報、訪談逐字揭露同一組延後數字」——EDGAR 全文檢索 08-07 起「Kyber」0 份；「Rubin Ultra」片語兩次回 HTTP 500（失敗，不是 0）；沒找到 | 站得住 |
| X | `lead_cb2644d6` | 2026-07-29 | `x:aleabitoreddit` | Kim Sunwoo of Meritz Securities: "This Is Not the Time to Sell Samsung | **未證實** | 缺「新的公司申報改寫 SCA 條款或實際供應」——沒找到（Micron FY26 10-K 預計 10 月） | 站得住 |
| 公司／新聞 feed | `lead_0e0197f7` | 2026-08-20 | `sivers:press` | Invitation to Presentation of Sivers Semiconductors’ Q2 2026 Report | **不適用** | IR 排程公告 | 站得住 |
| 公司／新聞 feed | `lead_27625bd1` | 2026-08-11 | `yahoo:iqe-l` | IQE completes fundraising and reports wider losses but improved tradin | **無法判** | registry 沒有 park 理由、也沒有觸發條件（IQE 募資與虧損擴大） | — |
| 公司／新聞 feed | `lead_299f9846` | 2026-08-11 | `mfn:sivers-semiconductors` | Sivers Semiconductors Updates Financial Reporting Calendar | **不適用** | 財報行事曆更新 | 站得住 |
| 公司／新聞 feed | `lead_2e5d8c3f` | 2026-08-11 | `mfn:sivers-semiconductors` | Sivers Semiconductors AB Postpones Publication of Annual Report 2025 A | **不適用** | 延後年報事件已被 05-13 年報實際發布 supersede | 站得住 |
| 公司／新聞 feed | `lead_697707f8` | 2026-08-11 | `mfn:sivers-semiconductors` | Sivers Semiconductors: Sivers & GlobalFoundries Advance AI Data Center | **不適用** | 重複既有圖增量 | 站得住 |
| 公司／新聞 feed | `lead_86106539` | 2026-08-11 | `mfn:sivers-semiconductors` | Sivers Semiconductors Announces Intention to Carry Out a Directed Shar | **不適用** | 定向增發結果（事件觀測，已由 Engine C／thesis 承載） | 站得住 |
| 公司／新聞 feed | `lead_a6a00003` | 2026-09-24 | `mops:4979.TWO` | 4979.TWO 華星光 重訊 2026-09-23：本公司有價證券達公布注意交易資訊標準，故公布相關 訊息，以利投資人區別瞭解。 | **不適用** | 櫃買注意交易資訊；月營收由 collector 承載 | 站得住 |
| 公司／新聞 feed | `lead_a7ab5e10` | 2026-08-11 | `yahoo:iqe-l` | IQE appoints MACOM executives to board under strategic partnership agr | **不適用** | MACOM 代表董事就任——既有協議的治理完成 | 站得住 |
| decompose | `lead_1446a653` | 2026-08-29 | `decompose:nvda-cpo-switch-2026-08-29` | CPO switch 液冷層：Q3450 液冷冷板同時冷卻 switch core 與光模組——誰供應資料中心級 CPO 液冷？一手未點名＝ | **未證實** | 缺「CPO 專用冷板單一供應商認證，或熱管理成為揭露的良率瓶頸」——沒有；反而 NVIDIA 技術部落格（2025-05-16，[694]）寫明 MGX 液冷元件刻意多源、avoiding vendor lock-in（早於 park 日，不算之後的一手） | 站得住，而且有客戶端原文撐 |
| decompose | `lead_55bd36e6` | 2026-09-09 | `decompose:nvda-cpo-switch-2026-08-29` | 可拆卸光連接器層：Spectrum-X 用 detachable optical connector 支撐自動化量產；SENKO 具名於 N | **不適用** | SENKO 非上市、沒有可買的標的——park 理由不是缺證據 | 站得住 |
| decompose | `lead_95b0d362` | 2026-08-31 | `decompose:nvda-cpo-switch-2026-08-29` | CPO 光纖層：laser input fiber（每 engine 2 條）＋內部 fiber routing；Corning／Sumit | **未證實** | 缺「TFC 或 Browave 法說／公告具名揭露 NVIDIA CPO 供應內容與量」——沒找到（未逐家查 TFC、Browave 的期中報告） | 站得住（多供應商、非瓶頸） |
| decompose | `lead_bc427a52` | 2026-08-29 | `decompose:nvda-cpo-switch-2026-08-29` | 光子晶圓級測試／KGD 層：CPO 把光學整合進 switch 封裝後，photonics wafer test／known-good-di | **未證實** | 缺「FormFactor／Advantest 財報揭露 SiPh 測試營收分項或 CPO 客戶量產訂單」——FormFactor 08-28 後沒有非內部人申報；EDGAR「co-packaged optics」兩則命中都不是這兩家 | 站得住 |
| 圖內部 | `lead_5087a657` | 2026-09-02 | `coverage-gap-2026-09-02` | [decompose 殘骸／人形] tech:force_torque_sensor 零供應商——人形關節/腕踝力矩感測器具名供應商(ATI | **未證實** | 缺「使用者核准 onboard，或任一人形製造商具名採用 ATI 感測器」——onboard 已核准（[446] go），但那是人的決定、不是之後的一手；人形製造商具名採用 ATI 沒找到 | 站得住 |
| 圖內部 | `lead_905b4949` | 2026-08-30 | `loop:runway-refresh` | HDS 6324 runway 觀測刷新：以 2027年3月期 Q1 決算短信（2026-08 上旬發布、資產負債表日 2026-06-30 | **不適用** | runway 刷新已完成並走 pq2 [274]（研究動作，不是缺證據） | 站得住 |
| 題材掃描 | `lead_2cdf807d` | 2026-09-12 | `weekly:cpo` | GIGALIGHT socket-based 1.6T NPO：工程樣品可出貨，但 Flip-Chip 熱膨脹與 socket 壓合一致性仍 | **未證實** | 缺「獨立的客戶、OIF 或製造端來源證實 socket／flip-chip 是量產障礙」——沒找到 | 站得住 |
| 題材掃描 | `lead_fcc4ddc4` | 2026-07-26 | `weekly:sivers` | Sivers 2026-07-21 lock-up 到期與 insider transactions | **不適用** | 已驗證並寫入 Engine C、掛在 thesis 上——追源本身已完成 | 站得住 |

## 這次回查本身撞到的事

- **2 則 parked 沒有 park 理由也沒有觸發條件**（`lead_e590eca7`、`lead_27625bd1`）——「為什麼停、等什麼」都沒寫，之後沒有人會知道什麼時候該重看（F5 的形狀）。兩則都是 07-25／08-11 早期的 lead。
- **park 缺的那一樣出現了、系統也接到了那份文件，卻沒有接回那則 park**（failure log #15；proposal 的 F5「park 了就沒人再看」，registration X2 開題就預期）：
  - park 時自動建 watch（`engine_b/leads.py:497-524`）只對非終局的 trace status 生效；`original_obtained` 在 `config/lead_trace_status.json` 是終局值
    （`terminal: true`），所以這類 park 寫下的 `trace_next_trigger` 預設沒有 watch 在等它。母體 353 則裡有 watch 在等的（`wake_lead`＝本則，或 `wake_pq2`＝本則的 pq2 編號）
    只有 **9 則**（active 7）。寫了 `trace_next_trigger` 的 226 則：以「後續 Form 4」開頭的通用模板 75、以「無」開頭 17、其餘 134——其餘裡有 watch 在等的 8 則；
    134 則裡真正在等一個具體事件的有幾則要逐則判，本報告不判。（出現在別的 watch 的 `consumed_leads` 裡的不算：那是「它叫醒過別人」，不是在等。）
  - **同一份 S-4 一次斷了四則**：09-04 CCXI 公開遞交 S-4（含 Agility 2025、2024 年經審計財報）；下面四則 park 等的東西因此出現，今天全部仍是 parked。
    - `lead_6e6000e1`（樣本內，唯一證實）：缺「Agility 歷史財報」。寫下的觸發是「遞交 S-4 或 S-4/A **並生效**」——生效還沒發生（CCXI 08-25 之後的申報沒有 EFFECT），
      但缺的那一樣在遞件時就出現了。它的等待掛在 pq2 [200] 與 watch `ew_0003`（08-31 建立，`entity_filing_signal`，盯 `co:agility_robotics`，註記「Agility 無 ticker，T0 靠 co: id、T2 輪詢補」）：
      S-4 由 CCXI 遞件，那條 EDGAR lead（`lead_f1cf205e`）的 entities 只有 `co:churchill_capital_xi`，T0 對不上；`ew_0003` 的 T2 輪詢停在 08-31
      （T2 sweep 已移出 daily、改由互動 session 跑研究段第 7 段 `pollable_watches`；今天 active 且可輪詢的 15 條，最近一次輪詢 09-21，6 條從沒輪詢過）；
      09-22 [200] 隨 decision_lab 機制退役被 drop，09-24 `ew_0003` 以 `pq2_item_gone` 關閉。
    - `lead_642cfd67`（樣本外，CCXI 10-Q 08-13）：觸發「公開 Form S-4 含 Agility 經審計財務，或交易完成並取得 AGLT ticker」——前半句 09-04 成立；沒有 watch 等它。
    - `lead_b30c33e9`（樣本外，X 07-29）：觸發「Agility 公開 S-4／具名供應鏈或實際量產揭露，才重新評估公司層 graph delta」——09-04 成立，graph delta 也已在 [683] 評估；沒有 watch 等它。
    - `lead_f1cf205e`（樣本外，S-4 那條 EDGAR lead 本身；第一次 park 是 partial、現在是 `original_obtained`）：觸發「SEC S-4 full text becomes indexable…」——至遲 10-04 成立（S-4/A 全文已用於 [683]）。
      它有 active watch `ew_0074`，09-15 被 CCXI 的 Digit 5 推文叫醒過一次；09-30 的 S-4/A 沒有叫醒它（`woken_by` 空、重啟紀錄只有 09-15 那一次）。
  - **文件本身沒漏**：S-4/A（09-30）的 lead `lead_44e588c4` 在 10-04 的 7.1 積壓 drain 做成入圖包、使用者核准後入圖
    （pq2 [683]：Schaeffler 部署 Digit、NVIDIA／Schaeffler 入股、致動器列關鍵零組件——歷史財報屬 A2、不入圖）。斷的是**連結**。
  - 同形、事件還沒發生的一則：`lead_5b6c52c2` 等「Sivers 遞交 Nasdaq 申請或公告上市」——`ew_0042` 在盯 Sivers 的 Nasdaq 公告，但醒了叫的是 `lead_9b9d5797`。
    （`lead_ba473b6b` 等「公開的 Morgan 報告或 NVIDIA 逐字」——沒有 watch 等它；`ew_0046` 盯的是另一份 Morgan Stanley CPO note，不是同一個事件。）
  - 所以 **H2 的「事後證實」系統自己不會知道**——這次是回放逐則重查才接上的。

## 偏差標註（registration §0.1）

| 偏差 | 本報告的情況 |
|---|---|
| ① discovery lookahead | 「之後有沒有一手」是 2026-10-05 回頭查的：查得到的是今天找得到的文件；未逐家查的（TFC、Browave 期中報告等）照寫「沒找到」，不寫「不存在」 |
| ② 選樣偏差 | 分層、不按比例（EDGAR 10／237、X 10／67、feed 8／36，其餘全取）；合併時依層母體加權 |
| ③ 超額基準回溯 | 唯一一則證實在機器人鏈——組未定義，只印絕對報酬 |

## 附錄：產生程式碼（逐字）

### `r2_dump.py`

```python
"""R2 樣本 36 則（registration 附錄 C 的程式，逐字重算）＋每則的 park 理由與觸發條件，寫 r2_sample.json 並印摘要。唯讀。"""
import hashlib
import json
from pathlib import Path

ROOT = Path(r"C:\Users\Cheng\code\StockBotv2")
T0 = json.loads((ROOT / "library/private/measurement/phase7/T0-2026-10-04.json").read_text(encoding="utf-8"))
POP = set(T0["leads"]["parked_original_obtained_ids"])
P3 = {"lead_18be6b7764b40d7cb853925a0a4836eb", "lead_3e0ba028986066e33b30d7c97c0a33b9",
      "lead_4c2881be9b2f66a3b2b54291e26985aa", "lead_a4c2e14392aec9ce92ee74d1f1b6e81d",
      "lead_fa672a299978b3f3ec2b0cf8ae1d4130"}
QUOTA = {"X": 10, "公司／新聞 feed": 8, "EDGAR": 10}
FEED_PREFIXES = ("mfn:", "sivers:", "yahoo:", "mops:", "official", "prnewswire:", "globenewswire:",
                 "businesswire:", "reuters")


def family(source: str) -> str:
    s = (source or "").lower()
    if s.startswith("x:") or "aleabitoreddit" in s:
        return "X"
    if s.startswith(("edgar:", "sec:")):
        return "EDGAR"
    if "decompose" in s:
        return "decompose"
    if "weekly" in s or "theme_scan" in s:
        return "題材掃描"
    if "graph_walk" in s or "coverage-gap" in s or "gap" in s or "loop" in s:
        return "圖內部"
    if s.startswith(FEED_PREFIXES) or ":" in s:
        return "公司／新聞 feed"
    return "互動點名／其他"


leads = json.loads((ROOT / "library/leads/pending_leads.json").read_text(encoding="utf-8"))["leads"]
src = {lid: x.get("source") for lid, x in leads.items()}
strata: dict[str, list[str]] = {}
for lid in sorted(POP - P3):
    strata.setdefault(family(src[lid]), []).append(lid)
key = lambda lid: hashlib.sha256(f"phase7-R2|{lid}".encode()).hexdigest()  # noqa: E731
sample = {f: sorted(ids, key=key)[:QUOTA.get(f, len(ids))] for f, ids in sorted(strata.items())}
assert sum(len(v) for v in sample.values()) == 36
out = []
for fam, ids in sample.items():
    for lid in ids:
        l = leads[lid]
        refs = l.get("refs") or {}
        tri = l.get("triage") if isinstance(l.get("triage"), dict) else {}
        out.append({"stratum": fam, "stratum_pop": len(strata[fam]), "lead_id": lid, "source": l.get("source"),
                    "status_now": l.get("status"), "first_seen": l.get("first_seen"), "decided_at": tri.get("decided_at"),
                    "company_id": l.get("company_id"), "entities": (l.get("entities") or {}).get("company_ids"),
                    "tickers": (l.get("entities") or {}).get("tickers"), "title": l.get("title"), "url": l.get("url"),
                    "trace_status": refs.get("trace_status"), "parked_reason": refs.get("parked_reason"),
                    "trace_next_trigger": refs.get("trace_next_trigger"), "trace_original_url": refs.get("trace_original_url"),
                    "trace_original_date": refs.get("trace_original_date")})
(Path(__file__).parent / "r2_sample.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print({f: f"{len(v)}／{len(strata[f])}" for f, v in sample.items()})
for r in out:
    print(f"[{r['stratum']}] {r['lead_id'][:13]} {r['status_now']} {str(r['decided_at'] or r['first_seen'])[:10]} {r['source']}"
          f"\n    T: {str(r['title'])[:120]}\n    P: {str(r['parked_reason'])[:200]}\n    N: {str(r['trace_next_trigger'])[:150]}")
```

### `r2_watch_check.py`

```python
"""R2 樣本 36 則：每則有沒有 watch 掛著（wake_lead＝本則、或 wake_pq2＝本則 pq2_ref），watch 現況；外加 CCXI 時間線。唯讀。"""
import json
from pathlib import Path

ROOT = Path(r"C:\Users\Cheng\code\StockBotv2")
HERE = Path(__file__).parent
sample = json.loads((HERE / "r2_sample.json").read_text(encoding="utf-8"))
leads = json.loads((ROOT / "library/leads/pending_leads.json").read_text(encoding="utf-8"))["leads"]
W = json.loads((ROOT / "library/leads/event_watches.json").read_text(encoding="utf-8"))
watches = W.get("watches") if isinstance(W, dict) else W
watches = watches if isinstance(watches, list) else list(watches.values())
pool = {x["n"]: x for x in json.loads((ROOT / "library/leads/todo_pool.json").read_text(encoding="utf-8"))["items"]}
T0 = json.loads((ROOT / "library/private/measurement/phase7/T0-2026-10-04.json").read_text(encoding="utf-8"))
POP = set(T0["leads"]["parked_original_obtained_ids"])


def linked(lid: str) -> list[dict]:
    refs = leads[lid].get("refs") or {}
    pq = refs.get("pq2_ref")
    out = []
    for w in watches:
        hit = []
        if w.get("wake_lead") == lid:
            hit.append("wake_lead")
        if lid in (w.get("consumed_leads") or []):
            hit.append("consumed_leads")
        if pq is not None and str(w.get("wake_pq2")) == str(pq):
            hit.append("wake_pq2")
        if hit:
            out.append({"watch_id": w["watch_id"], "via": hit, "status": w.get("status"), "kind": w.get("kind"),
                        "entities": w.get("entities"), "woken_by": w.get("woken_by"),
                        "closed": w.get("closed"), "reactivations": len(w.get("reactivations") or [])})
    return out


def summarize(ids) -> dict:
    # waiter＝watch 在等這則（wake_lead／wake_pq2）；signal＝這則叫醒過別的 watch（consumed_leads），不算在等
    c = {"total": 0, "has_pq2_ref": 0, "waiter_watch": 0, "waiter_active": 0, "signal_only": 0}
    for lid in ids:
        c["total"] += 1
        refs = leads[lid].get("refs") or {}
        if refs.get("pq2_ref") is not None:
            c["has_pq2_ref"] += 1
        ws = linked(lid)
        waiters = [w for w in ws if {"wake_lead", "wake_pq2"} & set(w["via"])]
        if waiters:
            c["waiter_watch"] += 1
        if any(w["status"] == "active" for w in waiters):
            c["waiter_active"] += 1
        if ws and not waiters:
            c["signal_only"] += 1
    return c


rows = []
for r in sample:
    lid = r["lead_id"]
    refs = leads[lid].get("refs") or {}
    pq = refs.get("pq2_ref")
    pitem = pool.get(int(pq)) if pq is not None and str(pq).isdigit() else None
    rows.append({"lead_id": lid, "stratum": r["stratum"], "pq2_ref": pq,
                 "pq2": None if pitem is None else {k: pitem.get(k) for k in ("type", "resolution", "resolved_at", "reason")},
                 "watches": linked(lid)})
(HERE / "r2_watch_check.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("sample", summarize([r["lead_id"] for r in sample]))
print("population", summarize(sorted(POP)))
for r in rows:
    if r["pq2_ref"] is not None or r["watches"]:
        print(r["lead_id"][:13], r["stratum"], "pq2", r["pq2_ref"], r["pq2"] and (r["pq2"]["type"], r["pq2"]["resolution"], str(r["pq2"]["resolved_at"])[:10]))
        for w in r["watches"]:
            print("   ", w["watch_id"], w["via"], w["status"], w["kind"], w["entities"], "woken" if w["woken_by"] else "never-woken",
                  "react", w["reactivations"], (w["closed"] or {}).get("kind"), str((w["closed"] or {}).get("at"))[:10])

with_trigger = [lid for lid in sorted(POP) if str((leads[lid].get("refs") or {}).get("trace_next_trigger") or "").strip()]
print("population 有 trace_next_trigger（研究在等未來事件）", summarize(with_trigger))
trig_text = {lid: str((leads[lid].get("refs") or {}).get("trace_next_trigger")).strip() for lid in with_trigger}
form4 = [lid for lid, t in trig_text.items() if t.startswith("後續 Form 4")]
none_ = [lid for lid, t in trig_text.items() if t.startswith("無")]
print(f"  其中以「後續 Form 4」開頭 {len(form4)}、以「無」開頭 {len(none_)}、其餘 {len(with_trigger) - len(form4) - len(none_)}")
print("  其餘裡有 watch 在等的：", summarize([lid for lid in with_trigger if lid not in form4 and lid not in none_]))
s4 = [lid for lid, t in trig_text.items() if "S-4" in t and "Agility" in t]
print("  觸發條件寫「S-4」且「Agility」的：", [(lid[:13], leads[lid]["status"], leads[lid].get("source")) for lid in s4])

import sys  # noqa: E402

sys.path.insert(0, str(ROOT))
from fetchers.edgar import fetch_submissions, get_cik, recent_filings  # noqa: E402

ccxi = [f for f in recent_filings(fetch_submissions(get_cik("CCXI"))) if f["filed_date"] >= "2026-08-25"]
print("CCXI 2026-08-25 之後的申報：", [(f["filed_date"], f["form_type"]) for f in ccxi])
print("  其中 EFFECT／424B：", [f["form_type"] for f in ccxi if f["form_type"] == "EFFECT" or f["form_type"].startswith("424B")])

polls = {}
for w in watches:
    p = w.get("poll") or {}
    if w.get("status") == "active" and p.get("eligible"):
        k = str(p.get("last_checked"))[:10]
        polls[k] = polls.get(k, 0) + 1
print("active 且可輪詢的 watch，依 poll.last_checked：", sorted(polls.items()), "合計", sum(polls.values()))

print("\n== CCXI／Agility 相關 lead（2026-08-15 之後）")
for lid, l in sorted(leads.items(), key=lambda kv: str(kv[1].get("first_seen"))):
    s = json.dumps({k: l.get(k) for k in ("source", "title", "company_id", "entities")}, ensure_ascii=False)
    if ("CCXI" in s or "churchill" in s.lower() or "agility" in s.lower()) and str(l.get("first_seen")) >= "2026-08-15":
        refs = l.get("refs") or {}
        print(lid[:13], str(l.get("first_seen"))[:16], l.get("status"), l.get("source"), "|", str(l.get("title"))[:70],
              "| trace", refs.get("trace_status"), "| ra", str(refs.get("research_action_id"))[:14], "| pq2", refs.get("pq2_ref"))
```

### `make_r2_report.py`

```python
"""產生 docs/reports/phase7/replay-r2-parked.md：36 則樣本取自 r2_sample.json（附錄 C 的程式重算），逐則裁決寫在 VERDICT（研究判斷，2026-10-05）。"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\Cheng\code\StockBotv2")
HERE = Path(__file__).parent
SAMPLE = json.loads((HERE / "r2_sample.json").read_text(encoding="utf-8"))
NA, NJ, NO, YES = "不適用", "無法判", "未證實", "證實"
# lead 前 13 碼 → (裁決, 證據或理由, park 理由今天站不站得住)
VERDICT = {
    "lead_8449bc60": (NA, "例行 Form 4（董事稅務代扣、RSU）——park 理由是「沒有結構事實」，沒有可被補上的缺口", "站得住"),
    "lead_6648e5f5": (NA, "例行 Form 4", "站得住"),
    "lead_51262d08": (NA, "10-Q 素材已由 [316] 涵蓋（重複）", "站得住"),
    "lead_f1b02f22": (NA, "例行 Form 4", "站得住"),
    "lead_e590eca7": (NJ, "registry 沒有 park 理由、也沒有觸發條件（AAOI 8-K 2026-06-16）——判不了「缺的那一樣」", "—"),
    "lead_7f15a5aa": (NA, "例行 6-K", "站得住"),
    "lead_29afe4c0": (NA, "例行 Form 4（RSU 歸屬）", "站得住"),
    "lead_91a73c29": (NA, "SPAC 向 sponsor 發行營運資金票據，無圖增量", "站得住"),
    "lead_06a8ab21": (NA, "例行 Form 4（稅務代扣）", "站得住"),
    "lead_79e1eada": (NA, "例行 Form 4；LRCX 非本圖候選", "站得住"),
    "lead_1b7d39eb": (NO, "缺「後續 10-Q／earnings 具名供應商的 qualification 揭露」——到 10-04 沒找到（MSFT、META 的下一份 10-Q 在 10 月底）", "站得住"),
    "lead_6e6000e1": (YES, "缺「Agility 歷史財報（要等 S-4）」——**CCXI S-4 2026-09-04**（accession 0001213900-26-097764）的財報索引含「Audited Financial Statements of Agility Robotics, Inc.」（2025、2024 年資產負債表與損益表）；S-4/A 09-30", "缺口已補：當時 park（等 S-4）是對的；S-4/A 已由 EDGAR feed 在 10-04 入圖（[683]），這則 X lead 本身仍 parked、沒被接回（見「這次回查本身撞到的事」）"),
    "lead_043e94a0": (NA, "JD 以機器人取代外送員——不在圖與主題範圍", "站得住"),
    "lead_ba473b6b": (NO, "缺「公開的 Morgan 報告，或 NVIDIA／客戶申報、訪談逐字揭露同一組延後數字」——EDGAR 全文檢索 08-07 起「Kyber」0 份；「Rubin Ultra」片語兩次回 HTTP 500（失敗，不是 0）；沒找到", "站得住"),
    "lead_3df060cf": (NA, "行事曆型貼文，沒有主張", "站得住"),
    "lead_2c061488": (NO, "缺「國家機器人戰略立法、IFR 新數據、獨立的 Agility 供應商清單」——沒找到（S-4 揭露的是客戶與財報，不是供應商清單）", "站得住"),
    "lead_798000da": (NA, "BBU 電芯短缺——當時不在任何追蹤主題（新題材候選）；與 P3 相關但各自回答（registration §7.3）", "站得住"),
    "lead_5b6c52c2": (NO, "缺「Sivers 遞交 Nasdaq 申請／註冊文件，或公告完成、延後、取消」——EDGAR 2026-07 起 F-1／DRS／20-F／6-K 0 份；庫內 Q2 報告摘錄沒有上市字樣（摘錄不是全文，「找不到」≠「不存在」，L11-5）", "站得住"),
    "lead_cb2644d6": (NO, "缺「新的公司申報改寫 SCA 條款或實際供應」——沒找到（Micron FY26 10-K 預計 10 月）", "站得住"),
    "lead_7bbf1d13": (NO, "缺「Ayar／Marvell／Sivers／WIN 一手更新供應商、合格或量產狀態」——**有一手更新但方向相反**：穩懋 2026-09-09 簡報把 CW-DFB 標「Ongoing Qualification」（[682]），沒有證實量產", "站得住"),
    "lead_55bd36e6": (NA, "SENKO 非上市、沒有可買的標的——park 理由不是缺證據", "站得住"),
    "lead_95b0d362": (NO, "缺「TFC 或 Browave 法說／公告具名揭露 NVIDIA CPO 供應內容與量」——沒找到（未逐家查 TFC、Browave 的期中報告）", "站得住（多供應商、非瓶頸）"),
    "lead_1446a653": (NO, "缺「CPO 專用冷板單一供應商認證，或熱管理成為揭露的良率瓶頸」——沒有；反而 NVIDIA 技術部落格（2025-05-16，[694]）寫明 MGX 液冷元件刻意多源、avoiding vendor lock-in（早於 park 日，不算之後的一手）", "站得住，而且有客戶端原文撐"),
    "lead_bc427a52": (NO, "缺「FormFactor／Advantest 財報揭露 SiPh 測試營收分項或 CPO 客戶量產訂單」——FormFactor 08-28 後沒有非內部人申報；EDGAR「co-packaged optics」兩則命中都不是這兩家", "站得住"),
    "lead_0e0197f7": (NA, "IR 排程公告", "站得住"),
    "lead_86106539": (NA, "定向增發結果（事件觀測，已由 Engine C／thesis 承載）", "站得住"),
    "lead_a6a00003": (NA, "櫃買注意交易資訊；月營收由 collector 承載", "站得住"),
    "lead_a7ab5e10": (NA, "MACOM 代表董事就任——既有協議的治理完成", "站得住"),
    "lead_27625bd1": (NJ, "registry 沒有 park 理由、也沒有觸發條件（IQE 募資與虧損擴大）", "—"),
    "lead_2e5d8c3f": (NA, "延後年報事件已被 05-13 年報實際發布 supersede", "站得住"),
    "lead_697707f8": (NA, "重複既有圖增量", "站得住"),
    "lead_299f9846": (NA, "財報行事曆更新", "站得住"),
    "lead_905b4949": (NA, "runway 刷新已完成並走 pq2 [274]（研究動作，不是缺證據）", "站得住"),
    "lead_5087a657": (NO, "缺「使用者核准 onboard，或任一人形製造商具名採用 ATI 感測器」——onboard 已核准（[446] go），但那是人的決定、不是之後的一手；人形製造商具名採用 ATI 沒找到", "站得住"),
    "lead_fcc4ddc4": (NA, "已驗證並寫入 Engine C、掛在 thesis 上——追源本身已完成", "站得住"),
    "lead_2cdf807d": (NO, "缺「獨立的客戶、OIF 或製造端來源證實 socket／flip-chip 是量產障礙」——沒找到", "站得住"),
}
CCXI = {"park": "2026-08-24", "confirm": "2026-09-04", "end": "2026-10-02", "pre": -0.049, "post": -0.1052}

rows = []
for r in SAMPLE:
    v = VERDICT[r["lead_id"][:13]]
    rows.append({**r, "verdict": v[0], "evidence": v[1], "stands": v[2]})
assert len(rows) == 36 and len(VERDICT) == 36

strata = defaultdict(list)
for r in rows:
    strata[r["stratum"]].append(r)
pop = {k: v[0]["stratum_pop"] for k, v in strata.items()}
t_strata = ["| 層 | 母體 | 樣本 | 證實 | 未證實 | 無法判 | 不適用 | 層內證實比例（全樣本為分母） | 層內證實比例（排除不適用、無法判） |",
            "|---|---|---|---|---|---|---|---|---|"]
w_all = w_sub = 0.0
w_sub_pop = 0.0
for k in sorted(strata, key=lambda x: -pop[x]):
    v = strata[k]
    c = {lab: sum(1 for r in v if r["verdict"] == lab) for lab in (YES, NO, NJ, NA)}
    p_all = c[YES] / len(v)
    sub = c[YES] + c[NO]
    p_sub = (c[YES] / sub) if sub else None
    w_all += pop[k] * p_all
    if p_sub is not None:
        w_sub += pop[k] * (sub / len(v)) * p_sub
        w_sub_pop += pop[k] * (sub / len(v))
    t_strata.append(f"| {k} | {pop[k]} | {len(v)} | {c[YES]} | {c[NO]} | {c[NJ]} | {c[NA]} | {p_all:.1%} | "
                    f"{'—（沒有可判的列）' if p_sub is None else f'{p_sub:.1%}'} |")
N = sum(pop.values())
weighted_all = w_all / N
weighted_sub = (w_sub / w_sub_pop) if w_sub_pop else None
n_yes = sum(1 for r in rows if r["verdict"] == YES)

t_rows = ["| 層 | lead | park 日 | 來源 | 標題（節錄） | 裁決 | 缺的那一樣與之後的一手 | park 理由今天 |", "|---|---|---|---|---|---|---|---|"]
for r in sorted(rows, key=lambda x: (-pop[x["stratum"]], x["stratum"], x["lead_id"])):
    park = str(r["decided_at"] or r["first_seen"])[:10]
    title = str(r["title"]).replace("|", "／").replace("\n", " ")[:70]
    t_rows.append(f"| {r['stratum']} | `{r['lead_id'][:13]}` | {park} | `{r['source']}` | {title} | **{r['verdict']}** | "
                  f"{r['evidence'].replace('|', '／')} | {r['stands']} |")
code = "\n\n".join(f"### `{n}`\n\n```python\n{(HERE / n).read_text(encoding='utf-8')}```" for n in ("r2_dump.py", "r2_watch_check.py", "make_r2_report.py"))

md = f"""# Phase 7 Step 7.2 — R2 parked 回查（X2）

> **性質：回放報告（評估檔）。** 樣本與抽樣規則照 [`registration.md`](registration.md) §7.3／附錄 C（36 則，程式重算逐則相同）；「證實」照 §1 H2 的定義：
> **之後的一手文件補上了當初 park 理由所缺的那一樣**，只有二手不算（L11-3）。只引用 id、不改任何 ledger。執行：2026-10-05（台北）；量測終點 2026-10-02。

## 一句話

36 則裡**證實 1 則**（CCXI 的 S-4 補上了 Agility 歷史財報）、未證實 11、無法判 2（registry 沒寫 park 理由）、**不適用 22**（park 理由本來就不是缺證據——例行 Form 4、行事曆、重複、非上市標的）。
**H2（X2 的部分）＝不足**（證實 {n_yes} 則 < 4，registration §1 H2「不足」）；依層母體加權的證實比例 **{weighted_all:.1%}**（全樣本為分母）／
{'—' if weighted_sub is None else f'{weighted_sub:.1%}'}（排除不適用與無法判）——照印，不判方向。H2 要與 P3（7.4）合併判。

⚠ **與登記的偏離**：registration §7.3（「之後有沒有一手證實」）與 plan §8 驗收（「每則有證實日或『未證實』」）只有兩類；「無法判」「不適用」是回查時加的。照登記的二分法這兩類都算未證實——
證實數（{n_yes}）、H2 判讀（不足）與全樣本為分母的 {weighted_all:.2%} 都不變；只有「排除不適用與無法判」那個比例是額外的數字，不進判讀。

## 各層

{chr(10).join(t_strata)}

- 加權（registration §7.3：合併任何比例時依層的母體大小加權）：全樣本為分母 **{weighted_all:.2%}**；排除不適用與無法判 **{'—' if weighted_sub is None else f'{weighted_sub:.2%}'}**。
- ⚠ EDGAR 層 10 則裡 9 則是「不適用」：parked × `original_obtained` 的 237 則 EDGAR 多半是例行申報——**這個母體量到的主要是「例行申報被正確 park」**，不是「保守擋掉了真東西」。

## 唯一一則證實的價格（H2 的量法）

`lead_6e6000e1`（X 帳號點名 XPEV 機器人分拆、Agility 估值）：park 日 {CCXI['park']}（triage decided_at）→ 證實日 {CCXI['confirm']}（S-4）→ 量測日 {CCXI['end']}。
標的取 CCXI（Agility 的 SPAC）：**park→證實 {CCXI['pre']:+.1%}、證實→量測 {CCXI['post']:+.1%}**（絕對報酬）。機器人鏈沒有主題等權組——超額寫「組未定義」，不拿別的組代替（registration §0.1）。
n＝1，不進判讀線。

## 逐則

{chr(10).join(t_rows)}

## 這次回查本身撞到的事

- **2 則 parked 沒有 park 理由也沒有觸發條件**（`lead_e590eca7`、`lead_27625bd1`）——「為什麼停、等什麼」都沒寫，之後沒有人會知道什麼時候該重看（F5 的形狀）。兩則都是 07-25／08-11 早期的 lead。
- **park 缺的那一樣出現了、系統也接到了那份文件，卻沒有接回那則 park**（failure log #15；proposal 的 F5「park 了就沒人再看」，registration X2 開題就預期）：
  - park 時自動建 watch（`engine_b/leads.py:497-524`）只對非終局的 trace status 生效；`original_obtained` 在 `config/lead_trace_status.json` 是終局值
    （`terminal: true`），所以這類 park 寫下的 `trace_next_trigger` 預設沒有 watch 在等它。母體 353 則裡有 watch 在等的（`wake_lead`＝本則，或 `wake_pq2`＝本則的 pq2 編號）
    只有 **9 則**（active 7）。寫了 `trace_next_trigger` 的 226 則：以「後續 Form 4」開頭的通用模板 75、以「無」開頭 17、其餘 134——其餘裡有 watch 在等的 8 則；
    134 則裡真正在等一個具體事件的有幾則要逐則判，本報告不判。（出現在別的 watch 的 `consumed_leads` 裡的不算：那是「它叫醒過別人」，不是在等。）
  - **同一份 S-4 一次斷了四則**：09-04 CCXI 公開遞交 S-4（含 Agility 2025、2024 年經審計財報）；下面四則 park 等的東西因此出現，今天全部仍是 parked。
    - `lead_6e6000e1`（樣本內，唯一證實）：缺「Agility 歷史財報」。寫下的觸發是「遞交 S-4 或 S-4/A **並生效**」——生效還沒發生（CCXI 08-25 之後的申報沒有 EFFECT），
      但缺的那一樣在遞件時就出現了。它的等待掛在 pq2 [200] 與 watch `ew_0003`（08-31 建立，`entity_filing_signal`，盯 `co:agility_robotics`，註記「Agility 無 ticker，T0 靠 co: id、T2 輪詢補」）：
      S-4 由 CCXI 遞件，那條 EDGAR lead（`lead_f1cf205e`）的 entities 只有 `co:churchill_capital_xi`，T0 對不上；`ew_0003` 的 T2 輪詢停在 08-31
      （T2 sweep 已移出 daily、改由互動 session 跑研究段第 7 段 `pollable_watches`；今天 active 且可輪詢的 15 條，最近一次輪詢 09-21，6 條從沒輪詢過）；
      09-22 [200] 隨 decision_lab 機制退役被 drop，09-24 `ew_0003` 以 `pq2_item_gone` 關閉。
    - `lead_642cfd67`（樣本外，CCXI 10-Q 08-13）：觸發「公開 Form S-4 含 Agility 經審計財務，或交易完成並取得 AGLT ticker」——前半句 09-04 成立；沒有 watch 等它。
    - `lead_b30c33e9`（樣本外，X 07-29）：觸發「Agility 公開 S-4／具名供應鏈或實際量產揭露，才重新評估公司層 graph delta」——09-04 成立，graph delta 也已在 [683] 評估；沒有 watch 等它。
    - `lead_f1cf205e`（樣本外，S-4 那條 EDGAR lead 本身；第一次 park 是 partial、現在是 `original_obtained`）：觸發「SEC S-4 full text becomes indexable…」——至遲 10-04 成立（S-4/A 全文已用於 [683]）。
      它有 active watch `ew_0074`，09-15 被 CCXI 的 Digit 5 推文叫醒過一次；09-30 的 S-4/A 沒有叫醒它（`woken_by` 空、重啟紀錄只有 09-15 那一次）。
  - **文件本身沒漏**：S-4/A（09-30）的 lead `lead_44e588c4` 在 10-04 的 7.1 積壓 drain 做成入圖包、使用者核准後入圖
    （pq2 [683]：Schaeffler 部署 Digit、NVIDIA／Schaeffler 入股、致動器列關鍵零組件——歷史財報屬 A2、不入圖）。斷的是**連結**。
  - 同形、事件還沒發生的一則：`lead_5b6c52c2` 等「Sivers 遞交 Nasdaq 申請或公告上市」——`ew_0042` 在盯 Sivers 的 Nasdaq 公告，但醒了叫的是 `lead_9b9d5797`。
    （`lead_ba473b6b` 等「公開的 Morgan 報告或 NVIDIA 逐字」——沒有 watch 等它；`ew_0046` 盯的是另一份 Morgan Stanley CPO note，不是同一個事件。）
  - 所以 **H2 的「事後證實」系統自己不會知道**——這次是回放逐則重查才接上的。

## 偏差標註（registration §0.1）

| 偏差 | 本報告的情況 |
|---|---|
| ① discovery lookahead | 「之後有沒有一手」是 2026-10-05 回頭查的：查得到的是今天找得到的文件；未逐家查的（TFC、Browave 期中報告等）照寫「沒找到」，不寫「不存在」 |
| ② 選樣偏差 | 分層、不按比例（EDGAR 10／237、X 10／67、feed 8／36，其餘全取）；合併時依層母體加權 |
| ③ 超額基準回溯 | 唯一一則證實在機器人鏈——組未定義，只印絕對報酬 |

## 附錄：產生程式碼（逐字）

{code}
"""
(ROOT / "docs" / "reports" / "phase7" / "replay-r2-parked.md").write_text(md, encoding="utf-8", newline="\n")
print(f"寫入 replay-r2-parked.md；證實 {n_yes}；加權 {weighted_all:.4f} / {weighted_sub}")
```
