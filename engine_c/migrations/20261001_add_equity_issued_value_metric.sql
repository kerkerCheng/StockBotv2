-- fundamental_history.metric 加新股發行金額（Phase 4 Step 4.6；稀釋燈的輸入：us-gaap:StockIssuedDuringPeriodValueNewIssues）。
-- 照營收的慣例拆季度／年度兩個名字；第四季由「年度 − 前三季累計」衍生（engine_c/history_backfill.py）。
-- 欄位內聯的 CHECK 在 Postgres 的預設名稱是 <table>_<column>_check；先刪再建，字彙與 SQLite 建表（METRICS）一致。
-- SQLite 對應的遷移是 engine_c/migrate_fundamental_metrics.py（SQLite 不能 ALTER CHECK，要重建表）。
ALTER TABLE fundamental_history DROP CONSTRAINT IF EXISTS fundamental_history_metric_check;
ALTER TABLE fundamental_history ADD CONSTRAINT fundamental_history_metric_check CHECK (metric IN (
    'revenue_quarter', 'revenue_annual', 'operating_income_quarter', 'operating_income_annual',
    'cash', 'total_debt', 'shares_outstanding_cover',
    'equity_issued_value_quarter', 'equity_issued_value_annual'));
