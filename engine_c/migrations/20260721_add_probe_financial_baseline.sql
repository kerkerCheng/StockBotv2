ALTER TABLE financial_snapshots
    ADD COLUMN IF NOT EXISTS cash_and_equivalents NUMERIC(20,2),
    ADD COLUMN IF NOT EXISTS total_debt NUMERIC(20,2),
    ADD COLUMN IF NOT EXISTS free_cash_flow_ttm NUMERIC(20,2);
