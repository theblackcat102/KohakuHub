---
title: Docker Deployment
description: Complete Docker Compose setup guide
icon: i-carbon-container-services
---

# Docker Deployment

Deploy KohakuHub with Docker Compose.

## Quick Deploy

\`\`\`bash
git clone https://github.com/KohakuBlueleaf/KohakuHub.git
cd KohakuHub
python scripts/generate_docker_compose.py
python scripts/deploy.py
\`\`\`

## Services

- nginx (28080) - Entry point
- kohaku-hub (48888) - FastAPI (4 workers)
- postgres (5432) - Database
- lakefs (28000) - Versioning
- minio (29000) - S3 storage

## Configuration

See [Configuration Reference](/docs/reference/config)

## Operations

\`\`\`bash
docker compose logs -f
docker compose restart
docker compose up -d --build
\`\`\`
