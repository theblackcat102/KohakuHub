from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, Literal, Any
from ..db import Repository, init_db
from .auth import get_current_user
from ..config import cfg
import httpx

router = APIRouter()
init_db()

RepoType = Literal["model", "dataset", "space"]


def _lakefs_repo_name(repo_type: str, repo_id: str) -> str:
    return f"{cfg.lakefs.repo_namespace}-{repo_type}-{repo_id.replace('/','-')}"


class CreateRepoPayload(BaseModel):
    type: RepoType = "model"
    name: str
    organization: Optional[str] = None
    private: bool = False
    sdk: Optional[str] = None


@router.post("/repos/create")
def create_repo(payload: CreateRepoPayload, user=Depends(get_current_user)):
    namespace = payload.organization or user.username
    full_id = f"{namespace}/{payload.name}"
    lakefs_repo = _lakefs_repo_name(payload.type, full_id)

    # 建立 LakeFS repo
    body = {
        "name": lakefs_repo,
        "storage_namespace": f"s3://{cfg.s3.bucket}/{lakefs_repo}",
        "default_branch": "main",
        "read_only": False,
        "sample_data": False,
    }
    headers = {
        "Authorization": f"Basic {cfg.lakefs.access_key}:{cfg.lakefs.secret_key}"
    }
    with httpx.Client(headers=headers) as client:
        r = client.post(
            f"{cfg.lakefs.internal_endpoint}/api/v1/repositories",
            json=body,
            auth=(cfg.lakefs.access_key, cfg.lakefs.secret_key),
        )
        if r.status_code not in (200, 201):
            print(r.json())
            raise HTTPException(
                r.status_code, detail=f"LakeFS repo create failed: {r.text}"
            )

    # DB 裡也建一筆（用來支援 HF client 的 list）
    Repository.get_or_create(
        repo_type=payload.type,
        namespace=namespace,
        name=payload.name,
        full_id=full_id,
        defaults={"private": payload.private},
    )

    return {"url": f"{cfg.app.base_url}/{payload.type}s/{full_id}", "repo_id": full_id}


# --- List repo tree (對接 LakeFS) ---
@router.get("/{repo_type}s/{repo_id:path}/tree/{revision}{path:path}")
def list_repo_tree(
    repo_type: RepoType,
    repo_id: str,
    revision: str = "main",
    path: str = "",
    recursive: bool = True,
    expand: bool = False,
):
    lakefs_repo = _lakefs_repo_name(repo_type, repo_id)
    url = f"{cfg.lakefs.internal_endpoint}/api/v1/repositories/{lakefs_repo}/refs/{revision}/objects/ls"

    # 規定一定要傳 path 參數
    prefix = path.lstrip("/") if path and path != "/" else ""
    params = {"path": prefix}
    if recursive:
        params["recursive"] = "true"
    else:
        params["delimiter"] = "/"

    with httpx.Client() as client:
        r = client.get(
            url,
            params=params,
            auth=(cfg.lakefs.access_key, cfg.lakefs.secret_key),
        )
        print(r.text)
        if r.status_code == 404:
            # 若 prefix 不存在（空目錄），回空 tree 而不要拋錯
            return {"sha": None, "truncated": False, "tree": [], "commit": {"oid": None, "date": None}}
        r.raise_for_status()
        data = r.json()

    tree = []
    for obj in data.get("results", []):
        if obj.get("path_type") == "object":
            tree.append({
                "path": obj["path"],
                "type": "blob",
                "size": obj.get("size_bytes"),
                "oid": obj.get("checksum"),         # ✅ 用 checksum 當 OID
                "lfs": False,
                "lastCommit": {                     # ✅ HF Hub API 會期待這欄位
                    "id": obj.get("checksum"),
                    "date": obj.get("mtime"),
                },
            })
        elif obj.get("path_type") == "common_prefix":
            tree.append({
                "path": obj["path"],
                "type": "tree",
            })

    return {
        "sha": None,
        "truncated": False,
        "tree": tree,
        "commit": {"oid": None, "date": None},
    }


@router.get("/models")
@router.get("/datasets")
@router.get("/spaces")
def list_repos(
    author: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    request: Request = None,
):
    path = request.url.path
    if "models" in path:
        rt = "model"
    elif "datasets" in path:
        rt = "dataset"
    elif "spaces" in path:
        rt = "space"
    else:
        raise HTTPException(404)

    q = Repository.select().where(Repository.repo_type == rt)
    if author:
        q = q.where(Repository.namespace == author)
    rows = q.limit(limit)

    return [
        {
            "id": r.full_id,
            "author": r.namespace,
            "private": r.private,
            "sha": None,
            "lastModified": None,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
            "downloads": 0,
            "likes": 0,
            "gated": False,
            "files": [],
        }
        for r in rows
    ]
