"""Run data access API endpoints

Unified API for accessing run data (scalars, media, tables, histograms).
Works in both local and remote modes with project-based organization.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from kohakuboard.api.utils.board_reader import BoardReader
from kohakuboard.auth import get_optional_user
from kohakuboard.auth.permissions import check_board_read_permission
from kohakuboard.config import cfg
from kohakuboard.db import Board, User
from kohakuboard.logger import logger_api

router = APIRouter()


def get_run_path(
    project: str, run_id: str, current_user: User | None
) -> tuple[Path, Board | None]:
    """Resolve run path based on mode.

    Args:
        project: Project name
        run_id: Run ID
        current_user: Current user (optional)

    Returns:
        Tuple of (run_path, board) - board is None in local mode

    Raises:
        HTTPException: 401/403/404 if access denied or not found
    """
    base_dir = Path(cfg.app.board_data_dir)

    if cfg.app.mode == "local":
        if project != "local":
            raise HTTPException(404, detail={"error": "Project not found"})
        return base_dir / run_id, None

    else:  # remote mode
        # Get board from DB (don't filter by owner - check permissions instead)
        board = Board.get_or_none(
            (Board.project_name == project) & (Board.run_id == run_id)
        )
        if not board:
            raise HTTPException(404, detail={"error": "Run not found"})

        # Check read permission (works for owner, org members, and public boards)
        check_board_read_permission(board, current_user)

        return base_dir / board.storage_path, board


@router.get("/projects/{project}/runs/{run_id}/status")
async def get_run_status(
    project: str,
    run_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get run status with latest update timestamp

    Returns minimal info for polling (last update time, row counts)
    """
    run_path, _ = get_run_path(project, run_id, current_user)

    # Check metadata for creation time
    metadata_file = run_path / "metadata.json"
    if metadata_file.exists():
        import json

        with open(metadata_file, "r") as f:
            metadata = json.load(f)
    else:
        metadata = {}

    # Get row count and last update from storage
    metrics_count = 0
    last_updated = metadata.get("created_at")

    try:
        reader = BoardReader(run_path)

        # Check if hybrid backend (has get_latest_step method)
        if hasattr(reader, "get_latest_step"):
            # Hybrid backend - get latest from steps table
            latest_step_info = reader.get_latest_step()
            if latest_step_info:
                metrics_count = latest_step_info.get("step", 0) + 1  # step count
                # Convert timestamp ms to ISO string
                ts_ms = latest_step_info.get("timestamp")
                if ts_ms:
                    from datetime import datetime, timezone

                    last_updated = datetime.fromtimestamp(
                        ts_ms / 1000, tz=timezone.utc
                    ).isoformat()
        else:
            # DuckDB backend - count rows
            conn = reader._get_metrics_connection()
            try:
                metrics_count = conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[
                    0
                ]
            finally:
                conn.close()

    except Exception as e:
        logger_api.warning(f"Failed to get status: {e}")

    return {
        "run_id": run_id,
        "project": project,
        "metrics_count": metrics_count,
        "last_updated": last_updated,
    }


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
        Same format as experiments API for compatibility
    """
    logger_api.info(f"Fetching summary for {project}/{run_id}")

    run_path, _ = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    summary = reader.get_summary()

    # Return in same format as experiments API for frontend compatibility
    metadata = summary["metadata"]

    return {
        "experiment_id": run_id,  # For compatibility with ConfigurableChartCard
        "project": project,
        "run_id": run_id,
        "experiment_info": {
            "id": run_id,
            "name": metadata.get("name", run_id),
            "description": f"Config: {metadata.get('config', {})}",
            "status": "completed",
            "total_steps": summary["metrics_count"],
            "duration": "N/A",
            "created_at": metadata.get("created_at", ""),
        },
        "total_steps": summary["metrics_count"],
        "available_data": {
            "scalars": summary["available_metrics"],
            "media": summary["available_media"],
            "tables": summary["available_tables"],
            "histograms": summary["available_histograms"],
        },
    }


@router.get("/projects/{project}/runs/{run_id}/metadata")
async def get_run_metadata(
    project: str,
    run_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get run metadata"""
    logger_api.info(f"Fetching metadata for {project}/{run_id}")

    run_path, _ = get_run_path(project, run_id, current_user)
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

    run_path, _ = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    metrics = reader.get_available_metrics()

    return {"metrics": metrics}


@router.get("/projects/{project}/runs/{run_id}/scalars/{metric:path}")
async def get_scalar_data(
    project: str,
    run_id: str,
    metric: str,
    limit: int | None = Query(None, description="Maximum number of data points"),
    current_user: User | None = Depends(get_optional_user),
):
    """Get scalar data for a specific metric

    Note: metric can contain slashes (e.g., "train/loss")
    FastAPI path parameter automatically URL-decodes it
    """
    logger_api.info(f"Fetching scalar data for {project}/{run_id}/{metric}")

    run_path, _ = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    data = reader.get_scalar_data(metric, limit=limit)

    # data is now columnar format: {steps: [], global_steps: [], timestamps: [], values: []}
    return {"metric": metric, **data}


@router.get("/projects/{project}/runs/{run_id}/media")
async def get_available_media(
    project: str,
    run_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get list of available media log names"""
    logger_api.info(f"Fetching available media for {project}/{run_id}")

    run_path, _ = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    media_names = reader.get_available_media_names()

    return {"media": media_names}


@router.get("/projects/{project}/runs/{run_id}/media/{name:path}")
async def get_media_data(
    project: str,
    run_id: str,
    name: str,
    limit: int | None = Query(None, description="Maximum number of entries"),
    current_user: User | None = Depends(get_optional_user),
):
    """Get media data for a specific log name"""
    logger_api.info(f"Fetching media data for {project}/{run_id}/{name}")

    run_path, _ = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    data = reader.get_media_data(name, limit=limit)

    # Transform to same format as experiments API
    media_entries = []
    for entry in data:
        media_entries.append(
            {
                "name": entry.get("media_id", ""),
                "step": entry.get("step", 0),
                "type": entry.get("type", "image"),
                "url": f"/api/projects/{project}/runs/{run_id}/media/files/{entry.get('filename', '')}",
                "caption": entry.get("caption", ""),
                "width": entry.get("width"),
                "height": entry.get("height"),
            }
        )

    return {"experiment_id": run_id, "media_name": name, "data": media_entries}


@router.get("/projects/{project}/runs/{run_id}/media/files/{filename}")
async def get_media_file(
    project: str,
    run_id: str,
    filename: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Serve media file (image/video/audio)"""
    logger_api.info(f"Serving media file: {project}/{run_id}/{filename}")

    run_path, _ = get_run_path(project, run_id, current_user)
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

    run_path, _ = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    table_names = reader.get_available_table_names()

    return {"tables": table_names}


@router.get("/projects/{project}/runs/{run_id}/tables/{name:path}")
async def get_table_data(
    project: str,
    run_id: str,
    name: str,
    limit: int | None = Query(None, description="Maximum number of entries"),
    current_user: User | None = Depends(get_optional_user),
):
    """Get table data for a specific log name"""
    logger_api.info(f"Fetching table data for {project}/{run_id}/{name}")

    run_path, _ = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    data = reader.get_table_data(name, limit=limit)

    return {"experiment_id": run_id, "table_name": name, "data": data}


@router.get("/projects/{project}/runs/{run_id}/histograms")
async def get_available_histograms(
    project: str,
    run_id: str,
    current_user: User | None = Depends(get_optional_user),
):
    """Get list of available histogram log names"""
    logger_api.info(f"Fetching available histograms for {project}/{run_id}")

    run_path, _ = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    histogram_names = reader.get_available_histogram_names()

    return {"histograms": histogram_names}


@router.get("/projects/{project}/runs/{run_id}/histograms/{name:path}")
async def get_histogram_data(
    project: str,
    run_id: str,
    name: str,
    limit: int | None = Query(None, description="Maximum number of entries"),
    current_user: User | None = Depends(get_optional_user),
):
    """Get histogram data for a specific log name"""
    logger_api.info(f"Fetching histogram data for {project}/{run_id}/{name}")

    run_path, _ = get_run_path(project, run_id, current_user)
    reader = BoardReader(run_path)
    data = reader.get_histogram_data(name, limit=limit)

    return {"experiment_id": run_id, "histogram_name": name, "data": data}
