"""Main Board class for non-blocking experiment logging"""

import atexit
import json
import multiprocessing as mp
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from kohakuboard.client.capture import OutputCapture
from kohakuboard.client.media_types import Media, is_media
from kohakuboard.client.table import Table
from kohakuboard.client.writer import writer_process_main


class Board:
    """Board - Main interface for logging ML experiments

    Features:
        - Non-blocking logging using background process
        - Automatic step tracking + explicit global_step
        - Parquet-based storage for efficient queries
        - Media (images) and table logging
        - stdout/stderr capture to log file

    Example:
        >>> # Create board - auto-finishes on program exit via atexit
        >>> board = Board(name="resnet_training", config={"lr": 0.001})
        >>>
        >>> for epoch in range(100):
        ...     board.step()  # Explicit step increment
        ...
        ...     for batch_idx, (data, target) in enumerate(train_loader):
        ...         loss = train_step(data, target)
        ...
        ...         # Log scalars (non-blocking)
        ...         board.log(loss=loss.item(), lr=optimizer.param_groups[0]['lr'])
        ...
        ...         # Log images occasionally
        ...         if batch_idx % 100 == 0:
        ...             board.log_images("predictions", images[:8], caption="Model predictions")
        ...
        ...     # Log table at end of epoch
        ...     board.log_table("metrics", [
        ...         {"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss}
        ...     ])
        ...
        >>> # board.finish() called automatically on program exit
    """

    def __init__(
        self,
        name: str,
        board_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        base_dir: Optional[Union[str, Path]] = None,
        capture_output: bool = True,
        backend: str = "duckdb",
    ):
        """Create a new Board for logging

        Args:
            name: Human-readable name for this board
            board_id: Unique ID (auto-generated if not provided)
            config: Configuration dict for this run (hyperparameters, etc.)
            base_dir: Base directory for boards (default: ./kohakuboard)
            capture_output: Whether to capture stdout/stderr to log file
            backend: Storage backend ("duckdb" or "parquet", default: "duckdb")
        """
        # Validate backend
        if backend not in ("duckdb", "parquet"):
            raise ValueError(
                f"Invalid backend: {backend}. Must be 'duckdb' or 'parquet'"
            )

        # Board metadata
        self.name = name
        self.board_id = board_id or self._generate_id()
        self.config = config or {}
        self.backend = backend
        self.created_at = datetime.now(timezone.utc)

        # Setup directories
        self.base_dir = Path(base_dir) if base_dir else Path.cwd() / "kohakuboard"
        self.board_dir = self.base_dir / self.board_id
        self.board_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.board_dir / "data").mkdir(exist_ok=True)
        (self.board_dir / "media").mkdir(exist_ok=True)
        (self.board_dir / "logs").mkdir(exist_ok=True)

        # Step tracking
        # _step increments on EVERY log/media/table call (auto-increment)
        # _global_step is set explicitly via step() method
        self._step = -1  # Start at -1, will be 0 on first log
        self._global_step: Optional[int] = None

        # Multiprocessing setup
        self.queue = mp.Queue(maxsize=10000)  # Large queue for buffering
        self.stop_event = mp.Event()

        # Start writer process
        self.writer_process = mp.Process(
            target=writer_process_main,
            args=(self.board_dir, self.queue, self.stop_event, self.backend),
            daemon=False,  # Not daemon - we want clean shutdown
        )
        self.writer_process.start()

        # Output capture
        self.capture_output = capture_output
        if capture_output:
            self.output_capture = OutputCapture(self.board_dir / "logs" / "output.log")
            self.output_capture.start()
        else:
            self.output_capture = None

        # Save board metadata
        self._save_metadata()

        # Register cleanup hooks
        atexit.register(self.finish)
        self._register_signal_handlers()

        logger.info(f"Board created: {self.name} (ID: {self.board_id})")
        logger.info(f"Board directory: {self.board_dir}")

    def log(self, **metrics: Union[int, float, Media]):
        """Log scalar metrics or media (non-blocking)

        Supports Python numbers, single-item tensors, numpy arrays, and Media objects.

        Args:
            **metrics: Metric name-value pairs
                      If value is Media object, equivalent to log_media(name, media)

        Example:
            >>> board.log(loss=0.5, accuracy=0.95, lr=0.001)
            >>> board.log(sample_img=Media(image_array))  # Same as log_images("sample_img", ...)
        """
        # Increment step (auto-increment on every log call)
        self._step += 1

        # Separate scalars and media
        scalars = {}
        media_logs = []

        for key, value in metrics.items():
            if is_media(value):
                # Media object - log as media
                media_logs.append((key, value))
            else:
                # Scalar - convert to Python number
                scalars[key] = self._to_python_number(value)

        # Send scalar message if we have scalars
        if scalars:
            message = {
                "type": "scalar",
                "step": self._step,
                "global_step": self._global_step,
                "metrics": scalars,
            }
            self.queue.put(message)

        # Send media messages (each media gets same step since we already incremented)
        for media_name, media_obj in media_logs:
            message = {
                "type": "media",
                "step": self._step,
                "global_step": self._global_step,
                "name": media_name,
                "media_type": media_obj.media_type,
                "media_data": media_obj.data,
                "caption": media_obj.caption,
            }
            self.queue.put(message)

    def log_images(
        self,
        name: str,
        images: Union[Any, List[Any]],
        caption: Optional[str] = None,
    ):
        """Log images (non-blocking)

        Supports: PIL Images, numpy arrays, torch Tensors, file paths

        Args:
            name: Name for this media log
            images: Single image or list of images
            caption: Optional caption

        Example:
            >>> # Single image
            >>> board.log_images("prediction", pred_image)
            >>>
            >>> # Multiple images
            >>> board.log_images("samples", [img1, img2, img3], caption="Generated samples")
        """
        # Increment step (auto-increment on every log call)
        self._step += 1

        # Ensure list
        if not isinstance(images, (list, tuple)):
            images = [images]

        message = {
            "type": "media",
            "step": self._step,
            "global_step": self._global_step,
            "name": name,
            "images": images,
            "caption": caption,
        }
        self.queue.put(message)

    def log_video(
        self, name: str, video_path: Union[str, Path], caption: Optional[str] = None
    ):
        """Log video file (non-blocking)

        Args:
            name: Name for this video log
            video_path: Path to video file (mp4, avi, mov, mkv, webm, etc.)
            caption: Optional caption

        Example:
            >>> board.log_video("training_progress", "output.mp4", caption="Training visualization")
        """
        self._step += 1

        message = {
            "type": "media",
            "step": self._step,
            "global_step": self._global_step,
            "name": name,
            "media_type": "video",
            "media_data": video_path,
            "caption": caption,
        }
        self.queue.put(message)

    def log_audio(
        self, name: str, audio_path: Union[str, Path], caption: Optional[str] = None
    ):
        """Log audio file (non-blocking)

        Args:
            name: Name for this audio log
            audio_path: Path to audio file (mp3, wav, flac, ogg, etc.)
            caption: Optional caption

        Example:
            >>> board.log_audio("generated_speech", "output.wav", caption="TTS output")
        """
        self._step += 1

        message = {
            "type": "media",
            "step": self._step,
            "global_step": self._global_step,
            "name": name,
            "media_type": "audio",
            "media_data": audio_path,
            "caption": caption,
        }
        self.queue.put(message)

    def log_table(self, name: str, table: Union[Table, List[Dict[str, Any]]]):
        """Log table data (non-blocking)

        Args:
            name: Name for this table log
            table: Table object or list of dicts

        Example:
            >>> # From list of dicts
            >>> board.log_table("results", [
            ...     {"epoch": 1, "loss": 0.5, "acc": 0.9},
            ...     {"epoch": 2, "loss": 0.3, "acc": 0.95},
            ... ])
            >>>
            >>> # Using Table class
            >>> from kohakuboard.client import Table
            >>> table = Table([{"name": "Alice", "score": 95}])
            >>> board.log_table("scores", table)
        """
        # Increment step (auto-increment on every log call)
        self._step += 1

        # Convert to Table if needed
        if not isinstance(table, Table):
            table = Table(table)

        message = {
            "type": "table",
            "step": self._step,
            "global_step": self._global_step,
            "name": name,
            "table_data": table.to_dict(),
        }
        self.queue.put(message)

    def step(self, increment: int = 1):
        """Explicit step increment

        This sets the global_step. All logs between step() calls
        belong to the previous global_step value.

        Args:
            increment: Step increment (default: 1)

        Example:
            >>> for epoch in range(100):
            ...     board.step()  # global_step = 0, 1, 2, ...
            ...     for batch in train_loader:
            ...         loss = train_step(batch)
            ...         board.log(loss=loss)  # All batches share same global_step
        """
        if self._global_step is None:
            self._global_step = 0
        else:
            self._global_step += increment

    def flush(self):
        """Flush all pending logs to disk (blocking)

        Normally logs are flushed automatically. Use this for
        critical checkpoints or before long-running operations.
        """
        message = {"type": "flush"}
        self.queue.put(message)

    def finish(self):
        """Finish logging and clean up

        Flushes all buffers, stops writer process, and releases resources.
        Called automatically on exit, Ctrl+C, or exceptions.
        """
        if not hasattr(self, "writer_process"):
            return  # Already finished

        logger.info(f"Finishing board: {self.name}")

        # Stop output capture
        if self.output_capture:
            self.output_capture.stop()

        # Signal writer to stop
        self.stop_event.set()

        # Give writer a moment to start draining queue
        time.sleep(0.1)

        # Check queue size and wait for processing
        try:
            queue_size = self.queue.qsize()
        except NotImplementedError:
            queue_size = 0  # Some platforms don't support qsize()

        if queue_size > 0:
            logger.info(
                f"Waiting for writer to process {queue_size} remaining messages..."
            )
            # Wait longer if queue has many messages
            time.sleep(min(2.0, queue_size * 0.01))

        # Wait for writer to finish with generous timeout
        timeout = max(10, queue_size * 0.02)  # At least 10s, plus 20ms per message
        self.writer_process.join(timeout=timeout)

        if self.writer_process.is_alive():
            logger.warning(
                "Writer process did not stop gracefully, terminating forcefully..."
            )
            self.writer_process.terminate()
            self.writer_process.join(timeout=2)

            # Force kill if still alive
            if self.writer_process.is_alive():
                logger.error("Writer process still alive, killing...")
                self.writer_process.kill()
                self.writer_process.join(timeout=1)

        logger.info(f"Board finished: {self.name}")

        # Remove finish method to prevent double-call
        delattr(self, "writer_process")

    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown

        Handles:
        - SIGINT (Ctrl+C)
        - SIGTERM (kill command)
        - Uncaught exceptions
        """

        def signal_handler(signum, frame):
            """Handle termination signals"""
            sig_name = signal.Signals(signum).name
            logger.warning(f"Received {sig_name}, shutting down gracefully...")
            try:
                self.finish()
            except Exception as e:
                logger.error(f"Error during signal handler cleanup: {e}")
            finally:
                sys.exit(0)

        # Register signal handlers (Ctrl+C, kill)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Hook into sys.excepthook for uncaught exceptions
        original_excepthook = sys.excepthook

        def exception_handler(exc_type, exc_value, exc_traceback):
            """Handle uncaught exceptions"""
            logger.error(f"Uncaught exception: {exc_type.__name__}: {exc_value}")
            logger.error("Attempting graceful shutdown...")
            try:
                self.finish()
            except Exception as e:
                logger.error(f"Error during exception cleanup: {e}")
            # Call original excepthook to print traceback
            original_excepthook(exc_type, exc_value, exc_traceback)

        sys.excepthook = exception_handler

    def _to_python_number(self, value: Any) -> Union[int, float]:
        """Convert various numeric types to Python number"""
        # Already Python number
        if isinstance(value, (int, float)):
            return value

        # Numpy
        if hasattr(value, "item"):
            return value.item()

        # Torch tensor
        if hasattr(value, "cpu"):
            return value.detach().cpu().item()

        raise ValueError(f"Cannot convert {type(value)} to number")

    def _generate_id(self) -> str:
        """Generate unique board ID"""
        # Use timestamp + random UUID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"{timestamp}_{unique_id}"

    def _save_metadata(self):
        """Save board metadata to JSON"""
        metadata = {
            "name": self.name,
            "board_id": self.board_id,
            "config": self.config,
            "backend": self.backend,
            "created_at": self.created_at.isoformat(),
        }

        metadata_file = self.board_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def __repr__(self) -> str:
        return f"Board(name={self.name!r}, id={self.board_id!r})"

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.flush()
        self.finish()
