---
title: LFS Configuration
description: Git LFS integration with flexible per-repository settings
icon: i-carbon-data-volume
---

# LFS (Large File Storage) Configuration

Git LFS integration with flexible per-repository settings.

---

## Overview

**Automatic LFS handling:**
- Files ≥5MB → LFS by default
- Or specific file extensions → Always LFS
- Configurable per-repository
- Server-wide defaults + repo overrides

---

## Server Defaults

**Environment variables:**

\`\`\`yaml
KOHAKU_HUB_LFS_THRESHOLD_BYTES: 5000000  # 5MB (decimal: 1MB = 1,000,000)
KOHAKU_HUB_LFS_KEEP_VERSIONS: 5          # Keep last 5 versions
KOHAKU_HUB_LFS_AUTO_GC: false            # Manual GC only
\`\`\`

**32 default suffix rules** (always use LFS):

**ML Models:**
- .safetensors, .bin, .pt, .pth, .ckpt
- .onnx, .pb, .h5, .tflite
- .gguf, .ggml, .msgpack

**Archives:**
- .zip, .tar, .gz, .bz2, .xz, .7z, .rar

**Data:**
- .npy, .npz, .arrow, .parquet

**Media:**
- .mp4, .avi, .mkv, .mov
- .wav, .mp3, .flac
- .tiff, .tif

---

## Per-Repository Settings

**Override server defaults:**

### Via Web UI

1. Navigate to repo → **Settings**
2. Scroll to **LFS Settings**
3. Configure:
   - **Threshold** - Size in bytes (null = use server default)
   - **Keep Versions** - How many versions to keep (null = server default)
   - **Suffix Rules** - Additional extensions (supplements server defaults)

### Via CLI

\`\`\`bash
# Set custom threshold (10MB)
kohub-cli settings repo lfs threshold username/repo --threshold 10000000

# Reset to server default
kohub-cli settings repo lfs threshold username/repo --reset

# Set keep versions
kohub-cli settings repo lfs versions username/repo --count 10

# Add suffix rules
kohub-cli settings repo lfs suffix username/repo --add .custom --add .special

# Remove suffix rule
kohub-cli settings repo lfs suffix username/repo --remove .custom

# Clear all custom rules (keep server defaults)
kohub-cli settings repo lfs suffix username/repo --clear
\`\`\`

### Via API

\`\`\`bash
# Get LFS settings
curl http://localhost:28080/api/models/username/repo/settings/lfs

# Update settings
curl -X PUT http://localhost:28080/api/models/username/repo/settings \\
  -d '{
    "lfs_threshold_bytes": 10000000,
    "lfs_keep_versions": 10,
    "lfs_suffix_rules": [".safetensors", ".custom"]
  }'
\`\`\`

---

## How LFS Works

### Upload Flow

**Small file (<threshold, not in suffix rules):**
1. Client → Base64 encode
2. Include in commit payload
3. LakeFS → Store in S3

**Large file (≥threshold OR in suffix rules):**
1. Client → Request presigned URL
2. Upload directly to S3
3. Server links object to LakeFS

### Download Flow

**All files:**
1. Client requests file
2. Server → 302 redirect to S3 presigned URL
3. Client downloads directly from S3

**Git clone:**
- Files <1MB → Included in pack
- Files ≥1MB → LFS pointers
- Run `git lfs pull` to download large files

---

## Garbage Collection

**Keep versions setting:**
- Keeps last N versions of each file
- Older versions marked for deletion
- Manual GC via admin API

**Manual GC:**

\`\`\`bash
# Via admin API
curl -X POST http://localhost:28080/admin/api/repositories/model/username/repo/gc \\
  -H "X-Admin-Token: admin_token"
\`\`\`

**Auto GC:**

\`\`\`yaml
KOHAKU_HUB_LFS_AUTO_GC: true  # Runs on every commit (careful!)
\`\`\`

---

## Best Practices

**Threshold:**
- 5MB good default (accounts for base64 overhead)
- Lower for many small files
- Higher if network is slow

**Suffix rules:**
- Use for files that should ALWAYS use LFS
- `.safetensors`, `.gguf` always LFS regardless of size
- Add custom formats as needed

**Keep versions:**
- 5-10 good for active development
- Higher for critical models
- Lower to save storage

**Warnings:**
- Setting keep_versions <2 breaks revert operations!
- Auto GC on commit can be slow
- Manual GC recommended

---

## Troubleshooting

**Files not using LFS:**
- Check threshold settings
- Verify suffix rules
- Check file actually meets criteria

**LFS download fails:**
- Install git-lfs: `git lfs install`
- Pull: `git lfs pull`
- Check .lfsconfig in repo

**Storage growing:**
- Old LFS versions not cleaned
- Run manual GC
- Check keep_versions setting

---

See also: [Quota Management](./quotas.md), [Configuration Reference](../reference/config.md)
