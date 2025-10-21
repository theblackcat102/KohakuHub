---
title: Repository API
description: CRUD operations for models, datasets, spaces
icon: i-carbon-data-base
---

# Repository API

Manage repositories via API.

## Create

```bash
POST /api/repos/create
{
  "repo_type": "model",
  "namespace": "username",
  "name": "my-model",
  "private": false
}
```

## Delete

```bash
DELETE /api/repos/delete
{
  "repo_type": "model",
  "namespace": "username",
  "name": "my-model"
}
```

## Move

```bash
POST /api/repos/move
{
  "from_namespace": "alice",
  "to_namespace": "org",
  "repo_type": "model",
  "name": "model"
}
```

## Squash

```bash
POST /api/repos/squash
{
  "repo_type": "model",
  "namespace": "user",
  "name": "repo"
}
```

Keeps only latest version of each file.
