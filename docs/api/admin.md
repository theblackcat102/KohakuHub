---
title: Admin API
description: Administrative endpoints for users, repos, quota, storage
icon: i-carbon-security
---

# Admin API

Comprehensive admin endpoints.

## Authentication

All admin endpoints require:
```
X-Admin-Token: your_admin_secret_token
```

## Users

```bash
GET    /admin/api/users
POST   /admin/api/users
PUT    /admin/api/users/{id}
DELETE /admin/api/users/{id}
POST   /admin/api/users/{id}/verify-email
```

## Repositories

```bash
GET    /admin/api/repositories
DELETE /admin/api/repositories/{type}/{namespace}/{name}
POST   /admin/api/repositories/recalculate-all
```

## Quota

```bash
GET  /admin/api/quota/overview
POST /admin/api/quota/{username}/recalculate
```

## Fallback Sources

```bash
GET    /admin/api/fallback-sources
POST   /admin/api/fallback-sources
PUT    /admin/api/fallback-sources/{id}
DELETE /admin/api/fallback-sources/{id}
GET    /admin/api/fallback-sources/cache/stats
DELETE /admin/api/fallback-sources/cache/clear
```

## Storage

```bash
GET /admin/api/storage/buckets
GET /admin/api/storage/objects
```

## Database

```bash
POST /admin/api/database/query
{
  "sql": "SELECT * FROM users LIMIT 10"
}
```

## Statistics

```bash
GET /admin/api/stats/overview
GET /admin/api/stats/repositories
GET /admin/api/stats/users
```
