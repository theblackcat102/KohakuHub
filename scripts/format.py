#!/usr/bin/env python3
"""Format all code (frontend and backend).

This script:
1. Builds frontend (to generate router/component info)
2. Formats frontend code
3. Formats backend Python code
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

    # Use shell=True on Windows (npm is npm.cmd), False on Unix
    use_shell = platform.system() == "Windows"

    result = subprocess.run(cmd, cwd=cwd, shell=use_shell)

    if result.returncode != 0:
        print(f"\n❌ Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    print(f"✓ {description or 'Command'} completed")


def main():
    """Main function."""
    root_dir = Path(__file__).parent.parent
    ui_dir = root_dir / "src" / "kohaku-hub-ui"
    admin_dir = root_dir / "src" / "kohaku-hub-admin"

    print("\nKohakuHub Code Formatter")
    print("=" * 60)

    # Step 1: Build UI (generates router/component definitions)
    run_command(
        ["npm", "run", "build"],
        cwd=ui_dir,
        description="Building UI (generating router/component info)",
    )

    # Step 2: Build Admin (generates router/component definitions)
    run_command(
        ["npm", "run", "build"],
        cwd=admin_dir,
        description="Building Admin (generating router/component info)",
    )

    # Step 3: Format UI
    run_command(["npm", "run", "format"], cwd=ui_dir, description="Formatting UI code")

    # Step 4: Format Admin
    run_command(
        ["npm", "run", "format"], cwd=admin_dir, description="Formatting Admin code"
    )

    # Step 5: Format Python
    run_command(["black", "."], cwd=root_dir, description="Formatting Python code")

    print("\n" + "=" * 60)
    print("[OK] All code formatted successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
