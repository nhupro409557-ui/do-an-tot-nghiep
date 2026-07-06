CREATE TABLE IF NOT EXISTS catalog_embedding_documents (
    file TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    excerpt TEXT NOT NULL DEFAULT '',
    text_hash TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'gemini',
    model TEXT NOT NULL,
    output_dimensionality INTEGER NOT NULL,
    embedding JSONB NOT NULL,
    source_dir TEXT NOT NULL DEFAULT '',
    complete_snapshot BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT catalog_embedding_documents_embedding_array_check
        CHECK (jsonb_typeof(embedding) = 'array'),
    CONSTRAINT catalog_embedding_documents_dimensionality_check
        CHECK (output_dimensionality > 0)
);

CREATE INDEX IF NOT EXISTS idx_catalog_embedding_documents_model
    ON catalog_embedding_documents (model, output_dimensionality);

CREATE INDEX IF NOT EXISTS idx_catalog_embedding_documents_updated_at
    ON catalog_embedding_documents (updated_at);
