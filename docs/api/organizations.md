---
title: Organizations API
description: Create and manage organizations and their members
icon: users
---

# Organizations API

Manage organizations, members, and roles for collaborative repository management.

## Overview

Organizations allow multiple users to collaborate on repositories. Members can have different roles:

- **visitor**: Read-only access
- **member**: Can create repositories, read all org repos
- **admin**: Can manage members and settings
- **super-admin**: Full control (creator role)

---

## Endpoints

### Create Organization

Create a new organization with default quotas.

**Endpoint:** `POST /api/organizations/create`

**Request Body:**

```json
{
  "name": "myorg",
  "description": "Machine Learning Research"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Organization name (alphanumeric, hyphens, underscores) |
| `description` | string | No | Organization description |

**Authentication:** Required

**Response:**

```json
{
  "success": true,
  "name": "myorg"
}
```

**Notes:**

- Creator is automatically added as `super-admin`
- Default quotas are applied from server configuration
- Organization name must not be reserved (e.g., `admin`, `api`, `models`, etc.)
- Name is validated and normalized

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Organization name already exists or is reserved |
| 401 | Authentication required |
| 422 | Invalid request body |

**Example:**

```python
import requests

response = requests.post(
    "http://localhost:28080/api/organizations/create",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "name": "myorg",
        "description": "Machine Learning Research"
    }
)

result = response.json()
print(f"Organization created: {result['name']}")
```

---

### Get Organization Info

Get basic organization information.

**Endpoint:** `GET /api/organizations/{org_name}`

**Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `org_name` | string | path | Yes | Organization name |
| `fallback` | boolean | query | No | Enable fallback to external sources (default: `true`) |

**Authentication:** Optional

**Response:**

```json
{
  "name": "myorg",
  "description": "Machine Learning Research",
  "created_at": "2025-01-01T00:00:00Z",
  "_source": "local"
}
```

**Example:**

```python
response = requests.get("http://localhost:28080/api/organizations/myorg")
org = response.json()
```

---

### Add Member

Add a member to an organization (admin only).

**Endpoint:** `POST /api/organizations/{org_name}/members`

**Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `org_name` | string | path | Yes | Organization name |

**Request Body:**

```json
{
  "username": "alice",
  "role": "member"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Username to add |
| `role` | string | Yes | Member role: `visitor`, `member`, `admin` |

**Authentication:** Required (admin or super-admin)

**Response:**

```json
{
  "success": true,
  "message": "Member added successfully"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | User is already a member |
| 403 | Not authorized to add members |
| 404 | Organization or user not found |

**Example:**

```python
response = requests.post(
    "http://localhost:28080/api/organizations/myorg/members",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "username": "alice",
        "role": "member"
    }
)
```

---

### Remove Member

Remove a member from an organization (admin only).

**Endpoint:** `DELETE /api/organizations/{org_name}/members/{username}`

**Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `org_name` | string | path | Yes | Organization name |
| `username` | string | path | Yes | Username to remove |

**Authentication:** Required (admin or super-admin)

**Response:**

```json
{
  "success": true,
  "message": "Member removed successfully"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 403 | Not authorized to remove members |
| 404 | Organization, user, or membership not found |

**Example:**

```python
response = requests.delete(
    "http://localhost:28080/api/organizations/myorg/members/alice",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)
```

---

### Update Member Role

Change a member's role in an organization (admin only).

**Endpoint:** `PUT /api/organizations/{org_name}/members/{username}`

**Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `org_name` | string | path | Yes | Organization name |
| `username` | string | path | Yes | Username to update |

**Request Body:**

```json
{
  "role": "admin"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | Yes | New role: `visitor`, `member`, or `admin` |

**Authentication:** Required (admin or super-admin)

**Response:**

```json
{
  "success": true,
  "message": "Member role updated successfully"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 403 | Not authorized to update member roles |
| 404 | Organization, user, or membership not found |

**Example:**

```python
# Promote member to admin
response = requests.put(
    "http://localhost:28080/api/organizations/myorg/members/alice",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={"role": "admin"}
)

# Demote admin to member
response = requests.put(
    "http://localhost:28080/api/organizations/myorg/members/bob",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={"role": "member"}
)
```

---

### List Organization Members

Get list of all organization members.

**Endpoint:** `GET /api/organizations/{org_name}/members`

**Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `org_name` | string | path | Yes | Organization name |

**Authentication:** Optional (public information)

**Response:**

```json
{
  "members": [
    {
      "user": "alice",
      "role": "super-admin"
    },
    {
      "user": "bob",
      "role": "admin"
    },
    {
      "user": "charlie",
      "role": "member"
    }
  ]
}
```

**Example:**

```python
response = requests.get(
    "http://localhost:28080/api/organizations/myorg/members"
)
members = response.json()["members"]

for member in members:
    print(f"{member['user']}: {member['role']}")
```

---

### List User Organizations

Get organizations a user belongs to.

**Endpoint:** `GET /api/users/{username}/orgs`

**Parameters:**

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `username` | string | path | Yes | Username to query |

**Authentication:** Optional (public information)

**Response:**

```json
{
  "organizations": [
    {
      "name": "myorg",
      "description": "Machine Learning Research",
      "role": "admin"
    },
    {
      "name": "anotherorg",
      "description": "Data Science Projects",
      "role": "member"
    }
  ]
}
```

**Example:**

```python
response = requests.get(
    "http://localhost:28080/api/users/alice/orgs"
)
orgs = response.json()["organizations"]

for org in orgs:
    print(f"{org['name']} ({org['role']})")
```

---

## Role Permissions

### Visitor

- View public repositories
- View organization profile
- No write access

### Member

- All visitor permissions
- Create repositories under organization
- Write to organization repositories they created
- View all organization repositories (public and private)

### Admin

- All member permissions
- Manage organization members (add, remove, update roles)
- Update organization settings and avatar
- Manage organization quotas
- Delete organization repositories

### Super-Admin

- All admin permissions
- Cannot be removed by other admins
- Transfer ownership capabilities
- Full organization control

**Note:** Only the organization creator gets `super-admin` role automatically. Admins cannot promote members to `super-admin`.

---

## Usage Examples

### Create and Set Up Organization

```python
import requests

BASE_URL = "http://localhost:28080"
TOKEN = "YOUR_TOKEN"

headers = {"Authorization": f"Bearer {TOKEN}"}

# 1. Create organization
response = requests.post(
    f"{BASE_URL}/api/organizations/create",
    headers=headers,
    json={
        "name": "ml-research",
        "description": "Machine Learning Research Lab"
    }
)
print(f"Created: {response.json()['name']}")

# 2. Update organization settings
requests.put(
    f"{BASE_URL}/api/organizations/ml-research/settings",
    headers=headers,
    json={
        "bio": "Advancing AI through open research",
        "website": "https://ml-research.example.com",
        "social_media": {
            "twitter_x": "ml_research",
            "github": "ml-research"
        }
    }
)

# 3. Upload organization logo
with open("logo.png", "rb") as f:
    requests.post(
        f"{BASE_URL}/api/organizations/ml-research/avatar",
        headers=headers,
        files={"file": f}
    )

# 4. Add team members
members = [
    ("alice", "admin"),
    ("bob", "member"),
    ("charlie", "member")
]

for username, role in members:
    requests.post(
        f"{BASE_URL}/api/organizations/ml-research/members",
        headers=headers,
        json={"username": username, "role": role}
    )
    print(f"Added {username} as {role}")
```

### Manage Organization Members

```python
# List all members
response = requests.get(
    f"{BASE_URL}/api/organizations/ml-research/members"
)
members = response.json()["members"]

# Find members by role
admins = [m for m in members if m["role"] in ["admin", "super-admin"]]
regular_members = [m for m in members if m["role"] == "member"]

print(f"Admins: {len(admins)}")
print(f"Members: {len(regular_members)}")

# Promote member to admin
requests.put(
    f"{BASE_URL}/api/organizations/ml-research/members/alice",
    headers=headers,
    json={"role": "admin"}
)

# Remove inactive member
requests.delete(
    f"{BASE_URL}/api/organizations/ml-research/members/bob",
    headers=headers
)
```

### Check User's Organizations

```python
# Get all organizations for a user
response = requests.get(
    f"{BASE_URL}/api/users/alice/orgs"
)
orgs = response.json()["organizations"]

# Filter by role
admin_orgs = [o for o in orgs if o["role"] in ["admin", "super-admin"]]
member_orgs = [o for o in orgs if o["role"] == "member"]

print(f"Alice is admin of: {[o['name'] for o in admin_orgs]}")
print(f"Alice is member of: {[o['name'] for o in member_orgs]}")
```

### Python Helper Class

```python
class OrganizationManager:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def create_org(self, name: str, description: str = None):
        response = requests.post(
            f"{self.base_url}/api/organizations/create",
            headers=self.headers,
            json={"name": name, "description": description}
        )
        response.raise_for_status()
        return response.json()

    def add_member(self, org_name: str, username: str, role: str = "member"):
        response = requests.post(
            f"{self.base_url}/api/organizations/{org_name}/members",
            headers=self.headers,
            json={"username": username, "role": role}
        )
        response.raise_for_status()
        return response.json()

    def list_members(self, org_name: str):
        response = requests.get(
            f"{self.base_url}/api/organizations/{org_name}/members"
        )
        response.raise_for_status()
        return response.json()["members"]

    def update_role(self, org_name: str, username: str, new_role: str):
        response = requests.put(
            f"{self.base_url}/api/organizations/{org_name}/members/{username}",
            headers=self.headers,
            json={"role": new_role}
        )
        response.raise_for_status()
        return response.json()

    def remove_member(self, org_name: str, username: str):
        response = requests.delete(
            f"{self.base_url}/api/organizations/{org_name}/members/{username}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
org_mgr = OrganizationManager("http://localhost:28080", "YOUR_TOKEN")

# Create and setup
org_mgr.create_org("ml-team", "ML Research Team")
org_mgr.add_member("ml-team", "alice", "admin")
org_mgr.add_member("ml-team", "bob", "member")

# List and manage
members = org_mgr.list_members("ml-team")
org_mgr.update_role("ml-team", "bob", "admin")
org_mgr.remove_member("ml-team", "charlie")
```

---

## JavaScript/TypeScript Example

```javascript
class OrganizationAPI {
  constructor(baseURL, token) {
    this.baseURL = baseURL;
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async createOrg(name, description) {
    const response = await fetch(`${this.baseURL}/api/organizations/create`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ name, description })
    });
    return await response.json();
  }

  async addMember(orgName, username, role = 'member') {
    const response = await fetch(
      `${this.baseURL}/api/organizations/${orgName}/members`,
      {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({ username, role })
      }
    );
    return await response.json();
  }

  async listMembers(orgName) {
    const response = await fetch(
      `${this.baseURL}/api/organizations/${orgName}/members`
    );
    const data = await response.json();
    return data.members;
  }

  async updateRole(orgName, username, newRole) {
    const response = await fetch(
      `${this.baseURL}/api/organizations/${orgName}/members/${username}`,
      {
        method: 'PUT',
        headers: this.headers,
        body: JSON.stringify({ role: newRole })
      }
    );
    return await response.json();
  }

  async removeMember(orgName, username) {
    const response = await fetch(
      `${this.baseURL}/api/organizations/${orgName}/members/${username}`,
      {
        method: 'DELETE',
        headers: this.headers
      }
    );
    return await response.json();
  }
}

// Usage
const orgAPI = new OrganizationAPI('http://localhost:28080', 'YOUR_TOKEN');

await orgAPI.createOrg('ml-team', 'ML Research Team');
await orgAPI.addMember('ml-team', 'alice', 'admin');
const members = await orgAPI.listMembers('ml-team');
```

---

## CLI Usage

See [CLI Documentation](../CLI.md#organizations) for command-line interface:

```bash
# Create organization
kohub-cli org create myorg --description "ML Research"

# Add member
kohub-cli org add-member myorg alice --role member

# List members
kohub-cli org list-members myorg

# Update role
kohub-cli org update-role myorg alice --role admin

# Remove member
kohub-cli org remove-member myorg bob
```

---

## Next Steps

- [Invitation API](./invitations.md) - Invite users to organizations
- [Quota Management API](./quota.md) - Manage organization storage quotas
- [Settings API](./settings.md) - Update organization profile and avatar
- [Repository API](../API.md#repositories) - Create repositories under organizations
