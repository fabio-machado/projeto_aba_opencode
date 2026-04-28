# Quickstart: Auth Login Screen (Magic Link Flow)

**Feature**: 004-auth-login-magic-link | **Date**: 2026-04-27

---

## Pré-requisitos

- Feature 003 (Stripe Webhook Auto Account) implementada — tabelas `profiles`, `magic_link_logs`, `audit_logs` existentes no Supabase.
- Supabase project rodando com Auth habilitado.
- Variáveis de ambiente configuradas no `.env`:
  ```bash
  SUPABASE_URL=https://<project>.supabase.co
  SUPABASE_KEY=<service_role_key>
  SUPABASE_ANON_KEY=<anon_key>
  SUPABASE_SERVICE_KEY=<service_role_key>  # Já usado pela spec 003
  SUPPORT_EMAIL=suporte@exemplo.com        # NOVO: e-mail de suporte no rodapé
  ```

---

## Passo 1: Criar tabela `login_attempts` no Supabase

```sql
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

## Passo 2: Criar app Django `apps/auth_app`

```bash
mkdir -p src/apps/auth_app/templates/auth_app/partials
touch src/apps/auth_app/__init__.py
```

Criar `src/apps/auth_app/apps.py`:
```python
from django.apps import AppConfig

class AuthAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth_app"
    label = "auth_app"
```

---

## Passo 3: Registrar app e middleware

Em `src/config/settings/base.py`, adicionar em `INSTALLED_APPS`:
```python
"apps.auth_app",
```

Adicionar nova config no final do arquivo:
```python
# Rotas públicas que não exigem autenticação
LOGIN_EXEMPT_URLS = [
    r"^/login/?$",
    r"^/auth/callback/?$",
    r"^/health/?$",
    r"^/webhooks/stripe/?$",
    r"^/static/",
]
LOGIN_URL = "/login"
```

Em `src/config/settings/base.py`, adicionar middleware ANTES do `django.middleware.common.CommonMiddleware`:
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.auth_app.middleware.LoginRequiredMiddleware",  # NOVO
    "django.contrib.sessions.middleware.SessionMiddleware",
    # ... restante ...
]
```

---

## Passo 4: Adicionar URLs

Em `src/config/urls.py`:
```python
path("", include("apps.auth_app.urls")),  # NOVO
```

---

## Passo 5: Corrigir redirect após callback

A URL de redirect após Magic Link (`redirectTo`) deve apontar para a área restrita. No `services.py` do `auth_app`:
```python
REDIRECT_TO_URL = os.getenv("APP_URL", "http://localhost:8000") + "/app"
```

Se `/app` ainda não existir como rota, usar `/` temporariamente:
```python
REDIRECT_TO_URL = os.getenv("APP_URL", "http://localhost:8000") + "/"
```

---

## Passo 6: Rodar e testar

```bash
python src/manage.py runserver
```

1. Acessar `http://localhost:8000/login` — deve exibir a tela de login.
2. Submeter e-mail de um usuário pagante existente (criado via spec 003).
3. Verificar recebimento do Magic Link no e-mail.
4. Clicar no link — deve redirecionar para área restrita com sessão ativa.
5. Acessar `http://localhost:8000/routines/` — se autenticado, exibe a página; se não, redireciona para `/login`.

---

## Fluxo de Teste Manual

```text
1. GET  /login                        → 200 (tela de login)
2. POST /login  email=teste@email.com  → 200 (erro: e-mail não encontrado)
3. POST /login  email=usuario@pago.com → 200 (sucesso: "Link enviado!")
4. ✉️  Clicar Magic Link no e-mail     →
5. GET  /auth/callback?access_token=... → 302 → /app
6. GET  /app                           → 200 (área restrita, autenticado)
7. Fechar e reabrir navegador           →
8. GET  /app                           → 200 (sessão persistente, autenticado)
```

---

## Verificações

- [ ] Tela de login acessível em `/login` (pública, sem autenticação).
- [ ] Submissão com e-mail não cadastrado exibe "E-mail não encontrado".
- [ ] Submissão com e-mail pagante válido exibe "Link enviado!" e dispara Magic Link.
- [ ] Magic Link chega no e-mail e redireciona para área restrita.
- [ ] Sessão persiste após fechar/reabrir navegador.
- [ ] Tentar acessar `/routines/` sem sessão redireciona para `/login?next=/routines/`.
- [ ] 4+ tentativas no mesmo e-mail em 60s exibe "Muitas tentativas".
- [ ] 11+ tentativas do mesmo IP em 60s exibe "Muitas tentativas".
- [ ] Tela de login atende contraste WCAG AA e navegação por teclado.
- [ ] Dark mode funciona conforme preferência salva no LocalStorage.
