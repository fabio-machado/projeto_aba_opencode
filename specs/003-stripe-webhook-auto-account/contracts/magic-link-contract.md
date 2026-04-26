# Contract: Magic Link Authentication

**Feature**: Stripe Webhook Auto Account  
**Version**: 1.0.0

## Overview

Magic link authentication flow for users created automatically via Stripe webhook. Allows passwordless login with 90-day session tokens.

## Flow

1. User receives magic link via email after account creation
2. User clicks the link
3. System validates the token and creates session
4. User is redirected to the application dashboard

## Endpoints

### 1. Send Magic Link (Internal)

Triggered automatically by webhook handler. Not exposed as public API.

**Internal Call**:
```python
supabase.auth.sign_in_with_otp({
  "email": "user@example.com",
  "options": {
    "email_redirect_to": "https://app.example.com/auth/callback"
  }
})
```

### 2. Magic Link Callback

**Endpoint**: `GET /auth/callback`

**Query Parameters**:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `access_token` | Yes | Supabase JWT access token |
| `refresh_token` | Yes | Token to refresh session |
| `type` | Yes | Must be `magiclink` |

**Success Response**:
- Sets HTTP-only cookie with session
- Redirects to `/dashboard`

**Error Response**:
- Redirects to `/login?error=invalid_magic_link`

### 3. Session Validation

**Endpoint**: `GET /api/auth/session` (or use Supabase client)

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "authenticated"
  },
  "expires_at": "2026-07-25T18:28:00Z"
}
```

## Token Specifications

| Property | Value |
|----------|-------|
| Token Type | JWT |
| Provider | Supabase Auth |
| Access Token TTL | 90 days (configured in Supabase dashboard) |
| Refresh Token | Rotating, single-use |
| Session Storage | HTTP-only cookie + localStorage (for HTMX requests) |

## Email Template

**Subject**: "Bem-vindo! Acesse sua conta"

**Body**:
```
Olá {full_name},

Sua conta foi criada com sucesso após a confirmação do pagamento.

Clique no link abaixo para acessar sua conta:

{magic_link}

Este link é válido por 1 hora e pode ser usado apenas uma vez.

Atenciosamente,
Equipe Autismo em Foco
```

## Security Considerations

1. **Token Expiry**: Magic links expire after 1 hour (Supabase default).
2. **Single Use**: Each magic link can only be used once.
3. **Rate Limiting**: Limit magic link sends to 3 per email per hour.
4. **Session Hijacking**: Use HTTPS-only cookies with `SameSite=Lax`.
5. **Logout**: Invalidate session server-side and clear cookies.

## Error Codes

| Code | Description | Action |
|------|-------------|--------|
| `invalid_magic_link` | Token expired or invalid | Request new magic link |
| `rate_limited` | Too many requests | Wait before retrying |
| `email_not_found` | User does not exist | Contact support |
| `session_expired` | 90-day token expired | Request new magic link |

## Integration with Stripe Webhook

```
Stripe Webhook
  │
  ▼
POST /webhooks/stripe
  │
  ├──> Valid signature?
  │      ├──> No → 400
  │      └──> Yes
  │
  ├──> Already processed?
  │      ├──> Yes → 200
  │      └──> No
  │
  ├──> Has email?
  │      ├──> No → 400
  │      └──> Yes
  │
  ├──> User exists?
  │      ├──> Yes + active session → 200
  │      ├──> Yes + no session → Resend magic link → 200
  │      └──> No → Create user + Send magic link → 200
```
