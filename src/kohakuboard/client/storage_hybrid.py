"""Hybrid storage backend: Lance for metrics + SQLite for metadata

Combines the best of both worlds:
- Lance: Dynamic schema, efficient columnar storage for metrics
- SQLite: Fixed schema, excellent concurrency for media/tables
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from kohakuboard.client.storage_lance import LanceMetricsStorage
from kohakuboard.client.storage_sqlite import SQLiteMetadataStorage


class HybridStorage:
    """Hybrid storage: Lance for metrics + SQLite for metadata

    Architecture:
    - Metrics (scalars): Lance columnar format (dynamic schema)
    - Media: SQLite (fixed schema, good for metadata)
    - Tables: SQLite (fixed schema)
    - Histograms: Skipped for now (wandb doesn't log locally)

    Benefits:
    - Fast metric writes (Lance batch append)
    - Fast media/table writes (SQLite autocommit)
    - No connection overhead
    - Multi-connection friendly (SQLite WAL mode)
    """

    def __init__(self, base_dir: Path):
        """Initialize hybrid storage

        Args:
            base_dir: Base directory for all storage files
        """
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Initialize sub-storages
        self.metrics_storage = LanceMetricsStorage(base_dir)
        self.metadata_storage = SQLiteMetadataStorage(base_dir)

        logger.debug("Hybrid storage initialized (Lance + SQLite)")

    def append_metrics(
        self,
        step: int,
        global_step: Optional[int],
        metrics: Dict[str, Any],
        timestamp: Any,
    ):
        """Append scalar metrics

        Args:
            step: Auto-increment step
            global_step: Explicit global step
            metrics: Dict of metric name -> value
            timestamp: Timestamp (datetime object)
        """
        # Convert timestamp to ms
        if hasattr(timestamp, "timestamp"):
            timestamp_ms = int(timestamp.timestamp() * 1000)
        else:
            timestamp_ms = int(timestamp * 1000) if timestamp else None

        # Store step info in SQLite for base column queries
        self.metadata_storage.append_step_info(step, global_step, timestamp_ms)

        # Store metrics in Lance
        self.metrics_storage.append_metrics(step, global_step, metrics, timestamp)

    def append_media(
        self,
        step: int,
        global_step: Optional[int],
        name: str,
        media_list: List[Dict[str, Any]],
        caption: Optional[str] = None,
    ):
        """Append media log entry

        Args:
            step: Auto-increment step
            global_step: Explicit global step
            name: Media log name
            media_list: List of media metadata dicts
            caption: Optional caption
        """
        self.metadata_storage.append_media(step, global_step, name, media_list, caption)

    def append_table(
        self,
        step: int,
        global_step: Optional[int],
        name: str,
        table_data: Dict[str, Any],
    ):
        """Append table log entry

        Args:
            step: Auto-increment step
            global_step: Explicit global step
            name: Table log name
            table_data: Table dict
        """
        self.metadata_storage.append_table(step, global_step, name, table_data)

    def append_histogram(
        self,
        step: int,
        global_step: Optional[int],
        name: str,
        values: List[float],
        num_bins: int = 64,
    ):
        """Append histogram (SKIPPED - not logged locally)

        Histograms are not logged locally in hybrid backend (following wandb pattern).
        This silently skips - no error, just logs debug message once per histogram name.

        Args:
            step: Step number
            global_step: Global step
            name: Histogram name
            values: Values (ignored)
            num_bins: Number of bins (ignored)
        """
        # Silent skip - only log once per histogram name to avoid spam
        if not hasattr(self, "_logged_histogram_skip"):
            self._logged_histogram_skip = set()

        if name not in self._logged_histogram_skip:
            logger.debug(
                f"Histogram '{name}' skipped (hybrid backend doesn't log histograms locally)"
            )
            self._logged_histogram_skip.add(name)

    def flush_metrics(self):
        """Flush metrics buffer to Lance"""
        self.metrics_storage.flush()

    def flush_media(self):
        """Flush media buffer"""
        self.metadata_storage._flush_media()

    def flush_tables(self):
        """Flush tables buffer"""
        self.metadata_storage._flush_tables()

    def flush_histograms(self):
        """Flush histograms (no-op, skipped)"""
        pass

    def flush_all(self):
        """Flush all buffers"""
        self.flush_metrics()
        self.flush_media()
        self.flush_tables()
        logger.info("Flushed all buffers (hybrid storage)")

    def close(self):
        """Close all storage backends"""
        self.metrics_storage.close()
        self.metadata_storage.close()
        logger.debug("Hybrid storage closed")
