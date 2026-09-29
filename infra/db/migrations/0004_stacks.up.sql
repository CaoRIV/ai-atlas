CREATE TABLE stacks (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL,
    title varchar(120) NOT NULL,
    purpose varchar(2000) NOT NULL,
    source_generation_id uuid,
    generation_snapshot jsonb,
    validation_state text NOT NULL,
    version integer NOT NULL DEFAULT 1,
    idempotency_key uuid,
    creation_request_hash text,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT stacks_owner_id_fkey
        FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT stacks_source_generation_id_fkey
        FOREIGN KEY (source_generation_id) REFERENCES generation_runs (id) ON DELETE SET NULL,
    CONSTRAINT stacks_title_check CHECK (char_length(btrim(title)) BETWEEN 1 AND 120),
    CONSTRAINT stacks_purpose_check CHECK (char_length(btrim(purpose)) BETWEEN 1 AND 2000),
    CONSTRAINT stacks_generation_snapshot_object_check
        CHECK (generation_snapshot IS NULL OR jsonb_typeof(generation_snapshot) = 'object'),
    CONSTRAINT stacks_validation_state_check
        CHECK (validation_state IN ('generated', 'manual', 'modified')),
    CONSTRAINT stacks_version_check CHECK (version >= 1),
    CONSTRAINT stacks_idempotency_pair_check
        CHECK ((idempotency_key IS NULL) = (creation_request_hash IS NULL)),
    CONSTRAINT stacks_creation_request_hash_check
        CHECK (
            creation_request_hash IS NULL
            OR char_length(btrim(creation_request_hash)) > 0
        )
);

CREATE INDEX stacks_owner_id_updated_at_id_idx
    ON stacks (owner_id, updated_at, id);
CREATE INDEX stacks_source_generation_id_idx
    ON stacks (source_generation_id)
    WHERE source_generation_id IS NOT NULL;
CREATE UNIQUE INDEX stacks_owner_id_idempotency_key_key
    ON stacks (owner_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE stack_items (
    id uuid PRIMARY KEY,
    stack_id uuid NOT NULL,
    tool_id uuid NOT NULL,
    role varchar(80) NOT NULL,
    position integer NOT NULL,
    rationale text,
    evidence_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
    tool_snapshot jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT stack_items_stack_id_fkey
        FOREIGN KEY (stack_id) REFERENCES stacks (id) ON DELETE CASCADE,
    CONSTRAINT stack_items_tool_id_fkey
        FOREIGN KEY (tool_id) REFERENCES tools (id),
    CONSTRAINT stack_items_stack_id_id_key UNIQUE (stack_id, id),
    CONSTRAINT stack_items_stack_id_position_key UNIQUE (stack_id, position),
    CONSTRAINT stack_items_role_check CHECK (char_length(btrim(role)) BETWEEN 1 AND 80),
    CONSTRAINT stack_items_position_check CHECK (position BETWEEN 1 AND 20),
    CONSTRAINT stack_items_rationale_check
        CHECK (rationale IS NULL OR char_length(rationale) <= 1000),
    CONSTRAINT stack_items_evidence_ids_check
        CHECK (
            COALESCE(array_ndims(evidence_ids), 1) = 1
            AND array_position(evidence_ids, NULL) IS NULL
        ),
    CONSTRAINT stack_items_tool_snapshot_object_check
        CHECK (jsonb_typeof(tool_snapshot) = 'object')
);

CREATE INDEX stack_items_tool_id_idx ON stack_items (tool_id);

CREATE TABLE stack_edges (
    id uuid PRIMARY KEY,
    stack_id uuid NOT NULL,
    from_item_id uuid NOT NULL,
    to_item_id uuid NOT NULL,
    description text NOT NULL,
    compatibility_status text NOT NULL,
    evidence_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT stack_edges_stack_id_fkey
        FOREIGN KEY (stack_id) REFERENCES stacks (id) ON DELETE CASCADE,
    CONSTRAINT stack_edges_from_item_fkey
        FOREIGN KEY (stack_id, from_item_id)
        REFERENCES stack_items (stack_id, id) ON DELETE CASCADE,
    CONSTRAINT stack_edges_to_item_fkey
        FOREIGN KEY (stack_id, to_item_id)
        REFERENCES stack_items (stack_id, id) ON DELETE CASCADE,
    CONSTRAINT stack_edges_stack_id_from_item_id_to_item_id_key
        UNIQUE (stack_id, from_item_id, to_item_id),
    CONSTRAINT stack_edges_no_self_loop_check CHECK (from_item_id <> to_item_id),
    CONSTRAINT stack_edges_description_check CHECK (char_length(description) <= 1000),
    CONSTRAINT stack_edges_compatibility_status_check
        CHECK (compatibility_status IN ('verified', 'unverified')),
    CONSTRAINT stack_edges_evidence_ids_check
        CHECK (
            COALESCE(array_ndims(evidence_ids), 1) = 1
            AND array_position(evidence_ids, NULL) IS NULL
        )
);

CREATE INDEX stack_edges_stack_id_to_item_id_idx
    ON stack_edges (stack_id, to_item_id);
