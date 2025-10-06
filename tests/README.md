# KohakuHub API Tests

Comprehensive test suite for KohakuHub API, validating HuggingFace Hub compatibility and custom endpoints.

## Test Strategy

This test suite uses a **dual-client approach** to ensure API correctness:

1. **HuggingFace Hub Client** (`huggingface_hub`): Tests HF API compatibility
2. **Custom HTTP Client** (`requests`): Tests custom endpoints and validates API schema

### Why Dual Testing?

- **HF Client tests**: Ensure compatibility with existing HF ecosystem
- **HTTP Client tests**: Validate custom endpoints and catch reverse-engineering errors

If HF client fails but HTTP client succeeds → Our reverse-engineering of HF API is wrong
If both fail → Our implementation is broken
If both succeed → ✅ Perfect compatibility

## Prerequisites

### 1. Deploy KohakuHub Server

Tests require a running KohakuHub instance (via docker-compose):

```bash
# From project root
cp docker-compose.example.yml docker-compose.yml
# Edit docker-compose.yml with your configuration

# Build and start
npm install --prefix ./src/kohaku-hub-ui
npm run build --prefix ./src/kohaku-hub-ui
docker-compose up -d --build

# Verify server is running
curl http://localhost:28080/api/version
```

**Important**: Tests connect to `http://localhost:28080` (nginx port) by default.

### 2. Install Test Dependencies

```bash
# Install test requirements
pip install pytest pytest-xdist requests huggingface_hub

# Or from project root
pip install -e ".[test]"
```

## Configuration

Tests are configured via environment variables or defaults in `config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_ENDPOINT` | `http://localhost:28080` | KohakuHub API endpoint (use nginx port!) |
| `TEST_USERNAME` | `testuser` | Test user username |
| `TEST_EMAIL` | `test@example.com` | Test user email |
| `TEST_PASSWORD` | `testpass123` | Test user password |
| `TEST_ORG_NAME` | `testorg` | Test organization name |
| `TEST_REPO_PREFIX` | `test` | Prefix for test repositories |
| `TEST_TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `TEST_CLEANUP` | `true` | Cleanup resources after tests |

### Example: Test Against Custom Endpoint

```bash
export TEST_ENDPOINT=http://my-server.com:28080
export TEST_USERNAME=myuser
export TEST_PASSWORD=mypass
pytest tests/
```

## Running Tests

### Run All Tests

```bash
# From project root
pytest tests/

# With verbose output
pytest tests/ -v

# With coverage
pytest tests/ --cov=kohakuhub --cov-report=html
```

### Run Specific Test Files

```bash
# Authentication tests only
pytest tests/test_auth.py -v

# Repository CRUD tests
pytest tests/test_repo_crud.py -v

# File operations
pytest tests/test_file_ops.py -v

# LFS operations
pytest tests/test_lfs.py -v
```

### Run Specific Tests

```bash
# Run single test
pytest tests/test_auth.py::TestAuthentication::test_version_check -v

# Run tests matching pattern
pytest tests/ -k "upload" -v

# Run tests with specific marker
pytest tests/ -m lfs -v
```

### Test Markers

Tests are marked for easier filtering:

```bash
# Run only LFS tests
pytest tests/ -m lfs

# Skip slow tests
pytest tests/ -m "not slow"

# Run tests for specific repo type
pytest tests/test_repo_crud.py::test_create_different_repo_types[model] -v
```

Available markers:
- `lfs` - Tests requiring LFS (large files >10MB)
- `slow` - Slow running tests (files >50MB)
- `repo_type(type)` - Tests for specific repository types

### Parallel Execution

```bash
# Run tests in parallel (4 workers)
pytest tests/ -n 4

# Auto-detect CPU cores
pytest tests/ -n auto
```

**Note**: Some tests may not be thread-safe. Use with caution.

## Test Structure

```
tests/
├── __init__.py              # Package init
├── conftest.py              # Pytest fixtures and configuration
├── config.py                # Test configuration
├── base.py                  # Base test classes and utilities
├── test_auth.py            # Authentication tests
├── test_repo_crud.py       # Repository CRUD operations
├── test_file_ops.py        # File upload/download/delete
├── test_lfs.py             # Large file storage tests
└── README.md               # This file
```

## Test Categories

### 1. Authentication Tests (`test_auth.py`)

- User registration
- Login/logout flow
- Session management
- API token creation/deletion
- Token-based authentication
- `whoami` endpoint

### 2. Repository CRUD Tests (`test_repo_crud.py`)

- Repository creation (model, dataset, space)
- Repository deletion
- Repository listing
- Repository info retrieval
- Repository move/rename
- Private repository handling
- Duplicate detection

### 3. File Operations Tests (`test_file_ops.py`)

- Small file upload/download (<10MB)
- Folder upload
- File deletion
- File listing (tree API)
- File metadata (HEAD request)
- Content integrity verification
- Commit messages

### 4. LFS Tests (`test_lfs.py`)

- Large file upload (>10MB)
- LFS batch API
- File size threshold (10MB boundary)
- LFS deduplication
- Mixed file sizes
- Content integrity for large files
- LFS metadata in tree API

## Fixtures

### Session-Scoped Fixtures

Created once per test session:

- `test_config`: Test configuration
- `http_client`: Unauthenticated HTTP client
- `api_token`: API token for test user
- `authenticated_http_client`: HTTP client with auth
- `hf_client`: HuggingFace Hub client wrapper
- `test_org`: Test organization

### Function-Scoped Fixtures

Created per test function:

- `temp_repo`: Temporary repository (auto-cleanup)

### Example Usage

```python
def test_something(hf_client, temp_repo):
    """Test with HF client and temporary repository."""
    repo_id, repo_type = temp_repo

    # Upload file
    hf_client.upload_file(
        path_or_fileobj="test.txt",
        path_in_repo="test.txt",
        repo_id=repo_id,
        repo_type=repo_type,
    )

    # Repository will be cleaned up automatically
```

## Debugging

### Enable Verbose Logging

```bash
# Pytest verbose mode
pytest tests/ -vv

# Show print statements
pytest tests/ -s

# Show local variables on failure
pytest tests/ -l
```

### Run Failed Tests Only

```bash
# Run last failed tests
pytest tests/ --lf

# Run failed first, then others
pytest tests/ --ff
```

### Stop on First Failure

```bash
pytest tests/ -x
```

### Interactive Debugging

```bash
# Drop into debugger on failure
pytest tests/ --pdb

# Drop into debugger on first failure
pytest tests/ -x --pdb
```

## Common Issues

### 1. Connection Refused

**Problem**: `ConnectionRefusedError` or `Connection refused to localhost:28080`

**Solution**: Ensure KohakuHub is running:
```bash
docker-compose ps
curl http://localhost:28080/api/version
```

### 2. Wrong Port (48888)

**Problem**: Tests connecting to backend port instead of nginx

**Solution**: Use `TEST_ENDPOINT=http://localhost:28080` (nginx port)

### 3. Authentication Errors

**Problem**: `401 Unauthorized` errors

**Solution**: Check test user credentials or recreate test user:
```bash
# Delete old user from database if needed
docker-compose exec hub-api python -c "from kohakuhub.db import User; User.delete().where(User.username == 'testuser').execute()"
```

### 4. File Permission Errors

**Problem**: Cannot create temporary files

**Solution**: Check disk space and permissions for temp directory

### 5. LFS Upload Failures

**Problem**: Large file uploads timing out

**Solution**:
- Increase `TEST_TIMEOUT` environment variable
- Check MinIO is running: `docker-compose ps minio`
- Verify S3 credentials in `docker-compose.yml`

## Cleanup

Tests automatically cleanup resources if `TEST_CLEANUP=true` (default):

- Temporary repositories are deleted
- Temporary files are removed
- API tokens are revoked (optional)

### Manual Cleanup

If tests fail and leave resources:

```bash
# List test repositories
curl http://localhost:28080/api/models?author=testuser

# Delete manually via API
curl -X DELETE http://localhost:28080/api/repos/delete \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "model", "name": "test-repo-name"}'

# Or use kohub-cli
kohub-cli repo delete testuser/test-repo-name --type model
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install pytest requests huggingface_hub

    - name: Start KohakuHub
      run: |
        cp docker-compose.example.yml docker-compose.yml
        npm install --prefix ./src/kohaku-hub-ui
        npm run build --prefix ./src/kohaku-hub-ui
        docker-compose up -d --build
        sleep 30  # Wait for services to start

    - name: Run tests
      run: pytest tests/ -v

    - name: Stop services
      run: docker-compose down
```

## Contributing

When adding new tests:

1. Follow existing patterns in test files
2. Use both HF client and HTTP client where applicable
3. Add appropriate markers (`@pytest.mark.lfs`, etc.)
4. Ensure cleanup in teardown or use fixtures
5. Document test purpose in docstring
6. Update this README if adding new test categories

## Support

- **Issues**: https://github.com/KohakuBlueleaf/KohakuHub/issues
- **Discord**: https://discord.gg/xWYrkyvJ2s
- **Documentation**: `../docs/`
