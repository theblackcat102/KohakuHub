"""Run data access API endpoints

Unified API for accessing run data (scalars, media, tables, histograms).
Works in both local and remote modes with project-based organization.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from kohakuboard.api.utils.board_reader import BoardReader
from kohakuboard.auth import check_board_read_permission, get_optional_user
from kohakuboard.config import cfg
from kohakuboard.db import Board, User
from kohakuboard.logger import logger_api

router = APIRouter()


def get_run_path(project: str, run_id: str, current_user: User | None) -> Path:
    """Resolve run path based on mode

    Args:
        project: Project name
        run_id: Run ID
        current_user: Current user (optional)

    Returns:
        Path to run directory

    Raises:
        HTTPException: 401/403/404 if access denied or not found
    """
    base_dir = Path(cfg.app.board_data_dir)

    if cfg.app.mode == "local":
        if project != "local":
            raise HTTPException(404, detail={"error": "Project not found"})
        return base_dir / run_id

    else:  # remote mode
        if not current_user:
            raise HTTPException(401, detail={"error": "Authentication required"})

        # Get board from DB
        board = Board.get_or_none(
            (Board.owner == current_user)
            & (Board.project_name == project)
            & (Board.run_id == run_id)
        )
        if not board:
            raise HTTPException(404, detail={"error": "Run not found"})

        # Check permissions
        check_board_read_permission(board, current_user)

        return base_dir / board.storage_path


@router.get("/projects/{project}/runs/{run_id}/summary")
async def get_run_summary(
    project: str,
    run_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get run summary with metadata and available data

    Args:
        project: Project name
        run_id: Run ID
        current_user: Current user (optional)

    Returns:
        dict: Run summary with metadata, counts, available metrics/media/tables
    """
    logger_api.info(f"Fetching summary for {project}/{run_id}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    summary = reader.get_summary()

    # Add project context
    summary["project"] = project
    summary["run_id"] = run_id

    return summary


@router.get("/projects/{project}/runs/{run_id}/metadata")
async def get_run_metadata(
    project: str,
    run_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get run metadata"""
    logger_api.info(f"Fetching metadata for {project}/{run_id}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    metadata = reader.get_metadata()

    return metadata


@router.get("/projects/{project}/runs/{run_id}/scalars")
async def get_available_scalars(
    project: str,
    run_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get list of available scalar metrics"""
    logger_api.info(f"Fetching available scalars for {project}/{run_id}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    metrics = reader.get_available_metrics()

    return {"metrics": metrics}


@router.get("/projects/{project}/runs/{run_id}/scalars/{metric}")
async def get_scalar_data(
    project: str,
    run_id: str,
    metric: str,
    limit: int | None = Query(None, description="Maximum number of data points"),
    current_user: User | None = Depends(get_optional_user),
):
    """Get scalar data for a specific metric"""
    logger_api.info(f"Fetching scalar data for {project}/{run_id}/{metric}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    data = reader.get_scalar_data(metric, limit=limit)

    return {"metric": metric, "data": data}


@router.get("/projects/{project}/runs/{run_id}/media")
async def get_available_media(
    project: str,
    run_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get list of available media log names"""
    logger_api.info(f"Fetching available media for {project}/{run_id}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    media_names = reader.get_available_media_names()

    return {"media": media_names}


@router.get("/projects/{project}/runs/{run_id}/media/{name}")
async def get_media_data(
    project: str,
    run_id: str,
    name: str,
    limit: int | None = Query(None, description="Maximum number of entries"),
    current_user: User | None = Depends(get_optional_user),
):
    """Get media data for a specific log name"""
    logger_api.info(f"Fetching media data for {project}/{run_id}/{name}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    data = reader.get_media_data(name, limit=limit)

    return {"name": name, "data": data}


@router.get("/projects/{project}/runs/{run_id}/media/files/{filename}")
async def get_media_file(
    project: str,
    run_id: str,
    filename: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Serve media file (image/video/audio)"""
    logger_api.info(f"Serving media file: {project}/{run_id}/{filename}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    file_path = reader.get_media_file_path(filename)

    if not file_path:
        raise HTTPException(404, detail={"error": "Media file not found"})

    # Determine media type from extension
    suffix = file_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
    }

    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )


@router.get("/projects/{project}/runs/{run_id}/tables")
async def get_available_tables(
    project: str,
    run_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get list of available table log names"""
    logger_api.info(f"Fetching available tables for {project}/{run_id}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    table_names = reader.get_available_table_names()

    return {"tables": table_names}


@router.get("/projects/{project}/runs/{run_id}/tables/{name}")
async def get_table_data(
    project: str,
    run_id: str,
    name: str,
    limit: int | None = Query(None, description="Maximum number of entries"),
    current_user: User | None = Depends(get_optional_user),
):
    """Get table data for a specific log name"""
    logger_api.info(f"Fetching table data for {project}/{run_id}/{name}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    data = reader.get_table_data(name, limit=limit)

    return {"name": name, "data": data}


@router.get("/projects/{project}/runs/{run_id}/histograms")
async def get_available_histograms(
    project: str,
    run_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get list of available histogram log names"""
    logger_api.info(f"Fetching available histograms for {project}/{run_id}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    histogram_names = reader.get_available_histogram_names()

    return {"histograms": histogram_names}


@router.get("/projects/{project}/runs/{run_id}/histograms/{name}")
async def get_histogram_data(
    project: str,
    run_id: str,
    name: str,
    limit: int | None = Query(None, description="Maximum number of entries"),
    current_user: User | None = Depends(get_optional_user),
):
    """Get histogram data for a specific log name"""
    logger_api.info(f"Fetching histogram data for {project}/{run_id}/{name}")

    run_path = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    data = reader.get_histogram_data(name, limit=limit)

    return {"name": name, "data": data}
