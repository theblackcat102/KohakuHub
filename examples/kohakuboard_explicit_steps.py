"""Example demonstrating explicit step tracking vs auto-increment step"""

import time

import numpy as np

from kohakuboard.client import Board


def main():
    board = Board(name="explicit_steps_demo")

    print("Demonstrating explicit step tracking...")
    print("\nKey concept:")
    print("- _step (auto): Increments every time you log (for timeline/ordering)")
    print("- global_step: Increments via board.step() = OPTIMIZER STEP")
    print()
    print("Use case: Standard training loop")
    print("- Call board.step() once per batch (like optimizer.step())")
    print("- global_step tracks total optimizer steps")
    print("- _step tracks individual log calls (can log multiple times per step)")
    print()

    # Example: 3 epochs, 5 batches each
    for epoch in range(3):
        print(f"\n=== Epoch {epoch} ===")

        for batch in range(5):
            # Increment per batch (like optimizer.step())
            board.step()  # global_step increments every batch

            # Simulate batch metrics
            batch_loss = np.random.rand() + 1.0 / (epoch + 1)

            # Log batch metrics
            # Each log call increments _step (0, 1, 2, 3, ...)
            # global_step = total batches processed
            board.log(
                batch_loss=float(batch_loss),
                epoch=epoch,  # Log epoch as a metric
            )

            print(f"  Batch {batch}: global_step={board._global_step}")

            time.sleep(0.05)

    print("\n" + "=" * 60)
    print("Result in DuckDB:")
    print("=" * 60)
    print("| _step | global_step | epoch | batch_loss |")
    print("|-------|-------------|-------|------------|")
    print("|   0   |      1      |   0   |   1.234    |")
    print("|   1   |      2      |   0   |   1.456    |")
    print("|   2   |      3      |   0   |   1.678    |")
    print("|   3   |      4      |   0   |   1.890    |")
    print("|   4   |      5      |   0   |   1.012    |")
    print("|   5   |      6      |   1   |   0.876    |")
    print("|   6   |      7      |   1   |   0.654    |")
    print("|  ...  |     ...     |  ...  |    ...     |")
    print()
    print("Query examples:")
    print("- Get all logs for epoch 0: WHERE epoch = 0")
    print("- Get logs from optimizer step 5-10: WHERE global_step BETWEEN 5 AND 10")
    print("- Get logs in timeline order: ORDER BY _step")

    board.finish()
    print(f"\nData saved to: {board.board_dir}")


if __name__ == "__main__":
    main()
