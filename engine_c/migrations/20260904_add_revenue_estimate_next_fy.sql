-- 下一會計年度的分析師營收估計（絕對值＋共識成長率＋分析師人數）。
--
-- ⚠ 這是 Phase 4c 的第一項，而它之所以拖到現在，是因為 ROADMAP 寫著
-- 「yfinance 只有 revenueGrowth（成長率），沒有絕對營收估計」——那句話是假的。
-- 2026-09-04 實測 `yf.Ticker().revenue_estimate` 直接給 `+1y` 的 avg／low／high／
-- growth／numberOfAnalysts，**73/73 檔全覆蓋**（含 KS／SZ／TW 標的）。
-- 這是「引用自家文件的現況陳述前先跑查證命令」第三次抓到同型錯誤。
--
-- ⚠ **單位是該標的的報表幣別，不是 USD。** 000660.KS 的 +1y 是 534 兆（KRW）。
-- 與 Phase 4a 的 forward EPS 同一個陷阱：只保證**同一標的的時間序列比值**有意義，
-- **不得跨標的比絕對值**。成長率（無單位）才是可跨標的比較的那一欄。
ALTER TABLE financial_snapshots
    ADD COLUMN IF NOT EXISTS revenue_estimate_next_fy NUMERIC(24,2);
ALTER TABLE financial_snapshots
    ADD COLUMN IF NOT EXISTS revenue_estimate_next_fy_growth NUMERIC(10,6);
ALTER TABLE financial_snapshots
    ADD COLUMN IF NOT EXISTS revenue_estimate_next_fy_analysts INTEGER;
