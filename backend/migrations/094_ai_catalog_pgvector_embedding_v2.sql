CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE catalog_embedding_documents
    ADD COLUMN IF NOT EXISTS embedding_v2 vector(768),
    ADD COLUMN IF NOT EXISTS source_id TEXT,
    ADD COLUMN IF NOT EXISTS source_type TEXT NOT NULL DEFAULT 'catalog_markdown',
    ADD COLUMN IF NOT EXISTS content_hash_v2 TEXT,
    ADD COLUMN IF NOT EXISTS indexed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

UPDATE catalog_embedding_documents
SET
    source_id = COALESCE(NULLIF(source_id, ''), regexp_replace(file, '\.md$', '')),
    source_type = COALESCE(NULLIF(source_type, ''), 'catalog_markdown'),
    is_active = TRUE
WHERE source_id IS NULL
   OR source_id = ''
   OR source_type = ''
   OR is_active IS DISTINCT FROM TRUE;

CREATE INDEX IF NOT EXISTS idx_catalog_embedding_documents_active_model
    ON catalog_embedding_documents (model, output_dimensionality, is_active);

CREATE INDEX IF NOT EXISTS idx_catalog_embedding_documents_source
    ON catalog_embedding_documents (source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_catalog_embedding_documents_indexed_at
    ON catalog_embedding_documents (indexed_at DESC)
    WHERE embedding_v2 IS NOT NULL AND is_active = TRUE;
