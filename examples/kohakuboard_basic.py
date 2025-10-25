"""Basic KohakuBoard usage example"""

import time

import numpy as np

from kohakuboard.client import Board


def main():
    # Create a board
    board = Board(
        name="basic_example",
        config={"learning_rate": 0.001, "batch_size": 32},
    )

    print("Starting basic logging example...")

    # Simple logging without explicit steps
    for i in range(100):
        # Log scalars (non-blocking)
        board.log(
            iteration=i,
            loss=1.0 / (i + 1),  # Decreasing loss
            accuracy=min(0.99, 0.5 + i * 0.005),  # Increasing accuracy
        )

        # Log occasionally
        if i % 10 == 0:
            print(f"Iteration {i}: logged metrics")

        time.sleep(0.01)  # Simulate work

    # Flush to ensure everything is written
    # We have auto-flush in runtime but it is recommended
    board.flush()

    print(f"\nBoard saved to: {board.board_dir}")
    print("Done! You can now view this board in the KohakuBoard UI.")

    # Clean finish
    board.finish()


if __name__ == "__main__":
    main()
