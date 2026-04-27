-- Migration 002: processed_webhook_events table
-- Idempotency tracker for Stripe webhook events.

-- ─── Table Definition ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS processed_webhook_events (
    stripe_event_id VARCHAR(255) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT NULLABLE
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────

CREATE INDEX idx_processed_events_type ON processed_webhook_events (event_type);

-- ─── Row Level Security ──────────────────────────────────────────────────────

ALTER TABLE processed_webhook_events ENABLE ROW LEVEL SECURITY;

-- Only service role can access webhook processing logs (deny all direct access)
CREATE POLICY "Service role only" ON processed_webhook_events
    FOR ALL USING (false);
