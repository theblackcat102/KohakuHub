# KohakuBoard Quick Start

**KohakuBoard** is a fully standalone ML experiment tracking platform.

---

## 🏃 Fastest Way to Start

### Local Mode (No Auth)
```bash
kobo open ./kohakuboard
```
→ Opens at http://localhost:48889

### Remote Mode (With Auth)
```bash
kobo serve --reload
```
→ Opens at http://localhost:48889 (register/login required)

---

## 📝 CLI Commands

### `kobo open` - Local Browsing
```bash
kobo open ./kohakuboard [--port 48889] [--no-browser]
```
- ❌ No authentication
- ❌ No database
- ✅ Browse local boards
- ✅ Perfect for development

### `kobo serve` - Remote Server
```bash
# Development
kobo serve --reload

# Production (SQLite)
kobo serve --workers 4 --session-secret <random>

# Production (PostgreSQL)
kobo serve --db postgresql://user:pass@host/db \
           --db-backend postgres \
           --workers 4 \
           --session-secret <random>
```
- ✅ Authentication enabled
- ✅ SQLite or PostgreSQL
- ✅ Multi-worker support
- ✅ Auto-reload option
- ✅ Production-ready

**Options:**
- `--host` - Server host (default: 0.0.0.0)
- `--port` - Server port (default: 48889)
- `--data-dir` - Data directory (default: ./kohakuboard)
- `--db` - Database URL (default: sqlite:///kohakuboard.db)
- `--db-backend` - sqlite or postgres (default: sqlite)
- `--reload` - Enable auto-reload (development)
- `--workers` - Worker count (default: 1, use 4+ for production)
- `--session-secret` - Session secret (required for production)
- `--no-browser` - Don't auto-open browser

---

## 🐳 Docker Deployment

### Standalone (Recommended)
```bash
python scripts/deploy_board.py
```
→ http://localhost:28081

### Integrated with KohakuHub (OPTIONAL)
```bash
python scripts/deploy_board_integrated.py
```
→ KohakuHub: http://localhost:28080
→ KohakuBoard: http://localhost:28081

**Note:** Integration is OPTIONAL. KohakuBoard is fully standalone.

---

## 🎯 When to Use What

| Need | Command |
|------|---------|
| Browse local files | `kobo open ./kohakuboard` |
| Test with auth | `kobo serve --reload` |
| Production (simple) | `kobo serve --workers 4` |
| Production (Docker) | `python scripts/deploy_board.py` |
| SSO with KohakuHub | `python scripts/deploy_board_integrated.py` |

---

## 📚 Full Documentation

- **Deployment Guide:** `docs/KOHAKUBOARD_DEPLOYMENT.md`
- **Scripts Reference:** `scripts/README_KOHAKUBOARD.md`
- **Implementation Details:** `.claude/summaries/2025-10-kohakuboard-remote-mode.md`

---

## ⚡ Quick Examples

### Example 1: Development
```bash
# Start local server for browsing
kobo open ./kohakuboard

# Start remote server with auth (auto-reload)
kobo serve --reload
```

### Example 2: Production (No Docker)
```bash
# Generate session secret
openssl rand -hex 32

# Start production server
kobo serve --db postgresql://board:pass@localhost/kohakuboard \
           --db-backend postgres \
           --workers 4 \
           --session-secret <paste-secret-here>
```

### Example 3: Docker Production
```bash
# Build and deploy
python scripts/deploy_board.py

# View logs
docker-compose -f docker-compose.kohakuboard.yml logs -f

# Stop
docker-compose -f docker-compose.kohakuboard.yml down
```

---

## 🔐 Security Notes

**For Production:**
1. ✅ Generate random session secret: `openssl rand -hex 32`
2. ✅ Use PostgreSQL (not SQLite)
3. ✅ Use HTTPS reverse proxy (nginx, Caddy, Traefik)
4. ✅ Strong database passwords
5. ✅ Only expose port 28081 (UI), not 48889 (API)

**Default values are UNSAFE for production!**

---

## 🆘 Troubleshooting

**"Authentication required" in local mode:**
- You're using `kobo serve` instead of `kobo open`
- Use `kobo open` for local browsing without auth

**Database connection error:**
- Check database URL is correct
- For PostgreSQL: ensure database exists and is accessible
- For SQLite: ensure directory is writable

**"No projects found" after login:**
- Projects are user-specific in remote mode
- Create a project first or sync existing boards

---

**Need help?** See full docs in `docs/KOHAKUBOARD_DEPLOYMENT.md`
