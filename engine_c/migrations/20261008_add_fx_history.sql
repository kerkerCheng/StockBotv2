-- 歷史匯率（個股頁 S3b，2026-10-08）：FRED 的聯準會 H.10 日序列（例 DEXTAUS＝一美元換幾元台幣）。
-- 可重建投影（L10：今天重抓拿得回來）——同一天重抓就覆寫；寫入端是 engine_c/history_backfill.py::backfill_fx。
-- quote：per_usd＝一美元換幾單位該幣；usd_per＝一單位該幣換幾美元（歐元、英鎊）。SQLite 走同一份 DDL（建表即可，不用遷移）。
CREATE TABLE IF NOT EXISTS fx_history (
    series_id VARCHAR(32) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    quote VARCHAR(8) NOT NULL CHECK (quote IN ('per_usd', 'usd_per')),
    obs_date DATE NOT NULL,
    rate NUMERIC(20,8) NOT NULL CHECK (rate > 0),
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (series_id, obs_date)
);
