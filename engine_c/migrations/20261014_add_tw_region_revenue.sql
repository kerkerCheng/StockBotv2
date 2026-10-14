-- 台股年度財報地區別營收（個股頁 S3d 第二段，2026-10-14）。
-- 可重建的 ETL 觀測，不是 append-only judgment ledger（L10：MOPS 年報永久可查，今天重取一次拿得回來）。
-- 一列＝一家公司的一份年報的抽取結果（當年與比較年都在 years_json）；同一結果重抓只更新 fetched_at。
-- 營收那一欄由「合計最接近那一年月營收十二個月加總（差 ≤0.3%）」機械認出；對不上就 check_status 不是 ok、讀取端不畫。
-- revenue_basis＝年報自己說收入依什麼分地區（客戶所在地／營運地點／兩者都寫／沒寫），basis_quotes_json 是原文句。
-- available_on＝MOPS 上傳日（filing_metadata），解析不到才用法定期限（次年 3/31）；不是 fetched_at（INV-6）。
-- SQLite 對應的建表住 engine_c/tw_region_revenue.py::ensure_region_revenue_schema（兩邊欄位與約束一致）。
CREATE TABLE IF NOT EXISTS tw_region_revenue_observations (
    observation_id VARCHAR(64) PRIMARY KEY,
    ticker VARCHAR(32) NOT NULL,
    company_code VARCHAR(16) NOT NULL,
    report_year INTEGER NOT NULL,
    years_json TEXT NOT NULL,
    check_status VARCHAR(32) NOT NULL,
    check_reason TEXT,
    revenue_basis VARCHAR(32) NOT NULL,
    basis_quotes_json TEXT NOT NULL,
    currency VARCHAR(8) NOT NULL,
    unit_scale INTEGER NOT NULL CHECK (unit_scale > 0),
    source_filename TEXT,
    available_on DATE NOT NULL,
    available_on_basis VARCHAR(32) NOT NULL,
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload_digest VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tw_region_revenue_ticker
    ON tw_region_revenue_observations (ticker, report_year DESC, fetched_at DESC);
