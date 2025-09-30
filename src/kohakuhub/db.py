"""Database models for Kohaku Hub."""

from functools import partial
from datetime import datetime, timezone

from peewee import (
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    IntegerField,
    Model,
    SqliteDatabase,
)

from .config import cfg


def _sqlite_path(url: str) -> str:
    """Extract file path from SQLite URL."""
    return url.replace("sqlite:///", "")


# Database connection
db = SqliteDatabase(_sqlite_path(cfg.app.database_url), pragmas={"foreign_keys": 1})


class BaseModel(Model):
    """Base model with database connection."""

    class Meta:
        database = db


class User(BaseModel):
    """User account (placeholder for future auth)."""

    id = AutoField()
    username = CharField(unique=True, index=True)


class Repository(BaseModel):
    """Repository metadata."""

    id = AutoField()
    repo_type = CharField(index=True)  # model/dataset/space
    namespace = CharField(index=True)  # org or username
    name = CharField(index=True)
    full_id = CharField(unique=True, index=True)  # "namespace/name"
    private = BooleanField(default=False)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        indexes = ((("repo_type", "namespace", "name"), True),)  # Unique constraint


class File(BaseModel):
    """File tracking for content deduplication.

    Tracks SHA256 hashes to implement HuggingFace's shouldIgnore mechanism.
    When a file with the same hash already exists, we skip the upload.
    """

    id = AutoField()
    repo_full_id = CharField(index=True)
    path_in_repo = CharField(index=True)
    size = IntegerField(default=0)
    sha256 = CharField(index=True)  # Content hash for deduplication
    lfs = BooleanField(default=False)  # True if file uses LFS
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))
    updated_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        indexes = ((("repo_full_id", "path_in_repo"), True),)  # Unique constraint


class StagingUpload(BaseModel):
    """Staging area for multipart/LFS uploads.

    Optional table for tracking in-progress uploads.
    Useful for resume functionality and cleanup of abandoned uploads.
    """

    id = AutoField()
    repo_full_id = CharField(index=True)
    repo_type = CharField(index=True)
    revision = CharField(index=True)
    path_in_repo = CharField()
    sha256 = CharField(default="")
    size = IntegerField(default=0)
    upload_id = CharField(null=True)  # S3 multipart upload ID
    storage_key = CharField()  # S3 object key
    lfs = BooleanField(default=False)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


def init_db():
    """Initialize database tables."""
    db.connect(reuse_if_open=True)
    db.create_tables([User, Repository, File, StagingUpload], safe=True)
