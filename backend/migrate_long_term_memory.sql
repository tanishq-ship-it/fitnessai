-- Long-term continuity layer for cross-conversation recall

CREATE TABLE IF NOT EXISTS conversation_summaries (
    conversation_id UUID PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary TEXT NOT NULL DEFAULT '',
    key_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    next_steps TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_summaries_user_updated_at
    ON conversation_summaries(user_id, updated_at DESC);
