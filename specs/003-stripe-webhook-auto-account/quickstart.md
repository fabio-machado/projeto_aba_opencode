# Quickstart: Stripe Webhook Auto Account

**Feature**: Stripe Webhook Auto Account  
**Date**: 2026-04-26

## Prerequisites

- Supabase project with Auth enabled
- Stripe account with webhook endpoint configured
- Django 5.x project with HTMX and Alpine.js
- `supabase-py` installed
- `stripe` Python SDK installed

## Environment Variables

```bash
# Stripe
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_SECRET_KEY=sk_...

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...  # service_role key for webhook handler
SUPABASE_ANON_KEY=eyJ...     # public anon key for frontend

# App
APP_URL=https://your-app.com
```

## Stripe Configuration

1. **Create Webhook Endpoint** in Stripe Dashboard:
   - URL: `https://your-app.com/webhooks/stripe`
   - Events: `payment_intent.succeeded`
   - Copy the **Signing secret** to `STRIPE_WEBHOOK_SECRET`

2. **Test Webhook Locally** (optional):
   ```bash
   stripe listen --forward-to localhost:8000/webhooks/stripe
   ```

## Supabase Configuration

1. **Enable Email Auth** in Supabase Dashboard → Authentication → Providers → Email
2. **Configure Magic Link**:
   - Enable "Confirm email" (optional for magic links)
   - Set "Mailer OTP Expiration" to 3600 (1 hour)
3. **Session Settings**:
   - Access Token (JWT) Expiry: 7776000 seconds (90 days)
   - Refresh Token: Enabled (rotating)
4. **Email Templates**:
   - Customize Magic Link email template in Supabase Dashboard

## Database Setup

Run the following migrations (or use Supabase Dashboard):

```sql
-- Profiles table
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name VARCHAR(255) NOT NULL,
  cpf VARCHAR(14) UNIQUE,
  has_generator_access BOOLEAN DEFAULT FALSE,
  has_library_access BOOLEAN DEFAULT FALSE,
  subscription_status VARCHAR(20) DEFAULT 'active',
  stripe_customer_id VARCHAR(255) UNIQUE,
  trial_ends_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Children table
CREATE TABLE children (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  birth_date DATE,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Webhook idempotency tracker
CREATE TABLE processed_webhook_events (
  stripe_event_id VARCHAR(255) PRIMARY KEY,
  event_type VARCHAR(100) NOT NULL,
  processed_at TIMESTAMPTZ DEFAULT NOW(),
  status VARCHAR(20) DEFAULT 'success',
  error_message TEXT
);

-- Magic link audit log (optional)
CREATE TABLE magic_link_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  email VARCHAR(255) NOT NULL,
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  triggered_by VARCHAR(50) NOT NULL,
  status VARCHAR(20) DEFAULT 'sent'
);

-- Indexes
CREATE INDEX idx_profiles_stripe_customer_id ON profiles(stripe_customer_id);
CREATE INDEX idx_profiles_subscription_status ON profiles(subscription_status);
CREATE INDEX idx_children_parent_id ON children(parent_id);
CREATE INDEX idx_processed_events_type ON processed_webhook_events(event_type);

-- RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE children ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_webhook_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE magic_link_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Parents can view own children" ON children
  FOR SELECT USING (auth.uid() = parent_id);

CREATE POLICY "Parents can manage own children" ON children
  FOR ALL USING (auth.uid() = parent_id);

CREATE POLICY "Service role only" ON processed_webhook_events
  FOR ALL USING (false);

CREATE POLICY "Users can view own logs" ON magic_link_logs
  FOR SELECT USING (auth.uid() = user_id);

-- Updated at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_children_updated_at BEFORE UPDATE ON children
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Testing

### 1. Test Webhook Signature Validation

```bash
curl -X POST http://localhost:8000/webhooks/stripe \
  -H "Content-Type: application/json" \
  -d '{"type":"payment_intent.succeeded"}'
# Expected: 400 Invalid signature
```

### 2. Test with Stripe CLI

```bash
# Forward webhooks locally
stripe listen --forward-to localhost:8000/webhooks/stripe

# Trigger test event
stripe trigger payment_intent.succeeded
```

### 3. Test Magic Link Flow

1. Complete a test payment (or trigger webhook)
2. Check email inbox for magic link
3. Click link and verify redirect to dashboard
4. Verify 90-day session cookie is set

## Deployment Checklist

- [ ] Stripe webhook endpoint configured in production
- [ ] Supabase Auth configured with correct email templates
- [ ] Environment variables set in production
- [ ] RLS policies enabled and tested
- [ ] Database migrations applied
- [ ] SSL/HTTPS enabled for webhook endpoint
- [ ] Error monitoring configured (webhook failures)
- [ ] Magic link email deliverability tested

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Webhook signature invalid | Verify `STRIPE_WEBHOOK_SECRET` matches Stripe Dashboard |
| Duplicate users created | Check `processed_webhook_events` table has proper unique constraint |
| Magic link not received | Check Supabase Auth logs and email provider settings |
| Session expires too quickly | Verify JWT expiry is set to 7776000s (90 days) in Supabase |
| RLS errors | Ensure webhook handler uses `service_role` key |
