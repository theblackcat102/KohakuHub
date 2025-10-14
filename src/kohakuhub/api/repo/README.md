# Repository Management Module

## Overview

The `kohakuhub.api.repo` module is the core repository management system for KohakuHub, providing a comprehensive API layer for repository operations. This module implements HuggingFace Hub-compatible endpoints while integrating with LakeFS for Git-like version control and object storage management.

## Purpose

This module serves as the primary interface for:

- Managing repository lifecycle (creation, deletion, moving, squashing)
- Retrieving repository information and metadata
- Browsing repository file trees and directory structures
- Listing repositories with filtering and search capabilities
- Maintaining HuggingFace Hub API compatibility
- Managing large file storage (LFS) with garbage collection

## Key Features

### Repository CRUD Operations
- **Create**: Initialize new repositories (models, datasets, spaces) with LakeFS integration and database tracking
- **Delete**: Remove repositories with proper cleanup of storage, metadata, and quota tracking
- **Move**: Migrate repositories between namespaces (users/organizations) with preservation of history and files
- **Squash**: Consolidate repository commits to optimize storage and history

### Repository Information
- **Individual Repository Info**: Retrieve detailed metadata including author, visibility, tags, and statistics
- **Repository Listing**: Query repositories with filtering by type (models/datasets/spaces), search, author, and privacy settings
- **User Repositories**: List all repositories owned by a specific user

### Tree Browsing
- **Directory Listing**: Navigate repository file structure with support for nested directories
- **Path Information**: Retrieve metadata for multiple files/directories in a single request
- **Statistics**: Calculate folder sizes and file counts recursively
- **Revision Support**: Browse repository content at specific commits or branches

### HuggingFace Integration
- **API Compatibility**: Implements HuggingFace Hub-compatible endpoints and error responses
- **Client Support**: Enables seamless integration with HuggingFace Hub Python client
- **Error Handling**: Provides HF-compatible error codes and messages for standard scenarios

### Garbage Collection
- **LFS Object Tracking**: Monitor large file storage objects across repository versions
- **Version Cleanup**: Remove old LFS versions while preserving recoverability
- **Storage Optimization**: Identify and clean up unreferenced objects
- **Commit Synchronization**: Maintain consistency between file tables and commit history

## Module Structure

### Core Components

**`__init__.py`**
- Module initialization and documentation

### Routers

The `routers/` subdirectory contains FastAPI route handlers organized by functionality:

**`crud.py`** - Repository CRUD Operations
- `POST /repos/create` - Create new repository
- `DELETE /repos/delete` - Delete existing repository
- `POST /repos/move` - Move repository to different namespace
- `POST /repos/squash` - Squash repository commits

**`info.py`** - Repository Information Endpoints
- `GET /{repo_type}s/{namespace}/{repo_name}` - Get repository details
- `GET /{repo_type}s` - List repositories with filters
- `GET /users/{username}/repos` - List user's repositories

**`tree.py`** - Repository Tree Browsing
- `GET /{repo_type}s/{namespace}/{repo_name}/tree/{revision}{path}` - List directory contents
- `POST /{repo_type}s/{namespace}/{repo_name}/paths-info/{revision}` - Get info for multiple paths

### Utilities

The `utils/` subdirectory provides supporting functionality:

**`hf.py`** - HuggingFace Hub Compatibility
- Error response generators matching HF API format
- Error code definitions and mappings
- DateTime formatting for HF compatibility
- LakeFS error detection and translation

**`gc.py`** - Garbage Collection Utilities
- LFS object tracking and version management
- Storage cleanup and recoverability checks
- Commit history synchronization
- Object reference counting and cleanup

## Repository Operations Management

### Storage Architecture

The module integrates multiple storage layers:

1. **LakeFS**: Provides Git-like version control for repository content
   - Branch and commit management
   - Object storage with deduplication
   - Staging and merging operations

2. **S3-Compatible Storage**: Underlying object storage for LFS files
   - Large file storage with content-addressable naming
   - Efficient copying and deletion operations
   - Support for multi-part uploads

3. **Database**: PostgreSQL/SQLAlchemy for metadata
   - Repository records (name, type, visibility, owner)
   - File tracking for LFS objects
   - Quota and usage statistics
   - User and organization relationships

### Permission System

Repository operations enforce access control through:

- User authentication via JWT tokens
- Permission checks for read/write/admin operations
- Organization membership validation
- Privacy settings (public/private repositories)
- Quota enforcement for storage limits

### Lifecycle Management

**Creation Flow**:
1. Validate user permissions and quota availability
2. Normalize and validate repository name
3. Create LakeFS repository with initial branch
4. Initialize database records
5. Set up default files (README, .gitattributes)
6. Track initial commit in quota system

**Deletion Flow**:
1. Verify user has delete permissions
2. Mark repository as deleted in database
3. Run garbage collection to clean up LFS objects
4. Delete LakeFS repository
5. Remove S3 objects with repository prefix
6. Update user quota usage

**Move Flow**:
1. Validate source and destination permissions
2. Rename LakeFS repository
3. Copy S3 objects to new namespace prefix
4. Update database records (repository, files, commits)
5. Delete old S3 objects
6. Update quota tracking for both parties

### Version Control Integration

The module maintains consistency across:

- **Commits**: Tracked in database with metadata and parent relationships
- **Branches**: Managed through LakeFS with HEAD tracking
- **Files**: Versioned with LFS for large files, regular Git for small files
- **Tags**: Supported through LakeFS tag mechanism

### Error Handling

Comprehensive error handling includes:

- HuggingFace-compatible error responses for client integration
- LakeFS error translation (404s, revision errors, etc.)
- Database transaction rollbacks on failures
- Detailed logging for debugging and auditing
- Graceful degradation for non-critical operations

## Dependencies

Key dependencies include:

- **FastAPI**: Web framework for API endpoints
- **LakeFS**: Version control and object storage
- **SQLAlchemy**: Database ORM for metadata
- **Pydantic**: Request/response validation
- **boto3**: S3 operations (via utils)

## Usage Context

This module is mounted into the main KohakuHub API application and provides endpoints that:

- Support the web UI for repository management
- Enable CLI operations for repository lifecycle
- Provide HuggingFace Hub-compatible API for existing tools
- Facilitate programmatic repository access via REST API

## Notes

- All repository operations are atomic with database transactions
- LFS objects are tracked for efficient garbage collection
- Quota enforcement prevents storage abuse
- Repository names are validated and normalized for consistency
- Operations support both user and organization namespaces
