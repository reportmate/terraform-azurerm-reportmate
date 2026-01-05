-- Migration 006: Fix profiles table schema
-- Issue: profiles table in production has different schema (missing 'data' column)
-- Solution: Drop and recreate profiles table with correct schema

-- Step 1: Drop all related objects first
DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
DROP INDEX IF EXISTS idx_profiles_device_id;
DROP INDEX IF EXISTS idx_profiles_data_gin;

-- Step 2: Drop the incorrect profiles table (CASCADE to drop constraints too)
DROP TABLE IF EXISTS profiles CASCADE;

-- Step 3: Recreate profiles table with correct schema
CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                        -- Raw JSON data from profiles.json
    collected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT unique_profiles_per_device UNIQUE(device_id)
);

-- Step 4: Create indexes
CREATE INDEX idx_profiles_device_id ON profiles(device_id);
CREATE INDEX idx_profiles_data_gin ON profiles USING GIN(data);

-- Step 5: Create trigger for updated_at
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Note: Profiles data will be re-collected from devices on next client sync
