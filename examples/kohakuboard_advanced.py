"""Advanced KohakuBoard usage example with images and tables"""

import time

import numpy as np

from kohakuboard.client import Board, Table


def main():
    # Create board - it will auto-finish on program exit (via atexit)
    # No need for 'with' statement - just create it!
    board = Board(
        name="advanced_example",
        config={
            "model": "ResNet50",
            "dataset": "ImageNet",
            "optimizer": "AdamW",
            "lr": 0.001,
            "batch_size": 64,
        },
    )

    print("Training simulation with images and tables...")

    # Simulate training epochs with explicit steps
    for epoch in range(5):
        # Explicit step increment (this is our "global_step")
        # This should be ONCE per epoch, not per batch!
        board.step()

        print(f"\n=== Epoch {epoch + 1} ===")

        # Simulate training batches
        epoch_losses = []
        for batch_idx in range(100):
            # Simulate training
            loss = np.random.randn() * 0.1 + (2.0 / (epoch + 1))
            epoch_losses.append(loss)

            # Log every batch (all belong to same global_step=epoch)
            board.log(
                batch_loss=float(loss),
                learning_rate=0.001 * (0.9**epoch),
            )

            # Log images occasionally
            if batch_idx % 30 == 0:
                # Generate fake images (random noise)
                fake_images = [
                    (np.random.rand(64, 64, 3) * 255).astype(np.uint8) for _ in range(4)
                ]

                board.log_images(
                    "predictions",
                    fake_images,
                    caption=f"Predictions at epoch {epoch + 1}, batch {batch_idx}",
                )
                print(f"  Batch {batch_idx}: logged 4 images")

            time.sleep(0.01)  # Simulate work

        # Epoch summary metrics
        train_loss = np.mean(epoch_losses)
        val_loss = train_loss * 0.9  # Simulate validation

        board.log(
            epoch_train_loss=float(train_loss),
            epoch_val_loss=float(val_loss),
            epoch=epoch + 1,
        )

        # Log per-class metrics table
        class_metrics = Table(
            [
                {
                    "class": "cat",
                    "precision": 0.85 + epoch * 0.02,
                    "recall": 0.80 + epoch * 0.03,
                },
                {
                    "class": "dog",
                    "precision": 0.88 + epoch * 0.01,
                    "recall": 0.85 + epoch * 0.02,
                },
                {
                    "class": "bird",
                    "precision": 0.75 + epoch * 0.03,
                    "recall": 0.70 + epoch * 0.04,
                },
            ]
        )
        board.log_table("class_metrics", class_metrics)

        print(
            f"  Epoch {epoch + 1} complete: train_loss={train_loss:.4f}, val_loss={val_loss:.4f}"
        )

    print(f"\nBoard saved to: {board.board_dir}")
    print("Training complete!")

    # Board automatically finishes on program exit (atexit hook)
    # Or call board.finish() explicitly if you want immediate cleanup


if __name__ == "__main__":
    main()
