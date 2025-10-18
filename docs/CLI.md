# KohakuHub CLI Documentation

*Last Updated: January 2025*

**Status:** ✅ Fully Implemented and Functional

## Quick Reference

```bash
# Authentication
kohub-cli auth login                        # Login to KohakuHub
kohub-cli auth token create --name "name"   # Create API token

# Repositories
kohub-cli repo create REPO_ID --type TYPE   # Create repository
kohub-cli repo list --type TYPE             # List repositories
kohub-cli repo ls NAMESPACE                 # List namespace repos
kohub-cli repo files REPO_ID                # List repository files
kohub-cli repo commits REPO_ID              # List commit history
kohub-cli repo commit REPO_ID COMMIT_ID     # Show commit details
kohub-cli repo commit-diff REPO_ID COMMIT   # Show commit diff

# Organizations
kohub-cli org create NAME                   # Create organization
kohub-cli org member add ORG USER --role R  # Add member

# Settings & Management
kohub-cli settings repo update REPO_ID --private        # Update repo settings
kohub-cli settings repo move FROM TO --type TYPE        # Move/rename repo
kohub-cli settings repo squash REPO_ID --type TYPE      # Squash repo history
kohub-cli settings repo branch create REPO_ID BRANCH    # Create branch
kohub-cli settings repo tag create REPO_ID TAG          # Create tag

# LFS Settings (NEW)
kohub-cli settings repo lfs get REPO_ID                                 # Get LFS settings
kohub-cli settings repo lfs threshold REPO_ID --threshold 5000000       # Set threshold
kohub-cli settings repo lfs threshold REPO_ID --reset                   # Reset to default
kohub-cli settings repo lfs versions REPO_ID --count 10                 # Set keep versions
kohub-cli settings repo lfs suffix REPO_ID --add .safetensors --add .bin  # Add suffix rules
kohub-cli settings repo lfs suffix REPO_ID --set .safetensors --set .gguf  # Set suffix rules
kohub-cli settings repo lfs suffix REPO_ID --clear                      # Clear suffix rules

# File Operations
kohub-cli settings repo upload REPO_ID FILE             # Upload file to repo
kohub-cli settings repo download REPO_ID PATH           # Download file from repo

# Configuration
kohub-cli config set KEY VALUE              # Set config value
kohub-cli config list                       # Show all config
kohub-cli config history                    # Show operation history

# Health & Diagnostics
kohub-cli health                            # Check service health

# Interactive Mode
kohub-cli interactive                       # Launch TUI mode
kohub-cli                                   # Default: launch TUI mode
```

## Overview

The KohakuHub CLI (`kohub-cli`) provides comprehensive access to KohakuHub through two interfaces:

1. **Python API (`KohubClient`)** - For programmatic access and integration
2. **Command-Line Interface** - Two modes:
   - **Interactive TUI Mode**: Full-featured menu-driven interface (default when running `kohub-cli`)
   - **Command Mode**: Click-based commands for scripting and automation (e.g., `kohub-cli repo list`)

This dual-mode design makes it easy to integrate KohakuHub into existing workflows while maintaining compatibility with HuggingFace ecosystem patterns.

## Python API Design

### Core Class: `KohubClient`

```python
from kohub_cli import KohubClient

# Initialize client
client = KohubClient(
    endpoint="http://localhost:28080",
    token="your_token_here"  # optional
)

# Or use environment variables
# HF_ENDPOINT, HF_TOKEN
client = KohubClient()
```

### User Operations

```python
# Register a new user
client.register(username="alice", email="alice@example.com", password="secret")

# Login (creates session)
session_info = client.login(username="alice", password="secret")

# Get current user info
user_info = client.whoami()

# Logout
client.logout()
```

### Token Management

```python
# Create an API token
token_info = client.create_token(name="my-laptop")
# Returns: {"token": "hf_...", "token_id": 123, ...}

# List all tokens
tokens = client.list_tokens()

# Revoke a token
client.revoke_token(token_id=123)
```

### Repository Operations

```python
# Create repository
repo = client.create_repo(
    repo_id="my-org/my-model",
    repo_type="model",  # "model", "dataset", or "space"
    private=False
)

# Delete repository
client.delete_repo(repo_id="my-org/my-model", repo_type="model")

# Get repository info
info = client.repo_info(
    repo_id="my-org/my-model",
    repo_type="model",
    revision="main"  # optional
)

# List repository files
files = client.list_repo_tree(
    repo_id="my-org/my-model",
    repo_type="model",
    revision="main",
    path="",
    recursive=False
)

# List all repositories of a type
repos = client.list_repos(repo_type="model", author="my-org", limit=50)

# List repositories under a namespace
repos = client.list_namespace_repos(
    namespace="my-org",
    repo_type="model"  # optional
)
```

### Repository Settings

```python
# Update repository settings
client.update_repo_settings(
    repo_id="my-org/my-model",
    repo_type="model",
    private=True,
    gated="auto",  # "auto", "manual", or None
)

# Update LFS settings
client.update_repo_settings(
    repo_id="my-org/my-model",
    repo_type="model",
    lfs_threshold_bytes=5000000,  # 5MB
    lfs_keep_versions=10,
    lfs_suffix_rules=[".safetensors", ".bin", ".gguf"],
)

# Get LFS settings
settings = client.get_repo_lfs_settings(
    repo_id="my-org/my-model",
    repo_type="model"
)

# Move/rename repository
client.move_repo(
    from_repo="my-org/old-name",
    to_repo="my-org/new-name",
    repo_type="model"
)

# Squash repository history
client.squash_repo(
    repo_id="my-org/my-model",
    repo_type="model"
)
```

### Branch and Tag Operations

```python
# Create branch
client.create_branch(
    repo_id="my-org/my-model",
    branch="dev",
    repo_type="model",
    revision="main"  # optional source revision
)

# Delete branch
client.delete_branch(
    repo_id="my-org/my-model",
    branch="dev",
    repo_type="model"
)

# Create tag
client.create_tag(
    repo_id="my-org/my-model",
    tag="v1.0",
    repo_type="model",
    revision="main",  # optional
    message="Release v1.0"  # optional
)

# Delete tag
client.delete_tag(
    repo_id="my-org/my-model",
    tag="v1.0",
    repo_type="model"
)
```

### Commit History

```python
# List commits
result = client.list_commits(
    repo_id="my-org/my-model",
    branch="main",
    repo_type="model",
    limit=20,
    after=None  # Pagination cursor
)
commits = result["commits"]
has_more = result["hasMore"]

# Get commit details
commit = client.get_commit_detail(
    repo_id="my-org/my-model",
    commit_id="abc1234567890",
    repo_type="model"
)

# Get commit diff
diff = client.get_commit_diff(
    repo_id="my-org/my-model",
    commit_id="abc1234567890",
    repo_type="model"
)
files = diff["files"]
```

### File Upload/Download

```python
# Upload file
result = client.upload_file(
    repo_id="my-org/my-model",
    local_path="./model.safetensors",
    repo_path="model.safetensors",
    repo_type="model",
    branch="main",
    commit_message="Upload model weights"
)

# Download file
local_path = client.download_file(
    repo_id="my-org/my-model",
    repo_path="model.safetensors",
    local_path="./downloaded_model.safetensors",
    repo_type="model",
    revision="main"
)
```

### Organization Operations

```python
# Create organization
client.create_organization(name="my-org", description="My awesome org")

# Get organization info
org = client.get_organization("my-org")

# List user's organizations
orgs = client.list_user_organizations(username="alice")

# List organization members
members = client.list_organization_members("my-org")

# Add member to organization
client.add_organization_member(
    org_name="my-org",
    username="bob",
    role="member"  # or "admin", "super-admin"
)

# Update member role
client.update_organization_member(
    org_name="my-org",
    username="bob",
    role="admin"
)

# Remove member
client.remove_organization_member(org_name="my-org", username="bob")

# Update organization settings
client.update_organization_settings(
    org_name="my-org",
    description="Updated description"
)
```

### Health Check

```python
# Check service health
health = client.health_check()
api_status = health["api"]["status"]  # "healthy", "unreachable", etc.
authenticated = health["authenticated"]
username = health["user"]  # If authenticated
```

### Configuration

```python
# Save configuration
client.save_config(
    endpoint="http://localhost:28080",
    token="hf_..."
)

# Load configuration
config = client.load_config()

# Get config file path
path = client.config_path  # ~/.kohub/config.json
```

## CLI Commands Reference

### Authentication

```bash
# Login
kohub-cli auth login
kohub-cli auth login --username alice --password secret

# Logout
kohub-cli auth logout

# Check current user
kohub-cli auth whoami

# Create token
kohub-cli auth token create --name "my-laptop"
kohub-cli auth token create -n "my-laptop"

# List tokens
kohub-cli auth token list

# Delete token
kohub-cli auth token delete --id 123
```

### Repository Operations

```bash
# Create repository
kohub-cli repo create my-model --type model
kohub-cli repo create my-org/my-model --type model --private

# Delete repository
kohub-cli repo delete my-org/my-model --type model

# Show repository info (shows downloads and likes)
kohub-cli repo info my-org/my-model --type model
kohub-cli repo info my-org/my-model --type model --revision v1.0

# List repositories
kohub-cli repo list --type model
kohub-cli repo list --type model --author my-org --limit 100

# List repositories under a namespace
kohub-cli repo ls my-org
kohub-cli repo ls my-org --type model

# List files in repository (with LFS indicators)
kohub-cli repo files my-org/my-model
kohub-cli repo files my-org/my-model --revision main --path configs/ --recursive
```

### Commit History

```bash
# List commits
kohub-cli repo commits my-org/my-model --type model
kohub-cli repo commits my-org/my-model --type model --branch main --limit 50

# Show commit details
kohub-cli repo commit my-org/my-model abc1234 --type model

# Show commit diff
kohub-cli repo commit-diff my-org/my-model abc1234 --type model
kohub-cli repo commit-diff my-org/my-model abc1234 --type model --show-diff
```

### Organization Operations

```bash
# Create organization
kohub-cli org create my-org --description "My organization"

# Show organization info
kohub-cli org info my-org

# List user's organizations
kohub-cli org list
kohub-cli org list --username alice

# Add member
kohub-cli org member add my-org bob --role member

# Update member role
kohub-cli org member update my-org bob --role admin

# Remove member
kohub-cli org member remove my-org bob
```

### Repository Settings

```bash
# Update repository settings
kohub-cli settings repo update my-org/my-model --type model --private
kohub-cli settings repo update my-org/my-model --type model --public
kohub-cli settings repo update my-org/my-model --type model --gated auto

# Move/rename repository
kohub-cli settings repo move my-org/old-name my-org/new-name --type model
kohub-cli settings repo move my-user/my-model my-org/my-model --type model

# Squash repository history (WARNING: irreversible)
kohub-cli settings repo squash my-org/my-model --type model
```

### Branch and Tag Management

```bash
# Create branch
kohub-cli settings repo branch create my-org/my-model dev --type model
kohub-cli settings repo branch create my-org/my-model feature-x --type model --revision main

# Delete branch
kohub-cli settings repo branch delete my-org/my-model dev --type model

# Create tag
kohub-cli settings repo tag create my-org/my-model v1.0 --type model
kohub-cli settings repo tag create my-org/my-model v1.0 --type model --revision main --message "Release v1.0"

# Delete tag
kohub-cli settings repo tag delete my-org/my-model v1.0 --type model
```

### LFS Settings Management

**Get current LFS settings:**
```bash
kohub-cli settings repo lfs get my-org/my-model --type model
```

**Output:**
```
LFS Threshold:
  Configured:  5.0 MB
  Effective:   5.0 MB (repository)

LFS Keep Versions:
  Configured:  10 versions
  Effective:   10 versions (repository)

LFS Suffix Rules:
  Active:      .safetensors, .bin

Server Defaults:
  Threshold:   10.0 MB
  Keep Versions: 5 versions
```

**Set LFS threshold:**
```bash
# Set to 5MB
kohub-cli settings repo lfs threshold my-org/my-model --type model --threshold 5000000

# Reset to server default
kohub-cli settings repo lfs threshold my-org/my-model --type model --reset
```

**Manage keep versions:**
```bash
# Set to keep last 10 versions
kohub-cli settings repo lfs versions my-org/my-model --type model --count 10

# Reset to server default
kohub-cli settings repo lfs versions my-org/my-model --type model --reset
```

**Manage suffix rules:**
```bash
# Add suffix rules
kohub-cli settings repo lfs suffix my-org/my-model --type model --add .safetensors --add .bin

# Set suffix rules (replaces all)
kohub-cli settings repo lfs suffix my-org/my-model --type model --set .safetensors --set .gguf

# Remove specific suffix
kohub-cli settings repo lfs suffix my-org/my-model --type model --remove .bin

# Clear all suffix rules
kohub-cli settings repo lfs suffix my-org/my-model --type model --clear
```

### File Operations

```bash
# Upload file to repository
kohub-cli settings repo upload my-org/my-model model.safetensors --type model
kohub-cli settings repo upload my-org/my-model ./weights/model.bin --path weights/model.bin --type model --branch main --message "Upload model weights"

# Download file from repository
kohub-cli settings repo download my-org/my-model model.safetensors --type model
kohub-cli settings repo download my-org/my-model weights/model.bin -o ./local-model.bin --type model --revision v1.0
```

### User Settings

```bash
# Update user settings
kohub-cli settings user update --email newemail@example.com
```

### Organization Settings

```bash
# Update organization settings
kohub-cli settings organization update my-org --description "New description"

# List organization members
kohub-cli settings organization members my-org
```

### Configuration

```bash
# Set endpoint
kohub-cli config set endpoint http://localhost:28080

# Set token
kohub-cli config set token hf_...

# Get current endpoint
kohub-cli config get endpoint

# Show all configuration
kohub-cli config list

# Show operation history
kohub-cli config history
kohub-cli config history --limit 20

# Clear operation history
kohub-cli config clear-history

# Clear configuration
kohub-cli config clear
```

### Health Check

```bash
# Check service health
kohub-cli health
kohub-cli --output json health
```

**Output:**
```
KohakuHub Health Check

✓ API: Healthy
  Site: KohakuHub
  Version: 0.0.1
  Endpoint: http://localhost:28080

✓ Auth: Authenticated as alice
```

### Interactive Mode

```bash
# Launch interactive TUI
kohub-cli interactive

# Or just run without arguments (default behavior)
kohub-cli
```

### Global Options

All commands support these global options:

```bash
--endpoint URL          # Override endpoint (or use HF_ENDPOINT env var)
--token TOKEN           # Override token (or use HF_TOKEN env var)
--output {json,text}    # Output format (default: text)
--help                  # Show help
```

Examples:
```bash
kohub-cli --endpoint http://localhost:28080 auth whoami
kohub-cli --output json repo list --type model
kohub-cli --token hf_xxxxx repo create my-model --type model
```

## Configuration File Format

Located at `~/.kohub/config.json`:

```json
{
  "endpoint": "http://localhost:28080",
  "token": "hf_...",
  "default_repo_type": "model",
  "interactive_mode_default": true
}
```

## Error Handling

### Python API

```python
from kohub_cli import KohubClient, KohubError, AuthenticationError, NotFoundError

client = KohubClient()

try:
    client.create_repo("my-repo", repo_type="model")
except AuthenticationError:
    print("Please login first")
except NotFoundError as e:
    print(f"Not found: {e}")
except KohubError as e:
    print(f"Error: {e}")
```

### CLI

```bash
$ kohub-cli repo create my-repo --type model
Error: Authentication required. Please login with 'kohub-cli auth login'

$ kohub-cli repo info nonexistent/repo --type model
Error: Repository not found: nonexistent/repo

$ kohub-cli --output json repo info nonexistent/repo --type model
{"error": "Repository not found", "code": "RepoNotFound", "details": "nonexistent/repo"}
```

## Environment Variables

- `HF_ENDPOINT` - KohakuHub endpoint URL (default: `http://localhost:28080`)
- `HF_TOKEN` - API token for authentication
- `KOHUB_CONFIG_DIR` - Config directory (default: `~/.kohub`)

## Interactive TUI Mode

The interactive TUI mode provides a full-featured menu-driven interface for managing KohakuHub. It's perfect for:
- Exploring available operations
- Interactive navigation with breadcrumb context
- Visual feedback and rich formatting
- Guided workflows with confirmation prompts

**Features:**
- Context-aware navigation (browse repos → select repo → manage files/commits)
- Error handling with helpful suggestions
- Session management with persistent config
- Rich UI with tables, panels, and progress indicators
- Support for Ctrl+C to go back at any prompt

**Access:**
```bash
kohub-cli                # Default: launches interactive mode
kohub-cli interactive    # Explicit: launches interactive mode
```

## Output Formatting

### Text Mode (Default)

Uses Rich library for beautiful terminal output:
- Tables for lists
- Panels for detailed information
- Color-coded badges
- Icons for file types
- Progress indicators

**Examples:**

**Repository info with stats:**
```
┌─ Model Repository ──────────────────────────────────────┐
│ org/my-model                                             │
│ ────────────────────────────────────────────────────────│
│ Author:        org                                       │
│ Type:          model                                     │
│ Visibility:    🌐 Public                                 │
│ Created:       2025-01-15T12:00:00Z                      │
│                                                          │
│ Downloads:     1234                                      │
│ Likes:         42                                        │
└──────────────────────────────────────────────────────────┘
```

**File listing with LFS indicators:**
```
org/my-model (main)
├── 📁 configs
│   └── 📄 config.json (1.2 KB)
├── 📄 README.md (5.0 KB)
└── 📄 model.safetensors (5.2 GB) (LFS)
```

### JSON Mode

Machine-readable output for scripting:

```bash
kohub-cli --output json repo info my-org/my-model --type model
```

```json
{
  "id": "my-org/my-model",
  "author": "my-org",
  "private": false,
  "downloads": 1234,
  "likes": 42,
  "createdAt": "2025-01-15T12:00:00Z"
}
```

## Advanced Features

### Operation History Tracking

The CLI automatically tracks all operations in a history file:

```bash
# View recent operations
kohub-cli config history --limit 20
```

**Example output:**
```
┌─ Recent Operations ────────────────────────────────────┐
│ Time               │ Operation    │ Details            │
├────────────────────┼──────────────┼────────────────────┤
│ 2025-01-15 12:30   │ create_repo  │ repo=org/model     │
│ 2025-01-15 12:25   │ login        │ username=alice     │
│ 2025-01-15 12:20   │ create_token │ name=my-laptop     │
└────────────────────────────────────────────────────────┘
```

### Autocomplete Support

Future feature: Shell autocomplete for bash/zsh/fish

## Command Structure Overview

```
kohub-cli
├── auth
│   ├── login           # Login with username/password
│   ├── logout          # Logout current session
│   ├── whoami          # Show current user
│   └── token
│       ├── create      # Create new API token
│       ├── list        # List all tokens
│       └── delete      # Delete a token
├── repo
│   ├── create          # Create repository
│   ├── delete          # Delete repository
│   ├── info            # Show repository info (with downloads/likes)
│   ├── list            # List repositories
│   ├── ls              # List repositories under a namespace
│   ├── files           # List repository files (with LFS indicators)
│   ├── commits         # List commit history
│   ├── commit          # Show commit details
│   └── commit-diff     # Show commit diff
├── org
│   ├── create          # Create organization
│   ├── info            # Show organization info
│   ├── list            # List user's organizations
│   └── member
│       ├── add         # Add member to org
│       ├── remove      # Remove member from org
│       └── update      # Update member role
├── settings
│   ├── user
│   │   └── update      # Update user settings
│   ├── repo
│   │   ├── update      # Update repository settings
│   │   ├── move        # Move/rename repository
│   │   ├── squash      # Squash repository history
│   │   ├── upload      # Upload file to repository
│   │   ├── download    # Download file from repository
│   │   ├── branch
│   │   │   ├── create  # Create branch
│   │   │   └── delete  # Delete branch
│   │   ├── tag
│   │   │   ├── create  # Create tag
│   │   │   └── delete  # Delete tag
│   │   └── lfs         # LFS settings management (NEW)
│   │       ├── get     # Get LFS settings
│   │       ├── threshold  # Set/reset threshold
│   │       ├── versions   # Set/reset keep versions
│   │       └── suffix     # Manage suffix rules
│   └── organization
│       ├── update      # Update organization settings
│       └── members     # List organization members
├── config
│   ├── set             # Set configuration value
│   ├── get             # Get configuration value
│   ├── list            # Show all configuration
│   ├── clear           # Clear all configuration
│   ├── history         # Show operation history
│   └── clear-history   # Clear operation history
├── health              # Check service health
└── interactive         # Launch interactive TUI mode
```

## Implementation Status

### ✅ Phase 1: Python API (COMPLETED)
- [x] Create `KohubClient` class
- [x] Implement user operations
- [x] Implement token management
- [x] Implement organization operations
- [x] Implement repository operations
- [x] Add proper error classes
- [x] Add configuration management
- [x] File upload/download support
- [x] LFS settings management

### ✅ Phase 2: CLI Commands (COMPLETED)
- [x] Set up Click command structure
- [x] Implement `auth` commands
- [x] Implement `repo` commands
- [x] Implement `org` commands
- [x] Implement `config` commands
- [x] Implement `settings` commands (user, repo, organization)
- [x] Add global options support
- [x] Add output formatting (JSON/text)
- [x] Implement branch/tag management
- [x] Rich output formatting with tables and panels
- [x] LFS settings commands
- [x] Operation history tracking

### ✅ Phase 3: Enhanced Features (COMPLETED)
- [x] Rich output formatting with tables
- [x] Operation history tracking
- [x] Health check command
- [x] File upload/download commands
- [x] Commit history viewing
- [x] Repository squash command
- [x] Config history management
- [x] LFS settings management
- [x] Pretty-printed displays

### 📋 Phase 4: Future Enhancements
- [ ] Bash/Zsh/Fish completion scripts
- [ ] Progress bars for long operations
- [ ] Configuration wizard
- [ ] Batch operations support
- [ ] Plugin system
- [ ] Alias support
- [ ] History undo functionality

## Dual-Mode Design

Both command mode and interactive TUI mode are fully implemented and production-ready:

- **Command Mode**: Best for scripting, automation, CI/CD pipelines
- **Interactive Mode**: Best for exploration, learning, and interactive management

Use whichever mode fits your workflow!

## Success Metrics

1. **Usability**: 90% of operations possible via CLI without interactive mode ✅
2. **API Coverage**: 100% of HTTP endpoints wrapped in Python API ✅
3. **Documentation**: Every function/command has examples ✅
4. **Performance**: CLI commands respond in <1s for metadata operations ✅

## Testing

### Unit Tests
```python
def test_create_repo():
    client = KohubClient(endpoint="http://test", token="test_token")
    with mock_http_response(200, {"repo_id": "test/repo"}):
        result = client.create_repo("test/repo", repo_type="model")
        assert result["repo_id"] == "test/repo"
```

### Integration Tests
```bash
# Test CLI commands
kohub-cli --endpoint http://test-server:8000 auth login --username test --password test
kohub-cli repo create test-repo --type model
kohub-cli repo info test-repo --type model
kohub-cli repo delete test-repo --type model
```

## Future Considerations

1. **Async Support**: `AsyncKohubClient` for async Python applications
2. **Streaming**: Progress callbacks for large operations
3. **Caching**: Cache repo metadata locally
4. **Webhooks**: CLI support for webhook management
5. **Desktop App**: Electron wrapper for non-technical users
