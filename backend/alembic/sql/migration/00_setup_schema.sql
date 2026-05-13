-- ============================================
-- QAstra Schema Setup
-- Run this FIRST before any migration scripts.
-- Creates the schema and sets the search path.
-- ============================================

CREATE SCHEMA IF NOT EXISTS qastraschema;
SET search_path TO qastraschema;

-- Create alembic_version tracking table
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
