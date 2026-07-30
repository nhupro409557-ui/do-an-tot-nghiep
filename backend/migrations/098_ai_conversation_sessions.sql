CREATE TABLE IF NOT EXISTS ai_conversation_sessions (
    conversation_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    active_intent VARCHAR(80),
    active_entities JSONB NOT NULL DEFAULT '{}'::jsonb,
    pending_slots JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary TEXT NOT NULL DEFAULT '',
    unresolved_streak INTEGER NOT NULL DEFAULT 0 CHECK (unresolved_streak >= 0),
    last_failure_reason VARCHAR(120),
    handover_offered_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_conversation_sessions_user_updated
    ON ai_conversation_sessions (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_conversation_sessions_expires
    ON ai_conversation_sessions (expires_at);
