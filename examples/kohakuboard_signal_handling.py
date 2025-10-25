"""Example: Graceful shutdown on Ctrl+C and exceptions"""

import time

import numpy as np

from kohakuboard.client import Board


def main():
    board = Board(name="signal_handling_demo")

    print("Demonstrating graceful shutdown...")
    print("\nTry one of these:")
    print("1. Press Ctrl+C during logging")
    print("2. Let it complete normally")
    print("3. Uncomment the exception to test crash handling")
    print("\nIn all cases, logs will be flushed and saved!\n")

    try:
        for i in range(100):
            # Log some metrics
            board.log(
                iteration=i,
                loss=1.0 / (i + 1),
                accuracy=min(0.99, 0.5 + i * 0.005),
            )

            if i % 10 == 0:
                print(f"Iteration {i}: logged metrics (try Ctrl+C now!)")

            time.sleep(0.1)  # Slow down to make Ctrl+C easier

            # Uncomment to test exception handling
            # if i == 50:
            #     raise ValueError("Simulated crash!")

        print("\n✓ Completed normally")

    except KeyboardInterrupt:
        print("\n✓ Caught Ctrl+C, cleaning up...")
        # Signal handlers will call board.finish() automatically

    except Exception as e:
        print(f"\n✗ Exception occurred: {e}")
        # sys.excepthook will call board.finish() automatically

    print(f"\nBoard saved to: {board.board_dir}")
    print("Check the data - it should all be there despite interruption!")


if __name__ == "__main__":
    main()
