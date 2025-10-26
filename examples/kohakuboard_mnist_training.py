"""Simplest MNIST training example with KohakuBoard

Demonstrates all features with minimal code:
- Scalar logging (loss, val_loss, val_acc, lr)
- Histogram logging (gradients, parameters)
- Table logging (sample predictions)
- Namespace/tab organization (train/xxx, val/xxx, etc.)
- AnySchedule LR scheduling
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.utils.data import DataLoader
from torchvision.datasets import MNIST
from torchvision.transforms import transforms
from tqdm import tqdm
from anyschedule import AnySchedule

from kohakuboard.client import Board, Table, Media


def main():
    # Config
    batch_size = 128
    epochs = 2
    lr = 5e-3

    # Create board
    board = Board(name="mnist_simple", config={"lr": lr, "batch_size": batch_size})

    # Load real MNIST dataset
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
    )

    train_dataset = MNIST("./data", train=True, download=True, transform=transform)
    val_dataset = MNIST("./data", train=False, transform=transform)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)

    # Model (simplest possible)
    model = nn.Sequential(
        nn.Flatten(),
        nn.Linear(28 * 28, 256),
        nn.Mish(),
        nn.Linear(256, 128),
        nn.Mish(),
        nn.Linear(128, 10),
    )

    # Optimizer
    optimizer = AdamW(model.parameters(), lr=lr)

    # AnySchedule (cosine annealing)
    total_steps = len(train_loader) * epochs
    scheduler = AnySchedule(
        optimizer,
        config={
            "lr": {
                "mode": "cosine",
                "end": total_steps + 1,
                "warmup": 100,
                "value": 1.0,  # Scale
                "min_value": 0.1,
            }
        },
    )

    print("Starting training...")

    # Training loop
    for epoch in range(epochs):
        print(f"\n{'='*60}\nEpoch {epoch + 1}/{epochs}\n{'='*60}")

        # Train
        model.train()
        epoch_losses = []

        pbar = tqdm(train_loader, desc="Training", ncols=100)
        for batch_idx, (data, target) in enumerate(pbar):
            optimizer.zero_grad()

            # Forward
            output = model(data)
            loss = F.nll_loss(F.log_softmax(output, dim=1), target)

            # Backward
            loss.backward()
            optimizer.step()
            scheduler.step()

            # Log AFTER optimizer.step()
            board.step()

            # Log training metrics (train/ tab)
            current_lr = optimizer.param_groups[0]["lr"]
            board.log(**{"train/loss": loss.item(), "train/lr": current_lr})

            # Log histograms every 50 steps
            if board._global_step % 128 == 0:
                # Gradients (gradients/ tab)
                for i, param in enumerate(model.parameters()):
                    if param.grad is not None:
                        board.log_histogram(f"gradients/layer_{i}", param.grad)

                # Parameters (params/ tab)
                for i, param in enumerate(model.parameters()):
                    board.log_histogram(f"params/layer_{i}", param)

            epoch_losses.append(loss.item())
            pbar.set_postfix(loss=f"{loss.item():.4f}", lr=f"{current_lr:.6f}")

        # Validation
        model.eval()
        val_losses = []
        correct = 0
        total = 0
        per_class_correct = [0] * 10
        per_class_total = [0] * 10

        # For table: store first batch predictions
        sample_data = None
        sample_target = None
        sample_pred = None

        with torch.no_grad():
            for batch_idx, (data, target) in enumerate(
                tqdm(val_loader, desc="Validation", leave=False, ncols=100)
            ):
                output = model(data)
                loss = F.nll_loss(F.log_softmax(output, dim=1), target)
                pred = output.argmax(dim=1)

                val_losses.append(loss.item())
                correct += (pred == target).sum().item()
                total += target.size(0)

                # Per-class accuracy
                for i in range(10):
                    mask = target == i
                    per_class_total[i] += mask.sum().item()
                    per_class_correct[i] += (pred[mask] == i).sum().item()

                # Save first batch for table
                if batch_idx == 0:
                    sample_data = data[:10]  # First 10 samples
                    sample_target = target[:10]
                    sample_pred = pred[:10]

        val_loss = np.mean(val_losses)
        val_acc = correct / total

        # Log validation metrics (val/ tab)
        board.log(**{"val/loss": val_loss, "val/acc": val_acc})

        # Log per-class accuracy table (val/ tab)
        class_metrics = [
            {
                "class": i,
                "samples": per_class_total[i],
                "correct": per_class_correct[i],
                "accuracy": (
                    per_class_correct[i] / per_class_total[i]
                    if per_class_total[i] > 0
                    else 0.0
                ),
            }
            for i in range(10)
        ]
        board.log_table("val/class_metrics", Table(class_metrics))

        # Log sample predictions table with images (val/ tab)
        if sample_pred is not None:
            predictions_table = []
            for i in range(len(sample_target)):
                # Denormalize image: (img * std) + mean
                img = sample_data[i].squeeze().numpy()
                img = img * 0.3081 + 0.1307  # Denormalize MNIST
                img = (np.clip(img, 0, 1) * 255).astype(np.uint8)

                predictions_table.append(
                    {
                        "sample_idx": i,
                        "image": Media(img, media_type="image"),
                        "ground_truth": sample_target[i].item(),
                        "prediction": sample_pred[i].item(),
                        "correct": "✓" if sample_target[i] == sample_pred[i] else "✗",
                    }
                )

            board.log_table("val/sample_predictions", Table(predictions_table))

        # Log epoch summary (main tab)
        board.log(
            epoch=epoch,
            epoch_train_loss=np.mean(epoch_losses),
            epoch_val_loss=val_loss,
            epoch_val_acc=val_acc,
        )

        print(
            f"Epoch {epoch + 1}: train_loss={np.mean(epoch_losses):.4f}, "
            f"val_loss={val_loss:.4f}, val_acc={val_acc:.3f}"
        )

    print(f"\n{'='*60}")
    print("Training complete!")
    print(f"Board saved to: {board.board_dir}")
    print(f"\nLogged data (namespace-based tabs):")
    print("  Main: epoch, epoch_train_loss, epoch_val_loss, epoch_val_acc")
    print("  train/: loss, lr")
    print("  val/: loss, acc, class_metrics, sample_predictions")
    print("  gradients/: layer_0, layer_2, layer_4 (histograms)")
    print("  params/: layer_0, layer_2, layer_4 (histograms)")
    print(f"\nView: python -m kohakuboard.main → http://localhost:48889")


if __name__ == "__main__":
    main()
