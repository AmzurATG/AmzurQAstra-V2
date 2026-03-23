-- Migration: Add sprint columns to user_stories table
-- Date: 2026-03-20
-- Description: Add sprint_id and sprint_name columns to support Jira sprint filtering

-- Add sprint columns
ALTER TABLE user_stories 
ADD COLUMN IF NOT EXISTS sprint_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS sprint_name VARCHAR(255);

-- Add index for sprint queries
CREATE INDEX IF NOT EXISTS idx_user_stories_sprint ON user_stories(sprint_id);

-- Verify the changes
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'user_stories' 
AND column_name IN ('sprint_id', 'sprint_name');
