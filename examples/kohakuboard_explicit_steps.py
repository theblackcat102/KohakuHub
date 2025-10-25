"""Example demonstrating explicit step tracking vs auto-increment step"""

import time

import numpy as np

from kohakuboard.client import Board


def main():
    board = Board(name="explicit_steps_demo")

    print("Demonstrating explicit step tracking...")
    print("\nKey concept:")
    print("- auto_step: Increments every time you log (step column in parquet)")
    print(
        "- global_step: Explicit step you control via board.step() (global_step column)"
    )
    print()
    print("Use case: Training with multiple batches per epoch")
    print("- global_step = epoch number")
    print("- auto_step = individual log calls")
    print("- All batches in an epoch share the same global_step")
    print()

    # Example: 3 epochs, 5 batches each
    for epoch in range(3):
        # Set global step (this is our "epoch number")
        board.step()  # global_step = 0, 1, 2

        print(f"\n=== Epoch {epoch} (global_step={board._global_step}) ===")

        for batch in range(5):
            # Simulate batch metrics
            batch_loss = np.random.rand() + 1.0 / (epoch + 1)

            # Log batch metrics
            # Each log call increments auto_step (0, 1, 2, 3, ...)
            # But all logs in this epoch have global_step = epoch
            board.log(
                batch_idx=batch,
                batch_loss=float(batch_loss),
            )

            print(
                f"  Batch {batch}: auto_step increments, but global_step={board._global_step}"
            )

            time.sleep(0.05)

    print("\n" + "=" * 60)
    print("Result in Parquet file:")
    print("=" * 60)
    print("| auto_step | global_step | batch_idx | batch_loss |")
    print("|-----------|-------------|-----------|------------|")
    print("|     0     |      0      |     0     |   1.234    |")
    print("|     1     |      0      |     1     |   1.456    |")
    print("|     2     |      0      |     2     |   1.678    |")
    print("|     3     |      0      |     3     |   1.890    |")
    print("|     4     |      0      |     4     |   1.012    |")
    print("|     5     |      1      |     0     |   0.876    |")
    print("|     6     |      1      |     1     |   0.654    |")
    print("|    ...    |     ...     |    ...    |    ...     |")
    print()
    print("Query examples:")
    print("- Get all logs for epoch 0: WHERE global_step = 0")
    print("- Get logs from step 5 to 10: WHERE auto_step BETWEEN 5 AND 10")
    print("- Get all batches for epoch 1: WHERE global_step = 1")

    board.finish()
    print(f"\nData saved to: {board.board_dir}")


if __name__ == "__main__":
    main()
