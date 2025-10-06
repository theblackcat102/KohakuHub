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
./deploy.sh
```

**Access:** http://localhost:28080

## Code Style

### Backend (Python)

Follow [CLAUDE.md](./CLAUDE.md) principles:
- Modern Python (match-case, async/await, native types)
- Import order: builtin → 3rd party → our package (alphabetical)
- Use `db_async` wrappers for all DB operations
- Split large functions into smaller ones

### Frontend (Vue 3)

Follow [CLAUDE.md](./CLAUDE.md) principles:
- JavaScript only (no TypeScript), use JSDoc for types
- Split reusable components
- Implement dark/light mode together
- Mobile responsive

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
- LakeFS versioning (branches, commits, diffs)

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

1. Update documentation if adding features
2. Add tests for new functionality
3. Ensure code follows style guidelines
4. Request review from maintainers
5. Address feedback promptly

## Community

- **Discord:** https://discord.gg/xWYrkyvJ2s
- **GitHub Issues:** https://github.com/KohakuBlueleaf/KohakuHub/issues

## License

By contributing, you agree that your contributions will be licensed under AGPL-3.0.

---

Thank you for contributing to KohakuHub! 🎉
