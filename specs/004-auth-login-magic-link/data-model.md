# Data Model: Auth Login Screen (Magic Link Flow)

**Feature**: Auth Login Screen (Magic Link Flow) | **Date**: 2026-04-27
**Dependency**: specs 003 (profiles, magic_link_logs, audit_logs)

## Overview

A feature de login reutiliza as tabelas Supabase já criadas pela spec 003 (`profiles`, `magic_link_logs`, `audit_logs`) e adiciona uma nova tabela `login_attempts` para rate limiting e observabilidade. Nenhuma tabela Django ORM é criada — toda persistência usa `supabase-py`.

---

## Entities

### 1. `profiles` *(existente — spec 003)*

Usada para verificar se o e-mail pertence a um usuário pagante ativo antes de disparar o Magic Link.

| Coluna | Tipo | Constraints | Relevância para Login |
|--------|------|-------------|----------------------|
| `id` | UUID | PK, FK → `auth.users.id` | Vincula perfil ao usuário autenticado |
| `email` | VARCHAR(255) | NOT NULL | Identificador de login (via JOIN com `auth.users`) |
| `subscription_status` | VARCHAR(20) | DEFAULT 'active' | Filtro: apenas `active` ou `trialing` podem logar |
| `has_generator_access` | BOOLEAN | DEFAULT FALSE | Flag de acesso ao produto |
| `has_library_access` | BOOLEAN | DEFAULT FALSE | Flag de acesso ao upsell |

**Query de validação de login**:
```sql
SELECT p.id, p.subscription_status, p.has_generator_access, p.has_library_access
FROM profiles p
JOIN auth.users u ON u.id = p.id
WHERE u.email = :email
  AND p.subscription_status IN ('active', 'trialing');
```
Executada via `supabase-py` com service_role key (usuário ainda não autenticado).

---

### 2. `magic_link_logs` *(existente — spec 003)*

Registra cada envio de Magic Link. Utilizada pela feature de login para tracking de disparos.

| Coluna | Tipo | Constraints | Relevância para Login |
|--------|------|-------------|----------------------|
| `id` | UUID | PK | Identificador único |
| `user_id` | UUID | NOT NULL, FK → `profiles.id` | Usuário que recebeu o Magic Link |
| `email` | VARCHAR(255) | NOT NULL | E-mail destinatário |
| `sent_at` | TIMESTAMPTZ | DEFAULT NOW() | Timestamp do envio |
| `triggered_by` | VARCHAR(50) | NOT NULL | Valor: `user_request` (login manual) |
| `status` | VARCHAR(20) | DEFAULT 'sent' | `sent` (enviado), `clicked` (usado), `expired` (1h), `failed` (erro) |

**Uso na feature de login**: inserido após `signInWithOtp` bem-sucedido pelo `auth_service.send_magic_link()`.

---

### 3. `audit_logs` *(existente — spec 003)*

Registra eventos de auditoria. A feature de login insere entradas para ações de segurança (bloqueio por enumeração, invalidação de sessão).

| Coluna | Tipo | Constraints | Relevância para Login |
|--------|------|-------------|----------------------|
| `id` | UUID | PK | Identificador único |
| `user_id` | UUID | NOT NULL, FK → `profiles.id` | Usuário afetado (NULLABLE para ações sem usuário) |
| `action` | VARCHAR(100) | NOT NULL | Ex: `enumeration_blocked`, `session_invalidated`, `login_success`, `login_rejected` |
| `metadata` | JSONB | DEFAULT '{}' | Contexto: IP, e-mail, razão do bloqueio |
| `timestamp` | TIMESTAMPTZ | DEFAULT NOW() | Timestamp do evento |

**Uso na feature de login**: inserido via `log_audit_event()` (já existente em `apps/core/services.py`) para eventos de segurança e login bem-sucedido.

---

### 4. `login_attempts` *(NOVA — esta feature)*

Tabela dedicada para rate limiting (por e-mail e por IP), detecção de enumeração e observabilidade de tentativas de login.

| Coluna | Tipo | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Identificador único |
| `email` | VARCHAR(255) | NOT NULL | E-mail normalizado (trim, lowercase) |
| `ip_address` | VARCHAR(45) | NOT NULL | Endereço IP do cliente (IPv4 ou IPv6) |
| `attempted_at` | TIMESTAMPTZ | DEFAULT NOW() | Timestamp da tentativa |
| `result` | VARCHAR(20) | NOT NULL | `success` (Magic Link enviado), `rejected` (recusado) |
| `rejection_reason` | VARCHAR(50) | NULLABLE | Razão: `email_not_found`, `account_inactive`, `rate_limit_email`, `rate_limit_ip`, `enumeration_detected`, `send_error` |

**Índices**:
```sql
CREATE INDEX idx_login_attempts_email ON login_attempts (email, attempted_at DESC);
CREATE INDEX idx_login_attempts_ip ON login_attempts (ip_address, attempted_at DESC);
CREATE INDEX idx_login_attempts_result ON login_attempts (result);
```

**RLS Policy**:
```sql
-- Apenas service_role pode inserir/consultar (dados sensíveis de IP)
ALTER TABLE login_attempts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON login_attempts FOR ALL USING (false);
```

**Queries de rate limiting**:
```sql
-- Rate limit por e-mail: máximo 3 tentativas em 60 segundos
SELECT COUNT(*) FROM login_attempts
WHERE email = :email
  AND attempted_at > NOW() - INTERVAL '60 seconds';

-- Rate limit por IP: máximo 10 tentativas em 60 segundos
SELECT COUNT(*) FROM login_attempts
WHERE ip_address = :ip_address
  AND attempted_at > NOW() - INTERVAL '60 seconds';

-- Detecção de enumeração: 5+ e-mails distintos do mesmo IP em 60 segundos
SELECT COUNT(DISTINCT email) FROM login_attempts
WHERE ip_address = :ip_address
  AND attempted_at > NOW() - INTERVAL '60 seconds'
  AND result = 'rejected'
  AND rejection_reason = 'email_not_found';
```

---

## Relationships

```
auth.users (1) ── (1) profiles (1) ── (N) magic_link_logs
                                  ── (N) audit_logs

login_attempts (N) ── (email) ──> auth.users.email (FK lógico, sem constraint)
login_attempts (N) ── (ip_address) ── sem FK (IP não é entidade)
```

## State Transitions

### Magic Link Lifecycle
```
  user_requests → sent ──> clicked (usuário clicou no link)
                    │
                    └──> expired (1 hora sem clique)
                    │
                    └──> failed (erro no envio Supabase)
```

### Login Attempt Result
```
  request_received → email_validated → [user exists?]
                                       ├── Yes → [account active?]
                                       │          ├── Yes → [rate limit ok?]
                                       │          │          ├── Yes → send_magic_link → success
                                       │          │          └── No  → rejected (rate_limit_email / rate_limit_ip)
                                       │          └── No  → rejected (account_inactive)
                                       └── No  → [enumeration?]
                                                  ├── Yes → rejected (enumeration_detected) + block IP
                                                  └── No  → rejected (email_not_found)
```

### Session Lifecycle
```
  created (after magic link click) → active (uso normal)
                                   → refreshed (refresh token renova JWT)
                                   → invalidated (cancelamento de assinatura)
                                   → expired (90 dias sem uso)
```

---

## Migration

### Nova migração Supabase

```sql
-- Migration: 005_add_login_attempts

CREATE TABLE login_attempts (
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

CREATE INDEX idx_login_attempts_email ON login_attempts (email, attempted_at DESC);
CREATE INDEX idx_login_attempts_ip ON login_attempts (ip_address, attempted_at DESC);
CREATE INDEX idx_login_attempts_result ON login_attempts (result);

ALTER TABLE login_attempts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON login_attempts FOR ALL USING (false);
```

---

## Constraints & Validation

1. **E-mail normalizado**: Trim whitespace + lowercase antes de qualquer operação (FR-003).
2. **Formato de e-mail**: Validação básica de formato (presença de `@` e domínio) antes de consultar Supabase (FR-002).
3. **IP address**: Extraído de `X-Forwarded-For` (produção com proxy) ou `REMOTE_ADDR` (desenvolvimento). Validado como string IPv4/IPv6 antes de inserir.
4. **Result/Reason enum**: Valores restritos via CHECK constraint no banco + validação no Python.
5. **Tempo de retenção**: Dados de `login_attempts` podem ser expurgados após 90 dias (política de dados temporários). Não implementado no MVP.

## Assumptions

- A tabela `profiles` já existe e é populada pelo webhook Stripe (spec 003).
- O campo `email` em `auth.users` é único (garantido pelo Supabase Auth).
- O IP do cliente é confiável (proxy/CDN configurado corretamente em produção para passar `X-Forwarded-For`).
- A limpeza de dados antigos em `login_attempts` pode ser feita manualmente ou via cron job futuro.
