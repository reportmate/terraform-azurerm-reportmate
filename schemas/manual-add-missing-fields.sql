-- Add missing graphics and hostname fields to devices table
-- These fields are expected by the Azure Functions but missing from current schema

-- Add graphics field if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'devices' AND column_name = 'graphics') THEN
        ALTER TABLE devices ADD COLUMN graphics TEXT;
    END IF;
END $$;

-- Add hostname field if it doesn't exist  
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'devices' AND column_name = 'hostname') THEN
        ALTER TABLE devices ADD COLUMN hostname TEXT;
    END IF;
END $$;

-- Verify the fields were added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'devices' 
AND column_name IN ('graphics', 'hostname')
ORDER BY column_name;
