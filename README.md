# Kohaku Hub - Self-hosted HuggingFace alternative
![](images/logo-banner-dark.svg)

---

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/KohakuBlueleaf/KohakuHub)

**⚠️ Work In Progress - Not Production Ready**

Self-hosted HuggingFace alternative with Git-like versioning for AI models and datasets. Fully compatible with the official `huggingface_hub` Python client.

</div>

|![Web UI](image/README/1759520817420.png)|![Dark Mode](image/README/1759521021890.png)|
|-|-|

**Join our community:** https://discord.gg/xWYrkyvJ2s

## Features

- **HuggingFace Compatible** - Drop-in replacement for `huggingface_hub`, `hfutils`, `transformers`, `diffusers`
- **Native Git Clone** - Standard Git operations (clone, pull, push) with Git LFS support
- **Git-Like Versioning** - Branches, commits, tags via LakeFS
- **S3 Storage** - Works with MinIO, AWS S3, Cloudflare R2, etc.
- **Large File Support** - Git LFS protocol with automatic LFS pointers (>1MB files)
- **Organizations** - Multi-user namespaces with role-based access
- **Web UI** - Vue 3 interface with file browser, editor, commit history, Mermaid chart support
- **CLI Tool** - Full-featured command-line interface
- **File Deduplication** - Content-addressed storage by SHA256
- **Pure Python Git Server** - No native dependencies, memory-efficient

## Quick Start

### Deploy with Docker

```bash
git clone https://github.com/KohakuBlueleaf/KohakuHub.git
cd KohakuHub

# Option 1: Use interactive generator (recommended)
python scripts/generate_docker_compose.py

# Option 2: Manual configuration
# cp docker-compose.example.yml docker-compose.yml
# Edit docker-compose.yml to change credentials and secrets

# Build frontend and start services
npm install --prefix ./src/kohaku-hub-ui
npm run build --prefix ./src/kohaku-hub-ui
docker-compose up -d --build
```

**Access:**
- Web UI & API: http://localhost:28080 (all traffic goes here)
- API Docs (Swagger): http://localhost:48888/docs (direct access for development)
- LakeFS UI: http://localhost:28000
- MinIO Console: http://localhost:29000

**LakeFS credentials:** Auto-generated in `docker/hub-meta/hub-api/credentials.env`

### Use with Python

```python
import os
from huggingface_hub import HfApi

os.environ["HF_ENDPOINT"] = "http://localhost:28080"
os.environ["HF_TOKEN"] = "your_token_here"

api = HfApi(endpoint=os.environ["HF_ENDPOINT"], token=os.environ["HF_TOKEN"])

# Create repo
api.create_repo("my-org/my-model", repo_type="model")

# Upload file
api.upload_file(
    path_or_fileobj="model.safetensors",
    path_in_repo="model.safetensors",
    repo_id="my-org/my-model",
)

# Download file
api.hf_hub_download(repo_id="my-org/my-model", filename="model.safetensors")
```

### Use with Transformers/Diffusers

```python
import os
os.environ["HF_ENDPOINT"] = "http://localhost:28080"
os.environ["HF_TOKEN"] = "your_token_here"

from diffusers import AutoencoderKL
vae = AutoencoderKL.from_pretrained("my-org/my-model")
```

### CLI Tool

```bash
# Install
pip install -e .

# Interactive mode
kohub-cli

# Command mode
kohub-cli auth login
kohub-cli repo create my-org/my-model --type model
kohub-cli repo list --type model
kohub-cli org create my-org
kohub-cli org member add my-org alice --role admin
```

See [docs/CLI.md](./docs/CLI.md) for complete CLI documentation.

### Git Clone (Native Git Support)

```bash
# Clone repository (fast - only metadata and small files)
git clone http://localhost:28080/namespace/repo-name.git

# For private repositories, use token authentication
git clone http://username:your-token@localhost:28080/namespace/private-repo.git

# Install Git LFS for large files
cd repo-name
git lfs install
git lfs pull  # Download large files (>1MB)

# All standard Git operations work
git pull
git checkout -b feature-branch
# (push operations coming soon)
```

**How it works:**
- Files **<1MB**: Included directly in Git pack (fast clone)
- Files **>=1MB**: Stored as LFS pointers (download via `git lfs pull`)
- Pure Python implementation (no pygit2/libgit2 dependencies)
- Automatic `.gitattributes` and `.lfsconfig` generation
- Memory-efficient (handles repos of any size)

See [docs/Git.md](./docs/Git.md) for complete Git clone documentation and implementation details.

## Architecture

**Stack:**
- **FastAPI** - HuggingFace-compatible API
- **LakeFS** - Git-like versioning (branches, commits, diffs) via REST API
- **MinIO/S3** - Object storage with deduplication
- **PostgreSQL/SQLite** - Metadata database (synchronous with db.atomic() transactions)
- **Vue 3** - Modern web interface

**Implementation Notes:**
- **LakeFS:** Uses REST API directly (not the deprecated lakefs-client Python library), providing pure async operations without thread pool overhead
- **Database:** Synchronous operations with Peewee ORM and `db.atomic()` for transaction safety. Supports multi-worker deployment (4-8 workers) for horizontal scaling. Future migration to peewee-async planned.

**Data Flow:**
1. Small files (<10MB) → Base64 in commit payload
2. Large files (>10MB) → Direct S3 upload via presigned URL (LFS protocol)
3. All files linked to LakeFS commits for version control
4. Downloads → 302 redirect to S3 presigned URL (no proxy)

See [docs/API.md](./docs/API.md) for detailed API documentation.

## Configuration

**Environment Variables** (in `docker-compose.yml`):

```yaml
# Application
KOHAKU_HUB_BASE_URL=http://localhost:28080
KOHAKU_HUB_LFS_THRESHOLD_BYTES=10000000  # 10MB

# S3 Storage
KOHAKU_HUB_S3_PUBLIC_ENDPOINT=http://localhost:29001
KOHAKU_HUB_S3_BUCKET=hub-storage

# Database
KOHAKU_HUB_DB_BACKEND=postgres
KOHAKU_HUB_DATABASE_URL=postgresql://hub:pass@postgres:5432/hubdb

# Auth
KOHAKU_HUB_SESSION_SECRET=change-me-in-production
KOHAKU_HUB_REQUIRE_EMAIL_VERIFICATION=false
```

See [config-example.toml](./config-example.toml) for all options.

## Development

**Backend:**
```bash
pip install -e .

# Single worker (development)
uvicorn kohakuhub.main:app --reload --port 48888

# Multi-worker (production-like testing)
uvicorn kohakuhub.main:app --host 0.0.0.0 --port 48888 --workers 4

# Note: Database uses db.atomic() for transaction safety in multi-worker setups
# Note: In production, access via nginx on port 28080
```

**Frontend:**
```bash
npm install --prefix ./src/kohaku-hub-ui
npm run dev --prefix ./src/kohaku-hub-ui
```

**Testing:**
```bash
python scripts/test.py
python scripts/test_auth.py
```

## Documentation

- [docs/setup.md](./docs/setup.md) - Setup and installation guide
- [docs/deployment.md](./docs/deployment.md) - Deployment architecture
- [docs/ports.md](./docs/ports.md) - Port configuration reference
- [docs/API.md](./docs/API.md) - API endpoints and workflows
- [docs/CLI.md](./docs/CLI.md) - Command-line tool usage
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contributing guide & roadmap

## Security Notes

⚠️ **Before Production:**
- Change all default passwords in `docker-compose.yml`
- Set secure `KOHAKU_HUB_SESSION_SECRET`
- Set secure `LAKEFS_AUTH_ENCRYPT_SECRET_KEY`
- Use HTTPS with reverse proxy
- Only expose port 28080 (Web UI)

## Known Limitations

- Repository transfer between namespaces not fully supported
- Some HuggingFace API endpoints may be incomplete
- No rate limiting yet
- See [docs/TODO.md](./docs/TODO.md) for full list

## License

AGPL-3.0 (may change to more permissive license later)

## Support

- **Discord:** https://discord.gg/xWYrkyvJ2s
- **Issues:** https://github.com/KohakuBlueleaf/KohakuHub/issues

## Acknowledgments

- [HuggingFace](https://huggingface.co/) - API design and client library
- [LakeFS](https://lakefs.io/) - Data versioning engine (REST API)
- [MinIO](https://min.io/) - Object storage

---

**Note:** Active development. APIs may change. Not for production use yet.
