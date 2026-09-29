CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE providers (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    slug text NOT NULL,
    website_url text,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT providers_slug_key UNIQUE (slug)
);

CREATE TABLE models (
    id uuid PRIMARY KEY,
    provider_id uuid,
    name text NOT NULL,
    slug text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT models_provider_id_fkey
        FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE SET NULL,
    CONSTRAINT models_slug_key UNIQUE (slug)
);

CREATE INDEX models_provider_id_idx ON models (provider_id);

CREATE TABLE categories (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    slug text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT categories_slug_key UNIQUE (slug)
);

CREATE TABLE capabilities (
    id uuid PRIMARY KEY,
    key text NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT capabilities_key_key UNIQUE (key)
);

CREATE TABLE tools (
    id uuid PRIMARY KEY,
    slug text NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    official_url text NOT NULL,
    provider_id uuid,
    tags text[] NOT NULL DEFAULT ARRAY[]::text[],
    publication_status text NOT NULL DEFAULT 'draft',
    last_verified_at timestamptz,
    revision integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT tools_provider_id_fkey
        FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE SET NULL,
    CONSTRAINT tools_slug_key UNIQUE (slug),
    CONSTRAINT tools_publication_status_check
        CHECK (publication_status IN ('draft', 'published', 'archived')),
    CONSTRAINT tools_revision_check CHECK (revision > 0)
);

CREATE INDEX tools_provider_id_idx ON tools (provider_id);

CREATE TABLE tool_categories (
    tool_id uuid NOT NULL,
    category_id uuid NOT NULL,
    CONSTRAINT tool_categories_pkey PRIMARY KEY (tool_id, category_id),
    CONSTRAINT tool_categories_tool_id_fkey
        FOREIGN KEY (tool_id) REFERENCES tools (id) ON DELETE CASCADE,
    CONSTRAINT tool_categories_category_id_fkey
        FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
);

CREATE INDEX tool_categories_category_id_idx ON tool_categories (category_id);

CREATE TABLE tool_models (
    tool_id uuid NOT NULL,
    model_id uuid NOT NULL,
    CONSTRAINT tool_models_pkey PRIMARY KEY (tool_id, model_id),
    CONSTRAINT tool_models_tool_id_fkey
        FOREIGN KEY (tool_id) REFERENCES tools (id) ON DELETE CASCADE,
    CONSTRAINT tool_models_model_id_fkey
        FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE CASCADE
);

CREATE INDEX tool_models_model_id_idx ON tool_models (model_id);
