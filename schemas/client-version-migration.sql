-- Add client_version column to devices table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'client_version'
    ) THEN
        ALTER TABLE devices ADD COLUMN client_version VARCHAR(50);
        COMMENT ON COLUMN devices.client_version IS 'Version of the ReportMate client that last sent data for this device';
    END IF;
END $$;

SELECT 'client_version column migration completed' as result;
