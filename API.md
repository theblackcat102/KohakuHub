# Kohaku Hub API Workflow Documentation

## Overview

Kohaku Hub implements a HuggingFace-compatible API using LakeFS for Git-like versioning and S3/MinIO for object storage. Files ≤10MB use regular upload, while >10MB use Git LFS protocol.

## Core Architecture

```
Client Request
     ↓
FastAPI Layer (kohakuhub/api/*)
     ↓
LakeFS (versioning/branching)
     ↓
S3/MinIO (object storage)
     ↓
SQLite DB (metadata/deduplication)
```

## Upload Workflow

### Step 1: Preupload Check
**Endpoint:** `POST /api/{repo_type}s/{repo_id}/preupload/{revision}`

**Request:**
```json
{
  "files": [
    {
      "path": "config.json",
      "size": 1024,
      "sha256": "a1b2c3..."
    }
  ]
}
```

**Response:**
```json
{
  "files": [
    {
      "path": "config.json",
      "uploadMode": "regular",  // or "lfs"
      "shouldIgnore": false     // true if sha256 matches existing
    }
  ]
}
```

**Logic:**
- Check file size: ≤10MB → "regular", >10MB → "lfs"
- Query DB for existing sha256 hash
- If hash exists with same size → `shouldIgnore: true`

### Step 2a: Regular Upload (≤10MB)
Files are sent inline in commit payload as base64

### Step 2b: LFS Upload (>10MB)
**Endpoint:** `POST /{repo_id}.git/info/lfs/objects/batch`

**Request:**
```json
{
  "operation": "upload",
  "transfers": ["basic", "multipart"],
  "objects": [
    {
      "oid": "sha256_hash",
      "size": 52428800
    }
  ]
}
```

**Response:**
```json
{
  "transfer": "basic",
  "objects": [
    {
      "oid": "sha256_hash",
      "size": 52428800,
      "actions": {
        "upload": {
          "href": "presigned_s3_url",
          "expires_at": "2025-10-01T00:00:00Z"
        }
      }
    }
  ]
}
```

**Note:** If OID exists, no `actions` field returned (deduplication)

### Step 3: Commit
**Endpoint:** `POST /api/{repo_type}s/{repo_id}/commit/{revision}`

**Format:** NDJSON (newline-delimited JSON)

```
{"key":"header","value":{"summary":"Add files","description":""}}
{"key":"file","value":{"path":"config.json","content":"eyJtb2RlbCI6...","encoding":"base64"}}
{"key":"lfsFile","value":{"path":"model.bin","algo":"sha256","oid":"a1b2c3...","size":52428800}}
{"key":"deletedFile","value":{"path":"old.txt"}}
```

**Response:**
```json
{
  "commitUrl": "https://hub.example.com/repo/commit/abc123",
  "commitOid": "abc123def456",
  "pullRequestUrl": null
}
```

## Download Workflow

### Step 1: Get File Metadata
**Endpoint:** `HEAD /{repo_id}/resolve/{revision}/{filename}`

**Response Headers:**
```
x-repo-commit: abc123def456
x-linked-etag: "sha256:a1b2c3..."
x-linked-size: 52428800
Location: https://cdn-lfs.example.com/repo/sha256_hash
```

### Step 2: Download File
**Endpoint:** `GET /{repo_id}/resolve/{revision}/{filename}`

**Response:**
- Small files: Direct content or redirect to S3 presigned URL
- LFS files: HTTP 302 redirect to CDN/S3 presigned URL

## Repository Management

### Create Repository
**Endpoint:** `POST /api/repos/create`

```json
{
  "type": "model",
  "name": "my-model",
  "organization": "my-org",
  "private": false
}
```

**Actions:**
1. Create LakeFS repository
2. Insert record in SQLite `Repository` table
3. Return repo URL

### List Repository Tree
**Endpoint:** `GET /api/{repo_type}s/{repo_id}/tree/{revision}/{path}`

**Query Params:**
- `recursive`: true/false
- `expand`: true/false (include LFS metadata)

**Response:**
```json
{
  "sha": "commit_hash",
  "truncated": false,
  "tree": [
    {
      "path": "config.json",
      "type": "blob",
      "size": 1024,
      "oid": "blob_hash",
      "lfs": false,
      "lastCommit": {"id": "commit_hash", "date": "2025-09-30"}
    }
  ]
}
```

### Get Revision Info
**Endpoint:** `GET /api/{repo_type}s/{repo_id}/revision/{revision}`

**Response:**
```json
{
  "id": "org/repo",
  "author": "org",
  "sha": "commit_hash",
  "lastModified": "2025-09-30T12:00:00Z",
  "private": false,
  "revision": "main"
}
```

## Database Schema

### Repository Table
```sql
CREATE TABLE repository (
    id INTEGER PRIMARY KEY,
    repo_type VARCHAR,      -- model/dataset/space
    namespace VARCHAR,      -- org or user
    name VARCHAR,
    full_id VARCHAR UNIQUE, -- "org/repo"
    private BOOLEAN,
    created_at TIMESTAMP
);
```

### File Table (Deduplication)
```sql
CREATE TABLE file (
    id INTEGER PRIMARY KEY,
    repo_full_id VARCHAR,
    path_in_repo VARCHAR,
    size INTEGER,
    sha256 VARCHAR,         -- for shouldIgnore check
    lfs BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(repo_full_id, path_in_repo)
);
```

### StagingUpload Table (Optional)
```sql
CREATE TABLE staging_upload (
    id INTEGER PRIMARY KEY,
    repo_full_id VARCHAR,
    revision VARCHAR,
    path_in_repo VARCHAR,
    sha256 VARCHAR,
    size INTEGER,
    upload_id VARCHAR,      -- S3 multipart upload ID
    storage_key VARCHAR,    -- S3 key
    lfs BOOLEAN,
    created_at TIMESTAMP
);
```

## LakeFS Integration

### Repository Naming
```
Pattern: {namespace}-{repo_type}-{org}-{name}
Example: hf-model-myorg-mymodel
```

### Storage Structure
```
S3 Bucket: {bucket_name}
  └── {lakefs_repo_name}/
      └── {branch}/
          └── {file_path}
```

### Key Operations
1. **Create Repo:** `repositories.create_repository()`
2. **Upload Object:** `objects.upload_object()` (small files)
3. **Link Physical Object:** `objects.link_physical_address()` (LFS files)
4. **Commit:** `commits.commit()`
5. **List Objects:** `objects.list_objects()`
6. **Get Object Stats:** `objects.stat_object()`

## API Endpoints Summary

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/api/repos/create` | POST | Create repository | Required |
| `/api/{type}s` | GET | List repositories | Optional |
| `/api/{type}s/{id}/tree/{rev}/{path}` | GET | List files | Optional |
| `/api/{type}s/{id}/revision/{rev}` | GET | Get revision info | Optional |
| `/api/{type}s/{id}/preupload/{rev}` | POST | Check before upload | Required |
| `/{id}.git/info/lfs/objects/batch` | POST | LFS batch API | Required |
| `/api/{type}s/{id}/commit/{rev}` | POST | Atomic commit | Required |
| `/{id}/resolve/{rev}/{file}` | GET/HEAD | Download file | Optional |
| `/api/validate-yaml` | POST | Validate YAML | None |
| `/api/whoami-v2` | GET | User info | Required |
