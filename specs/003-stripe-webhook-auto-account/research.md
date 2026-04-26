# Research: Stripe Webhook Auto Account

**Date**: 2026-04-26
**Feature**: Stripe Webhook Auto Account

## Decisions

### Stripe Webhook Signature Validation
- **Decision**: Use Stripe's official SDK/library for signature validation (`stripe.Webhook.construct_event` equivalent).
- **Rationale**: Stripe provides a well-tested, cryptographically secure method using HMAC-SHA256 with timestamp tolerance checks. Rolling a custom implementation introduces security risks.
- **Alternatives considered**: Custom HMAC implementation (rejected — security risk).

### Idempotency Strategy
- **Decision**: Track processed Stripe event IDs in a dedicated `processed_webhook_events` table.
- **Rationale**: Stripe event IDs (`evt_xxx`) are globally unique and immutable. Storing them with a unique constraint prevents duplicate processing at the database level, providing a robust idempotency guarantee.
- **Alternatives considered**: Redis/Memcached deduplication (rejected — adds infrastructure dependency); application-level locking (rejected — less reliable under retries).

### Magic Link Authentication
- **Decision**: Use Supabase Auth `signInWithOtp` with magic link emails.
- **Rationale**: Supabase Auth natively supports passwordless login via magic links. The token/session management (including 90-day expiry) is handled by Supabase, reducing custom auth code. Tokens are JWT-based and configurable via Supabase dashboard.
- **Alternatives considered**: Custom JWT generation and email sending (rejected — unnecessary complexity when Supabase provides this); password-based with temporary passwords (rejected — poor UX and security).

### User Creation Flow
- **Decision**: Create Supabase Auth user first, then insert into `profiles` table using the Auth user UUID as `id`.
- **Rationale**: This maintains referential integrity between Supabase Auth and application data. The `profiles` table acts as an extension of the auth user, following the standard Supabase pattern.
- **Alternatives considered**: Create profile first then auth user (rejected — risk of orphan profiles if auth creation fails).

### Data Access Pattern
- **Decision**: Use `supabase-py` for all Supabase interactions (both Auth and Database), with Django views as thin HTTP adapters.
- **Rationale**: Aligns with project constitution (Anti-ORM for core data, Service Layer pattern). Django ORM is avoided for user/patient data per project constraints.

### Webhook Endpoint Design
- **Decision**: Stateless webhook endpoint that validates, processes, and responds synchronously.
- **Rationale**: Stripe expects a response within a few seconds. Synchronous processing is acceptable for user creation (fast DB operation). For future expansion to slower operations, a queue can be introduced.
- **Alternatives considered**: Async queue-based processing (deferred — not needed for v1, user creation is fast enough).

## Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Web Framework | Django 5.x | Project standard, handles HTTP routing |
| HTTP Client | HTMX | Project standard for frontend interactivity |
| Database Client | supabase-py | Project constitution mandates for core data |
| Auth | Supabase Auth | Handles magic links, JWT sessions, 90-day tokens |
| Payment | Stripe | Requirement from feature description |
| Validation | Stripe Python SDK | Official, secure webhook signature validation |

## Security Considerations

1. **Webhook Endpoint Exposure**: The endpoint is public but protected by Stripe signature validation. No authentication required from Stripe side (they use the signature).
2. **Replay Attacks**: Mitigated by Stripe's timestamp tolerance (default 5 minutes) in signature validation.
3. **Magic Link Security**: Single-use links with configurable expiry. Supabase Auth handles invalidation after use.
4. **Email Enumeration**: The webhook returns 200 for existing users (no account created) to prevent leakage, per specification.

## References

- Stripe Webhook Best Practices: https://stripe.com/docs/webhooks/quickstart
- Supabase Auth Magic Link: https://supabase.com/docs/guides/auth/auth-magic-link
- Supabase Python Client: https://supabase.com/docs/reference/python
- Stripe Python SDK: https://stripe.com/docs/api?lang=python
