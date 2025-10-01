# KohakuHub: Self-Hosted HuggingFace Hub Alternative

**⚠️ Work In Progress - Not Ready for Production**

**Join our community!: https://discord.gg/xWYrkyvJ2s**


KohakuHub is a minimal, self-hosted alternative to HuggingFace Hub that lets you host and version your own models, datasets, and other AI artifacts with full HuggingFace client compatibility.

## What is KohakuHub?

KohakuHub provides a simple but functional solution for teams and individuals who want to:

- **Host their own AI models and datasets** without relying on external services
- **Maintain version control** with Git-like branching and commits via LakeFS
- **Scale storage independently** using S3-compatible object storage
- **Keep existing workflows** with full `huggingface_hub` Python client compatibility

## Key Features

- ✅ **HuggingFace Compatible**: Works seamlessly with existing `huggingface_hub` client code
- ✅ **S3-Compatible Storage**: Use any S3-compatible backend (MinIO, Cloudflare R2, Wasabi, AWS S3, etc.) - pick the one that fits your budget and performance needs
- ✅ **Repository Management**: Create, list, and delete model/dataset/space repositories
- ✅ **File Operations**: Upload, download, copy, and delete files with automatic deduplication
- ✅ **Large File Support**: Handles files of any size with Git LFS protocol
- ✅ **Version Control**: Git-like branching and commit history via LakeFS
- 🚧 **Web UI**: Coming soon (contributions welcome!)
- 🚧 **Authentication**: Basic auth system (under development)

## Architecture

KohakuHub combines three powerful technologies:

- **LakeFS**: Provides Git-like versioning for your data (branches, commits, diffs)
- **MinIO/S3**: Object storage backend for actual file storage
- **PostgreSQL/SQLite**: Lightweight metadata database for deduplication and indexing
- **FastAPI**: HuggingFace-compatible API layer

See [API.md](./API.md) for detailed API documentation and workflow diagrams.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for testing with `huggingface_hub` client)

### 1. Clone the Repository

```bash
git clone https://github.com/KohakuBlueleaf/Kohaku-Hub.git
cd Kohaku-Hub
```

### 2. Configure Docker Compose

Before starting, review and customize `docker-compose.yml`:

#### **Important: Security Configuration**

⚠️ **Change Default Passwords!** The default configuration uses weak credentials. For any serious deployment:

```yaml
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
```

#### **Port Configuration**

The default setup exposes these ports:

- `48888` - KohakuHub API (main interface)
- `28000` - LakeFS Web UI + API
- `29000` - MinIO Web Console
- `29001` - MinIO S3 API
- `25432` - PostgreSQL (optional, for external access)

**For production deployment**, you should:
1. **Only expose port 48888** (KohakuHub API) to users
2. Keep other ports internal or behind a firewall
3. Use a reverse proxy (nginx/traefik) with HTTPS

#### **Public Endpoint Configuration**

If deploying on a server, update these environment variables:

```yaml
environment:
  # Replace with your actual domain/IP
  - KOHAKU_HUB_BASE_URL=https://your-domain.com
  - KOHAKU_HUB_S3_PUBLIC_ENDPOINT=https://s3.your-domain.com
```

The S3 public endpoint is used for generating download URLs. It should point to wherever your MinIO S3 API is accessible (port 29001 by default).

### 3. Start the Services

```bash
# Set user/group ID for proper permissions
export UID=$(id -u)
export GID=$(id -g)

# Start all services
docker compose up -d --build
```

Services will start in this order:
1. MinIO (S3 storage)
2. PostgreSQL (metadata database)
3. LakeFS (version control)
4. KohakuHub API (main application)

### 4. Verify Installation

Check that all services are running:

```bash
docker compose ps
```

Access the web interfaces:
- **KohakuHub API**: http://localhost:48888/docs (API documentation)
- **LakeFS Web UI**: http://localhost:28000 (repository browser)
- **MinIO Console**: http://localhost:29000 (storage browser)

### 5. Test with Python Client

```bash
# Install the official HuggingFace client
pip install huggingface_hub

# Run the test script
python test.py
```

The test script will:
- Create a test repository
- Upload files (both small and large)
- Download them back
- Verify content integrity

## Using KohakuHub

### With Python Client

```python
import os
from huggingface_hub import HfApi

# Point to your KohakuHub instance
os.environ["HF_ENDPOINT"] = "http://localhost:48888"
api = HfApi(endpoint="http://localhost:48888")

# Create a repository
api.create_repo("myorg/mymodel", repo_type="model")

# Upload files
api.upload_file(
    path_or_fileobj="model.safetensors",
    path_in_repo="model.safetensors",
    repo_id="myorg/mymodel",
)

# Download files
file = api.hf_hub_download(
    repo_id="myorg/mymodel",
    filename="model.safetensors",
)
```

That's it! All existing `huggingface_hub` code works without modification.

### With `hfutils`
hfutils: https://github.com/deepghs/hfutils

With `hfutils` you can also upload your whole folder easily and utilize KohakuHub in any huggingface model loader like `transformers` or `diffusers`
```bash
export HF_ENDPOINT="https://huggingface.co/"
hfutils download -t model -r KBlueLeaf/EQ-SDXL-VAE -d . -o ./eq-sdxl
export HF_ENDPOINT="http://127.0.0.1:48888/"
hfutils upload -t model -r KBlueLeaf/EQ-SDXL-VAE -d . -i ./eq-sdxl
```

### Use KohakuHub in `transformers` and `diffusers`
You can utilize your model on KohakuHub in `transformers` and `diffusers` directly:

```python
import os
os.environ["HF_ENDPOINT"] = "http://127.0.0.1:48888/"
from diffusers import AutoencoderKL

vae = AutoencoderKL.from_pretrained("KBlueLeaf/EQ-SDXL-VAE")
```


### Accessing LakeFS Web UI

LakeFS credentials are automatically generated on first startup and stored in:
```
hub-meta/hub-api/credentials.env
```

Use these credentials to log into the LakeFS web interface at http://localhost:28000 and browse your repositories.

## Configuration Options

For advanced configuration, you can create a `config.toml` file or use environment variables. See [config-example.toml](./config-example.toml) for all available options.

Key settings include:
- **LFS threshold**: Files larger than this use Git LFS protocol (default: 10MB)
- **Database backend**: Choose between SQLite (default) or PostgreSQL
- **Storage paths**: Customize where metadata and files are stored

## Project Status & Roadmap

See [TODO.md](./TODO.md) for detailed development status.

**Current Status:**
- ✅ Core API (upload, download, version control)
- ✅ HuggingFace client compatibility
- ✅ Large file support (Git LFS)
- ✅ Docker deployment
- 🚧 Authentication & authorization
- 🚧 Web user interface
- 🚧 Organization management

## Contributing

We welcome contributions! Especially:

### 🎨 Web Interface (High Priority!)

We're looking for frontend developers to help build a modern web UI. Preferred stack:
- **Vue 3 + Vite** for the framework
- **Tailwind CSS** for styling
- Similar UX to HuggingFace Hub

If you're interested in leading the web UI development, please reach out on Discord!

### Other Contributions

- Bug reports and feature requests via GitHub Issues
- Code improvements and bug fixes via Pull Requests
- Documentation improvements
- Testing and feedback

Join our community on Discord: https://discord.gg/xWYrkyvJ2s

## License

Currently licensed under **AGPL-3.0**. The license may be updated to a more permissive option after initial development is complete.

## Acknowledgments

- [HuggingFace](https://huggingface.co/) for the amazing Hub platform and client library
- [LakeFS](https://lakefs.io/) for Git-like data versioning
- [MinIO](https://min.io/) for S3-compatible object storage

## Support & Community

- **Discord**: https://discord.gg/xWYrkyvJ2s
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Design discussions and questions

---

**Note**: This project is in active development. APIs may change, and features may be incomplete. Not recommended for production use yet.