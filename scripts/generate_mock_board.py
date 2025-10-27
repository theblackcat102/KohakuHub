#!/usr/bin/env python3
"""Generate mock board data for KohakuBoard testing

Creates realistic training run data with configurable number of metrics and steps.
Uses the KohakuBoard client API to ensure correct format.

Usage:
    python scripts/generate_mock_board.py --steps 1000 --metrics 5
    python scripts/generate_mock_board.py --steps 5000 --metrics 10 --name "resnet_training"
    python scripts/generate_mock_board.py --steps 100 --metrics 3 --add-images --add-tables
"""

import argparse
import math
import random
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kohakuboard.client import Board
import numpy as np


def generate_loss_curve(
    steps: int, base: float = 2.0, noise: float = 0.1
) -> list[float]:
    """Generate realistic decreasing loss curve with noise

    Args:
        steps: Number of data points
        base: Base loss value at start
        noise: Noise level (0.0 to 1.0)

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

        curve.append(max(0.001, value))  # Keep positive

    return curve


def generate_accuracy_curve(
    steps: int, target: float = 0.95, noise: float = 0.02
) -> list[float]:
    """Generate realistic increasing accuracy curve

    Args:
        steps: Number of data points
        target: Target accuracy (e.g., 0.95 for 95%)
        noise: Noise level

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


def generate_gradient_norm_curve(steps: int, base: float = 10.0) -> list[float]:
    """Generate gradient norm curve (usually decreases over time)

    Args:
        steps: Number of data points
        base: Base gradient norm

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

        curve.append(max(0.1, value))

    return curve


def generate_metric_curve(metric_name: str, steps: int) -> list[float]:
    """Generate curve for arbitrary metric name

    Args:
        metric_name: Name of the metric
        steps: Number of data points

    Returns:
        List of metric values
    """
    # Determine behavior based on metric name
    name_lower = metric_name.lower()

    if "loss" in name_lower or "error" in name_lower:
        return generate_loss_curve(steps, base=random.uniform(1.0, 3.0))

    elif (
        "acc" in name_lower
        or "precision" in name_lower
        or "recall" in name_lower
        or "f1" in name_lower
    ):
        return generate_accuracy_curve(steps, target=random.uniform(0.85, 0.98))

    elif "lr" in name_lower or "learning_rate" in name_lower:
        return generate_learning_rate_schedule(
            steps, initial=random.uniform(0.0001, 0.01)
        )

    elif "grad" in name_lower or "norm" in name_lower:
        return generate_gradient_norm_curve(steps, base=random.uniform(5.0, 20.0))

    else:
        # Generic oscillating metric
        curve = []
        base = random.uniform(0.5, 2.0)
        for i in range(steps):
            t = i / steps
            value = base * (1 + 0.3 * math.sin(10 * t)) + random.gauss(0, 0.1)
            curve.append(value)
        return curve


def generate_mock_image():
    """Generate a simple mock image (numpy array)"""
    # Create a simple gradient image
    size = 64
    img = np.zeros((size, size, 3), dtype=np.uint8)

    for i in range(size):
        for j in range(size):
            img[i, j, 0] = int(255 * i / size)  # Red gradient
            img[i, j, 1] = int(255 * j / size)  # Green gradient
            img[i, j, 2] = int(128 + 127 * random.random())  # Random blue

    return img


def main():
    parser = argparse.ArgumentParser(
        description="Generate mock board data for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 1000 steps with 5 metrics
  python scripts/generate_mock_board.py --steps 1000 --metrics 5

  # Generate with custom name and more metrics
  python scripts/generate_mock_board.py --steps 5000 --metrics 10 --name "bert_pretraining"

  # Include images and tables
  python scripts/generate_mock_board.py --steps 500 --metrics 8 --add-images --add-tables

  # Quick test with minimal data
  python scripts/generate_mock_board.py --steps 100 --metrics 3
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
        default="mock_training_run",
        help="Name for the board (default: mock_training_run)",
    )

    parser.add_argument(
        "--base-dir",
        type=str,
        default="./kohakuboard",
        help="Base directory for boards (default: ./kohakuboard)",
    )

    parser.add_argument(
        "--add-images", action="store_true", help="Add mock images every 100 steps"
    )

    parser.add_argument(
        "--add-tables", action="store_true", help="Add mock tables every 250 steps"
    )

    parser.add_argument(
        "--backend",
        choices=["duckdb", "parquet"],
        default="duckdb",
        help="Storage backend (default: duckdb)",
    )

    args = parser.parse_args()

    # Validate inputs
    if args.steps < 1:
        print("❌ Error: --steps must be >= 1")
        sys.exit(1)

    if args.metrics < 1:
        print("❌ Error: --metrics must be >= 1")
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

    print("Generating mock board data")
    print(f"   Name: {args.name}")
    print(f"   Steps: {args.steps}")
    print(f"   Metrics: {args.metrics} ({', '.join(selected_metrics)})")
    print(f"   Base dir: {args.base_dir}")
    print(f"   Backend: {args.backend}")
    if args.add_images:
        print(f"   Images: Every 100 steps")
    if args.add_tables:
        print(f"   Tables: Every 250 steps")
    print()

    # Generate metric curves
    print("Generating metric curves...")
    metric_curves = {}
    for metric_name in selected_metrics:
        metric_curves[metric_name] = generate_metric_curve(metric_name, args.steps)
        print(f"   [OK] {metric_name}")

    # Create board
    print("\nCreating board...")
    config = {
        "model": "ResNet50",
        "batch_size": 32,
        "optimizer": "Adam",
        "initial_lr": 0.001,
        "epochs": args.steps // 100 if args.steps >= 100 else 1,
        "dataset": "ImageNet",
        "augmentation": True,
        "mock_data": True,  # Flag to indicate this is mock data
    }

    board = Board(
        name=args.name,
        config=config,
        base_dir=args.base_dir,
        capture_output=False,  # Don't capture output for mock data
        backend=args.backend,
    )

    print(f"   [OK] Board created: {board.board_id}")
    print(f"   [OK] Location: {board.board_dir}")

    # Log metrics
    print(f"\nLogging {args.steps} steps...")

    for step in range(args.steps):
        # Build metrics dict for this step
        metrics = {}
        for metric_name in selected_metrics:
            metrics[metric_name] = metric_curves[metric_name][step]

        # Increment global step first
        if step > 0:
            board.step()

        # Log metrics
        board.log(**metrics)

        # Add images occasionally
        if args.add_images and step > 0 and step % 100 == 0:
            images = [generate_mock_image() for _ in range(4)]
            board.log_images(
                "training_samples", images, caption=f"Training samples at step {step}"
            )

        # Add tables occasionally
        if args.add_tables and step > 0 and step % 250 == 0:
            table_data = [
                {
                    "step": step,
                    "epoch": step // 100,
                    "train_loss": metrics.get("train_loss", 0),
                    "val_loss": metrics.get("val_loss", 0),
                    "train_acc": metrics.get("train_acc", 0),
                    "val_acc": metrics.get("val_acc", 0),
                }
            ]
            board.log_table("checkpoints", table_data)

        # Progress indicator
        if (step + 1) % max(1, args.steps // 20) == 0:
            progress = (step + 1) / args.steps * 100
            print(f"   Progress: {progress:.0f}% ({step + 1}/{args.steps})")

    # Finish board
    print("\nFinishing board...")
    board.finish()

    print(f"\nMock board data generated successfully!")
    print(f"   Board ID: {board.board_id}")
    print(f"   Location: {board.board_dir}")
    print(f"   Total steps: {args.steps}")
    print(f"   Total metrics: {args.metrics}")
    print(f"\nTo view the board, run:")
    print(f"   kobo open {args.base_dir}")


if __name__ == "__main__":
    main()
