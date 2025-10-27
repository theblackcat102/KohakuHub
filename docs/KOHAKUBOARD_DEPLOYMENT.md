# KohakuBoard Deployment Guide

KohakuBoard is an ML experiment tracking and visualization platform. It supports three deployment modes:

1. **Local Mode** - No authentication, filesystem-only (development)
2. **Remote Mode (Standalone)** - With authentication, SQLite or PostgreSQL
3. **Remote Mode (Integrated)** - Shares KohakuHub's database for unified accounts (SSO)

---

## Quick Start: Local Mode (No Auth, No Docker)

Browse local board files without authentication:

```bash
# Start local server
kobo open ./kohakuboard
```

**What this does:**
- Opens local board directory
- No authentication required
- No database needed
- Auto-opens browser

**Access:** http://localhost:48889

**Stop:** Press `Ctrl+C`

---

## Quick Start: Remote Server (With Auth, No Docker)

For testing or production with authentication enabled:

```bash
# Development with auto-reload (SQLite)
kobo serve --reload

# Production with PostgreSQL
kobo serve --db postgresql://user:pass@localhost/kohakuboard \
           --db-backend postgres \
           --workers 4 \
           --session-secret $(openssl rand -hex 32)
```

**What this does:**
- Mode: `remote`
- Database: SQLite or PostgreSQL (your choice)
- Port: `48889` (customizable)
- Authentication: ✅ Enabled
- No Docker required
- Perfect for both testing AND production

**Access:**
- Web UI: http://localhost:48889
- API Docs: http://localhost:48889/api/docs

**Test workflow:**
1. Run `kobo serve --reload`
2. Open http://localhost:48889
3. Click "Sign Up" and register
4. Login and create projects

**Stop:** Press `Ctrl+C`

### CLI Options

```
kobo serve [OPTIONS]

Options:
  --host TEXT              Server host (default: 0.0.0.0)
  --port INTEGER           Server port (default: 48889)
  --data-dir TEXT          Board data directory (default: ./kohakuboard)
  --db TEXT                Database URL (default: sqlite:///kohakuboard.db)
  --db-backend [sqlite|postgres]  Database backend (default: sqlite)
  --reload                 Enable auto-reload for development
  --workers INTEGER        Number of worker processes (default: 1)
  --session-secret TEXT    Session secret (required in production)
  --no-browser            Do not open browser automatically
```

---

## Deployment Option 1: Standalone Docker (Recommended)

Deploy KohakuBoard as a standalone application with its own database.

### Prerequisites

- Docker and Docker Compose installed
- Node.js 18+ (for building frontend)

### Configuration Options

The standalone deployment supports two database modes:

#### Option A: SQLite (Default, for testing)
- Easiest setup
- Single-file database
- Good for development and small deployments
- Limited concurrent access

#### Option B: PostgreSQL (Production)
- Better performance
- Better concurrent access
- Recommended for production

### Deployment Steps

**1. Choose your database mode:**

**For SQLite (default):**
```bash
# No changes needed - SQLite is default in docker-compose.kohakuboard.yml
```

**For PostgreSQL:**
```bash
# Edit docker-compose.kohakuboard.yml
# Uncomment the postgres-board service
# Uncomment the depends_on line in board-api
# Update environment variables in board-api:
#   - KOHAKU_BOARD_DB_BACKEND=postgres
#   - KOHAKU_BOARD_DATABASE_URL=postgresql://board:boardpass@postgres-board:5432/kohakuboard
```

**2. Configure secrets (IMPORTANT):**

Edit `docker-compose.kohakuboard.yml` and change:
- `KOHAKU_BOARD_AUTH_SESSION_SECRET` - Use a random string (generate with `openssl rand -hex 32`)
- Database password (if using PostgreSQL)

**3. Deploy:**

```bash
python scripts/deploy_board.py
```

This script will:
1. Install frontend dependencies
2. Build frontend
3. Start Docker services

**4. Access:**

- **Web UI:** http://localhost:28081
- **API Docs:** http://localhost:48889/api/docs

**5. Manage services:**

```bash
# View logs
docker-compose -f docker-compose.kohakuboard.yml logs -f

# Stop services
docker-compose -f docker-compose.kohakuboard.yml down

# Restart services
docker-compose -f docker-compose.kohakuboard.yml restart
```

### First Use

1. Open http://localhost:28081
2. Click "Sign Up" (top right)
3. Create an account
4. Login with your credentials
5. Start creating projects!

---

## Deployment Option 2: Integrated with KohakuHub (SSO) - OPTIONAL

⚠️ **This is COMPLETELY OPTIONAL.**

KohakuBoard is a **fully standalone application**. You do NOT need KohakuHub to use it.

This integration option is ONLY for users who:
- Already have KohakuHub deployed
- Want single sign-on (SSO) between KohakuHub and KohakuBoard
- Want unified user management across both systems

If you just want KohakuBoard, use **Option 1: Standalone Docker** instead.

### What is "Integrated Mode"?

Deploy KohakuBoard to share the same PostgreSQL database with KohakuHub. This enables:
- Same user accounts across both systems
- Login once, access both KohakuHub and KohakuBoard
- Shared organizations and teams

### Prerequisites

**None required!** KohakuBoard is fully standalone.

**Optional:** If you want SSO with KohakuHub:
- KohakuHub should be deployed and running
- You need access to KohakuHub's database credentials

### Benefits

- **Single Sign-On (SSO)**: Login once, access both KohakuHub and KohakuBoard
- **Unified user accounts**: Same users across both systems
- **Shared organizations**: Manage teams in one place
- **Single database**: Easier to manage and backup

### Deployment Steps

**1. Deploy KohakuHub first (if not already deployed):**

```bash
cp docker-compose.example.yml docker-compose.yml
# Edit docker-compose.yml to change passwords and secrets
./deploy.sh
```

**2. Configure KohakuBoard integration:**

Edit `docker-compose.board-integrated.yml`:

- **Match session secret:** Set `KOHAKU_BOARD_AUTH_SESSION_SECRET` to the **SAME** value as KohakuHub's `KOHAKU_HUB_SESSION_SECRET`
  - This enables SSO (shared sessions between systems)

- **Database credentials:** Ensure database URL matches KohakuHub:
  ```
  KOHAKU_BOARD_DATABASE_URL=postgresql://hub:hubpass@postgres:5432/kohakuhub
  ```
  (Must match KohakuHub's database URL)

**3. Deploy KohakuBoard:**

```bash
python scripts/deploy_board_integrated.py
```

**4. Access:**

- **KohakuHub:** http://localhost:28080 (model/dataset hosting)
- **KohakuBoard:** http://localhost:28081 (experiment tracking)
- **API Docs:** http://localhost:48889/api/docs

**5. Test SSO:**

1. Register/login on KohakuHub (http://localhost:28080)
2. Open KohakuBoard (http://localhost:28081) in the same browser
3. You should be automatically logged in! ✨

**6. Manage services:**

```bash
# View KohakuBoard logs
docker-compose -f docker-compose.board-integrated.yml logs -f

# Stop KohakuBoard only (keeps KohakuHub running)
docker-compose -f docker-compose.board-integrated.yml down

# Stop everything (KohakuHub + KohakuBoard)
docker-compose down && docker-compose -f docker-compose.board-integrated.yml down
```

---

## Alternative: Python Scripts (Legacy)

You can also use Python scripts directly (not recommended, use CLI instead):

```bash
# Test server (remote mode, SQLite)
python scripts/test_server_board.py

# Or with environment variables
export KOHAKU_BOARD_MODE=local
python -m kohakuboard.main
```

---

## Configuration Reference

### Environment Variables

All configuration via `KOHAKU_BOARD_*` environment variables:

#### Application
- `KOHAKU_BOARD_MODE` - `local` or `remote` (default: `local`)
- `KOHAKU_BOARD_HOST` - Bind address (default: `0.0.0.0`)
- `KOHAKU_BOARD_PORT` - Port number (default: `48889`)
- `KOHAKU_BOARD_BASE_URL` - Public URL (default: `http://localhost:28081`)
- `KOHAKU_BOARD_BOARD_DATA_DIR` - Data directory (default: `./kohakuboard`)

#### Database (Remote mode only)
- `KOHAKU_BOARD_DB_BACKEND` - `sqlite` or `postgres` (default: `sqlite`)
- `KOHAKU_BOARD_DATABASE_URL` - Connection string
  - SQLite: `sqlite:///kohakuboard.db`
  - PostgreSQL: `postgresql://user:pass@host:5432/dbname`

#### Authentication (Remote mode only)
- `KOHAKU_BOARD_AUTH_SESSION_SECRET` - Session encryption key (**change in production**)
- `KOHAKU_BOARD_AUTH_REQUIRE_EMAIL_VERIFICATION` - `true`/`false` (default: `false`)
- `KOHAKU_BOARD_AUTH_INVITATION_ONLY` - `true`/`false` (default: `false`)
- `KOHAKU_BOARD_AUTH_SESSION_EXPIRE_HOURS` - Session lifetime (default: `168` = 7 days)
- `KOHAKU_BOARD_AUTH_TOKEN_EXPIRE_DAYS` - API token lifetime (default: `365`)

#### SMTP (Optional, for email verification)
- `KOHAKU_BOARD_SMTP_ENABLED` - `true`/`false` (default: `false`)
- `KOHAKU_BOARD_SMTP_HOST` - SMTP server (default: `localhost`)
- `KOHAKU_BOARD_SMTP_PORT` - SMTP port (default: `587`)
- `KOHAKU_BOARD_SMTP_USERNAME` - SMTP username
- `KOHAKU_BOARD_SMTP_PASSWORD` - SMTP password
- `KOHAKU_BOARD_SMTP_FROM` - From email address (default: `noreply@localhost`)
- `KOHAKU_BOARD_SMTP_TLS` - Use TLS (default: `true`)

---

## Comparison: Standalone vs Integrated

| Feature | Standalone | Integrated with KohakuHub |
|---------|-----------|---------------------------|
| **Database** | Own PostgreSQL or SQLite | Shares KohakuHub's PostgreSQL |
| **User accounts** | Independent | Unified with KohakuHub |
| **Single Sign-On** | ❌ No | ✅ Yes |
| **Organizations** | Separate | Shared with KohakuHub |
| **Deployment complexity** | Simple | Requires KohakuHub |
| **Use case** | Standalone ML tracking | Unified AI platform |

---

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| KohakuBoard UI | 28081 | http://localhost:28081 |
| KohakuBoard API | 48889 | http://localhost:48889/api/docs |
| KohakuHub UI | 28080 | http://localhost:28080 |
| KohakuHub API | 48888 | http://localhost:48888/docs |
| PostgreSQL (Board standalone) | 25433 | localhost:25433 |
| PostgreSQL (Hub + Board) | 25432 | localhost:25432 |

---

## Troubleshooting

### "Authentication required" in local mode

**Problem:** Frontend shows "Authentication Required" even in local mode.

**Solution:** Check `/api/system/info` - it should return `{"mode": "local"}`. If not, set `KOHAKU_BOARD_MODE=local` environment variable.

### Database connection error

**Problem:** `peewee.InterfaceError: Query must be bound to a database`

**Solution:** In remote mode, ensure database is initialized:
- SQLite: File path is correct and writable
- PostgreSQL: Connection URL is correct and database exists

### SSO not working (integrated mode)

**Problem:** Logged into KohakuHub but not KohakuBoard (or vice versa)

**Solution:** Ensure `KOHAKU_BOARD_AUTH_SESSION_SECRET` **exactly matches** `KOHAKU_HUB_SESSION_SECRET`

### Frontend shows "No projects found" in remote mode

**Problem:** Projects exist but not visible after login

**Solution:** Check browser console for errors. Ensure:
1. User is authenticated (check `/api/auth/me`)
2. Projects belong to the logged-in user
3. Backend logs show no permission errors

---

## Development Workflow

### Backend Development (Remote mode with auto-reload)

```bash
# Set environment
export KOHAKU_BOARD_MODE=remote
export KOHAKU_BOARD_DB_BACKEND=sqlite
export KOHAKU_BOARD_DATABASE_URL=sqlite:///dev-kohakuboard.db
export KOHAKU_BOARD_AUTH_SESSION_SECRET=dev-secret

# Start with auto-reload
uvicorn kohakuboard.main:app --host 0.0.0.0 --port 48889 --reload
```

### Frontend Development

```bash
# Start dev server (proxies API to localhost:48889)
npm run dev --prefix ./src/kohaku-board-ui

# Access at http://localhost:5175
```

---

## Security Notes

### Production Deployment

**CRITICAL:** Change these values before deploying to production:

1. **Session Secret:** Generate with `openssl rand -hex 32`
2. **Database Password:** Use strong passwords
3. **HTTPS:** Use a reverse proxy (nginx, Caddy, Traefik) with SSL/TLS
4. **Firewall:** Only expose port 28081 (UI), not 48889 (API)

### Default Values (UNSAFE for production)

These are **ONLY for testing**:
- `KOHAKU_BOARD_AUTH_SESSION_SECRET=change-me-in-production`
- Database passwords in docker-compose files

---

## Migration Guide

### From Local to Remote Mode

1. **Backup data:** `cp -r ./kohakuboard ./kohakuboard-backup`
2. **Deploy in remote mode** (see above)
3. **Sync data:** Use the sync API to upload existing boards to remote server

### From Standalone to Integrated

1. **Export users:** Dump SQLite/PostgreSQL users table
2. **Deploy integrated mode** with KohakuHub
3. **Import users:** Insert into KohakuHub's database
4. **Update board ownership:** Update `Board.owner` ForeignKeys

---

## API Endpoints

### Local Mode
- ✅ `/api/system/info` - System information
- ✅ `/api/projects` - List all projects from filesystem
- ✅ `/api/projects/{project}/runs` - List runs
- ✅ `/api/projects/{project}/runs/{run_id}/*` - Run data (scalars, media, tables, histograms)
- ❌ `/api/auth/*` - Not available
- ❌ `/org/*` - Not available

### Remote Mode
- ✅ `/api/system/info` - System information
- ✅ `/api/auth/*` - Authentication (register, login, logout, tokens)
- ✅ `/org/*` - Organizations (create, members)
- ✅ `/api/projects` - List user's projects (requires auth)
- ✅ `/api/projects/{project}/runs` - List user's runs (requires auth)
- ✅ `/api/projects/{project}/runs/{run_id}/*` - Run data (with permission checks)
- ✅ `/api/projects/{project}/sync` - Sync run to server (requires auth)

---

## Client Library Usage

### Local Mode

```python
from kohakuboard import KohakuBoardLogger

# No authentication needed
logger = KohakuBoardLogger(
    name="my-experiment",
    base_url="http://localhost:48889"  # Local server
)

logger.log_scalar("train/loss", 0.5, step=100)
```

### Remote Mode

```python
from kohakuboard import KohakuBoardLogger

# With authentication
logger = KohakuBoardLogger(
    name="my-experiment",
    project="my-project",  # Or "org-name/project" for org projects
    base_url="http://localhost:28081",  # Remote server
    token="your_api_token_here"  # Get from /api/auth/tokens/create
)

logger.log_scalar("train/loss", 0.5, step=100)
logger.sync()  # Upload to server
```

---

## FAQ

**Q: Can I use KohakuBoard without Docker?**
A: Yes! Use `python -m kohakuboard.main` for local mode or `python scripts/test_server_board.py` for remote mode testing.

**Q: Can I migrate from standalone to integrated mode later?**
A: Yes, but requires database migration. See Migration Guide above.

**Q: Does integrated mode require both KohakuHub and KohakuBoard to be running?**
A: No - they're independent services. You can run KohakuBoard alone even in integrated mode (just needs the shared PostgreSQL).

**Q: Can I use different databases for KohakuHub and KohakuBoard?**
A: Yes, but you lose SSO. Use standalone mode instead.

**Q: How do I enable email verification?**
A: Set `KOHAKU_BOARD_AUTH_REQUIRE_EMAIL_VERIFICATION=true` and configure SMTP settings.

---

## Support

- **GitHub:** https://github.com/KohakuBlueleaf/KohakuHub
- **Discord:** https://discord.gg/xWYrkyvJ2s
- **Documentation:** See `docs/` directory
