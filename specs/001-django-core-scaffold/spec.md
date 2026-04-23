# Feature Specification: Django Core Scaffold

**Feature Branch**: `001-django-core-scaffold`  
**Created**: 2026-04-23  
**Status**: Draft  
**Input**: User description: "Configure o esqueleto base da aplicação incluindo Django 5, Docker, integração com SDK Supabase via MCP e templates base para HTMX/Alpine.js, seguindo estritamente a Constitution"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ambiente Django Estruturado (Priority: P1)

Como desenvolvedor, quero um projeto Django 5.x com a estrutura de pastas definida pela Constitution para poder implementar features sem violar os princípios de arquitetura desde o primeiro commit.

**Why this priority**: Sem a estrutura base correta (`src/`, `apps/`, `services.py`, `templates/partials/`), todo código subsequente corre risco de acumular débito técnico e violar a Clean Architecture.

**Independent Test**: Um novo desenvolvedor clona o repositório e encontra a estrutura `src/config/`, `src/apps/`, `src/templates/` e `src/static/` já criadas, com `manage.py` funcional.

**Acceptance Scenarios**:

1. **Given** o repositório clonado, **When** o desenvolvedor executa `python src/manage.py check`, **Then** o Django valida a configuração sem erros críticos.
2. **Given** o projeto inicializado, **When** o desenvolvedor cria um novo app em `src/apps/`, **Then** o app já contém o arquivo `services.py` vazio e a pasta `templates/<app_name>/partials/`.

---

### User Story 2 - Containerização com Paridade DEV/PRD (Priority: P1)

Como desenvolvedor, quero rodar a aplicação via Docker Compose para garantir que o ambiente local seja idêntico ao de produção, eliminando "funciona na minha máquina".

**Why this priority**: A Constitution exige Docker como infraestrutura imutável para paridade absoluta entre DEV e PRD.

**Independent Test**: `docker-compose up --build` sobe a aplicação acessível em `http://localhost:8000` sem necessidade de instalar Python localmente.

**Acceptance Scenarios**:

1. **Given** Docker e Docker Compose instalados, **When** o desenvolvedor executa `docker-compose up --build`, **Then** o container sobe sem erros e expõe a porta 8000.
2. **Given** o container rodando, **When** o desenvolvedor altera arquivos no host, **Then** o hot-reload do Django reflete as mudanças sem rebuild.

---

### User Story 3 - Integração Supabase com RLS-First (Priority: P2)

Como desenvolvedor, quero o cliente `supabase-py` configurado e uma camada de serviço pronta para que todas as queries em dados de pacientes respeitem o RLS desde o início.

**Why this priority**: A Constitution proíbe o uso do ORM Django para dados core de pacientes e exige RLS-First. É mais barato construir isso no skeleton do que refatorar depois.

**Independent Test**: Um teste de integração conecta ao Supabase, insere um registro de teste filtrado por `parent_id`, e valida que o UUID foi serializado como string antes da operação.

**Acceptance Scenarios**:

1. **Given** as variáveis `SUPABASE_URL` e `SUPABASE_KEY` configuradas no `.env`, **When** a aplicação inicia, **Then** o cliente Supabase está disponível globalmente via service layer.
2. **Given** uma operação de escrita em dados de pacientes, **When** o service executa a query, **Then** o log de auditoria contém `user_id`, `action` e `timestamp`.

---

### User Story 4 - Templates Base Anti-SPA e Offline-First (Priority: P2)

Como desenvolvedor, quero templates base HTMX + Alpine.js configurados para que novas features entreguem fragmentos HTML parciais e persistam estado local automaticamente.

**Why this priority**: A Constitution proíbe frameworks SPA e exige Offline-First via LocalStorage. O template base precisa carregar HTMX, Alpine.js e Tailwind CSS corretamente.

**Independent Test**: Acessar a página base exibe um layout mobile-first funcional; desconectar a internet e registrar um dado ABC mantém o estado em LocalStorage até reconexão.

**Acceptance Scenarios**:

1. **Given** o template `base.html` renderizado, **When** o usuário interage com um botão de ação primária, **Then** a área de toque é ≥ 48×48 dp e o contraste é ≥ 4.5:1.
2. **Given** o navegador offline, **When** o cuidador registra um comportamento ABC, **Then** o estado é persistido em LocalStorage e exibe indicador "pendente".

---

### Edge Cases

- **Falta de variáveis de ambiente**: A aplicação deve falhar gracefulmente com mensagem clara indicando qual variável está ausente (ex: `SUPABASE_URL` não configurada).
- **Porta 8000 ocupada**: `docker-compose.yml` deve permitir override via variável de ambiente ou usar porta dinâmica.
- **Supabase indisponível no setup inicial**: A aplicação deve iniciar mesmo sem conectividade, permitindo desenvolvimento offline; a camada de serviço deve lidar com timeout e retry.
- **Primeiro app sem `services.py`**: O scaffold deve incluir um app de exemplo (`core` ou `system`) com `services.py`, `views.py`, `urls.py` e partials preenchidos como referência.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Sistema DEVE ter estrutura de diretórios `src/` contendo `manage.py`, `config/`, `apps/`, `templates/` e `static/`.
- **FR-002**: Sistema DEVE usar Django 5.x como framework backend.
- **FR-003**: Sistema DEVE conter `Dockerfile` e `docker-compose.yml` funcionais na raiz do repositório.
- **FR-004**: Sistema DEVE conter `requirements.txt` com todas as dependências da stack (Django, django-htmx, supabase-py, stripe, tailwindcss integração, etc.). A integração do Supabase via MCP (Model Context Protocol) deve estar configurada desde o início; a integração do Stripe via MCP será adicionada em momento posterior, após o planejamento.
- **FR-005**: Sistema DEVE conter `.env.example` documentando todas as variáveis obrigatórias.
- **FR-006**: Sistema DEVE ter configuração de conexão Supabase via `supabase-py` isolada em `services.py`.
- **FR-007**: Sistema DEVE ter template base `base.html` carregando HTMX, Alpine.js e Tailwind CSS.
- **FR-008**: Sistema DEVE ter diretório `templates/partials/` e convenção `_partial.html` para fragmentos HTMX.
- **FR-009**: Sistema DEVE proibir o uso do ORM Django para dados core de pacientes; `services.py` deve usar `supabase-py`.
- **FR-010**: Sistema DEVE garantir que UUIDs sejam convertidos para `str(uuid)` antes de operações no SDK Supabase.
- **FR-011**: Sistema DEVE ter um app de exemplo (`core`) contendo `services.py`, `views.py`, `urls.py` e partials como referência de implementação.
- **FR-012**: Sistema DEVE ter settings configuradas para `django-htmx` e com separação obrigatória por ambiente (`dev` e `prd`), garantindo que a arquitetura nasça pronta para ambos os ambientes desde o primeiro commit.
- **FR-013**: Sistema DEVE ter infraestrutura de logging configurada nativamente desde o início, com suporte a níveis (DEBUG, INFO, WARNING, ERROR) e saída estruturada para auditoria e observabilidade.

### Key Entities

- **Configuração do Projeto**: Settings do Django, variáveis de ambiente, conexão Supabase.
- **App Core**: App Django de referência demonstrando Service Layer, views mínimas e partials HTMX.
- **Integrações MCP**: O Supabase está configurado via MCP (Model Context Protocol) desde o início. O Stripe será integrado via MCP em momento posterior; a arquitetura deve nascer preparada para receber essa integração sem retrabalho estrutural.

## Constraints & Non-Negotiables *(mandatory)*

- **UX Fricção Zero**: Nenhuma ação primária pode exceder 5 segundos ou usar `<select>` para inputs frequentes. Área de toque mínima: 48×48 dp.
- **Anti-SPA**: Proibido uso de React, Vue, Angular ou Svelte. Interatividade via HTMX + Alpine.js apenas.
- **Service Layer**: Toda lógica de negócio reside em `services.py`; views apenas validam input e retornam response.
- **Anti-ORM (dados core)**: Dados de pacientes usam `supabase-py`; ORM do Django é proibido para esses dados.
- **RLS-First**: Toda query em dados de pacientes filtra por `parent_id`; UUIDs serializados como `str(uuid)` antes do SDK Supabase.
- **Offline-First**: Ações de registro DEVEM persistir em LocalStorage e sincronizar quando online; conflitos usam last-write-wins.
- **Type Hinting**: Todo código Python DEVE usar type hints estritos.
- **Lock-in por utilidade**: Nenhuma feature pode dificultar entrada ou exportação de dados do usuário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um novo desenvolvedor consegue executar `docker-compose up --build` e acessar a aplicação em menos de 5 minutos após clonar o repositório.
- **SC-002**: Todos os 5 princípios da Constitution são verificáveis no código base (checklist de conformidade passa em 100% dos itens).
- **SC-003**: Nenhum framework SPA (React, Vue, Angular, Svelte) está presente no `requirements.txt`, `package.json` ou templates.
- **SC-004**: Templates base permitem que um registro ABC seja iniciado em menos de 3 segundos (preparado para a Regra dos 5 Segundos).
- **SC-005**: A aplicação inicia com sucesso mesmo quando o Supabase está temporariamente indisponível, exibindo estado offline claro.

## Assumptions

- Docker e Docker Compose estão instalados no ambiente de desenvolvimento.
- Python 3.12+ está disponível no host ou no container base.
- O desenvolvedor terá acesso às credenciais do projeto Supabase para configurar o `.env`.
- Tailwind CSS será integrado via CDN inicialmente; reavaliação de pipeline de build será feita em momento futuro.

## Clarifications

### Session 2026-04-23

- **Q1**: O que significa "MCP" no contexto da integração Supabase? → **A**: MCP significa Model Context Protocol. Será usado tanto no Supabase quanto no Stripe. No momento apenas o Supabase está configurado na lista de MCP; o Stripe será adicionado em outro momento, depois do planejamento.
- **Q2**: A arquitetura deve suportar apenas um ambiente ou múltiplos (dev/prod)? → **A**: A arquitetura deve nascer pronta para ambos os ambientes (dev e prd).
- **Q3**: Tailwind CSS deve ser integrado via CDN ou build step? → **A**: Via CDN inicialmente; reavaliar no futuro.
- **Q4**: Qual a melhor forma de lidar com a integração Stripe via MCP? → **A**: O Stripe usará MCP (Model Context Protocol). A arquitetura deve nascer preparada para receber essa integração sem retrabalho estrutural.
- **Q5**: Devemos configurar logging nativo desde o início? → **A**: Sim. Configurar log para dar suporte nativo à aplicação desde o início, com níveis e saída estruturada.

