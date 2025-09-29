from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    BooleanField,
    IntegerField,
    DateTimeField,
    AutoField,
)
from datetime import datetime
from .config import cfg

def _sqlite_path(url: str) -> str:
    return url.replace("sqlite:///", "")

db = SqliteDatabase(_sqlite_path(cfg.app.database_url), pragmas={"foreign_keys": 1})

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    id = AutoField()
    username = CharField(unique=True, index=True)

class Repository(BaseModel):
    id = AutoField()
    repo_type = CharField(index=True)  # model/dataset/space
    namespace = CharField(index=True)
    name = CharField(index=True)
    full_id = CharField(unique=True, index=True)  # "ns/name"
    private = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = ((("repo_type", "namespace", "name"), True),)

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
    created_at = DateTimeField(default=datetime.utcnow)

class File(BaseModel):
    """
    真正追蹤檔案 hash 的表，用來模擬 HuggingFace Hub 的去重判斷。
    """
    id = AutoField()
    repo_full_id = CharField(index=True)
    path_in_repo = CharField(index=True)
    size = IntegerField(default=0)
    sha256 = CharField(index=True)  # 存 huggingface 的 sha256
    lfs = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        indexes = ((("repo_full_id", "path_in_repo"), True),)

def init_db():
    db.connect(reuse_if_open=True)
    db.create_tables([User, Repository, StagingUpload, File])
