-- Migration 007: Composite indexes for event type filtering
-- Enables fast per-type queries (e.g. "last 50 errors") without full table scans
-- Existing idx_events_type (single column) is insufficient for sorted paginated queries

-- Fleet-level: filter by type + sort by timestamp
CREATE INDEX IF NOT EXISTS idx_events_type_timestamp 
    ON events(event_type, timestamp DESC);

-- Device-level: filter by device + type + sort by timestamp
CREATE INDEX IF NOT EXISTS idx_events_device_type_timestamp 
    ON events(device_id, event_type, timestamp DESC);
