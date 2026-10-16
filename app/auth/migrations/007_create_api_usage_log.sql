-- Migration 007: Create api_usage_log table for audit logging
--
-- This table stores structured audit records for every authenticated API request.
-- Anonymous requests are logged to file only, not to this table.
-- Created: Layer 8 Sublayer 1 (spec) / Layer 10 (implementation)

CREATE TABLE IF NOT EXISTS api_usage_log (
    id SERIAL PRIMARY KEY,
    user_key TEXT NOT NULL,
    auth_method TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    http_method TEXT NOT NULL,
    query_params JSONB,
    path_params JSONB,
    request_body JSONB,
    response_status INTEGER NOT NULL,
    response_time_ms INTEGER,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_usage_log_user_key ON api_usage_log(user_key);
CREATE INDEX IF NOT EXISTS idx_api_usage_log_endpoint ON api_usage_log(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_usage_log_requested_at ON api_usage_log(requested_at);

COMMENT ON TABLE api_usage_log IS 'Audit log for authenticated API requests (Layer 10)';
