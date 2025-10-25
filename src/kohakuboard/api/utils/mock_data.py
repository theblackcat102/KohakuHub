"""Mock data generation utilities"""

import random
import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from kohakuboard.config import cfg


def generate_time_series_data(
    steps: int = None,
    start_value: float = 1.0,
    trend: str = "decreasing",
    noise_level: float = None,
    smoothness: float = 0.95,
) -> List[float]:
    """
    Generate realistic time series data

    Args:
        steps: Number of data points
        start_value: Starting value
        trend: 'increasing', 'decreasing', or 'stable'
        noise_level: Amount of random noise (0.0 to 1.0)
        smoothness: Exponential smoothing factor (0.0 to 1.0)

    Returns:
        List of values
    """
    if steps is None:
        steps = cfg.mock.default_steps
    if noise_level is None:
        noise_level = cfg.mock.default_noise_level

    values = []
    current_value = start_value
    smoothed_value = start_value

    for step in range(steps):
        # Calculate trend component
        progress = step / max(steps - 1, 1)

        match trend:
            case "decreasing":
                trend_value = start_value * math.exp(-3 * progress)
            case "increasing":
                trend_value = start_value * (1 + 2 * progress)
            case "stable":
                trend_value = start_value
            case "oscillating":
                trend_value = start_value * (1 + 0.3 * math.sin(10 * progress))
            case _:
                trend_value = start_value

        # Add noise
        noise = random.gauss(0, noise_level * start_value)

        # Combine and smooth
        current_value = trend_value + noise
        smoothed_value = smoothness * smoothed_value + (1 - smoothness) * current_value

        values.append(smoothed_value)

    return values


def generate_sparse_metrics_data(
    total_events: int = 1000, metrics_config: List[Dict[str, Any]] = None
) -> Dict[str, List[Any]]:
    """
    Generate sparse multi-metric logging data

    Args:
        total_events: Total number of logging events
        metrics_config: List of metric configurations with logging frequency

    Returns:
        Dict mapping metric names to lists with None for missing values
    """
    if metrics_config is None:
        metrics_config = [
            {
                "name": "train_loss",
                "log_every": 1,
                "type": "loss",
                "start": 2.5,
                "noise": 0.08,
            },
            {
                "name": "train_accuracy",
                "log_every": 1,
                "type": "accuracy",
                "start": 0.3,
                "noise": 0.015,
            },
            {
                "name": "val_loss",
                "log_every": 10,
                "type": "loss",
                "start": 2.8,
                "noise": 0.12,
            },
            {
                "name": "val_accuracy",
                "log_every": 10,
                "type": "accuracy",
                "start": 0.25,
                "noise": 0.02,
            },
            {
                "name": "learning_rate",
                "log_every": 5,
                "type": "lr",
                "start": 0.001,
                "noise": 0,
            },
            {"name": "step", "log_every": 1, "type": "step"},
        ]

    result = {"time": list(range(total_events))}

    for config in metrics_config:
        metric_name = config["name"]
        log_every = config["log_every"]
        metric_type = config.get("type", "default")
        start_val = config.get("start", 1.0)
        noise_level = config.get("noise", 0.1)

        values = []
        value_index = 0

        for i in range(total_events):
            if i % log_every == 0:
                if metric_type == "loss":
                    base_value = start_val * (0.95 ** (value_index / 10))
                    value = base_value + random.gauss(0, noise_level)
                elif metric_type == "accuracy":
                    progress = value_index / (total_events / log_every)
                    base_value = min(0.99, start_val + progress * 0.65)
                    value = base_value + random.gauss(0, noise_level)
                elif metric_type == "lr":
                    value = start_val * (0.99 ** (value_index / 10))
                elif metric_type == "step":
                    value = i
                else:
                    value = random.random()

                values.append(value)
                value_index += 1
            else:
                values.append(None)

        result[metric_name] = values

    return result


def generate_metrics_data(
    steps: int = None, metrics: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate mock metrics data for line plots

    Args:
        steps: Number of steps
        metrics: List of metric names

    Returns:
        List of metric series
    """
    if steps is None:
        steps = cfg.mock.default_steps
    if metrics is None:
        metrics = ["train_loss", "val_loss", "train_accuracy", "val_accuracy"]

    result = []

    for metric_name in metrics:
        x_values = list(range(steps))

        # Configure based on metric type
        if "loss" in metric_name:
            y_values = generate_time_series_data(
                steps=steps,
                start_value=2.5 if "train" in metric_name else 2.8,
                trend="decreasing",
                noise_level=0.05,
                smoothness=0.95,
            )
        elif "accuracy" in metric_name:
            y_values = generate_time_series_data(
                steps=steps,
                start_value=0.3 if "train" in metric_name else 0.25,
                trend="increasing",
                noise_level=0.02,
                smoothness=0.97,
            )
        else:
            y_values = generate_time_series_data(
                steps=steps,
                start_value=1.0,
                trend="stable",
                noise_level=0.1,
                smoothness=0.9,
            )

        result.append({"name": metric_name, "x": x_values, "y": y_values})

    return result


def generate_histogram_data(
    num_values: int = 10000,
    distribution: str = "normal",
    mean: float = 0.0,
    std: float = 1.0,
) -> Dict[str, Any]:
    """
    Generate histogram data

    Args:
        num_values: Number of data points
        distribution: 'normal', 'uniform', 'exponential'
        mean: Mean value (for normal distribution)
        std: Standard deviation (for normal distribution)

    Returns:
        Histogram data dict
    """
    match distribution:
        case "normal":
            values = [random.gauss(mean, std) for _ in range(num_values)]
        case "uniform":
            values = [random.uniform(mean - std, mean + std) for _ in range(num_values)]
        case "exponential":
            values = [random.expovariate(1 / std) for _ in range(num_values)]
        case _:
            values = [random.gauss(mean, std) for _ in range(num_values)]

    return {
        "values": values,
        "bins": 50,
        "name": f"{distribution.capitalize()} Distribution",
    }


def generate_scatter_data(
    num_points: int = 1000, correlation: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Generate scatter plot data

    Args:
        num_points: Number of data points
        correlation: Correlation between x and y (-1.0 to 1.0)

    Returns:
        List of scatter series
    """
    x_values = [random.gauss(0, 1) for _ in range(num_points)]
    y_values = [
        correlation * x + math.sqrt(1 - correlation**2) * random.gauss(0, 1)
        for x in x_values
    ]

    # Generate color values based on distance from origin
    colors = [math.sqrt(x**2 + y**2) for x, y in zip(x_values, y_values)]

    return [{"name": "Data Points", "x": x_values, "y": y_values, "color": colors}]


def generate_table_data(num_rows: int = 100, num_cols: int = 6) -> Dict[str, Any]:
    """
    Generate table data

    Args:
        num_rows: Number of rows
        num_cols: Number of columns

    Returns:
        Table data dict
    """
    columns = [f"Column_{i+1}" for i in range(num_cols)]
    rows = []

    for i in range(num_rows):
        row = [
            i + 1,  # ID column
            f"Item_{i+1}",  # Name column
            round(random.uniform(0, 100), 2),  # Value 1
            round(random.uniform(0, 1), 4),  # Value 2
            random.choice(["A", "B", "C", "D"]),  # Category
            round(random.uniform(0, 10), 1),  # Value 3
        ]
        rows.append(row[:num_cols])

    return {"columns": columns, "rows": rows}


def generate_experiment(
    experiment_id: str, name: str, steps: int = None, status: str = "completed"
) -> Dict[str, Any]:
    """
    Generate a complete experiment with all data

    Args:
        experiment_id: Experiment ID
        name: Experiment name
        steps: Number of training steps
        status: Experiment status

    Returns:
        Complete experiment data
    """
    if steps is None:
        steps = cfg.mock.default_steps

    created_at = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 168))
    duration_seconds = random.randint(600, 14400)  # 10 min to 4 hours

    return {
        "id": experiment_id,
        "name": name,
        "description": f"Mock experiment for testing KohakuBoard visualization",
        "status": status,
        "total_steps": steps,
        "duration": format_duration(duration_seconds),
        "created_at": created_at.isoformat(),
        "updated_at": (created_at + timedelta(seconds=duration_seconds)).isoformat(),
        "config": {
            "learning_rate": round(random.uniform(1e-5, 1e-2), 6),
            "batch_size": random.choice([16, 32, 64, 128]),
            "optimizer": random.choice(["Adam", "SGD", "AdamW"]),
            "model": random.choice(["ResNet50", "ViT-B/16", "BERT-base"]),
        },
    }


def format_duration(seconds: int) -> str:
    """Format duration in human-readable format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
