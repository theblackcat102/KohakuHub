"""
Dataset Viewer API Router

Minimal, auth-free endpoints for previewing dataset files.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, HttpUrl

from kohakuhub.datasetviewer.parsers import (
    CSVParser,
    JSONLParser,
    JSONParser,
    ParquetParser,
    TARParser,
    detect_format,
)
from kohakuhub.datasetviewer.rate_limit import (
    check_rate_limit_dependency,
    get_rate_limiter,
)
from kohakuhub.datasetviewer.sql_query import SQLQueryError, execute_sql_query
from kohakuhub.datasetviewer.streaming_parsers import (
    TARStreamParser,
    WebDatasetTARParser,
)

router = APIRouter(prefix="/dataset-viewer", tags=["Dataset Viewer"])


class PreviewRequest(BaseModel):
    """Request to preview a file."""

    url: HttpUrl  # S3 presigned URL or any HTTP(S) URL
    format: Optional[str] = None  # Auto-detect if not provided
    max_rows: int = 1000
    delimiter: str = ","  # For CSV/TSV


class SQLQueryRequest(BaseModel):
    """Request to execute SQL query on a file."""

    url: HttpUrl  # S3 presigned URL or any HTTP(S) URL
    query: str  # SQL query to execute
    format: Optional[str] = None  # Auto-detect if not provided
    max_rows: int = 10000  # Safety limit


class PreviewResponse(BaseModel):
    """Response with preview data."""

    columns: list[str]
    rows: list[list]
    total_rows: int
    truncated: bool
    file_size: Optional[int] = None
    format: str


class TARListRequest(BaseModel):
    """Request to list TAR contents."""

    url: HttpUrl


class TARListResponse(BaseModel):
    """Response with TAR file listing."""

    files: list[dict]
    total_size: int


class TARExtractRequest(BaseModel):
    """Request to extract file from TAR."""

    url: HttpUrl
    file_name: str


class RateLimitStatsResponse(BaseModel):
    """Rate limit statistics."""

    requests_used: int
    requests_limit: int
    concurrent_requests: int
    concurrent_limit: int
    bytes_processed: int
    window_seconds: int


@router.post("/preview", response_model=PreviewResponse)
async def preview_file(
    request: Request,
    req: PreviewRequest,
    identifier: str = Depends(check_rate_limit_dependency),
):
    """
    Preview a dataset file from URL.

    Supports: CSV, TSV, JSON, JSONL, Parquet

    Args:
        req: Preview request with URL and options

    Returns:
        Preview data with columns and rows

    Rate limits:
        - 60 requests per minute per session/IP
        - 3 concurrent requests per session/IP
        - Max 500MB file size
        - Max 10,000 rows returned
    """
    limiter = get_rate_limiter()

    # Validate max_rows
    if req.max_rows > limiter.config.max_rows:
        raise HTTPException(
            400,
            detail=f"max_rows cannot exceed {limiter.config.max_rows}",
        )

    # Detect format
    url_str = str(req.url)
    file_format = req.format or detect_format(url_str)

    if not file_format:
        raise HTTPException(
            400,
            detail="Cannot detect file format. Please specify 'format' parameter.",
        )

    # Parse file
    try:
        if file_format == "csv" or file_format == "tsv":
            delimiter = "\t" if file_format == "tsv" else req.delimiter
            result = await CSVParser.parse(url_str, req.max_rows, delimiter)
        elif file_format == "jsonl":
            result = await JSONLParser.parse(url_str, req.max_rows)
        elif file_format == "parquet":
            result = await ParquetParser.parse(url_str, req.max_rows)
        else:
            raise HTTPException(
                400,
                detail=f"Unsupported format: {file_format}. Supported: CSV, JSONL, Parquet, TAR",
            )

        # Track bytes processed
        bytes_processed = result.get("file_size") or 0
        limiter.finish_request(identifier, bytes_processed)

        return {**result, "format": file_format}

    except Exception as e:
        limiter.finish_request(identifier)
        raise HTTPException(500, detail=f"Failed to parse file: {str(e)}")


@router.post("/tar/list", response_model=TARListResponse)
async def list_tar_files(
    request: Request,
    req: TARListRequest,
    identifier: str = Depends(check_rate_limit_dependency),
):
    """
    List files in a TAR archive.

    Args:
        req: Request with TAR file URL

    Returns:
        List of files in archive
    """
    limiter = get_rate_limiter()

    try:
        # Use streaming parser (doesn't load full TAR into memory!)
        result = await TARStreamParser.list_files_streaming(str(req.url))
        limiter.finish_request(identifier, 0)  # Only reads headers, minimal data
        return result
    except Exception as e:
        limiter.finish_request(identifier)
        raise HTTPException(500, detail=f"Failed to list TAR: {str(e)}")


@router.post("/tar/extract")
async def extract_tar_file(
    request: Request,
    req: TARExtractRequest,
    identifier: str = Depends(check_rate_limit_dependency),
):
    """
    Extract a single file from TAR archive.

    After extraction, use /preview endpoint to preview the extracted file.

    Args:
        req: Request with TAR URL and file name

    Returns:
        File content (raw bytes)
    """
    limiter = get_rate_limiter()

    try:
        content = await TARParser.extract_file(str(req.url), req.file_name)
        limiter.finish_request(identifier, len(content))

        # Return raw bytes
        from fastapi.responses import Response

        return Response(content=content, media_type="application/octet-stream")

    except Exception as e:
        limiter.finish_request(identifier)
        raise HTTPException(500, detail=f"Failed to extract file: {str(e)}")


@router.post("/tar/webdataset", response_model=PreviewResponse)
async def preview_webdataset_tar(
    request: Request,
    req: TARListRequest,
    max_samples: int = Query(100, description="Max samples to preview"),
    identifier: str = Depends(check_rate_limit_dependency),
):
    """
    Preview TAR file in webdataset format.

    Webdataset format: Files grouped by ID (e.g., 000.jpg, 000.txt, 001.jpg)
    Each ID is a row, suffixes are columns.

    Args:
        req: TAR file URL
        max_samples: Maximum samples (rows) to preview

    Returns:
        Preview data in columnar format
    """
    limiter = get_rate_limiter()

    try:
        result = await WebDatasetTARParser.parse_streaming(str(req.url), max_samples)
        limiter.finish_request(identifier, 0)
        return result
    except Exception as e:
        limiter.finish_request(identifier)
        raise HTTPException(500, detail=f"Failed to parse webdataset: {str(e)}")


@router.get("/rate-limit", response_model=RateLimitStatsResponse)
async def get_rate_limit_stats(request: Request):
    """
    Get current rate limit statistics for this session/IP.

    Returns:
        Current usage stats
    """
    limiter = get_rate_limiter()
    identifier = limiter._get_identifier(request)
    return limiter.get_stats(identifier)


@router.post("/sql", response_model=PreviewResponse)
async def execute_sql(
    request: Request,
    req: SQLQueryRequest,
    identifier: str = Depends(check_rate_limit_dependency),
):
    """
    Execute SQL query on dataset file using DuckDB.

    DuckDB reads files with range requests (doesn't download entire file!).

    Supported formats: CSV, Parquet

    Example queries:
        SELECT * FROM dataset LIMIT 100
        SELECT age, AVG(salary) FROM dataset GROUP BY age
        SELECT * FROM dataset WHERE city = 'New York' ORDER BY salary DESC

    Args:
        req: File URL, query, and format (all in request body)

    Returns:
        Query results in tabular format

    Note: 'dataset' is a placeholder for the file being queried.
    """
    limiter = get_rate_limiter()

    # Validate max_rows
    if req.max_rows > limiter.config.max_rows:
        raise HTTPException(
            400,
            detail=f"max_rows cannot exceed {limiter.config.max_rows}",
        )

    # Detect format
    url_str = str(req.url)
    file_format = req.format or detect_format(url_str)

    if not file_format:
        raise HTTPException(
            400,
            detail="Cannot detect file format. Please specify 'format' parameter.",
        )

    # Only CSV and Parquet for now
    if file_format not in ["csv", "tsv", "parquet"]:
        raise HTTPException(
            400,
            detail=f"SQL queries not supported for {file_format}. Use CSV or Parquet.",
        )

    try:
        result = await execute_sql_query(url_str, req.query, file_format, req.max_rows)

        limiter.finish_request(identifier, 0)

        return {**result, "format": file_format}

    except SQLQueryError as e:
        limiter.finish_request(identifier)
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        limiter.finish_request(identifier)
        raise HTTPException(500, detail=f"Query execution failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "dataset-viewer"}
