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
- **super-admin**: Organization creator with full administrative privileges.
- **admin**: Administrative privileges for member management.
- **member**: Basic organization membership with write access to repositories.

### Authorization
- Admin and super-admin roles required for member management operations.
- Organization creators automatically receive super-admin role.
- Permission checks enforce access control on all protected endpoints.

## Database Integration

The module interacts with three primary database models:

- **User**: A unified model representing both users and organizations. Organizations are distinguished by the `is_org=True` flag. This model stores metadata, quotas, and timestamps.
- **UserOrganization**: A junction table tracking membership and roles, linking users to organizations.

Database operations are primarily handled by `kohakuhub.db_operations` and leverage atomic transactions for data consistency.


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
