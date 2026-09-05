-- 會計年度別的分析師共識（EPS 與營收），每一筆在抓取當下就解析成絕對的會計期間。
--
-- 為什麼不是再加幾欄到 financial_snapshots：
-- 既有的 revenue_estimate_next_fy 存的是 yfinance 的 `+1y`——一個**相對於抓取日**的標籤。
-- COHR 在 2026-09 抓到的 `+1y` 是 FY2028，而欄位名叫「下一會計年度」；同一個欄位在財報
-- 前後指的是不同年度（L12 一表兩義）。內部估計要與共識做數值比較，前提是「同一個會計
-- 期間」，所以身分必須是 fiscal_period_end 這個**絕對日期**，且在抓取當下解析、隨列保存。
--
-- ⚠ 單位：estimate_* 以該標的的報表幣別計（currency 欄位），不是 USD；
-- 只能與同一標的、同一會計期間的內部估計比，不得跨標的比絕對值。
-- ⚠ accounting basis（GAAP／non-GAAP）provider 不宣告，本表**不猜**：
-- year_ago_actual 保存 provider 給的去年實際值，供讀取端與一手財報數字機械核對
-- （COHR 實測：yearAgoEps 5.61 ＝ 8-K 的 non-GAAP 稀釋 EPS，≠ GAAP 4.12）。
-- 取不到的期間**不寫列**（缺料＝沒有列，不是 0）。
CREATE TABLE IF NOT EXISTS consensus_estimates (
    id                 BIGSERIAL PRIMARY KEY,
    ticker             VARCHAR(32)  NOT NULL,
    snapshot_date      DATE         NOT NULL,
    bar_date           DATE,
    metric             VARCHAR(16)  NOT NULL CHECK (metric IN ('eps', 'revenue')),
    period_kind        VARCHAR(16)  NOT NULL CHECK (period_kind IN ('fiscal_year')),
    relative_label     VARCHAR(8)   NOT NULL,
    fiscal_period_end  DATE         NOT NULL,
    fiscal_label       VARCHAR(16)  NOT NULL,
    estimate_avg       NUMERIC(24,6),
    estimate_low       NUMERIC(24,6),
    estimate_high      NUMERIC(24,6),
    analyst_count      INTEGER,
    year_ago_actual    NUMERIC(24,6),
    growth             NUMERIC(12,6),
    currency           VARCHAR(8),
    source             VARCHAR(64)  NOT NULL,
    fetched_at         TIMESTAMPTZ  NOT NULL,
    UNIQUE (ticker, snapshot_date, metric, fiscal_period_end, source)
);
CREATE INDEX IF NOT EXISTS idx_consensus_estimates_ticker_date
    ON consensus_estimates (ticker, snapshot_date DESC);
