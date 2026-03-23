-- Migration: Add integrity_check column to test_cases table
-- This column flags test cases to be included in build integrity checks

ALTER TABLE test_cases 
ADD COLUMN IF NOT EXISTS integrity_check BOOLEAN DEFAULT FALSE;

-- Create index for faster lookup of integrity check test cases
CREATE INDEX IF NOT EXISTS idx_test_cases_integrity_check 
ON test_cases(project_id, integrity_check) 
WHERE integrity_check = TRUE;

COMMENT ON COLUMN test_cases.integrity_check IS 'When true, this test case will be executed as part of build integrity checks';
