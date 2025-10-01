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
)
from .config import cfg


def _sqlite_path(url: str) -> str:
    return url.replace("sqlite:///", "")


# Choose DB backend
if cfg.app.db_backend == "postgres":
    # Example: postgresql://user:pass@host:5432/dbname
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


class Repository(BaseModel):
    id = AutoField()
    repo_type = CharField(index=True)
    namespace = CharField(index=True)
    name = CharField(index=True)
    full_id = CharField(unique=True, index=True)
    private = BooleanField(default=False)
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


def init_db():
    db.connect(reuse_if_open=True)
    db.create_tables([User, Repository, File, StagingUpload], safe=True)
