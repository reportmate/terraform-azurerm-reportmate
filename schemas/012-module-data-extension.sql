-- Generic extension-module storage for ReportMate
--
-- Core modules (002-modules-migration.sql) keep their dedicated per-module
-- tables. Extension modules -- server-joined integrations (e.g. a security
-- vendor's risk feed) or third-party add-ons that have no dedicated table --
-- land here, keyed by (device_id, module_id). device_id holds the SERIAL
-- NUMBER, consistent with every other module table (devices.id is the serial).
--
-- The read path merges these rows into the device's `modules` object alongside
-- the dedicated-table modules, so the frontend renders client-collected and
-- server-attached modules identically.

CREATE TABLE IF NOT EXISTS module_data (
    id           SERIAL PRIMARY KEY,
    device_id    VARCHAR(255) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    module_id    VARCHAR(64)  NOT NULL,
    data         JSONB        NOT NULL,
    source       VARCHAR(64),               -- 'client' or an integration id (e.g. a vendor name)
    collected_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (device_id, module_id)
);

CREATE INDEX IF NOT EXISTS idx_module_data_device_id ON module_data(device_id);
CREATE INDEX IF NOT EXISTS idx_module_data_module_id ON module_data(module_id);
