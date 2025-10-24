---
title: Git Protocol API
description: Git Smart HTTP and SSH support for clone/push/pull operations
icon: i-carbon-code
---

# Git Protocol API

KohakuHub implements Git Smart HTTP protocol for seamless `git clone`, `git push`, and `git pull` operations.

---

## Git Smart HTTP

### Service Advertisement

**Pattern:** `GET /{namespace}/{name}.git/info/refs?service={service}`

**Path Parameters:**
- `namespace`: User or organization name
- `name`: Repository name

**Query Parameters:**
- `service`: `git-upload-pack` (clone/fetch) or `git-receive-pack` (push)

**Authentication:**
- Optional for `git-upload-pack` (public repos)
- Required for `git-receive-pack` (push operations)
- Uses HTTP Basic Auth with token as password

**Response:**
```
001e# service=git-upload-pack
0000
<pkt-line formatted capabilities>
```

**Headers:**
- `Content-Type`: `application/x-git-upload-pack-advertisement` or `application/x-git-receive-pack-advertisement`

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Auth required for push
- `403 Forbidden` - Permission denied
- `404 Not Found` - Repository not found

---

### Upload Pack (Clone/Fetch/Pull)

**Pattern:** `POST /{namespace}/{name}.git/git-upload-pack`

**Purpose:** Download objects from repository (git clone, git fetch, git pull)

**Authentication:** Optional (required for private repos)

**Request:**
- `Content-Type`: `application/x-git-upload-pack-request`
- Body: Git pack negotiation in pkt-line format

**Response:**
- `Content-Type`: `application/x-git-upload-pack-result`
- Body: Git pack file with requested objects

**Process:**
1. Client sends want/have negotiation
2. Server generates pack with missing objects
3. Pack includes LFS pointers for large files (>1MB)

**LFS Handling:**
- Files >1MB converted to LFS pointers automatically
- Pointer format: Git LFS specification
- Actual files downloaded via LFS batch API

**Status Codes:**
- `200 OK` - Success
- `403 Forbidden` - Permission denied
- `404 Not Found` - Repository not found

---

### Receive Pack (Push)

**Pattern:** `POST /{namespace}/{name}.git/git-receive-pack`

**Purpose:** Upload objects to repository (git push)

**Authentication:** Required (HTTP Basic Auth)

**Request:**
- `Content-Type`: `application/x-git-receive-pack-request`
- Body: Git pack file with objects

**Response:**
- `Content-Type`: `application/x-git-receive-pack-result`
- Body: Status report in pkt-line format

**Process:**
1. Client sends pack with new commits/objects
2. Server validates and stores objects in LakeFS
3. Server updates branch references
4. Server sends status report

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Auth required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Repository not found

---

### HEAD Reference

**Pattern:** `GET /{namespace}/{name}.git/HEAD`

**Purpose:** Get default branch reference

**Response:**
```
ref: refs/heads/main
```

**Headers:**
- `Content-Type`: `text/plain`

---

## SSH Keys Management

### List SSH Keys

**Pattern:** `GET /api/user/keys`

**Authentication:** Required (current user)

**Response:**
```json
[
  {
    "id": 1,
    "title": "My Laptop",
    "key_type": "ssh-ed25519",
    "fingerprint": "SHA256:abc123def456...",
    "created_at": "2025-01-01T00:00:00Z",
    "last_used": "2025-01-02T12:30:00Z"
  }
]
```

---

### Add SSH Key

**Pattern:** `POST /api/user/keys`

**Authentication:** Required (current user)

**Request Body:**
```json
{
  "title": "My Laptop",
  "key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5... user@host"
}
```

**Supported Key Types:**
- `ssh-ed25519` (recommended)
- `ssh-rsa` (2048+ bits)
- `ecdsa-sha2-nistp256`
- `ecdsa-sha2-nistp384`
- `ecdsa-sha2-nistp521`

**Validation:**
- Key format must be valid OpenSSH format
- Title is required (max 255 chars)
- Duplicate keys rejected (same fingerprint)

**Response:**
```json
{
  "id": 2,
  "title": "My Laptop",
  "key_type": "ssh-ed25519",
  "fingerprint": "SHA256:abc123...",
  "created_at": "2025-01-15T10:00:00Z",
  "last_used": null
}
```

**Status Codes:**
- `200 OK` - Created successfully
- `400 Bad Request` - Invalid key format
- `409 Conflict` - Key already exists

---

### Get SSH Key

**Pattern:** `GET /api/user/keys/{key_id}`

**Authentication:** Required (must own key)

**Response:**
```json
{
  "id": 1,
  "title": "My Laptop",
  "key_type": "ssh-ed25519",
  "fingerprint": "SHA256:abc123...",
  "public_key": "ssh-ed25519 AAAAC3...",
  "created_at": "2025-01-01T00:00:00Z",
  "last_used": "2025-01-02T12:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Success
- `403 Forbidden` - Not authorized
- `404 Not Found` - Key not found

---

### Delete SSH Key

**Pattern:** `DELETE /api/user/keys/{key_id}`

**Authentication:** Required (must own key)

**Response:**
```json
{
  "success": true,
  "message": "SSH key deleted successfully"
}
```

**Status Codes:**
- `200 OK` - Deleted successfully
- `403 Forbidden` - Not authorized
- `404 Not Found` - Key not found

---

## Git Usage Examples

### Clone Repository

```bash
# HTTPS (with token)
git clone https://token@hub.example.com/username/repo.git

# HTTPS (with credential helper)
git clone https://hub.example.com/username/repo.git
# Enter username and token when prompted

# SSH (requires SSH key setup)
git clone ssh://git@hub.example.com/username/repo.git
```

### Push Changes

```bash
# Add changes
git add .
git commit -m "Update model"

# Push to main branch
git push origin main
```

### Fetch/Pull Updates

```bash
# Fetch updates
git fetch origin

# Pull and merge
git pull origin main
```

---

## LFS Integration

Git operations automatically handle LFS files:

**On Clone:**
- Small files (<1MB) downloaded normally
- Large files (≥1MB) converted to LFS pointers
- Use `git lfs pull` to download actual LFS files

**On Push:**
- LFS files automatically uploaded via LFS batch API
- Regular files uploaded via git protocol
- Server validates and links LFS objects

**LFS Commands:**
```bash
# Install Git LFS
git lfs install

# Track large file types
git lfs track "*.safetensors"
git lfs track "*.bin"

# Pull LFS files
git lfs pull

# Push with LFS
git add large_file.safetensors
git commit -m "Add model weights"
git push origin main
```

---

## Authentication Methods

### HTTPS with Token

**URL format:**
```
https://token@hub.example.com/namespace/repo.git
```

**Credential Helper:**
```bash
# Store credentials
git config credential.helper store

# Or use OS keychain
git config credential.helper osxkeychain  # macOS
git config credential.helper wincred      # Windows
git config credential.helper libsecret    # Linux
```

### SSH with Key

**Prerequisites:**
1. Add SSH public key via API or UI
2. Configure SSH client

**SSH Config (~/.ssh/config):**
```
Host hub.example.com
  HostName hub.example.com
  User git
  Port 22
  IdentityFile ~/.ssh/id_ed25519
```

**Clone:**
```bash
git clone ssh://git@hub.example.com/username/repo.git
```

---

## Error Handling

### Common Errors

**401 Unauthorized:**
```
fatal: Authentication failed for 'https://hub.example.com/repo.git/'
```
**Solution:** Check token or SSH key

**403 Forbidden:**
```
fatal: unable to access 'https://hub.example.com/repo.git/': The requested URL returned error: 403
```
**Solution:** Check repository permissions

**404 Not Found:**
```
fatal: repository 'https://hub.example.com/repo.git/' not found
```
**Solution:** Verify repository exists and you have access

---

## Performance Notes

**Clone Speed:**
- Small repos (<100MB): ~10-30 seconds
- Large repos (1GB+): Minutes (depends on network)
- LFS files excluded from initial clone (download separately)

**Push Speed:**
- Incremental pushes: Fast (only new objects)
- Large files: Use LFS for >1MB files
- Parallel uploads: LFS batch API supports concurrent uploads

**Best Practices:**
- Use LFS for files >1MB
- Shallow clone for CI/CD: `git clone --depth 1`
- Use sparse checkout for large repos
- Configure `.gitattributes` for LFS tracking

---

## Next Steps

- [Git LFS API](./git-lfs.md) - Detailed LFS protocol
- [File Upload API](./file-upload.md) - Direct file uploads
- [Authentication](./authentication.md) - Token management
