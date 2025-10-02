"""Main FastAPI application for Kohaku Hub."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .api import basic, file, lfs, utils
from .auth import router as auth_router
from .org import router as org_router
from .config import cfg
from .db import Repository
from .api.file import resolve_file
from .api.s3_utils import init_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_storage()
    yield


app = FastAPI(
    title="Kohaku Hub",
    description="HuggingFace-compatible hub with LakeFS and S3 storage",
    version="0.0.1",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=cfg.app.api_base)
app.include_router(basic.router, prefix=cfg.app.api_base, tags=["repositories"])
app.include_router(file.router, prefix=cfg.app.api_base, tags=["files"])
app.include_router(lfs.router, tags=["lfs"])
app.include_router(utils.router, prefix=cfg.app.api_base, tags=["utils"])
app.include_router(org_router, prefix="/org", tags=["organizations"])


@app.get("/{namespace}/{name}/resolve/{revision}/{path:path}")
@app.head("/{namespace}/{name}/resolve/{revision}/{path:path}")
async def public_resolve(
    namespace: str, name: str, revision: str, path: str, request: Request
):
    """Public download endpoint without /api prefix."""

    repo = Repository.get_or_none(name=name, namespace=namespace)
    if not repo:
        raise HTTPException(404, detail={"error": "Repository not found"})

    return await resolve_file(
        repo_type=repo.repo_type,
        namespace=namespace,
        name=name,
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
            "auth": f"{cfg.app.api_base}/auth",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
