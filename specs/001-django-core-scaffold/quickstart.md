# Quickstart: Django Core Scaffold

**Feature**: 001-django-core-scaffold  
**Date**: 2026-04-23  
**Purpose**: Guia de primeiro acesso para desenvolvedores novos no projeto.

---

## Pré-requisitos

- Docker ≥ 24.0
- Docker Compose ≥ 2.20
- Git
- Acesso às credenciais do projeto (Supabase e Stripe)

## 1. Clone e Setup Inicial

```bash
git clone <repository-url>
cd projeto_aba_opencode
```

## 2. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
# Edite .env com suas credenciais
```

Variáveis obrigatórias:
```
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=your-dev-secret-key-min-50-chars
DEBUG=True
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
LOG_LEVEL=DEBUG
```

## 3. Subir a Aplicação

```bash
docker-compose up --build
```

A aplicação estará disponível em: http://localhost:8000

## 4. Verificar Instalação

```bash
# Em outro terminal
docker-compose exec web python src/manage.py check
```

Saída esperada:
```
System check identified no issues (0 silenced).
```

## 5. Estrutura de Diretórios

```
src/
├── config/           # Settings (base.py, dev.py, prd.py)
├── apps/
│   └── core/         # App de referência
├── templates/        # base.html e partials globais
└── static/           # CSS, JS, imagens
```

## 6. Criar um Novo App

```bash
# Dentro do container
docker-compose exec web python src/manage.py startapp <nome_do_app> src/apps/<nome_do_app>
```

Estrutura esperada do novo app:
```
src/apps/<nome_do_app>/
├── __init__.py
├── services.py       # Obrigatório: lógica de negócio
├── views.py          # Obrigatório: apenas validação e response
├── urls.py           # Obrigatório: rotas do app
└── templates/
    └── <nome_do_app>/
        └── partials/
            └── _*.html   # Partials HTMX
```

## 7. Conventions

### Service Layer
- Toda lógica de negócio em `services.py`
- Views apenas validam input e chamam services
- Type hints obrigatórios em toda interface pública

### HTMX Partials
- Nomear arquivos com prefixo `_` e sufixo `_partial.html`
- Exemplo: `_patient_list_partial.html`
- Retornar apenas o fragmento HTML necessário (sem `<html>`, `<head>`)

### Anti-ORM
- Dados core de pacientes: usar `supabase-py` em `services.py`
- ORM Django permitido apenas para: auth, sessions, admin (não para dados de pacientes)

### RLS-First
- Sempre filtrar por `parent_id = auth.uid()` em queries de pacientes
- Converter UUIDs para `str(uuid)` antes de operações no SDK

### Offline-First
- Usar Alpine.js `x-data` com `localStorage` para estado local
- Indicador de sync visível em todas as páginas

## 8. Troubleshooting

### Porta 8000 ocupada
```bash
# Override via env var
PORT=8001 docker-compose up
```

### Supabase indisponível
- A aplicação deve iniciar mesmo offline
- Verifique indicador de status no header
- Ações offline são enfileiradas em LocalStorage

### Variáveis de ambiente faltando
```bash
# O sistema falha gracefulmente indicando qual variável está ausente
docker-compose logs web
```

## 9. Próximos Passos

Após confirmar que o scaffold está funcionando:

1. Implementar features de negócio seguindo o Service Layer Pattern
2. Criar tabelas no Supabase com RLS habilitado
3. Desenvolver partials HTMX para cada fluxo de usuário
4. Garantir que todas as ações primárias respeitem a Regra dos 5 Segundos

