-- Migration 003: magic_link_logs table
-- Tracks magic link sends for debugging and audit purposes.

-- ─── Table Definition ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS magic_link_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    triggered_by VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'sent'
);

-- ─── Row Level Security ──────────────────────────────────────────────────────

ALTER TABLE magic_link_logs ENABLE ROW LEVEL SECURITY;

-- Users can view their own magic link logs
CREATE POLICY "Users can view own logs" ON magic_link_logs
    FOR SELECT USING (auth.uid() = user_id);
