# Dataset Viewer

**Interactive data exploration for datasets with SQL query support**

**License:** Kohaku Software License 1.0 (Non-Commercial with Trial)
**Status:** Production Ready (v0.1.0)

---

## Overview

The Dataset Viewer is a powerful, standalone component for previewing and querying large dataset files directly in your browser. It's designed to handle multi-GB files efficiently without downloading them entirely, using streaming parsers and HTTP range requests.

### Key Features

- ✅ **No Full Download** - Streams data using range requests
- ✅ **Multiple Formats** - CSV, Parquet, JSONL, TAR (webdataset)
- ✅ **SQL Queries** - Run DuckDB queries without downloading full file
- ✅ **Infinite Scroll** - Automatically loads more rows as you scroll
- ✅ **Auth-Free Backend** - Works with any S3 presigned URL
- ✅ **Rate Limited** - Built-in DDoS protection
- ✅ **Standalone** - Can be extracted from KohakuHub

---

## Architecture

### Backend (`src/kohakuhub/datasetviewer/`)

**Minimal, stateless API that accepts URLs:**

```
Client (Browser)
    ↓ Sends: S3 presigned URL + max_rows
Backend API (/api/dataset-viewer/preview)
    ↓ Streams file with httpx/fsspec
S3 or any HTTP(S) URL
    ↓ Returns: Only needed bytes (range requests!)
Backend Parser
    ↓ Returns: JSON (columns + rows)
Client renders in table
```

**No authentication required** - Security comes from presigned URLs.

### Frontend (`src/kohaku-hub-ui/src/components/DatasetViewer/`)

**Vue 3 components:**
- `DatasetViewer.vue` - Main container
- `DataGridEnhanced.vue` - Table with infinite scroll and row details
- `TARFileList.vue` - TAR archive file browser
- `api.js` - API client

---

## Supported Formats

| Format | Streaming | SQL | Notes |
|--------|-----------|-----|-------|
| **CSV** | ✅ Yes | ✅ Yes | Stops after N rows, no full download |
| **TSV** | ✅ Yes | ✅ Yes | Tab-delimited CSV |
| **Parquet** | ✅ Yes | ✅ Yes | DuckDB/fsspec use range requests (best for SQL!) |
| **JSONL** | ✅ Yes | ✅ Yes | Line-by-line streaming, DuckDB support |
| **TAR** | ⚠️ Headers | ❌ No | Lists files without full download |
| **WebDataset** | ✅ Yes | ❌ No | TAR with ID.suffix format |
| JSON | ❌ No | ❌ No | Not supported (requires full download) |

---

## Quick Start

### Using in KohakuHub

1. **Upload a dataset** to your repository
2. **Go to the Viewer tab** (appears for dataset repositories)
3. **Select a file** from the left sidebar
4. **Preview appears** - First 100 rows load automatically
5. **Scroll down** - More rows load automatically (infinite scroll)
6. **Enable SQL** (CSV/Parquet only) - Run queries on data

### Standalone Usage

The Dataset Viewer can be used independently:

```python
# Backend only
from fastapi import FastAPI
from kohakuhub.datasetviewer import router

app = FastAPI()
app.include_router(router)
# Access: POST /dataset-viewer/preview
```

---

## Usage Examples

### Basic Preview

**Request:**
```bash
curl -X POST http://localhost:48888/api/dataset-viewer/preview \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://s3.amazonaws.com/bucket/data.csv?...",
    "format": "csv",
    "max_rows": 1000
  }'
```

**Response:**
```json
{
  "columns": ["id", "name", "age", "city"],
  "rows": [
    [1, "Alice", 28, "New York"],
    [2, "Bob", 34, "San Francisco"]
  ],
  "total_rows": 2,
  "truncated": false,
  "file_size": 1024,
  "format": "csv"
}
```

### SQL Queries

**Request:**
```bash
curl -X POST http://localhost:48888/api/dataset-viewer/sql \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://s3.../employees.parquet?...",
    "query": "SELECT city, AVG(salary) as avg_salary FROM dataset GROUP BY city ORDER BY avg_salary DESC LIMIT 10",
    "format": "parquet"
  }'
```

**Response:**
```json
{
  "columns": ["city", "avg_salary"],
  "rows": [
    ["San Francisco", 125000],
    ["New York", 118000],
    ["Seattle", 105000"]
  ],
  "total_rows": 3,
  "query": "SELECT city, AVG(salary) as avg_salary FROM read_parquet('...') GROUP BY city ORDER BY avg_salary DESC LIMIT 10"
}
```

---

## SQL Query Features

### Supported Operations

**DuckDB powers SQL queries with full SQL support:**

```sql
-- Filtering
SELECT * FROM dataset WHERE age > 30 AND city = 'New York'

-- Aggregation
SELECT department, COUNT(*) as count, AVG(salary) as avg_salary
FROM dataset
GROUP BY department
HAVING count > 5
ORDER BY avg_salary DESC

-- Joins (if you have multiple files)
SELECT * FROM dataset
ORDER BY RANDOM() LIMIT 100

-- Window functions
SELECT name, salary,
       ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as rank
FROM dataset
```

### Performance

**DuckDB + HTTP Range Requests:**
- **Parquet:** Reads only needed row groups (metadata + selected columns)
- **CSV:** Streams and stops after getting results
- **1GB Parquet file, filtered query:** Downloads ~50-100MB (not full 1GB!)

### Safety Features

1. **Auto-LIMIT** - Adds `LIMIT 10000` if not specified
2. **Query sanitization** - Blocks DROP, DELETE, INSERT, UPDATE, CREATE, ALTER
3. **SELECT only** - Only SELECT queries allowed
4. **Rate limiting** - 60 queries/minute per IP/session

---

## Frontend UI

### Simple Mode (No SQL)

1. Select file from sidebar
2. Choose max rows (100, 500, 1000, 5000, 10000)
3. Click "Reload"
4. View first N rows

### SQL Mode (CSV/Parquet only)

1. Check "Use SQL Query"
2. Enter query in textarea (use `dataset` as table name)
3. Click "Run Query"
4. View results

**Quick query buttons:**
- First 100 rows
- Random 100 rows
- Count all rows

### Table Features

- **Sortable columns** - Click headers to sort
- **Row details** - Click row to expand full content
- **Auto-collapse** - Long cells (>100 chars) truncated with "..."
- **Image support** - Displays images inline (data URLs)
- **Infinite scroll** - Loads 100 rows at a time automatically

---

## API Endpoints

### POST `/api/dataset-viewer/preview`

Preview a file without SQL.

**Request Body:**
```json
{
  "url": "https://...",
  "format": "csv",  // Optional: auto-detect
  "max_rows": 1000,
  "delimiter": ","  // For CSV only
}
```

**Response:** See "Basic Preview" example above

---

### POST `/api/dataset-viewer/sql`

Execute SQL query on file.

**Request Body:**
```json
{
  "url": "https://...",
  "query": "SELECT * FROM dataset WHERE age > 30",
  "format": "parquet",  // Optional: auto-detect
  "max_rows": 10000  // Safety limit if no LIMIT in query
}
```

**Response:** Same as preview

---

### POST `/api/dataset-viewer/tar/list`

List files in TAR archive (streaming - doesn't load full TAR).

**Request Body:**
```json
{
  "url": "https://..."
}
```

**Response:**
```json
{
  "files": [
    {"name": "train.csv", "size": 10240, "offset": 512},
    {"name": "test.csv", "size": 5120, "offset": 11264}
  ],
  "total_size": 20480
}
```

---

### POST `/api/dataset-viewer/tar/extract`

Extract single file from TAR (using range request).

**Request Body:**
```json
{
  "url": "https://...",
  "file_name": "train.csv"
}
```

**Response:** Raw file bytes

---

### POST `/api/dataset-viewer/tar/webdataset`

Preview TAR in webdataset format (ID.suffix pattern).

**Request Body:**
```json
{
  "url": "https://..."
}
```

**Query Parameter:**
- `max_samples=100` - Max samples to preview

**Response:**
```json
{
  "columns": ["id", "json", "txt", "ppm"],
  "rows": [
    ["000000", "{...}", "caption", "<binary: 12KB>"],
    ["000001", "{...}", "caption2", "<binary: 12KB>"]
  ],
  "format": "webdataset"
}
```

---

### GET `/api/dataset-viewer/rate-limit`

Get current rate limit stats.

**Response:**
```json
{
  "requests_used": 10,
  "requests_limit": 60,
  "concurrent_requests": 1,
  "concurrent_limit": 3,
  "bytes_processed": 1048576,
  "window_seconds": 60
}
```

---

## Rate Limiting

**Per IP/session:**
- 60 requests per minute
- 3 concurrent requests max
- 500 MB file size limit
- 10,000 rows max per response

**Implementation:**
- Sliding window algorithm
- In-memory storage (no Redis required)
- Auto-cleanup of old records

**Bypass:** No bypass available (by design - prevents abuse)

---

## Performance Benchmarks

### File Streaming

| File Type | Size | Load Time | Network Download | Memory |
|-----------|------|-----------|------------------|--------|
| CSV | 1 GB | ~5s | ~10 MB | ~20 MB |
| JSONL | 1 GB | ~5s | ~10 MB | ~20 MB |
| Parquet | 1 GB | ~3s | ~50 MB | ~50 MB |
| TAR (list) | 10 GB | ~10s | ~5 MB | ~10 MB |

**Key insight:** Even for GB-level files, only MB-level data is downloaded!

### SQL Queries

| Query Type | File Size | Execution Time | Network Download |
|------------|-----------|----------------|------------------|
| SELECT with LIMIT | 1 GB Parquet | ~2s | ~50 MB |
| WHERE filter | 1 GB Parquet | ~5s | ~200 MB |
| GROUP BY aggregation | 1 GB Parquet | ~10s | ~500 MB |
| COUNT(*) | 1 GB CSV | ~30s | Full file |

**Parquet is MUCH faster for SQL queries** (columnar format + range requests)

---

## Configuration

### Environment Variables

```bash
# Not required - Dataset Viewer has no specific config
# Uses parent KohakuHub's S3 settings automatically
```

### Rate Limit Customization

```python
from kohakuhub.datasetviewer.rate_limit import RateLimitConfig, get_rate_limiter

config = RateLimitConfig(
    max_requests=100,        # 100 req/min (default: 60)
    window_seconds=60,       # 1 minute window
    max_concurrent=5,        # 5 concurrent (default: 3)
    max_file_size=1_000_000_000,  # 1GB (default: 500MB)
    max_rows=20000           # 20k rows (default: 10k)
)

# Apply before server start
from kohakuhub.datasetviewer.rate_limit import _rate_limiter
_rate_limiter = RateLimiter(config)
```

---

## Security

### Built-in Protections

1. **Rate limiting** - Prevents flooding
2. **SQL sanitization** - Blocks dangerous queries
3. **File size limits** - Prevents memory exhaustion
4. **Concurrent limits** - Prevents resource starvation
5. **No authentication** - Can't be used to bypass auth (relies on presigned URLs)

### Potential Risks

**SSRF (Server-Side Request Forgery):**
- Backend fetches any URL provided by client
- Could be used to probe internal network

**Mitigation:**
```python
# Optional: Add URL allowlist
ALLOWED_HOSTS = ["s3.amazonaws.com", "*.r2.cloudflarestorage.com"]

def validate_url(url):
    parsed = urlparse(url)
    if not any(fnmatch(parsed.hostname, pattern) for pattern in ALLOWED_HOSTS):
        raise HTTPException(403, "URL not allowed")
```

**Bandwidth Abuse:**
- Already mitigated by rate limiting
- Monitor S3 egress costs

---

## Licensing

### Kohaku Software License 1.0

**Non-Commercial Use:** ✅ Free
- Personal projects
- Academic research
- Non-profit organizations

**Commercial Use:** ⚠️ Trial then License Required
- **Trial period:** 3 months OR $25,000 revenue/year (whichever comes first)
- **After trial:** Contact kohaku@kblueleaf.net for commercial license

**Source Code:** ✅ Must be available
- Like AGPL-3, you must provide source code
- Derivative works must use same license
- Cannot create closed-source proprietary versions

**Integration Note:**
- KohakuHub itself can integrate Dataset Viewer (same copyright owner)
- Third-party users: Using KohakuHub WITH Dataset Viewer = Both licenses apply
- Third-party users: Remove Dataset Viewer = AGPL-3 only

---

## Technical Deep Dive

### How Streaming Works

**CSV/JSONL:**
```python
async with httpx.AsyncClient().stream("GET", url) as response:
    buffer = ""
    row_count = 0

    async for chunk in response.aiter_text():
        buffer += chunk
        # Process complete lines
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            parse_line(line)
            row_count += 1

            if row_count >= max_rows:
                await response.aclose()  # Stop downloading!
                break
```

**Result:** For 1GB CSV, downloads only ~10MB to get first 1000 rows.

**Parquet (with fsspec):**
```python
from fsspec.implementations.http import HTTPFileSystem

fs = HTTPFileSystem()
with fs.open(url, mode="rb") as f:
    # PyArrow reads Parquet using seek() and read()
    # fsspec translates to HTTP range requests!
    parquet_file = pq.ParquetFile(f)

    # Read only first row group
    table = parquet_file.read_row_group(0)
```

**Result:** For 1GB Parquet, downloads ~50MB (footer + first row group metadata + data).

**TAR Streaming:**
```python
async with client.stream("GET", url) as response:
    buffer = b""
    files = []

    async for chunk in response.aiter_bytes(8192):
        buffer += chunk

        # Parse TAR headers (512 bytes each)
        while len(buffer) >= 512:
            header = buffer[:512]
            name, size, offset = parse_tar_header(header)
            files.append({"name": name, "size": size, "offset": offset})

            # Skip file data (don't download!)
            buffer = buffer[512 + padded_size:]

            if len(files) >= 1000:
                await response.aclose()  # Stop!
                break
```

**Result:** For 10GB TAR with 10k files, downloads ~5MB (just headers) to list files.

### SQL Query Execution

**DuckDB httpfs extension:**
```python
conn = duckdb.connect(":memory:")
conn.execute("INSTALL httpfs")
conn.execute("LOAD httpfs")
conn.execute("SET unsafe_disable_etag_checks = true")  # For presigned URLs

# DuckDB reads directly from HTTP with range requests!
query = f"SELECT * FROM read_parquet('{url}') WHERE age > 30 LIMIT 100"
result = conn.execute(query).fetchall()
```

**Why disable ETag checks:**
- S3 presigned URLs have changing signatures
- Each HTTP request gets new presigned URL (different ETag)
- DuckDB makes multiple requests (range requests)
- Without disabling: "ETag mismatch" error

---

## Frontend Integration

### In KohakuHub

Dataset Viewer is automatically integrated:

```vue
<!-- In repo viewer page (AGPL-3 code) -->
<template>
  <div class="viewer-tab">
    <!-- This import is allowed - KohakuHub owns both licenses -->
    <DatasetViewer
      :file-url="presignedUrl"
      :file-name="fileName"
      :max-rows="100"
    />
  </div>
</template>
```

### Standalone

Can be used in any Vue 3 app:

```vue
<script setup>
import DatasetViewer from '@/components/DatasetViewer/DatasetViewer.vue'

const fileUrl = 'https://s3.amazonaws.com/bucket/data.csv?...'
</script>

<template>
  <DatasetViewer
    :file-url="fileUrl"
    :file-name="data.csv"
    :max-rows="1000"
  />
</template>
```

**Note:** Must include Kohaku License and attribution.

---

## Troubleshooting

### "Failed to parse Parquet"

**Cause:** Missing dependencies

**Solution:**
```bash
pip install pyarrow fsspec aiohttp
```

### "Rate limit exceeded"

**Cause:** Too many requests (60/minute limit)

**Solution:** Wait 60 seconds or check stats:
```bash
curl http://localhost:48888/api/dataset-viewer/rate-limit
```

### "Query execution failed: ETag mismatch"

**Cause:** DuckDB ETag validation with presigned URLs

**Solution:** Already fixed in code with `SET unsafe_disable_etag_checks = true`

### SQL queries timing out

**Cause:** Complex queries on large files

**Solution:**
- Use Parquet instead of CSV (much faster)
- Add WHERE clauses to filter data
- Use simpler aggregations
- Reduce max_rows limit

### "No previewable files"

**Cause:** Files not in supported format

**Solution:**
- Check file extension (.csv, .parquet, .jsonl)
- JSON files not supported (use JSONL instead)
- TAR files need special handling (webdataset format)

---

## Development

### Dependencies

**Python (Backend):**
```bash
pip install fastapi httpx duckdb pyarrow fsspec aiohttp pydantic
```

**JavaScript (Frontend):**
- No external dependencies (plain Vue 3)

### Running Tests

```bash
# Generate test data
cd test-viewer
python generate_datasets.py

# Upload to test server
kohub-cli upload --repo test-viewer-data --file *.csv
kohub-cli upload --repo test-viewer-data --file *.parquet

# Test in browser
http://localhost:28080/datasets/{username}/test-viewer-data?tab=viewer
```

### Adding New Format Support

1. Create parser in `parsers.py`:
```python
class MyFormatParser:
    @staticmethod
    async def parse(url: str, max_rows: int) -> dict:
        # Implement streaming parser
        pass
```

2. Add to router:
```python
elif file_format == "myformat":
    result = await MyFormatParser.parse(url_str, req.max_rows)
```

3. Add to `detect_format()`:
```python
elif filename_lower.endswith(".myformat"):
    return "myformat"
```

---

## Roadmap

### Phase 1 (✅ Complete)
- CSV, JSONL, Parquet streaming
- TAR archive support
- SQL queries (DuckDB)
- Infinite scroll
- Rate limiting

### Phase 2 (Planned)
- Column statistics (min/max/avg/null counts)
- Data visualization (histograms, scatter plots)
- Export filtered results
- Client-side caching (IndexedDB)
- WebDataset preview in UI

### Phase 3 (Future)
- More formats (Avro, ORC, Excel)
- Advanced SQL (JOINs across multiple files)
- Saved queries
- Query history
- Collaborative annotations

---

## FAQ

### Q: Can I use Dataset Viewer without KohakuHub?

**A:** Yes! It's a standalone module. Just import the router and run it.

### Q: Does it work with non-S3 URLs?

**A:** Yes! Any HTTP(S) URL works. S3 presigned URLs are just one use case.

### Q: How much bandwidth does it use?

**A:** Typically 1-10% of file size for preview, 10-50% for SQL queries (depending on complexity).

### Q: Can I query multiple files at once?

**A:** Not currently. Each query targets one file. Multi-file JOINs are planned for Phase 3.

### Q: What's the largest file you've tested?

**A:** Successfully tested with:
- 3 GB JSONL (1.5M rows)
- 1.6 GB CSV (1M rows)
- 870 MB Parquet (2M rows)

### Q: Does sorting work on large files?

**A:** Yes, but sorting happens client-side after data is loaded. For large files (>1000 rows), use SQL ORDER BY instead.

### Q: Can I filter data before loading?

**A:** Yes! Use SQL queries with WHERE clauses. This is the recommended approach for large files.

---

## Attribution Requirements

When using Dataset Viewer, you must display:

```
This Software is licensed under the Kohaku Software License by KohakuBlueLeaf.
Copyright 2025 KohakuBlueLeaf.

Commercial usage exceeding trial limits ($25k/year OR 3 months)
requires a commercial license. Contact: kohaku@kblueleaf.net
```

This is already included in `DatasetViewerTab.vue`.

---

## Commercial Licensing

**Need a commercial license?**

**Contact:** kohaku@kblueleaf.net

**Include:**
- Company name and size
- Expected revenue from Dataset Viewer usage
- Use case description
- Number of users/deployments

**Pricing models:**
- Annual flat fee
- Revenue sharing
- Per-seat licensing
- Custom enterprise agreements

---

## Conclusion

The Dataset Viewer is a powerful, production-ready tool for exploring large datasets efficiently. Its streaming architecture, SQL support, and rate limiting make it suitable for both development and production use.

**Get started:** Upload a dataset and click the "Viewer" tab!

**Questions?** Check the main documentation or contact kohaku@kblueleaf.net
