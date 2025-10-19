<script setup>
import MarkdownPage from "@/components/common/MarkdownPage.vue";

const content = `# Self-Host KohakuHub

Complete guide to deploying your own KohakuHub instance with all features enabled.

---

## 📋 Prerequisites

**System Requirements:**
- **OS:** Linux (recommended), macOS, Windows with WSL2
- **RAM:** 4GB minimum, 8GB+ recommended
- **Storage:** 50GB+ (depends on your models/datasets)
- **Docker:** 20.10+ with Docker Compose

**For Production:**
- Domain name with SSL certificate
- Reverse proxy (nginx included in docker-compose)
- Backup strategy for PostgreSQL database

---

## 🚀 Quick Deploy (Docker Compose)

### Step 1: Clone Repository

\`\`\`bash
git clone https://github.com/KohakuBlueleaf/KohakuHub.git
cd KohakuHub
\`\`\`

### Step 2: Generate Configuration

**Option A: Interactive Generator (Recommended)**

\`\`\`bash
python scripts/generate_docker_compose.py
\`\`\`

This creates \`docker-compose.yml\` with:
- Secure random passwords
- LakeFS credentials
- Admin token
- Session secret

**Option B: Manual Configuration**

\`\`\`bash
cp docker-compose.example.yml docker-compose.yml
# Edit docker-compose.yml to change:
# - POSTGRES_PASSWORD
# - KOHAKU_HUB_SESSION_SECRET (use: python scripts/generate_secret.py)
# - KOHAKU_HUB_ADMIN_SECRET_TOKEN
\`\`\`

### Step 3: Build Frontend

\`\`\`bash
# Install dependencies
npm install --prefix src/kohaku-hub-ui
npm install --prefix src/kohaku-hub-admin

# Build for production
npm run build --prefix src/kohaku-hub-ui
npm run build --prefix src/kohaku-hub-admin

# Or use the deploy script:
python scripts/deploy.py
\`\`\`

### Step 4: Start Services

\`\`\`bash
docker compose up -d --build
\`\`\`

**Services Started:**
- **nginx** (port 28080) - Main entry point
- **kohaku-hub** (port 48888) - FastAPI backend (4 workers)
- **postgres** (port 5432) - Database
- **lakefs** (port 28000) - Versioning
- **minio** (port 29000) - S3 storage
- **kohaku-hub-admin** (port 5174) - Admin UI dev server (optional)

### Step 5: First-Time Setup

**Access:** http://localhost:28080

1. **Register admin account:**
   - Username: admin (or your choice)
   - Email: your@email.com
   - Password: secure password

2. **Access admin portal:**
   - Visit: http://localhost:28080/admin
   - Login with \`KOHAKU_HUB_ADMIN_SECRET_TOKEN\`

3. **Create first repository:**
   - Click **New** → **Model**
   - Test upload/download

---

## ⚙️ Configuration

### Core Settings

**In \`docker-compose.yml\`:**

\`\`\`yaml
environment:
  # Application
  KOHAKU_HUB_BASE_URL: http://localhost:28080
  KOHAKU_HUB_SITE_NAME: KohakuHub  # Custom site name

  # Database
  KOHAKU_HUB_DB_BACKEND: postgres
  KOHAKU_HUB_DATABASE_URL: postgresql://hub:password@postgres:5432/kohakuhub

  # S3 Storage
  KOHAKU_HUB_S3_ENDPOINT: http://minio:9000
  KOHAKU_HUB_S3_PUBLIC_ENDPOINT: http://localhost:29001
  KOHAKU_HUB_S3_BUCKET: hub-storage
  KOHAKU_HUB_S3_REGION: us-east-1

  # LakeFS
  KOHAKU_HUB_LAKEFS_ENDPOINT: http://lakefs:8000

  # Auth
  KOHAKU_HUB_SESSION_SECRET: change-me-in-production
  KOHAKU_HUB_SESSION_EXPIRE_HOURS: 168  # 7 days
  KOHAKU_HUB_TOKEN_EXPIRE_DAYS: 365
  KOHAKU_HUB_REQUIRE_EMAIL_VERIFICATION: false
  KOHAKU_HUB_INVITATION_ONLY: false

  # Admin
  KOHAKU_HUB_ADMIN_ENABLED: true
  KOHAKU_HUB_ADMIN_SECRET_TOKEN: change-me-in-production

  # LFS
  KOHAKU_HUB_LFS_THRESHOLD_BYTES: 5000000  # 5MB
  KOHAKU_HUB_LFS_KEEP_VERSIONS: 5
  KOHAKU_HUB_LFS_AUTO_GC: false

  # Quota (bytes, or null for unlimited)
  KOHAKU_HUB_DEFAULT_USER_PUBLIC_QUOTA_BYTES: null
  KOHAKU_HUB_DEFAULT_USER_PRIVATE_QUOTA_BYTES: null

  # External Fallback
  KOHAKU_HUB_FALLBACK_ENABLED: true
  KOHAKU_HUB_FALLBACK_CACHE_TTL: 300
  KOHAKU_HUB_FALLBACK_SOURCES: |
    [
      {
        "url": "https://huggingface.co",
        "token": "",
        "priority": 1,
        "name": "HuggingFace",
        "source_type": "huggingface"
      }
    ]
\`\`\`

### Email Configuration (Optional)

**For email verification and notifications:**

\`\`\`yaml
KOHAKU_HUB_SMTP_ENABLED: true
KOHAKU_HUB_SMTP_HOST: smtp.gmail.com
KOHAKU_HUB_SMTP_PORT: 587
KOHAKU_HUB_SMTP_USERNAME: your-email@gmail.com
KOHAKU_HUB_SMTP_PASSWORD: app-password
KOHAKU_HUB_SMTP_FROM: noreply@yourdomain.com
KOHAKU_HUB_SMTP_TLS: true

KOHAKU_HUB_REQUIRE_EMAIL_VERIFICATION: true
\`\`\`

### Invitation-Only Mode

**Restrict registration:**

\`\`\`yaml
KOHAKU_HUB_INVITATION_ONLY: true
\`\`\`

Then create invitations via admin portal.

---

## 🔒 Security Hardening

### Change Default Secrets

**Critical:**
\`\`\`bash
# Generate secure secrets
python scripts/generate_secret.py  # For session secret
python scripts/generate_secret.py  # For admin token

# Update docker-compose.yml with generated values
\`\`\`

### PostgreSQL Security

\`\`\`yaml
POSTGRES_PASSWORD: use-strong-password-here  # Change from default!
\`\`\`

### MinIO Security

\`\`\`yaml
MINIO_ROOT_USER: change-me
MINIO_ROOT_PASSWORD: change-me-too
\`\`\`

### LakeFS Security

Auto-generated credentials saved to:
\`\`\`
docker/hub-meta/hub-api/credentials.env
\`\`\`

Keep this file secure!

---

## 🌐 Production Deployment

### Domain & SSL

**Update nginx config:**

\`\`\`nginx
# docker/nginx/nginx.conf
server {
    listen 443 ssl http2;
    server_name hub.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # ... rest of config
}
\`\`\`

**Update base URL:**
\`\`\`yaml
KOHAKU_HUB_BASE_URL: https://hub.yourdomain.com
\`\`\`

### External S3 (AWS/R2)

**For Cloudflare R2:**

\`\`\`yaml
KOHAKU_HUB_S3_ENDPOINT: https://account-id.r2.cloudflarestorage.com
KOHAKU_HUB_S3_PUBLIC_ENDPOINT: https://pub-id.r2.dev
KOHAKU_HUB_S3_REGION: auto
KOHAKU_HUB_S3_SIGNATURE_VERSION: s3v4
KOHAKU_HUB_S3_ACCESS_KEY: your-r2-access-key
KOHAKU_HUB_S3_SECRET_KEY: your-r2-secret-key
KOHAKU_HUB_S3_BUCKET: kohakuhub
KOHAKU_HUB_S3_FORCE_PATH_STYLE: true
\`\`\`

**For AWS S3:**

\`\`\`yaml
KOHAKU_HUB_S3_ENDPOINT: https://s3.amazonaws.com
KOHAKU_HUB_S3_REGION: us-east-1
KOHAKU_HUB_S3_SIGNATURE_VERSION: s3v4
KOHAKU_HUB_S3_BUCKET: your-bucket-name
KOHAKU_HUB_S3_FORCE_PATH_STYLE: false
\`\`\`

### Database Backups

**Automated backups:**

\`\`\`bash
# Backup script
docker exec kohakuhub-postgres pg_dump -U hub kohakuhub > backup.sql

# Restore
cat backup.sql | docker exec -i kohakuhub-postgres psql -U hub kohakuhub
\`\`\`

**Cron job:**
\`\`\`cron
0 2 * * * cd /path/to/KohakuHub && docker exec kohakuhub-postgres pg_dump -U hub kohakuhub | gzip > backups/kohakuhub-$(date +\%Y\%m\%d).sql.gz
\`\`\`

---

## 🎛️ Advanced Configuration

### Multi-Worker Deployment

**Backend is already multi-worker:**
\`\`\`yaml
# docker-compose.yml
command: >
  sh -c "uvicorn kohakuhub.main:app
    --host 0.0.0.0 --port 48888
    --workers 4"  # Adjust based on CPU cores
\`\`\`

**Database uses \`db.atomic()\` for transaction safety.**

### Quota Configuration

**Per-user defaults:**
\`\`\`yaml
KOHAKU_HUB_DEFAULT_USER_PUBLIC_QUOTA_BYTES: 10737418240   # 10GB
KOHAKU_HUB_DEFAULT_USER_PRIVATE_QUOTA_BYTES: 5368709120   # 5GB
KOHAKU_HUB_DEFAULT_ORG_PUBLIC_QUOTA_BYTES: 107374182400   # 100GB
KOHAKU_HUB_DEFAULT_ORG_PRIVATE_QUOTA_BYTES: 53687091200   # 50GB
\`\`\`

**Customize per-user:** Admin Portal → Users → Edit → Set custom quota

### LFS Configuration

**Server defaults (apply to all repos):**
\`\`\`yaml
KOHAKU_HUB_LFS_THRESHOLD_BYTES: 5000000  # 5MB
KOHAKU_HUB_LFS_KEEP_VERSIONS: 5  # Keep 5 versions per file
KOHAKU_HUB_LFS_AUTO_GC: false  # Manual GC only
\`\`\`

**32 default LFS suffix rules:**
- Models: .safetensors, .bin, .pt, .onnx, .h5, .gguf, etc.
- Archives: .zip, .tar, .gz, .7z, .rar
- Data: .parquet, .arrow, .npy, .npz
- Media: .mp4, .wav, .mp3, .tiff

**Per-repo overrides:** Repo Settings → LFS Settings

### Fallback Sources

**Add HuggingFace globally:**
\`\`\`yaml
KOHAKU_HUB_FALLBACK_ENABLED: true
KOHAKU_HUB_FALLBACK_CACHE_TTL: 300
KOHAKU_HUB_FALLBACK_SOURCES: |
  [{
    "url": "https://huggingface.co",
    "token": "",
    "priority": 1,
    "name": "HuggingFace",
    "source_type": "huggingface"
  }]
\`\`\`

**Or manage via:** Admin Portal → Fallback Sources

**Add private HF token:**
\`\`\`json
{
  "url": "https://huggingface.co",
  "token": "hf_your_token_here",
  "priority": 1,
  "name": "HuggingFace",
  "source_type": "huggingface"
}
\`\`\`

---

## 🔧 Operations

### View Logs

\`\`\`bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f kohaku-hub
docker compose logs -f postgres
docker compose logs -f lakefs
\`\`\`

### Restart Services

\`\`\`bash
# Restart all
docker compose restart

# Restart backend only
docker compose restart kohaku-hub
\`\`\`

### Update KohakuHub

\`\`\`bash
# Pull latest code
git pull origin main

# Rebuild frontend
npm run build --prefix src/kohaku-hub-ui
npm run build --prefix src/kohaku-hub-admin

# Rebuild and restart
docker compose up -d --build
\`\`\`

### Database Migrations

**Automatic on startup:**
\`\`\`
docker/startup.sh runs migrations before starting API
\`\`\`

**Manual migration:**
\`\`\`bash
docker exec -it kohakuhub-backend python scripts/run_migrations.py
\`\`\`

### Storage Management

**View S3 usage:**
\`\`\`bash
python scripts/show_s3_usage.py
\`\`\`

**Clear test data:**
\`\`\`bash
python scripts/clear_s3_storage.py  # WARNING: Deletes all data!
\`\`\`

**Admin Portal:**
- Storage → Browse buckets and objects
- Quota Overview → See all quotas
- Repositories → Storage breakdown per repo

---

## 🎯 Feature Configuration

### Enable Email Verification

\`\`\`yaml
KOHAKU_HUB_REQUIRE_EMAIL_VERIFICATION: true
KOHAKU_HUB_SMTP_ENABLED: true
KOHAKU_HUB_SMTP_HOST: smtp.your-provider.com
KOHAKU_HUB_SMTP_PORT: 587
KOHAKU_HUB_SMTP_USERNAME: your-smtp-username
KOHAKU_HUB_SMTP_PASSWORD: your-smtp-password
KOHAKU_HUB_SMTP_FROM: noreply@yourdomain.com
KOHAKU_HUB_SMTP_TLS: true
\`\`\`

### Enable Invitation-Only Registration

\`\`\`yaml
KOHAKU_HUB_INVITATION_ONLY: true
\`\`\`

**Create invitations:** Admin Portal → Invitations → Register Invitation

**Invitation types:**
- Single-use (max_usage: 1)
- Multi-use (max_usage: 50)
- Unlimited (max_usage: -1)
- With auto-org-join (org_id + role)

### Configure Site Branding

\`\`\`yaml
KOHAKU_HUB_SITE_NAME: "MyCompany AI Hub"
\`\`\`

Shows in:
- Page titles
- API responses (/api/version, /api/whoami-v2)
- Homepage

---

## 📊 Monitoring & Admin

### Admin Portal Features

**Access:** http://localhost:28080/admin

**Available Tools:**
1. **Dashboard** - Overview stats
2. **Users** - CRUD, email verification, quotas
3. **Repositories** - Browse, delete, view files
4. **Invitations** - Create/manage invite links
5. **Quota Overview** - All quotas at a glance
6. **Storage** - Browse S3 buckets/objects
7. **Fallback Sources** - Manage external sources
8. **Database** - Query tool with templates
9. **Statistics** - Usage analytics
10. **Commits** - Global commit history

### API Documentation

**Swagger UI:** http://localhost:48888/docs

**All endpoints documented with:**
- Parameters
- Request/response schemas
- Try-it-out functionality

---

## 🔄 External Source Fallback

### Setup HuggingFace Fallback

**Via Admin Portal:**
1. Navigate to **Fallback Sources**
2. Click **Add Source**
3. Fill in:
   - Name: HuggingFace
   - URL: https://huggingface.co
   - Source Type: huggingface
   - Priority: 1
   - Enabled: ✓
4. Click **Create**

**Now users can:**
- Browse HuggingFace profiles: \`/openai\`
- View external models: \`/models/stabilityai/stable-diffusion-xl\`
- Download from HF automatically
- See trending HF content

**Benefits:**
- No manual importing
- Always up-to-date
- Transparent source tagging
- Cached for performance

---

## 🏗️ Architecture

### Services

\`\`\`
nginx (28080) - Entry point
  ├─→ kohaku-hub (48888) - FastAPI backend (4 workers)
  ├─→ kohaku-hub-ui (built static) - Vue 3 frontend
  └─→ kohaku-hub-admin (built static) - Admin UI

kohaku-hub connects to:
  ├─→ postgres (5432) - Metadata (Peewee ORM)
  ├─→ lakefs (28000) - Versioning (REST API)
  └─→ minio (29000) - Object storage (S3 compatible)
\`\`\`

### Data Flow

**Upload (<10MB):**
1. Client → Base64 encode
2. FastAPI → Commit to LakeFS
3. LakeFS → Store in S3

**Upload (>10MB):**
1. FastAPI → Generate presigned URL
2. Client → Direct S3 upload
3. FastAPI → Link to LakeFS

**Download:**
1. FastAPI → 302 redirect to S3 presigned URL
2. Client → Direct S3 download (no proxy)

---

## 🐛 Troubleshooting

### Services Won't Start

\`\`\`bash
# Check logs
docker compose logs

# Check individual service
docker compose ps
docker compose logs kohaku-hub
\`\`\`

**Common issues:**
- Port conflicts (28080, 48888, etc.)
- Insufficient disk space
- Missing environment variables
- Database connection errors

### Frontend Not Loading

\`\`\`bash
# Rebuild frontend
npm run build --prefix src/kohaku-hub-ui

# Check nginx logs
docker compose logs nginx
\`\`\`

### Database Connection Errors

\`\`\`bash
# Check postgres is running
docker compose ps postgres

# Check credentials match
# DATABASE_URL must match POSTGRES_* vars
\`\`\`

### LakeFS Errors

\`\`\`bash
# Verify credentials
cat docker/hub-meta/hub-api/credentials.env

# Restart LakeFS
docker compose restart lakefs
\`\`\`

### Performance Issues

**Optimize:**
- Increase worker count (default: 4)
- Enable Redis for caching (future)
- Use external S3 (R2, AWS)
- Enable fallback cache

---

## 📈 Scaling

### Horizontal Scaling

**Multiple backend workers already enabled:**
- Uses \`db.atomic()\` for safety
- Stateless design
- Can add more workers in docker-compose

### Database Scaling

**PostgreSQL optimization:**
\`\`\`sql
-- Increase connection pool
max_connections = 200

-- Enable query optimization
shared_buffers = 256MB
effective_cache_size = 1GB
\`\`\`

### S3 Scaling

**Use external S3:**
- AWS S3 (global scale)
- Cloudflare R2 (zero egress fees)
- MinIO cluster (self-hosted)

---

## 🔄 Backup & Recovery

### What to Backup

**Critical:**
1. PostgreSQL database
2. LakeFS metadata (auto-persists to MinIO)
3. \`docker-compose.yml\`
4. \`docker/hub-meta/hub-api/credentials.env\`

**Not needed:**
- S3 object storage (can rebuild from LakeFS)
- Docker images (rebuildable)

### Backup Script

\`\`\`bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="./backups"

# Database backup
docker exec kohakuhub-postgres pg_dump -U hub kohakuhub | gzip > $BACKUP_DIR/db-$DATE.sql.gz

# Config backup
cp docker-compose.yml $BACKUP_DIR/docker-compose-$DATE.yml
cp docker/hub-meta/hub-api/credentials.env $BACKUP_DIR/credentials-$DATE.env
\`\`\`

### Recovery

\`\`\`bash
# Restore database
gunzip < backup.sql.gz | docker exec -i kohakuhub-postgres psql -U hub kohakuhub

# Restart services
docker compose restart
\`\`\`

---

## 📚 Next Steps

- **Admin Portal:** Explore all management features
- **Fallback:** Enable HuggingFace browsing
- **Invitations:** Set up invite-only mode
- **Quotas:** Configure storage limits
- **Monitoring:** Set up log aggregation
- **Backups:** Automate with cron

**Need help?**
- **GitHub Issues:** https://github.com/KohakuBlueleaf/KohakuHub/issues
- **Discord:** https://discord.gg/xWYrkyvJ2s
- **Documentation:** Check /docs for detailed guides
`;
</script>

<template>
  <MarkdownPage :content="content" />
</template>
