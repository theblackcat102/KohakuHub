#!/usr/bin/env python3
"""Build and format KohakuBoard (frontend and backend).

This script:
1. Installs frontend dependencies
2. Formats frontend code
3. Builds frontend
4. Formats backend Python code
"""

import platform
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None, description: str = ""):
    """Run a command and exit if it fails."""
    if description:
        print(f"\n{'=' * 60}")
        print(f"  {description}")
        print(f"{'=' * 60}")

    print(f"Running: {' '.join(cmd)}")
    if cwd:
        print(f"  in: {cwd}")

    use_shell = platform.system() == "Windows"
    result = subprocess.run(cmd, cwd=cwd, shell=use_shell)

    if result.returncode != 0:
        print(f"\n❌ Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    print(f"[OK] {description or 'Command'} completed")


def main():
    """Main function."""
    root_dir = Path(__file__).parent.parent
    ui_dir = root_dir / "src" / "kohaku-board-ui"
    backend_dir = root_dir / "src" / "kohakuboard"

    print("\nKohakuBoard Build & Format")
    print("=" * 60)

    # Step 1: Install dependencies
    run_command(["npm", "install"], cwd=ui_dir, description="Installing dependencies")

    # Step 2: Format frontend
    run_command(
        ["npm", "run", "format"], cwd=ui_dir, description="Formatting frontend code"
    )

    # Step 3: Build frontend
    run_command(["npm", "run", "build"], cwd=ui_dir, description="Building frontend")

    # Step 4: Format Python backend
    run_command(
        ["black", str(backend_dir)], cwd=root_dir, description="Formatting Python code"
    )

    print("\n" + "=" * 60)
    print("[OK] KohakuBoard built and formatted successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("  - Frontend build: src/kohaku-board-ui/dist/")
    print("  - Start backend: uvicorn kohakuboard.main:app --reload --port 48889")


if __name__ == "__main__":
    main()
