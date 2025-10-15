"""Synchronous database operations with transaction support.

All database operations are now synchronous. Use db.atomic() for transactions.
Multi-worker deployment is safe with proper transaction usage.
"""

from kohakuhub.config import cfg
from kohakuhub.db import (
    Commit,
    EmailVerification,
    File,
    Invitation,
    LFSObjectHistory,
    Organization,
    Repository,
    Session,
    SSHKey,
    StagingUpload,
    Token,
    User,
    UserOrganization,
    db,
)


# User operations
def get_user_by_id(user_id: int) -> User | None:
    """Get user by ID."""
    return User.get_or_none(User.id == user_id)


def get_user_by_username(username: str) -> User | None:
    """Get user by username."""
    return User.get_or_none(User.username == username)


def get_user_by_email(email: str) -> User | None:
    """Get user by email."""
    return User.get_or_none(User.email == email)


def create_user(
    username: str,
    email: str,
    password_hash: str,
    email_verified: bool = False,
    is_active: bool = True,
    private_quota_bytes: int | None = None,
    public_quota_bytes: int | None = None,
) -> User:
    """Create a new user with default quota values if not specified.

    NOTE: Wrap in db.atomic() if checking existence first to prevent race conditions.
    """
    # Apply default quotas if not explicitly provided
    if private_quota_bytes is None:
        private_quota_bytes = cfg.quota.default_user_private_quota_bytes
    if public_quota_bytes is None:
        public_quota_bytes = cfg.quota.default_user_public_quota_bytes

    return User.create(
        username=username,
        email=email,
        password_hash=password_hash,
        email_verified=email_verified,
        is_active=is_active,
        private_quota_bytes=private_quota_bytes,
        public_quota_bytes=public_quota_bytes,
    )


def update_user(user: User, **fields) -> None:
    """Update user fields."""
    for key, value in fields.items():
        setattr(user, key, value)
    user.save()


def delete_user(user: User) -> None:
    """Delete a user and all related data.

    This will delete:
    - All sessions
    - All tokens
    - All SSH keys
    - All email verifications
    - All user-organization memberships
    - The user record itself

    NOTE: This is automatically transactional via db.atomic() wrapper.
    """
    with db.atomic():
        user_id = user.id

        # Delete all sessions
        Session.delete().where(Session.user_id == user_id).execute()

        # Delete all tokens
        Token.delete().where(Token.user_id == user_id).execute()

        # Delete all SSH keys
        SSHKey.delete().where(SSHKey.user_id == user_id).execute()

        # Delete all email verifications
        EmailVerification.delete().where(EmailVerification.user == user_id).execute()

        # Delete all user-organization memberships
        UserOrganization.delete().where(UserOrganization.user == user_id).execute()

        # Finally delete the user
        user.delete_instance()


# Repository operations
def get_repository(repo_type: str, namespace: str, name: str) -> Repository | None:
    """Get repository by type, namespace, and name."""
    return Repository.get_or_none(
        Repository.repo_type == repo_type,
        Repository.namespace == namespace,
        Repository.name == name,
    )


def get_repository_by_full_id(full_id: str, repo_type: str) -> Repository | None:
    """Get repository by full ID and type."""
    return Repository.get_or_none(
        Repository.full_id == full_id, Repository.repo_type == repo_type
    )


def create_repository(
    repo_type: str,
    namespace: str,
    name: str,
    full_id: str,
    private: bool,
    owner_id: int,
) -> Repository:
    """Create a new repository.

    NOTE: Wrap in db.atomic() if checking existence first.
    """
    return Repository.create(
        repo_type=repo_type,
        namespace=namespace,
        name=name,
        full_id=full_id,
        private=private,
        owner_id=owner_id,
    )


def delete_repository(repo: Repository) -> None:
    """Delete a repository."""
    repo.delete_instance()


def update_repository(repo: Repository, **fields) -> None:
    """Update repository fields."""
    for key, value in fields.items():
        setattr(repo, key, value)
    repo.save()


def list_repositories(
    repo_type: str | None = None, namespace: str | None = None, limit: int | None = None
) -> list[Repository]:
    """List repositories with optional filters."""
    query = Repository.select()
    if repo_type:
        query = query.where(Repository.repo_type == repo_type)
    if namespace:
        query = query.where(Repository.namespace == namespace)
    if limit:
        query = query.limit(limit)
    return list(query)


# Session operations
def get_session(session_id: str) -> Session | None:
    """Get session by session ID."""
    return Session.get_or_none(Session.session_id == session_id)


def create_session(session_id: str, user_id: int, secret: str, expires_at) -> Session:
    """Create a new session."""
    return Session.create(
        session_id=session_id, user_id=user_id, secret=secret, expires_at=expires_at
    )


def delete_session(session_id: str) -> None:
    """Delete a session."""
    Session.delete().where(Session.session_id == session_id).execute()


# Token operations
def get_token_by_hash(token_hash: str) -> Token | None:
    """Get token by hash."""
    return Token.get_or_none(Token.token_hash == token_hash)


def create_token(user_id: int, token_hash: str, name: str) -> Token:
    """Create a new API token."""
    return Token.create(user_id=user_id, token_hash=token_hash, name=name)


def list_user_tokens(user_id: int) -> list[Token]:
    """List all tokens for a user."""
    return list(Token.select().where(Token.user_id == user_id))


def delete_token(token_id: int) -> None:
    """Delete a token."""
    Token.delete().where(Token.id == token_id).execute()


def update_token_last_used(token: Token, last_used) -> None:
    """Update token last used timestamp."""
    token.last_used = last_used
    token.save()


# Organization operations
def get_organization(name: str) -> Organization | None:
    """Get organization by name."""
    return Organization.get_or_none(Organization.name == name)


def create_organization(
    name: str,
    description: str | None = None,
    private_quota_bytes: int | None = None,
    public_quota_bytes: int | None = None,
) -> Organization:
    """Create a new organization with default quota values if not specified."""
    if private_quota_bytes is None:
        private_quota_bytes = cfg.quota.default_org_private_quota_bytes
    if public_quota_bytes is None:
        public_quota_bytes = cfg.quota.default_org_public_quota_bytes

    return Organization.create(
        name=name,
        description=description,
        private_quota_bytes=private_quota_bytes,
        public_quota_bytes=public_quota_bytes,
    )


def update_organization(org: Organization, **fields) -> None:
    """Update organization fields."""
    for key, value in fields.items():
        setattr(org, key, value)
    org.save()


def delete_organization(org: Organization) -> None:
    """Delete an organization."""
    org.delete_instance()


# UserOrganization operations
def get_user_organization(user_id: int, org_id: int) -> UserOrganization | None:
    """Get user-organization relationship."""
    return UserOrganization.get_or_none(
        UserOrganization.user == user_id, UserOrganization.organization == org_id
    )


def create_user_organization(user_id: int, org_id: int, role: str) -> UserOrganization:
    """Create user-organization relationship."""
    return UserOrganization.create(user=user_id, organization=org_id, role=role)


def update_user_organization(user_org: UserOrganization, **fields) -> None:
    """Update user-organization fields."""
    for key, value in fields.items():
        setattr(user_org, key, value)
    user_org.save()


def delete_user_organization(user_org: UserOrganization) -> None:
    """Delete user-organization relationship."""
    user_org.delete_instance()


def list_user_organizations(user_id: int) -> list[UserOrganization]:
    """List all organizations for a user."""
    return list(UserOrganization.select().where(UserOrganization.user == user_id))


def list_organization_members(org_id: int) -> list[UserOrganization]:
    """List all members of an organization."""
    return list(
        UserOrganization.select().where(UserOrganization.organization == org_id)
    )


# File operations
def get_file(repo_full_id: str, path_in_repo: str) -> File | None:
    """Get file by repository and path."""
    return File.get_or_none(
        File.repo_full_id == repo_full_id, File.path_in_repo == path_in_repo
    )


def get_file_by_sha256(sha256: str) -> File | None:
    """Get file by SHA256 hash."""
    return File.get_or_none(File.sha256 == sha256)


def create_file(
    repo_full_id: str, path_in_repo: str, size: int, sha256: str, lfs: bool
) -> File:
    """Create a new file record."""
    return File.create(
        repo_full_id=repo_full_id,
        path_in_repo=path_in_repo,
        size=size,
        sha256=sha256,
        lfs=lfs,
    )


def update_file(file: File, **fields) -> None:
    """Update file fields."""
    for key, value in fields.items():
        setattr(file, key, value)
    file.save()


def delete_file(file: File) -> None:
    """Delete a file record."""
    file.delete_instance()


# Commit operations
def create_commit(
    commit_id: str,
    repo_full_id: str,
    repo_type: str,
    branch: str,
    user_id: int,
    username: str,
    message: str,
    description: str = "",
) -> Commit:
    """Create commit record."""
    return Commit.create(
        commit_id=commit_id,
        repo_full_id=repo_full_id,
        repo_type=repo_type,
        branch=branch,
        user_id=user_id,
        username=username,
        message=message,
        description=description,
    )


def get_commit(commit_id: str, repo_full_id: str) -> Commit | None:
    """Get commit by ID and repo."""
    return Commit.get_or_none(
        Commit.commit_id == commit_id, Commit.repo_full_id == repo_full_id
    )


def list_commits_by_repo(
    repo_full_id: str, branch: str | None = None, limit: int | None = None
) -> list[Commit]:
    """List commits for a repository."""
    query = Commit.select().where(Commit.repo_full_id == repo_full_id)
    if branch:
        query = query.where(Commit.branch == branch)
    query = query.order_by(Commit.created_at.desc())
    if limit:
        query = query.limit(limit)
    return list(query)


# SSH Key operations
def get_ssh_key_by_id(key_id: int) -> SSHKey | None:
    """Get SSH key by ID."""
    return SSHKey.get_or_none(SSHKey.id == key_id)


def get_ssh_key_by_fingerprint(fingerprint: str) -> SSHKey | None:
    """Get SSH key by fingerprint."""
    return SSHKey.get_or_none(SSHKey.fingerprint == fingerprint)


def list_user_ssh_keys(user_id: int) -> list[SSHKey]:
    """List all SSH keys for a user."""
    return list(
        SSHKey.select()
        .where(SSHKey.user_id == user_id)
        .order_by(SSHKey.created_at.desc())
    )


def create_ssh_key(
    user_id: int, key_type: str, public_key: str, fingerprint: str, title: str
) -> SSHKey:
    """Create a new SSH key."""
    return SSHKey.create(
        user_id=user_id,
        key_type=key_type,
        public_key=public_key,
        fingerprint=fingerprint,
        title=title,
    )


def update_ssh_key(key: SSHKey, **fields) -> None:
    """Update SSH key fields."""
    for field_name, value in fields.items():
        setattr(key, field_name, value)
    key.save()


def delete_ssh_key(key: SSHKey) -> None:
    """Delete an SSH key."""
    key.delete_instance()


# LFS operations
def create_lfs_history(
    repo_full_id: str, path_in_repo: str, sha256: str, size: int, commit_id: str
) -> LFSObjectHistory:
    """Create LFS object history record."""
    return LFSObjectHistory.create(
        repo_full_id=repo_full_id,
        path_in_repo=path_in_repo,
        sha256=sha256,
        size=size,
        commit_id=commit_id,
    )


def list_lfs_history(
    repo_full_id: str, path_in_repo: str, limit: int | None = None
) -> list[LFSObjectHistory]:
    """List LFS history for a file."""
    query = (
        LFSObjectHistory.select()
        .where(
            LFSObjectHistory.repo_full_id == repo_full_id,
            LFSObjectHistory.path_in_repo == path_in_repo,
        )
        .order_by(LFSObjectHistory.created_at.desc())
    )
    if limit:
        query = query.limit(limit)
    return list(query)


# Email verification operations
def create_email_verification(
    user_id: int, token: str, expires_at
) -> EmailVerification:
    """Create email verification token."""
    return EmailVerification.create(user=user_id, token=token, expires_at=expires_at)


def get_email_verification(token: str) -> EmailVerification | None:
    """Get email verification by token."""
    return EmailVerification.get_or_none(EmailVerification.token == token)


def delete_email_verification(verification: EmailVerification) -> None:
    """Delete email verification."""
    verification.delete_instance()


# Staging upload operations
def create_staging_upload(
    repo_full_id: str,
    repo_type: str,
    revision: str,
    path_in_repo: str,
    sha256: str,
    size: int,
    storage_key: str,
    lfs: bool,
    upload_id: str | None = None,
) -> StagingUpload:
    """Create a staging upload record."""
    return StagingUpload.create(
        repo_full_id=repo_full_id,
        repo_type=repo_type,
        revision=revision,
        path_in_repo=path_in_repo,
        sha256=sha256,
        size=size,
        storage_key=storage_key,
        lfs=lfs,
        upload_id=upload_id,
    )


def delete_staging_upload(staging: StagingUpload) -> None:
    """Delete a staging upload record."""
    staging.delete_instance()


# Invitation operations
def create_invitation(
    token: str,
    action: str,
    parameters: str,
    created_by: int,
    expires_at,
    max_usage: int | None = None,
) -> Invitation:
    """Create a new invitation.

    Args:
        token: Unique invitation token (UUID)
        action: Action type (e.g., "join_org", "register_account")
        parameters: JSON string with action-specific data
        created_by: User ID who created the invitation
        expires_at: Expiration datetime
        max_usage: Maximum usage count (None=one-time, -1=unlimited, N=max N uses)

    Returns:
        Created invitation

    Note: Wrap in db.atomic() if checking existence first.
    """
    return Invitation.create(
        token=token,
        action=action,
        parameters=parameters,
        created_by=created_by,
        expires_at=expires_at,
        max_usage=max_usage,
        usage_count=0,
    )


def get_invitation(token: str) -> Invitation | None:
    """Get invitation by token."""
    return Invitation.get_or_none(Invitation.token == token)


def get_invitation_by_id(invitation_id: int) -> Invitation | None:
    """Get invitation by ID."""
    return Invitation.get_or_none(Invitation.id == invitation_id)


def mark_invitation_used(invitation: Invitation, user_id: int) -> None:
    """Mark invitation as used by a user.

    For multi-use invitations, this increments usage_count.
    For single-use invitations, it also sets used_at and used_by.
    """
    from datetime import datetime, timezone

    # Increment usage count
    invitation.usage_count += 1

    # For first use, set used_at and used_by (legacy fields)
    if invitation.used_at is None:
        invitation.used_at = datetime.now(timezone.utc)
        invitation.used_by = user_id

    invitation.save()


def check_invitation_available(invitation: Invitation) -> tuple[bool, str | None]:
    """Check if invitation can still be used.

    Args:
        invitation: Invitation to check

    Returns:
        Tuple of (is_available, error_message)
    """
    from datetime import datetime, timezone

    # Check expiration
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        return False, "Invitation has expired"

    # Check usage limit
    if invitation.max_usage is None:
        # One-time use (legacy)
        if invitation.used_at is not None:
            return False, "Invitation has already been used"
    elif invitation.max_usage == -1:
        # Unlimited use
        return True, None
    else:
        # Limited use (check count)
        if invitation.usage_count >= invitation.max_usage:
            return False, f"Invitation has reached maximum usage limit ({invitation.max_usage})"

    return True, None


def delete_invitation(invitation: Invitation) -> None:
    """Delete an invitation."""
    invitation.delete_instance()


def list_org_invitations(org_id: int) -> list[Invitation]:
    """List all invitations for an organization.

    Args:
        org_id: Organization ID

    Returns:
        List of invitations (both pending and used)
    """
    import json

    # Get all invitations with action "join_org" and matching org_id in parameters
    invitations = []
    all_invites = Invitation.select().where(Invitation.action == "join_org")

    for invite in all_invites:
        try:
            params = json.loads(invite.parameters)
            if params.get("org_id") == org_id:
                invitations.append(invite)
        except (json.JSONDecodeError, KeyError):
            continue

    return invitations


def delete_expired_invitations() -> int:
    """Delete all expired invitations.

    Returns:
        Number of invitations deleted
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    deleted = (
        Invitation.delete()
        .where(Invitation.expires_at < now, Invitation.used_at.is_null())
        .execute()
    )

    return deleted
