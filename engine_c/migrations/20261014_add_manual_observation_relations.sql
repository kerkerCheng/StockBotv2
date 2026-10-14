-- 人工觀測的取代／並存關係（2026-10-14 取代鏈 A；ROADMAP「人工觀測的取代鏈收多值」，使用者選 A）。
-- manual_observations.supersedes_id 是單值欄位而且帶 FK：一筆新紀錄只能關掉一條鏈，同一期間長出兩條互不相干的鏈之後
-- 就合併不了（2026-09-13 實測 14 組）。這張表 append-only：一筆可以關掉多筆（每個目標一列），也記刻意並存（parallel）。
-- 既有 manual_observations 一個欄位都不改；「哪幾筆生效」＝沒被 supersedes_id 也沒被 supersedes 關係指到的列。
-- 判斷欄位的關係要 pq2（approval_ref＝提案與編號；只有 engine_b.todo complete-observation 帶得出來）。
-- SQLite 對應的建表住 engine_c/manual_observations.py::ensure_manual_observation_schema（兩邊欄位與約束一致）。
CREATE TABLE IF NOT EXISTS manual_observation_relations (
    relation_id VARCHAR(64) PRIMARY KEY,
    observation_id VARCHAR(64) NOT NULL REFERENCES manual_observations(observation_id),
    target_id VARCHAR(64) NOT NULL REFERENCES manual_observations(observation_id),
    relation VARCHAR(16) NOT NULL CHECK (relation IN ('supersedes', 'parallel')),
    reason TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    approval_ref TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_digest VARCHAR(64) NOT NULL UNIQUE,
    CHECK (observation_id <> target_id)
);
CREATE INDEX IF NOT EXISTS idx_manual_observation_relations_target
    ON manual_observation_relations (target_id);
