-- 014: workspace settings that actually save. Archive is a flag, never a delete.
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS alert_on_filings BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_workspaces_user_active ON workspaces (user_id) WHERE archived_at IS NULL;
