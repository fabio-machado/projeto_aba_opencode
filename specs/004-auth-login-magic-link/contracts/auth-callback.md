# Contract: GET /auth/callback

**Feature**: Auth Login Screen (Magic Link Flow)
**Method**: GET
**Source**: Refatorado de `apps/payments/views.py:auth_callback` para `apps/auth_app/views.py:auth_callback`

## Request

### Query Parameters (do Supabase Auth Redirect)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `access_token` | string | Yes | JWT access token emitido pelo Supabase Auth |
| `refresh_token` | string | Yes | Refresh token para renovação de sessão |
| `type` | string | Yes | Tipo de callback: `recovery`, `signup`, `magiclink` |
| `token_type` | string | No | Tipo de token: `bearer` |

### Exemplo de URL
```
/auth/callback?access_token=eyJ...&refresh_token=abc123&type=magiclink&token_type=bearer
```

## Response

### Success — Redirect to App (302 Found)

**Condição**: Tokens válidos + usuário pagante ativo.

```http
HTTP/1.1 302 Found
Location: /app
Set-Cookie: supabase_session={access_token}; HttpOnly; Secure; Path=/; Max-Age=7776000; SameSite=Lax
Set-Cookie: supabase_refresh={refresh_token}; HttpOnly; Secure; Path=/; Max-Age=7776000; SameSite=Lax
```

O cookie `supabase_session` contém o JWT `access_token`. O cookie `supabase_refresh` contém o `refresh_token`. Ambos são HTTP-only (não acessíveis via JavaScript), Secure (apenas HTTPS), SameSite=Lax.

### Error — Magic Link Inválido/Expirado (302 Found)

**Condição**: Tokens ausentes, expirados ou inválidos.

```http
HTTP/1.1 302 Found
Location: /login?error=invalid_magic_link
```

### Error — Conta Inativa (302 Found)

**Condição**: Tokens válidos mas `subscription_status` não é `active`/`trialing`.

```http
HTTP/1.1 302 Found
Location: /login?error=account_inactive
```

### Error — Erro Interno (302 Found)

**Condição**: Falha na validação dos tokens ou erro inesperado.

```http
HTTP/1.1 302 Found
Location: /login?error=unexpected
```

## Behavior Notes

- Esta view é chamada automaticamente pelo Supabase Auth após o usuário clicar no Magic Link.
- A URL de callback é configurada no `signInWithOtp` via `emailRedirectTo` apontando para `https://<domain>/auth/callback`.
- A view valida os tokens via Supabase Auth Admin API (`getUser()` com `access_token`).
- Após validação, verifica `profiles.subscription_status` para garantir que o usuário ainda tem acesso ativo.
- Registra `magic_link_logs.status = 'clicked'` quando bem-sucedido.
- Registra `audit_logs` com `action = 'login_success'` ou `'login_rejected'`.
- A rota `/auth/callback` NÃO está na whitelist do middleware (é pública por natureza — o usuário chega sem sessão).
- O redirect `Location: /app` é a entrada da área restrita (ainda a ser definida pelo app shell). No MVP, pode ser `/` ou `/dashboard`.
