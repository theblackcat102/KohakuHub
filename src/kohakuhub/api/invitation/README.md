# Invitation API Module

## Overview

The `kohakuhub.api.invitation` module provides a flexible and secure system for managing invitations within KohakuHub. It supports different types of invitations, such as joining an organization or registering a new account, and allows for both single-use and multi-use tokens with configurable expiration dates.

## Key Features

- **Action-Based Invitations**: Create invitations for specific actions, like `join_org` or `register_account`.
- **Organization Invites**: Admins of an organization can invite new members, specifying their role (`visitor`, `member`, or `admin`).
- **Registration Invites**: In an invitation-only deployment, admins can generate tokens that allow new users to register.
- **Multi-Use Tokens**: Invitations can be configured for a single use, a specific number of uses, or unlimited uses.
- **Expiration Dates**: All invitations have a configurable expiration date.
- **Email Integration**: Automatically sends email invitations to users when an email address is provided.

## Module Structure

- **`router.py`**: Contains all the FastAPI endpoints for creating, viewing, and accepting invitations.

## How It Works

1.  **Creation**: An authorized user (e.g., an organization admin) creates an invitation for a specific action. A unique, secure token is generated and stored in the database along with the action, parameters (like `org_id` and `role`), usage limits, and an expiration date.
2.  **Sharing**: The invitation link, which contains the token (e.g., `https://hub.example.com/invite/{token}`), is shared with the intended user. If an email is provided, the system can send the invitation directly to the user.
3.  **Acceptance**: The user clicks the link and accepts the invitation. The system validates the token, checks its availability (i.e., not expired or fully used), and then executes the associated action (e.g., adds the user to the organization).
4.  **Usage Tracking**: Each time an invitation is successfully used, its `usage_count` is incremented.

## API Endpoints

All invitation endpoints are prefixed with `/api/invitations`.

- **`POST /org/{org_name}/create`**: Creates an invitation to join an organization.
- **`GET /{token}`**: Retrieves the details of an invitation without accepting it.
- **`POST /{token}/accept`**: Accepts an invitation.
- **`GET /org/{org_name}/list`**: Lists all pending invitations for an organization.
- **`DELETE /{token}`**: Deletes or cancels an invitation.

## Database Integration

The invitation system relies on the `Invitation` model in the database, which stores all the necessary information for each invitation, including the token, action, parameters, creator, usage data, and expiration date.
