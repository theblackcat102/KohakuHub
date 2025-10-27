# KohakuBoard Deployment Scripts

Quick reference for deploying KohakuBoard.

---

## 🚀 Quick Start: CLI Commands (Recommended)

### Local Mode (No Auth, No Docker)

```bash
kobo open ./kohakuboard
```

Browse local boards without authentication. Perfect for development.

### Remote Mode (With Auth, No Docker)

```bash
# Development with auto-reload
kobo serve --reload

# Production with PostgreSQL
kobo serve --db postgresql://user:pass@localhost/kohakuboard \
           --db-backend postgres \
           --workers 4 \
           --session-secret $(openssl rand -hex 32)
```

Lightweight server with authentication. Works for both testing and production.

**Access:** http://localhost:48889

---

## 📜 Legacy: Python Scripts

These scripts are kept for backward compatibility. **Use CLI commands instead.**

### Test Server Script

```bash
python scripts/test_server_board.py
```

Equivalent to: `kobo serve --reload`

**Stop:** Press `Ctrl+C`

---

## 📦 Standalone Docker Deployment (Recommended)

**Fully standalone KohakuBoard with Docker (no KohakuHub needed):**

```bash
python scripts/deploy_board.py
```

**What you get:**
- ✅ Full Docker deployment
- ✅ Production-ready (with PostgreSQL option)
- ✅ Default: SQLite mode (easy setup)
- ✅ Completely independent from KohakuHub

**Access:**
- Web UI: http://localhost:28081
- API Docs: http://localhost:48889/api/docs

**Configuration:**
- Edit `docker-compose.kohakuboard.yml` before deploying
- Change `KOHAKU_BOARD_AUTH_SESSION_SECRET` to a random value
- Choose SQLite (default) or PostgreSQL (uncomment postgres-board service)

**Stop:**
```bash
docker-compose -f docker-compose.kohakuboard.yml down
```

---

## 🔗 Integrated with KohakuHub (OPTIONAL)

**Only use this if you want SSO (single sign-on) with KohakuHub:**

```bash
python scripts/deploy_board_integrated.py
```

**What you get:**
- ✅ Shared user accounts with KohakuHub
- ✅ Single sign-on (login once, access both)
- ✅ Shared organizations
- ⚠️ Requires matching session secrets

**Configuration:**
- Edit `docker-compose.board-integrated.yml`
- **CRITICAL:** Set `KOHAKU_BOARD_AUTH_SESSION_SECRET` to **SAME** value as `KOHAKU_HUB_SESSION_SECRET`
- Ensure database URL matches KohakuHub's PostgreSQL

**Stop:**
```bash
docker-compose -f docker-compose.board-integrated.yml down
```

---

## Comparison

| Method | Use Case | Database | Docker | Auth | Reload |
|--------|----------|----------|--------|------|--------|
| **kobo open** | Local browsing | ❌ None | ❌ No | ❌ No | ❌ No |
| **kobo serve --reload** | Development | SQLite | ❌ No | ✅ Yes | ✅ Yes |
| **kobo serve --workers 4** | Production (no Docker) | SQLite/PostgreSQL | ❌ No | ✅ Yes | ❌ No |
| **deploy_board.py** | Production (Docker) | SQLite/PostgreSQL | ✅ Yes | ✅ Yes | ❌ No |
| **deploy_board_integrated.py** | SSO with KohakuHub | Shared PostgreSQL | ✅ Yes | ✅ Yes (SSO) | ❌ No |

---

## Recommendations

- **Local browsing:** Use `kobo open ./kohakuboard`
- **Development/Testing:** Use `kobo serve --reload`
- **Production (no Docker):** Use `kobo serve --workers 4 --db postgresql://...`
- **Production (with Docker):** Use `python scripts/deploy_board.py`
- **SSO with KohakuHub:** Use `python scripts/deploy_board_integrated.py` (OPTIONAL)

---

## Full Documentation

See `docs/KOHAKUBOARD_DEPLOYMENT.md` for detailed instructions.
