-- Application Usage Tracking Migration
-- Creates tables for storing application usage events and aggregated summaries
-- Supports per-user tracking and historical time-series data

-- Application usage events table (time-series data)
-- Stores individual process start/stop sessions for detailed analysis
CREATE TABLE IF NOT EXISTS application_usage_events (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    serial_number VARCHAR(255) NOT NULL,
    
    -- User context (resolved at collection time)
    username VARCHAR(255) NOT NULL,
    user_sid VARCHAR(255),
    
    -- Application identification
    application_name VARCHAR(500) NOT NULL,
    executable_name VARCHAR(255) NOT NULL,
    executable_path VARCHAR(1000),
    publisher VARCHAR(255),
    
    -- Session timing
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_seconds DOUBLE PRECISION DEFAULT 0,
    
    -- Session status: 'complete', 'interrupted' (shutdown/crash), 'active'
    session_status VARCHAR(20) DEFAULT 'complete',
    
    -- Process metadata
    process_id INTEGER,
    session_id INTEGER, -- Windows terminal services session
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint for session uniqueness
    CONSTRAINT unique_session UNIQUE (device_id, process_id, start_time)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_usage_events_device_time 
    ON application_usage_events(device_id, start_time DESC);

CREATE INDEX IF NOT EXISTS idx_usage_events_device_user 
    ON application_usage_events(device_id, username);

CREATE INDEX IF NOT EXISTS idx_usage_events_app_name 
    ON application_usage_events(application_name);

CREATE INDEX IF NOT EXISTS idx_usage_events_start_time 
    ON application_usage_events(start_time DESC);

CREATE INDEX IF NOT EXISTS idx_usage_events_serial 
    ON application_usage_events(serial_number);

-- GIN index for full-text search on application name
CREATE INDEX IF NOT EXISTS idx_usage_events_app_name_gin 
    ON application_usage_events USING gin(to_tsvector('english', application_name));

-- Application usage summary table (aggregated data)
-- Stores rolled-up statistics per device/user/application combination
-- Updated during collection and by nightly aggregation job
CREATE TABLE IF NOT EXISTS application_usage_summary (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    serial_number VARCHAR(255) NOT NULL,
    
    -- User context
    username VARCHAR(255) NOT NULL,
    
    -- Application identification
    application_name VARCHAR(500) NOT NULL,
    executable_name VARCHAR(255),
    executable_path VARCHAR(1000),
    publisher VARCHAR(255),
    
    -- Usage statistics
    launch_count BIGINT DEFAULT 0,
    total_seconds DOUBLE PRECISION DEFAULT 0,
    active_seconds DOUBLE PRECISION DEFAULT 0,
    average_session_seconds DOUBLE PRECISION DEFAULT 0,
    
    -- Temporal tracking
    first_seen TIMESTAMPTZ,
    last_used TIMESTAMPTZ,
    last_exit_time TIMESTAMPTZ,
    
    -- Window for this summary (for rolling aggregation)
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint for unique device/user/app combination
    CONSTRAINT unique_summary UNIQUE (device_id, username, application_name)
);

-- Indexes for summary queries
CREATE INDEX IF NOT EXISTS idx_usage_summary_device 
    ON application_usage_summary(device_id);

CREATE INDEX IF NOT EXISTS idx_usage_summary_device_user 
    ON application_usage_summary(device_id, username);

CREATE INDEX IF NOT EXISTS idx_usage_summary_app_name 
    ON application_usage_summary(application_name);

CREATE INDEX IF NOT EXISTS idx_usage_summary_last_used 
    ON application_usage_summary(last_used DESC);

CREATE INDEX IF NOT EXISTS idx_usage_summary_total_time 
    ON application_usage_summary(total_seconds DESC);

CREATE INDEX IF NOT EXISTS idx_usage_summary_serial 
    ON application_usage_summary(serial_number);

-- Fleet-wide application usage statistics view
-- Aggregates usage across all devices for each application
CREATE OR REPLACE VIEW v_fleet_application_usage AS
SELECT 
    application_name,
    publisher,
    COUNT(DISTINCT device_id) as device_count,
    COUNT(DISTINCT username) as user_count,
    SUM(launch_count) as total_launches,
    SUM(total_seconds) as total_seconds,
    SUM(total_seconds) / 3600.0 as total_hours,
    AVG(average_session_seconds) as avg_session_seconds,
    MIN(first_seen) as first_seen,
    MAX(last_used) as last_used
FROM application_usage_summary
GROUP BY application_name, publisher
ORDER BY total_seconds DESC;

-- Per-device application usage statistics view
CREATE OR REPLACE VIEW v_device_application_usage AS
SELECT 
    device_id,
    serial_number,
    application_name,
    publisher,
    COUNT(DISTINCT username) as user_count,
    SUM(launch_count) as total_launches,
    SUM(total_seconds) as total_seconds,
    SUM(total_seconds) / 3600.0 as total_hours,
    AVG(average_session_seconds) as avg_session_seconds,
    MIN(first_seen) as first_seen,
    MAX(last_used) as last_used,
    array_agg(DISTINCT username) as users
FROM application_usage_summary
GROUP BY device_id, serial_number, application_name, publisher
ORDER BY total_seconds DESC;

-- Unused applications view (apps not used in last 30 days)
CREATE OR REPLACE VIEW v_unused_applications AS
SELECT 
    aus.device_id,
    aus.serial_number,
    aus.application_name,
    aus.publisher,
    aus.last_used,
    EXTRACT(DAY FROM (NOW() - aus.last_used)) as days_since_used,
    aus.total_seconds / 3600.0 as total_hours_used,
    aus.launch_count
FROM application_usage_summary aus
WHERE aus.last_used < NOW() - INTERVAL '30 days'
   OR aus.last_used IS NULL
ORDER BY aus.last_used ASC NULLS FIRST;

-- Function to upsert usage summary from events
CREATE OR REPLACE FUNCTION upsert_usage_summary(
    p_device_id VARCHAR(255),
    p_serial_number VARCHAR(255),
    p_username VARCHAR(255),
    p_application_name VARCHAR(500),
    p_executable_name VARCHAR(255),
    p_executable_path VARCHAR(1000),
    p_publisher VARCHAR(255),
    p_launch_count BIGINT,
    p_total_seconds DOUBLE PRECISION,
    p_first_seen TIMESTAMPTZ,
    p_last_used TIMESTAMPTZ,
    p_last_exit_time TIMESTAMPTZ
) RETURNS VOID AS $$
BEGIN
    INSERT INTO application_usage_summary (
        device_id, serial_number, username, application_name,
        executable_name, executable_path, publisher,
        launch_count, total_seconds, average_session_seconds,
        first_seen, last_used, last_exit_time,
        window_start, window_end, updated_at
    ) VALUES (
        p_device_id, p_serial_number, p_username, p_application_name,
        p_executable_name, p_executable_path, p_publisher,
        p_launch_count, p_total_seconds, 
        CASE WHEN p_launch_count > 0 THEN p_total_seconds / p_launch_count ELSE 0 END,
        p_first_seen, p_last_used, p_last_exit_time,
        NOW() - INTERVAL '4 hours', NOW(), NOW()
    )
    ON CONFLICT (device_id, username, application_name) 
    DO UPDATE SET
        executable_name = COALESCE(EXCLUDED.executable_name, application_usage_summary.executable_name),
        executable_path = COALESCE(EXCLUDED.executable_path, application_usage_summary.executable_path),
        publisher = COALESCE(EXCLUDED.publisher, application_usage_summary.publisher),
        launch_count = application_usage_summary.launch_count + EXCLUDED.launch_count,
        total_seconds = application_usage_summary.total_seconds + EXCLUDED.total_seconds,
        average_session_seconds = CASE 
            WHEN (application_usage_summary.launch_count + EXCLUDED.launch_count) > 0 
            THEN (application_usage_summary.total_seconds + EXCLUDED.total_seconds) / 
                 (application_usage_summary.launch_count + EXCLUDED.launch_count)
            ELSE 0 
        END,
        first_seen = LEAST(application_usage_summary.first_seen, EXCLUDED.first_seen),
        last_used = GREATEST(application_usage_summary.last_used, EXCLUDED.last_used),
        last_exit_time = GREATEST(application_usage_summary.last_exit_time, EXCLUDED.last_exit_time),
        window_end = NOW(),
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old usage events (retention policy)
-- Keeps raw events for 90 days, then relies on summary table
CREATE OR REPLACE FUNCTION cleanup_old_usage_events(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM application_usage_events 
    WHERE start_time < NOW() - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Add comment to tables
COMMENT ON TABLE application_usage_events IS 'Time-series data for individual application usage sessions. Stores process start/stop events with user context.';
COMMENT ON TABLE application_usage_summary IS 'Aggregated application usage statistics per device/user/application. Updated during collection and by nightly aggregation.';
COMMENT ON VIEW v_fleet_application_usage IS 'Fleet-wide application usage aggregated across all devices.';
COMMENT ON VIEW v_device_application_usage IS 'Per-device application usage with user breakdown.';
COMMENT ON VIEW v_unused_applications IS 'Applications not used in the last 30 days for cleanup recommendations.';
