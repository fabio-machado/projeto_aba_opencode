# Overview da Operação: Autismo em Foco (v1.0.0)

Este documento estabelece as diretrizes técnico-comerciais não negociáveis para a aplicação **Autismo em Foco**. Ele deve ser utilizado pela IA como o oráculo de validação para todos os comandos `/speckit.plan`, `/speckit.tasks` e `/speckit.implement`[cite: 102, 453].

## I. Visão de Produto e Estratégia Direct Response
O sucesso deste SaaS depende da conversão rápida e retenção por utilidade extrema.
* **Modelo de Receita:** Estrutura de funil High-Velocity (Low Ticket -> Order Bump -> Core SaaS)[cite: 248].
* **Foco em LTV:** O acúmulo de dados de evolução do paciente é o mecanismo de *lock-in*. Nenhuma feature deve dificultar a entrada ou exportação de dados.
* **Objetivo:** Transformar registros caóticos em previsibilidade clínica para pais e cuidadores exaustos.

## II. UX "Fricção Zero": O Teste do Supermercado
A interface deve ser operável em cenários de alto estresse e fadiga cognitiva[cite: 124].
* **Single-Handed Operation:** Design otimizado para uso com apenas uma mão (Mobile First)[cite: 154].
* **Regra dos 5 Segundos:** Registros de comportamento (ABC) não podem exceder 5 segundos para conclusão.
* **Proibição de Dropdowns:** Use `Toggle Buttons` ou `Radio Buttons` grandes para inputs frequentes.
* **Offline-First:** O estado da aplicação deve persistir localmente via Alpine.js/Localstorage até que a sincronização via HTMX/Django seja possível.

## III. Stack Tecnológica e Arquitetura de Software
Fica proibido o uso de frameworks SPA complexos (React/Vue). A stack é focada em **SSR (Server Side Rendering) Dinâmico**[cite: 154].

| Camada | Tecnologia | Papel Estratégico |
| :--- | :--- | :--- |
| **Backend** | Django 5.x + django-htmx | Core lógico, Auth local e Segurança. |
| **Interação** | HTMX | Trocas parciais de HTML (Zero Full Page Reloads). |
| **Estado UI** | Alpine.js | Micro-interações, modais e estados locais efêmeros. |
| **Estilização** | Tailwind CSS | Design System utilitário e responsivo. |
| **Banco de Dados** | Supabase (Via MCP) | Fonte da verdade via PostgreSQL + RLS, Auth e Storage. |
| **Pagamentos** | Stripe | Gateway de pagamento. |
| **Infra** | Docker | Paridade absoluta entre DEV e PRD[cite: 313]. |

### Diretrizes de Engenharia (Clean Architecture)
Para evitar o débito técnico de "vibe coding", as seguintes regras são imutáveis[cite: 37, 38]:
1.  **Service Layer Pattern:** Toda lógica de negócio, integração com Stripe e chamadas ao Supabase DEVEM residir em `services.py` dentro de cada app. Views são proibidas de conter lógica complexa.
2.  **Anti-ORM:** O ORM do Django NÃO deve ser usado para dados core de pacientes. Use o cliente `supabase-py`.
3.  **Fragmentação de Templates:** Use arquivos HTML parciais (`_partial.html`) para retornos do HTMX, mantendo a semântica e reuso.
4.  **Type Hinting:** Todo código Python deve utilizar *type hints* estritos para garantir a integridade via análise estática.

## IV. Integridade, Segurança e Supabase SDK
A segurança é garantida no nível do banco (RLS), não apenas no código[cite: 12].
* **Serialização:** Todos os UUIDs vindos do frontend ou gerados internamente DEVEM ser convertidos para `str(uuid)` antes de qualquer operação no SDK do Supabase.
* **RLS-First:** Nenhuma query pode ser disparada sem o filtro explícito de `parent_id = auth.uid()` ou validação equivalente no backend.

## V. Estrutura de Projeto e Governança
- Todo código-fonte da aplicação (Django, templates, static files)
  DEVE residir dentro do diretório `src/`.
- A raiz do repositório é reservada para configurações de
  infraestrutura (`Dockerfile`, `docker-compose.yml`, `.env`,
  `requirements.txt`).
- Diretórios de tooling de IA (`.opencode/`, `.specify/`) e
  documentação de produto (`.aba_docs/`) NÃO DEVEM conter
  código da aplicação.
- Referência de layout:

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

* **Fluxo de Mudança:** Alterações nesta Constitution exigem incremento de versão (SemVer). Em caso de conflito, a Constitution anula qualquer plano de implementação[cite: 102].

