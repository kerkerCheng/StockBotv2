# Phase 7 監看來源與母體變動（cohort changes）

> **append-only。** 每次監看來源（X 帳號、harvest 來源、雷達）、題材清單、主題等權組或 R3 母體有變動，就在檔尾加一筆：
> **日期｜改了什麼｜為什麼｜影響哪些量測（從哪一天起量、回不回溯）**。T1 manifest 與 T0 的每一類差異都要歸因到這裡的某一筆（plan §11 第 5 項）。
> 新 X 帳號：照 `config/signal_sources.json` 的規則以 probation 加入、`crons/harvest_config.json` 的 handles 同步；**加入日起量、不回溯**（plan §0.1 Q4）。

---

## 2026-10-04　T0

- **T0 manifest**：`library/private/measurement/phase7/T0-2026-10-04.json`（private、不進 Git），sha256 `eb13ae65709a842209e19ae16bfb9d878a22776815dd2d76da4aa19b0afa924a`，
  生成於 2026-10-04T07:09:14Z；對照心跳 `heartbeat_2026-10-04.md`（一致，registration §8）；產生程式碼＝registration 附錄 A。
- **監看來源**：X 帳號 1 個——`aleabitoreddit`（active，tier probation，自 2026-09-17）；harvest 來源 36 個（心跳段 1）；
  `crons/harvest_config.json` sha256 `1a2a4aa6dac12641a8e257082c97067682e58466e7ab36d1d5e42a877044dda2`、
  `config/signal_sources.json` sha256 `8f3c92638d939bdfd0e6a6473c24a5c713457e554c7a3974cc89e57929f81613`。
- **題材**：`config/themes.txt` 3 個主題（cpo、sivers、robotics），sha256 `898c9813fd70ac15ae986c94dfdc9f2e80f37bfd6a5af77572ca381f36082556`。
- **主題等權組**：1 組——`tc_35b0d5cd521656ea`（AI 光互連／CPO，2026-09-30，pq2 [656]，15 檔）。
- **R3 母體**：光通訊組 15 檔＋AI 基礎設施觀察名單 43 檔（registration §5.2）。
- **已知會在 T0 之後發生的變動**（發生時各記一筆，這裡只預告）：Step 7.0f 外部雷達上線（新來源 `web_radar:<theme>`）與 `config/themes.txt` 加 `power`、`cooling`；
  Step 7.1 電力、散熱主題等權組的前瞻定義（pq2）與它們的成分 append 進 R3 母體（從第二個窗口起計，registration §5.3）；使用者之後加的 X 帳號。
