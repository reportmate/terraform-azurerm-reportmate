-- Add network fields to devices table
-- This migration adds IPv4, IPv6, and MAC address fields to support better network tracking

-- Add new columns to devices table
ALTER TABLE devices ADD COLUMN IF NOT EXISTS ip_address_v4 VARCHAR(45);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS ip_address_v6 VARCHAR(45);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS mac_address_primary VARCHAR(17);

-- Add indexes for the new fields
CREATE INDEX IF NOT EXISTS idx_devices_ip_address_v4 ON devices(ip_address_v4);
CREATE INDEX IF NOT EXISTS idx_devices_mac_address_primary ON devices(mac_address_primary);

-- Update the existing ip_address field to use IPv4 as primary
UPDATE devices 
SET ip_address_v4 = ip_address
WHERE ip_address IS NOT NULL 
  AND ip_address LIKE '%\.%\.%\.%' -- Simple IPv4 pattern
  AND ip_address_v4 IS NULL;

-- Add comments for documentation
COMMENT ON COLUMN devices.ip_address_v4 IS 'Primary IPv4 address of the device';
COMMENT ON COLUMN devices.ip_address_v6 IS 'Primary IPv6 address of the device';
COMMENT ON COLUMN devices.mac_address_primary IS 'Primary MAC address of the device';

-- Update the existing mac_address field to use the new column
UPDATE devices 
SET mac_address_primary = mac_address
WHERE mac_address IS NOT NULL 
  AND mac_address_primary IS NULL;
