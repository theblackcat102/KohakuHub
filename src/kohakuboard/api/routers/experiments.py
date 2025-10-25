"""Experiments API endpoints"""

import random

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from kohakuboard.api.utils.mock_data import (
    generate_experiment,
    generate_metrics_data,
    generate_sparse_metrics_data,
    generate_histogram_data,
    generate_table_data,
)
from kohakuboard.config import cfg
from kohakuboard.logger import logger_api

router = APIRouter()

# Mock experiment storage with large datasets for testing WebGL performance
MOCK_EXPERIMENTS = {
    "exp-001": generate_experiment(
        "exp-001", "ResNet50 Training (1K steps)", steps=1000, status="completed"
    ),
    "exp-002": generate_experiment(
        "exp-002", "BERT Fine-tuning (10K steps)", steps=10000, status="running"
    ),
    "exp-003": generate_experiment(
        "exp-003", "ViT Pretraining (50K steps)", steps=50000, status="completed"
    ),
    "exp-004": generate_experiment(
        "exp-004", "GPT-2 Training (100K steps)", steps=100000, status="completed"
    ),
    "exp-005": generate_experiment(
        "exp-005", "Stable Diffusion (25K steps)", steps=25000, status="stopped"
    ),
}


class MetricsQuery(BaseModel):
    """Query parameters for metrics"""

    metric_names: Optional[List[str]] = None
    start_step: Optional[int] = None
    end_step: Optional[int] = None


@router.get("/experiments")
async def list_experiments():
    """List all experiments"""
    logger_api.info("Fetching experiments list")
    return list(MOCK_EXPERIMENTS.values())


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get experiment details"""
    logger_api.info(f"Fetching experiment: {experiment_id}")

    if experiment_id not in MOCK_EXPERIMENTS:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return MOCK_EXPERIMENTS[experiment_id]


@router.get("/experiments/{experiment_id}/metrics")
async def get_metrics(
    experiment_id: str,
    metric_names: Optional[str] = Query(
        None, description="Comma-separated metric names"
    ),
    start_step: Optional[int] = Query(None, description="Start step"),
    end_step: Optional[int] = Query(None, description="End step"),
    steps: int = Query(None, description="Number of steps", le=cfg.mock.max_steps),
):
    """Get metrics data for an experiment"""
    logger_api.info(f"Fetching metrics for experiment: {experiment_id}")

    if experiment_id not in MOCK_EXPERIMENTS:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if steps is None:
        steps = MOCK_EXPERIMENTS[experiment_id]["total_steps"]

    # Parse metric names
    metrics = None
    if metric_names:
        metrics = [m.strip() for m in metric_names.split(",")]

    # Generate metrics data
    metrics_data = generate_metrics_data(steps=steps, metrics=metrics)

    # Filter by step range if provided
    if start_step is not None or end_step is not None:
        for metric in metrics_data:
            start = start_step or 0
            end = end_step or len(metric["x"])
            metric["x"] = metric["x"][start:end]
            metric["y"] = metric["y"][start:end]

    return {"experiment_id": experiment_id, "metrics": metrics_data}


@router.get("/experiments/{experiment_id}/summary")
async def get_experiment_summary(experiment_id: str):
    """Get experiment summary with available data"""
    logger_api.info(f"Fetching summary for experiment: {experiment_id}")

    if experiment_id not in MOCK_EXPERIMENTS:
        raise HTTPException(status_code=404, detail="Experiment not found")

    sample = generate_sparse_metrics_data(total_events=100)

    return {
        "experiment_id": experiment_id,
        "experiment_info": MOCK_EXPERIMENTS[experiment_id],
        "total_steps": MOCK_EXPERIMENTS[experiment_id]["total_steps"],
        "available_data": {
            "scalars": [k for k in sample.keys() if k != "time"],
            "media": ["generated_images", "model_predictions", "attention_maps"],
            "tables": ["validation_results", "layer_stats", "confusion_matrix"],
            "histograms": ["gradients", "weights", "activations"],
        },
    }


@router.get("/experiments/{experiment_id}/scalars/{metric_name}")
async def get_scalar_metric(experiment_id: str, metric_name: str):
    """Get scalar metric as step-value pairs"""
    logger_api.info(f"Fetching scalar '{metric_name}' for experiment: {experiment_id}")

    if experiment_id not in MOCK_EXPERIMENTS:
        raise HTTPException(status_code=404, detail="Experiment not found")

    total_steps = MOCK_EXPERIMENTS[experiment_id]["total_steps"]
    full_data = generate_sparse_metrics_data(total_events=total_steps)

    if metric_name not in full_data:
        raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")

    # Return as step-value pairs (filter out None values)
    data = []
    for i, value in enumerate(full_data[metric_name]):
        if value is not None:
            data.append({"step": i, "value": value})

    return {"experiment_id": experiment_id, "metric_name": metric_name, "data": data}


@router.get("/experiments/{experiment_id}/media/{media_name}")
async def get_media_log(experiment_id: str, media_name: str):
    """Get media log entries"""
    logger_api.info(f"Fetching media '{media_name}' for experiment: {experiment_id}")

    if experiment_id not in MOCK_EXPERIMENTS:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # Mock media data with real placeholder URLs
    media_entries = []
    total_steps = MOCK_EXPERIMENTS[experiment_id]["total_steps"]
    log_every = 1000  # Log media every 1000 steps

    for step in range(0, total_steps, log_every):
        media_entries.append(
            {
                "step": step,
                "type": "image",
                "url": f"https://picsum.photos/seed/{experiment_id}-{media_name}-{step}/512/512",
                "caption": f"{media_name} at step {step}",
            }
        )

    return {
        "experiment_id": experiment_id,
        "media_name": media_name,
        "data": media_entries,
    }


@router.get("/experiments/{experiment_id}/tables/{table_name}")
async def get_table_log(experiment_id: str, table_name: str):
    """Get table log entries"""
    logger_api.info(f"Fetching table '{table_name}' for experiment: {experiment_id}")

    if experiment_id not in MOCK_EXPERIMENTS:
        raise HTTPException(status_code=404, detail="Experiment not found")

    total_steps = MOCK_EXPERIMENTS[experiment_id]["total_steps"]
    log_every = 5000

    table_entries = []
    for step in range(0, total_steps, log_every):
        step_num = step // log_every
        table_entries.append(
            {
                "step": step,
                "columns": [
                    "Sample",
                    "Image",
                    "Precision",
                    "Recall",
                    "F1-Score",
                    "Support",
                ],
                "column_types": [
                    "text",
                    "image",
                    "number",
                    "number",
                    "number",
                    "number",
                ],
                "rows": [
                    [
                        "Cat",
                        f"https://picsum.photos/seed/{experiment_id}-cat-{step}/64/64",
                        0.85 + random.random() * 0.1,
                        0.80 + random.random() * 0.1,
                        0.82 + random.random() * 0.1,
                        120,
                    ],
                    [
                        "Dog",
                        f"https://picsum.photos/seed/{experiment_id}-dog-{step}/64/64",
                        0.88 + random.random() * 0.1,
                        0.85 + random.random() * 0.1,
                        0.86 + random.random() * 0.1,
                        150,
                    ],
                    [
                        "Bird",
                        f"https://picsum.photos/seed/{experiment_id}-bird-{step}/64/64",
                        0.75 + random.random() * 0.1,
                        0.70 + random.random() * 0.1,
                        0.72 + random.random() * 0.1,
                        80,
                    ],
                ],
            }
        )

    return {
        "experiment_id": experiment_id,
        "table_name": table_name,
        "data": table_entries,
    }


@router.get("/experiments/{experiment_id}/histograms/{histogram_name}")
async def get_histogram_log(experiment_id: str, histogram_name: str):
    """Get histogram log entries"""
    logger_api.info(
        f"Fetching histogram '{histogram_name}' for experiment: {experiment_id}"
    )

    if experiment_id not in MOCK_EXPERIMENTS:
        raise HTTPException(status_code=404, detail="Experiment not found")

    total_steps = MOCK_EXPERIMENTS[experiment_id]["total_steps"]
    log_every = 2000

    histogram_entries = []
    for step in range(0, total_steps, log_every):
        histogram_entries.append(
            {
                "step": step,
                "bins": 50,
                "values": [
                    random.gauss(0, 1 - step / total_steps) for _ in range(10000)
                ],
            }
        )

    return {
        "experiment_id": experiment_id,
        "histogram_name": histogram_name,
        "data": histogram_entries,
    }


@router.get("/experiments/{experiment_id}/histograms/{histogram_name}")
async def get_histogram(
    experiment_id: str,
    histogram_name: str,
    num_values: int = Query(10000, description="Number of data points", le=1000000),
    distribution: str = Query(
        "normal", description="Distribution type (normal, uniform, exponential)"
    ),
):
    """Get histogram data"""
    logger_api.info(
        f"Fetching histogram '{histogram_name}' for experiment: {experiment_id}"
    )

    if experiment_id not in MOCK_EXPERIMENTS:
        raise HTTPException(status_code=404, detail="Experiment not found")

    histogram_data = generate_histogram_data(
        num_values=num_values, distribution=distribution
    )

    return histogram_data


@router.get("/experiments/{experiment_id}/tables/{table_name}")
async def get_table(
    experiment_id: str,
    table_name: str,
    num_rows: int = Query(100, description="Number of rows", le=10000),
    num_cols: int = Query(6, description="Number of columns", le=50),
):
    """Get table data"""
    logger_api.info(f"Fetching table '{table_name}' for experiment: {experiment_id}")

    if experiment_id not in MOCK_EXPERIMENTS:
        raise HTTPException(status_code=404, detail="Experiment not found")

    table_data = generate_table_data(num_rows=num_rows, num_cols=num_cols)

    return table_data
