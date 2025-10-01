# Kohaku Hub: Minimal self-hosted HuggingFace Hub

Kohaku Hub is an experimental, HuggingFace-compatible hub implementation.  
It combines:

- **LakeFS** → Git-like versioning of files  
- **MinIO (S3)** → Object storage backend  
- **FastAPI** → API layer compatible with HuggingFace Hub client  
- **SQLite** → Lightweight metadata and deduplication database  

⚠️ This project is still under active development. Expect incomplete features and frequent changes.

---

## Features (WIP)

- ✅ Repository creation & listing
- ✅ File upload (small files)
- ✅ File download (via presigned URLs)
- ✅ Tree listing & revision metadata
- ⚠️ Large file upload (Git LFS) – partially implemented
- ⚠️ User auth & organizations – not yet implemented
- ⚠️ Web UI – not yet implemented

For detailed API workflow, see [API.md](./API.md).

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/KohakuBlueleaf/Kohaku-Hub.git
cd Kohaku-Hub
python -m pip install -e .[dev]
````

### 2. Launch dependencies with Docker Compose

This spins up **MinIO** and **LakeFS** under a local network.

```bash
docker compose up -d
```

Services:

* MinIO S3 API → `http://127.0.0.1:29001`
* MinIO Console → `http://127.0.0.1:29000`
* LakeFS Web + API → `http://127.0.0.1:28000`

### 3. Configure the app

Copy the example config and adjust as needed:

```bash
cp config-example.toml config.toml
```

At minimum, ensure:

* `s3.public_endpoint` / `s3.endpoint`
* `lakefs.endpoint`
* `app.base_url` / `app.db_backend` / `app.database_url`

### 4. Run the API server

For development:

```bash
uvicorn kohakuhub.main:app --reload --port 48888
```

Now your hub API is available at `http://127.0.0.1:48888`.

### 5. Test with HuggingFace Hub client

A sample script is included in [`test.py`](./test.py):

```bash
python test.py
```

This will:

* Create a test repo (`kohaku/test-2`)
* Upload a folder with random content + README file
* Download them back and print content
* delete the folder with random content

---

## Development Notes

* Config format: [TOML](./config-example.toml)
* Dependencies: see [pyproject.toml](./pyproject.toml)
* Database: SQLite (auto-initialized on startup) / PostgreSQL (docker-compose)
* Auth: currently mocked (`me` user only)
