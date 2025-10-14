# Commit Management Module

## Overview

The `commit` module provides comprehensive Git-like commit management functionality for KohakuHub repositories. It handles atomic commit operations, commit history retrieval, and diff generation, supporting both regular files and Git LFS (Large File Storage) objects. This module bridges the gap between HuggingFace Hub API compatibility and the underlying LakeFS storage system.

## Purpose and Functionality

This module serves as the core commit interface for KohakuHub, enabling users to:

- Create atomic commits with multiple file operations in a single transaction
- Retrieve commit history with pagination support
- View detailed commit information including author metadata
- Generate and view commit diffs showing file changes

The module ensures data integrity through atomic operations, handles both small inline files and large LFS objects efficiently, and maintains compatibility with the HuggingFace Hub API format.

## Key Features and Capabilities

### Atomic Commit Operations

- **Multi-Operation Commits**: Support for multiple file operations in a single atomic commit
- **NDJSON Payload Format**: Accepts commits in NDJSON (Newline-Delimited JSON) format for efficient streaming
- **Deduplication**: Automatically skips unchanged files to optimize storage and performance
- **Storage Quota Management**: Automatically updates namespace storage usage after commits

### File Operation Support

The module supports the following file operations within commits:

- **file**: Upload small files with inline base64-encoded content (below LFS threshold)
- **lfsFile**: Link large files that have been uploaded to S3 via Git LFS workflow
- **deletedFile**: Remove individual files from the repository
- **deletedFolder**: Recursively delete entire directories
- **copyFile**: Copy files within the repository across revisions

### LFS Integration

- **Automatic LFS Detection**: Files exceeding the configured threshold are automatically handled as LFS objects
- **S3 Physical Address Linking**: LFS files stored in S3 are linked to LakeFS without duplication
- **LFS Garbage Collection**: Optional automatic cleanup of old LFS object versions
- **LFS Object Tracking**: Maintains tracking history for LFS objects across commits

### Commit History and Diffs

- **Paginated History**: Retrieve commit history with configurable pagination
- **Commit Details**: Access detailed commit information including user metadata
- **Diff Generation**: Generate unified diffs showing file changes between commits
- **Concurrent Processing**: Parallel processing of diff entries for performance

### Repository Type Support

The module supports all repository types in KohakuHub:
- **models**: Machine learning models
- **datasets**: Data collections
- **spaces**: Application spaces

## Main Components

### Core Module Files

- **`__init__.py`**: Module initialization and exports. Exposes the main `router` for commit operations and the `history` router for commit history endpoints.

### Routers Subdirectory

The `routers/` subdirectory contains the API endpoint implementations:

- **`operations.py`**: Main commit creation endpoint and file operation processors. Handles the atomic commit workflow, including processing of regular files, LFS files, deletions, and copy operations. Contains helper functions for SHA1 calculation and individual operation processing.

- **`history.py`**: Commit history and diff endpoints. Provides three main endpoints:
  - List commits for a repository branch with pagination
  - Get detailed information about a specific commit
  - Get commit diff showing file changes

- **`__init__.py`**: Router initialization file.

## Integration with Larger System

### Database Layer

The commit module interacts with several database models:
- **Repository**: Verifies repository existence and permissions
- **File**: Tracks file metadata including size, SHA256 hash, and LFS status
- **Commit**: Records commit metadata with user information
- **User/Organization**: Handles authentication and namespace storage quotas

### Storage Layer

The module integrates with multiple storage systems:
- **LakeFS**: Primary version control system for all file operations
- **S3**: Object storage for LFS files and regular file content
- **LakeFS REST Client**: API client for interacting with LakeFS

### Related Modules

- **`auth`**: Provides authentication and permission checking (read/write access)
- **`quota`**: Manages storage usage and namespace quotas
- **`repo.utils.gc`**: Garbage collection utilities for LFS objects
- **`db_operations`**: Database CRUD operations for commits and files

### API Endpoints

The module exposes the following API endpoints (registered in `main.py`):

**Commit Operations:**
- `POST /{repo_type}s/{namespace}/{name}/commit/{revision}`: Create a new commit

**Commit History:**
- `GET /{repo_type}s/{namespace}/{name}/commits/{branch}`: List commits
- `GET /{repo_type}s/{namespace}/{name}/commit/{commit_id}`: Get commit details
- `GET /{repo_type}s/{namespace}/{name}/commit/{commit_id}/diff`: Get commit diff

## Workflow Overview

### Commit Creation Flow

1. **Authentication**: Verify user identity and write permissions
2. **Payload Parsing**: Parse NDJSON payload containing commit header and operations
3. **Operation Processing**: Process each file operation (upload, delete, copy, etc.)
4. **Deduplication**: Skip unchanged files to optimize storage
5. **LFS Handling**: Link large files from S3 to LakeFS without duplication
6. **Commit Creation**: Create atomic commit in LakeFS with all changes
7. **Metadata Recording**: Record commit information in database with user attribution
8. **Post-Processing**: Track LFS objects, run garbage collection, update storage quotas

### Commit History Flow

1. **Authentication**: Verify user identity and read permissions
2. **Query Processing**: Handle pagination parameters for commit listing
3. **LakeFS Integration**: Fetch commit data from LakeFS
4. **User Attribution**: Enrich commit data with user information from database
5. **Response Formatting**: Format response for HuggingFace Hub compatibility

### Diff Generation Flow

1. **Authentication**: Verify user identity and read permissions
2. **Commit Retrieval**: Fetch commit and parent commit from LakeFS
3. **Diff Calculation**: Calculate file differences between commits
4. **Parallel Processing**: Process diff entries concurrently for performance
5. **Content Retrieval**: Fetch file contents for non-LFS files
6. **Unified Diff**: Generate unified diff format for each changed file
7. **Response Assembly**: Combine all diff information into response

## Technical Details

### Git Blob SHA1 Calculation

For non-LFS files, the module calculates SHA1 hashes using Git's blob format:
```
sha1(f'blob {size}\0' + content)
```

This ensures compatibility with Git and HuggingFace Hub expectations.

### LFS Threshold

Files are automatically categorized as LFS objects based on the configured `lfs_threshold_bytes` setting (configurable in application config). This prevents large files from being stored inline in commits.

### Error Handling

The module includes comprehensive error handling:
- Invalid JSON parsing in NDJSON payloads
- Missing required fields in operations
- Storage failures (S3, LakeFS)
- Permission denied scenarios
- File size validation for non-LFS operations

## Dependencies

### External Libraries
- **FastAPI**: Web framework for API endpoints
- **httpx**: Async HTTP client for LakeFS REST API
- **difflib**: Python standard library for diff generation

### Internal Dependencies
- **kohakuhub.config**: Application configuration
- **kohakuhub.db**: Database models
- **kohakuhub.db_operations**: Database operations
- **kohakuhub.auth**: Authentication and authorization
- **kohakuhub.utils.lakefs**: LakeFS utility functions
- **kohakuhub.utils.s3**: S3 utility functions
- **kohakuhub.logger**: Logging utilities
