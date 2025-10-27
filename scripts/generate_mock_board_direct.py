#!/usr/bin/env python3
"""Generate mock board data directly to DuckDB (no worker process)

Creates realistic training run data with NaN/inf values for testing edge cases.
Writes directly to DuckDB without using the Board client's worker process.

Usage:
    python scripts/generate_mock_board_direct.py --steps 1000 --metrics 5
    python scripts/generate_mock_board_direct.py --steps 500 --metrics 8 --add-nan-inf
"""

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from kohakuboard.client.storage_duckdb import DuckDBStorage


def generate_loss_curve(
    steps: int, base: float = 2.0, noise: float = 0.1, add_nan_inf: bool = False
) -> list[float]:
    """Generate realistic decreasing loss curve with noise

    Args:
        steps: Number of data points
        base: Base loss value at start
        noise: Noise level (0.0 to 1.0)
        add_nan_inf: Whether to inject NaN/inf values at random positions (guarantees at least 1)

    Returns:
        List of loss values
    """
    curve = []

    for i in range(steps):
        # Exponential decay with plateaus
        t = i / steps
        value = base * math.exp(-2 * t) + 0.1  # Converge to 0.1

        # Add some realistic noise
        value += random.gauss(0, noise * base * 0.1)

        # Add occasional spikes (learning rate adjustments, etc.)
        if random.random() < 0.01:
            value += random.uniform(0, noise * base * 0.5)

        value = max(0.001, value)  # Keep positive
        curve.append(value)

    # Randomly inject 1-3 special values at random positions
    if add_nan_inf:
        num_special = random.randint(1, min(3, steps))  # 1-3 special values
        positions = random.sample(range(steps), num_special)

        for pos in positions:
            choice = random.choice(["nan", "inf", "-inf"])
            if choice == "nan":
                curve[pos] = float("nan")
            elif choice == "inf":
                curve[pos] = float("inf")
            elif choice == "-inf":
                curve[pos] = float("-inf")

    return curve


def generate_accuracy_curve(
    steps: int, target: float = 0.95, noise: float = 0.02, add_nan_inf: bool = False
) -> list[float]:
    """Generate realistic increasing accuracy curve

    Args:
        steps: Number of data points
        target: Target accuracy (e.g., 0.95 for 95%)
        noise: Noise level
        add_nan_inf: Whether to inject NaN values at random positions (guarantees at least 1)

    Returns:
        List of accuracy values
    """
    curve = []
    start = 0.1  # Start from random performance

    for i in range(steps):
        t = i / steps
        # Sigmoid-like growth
        value = start + (target - start) * (1 - math.exp(-3 * t))

        # Add noise
        value += random.gauss(0, noise)

        # Clamp to [0, 1]
        value = max(0.0, min(1.0, value))
        curve.append(value)

    # Randomly inject 1-2 NaN values at random positions
    if add_nan_inf:
        num_special = random.randint(1, min(2, steps))
        positions = random.sample(range(steps), num_special)

        for pos in positions:
            curve[pos] = float("nan")

    return curve


def generate_learning_rate_schedule(steps: int, initial: float = 0.001) -> list[float]:
    """Generate learning rate schedule with step decay

    Args:
        steps: Number of data points
        initial: Initial learning rate

    Returns:
        List of learning rate values
    """
    curve = []
    lr = initial

    for i in range(steps):
        # Decay every 1/4 of training
        if i > 0 and i % (steps // 4) == 0:
            lr *= 0.5

        curve.append(lr)

    return curve


def generate_gradient_norm_curve(
    steps: int, base: float = 10.0, add_nan_inf: bool = False
) -> list[float]:
    """Generate gradient norm curve (usually decreases over time)

    Args:
        steps: Number of data points
        base: Base gradient norm
        add_nan_inf: Whether to inject NaN/inf values at random positions (guarantees at least 1)

    Returns:
        List of gradient norm values
    """
    curve = []

    for i in range(steps):
        t = i / steps
        # Decrease with occasional spikes
        value = base * (0.3 + 0.7 * math.exp(-2 * t))

        # Add noise
        value += random.gauss(0, base * 0.1)

        # Occasional gradient explosion
        if random.random() < 0.005:
            value *= random.uniform(2, 5)

        value = max(0.1, value)
        curve.append(value)

    # Randomly inject 1-3 special values at random positions
    if add_nan_inf:
        num_special = random.randint(1, min(3, steps))
        positions = random.sample(range(steps), num_special)

        for pos in positions:
            choice = random.choice(["inf", "nan"])
            if choice == "inf":
                curve[pos] = float("inf")
            else:
                curve[pos] = float("nan")

    return curve


def generate_metric_curve(
    metric_name: str, steps: int, add_nan_inf: bool = False
) -> list[float]:
    """Generate curve for arbitrary metric name

    Args:
        metric_name: Name of the metric
        steps: Number of data points
        add_nan_inf: Whether to inject NaN/inf values

    Returns:
        List of metric values
    """
    # Determine behavior based on metric name
    name_lower = metric_name.lower()

    if "loss" in name_lower or "error" in name_lower:
        return generate_loss_curve(
            steps, base=random.uniform(1.0, 3.0), add_nan_inf=add_nan_inf
        )

    elif (
        "acc" in name_lower
        or "precision" in name_lower
        or "recall" in name_lower
        or "f1" in name_lower
    ):
        return generate_accuracy_curve(
            steps, target=random.uniform(0.85, 0.98), add_nan_inf=add_nan_inf
        )

    elif "lr" in name_lower or "learning_rate" in name_lower:
        return generate_learning_rate_schedule(
            steps, initial=random.uniform(0.0001, 0.01)
        )

    elif "grad" in name_lower or "norm" in name_lower:
        return generate_gradient_norm_curve(
            steps, base=random.uniform(5.0, 20.0), add_nan_inf=add_nan_inf
        )

    else:
        # Generic oscillating metric
        curve = []
        base = random.uniform(0.5, 2.0)

        for i in range(steps):
            t = i / steps
            value = base * (1 + 0.3 * math.sin(10 * t)) + random.gauss(0, 0.1)
            curve.append(value)

        # Randomly inject 1-3 special values at random positions
        if add_nan_inf:
            num_special = random.randint(1, min(3, steps))
            positions = random.sample(range(steps), num_special)

            for pos in positions:
                choice = random.choice(["nan", "inf"])
                if choice == "nan":
                    curve[pos] = float("nan")
                else:
                    curve[pos] = float("inf")

        return curve


def main():
    parser = argparse.ArgumentParser(
        description="Generate mock board data directly to DuckDB (no worker process)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 1000 steps with 5 metrics
  python scripts/generate_mock_board_direct.py --steps 1000 --metrics 5

  # Generate with NaN/inf values for edge case testing
  python scripts/generate_mock_board_direct.py --steps 500 --metrics 8 --add-nan-inf

  # Quick test with minimal data
  python scripts/generate_mock_board_direct.py --steps 100 --metrics 3
        """,
    )

    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
        help="Number of data points per metric (default: 1000)",
    )

    parser.add_argument(
        "--metrics",
        type=int,
        default=5,
        help="Number of metrics to generate (default: 5)",
    )

    parser.add_argument(
        "--name",
        type=str,
        default="mock_training_direct",
        help="Name for the board (default: mock_training_direct)",
    )

    parser.add_argument(
        "--base-dir",
        type=str,
        default="./kohakuboard",
        help="Base directory for boards (default: ./kohakuboard)",
    )

    parser.add_argument(
        "--add-nan-inf",
        action="store_true",
        help="Inject NaN/±inf values for edge case testing",
    )

    args = parser.parse_args()

    # Validate inputs
    if args.steps < 1:
        print("Error: --steps must be >= 1")
        sys.exit(1)

    if args.metrics < 1:
        print("Error: --metrics must be >= 1")
        sys.exit(1)

    # Define metric names
    metric_names = [
        "train_loss",
        "val_loss",
        "train_acc",
        "val_acc",
        "learning_rate",
        "grad_norm",
        "train_f1",
        "val_f1",
        "perplexity",
        "bleu_score",
        "rouge_score",
        "validation_precision",
        "validation_recall",
        "gpu_memory_mb",
        "throughput_samples_per_sec",
    ]

    # Select requested number of metrics
    selected_metrics = metric_names[: args.metrics]

    print("Generating mock board data (direct DuckDB write)")
    print(f"   Name: {args.name}")
    print(f"   Steps: {args.steps}")
    print(f"   Metrics: {args.metrics} ({', '.join(selected_metrics)})")
    print(f"   Base dir: {args.base_dir}")
    print(f"   NaN/inf injection: {'Enabled' if args.add_nan_inf else 'Disabled'}")
    print()

    # Generate board ID
    board_id = (
        datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        + "_"
        + format(random.randint(0, 0xFFFFFFFF), "08x")
    )

    # Create board directory structure
    base_dir = Path(args.base_dir)
    board_dir = base_dir / board_id
    board_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "data").mkdir(exist_ok=True)
    (board_dir / "media").mkdir(exist_ok=True)
    (board_dir / "logs").mkdir(exist_ok=True)

    print(f"Board ID: {board_id}")
    print(f"Location: {board_dir}")
    print()

    # Generate metric curves
    print("Generating metric curves...")
    metric_curves = {}
    for metric_name in selected_metrics:
        metric_curves[metric_name] = generate_metric_curve(
            metric_name, args.steps, add_nan_inf=args.add_nan_inf
        )

        # Count special values if NaN/inf enabled
        if args.add_nan_inf:
            nan_count = sum(1 for v in metric_curves[metric_name] if math.isnan(v))
            inf_count = sum(
                1 for v in metric_curves[metric_name] if math.isinf(v) and v > 0
            )
            neginf_count = sum(
                1 for v in metric_curves[metric_name] if math.isinf(v) and v < 0
            )

            if nan_count + inf_count + neginf_count > 0:
                print(
                    f"   [OK] {metric_name} (NaN: {nan_count}, +inf: {inf_count}, -inf: {neginf_count})"
                )
            else:
                print(f"   [OK] {metric_name}")
        else:
            print(f"   [OK] {metric_name}")

    # Create DuckDB storage
    print("\nInitializing DuckDB storage...")
    storage = DuckDBStorage(board_dir / "data")
    print(f"   [OK] Database: {board_dir / 'data' / 'board.duckdb'}")

    # Write metrics directly to DuckDB
    print(f"\nWriting {args.steps} steps to DuckDB...")
    start_time = datetime.now(timezone.utc)

    for step in range(args.steps):
        # Build metrics dict for this step
        metrics = {}
        for metric_name in selected_metrics:
            metrics[metric_name] = metric_curves[metric_name][step]

        # Write directly to storage (no worker process!)
        timestamp = start_time.timestamp() + step  # Simulate time progression
        storage.append_metrics(
            step=step,
            global_step=step,
            metrics=metrics,
            timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc),
        )

        # Progress indicator
        if (step + 1) % max(1, args.steps // 20) == 0:
            progress = (step + 1) / args.steps * 100
            print(f"   Progress: {progress:.0f}% ({step + 1}/{args.steps})")

    # Flush remaining buffers
    print("\nFlushing buffers...")
    storage.flush_metrics()
    print("   [OK] All data written")

    # Create metadata.json
    print("\nWriting metadata...")
    config = {
        "model": "ResNet50",
        "batch_size": 32,
        "optimizer": "Adam",
        "initial_lr": 0.001,
        "epochs": args.steps // 100 if args.steps >= 100 else 1,
        "dataset": "ImageNet",
        "augmentation": True,
        "mock_data": True,
        "direct_write": True,
        "nan_inf_injection": args.add_nan_inf,
    }

    metadata = {
        "board_id": board_id,
        "name": args.name,
        "backend": "duckdb",
        "created_at": start_time.isoformat(),
        "config": config,
    }

    metadata_path = board_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"   [OK] {metadata_path}")

    print("\nMock board data generated successfully!")
    print(f"   Board ID: {board_id}")
    print(f"   Location: {board_dir}")
    print(f"   Total steps: {args.steps}")
    print(f"   Total metrics: {args.metrics}")

    if args.add_nan_inf:
        print(f"   Special values: NaN/±inf injected for testing")

    print(f"\nTo view the board, run:")
    print(f"   kobo open {args.base_dir}")


if __name__ == "__main__":
    main()
