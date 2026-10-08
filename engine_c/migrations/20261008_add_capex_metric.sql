-- fundamental_history.metric 加現金資本支出（個股頁 S3a；需求錨序列的原料：雲端四大的「購置不動產、廠房與設備」）。
-- us-gaap:PaymentsToAcquirePropertyPlantAndEquipment／PaymentsToAcquireProductiveAssets；照營收的慣例拆季度／年度兩個名字。
-- 季報的現金流量是年初累計：單季由累計差分衍生（Q2＝6M−Q1、Q3＝9M−6M、Q4＝FY−9M，engine_c/history_backfill.py）。
-- 欄位內聯的 CHECK 在 Postgres 的預設名稱是 <table>_<column>_check；先刪再建，字彙與 SQLite 建表（METRICS）一致。
-- SQLite 對應的遷移是 engine_c/migrate_fundamental_metrics.py（SQLite 不能 ALTER CHECK，要重建表）。
ALTER TABLE fundamental_history DROP CONSTRAINT IF EXISTS fundamental_history_metric_check;
ALTER TABLE fundamental_history ADD CONSTRAINT fundamental_history_metric_check CHECK (metric IN (
    'revenue_quarter', 'revenue_annual', 'operating_income_quarter', 'operating_income_annual',
    'cash', 'total_debt', 'shares_outstanding_cover',
    'equity_issued_value_quarter', 'equity_issued_value_annual',
    'capex_quarter', 'capex_annual'));
