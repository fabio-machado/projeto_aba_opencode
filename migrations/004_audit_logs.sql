-- Migration 004: audit_logs table
-- Audit trail for all write operations on user data (Constitution IV: Auditabilidade).

-- ─── Table Definition ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────

CREATE INDEX idx_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs (action);

-- ─── Row Level Security ──────────────────────────────────────────────────────

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Service role can insert audit logs (use service key for writes)
CREATE POLICY "Service role can insert" ON audit_logs
    FOR INSERT WITH CHECK (false);

-- Users can view their own audit logs
CREATE POLICY "Users can view own audits" ON audit_logs
    FOR SELECT USING (auth.uid() = user_id);
