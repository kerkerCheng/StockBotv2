-- financial_snapshots 加租賃負債（與 total_debt 同一季；yfinance quarterly_balance_sheet 的 Capital Lease Obligations）。
-- 負債燈比的是總債扣掉租賃的借款（failure log #118，使用者 2026-11-10「#118 只做租賃那一半」）——總債同時承載借款與
-- IFRS 16／ASC 842 的租約（L12）。既有列留 NULL，不回填（分不出租賃，燈照總債判並說）。
-- SQLite 對應的是 engine_c/db.py `_ensure_sqlite_schema` 的 ALTER TABLE ADD COLUMN。
ALTER TABLE financial_snapshots ADD COLUMN IF NOT EXISTS lease_liabilities DOUBLE PRECISION;
