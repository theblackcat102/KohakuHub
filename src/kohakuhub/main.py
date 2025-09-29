"""Main FastAPI application for Kohaku Hub."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .api import basic, file, lfs, utils
from .config import cfg

app = FastAPI(
    title="Kohaku Hub",
    description="HuggingFace-compatible hub with LakeFS and S3 storage",
    version="0.0.1",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers with configured prefix
app.include_router(basic.router, prefix=cfg.app.api_base, tags=["repositories"])
app.include_router(file.router, prefix=cfg.app.api_base, tags=["files"])
app.include_router(lfs.router, prefix=cfg.app.api_base, tags=["lfs"])
app.include_router(utils.router, prefix=cfg.app.api_base, tags=["utils"])


# Public download endpoint (no /api prefix, matches HuggingFace URL pattern)
@app.get("/{repo_id:path}/resolve/{revision}/{path:path}")
@app.head("/{repo_id:path}/resolve/{revision}/{path:path}")
async def public_resolve(repo_id: str, revision: str, path: str, request: Request):
    """Public download endpoint without /api prefix.

    Matches HuggingFace Hub URL pattern for direct file downloads.
    Defaults to model repository type.

    Args:
        repo_id: Repository ID (e.g., "org/repo")
        revision: Branch name or commit hash
        path: File path within repository

    Returns:
        File download response or redirect
    """
    from .db import Repository
    from .api.file import resolve_file, RepoType

    namespace, name = repo_id.split("/")
    repo = Repository.get_or_none(name=name, namespace=namespace)
    if not repo:
        raise HTTPException(404, detail="Repository not found")

    return await resolve_file(
        repo_type=repo.repo_type,
        repo_id=repo_id,
        revision=revision,
        path=path,
        request=request,
    )


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Kohaku Hub",
        "version": "0.0.1",
        "description": "HuggingFace-compatible hub with LakeFS and S3 storage",
        "endpoints": {
            "api": cfg.app.api_base,
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
