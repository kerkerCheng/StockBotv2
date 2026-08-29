-- 相對水位的主要欄位：最新收盤在近 252 個交易日區間中的位置（0.0 低點 / 1.0 高點）。
-- 純位置指標，取代隨技術訊號移除的 RSI／MACD。既有 legacy 動能欄位不刪，只停止寫入。
ALTER TABLE technical_observations
    ADD COLUMN IF NOT EXISTS range_percentile_252 NUMERIC(18,10);
