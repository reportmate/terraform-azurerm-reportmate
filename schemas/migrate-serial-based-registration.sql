-- Migration script to implement serial number-based device registration
-- This prevents duplicate device registrations and ensures serial number uniqueness

BEGIN;

-- Step 1: Add unique constraint on serial_number
-- This will prevent duplicate devices from being registered with the same serial number
DO $$
BEGIN
    -- Check if the constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'devices_serial_number_key'
    ) THEN
        -- Add unique constraint on serial_number
        ALTER TABLE devices ADD CONSTRAINT devices_serial_number_key UNIQUE (serial_number);
    END IF;
END $$;

-- Step 2: Update existing devices to use serial_number as id where possible
-- This ensures that existing devices follow the new pattern
UPDATE devices 
SET id = serial_number 
WHERE serial_number IS NOT NULL 
  AND serial_number != '' 
  AND serial_number != id
  AND NOT EXISTS (
    SELECT 1 FROM devices d2 
    WHERE d2.id = devices.serial_number 
      AND d2.id != devices.id
  );

-- Step 3: Clean up any devices without serial numbers
-- Set a fallback serial number for devices that don't have one
UPDATE devices 
SET serial_number = COALESCE(serial_number, 'UNKNOWN-' || id)
WHERE serial_number IS NULL OR serial_number = '';

-- Step 4: Update events table to reference the correct device IDs
-- This ensures event data is properly linked after device ID changes
UPDATE events 
SET device_id = (
    SELECT serial_number 
    FROM devices 
    WHERE devices.id = events.device_id 
      AND devices.serial_number != devices.id
    LIMIT 1
)
WHERE EXISTS (
    SELECT 1 FROM devices 
    WHERE devices.id = events.device_id 
      AND devices.serial_number != devices.id
);

-- Step 5: Update other related tables to maintain referential integrity
-- Update cimian_runs table
UPDATE cimian_runs 
SET device = (
    SELECT serial_number 
    FROM devices 
    WHERE devices.id = cimian_runs.device 
      AND devices.serial_number != devices.id
    LIMIT 1
)
WHERE EXISTS (
    SELECT 1 FROM devices 
    WHERE devices.id = cimian_runs.device 
      AND devices.serial_number != devices.id
);

-- Step 6: Update device_hardware table if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'device_hardware'
    ) THEN
        UPDATE device_hardware 
        SET device_id = (
            SELECT serial_number 
            FROM devices 
            WHERE devices.id = device_hardware.device_id 
              AND devices.serial_number != devices.id
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1 FROM devices 
            WHERE devices.id = device_hardware.device_id 
              AND devices.serial_number != devices.id
        );
    END IF;
END $$;

-- Step 7: Update mdm_info table if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'mdm_info'
    ) THEN
        UPDATE mdm_info 
        SET device_id = (
            SELECT serial_number 
            FROM devices 
            WHERE devices.id = mdm_info.device_id 
              AND devices.serial_number != devices.id
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1 FROM devices 
            WHERE devices.id = mdm_info.device_id 
              AND devices.serial_number != devices.id
        );
    END IF;
END $$;

-- Step 8: Update security_features table if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'security_features'
    ) THEN
        UPDATE security_features 
        SET device_id = (
            SELECT serial_number 
            FROM devices 
            WHERE devices.id = security_features.device_id 
              AND devices.serial_number != devices.id
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1 FROM devices 
            WHERE devices.id = security_features.device_id 
              AND devices.serial_number != devices.id
        );
    END IF;
END $$;

COMMIT;

-- Verify the migration
SELECT 
    'Migration Complete' as status,
    COUNT(*) as total_devices,
    COUNT(DISTINCT serial_number) as unique_serials,
    SUM(CASE WHEN id = serial_number THEN 1 ELSE 0 END) as devices_with_serial_id
FROM devices;
