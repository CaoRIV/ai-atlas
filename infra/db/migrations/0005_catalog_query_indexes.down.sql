DROP INDEX IF EXISTS tools_search_vector_idx;
DROP INDEX IF EXISTS tools_publication_status_slug_idx;
ALTER TABLE tools DROP COLUMN IF EXISTS search_vector;
