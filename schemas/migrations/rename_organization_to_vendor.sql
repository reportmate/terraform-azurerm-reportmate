-- Migration to rename 'organization' field to 'vendor' in mdm_info table
-- This aligns the database schema with the application expectations

BEGIN;

-- Rename the organization column to vendor
ALTER TABLE mdm_info RENAME COLUMN organization TO vendor;

-- Update any existing Microsoft Intune entries to just Intune
UPDATE mdm_info SET vendor = 'Intune' WHERE vendor = 'Microsoft Intune';

-- Update mdm_vendor field to match vendor field for consistency
UPDATE mdm_info SET mdm_vendor = vendor WHERE mdm_vendor IS NULL OR mdm_vendor = '';

COMMIT;
