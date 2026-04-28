# Contract: POST /login/submit

**Feature**: Auth Login Screen (Magic Link Flow)
**Method**: POST
**Content-Type**: application/x-www-form-urlencoded (HTMX default)

## Request

### Body Parameters

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `email` | string | Yes | Formato de e-mail válido (contém `@` e domínio). Max 255 chars. |

### Headers

| Header | Value | Required |
|--------|-------|----------|
| `HX-Request` | `true` | Yes (indica submissão via HTMX) |
| `X-Forwarded-For` | string | No (IP real em produção com proxy) |

## Response

### Success (200 OK — Magic Link Enviado)

**Condição**: E-mail pertence a usuário pagante ativo + rate limits não excedidos + envio Supabase bem-sucedido.

```html
<!-- HTMX partial: substitui #login-form -->
<div id="login-form" role="status">
  <div class="rounded-2xl bg-green-50 p-6 text-center dark:bg-green-900/20">
    <p class="text-base font-medium text-green-800 dark:text-green-200">
      Link enviado! Verifique sua caixa de entrada e spam.
    </p>
    <p class="mt-2 text-sm text-green-600 dark:text-green-300">
      Se o e-mail não chegar em 2 minutos, você pode tentar novamente.
    </p>
  </div>
</div>
```

### Error — E-mail Não Encontrado (200 OK)

**Condição**: E-mail não existe em `profiles` ou `subscription_status` não é `active`/`trialing`.

```html
<!-- HTMX partial: insere mensagem de erro inline -->
<div id="login-form">
  <div id="login-error" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-300" role="alert">
    E-mail não encontrado. Certifique-se de usar o mesmo e-mail utilizado na compra.
  </div>
  <!-- ... form mantido para nova tentativa ... -->
</div>
```

### Error — Conta Inativa (200 OK)

**Condição**: E-mail existe mas `subscription_status` é `canceled` ou `past_due`.

```html
<div id="login-error" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-300" role="alert">
  Seu acesso não está disponível no momento. Entre em contato com o suporte.
</div>
```

### Error — Rate Limited (200 OK)

**Condição**: Limite de tentativas por e-mail (3/60s) ou por IP (10/60s) excedido.

```html
<div id="login-error" class="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-700 dark:bg-amber-900/20 dark:text-amber-300" role="alert">
  Muitas tentativas. Aguarde alguns instantes antes de tentar novamente.
</div>
```

### Error — Serviço Indisponível (200 OK)

**Condição**: Falha no Supabase Auth ao disparar Magic Link (erro de rede, timeout, API error).

```html
<div id="login-error" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-300" role="alert">
  Não foi possível enviar o link de acesso. Tente novamente mais tarde.
</div>
```

## Behavior Notes

- O formulário NÃO é recarregado via full page reload. A submissão usa `hx-post="/login/submit/" hx-target="#login-form" hx-swap="outerHTML"`.
- Em caso de erro, o formulário permanece visível para nova tentativa (apenas a mensagem de erro é inserida).
- Em caso de sucesso, o formulário inteiro é substituído pela mensagem de confirmação.
- O rate limiting é aplicado ANTES da consulta ao Supabase para evitar consumo desnecessário de recursos.
- O IP é extraído de `X-Forwarded-For` (produção) ou `REMOTE_ADDR` (dev).
- O e-mail é normalizado (trim, lowercase) antes de qualquer processamento.
