"""Example: Using Media objects in tables"""

import numpy as np

from kohakuboard.client import Board, Media, Table


def main():
    board = Board(name="media_in_tables_demo")

    print("Demonstrating Media objects in tables...")

    # Create some sample images
    cat_image = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)
    dog_image = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)
    bird_image = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)

    # Method 1: Using Media objects in Table
    results_table = Table(
        [
            {
                "class": "cat",
                "image": Media(cat_image, caption="Sample cat"),
                "precision": 0.95,
                "recall": 0.92,
            },
            {
                "class": "dog",
                "image": Media(dog_image, caption="Sample dog"),
                "precision": 0.88,
                "recall": 0.85,
            },
            {
                "class": "bird",
                "image": Media(bird_image, caption="Sample bird"),
                "precision": 0.76,
                "recall": 0.73,
            },
        ]
    )

    board.log_table("classification_results", results_table)
    print("✓ Logged table with embedded Media objects")

    # Method 2: Direct media logging (equivalent)
    board.log_images("cat_sample", cat_image, caption="Sample cat")
    board.log_images("dog_sample", dog_image, caption="Sample dog")
    board.log_images("bird_sample", bird_image, caption="Sample bird")
    print("✓ Logged images directly")

    # The table column type will be automatically inferred as "media"
    print(f"\nColumn types: {results_table.column_types}")
    # Output: ['text', 'media', 'number', 'number']

    board.finish()
    print(f"\nData saved to: {board.board_dir}")
    print("\nIn the frontend, the table will display:")
    print("- 'class' column: text")
    print("- 'image' column: thumbnail images")
    print("- 'precision'/'recall' columns: numbers")


if __name__ == "__main__":
    main()
