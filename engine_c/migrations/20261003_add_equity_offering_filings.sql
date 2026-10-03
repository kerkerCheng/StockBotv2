-- 募資文件清單（Phase 6 Step 6.6；稀釋燈的判色依據）：EDGAR submissions 裡的募資文件與不算募資的登記表單，
-- 每份申報一列（accession 主鍵）；判定不存（讀取端 engine_c/offerings.py::is_offering_filing）。
-- equity_offering_checks：每檔最後一次抓清單的時間與涵蓋起點——「抓過、沒有」與「沒抓過」不得同形（L12）。
-- 新表、只 CREATE IF NOT EXISTS，不動既有表。SQLite 由 engine_c/offerings.py::ensure_offering_schema 建（開庫時）。
CREATE TABLE IF NOT EXISTS equity_offering_filings (
    accession VARCHAR(32) PRIMARY KEY,
    ticker VARCHAR(32) NOT NULL,
    cik VARCHAR(16) NOT NULL,
    form VARCHAR(16) NOT NULL,
    items TEXT,
    filed DATE NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_equity_offering_filings_ticker
    ON equity_offering_filings (ticker, filed);

CREATE TABLE IF NOT EXISTS equity_offering_checks (
    ticker VARCHAR(32) PRIMARY KEY,
    cik VARCHAR(16) NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    coverage_from DATE,
    recent_count INTEGER NOT NULL
);
