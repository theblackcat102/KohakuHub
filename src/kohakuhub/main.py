from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import cfg
from .api import basic, file as file_api, utils
from .api.file import presigned_download

app = FastAPI(title="HF-Compatible Hub (LakeFS + MinIO)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 用 config 的 api_base 掛載
app.include_router(basic.router, prefix=cfg.app.api_base)
app.include_router(file_api.router, prefix=cfg.app.api_base)
app.include_router(utils.router, prefix=cfg.app.api_base)


# 兼容 huggingface 樣式的公開下載路徑（預設 model）
@app.get("/{repo_id:path}/resolve/{revision}/{path:path}")
def public_resolve(repo_id: str, revision: str, path: str):
    return presigned_download("model", repo_id, revision, path)
