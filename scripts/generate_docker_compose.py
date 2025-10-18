#!/usr/bin/env python3
"""
Docker Compose Generator for KohakuHub

This script generates a docker-compose.yml file based on user preferences.
Can read configuration from kohakuhub.conf file for automation.
"""

import argparse
import configparser
import os
import secrets
import sys
from pathlib import Path


def generate_secret(length: int = 32) -> str:
    """Generate a random URL-safe secret key.

    Args:
        length: Number of random bytes (result will be ~1.33x longer due to base64 encoding)
                Common values: 32 (→43 chars), 48 (→64 chars)

    Returns:
        URL-safe base64 encoded string
    """
    return secrets.token_urlsafe(length)


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ["y", "yes"]:
            return True
        if response in ["n", "no"]:
            return False
        print("Please answer 'y' or 'n'")


def ask_string(prompt: str, default: str = "") -> str:
    """Ask for a string input."""
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    else:
        while True:
            response = input(f"{prompt}: ").strip()
            if response:
                return response
            print("This field is required")


def ask_int(prompt: str, default: int) -> int:
    """Ask for an integer input."""
    while True:
        response = input(f"{prompt} [{default}]: ").strip()
        if not response:
            return default
        try:
            return int(response)
        except ValueError:
            print("Please enter a valid number")


def generate_postgres_service(config: dict) -> str:
    """Generate PostgreSQL service configuration."""
    if config["postgres_builtin"]:
        return f"""  postgres:
    image: postgres:15
    container_name: postgres
    restart: always
    environment:
      - POSTGRES_USER={config['postgres_user']}
      - POSTGRES_PASSWORD={config['postgres_password']}
      - POSTGRES_DB={config['postgres_db']}
    ports:
      - "25432:5432" # Optional: for external access
    volumes:
      - ./hub-meta/postgres-data:/var/lib/postgresql/data
"""
    return ""


def generate_minio_service(config: dict) -> str:
    """Generate MinIO service configuration."""
    if config["s3_builtin"]:
        return f"""  minio:
    image: quay.io/minio/minio:latest
    container_name: minio
    command: server /data --console-address ":29000"
    environment:
      - MINIO_ROOT_USER={config['s3_access_key']}
      - MINIO_ROOT_PASSWORD={config['s3_secret_key']}
      - MINIO_REGION=auto
    ports:
      - "29001:9000"    # S3 API
      - "29000:29000"   # Web Console
    volumes:
      - ./hub-storage/minio-data:/data
      - ./hub-meta/minio-data:/root/.minio
"""
    return ""


def generate_lakefs_service(config: dict) -> str:
    """Generate LakeFS service configuration."""
    depends_on = []

    if config["s3_builtin"]:
        depends_on.append("minio")

    if config["postgres_builtin"] and config["lakefs_use_postgres"]:
        depends_on.append("postgres")

    depends_on_str = ""
    if depends_on:
        depends_on_str = "    depends_on:\n"
        for dep in depends_on:
            depends_on_str += f"      - {dep}\n"

    # LakeFS database configuration
    if config["lakefs_use_postgres"]:
        if config["postgres_builtin"]:
            lakefs_db_config = f"""      - LAKEFS_DATABASE_TYPE=postgres
      - LAKEFS_DATABASE_POSTGRES_CONNECTION_STRING=postgres://{config['postgres_user']}:{config['postgres_password']}@postgres:5432/{config['lakefs_db']}?sslmode=disable"""
            # Add environment variables for init script
            init_env_vars = f"""      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_USER={config['postgres_user']}
      - POSTGRES_PASSWORD={config['postgres_password']}
      - POSTGRES_DB={config['postgres_db']}
      - LAKEFS_DB={config['lakefs_db']}"""
        else:
            lakefs_db_config = f"""      - LAKEFS_DATABASE_TYPE=postgres
      - LAKEFS_DATABASE_POSTGRES_CONNECTION_STRING=postgres://{config['postgres_user']}:{config['postgres_password']}@{config['postgres_host']}:{config['postgres_port']}/{config['lakefs_db']}?sslmode=disable"""
            # Add environment variables for init script
            init_env_vars = f"""      - POSTGRES_HOST={config['postgres_host']}
      - POSTGRES_PORT={config['postgres_port']}
      - POSTGRES_USER={config['postgres_user']}
      - POSTGRES_PASSWORD={config['postgres_password']}
      - POSTGRES_DB={config['postgres_db']}
      - LAKEFS_DB={config['lakefs_db']}"""
    else:
        lakefs_db_config = """      - LAKEFS_DATABASE_TYPE=local
      - LAKEFS_DATABASE_LOCAL_PATH=/var/lakefs/data/metadata.db"""
        init_env_vars = ""

    # S3 blockstore configuration
    if config["s3_builtin"]:
        s3_endpoint = "http://minio:9000"
        force_path_style = "true"
        s3_region = "auto"
    else:
        s3_endpoint = config["s3_endpoint"]
        # Use path-style for all non-AWS endpoints (MinIO, CloudFlare R2, custom S3)
        # Only AWS S3 (*.amazonaws.com) should use virtual-hosted style
        force_path_style = "false" if "amazonaws.com" in s3_endpoint.lower() else "true"
        s3_region = config.get("s3_region", "auto")

    # Add entrypoint and volumes for database initialization
    entrypoint_config = ""
    volumes_config = """      - ./hub-meta/lakefs-data:/var/lakefs/data
      - ./hub-meta/lakefs-cache:/lakefs/data/cache"""

    if config["lakefs_use_postgres"]:
        entrypoint_config = """    entrypoint: ["/bin/sh", "/scripts/lakefs-entrypoint.sh"]
    command: ["run"]"""
        volumes_config += """
      - ./scripts/lakefs-entrypoint.sh:/scripts/lakefs-entrypoint.sh:ro
      - ./scripts/init-databases.sh:/scripts/init-databases.sh:ro"""

    # Add external network if needed (for external postgres or s3)
    lakefs_networks_str = ""
    if config.get("external_network") and (
        not config["postgres_builtin"] or not config["s3_builtin"]
    ):
        lakefs_networks_str = f"""    networks:
      - default
      - {config['external_network']}
"""

    return f"""  lakefs:
    image: treeverse/lakefs:latest
    container_name: lakefs
{entrypoint_config}
    environment:
{lakefs_db_config}
{init_env_vars}
      - LAKEFS_BLOCKSTORE_TYPE=s3
      - LAKEFS_BLOCKSTORE_S3_ENDPOINT={s3_endpoint}
      - LAKEFS_BLOCKSTORE_S3_FORCE_PATH_STYLE={force_path_style}
      - LAKEFS_BLOCKSTORE_S3_CREDENTIALS_ACCESS_KEY_ID={config['s3_access_key']}
      - LAKEFS_BLOCKSTORE_S3_CREDENTIALS_SECRET_ACCESS_KEY={config['s3_secret_key']}
      - LAKEFS_BLOCKSTORE_S3_REGION={s3_region}
      - LAKEFS_AUTH_ENCRYPT_SECRET_KEY={config['lakefs_encrypt_key']}
      - LAKEFS_LOGGING_FORMAT=text
      - LAKEFS_LISTEN_ADDRESS=0.0.0.0:28000
    ports:
      - "28000:28000"   # LakeFS admin UI (optional)
    user: "${{UID}}:${{GID}}"
{depends_on_str}    volumes:
{volumes_config}
{lakefs_networks_str}"""


def generate_hub_api_service(config: dict) -> str:
    """Generate hub-api service configuration."""
    depends_on = ["lakefs"]

    if config["postgres_builtin"]:
        depends_on.insert(0, "postgres")

    if config["s3_builtin"]:
        depends_on.append("minio")

    depends_on_str = "    depends_on:\n"
    for dep in depends_on:
        depends_on_str += f"      - {dep}\n"

    # Add external network if needed (for external postgres or s3)
    networks_str = ""
    if config.get("external_network") and (
        not config["postgres_builtin"] or not config["s3_builtin"]
    ):
        networks_str = f"""    networks:
      - default
      - {config['external_network']}
"""

    # Database configuration
    if config["postgres_builtin"]:
        db_url = f"postgresql://{config['postgres_user']}:{config['postgres_password']}@postgres:5432/{config['postgres_db']}"
    else:
        db_url = f"postgresql://{config['postgres_user']}:{config['postgres_password']}@{config['postgres_host']}:{config['postgres_port']}/{config['postgres_db']}"

    # S3 configuration
    if config["s3_builtin"]:
        s3_endpoint_internal = "http://minio:9000"
        s3_endpoint_public = "http://127.0.0.1:29001"
        s3_region = "auto"
        # MinIO: Don't set signature_version (uses default/s3v2-compatible)
        s3_sig_version_line = "      # - KOHAKU_HUB_S3_SIGNATURE_VERSION=s3v4  # Uncomment for R2/AWS S3 (leave commented for MinIO)"
    else:
        s3_endpoint_internal = config["s3_endpoint"]
        s3_endpoint_public = config["s3_endpoint"]
        s3_region = config.get("s3_region", "auto")
        # External S3: Use configured value or default to s3v4
        s3_sig_version = config.get("s3_signature_version", "s3v4")
        if s3_sig_version:
            s3_sig_version_line = (
                f"      - KOHAKU_HUB_S3_SIGNATURE_VERSION={s3_sig_version}"
            )
        else:
            s3_sig_version_line = (
                "      # - KOHAKU_HUB_S3_SIGNATURE_VERSION=s3v4  # Uncomment if needed"
            )

    return f"""  hub-api:
    build: .
    container_name: hub-api
    restart: always
    ports:
      - "48888:48888" # Internal API port (optional, for debugging)
{depends_on_str}    environment:
      ## ===== CRITICAL: Endpoint Configuration (MUST CHANGE) =====
      ## These determine how users access your KohakuHub instance
      - KOHAKU_HUB_BASE_URL=http://127.0.0.1:28080 # Change to your public URL (e.g., https://hub.example.com)
      - KOHAKU_HUB_S3_PUBLIC_ENDPOINT={s3_endpoint_public} # Change to your S3 public URL

      ## ===== CRITICAL: Security Configuration (MUST CHANGE) =====
      - KOHAKU_HUB_SESSION_SECRET={config['session_secret']}
      - KOHAKU_HUB_ADMIN_SECRET_TOKEN={config['admin_secret']}

      ## ===== Performance Configuration =====
      - KOHAKU_HUB_WORKERS=4 # Number of worker processes (1-8, recommend: CPU cores)

      ## ===== Database Configuration =====
      - KOHAKU_HUB_DB_BACKEND=postgres
      - KOHAKU_HUB_DATABASE_URL={db_url}

      ## ===== S3 Storage Configuration =====
      - KOHAKU_HUB_S3_ENDPOINT={s3_endpoint_internal}
      - KOHAKU_HUB_S3_ACCESS_KEY={config['s3_access_key']}
      - KOHAKU_HUB_S3_SECRET_KEY={config['s3_secret_key']}
      - KOHAKU_HUB_S3_BUCKET=hub-storage
      - KOHAKU_HUB_S3_REGION={s3_region}  # auto (recommended), us-east-1, or your AWS region
{s3_sig_version_line}

      ## ===== LakeFS Configuration =====
      - KOHAKU_HUB_LAKEFS_ENDPOINT=http://lakefs:28000
      - KOHAKU_HUB_LAKEFS_REPO_NAMESPACE=hf
      # LakeFS credentials auto-generated on first start

      ## ===== Application Configuration =====
      - KOHAKU_HUB_SITE_NAME=KohakuHub
      - KOHAKU_HUB_LFS_THRESHOLD_BYTES=1000000
      - KOHAKU_HUB_LFS_KEEP_VERSIONS=5
      - KOHAKU_HUB_LFS_AUTO_GC=true
      - KOHAKU_HUB_AUTO_MIGRATE=true # Auto-confirm database migrations (required for Docker)

      ## ===== Auth & SMTP Configuration =====
      - KOHAKU_HUB_REQUIRE_EMAIL_VERIFICATION=false
      - KOHAKU_HUB_INVITATION_ONLY=false # Set to true to require invitation for registration
      - KOHAKU_HUB_SESSION_EXPIRE_HOURS=168
      - KOHAKU_HUB_TOKEN_EXPIRE_DAYS=365
      - KOHAKU_HUB_ADMIN_ENABLED=true
      # SMTP (Optional - for email verification)
      - KOHAKU_HUB_SMTP_ENABLED=false
      - KOHAKU_HUB_SMTP_HOST=smtp.gmail.com
      - KOHAKU_HUB_SMTP_PORT=587
      - KOHAKU_HUB_SMTP_USERNAME=
      - KOHAKU_HUB_SMTP_PASSWORD=
      - KOHAKU_HUB_SMTP_FROM=noreply@kohakuhub.local
      - KOHAKU_HUB_SMTP_TLS=true

      ## ===== Storage Quota Configuration (Optional) =====
      - KOHAKU_HUB_DEFAULT_USER_PRIVATE_QUOTA_BYTES=10_000_000
      - KOHAKU_HUB_DEFAULT_USER_PUBLIC_QUOTA_BYTES=100_000_000
      - KOHAKU_HUB_DEFAULT_ORG_PRIVATE_QUOTA_BYTES=10_000_000
      - KOHAKU_HUB_DEFAULT_ORG_PUBLIC_QUOTA_BYTES=100_000_000
    volumes:
      - ./hub-meta/hub-api:/hub-api-creds
{networks_str}"""


def generate_hub_ui_service() -> str:
    """Generate hub-ui service configuration."""
    return """  hub-ui:
    image: nginx:alpine
    container_name: hub-ui
    restart: always
    ports:
      - "28080:80" # Public web interface
    volumes:
      - ./src/kohaku-hub-ui/dist:/usr/share/nginx/html
      - ./src/kohaku-hub-admin/dist:/usr/share/nginx/html-admin
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - hub-api
"""


def generate_docker_compose(config: dict) -> str:
    """Generate the complete docker-compose.yml content."""
    services = []

    # Add services in order
    services.append(generate_hub_ui_service())
    services.append(generate_hub_api_service(config))

    if config["s3_builtin"]:
        services.append(generate_minio_service(config))

    services.append(generate_lakefs_service(config))

    if config["postgres_builtin"]:
        services.append(generate_postgres_service(config))

    content = """# docker-compose.yml - KohakuHub Configuration
# Generated by KohakuHub docker-compose generator
# Customize for your deployment

services:
"""
    content += "\n".join(services)

    # Network configuration
    content += "\nnetworks:\n  default:\n    name: hub-net\n"

    # Add external network if specified
    if config.get("external_network"):
        content += f"""  {config['external_network']}:
    external: true
"""

    return content


def load_config_file(config_path: Path) -> dict:
    """Load configuration from INI file."""
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    config = {}

    # PostgreSQL section
    if parser.has_section("postgresql"):
        pg = parser["postgresql"]
        config["postgres_builtin"] = pg.getboolean("builtin", fallback=True)
        config["postgres_host"] = pg.get("host", fallback="postgres")
        config["postgres_port"] = pg.getint("port", fallback=5432)
        config["postgres_user"] = pg.get("user", fallback="hub")
        config["postgres_password"] = pg.get("password", fallback="hubpass")
        config["postgres_db"] = pg.get("database", fallback="kohakuhub")
    else:
        config["postgres_builtin"] = True
        config["postgres_user"] = "hub"
        config["postgres_password"] = "hubpass"
        config["postgres_db"] = "kohakuhub"
        config["postgres_host"] = "postgres"
        config["postgres_port"] = 5432

    # LakeFS section
    if parser.has_section("lakefs"):
        lakefs = parser["lakefs"]
        config["lakefs_use_postgres"] = lakefs.getboolean("use_postgres", fallback=True)
        config["lakefs_db"] = lakefs.get("database", fallback="lakefs")
        config["lakefs_encrypt_key"] = lakefs.get(
            "encrypt_key", fallback=generate_secret(32)  # 43 chars
        )
    else:
        config["lakefs_use_postgres"] = True
        config["lakefs_db"] = "lakefs"
        config["lakefs_encrypt_key"] = generate_secret(32)  # 43 chars

    # S3 section
    if parser.has_section("s3"):
        s3 = parser["s3"]
        config["s3_builtin"] = s3.getboolean("builtin", fallback=True)
        config["s3_endpoint"] = s3.get("endpoint", fallback="http://minio:9000")
        config["s3_access_key"] = s3.get(
            "access_key", fallback=generate_secret(24)
        )  # 32 chars
        config["s3_secret_key"] = s3.get(
            "secret_key", fallback=generate_secret(48)
        )  # 64 chars
        config["s3_region"] = s3.get("region", fallback="auto")
        config["s3_signature_version"] = s3.get(
            "signature_version", fallback="" if config["s3_builtin"] else "s3v4"
        )  # Empty for MinIO (default), s3v4 for R2/AWS S3
    else:
        config["s3_builtin"] = True
        config["s3_endpoint"] = "http://minio:9000"
        config["s3_access_key"] = generate_secret(24)  # 32 chars
        config["s3_secret_key"] = generate_secret(48)  # 64 chars
        config["s3_region"] = "auto"
        config["s3_signature_version"] = ""  # Empty for MinIO (default)

    # Security section
    if parser.has_section("security"):
        sec = parser["security"]
        config["session_secret"] = sec.get(
            "session_secret", fallback=generate_secret(48)
        )  # 64 chars
        config["admin_secret"] = sec.get(
            "admin_secret", fallback=generate_secret(48)
        )  # 64 chars
    else:
        config["session_secret"] = generate_secret(48)  # 64 chars
        config["admin_secret"] = generate_secret(48)  # 64 chars

    # Network section
    if parser.has_section("network"):
        net = parser["network"]
        config["external_network"] = net.get("external_network", fallback="")
    else:
        config["external_network"] = ""

    return config


def generate_config_template(output_path: Path):
    """Generate a template configuration file."""
    template = """# KohakuHub Configuration Template
# Use this file to automate docker-compose.yml generation
# Usage: python scripts/generate_docker_compose.py --config kohakuhub.conf

[postgresql]
# Use built-in PostgreSQL container (true) or external server (false)
builtin = true

# If builtin = false, specify connection details:
# host = your-postgres-host.com
# port = 5432

# PostgreSQL credentials
user = hub
password = hubpass
database = kohakuhub

[lakefs]
# Use PostgreSQL for LakeFS (true) or SQLite (false)
use_postgres = true

# LakeFS database name (separate from hub-api database)
database = lakefs

# LakeFS encryption key (auto-generated if not specified)
# encrypt_key = your-secret-key-here

[s3]
# Use built-in MinIO container (true) or external S3 (false)
builtin = true

# If builtin = false, specify S3 endpoint and credentials:
# endpoint = https://your-s3-endpoint.com
# access_key = your-access-key
# secret_key = your-secret-key
# region = auto  # auto (recommended), us-east-1, or your AWS region
# signature_version = s3v4  # s3v4 for R2/AWS S3, leave empty for MinIO

# If builtin = true, MinIO credentials are auto-generated (recommended)
# You can override by uncommenting and setting custom values:
# access_key = your-custom-access-key
# secret_key = your-custom-secret-key
# region = auto
# signature_version =  # Leave empty for MinIO (uses default)

[security]
# Session and admin secrets (auto-generated if not specified)
# session_secret = your-session-secret-here
# admin_secret = your-admin-secret-here

[network]
# External bridge network (optional)
# Use this if PostgreSQL or S3 are in different Docker Compose setups
# Create the network first: docker network create shared-network
# external_network = shared-network
"""

    output_path.write_text(template, encoding="utf-8")
    print(f"[OK] Generated configuration template: {output_path}")
    print()
    print("Edit this file with your settings, then run:")
    print(f"  python scripts/generate_docker_compose.py --config {output_path}")


def main():
    """Main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Generate docker-compose.yml for KohakuHub"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Path to configuration file (kohakuhub.conf)",
    )
    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Generate a template configuration file",
    )
    args = parser.parse_args()

    # Generate template if requested
    if args.generate_config:
        template_path = Path(__file__).parent.parent / "kohakuhub.conf"
        generate_config_template(template_path)
        return

    print("=" * 60)
    print("KohakuHub Docker Compose Generator")
    print("=" * 60)
    print()

    # Load config from file if provided
    if args.config:
        print(f"Loading configuration from: {args.config}")
        print()
        config = load_config_file(args.config)
        # Show loaded configuration
        print("Loaded configuration:")
        print(
            f"  PostgreSQL: {'Built-in' if config['postgres_builtin'] else 'External'}"
        )
        if not config["postgres_builtin"]:
            print(f"    Host: {config['postgres_host']}:{config['postgres_port']}")
        print(f"    Database: {config['postgres_db']}")
        print(
            f"  LakeFS: {'PostgreSQL' if config['lakefs_use_postgres'] else 'SQLite'}"
        )
        if config["lakefs_use_postgres"]:
            print(f"    Database: {config['lakefs_db']}")
        print(f"  S3: {'Built-in MinIO' if config['s3_builtin'] else 'External S3'}")
        if not config["s3_builtin"]:
            print(f"    Endpoint: {config['s3_endpoint']}")
        print()
    else:
        # Interactive mode
        config = interactive_config()

    # Generate and write files
    generate_and_write_files(config)


def interactive_config() -> dict:
    """Run interactive configuration."""
    config = {}

    # PostgreSQL Configuration
    print("--- PostgreSQL Configuration ---")
    config["postgres_builtin"] = ask_yes_no(
        "Use built-in PostgreSQL container?", default=True
    )

    if config["postgres_builtin"]:
        config["postgres_user"] = ask_string("PostgreSQL username", default="hub")
        config["postgres_password"] = ask_string(
            "PostgreSQL password", default="hubpass"
        )
        config["postgres_db"] = ask_string(
            "PostgreSQL database name for hub-api", default="kohakuhub"
        )
        config["postgres_host"] = "postgres"
        config["postgres_port"] = 5432
    else:
        config["postgres_host"] = ask_string("PostgreSQL host")
        config["postgres_port"] = ask_int("PostgreSQL port", default=5432)
        config["postgres_user"] = ask_string("PostgreSQL username")
        config["postgres_password"] = ask_string("PostgreSQL password")
        config["postgres_db"] = ask_string(
            "PostgreSQL database name for hub-api", default="kohakuhub"
        )

    # LakeFS database configuration
    print()
    print("--- LakeFS Database Configuration ---")
    config["lakefs_use_postgres"] = ask_yes_no(
        "Use PostgreSQL for LakeFS? (No = use local SQLite)", default=True
    )

    if config["lakefs_use_postgres"]:
        config["lakefs_db"] = ask_string(
            "PostgreSQL database name for LakeFS", default="lakefs"
        )
    else:
        config["lakefs_db"] = None

    print()

    # S3 Configuration
    print("--- S3 Storage Configuration ---")
    config["s3_builtin"] = ask_yes_no("Use built-in MinIO container?", default=True)

    if config["s3_builtin"]:
        # Generate secure random credentials for MinIO
        default_access_key = generate_secret(24)  # 32 chars
        default_secret_key = generate_secret(48)  # 64 chars

        print(f"Generated MinIO access key: {default_access_key}")
        print(f"Generated MinIO secret key: {default_secret_key}")
        use_generated = ask_yes_no("Use generated MinIO credentials?", default=True)

        if use_generated:
            config["s3_access_key"] = default_access_key
            config["s3_secret_key"] = default_secret_key
        else:
            config["s3_access_key"] = ask_string("MinIO access key")
            config["s3_secret_key"] = ask_string("MinIO secret key")

        config["s3_endpoint"] = "http://minio:9000"
        config["s3_region"] = "auto"
        config["s3_signature_version"] = ""  # MinIO uses default (don't set)
    else:
        config["s3_endpoint"] = ask_string("S3 endpoint URL")
        config["s3_access_key"] = ask_string("S3 access key")
        config["s3_secret_key"] = ask_string("S3 secret key")
        config["s3_region"] = ask_string("S3 region", default="auto")

        # Ask about signature version for external S3
        print()
        print("Signature version:")
        print("  - (empty): Use default (for MinIO compatibility)")
        print("  - s3v4: Cloudflare R2, AWS S3 (recommended for R2/AWS)")
        sig_input = ask_string(
            "S3 signature version (s3v4 or leave empty)", default="s3v4"
        )
        config["s3_signature_version"] = (
            sig_input if sig_input.lower() != "none" else ""
        )

    print()

    # Security Configuration
    print("--- Security Configuration ---")
    default_session_secret = generate_secret(48)  # 64 chars for session encryption
    print(f"Generated session secret: {default_session_secret}")
    use_generated = ask_yes_no("Use generated session secret?", default=True)

    if use_generated:
        config["session_secret"] = default_session_secret
    else:
        config["session_secret"] = ask_string("Session secret key")

    print()
    same_as_session = ask_yes_no("Use same secret for admin token?", default=False)

    if same_as_session:
        config["admin_secret"] = config["session_secret"]
    else:
        default_admin_secret = generate_secret(48)  # 64 chars for admin token
        print(f"Generated admin secret: {default_admin_secret}")
        use_generated_admin = ask_yes_no("Use generated admin secret?", default=True)

        if use_generated_admin:
            config["admin_secret"] = default_admin_secret
        else:
            config["admin_secret"] = ask_string("Admin secret token")

    # LakeFS encryption key
    config["lakefs_encrypt_key"] = generate_secret(32)  # 43 chars

    # Network configuration
    print()
    print("--- Network Configuration ---")
    use_external_network = False
    if not config["postgres_builtin"] or not config["s3_builtin"]:
        use_external_network = ask_yes_no(
            "Use external Docker network for cross-compose communication?",
            default=False,
        )

    if use_external_network:
        config["external_network"] = ask_string(
            "External network name", default="shared-network"
        )
        print()
        print(f"Note: Make sure the network exists:")
        print(f"  docker network create {config['external_network']}")
    else:
        config["external_network"] = ""

    return config


def generate_and_write_files(config: dict):
    """Generate and write docker-compose.yml and related files."""
    print()
    print("=" * 60)
    print("Generating docker-compose.yml...")
    print("=" * 60)

    # Generate docker-compose content
    content = generate_docker_compose(config)

    # Write to file
    output_path = Path(__file__).parent.parent / "docker-compose.yml"
    output_path.write_text(content, encoding="utf-8")

    print()
    print(f"[OK] Successfully generated: {output_path}")

    if config["lakefs_use_postgres"]:
        print(
            "[OK] Database initialization scripts will run automatically when LakeFS starts"
        )
        print("     - scripts/init-databases.sh")
        print("     - scripts/lakefs-entrypoint.sh")
    print()
    print("Configuration Summary:")
    print("-" * 60)
    print(f"PostgreSQL: {'Built-in' if config['postgres_builtin'] else 'Custom'}")
    if config["postgres_builtin"]:
        print(f"  Hub-API Database: {config['postgres_db']}")
        if config["lakefs_use_postgres"]:
            print(f"  LakeFS Database: {config['lakefs_db']}")
    else:
        print(f"  Host: {config['postgres_host']}:{config['postgres_port']}")
        print(f"  Hub-API Database: {config['postgres_db']}")
        if config["lakefs_use_postgres"]:
            print(f"  LakeFS Database: {config['lakefs_db']}")
    print(
        f"LakeFS Database Backend: {'PostgreSQL' if config['lakefs_use_postgres'] else 'SQLite'}"
    )
    print(f"S3 Storage: {'Built-in MinIO' if config['s3_builtin'] else 'Custom S3'}")
    if not config["s3_builtin"]:
        print(f"  Endpoint: {config['s3_endpoint']}")
    if config.get("external_network"):
        print(f"External Network: {config['external_network']}")
    print(f"Session Secret: {config['session_secret'][:20]}...")
    print(f"Admin Secret: {config['admin_secret'][:20]}...")
    print("-" * 60)
    print()
    print("Next steps:")
    step_num = 1

    if config.get("external_network"):
        print(f"{step_num}. Create external network if not exists:")
        print(f"   docker network create {config['external_network']}")
        step_num += 1
        print()

    print(f"{step_num}. Review the generated docker-compose.yml")
    step_num += 1
    print(f"{step_num}. Build frontend: npm run build --prefix ./src/kohaku-hub-ui")
    step_num += 1
    print(f"{step_num}. Start services: docker-compose up -d")
    print()
    if config["lakefs_use_postgres"]:
        print("   Note: Databases will be created automatically on first startup:")
        print(f"   - {config['postgres_db']} (hub-api)")
        print(f"   - {config['lakefs_db']} (LakeFS)")
        print()
    step_num += 1
    print(f"{step_num}. Access at: http://localhost:28080")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)
