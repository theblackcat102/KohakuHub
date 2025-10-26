"""Experiments API endpoints - serves real board data"""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from kohakuboard.api.utils.board_reader import BoardReader, list_boards
from kohakuboard.config import cfg
from kohakuboard.logger import logger_api

router = APIRouter()


class MetricsQuery(BaseModel):
    """Query parameters for metrics"""

    metric_names: Optional[List[str]] = None
    start_step: Optional[int] = None
    end_step: Optional[int] = None


@router.get("/experiments")
async def list_experiments():
    """List all experiments (boards)"""
    logger_api.info("Fetching experiments list from boards")

    try:
        boards = list_boards(Path(cfg.app.board_data_dir))

        # Convert board format to experiment format
        experiments = []
        for board in boards:
            experiments.append(
                {
                    "id": board["board_id"],
                    "name": board["name"],
                    "description": f"Config: {board.get('config', {})}",
                    "status": "completed",  # For now, all boards are considered completed
                    "total_steps": 0,  # Will be filled from actual data if needed
                    "duration": "N/A",
                    "created_at": board.get("created_at", ""),
                }
            )

        logger_api.info(f"Found {len(experiments)} experiments")
        return experiments
    except Exception as e:
        logger_api.error(f"Failed to list experiments: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list experiments: {str(e)}"
        )


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get experiment details"""
    logger_api.info(f"Fetching experiment: {experiment_id}")

    try:
        board_dir = Path(cfg.app.board_data_dir) / experiment_id
        reader = BoardReader(board_dir)
        metadata = reader.get_metadata()

        return {
            "id": experiment_id,
            "name": metadata.get("name", experiment_id),
            "description": f"Config: {metadata.get('config', {})}",
            "status": "completed",
            "total_steps": 0,  # TODO: Calculate from data
            "duration": "N/A",
            "created_at": metadata.get("created_at", ""),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except Exception as e:
        logger_api.error(f"Failed to get experiment {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}/summary")
async def get_experiment_summary(experiment_id: str):
    """Get experiment summary with available data"""
    logger_api.info(f"Fetching summary for experiment: {experiment_id}")

    try:
        board_dir = Path(cfg.app.board_data_dir) / experiment_id
        reader = BoardReader(board_dir)
        summary = reader.get_summary()

        metadata = summary["metadata"]

        return {
            "experiment_id": experiment_id,
            "experiment_info": {
                "id": experiment_id,
                "name": metadata.get("name", experiment_id),
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
                "histograms": [],  # Not yet implemented in board storage
            },
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except Exception as e:
        logger_api.error(f"Failed to get summary for {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}/scalars/{metric_name}")
async def get_scalar_metric(experiment_id: str, metric_name: str):
    """Get scalar metric as step-value pairs"""
    logger_api.info(f"Fetching scalar '{metric_name}' for experiment: {experiment_id}")

    try:
        board_dir = Path(cfg.app.board_data_dir) / experiment_id
        reader = BoardReader(board_dir)
        data = reader.get_scalar_data(metric_name)

        return {
            "experiment_id": experiment_id,
            "metric_name": metric_name,
            "data": data,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404, detail=f"Metric '{metric_name}' not found"
            )
        logger_api.error(f"Failed to get scalar {metric_name} for {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}/media/{media_name}")
async def get_media_log(experiment_id: str, media_name: str):
    """Get media log entries"""
    logger_api.info(f"Fetching media '{media_name}' for experiment: {experiment_id}")

    try:
        board_dir = Path(cfg.app.board_data_dir) / experiment_id
        reader = BoardReader(board_dir)
        data = reader.get_media_data(media_name)

        # Transform to expected format
        media_entries = []
        for entry in data:
            media_entries.append(
                {
                    "name": entry.get("media_id", ""),
                    "step": entry.get("step", 0),
                    "type": entry.get("type", "image"),
                    "url": f"/api/boards/{experiment_id}/media/files/{entry.get('filename', '')}",
                    "caption": entry.get("caption", ""),
                    "width": entry.get("width"),
                    "height": entry.get("height"),
                }
            )

        return {
            "experiment_id": experiment_id,
            "media_name": media_name,
            "data": media_entries,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except Exception as e:
        logger_api.error(f"Failed to get media {media_name} for {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}/tables/{table_name}")
async def get_table_log(experiment_id: str, table_name: str):
    """Get table log entries"""
    logger_api.info(f"Fetching table '{table_name}' for experiment: {experiment_id}")

    try:
        board_dir = Path(cfg.app.board_data_dir) / experiment_id
        reader = BoardReader(board_dir)
        data = reader.get_table_data(table_name)

        # Transform to expected format (data is already parsed)
        return {
            "experiment_id": experiment_id,
            "table_name": table_name,
            "data": data,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except Exception as e:
        logger_api.error(f"Failed to get table {table_name} for {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}/histograms/{histogram_name}")
async def get_histogram_log(experiment_id: str, histogram_name: str):
    """Get histogram log entries"""
    logger_api.info(
        f"Fetching histogram '{histogram_name}' for experiment: {experiment_id}"
    )

    # Histograms not yet implemented in board storage
    raise HTTPException(status_code=501, detail="Histograms not yet implemented")
