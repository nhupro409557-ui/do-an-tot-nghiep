CREATE TABLE IF NOT EXISTS ai_support_requests (
    id UUID PRIMARY KEY,
    request_code VARCHAR(30) NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id),
    conversation_id UUID NOT NULL,
    category VARCHAR(40) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
    summary TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    resolution_note TEXT,
    assigned_to UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ai_support_user_conversation UNIQUE (user_id, conversation_id),
    CONSTRAINT ck_ai_support_priority CHECK (priority IN ('NORMAL', 'HIGH', 'URGENT')),
    CONSTRAINT ck_ai_support_status CHECK (status IN ('OPEN', 'IN_PROGRESS', 'WAITING_CUSTOMER', 'RESOLVED', 'CLOSED'))
);

CREATE INDEX IF NOT EXISTS ix_ai_support_status_updated
    ON ai_support_requests (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS ix_ai_support_user_updated
    ON ai_support_requests (user_id, updated_at DESC);
