# Data Model: PWA com Sessão Persistente

**Date**: 2026-04-29
**Feature**: 005-pwa-persistent-auth

## Overview

Esta feature **não introduz novas entidades de banco de dados**. Toda a persistência é feita no lado do cliente (browser) via:

1. **Cookies HTTP-only** (já existentes — feature 004): `supabase_session`, `supabase_refresh`
2. **LocalStorage** (já existente — feature 002): tema (dark/light), estado do banner de instalação
3. **CacheStorage** (novo — via Service Worker): cache de assets estáticos (CSS, JS, ícones)

## Reutilização de Entidades Existentes

### Sessão de Usuário (feature 004)

- **Armazenamento**: Cookies HTTP-only (`supabase_session`, `supabase_refresh`)
- **Duração**: 90 dias (`cookie_max_age_seconds = 7776000`)
- **Renovação**: `refresh_session()` em `apps/auth/services.py`
- **Persistência frontend**: Supabase JS client com `persistSession: true` recupera tokens do LocalStorage interno do Supabase

### Perfil do Usuário (feature 003/004)

- **Tabela**: `profiles` (Supabase)
- **Uso**: Verificação de status da conta ao abrir o app
- **RLS**: Filtrado por `parent_id = auth.uid()`

## Nova Entidade: Cache de Aplicação (Browser-side)

### CacheStorage (API do Navegador)

- **Nome do cache**: `aef-static-v1` (versionado para invalidação)
- **Conteúdo**: Arquivos estáticos do projeto
  - `/static/css/theme.css`
  - `/static/js/app-shell.js`
  - `/static/js/bottom-sheet.js`
  - `/static/js/pwa-session-manager.js` (novo)
  - `/static/js/pwa-install-banner.js` (novo)
  - `/static/images/pwa/icon-192x192.png`
  - `/static/images/pwa/icon-512x512.png`
- **Estratégia**: Cache-First para assets estáticos; Network-First não é usado (dados dinâmicos não são cacheados)
- **Invalidação**: No evento `activate` do service worker, caches antigos são deletados quando uma nova versão é instalada

### LocalStorage (Frontend)

Novas chaves adicionadas:

| Chave | Tipo | Descrição |
|-------|------|-----------|
| `aef_pwa_banner_dismissed` | boolean | Usuário dispensou o banner de instalação |
| `aef_pwa_installed` | boolean | App foi instalado (detectado via `appinstalled`) |

**Nota**: O tema (`aef_theme`) já existe desde a feature 002.

## Manifesto do App (JSON)

Gerado automaticamente pelo django-pwa a partir de `PWA_APP_CONFIG`:

```json
{
  "name": "Autismo em Foco",
  "short_name": "AEF",
  "display": "standalone",
  "orientation": "portrait",
  "theme_color": "#14b8a6",
  "background_color": "#f8fafc",
  "start_url": "/",
  "scope": "/",
  "icons": [
    {"src": "/static/images/pwa/icon-192x192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/static/images/pwa/icon-512x512.png", "sizes": "512x512", "type": "image/png"}
  ]
}
```
