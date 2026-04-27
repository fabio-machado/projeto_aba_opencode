# Feature Specification: Auth Login Screen (Magic Link Flow)

**Feature Branch**: `004-auth-login-magic-link`  
**Created**: 2026-04-27  
**Status**: Draft  
**Input**: User description: "Spec: Auth Login Screen (Magic Link Flow) - Implementar camada de entrada (Login) para Web App focado em pais e cuidadores, utilizando Magic Link via Supabase Auth. Sem criação manual de conta; usuário já deve existir no banco (criado via webhook do Stripe)."

## Clarifications

### Session 2026-04-27

- Q: Qual o escopo de observabilidade para tentativas de login? → A: Logging de todas as tentativas (sucesso/falha/razão) + métricas agregadas, sem alertas automáticos no MVP.
- Q: O que ocorre com a sessão ativa de um usuário cuja assinatura é cancelada? → A: Invalidar a sessão imediatamente ao detectar cancelamento, forçando reautenticação que será recusada por conta inativa.
- Q: A tela de login deve incluir aviso de privacidade conforme LGPD? → A: Sim — texto resumido com link para a Política de Privacidade (ex: "Seus dados são protegidos conforme nossa Política de Privacidade").
- Q: Qual o tempo de expiração do Magic Link se não clicado? → A: 1 hora (padrão Supabase OTP).
- Q: A tela de login deve atender requisitos de acessibilidade? → A: Sim — WCAG 2.1 Nível AA mínimo (contraste, labels semânticos, navegação por teclado, foco visível).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acesso via Magic Link (Priority: P1)

Um pai/cuidador que já adquiriu o produto (conta criada via Stripe) deseja acessar o aplicativo. Ele informa seu e-mail de compra, recebe um link mágico no e-mail e clica para entrar.

**Why this priority**: É o fluxo principal e obrigatório de entrada no sistema. Sem ele, nenhum usuário consegue acessar a aplicação. Representa o MVP da feature.

**Independent Test**: Pode ser testado isoladamente fornecendo um e-mail válido de um usuário pagante, confirmando o recebimento do Magic Link e verificando o acesso à área restrita após o clique.

**Acceptance Scenarios**:

1. **Given** um usuário pagante com conta existente no sistema, **When** ele informa seu e-mail e clica em "Receber Acesso", **Then** o sistema envia um Magic Link para o e-mail informado e exibe a mensagem "Link enviado! Verifique sua caixa de entrada e spam."
2. **Given** um usuário que recebeu o Magic Link no e-mail, **When** ele clica no link, **Then** ele é redirecionado para a área restrita do aplicativo com uma sessão ativa e autenticada.
3. **Given** um e-mail válido digitado, **When** o usuário submete o formulário, **Then** o sistema inicia o envio em até 5 segundos, respeitando o princípio de UX Fricção Zero.

---

### User Story 2 - Rejeição de E-mail Não Cadastrado (Priority: P1)

Um usuário tenta fazer login com um e-mail que não está associado a nenhuma conta pagante ativa. O sistema deve rejeitar com uma mensagem amigável, evitando disparar Magic Links indevidos.

**Why this priority**: Segurança e experiência do usuário — evita envio de links para e-mails não autorizados e orienta o usuário sobre o motivo da rejeição. Tão crítico quanto o fluxo de sucesso.

**Independent Test**: Pode ser testado submetendo um e-mail que não consta na base de usuários pagantes e verificando se o sistema retorna mensagem de erro sem disparar Magic Link.

**Acceptance Scenarios**:

1. **Given** um e-mail que não existe na base de usuários pagantes, **When** o usuário submete o formulário, **Then** o sistema exibe a mensagem "E-mail não encontrado. Certifique-se de usar o mesmo e-mail utilizado na compra." e NÃO envia Magic Link.
2. **Given** um e-mail válido em formato mas com conta inativa/cancelada, **When** o usuário tenta login, **Then** o sistema exibe mensagem informando que o acesso não está disponível.

---

### User Story 3 - Persistência de Sessão (Priority: P2)

Após autenticar via Magic Link, o usuário permanece logado por um período prolongado sem precisar repetir o fluxo de e-mail frequentemente.

**Why this priority**: Essencial para usabilidade e retenção. Sem isso, o usuário precisaria solicitar novo Magic Link a cada acesso, gerando fricção excessiva. Porém, o fluxo de login (P1) funciona sem este refinamento.

**Independent Test**: Pode ser testado realizando login, fechando o navegador, reabrindo após 24h e verificando se a sessão ainda está ativa sem necessidade de novo login.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado, **When** ele fecha e reabre o navegador em um intervalo menor que 90 dias, **Then** ele permanece autenticado e acessa diretamente a área restrita.
2. **Given** um usuário autenticado cuja sessão está prestes a expirar, **When** o sistema detecta a proximidade da expiração, **Then** a sessão é renovada automaticamente via refresh token sem ação do usuário.

---

### User Story 4 - Proteção de Rotas (Priority: P2)

Qualquer tentativa de acessar páginas internas do aplicativo sem uma sessão ativa resulta em redirecionamento para a tela de login.

**Why this priority**: Essencial para segurança, mas depende do fluxo de login (P1) estar funcional. Pode ser implementado como camada de middleware/guarda de rota.

**Independent Test**: Pode ser testado tentando acessar uma URL interna da aplicação em um navegador sem sessão ativa e verificando o redirecionamento para a tela de login.

**Acceptance Scenarios**:

1. **Given** um visitante sem sessão ativa, **When** ele tenta acessar qualquer rota interna da aplicação, **Then** ele é redirecionado automaticamente para a tela de login.
2. **Given** um usuário com sessão ativa, **When** ele acessa qualquer rota interna, **Then** a página é exibida normalmente sem redirecionamento.
3. **Given** um usuário com sessão expirada, **When** ele tenta acessar uma rota interna, **Then** ele é redirecionado para a tela de login.

---

### User Story 5 - Proteção contra Abuso e Enumeração (Priority: P3)

O sistema protege contra abuso limitando solicitações de Magic Link tanto por e-mail quanto por IP, e detecta padrões de enumeração — tentativas de testar múltiplos e-mails diferentes para descobrir quais estão cadastrados.

**Why this priority**: Previne spam, força bruta e ataques de enumeração contra o sistema de Magic Link. Embora não bloqueie o funcionamento básico, é uma camada crítica de segurança para evitar vazamento de dados de usuários e abuso do serviço de e-mail.

**Independent Test**: Pode ser testado submetendo o mesmo e-mail repetidamente, bem como alternando vários e-mails diferentes a partir do mesmo IP, e verificando o bloqueio em ambos os cenários.

**Acceptance Scenarios**:

1. **Given** um usuário que solicitou Magic Link recentemente para um e-mail específico, **When** ele tenta solicitar novamente para o mesmo e-mail em menos de 60 segundos, **Then** o sistema exibe uma mensagem informando para aguardar antes de uma nova tentativa.
2. **Given** um mesmo IP que realizou múltiplas solicitações de Magic Link em um curto intervalo (independentemente dos e-mails), **When** o limite de tentativas por IP é excedido, **Then** o sistema bloqueia novas solicitações desse IP temporariamente e exibe mensagem genérica de erro, sem revelar se o e-mail existe ou não.
3. **Given** um atacante tentando enumerar e-mails variados a partir do mesmo IP, **When** o sistema detecta um padrão de tentativas com múltiplos e-mails inexistentes em sequência, **Then** o sistema bloqueia o IP e registra o evento para monitoramento de segurança.

---

### Edge Cases

- O que acontece quando o Magic Link expira antes de o usuário clicar (após 1 hora)? O sistema deve permitir que o usuário solicite um novo Magic Link normalmente, sem bloqueios adicionais.
- Como o sistema lida com e-mails digitados com espaços em branco ou maiúsculas/minúsculas inconsistentes? O e-mail deve ser normalizado (trim e lowercase) antes da validação.
- O que acontece se o serviço de envio de e-mail estiver indisponível? O sistema deve exibir uma mensagem de erro genérica e orientar o usuário a tentar novamente mais tarde, sem expor detalhes técnicos.
- Como o sistema trata um Magic Link que foi utilizado mais de uma vez? O link deve ser de uso único e expirar após o primeiro uso bem-sucedido.
- O que ocorre quando um usuário tenta acessar a tela de login já estando autenticado? O sistema deve redirecioná-lo diretamente para a área restrita.
- Como o sistema responde a um ataque de enumeração (vários e-mails diferentes de um mesmo IP)? O sistema deve detectar o padrão, bloquear o IP e jamais revelar se um e-mail específico existe ou não durante o bloqueio.
- O que acontece com um usuário autenticado cuja assinatura é cancelada enquanto está logado? Sua sessão deve ser invalidada imediatamente; ao tentar qualquer ação protegida, ele é redirecionado para login onde receberá a mensagem de conta inativa.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE exibir uma tela de login com um campo único para entrada de e-mail, botão de ação ("Receber Acesso"), texto instrucional sobre Magic Link, seção de suporte com informações de contato, e aviso resumido de privacidade com link para a Política de Privacidade ("Seus dados são protegidos conforme nossa Política de Privacidade").
- **FR-002**: O sistema DEVE validar o formato do e-mail (presença de "@" e domínio válido) antes de submeter a solicitação.
- **FR-003**: O sistema DEVE normalizar o e-mail (remover espaços, converter para minúsculas) antes de qualquer processamento.
- **FR-004**: O sistema DEVE verificar se o e-mail informado pertence a um usuário pagante ativo na base de dados antes de disparar o Magic Link.
- **FR-005**: O sistema DEVE exibir a mensagem "E-mail não encontrado. Certifique-se de usar o mesmo e-mail utilizado na compra." quando o e-mail não corresponder a um usuário pagante ativo.
- **FR-006**: O sistema DEVE exibir a mensagem "Link enviado! Verifique sua caixa de entrada e spam." após o envio bem-sucedido do Magic Link.
- **FR-007**: O sistema DEVE substituir o formulário de login pela mensagem de confirmação após o envio bem-sucedido do Magic Link.
- **FR-008**: O sistema DEVE disparar o Magic Link de autenticação para o e-mail validado, com redirecionamento automático para a área restrita da aplicação após o clique.
- **FR-009**: O sistema DEVE configurar sessões de longa duração (90 dias) com renovação automática via refresh tokens.
- **FR-010**: O sistema DEVE proteger todas as rotas internas da aplicação, redirecionando para a tela de login qualquer requisição sem sessão ativa.
- **FR-011**: O sistema DEVE limitar as solicitações de Magic Link por e-mail (máximo 3 tentativas por e-mail em 60 segundos) e por IP (máximo 10 tentativas por IP em 60 segundos, independentemente dos e-mails informados).
- **FR-012**: O sistema DEVE informar ao usuário que "Enviaremos um link de acesso para o seu e-mail. Não é necessário senha." em texto descritivo visível.
- **FR-013**: O sistema DEVE exibir o formulário de login como rota pública, acessível sem autenticação.
- **FR-014**: O sistema DEVE redirecionar usuários já autenticados para a área restrita caso acessem a tela de login.
- **FR-015**: O sistema DEVE detectar padrões de enumeração (múltiplos e-mails inexistentes a partir do mesmo IP em curto intervalo) e, ao identificar o padrão, bloquear o IP e registrar o evento de segurança.
- **FR-016**: O sistema DEVE registrar em log toda tentativa de login, incluindo: e-mail normalizado, IP de origem, timestamp, resultado (sucesso/falha) e razão da falha quando aplicável (e-mail não encontrado, conta inativa, rate limit, erro de envio).
- **FR-017**: O sistema DEVE invalidar a sessão ativa de um usuário imediatamente quando sua conta for marcada como inativa ou cancelada (via atualização proveniente do webhook Stripe), forçando reautenticação na próxima requisição.
- **FR-018**: O sistema DEVE configurar o Magic Link para expirar em 1 hora caso não seja clicado (tempo de vida padrão do OTP).
- **FR-019**: A tela de login DEVE atender aos critérios WCAG 2.1 Nível AA, incluindo: labels semânticos para leitores de tela, navegação completa por teclado com foco visível, e contraste mínimo de 4.5:1 entre texto e fundo.

### Key Entities *(include if feature involves data)*

- **Sessão de Usuário**: Representa o estado autenticado de um usuário. Atributos relevantes: data de criação, data de expiração (90 dias), token de acesso, token de renovação (refresh token), estado (ativa/expirada).
- **Usuário Pagante**: Representa um pai/cuidador que adquiriu o produto. Atributos relevantes: e-mail (identificador único para login), status da conta (ativo/inativo), data de criação (via webhook Stripe).
- **Tentativa de Login**: Registro de solicitação de Magic Link para controle de rate limiting, detecção de enumeração e observabilidade. Atributos relevantes: e-mail normalizado, endereço IP de origem, timestamp da tentativa, resultado (sucesso/recusado), razão da recusa (e-mail não encontrado, conta inativa, rate limit por e-mail, rate limit por IP, enumeração detectada, erro de envio).

## Constraints & Non-Negotiables *(mandatory)*

- **UX Fricção Zero**: Nenhuma ação primária pode exceder 5 segundos ou usar `<select>` para inputs frequentes. Área de toque mínima: 48×48 dp.
- **Anti-SPA**: Proibido uso de React, Vue, Angular ou Svelte. Interatividade via HTMX + Alpine.js apenas.
- **Service Layer**: Toda lógica de negócio reside em `services.py`; views apenas validam input e retornam response.
- **Type Hinting**: Todo código Python DEVE usar type hints estritos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário pagante consegue completar o fluxo de login (informar e-mail → clicar no Magic Link → acessar área restrita) em menos de 60 segundos.
- **SC-002**: 95% dos usuários com conta ativa conseguem autenticar com sucesso na primeira tentativa.
- **SC-003**: O tempo entre submeter o e-mail e o Magic Link chegar na caixa de entrada não ultrapassa 10 segundos em 90% dos casos.
- **SC-004**: Usuários permanecem autenticados por pelo menos 30 dias consecutivos sem necessidade de reautenticação em uso regular.
- **SC-005**: Zero tickets de suporte relacionados a "não sei como fazer login" ou "não recebi o link" por falha sistêmica (excluindo erros de digitação de e-mail pelo usuário).
- **SC-006**: Nenhum Magic Link é enviado para e-mails não cadastrados como pagantes ativos (taxa de falsos positivos = 0%).
- **SC-007**: Ataques de enumeração com 5 ou mais e-mails distintos a partir do mesmo IP em 60 segundos são detectados e bloqueados automaticamente em 100% dos casos.
- **SC-008**: A tela de login atinge pontuação 100% em ferramenta de auditoria automática de acessibilidade (ex: Lighthouse Accessibility) para critérios WCAG 2.1 Nível AA.

## Assumptions

- O webhook do Stripe (Feature 003) já cria e mantém os registros de usuários pagantes na base de dados. Esta feature apenas consulta esses registros.
- O serviço de envio de e-mail (provedor do Magic Link) é o próprio Supabase Auth, com disponibilidade e entrega assumidas como externas.
- O endereço de contato de suporte será configurado como variável de ambiente e exibido no rodapé da tela de login (ex: e-mail de suporte do produto).
- A rota de destino após autenticação bem-sucedida (`redirectTo`) será a página inicial da área restrita da aplicação (ex: `/app`).
- A tela de login é uma página pública, renderizada pelo servidor, sem dependência de JavaScript para renderização inicial (HTMX + Alpine.js para interatividade).
- O rate limiting (3 tentativas por e-mail, 10 tentativas por IP a cada 60 segundos) e a detecção de enumeração são implementações iniciais; os limiares podem ser ajustados com base em dados de uso reais.
- Esta feature não contempla criação manual de conta, redefinição de senha, nem autenticação por senha — apenas Magic Link.
- A identidade visual (cores, tipografia, logotipo) já foi estabelecida pela feature 002 (App Shell & Identidade Visual) e serve como fundação para o design da tela de login. Os critérios WCAG 2.1 AA são uma camada adicional de acessibilidade sobre essa base.
