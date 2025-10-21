# Quota Management Module

## Overview

The quota management module provides comprehensive storage tracking and enforcement for KohakuHub users and organizations. It implements a dual-quota system that separately tracks and enforces limits for private and public repositories, allowing fine-grained control over resource allocation.

## Purpose

This module enables:

- Real-time monitoring of storage usage across all repositories
- Enforcement of storage limits to prevent resource exhaustion
- Separate quota management for private and public repositories
- Permission-based visibility of storage information
- Manual recalculation of storage usage when needed

## Key Features

### Dual-Quota System

The module implements separate quota tracking for:

- **Private Repositories**: Storage used by private repos with configurable limits
- **Public Repositories**: Storage used by public repos with independent limits
- **Unlimited Quotas**: Setting a quota to `None` allows unlimited storage

### Storage Calculation

Storage tracking includes:

- **Current Branch Storage**: All objects in the main branch
- **LFS Object Storage**: All Git LFS objects with version history
- **Deduplication Awareness**: Tracks both total and unique LFS storage
- **Incremental Updates**: Efficient delta updates for storage changes

### Permission-Based Access

The module provides different visibility levels:

- **Authenticated Access**: Users can view their own complete quota information
- **Organization Members**: Members can view organization quota details
- **Public Access**: Anyone can view public repository storage usage
- **Private Data Protection**: Private storage info only visible to authorized users

## Architecture

### Components

#### router.py

FastAPI router implementing REST endpoints for quota management:

- `GET /api/quota/{namespace}` - Get complete quota information (authenticated)
- `PUT /api/quota/{namespace}` - Set storage quotas (admin only)
- `POST /api/quota/{namespace}/recalculate` - Manually recalculate storage
- `GET /api/quota/{namespace}/public` - Get public quota info with conditional private data

**Data Models:**

- `QuotaInfo`: Complete quota information for authenticated users
- `PublicQuotaInfo`: Permission-aware quota data for public profiles
- `SetQuotaRequest`: Request body for setting quota limits

**Authorization:**

- Users can manage their own quotas
- Organization admins can manage org quotas
- Super-admins and admins have elevated permissions

#### util.py

Core business logic for storage calculation and quota enforcement:

**Async Functions:**

- `calculate_repository_storage(repo)` - Calculate storage for a single repository
- `calculate_namespace_storage(namespace, is_org)` - Calculate total storage by privacy
- `update_namespace_storage(namespace, is_org)` - Recalculate and update storage in DB

**Sync Functions:**

- `check_quota(namespace, additional_bytes, is_private, is_org)` - Validate quota before operations
- `increment_storage(namespace, bytes_delta, is_private, is_org)` - Update storage counters
- `get_storage_info(namespace, is_org)` - Retrieve current quota and usage
- `set_quota(namespace, private_quota_bytes, public_quota_bytes, is_org)` - Update quota limits

## Storage Management

### How Quotas Are Enforced

1. **Pre-upload Check**: `check_quota()` validates that new uploads won't exceed limits
2. **Incremental Updates**: `increment_storage()` updates usage counters after operations
3. **Periodic Recalculation**: Admins can trigger full recalculation to fix drift

### Storage Calculation Details

For each repository, storage includes:

```
Total Storage = Current Branch Storage + LFS Total Storage
```

**Current Branch Storage:**
- All objects in the main branch
- Retrieved via LakeFS API pagination
- Includes regular files tracked by Git

**LFS Storage:**
- All LFS objects across all versions (total)
- Unique LFS objects after deduplication (tracked separately)
- Retrieved from LFSObjectHistory database table

**Namespace Aggregation:**
- Private repos summed separately from public repos
- Parallel calculation using asyncio.gather for performance
- Results stored in User/Organization models

### Database Schema

The module expects these fields in User and Organization models:

```python
# Quota limits (None = unlimited)
private_quota_bytes: int | None
public_quota_bytes: int | None

# Current usage
private_used_bytes: int  # Default: 0
public_used_bytes: int   # Default: 0
```

## Usage Examples

### Check Quota Before Upload

```python
from kohakuhub.api.quota.util import check_quota

allowed, error_msg = check_quota(
    namespace="username",
    additional_bytes=100 * 1000 * 1000,  # 100 MB
    is_private=True,
    is_org=False
)

if not allowed:
    raise HTTPException(413, detail={"error": error_msg})
```

### Update Storage After Operation

```python
from kohakuhub.api.quota.util import increment_storage

# After uploading a file
increment_storage(
    namespace="orgname",
    bytes_delta=file_size,
    is_private=False,
    is_org=True
)

# After deleting a file
increment_storage(
    namespace="username",
    bytes_delta=-file_size,
    is_private=True,
    is_org=False
)
```

### Recalculate Storage (Manual Sync)

```python
from kohakuhub.api.quota.util import update_namespace_storage

# Recalculate all storage for a namespace
storage = await update_namespace_storage("username", is_org=False)
print(f"Private: {storage['private_bytes']} bytes")
print(f"Public: {storage['public_bytes']} bytes")
```

### Get Storage Information

```python
from kohakuhub.api.quota.util import get_storage_info

info = get_storage_info("username", is_org=False)
print(f"Private quota: {info['private_quota_bytes']}")
print(f"Private used: {info['private_used_bytes']}")
print(f"Private available: {info['private_available_bytes']}")
print(f"Private percentage: {info['private_percentage_used']}%")
```

## API Endpoints

### Namespace Quotas
- `GET /api/quota/{namespace}` - Get complete quota information (authenticated)
- `PUT /api/quota/{namespace}` - Set storage quotas (admin only)
- `POST /api/quota/{namespace}/recalculate` - Manually recalculate storage
- `GET /api/quota/{namespace}/public` - Get public quota info with conditional private data
- `GET /api/quota/{namespace}/repos` - List storage for all repositories in a namespace

### Repository Quotas
- `GET /api/quota/repo/{repo_type}/{namespace}/{name}` - Get repository-specific quota information
- `PUT /api/quota/repo/{repo_type}/{namespace}/{name}` - Set repository-specific quota
- `POST /api/quota/repo/{repo_type}/{namespace}/{name}/recalculate` - Recalculate storage for a single repository

## Error Handling

The module uses HTTP exceptions for error conditions:

- `404 Not Found`: Namespace (user/org) does not exist
- `403 Forbidden`: User lacks permission to perform operation
- `413 Payload Too Large`: Upload would exceed quota (via check_quota)

## Integration Points

### Dependencies

- **Database Models**: User, Organization, Repository, LFSObjectHistory
- **LakeFS Client**: For retrieving object storage information
- **Authentication**: get_current_user, get_optional_user dependencies
- **Configuration**: cfg module for system settings

### Used By

- File upload handlers (check quota before accepting uploads)
- Repository management (track storage on create/delete)
- LFS operations (increment storage on LFS object operations)
- User/org profile pages (display quota information)

## Performance Considerations

- **Parallel Calculation**: Uses asyncio.gather to calculate multiple repos simultaneously
- **Pagination**: LakeFS queries paginate results (1000 objects per request)
- **Incremental Updates**: Prefer increment_storage over full recalculation
- **Synchronous Operations**: check_quota and increment_storage are sync for transaction safety

## Logging

The module uses the "QUOTA" logger for operational visibility:

- Info level: Quota changes, recalculation results
- Debug level: Incremental storage updates
- Warning level: Calculation failures (non-fatal)

## Future Enhancements

Potential improvements for consideration:

- Background job for periodic quota recalculation
- Quota usage alerts and notifications
- Historical usage tracking and analytics
- Per-repository quota limits
- Quota grace periods before enforcement
