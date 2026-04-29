# Research: PWA com Sessão Persistente

**Date**: 2026-04-29
**Feature**: 005-pwa-persistent-auth

## Decisions

### Decision 1: django-pwa como biblioteca PWA

**Rationale**: A biblioteca `django-pwa` (maintained by silviolleite/django-pwa) é a solução mais madura e de menor fricção para projetos Django. Ela fornece:
- Geração automática do manifest.json via configuração Python (`PWA_APP_CONFIG`)
- Template tag `{% progressive_web_app_meta %}` que injeta todas as meta tags necessárias
- Registro automático de URLs para `/manifest.json` e `/serviceworker.js`
- Template base de service worker customizável

**Alternatives considered**:
- Implementar manifest.json e service worker manualmente: rejeitado porque adiciona manutenção desnecessária sem ganho funcional
- Usar Workbox: rejeitado porque adiciona complexidade de build (npm/webpack) que viola o princípio Anti-SPA da Constitution

### Decision 2: Service Worker com Cache-First para assets estáticos

**Rationale**: Para um app focado em mobile com conectividade instável, a estratégia Cache-First para assets estáticos (CSS, JS, ícones) garante carregamento instantâneo em aberturas subsequentes. Dados dinâmicos (conteúdo HTMX) não são cacheados pelo service worker — eles vêm do servidor.

**Estratégia**:
- `install` event: pré-cache dos assets críticos (theme.css, app-shell.js, bottom-sheet.js, ícones)
- `fetch` event: para requests de assets estáticos, responde do cache; para outros, passa-through para rede
- `activate` event: limpa caches antigos

### Decision 3: persistSession: true no Supabase JS client

**Rationale**: O Supabase Auth já gerencia automaticamente a persistência de sessão quando `persistSession: true` é configurado. O cliente JS armazena tokens em LocalStorage e os recupera ao inicializar. Isso alinha-se perfeitamente com o requisito de sessão persistente de 90 dias já implementado pelo backend (feature 004).

**Comportamento**:
- Ao abrir o app, o cliente JS recupera a sessão do LocalStorage
- Se o access token estiver próximo de expirar, chama `refreshSession()` automaticamente
- Se o refresh token expirou (após 90 dias), o usuário é redirecionado para login

### Decision 4: Banner de instalação customizado com beforeinstallprompt

**Rationale**: O evento `beforeinstallprompt` do navegador permite capturar o prompt nativo de instalação e apresentá-lo sob demanda. Isso evita que o navegador mostre o prompt automaticamente (que pode ser intrusivo) e permite UX customizada.

**Implementação**:
- Script vanilla JS (≤ 50 linhas) escuta `beforeinstallprompt`, guarda o evento
- Alpine.js controla a visibilidade do banner
- O banner é um componente discreto no topo da página com texto "Instalar App para registro rápido"
- Ao clicar, dispara o prompt nativo via `event.prompt()`
- Após instalação (`appinstalled`), o banner é oculto permanentemente (guarda estado no LocalStorage)

### Decision 5: Ícones em 192x192 e 512x512

**Rationale**: O manifesto do PWA requer ícones em múltiplas resoluções. 192x192 é usado para ícone de app na tela inicial; 512x512 é usado para splash screen e ícones de alta resolução. Formatos PNG com fundo transparente.

**Arquivos**:
- `static/images/pwa/icon-192x192.png`
- `static/images/pwa/icon-512x512.png`
- (Opcional) `static/images/pwa/maskable-icon.png` — para Android adaptive icons

## Open Questions Resolved

- **Q**: O django-pwa conflita com o HTMX/Alpine.js? **A**: Não. O django-pwa apenas serve arquivos estáticos e meta tags; não interfere no comportamento do HTMX.
- **Q**: O service worker pode interferir nas requisições HTMX? **A**: Sim, se mal configurado. A solução é usar pass-through para todos os requests que não sejam assets estáticos, ou usar `navigator.serviceWorker.register` com `scope` adequado.
- **Q**: Como detectar se o app já está instalado? **A**: Verificar `window.matchMedia('(display-mode: standalone)').matches` ou `navigator.standalone` no iOS. Também escutar o evento `appinstalled`.
