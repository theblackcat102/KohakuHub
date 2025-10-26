"""Storage backend using DuckDB for true incremental appends"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd
from loguru import logger


class DuckDBStorage:
    """DuckDB-based storage for metrics, media, and table logs

    Benefits over Parquet:
    - True incremental append (connection.append())
    - No read overhead
    - SQL queries natively
    - ACID transactions
    - Schema evolution via ALTER TABLE
    - Single .duckdb file per board
    """

    def __init__(self, base_dir: Path):
        """Initialize DuckDB storage

        Args:
            base_dir: Base directory for database file
        """
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Single database file
        self.db_file = base_dir / "board.duckdb"

        # Connect to database
        self.conn = duckdb.connect(str(self.db_file))

        # Create tables
        self._init_tables()

        # In-memory buffers
        self.metrics_buffer: List[Dict[str, Any]] = []
        self.media_buffer: List[Dict[str, Any]] = []
        self.tables_buffer: List[Dict[str, Any]] = []
        self.histograms_buffer: List[Dict[str, Any]] = []

        # Track known columns for schema evolution
        self.known_metric_cols = {"step", "global_step", "timestamp"}

        # Flush thresholds
        self.flush_threshold = 10  # Metrics
        self.histogram_flush_threshold = (
            100  # Histograms (batch aggressively for performance)
        )

    def _init_tables(self):
        """Initialize database tables"""
        # Metrics table (dynamic columns added as needed)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                step BIGINT NOT NULL,
                global_step BIGINT,
                timestamp TIMESTAMP NOT NULL
            )
        """
        )

        # Media table (fixed schema)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS media (
                step BIGINT NOT NULL,
                global_step BIGINT,
                name VARCHAR NOT NULL,
                caption VARCHAR,
                media_id VARCHAR,
                type VARCHAR,
                filename VARCHAR,
                path VARCHAR,
                size_bytes BIGINT,
                format VARCHAR,
                width INTEGER,
                height INTEGER
            )
        """
        )

        # Tables table (fixed schema, JSON for table data)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tables (
                step BIGINT NOT NULL,
                global_step BIGINT,
                name VARCHAR NOT NULL,
                columns VARCHAR,
                column_types VARCHAR,
                rows VARCHAR
            )
        """
        )

        # Histograms table (pre-computed bins to save space)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS histograms (
                step BIGINT NOT NULL,
                global_step BIGINT,
                name VARCHAR NOT NULL,
                num_bins INTEGER,
                bins VARCHAR,
                counts VARCHAR
            )
        """
        )

        self.conn.commit()

    def append_metrics(
        self,
        step: int,
        global_step: Optional[int],
        metrics: Dict[str, Any],
        timestamp: Any,
    ):
        """Append metrics for a step

        Args:
            step: Auto-increment step
            global_step: Explicit global step (optional)
            metrics: Dict of metric name -> value (can contain "/" for namespaces)
            timestamp: Timestamp of log event (datetime object)
        """
        # Escape metric names (replace "/" with "__" for DuckDB)
        escaped_metrics = {k.replace("/", "__"): v for k, v in metrics.items()}

        row = {
            "step": step,
            "global_step": global_step,
            "timestamp": timestamp,
            **escaped_metrics,
        }
        self.metrics_buffer.append(row)

        # Check for new columns and add them to schema
        new_cols = set(metrics.keys()) - self.known_metric_cols
        if new_cols:
            self._add_metric_columns(new_cols)

        # Flush when threshold reached
        if len(self.metrics_buffer) >= self.flush_threshold:
            self.flush_metrics()

    def _add_metric_columns(self, new_cols: set):
        """Add new metric columns to metrics table

        Args:
            new_cols: Set of new column names
        """
        for col in new_cols:
            try:
                # Escape column name (replace "/" with "__" for DuckDB compatibility)
                escaped_col = col.replace("/", "__")
                # Add column as DOUBLE (works for most ML metrics)
                self.conn.execute(
                    f'ALTER TABLE metrics ADD COLUMN IF NOT EXISTS "{escaped_col}" DOUBLE'
                )
                self.known_metric_cols.add(col)
                logger.debug(f"Added new metric column: {col} (as {escaped_col})")
            except Exception as e:
                logger.error(f"Failed to add column {col}: {e}")

        self.conn.commit()

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
        for media_meta in media_list:
            row = {
                "step": step,
                "global_step": global_step,
                "name": name,
                "caption": caption or "",
                **media_meta,
            }
            self.media_buffer.append(row)

        # Flush immediately
        self.flush_media()

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
            table_data: Table dict with columns, column_types, rows
        """
        row = {
            "step": step,
            "global_step": global_step,
            "name": name,
            "columns": json.dumps(table_data["columns"]),
            "column_types": json.dumps(table_data["column_types"]),
            "rows": json.dumps(table_data["rows"]),
        }
        self.tables_buffer.append(row)

        # Flush immediately
        self.flush_tables()

    def flush_metrics(self):
        """Flush metrics buffer to DuckDB (TRUE INCREMENTAL!)"""
        if not self.metrics_buffer:
            return

        try:
            # Convert to DataFrame
            df = pd.DataFrame(self.metrics_buffer)

            # TRUE INCREMENTAL APPEND - no read, just append!
            self.conn.append("metrics", df, by_name=True)
            self.conn.commit()

            logger.debug(
                f"Appended {len(self.metrics_buffer)} metrics rows (INCREMENTAL)"
            )
            self.metrics_buffer.clear()

        except KeyboardInterrupt:
            logger.warning("Metrics flush interrupted")
            self.metrics_buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")
            logger.exception(e)

    def flush_media(self):
        """Flush media buffer to DuckDB (TRUE INCREMENTAL!)"""
        if not self.media_buffer:
            return

        try:
            df = pd.DataFrame(self.media_buffer)
            self.conn.append("media", df, by_name=True)
            self.conn.commit()

            logger.debug(f"Appended {len(self.media_buffer)} media rows (INCREMENTAL)")
            self.media_buffer.clear()

        except KeyboardInterrupt:
            logger.warning("Media flush interrupted")
            self.media_buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush media: {e}")

    def flush_tables(self):
        """Flush tables buffer to DuckDB (TRUE INCREMENTAL!)"""
        if not self.tables_buffer:
            return

        try:
            df = pd.DataFrame(self.tables_buffer)
            self.conn.append("tables", df, by_name=True)
            self.conn.commit()

            logger.debug(f"Appended {len(self.tables_buffer)} table rows (INCREMENTAL)")
            self.tables_buffer.clear()

        except KeyboardInterrupt:
            logger.warning("Tables flush interrupted")
            self.tables_buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush tables: {e}")

    def append_histogram(
        self,
        step: int,
        global_step: Optional[int],
        name: str,
        values: List[float],
        num_bins: int = 64,
    ):
        """Append histogram log entry (pre-computed bins to save space)

        Args:
            step: Auto-increment step
            global_step: Explicit global step
            name: Histogram log name
            values: List of values to create histogram from
            num_bins: Number of bins for histogram
        """
        # Compute histogram (bins + counts) instead of storing raw values
        import numpy as np

        values_array = np.array(values, dtype=np.float32)
        counts, bin_edges = np.histogram(values_array, bins=num_bins)

        row = {
            "step": step,
            "global_step": global_step,
            "name": name,
            "num_bins": num_bins,
            "bins": json.dumps(bin_edges.tolist()),  # Bin edges
            "counts": json.dumps(counts.tolist()),  # Counts per bin
        }
        self.histograms_buffer.append(row)

        # Batch flush when threshold reached (not immediate!)
        if len(self.histograms_buffer) >= self.histogram_flush_threshold:
            self.flush_histograms()

    def flush_histograms(self):
        """Flush histograms buffer to DuckDB (TRUE INCREMENTAL!)"""
        if not self.histograms_buffer:
            return

        try:
            df = pd.DataFrame(self.histograms_buffer)
            self.conn.append("histograms", df, by_name=True)
            self.conn.commit()

            logger.debug(
                f"Appended {len(self.histograms_buffer)} histogram rows (INCREMENTAL)"
            )
            self.histograms_buffer.clear()

        except KeyboardInterrupt:
            logger.warning("Histograms flush interrupted")
            self.histograms_buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush histograms: {e}")

    def flush_all(self):
        """Flush all buffers"""
        self.flush_metrics()
        self.flush_media()
        self.flush_tables()
        self.flush_histograms()
        logger.info("Flushed all buffers to DuckDB")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.debug("Closed DuckDB connection")
