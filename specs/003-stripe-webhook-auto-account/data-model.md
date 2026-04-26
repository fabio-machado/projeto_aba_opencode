# Data Model: Stripe Webhook Auto Account

**Feature**: Stripe Webhook Auto Account  
**Date**: 2026-04-26

## Overview

This data model supports automatic account creation after Stripe payment success via webhook. It integrates with Supabase Auth for authentication and magic link access control.

---

## Entities

### 1. `profiles`

Extends the Supabase Auth user with application-specific profile data and access control flags.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, FK → `auth.users.id` | Links to Supabase Auth user |
| `full_name` | VARCHAR(255) | NOT NULL | User's complete name from Stripe payment |
| `cpf` | VARCHAR(14) | UNIQUE, NULLABLE | Brazilian tax ID for invoicing/compliance |
| `has_generator_access` | BOOLEAN | DEFAULT FALSE | Low-ticket product access flag |
| `has_library_access` | BOOLEAN | DEFAULT FALSE | Upsell/order bump product access flag |
| `subscription_status` | VARCHAR(20) | DEFAULT 'active' | Enum: `active`, `trialing`, `past_due`, `canceled` |
| `stripe_customer_id` | VARCHAR(255) | UNIQUE, NULLABLE | Stripe Customer ID for billing reference |
| `trial_ends_at` | TIMESTAMPTZ | NULLABLE | End date of trial period |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Indexes**:
- `idx_profiles_stripe_customer_id` on `stripe_customer_id` (for Stripe webhook lookups)
- `idx_profiles_subscription_status` on `subscription_status` (for access control queries)

**RLS Policy**:
```sql
-- Users can only read/update their own profile
CREATE POLICY "Users can view own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);
```

---

### 2. `children`

Represents children/patients associated with a parent user profile.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `parent_id` | UUID | NOT NULL, FK → `profiles.id` | Reference to parent user |
| `name` | VARCHAR(255) | NOT NULL | Child's name |
| `birth_date` | DATE | NULLABLE | Child's date of birth |
| `metadata` | JSONB | DEFAULT '{}' | Flexible data: allergies, hyperfocuses, support level |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Indexes**:
- `idx_children_parent_id` on `parent_id` (for listing children by parent)

**RLS Policy**:
```sql
-- Parents can only access their own children's records
CREATE POLICY "Parents can view own children" ON children
  FOR SELECT USING (auth.uid() = parent_id);

CREATE POLICY "Parents can manage own children" ON children
  FOR ALL USING (auth.uid() = parent_id);
```

---

### 3. `processed_webhook_events`

Idempotency tracker for Stripe webhook events.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `stripe_event_id` | VARCHAR(255) | PK | Stripe event ID (e.g., `evt_xxx`) |
| `event_type` | VARCHAR(100) | NOT NULL | Stripe event type (e.g., `payment_intent.succeeded`) |
| `processed_at` | TIMESTAMPTZ | DEFAULT NOW() | When the event was processed |
| `status` | VARCHAR(20) | DEFAULT 'success' | Enum: `success`, `error`, `ignored` |
| `error_message` | TEXT | NULLABLE | Error details if processing failed |

**Indexes**:
- `idx_processed_events_type` on `event_type` (for filtering by event type)

**RLS Policy**:
```sql
-- Only service role can access webhook processing logs
CREATE POLICY "Service role only" ON processed_webhook_events
  FOR ALL USING (false); -- Deny all direct access, use service key
```

---

### 4. `magic_link_logs` *(Optional Audit Table)*

Tracks magic link sends for debugging and audit purposes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `user_id` | UUID | NOT NULL, FK → `profiles.id` | User who received the link |
| `email` | VARCHAR(255) | NOT NULL | Email the link was sent to |
| `sent_at` | TIMESTAMPTZ | DEFAULT NOW() | When the link was sent |
| `triggered_by` | VARCHAR(50) | NOT NULL | Source: `webhook_auto_account`, `user_request`, `admin` |
| `status` | VARCHAR(20) | DEFAULT 'sent' | Enum: `sent`, `clicked`, `expired`, `failed` |

**RLS Policy**:
```sql
-- Users can view their own magic link logs
CREATE POLICY "Users can view own logs" ON magic_link_logs
  FOR SELECT USING (auth.uid() = user_id);
```

---

## Relationships

```
auth.users (1) ────< (1) profiles (1) ────< (N) children
                                              
profiles (1) ────< (N) magic_link_logs
```

## State Transitions

### Subscription Status
```
  trialing ──> active (when trial ends and payment succeeds)
  trialing ──> past_due (when trial ends and payment fails)
  active ──> past_due (when payment fails)
  past_due ──> active (when payment succeeds)
  active ──> canceled (when user cancels or subscription ends)
  past_due ──> canceled (after grace period)
```

### Webhook Event Processing
```
  received ──> validated ──> [idempotent?] ──> processed ──> user_created
                                     │
                                     └────> ignored (duplicate)
  received ──> invalid_signature ──> rejected
  received ──> missing_email ──> rejected
```

## Constraints & Validation

1. **Email Uniqueness**: Enforced by Supabase Auth `auth.users.email` unique constraint.
2. **Stripe Customer ID Uniqueness**: Enforced by `profiles.stripe_customer_id` unique index.
3. **CPF Format**: Should be validated at application layer (11 digits, optional formatting).
4. **Trial End Date**: Must be >= `created_at` if set.
5. **Idempotency**: `processed_webhook_events.stripe_event_id` primary key prevents duplicate processing.

## Migration Notes

- Create `profiles` table with FK to `auth.users.id` (ON DELETE CASCADE)
- Create `children` table with FK to `profiles.id` (ON DELETE CASCADE)
- Create `processed_webhook_events` table (no FK needed, standalone)
- Enable RLS on all tables and create policies
- Create triggers for `updated_at` auto-update

## Assumptions

- Supabase Auth `auth.users` table exists and is managed by Supabase.
- Stripe Customer ID is available in the `payment_intent` object or can be derived from the payment.
- The webhook handler runs with service_role key to bypass RLS during user creation.
