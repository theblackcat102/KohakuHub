"""
Dataset Viewer - Minimal Backend for Large File Preview

This module provides a minimal, auth-free backend for previewing large dataset files.
It's designed to be independent from KohakuHub core for licensing flexibility.

Features:
- No authentication required (relies on S3 presigned URLs)
- Session-based rate limiting (prevent abuse)
- Streaming support for CSV, JSON, JSONL
- Smart loading for Parquet (DuckDB over HTTP)
- TAR archive extraction

License: Kohaku Software License 1.0 (see LICENSE file)
Copyright 2025 KohakuBlueLeaf

This Software is licensed under the Kohaku Software License by KohakuBlueLeaf.
For commercial usage exceeding the trial limits ($25k/year OR 3 months),
please contact: kohaku@kblueleaf.net
"""

__version__ = "0.1.0"
