# Organization Management API Module

## Overview

The `kohakuhub.api.org` module provides comprehensive organization management capabilities for KohakuHub. It implements a complete RESTful API for creating, managing, and querying organizations and their memberships, including role-based access control (RBAC) and quota management.

## Purpose

This module serves as the central interface for all organization-related operations in KohakuHub, enabling:

- Multi-user collaboration through organizations
- Hierarchical permission management with role-based access
- Resource quota allocation and tracking
- Organization membership lifecycle management

## Key Features

### Organization Management
- **Organization Creation**: Create new organizations with configurable descriptions and automatic quota allocation
- **Organization Retrieval**: Query organization details by name
- **Default Quotas**: Automatically apply system-defined default quotas for private and public resources

### Member Management
- **Add Members**: Add users to organizations with specific roles
- **Remove Members**: Remove users from organization membership
- **Update Roles**: Modify member roles within organizations
- **List Members**: Retrieve all members and their roles for an organization
- **List User Organizations**: Query all organizations a user belongs to

### Role-Based Access Control
The module implements a three-tier role hierarchy:
- **super-admin**: Organization creator with full administrative privileges
- **admin**: Administrative privileges for member management
- **member**: Basic organization membership (roles are extensible)

### Authorization
- Admin and super-admin roles required for member management operations
- Organization creators automatically receive super-admin role
- Permission checks enforce access control on all protected endpoints

## Architecture

### Components

#### router.py
The main API router defining all organization-related endpoints.

**Endpoints:**

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `/create` | Create a new organization | Yes |
| GET | `/{org_name}` | Get organization details | No |
| POST | `/{org_name}/members` | Add member to organization | Yes (Admin) |
| DELETE | `/{org_name}/members/{username}` | Remove member from organization | Yes (Admin) |
| PUT | `/{org_name}/members/{username}` | Update member role | Yes (Admin) |
| GET | `/{org_name}/members` | List organization members | No |
| GET | `/users/{username}/orgs` | List user's organizations | No |

**Request/Response Models:**

```python
# Create organization
CreateOrganizationPayload:
    - name: str
    - description: str | None

# Add member
AddMemberPayload:
    - username: str
    - role: str

# Update member role
UpdateMemberRolePayload:
    - role: str
```

#### util.py
Utility functions providing core business logic for organization operations.

**Functions:**

- `create_organization(name, description, user)`: Creates organization with default quotas (deprecated, synchronous)
- `get_organization_details(name)`: Retrieves organization by name
- `add_member_to_organization(org_id, username, role)`: Adds user to organization with specified role
- `remove_member_from_organization(org_id, username)`: Removes user from organization
- `get_user_organizations(user_id)`: Retrieves all organizations for a user with joined data
- `update_member_role(org_id, username, role)`: Updates member's role in organization

**Note:** The synchronous `create_organization` function is deprecated. The module uses async database operations from `kohakuhub.db_operations` for organization creation.

## Operation Flow

### Creating an Organization

1. User sends POST request to `/create` with organization name and optional description
2. System validates authentication via `get_current_user` dependency
3. Atomic transaction checks for name uniqueness
4. Organization created with default quotas from configuration:
   - `default_org_private_quota_bytes`
   - `default_org_public_quota_bytes`
5. Creator automatically added as super-admin member
6. Operation logged and success response returned

### Managing Members

**Adding a Member:**
1. Admin/super-admin sends POST request to `/{org_name}/members`
2. System verifies organization exists
3. Authorization check confirms requester has admin/super-admin role
4. Validates target user exists
5. Checks user is not already a member
6. Creates UserOrganization relationship with specified role

**Removing a Member:**
1. Admin/super-admin sends DELETE request to `/{org_name}/members/{username}`
2. System verifies organization and authorization
3. Validates membership exists
4. Deletes UserOrganization relationship

**Updating Member Role:**
1. Admin/super-admin sends PUT request with new role
2. System verifies organization, authorization, and membership
3. Updates role field in UserOrganization
4. Changes persisted to database

### Querying Organizations

**Organization Details:**
- Public endpoint returning name, description, and creation timestamp
- No authentication required

**Organization Members:**
- Public endpoint listing all members with usernames and roles
- Uses database join to efficiently retrieve user information

**User Organizations:**
- Public endpoint showing all organizations a user belongs to
- Returns organization details and user's role in each
- Uses FK-based join for efficient data retrieval

## Database Integration

The module interacts with three primary database models:

- **Organization**: Stores organization metadata, quotas, and timestamps
- **User**: User accounts referenced in membership relationships
- **UserOrganization**: Junction table tracking membership and roles

Database operations use a mix of:
- Synchronous ORM queries via Peewee (utility functions)
- Async operations via `kohakuhub.db_operations` (router endpoints)
- Atomic transactions for data consistency

## Error Handling

The module implements comprehensive error handling:

| Status Code | Scenario |
|-------------|----------|
| 400 | Organization name already exists, user already member |
| 403 | Insufficient permissions for operation |
| 404 | Organization not found, user not found, member not found |

All errors return structured HTTPException responses with descriptive messages.

## Dependencies

**External:**
- `fastapi`: API framework and routing
- `pydantic`: Request/response validation
- `peewee`: ORM for database operations

**Internal:**
- `kohakuhub.db`: Database models and connection
- `kohakuhub.db_operations`: Async database operations
- `kohakuhub.auth.dependencies`: Authentication middleware
- `kohakuhub.config`: Configuration management
- `kohakuhub.logger`: Logging infrastructure

## Usage Example

```python
from kohakuhub.api.org import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router, prefix="/api/org", tags=["organizations"])
```

## Logging

All significant operations are logged using the "ORG" logger:
- Organization creation events
- Member management operations
- Error conditions

## Future Considerations

- The synchronous `create_organization` utility function is marked deprecated
- Consider fully migrating to async database operations
- Potential for adding organization update/deletion endpoints
- Role hierarchy and permission model could be further formalized
- Quota enforcement mechanisms may be expanded
