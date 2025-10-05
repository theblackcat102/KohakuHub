#!/usr/bin/env python3
"""
Generate test files for upload testing.

Creates 1000 files of 1.5MB each in the large_file_test folder.
Useful for testing bulk uploads, LFS threshold behavior, and performance.
"""

import os
import random
import string
from pathlib import Path


def generate_random_text(size_bytes):
    """Generate random text content of specified size.

    Args:
        size_bytes: Target file size in bytes

    Returns:
        String of random text approximately the specified size
    """
    # Use a mix of text and numbers for more realistic content
    chars = string.ascii_letters + string.digits + " \n"

    # Generate in chunks to avoid memory issues
    chunk_size = 1024 * 100  # 100KB chunks
    chunks = []

    remaining = size_bytes
    while remaining > 0:
        current_chunk_size = min(chunk_size, remaining)
        chunk = "".join(random.choices(chars, k=current_chunk_size))
        chunks.append(chunk)
        remaining -= current_chunk_size

    return "".join(chunks)


def generate_structured_content(file_number, size_bytes):
    """Generate structured content with headers and repeated text.

    This creates more realistic file content with headers, sections, etc.

    Args:
        file_number: File number for unique header
        size_bytes: Target file size in bytes

    Returns:
        String of structured content
    """
    header = f"""# Test File {file_number:04d}

This is a generated test file for upload testing.
File size: {size_bytes / (1024*1024):.2f} MB

## Content Section

"""

    # Calculate how much content we need to fill
    remaining = size_bytes - len(header.encode("utf-8"))

    # Generate repeated paragraph content
    paragraph = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud
exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure
dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.

"""

    # Calculate how many paragraphs we need
    paragraph_bytes = len(paragraph.encode("utf-8"))
    num_paragraphs = remaining // paragraph_bytes + 1

    content = header + (paragraph * num_paragraphs)

    # Trim to exact size
    content_bytes = content.encode("utf-8")[:size_bytes]
    return content_bytes.decode("utf-8", errors="ignore")


def main():
    # Configuration
    output_dir = Path("large_file_test")
    num_files = 1000
    file_size_mb = 1.5
    file_size_bytes = int(file_size_mb * 1024 * 1024)

    # Create output directory
    output_dir.mkdir(exist_ok=True)
    print(f"Creating {num_files} files of {file_size_mb}MB each...")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Total size: {num_files * file_size_mb / 1024:.2f} GB")
    print()

    # Generate files
    for i in range(1, num_files + 1):
        filename = f"test_file_{i:04d}.txt"
        filepath = output_dir / filename

        # Generate content (use structured content for better testing)
        # Change to generate_random_text(file_size_bytes) for random content
        content = generate_structured_content(i, file_size_bytes)

        # Write file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # Progress indicator
        if i % 50 == 0:
            progress = (i / num_files) * 100
            print(f"Progress: {i}/{num_files} files ({progress:.1f}%)")

    print()
    print(f"✓ Successfully created {num_files} files")
    print(f"✓ Location: {output_dir.absolute()}")

    # Calculate actual size
    total_size = sum(f.stat().st_size for f in output_dir.glob("*.txt"))
    print(f"✓ Total size: {total_size / (1024**3):.2f} GB")
    print()
    print("You can now test with:")
    print("  - Upload via web UI")
    print("  - Upload via huggingface_hub CLI")
    print("  - Upload via kohub-cli")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback

        traceback.print_exc()
