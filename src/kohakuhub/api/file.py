import httpx
import json
import base64
import io
import hashlib
from fastapi import APIRouter, HTTPException, Request, Depends
from enum import Enum
from typing import Dict, Any, List, Optional
from ..config import cfg
from ..db import StagingUpload, Repository, File
import boto3, uuid, time
from botocore.config import Config as BotoConfig
from .auth import get_current_user
from datetime import datetime

router = APIRouter()


class RepoType(str, Enum):
    model = "model"
    dataset = "dataset"
    space = "space"


def _s3_client():
    bc = BotoConfig(s3={"addressing_style": "path"} if cfg.s3.force_path_style else {})
    return boto3.client(
        "s3",
        endpoint_url=cfg.s3.endpoint,
        aws_access_key_id=cfg.s3.access_key,
        aws_secret_access_key=cfg.s3.secret_key,
        region_name=cfg.s3.region,
        config=bc,
    )


def _lakefs_repo_name(repo_type: str, repo_id: str) -> str:
    return f"{cfg.lakefs.repo_namespace}-{repo_type}-{repo_id.replace('/','-')}"


# -------- Preupload: 回 {"files":[{"path","uploadMode"}]}
@router.post("/{repo_type}s/{repo_id:path}/preupload/{revision}")
async def preupload(repo_type: RepoType, repo_id: str, revision: str, request: Request):
    if not Repository.get_or_none(
        (Repository.full_id == repo_id) & (Repository.repo_type == repo_type.value)
    ):
        raise HTTPException(404, detail="Repo not found")

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if cfg.app.debug_log_payloads:
        print("==== Preupload Payload ====")
        print(body)

    files = body.get("files")
    if not isinstance(files, list):
        raise HTTPException(400, detail="Missing or invalid 'files'")

    out: List[Dict[str, Any]] = []
    threshold = int(cfg.app.lfs_threshold_bytes)

    for f in files:
        path = f.get("path") or f.get("path_in_repo")
        size = int(f.get("size") or 0)
        sha256 = f.get("sha256")

        upload_mode = "lfs" if size >= threshold else "regular"
        should_ignore = False

        # ✅ 若 client 提供 sha256，且 DB 已有相同記錄 → 可以忽略
        if sha256:
            existing = File.get_or_none(
                (File.repo_full_id == repo_id) & (File.path_in_repo == path)
            )
            if existing and existing.sha256 == sha256 and existing.size == size:
                should_ignore = True

        out.append({
            "path": path,
            "uploadMode": upload_mode,
            "shouldIgnore": should_ignore,
        })

        # 你若想保留「我們自己的 staging + presign」流程，可以在這裡生成 staging 記錄
        # （HF client 目前不會讀取我們自定欄位，但 commit 端我們可支援 base64 inline）
        if upload_mode == "regular":
            # 建一筆 staging（選擇性）
            staging_key = f"_staging/{repo_id}/{revision}/{uuid.uuid4().hex}/{path}"
            StagingUpload.create(
                repo_full_id=repo_id,
                repo_type=repo_type.value,
                revision=revision,
                path_in_repo=path,
                sha256=f.get("sha256", ""),
                size=size,
                upload_id="",
                storage_key=staging_key,
                lfs=False,
            )

    return {"files": out}


@router.get("/{repo_type}s/{repo_id:path}/revision/{revision}")
def get_revision(
    repo_type: RepoType, repo_id: str, revision: str, expand: Optional[str] = None
):
    lakefs_repo = _lakefs_repo_name(repo_type.value, repo_id)

    # 查 branch
    branch_url = f"{cfg.lakefs.internal_endpoint}/api/v1/repositories/{lakefs_repo}/branches/{revision}"
    headers = {
        "Authentication": f"Basic {cfg.lakefs.access_key}:{cfg.lakefs.secret_key}"
    }
    with httpx.Client(headers=headers) as client:
        resp = client.get(
            branch_url, auth=(cfg.lakefs.access_key, cfg.lakefs.secret_key)
        )
        if resp.status_code == 404:
            raise HTTPException(404, detail=f"Revision {revision} not found")
        resp.raise_for_status()
        branch_data = resp.json()

    commit_id = branch_data.get("commit_id")

    commit_info = None
    if commit_id:
        commit_url = f"{cfg.lakefs.internal_endpoint}/api/v1/repositories/{lakefs_repo}/commits/{commit_id}"
        with httpx.Client(headers=headers) as client:
            r2 = client.get(
                commit_url, auth=(cfg.lakefs.access_key, cfg.lakefs.secret_key)
            )
            if r2.status_code == 200:
                commit_info = r2.json()

    # 查 DB 裡的 repo metadata
    repo_row = Repository.get_or_none(
        (Repository.repo_type == repo_type) & (Repository.full_id == repo_id)
    )
    namespace = repo_row.namespace if repo_row else repo_id.split("/")[0]
    private = repo_row.private if repo_row else False
    created_at = (
        repo_row.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if repo_row else None
    )
    last_modified = commit_info.get("creation_date") if commit_info else None
    if last_modified is not None:
        last_modified = datetime.fromtimestamp(last_modified).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )

    return {
        "id": repo_id,  # ✅ 必填，避免 KeyError
        "author": namespace,
        "sha": commit_id,
        "lastModified": last_modified,
        "createdAt": created_at,
        "private": private,
        "downloads": 0,
        "likes": 0,
        "gated": False,
        "files": [],  # HF client 會再呼叫 /tree 或 /paths-info
        "type": "model",  # 或 dataset/space
        "revision": revision,
        "commit": {
            "oid": commit_id,
            "date": commit_info.get("creation_date") if commit_info else None,
        },
        "xetEnabled": False,
    }


# -------- Resolve (下載產生預簽名 GET)
@router.get("/{repo_type}s/{repo_id:path}/resolve/{revision}/{path:path}")
def presigned_download(repo_type: RepoType, repo_id: str, revision: str, path: str):
    key = f"{_lakefs_repo_name(repo_type.value, repo_id)}/{revision}/{path}"
    s3 = _s3_client()
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": cfg.s3.bucket, "Key": key},
            ExpiresIn=3600,
        )
    except Exception as e:
        raise HTTPException(404, detail=f"Object not found: {e}")
    return {"url": url}


# -------- Commit（支援小檔 inline base64；大檔未來接 LFS）
import json, base64, uuid, time
import lakefs_client
import io
from lakefs_client.client import LakeFSClient
from lakefs_client.models import CommitCreation
from fastapi import HTTPException, Request, Depends
from .auth import get_current_user
from ..config import cfg


def _lakefs_client():
    conf = lakefs_client.Configuration()
    conf.username = cfg.lakefs.access_key
    conf.password = cfg.lakefs.secret_key
    conf.host = f"{cfg.lakefs.internal_endpoint}/api/v1"
    return LakeFSClient(conf)


@router.post("/{repo_type}s/{repo_id:path}/commit/{revision}")
async def commit(
    repo_type: RepoType,
    repo_id: str,
    revision: str,
    request: Request,
    user=Depends(get_current_user),
):
    lakefs_repo = _lakefs_repo_name(repo_type.value, repo_id)
    client = _lakefs_client()

    # 讀取 NDJSON（application/x-ndjson）
    raw = await request.body()
    lines = raw.decode().splitlines()

    header = None
    files = []
    for line in lines:
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("key") == "header":
            header = obj.get("value") or {}
        elif obj.get("key") == "file":
            files.append(obj.get("value") or {})

    if header is None:
        raise HTTPException(400, detail="Missing commit header")

    for f in files:
        path = f.get("path")
        content_b64 = f.get("content")
        encoding = (f.get("encoding") or "").lower()
        storage_key = f.get("storage_key")

        # 先檢查 DB 有無記錄
        existing = File.get_or_none(
            (File.repo_full_id == repo_id) & (File.path_in_repo == path)
        )

        if content_b64 and encoding.startswith("base64"):
            data = base64.b64decode(content_b64)
            new_sha256 = hashlib.sha256(data).hexdigest()

            if existing and existing.sha256 == new_sha256 and existing.size == len(data):
                print(f"Skipping identical file {path}")
                continue  # 跳過，不 stage

            # 上傳並更新 DB
            client.objects.upload_object(
                repository=lakefs_repo, branch=revision, path=path, content=io.BytesIO(data)
            )
            File.insert(
                repo_full_id=repo_id,
                path_in_repo=path,
                size=len(data),
                sha256=new_sha256,
                lfs=False,
            ).on_conflict(
                conflict_target=(File.repo_full_id, File.path_in_repo),
                update={File.sha256: new_sha256, File.size: len(data), File.updated_at: datetime.utcnow()},
            ).execute()

        elif storage_key:
            # 大檔案：這裡 sha256 要從 client 提供
            new_sha256 = f.get("sha256")
            if not new_sha256:
                raise HTTPException(400, detail=f"Missing sha256 for large file {path}")

            if existing and existing.sha256 == new_sha256 and existing.size == size:
                print(f"Skipping identical LFS file {path}")
                continue

            client.objects.link_physical_object(
                repository=lakefs_repo, branch=revision, path=path, physical_address=storage_key
            )
            File.insert(
                repo_full_id=repo_id,
                path_in_repo=path,
                size=size,
                sha256=new_sha256,
                lfs=True,
            ).on_conflict(
                conflict_target=(File.repo_full_id, File.path_in_repo),
                update={File.sha256: new_sha256, File.size: size, File.updated_at: datetime.utcnow()},
            ).execute()
        else:
            raise HTTPException(400, detail=f"Unsupported file format for {path}")

    # Commit 至 LakeFS
    msg = header.get("summary") or "commit"
    desc = header.get("description") or ""
    commit = client.commits.commit(
        repository=lakefs_repo,
        branch=revision,
        commit_creation=CommitCreation(
            message=msg,
            metadata={"description": desc},
            committer=user.username,
        ),
    )

    # 建立一個可點的 commitUrl（指向 LakeFS Web UI）
    # e.g. https://file.hub.kohaku-lab.org/repositories/<lakefs_repo>/commits/<commit_id>
    commit_url = (
        f"{cfg.app.base_url}/{repo_id}/commit/{commit.id}"
    )
    print(commit_url)

    # ✅ 符合 huggingface_hub 期望的欄位
    resp = {
        "commitUrl": commit_url,
        "commitOid": commit.id,
        "pullRequestUrl": None,  # 目前不做 PR
        # 下面是兼容/除錯用途（非必需）
        "commit": {
            "oid": commit.id,
            "message": commit.message,
            "date": commit.creation_date,
            "author": {"name": commit.committer},
        },
    }
    return resp
