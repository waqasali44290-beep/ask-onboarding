-- Runs once, the first time the Postgres container starts with an empty volume.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id            SERIAL PRIMARY KEY,
    filename      TEXT NOT NULL UNIQUE,          -- re-upload of same name replaces chunks
    mime_type     TEXT NOT NULL,
    content_hash  TEXT NOT NULL,                 -- skip re-embedding if unchanged
    status        TEXT NOT NULL DEFAULT 'processing'
                  CHECK (status IN ('processing', 'ready', 'failed')),
    error         TEXT,
    full_text     TEXT,                          -- used by the citation viewer
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chunks (
    id            SERIAL PRIMARY KEY,
    document_id   INT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INT NOT NULL,
    content       TEXT NOT NULL,
    start_char    INT NOT NULL,                  -- offsets into documents.full_text,
    end_char      INT NOT NULL,                  -- so citations can highlight the exact passage
    page          INT,                           -- PDF page number, NULL for md/txt
    embedding     vector(384) NOT NULL
);
CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_document_idx ON chunks (document_id);

CREATE TABLE conversations (
    id            SERIAL PRIMARY KEY,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    citations       JSONB NOT NULL DEFAULT '[]', -- [{chunk_id, document_id, filename, start_char, end_char}]
    no_answer       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tickets (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    question        TEXT NOT NULL,
    user_name       TEXT NOT NULL,
    conversation_id INT REFERENCES conversations(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'open',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
