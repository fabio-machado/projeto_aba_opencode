# Research: Auth Login Screen (Magic Link Flow)

**Feature**: Auth Login Screen (Magic Link Flow) | **Date**: 2026-04-27
**Source**: [spec.md](./spec.md) | [plan.md](./plan.md)

---

## 1. Supabase Auth Magic Link Flow

### Decision
Usar `auth.signInWithOtp` (Supabase Auth SDK) com `emailRedirectTo` apontando para `/auth/callback`. O callback já existe no app `payments` (spec 003) e será refatorado para o novo `apps/auth_app`.

### Rationale
- O Supabase Auth gerencia todo o ciclo do Magic Link: geração do token, envio de e-mail, verificação na callback.
- O callback existente em `payments/views.py:auth_callback` já extrai `access_token`, `refresh_token`, `type` da query string e armazena sessão via cookie HTTP-only.
- A separação em `apps/auth_app` isola a responsabilidade de autenticação do app de pagamentos, respeitando o Service Layer pattern.

### Alternatives Considered
- **Django Allauth / Django built-in auth**: Rejeitado — o projeto usa Supabase Auth como provedor de identidade externo; Django serve apenas como servidor HTTP/SSR. Usar Django auth local criaria uma segunda fonte de verdade de identidade e complexidade desnecessária.
- **Edge Function (Deno)** no Supabase para validação de usuário pagante: Rejeitado para MVP — manter a lógica no Django `services.py` simplifica debugging e evita duplicação da lógica de rate limiting entre edge e backend.

---

## 2. Verificação de Usuário Pagante Ativo

### Decision
Consultar a tabela `profiles` no Supabase (criada pela spec 003) filtrando por `email` e `subscription_status = 'active'`. Usar `supabase-py` com service_role key para bypass RLS (a query ocorre antes da autenticação).

### Rationale
- A tabela `profiles` já contém `subscription_status` (ativo, trialing, past_due, canceled) sincronizado pelo webhook Stripe.
- A service_role key permite consultar `profiles` sem RLS — necessário porque o usuário ainda não está autenticado.
- Consulta por e-mail (não por UUID) usando índice na tabela `auth.users` → JOIN implícito via FK.

### Alternatives Considered
- **Usar Supabase Auth Admin API (`getUserByEmail`)**: Rejeitado — requer chamada API extra e não retorna o `subscription_status` que está em `profiles`.
- **Criar view materializada**: Rejeitado para MVP — adiciona complexidade de manutenção sem ganho de performance mensurável para o volume esperado.

---

## 3. Rate Limiting — E-mail e IP

### Decision
Implementar rate limiting em duas camadas via tabela Supabase `login_attempts`:
1. **Por e-mail**: máximo 3 tentativas em 60 segundos (janela deslizante).
2. **Por IP**: máximo 10 tentativas em 60 segundos (janela deslizante), independente do e-mail.
3. **Detecção de enumeração**: 5+ e-mails distintos do mesmo IP em 60 segundos → bloqueio do IP + log de segurança.

### Rationale
- Tabela dedicada no Supabase garante persistência cross-instance (Django pode ter múltiplos workers).
- Janela deslizante via `COUNT` com `WHERE created_at > NOW() - INTERVAL '60 seconds'` — simples e eficaz.
- IP do cliente extraído de `request.META['REMOTE_ADDR']` (ou `X-Forwarded-For` em produção com proxy).
- Durante bloqueio, a mensagem de erro é genérica: "Muitas tentativas. Aguarde antes de tentar novamente." — NUNCA revela se o e-mail existe.

### Alternatives Considered
- **Django cache framework (Redis/Memcached)**: Rejeitado — adiciona dependência de infra; tabela Supabase é suficiente para o volume MVP.
- **Rate limiting no middleware Django**: Rejeitado — precisa ser aplicado especificamente ao endpoint de login, não a todas as rotas.
- **django-ratelimit (pacote externo)**: Rejeitado — simplicidade; implementação própria com Supabase é ~20 linhas de SQL.

---

## 4. Persistência de Sessão (90 dias + Refresh Token)

### Decision
Usar a configuração padrão do Supabase Auth com `auth.setSession()` ao receber o callback. O Supabase Auth já emite refresh tokens automaticamente. Configurar:
- JWT expiry: 3600 segundos (1 hora — padrão Supabase).
- Refresh token rotation: habilitado.
- Cookie `supabase_session` HTTP-only com `max_age = 7776000` (90 dias).

### Rationale
- O Supabase Auth já suporta refresh token rotation nativa — não requer código customizado.
- O refresh ocorre automaticamente via `supabase.auth.refreshSession()` — pode ser chamado no middleware de proteção de rota quando o token expirar.
- Sessão de 90 dias atende SC-004 ("permanecem autenticados por pelo menos 30 dias consecutivos").

### Alternatives Considered
- **Django sessions**: Rejeitado — o Django não é a fonte de verdade de autenticação; manter duas sessões (Django + Supabase) duplica complexidade e cria risco de dessincronização.
- **JWT custom com refresh manual**: Rejeitado — reinventar a roda; o Supabase Auth já implementa refresh token rotation seguro.

---

## 5. Proteção de Rotas (LoginRequiredMiddleware)

### Decision
Criar um middleware Django `LoginRequiredMiddleware` que verifica a existência de sessão Supabase ativa no cookie `supabase_session`. Rotas públicas (ex: `/login`, `/health/`, `/webhooks/stripe`) são configuradas em uma whitelist. Rotas sem sessão ativa recebem redirect 302 para `/login?next=<original_url>`.

### Rationale
- Middleware intercepta todas as requisições antes de alcançar views — cobertura completa sem depender de mixins em cada view.
- O cookie `supabase_session` é setado pelo `auth_callback` existente — já contém `access_token` e `refresh_token`.
- Whitelist configurável via `settings.LOGIN_EXEMPT_URLS` (lista de padrões regex).

### Alternatives Considered
- **LoginRequiredMixin em cada view**: Rejeitado — propenso a falha humana (esquecer uma view desprotegida).
- **Decorator @login_required em views**: Rejeitado — mesmo problema de cobertura; middleware é mais seguro.

---

## 6. Invalidação de Sessão ao Cancelar Assinatura

### Decision
O middleware de proteção de rota, além de verificar existência de sessão, consulta `profiles.subscription_status` para o usuário autenticado. Se `subscription_status IN ('canceled', 'past_due')`, a sessão é invalidada (cookie removido) e o usuário é redirecionado para `/login` com mensagem de conta inativa.

### Rationale
- Evita polling ou sinais assíncronos — cada requisição protegida verifica o status no banco.
- A latência da verificação é mínima (query por `user_id` indexado).
- Atende FR-017 sem necessidade de webhook adicional.

### Alternatives Considered
- **Supabase Auth Hooks (Postgres trigger)**: Rejeitado — Supabase Auth hooks são complexos de configurar e testar localmente.
- **Signal/evento do webhook Stripe**: Rejeitado — o webhook já atualiza `profiles.subscription_status`; o middleware reage a essa mudança de forma passiva.

---

## 7. Identidade Visual — Consistência com Spec 002

### Decision
A tela de login (`login.html`) segue 100% os tokens visuais estabelecidos na spec 002 (App Shell e Identidade Visual):
- **Fonte**: Inter (Google Fonts), escala: base 16px, caption 12px.
- **Cores**: primary Teal-500 (#14b8a6), surface Slate-50 (#f8fafc), on-surface Slate-900 (#0f172a), error Red-500 (#ef4444).
- **Arredondamento**: botão `rounded-xl` (12px), input `rounded-lg` (8px).
- **Espaçamento**: grid 4px com múltiplos definidos (4, 8, 12, 16, 24, 32, 48).
- **Toque mínimo**: 48×48 dp em todos os elementos interativos.
- **Contraste**: WCAG AA 4.5:1 texto normal, 3:1 componentes grandes.
- **Dark mode**: Respeita preferência salva no LocalStorage + fallback para sistema operacional (spec 002 FR-002).

### Rationale
- O usuário exige explicitamente conciliar com a identidade visual existente.
- A spec 002 define tokens semânticos que facilitam reuso — basta usar as classes Tailwind correspondentes.
- Dark mode já implementado via `theme.css` e `app-shell.js` — a tela de login herda automaticamente.

### Design específico da tela de login
- Layout **minimalista**: sem header fixo com logo/nav, sem bottom navigation bar. Apenas o essencial.
- Centralizado verticalmente no viewport (`min-h-screen flex items-center justify-center`).
- Card com `rounded-2xl`, `shadow-lg`, fundo `surface` no modo claro / `surface-variant` no modo escuro.
- Logo/ícone da marca no topo do card (sem elemento `<img>` que possa quebrar).
- Campo de e-mail com `rounded-lg`, label visível, placeholder: "seu@email.com".
- Botão "Receber Acesso" `rounded-xl`, fundo `primary` (Teal-500), texto branco, largura total.
- Texto instrucional abaixo do campo: "Enviaremos um link de acesso para o seu e-mail. Não é necessário senha." (caption, 12px).
- Link de suporte no rodapé: "Problemas com seu acesso? Fale conosco" (link mailto ou página de contato).
- Aviso LGPD: "Seus dados são protegidos conforme nossa Política de Privacidade" (caption, link).
- Estados: loading (spinner no botão), erro (mensagem inline vermelha via HTMX partial), sucesso (substituição do form pela mensagem de confirmação).

---

## 8. Logging e Observabilidade

### Decision
Log de todas as tentativas de login na tabela `login_attempts` no Supabase, incluindo: e-mail normalizado, IP, timestamp, resultado, razão da falha. Métricas agregadas via queries SQL (COUNT por status, por hora). Sem alertas automáticos no MVP.

### Rationale
- Tabela única combina rate limiting e logging — evita duplicação de dados.
- Mesmo schema usado para queries de rate limiting serve para dashboards de monitoramento.
- Alertas automáticos podem ser adicionados futuramente (ex: webhook alertando quando >20 falhas em 5 minutos).

### Alternatives Considered
- **structlog / Django logging**: Rejeitado — logs em arquivo são efêmeros em containers Docker; tabela Supabase é persistente e queryable.
- **Sentry / Datadog**: Rejeitado para MVP — custo adicional; logging na tabela Supabase cobre necessidade imediata.

---

## 9. Magic Link Expiration (1 hora)

### Decision
Usar o valor padrão do Supabase Auth OTP: 3600 segundos (1 hora). FR-018 confirma este valor.

### Rationale
- Padrão Supabase — zero configuração adicional.
- 1 hora é tempo suficiente para o usuário acessar o e-mail (incluindo delays de provedor) e seguro o suficiente para mitigar interceptação de link.

---

## 10. Acessibilidade WCAG 2.1 AA

### Decision
Implementar os seguintes critérios na tela de login:
- **Contraste**: 4.5:1 texto normal, 3:1 componentes grandes (já garantido pelos tokens spec 002).
- **Labels semânticos**: `<label for="email">` associado ao input; `aria-label` no botão.
- **Navegação por teclado**: ordem de tabulação lógica (email → botão → suporte); foco visível com outline.
- **Screen readers**: `role="alert"` na área de feedback de erro/sucesso para anúncio automático.
- **Font scaling**: layout não quebra com aumento de 200% do sistema operacional (testado via SC-008).

### Rationale
- A spec 002 já atinge WCAG AA para a estrutura base (SC-002 da spec 002: Lighthouse ≥ 95).
- A tela de login precisa apenas garantir que os elementos específicos (input, botão, feedback) também atendam.
