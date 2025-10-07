# KohakuHub Utility Scripts

This directory contains utility scripts for KohakuHub administration and maintenance.

## Storage Management

### Clear S3 Storage

For demo deployments with constrained S3 storage (like CloudFlare R2 free tier), use these scripts to manage storage.

**All scripts now accept S3 credentials via command-line arguments or environment variables, making them standalone tools independent of KohakuHub configuration.**

#### Python Script (Recommended)

**Features:**
- ✅ Rich progress display with progress bars
- ✅ Detailed statistics (object count, total size)
- ✅ Dry run mode
- ✅ Batch deletion (handles large buckets efficiently)
- ✅ Prefix filtering
- ✅ Error reporting

**Usage:**

```bash
# Clear all content (interactive confirmation required)
python scripts/clear_s3_storage.py \
    --endpoint https://s3.amazonaws.com \
    --access-key YOUR_ACCESS_KEY \
    --secret-key YOUR_SECRET_KEY \
    --bucket my-bucket

# Clear only LFS files (large files)
python scripts/clear_s3_storage.py \
    --endpoint https://s3.amazonaws.com \
    --access-key YOUR_ACCESS_KEY \
    --secret-key YOUR_SECRET_KEY \
    --bucket my-bucket \
    --prefix lfs/

# Clear specific repository type
python scripts/clear_s3_storage.py \
    --endpoint https://s3.amazonaws.com \
    --access-key YOUR_ACCESS_KEY \
    --secret-key YOUR_SECRET_KEY \
    --bucket my-bucket \
    --prefix hf-model-

# Clear multiple prefixes
python scripts/clear_s3_storage.py \
    --endpoint https://s3.amazonaws.com \
    --access-key YOUR_ACCESS_KEY \
    --secret-key YOUR_SECRET_KEY \
    --bucket my-bucket \
    --prefix lfs/ --prefix hf-model-

# Dry run (show what would be deleted without deleting)
python scripts/clear_s3_storage.py \
    --endpoint https://s3.amazonaws.com \
    --access-key YOUR_ACCESS_KEY \
    --secret-key YOUR_SECRET_KEY \
    --bucket my-bucket \
    --dry-run

# Force delete without confirmation (dangerous!)
python scripts/clear_s3_storage.py \
    --endpoint https://s3.amazonaws.com \
    --access-key YOUR_ACCESS_KEY \
    --secret-key YOUR_SECRET_KEY \
    --bucket my-bucket \
    --force

# Use environment variables for credentials
export S3_ENDPOINT=https://s3.amazonaws.com
export S3_ACCESS_KEY=YOUR_ACCESS_KEY
export S3_SECRET_KEY=YOUR_SECRET_KEY
export S3_BUCKET=my-bucket
python scripts/clear_s3_storage.py --prefix lfs/

# Limit number of objects (for testing)
python scripts/clear_s3_storage.py \
    --endpoint https://s3.amazonaws.com \
    --access-key YOUR_ACCESS_KEY \
    --secret-key YOUR_SECRET_KEY \
    --bucket my-bucket \
    --max-objects 100
```

**Requirements:**
- Python 3.10+
- `boto3` and `rich` packages (`pip install boto3 rich`)
- S3 credentials with delete permissions

---

#### Shell Script (Alternative)

**Features:**
- ✅ No Python dependencies (uses AWS CLI or MinIO client)
- ✅ Simple and portable
- ✅ Supports both `aws` CLI and `mc` (MinIO client)

**Usage:**

```bash
# Make script executable
chmod +x scripts/clear_s3_storage.sh

# Clear all content
./scripts/clear_s3_storage.sh

# Clear with prefix
./scripts/clear_s3_storage.sh --prefix lfs/

# Dry run
./scripts/clear_s3_storage.sh --dry-run

# Force delete
./scripts/clear_s3_storage.sh --force
```

**Requirements:**
- AWS CLI (`aws`) or MinIO Client (`mc`)
- KohakuHub environment variables configured

**Install AWS CLI:**
```bash
# Linux/macOS
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Or via package manager
sudo apt install awscli  # Ubuntu/Debian
brew install awscli      # macOS
```

**Install MinIO Client:**
```bash
# Linux
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# macOS
brew install minio/stable/mc

# Windows
choco install minio-client
```

---

## Common Prefixes in KohakuHub

Understanding KohakuHub's S3 storage structure:

| Prefix | Description | Example |
|--------|-------------|---------|
| `lfs/` | Large File Storage objects (files >5MB) | `lfs/ab/cd/abcd1234...` |
| `hf-model-*` | Model repository data | `hf-model-myuser-mymodel/` |
| `hf-dataset-*` | Dataset repository data | `hf-dataset-myuser-mydataset/` |
| `hf-space-*` | Space repository data | `hf-space-myuser-myspace/` |

**Note:** LFS objects are deduplicated by SHA256 hash. Deleting from `lfs/` prefix removes all large files across all repositories.

---

## Database Migration Scripts

### Add Storage Quota Fields

```bash
# Add quota tracking to users/organizations
python scripts/migrate_add_storage_quota.py
python scripts/migrate_separate_quotas.py
python scripts/migrate_add_quotas_final.py
```

### Update Repository Schema

```bash
python scripts/migrate_repository_schema.py
```

---

## Testing Scripts

### Generate Test Files

```bash
# Generate test files for upload testing
python scripts/generate_test_files.py
```

### Test Authentication

```bash
# Test authentication flow
python scripts/test_auth.py
```

---

## Security

### Generate Secret Keys

```bash
# Generate secure random secret for session/admin tokens
python scripts/generate_secret.py
```

**Output:**
```
Generated secure random secret (64 characters):
a1b2c3d4e5f6...

Add this to your docker-compose.yml:
  KOHAKU_HUB_SESSION_SECRET=a1b2c3d4e5f6...
  KOHAKU_HUB_ADMIN_SECRET_TOKEN=a1b2c3d4e5f6...
```

---

## Environment Variables

### S3 Storage Scripts (`clear_s3_storage.py`, `show_s3_usage.py`)

These scripts accept credentials via command-line arguments or environment variables:

```bash
# Option 1: Command-line arguments
python scripts/clear_s3_storage.py \
    --endpoint https://s3.amazonaws.com \
    --access-key YOUR_KEY \
    --secret-key YOUR_SECRET \
    --bucket my-bucket

# Option 2: Environment variables
export S3_ENDPOINT=https://s3.amazonaws.com
export S3_ACCESS_KEY=YOUR_ACCESS_KEY
export S3_SECRET_KEY=YOUR_SECRET_KEY
export S3_BUCKET=my-bucket
export S3_REGION=us-east-1  # Optional, default: us-east-1

python scripts/clear_s3_storage.py --prefix lfs/
```

### Migration Scripts

Migration scripts require full KohakuHub configuration:

```bash
# S3 Storage
export KOHAKU_HUB_S3_ENDPOINT=http://localhost:29001
export KOHAKU_HUB_S3_PUBLIC_ENDPOINT=http://localhost:29001
export KOHAKU_HUB_S3_ACCESS_KEY=minioadmin
export KOHAKU_HUB_S3_SECRET_KEY=minioadmin
export KOHAKU_HUB_S3_BUCKET=hub-storage

# LakeFS
export KOHAKU_HUB_LAKEFS_ENDPOINT=http://localhost:28000
export KOHAKU_HUB_LAKEFS_ACCESS_KEY=...
export KOHAKU_HUB_LAKEFS_SECRET_KEY=...

# Database
export KOHAKU_HUB_DATABASE_URL=postgresql://user:pass@localhost:5432/kohakuhub

# Application
export KOHAKU_HUB_BASE_URL=http://localhost:28080
```

---

## Tips for Demo Deployments

### CloudFlare R2 Free Tier

- **Limit:** 10GB storage
- **Strategy:** Regularly clear LFS files and old repository data

```bash
# Weekly cleanup schedule
# 1. Clear old LFS files
python scripts/clear_s3_storage.py --prefix lfs/ --force

# 2. Clear test repositories
python scripts/clear_s3_storage.py --prefix hf-space-test --force
```

### MinIO Development

- **No limits:** MinIO has no storage limits
- **Cleanup:** Only needed for testing or reset

```bash
# Reset entire storage for clean slate
python scripts/clear_s3_storage.py --force
```

---

## Safety Features

All deletion scripts include:

1. **Dry run mode:** See what would be deleted before committing
2. **Interactive confirmation:** Requires explicit "yes" to proceed
3. **Double confirmation:** Extra prompt for full bucket deletion
4. **Progress display:** See deletion progress in real-time
5. **Error reporting:** Track and report any deletion failures

---

## Troubleshooting

### "NoSuchBucket" Error

**Problem:** Bucket doesn't exist

**Solution:**
```bash
# Create bucket using AWS CLI
aws s3 mb "s3://${KOHAKU_HUB_S3_BUCKET}" --endpoint-url="${KOHAKU_HUB_S3_ENDPOINT}"

# Or using MinIO client
mc mb kohakuhub-temp/${KOHAKU_HUB_S3_BUCKET}
```

### "Access Denied" Error

**Problem:** S3 credentials lack delete permissions

**Solution:** Check your S3 access key has `s3:DeleteObject` permission

### Script Hangs

**Problem:** Large bucket (millions of objects)

**Solution:** Use `--max-objects` to test first:
```bash
python scripts/clear_s3_storage.py --max-objects 1000 --dry-run
```

---

## Contributing

When adding new scripts:

1. Add docstring with usage examples
2. Include error handling
3. Support dry-run mode if applicable
4. Update this README
5. Test with both SQLite and PostgreSQL backends
