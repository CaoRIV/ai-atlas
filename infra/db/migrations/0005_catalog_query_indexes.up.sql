ALTER TABLE tools
    ADD COLUMN search_vector tsvector NOT NULL DEFAULT ''::tsvector;

CREATE INDEX tools_publication_status_slug_idx
    ON tools (publication_status, slug);
CREATE INDEX tools_search_vector_idx
    ON tools USING GIN (search_vector);
