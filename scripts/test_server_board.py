#!/usr/bin/env python3
"""Start KohakuBoard test server (SQLite, remote mode, no Docker)

This is a convenience script for testing remote mode with SQLite database.
Useful for development and testing without Docker.
"""

import os
import subprocess
import sys


def main():
    print("=" * 60)
    print("KohakuBoard Test Server (SQLite + Remote Mode)")
    print("=" * 60)

    # Set test configuration
    os.environ["KOHAKU_BOARD_MODE"] = "remote"
    os.environ["KOHAKU_BOARD_DB_BACKEND"] = "sqlite"
    os.environ["KOHAKU_BOARD_DATABASE_URL"] = "sqlite:///test-kohakuboard.db"
    os.environ["KOHAKU_BOARD_AUTH_SESSION_SECRET"] = "test-secret-do-not-use-in-prod"
    os.environ["KOHAKU_BOARD_AUTH_REQUIRE_EMAIL_VERIFICATION"] = "false"
    os.environ["KOHAKU_BOARD_AUTH_INVITATION_ONLY"] = "false"
    os.environ["KOHAKU_BOARD_BASE_URL"] = "http://localhost:48889"
    os.environ["KOHAKU_BOARD_PORT"] = "48889"
    os.environ["KOHAKU_BOARD_SMTP_ENABLED"] = "false"

    print("\n📋 Configuration:")
    print(f"   Mode: remote")
    print(f"   Database: test-kohakuboard.db (SQLite)")
    print(f"   Port: 48889")
    print(f"   Auth: Enabled (no email verification)")
    print("\n🌐 URLs:")
    print(f"   API: http://localhost:48889")
    print(f"   API Docs: http://localhost:48889/api/docs")
    print("\n⚠️  Note: This is a TEST server. Do NOT use in production!")
    print("=" * 60)
    print("\nStarting server...\n")

    try:
        subprocess.run(
            [
                "uvicorn",
                "kohakuboard.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "48889",
                "--reload",
            ],
            check=True,
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\n✗ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
