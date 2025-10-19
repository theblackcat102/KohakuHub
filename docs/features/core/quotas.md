---
title: Quota Management
description: Storage limits for users, organizations, and repositories
icon: i-carbon-meter
---

# Quota Management

Storage limits for users, organizations, and repositories.

---

## Overview

**Separate quotas for:**
- Public repositories
- Private repositories
- Per-user defaults
- Per-organization defaults
- Per-repository overrides

**Inheritance:**
- Repository quota → Namespace quota → Server default
- NULL = unlimited (or inherit from parent)

---

## Configuration

### Server Defaults

\`\`\`yaml
# Environment variables
KOHAKU_HUB_DEFAULT_USER_PUBLIC_QUOTA_BYTES: null     # Unlimited
KOHAKU_HUB_DEFAULT_USER_PRIVATE_QUOTA_BYTES: null    # Unlimited
KOHAKU_HUB_DEFAULT_ORG_PUBLIC_QUOTA_BYTES: null      # Unlimited
KOHAKU_HUB_DEFAULT_ORG_PRIVATE_QUOTA_BYTES: null     # Unlimited
\`\`\`

**Example with limits:**

\`\`\`yaml
KOHAKU_HUB_DEFAULT_USER_PUBLIC_QUOTA_BYTES: 10737418240   # 10GB
KOHAKU_HUB_DEFAULT_USER_PRIVATE_QUOTA_BYTES: 5368709120   # 5GB
KOHAKU_HUB_DEFAULT_ORG_PUBLIC_QUOTA_BYTES: 107374182400   # 100GB
KOHAKU_HUB_DEFAULT_ORG_PRIVATE_QUOTA_BYTES: 53687091200   # 50GB
\`\`\`

### Per-User Quotas

**Admin Portal:**
1. Users → Select user → Edit
2. Set custom quotas:
   - Public quota (bytes or null)
   - Private quota (bytes or null)
3. Save

**API:**

\`\`\`bash
# Get user quota
curl http://localhost:28080/api/quota/username

# Response
{
  "public_quota_bytes": 10737418240,
  "private_quota_bytes": 5368709120,
  "public_used_bytes": 1234567,
  "private_used_bytes": 7654321,
  "public_percentage_used": 0.011,
  "private_percentage_used": 0.142
}
\`\`\`

### Per-Repository Quotas

**Repository-specific limits:**

\`\`\`bash
# Via API (admin only)
curl -X PUT http://localhost:28080/api/models/username/repo/settings \\
  -d '{"quota_bytes": 1073741824}'  # 1GB limit for this repo
\`\`\`

**Inheritance:**
- If repo quota is NULL → Inherits from namespace
- Namespace checks both repo and namespace limits

---

## Checking Quotas

### User Quota

**Web UI:**
- Click username → Storage
- See public/private usage
- Progress bars and percentages

**API:**

\`\`\`bash
# Public quota (anyone can view)
curl http://localhost:28080/api/quota/username/public

# Full quota (authenticated users)
curl http://localhost:28080/api/quota/username \\
  -H "Authorization: Bearer token"
\`\`\`

### Repository Quota

**Web UI:**
- Repo page → Sidebar → Storage card
- Shows: used / limit

**API:**

\`\`\`bash
curl http://localhost:28080/api/quota/repo/model/username/repo
\`\`\`

---

## Quota Enforcement

**Upload blocked when:**
- Total upload size + current usage > quota
- Checked at preupload stage
- Error 413: Payload Too Large

**Quota calculation:**
- Actual file size in S3
- Includes all LFS versions
- Deduplicated by SHA256

---

## Admin Tools

### Quota Overview

**Admin Portal → Quota Overview:**
- All users and quotas at a glance
- Sort by usage, percentage
- Filter by over-limit
- Recalculate all quotas

### Recalculate Quota

**When to use:**
- After manual S3 operations
- If numbers seem wrong
- After GC or cleanup

**How:**

\`\`\`bash
# Single user
curl -X POST http://localhost:28080/admin/api/quota/username/recalculate \\
  -H "X-Admin-Token: admin_token"

# Single repo
curl -X POST http://localhost:28080/admin/api/quota/repo/model/username/repo/recalculate

# All repos (slow!)
curl -X POST http://localhost:28080/admin/api/repositories/recalculate-all
\`\`\`

### View Storage Breakdown

**Admin Portal → Repositories:**
- Storage breakdown per repo
- Public vs private usage
- File count
- LFS object count

---

## Best Practices

**For admins:**
- Start with unlimited quotas
- Monitor actual usage
- Set limits based on data
- Communicate limits to users

**For users:**
- Check quota before large uploads
- Use efficient file formats
- Clean up old versions
- Archive unused repos

**Quota sizing:**
- 10GB per user (small team)
- 50-100GB per organization
- Per-repo limits for critical ones

---

## Troubleshooting

**Upload rejected (413):**
- Check quota: `/api/quota/username/public`
- Contact admin for increase
- Delete unused files
- Use organization quota instead

**Quota shows wrong number:**
- Recalculate: Admin Portal → Quota
- Check S3 directly
- Verify LFS objects counted

**Over quota but can't find files:**
- Old LFS versions
- Run garbage collection
- Check hidden/deleted files

---

See also: [LFS Configuration](./lfs.md), [Admin Portal](../api/admin.md)
