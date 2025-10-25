# KohakuBoard - Backend

Minimal experiment tracking backend with high-performance data serving.

## Features

- FastAPI-based REST API
- Sparse metric logging support
- Multiple data types: scalars, media, tables, histograms
- Step-indexed data structure
- Mock data generation for testing

## License

**Kohaku Software License 1.0**

This is a premium feature of KohakuHub with commercial usage restrictions.

- ✅ Free for non-commercial use
- ⚠️ Commercial trial: 3 months OR $25k revenue/year
- ⚠️ After trial, requires commercial license

Contact: kohaku@kblueleaf.net

## Installation

```bash
pip install -e .
```

## Development

```bash
uvicorn kohakuboard.main:app --reload --port 48889
```

API docs: http://localhost:48889/docs

## API Endpoints

- `GET /api/experiments` - List experiments
- `GET /api/experiments/{id}/summary` - Get experiment summary
- `GET /api/experiments/{id}/scalars/{name}` - Get scalar metric data
- `GET /api/experiments/{id}/media/{name}` - Get media log
- `GET /api/experiments/{id}/tables/{name}` - Get table log
- `GET /api/experiments/{id}/histograms/{name}` - Get histogram log
