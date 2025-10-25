"""Mock data generation API endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from kohakuboard.api.utils.mock_data import (
    generate_metrics_data,
    generate_histogram_data,
    generate_scatter_data,
    generate_table_data,
)
from kohakuboard.config import cfg
from kohakuboard.logger import logger_mock

router = APIRouter()


class MockMetricsConfig(BaseModel):
    """Configuration for mock metrics generation"""

    steps: int = Field(
        default=100000, le=cfg.mock.max_steps, description="Number of steps"
    )
    metrics: Optional[List[str]] = Field(default=None, description="Metric names")


class MockHistogramConfig(BaseModel):
    """Configuration for mock histogram generation"""

    num_values: int = Field(
        default=10000, le=1000000, description="Number of data points"
    )
    distribution: str = Field(default="normal", description="Distribution type")
    mean: float = Field(default=0.0, description="Mean value")
    std: float = Field(default=1.0, description="Standard deviation")


class MockScatterConfig(BaseModel):
    """Configuration for mock scatter plot generation"""

    num_points: int = Field(default=1000, le=100000, description="Number of points")
    correlation: float = Field(
        default=0.7, ge=-1.0, le=1.0, description="Correlation coefficient"
    )


class MockTableConfig(BaseModel):
    """Configuration for mock table generation"""

    num_rows: int = Field(default=100, le=10000, description="Number of rows")
    num_cols: int = Field(default=6, le=50, description="Number of columns")


@router.post("/mock/metrics")
async def generate_mock_metrics(config: MockMetricsConfig):
    """Generate mock metrics data"""
    logger_mock.info(
        f"Generating mock metrics: steps={config.steps}, metrics={config.metrics}"
    )

    try:
        data = generate_metrics_data(steps=config.steps, metrics=config.metrics)
        return {"metrics": data}
    except Exception as e:
        logger_mock.error(f"Failed to generate mock metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mock/histogram")
async def generate_mock_histogram(config: MockHistogramConfig):
    """Generate mock histogram data"""
    logger_mock.info(
        f"Generating mock histogram: num_values={config.num_values}, distribution={config.distribution}"
    )

    try:
        data = generate_histogram_data(
            num_values=config.num_values,
            distribution=config.distribution,
            mean=config.mean,
            std=config.std,
        )
        return data
    except Exception as e:
        logger_mock.error(f"Failed to generate mock histogram: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mock/scatter")
async def generate_mock_scatter(config: MockScatterConfig):
    """Generate mock scatter plot data"""
    logger_mock.info(
        f"Generating mock scatter: num_points={config.num_points}, correlation={config.correlation}"
    )

    try:
        data = generate_scatter_data(
            num_points=config.num_points, correlation=config.correlation
        )
        return {"scatter": data}
    except Exception as e:
        logger_mock.error(f"Failed to generate mock scatter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mock/table")
async def generate_mock_table(config: MockTableConfig):
    """Generate mock table data"""
    logger_mock.info(
        f"Generating mock table: rows={config.num_rows}, cols={config.num_cols}"
    )

    try:
        data = generate_table_data(num_rows=config.num_rows, num_cols=config.num_cols)
        return data
    except Exception as e:
        logger_mock.error(f"Failed to generate mock table: {e}")
        raise HTTPException(status_code=500, detail=str(e))
