# KohakuHub CLI Design Document

## Overview

The KohakuHub CLI (`kohub-cli`) should provide both a **Python API** for programmatic access and a **command-line interface** for interactive and scripted usage. This design aims to make it easy to integrate KohakuHub into existing workflows while maintaining compatibility with HuggingFace ecosystem patterns.

## Design Goals

1. **Python API First**: Expose all functionality through a clean Python API (similar to `huggingface_hub.HfApi`)
2. **CLI as a Wrapper**: Build CLI commands on top of the Python API
3. **Dual Mode**: Support both interactive (TUI) and non-interactive (scripted) modes
4. **Configuration Management**: Easy endpoint and credential management
5. **HuggingFace Compatibility**: Similar patterns and naming conventions where applicable
6. **Extensibility**: Easy to add new features without breaking existing code

## Architecture

```
┌─────────────────────────────────────────────┐
│         CLI Interface (Click)               │
│  - kohub-cli [command] [options]            │
│  - Interactive TUI mode                     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│       Python API (KohubClient)              │
│  - User operations                          │
│  - Organization operations                  │
│  - Repository operations                    │
│  - Token management                         │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│      HTTP Client (requests.Session)         │
│  - KohakuHub REST API                       │
└─────────────────────────────────────────────┘
```

## Python API Design

### Core Class: `KohubClient`

```python
from kohub_cli import KohubClient

# Initialize client
client = KohubClient(
    endpoint="http://localhost:8000",
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

### Organization Operations

```python
# Create organization
client.create_organization(name="my-org", description="My awesome org")

# Get organization info
org = client.get_organization("my-org")

# List user's organizations
orgs = client.list_user_organizations(username="alice")

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
info = client.repo_info(repo_id="my-org/my-model", repo_type="model")

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
```

### Configuration

```python
# Save configuration
client.save_config(
    endpoint="http://localhost:8000",
    token="hf_..."
)

# Load configuration
config = client.load_config()

# Get config file path
path = client.config_path  # ~/.kohub/config.json
```

## CLI Design

### Command Structure

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
│   ├── info            # Show repository info
│   ├── list            # List repositories
│   └── files           # List repository files
├── org
│   ├── create          # Create organization
│   ├── info            # Show organization info
│   ├── list            # List user's organizations
│   └── member
│       ├── add         # Add member to org
│       ├── remove      # Remove member from org
│       └── update      # Update member role
├── config
│   ├── set             # Set configuration value
│   ├── get             # Get configuration value
│   └── list            # Show all configuration
└── interactive         # Launch interactive TUI mode
```

### Command Examples

#### Authentication

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

#### Repository Operations

```bash
# Create repository
kohub-cli repo create my-model --type model
kohub-cli repo create my-org/my-model --type model --private

# Delete repository
kohub-cli repo delete my-org/my-model --type model

# Show repository info
kohub-cli repo info my-org/my-model --type model

# List repositories
kohub-cli repo list --type model
kohub-cli repo list --type model --author my-org

# List files in repository
kohub-cli repo files my-org/my-model
kohub-cli repo files my-org/my-model --revision main --path configs/ --recursive
```

#### Organization Operations

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

#### Configuration

```bash
# Set endpoint
kohub-cli config set endpoint http://localhost:8000

# Set token
kohub-cli config set token hf_...

# Get current endpoint
kohub-cli config get endpoint

# Show all configuration
kohub-cli config list

# Clear configuration
kohub-cli config clear
```

#### Interactive Mode

```bash
# Launch interactive TUI (current behavior)
kohub-cli interactive

# Or just run without arguments
kohub-cli
```

### Global Options

All commands support these global options:

```bash
--endpoint URL          # Override endpoint (or use HF_ENDPOINT env var)
--token TOKEN           # Override token (or use HF_TOKEN env var)
--output {json,text}    # Output format (default: text)
--quiet                 # Suppress non-essential output
--verbose               # Show detailed output
--help                  # Show help
```

Examples:
```bash
kohub-cli --endpoint http://localhost:8000 auth whoami
kohub-cli --output json repo list --type model
kohub-cli --quiet repo create my-model --type model
```

## Configuration File Format

Located at `~/.kohub/config.json`:

```json
{
  "endpoint": "http://localhost:8000",
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

- `HF_ENDPOINT` - KohakuHub endpoint URL (default: `http://localhost:8000`)
- `HF_TOKEN` - API token for authentication
- `KOHUB_CONFIG_DIR` - Config directory (default: `~/.kohub`)

## Migration from Current Implementation

### Compatibility

1. Keep existing `main_menu()` function for backward compatibility
2. Make it accessible via `kohub-cli interactive`
3. If no arguments provided, launch interactive mode (current behavior)

### Deprecation Path

1. v0.1.x - Add new API and CLI commands alongside interactive mode
2. v0.2.x - Recommend new CLI commands in help text
3. v0.3.x - Default to CLI commands, require `--interactive` for TUI

## Implementation Phases

### Phase 1: Python API (Priority: High)
- [ ] Create `KohubClient` class
- [ ] Implement user operations
- [ ] Implement token management
- [ ] Implement organization operations
- [ ] Implement repository operations
- [ ] Add proper error classes
- [ ] Add configuration management

### Phase 2: CLI Commands (Priority: High)
- [ ] Set up Click command structure
- [ ] Implement `auth` commands
- [ ] Implement `repo` commands
- [ ] Implement `org` commands
- [ ] Implement `config` commands
- [ ] Add global options support
- [ ] Add output formatting (JSON/text)

### Phase 3: Enhanced Features (Priority: Medium)
- [ ] Bash/Zsh completion scripts
- [ ] Progress bars for operations
- [ ] Rich output formatting with tables
- [ ] Configuration wizard
- [ ] Batch operations support

### Phase 4: Advanced Features (Priority: Low)
- [ ] Plugin system
- [ ] Alias support
- [ ] History and undo
- [ ] Integration with git
- [ ] File upload/download commands (if needed beyond hfutils)

## Testing Strategy

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

## Documentation Requirements

1. **API Reference** - Auto-generated from docstrings
2. **CLI Reference** - Auto-generated from Click commands
3. **Tutorials** - Getting started, common workflows
4. **Examples** - Python scripts and shell scripts

## Success Metrics

1. **Usability**: 90% of operations possible via CLI without interactive mode
2. **API Coverage**: 100% of HTTP endpoints wrapped in Python API
3. **Documentation**: Every function/command has examples
4. **Testing**: >80% code coverage
5. **Performance**: CLI commands respond in <1s for metadata operations

## Future Considerations

1. **Async Support**: `AsyncKohubClient` for async Python applications
2. **Streaming**: Progress callbacks for large operations
3. **Caching**: Cache repo metadata locally
4. **Webhooks**: CLI support for webhook management
5. **Desktop App**: Electron wrapper for non-technical users
