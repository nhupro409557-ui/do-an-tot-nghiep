CREATE TABLE IF NOT EXISTS ai_response_feedback (
    response_id UUID PRIMARY KEY REFERENCES ai_context_logs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    helpful BOOLEAN NOT NULL,
    reason VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_response_feedback_created_at
    ON ai_response_feedback(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_response_feedback_helpful
    ON ai_response_feedback(helpful, created_at DESC);
