---
title: Branch Operations
description: Create, delete, revert, reset, cherry-pick commits
icon: i-carbon-branch
---

# Branch Operations

Git-like branch management.

## Operations

**Create:**
\`\`\`bash
POST /api/repos/branches/create
{
  "repo_type": "model",
  "namespace": "user",
  "name": "repo",
  "branch": "dev",
  "revision": "main"
}
\`\`\`

**Delete:**
\`\`\`bash
DELETE /api/repos/branches/delete
\`\`\`

**Revert:**
\`\`\`bash
POST /api/repos/branches/revert
\`\`\`

**Reset:**
\`\`\`bash
POST /api/repos/branches/reset
\`\`\`

**Cherry-pick:**
\`\`\`bash
POST /api/repos/branches/cherry-pick
\`\`\`

See API.md for full details.
