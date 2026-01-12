-- Quick migration to add platform column
-- Run this manually in Azure Portal Query Editor or pgAdmin

-- Step 1: Add platform column
ALTER TABLE devices ADD COLUMN IF NOT EXISTS platform VARCHAR(50);

-- Step 2: Create index
CREATE INDEX IF NOT EXISTS idx_devices_platform ON devices(platform);

-- Step 3: Update existing devices with inferred platform
UPDATE devices 
SET platform = CASE
    WHEN LOWER(os_name) LIKE '%windows%' OR LOWER(os) LIKE '%windows%' THEN 'Windows'
    WHEN LOWER(os_name) LIKE '%mac%' OR LOWER(os) LIKE '%mac%' OR LOWER(os_name) LIKE '%darwin%' THEN 'macOS'
    ELSE 'Unknown'
END
WHERE platform IS NULL;

-- Step 4: Verify
SELECT serial_number, platform, os_name FROM devices LIMIT 10;
