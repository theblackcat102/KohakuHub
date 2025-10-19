---
title: Port Reference
description: All ports used by KohakuHub services
icon: i-carbon-network-3
---

# Port Reference

Quick reference for all ports.

## User-Facing

- **28080** - nginx (main entry, HTTP)
- **443** - nginx (HTTPS, production)

## Internal Services

- **48888** - kohaku-hub FastAPI backend
- **5432** - PostgreSQL database
- **28000** - LakeFS API
- **9000** - MinIO S3 API
- **9001** - MinIO Console

## Development

- **5173** - Vite dev server (UI)
- **5174** - Vite dev server (Admin)

## Public Endpoints

- **29001** - MinIO S3 public endpoint

Use nginx reverse proxy in production!
