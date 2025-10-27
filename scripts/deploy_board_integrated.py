#!/usr/bin/env python3
"""Deploy KohakuBoard integrated with KohakuHub (shared database for SSO)

OPTIONAL: This is only if you want to share database with KohakuHub.
For fully standalone deployment, use deploy_board.py instead.
"""

import subprocess
import sys


def main():
    print("=" * 60)
    print("KohakuBoard Integrated Deployment (OPTIONAL)")
    print("Shares database with KohakuHub for unified accounts")
    print("=" * 60)

    # Check if KohakuHub is running (optional warning, not error)
    print("\n[0/3] Checking KohakuHub services...")
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=postgres", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    if "postgres" not in result.stdout:
        print("⚠️  Warning: KohakuHub PostgreSQL is not running")
        print("\nThis deployment expects to connect to KohakuHub's database.")
        print("If you want fully standalone deployment, use:")
        print("  python scripts/deploy_board.py")
        print("\nIf you want to deploy KohakuHub first:")
        print("  1. cp docker-compose.example.yml docker-compose.yml")
        print("  2. Edit docker-compose.yml (change passwords and secrets)")
        print("  3. ./deploy.sh")
        print("\nContinuing anyway (will fail if database is not accessible)...")
    else:
        print("✓ KohakuHub PostgreSQL is running")

    # Build frontend
    print("\n[1/3] Building frontend...")
    result = subprocess.run(
        ["npm", "install", "--prefix", "./src/kohaku-board-ui"],
        check=False,
    )
    if result.returncode != 0:
        print("✗ Failed to install dependencies")
        sys.exit(1)

    result = subprocess.run(
        ["npm", "run", "build", "--prefix", "./src/kohaku-board-ui"],
        check=False,
    )
    if result.returncode != 0:
        print("✗ Failed to build frontend")
        sys.exit(1)

    print("\n[2/3] Starting KohakuBoard services...")
    result = subprocess.run(
        [
            "docker-compose",
            "-f",
            "docker-compose.board-integrated.yml",
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
    print("✓ KohakuBoard deployed successfully (integrated mode)!")
    print("=" * 60)
    print(f"\nKohakuHub: http://localhost:28080")
    print(f"KohakuBoard: http://localhost:28081")
    print(f"\n⚡ SSO enabled: Login works across both systems")
    print(f"\n📊 Shared database: Users are unified")
    print("\nView logs: docker-compose -f docker-compose.board-integrated.yml logs -f")
    print("Stop services: docker-compose -f docker-compose.board-integrated.yml down")
    print()


if __name__ == "__main__":
    main()
