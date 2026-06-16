-- Extension storage for ReportMate
--
-- Core modules (002-modules-migration.sql) are device-collected and keep their
-- dedicated per-module tables (device.modules). EXTENSIONS are the server-joined
-- / add-on counterpart: data that lives in an external cloud system keyed to a
-- device (e.g. an Intune/Graph audit, a security-vendor risk feed) with no
-- device-local footprint a client could collect. They land here, keyed by
-- (device_id, extension_name). device_id holds the SERIAL NUMBER, consistent
-- with every other module table (devices.id is the serial).
--
-- A fresh table (not the legacy `module_data` from 002) so the naming matches
-- the /device/{serial}/extension/{name} ingress and there is no collision with
-- the legacy table's columns/indexes.

CREATE TABLE IF NOT EXISTS extension_data (
    id             SERIAL PRIMARY KEY,
    device_id      VARCHAR(255) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    extension_name VARCHAR(64)  NOT NULL,
    data           JSONB        NOT NULL,
    source         VARCHAR(64),               -- integration id (e.g. 'intune', a vendor name)
    collected_at   TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (device_id, extension_name)
);

CREATE INDEX IF NOT EXISTS idx_extension_data_device_id ON extension_data(device_id);
CREATE INDEX IF NOT EXISTS idx_extension_data_name ON extension_data(extension_name);
