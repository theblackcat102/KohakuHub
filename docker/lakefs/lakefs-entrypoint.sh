#!/bin/sh
# LakeFS entrypoint wrapper
# Runs database initialization before starting LakeFS

set -e

# Install PostgreSQL client if not available (for database initialization)
if ! command -v psql >/dev/null 2>&1; then
    echo "Installing PostgreSQL client..."
    if apk --version >/dev/null 2>&1; then
        # Alpine Linux
        apk add --no-cache postgresql-client >/dev/null 2>&1 || echo "⚠ Failed to install psql via apk"
    elif apt-get --version >/dev/null 2>&1; then
        # Debian/Ubuntu
        apt-get update >/dev/null 2>&1 && apt-get install -y postgresql-client >/dev/null 2>&1 || echo "⚠ Failed to install psql via apt"
    else
        echo "⚠ Unknown package manager, cannot install psql"
    fi
fi

# Run database initialization if PostgreSQL is configured and script exists
if [ -f /scripts/init-databases.sh ]; then
    if command -v psql >/dev/null 2>&1; then
        echo "Running database initialization..."
        sh /scripts/init-databases.sh || echo "Database initialization failed (continuing anyway)"
    else
        echo "psql not available, skipping database initialization"
        echo "  Please ensure databases exist manually:"
        echo "  - ${POSTGRES_DB:-kohakuhub}"
        echo "  - ${LAKEFS_DB:-lakefs}"
    fi
else
    echo "/scripts/init-databases.sh not found, skipping database initialization"
fi

# Start LakeFS with original command
echo "Starting LakeFS..."
exec /app/lakefs "$@"
