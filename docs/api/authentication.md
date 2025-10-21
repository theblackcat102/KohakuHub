---
title: Authentication API
description: User registration, login, tokens, email verification
icon: i-carbon-password
---

# Authentication API

All auth endpoints.

## Register

```bash
POST /auth/register
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "secure123"
}
```

## Login

```bash
POST /auth/login
{
  "username": "alice",
  "password": "secure123"
}
```

## Tokens

```bash
POST /auth/tokens
GET /auth/tokens
DELETE /auth/tokens/{id}
```

## Email Verification

```bash
POST /auth/verify-email/{token}
POST /auth/resend-verification
```
