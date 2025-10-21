---
title: Organizations
description: Team collaboration with roles and member management
icon: i-carbon-group
---

# Organizations

Create teams and manage shared repositories.

## Create Organization

**Web UI:**
1. Click Organizations → New
2. Enter name and description
3. Create

**CLI:**
```bash
kohub-cli org create my-team --description "AI Team"
```

## Roles

- **Member** - View, create repos
- **Admin** - Manage members
- **Super Admin** - Full control

## Manage Members

```bash
kohub-cli org member add my-team alice --role admin
kohub-cli org member remove my-team bob
kohub-cli org member list my-team
```

## Features

- Separate public/private quotas
- Shared repositories
- Organization avatars
- Profile pages
