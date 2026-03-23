-- Migration: Add integrity_check column to user_stories table
-- This column flags user stories whose test cases should be included in build integrity checks

ALTER TABLE user_stories 
ADD COLUMN IF NOT EXISTS integrity_check BOOLEAN DEFAULT FALSE NOT NULL;

-- Create index for faster lookup of integrity check user stories
CREATE INDEX IF NOT EXISTS idx_user_stories_integrity_check 
ON user_stories(project_id, integrity_check) 
WHERE integrity_check = TRUE;

COMMENT ON COLUMN user_stories.integrity_check IS 'When true, all test cases under this user story will be executed as part of build integrity checks';
