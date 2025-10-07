# Contributing to KohakuHub

Thank you for your interest in contributing to KohakuHub! We welcome contributions from the community.

## Quick Links

- **Discord:** https://discord.gg/xWYrkyvJ2s (Best for discussions)
- **GitHub Issues:** Bug reports and feature requests
- **Development Guide:** See [CLAUDE.md](./CLAUDE.md)
- **Roadmap:** See [Project Status](#project-status) below

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Git

### Setup

```bash
git clone https://github.com/KohakuBlueleaf/KohakuHub.git
cd KohakuHub

# Backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Frontend
npm install --prefix ./src/kohaku-hub-ui

# Start with Docker
cp docker-compose.example.yml docker-compose.yml
# IMPORTANT: Edit docker-compose.yml to change default passwords and secrets
./deploy.sh
```

**Access:** http://localhost:28080

## Code Style

### Backend (Python)

Follow [CLAUDE.md](./CLAUDE.md) principles:
- Modern Python (match-case, async/await, native types like `list[]`, `dict[]`)
- Import order: **builtin → 3rd party → ours**, then **shorter paths first**, then **alphabetical**
  - `import os` before `from datetime import`
  - `from kohakuhub.db import` before `from kohakuhub.auth.dependencies import`
- **ALWAYS** use `db_async` wrappers for all DB operations (never direct Peewee in async code)
- Split large functions into smaller ones (especially match-case with >3 branches)
- Use `black` for code formatting
- Type hints recommended but not required (no static type checking)

### Frontend (Vue 3)

Follow [CLAUDE.md](./CLAUDE.md) principles:
- JavaScript only (no TypeScript), use JSDoc comments for type hints
- Vue 3 Composition API with `<script setup>`
- Split reusable components
- **Always** implement dark/light mode together using `dark:` classes
- Mobile responsive design
- Use `prettier` for code formatting
- UnoCSS for styling

## How to Contribute

### Reporting Bugs

Create an issue with:
- Clear title
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Python/Node version)
- Logs/error messages

### Suggesting Features

- Check [Project Status](#project-status) first
- Open GitHub issue or discuss on Discord
- Describe use case and value
- Propose implementation approach

### Contributing Code

1. Pick an issue or create one
2. Fork and create branch
3. Make changes following style guidelines
4. Test thoroughly
5. Submit pull request

## Project Status

*Last Updated: January 2025*

### ✅ Core Features (Complete)

**API & Storage:**
- HuggingFace Hub API compatibility
- Git LFS protocol for large files
- File deduplication (SHA256)
- Repository management (create, delete, list, move/rename)
- Branch and tag management
- Commit history
- S3-compatible storage (MinIO, AWS S3, etc.)
- LakeFS versioning (branches, commits, diffs) - using REST API directly via httpx

**Authentication:**
- User registration with email verification (optional)
- Session-based auth + API tokens
- Organization management with role-based access
- Permission system (namespace-based)

**Web UI:**
- Vue 3 interface with dark/light mode
- Repository browsing and file viewer
- Code editor (Monaco) with syntax highlighting
- Markdown rendering
- Commit history viewer
- Settings pages (user, org, repo)
- Documentation viewer

**CLI Tool:**
- Full-featured `kohub-cli` with interactive TUI
- Repository, organization, user management
- Branch/tag operations
- File upload/download
- Commit history viewing
- Health check
- Operation history tracking
- Shell autocomplete (bash/zsh/fish)

### 🚧 In Progress

- Rate limiting
- More granular permissions
- Repository transfer between namespaces
- Organization deletion
- Search functionality

### 📋 Planned Features

**Advanced Features:**
- Pull requests / merge requests
- Discussion/comments
- Repository stars/likes
- Download statistics
- Model/dataset card templates
- Automated model evaluation
- Multi-region CDN support
- Webhook system

**UI Improvements:**
- Branch/tag management UI
- Diff viewer for commits
- Image/media file preview
- Activity feed

**Testing & Quality:**
- Unit tests for API endpoints
- Integration tests for HF client
- E2E tests for web UI
- Performance/load testing

## Development Areas

We're especially looking for help in:

### 🎨 Frontend (High Priority)
- Improving UI/UX
- Missing pages (branch/tag management, diff viewer)
- Mobile responsiveness
- Accessibility

### 🔧 Backend
- Additional HuggingFace API compatibility
- Performance optimizations
- Advanced repository features
- Search functionality

### 📚 Documentation
- Tutorial videos
- Architecture deep-dives
- Deployment guides
- API examples

### 🧪 Testing
- Unit test coverage
- Integration tests
- E2E scenarios
- Load testing

## Pull Request Process

1. **Before submitting:**
   - Read [CLAUDE.md](./CLAUDE.md) to understand the codebase
   - Update relevant documentation (API.md, CLI.md, etc.)
   - Add tests for new functionality
   - Ensure code follows style guidelines
   - Test in both development and Docker deployment modes
   - Run `black` on Python code
   - Run `prettier` on frontend code

2. **Submitting PR:**
   - Create a clear, descriptive title
   - Describe what changes were made and why
   - Link related issues
   - Include screenshots for UI changes
   - List any breaking changes
   - Request review from maintainers

3. **After submission:**
   - Address feedback promptly
   - Keep PR focused (split large changes into multiple PRs)
   - Rebase on main if needed

## Development Workflow

**Implementation Note:** KohakuHub uses LakeFS REST API directly (httpx AsyncClient) instead of the deprecated lakefs-client library. All LakeFS operations are pure async without thread pool overhead.

### Backend Development

```bash
# Start infrastructure
docker-compose up -d lakefs minio postgres

# Run backend with hot reload
uvicorn kohakuhub.main:app --reload --port 48888

# API documentation available at:
# http://localhost:48888/docs
```

### Frontend Development

```bash
# Run frontend dev server (proxies API to localhost:48888)
npm run dev --prefix ./src/kohaku-hub-ui

# Access at http://localhost:5173
```

### Full Docker Deployment

```bash
# Build frontend and start all services
npm run build --prefix ./src/kohaku-hub-ui
docker-compose up -d --build

# View logs
docker-compose logs -f hub-api
docker-compose logs -f hub-ui
```

## Best Practices

### Database Operations

❌ **NEVER do this:**
```python
async def bad_example():
    # Direct Peewee usage in async code blocks event loop!
    repo = Repository.get_or_none(name="test")
```

✅ **ALWAYS do this:**
```python
from kohakuhub.db_async import get_repository

async def good_example():
    repo = await get_repository("model", "myorg", "mymodel")
```

### Permission Checks

Always check permissions before write operations:

```python
from kohakuhub.auth.permissions import check_repo_write_permission

async def upload_file(repo: Repository, user: User):
    # Check permission first
    check_repo_write_permission(repo, user)

    # Then proceed with operation
    ...
```

### Error Handling

Use HuggingFace-compatible error responses:

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=404,
    detail={"error": "Repository not found"},
    headers={"X-Error-Code": "RepoNotFound"}
)
```

### Logging

Use the custom logger system with colored output:

```python
from kohakuhub.logger import get_logger

logger = get_logger("MY_MODULE")

# Log different levels
logger.debug("Verbose debugging info")
logger.info("General information")
logger.success("Operation completed successfully")
logger.warning("Something unusual happened")
logger.error("An error occurred")

# Exception handling with formatted traceback
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed", e)
    # Automatically prints formatted traceback with stack frames
```

**Pre-created loggers available:**
- `logger_auth`, `logger_file`, `logger_lfs`, `logger_repo`, `logger_org`, `logger_settings`, `logger_api`, `logger_db`

### Frontend Best Practices

```vue
<script setup>
// Use composition API
import { ref, computed, onMounted } from 'vue'

// Reactive state
const data = ref(null)
const loading = ref(false)

// Computed properties
const isReady = computed(() => data.value !== null)

// Async operations
async function fetchData() {
  loading.value = true
  try {
    const response = await fetch('/api/endpoint')
    data.value = await response.json()
  } catch (error) {
    // Handle error
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <!-- Always support dark mode -->
  <div class="bg-white dark:bg-gray-900 text-black dark:text-white">
    <div v-if="loading">Loading...</div>
    <div v-else-if="isReady">{{ data }}</div>
  </div>
</template>
```

## Community

- **Discord:** https://discord.gg/xWYrkyvJ2s
- **GitHub Issues:** https://github.com/KohakuBlueleaf/KohakuHub/issues

## License

By contributing, you agree that your contributions will be licensed under AGPL-3.0.

---

Thank you for contributing to KohakuHub! 🎉
