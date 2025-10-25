"""Experiment runs API with better data structure"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from kohakuboard.api.utils.mock_data import generate_sparse_metrics_data
from kohakuboard.logger import logger_api

router = APIRouter()

# Mock runs data
MOCK_RUNS = {
    "run-001": {
        "id": "run-001",
        "name": "ResNet50 Training",
        "status": "running",
        "created_at": "2025-01-15T10:00:00Z",
    }
}


@router.get("/runs/{run_id}/summary")
async def get_run_summary(run_id: str):
    """Get run summary with all available metrics"""
    logger_api.info(f"Fetching summary for run: {run_id}")

    if run_id not in MOCK_RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    # Generate sample data to get metric names
    sample_data = generate_sparse_metrics_data(total_events=100)

    return {
        "run_id": run_id,
        "run_info": MOCK_RUNS[run_id],
        "total_events": 100000,
        "available_metrics": {
            "scalars": [k for k in sample_data.keys() if k != "time"],
            "images": ["generated_samples", "confusion_matrix"],
            "tables": ["validation_results", "layer_stats"],
        },
    }


@router.get("/runs/{run_id}/scalars/{metric_name}")
async def get_scalar_values(
    run_id: str,
    metric_name: str,
    start_event: Optional[int] = Query(None),
    end_event: Optional[int] = Query(None),
):
    """Get scalar values for a specific metric"""
    logger_api.info(f"Fetching scalar '{metric_name}' for run: {run_id}")

    if run_id not in MOCK_RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    # Generate full dataset
    full_data = generate_sparse_metrics_data(total_events=100000)

    if metric_name not in full_data:
        raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")

    start = start_event or 0
    end = end_event or len(full_data["time"])

    return {
        "run_id": run_id,
        "metric_name": metric_name,
        "time": full_data["time"][start:end],
        "values": full_data[metric_name][start:end],
    }


@router.get("/runs/{run_id}/images/{image_name}")
async def get_image_log(run_id: str, image_name: str, limit: int = Query(100, le=1000)):
    """Get image log entries"""
    logger_api.info(f"Fetching images '{image_name}' for run: {run_id}")

    if run_id not in MOCK_RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    # Mock image data
    images = []
    for i in range(min(limit, 10)):
        images.append(
            {
                "step": i * 1000,
                "url": f"https://via.placeholder.com/256x256?text=Step+{i * 1000}",
                "caption": f"Generated sample at step {i * 1000}",
            }
        )

    return {"run_id": run_id, "image_name": image_name, "images": images}


@router.get("/runs/{run_id}/tables/{table_name}")
async def get_table_log(run_id: str, table_name: str):
    """Get table log with optional image columns"""
    logger_api.info(f"Fetching table '{table_name}' for run: {run_id}")

    if run_id not in MOCK_RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    # Mock table with images
    columns = ["ID", "Name", "Score", "Image", "Status"]
    column_types = ["number", "text", "number", "image", "text"]
    rows = []

    for i in range(20):
        rows.append(
            [
                i + 1,
                f"Sample_{i + 1}",
                round(0.5 + (i / 20) * 0.5, 3),
                f"https://via.placeholder.com/64x64?text={i + 1}",
                "Pass" if i % 3 == 0 else "Fail",
            ]
        )

    return {
        "run_id": run_id,
        "table_name": table_name,
        "columns": columns,
        "column_types": column_types,
        "rows": rows,
    }
