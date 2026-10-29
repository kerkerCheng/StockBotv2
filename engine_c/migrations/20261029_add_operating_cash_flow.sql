-- financial_snapshots 加營業現金流（近四季；yfinance info `operatingCashflow`）。
-- 歸零燈要分「本業燒錢」（營業現金流 < 0）與「擴產花錢」（營業現金流 ≥ 0、自由現金流 < 0）——
-- 自由現金流為負同時承載兩件事（L12；2026-10-29 有獲利卻亮紅 32 檔）。既有列留 NULL，不回填（那天的值不可知）。
-- SQLite 對應的是 engine_c/db.py `_ensure_sqlite_schema` 的 ALTER TABLE ADD COLUMN。
ALTER TABLE financial_snapshots ADD COLUMN IF NOT EXISTS operating_cash_flow_ttm DOUBLE PRECISION;
