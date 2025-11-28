-- Archive and Delete Feature Migration
-- Adds archived flag to devices table for soft deletion
-- Archived devices are hidden from reports/views by default but still exist in database

-- Add archived column to devices table
ALTER TABLE devices 
ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;

-- Add archived_at timestamp to track when device was archived
ALTER TABLE devices
ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

-- Create index for filtering archived devices (improves query performance)
CREATE INDEX IF NOT EXISTS idx_devices_archived ON devices(archived);

-- Create index for archived + status queries (common filter combination)
CREATE INDEX IF NOT EXISTS idx_devices_archived_status ON devices(archived, status);

-- Add comment to document the column purpose
COMMENT ON COLUMN devices.archived IS 'Soft deletion flag - when TRUE, device is hidden from default views but data remains in database';
COMMENT ON COLUMN devices.archived_at IS 'Timestamp when device was archived';

-- Update existing devices to ensure archived is FALSE (for any NULL values)
UPDATE devices SET archived = FALSE WHERE archived IS NULL;

-- Make archived NOT NULL after ensuring all values are set
ALTER TABLE devices ALTER COLUMN archived SET NOT NULL;
