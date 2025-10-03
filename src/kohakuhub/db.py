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
    PostgresqlDatabase,
    TextField,
    ForeignKeyField,
)
from .config import cfg


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

    print(f"Connecting to postgresql://{user}:{password}@{host}:{port}/{dbname}")

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
    id = AutoField()
    username = CharField(unique=True, index=True)
    email = CharField(unique=True, index=True)
    password_hash = CharField()
    email_verified = BooleanField(default=False)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class EmailVerification(BaseModel):
    id = AutoField()
    user = IntegerField(index=True)
    token = CharField(unique=True, index=True)
    expires_at = DateTimeField()
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class Session(BaseModel):
    id = AutoField()
    session_id = CharField(unique=True, index=True)
    user_id = IntegerField(index=True)
    secret = CharField()
    expires_at = DateTimeField()
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class Token(BaseModel):
    id = AutoField()
    user_id = IntegerField(index=True)
    token_hash = CharField(unique=True, index=True)
    name = CharField()
    last_used = DateTimeField(null=True)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class Repository(BaseModel):
    id = AutoField()
    repo_type = CharField(index=True)
    namespace = CharField(index=True)
    name = CharField(index=True)
    full_id = CharField(unique=True, index=True)
    private = BooleanField(default=False)
    owner_id = IntegerField(index=True, default=1)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        indexes = ((("repo_type", "namespace", "name"), True),)


class File(BaseModel):
    id = AutoField()
    repo_full_id = CharField(index=True)
    path_in_repo = CharField(index=True)
    size = IntegerField(default=0)
    sha256 = CharField(index=True)
    lfs = BooleanField(default=False)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))
    updated_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        indexes = ((("repo_full_id", "path_in_repo"), True),)


class StagingUpload(BaseModel):
    id = AutoField()
    repo_full_id = CharField(index=True)
    repo_type = CharField(index=True)
    revision = CharField(index=True)
    path_in_repo = CharField()
    sha256 = CharField(default="")
    size = IntegerField(default=0)
    upload_id = CharField(null=True)
    storage_key = CharField()
    lfs = BooleanField(default=False)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class Organization(BaseModel):
    id = AutoField()
    name = CharField(unique=True, index=True)
    description = TextField(null=True)
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))


class UserOrganization(BaseModel):
    id = AutoField()
    user = ForeignKeyField(
        User,
        backref="user_orgs",
        on_delete="CASCADE",
        index=True,
    )
    organization = ForeignKeyField(
        Organization,
        backref="members",
        on_delete="CASCADE",
        index=True,
    )
    role = CharField(default="member")  # keep your role semantics as before
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))

    class Meta:
        indexes = ((("user", "organization"), True),)


def init_db():
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
            Organization,
            UserOrganization,
        ],
        safe=True,
    )
