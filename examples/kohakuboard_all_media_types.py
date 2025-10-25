"""Example: Logging images, videos, and audio"""

import numpy as np

from kohakuboard.client import Board, Media, Table


def main():
    board = Board(name="all_media_types_demo")

    print("Demonstrating all media types: images, videos, audio...")

    # 1. Log images (numpy arrays)
    print("\n1. Logging images from numpy arrays...")
    cat_image = (np.random.rand(128, 128, 3) * 255).astype(np.uint8)
    board.log_images("predictions", [cat_image], caption="Generated cat image")
    print("   ✓ Logged image from numpy array")

    # 2. Log video (file path)
    print("\n2. Logging video from file path...")
    # board.log_video("training_viz", "path/to/video.mp4", caption="Training progress")
    print("   (Skipped - requires actual video file)")

    # 3. Log audio (file path)
    print("\n3. Logging audio from file path...")
    # board.log_audio("tts_output", "path/to/audio.wav", caption="Generated speech")
    print("   (Skipped - requires actual audio file)")

    # 4. Using Media objects in log()
    print("\n4. Using Media objects directly...")
    dog_image = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)
    board.log(
        loss=0.5,
        sample_image=Media(dog_image, caption="Dog sample"),  # Media in log()!
    )
    print("   ✓ Logged scalar + Media object together")

    # 5. Media in tables (with media_id references)
    print("\n5. Media objects in tables...")
    img1 = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)
    img2 = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)
    img3 = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)

    results_table = Table(
        [
            {"class": "cat", "image": Media(img1), "precision": 0.95},
            {"class": "dog", "image": Media(img2), "precision": 0.88},
            {"class": "bird", "image": Media(img3), "precision": 0.76},
        ]
    )

    board.log_table("classification_results", results_table)
    print("   ✓ Logged table with embedded Media objects")
    print("     → Images saved first, table stores <media id=...> references")

    print("\n" + "=" * 60)
    print("Result in Parquet files:")
    print("=" * 60)
    print("\nmedia.parquet:")
    print("step | global_step | name        | type  | media_id (hash) | path")
    print("-----|-------------|-------------|-------|-----------------|------")
    print("0    | NULL        | predictions | image | abc123...       | /path/img.png")
    print("1    | NULL        | sample_img  | image | def456...       | /path/img2.png")
    print("2    | NULL        | results_0_0 | image | ghi789...       | /path/img3.png")
    print("2    | NULL        | results_1_0 | image | jkl012...       | /path/img4.png")
    print("2    | NULL        | results_2_0 | image | mno345...       | /path/img5.png")
    print("\ntables.parquet:")
    print("step | name                   | rows")
    print("-----|------------------------|------")
    print('2    | classification_results | [["cat","<media id=ghi789...>",0.95],...]')
    print("\n→ Frontend can lookup media by ID from media.parquet!")

    board.finish()
    print(f"\nData saved to: {board.board_dir}")


if __name__ == "__main__":
    main()
