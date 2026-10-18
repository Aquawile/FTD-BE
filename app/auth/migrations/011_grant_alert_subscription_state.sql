-- 011: let the application role use alert_subscription_state.
-- Migrations run as postgres, so 010 created the table without privileges for ftd_app.
-- Insert/update only: evaluator state is never deleted.
GRANT SELECT, INSERT, UPDATE ON alert_subscription_state TO ftd_app;
