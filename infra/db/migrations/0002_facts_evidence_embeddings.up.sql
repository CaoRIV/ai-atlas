CREATE TABLE tool_facts (
    id uuid PRIMARY KEY,
    tool_id uuid NOT NULL,
    key text NOT NULL,
    value jsonb NOT NULL,
    verification_status text NOT NULL,
    revision integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT tool_facts_tool_id_fkey
        FOREIGN KEY (tool_id) REFERENCES tools (id) ON DELETE CASCADE,
    CONSTRAINT tool_facts_tool_id_key_key UNIQUE (tool_id, key),
    CONSTRAINT tool_facts_tool_id_id_key UNIQUE (tool_id, id),
    CONSTRAINT tool_facts_verification_status_check
        CHECK (verification_status IN ('verified', 'unverified', 'unknown')),
    CONSTRAINT tool_facts_revision_check CHECK (revision > 0)
);

CREATE INDEX tool_facts_key_verification_status_tool_id_idx
    ON tool_facts (key, verification_status, tool_id);

CREATE TABLE evidence (
    id uuid PRIMARY KEY,
    fact_id uuid NOT NULL,
    fact_revision integer NOT NULL,
    source_url text NOT NULL,
    source_kind text NOT NULL,
    excerpt text,
    checked_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    checked_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT evidence_fact_id_fkey
        FOREIGN KEY (fact_id) REFERENCES tool_facts (id) ON DELETE CASCADE,
    CONSTRAINT evidence_fact_revision_check CHECK (fact_revision > 0),
    CONSTRAINT evidence_source_kind_check
        CHECK (source_kind IN ('official_docs', 'official_pricing', 'official_site')),
    CONSTRAINT evidence_freshness_window_check CHECK (expires_at > checked_at)
);

CREATE INDEX evidence_fact_id_fact_revision_expires_at_idx
    ON evidence (fact_id, fact_revision, expires_at);

CREATE TABLE tool_capabilities (
    tool_id uuid NOT NULL,
    capability_id uuid NOT NULL,
    fact_id uuid NOT NULL,
    CONSTRAINT tool_capabilities_pkey PRIMARY KEY (tool_id, capability_id),
    CONSTRAINT tool_capabilities_tool_id_fkey
        FOREIGN KEY (tool_id) REFERENCES tools (id) ON DELETE CASCADE,
    CONSTRAINT tool_capabilities_capability_id_fkey
        FOREIGN KEY (capability_id) REFERENCES capabilities (id) ON DELETE CASCADE,
    CONSTRAINT tool_capabilities_tool_id_fact_id_fkey
        FOREIGN KEY (tool_id, fact_id)
        REFERENCES tool_facts (tool_id, id)
        ON DELETE CASCADE
);

CREATE INDEX tool_capabilities_capability_id_idx ON tool_capabilities (capability_id);
CREATE INDEX tool_capabilities_tool_id_fact_id_idx ON tool_capabilities (tool_id, fact_id);

CREATE TABLE tool_embeddings (
    tool_id uuid NOT NULL,
    model_key text NOT NULL,
    content_hash text NOT NULL,
    source_revision integer NOT NULL,
    embedding vector(1536) NOT NULL,
    embedded_at timestamptz NOT NULL,
    CONSTRAINT tool_embeddings_pkey PRIMARY KEY (tool_id, model_key),
    CONSTRAINT tool_embeddings_tool_id_fkey
        FOREIGN KEY (tool_id) REFERENCES tools (id) ON DELETE CASCADE,
    CONSTRAINT tool_embeddings_source_revision_check CHECK (source_revision > 0)
);
