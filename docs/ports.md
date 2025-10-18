# KohakuHub Port Configuration

## Quick Reference

### For Users (Production)

**Use this port for everything:**
- **28080** - Web UI + API (nginx reverse proxy)

**Don't use:**
- ~~48888~~ - Backend API (internal only)

### For Developers

**Development:**
- **5173** - Frontend dev server (npm run dev)
- **48888** - Backend API (uvicorn)
- **48888/docs** - Swagger API documentation

**Production:**
- **28080** - All traffic (nginx → frontend + backend)

### For Admins

**Service Management:**
- **28000** - LakeFS Web UI
- **29000** - MinIO Console
- **29001** - MinIO S3 API
- **25432** - PostgreSQL (if exposed)

## Port Architecture Diagram

```mermaid
graph TB
    subgraph External["External Access"]
        Client[Client Requests]
    end

    subgraph Entry["Entry Point - Port 28080"]
        Nginx[Nginx Reverse Proxy<br/>hub-ui:80]
    end

    subgraph Application["Application Layer - Port 48888"]
        FastAPI[FastAPI Backend<br/>hub-api:48888<br/>INTERNAL ONLY]
    end

    subgraph Storage["Storage Services - Internal Ports"]
        LakeFS[LakeFS<br/>:28000<br/>Admin UI]
        MinIO[MinIO<br/>:9000 S3 API<br/>:29001 Public<br/>:29000 Console]
        Postgres[PostgreSQL<br/>:5432<br/>Optional :25432 External]
    end

    Client -->|HTTP/HTTPS<br/>:28080| Nginx
    Nginx -->|Static Files| Client
    Nginx -->|API Proxy<br/>:48888| FastAPI
    FastAPI -->|Response| Nginx
    Nginx -->|Response| Client

    FastAPI -->|REST API<br/>:28000| LakeFS
    FastAPI -->|S3 API<br/>:9000| MinIO
    FastAPI -->|SQL<br/>:5432| Postgres
    LakeFS -->|Objects<br/>:9000| MinIO
```

## Configuration Examples

### Python Client
```python
os.environ["HF_ENDPOINT"] = "http://localhost:28080"  # ✓ Correct
os.environ["HF_ENDPOINT"] = "http://localhost:48888"  # ✗ Wrong
```

### CLI
```bash
export HF_ENDPOINT=http://localhost:28080  # ✓ Correct
kohub-cli auth login
```

### Docker Compose
```yaml
# Production - Only expose port 28080
hub-ui:
  ports:
    - "28080:80"  # ✓ Only this

hub-api:
  # NO ports exposed  # ✓ Internal only
```

## Why Nginx Reverse Proxy?

1. **Single Entry Point** - One port for users to remember
2. **Security** - Backend not directly accessible
3. **SSL Termination** - Nginx handles HTTPS
4. **Static Files** - Nginx serves frontend efficiently
5. **API Proxying** - `/api`, `/org`, resolve → backend:48888
6. **Scalability** - Can add multiple backend instances

## Port Mapping

```
Client Request → Port 28080 (Nginx)
                    ├→ / (static files) → Frontend
                    ├→ /api/* → backend:48888
                    ├→ /org/* → backend:48888
                    └→ /{type}s/{ns}/{name}/resolve/* → backend:48888
```
