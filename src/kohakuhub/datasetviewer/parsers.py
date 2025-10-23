"""
File parsers for various dataset formats.

All parsers accept URLs (including S3 presigned URLs) and stream data efficiently.
"""

import asyncio
import csv
import io
import json
import tarfile
from typing import Any, AsyncIterator, Optional

import httpx
import pyarrow.parquet as pq
from fsspec.implementations.http import HTTPFileSystem


async def resolve_url_redirects(url: str) -> str:
    """
    Resolve URL redirects by following 302 responses.

    For resolve URLs that return 302, we need to follow the redirect
    and use the final S3 presigned URL for fsspec/DuckDB.
    Otherwise, they keep hitting our backend for every range request.

    Uses GET with streaming (no redirect following) to detect 302 responses
    without actually downloading content.

    Args:
        url: Original URL (may return 302)

    Returns:
        Final URL after following redirects (or original if no redirect)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            # Send GET request with streaming, but don't follow redirects
            # This gives us the correct 302 response that GET would return
            async with client.stream("GET", url) as response:
                # Check for redirect status codes
                if response.status_code in [301, 302, 303, 307, 308]:
                    location = response.headers.get("Location")
                    if location:
                        print(f"Resolved redirect: {url[:50]}... -> {location[:50]}...")
                        # Close stream immediately without reading content
                        await response.aclose()
                        return location

                # For other status codes (200, 4xx, 5xx), use original URL
                # Close stream without reading content
                await response.aclose()
                return url

    except Exception as e:
        # If request fails, fall back to original URL
        # fsspec will handle the actual request
        print(f"Warning: Could not resolve redirects for {url[:50]}...: {e}")
        return url


class ParserError(Exception):
    """Base exception for parser errors."""

    pass


class CSVParser:
    """Parse CSV files using DuckDB (non-blocking, efficient)."""

    @staticmethod
    async def parse(
        url: str, max_rows: int = 1000, delimiter: str = ","
    ) -> dict[str, Any]:
        """
        Parse CSV file from URL using DuckDB.

        DuckDB supports CSV with automatic type detection and HTTP range requests.
        Much faster and more robust than manual parsing.

        Args:
            url: File URL (presigned S3 URL)
            max_rows: Maximum rows to return
            delimiter: CSV delimiter

        Returns:
            {
                "columns": ["col1", "col2", ...],
                "rows": [[val1, val2, ...], ...],
                "total_rows": N,
                "truncated": bool,
                "file_size": N
            }
        """
        # Resolve redirects first
        resolved_url = await resolve_url_redirects(url)

        def _parse_csv_sync(url: str, max_rows: int, delimiter: str) -> dict[str, Any]:
            """Synchronous CSV parsing with DuckDB (runs in thread pool)."""
            import duckdb

            conn = duckdb.connect(":memory:")
            conn.execute("INSTALL httpfs")
            conn.execute("LOAD httpfs")

            try:
                # Read CSV with DuckDB
                query = f"""
                SELECT * FROM read_csv(
                    '{url}',
                    delim='{delimiter}',
                    header=true,
                    auto_detect=true
                )
                LIMIT {max_rows}
                """

                result = conn.execute(query).fetchall()
                columns = [desc[0] for desc in conn.description]

                # Get total row count
                try:
                    count_query = f"SELECT COUNT(*) FROM read_csv('{url}', delim='{delimiter}', header=true)"
                    total_rows = conn.execute(count_query).fetchone()[0]
                except Exception:
                    total_rows = len(result)

                conn.close()

                return {
                    "columns": columns,
                    "rows": [list(row) for row in result],
                    "total_rows": total_rows,
                    "truncated": len(result) >= max_rows,
                    "file_size": None,
                }

            except Exception as e:
                conn.close()
                raise ParserError(f"Failed to parse CSV with DuckDB: {e}")

        # Run in thread pool to avoid blocking event loop
        return await asyncio.to_thread(
            _parse_csv_sync, resolved_url, max_rows, delimiter
        )


class JSONLParser:
    """Parse JSONL files using DuckDB (non-blocking, efficient)."""

    @staticmethod
    async def parse(url: str, max_rows: int = 1000) -> dict[str, Any]:
        """
        Parse JSONL file from URL using DuckDB.

        DuckDB's read_ndjson supports newline-delimited JSON with HTTP URLs.

        Args:
            url: File URL
            max_rows: Maximum rows to return

        Returns:
            {
                "columns": ["col1", "col2", ...],
                "rows": [[val1, val2, ...], ...],
                "total_rows": N,
                "truncated": bool,
                "file_size": N
            }
        """
        # Resolve redirects first
        resolved_url = await resolve_url_redirects(url)

        def _parse_jsonl_sync(url: str, max_rows: int) -> dict[str, Any]:
            """Synchronous JSONL parsing with DuckDB (runs in thread pool)."""
            import duckdb

            conn = duckdb.connect(":memory:")
            conn.execute("INSTALL httpfs")
            conn.execute("LOAD httpfs")
            conn.execute("INSTALL json")
            conn.execute("LOAD json")

            try:
                # Read JSONL with DuckDB (newline-delimited JSON)
                query = f"""
                SELECT * FROM read_ndjson('{url}')
                LIMIT {max_rows}
                """

                result = conn.execute(query).fetchall()
                columns = [desc[0] for desc in conn.description]

                # Get total row count
                try:
                    count_query = f"SELECT COUNT(*) FROM read_ndjson('{url}')"
                    total_rows = conn.execute(count_query).fetchone()[0]
                except Exception:
                    total_rows = len(result)

                conn.close()

                return {
                    "columns": columns,
                    "rows": [list(row) for row in result],
                    "total_rows": total_rows,
                    "truncated": len(result) >= max_rows,
                    "file_size": None,
                }

            except Exception as e:
                conn.close()
                raise ParserError(f"Failed to parse JSONL with DuckDB: {e}")

        # Run in thread pool to avoid blocking event loop
        return await asyncio.to_thread(_parse_jsonl_sync, resolved_url, max_rows)


class JSONParser:
    """Parse JSON array files using DuckDB (non-blocking)."""

    @staticmethod
    async def parse(url: str, max_rows: int = 1000) -> dict[str, Any]:
        """
        Parse JSON array file from URL using DuckDB.

        DuckDB's read_json supports JSON arrays with automatic schema detection.

        Args:
            url: File URL
            max_rows: Maximum rows to return

        Returns:
            Same format as JSONLParser
        """
        # Resolve redirects first
        resolved_url = await resolve_url_redirects(url)

        def _parse_json_sync(url: str, max_rows: int) -> dict[str, Any]:
            """Synchronous JSON parsing with DuckDB (runs in thread pool)."""
            import duckdb

            conn = duckdb.connect(":memory:")
            conn.execute("INSTALL httpfs")
            conn.execute("LOAD httpfs")
            conn.execute("INSTALL json")
            conn.execute("LOAD json")

            try:
                # Read JSON array with DuckDB
                query = f"""
                SELECT * FROM read_json('{url}', format='array')
                LIMIT {max_rows}
                """

                result = conn.execute(query).fetchall()
                columns = [desc[0] for desc in conn.description]

                # Get total row count
                try:
                    count_query = (
                        f"SELECT COUNT(*) FROM read_json('{url}', format='array')"
                    )
                    total_rows = conn.execute(count_query).fetchone()[0]
                except Exception:
                    total_rows = len(result)

                conn.close()

                return {
                    "columns": columns,
                    "rows": [list(row) for row in result],
                    "total_rows": total_rows,
                    "truncated": len(result) >= max_rows,
                    "file_size": None,
                }

            except Exception as e:
                conn.close()
                raise ParserError(f"Failed to parse JSON with DuckDB: {e}")

        # Run in thread pool to avoid blocking event loop
        return await asyncio.to_thread(_parse_json_sync, resolved_url, max_rows)


class ParquetParser:
    """Parse Parquet files using DuckDB (non-blocking, most efficient)."""

    @staticmethod
    async def parse(url: str, max_rows: int = 1000) -> dict[str, Any]:
        """
        Parse Parquet file from URL using DuckDB.

        DuckDB is the most efficient way to read Parquet with HTTP range requests.
        It only reads the necessary row groups and columns, not the entire file.

        Args:
            url: File URL (HTTP/HTTPS, including S3 presigned URLs)
            max_rows: Maximum rows to return

        Returns:
            Same format as other parsers
        """
        # Resolve redirects first (302 from resolve endpoint -> S3 presigned URL)
        # This prevents DuckDB from repeatedly hitting our backend
        resolved_url = await resolve_url_redirects(url)

        def _parse_parquet_sync(url: str, max_rows: int) -> dict[str, Any]:
            """Synchronous Parquet parsing with DuckDB (runs in thread pool)."""
            import duckdb

            conn = duckdb.connect(":memory:")
            conn.execute("INSTALL httpfs")
            conn.execute("LOAD httpfs")

            try:
                # Read Parquet with DuckDB (uses HTTP range requests automatically!)
                query = f"SELECT * FROM read_parquet('{url}') LIMIT {max_rows}"

                result = conn.execute(query).fetchall()
                columns = [desc[0] for desc in conn.description]

                # Get total row count (efficient - reads only metadata)
                try:
                    count_query = f"SELECT COUNT(*) FROM read_parquet('{url}')"
                    total_rows = conn.execute(count_query).fetchone()[0]
                except Exception:
                    total_rows = len(result)

                conn.close()

                return {
                    "columns": columns,
                    "rows": [list(row) for row in result],
                    "total_rows": total_rows,
                    "truncated": len(result) >= max_rows or total_rows > max_rows,
                    "file_size": None,
                }

            except Exception as e:
                conn.close()
                raise ParserError(f"Failed to parse Parquet with DuckDB: {e}")

        try:
            # Run in thread pool to avoid blocking event loop
            result = await asyncio.to_thread(
                _parse_parquet_sync, resolved_url, max_rows
            )
            return result

        except Exception as e:
            raise ParserError(f"Failed to parse Parquet: {e}")


class TARParser:
    """Parse TAR archives from URL."""

    @staticmethod
    async def list_files(url: str) -> dict[str, Any]:
        """
        List files in TAR archive.

        Args:
            url: TAR file URL

        Returns:
            {
                "files": [
                    {"name": "...", "size": N, "offset": N},
                    ...
                ]
            }
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Load TAR into memory (for simplicity)
            # For very large TARs, we'd need streaming TAR parser
            tar_bytes = io.BytesIO(response.content)

            files = []
            with tarfile.open(fileobj=tar_bytes, mode="r:*") as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        files.append(
                            {
                                "name": member.name,
                                "size": member.size,
                                "offset": member.offset_data,
                            }
                        )

            return {"files": files, "total_size": len(response.content)}

    @staticmethod
    async def extract_file(url: str, file_name: str) -> bytes:
        """
        Extract single file from TAR archive.

        Args:
            url: TAR file URL
            file_name: Name of file to extract

        Returns:
            File content as bytes
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            tar_bytes = io.BytesIO(response.content)

            with tarfile.open(fileobj=tar_bytes, mode="r:*") as tar:
                try:
                    member = tar.getmember(file_name)
                    file_obj = tar.extractfile(member)
                    if file_obj is None:
                        raise ParserError(f"Cannot extract {file_name}")
                    return file_obj.read()
                except KeyError:
                    raise ParserError(f"File not found in archive: {file_name}")


def detect_format(filename: str) -> Optional[str]:
    """
    Detect file format from filename.

    Returns:
        "csv", "jsonl", "parquet", "tar", or None

    Note: JSON format is NOT supported (requires loading entire file).
    Use JSONL instead for streaming support.
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".csv"):
        return "csv"
    elif filename_lower.endswith(".jsonl") or filename_lower.endswith(".ndjson"):
        return "jsonl"
    elif filename_lower.endswith(".parquet"):
        return "parquet"
    elif filename_lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2")):
        return "tar"
    elif filename_lower.endswith(".tsv"):
        return "csv"  # TSV is CSV with tab delimiter
    # JSON format deliberately excluded - requires full file download

    return None
