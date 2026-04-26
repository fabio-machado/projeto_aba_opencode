# Contract: Stripe Webhook Endpoint

**Feature**: Stripe Webhook Auto Account  
**Endpoint**: `POST /webhooks/stripe`  
**Version**: 1.0.0

## Overview

Public endpoint that receives Stripe webhook events. Validates signature, processes `payment_intent.succeeded` events, and creates user accounts automatically.

## Request

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Stripe-Signature` | Yes | Stripe webhook signature for verification |
| `Content-Type` | Yes | Must be `application/json` |

### Body

Stripe event object (JSON). Relevant fields for `payment_intent.succeeded`:

```json
{
  "id": "evt_1O...",
  "object": "event",
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "id": "pi_1O...",
      "object": "payment_intent",
      "status": "succeeded",
      "customer": "cus_1O...",
      "receipt_email": "user@example.com",
      "charges": {
        "data": [
          {
            "billing_details": {
              "name": "John Doe",
              "email": "user@example.com"
            }
          }
        ]
      }
    }
  }
}
```

### Required Fields

| Field | Path | Description |
|-------|------|-------------|
| `id` | `$.id` | Stripe event ID (for idempotency) |
| `type` | `$.type` | Must be `payment_intent.succeeded` |
| `receipt_email` or `charges.data[0].billing_details.email` | `$.data.object.receipt_email` | User email for account creation |

## Response

### Success (200 OK)

```json
{
  "status": "success",
  "message": "Webhook processed successfully"
}
```

Sent when:
- New user created successfully
- Duplicate event (already processed)
- User already exists (idempotent success)

### Invalid Signature (400 Bad Request)

```json
{
  "status": "error",
  "message": "Invalid webhook signature"
}
```

### Missing Email (400 Bad Request)

```json
{
  "status": "error",
  "message": "Missing email in payment intent"
}
```

### Processing Error (500 Internal Server Error)

```json
{
  "status": "error",
  "message": "Failed to process webhook"
}
```

Sent when database or user creation fails. Stripe will retry automatically.

## Error Handling

| Scenario | HTTP Status | Retry by Stripe? |
|----------|-------------|------------------|
| Invalid signature | 400 | No |
| Missing required fields | 400 | No |
| Duplicate event | 200 | N/A |
| Database error | 500 | Yes |
| User creation failure | 500 | Yes |
| Email service failure | 200 | N/A (webhook processed, email queued) |

## Security

1. **Signature Validation**: All requests MUST pass Stripe signature validation using webhook secret.
2. **Timestamp Tolerance**: Reject signatures older than 5 minutes (Stripe default).
3. **Idempotency**: Track processed `evt_xxx` IDs to prevent duplicate processing.
4. **No Auth Required**: Stripe does not send authentication tokens; signature validation is the security mechanism.

## Example cURL

```bash
curl -X POST https://api.example.com/webhooks/stripe \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=1234567890,v1=abc123..." \
  -d '{
    "id": "evt_test_123",
    "type": "payment_intent.succeeded",
    "data": {
      "object": {
        "id": "pi_test_123",
        "receipt_email": "user@example.com",
        "charges": {
          "data": [{
            "billing_details": {
              "name": "John Doe",
              "email": "user@example.com"
            }
          }]
        }
      }
    }
  }'
```
