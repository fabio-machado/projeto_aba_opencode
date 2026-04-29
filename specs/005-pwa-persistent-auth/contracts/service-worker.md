# Contract: Service Worker

**Date**: 2026-04-29
**Feature**: 005-pwa-persistent-auth

## Overview

O Service Worker é um script JavaScript que roda em background no navegador, independente da página web. Ele intercepta requisições de rede e gerencia o cache de assets estáticos.

## Lifecycle

### Install

**Trigger**: Primeira visita ao site ou quando uma nova versão do service worker é detectada.

**Behavior**:
- Abre o cache `aef-static-v1`
- Adiciona todos os assets críticos ao cache (pré-cache)
- Assets pré-cacheados:
  - `/static/css/theme.css`
  - `/static/js/app-shell.js`
  - `/static/js/bottom-sheet.js`
  - `/static/js/pwa-session-manager.js`
  - `/static/js/pwa-install-banner.js`
  - `/static/images/pwa/icon-192x192.png`
  - `/static/images/pwa/icon-512x512.png`

### Activate

**Trigger**: O service worker anterior é liberado (todas as páginas controladas pelo worker antigo são fechadas).

**Behavior**:
- Deleta caches antigos (nomes diferentes de `aef-static-v1`)
- Toma controle das páginas imediatamente (`clients.claim()`)

### Fetch

**Trigger**: Qualquer requisição de rede feita pela página controlada.

**Behavior**:
- Para requests de assets estáticos (CSS, JS, PNG, SVG, fontes):
  - Tenta responder do cache primeiro (`cache.match()`)
  - Se não estiver no cache, faz fetch para a rede e armazena no cache
- Para todos os outros requests (HTMX, API, etc.):
  - Pass-through para a rede (não intercepta)

## Cache Strategy

| Tipo de Asset | Estratégia | Justificativa |
|---------------|------------|---------------|
| CSS/JS estáticos | Cache-First | Garante carregamento instantâneo; assets raramente mudam |
| Ícones/imagens | Cache-First | Ícones são estáticos; carregamento rápido é crítico para UX |
| HTMX fragments | Network-Only | Dados dinâmicos não devem ser cacheados para evitar stale data |
| API / Supabase | Network-Only | Dados de autenticação e pacientes devem vir do servidor |

## Versionamento

O nome do cache inclui a versão (`aef-static-v1`). Quando os assets são atualizados:
1. Incrementar a versão no service worker (ex: `aef-static-v2`)
2. O novo service worker será instalado em background
3. Na próxima visita (ou após fechar todas as abas), o novo cache será ativado

## Limitações

- O Service Worker **não pode** acessar DOM diretamente
- O Service Worker **não pode** interceptar requisições cross-origin (a menos que com CORS)
- O cache é limitado pelo espaço disponível do navegador (geralmente ~50MB por origin)
- HTTPS é obrigatório para Service Workers em produção (localhost é exceção para desenvolvimento)

## Fallback

Se o Service Worker falhar ao carregar ou não for suportado pelo navegador:
- O app funciona normalmente como um site web padrão
- Nenhum cache offline estará disponível
- A sessão ainda persiste via cookies HTTP-only e LocalStorage do Supabase
