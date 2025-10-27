#!/usr/bin/env python3
"""Deploy KohakuBoard (build frontend + start Docker)"""

import subprocess
import sys
from pathlib import Path


def main():
    print("=" * 60)
    print("KohakuBoard Deployment Script")
    print("=" * 60)

    # Build frontend
    print("\n[1/3] Installing frontend dependencies...")
    result = subprocess.run(
        ["npm", "install", "--prefix", "./src/kohaku-board-ui"],
        check=False,
    )
    if result.returncode != 0:
        print("✗ Failed to install dependencies")
        sys.exit(1)

    print("\n[2/3] Building frontend...")
    result = subprocess.run(
        ["npm", "run", "build", "--prefix", "./src/kohaku-board-ui"],
        check=False,
    )
    if result.returncode != 0:
        print("✗ Failed to build frontend")
        sys.exit(1)

    print("\n[3/3] Starting Docker services...")
    result = subprocess.run(
        [
            "docker-compose",
            "-f",
            "docker-compose.kohakuboard.yml",
            "up",
            "-d",
            "--build",
        ],
        check=False,
    )
    if result.returncode != 0:
        print("✗ Failed to start Docker services")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ KohakuBoard deployed successfully!")
    print("=" * 60)
    print(f"\nWeb UI: http://localhost:28081")
    print(f"API Docs: http://localhost:48889/api/docs")
    print("\nView logs: docker-compose -f docker-compose.kohakuboard.yml logs -f")
    print("Stop services: docker-compose -f docker-compose.kohakuboard.yml down")
    print()


if __name__ == "__main__":
    main()
