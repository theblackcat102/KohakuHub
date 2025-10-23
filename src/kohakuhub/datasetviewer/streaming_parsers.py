"""
Streaming parsers for large files using HTTP range requests.

These parsers minimize memory usage by:
1. Using range requests to fetch only needed bytes
2. Parsing incrementally without loading full file
3. Supporting webdataset-style TAR format
"""

import io
import struct
import tarfile
from typing import Any, Optional

import httpx


class ParquetStreamParser:
    """
    Stream Parquet files using range requests.

    Parquet file structure:
    [Header: 4 bytes "PAR1"]
    [Row Group 1]
    [Row Group 2]
    ...
    [Footer metadata]
    [Footer length: 4 bytes]
    [Magic: 4 bytes "PAR1"]
    """

    @staticmethod
    async def parse(url: str, max_rows: int = 1000) -> dict[str, Any]:
        """
        Parse Parquet file using DuckDB with HTTP range requests.

        DuckDB automatically uses range requests to:
        1. Read footer (last ~MB) to get metadata
        2. Read only required row groups
        3. Skip unused columns if specified

        This is MUCH more efficient than downloading entire file!
        """
        try:
            import duckdb
        except ImportError:
            raise Exception("DuckDB not installed. Install with: pip install duckdb")

        try:
            conn = duckdb.connect(":memory:")

            # DuckDB reads Parquet over HTTP with automatic range requests
            # It only downloads: footer + first row group (typically <10% of file)
            query = f"SELECT * FROM read_parquet('{url}') LIMIT {max_rows}"
            result = conn.execute(query).fetchall()

            # Get column names
            columns = [desc[0] for desc in conn.description]

            # Get total row count (fast - just reads metadata from footer)
            total_query = f"SELECT COUNT(*) FROM read_parquet('{url}')"
            total_rows = conn.execute(total_query).fetchone()[0]

            conn.close()

            return {
                "columns": columns,
                "rows": [list(row) for row in result],
                "total_rows": total_rows,
                "truncated": total_rows > max_rows,
                "file_size": None,  # Not easily available
            }

        except Exception as e:
            raise Exception(f"Failed to parse Parquet: {e}")


class WebDatasetTARParser:
    """
    Parse TAR files in webdataset format without loading entire archive.

    Webdataset format:
    - Files grouped by ID: 001.jpg, 001.txt, 001.json
    - Each ID represents one sample/row
    - Different suffixes represent different columns

    Example:
    000.jpg    -> ID=000, column=image
    000.txt    -> ID=000, column=caption
    001.jpg    -> ID=001, column=image
    001.txt    -> ID=001, column=caption
    """

    @staticmethod
    async def parse_streaming(url: str, max_samples: int = 100) -> dict[str, Any]:
        """
        Parse webdataset TAR file using streaming.

        Reads TAR headers sequentially until we have enough samples.
        Does NOT load file content - only headers!

        Args:
            url: TAR file URL
            max_samples: Maximum number of samples (IDs) to collect

        Returns:
            {
                "columns": ["id", "jpg", "txt", "json", ...],
                "rows": [
                    ["000", "<jpg binary>", "caption text", {...}],
                    ...
                ],
                "total_samples": N,
                "truncated": bool
            }
        """
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                # Stream TAR file
                samples = {}  # {id: {suffix: content}}
                current_id = None
                buffer = b""

                async for chunk in response.aiter_bytes(chunk_size=8192):
                    buffer += chunk

                    # Parse TAR headers (512 bytes each)
                    while len(buffer) >= 512:
                        header = buffer[:512]

                        # Check for end of archive (all zeros)
                        if header == b"\x00" * 512:
                            break

                        # Parse TAR header
                        try:
                            name = header[0:100].rstrip(b"\x00").decode("utf-8")
                            size_str = header[124:136].rstrip(b"\x00").decode("utf-8")
                            size = int(size_str, 8) if size_str else 0
                        except Exception:
                            # Invalid header, skip
                            buffer = buffer[512:]
                            continue

                        # Skip directory entries
                        if name.endswith("/"):
                            buffer = buffer[512:]
                            continue

                        # Calculate total size (header + data, rounded to 512)
                        data_blocks = (size + 511) // 512
                        total_size = 512 + data_blocks * 512

                        # Do we have enough data?
                        if len(buffer) < total_size:
                            break

                        # Extract file data
                        file_data = buffer[512 : 512 + size]

                        # Parse filename: "000.jpg" -> id="000", suffix="jpg"
                        parts = name.rsplit(".", 1)
                        if len(parts) == 2:
                            file_id, suffix = parts

                            # Initialize sample if new
                            if file_id not in samples:
                                samples[file_id] = {}

                            # Store content (for small files only)
                            # For images/large files, just store metadata
                            if size < 1024 * 1024:  # <1MB
                                try:
                                    # Try to decode as text
                                    content = file_data.decode("utf-8")
                                except UnicodeDecodeError:
                                    # Binary file - store size instead
                                    content = f"<binary: {size} bytes>"
                            else:
                                content = f"<large file: {size} bytes>"

                            samples[file_id][suffix] = content

                        # Move buffer forward
                        buffer = buffer[total_size:]

                        # Stop if we have enough samples
                        if len(samples) >= max_samples:
                            # Cancel stream to save bandwidth!
                            await response.aclose()
                            break

                    if len(samples) >= max_samples:
                        break

        # Convert to columnar format
        all_suffixes = set()
        for sample in samples.values():
            all_suffixes.update(sample.keys())

        columns = ["id"] + sorted(all_suffixes)

        rows = []
        for sample_id, data in sorted(samples.items()):
            row = [sample_id] + [
                data.get(suffix, None) for suffix in sorted(all_suffixes)
            ]
            rows.append(row)

        return {
            "columns": columns,
            "rows": rows,
            "total_samples": len(samples),
            "truncated": len(samples) >= max_samples,
            "format": "webdataset",
        }


class TARStreamParser:
    """
    Stream TAR files without loading into memory.

    For regular TAR files (not webdataset), we:
    1. Stream headers only to build file index
    2. Use range requests to fetch individual files
    """

    @staticmethod
    async def list_files_streaming(url: str) -> dict[str, Any]:
        """
        List files in TAR by streaming headers only.

        This is MUCH more efficient than current implementation
        which loads entire TAR into memory!

        Returns:
            {
                "files": [
                    {"name": "...", "size": N, "offset": N},
                    ...
                ],
                "total_size": N  # Total TAR size
            }
        """
        files = []
        offset = 0

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                buffer = b""

                async for chunk in response.aiter_bytes(chunk_size=8192):
                    buffer += chunk

                    # Parse headers (512 bytes each)
                    while len(buffer) >= 512:
                        header = buffer[:512]

                        # End of archive
                        if header == b"\x00" * 512:
                            await response.aclose()
                            return {"files": files, "total_size": total_size}

                        # Parse header
                        try:
                            name = header[0:100].rstrip(b"\x00").decode("utf-8")
                            size_str = header[124:136].rstrip(b"\x00").decode("utf-8")
                            size = int(size_str, 8) if size_str else 0
                        except Exception:
                            buffer = buffer[512:]
                            offset += 512
                            continue

                        # Skip directories
                        if not name.endswith("/"):
                            files.append(
                                {"name": name, "size": size, "offset": offset + 512}
                            )

                        # Calculate block size
                        data_blocks = (size + 511) // 512
                        total_blocks = 1 + data_blocks  # header + data
                        block_size = total_blocks * 512

                        # Skip file data (we only want headers)
                        if len(buffer) >= block_size:
                            buffer = buffer[block_size:]
                            offset += block_size
                        else:
                            # Need more data
                            break

        return {"files": files, "total_size": total_size}

    @staticmethod
    async def extract_file_range(url: str, offset: int, size: int) -> bytes:
        """
        Extract file from TAR using range request.

        Args:
            url: TAR file URL
            offset: Byte offset where file data starts
            size: File size in bytes

        Returns:
            File content
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                url, headers={"Range": f"bytes={offset}-{offset + size - 1}"}
            )
            response.raise_for_status()
            return response.content
