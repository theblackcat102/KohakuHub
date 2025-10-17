"""Database models for Kohaku Hub.

Major refactoring: Merged User and Organization into unified User model.
All relationships now use proper ForeignKey constraints for data integrity.
"""

from datetime import datetime, timezone
from functools import partial

from peewee import (
    AutoField,
    BigIntegerField,
    BlobField,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    PostgresqlDatabase,
    SqliteDatabase,
    TextField,
)

from kohakuhub.config import cfg
from kohakuhub.logger import get_logger

logger = get_logger("DB")


def _sqlite_path(url: str) -> str:
    return url.replace("sqlite:///", "")


# Choose DB backend
if cfg.app.db_backend == "postgres":
    url = cfg.app.database_url.replace("postgresql://", "")
    user_pass, host_db = url.split("@")
    user, password = user_pass.split(":")
    host_port, dbname = host_db.split("/")
    if ":" in host_port:
        host, port = host_port.split(":")
    else:
        host, port = host_port, 5432

    logger.info(f"Connecting to PostgreSQL: {user}@{host}:{port}/{dbname}")

    db = PostgresqlDatabase(
        dbname,
        user=user,
        password=password,
        host=host,
        port=int(port),
    )
else:
    db = SqliteDatabase(_sqlite_path(cfg.app.database_url), pragmas={"foreign_keys": 1})


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    """Unified User/Organization model.

    When is_org=False: Regular user with email/password
    When is_org=True: Organization (no email/password required)
    """

    id = AutoField()
    username = CharField(unique=True, index=True)
    normalized_name = CharField(
        unique=True, index=True
    )  # Normalized username for fast conflict checking
    is_org = BooleanField(default=False, index=True)  # True for organizations

    # User-specific fields (nullable for orgs)
    email = CharField(unique=True, index=True, null=True)
    password_hash = CharField(null=True)
    email_verified = BooleanField(default=False)
    is_active = BooleanField(default=True)

    # Separate quotas for private and public repositories
    private_quota_bytes = BigIntegerField(null=True)  # NULL = unlimited
    public_quota_bytes = BigIntegerField(null=True)  # NULL = unlimited
    private_used_bytes = BigIntegerField(default=0)
    public_used_bytes = BigIntegerField(default=0)

    # Profile fields (shared by both users and orgs)
    full_name = CharField(null=True)
    bio = TextField(null=True)
    description = TextField(null=True)  # For backward compat with orgs
    website = CharField(null=True)
    social_media = TextField(
        null=True
    )  # JSON: {twitter_x, threads, github, huggingface}

    # Avatar (1024x1024 JPEG stored as binary)
    avatar = BlobField(null=True)  # Binary JPEG data
    avatar_updated_at = DateTimeField(null=True)  # Track updates for cache busting
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class EmailVerification(BaseModel):
    id = AutoField()
    user = ForeignKeyField(
        User, backref="email_verifications", on_delete="CASCADE", index=True
    )
    token = CharField(unique=True, index=True)
    expires_at = DateTimeField()
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class Session(BaseModel):
    id = AutoField()
    session_id = CharField(unique=True, index=True)
    user = ForeignKeyField(User, backref="sessions", on_delete="CASCADE", index=True)
    secret = CharField()
    expires_at = DateTimeField()
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class Token(BaseModel):
    id = AutoField()
    user = ForeignKeyField(User, backref="tokens", on_delete="CASCADE", index=True)
    token_hash = CharField(unique=True, index=True)
    name = CharField()
    last_used = DateTimeField(null=True)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class Repository(BaseModel):
    """Repository model BEFORE migration 009 (no LFS settings)."""

    id = AutoField()
    repo_type = CharField(index=True)
    namespace = CharField(index=True)
    name = CharField(index=True)
    full_id = CharField(index=True)  # Not unique - same full_id can exist across types
    private = BooleanField(default=False)
    owner = ForeignKeyField(
        User, backref="owned_repos", on_delete="CASCADE", index=True
    )

    # Repository-specific quota (NULL = inherit from namespace)
    quota_bytes = BigIntegerField(
        null=True
    )  # NULL = no specific limit, inherit from namespace
    used_bytes = BigIntegerField(default=0)

    # LFS settings (added in migration 009)
    lfs_threshold_bytes = IntegerField(null=True)
    lfs_keep_versions = IntegerField(null=True)
    lfs_suffix_rules = TextField(null=True)

    # NOTE: Social metrics NOT present - this represents schema BEFORE migration 010
    # Migration 010 will add:
    # - downloads
    # - likes_count

    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        # Unique constraint on (repo_type, namespace, name) allows same name across types
        indexes = ((("repo_type", "namespace", "name"), True),)


class File(BaseModel):
    id = AutoField()
    repository = ForeignKeyField(
        Repository, backref="files", on_delete="CASCADE", index=True
    )
    path_in_repo = CharField(index=True)
    size = IntegerField(default=0)
    sha256 = CharField(index=True)
    lfs = BooleanField(default=False)
    owner = ForeignKeyField(
        User, backref="owned_files", on_delete="CASCADE", index=True
    )  # Repository owner (denormalized for convenience)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))
    updated_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        indexes = ((("repository", "path_in_repo"), True),)


class StagingUpload(BaseModel):
    id = AutoField()
    repository = ForeignKeyField(
        Repository, backref="staging_uploads", on_delete="CASCADE", index=True
    )
    repo_type = CharField(index=True)
    revision = CharField(index=True)
    path_in_repo = CharField()
    sha256 = CharField(default="")
    size = IntegerField(default=0)
    upload_id = CharField(null=True)
    storage_key = CharField()
    lfs = BooleanField(default=False)
    uploader = ForeignKeyField(
        User, backref="uploads", on_delete="SET NULL", null=True, index=True
    )
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class UserOrganization(BaseModel):
    """User-Organization membership.

    Links regular users (is_org=False) to organizations (is_org=True).
    """

    id = AutoField()
    user = ForeignKeyField(
        User, backref="org_memberships", on_delete="CASCADE", index=True
    )
    organization = ForeignKeyField(
        User, backref="members", on_delete="CASCADE", index=True
    )
    role = CharField(default="member")  # visitor, member, admin, super-admin
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        indexes = ((("user", "organization"), True),)  # Unique membership


class Commit(BaseModel):
    """Track commits made by users (LakeFS doesn't track the actual user).

    author = actual user who made the commit
    owner = repository owner (user or org, denormalized for convenience)
    """

    id = AutoField()
    commit_id = CharField(index=True)  # LakeFS commit ID (SHA)
    repository = ForeignKeyField(
        Repository, backref="commits", on_delete="CASCADE", index=True
    )
    repo_type = CharField(index=True)  # model/dataset/space
    branch = CharField(index=True)  # Branch name
    author = ForeignKeyField(
        User, backref="authored_commits", on_delete="CASCADE", index=True
    )  # User who made commit
    owner = ForeignKeyField(
        User, backref="owned_commits", on_delete="CASCADE", index=True
    )  # Repository owner (denormalized)
    username = CharField(index=True)  # Username (denormalized for performance)
    message = TextField()  # Commit message
    description = TextField(default="")  # Optional description
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        indexes = (
            (("repository", "branch"), False),  # Query commits by repo+branch
            (("commit_id", "repository"), True),  # Unique commit per repo
        )


class LFSObjectHistory(BaseModel):
    """Track LFS object usage history for garbage collection.

    Keeps track of which commits reference which LFS objects,
    allowing us to preserve K versions of each file.
    """

    id = AutoField()
    repository = ForeignKeyField(
        Repository, backref="lfs_history", on_delete="CASCADE", index=True
    )
    path_in_repo = CharField(index=True)  # File path
    sha256 = CharField(index=True)  # LFS object hash
    size = IntegerField()
    commit_id = CharField(index=True)  # LakeFS commit ID
    # Optional link to File record for faster lookups
    file = ForeignKeyField(
        File, backref="lfs_versions", on_delete="CASCADE", null=True, index=True
    )
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        # Index for quick lookups by repo and path
        indexes = (
            (("repository", "path_in_repo"), False),
            (("sha256",), False),
        )


class SSHKey(BaseModel):
    """User SSH public keys for Git operations."""

    id = AutoField()
    user = ForeignKeyField(User, backref="ssh_keys", on_delete="CASCADE", index=True)
    key_type = CharField()  # "ssh-rsa", "ssh-ed25519", "ecdsa-sha2-nistp256", etc.
    public_key = TextField()  # Full public key content
    fingerprint = CharField(unique=True, index=True)  # SHA256 fingerprint for lookup
    title = CharField()  # User-friendly title/name for the key
    last_used = DateTimeField(null=True)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        indexes = ((("user", "fingerprint"), True),)  # Unique per user


class Invitation(BaseModel):
    """Generic invitation system for various actions (org invites, account registration, etc.)."""

    id = AutoField()
    token = CharField(unique=True, index=True)  # UUID for invitation link
    action = CharField(index=True)  # "join_org", "register_account", etc.
    parameters = (
        TextField()
    )  # JSON string for action-specific data (org_id, role, etc.)
    created_by = ForeignKeyField(
        User, backref="created_invitations", on_delete="CASCADE", index=True
    )
    expires_at = DateTimeField()

    # Multi-use support
    max_usage = IntegerField(null=True)  # NULL=one-time, -1=unlimited, N=max N uses
    usage_count = IntegerField(default=0)  # Track how many times used

    # Legacy fields (kept for single-use compatibility)
    used_at = DateTimeField(null=True)  # First use timestamp
    used_by = ForeignKeyField(
        User, backref="used_invitations", on_delete="SET NULL", null=True, index=True
    )
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        indexes = (
            (
                ("action", "created_by"),
                False,
            ),  # Query invitations by action and creator
        )


def init_db():
    """Initialize database with OLD schema (before migration 010).

    NOTE: RepositoryLike, DownloadSession, DailyRepoStats are NOT included.
    These tables are added by migration 010.
    """
    db.connect(reuse_if_open=True)
    db.create_tables(
        [
            User,
            EmailVerification,
            Session,
            Token,
            Repository,
            File,
            StagingUpload,
            UserOrganization,
            Commit,
            LFSObjectHistory,
            SSHKey,
            Invitation,
            # NOTE: RepositoryLike, DownloadSession, DailyRepoStats NOT included
            # Migration 010 adds these tables
        ],
        safe=True,
    )
