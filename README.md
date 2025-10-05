# KohakuHub: Self-Hosted HuggingFace Hub Alternative

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/KohakuBlueleaf/KohakuHub)

**⚠️ Work In Progress - Not Ready for Production**

**Join our community!: https://discord.gg/xWYrkyvJ2s**

|![1759520817420](image/README/1759520817420.png)|![1759521021890](image/README/1759521021890.png)|
|-|-|

KohakuHub is a minimal, self-hosted alternative to HuggingFace Hub that lets you host and version your own models, datasets, and other AI artifacts with full HuggingFace client compatibility.

## What is KohakuHub?

KohakuHub provides a simple but functional solution for teams and individuals who want to:

- **Host their own AI models and datasets** without relying on external services
- **Maintain version control** with Git-like branching and commits via LakeFS
- **Scale storage independently** using S3-compatible object storage
- **Keep existing workflows** with full `huggingface_hub` Python client compatibility

## Key Features

### Core Infrastructure
- ✅ **HuggingFace Compatible**: Works seamlessly with existing `huggingface_hub` client code
- ✅ **S3-Compatible Storage**: Use any S3-compatible backend (MinIO, Cloudflare R2, Wasabi, AWS S3, etc.)
- ✅ **Large File Support**: Handles files of any size with Git LFS protocol
- ✅ **File Operations**: Upload, download, copy, and delete files with automatic deduplication
- ✅ **Version Control**: Git-like branching, tagging, and commit history via LakeFS

### Repository & Organization Management
- ✅ **Complete Repository Management**: Create, delete, list, move/rename repositories with full settings control
- ✅ **Branch Management**: Create and delete branches with full version control
- ✅ **Tag Management**: Create and delete tags for release versioning
- ✅ **Repository Settings**: Configure visibility (private/public), gated access, and descriptions
- ✅ **Organization Management**: Full organization support with member roles (admin, super-admin, member)
- ✅ **Permission System**: Namespace-based permissions for repositories and organizations

### Authentication & API
- ✅ **Authentication & Authorization**: Complete user registration, session management, and API tokens
- ✅ **User Settings Management**: Update user profiles, preferences, and account settings
- ✅ **Organization Settings Management**: Configure organization-wide settings and policies
- ✅ **Detailed User Info API**: Enhanced user information endpoint (whoami-v2)
- ✅ **Version API**: Track KohakuHub version and API compatibility
- ✅ **YAML Validation**: Built-in validation for configuration files

### Web Interface
- ✅ **Modern Web UI**: Vue 3 interface with file browsing, editing, and repository management
- ✅ **Repository Settings Page**: Complete UI for managing repository configuration
- ✅ **Organization Settings Page**: Full organization management interface
- ✅ **Commit History Viewer**: Browse and explore repository history
- ✅ **Code Highlighting**: Syntax highlighting for code files with Monaco Editor integration
- ✅ **Markdown Support**: Built-in markdown rendering for documentation
- ✅ **Comprehensive Documentation**: API docs, CLI guides, roadmap, and contributing guidelines

### Command-Line Interface
- ✅ **Full-Featured CLI**: Complete command-line tool with interactive TUI mode
- ✅ **User Management**: Login, logout, whoami, register, and update user settings
- ✅ **Token Management**: Create, list, and delete API tokens
- ✅ **Organization Operations**: Create, info, list, member management, and settings updates
- ✅ **Repository Operations**: Create, delete, info, list, files, settings, and move/rename
- ✅ **Branch & Tag Management**: Create and delete branches and tags via CLI
- ✅ **Configuration Management**: Set, get, list, and clear CLI configuration
- ✅ **Multiple Output Formats**: JSON and text output for scripting and automation

## Architecture

KohakuHub combines three powerful technologies:

- **LakeFS**: Provides Git-like versioning for your data (branches, commits, diffs)
- **MinIO/S3**: Object storage backend for actual file storage
- **PostgreSQL/SQLite**: Lightweight metadata database for deduplication and indexing
- **FastAPI**: HuggingFace-compatible API layer

See [API.md](./docs/API.md) for detailed API documentation and workflow diagrams.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js and npm (or compatible package manager) for building the frontend
- Python 3.10+ (for testing with `huggingface_hub` client)
- [Optional]
    - S3 Storage (MinIO is default one which run with docker compose)
    - SMTP service (For optional email verification)

### 1. Clone the Repository

```bash
git clone https://github.com/KohakuBlueleaf/Kohaku-Hub.git
cd Kohaku-Hub
```

### 2. Configure Docker Compose

Before starting, review and customize `docker/docker-compose.yml`:

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

- `28080` - **KohakuHub Web UI (main user/API interface)**
- `48888` - KohakuHub API (for clients like `huggingface_hub`)
- `28000` - LakeFS Web UI + API
- `29000` - MinIO Web Console
- `29001` - MinIO S3 API
- `25432` - PostgreSQL (optional, for external access)

**For production deployment**, you should:
1. **Only expose port 8080** (or 443 with HTTPS) to users.
2. The Web UI will proxy requests to the API. Keep other ports internal or behind a firewall.
3. Use a reverse proxy (nginx/traefik) with HTTPS.

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

# Build Frontend and Start all services
./deploy.sh

## You can manually set them up
# npm install --prefix ./src/kohaku-hub-ui
# npm run build --prefix ./src/kohaku-hub-ui
# docker compose up -d --build
```

Services will start in this order:
1. MinIO (S3 storage)
2. PostgreSQL (metadata database)
3. LakeFS (version control)
4. KohakuHub API (backend application)
5. **KohakuHub Web UI (Nginx, fronten + reverse proxy to API server)**

### 5. Verify Installation

Check that all services are running:

```bash
docker compose ps
```

Access the web interfaces:
- **KohakuHub Web UI**: http://localhost:28080 (main interface, include API)
- **KohakuHub API Docs**: http://localhost:48888/docs (API documentation)
- **LakeFS Web UI**: http://localhost:28000 (repository browser)
- **MinIO Console**: http://localhost:29000 (storage browser)

### 6. Test with Python Client

```bash
# Install the official HuggingFace client
pip install huggingface_hub

# Run the test script
python scripts/test.py
```

The test script will:
- Create a test repository
- Upload files (both small and large)
- Download them back
- Verify content integrity

## `kohub-cli` Usage

KohakuHub includes a **complete command-line tool** with both a **Python API** for programmatic access and a **full-featured CLI** for interactive and scripted usage. The CLI provides access to all major KohakuHub features including user management, organization management, repository operations, branch/tag management, and more.

### Installation

The CLI is included in the source code. To install:

```bash
# Clone and install
git clone https://github.com/KohakuBlueleaf/KohakuHub.git
cd KohakuHub
pip install -r requirements.txt
pip install -e .
```

### Python API

Use KohakuHub programmatically in your Python scripts:

```python
from kohub_cli import KohubClient

# Initialize client
client = KohubClient(endpoint="http://localhost:8000")

# Login
client.login(username="alice", password="secret")

# Create a repository
client.create_repo("my-org/my-model", repo_type="model", private=False)

# List files
files = client.list_repo_tree("my-org/my-model", repo_type="model")

# Create an API token
token_info = client.create_token(name="my-laptop")
print(f"Token: {token_info['token']}")
```

See [CLI.md](./docs/CLI.md) for complete Python API documentation.

### Command-Line Interface

`kohub-cli` supports both interactive and command-line modes.

#### Interactive Mode (Default)

Run without arguments to launch the interactive menu:

```bash
kohub-cli
# or explicitly
kohub-cli interactive
```

#### Command-Line Mode

Use specific commands for scripting and automation:

```bash
# Authentication & User Management
kohub-cli auth login
kohub-cli auth logout
kohub-cli auth whoami
kohub-cli auth register
kohub-cli user update --display-name "Alice Smith" --bio "ML Engineer"

# Token Management
kohub-cli auth token create --name "my-laptop"
kohub-cli auth token list
kohub-cli auth token delete <token-id>

# Repository Management
kohub-cli repo create my-org/my-model --type model --private
kohub-cli repo list --type model --author my-org
kohub-cli repo info my-org/my-model --type model
kohub-cli repo files my-org/my-model --recursive
kohub-cli repo update my-org/my-model --description "My awesome model"
kohub-cli repo move my-org/my-model my-org/my-new-model
kohub-cli repo delete my-org/my-model --type model

# Branch & Tag Management
kohub-cli branch create my-org/my-model new-feature --type model
kohub-cli branch delete my-org/my-model old-feature --type model
kohub-cli tag create my-org/my-model v1.0.0 --type model
kohub-cli tag delete my-org/my-model v0.9.0 --type model

# Organization Management
kohub-cli org create my-org --description "My organization"
kohub-cli org list
kohub-cli org info my-org
kohub-cli org member add my-org bob --role member
kohub-cli org member list my-org
kohub-cli org member update my-org bob --role admin
kohub-cli org member remove my-org bob
kohub-cli org update my-org --description "Updated description"

# Configuration Management
kohub-cli config set endpoint http://localhost:8000
kohub-cli config get endpoint
kohub-cli config list
kohub-cli config clear
```

#### Global Options

All commands support these global options:

```bash
--endpoint URL          # Override endpoint (or use HF_ENDPOINT env var)
--token TOKEN           # Override token (or use HF_TOKEN env var)
--output {json,text}    # Output format (default: text)
```

Examples:
```bash
kohub-cli --endpoint http://localhost:8000 auth whoami
kohub-cli --output json repo list --type model
```

#### Getting Help

```bash
# General help
kohub-cli --help

# Command-specific help
kohub-cli auth --help
kohub-cli repo create --help
```

### CLI Features Summary

The `kohub-cli` tool provides comprehensive access to KohakuHub functionality:

- **User Management**: Full user lifecycle (register, login, logout, profile updates)
- **Token Management**: Create, list, and delete API tokens for authentication
- **Organization Management**: Complete organization operations including member management
- **Repository Management**: Full CRUD operations plus advanced features like move/rename
- **Branch & Tag Management**: Create and delete branches and tags for version control
- **Configuration Management**: Persistent configuration storage for endpoint and credentials
- **Interactive TUI**: User-friendly text-based interface for all operations
- **Multiple Output Formats**: JSON for scripting, text for human-readable output
- **Python API**: Use KohakuHub programmatically in your Python scripts

For complete CLI documentation, see [CLI.md](./docs/CLI.md).

## Using KohakuHub

### With Python Client

To interact with your private repositories, you need to provide your API token.

```python
import os
from huggingface_hub import HfApi

# Point to your KohakuHub instance
os.environ["HF_ENDPOINT"] = "http://localhost:48888"
# Provide your API token
os.environ["HF_TOKEN"] = "your_api_token_here"

api = HfApi(
    endpoint=os.environ["HF_ENDPOINT"],
    token=os.environ["HF_TOKEN"]
)

# Create a repository
api.create_repo("my-org/my-model", repo_type="model")

# Upload files
api.upload_file(
    path_or_fileobj="model.safetensors",
    path_in_repo="model.safetensors",
    repo_id="my-org/my-model",
)

# Download files
file = api.hf_hub_download(
    repo_id="my-org/my-model",
    filename="model.safetensors",
)
```

### With `hfutils`
hfutils: https://github.com/deepghs/hfutils

With `hfutils` you can also upload your whole folder easily and utilize KohakuHub in any huggingface model loader like `transformers` or `diffusers`
```bash
export HF_ENDPOINT="https://huggingface.co/"
hfutils download -t model -r KBlueLeaf/EQ-SDXL-VAE -d . -o ./eq-sdxl
export HF_ENDPOINT="http://127.0.0.1:48888/"
export HF_TOKEN="your_api_token_here"
hfutils upload -t model -r KBlueLeaf/EQ-SDXL-VAE -d . -i ./eq-sdxl
```

### Use KohakuHub in `transformers` and `diffusers`
You can utilize your model on KohakuHub in `transformers` and `diffusers` directly:

```python
import os
os.environ["HF_ENDPOINT"] = "http://127.0.0.1:48888/"
os.environ["HF_TOKEN"] = "your_api_token_here"
from diffusers import AutoencoderKL

vae = AutoencoderKL.from_pretrained("KBlueLeaf/EQ-SDXL-VAE")
```


### Accessing LakeFS Web UI

LakeFS credentials are automatically generated on first startup and stored in:
```
docker/hub-meta/hub-api/credentials.env
# or other path if you have modified docker-compose.yml
```

Use these credentials to log into the LakeFS web interface at http://localhost:28000 and browse your repositories.

## Configuration Options

For advanced configuration, you can create a `config.toml` file or use environment variables. See [config-example.toml](./config-example.toml) for all available options.

Key settings include:
- **LFS threshold**: Files larger than this use Git LFS protocol (default: 10MB)
- **Database backend**: Choose between SQLite (default) or PostgreSQL
- **Authentication**: Enable email verification, set session expiry, etc.

## Project Status & Roadmap

See [TODO.md](./docs/TODO.md) for detailed development status.

**Current Status:**
- ✅ **Core API** (upload, download, version control)
  - Complete repository management (create, delete, list, move/rename, update settings)
  - Branch management (create, delete branches)
  - Tag management (create, delete tags)
  - Commit history API
  - User and organization settings management
  - Version API endpoint
  - YAML validation API
  - Detailed user info API (whoami-v2)
  - Some Path related API may not be 100% supported, report if they are important for you.
- ✅ **HuggingFace Client Compatibility**
  - Full compatibility with `huggingface_hub` Python client
  - Works with `hfutils`, `transformers`, and `diffusers`
- ✅ **Large File Support** (Git LFS)
  - Handles files of any size with Git LFS protocol
- ✅ **Docker Deployment**
  - Complete docker-compose setup
  - Includes LakeFS, MinIO, PostgreSQL, and KohakuHub services
- ✅ **Authentication & Authorization**
  - User registration with optional email verification
  - Session-based authentication with secure cookies
  - API token generation and management
  - Permission system for repositories and organizations
- ✅ **Organization Management**
  - Create/delete organizations
  - Member management with roles (admin, super-admin, member)
  - Organization-based namespaces for repositories
  - Organization settings management
- ✅ **Web User Interface**
  - Vue 3 + Vite frontend with modern UI
  - Repository browsing and file viewing
  - Code editor with syntax highlighting (Monaco Editor)
  - File upload/download interface
  - Markdown documentation rendering
  - User authentication pages (login/register)
  - Repository and organization settings pages
  - Commit history viewer
  - Comprehensive documentation pages (API, CLI, Roadmap, Contributing)
- ✅ **Command-Line Interface (CLI)**
  - Complete user management (login, logout, whoami, register, update settings)
  - Full token management (create, list, delete)
  - Complete organization management (create, info, list, member operations, update settings)
  - Full repository management (create, delete, info, list, files, update settings, move/rename)
  - Branch and tag management (create, delete)
  - Configuration management (set, get, list, clear)
  - Interactive TUI mode
  - JSON and text output formats for scripting

## Contributing

We welcome contributions! Please read our [Contributing Guide](./CONTRIBUTING.md) to get started.

### 🎨 Web Interface (High Priority!)

We're looking for frontend developers to help build a modern web UI. Preferred stack:
- **Vue 3 + Vite** for the framework
- **UnoCSS** for styling
- Similar UX to HuggingFace Hub

If you're interested in leading the web UI development, please reach out on Discord!

### Other Contributions

- Bug reports and feature requests via GitHub Issues
- Code improvements and bug fixes via Pull Requests
- Documentation improvements
- Testing and feedback

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines.

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