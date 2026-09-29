CREATE TABLE users (
    id uuid PRIMARY KEY,
    auth_issuer text NOT NULL,
    auth_subject text NOT NULL,
    display_name text,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_auth_issuer_auth_subject_key UNIQUE (auth_issuer, auth_subject)
);

CREATE TABLE generation_runs (
    id uuid PRIMARY KEY,
    owner_id uuid,
    result jsonb,
    status text NOT NULL,
    pipeline_version text NOT NULL,
    catalog_revision text NOT NULL,
    usage jsonb NOT NULL DEFAULT '{}'::jsonb,
    reserved_cost_usd numeric(12, 6) NOT NULL,
    estimated_cost_usd numeric(12, 6),
    expires_at timestamptz NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours'),
    request_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT generation_runs_owner_id_fkey
        FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT generation_runs_status_check
        CHECK (
            status IN (
                'running',
                'complete',
                'partial',
                'no_match',
                'needs_clarification',
                'failed'
            )
        ),
    CONSTRAINT generation_runs_result_object_check
        CHECK (result IS NULL OR jsonb_typeof(result) = 'object'),
    CONSTRAINT generation_runs_usage_object_check CHECK (jsonb_typeof(usage) = 'object'),
    CONSTRAINT generation_runs_reserved_cost_usd_check CHECK (reserved_cost_usd >= 0),
    CONSTRAINT generation_runs_estimated_cost_usd_check
        CHECK (estimated_cost_usd IS NULL OR estimated_cost_usd >= 0),
    CONSTRAINT generation_runs_result_ttl_check
        CHECK (
            expires_at > created_at
            AND expires_at <= created_at + INTERVAL '24 hours'
        )
);

CREATE INDEX generation_runs_owner_id_created_at_idx
    ON generation_runs (owner_id, created_at);
CREATE INDEX generation_runs_created_at_status_idx
    ON generation_runs (created_at, status);

CREATE FUNCTION redact_generation_runs_before_user_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE generation_runs
    SET owner_id = NULL,
        result = NULL,
        updated_at = CURRENT_TIMESTAMP
    WHERE owner_id = OLD.id;

    RETURN OLD;
END;
$$;

CREATE TRIGGER users_redact_generation_runs_before_delete
BEFORE DELETE ON users
FOR EACH ROW
EXECUTE FUNCTION redact_generation_runs_before_user_delete();
