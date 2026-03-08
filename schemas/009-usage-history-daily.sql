-- Migration 009: Daily application usage history table
-- Stores per-device, per-app, per-day cumulative usage summaries
-- Retention: 18 months (cleanup via API scheduled task)
-- UPSERT semantics: last collection of the day wins

CREATE TABLE IF NOT EXISTS usage_history (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    date DATE NOT NULL,
    app_name TEXT NOT NULL,
    publisher TEXT NOT NULL DEFAULT '',
    launches INTEGER NOT NULL DEFAULT 0,
    total_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
    users JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(device_id, date, app_name)
);

-- Index for per-device time-series queries
CREATE INDEX IF NOT EXISTS idx_usage_history_device_date
    ON usage_history(device_id, date DESC);

-- Index for fleet-wide per-app queries
CREATE INDEX IF NOT EXISTS idx_usage_history_app_date
    ON usage_history(app_name, date DESC);

-- Index for retention cleanup
CREATE INDEX IF NOT EXISTS idx_usage_history_date
    ON usage_history(date);

-- Comment on table
COMMENT ON TABLE usage_history IS 'Daily per-application usage summaries. Cumulative: last collection of the day wins via ON CONFLICT UPDATE.';
