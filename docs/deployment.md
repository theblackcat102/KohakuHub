# KohakuHub Deployment Architecture

## Setup Instructions

### First Time Setup

1. **Copy configuration file:**
   ```bash
   cp docker-compose.example.yml docker-compose.yml
   ```

2. **Edit docker-compose.yml:**
   - Change MinIO credentials (MINIO_ROOT_USER, MINIO_ROOT_PASSWORD)
   - Change PostgreSQL password (POSTGRES_PASSWORD)
   - Change LakeFS secret key (LAKEFS_AUTH_ENCRYPT_SECRET_KEY)
   - Change session secret (KOHAKU_HUB_SESSION_SECRET)
   - Update BASE_URL if deploying to a domain

3. **Build and start:**
   ```bash
   npm install --prefix ./src/kohaku-hub-ui
   npm run build --prefix ./src/kohaku-hub-ui
   docker-compose up -d --build
   ```

**Note:** The repository only includes `docker-compose.example.yml` as a template. Your customized `docker-compose.yml` is excluded from git to prevent committing sensitive credentials.

## Port Configuration

### Production Deployment (Docker)

**Exposed Port:**
- **28080** - Main entry point (Web UI + API via nginx reverse proxy)

**Internal Ports (not exposed to users):**
- 48888 - Backend API server (proxied by nginx)
- 28000 - LakeFS UI (admin only)
- 29000 - MinIO Console (admin only)
- 29001 - MinIO S3 API (used by backend)
- 25432 - PostgreSQL (optional, for external access)

### Nginx Reverse Proxy

**Configuration:** `docker/nginx/default.conf`

Nginx on port 28080:
1. Serves frontend static files from `/usr/share/nginx/html`
2. Proxies API requests to backend:48888:
   - `/api/*` → `http://hub-api:48888/api/*`
   - `/org/*` → `http://hub-api:48888/org/*`
   - `/{namespace}/{name}.git/*` → `http://hub-api:48888/{namespace}/{name}.git/*` (Git Smart HTTP)
   - `/{type}s/{namespace}/{name}/resolve/*` → `http://hub-api:48888/{type}s/{namespace}/{name}/resolve/*`

### Client Configuration

**For HuggingFace Client:**
```python
import os
os.environ["HF_ENDPOINT"] = "http://localhost:28080"  # Use nginx port
os.environ["HF_TOKEN"] = "your_token"
```

**For kohub-cli:**
```bash
export HF_ENDPOINT=http://localhost:28080
kohub-cli auth login
```

**For Git Clone:**
```bash
# Clone repository
git clone http://localhost:28080/namespace/repo.git

# With authentication (private repos)
git clone http://username:token@localhost:28080/namespace/repo.git

# Download large files
cd repo
git lfs install
git lfs pull
```

**❌ WRONG:**
```python
os.environ["HF_ENDPOINT"] = "http://localhost:48888"  # Don't use backend port directly
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     Client Access                       │
│            (HuggingFace Hub, kohub-cli, Web)            │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Port 28080
                     ▼
         ┌───────────────────────┐
         │   Nginx (hub-ui)      │
         │  - Serves frontend    │
         │  - Reverse proxy API  │
         └───────┬───────────────┘
                 │
         ┌───────┴───────────────┐
         │                       │
   Static Files            /api, /org, resolve
   (Vue 3 app)                   │
                                 │ Internal: hub-api:48888
                                 ▼
                    ┌────────────────────────┐
                    │  FastAPI (hub-api)     │
                    │  - HF-compatible API   │
                    └──┬─────────────┬───────┘
                       │             │
              ┌────────┴────┐   ┌────┴────────┐
              │   LakeFS    │   │   MinIO     │
              │  (version)  │   │  (storage)  │
              └─────────────┘   └─────────────┘
```

## Development vs Production

### Development

**Frontend Dev Server** (port 5173):
```bash
npm run dev --prefix ./src/kohaku-hub-ui
# Proxies /api → http://localhost:48888
```

**Backend** (port 48888):
```bash
uvicorn kohakuhub.main:app --reload --port 48888
```

**Client Access:**
- Frontend: http://localhost:5173
- API: http://localhost:48888 (direct)
- Swagger Docs: http://localhost:48888/docs

### Production (Docker)

**All services via docker-compose:**
```bash
./deploy.sh
```

**Client Access:**
- **Everything:** http://localhost:28080 (Web UI + API)
- Swagger Docs (dev): http://localhost:48888/docs (if port exposed)

## Security Best Practices

### Production Deployment

1. **Only expose port 28080**
   ```yaml
   # docker-compose.yml
   hub-ui:
     ports:
       - "28080:80"  # ONLY THIS PORT

   hub-api:
     # NO ports section - internal only
   ```

2. **Use HTTPS with reverse proxy**
   ```nginx
   # Production nginx config
   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /etc/nginx/ssl/cert.pem;
       ssl_certificate_key /etc/nginx/ssl/key.pem;

       location / {
           proxy_pass http://hub-ui:80;
       }
   }
   ```

3. **Set BASE_URL to your domain**
   ```yaml
   environment:
     - KOHAKU_HUB_BASE_URL=https://your-domain.com
     - KOHAKU_HUB_S3_PUBLIC_ENDPOINT=https://s3.your-domain.com
   ```

## Common Mistakes

❌ **Don't do this:**
```python
# Wrong - bypassing nginx
os.environ["HF_ENDPOINT"] = "http://localhost:48888"
```

✅ **Do this:**
```python
# Correct - using nginx reverse proxy
os.environ["HF_ENDPOINT"] = "http://localhost:28080"
```

## Why This Architecture?

1. **Single Entry Point:** Users only need to know one port (28080)
2. **Security:** Backend (48888) not exposed to internet
3. **SSL Termination:** Nginx handles HTTPS
4. **Static File Serving:** Nginx serves frontend efficiently
5. **Load Balancing:** Can add multiple backend instances behind nginx
6. **Caching:** Nginx can cache static assets

## Troubleshooting

### "Connection refused to localhost:48888"

**Problem:** Client trying to connect directly to backend

**Solution:** Change `HF_ENDPOINT` to use port 28080:
```bash
export HF_ENDPOINT=http://localhost:28080
```

### "CORS errors in browser"

**Problem:** Frontend trying to access wrong port

**Solution:** Ensure `KOHAKU_HUB_BASE_URL` is set correctly:
```yaml
environment:
  - KOHAKU_HUB_BASE_URL=http://localhost:28080
```

### "API calls returning HTML instead of JSON"

**Problem:** Hitting nginx for a non-proxied path

**Solution:** Check nginx config ensures all API paths are proxied
