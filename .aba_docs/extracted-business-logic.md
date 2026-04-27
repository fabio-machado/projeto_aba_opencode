# 📋 Mapa de Regras de Negócio — Autismo em Foco

> **Extraído de:** Análise estática do código-fonte (Repo Research Skill — Fase 4)
> **Data:** 2026-04-13
> **Escopo:** 6 Django Apps (`accounts`, `core`, `payments`, `routines`, `behavior`, `library`)

---

## Sumário

1. [Modelo de Negócio e Funil](#1-modelo-de-negócio-e-funil)
2. [Módulo Accounts — Autenticação](#2-módulo-accounts--autenticação)
3. [Módulo Core — Dashboard e Onboarding](#3-módulo-core--dashboard-e-onboarding)
4. [Módulo Payments — Stripe Checkout & Webhooks](#4-módulo-payments--stripe-checkout--webhooks)
5. [Módulo Routines — Gerador de Rotinas Visuais](#5-módulo-routines--gerador-de-rotinas-visuais)
6. [Módulo Behavior — Registros ABC, Skills e Relatórios](#6-módulo-behavior--registros-abc-skills-e-relatórios)
7. [Módulo Library — Biblioteca de Crises](#7-módulo-library--biblioteca-de-crises)
8. [Regras de Autorização Transversais](#8-regras-de-autorização-transversais)
9. [Débitos Técnicos e Inconsistências](#9-débitos-técnicos-e-inconsistências)

---

## 1. Modelo de Negócio e Funil

### Estrutura de Monetização

O produto opera com **3 produtos Stripe** mapeados por Price IDs em variáveis de ambiente:

| Produto           | Variável              | Tipo           | Acesso Controlado                    |
| ----------------- | --------------------- | -------------- | ------------------------------------ |
| Gerador de Rotinas | `STRIPE_PRICE_GENERATOR` | Pagamento único | `profile.has_generator_access`       |
| Biblioteca de Crises | `STRIPE_PRICE_LIBRARY`   | Pagamento único (Order Bump) | `profile.has_library_access` |
| Monitor de Evolução | `STRIPE_PRICE_MONITOR`   | Assinatura recorrente | `profile.subscription_status` |

### Funil de Conversão (extraído do código)

```
Anúncio → Landing Page → Checkout Stripe
                              ├── Low-Ticket: Gerador (pagamento único)
                              ├── Order Bump: Biblioteca (checkbox no checkout)
                              └── SaaS: Monitor (assinatura + 7 dias trial)
```

### Flags de Acesso no Perfil (`profiles`)

| Flag                     | Tipo    | Valores possíveis                                |
| ------------------------ | ------- | ------------------------------------------------ |
| `has_generator_access`   | Boolean | `true` / `false`                                 |
| `has_library_access`     | Boolean | `true` / `false`                                 |
| `subscription_status`    | String  | `free`, `active`, `trialing`, `past_due`, `canceled` |
| `stripe_customer_id`     | String  | ID do customer no Stripe                         |
| `trial_ends_at`          | Timestamp | Data de fim do trial                           |

---

## 2. Módulo Accounts — Autenticação

### US-ACC-01: Cadastro de novo usuário (e-mail/senha)

**Rota:** `POST /accounts/signup/`

**Campos obrigatórios:**
- `email` (string, trimmed)
- `password` (string, mínimo 8 caracteres)
- `full_name` (string, trimmed)

**Campos opcionais (UTM tracking):**
- `utm_source`, `utm_medium`, `utm_campaign` — capturados de GET ou POST

**Critérios de aceitação:**
1. Se o usuário já está autenticado (`request.supabase_user`), redireciona para dashboard.
2. Todos os 3 campos são obrigatórios; se vazio → mensagem de erro genérica.
3. Senha < 8 caracteres → erro "A senha deve ter pelo menos 8 caracteres."
4. E-mail já registrado → erro "Este e-mail já está cadastrado." (detectado por str matching em exceção).
5. Sucesso → redireciona para login com mensagem "Conta criada! Verifique seu e-mail para confirmar o cadastro."
6. UTMs são persistidos nos `user_metadata` do Supabase Auth (campo `data`).

**Regras de validação:**
- Validação de e-mail é delegada ao Supabase Auth (sem validação de formato no backend Django).
- Confirmação de e-mail é obrigatória (Supabase envia link).

> **[DÉBITO] ACC-01a:** Não há validação de formato de e-mail no backend. Se o Supabase falhar na validação, o erro genérico é exibido ao usuário.

> **[DÉBITO] ACC-01b:** Não há campo de confirmação de senha. O usuário pode digitar a senha errada sem perceber.

---

### US-ACC-02: Login via e-mail/senha

**Rota:** `POST /accounts/login/`

**Campos obrigatórios:**
- `email` (trimmed)
- `password`

**Critérios de aceitação:**
1. Usuário já autenticado → redireciona para dashboard.
2. Campos vazios → erro "Por favor, preencha e-mail e senha."
3. Credenciais inválidas → erro genérico "E-mail ou senha incorretos." (sem distinção entre e-mail inexistente ou senha errada — segurança).
4. Login bem-sucedido → salva `supabase_access_token` e `supabase_refresh_token` na sessão Django.
5. Parâmetro `?next=` redireciona após login.

**Fluxo de dados:**
```
POST → sign_in_with_password → session.access_token → Django session
```

---

### US-ACC-03: Login Social via Google OAuth

**Rota:** `GET /accounts/google/login/` → redirect → `/accounts/google/callback/`

**Critérios de aceitação:**
1. Inicia OAuth com provider `google` e scopes `email profile`.
2. Redirect URL é construída dinamicamente (`request.build_absolute_uri`).
3. Callback suporta **dois fluxos**:
   - **PKCE (code):** `?code=` no GET → `exchange_code_for_session` → salva tokens na sessão.
   - **Fragment (fallback):** Renderiza template JS que captura `#access_token` do fragment URL.

> **[DÉBITO] ACC-03a:** O template `google_callback.html` com captura de fragment via JS sugere um workaround para o fluxo implícito do OAuth. Deve ser validado se o PKCE é consistente em produção.

---

### US-ACC-04: Logout

**Rota:** `GET|POST /accounts/logout/`

**Critérios de aceitação:**
1. Tenta sign_out no Supabase (se falhar, apenas loga warning — não bloqueia).
2. `request.session.flush()` — destrói toda a sessão Django.
3. Redireciona para login com mensagem "Você saiu com segurança."

---

### Middleware de Autenticação (`SupabaseAuthMiddleware`)

**Regra crítica:** Executado em TODA requisição.

1. Inicializa `request.supabase_user`, `request.supabase_profile`, `request.supabase_session` como `None`.
2. Tenta resgatar `access_token` da sessão Django.
3. Se existe → `client.auth.set_session(access_token, refresh_token)`.
4. Se sessão válida → atualiza tokens na sessão (refresh automático).
5. Busca perfil do usuário na tabela `profiles` via `client.table('profiles').select('*').eq('id', user.id).single()`.
6. Se sessão inválida → limpa tokens da sessão (sem redirecionar).

> **[DÉBITO] ACC-MIDW-01:** O middleware cria um **novo client Supabase por requisição** (`create_client`). Não há pool de conexões ou reutilização. Impacto de performance em escala.

> **[DÉBITO] ACC-MIDW-02:** A query `profiles.select('*')` é executada **em cada requisição autenticada**, mesmo em requisições de arquivos estáticos. Falta cache de perfil.

---

## 3. Módulo Core — Dashboard e Onboarding

### US-CORE-01: Visualizar Dashboard

**Rota:** `GET /dashboard/`

**Pré-requisitos:** Autenticado (`@supabase_login_required`)

**Critérios de aceitação:**
1. Se o usuário não tem filhos cadastrados → redireciona para `/onboarding/`.
2. Exibe estado de acesso de cada módulo baseado nas flags do perfil.
3. Parâmetro `?upgrade=true` exibe UI de upgrade.
4. Contexto inclui: `full_name`, `user_email`, `has_generator_access`, `has_library_access`, `subscription_status`, Price IDs para links de compra.

**Dados obrigatórios:** Perfil do usuário + contagem de filhos.

---

### US-CORE-02: Onboarding (cadastro da criança)

**Rota:** `GET|POST /onboarding/`

**Pré-requisitos:** Autenticado

**Campos obrigatórios:**
- `child_name` (string, trimmed) — **O ÚNICO campo realmente obrigatório**

**Campos opcionais:**
- `date_of_birth` (string, formato date) — enviado como `None` se vazio

**Critérios de aceitação:**
1. Nome vazio → erro "Por favor, informe o nome da criança."
2. Sucesso → insere na tabela `children` com `parent_id` do perfil.
3. Após inserção → dispara e-mail de boas-vindas (não-crítico, falha silenciosamente).
4. Redireciona para dashboard.

**Regra de negócio:** `_has_children()` retorna `True` em caso de erro para evitar loop de redirect (fail-safe).

> **[DÉBITO] CORE-02a:** Não há validação de formato ou coerência da `date_of_birth`. O campo aceita qualquer string ou nulo.

> **[DÉBITO] CORE-02b:** O sistema assume **sempre o primeiro filho** (`children[0]`). Não há suporte real para múltiplos filhos na UI, embora o schema permita.

---

### US-CORE-03: E-mails Transacionais

**Tipos implementados:**

| E-mail                  | Trigger                                      | Template                      |
| ----------------------- | -------------------------------------------- | ----------------------------- |
| Boas-vindas             | Após onboarding (cadastro de criança)        | `emails/welcome.html`        |
| Trial encerrando        | Webhook `customer.subscription.trial_will_end` | `emails/trial_ending.html`  |
| Pagamento falhou        | Webhook `invoice.payment_failed`              | `emails/payment_failed.html` |

**Regras de e-mail:**
- Via SMTP Django (Hostinger).
- Apenas HTML (sem versão texto puro).
- Nome do destinatário: primeiro nome extraído via `name.split()[0]`.
- Fallback: "pai/mãe" se nome vazio.

---

## 4. Módulo Payments — Stripe Checkout & Webhooks

### US-PAY-01: Iniciar Checkout

**Rota:** `GET /payments/checkout/create/?product=<tipo>`

**Pré-requisitos:** Autenticado

**Parâmetros:**
- `product`: `generator` | `library` | `monitor` — mapeia para Price IDs.
- `bump`: `1` — ativa Order Bump (Library + Generator).

**Critérios de aceitação:**
1. Produto inválido → redireciona ao dashboard.
2. Se o usuário não tem `stripe_customer_id` → cria Customer no Stripe e salva no perfil.
3. Line items construídos dinamicamente:
   - Generator + `bump=1` → adiciona Library automaticamente.
4. Modo: `subscription` para Monitor, `payment` para os demais.
5. Trial de 7 dias **apenas** para Monitor (`subscription_data.trial_period_days = 7`).
6. `allow_promotion_codes = True` (cupons habilitados).
7. `locale = 'pt-BR'`.
8. Metadata inclui `supabase_user_id` e `product`.

**Fluxo de dados:**
```
User → checkout_create → Stripe API → Stripe Hosted Checkout → callback
```

---

### US-PAY-02: Página de Sucesso pós-compra

**Rota:** `GET /payments/checkout/success/?session_id=<id>`

**Critérios de aceitação:**
1. Tenta provisionar acesso **imediatamente** via `_provision_from_session`:
   - Paga (`paid` ou `no_payment_required`) → atualiza flags no perfil.
   - Não paga → ignora (webhook tratará depois).
2. Este é um **fallback síncrono** para funcionar em localhost sem webhook.

**Mapeamento de provisão (via line_items):**

| Price ID           | Flag atualizada                     |
| ------------------ | ----------------------------------- |
| `PRICE_GENERATOR`  | `has_generator_access = True`       |
| `PRICE_LIBRARY`    | `has_library_access = True`         |
| `PRICE_MONITOR`    | `subscription_status = 'trialing'`  |

> **[DÉBITO] PAY-02a:** Na provisão síncrona (`_provision_from_session`), o Monitor é setado como `'trialing'`. Porém, no webhook `checkout.session.completed`, o mesmo Monitor é setado como `'active'`. **Inconsistência:** há uma race condition onde o status final depende de qual callback executa por último.

---

### US-PAY-03: Webhook Stripe

**Rota:** `POST /payments/webhook/` (CSRF exempt)

**Eventos tratados:**

| Evento                                     | Handler                         | Ação no Perfil                                  |
| ------------------------------------------ | ------------------------------- | ------------------------------------------------ |
| `checkout.session.completed`               | `_handle_checkout_completed`    | Provisiona acesso por Price ID                   |
| `invoice.payment_succeeded`                | `_handle_invoice_succeeded`     | `subscription_status = 'active'`                 |
| `invoice.payment_failed`                   | `_handle_invoice_failed`        | `subscription_status = 'past_due'` + e-mail      |
| `customer.subscription.deleted`            | `_handle_subscription_deleted`  | `subscription_status = 'canceled'`               |
| `customer.subscription.trial_will_end`     | `_handle_trial_will_end`        | Dispara e-mail de aviso de fim de trial          |

**Regras de segurança:**
1. Valida assinatura HMAC via `stripe.Webhook.construct_event`.
2. Payload inválido → HTTP 400.
3. Assinatura inválida → HTTP 400.
4. Erro no handler → logado, mas retorna 200 (idempotente).

**Regras de provisão no webhook:**
- `supabase_user_id` vem do `session.metadata` — se ausente, ignora.
- Atualização via `stripe_customer_id` para eventos de invoice/subscription.

**E-mails disparados por webhook:**
- `invoice.payment_failed` → busca e-mail do usuário via `auth.admin.get_user_by_id()`.
- `trial_will_end` → calcula dias restantes via `(trial_end - time.time()) / 86400`.

> **[DÉBITO] PAY-03a:** O cálculo de `days_left` no handler `trial_will_end` usa `time.time()` (timezone-unaware). Pode gerar imprecisão dependendo do fuso horário.

---

### US-PAY-04: Portal do Cliente Stripe

**Rota:** `GET /payments/portal/`

**Critérios de aceitação:**
1. Sem `stripe_customer_id` → redireciona ao dashboard.
2. Cria sessão no Stripe Billing Portal.
3. Return URL: `/dashboard/`.

---

## 5. Módulo Routines — Gerador de Rotinas Visuais

### US-ROT-01: Listar rotinas da criança

**Rota:** `GET /rotinas/`

**Pré-requisitos:** Autenticado + `@generator_access_required`

**Critérios de aceitação:**
1. Sem criança cadastrada → redireciona ao onboarding.
2. Busca rotinas com `routine_items` aninados (join com `pictograms`).
3. Itens são ordenados pelo campo `order` em Python (não no banco).

---

### US-ROT-02: Criar rotina unificada (título + pictogramas)

**Rota:** `GET|POST /rotinas/criar/`

**Pré-requisitos:** Autenticado + `@generator_access_required`

**Campos obrigatórios:**
- `title` (string, trimmed)

**Campos opcionais:**
- `pictogram_ids` (lista de UUIDs)

**Critérios de aceitação:**
1. Título vazio → erro "Dê um nome para a rotina antes de salvar."
2. Criação atômica: primeiro cria rotina → depois `bulk_add_routine_items`.
3. Nada é salvo no banco até o submit final.
4. Pictogramas vêm da tabela `pictograms` onde `is_public = True`.

**Categorias de pictogramas:**
- Higiene, Alimentação, Escola, Lazer, Comunicação, Emoções.

---

### US-ROT-03: Editar rotina (reordenar/adicionar/remover pictogramas)

**Rota:** `GET /rotinas/<uuid>/`

**Critérios de aceitação:**
1. Rotina não encontrada (ou de outra criança) → HTTP 404.
2. Itens serializados como JSON para gerenciamento client-side (Alpine.js + SortableJS).
3. **Salvamento batch:** `POST /rotinas/<uuid>/salvar/` → replace all (delete + bulk insert).

**Endpoints HTMX legados (mantidos para compatibilidade):**

| Ação       | Rota                                         | Método |
| ---------- | -------------------------------------------- | ------ |
| Adicionar  | `/rotinas/<routine>/adicionar/`              | POST   |
| Remover    | `/rotinas/<routine>/remover/<item>/`         | POST   |
| Reordenar  | `/rotinas/<routine>/reordenar/<item>/`       | POST   |

**Regra de reordenação:** Swap de valores da coluna `order` entre item atual e vizinho (up/down).

> **[DÉBITO] ROT-03a:** Os endpoints HTMX (`item_add`, `item_remove`, `item_reorder`) são marcados como "legado — mantidos para compatibilidade" mas ainda existem nas URLs. O fluxo principal mudou para salvamento batch. Código morto potencial.

---

### US-ROT-04: Renomear rotina

**Rota:** `POST /rotinas/<uuid>/renomear/`

**Campos obrigatórios:**
- `title` (string, trimmed) — se vazio, **nada é atualizado** (sem mensagem de erro).

**Critérios de aceitação:**
1. Suporta HTMX (retorna HX-Redirect 204) e form nativo (redirect 302).

> **[DÉBITO] ROT-04a:** Título vazio é silenciosamente ignorado. Sem feedback ao usuário.

---

### US-ROT-05: Excluir rotina

**Rota:** `POST /rotinas/<uuid>/excluir/`

**Critérios de aceitação:**
1. Deleta rotina e itens (cascade no banco).
2. Validação de propriedade via `child_id`.
3. Suporta HTMX e form nativo.

---

### US-ROT-06: Exportar rotina como PDF

**Rota:** `GET /rotinas/<uuid>/export/pdf/`

**Critérios de aceitação:**
1. Gera PDF via WeasyPrint.
2. Se WeasyPrint não instalado → HTTP 503 "PDF não disponível."
3. Filename: `rotina_<titulo_sanitizado>.pdf`.

> **[DÉBITO] ROT-06a:** O título da rotina é usado diretamente no filename do PDF sem sanitização de caracteres especiais (acentos, espaços). Pode gerar problemas em certos browsers.

---

## 6. Módulo Behavior — Registros ABC, Skills e Relatórios

### US-BEH-01: Criar registro ABC (Antecedente-Comportamento-Consequência)

**Rota:** `POST /comportamento/registrar/`

**Pré-requisitos:** Autenticado + `@subscription_required`

**Campos obrigatórios:**
- `behavior` (lista, seleção múltipla) — "Selecione pelo menos um comportamento observado."

**Campos opcionais (todos):**
- `antecedent` (lista, seleção múltipla) — JSON ou multiselect
- `consequence` (string, seleção única)
- `intensity` (int, default `3`) — range: 1-5
- `duration` (string key → convertido para minutos) — `5min`=5, `15min`=15, `30min`=30, `60min`=60
- `location` (string) — Casa, Escola/Clínica, Supermercado, Carro, Restaurante, Área pública, Outro
- `notes` (string) — campo livre

**Opções pré-definidas (hardcoded na camada de serviço):**

| Campo        | Quantidade | Exemplos                                              |
| ------------ | ---------- | ----------------------------------------------------- |
| Antecedentes | 10         | "Recebeu uma ordem", "Ouviu um não", "Muito barulho"  |
| Comportamentos | 10       | "Agressão física", "Crise de choro", "Autolesão"      |
| Consequências  | 10       | "Recebeu atenção", "Ganhou o que queria"               |
| Locais       | 7          | "Casa", "Escola/Clínica", "Supermercado"               |
| Durações     | 4          | "Até 5 min", "5–15 min", "15–30 min", "+30 min"       |

**Critérios de aceitação:**
1. Sem criança → redireciona ao onboarding.
2. Sem comportamento selecionado → erro de validação.
3. Antecedente e behavior aceitam JSON ou multiselect (parsing com fallback).
4. `duration` convertido de chave texto para minutos (tabela `DURATION_TO_MINUTES`).
5. Campos vazios são salvos como `None` (não string vazia).
6. Sucesso → redireciona para lista de registros.

---

### US-BEH-02: Editar registro ABC

**Rota:** `POST /comportamento/registros/<uuid>/editar/`

**Critérios de aceitação:**
1. Validação de propriedade: busca registro por `log_id` AND `child_id`.
2. Registro não encontrado → redireciona para lista.
3. Mesmas regras de validação do create.
4. Pré-popula formulário com dados existentes.
5. Duração pré-selecionada via mapeamento reverso (`DURATION_TO_MINUTES` → chave).

---

### US-BEH-03: Excluir registro ABC

**Rota:** `POST /comportamento/registros/<uuid>/deletar/`

**Critérios de aceitação:**
1. `@require_POST` — apenas POST aceito.
2. Validação de propriedade via `child_id`.
3. Suporta HTMX (HX-Redirect 204) e form nativo (redirect 302).

---

### US-BEH-04: Listar registros ABC

**Rota:** `GET /comportamento/`

**Critérios de aceitação:**
1. Últimos 30 registros (limit fixo no service).
2. Paginação: 5 itens por página (`Paginator`).
3. Ordenados por `logged_at DESC`.

**Data Healing (na camada de serviço):**
- Detecta e corrige arrays JSONB aninhados incorretamente (ex: `['["Choro", "Gritos"]']` → `["Choro", "Gritos"]`).

> **[DÉBITO] BEH-04a:** "Data Healing" no `_parse_logged_at` indica dados corrompidos no banco. Os registros com arrays aninhados foram gravados incorretamente em algum momento. Workaround em runtime.

---

### US-BEH-05: Dashboard de Tendências

**Rota:** `GET /comportamento/dashboard/?days=<N>`

**Parâmetros:**
- `days`: `7` | `14` | `30` (default: 7). Valor fora do range → força 7.

**Dados gerados:**
1. **Frequência diária** (gráfico de linha) — preenche dias sem registro com 0.
2. **Top 5 comportamentos** (gráfico de barras horizontais).
3. **Distribuição de intensidade** (gráfico donut) — cores mapeadas: verde (1) → rosa (5).
4. **Estatísticas-resumo:** total, intensidade média, comportamento mais frequente.

**Formatação local:** Meses em PT-BR (`Jan`, `Fev`, etc.) hardcoded.

> **[DÉBITO] BEH-05a:** O fallback de `days` diverge: `except ValueError` seta `days = 30`, mas a validação `if days not in (7, 14, 30)` seta `days = 7`. Lógica inconsistente.

---

### US-BEH-06: Criar habilidade

**Rota:** `POST /comportamento/habilidades/criar/`

**Campos obrigatórios:**
- `skill_name` (string, trimmed) — "Nome obrigatório."

**Critérios de aceitação:**
1. Via HTMX POST → retorna board atualizado (partial render).
2. Habilidade criada com `status = 'active'`.
3. Erro → HTTP 500 com mensagem inline.

---

### US-BEH-07: Registrar skill_log (nível de ajuda)

**Rota:** `POST /comportamento/habilidades/<uuid>/log/`

**Campos obrigatórios:**
- `prompt_level` (int, 1-4) — deve ser exatamente 1, 2, 3 ou 4.

**Níveis e significado:**

| Nível | Label              | Cor      | Emoji |
| ----- | ------------------ | -------- | ----- |
| 1     | Fez sozinho        | Verde    | 🟢    |
| 2     | Precisou de dica   | Amarelo  | 🟡    |
| 3     | Ajuda física       | Laranja  | 🟠    |
| 4     | Não conseguiu      | Vermelho | 🔴    |

**Critérios de aceitação:**
1. `prompt_level` fora de 1-4 → HTTP 400.
2. Retorna card atualizado da habilidade via HTMX.
3. Timestamp gerado automaticamente no banco (`DEFAULT now()`).

---

### US-BEH-08: Visualizar detalhe da habilidade

**Rota:** `GET /comportamento/habilidades/<uuid>/detalhe/?days=<N>`

**Critérios de aceitação:**
1. Habilidade não encontrada → redireciona para lista.
2. Exibe histórico (últimos 5 logs) + gráfico de evolução (barras empilhadas).
3. Dados do gráfico: contagem diária por `prompt_level` no período.
4. Inclui % de independência (`prompt_level=1 / total`).

---

### US-BEH-09: Arquivar / Desarquivar habilidade

**Rotas:**
- `POST /comportamento/habilidades/<uuid>/arquivar/`
- `POST /comportamento/habilidades/<uuid>/desarquivar/`

**Critérios de aceitação:**
1. Arquivar: `status = 'archived'`.
2. Desarquivar: `status = 'active'`.
3. Retorna board atualizado via HTMX.
4. Na listagem, ativos aparecem primeiro, arquivados no final.

---

### US-BEH-10: Excluir habilidade permanentemente

**Rota:** `POST /comportamento/habilidades/<uuid>/deletar/`

**Critérios de aceitação:**
1. Deleta a habilidade E seus logs (cascade no banco).
2. Via form nativo → redirect para lista.
3. Via HTMX → retorna board atualizado.

---

### US-BEH-11: Gerar relatório PDF estruturado

**Rota:** `GET /comportamento/relatorios/gerar/?template=<tipo>&days=<N>`

**Pré-requisitos:** Autenticado + `@subscription_required`

**Parâmetros:**
- `template`: `clinica` | `escolar` | `completo` (default: `completo`)
- `days`: `7` | `14` | `30` | `90` (default: `30`)

**Templates e conteúdo:**

| Template   | Seções incluídas                                                    |
| ---------- | ------------------------------------------------------------------- |
| `clinica`  | Comportamentos ABC, gatilhos, tendência, intensidade, mapa de horários |
| `escolar`  | Habilidades, independência, prompt fading por semana                 |
| `completo` | Todas as seções acima combinadas                                    |

**Gráficos gerados (Base64 via matplotlib):**
- Pizza de gatilhos/antecedentes
- Pizza de consequências
- Linha de tendência comportamental
- Scatter/heatmap de horários (Manhã/Tarde/Noite)
- Barras empilhadas de skills por semana

**Resumo executivo:** Gerado 100% deterministicamente (Zero-LLM) pelo `summary_service.py`:
- Sem chamadas a APIs externas.
- Compliance LGPD/HIPAA (dados nunca saem do servidor).
- Templates de frase em português com variações por tendência (up/down/stable).

**Métricas calculadas para o resumo:**
- Tendência global: comparação entre 1ª e 2ª metade do período.
- Tolerância de 10% para classificar como estável.
- Mínimo de 3 registros para calcular tendência (caso contrário → "stable").
- Intensidade: ≤2 "leve", ≤3 "moderada", >3 "elevada".
- Independência: ≥70% "excelente", ≥40% "consistente", <40% "precisa estímulo".

**Enriquecimento do Top Behaviors:**
- Cada comportamento top-5 inclui: contagem, duração média, tendência individual (up/down/stable/insufficient), % de variação.

**Persistência:**
1. Upload do PDF para Supabase Storage (bucket `reports`, path: `<child_id>/<filename>`).
2. Registro em `exported_reports`: `child_id`, `report_type`, `date_range`, `file_url`.
3. Filename inclui UUID curto para evitar duplicatas no Storage.
4. Filename com caracteres ASCII (acentos removidos via `unicodedata`).

> **[DÉBITO] BEH-11a:** O upload do report para Storage ignora erros (`except → return path`). Se o upload falhar, o registro no banco apontará para um arquivo inexistente, mas a URL assinada gerará 404.

---

### US-BEH-12: Listar relatórios gerados

**Rota:** `GET /comportamento/relatorios/`

**Critérios de aceitação:**
1. Paginação: 5 relatórios por página.
2. URLs assinadas (Signed URLs) com validade de 1 hora (3600s).
3. Conversão de `generated_at` para datetime (parse ISO com fallback para `+00:00`).
4. Se URL assinada falha → `file_url = None` (link desabilitado).

---

### US-BEH-13: Excluir relatório

**Rota:** `POST /comportamento/relatorios/<uuid>/deletar/`

**Critérios de aceitação:**
1. Busca `file_url` no banco → deleta arquivo do Storage → deleta registro do banco.
2. Suporta HTMX (HX-Refresh) e form nativo.
3. Falha na exclusão do Storage é logada mas não bloqueia a exclusão do registro.

---

## 7. Módulo Library — Biblioteca de Crises

### US-LIB-01: Visualizar grid de conteúdos

**Rota:** `GET /biblioteca/`

**Pré-requisitos:** Autenticado + `@library_access_required`

**Critérios de aceitação:**
1. Conteúdos agrupados por categoria.
2. Apenas conteúdos publicados (`is_published = True`).
3. Ordenação: `category` → `created_at`.

**Categorias e metadados:**

| Categoria    | Label              | Emoji | Cor   |
| ------------ | ------------------ | ----- | ----- |
| Crise        | Manejo de Crises   | 🚨    | red   |
| Autocuidado  | Autocuidado        | 💙    | blue  |
| Comunicacao  | Comunicação        | 💬    | green |

---

### US-LIB-02: Visualizar detalhe de conteúdo

**Rota:** `GET /biblioteca/<slug>/`

**Critérios de aceitação:**
1. Busca conteúdo por `slug` + `is_published = True`.
2. Conteúdo não encontrado → redireciona para home da biblioteca.
3. Suporta embed de YouTube (parsing de URLs youtu.be, youtube.com/watch, youtube.com/embed).

---

## 8. Regras de Autorização Transversais

### Decorators de Proteção

| Decorator                  | Verifica                                          | Redirect se falha              |
| -------------------------- | ------------------------------------------------- | ------------------------------ |
| `@supabase_login_required` | `request.supabase_user` existe                    | `/accounts/login/?next=<path>` |
| `@subscription_required`   | `subscription_status` ∈ `{active, trialing}`      | `/dashboard/?upgrade=true`     |
| `@generator_access_required` | `has_generator_access = True`                   | `/dashboard/?upgrade=generator` |
| `@library_access_required` | `has_library_access = True`                       | `/dashboard/?upgrade=library`  |

**Hierarquia de verificação:** Todos os decorators verificam `supabase_user` primeiro (redundância com `@supabase_login_required` para segurança em profundidade).

### Isolamento de Dados (Multi-tenancy)

**Regra fundamental:** Toda operação de leitura/escrita inclui filtro `child_id` ou `parent_id`:
- Registros ABC: `behavior_logs.child_id`
- Habilidades: `skills.child_id`
- Rotinas: `routines.child_id`
- Filhos: `children.parent_id`

**Regra de "primeiro filho":** Todas as views usam `children[0]` — apenas o primeiro filho é considerado.

> **[DÉBITO] AUTH-01:** As queries usam `service_role` (admin) para tudo (`_admin()` client), o que bypassa RLS do Supabase. A segurança de isolamento depende **exclusivamente** dos filtros no código Python, não das policies RLS. Se uma view esquecesse o filtro `child_id`, dados de outros usuários poderiam ser expostos.

---

## 9. Débitos Técnicos e Inconsistências

### Resumo Consolidado

| ID             | Severidade | Descrição                                                                                          |
| -------------- | ---------- | -------------------------------------------------------------------------------------------------- |
| ACC-01a        | Baixa      | Sem validação de formato de e-mail no backend                                                     |
| ACC-01b        | Baixa      | Sem campo de confirmação de senha no signup                                                       |
| ACC-03a        | Média      | Fallback de fragment OAuth (workaround JS para flow implícito)                                    |
| ACC-MIDW-01    | Alta       | Novo client Supabase criado por requisição (sem pool/cache)                                       |
| ACC-MIDW-02    | Alta       | Query `profiles.select('*')` em TODA requisição autenticada (sem cache)                           |
| CORE-02a       | Baixa      | `date_of_birth` sem validação de formato                                                          |
| CORE-02b       | Média      | Sistema assume sempre 1 filho (sem suporte multi-filho na UI)                                     |
| PAY-02a        | Alta       | Race condition: provision síncrono seta `trialing`, webhook seta `active` para Monitor            |
| PAY-03a        | Baixa      | Cálculo de `days_left` timezone-unaware                                                           |
| ROT-03a        | Baixa      | Endpoints HTMX legados coexistem com batch save (código potencialmente morto)                     |
| ROT-04a        | Baixa      | Título vazio silenciosamente ignorado (sem feedback)                                              |
| ROT-06a        | Baixa      | Filename de PDF sem sanitização completa                                                          |
| BEH-04a        | Média      | Data Healing em runtime para corrigir arrays JSONB corrompidos                                    |
| BEH-05a        | Baixa      | Default de `days` inconsistente (30 no except vs 7 na validação)                                  |
| BEH-11a        | Média      | Upload de relatório ignora erros silenciosamente                                                  |
| AUTH-01         | **Crítica**| `service_role` usado para TODAS as queries, bypassa RLS. Segurança depende 100% do código Python  |

### Inconsistências de Schema (Wiki vs Código)

| Aspecto             | Wiki/Schema Planejado           | Implementação Real                    |
| ------------------- | ------------------------------- | ------------------------------------- |
| Tabela de skills    | `skill_tracker` com `skill_name` | Dividida em `skills` + `skill_logs`  |
| Status de skill     | `not_started`, `in_progress`, `mastered` | `active`, `mastered`, `archived`  |
| `exported_reports.report_type` | "Semanal, Mensal, Evolutivo" | "Relatório para consultas médicas", "Relatório para acompanhamento escolar", "Visão geral" |
| `exported_reports.date_range` | JSONB `{start, end}` | String "DD/MM/YYYY à DD/MM/YYYY" |
| `exported_reports.ai_summary` | Text (resumo IA) | **Não implementado** — campo ausente |
| `children.diagnostico_data` | Date | **Não usado** no código |
| `children.metadados` | JSONB (alergias, hiperfocos) | **Não usado** no código |
| `pictograms.owner_id` | FK → profiles (para uploads privados) | **Não implementado** — apenas `is_public` |
| `routines.is_template` | Boolean | **Não usado** no código |
| `routine_items.time_alert` | Time (notificações) | **Não implementado** |
| Campo de coluna de order | `position` (original) | `order` (palavra reservada SQL — requer aspas duplas) |
| `library_contents.required_access_level` | Controle granular | **Não implementado** — acesso binário via `has_library_access` |

---

*Documento gerado automaticamente via Repo Research Skill — Fase 4 (Targeted Deep Dive em regras de negócio).*
