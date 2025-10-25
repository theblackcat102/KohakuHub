"""Main FastAPI application for KohakuBoard"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kohakuboard.api.routers import experiments, mock
from kohakuboard.config import cfg
from kohakuboard.logger import logger_api

app = FastAPI(
    title="KohakuBoard API",
    description="ML Experiment Tracking API",
    version="0.1.0",
    docs_url=f"{cfg.app.api_base}/docs",
    openapi_url=f"{cfg.app.api_base}/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(experiments.router, prefix=cfg.app.api_base, tags=["experiments"])
app.include_router(mock.router, prefix=cfg.app.api_base, tags=["mock"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "KohakuBoard API",
        "version": "0.1.0",
        "docs": f"{cfg.app.api_base}/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    logger_api.info(f"Starting KohakuBoard API on {cfg.app.host}:{cfg.app.port}")
    uvicorn.run(
        "kohakuboard.main:app", host=cfg.app.host, port=cfg.app.port, reload=True
    )
