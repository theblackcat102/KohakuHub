<!-- src/pages/self-hosted.vue -->
<script setup>
import MarkdownPage from "@/components/common/MarkdownPage.vue";

const content = `# Self-Hosting KohakuHub

This guide will help you set up and run your own KohakuHub instance. KohakuHub is designed to be self-hosted, giving you complete control over your AI models, datasets, and applications.

## Overview

KohakuHub combines several powerful technologies to provide a complete model hosting solution:

- **LakeFS**: Git-like versioning for your data (branches, commits, diffs)
- **MinIO/S3**: Object storage backend for file storage
- **PostgreSQL/SQLite**: Metadata database for deduplication and indexing
- **FastAPI**: HuggingFace-compatible API layer
- **Vue 3**: Modern web interface

## Prerequisites

Before you begin, ensure you have:

- **Docker** and **Docker Compose** installed
- **Node.js** and **npm** (for building the frontend)
- **Python 3.10+** (for testing with \`huggingface_hub\` client)
- At least **10GB** of free disk space (more for production use)

### Optional Services

- **S3 Storage**: You can use external S3-compatible storage (MinIO runs in Docker by default)
- **SMTP Service**: For email verification (optional but recommended for production)

## Quick Start

### 1. Clone the Repository

\`\`\`bash
git clone https://github.com/KohakuBlueleaf/Kohaku-Hub.git
cd Kohaku-Hub
\`\`\`

### 2. Configure Docker Compose

The main configuration file is located at \`docker/docker-compose.yml\`. You should review and customize it before starting.

#### ⚠️ Important: Security Configuration

**NEVER use default passwords in production!** Change these immediately:

\`\`\`yaml
# MinIO credentials - CHANGE THESE!
environment:
  - MINIO_ROOT_USER=your_secure_username
  - MINIO_ROOT_PASSWORD=your_very_secure_password_here

# PostgreSQL credentials - CHANGE THESE!
environment:
  - POSTGRES_USER=hub
  - POSTGRES_PASSWORD=your_secure_db_password
  - POSTGRES_DB=hubdb

# LakeFS encryption key - CHANGE THIS!
environment:
  - LAKEFS_AUTH_ENCRYPT_SECRET_KEY=generate_a_long_random_key_here
\`\`\`

#### Port Configuration

The default setup exposes these ports:

- **28080** - KohakuHub Web UI (main user/API interface)
- **48888** - KohakuHub API (for clients like \`huggingface_hub\`)
- **28000** - LakeFS Web UI + API
- **29000** - MinIO Web Console
- **29001** - MinIO S3 API
- **25432** - PostgreSQL (optional, for external access)

**For production deployment:**

1. Only expose port **28080** (or **443** with HTTPS) to users
2. The Web UI will proxy requests to the API
3. Keep other ports internal or behind a firewall
4. Use a reverse proxy (nginx/traefik) with HTTPS

#### Public Endpoint Configuration

If deploying on a server, update these environment variables:

\`\`\`yaml
environment:
  # Replace with your actual domain/IP
  - KOHAKU_HUB_BASE_URL=https://your-domain.com
  - KOHAKU_HUB_S3_PUBLIC_ENDPOINT=https://s3.your-domain.com
\`\`\`

The S3 public endpoint is used for generating download URLs. It should point to wherever your MinIO S3 API is accessible (port 29001 by default).

### 3. Start the Services

\`\`\`bash
# Set user/group ID for proper permissions
export UID=$(id -u)
export GID=$(id -g)

# Build Frontend and Start all services
./deploy.sh
\`\`\`

Alternatively, you can manually build and deploy:

\`\`\`bash
# Install frontend dependencies
npm install --prefix ./src/kohaku-hub-ui

# Build frontend
npm run build --prefix ./src/kohaku-hub-ui

# Start Docker services
docker compose -f docker/docker-compose.yml up -d --build
\`\`\`

### 4. Verify Installation

Check that all services are running:

\`\`\`bash
docker compose -f docker/docker-compose.yml ps
\`\`\`

All services should show "Up" status.

### 5. Access the Web Interfaces

- **KohakuHub Web UI**: http://localhost:28080 (main interface)
- **KohakuHub API Docs**: http://localhost:48888/docs (API documentation)
- **LakeFS Web UI**: http://localhost:28000 (repository browser)
- **MinIO Console**: http://localhost:29000 (storage browser)

### 6. Create Your First User

Navigate to http://localhost:28080 and click **Register** to create your first user account.

## Advanced Configuration

### Using a Configuration File

For advanced configuration, create a \`config.toml\` file. See \`config-example.toml\` in the repository for all available options.

Key settings include:

\`\`\`toml
[server]
host = "0.0.0.0"
port = 8000
base_url = "https://your-domain.com"

[storage]
# Use SQLite (default) or PostgreSQL
db_type = "sqlite"
db_path = "./data/hub.db"

# Or use PostgreSQL
# db_type = "postgresql"
# db_host = "localhost"
# db_port = 5432
# db_user = "hub"
# db_password = "your_password"
# db_name = "hubdb"

[lakefs]
endpoint = "http://lakefs:8000"
access_key_id = "your_access_key"
secret_access_key = "your_secret_key"

[s3]
endpoint = "http://minio:9000"
access_key_id = "your_minio_user"
secret_access_key = "your_minio_password"
bucket_name = "hub-data"

[auth]
session_expire_days = 30
require_email_verification = false

[lfs]
# Files larger than this use Git LFS protocol
threshold_mb = 10
\`\`\`

### Environment Variables

You can also configure KohakuHub using environment variables:

\`\`\`bash
# Server configuration
export KOHAKU_HUB_BASE_URL=https://your-domain.com
export KOHAKU_HUB_PORT=8000

# Database configuration
export KOHAKU_HUB_DB_TYPE=postgresql
export KOHAKU_HUB_DB_HOST=localhost
export KOHAKU_HUB_DB_PORT=5432

# Storage configuration
export KOHAKU_HUB_S3_ENDPOINT=http://minio:9000
export KOHAKU_HUB_S3_ACCESS_KEY=your_key
export KOHAKU_HUB_S3_SECRET_KEY=your_secret

# Authentication
export KOHAKU_HUB_SESSION_EXPIRE_DAYS=30
export KOHAKU_HUB_REQUIRE_EMAIL_VERIFICATION=false
\`\`\`

## Production Deployment

### Using a Reverse Proxy

For production, use a reverse proxy like nginx or Caddy to handle HTTPS:

#### Nginx Example

\`\`\`nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:28080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # For large file uploads
        client_max_body_size 10G;
        proxy_request_buffering off;
    }
}
\`\`\`

#### Caddy Example

\`\`\`caddy
your-domain.com {
    reverse_proxy localhost:28080

    # For large file uploads
    request_body {
        max_size 10GB
    }
}
\`\`\`

### Database Backup

For production, regularly backup your PostgreSQL database:

\`\`\`bash
# Create backup
docker exec kohaku-postgres pg_dump -U hub hubdb > backup.sql

# Restore backup
cat backup.sql | docker exec -i kohaku-postgres psql -U hub hubdb
\`\`\`

### Storage Backup

Your repository data is stored in the MinIO volumes. Back up these directories:

\`\`\`bash
# Default locations (check your docker-compose.yml)
./docker/hub-meta/minio/data
./docker/hub-meta/lakefs/data
\`\`\`

### Monitoring

Monitor your KohakuHub instance using Docker:

\`\`\`bash
# View logs
docker compose -f docker/docker-compose.yml logs -f kohaku-hub

# Check resource usage
docker stats
\`\`\`

## Scaling Considerations

### Storage

- **MinIO**: Can be scaled to multiple nodes for redundancy
- **S3**: Use external S3-compatible storage (Cloudflare R2, Wasabi, AWS S3)
- **LFS**: Configure threshold based on your use case

### Database

- **SQLite**: Good for small deployments (< 10 users)
- **PostgreSQL**: Recommended for production (> 10 users)
- Consider read replicas for high traffic

### Compute

- Increase Docker resource limits for heavy workloads
- Use load balancer for multiple KohakuHub instances
- Cache frequently accessed files with CDN

## Troubleshooting

### Services Won't Start

\`\`\`bash
# Check logs
docker compose -f docker/docker-compose.yml logs

# Restart services
docker compose -f docker/docker-compose.yml restart

# Full rebuild
docker compose -f docker/docker-compose.yml down
./deploy.sh
\`\`\`

### Permission Issues

\`\`\`bash
# Fix permission on mounted volumes
sudo chown -R $UID:$GID ./docker/hub-meta
\`\`\`

### Database Connection Errors

- Verify PostgreSQL is running: \`docker compose ps\`
- Check credentials in docker-compose.yml
- Ensure database exists: \`docker exec -it kohaku-postgres psql -U hub -l\`

### Storage Issues

- Check MinIO is accessible: http://localhost:29000
- Verify credentials match docker-compose.yml
- Check bucket exists (default: \`hub-data\`)

### LakeFS Credentials

LakeFS credentials are automatically generated on first startup and stored in:

\`\`\`
docker/hub-meta/hub-api/credentials.env
\`\`\`

Use these to log into LakeFS Web UI at http://localhost:28000

## Updating KohakuHub

To update to the latest version:

\`\`\`bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
./deploy.sh

# Or manually:
npm run build --prefix ./src/kohaku-hub-ui
docker compose -f docker/docker-compose.yml up -d --build
\`\`\`

## Security Best Practices

1. **Change all default passwords** before production use
2. **Enable HTTPS** using a reverse proxy
3. **Use strong session secrets** and encryption keys
4. **Enable email verification** for user registration
5. **Regular backups** of database and storage
6. **Keep Docker images updated** for security patches
7. **Limit exposed ports** to only what's necessary
8. **Use firewall rules** to restrict access
9. **Monitor logs** for suspicious activity
10. **Implement rate limiting** at the reverse proxy level

## Getting Help

If you need help with self-hosting:

- **Documentation**: Check the [GitHub repository](https://github.com/KohakuBlueleaf/Kohaku-Hub)
- **Discord**: Join our [community](https://discord.gg/xWYrkyvJ2s)
- **GitHub Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share experiences

## Next Steps

After setting up your instance:

1. **Register users**: Create accounts for your team
2. **Create organizations**: Set up teams and projects
3. **Upload models**: Start hosting your AI models
4. **Configure integrations**: Set up with your ML pipeline
5. **Monitor usage**: Track downloads and activity

---

**Note**: KohakuHub is under active development. Features may change, and this guide will be updated accordingly. For the latest information, check the [GitHub repository](https://github.com/KohakuBlueleaf/Kohaku-Hub).
`;
</script>

<template>
  <MarkdownPage :content="content" />
</template>
