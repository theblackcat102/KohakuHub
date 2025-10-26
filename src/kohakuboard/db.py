"""Database models for KohakuBoard.

Separate from KohakuHub for licensing compliance (AGPL-3.0).
Can be optionally integrated with KohakuHub by connecting to same database.
"""

from datetime import datetime, timezone
from functools import partial

from peewee import (
    AutoField,
    BigIntegerField,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    Model,
    PostgresqlDatabase,
    SqliteDatabase,
    TextField,
)

# Database connection will be initialized based on config
db = None


def init_db(backend: str, database_url: str):
    """Initialize database connection"""
    global db

    if backend == "postgres":
        # Parse PostgreSQL URL
        url = database_url.replace("postgresql://", "")
        user_pass, host_db = url.split("@")
        user, password = user_pass.split(":")
        host_port, dbname = host_db.split("/")
        if ":" in host_port:
            host, port = host_port.split(":")
        else:
            host, port = host_port, 5432

        db = PostgresqlDatabase(
            dbname,
            user=user,
            password=password,
            host=host,
            port=int(port),
        )
    else:
        # SQLite
        db_path = database_url.replace("sqlite:///", "")
        db = SqliteDatabase(db_path, pragmas={"foreign_keys": 1})

    # Create tables
    with db:
        db.create_tables(
            [User, Session, Token, Board],
            safe=True,
        )

    return db


class BaseModel(Model):
    """Base model for all database models"""

    class Meta:
        database = db


class User(BaseModel):
    """User model for authentication

    Can coexist with KohakuHub User table (same table name).
    When integrated with KohakuHub, both systems use the same users.
    """

    id = AutoField()
    username = CharField(unique=True, index=True)
    email = CharField(unique=True, index=True)
    password_hash = CharField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        table_name = "user"  # Same as KohakuHub for compatibility


class Session(BaseModel):
    """User session for web authentication"""

    id = AutoField()
    session_id = CharField(unique=True, index=True)
    user = ForeignKeyField(User, backref="sessions", on_delete="CASCADE", index=True)
    secret = CharField()
    expires_at = DateTimeField()
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        table_name = "session"


class Token(BaseModel):
    """API token for programmatic access"""

    id = AutoField()
    user = ForeignKeyField(User, backref="tokens", on_delete="CASCADE", index=True)
    token_hash = CharField(unique=True, index=True)
    name = CharField()
    last_used = DateTimeField(null=True)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        table_name = "token"


class Board(BaseModel):
    """Board metadata for remote hosting

    Stores information about uploaded training runs.
    """

    id = AutoField()
    run_id = CharField(unique=True, index=True)  # Globally unique identifier
    name = CharField()  # Human-readable name
    project_name = CharField(index=True)  # User-defined project grouping
    owner = ForeignKeyField(User, backref="boards", on_delete="CASCADE", index=True)
    private = BooleanField(default=True)  # Public/private visibility

    # Storage metadata
    config = TextField(null=True)  # JSON string of config dict
    backend = CharField(default="duckdb")  # "duckdb" or "parquet"
    storage_path = CharField()  # Relative path: users/{username}/{project}/{run_id}
    total_size_bytes = BigIntegerField(default=0)

    # Timestamps
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))
    updated_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))
    last_synced_at = DateTimeField(null=True)

    class Meta:
        table_name = "board"
        indexes = (
            (("owner_id", "project_name"), False),
        )  # Index for fast project queries
