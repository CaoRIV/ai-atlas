DROP TRIGGER IF EXISTS users_redact_generation_runs_before_delete ON users;
DROP FUNCTION IF EXISTS redact_generation_runs_before_user_delete();
DROP TABLE IF EXISTS generation_runs;
DROP TABLE IF EXISTS users;
