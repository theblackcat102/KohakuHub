# Contributing to KohakuHub

*Last Updated: October 2025*

Thank you for your interest in contributing to KohakuHub! We welcome contributions from the community and are excited to have you here.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [How to Contribute](#how-to-contribute)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

## Getting Started

Before you begin:
- Read the [README.md](./README.md) to understand what KohakuHub does
- Check out our [TODO.md](./docs/TODO.md) to see what needs to be done
- Join our [Discord community](https://discord.gg/xWYrkyvJ2s) to discuss your ideas

## Development Setup

### Prerequisites

- **Python 3.10+**: Backend development
- **Node.js 18+**: Frontend development
- **Docker & Docker Compose**: For running the full stack
- **Git**: Version control

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/KohakuBlueleaf/KohakuHub.git
   cd KohakuHub
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Install frontend dependencies**
   ```bash
   cd src/kohaku-hub-ui
   npm install
   ```

4. **Start development environment**
   ```bash
   # From project root
   ./deploy.sh
   ```

5. **Access the services**
   - KohakuHub Web UI: http://localhost:28080
   - KohakuHub API: http://localhost:48888
   - API Documentation: http://localhost:48888/docs

## Project Structure

```
KohakuHub/
├── src/
│   ├── kohakuhub/          # Backend (FastAPI)
│   │   ├── api/            # API endpoints
│   │   ├── auth/           # Authentication & authorization
│   │   ├── org/            # Organization management
│   │   ├── db.py           # Database models
│   │   └── main.py         # Application entry point
│   ├── kohub_cli/          # CLI tool
│   │   ├── cli.py          # CLI commands
│   │   ├── client.py       # Python API client
│   │   └── main.py         # CLI entry point
│   └── kohaku-hub-ui/      # Frontend (Vue 3 + Vite)
│       ├── src/
│       │   ├── components/ # Reusable components
│       │   ├── pages/      # Page components
│       │   ├── stores/     # State management (Pinia)
│       │   └── utils/      # Utility functions
│       └── vite.config.js
├── docker/                  # Docker compose files
├── docs/                    # Documentation
│   ├── API.md              # API documentation
│   ├── CLI.md              # CLI documentation
│   └── TODO.md             # Development roadmap
├── scripts/                 # Utility scripts
└── README.md
```

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue on GitHub with:
- **Clear title**: Describe the issue concisely
- **Steps to reproduce**: How can we recreate the bug?
- **Expected behavior**: What should happen?
- **Actual behavior**: What actually happens?
- **Environment**: OS, Python version, Docker version, etc.
- **Logs**: Include relevant error messages or logs

### Suggesting Features

We welcome feature suggestions! Please:
- Check if the feature is already in [TODO.md](./docs/TODO.md)
- Open a GitHub issue or discuss on Discord
- Describe the use case and why it's valuable
- Propose how it might work

### Contributing Code

1. **Pick an issue** or create one describing what you plan to work on
2. **Fork the repository** and create a new branch
3. **Make your changes** following our code style guidelines
4. **Test your changes** thoroughly
5. **Submit a pull request** with a clear description

## Code Style Guidelines

### Backend (Python)

Follow the guidelines in [CLAUDE.md](./CLAUDE.md):
- **Modern Python**: Use match-case, async/await, type hints
- **Import order**: builtin → 3rd party → our package (alphabetical)
- **Type hints**: Use native types (`dict` not `Dict`)
- **Clean code**: Split large functions into smaller ones
- **Async operations**: Use dedicated threadpools (S3/LakeFS/DB)
  - S3 operations → `run_in_s3_executor()`
  - LakeFS operations → `run_in_lakefs_executor()`
  - DB operations → `db_async` module wrappers

```python
from typing import Optional
from fastapi import APIRouter, HTTPException

def create_repository(
    repo_id: str,
    repo_type: str,
    private: bool = False
) -> dict:
    """Create a new repository.

    Args:
        repo_id: Full repository ID (namespace/name)
        repo_type: Type of repository (model, dataset, space)
        private: Whether the repository is private

    Returns:
        Dictionary with repository information

    Raises:
        HTTPException: If repository already exists
    """
    pass
```

### Frontend (Vue 3 + JavaScript)

Follow the guidelines in [CLAUDE.md](./CLAUDE.md):
- **JavaScript only** - No TypeScript, use JSDoc for type hints
- **Split reusable components** - One component per file
- **Dark/light mode** - Implement both at once
- **Mobile responsive** - Consider auto-break lines
- **Composition API**: Use `<script setup>` syntax
- **Styling**: UnoCSS utility classes

```vue
<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

/**
 * @typedef {Object} Props
 * @property {string} repoId - Repository ID
 * @property {string} repoType - Repository type (model/dataset/space)
 */

const props = defineProps({
  repoId: String,
  repoType: String
})

const router = useRouter()

/** @type {import('vue').Ref<Array<Object>>} */
const files = ref([])

const isLoading = computed(() => files.value.length === 0)
</script>

<template>
  <div class="container mx-auto p-4">
    <h1 class="text-2xl font-bold">{{ repoId }}</h1>
    <!-- Content -->
  </div>
</template>
```

### CLI (Python)

- Follow backend Python guidelines
- Use **Click** for command-line interface
- Provide helpful error messages
- Support both interactive and non-interactive modes

## Testing

### Backend Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=kohakuhub
```

### Frontend Testing

```bash
cd src/kohaku-hub-ui

# Run unit tests
npm run test

# Run E2E tests
npm run test:e2e
```

### Manual Testing

1. Start the development environment
2. Test your changes through the Web UI
3. Test API endpoints using the interactive docs at http://localhost:48888/docs
4. Test CLI commands: `kohub-cli [command]`

## Pull Request Process

1. **Update documentation**: If you add features, update relevant docs
2. **Add tests**: Include tests for new functionality
3. **Update CHANGELOG**: Add entry for your changes (if applicable)
4. **Ensure CI passes**: All automated checks must pass
5. **Request review**: Tag maintainers for review
6. **Address feedback**: Respond to review comments promptly

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How did you test these changes?

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No new warnings generated
```

## Development Areas

We're especially looking for help in these areas:

### 🎨 Frontend Development (High Priority)
- Improving the Vue 3 UI/UX
- Adding missing pages (commit history, diff viewer, etc.)
- Mobile responsiveness
- Accessibility improvements

### 🔧 Backend Features
- Additional HuggingFace API compatibility
- Performance optimizations
- Advanced repository features (branches, PRs)
- Search functionality

### 📚 Documentation
- Tutorial videos
- Architecture deep-dives
- Deployment guides
- API examples

### 🧪 Testing
- Unit test coverage
- Integration tests
- E2E test scenarios
- Load testing

### 🔨 CLI Tools
- Additional administrative commands
- File upload/download features
- Batch operations

## Community

- **Discord**: https://discord.gg/xWYrkyvJ2s (Best for real-time discussion)
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Design discussions and questions

## Questions?

Don't hesitate to ask! We're here to help:
- Join our Discord and ask in the #dev channel
- Open a GitHub Discussion
- Comment on related issues

## License

By contributing to KohakuHub, you agree that your contributions will be licensed under the AGPL-3.0 license.

---

Thank you for contributing to KohakuHub! 🎉
