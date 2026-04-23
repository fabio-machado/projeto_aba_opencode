<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version Change: N/A → 1.0.0 (initial ratification)
Modified Principles: All 5 principles introduced from template placeholders
  - I. UX Fricção Zero
  - II. SSR Dinâmico (Anti-SPA)
  - III. Service Layer Pattern (Clean Architecture)
  - IV. RLS-First Security
  - V. Offline-First
Added Sections:
  - Stack Tecnológica e Restrições
  - Estrutura de Projeto e Governança
Removed Sections: None
Templates Requiring Updates:
  - ✅ .specify/templates/plan-template.md (Constitution Check gates aligned)
  - ✅ .specify/templates/spec-template.md (requirements alignment)
  - ✅ .specify/templates/tasks-template.md (principle-driven task types)
  - ⚠ .specify/templates/commands/*.md (verify no outdated agent references)
Follow-up TODOs:
  - TODO(RATIFICATION_DATE): data original de adoção não documentada; informar quando disponível
================================================================================
-->

# Autismo em Foco Constitution

## Core Principles

### I. UX Fricção Zero

A interface DEVE ser operável em cenários de alto estresse e fadiga cognitiva.
Todo design é validado pelo Teste do Supermercado: se um cuidador exausto,
segurando uma criança, não consegue completar a ação com uma mão em menos de
5 segundos, o design falhou.

- **Single-Handed Operation**: todo layout DEVE ser otimizado para uso com uma
  única mão (Mobile First).
- **Regra dos 5 Segundos**: registros de comportamento (ABC) NÃO PODEM exceder
  5 segundos para conclusão.
- **Proibição de Dropdowns**: inputs frequentes DEVEM usar Toggle Buttons ou
  Radio Buttons de tamanho grande. Elementos `<select>` são proibidos para
  ações primárias de registro.
- **Hierarquia Visual**: ações primárias DEVEM ter contraste mínimo de 4.5:1 e
  área de toque ≥ 48×48 dp.

### II. SSR Dinâmico (Anti-SPA)

Fica proibido o uso de frameworks SPA complexos (React, Vue, Angular, Svelte).
A stack é focada em Server-Side Rendering dinâmico com trocas parciais de HTML.

- Todo conteúdo dinâmico DEVE ser entregue via HTMX como fragmentos HTML
  parciais (`_partial.html`). Zero full-page reloads.
- Micro-interações e estados efêmeros de UI DEVEM usar Alpine.js.
- JavaScript customizado NÃO DEVE exceder 50 linhas por template/partial sem
  justificativa documentada.
- Estilização DEVE usar Tailwind CSS como design system utilitário.

### III. Service Layer Pattern (Clean Architecture)

Para evitar o débito técnico de "vibe coding", a separação de responsabilidades
é imutável.

- Toda lógica de negócio — incluindo integrações com Stripe e chamadas ao
  Supabase — DEVE residir em `services.py` dentro de cada app Django.
- Views são proibidas de conter lógica de negócio. Views DEVEM apenas: validar
  input, chamar services, e retornar response.
- **Anti-ORM**: o ORM do Django NÃO DEVE ser usado para dados core de pacientes.
  Use exclusivamente o cliente `supabase-py`.
- **Fragmentação de Templates**: retornos do HTMX DEVEM usar arquivos HTML
  parciais (`_partial.html`), mantendo semântica e reuso.
- **Type Hinting**: todo código Python DEVE utilizar type hints estritos para
  garantir integridade via análise estática.

### IV. RLS-First Security

A segurança é garantida no nível do banco de dados (Row Level Security), não
apenas no código da aplicação.

- **UUID Serialization**: todos os UUIDs vindos do frontend ou gerados
  internamente DEVEM ser convertidos para `str(uuid)` antes de qualquer
  operação no SDK do Supabase.
- **RLS Obrigatório**: nenhuma query pode ser disparada sem o filtro explícito
  de `parent_id = auth.uid()` ou validação equivalente no backend Django.
- **Dupla Validação**: inputs DEVEM ser validados tanto no frontend (Alpine.js)
  quanto no backend (Django forms/serializers) antes de alcançar o Supabase.
- **Auditabilidade**: operações de escrita em dados de pacientes DEVEM gerar
  log com `user_id`, `action`, e `timestamp`.

### V. Offline-First

O estado da aplicação DEVE ser resiliente a falhas de conectividade, priorizando
a experiência do cuidador em campo.

- O estado local da aplicação DEVE persistir via Alpine.js + LocalStorage até
  que a sincronização via HTMX/Django seja possível.
- Ações de registro (ABC) DEVEM ser armazenadas localmente e sincronizadas
  quando a conexão for restabelecida.
- A UI DEVE indicar claramente o estado de sincronização
  (online/offline/pendente) ao usuário.
- Conflitos de sincronização DEVEM seguir a política "last-write-wins" com log
  de conflitos para auditoria.

## Stack Tecnológica e Restrições

A stack tecnológica abaixo é imutável. Substituições exigem emenda formal à
Constitution com justificativa técnica documentada.

| Camada | Tecnologia | Papel Estratégico |
| :-------------- | :--------------------- | :--------------------------------------------- |
| Backend | Django 5.x + django-htmx | Core lógico, Auth local e Segurança |
| Interação | HTMX | Trocas parciais de HTML (Zero Full Page Reloads) |
| Estado UI | Alpine.js | Micro-interações, modais e estados efêmeros |
| Estilização | Tailwind CSS | Design System utilitário e responsivo |
| Banco de Dados | Supabase (PostgreSQL + RLS) | Fonte da verdade, Auth e Storage |
| Pagamentos | Stripe | Gateway de pagamento |
| Infra | Docker | Paridade absoluta entre DEV e PRD |

### Restrições Adicionais

- Frameworks SPA (React, Vue, Angular, Svelte) são proibidos.
- O ORM do Django NÃO DEVE ser usado para dados core de pacientes.
- Toda integração com serviços externos (Stripe, Supabase) DEVE estar isolada
  na service layer.
- O modelo de receita (Low Ticket → Order Bump → Core SaaS) DEVE ser refletido
  na modelagem de dados e nos fluxos de pagamento.
- Nenhuma feature DEVE dificultar a entrada ou exportação de dados do usuário
  (mecanismo de lock-in por utilidade, não por restrição).

## Estrutura de Projeto e Governança

Todo código-fonte da aplicação (Django, templates, static files) DEVE residir
dentro do diretório `src/`. A raiz do repositório é reservada para
configurações de infraestrutura.

```text
projeto_aba_opencode/
├── .opencode/        # Tooling de IA (skills, workflows)
├── .specify/         # Spec-driven development
├── .aba_docs/        # Documentação de produto/negócio
├── src/              # Código-fonte da aplicação Django
│   ├── manage.py
│   ├── config/       # Settings, URLs, WSGI/ASGI
│   ├── apps/         # Django apps (routines, payments, etc.)
│   ├── templates/    # Templates HTML
│   └── static/       # CSS, JS, imagens
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

### Regras de Estrutura

- Diretórios de tooling de IA (`.opencode/`, `.specify/`) e documentação de
  produto (`.aba_docs/`) NÃO DEVEM conter código da aplicação.
- Cada Django app DEVE conter: `services.py`, `urls.py`, `views.py`, e templates
  parciais em `templates/<app_name>/partials/`.
- Arquivos de configuração de infra (`Dockerfile`, `docker-compose.yml`, `.env`,
  `requirements.txt`) DEVEM residir na raiz do repositório.

## Governance

### Supremacia

Em caso de conflito entre esta Constitution e qualquer plano de implementação,
a Constitution prevalece incondicionalmente.

### Emendas

Alterações nesta Constitution exigem:

1. Justificativa técnica documentada.
2. Incremento de versão semântica (SemVer).
3. Atualização do Sync Impact Report no topo do arquivo.
4. Propagação de mudanças para todos os templates dependentes.

### Compliance Review

Todo PR/review DEVE verificar conformidade com os 5 princípios core antes de
aprovação.

### Guidance File

Use `.aba_docs/operation-overview.md` como referência operacional complementar
a esta Constitution.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): data original de adoção não documentada | **Last Amended**: 2026-04-23
