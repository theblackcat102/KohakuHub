#!/usr/bin/env python3
"""Generate test repository with nested folders and mixed LFS/non-LFS files."""

import hashlib
import os
import random
import string
from pathlib import Path


def random_content(size: int) -> bytes:
    """Generate random binary content.

    Args:
        size: Size in bytes

    Returns:
        Random bytes
    """
    return os.urandom(size)


def random_text_content(size: int) -> bytes:
    """Generate random text content.

    Args:
        size: Size in bytes

    Returns:
        Random text as bytes
    """
    chars = string.ascii_letters + string.digits + " \n"
    content = "".join(random.choices(chars, k=size))
    return content.encode("utf-8")


def create_file(path: Path, size: int, binary: bool = False):
    """Create a file with random content.

    Args:
        path: File path
        size: File size in bytes
        binary: If True, use binary content; otherwise text
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if binary:
        content = random_content(size)
    else:
        content = random_text_content(size)

    path.write_bytes(content)

    # Compute hashes for verification
    sha256 = hashlib.sha256(content).hexdigest()
    sha1 = hashlib.sha1(content).hexdigest()

    print(
        f"  {str(path):<60} {size:>10} bytes  sha256:{sha256[:8]}  {'[LFS]' if size >= 1_000_000 else ''}"
    )

    return sha256, size


def generate_test_repo(base_path: str = "test_folder"):
    """Generate test repository with nested structure.

    Structure:
      test_folder/
        README.md                          (small text)
        .gitattributes                     (LFS config)
        config/
          settings.json                    (small JSON)
          large_config.yaml                (LFS - 2MB)
        models/
          small_model.txt                  (small text)
          large_model.bin                  (LFS - 10MB)
          checkpoints/
            checkpoint_1.safetensors       (LFS - 5MB)
            checkpoint_2.safetensors       (LFS - 5MB)
            metadata.json                  (small)
        data/
          train/
            samples/
              image_001.png                (LFS - 1.5MB)
              image_002.png                (LFS - 1.5MB)
              labels.txt                   (small)
            dataset.csv                    (medium - 500KB)
          test/
            results.json                   (small)
        docs/
          guide.md                         (small)
          images/
            diagram.png                    (LFS - 2MB)
            screenshot.jpg                 (LFS - 1MB)
        scripts/
          train.py                         (small)
          evaluate.py                      (small)
    """
    base = Path(base_path)

    # Clean up if exists
    if base.exists():
        import shutil

        shutil.rmtree(base)

    print(f"\n{'='*100}")
    print(f"Generating test repository: {base_path}")
    print(f"LFS threshold: 1,000,000 bytes (1 MB)")
    print(f"{'='*100}\n")

    files_created = []

    # Root level files
    print("Root level:")
    files_created.append(create_file(base / "README.md", 5_000, binary=False))
    files_created.append(
        create_file(base / ".gitattributes", 200, binary=False)
    )  # Will overwrite with proper content

    # config/
    print("\nconfig/:")
    files_created.append(
        create_file(base / "config" / "settings.json", 1_500, binary=False)
    )
    files_created.append(
        create_file(base / "config" / "large_config.yaml", 2_000_000, binary=False)
    )  # LFS

    # models/
    print("\nmodels/:")
    files_created.append(
        create_file(base / "models" / "small_model.txt", 50_000, binary=False)
    )
    files_created.append(
        create_file(base / "models" / "large_model.bin", 10_000_000, binary=True)
    )  # LFS

    # models/checkpoints/
    print("\nmodels/checkpoints/:")
    files_created.append(
        create_file(
            base / "models" / "checkpoints" / "checkpoint_1.safetensors",
            5_000_000,
            binary=True,
        )
    )  # LFS
    files_created.append(
        create_file(
            base / "models" / "checkpoints" / "checkpoint_2.safetensors",
            5_500_000,
            binary=True,
        )
    )  # LFS
    files_created.append(
        create_file(
            base / "models" / "checkpoints" / "metadata.json", 800, binary=False
        )
    )

    # data/train/samples/
    print("\ndata/train/samples/:")
    files_created.append(
        create_file(
            base / "data" / "train" / "samples" / "image_001.png",
            1_500_000,
            binary=True,
        )
    )  # LFS
    files_created.append(
        create_file(
            base / "data" / "train" / "samples" / "image_002.png",
            1_600_000,
            binary=True,
        )
    )  # LFS
    files_created.append(
        create_file(
            base / "data" / "train" / "samples" / "image_003.png",
            1_400_000,
            binary=True,
        )
    )  # LFS
    files_created.append(
        create_file(
            base / "data" / "train" / "samples" / "labels.txt", 3_000, binary=False
        )
    )

    # data/train/
    print("\ndata/train/:")
    files_created.append(
        create_file(base / "data" / "train" / "dataset.csv", 500_000, binary=False)
    )

    # data/test/
    print("\ndata/test/:")
    files_created.append(
        create_file(base / "data" / "test" / "results.json", 2_500, binary=False)
    )

    # docs/
    print("\ndocs/:")
    files_created.append(create_file(base / "docs" / "guide.md", 8_000, binary=False))

    # docs/images/
    print("\ndocs/images/:")
    files_created.append(
        create_file(base / "docs" / "images" / "diagram.png", 2_000_000, binary=True)
    )  # LFS
    files_created.append(
        create_file(base / "docs" / "images" / "screenshot.jpg", 1_200_000, binary=True)
    )  # LFS

    # scripts/
    print("\nscripts/:")
    files_created.append(
        create_file(base / "scripts" / "train.py", 4_000, binary=False)
    )
    files_created.append(
        create_file(base / "scripts" / "evaluate.py", 3_500, binary=False)
    )

    # Generate proper .gitattributes
    print("\nGenerating .gitattributes...")
    lfs_files = []
    regular_files = []

    for sha256, size in files_created:
        if size >= 1_000_000:
            lfs_files.append((sha256, size))
        else:
            regular_files.append((sha256, size))

    gitattributes_lines = ["# Git LFS tracking\n"]
    gitattributes_lines.append("*.bin filter=lfs diff=lfs merge=lfs -text\n")
    gitattributes_lines.append("*.safetensors filter=lfs diff=lfs merge=lfs -text\n")
    gitattributes_lines.append("*.png filter=lfs diff=lfs merge=lfs -text\n")
    gitattributes_lines.append("*.jpg filter=lfs diff=lfs merge=lfs -text\n")
    gitattributes_lines.append(
        "config/large_config.yaml filter=lfs diff=lfs merge=lfs -text\n"
    )

    (base / ".gitattributes").write_text("".join(gitattributes_lines))

    # Summary
    print(f"\n{'='*100}")
    print("Summary:")
    print(f"  Total files: {len(files_created)}")
    print(f"  LFS files (>=1MB): {len(lfs_files)}")
    print(f"  Regular files (<1MB): {len(regular_files)}")

    total_size = sum(size for _, size in files_created)
    lfs_size = sum(size for _, size in lfs_files)
    regular_size = sum(size for _, size in regular_files)

    print(f"\n  Total size: {total_size / 1024 / 1024:.2f} MB")
    print(f"  LFS size: {lfs_size / 1024 / 1024:.2f} MB")
    print(f"  Regular size: {regular_size / 1024:.2f} KB")

    print(f"\n  Directory structure:")
    print(f"    - Root: 2 files")
    print(f"    - config/: 2 files")
    print(f"    - models/: 2 files")
    print(f"    - models/checkpoints/: 3 files")
    print(f"    - data/train/: 1 file")
    print(f"    - data/train/samples/: 4 files")
    print(f"    - data/test/: 1 file")
    print(f"    - docs/: 1 file")
    print(f"    - docs/images/: 2 files")
    print(f"    - scripts/: 2 files")

    print(f"\n  Test repository created at: {base.absolute()}")
    print(f"{'='*100}\n")

    # Create file listing
    file_list_path = base / "FILE_LIST.txt"
    with open(file_list_path, "w") as f:
        f.write("# File listing for test repository\n\n")
        for root, dirs, files in os.walk(base):
            level = root.replace(str(base), "").count(os.sep)
            indent = " " * 2 * level
            f.write(f"{indent}{os.path.basename(root)}/\n")
            sub_indent = " " * 2 * (level + 1)
            for file in files:
                if file == "FILE_LIST.txt":
                    continue
                file_path = Path(root) / file
                size = file_path.stat().st_size
                lfs_marker = "[LFS]" if size >= 1_000_000 else ""
                f.write(f"{sub_indent}{file} ({size} bytes) {lfs_marker}\n")

    print(f"File listing saved to: {file_list_path}\n")


if __name__ == "__main__":
    import sys

    base_path = sys.argv[1] if len(sys.argv) > 1 else "test_folder"
    generate_test_repo(base_path)
    print("✅ Test repository generated successfully!")
    print("\nNext steps:")
    print("  1. Upload to KohakuHub via API/CLI")
    print("  2. Test git clone")
    print("  3. Verify folder structure matches")
    print("  4. Test git lfs pull for large files")
