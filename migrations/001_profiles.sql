-- Migration 001: profiles table
-- Extends Supabase Auth user with application-specific profile data and access control flags.

-- ─── Table Definition ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    cpf VARCHAR(14) UNIQUE NULLABLE,
    has_generator_access BOOLEAN DEFAULT FALSE,
    has_library_access BOOLEAN DEFAULT FALSE,
    subscription_status VARCHAR(20) DEFAULT 'active',
    stripe_customer_id VARCHAR(255) UNIQUE NULLABLE,
    trial_ends_at TIMESTAMPTZ NULLABLE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────

CREATE INDEX idx_profiles_stripe_customer_id ON profiles (stripe_customer_id);
CREATE INDEX idx_profiles_subscription_status ON profiles (subscription_status);

-- ─── Row Level Security ──────────────────────────────────────────────────────

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Users can view their own profile
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

-- ─── Trigger: Auto-update updated_at ─────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
