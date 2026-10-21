-- fundamental_history.metric 加半年營收與營業利益（日韓財報來源 S1，2026-10-21；使用者「日韓 AAA」）。
-- 日本 EDINET 2024-04 起只有半期報告書＋有價證券報告書（沒有 Q1／Q3 法定申報）：下半年＝年度−上半年，標 derived
-- （engine_c/edinet_history.py）。先刪再建，字彙與 SQLite 建表（engine_c/history_backfill.py 的 METRICS）一致。
-- SQLite 對應的遷移是 engine_c/migrate_fundamental_metrics.py（SQLite 不能 ALTER CHECK，要重建表）。
ALTER TABLE fundamental_history DROP CONSTRAINT IF EXISTS fundamental_history_metric_check;
ALTER TABLE fundamental_history ADD CONSTRAINT fundamental_history_metric_check CHECK (metric IN (
    'revenue_quarter', 'revenue_annual', 'operating_income_quarter', 'operating_income_annual',
    'cash', 'total_debt', 'shares_outstanding_cover',
    'equity_issued_value_quarter', 'equity_issued_value_annual',
    'capex_quarter', 'capex_annual',
    'revenue_half', 'operating_income_half'));
