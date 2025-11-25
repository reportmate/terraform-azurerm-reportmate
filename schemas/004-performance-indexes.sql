-- Performance indexes for Events table
-- Addresses slow dashboard loading times

-- Index for sorting by created_at (if used as fallback)
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

-- Index for global event sorting (Dashboard feed)
-- Optimizes: SELECT ... FROM events ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);

-- Composite index for filtering events by device and sorting by time
-- Optimizes: SELECT ... FROM events WHERE device_id = ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS idx_events_device_timestamp ON events(device_id, timestamp DESC);
