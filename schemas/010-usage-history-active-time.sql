-- Migration 010: Add active and foreground time tracking to usage_history
--
-- Splits "process running" into three nested measurements:
--   total_seconds      -- process was running (existing — open but possibly idle/backgrounded)
--   foreground_seconds -- app held OS focus, regardless of input
--   active_seconds     -- app was foreground AND user input within prior 300s
--
-- Lets reports distinguish "app open all day" from "actively used" so budget
-- defensibility no longer relies on inflated process-lifetime totals.
--
-- Columns are added with DEFAULT 0 so existing rows are valid and clients that
-- don't yet emit the new fields just contribute zeros to the new columns.

ALTER TABLE usage_history
    ADD COLUMN IF NOT EXISTS active_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS foreground_seconds DOUBLE PRECISION NOT NULL DEFAULT 0;

COMMENT ON COLUMN usage_history.total_seconds IS 'Process lifetime in seconds (open, possibly idle or backgrounded)';
COMMENT ON COLUMN usage_history.foreground_seconds IS 'Time the app held OS focus, regardless of user input';
COMMENT ON COLUMN usage_history.active_seconds IS 'Time the app was foreground AND user input occurred within the prior 300 seconds';
