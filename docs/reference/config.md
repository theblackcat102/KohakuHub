---
title: Configuration Reference
description: All environment variables and settings
icon: i-carbon-settings-adjust
---

# Configuration Reference

Complete list of environment variables.

## Application

\`\`\`yaml
KOHAKU_HUB_BASE_URL: http://localhost:28080
KOHAKU_HUB_SITE_NAME: KohakuHub
KOHAKU_HUB_API_BASE: /api
\`\`\`

## Database

\`\`\`yaml
KOHAKU_HUB_DB_BACKEND: postgres
KOHAKU_HUB_DATABASE_URL: postgresql://user:pass@host:5432/db
\`\`\`

## S3

\`\`\`yaml
KOHAKU_HUB_S3_ENDPOINT: http://minio:9000
KOHAKU_HUB_S3_PUBLIC_ENDPOINT: http://localhost:29001
KOHAKU_HUB_S3_BUCKET: hub-storage
KOHAKU_HUB_S3_REGION: us-east-1
\`\`\`

## LFS

\`\`\`yaml
KOHAKU_HUB_LFS_THRESHOLD_BYTES: 5000000
KOHAKU_HUB_LFS_KEEP_VERSIONS: 5
KOHAKU_HUB_LFS_AUTO_GC: false
\`\`\`

## Auth

\`\`\`yaml
KOHAKU_HUB_SESSION_SECRET: change-me
KOHAKU_HUB_REQUIRE_EMAIL_VERIFICATION: false
KOHAKU_HUB_INVITATION_ONLY: false
\`\`\`

## Quotas

\`\`\`yaml
KOHAKU_HUB_DEFAULT_USER_PUBLIC_QUOTA_BYTES: null
KOHAKU_HUB_DEFAULT_USER_PRIVATE_QUOTA_BYTES: null
\`\`\`

## Fallback

\`\`\`yaml
KOHAKU_HUB_FALLBACK_ENABLED: true
KOHAKU_HUB_FALLBACK_CACHE_TTL: 300
\`\`\`

See deployment.md for full examples.
