"""Utility functions for reading board data from DuckDB files"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
from loguru import logger


class BoardReader:
    """Read-only interface for accessing board data"""

    def __init__(self, board_dir: Path):
        """Initialize board reader

        Args:
            board_dir: Path to board directory
        """
        self.board_dir = Path(board_dir)
        self.metadata_path = self.board_dir / "metadata.json"
        self.db_path = self.board_dir / "data" / "board.duckdb"
        self.media_dir = self.board_dir / "media"

        # Validate paths
        if not self.board_dir.exists():
            raise FileNotFoundError(f"Board directory not found: {board_dir}")

    def get_metadata(self) -> Dict[str, Any]:
        """Get board metadata

        Returns:
            Metadata dict with board info, config, timestamps
        """
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_path}")

        with open(self.metadata_path, "r") as f:
            return json.load(f)

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get read-only DuckDB connection

        Returns:
            DuckDB connection
        """
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        return duckdb.connect(str(self.db_path), read_only=True)

    def get_available_metrics(self) -> List[str]:
        """Get list of available scalar metrics

        Returns:
            List of metric names (INCLUDING step/global_step for x-axis selection)
        """
        conn = self._get_connection()
        try:
            # Get all columns from metrics table
            result = conn.execute("PRAGMA table_info(metrics)").fetchall()
            columns = [row[1] for row in result]  # Column name is at index 1

            # Return all columns (including step, global_step, timestamp for x-axis)
            # step, global_step, timestamp should be first for better UX
            # Also convert "__" back to "/" for namespace support
            axis_cols = [
                col for col in columns if col in ("step", "global_step", "timestamp")
            ]
            other_cols = [
                col.replace("__", "/")  # Convert back to namespace format
                for col in columns
                if col not in ("step", "global_step", "timestamp")
            ]

            return axis_cols + other_cols
        finally:
            conn.close()

    def get_scalar_data(
        self, metric: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get scalar data for a specific metric

        Args:
            metric: Metric name (can be 'step', 'global_step', or any other metric)
            limit: Optional row limit

        Returns:
            List of dicts with step, global_step, value
        """
        conn = self._get_connection()
        try:
            # Special handling for step/global_step/timestamp - they're already included
            # Escape metric name (convert "/" to "__" for DuckDB column name)
            escaped_metric = metric.replace("/", "__")

            # Build query - always select step, global_step, timestamp, and the requested metric
            query = f'SELECT step, global_step, timestamp, "{escaped_metric}" as value FROM metrics'

            # For regular metrics, filter out NULLs
            # For step/global_step/timestamp, include all rows (they're never NULL)
            if metric not in ("step", "global_step", "timestamp"):
                query += f' WHERE "{escaped_metric}" IS NOT NULL'

            if limit:
                query += f" LIMIT {limit}"

            result = conn.execute(query).fetchall()

            # Convert to list of dicts
            return [
                {
                    "step": row[0],
                    "global_step": row[1],
                    "timestamp": row[2].isoformat() if row[2] else None,
                    "value": row[3],
                }
                for row in result
            ]
        finally:
            conn.close()

    def get_available_media_names(self) -> List[str]:
        """Get list of available media log names

        Returns:
            List of unique media log names
        """
        conn = self._get_connection()
        try:
            result = conn.execute(
                "SELECT DISTINCT name FROM media ORDER BY name"
            ).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.warning(f"Failed to query media table: {e}")
            return []
        finally:
            conn.close()

    def get_media_data(
        self, name: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get media data for a specific log name

        Args:
            name: Media log name
            limit: Optional row limit

        Returns:
            List of dicts with step, global_step, caption, media metadata
        """
        conn = self._get_connection()
        try:
            query = f"SELECT * FROM media WHERE name = ?"
            if limit:
                query += f" LIMIT {limit}"

            result = conn.execute(query, [name]).fetchall()

            # Get column names
            columns = [desc[0] for desc in conn.description]

            # Convert to list of dicts
            return [dict(zip(columns, row)) for row in result]
        finally:
            conn.close()

    def get_available_table_names(self) -> List[str]:
        """Get list of available table log names

        Returns:
            List of unique table log names
        """
        conn = self._get_connection()
        try:
            result = conn.execute(
                "SELECT DISTINCT name FROM tables ORDER BY name"
            ).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.warning(f"Failed to query tables table: {e}")
            return []
        finally:
            conn.close()

    def get_table_data(
        self, name: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get table data for a specific log name

        Args:
            name: Table log name
            limit: Optional row limit

        Returns:
            List of dicts with step, global_step, columns, column_types, rows
        """
        conn = self._get_connection()
        try:
            query = f"SELECT * FROM tables WHERE name = ?"
            if limit:
                query += f" LIMIT {limit}"

            result = conn.execute(query, [name]).fetchall()

            # Get column names
            columns = [desc[0] for desc in conn.description]

            # Convert to list of dicts, parsing JSON fields
            data = []
            for row in result:
                row_dict = dict(zip(columns, row))

                # Parse JSON fields
                if row_dict.get("columns"):
                    row_dict["columns"] = json.loads(row_dict["columns"])
                if row_dict.get("column_types"):
                    row_dict["column_types"] = json.loads(row_dict["column_types"])
                if row_dict.get("rows"):
                    row_dict["rows"] = json.loads(row_dict["rows"])

                data.append(row_dict)

            return data
        finally:
            conn.close()

    def get_available_histogram_names(self) -> List[str]:
        """Get list of available histogram log names

        Returns:
            List of unique histogram log names
        """
        conn = self._get_connection()
        try:
            result = conn.execute(
                "SELECT DISTINCT name FROM histograms ORDER BY name"
            ).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.warning(f"Failed to query histograms table: {e}")
            return []
        finally:
            conn.close()

    def get_histogram_data(
        self, name: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get histogram data for a specific log name

        Args:
            name: Histogram log name
            limit: Optional row limit

        Returns:
            List of dicts with step, global_step, bins, values
        """
        conn = self._get_connection()
        try:
            query = f"SELECT * FROM histograms WHERE name = ?"
            if limit:
                query += f" LIMIT {limit}"

            result = conn.execute(query, [name]).fetchall()

            # Get column names
            columns = [desc[0] for desc in conn.description]

            # Convert to list of dicts, parsing JSON fields
            data = []
            for row in result:
                row_dict = dict(zip(columns, row))

                # Parse JSON bins and counts fields
                if row_dict.get("bins"):
                    row_dict["bins"] = json.loads(row_dict["bins"])
                if row_dict.get("counts"):
                    row_dict["counts"] = json.loads(row_dict["counts"])

                data.append(row_dict)

            return data
        finally:
            conn.close()

    def get_media_file_path(self, filename: str) -> Optional[Path]:
        """Get full path to media file

        Args:
            filename: Media filename

        Returns:
            Full path to media file, or None if not found
        """
        media_path = self.media_dir / filename
        if media_path.exists():
            return media_path
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get board summary with available data

        Returns:
            Dict with metadata, metrics, media, tables counts
        """
        conn = self._get_connection()
        try:
            metadata = self.get_metadata()

            # Count rows
            metrics_count = conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]

            try:
                media_count = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]
            except Exception:
                media_count = 0

            try:
                tables_count = conn.execute("SELECT COUNT(*) FROM tables").fetchone()[0]
            except Exception:
                tables_count = 0

            try:
                histograms_count = conn.execute(
                    "SELECT COUNT(*) FROM histograms"
                ).fetchone()[0]
            except Exception:
                histograms_count = 0

            return {
                "metadata": metadata,
                "metrics_count": metrics_count,
                "media_count": media_count,
                "tables_count": tables_count,
                "histograms_count": histograms_count,
                "available_metrics": self.get_available_metrics(),
                "available_media": self.get_available_media_names(),
                "available_tables": self.get_available_table_names(),
                "available_histograms": self.get_available_histogram_names(),
            }
        finally:
            conn.close()


def list_boards(base_dir: Path) -> List[Dict[str, Any]]:
    """List all boards in base directory

    Args:
        base_dir: Base directory containing boards

    Returns:
        List of dicts with board_id and metadata
    """
    base_dir = Path(base_dir)
    if not base_dir.exists():
        logger.warning(f"Board data directory does not exist: {base_dir}")
        return []

    boards = []
    for board_dir in base_dir.iterdir():
        if not board_dir.is_dir():
            continue

        # Check if it has metadata.json
        metadata_path = board_dir / "metadata.json"
        if not metadata_path.exists():
            continue

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            boards.append(
                {
                    "board_id": board_dir.name,
                    "name": metadata.get("name", board_dir.name),
                    "created_at": metadata.get("created_at"),
                    "updated_at": metadata.get("updated_at"),
                    "config": metadata.get("config", {}),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to read metadata for {board_dir.name}: {e}")

    return sorted(boards, key=lambda x: x.get("created_at", ""), reverse=True)
