-- Migration: 005_add_login_attempts
-- Feature: Auth Login Screen (Magic Link Flow)
-- Purpose: Rate limiting, enumeration detection, and login attempt observability

CREATE TABLE IF NOT EXISTS login_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    attempted_at TIMESTAMPTZ DEFAULT NOW(),
    result VARCHAR(20) NOT NULL CHECK (result IN ('success', 'rejected')),
    rejection_reason VARCHAR(50) CHECK (rejection_reason IN (
        'email_not_found', 'account_inactive', 'rate_limit_email',
        'rate_limit_ip', 'enumeration_detected', 'send_error'
    ))
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_email ON login_attempts (email, attempted_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts (ip_address, attempted_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_attempts_result ON login_attempts (result);

ALTER TABLE login_attempts ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'login_attempts' AND policyname = 'Service role only'
    ) THEN
        CREATE POLICY "Service role only" ON login_attempts FOR ALL USING (false);
    END IF;
END $$;
