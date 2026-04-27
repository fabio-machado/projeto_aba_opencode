# Research: Django Core Scaffold

**Feature**: 001-django-core-scaffold  
**Date**: 2026-04-23  
**Purpose**: Documentar decisões técnicas investigadas para o esqueleto base da aplicação Autismo em Foco.

---

## Decision 1: Docker Base Image

**Decision**: Usar `python:3.12-slim` como imagem base.

**Rationale**:
- `python:3.12-slim` oferece equilíbrio entre tamanho de imagem (~60MB) e disponibilidade de ferramentas de build
- `alpine` é menor mas pode causar problemas com bibliotecas nativas (psycopg2, cryptography)
- `python:3.12` (full) é desnecessariamente grande para produção

**Alternatives considered**:
- `python:3.12-alpine` — Rejeitado devido a complexidade de compilação de dependências nativas
- `python:3.12` (full) — Rejeitado devido ao tamanho excessivo (~900MB)

---

## Decision 2: Django Settings Split

**Decision**: Dividir settings em `base.py`, `dev.py`, e `prd.py` dentro de `src/config/settings/`.

**Rationale**:
- A Constitution exige que a arquitetura nasça pronta para dev e prd
- `DJANGO_SETTINGS_MODULE=config.settings.dev` para desenvolvimento local
- `DJANGO_SETTINGS_MODULE=config.settings.prd` para produção (via env var)
- `base.py` contém configurações compartilhadas (INSTALLED_APPS, MIDDLEWARE, HTMX config)

**Alternatives considered**:
- Arquivo único `settings.py` com `if DEBUG:` — Rejeitado por violar o princípio de separação explícita de ambientes
- `django-environ` com sobreposição de variáveis — Aceito como complemento, não substituto

---

## Decision 3: Supabase Client Pattern

**Decision**: Usar `supabase-py` com padrão Singleton encapsulado em `services.py`.

**Rationale**:
- A Constitution proíbe ORM Django para dados core de pacientes
- `supabase-py` é o cliente oficial Python para Supabase
- Singleton evita recriação de conexão a cada request
- Service Layer garante que toda lógica de negócio (incluindo RLS, UUID serialization, audit logging) está centralizada

**Pattern**:
```python
from supabase import create_client
from django.conf import settings

class SupabaseService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
        return cls._instance
```

**Alternatives considered**:
- `postgrest-py` direto — Rejeitado por perder funcionalidades do Supabase (auth, storage, realtime)
- Conexão por request (non-singleton) — Rejeitado por overhead desnecessário

---

## Decision 4: Stripe MCP Integration

**Decision**: Integrar Stripe via MCP (Model Context Protocol) usando SDK `stripe` isolado em `services.py`.

**Rationale**:
- MCP do Stripe já está habilitado no ambiente
- SDK `stripe` oficial é a forma mais robusta de interagir com a API
- Isolamento em `services.py` segue o Service Layer Pattern da Constitution
- Preparação para futuras features de pagamento (Low Ticket → Order Bump → Core SaaS)

**Pattern**:
```python
import stripe
from django.conf import settings

class StripeService:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
```

**Alternatives considered**:
- HTTP raw requests para Stripe API — Rejeitado por reinventar o que o SDK já faz (retry, typing, webhooks)
- Deferir para feature futura — Rejeitado porque o ambiente já está pronto e a arquitetura deve nascer completa

---

## Decision 5: Tailwind CSS Delivery

**Decision**: CDN inicial via `<script src="https://cdn.tailwindcss.com"></script>`.

**Rationale**:
- Clarificação do usuário: "CDN inicialmente e reavaliar no futuro"
- Zero tempo de build no setup inicial
- Permite desenvolvimento imediato sem pipeline de assets
- Reavaliação para build step (PostCSS/django-tailwind) quando o projeto amadurecer

**Alternatives considered**:
- `django-tailwind` com npm — Rejeitado por adicionar complexidade de build no scaffold
- Arquivo CSS estático customizado — Rejeitado por violar o Design System utilitário da Constitution

---

## Decision 6: HTMX + Alpine.js Delivery

**Decision**: Carregar HTMX e Alpine.js via CDN no `base.html`.

**Rationale**:
- Ambas as bibliotecas são standalone e funcionam perfeitamente via CDN
- Zero build step necessário
- A Constitution exige HTMX para trocas parciais e Alpine.js para micro-interações
- Versões pinadas (não "latest") para reproducibilidade

**Pattern**:
```html
<script src="https://unpkg.com/htmx.org@2.0.0"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.0/dist/cdn.min.js"></script>
```

**Alternatives considered**:
- npm + bundler — Rejeitado por adicionar complexidade desnecessária no scaffold
- Download local dos arquivos — Rejeitado por adicionar passo manual de atualização

---

## Decision 7: Logging Infrastructure

**Decision**: Usar `structlog` para logging estruturado com fallback para `logging` padrão do Python.

**Rationale**:
- A Constitution exige auditabilidade (`user_id`, `action`, `timestamp`)
- `structlog` produz JSON em produção (parseável por ferramentas de observabilidade)
- Em desenvolvimento, formato colorido e legível para humanos
- Integração natural com Django via middleware de request logging

**Configuração**:
- DEV: formato console colorido, nível DEBUG
- PRD: formato JSON, nível INFO, saída para stdout (capturado pelo Docker logging driver)

**Alternatives considered**:
- `logging` padrão apenas — Rejeitado por dificultar parsing estruturado em produção
- `loguru` — Rejeitado por ser menos compatível com o ecossistema Django

---

## Decision 8: Type Hints Enforcement

**Decision**: Configurar `mypy` com modo `strict` para garantir type hints em todo código Python.

**Rationale**:
- A Constitution exige type hints estritos para integridade via análise estática
- `mypy` é o type checker de facto para Python
- Modo strict garante cobertura completa (no implicit optional, no untyped calls)
- Integração com pre-commit/CI para bloquear PRs que quebram tipagem

**Configuração**:
```ini
[mypy]
python_version = 3.12
strict = True
warn_return_any = True
warn_unused_configs = True
```

**Alternatives considered**:
- `pyright` — Válido, mas `mypy` tem melhor integração com Django (django-stubs)
- Type hints opcionais — Rejeitado por violar a Constitution

---

## Decision 9: App de Referência (core)

**Decision**: Criar app Django `core` como referência de implementação.

**Rationale**:
- A Constitution exige que cada app contenha `services.py`, `views.py`, `urls.py`, e partials
- O app `core` demonstra o padrão correto sem adicionar lógica de negócio real
- Serve como template para futuros apps (routines, payments, etc.)
- Inclui uma view simples que retorna um partial HTMX como exemplo funcional

**Estrutura do app `core`**:
```
src/apps/core/
├── __init__.py
├── services.py       # SupabaseService, StripeService, AuditLog
├── views.py          # View delegando para service, retornando partial
├── urls.py           # Rota para a view de exemplo
└── templates/
    └── core/
        └── partials/
            └── _example_partial.html
```

---

## Resolução de NEEDS CLARIFICATION

Nenhum marcador `[NEEDS CLARIFICATION]` permanece no spec após esta fase de pesquisa. Todas as decisões técnicas foram documentadas com justificativa.
