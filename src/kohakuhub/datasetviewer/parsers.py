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


class ParserError(Exception):
    """Base exception for parser errors."""

    pass


class CSVParser:
    """Stream CSV files from URL."""

    @staticmethod
    async def parse(
        url: str, max_rows: int = 1000, delimiter: str = ","
    ) -> dict[str, Any]:
        """
        Parse CSV file from URL.

        Args:
            url: File URL (presigned S3 URL)
            max_rows: Maximum rows to return
            delimiter: CSV delimiter

        Returns:
            {
                "columns": ["col1", "col2", ...],
                "rows": [[val1, val2, ...], ...],
                "total_rows": N,
                "truncated": bool
            }
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                # Get file size if available
                content_length = response.headers.get("content-length")
                file_size = int(content_length) if content_length else None

                # Read in chunks
                buffer = ""
                rows = []
                columns = None
                line_count = 0

                async for chunk in response.aiter_text():
                    buffer += chunk

                    # Process complete lines
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)

                        if not line.strip():
                            continue

                        # Parse CSV line
                        try:
                            parsed = list(csv.reader([line], delimiter=delimiter))[0]
                        except Exception:
                            continue

                        # First line is header
                        if columns is None:
                            columns = parsed
                            continue

                        rows.append(parsed)
                        line_count += 1

                        if line_count >= max_rows:
                            break

                    if line_count >= max_rows:
                        break

                # Process remaining buffer
                if buffer.strip() and line_count < max_rows and columns is not None:
                    try:
                        parsed = list(csv.reader([buffer], delimiter=delimiter))[0]
                        rows.append(parsed)
                        line_count += 1
                    except Exception:
                        pass

                return {
                    "columns": columns or [],
                    "rows": rows,
                    "total_rows": line_count,
                    "truncated": line_count >= max_rows,
                    "file_size": file_size,
                }


class JSONLParser:
    """Stream JSONL (newline-delimited JSON) files from URL."""

    @staticmethod
    async def parse(url: str, max_rows: int = 1000) -> dict[str, Any]:
        """
        Parse JSONL file from URL.

        Args:
            url: File URL
            max_rows: Maximum rows to return

        Returns:
            {
                "columns": ["col1", "col2", ...],
                "rows": [[val1, val2, ...], ...],
                "total_rows": N,
                "truncated": bool
            }
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                content_length = response.headers.get("content-length")
                file_size = int(content_length) if content_length else None

                buffer = ""
                rows = []
                columns = set()
                line_count = 0

                async for chunk in response.aiter_text():
                    buffer += chunk

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)

                        if not line.strip():
                            continue

                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict):
                                # Collect all keys
                                columns.update(obj.keys())
                                rows.append(obj)
                                line_count += 1
                        except json.JSONDecodeError:
                            continue

                        if line_count >= max_rows:
                            break

                    if line_count >= max_rows:
                        break

                # Process remaining buffer
                if buffer.strip() and line_count < max_rows:
                    try:
                        obj = json.loads(buffer)
                        if isinstance(obj, dict):
                            columns.update(obj.keys())
                            rows.append(obj)
                            line_count += 1
                    except json.JSONDecodeError:
                        pass

                # Convert to columnar format
                # Sort columns by completeness (most complete first), then alphabetically
                columns_list = sorted(columns)

                # Calculate completeness for each column
                column_completeness = {}
                for col in columns_list:
                    non_null_count = sum(1 for row in rows if row.get(col) is not None)
                    column_completeness[col] = non_null_count

                # Sort by completeness (descending), then alphabetically
                columns_list = sorted(
                    columns_list, key=lambda col: (-column_completeness[col], col)
                )

                rows_list = [[row.get(col) for col in columns_list] for row in rows]

                return {
                    "columns": columns_list,
                    "rows": rows_list,
                    "total_rows": line_count,
                    "truncated": line_count >= max_rows,
                    "file_size": file_size,
                }


class JSONParser:
    """
    Parse JSON array files from URL.

    NOTE: This parser is DEPRECATED and should not be used for large files!
    It requires loading the entire file into memory.
    Use JSONL format instead for streaming support.
    """

    @staticmethod
    async def parse(url: str, max_rows: int = 1000) -> dict[str, Any]:
        """
        Parse JSON file from URL.

        Expects format: [{"col1": val1, ...}, ...]

        Args:
            url: File URL
            max_rows: Maximum rows to return

        Returns:
            Same format as JSONLParser
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            file_size = len(response.content)

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise ParserError(f"Invalid JSON: {e}")

            if not isinstance(data, list):
                raise ParserError("JSON must be an array of objects")

            # Limit rows
            rows_data = data[:max_rows]

            # Extract columns
            columns = set()
            for row in rows_data:
                if isinstance(row, dict):
                    columns.update(row.keys())

            columns_list = sorted(columns)

            # Calculate completeness for each column
            column_completeness = {}
            for col in columns_list:
                non_null_count = sum(
                    1
                    for row in rows_data
                    if isinstance(row, dict) and row.get(col) is not None
                )
                column_completeness[col] = non_null_count

            # Sort by completeness (descending), then alphabetically
            columns_list = sorted(
                columns_list, key=lambda col: (-column_completeness[col], col)
            )

            rows_list = [
                [
                    row.get(col) if isinstance(row, dict) else None
                    for col in columns_list
                ]
                for row in rows_data
            ]

            return {
                "columns": columns_list,
                "rows": rows_list,
                "total_rows": len(rows_data),
                "truncated": len(data) > max_rows,
                "file_size": file_size,
            }


class ParquetParser:
    """Parse Parquet files using PyArrow with fsspec for range requests."""

    @staticmethod
    async def parse(url: str, max_rows: int = 1000) -> dict[str, Any]:
        """
        Parse Parquet file from URL using fsspec + PyArrow.

        fsspec provides HTTP file-like object with automatic range requests.
        PyArrow reads only footer + first row group, not entire file!

        Uses asyncio.to_thread to run blocking fsspec operations without blocking event loop.

        Args:
            url: File URL (HTTP/HTTPS, including S3 presigned URLs)
            max_rows: Maximum rows to return

        Returns:
            Same format as other parsers
        """

        def _parse_parquet_sync(url: str, max_rows: int) -> dict[str, Any]:
            """Synchronous Parquet parsing (runs in thread pool)."""
            # Create sync HTTP filesystem
            fs = HTTPFileSystem()

            # Open file with fsspec (handles range requests automatically!)
            with fs.open(url, mode="rb") as f:
                # PyArrow reads with range requests via fsspec
                parquet_file = pq.ParquetFile(f)

                # Read only first row group (not entire file!)
                table = parquet_file.read_row_group(0)

                # Convert to list of dicts
                data = table.to_pylist()

                # Limit rows
                limited_data = data[:max_rows]

                # Get columns
                columns = table.schema.names

                # Convert to row format
                rows = [[row[col] for col in columns] for row in limited_data]

                # Get total rows from metadata
                total_rows = parquet_file.metadata.num_rows

                # Get file size
                file_size = parquet_file.metadata.serialized_size

                return {
                    "columns": columns,
                    "rows": rows,
                    "total_rows": total_rows,
                    "truncated": total_rows > max_rows,
                    "file_size": file_size,
                }

        try:
            # Run in thread pool to avoid blocking event loop
            result = await asyncio.to_thread(_parse_parquet_sync, url, max_rows)
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
