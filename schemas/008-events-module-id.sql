-- Migration 008: Add module_id column to events table for upsert support
-- Enables "latest only" events (e.g., os_update) where newer overwrites older per device

ALTER TABLE events ADD COLUMN IF NOT EXISTS module_id VARCHAR(50);

-- Partial unique index: only applies when module_id is set
-- Regular events (NULL module_id) keep full history
-- Module-scoped events (e.g., os_update) are one per device
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_device_module_upsert
    ON events(device_id, module_id) WHERE module_id IS NOT NULL;
