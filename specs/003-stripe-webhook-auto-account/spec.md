# Feature Specification: Stripe Webhook Auto Account

**Feature Branch**: `003-stripe-webhook-auto-account`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "Webhook Stripe Payments - A feature é um webhook handler do Stripe para criação de conta automática após pagamento. Os inputs são as requisições POST do Stripe no evento payment_intent.succeeded. O output é a criação de um novo usuário no banco de dados e retorno de sucesso para o Stripe. Devem ser tratados os casos de erro de validação da assinatura e idempotência"

## Clarifications

### Session 2026-04-26

- Q: Quando um payment_intent.succeeded é recebido para um email que já possui conta, qual deve ser o comportamento? → A: Retornar sucesso (200) sem criar nova conta nem modificar a existente (Option A).
- Q: Se o payment_intent.succeeded não contiver email do cliente, qual deve ser o comportamento? → A: Retornar erro (ex: 400) para o Stripe, registrando o evento como não processável sem retry (Option A).
- Q: Como o usuário deve fazer login na conta criada automaticamente pelo webhook? → A: Via magic link de login único enviado por email, com tokens de acesso de 90 dias no Supabase (banco + auth do app) (Option B customizado).
- Q: Quando um payment_intent.succeeded é recebido para um email que já possui conta, o sistema deve reenviar o magic link? → A: Reenviar apenas se o usuário não possuir sessão/token ativo (não logado recentemente) (Option B).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pagamento bem-sucedido cria conta automaticamente (Priority: P1)

Um novo cliente realiza um pagamento via Stripe. Assim que o pagamento é confirmado com sucesso, o sistema deve criar automaticamente uma conta para esse cliente sem necessidade de cadastro manual posterior.

**Why this priority**: Esse é o fluxo principal da feature. Sem ele, não há valor entregue — o webhook não teria propósito.

**Independent Test**: Pode ser testado enviando um evento simulado de `payment_intent.succeeded` para o endpoint do webhook e verificando se um novo usuário é criado no banco de dados.

**Acceptance Scenarios**:

1. **Given** que um pagamento foi processado com sucesso no Stripe, **When** o Stripe envia um webhook `payment_intent.succeeded` com assinatura válida e dados do cliente, **Then** o sistema cria um novo usuário no banco de dados e retorna HTTP 200 para o Stripe.
2. **Given** que um pagamento foi processado com sucesso no Stripe para um cliente que já possui conta com o mesmo email e não possui sessão ativa, **When** o webhook é recebido, **Then** o sistema não cria um usuário duplicado, reenvia um magic link de acesso e retorna HTTP 200.
3. **Given** que um pagamento foi processado com sucesso no Stripe para um cliente que já possui conta com o mesmo email e possui sessão ativa, **When** o webhook é recebido, **Then** o sistema não cria um usuário duplicado, não reenvia magic link e retorna HTTP 200.

---

### User Story 2 - Rejeição de webhooks com assinatura inválida (Priority: P1)

O sistema deve garantir que apenas webhooks legítimos do Stripe sejam processados, rejeitando requisições maliciosas ou acidentais.

**Why this priority**: Segurança é critica para um endpoint exposto publicamente. Sem validação de assinatura, o sistema está vulnerável a criação não autorizada de contas.

**Independent Test**: Pode ser testado enviando uma requisição POST para o endpoint do webhook com uma assinatura inválida ou ausente e verificando se o sistema retorna erro e não cria usuário.

**Acceptance Scenarios**:

1. **Given** que uma requisição POST é recebida no endpoint do webhook, **When** a assinatura do Stripe está ausente ou inválida, **Then** o sistema retorna HTTP 400 e não processa a criação de usuário.
2. **Given** que uma requisição POST é recebida com timestamp muito antigo na assinatura, **When** a validação de assinatura é executada, **Then** o sistema rejeita a requisição como potencial replay attack.

---

### User Story 3 - Garantia de idempotência no processamento (Priority: P2)

O Stripe pode enviar o mesmo evento de webhook múltiplas vezes (retries). O sistema deve garantir que o processamento duplicado não cause efeitos colaterais indesejados, como múltiplas contas para o mesmo pagamento.

**Why this priority**: Embora não bloqueie o lançamento, a falta de idempotência causa poluição de dados e experiência ruim. É um requisito de qualidade essencial para integrações com Stripe.

**Independent Test**: Pode ser testado enviando o mesmo evento `payment_intent.succeeded` (com mesmo ID de evento Stripe) duas vezes consecutivas e verificando que apenas um usuário é criado.

**Acceptance Scenarios**:

1. **Given** que um evento `payment_intent.succeeded` já foi processado com sucesso, **When** o Stripe reenvia o mesmo evento (mesmo `id` de evento), **Then** o sistema reconhece como duplicado, não cria novo usuário e retorna HTTP 200.
2. **Given** que o processamento de um webhook falhou parcialmente, **When** o Stripe reenvia o mesmo evento, **Then** o sistema deve tratar o retry de forma segura, sem criar dados inconsistentes.

---

### User Story 4 - Acesso à conta via magic link (Priority: P2)

Após a criação automática da conta, o usuário recebe um email com um magic link que permite acesso direto à plataforma sem necessidade de definir senha manualmente.

**Why this priority**: Completa a jornada do usuário desde o pagamento até o primeiro acesso. Sem isso, a conta existe mas o usuário não consegue utilizá-la.

**Independent Test**: Pode ser testado verificando se um email com magic link é enviado após a criação da conta e se o link permite login válido com token de 90 dias.

**Acceptance Scenarios**:

1. **Given** que um novo usuário foi criado automaticamente após pagamento, **When** o sistema processa a criação com sucesso, **Then** um email contendo magic link de acesso único é enviado para o email do usuário.
2. **Given** que o usuário recebeu o magic link por email, **When** clica no link dentro do prazo de validade, **Then** é autenticado automaticamente no sistema com um token de acesso válido por 90 dias.
3. **Given** que o magic link expirou ou já foi utilizado, **When** o usuário tenta acessar pelo link, **Then** o sistema solicita um novo magic link ou redireciona para fluxo de recuperação de acesso.

---

### Edge Cases

- Se o `payment_intent` não contiver email do cliente, o sistema DEVE retornar erro (ex: HTTP 400) para o Stripe, sem criar conta, para evitar retries de um evento que nunca será processável.
- Como o sistema lida com falhas temporárias no banco de dados durante a criação do usuário?
- O que ocorre se o Stripe enviar um evento com tipo diferente de `payment_intent.succeeded`?
- Como o sistema trata webhooks recebidos fora de ordem?
- O que acontece se a criação do usuário falhar após o webhook ter sido validado? O Stripe deve receber um erro (HTTP 500) para que faça retry.
- O que ocorre se o envio do email com magic link falhar após a criação do usuário? O sistema deve registrar o erro mas não deve expor falha ao Stripe (webhook já foi processado).
- Como o sistema trata um magic link que foi compartilhado ou acessado por outra pessoa?
- O que acontece quando o token de 90 dias expira? O usuário deve solicitar novo magic link.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor um endpoint HTTP POST capaz de receber webhooks do Stripe.
- **FR-002**: O sistema DEVE validar a assinatura do webhook utilizando o secret do Stripe antes de processar qualquer evento.
- **FR-003**: O sistema DEVE rejeitar webhooks com assinatura inválida, ausente ou expirada, retornando um erro apropriado.
- **FR-004**: O sistema DEVE processar exclusivamente eventos do tipo `payment_intent.succeeded`.
- **FR-005**: Ao processar um evento `payment_intent.succeeded` válido, o sistema DEVE criar um novo usuário no banco de dados com informações extraídas do pagamento. Se já existir um usuário com o mesmo email e ele não possuir sessão/token ativo, o sistema DEVE reenviar um magic link de acesso. Se já existir e possuir sessão ativa, o sistema DEVE retornar sucesso sem reenviar magic link.
- **FR-006**: O sistema DEVE garantir idempotência no processamento de eventos, utilizando o identificador único do evento Stripe para evitar processamento duplicado.
- **FR-007**: O sistema DEVE retornar HTTP 200 para o Stripe quando o evento for processado com sucesso ou for reconhecido como duplicado.
- **FR-008**: O sistema DEVE retornar um código de erro apropriado (ex: HTTP 400 ou 500) quando o processamento falhar, permitindo que o Stripe realize retries conforme sua política.
- **FR-009**: Se o evento `payment_intent.succeeded` não contiver email do cliente, o sistema DEVE retornar erro (HTTP 400) e não criar usuário, evitando retries para eventos incompletos.
- **FR-010**: Após criar um novo usuário com sucesso, o sistema DEVE enviar um email contendo um magic link de acesso único para o email do usuário.
- **FR-011**: O magic link DEVE autenticar o usuário automaticamente e gerar um token de acesso válido por 90 dias no Supabase (banco + auth do app).
- **FR-012**: O sistema DEVE mapear o produto/price do Stripe pago para as flags de acesso do funil (`has_generator_access` para Low Ticket, `has_library_access` para Upsell/Order Bump), garantindo que o modelo de receita seja refletido nos dados do usuário.
- **FR-013**: O sistema DEVE registrar logs de auditoria (Constitution IV) para toda operação de escrita em dados de usuários, incluindo `user_id`, `action` e `timestamp` na tabela `audit_logs`.
- **FR-014**: O sistema DEVE retornar HTTP 500 para o Stripe em caso de falhas temporárias no banco de dados durante a criação do usuário, permitindo retry automático.

### Key Entities *(include if feature involves data)*

- **Stripe Event**: Representa um evento enviado pelo Stripe via webhook. Contém atributos como `id` (identificador único do evento Stripe), `type` (tipo do evento, ex: `payment_intent.succeeded`) e `data.object` (dados do payment intent).
- **Payment Intent**: Representa a intenção de pagamento no Stripe. Contém informações sobre o pagamento, incluindo dados do cliente como email e nome.
- **Usuário**: Representa uma conta de usuário no sistema. É criado automaticamente após um pagamento bem-sucedido e contém atributos como email, nome e data de criação.
- **Magic Link**: Link de acesso único enviado por email que permite autenticação automática do usuário sem senha. Vinculado a um token de acesso com validade de 90 dias no Supabase.

## Constraints & Non-Negotiables *(mandatory)*

- **UX Fricção Zero**: Nenhuma ação primária pode exceder 5 segundos ou usar `<select>` para inputs frequentes. Área de toque mínima: 48×48 dp.
- **Anti-SPA**: Proibido uso de React, Vue, Angular ou Svelte. Interatividade via HTMX + Alpine.js apenas.
- **Service Layer**: Toda lógica de negócio reside em `services.py`; views apenas validam input e retornam response.
- **Anti-ORM (dados core)**: Dados de usuários (`profiles`, `processed_webhook_events`, `magic_link_logs`) usam `supabase-py`; ORM do Django é proibido para esses dados.
- **RLS-First**: Toda query em dados de usuários filtra por `id` (UUID do auth user); UUIDs serializados como `str(uuid)` antes do SDK Supabase.
- **Offline-First**: Ações de registro DEVEM persistir em LocalStorage e sincronizar quando online; conflitos usam last-write-wins.
- **Type Hinting**: Todo código Python DEVE usar type hints estritos.
- **Lock-in por utilidade**: Nenhuma feature pode dificultar entrada ou exportação de dados do usuário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos webhooks `payment_intent.succeeded` válidos resultam na criação de uma conta de usuário em até 3 segundos após o recebimento.
- **SC-002**: 100% dos webhooks com assinatura inválida são rejeitados sem criar ou modificar dados de usuário.
- **SC-003**: Taxa de zero (0%) de criação de contas duplicadas para o mesmo evento Stripe, mesmo em cenários de retry.
- **SC-004**: O sistema retorna resposta apropriada para o Stripe em 100% das requisições, mantendo a taxa de falhas silenciosas em zero.

## Assumptions

- O endpoint do webhook será expo publicamente na internet para receber callbacks do Stripe.
- Os dados mínimos necessários para criação de usuário (pelo menos email) estarão presentes no objeto `payment_intent` do Stripe.
- O Stripe está configurado para enviar eventos `payment_intent.succeeded` para o endpoint correto.
- O secret de validação de webhook do Stripe está disponível como variável de ambiente ou configuração segura.
- A lógica de criação de usuário reutiliza o serviço de autenticação/registro existente do sistema quando possível.
- O código da feature reside no Django app `payments` dentro de `src/apps/`, seguindo a Constitution do projeto (Service Layer em `services.py`, views finas, templates parciais HTMX em `templates/payments/partials/`).
