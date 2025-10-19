#!/usr/bin/env python3
"""Deploy KohakuHub using Docker Compose.

This script:
1. Builds frontend (UI and Admin)
2. Runs docker compose up -d --build
"""

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

    result = subprocess.run(cmd, cwd=cwd, shell=True)

    if result.returncode != 0:
        print(f"\n❌ Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    print(f"✓ {description or 'Command'} completed")


def main():
    """Main function."""
    root_dir = Path(__file__).parent.parent
    ui_dir = root_dir / "src" / "kohaku-hub-ui"
    admin_dir = root_dir / "src" / "kohaku-hub-admin"

    print("\n🚀 KohakuHub Deployment")
    print("=" * 60)

    # Step 1: Build UI
    run_command(["npm", "run", "build"], cwd=ui_dir, description="Building UI")

    # Step 2: Build Admin
    run_command(["npm", "run", "build"], cwd=admin_dir, description="Building Admin")

    # Step 3: Docker Compose up
    run_command(
        ["docker", "compose", "up", "-d", "--build"],
        cwd=root_dir,
        description="Starting Docker containers",
    )

    print("\n" + "=" * 60)
    print("✅ KohakuHub deployed successfully!")
    print("=" * 60)
    print("\n📍 Access Points:")
    print("   Main UI:    http://localhost:28080")
    print("   Admin UI:   http://localhost:28080/admin")
    print("   API:        http://localhost:28080/api")
    print("   API Docs:   http://localhost:28080/docs")
    print("\n💡 Tip: View logs with: docker compose logs -f")


if __name__ == "__main__":
    main()
