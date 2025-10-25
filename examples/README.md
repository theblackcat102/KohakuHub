# KohakuBoard Client Examples

This directory contains example scripts demonstrating how to use the KohakuBoard client library.

## Installation

```bash
# Install dependencies (DuckDB backend - recommended, default)
pip install duckdb pandas pillow loguru

# Optional: For Parquet backend (legacy)
pip install pyarrow

# Optional: For Jupyter notebook viewer
pip install jupyter matplotlib

# Or install in development mode
pip install -e .
```

## Important: Windows Users

On Windows, multiprocessing requires the `if __name__ == "__main__":` guard. All examples include this, but when writing your own scripts, make sure to use:

```python
from kohakuboard.client import Board

def main():
    board = Board(name="my_experiment")
    # ... your training code ...

if __name__ == "__main__":
    main()
```

**Why?** Windows uses `spawn` instead of `fork` for multiprocessing, which requires the main module to be importable without side effects.

## Examples

### 1. Basic Usage (`kohakuboard_basic.py`)

Simple logging of scalar metrics without explicit step tracking.

```bash
python examples/kohakuboard_basic.py
```

**Features demonstrated:**
- Creating a board with configuration
- Logging scalar metrics (non-blocking)
- Auto-increment step tracking
- Flushing and finishing

**Output:** `./kohakuboard/<board_id>/data/board.duckdb` (DuckDB) or `metrics.parquet` (Parquet)

---

### 2. Advanced Usage (`kohakuboard_advanced.py`)

Complete training simulation with images, tables, and explicit steps.

```bash
python examples/kohakuboard_advanced.py
```

**Features demonstrated:**
- Context manager usage (automatic cleanup)
- Explicit step tracking (`board.step()`)
- Logging images from numpy arrays
- Logging tables with class metrics
- Epoch-based training simulation

**Output:**
- `./kohakuboard/<board_id>/data/board.duckdb` - All data (DuckDB backend)
  - OR `metrics.parquet`, `media.parquet`, `tables.parquet` (Parquet backend)
- `./kohakuboard/<board_id>/media/*.png` - Actual image files

---

### 4. Interactive Viewer (`view_board_duckdb.ipynb`)

Jupyter notebook for exploring board data interactively.

```bash
# From project root
jupyter notebook examples/view_board_duckdb.ipynb
```

**Features:**
- Auto-finds latest board
- Supports both DuckDB and Parquet backends
- SQL queries with results
- Plot metrics by global_step
- Display images inline
- Export to CSV
- Database statistics

---

### 3. Explicit Steps Deep Dive (`kohakuboard_explicit_steps.py`)

Detailed demonstration of the dual-step tracking system.

```bash
python examples/kohakuboard_explicit_steps.py
```

**Features demonstrated:**
- Difference between `step` (auto-increment) and `global_step` (explicit)
- How to use `global_step` for epoch tracking
- How all batches in an epoch share the same `global_step`

**Key Concept:**
```
auto_step (column: step):
  - Increments automatically on every log call
  - Used for: Timeline, sequential ordering

global_step (column: global_step):
  - Controlled explicitly via board.step()
  - Used for: Epochs, checkpoints, phases
  - All logs between step() calls share same global_step
```

---

## Directory Structure After Running Examples

**DuckDB Backend (default):**
```
kohakuboard/
└── <board_id>/              # e.g., 20250126_153045_a1b2c3d4
    ├── metadata.json        # Board info, config, backend type
    ├── data/
    │   └── board.duckdb     # Single database (metrics, media, tables)
    ├── media/               # Actual media files
    │   ├── predictions_0_00000000_abc123.png
    │   └── ...
    └── logs/
        ├── output.log       # Captured stdout/stderr
        └── writer.log       # Writer process logs
```

**Parquet Backend (legacy):**
```
kohakuboard/
└── <board_id>/
    ├── metadata.json
    ├── data/
    │   ├── metrics.parquet  # Scalar metrics
    │   ├── media.parquet    # Image metadata
    │   └── tables.parquet   # Table data
    ├── media/               # Actual media files
    └── logs/
```

---

## Using the Data

### Option 1: Jupyter Notebook (Recommended)

Use the interactive viewer notebook:

```bash
jupyter notebook examples/view_board_duckdb.ipynb
```

Features:
- Auto-finds latest board
- SQL queries with visualization
- Display images inline
- Export to CSV

### Option 2: Python Script (DuckDB)

```python
import duckdb

# Connect to board
conn = duckdb.connect("kohakuboard/<board_id>/data/board.duckdb", read_only=True)

# Query metrics with SQL
df = conn.execute("""
    SELECT * FROM metrics
    WHERE global_step = 0
    ORDER BY step
""").df()

# Get all available metrics
metrics = conn.execute("SELECT * FROM metrics").df()

# Query media
media = conn.execute("SELECT * FROM media WHERE type = 'image'").df()

# Close connection
conn.close()
```

### Option 3: Python Script (Parquet Backend)

```python
import pandas as pd

# Read metrics
df = pd.read_parquet("kohakuboard/<board_id>/data/metrics.parquet")

# Query by global_step
epoch_0 = df[df["global_step"] == 0]

# Read media
media_df = pd.read_parquet("kohakuboard/<board_id>/data/media.parquet")
```

---

## Best Practices

1. **Just create the board and let atexit handle cleanup:**
   ```python
   # Create board at the start of your training script
   board = Board(name="my_experiment", config={"lr": 0.001})

   # Your existing training loop - no changes needed!
   for epoch in range(100):
       board.step()
       for batch in train_loader:
           board.log(loss=...)

   # Board automatically finishes on program exit (atexit hook)
   # Or call board.finish() explicitly if needed
   ```

   **Why not `with`?** - Integrating into existing training loops is easier without
   restructuring your code into a `with` block.

2. **Use explicit steps for epochs/phases:**
   ```python
   for epoch in range(100):
       board.step()  # Set global_step
       for batch in train_loader:
           board.log(loss=...)  # All batches share epoch's global_step
   ```

3. **Flush before long-running operations:**
   ```python
   board.log(checkpoint="saving...")
   board.flush()  # Ensure log is written
   save_checkpoint(model)  # Long operation
   ```

4. **Use descriptive metric names:**
   ```python
   # Good
   board.log(train_loss=0.5, val_accuracy=0.95)

   # Avoid
   board.log(loss=0.5, acc=0.95)
   ```

5. **Log images selectively:**
   ```python
   # Don't log every batch
   if batch_idx % 100 == 0:
       board.log_images("samples", images)
   ```

---

## Performance Notes

- **Non-blocking:** All `board.log*()` calls are non-blocking (return immediately)
- **Background writer:** Separate process handles all disk I/O
- **DuckDB (default):**
  - True incremental append (no read overhead!)
  - Automatic compression (RLE, bit-packing, dictionary)
  - ACID transactions
  - Single file storage
- **Parquet (legacy):**
  - Read-concat-write (slower)
  - Manual compression (Snappy)
  - Multiple files
- **Deduplication:** Images are content-addressed (duplicate images share storage)

---

## Troubleshooting

**Board doesn't finish gracefully:**
- Always call `board.finish()` or use context manager
- Check `logs/writer.log` for errors

**Images not saving:**
- Make sure PIL is installed: `pip install pillow`
- Check `logs/writer.log` for conversion errors

**High memory usage:**
- Reduce queue size: `board.queue = mp.Queue(maxsize=1000)`
- Flush more frequently: `board.flush()`

**DuckDB errors:**
- Install duckdb: `pip install duckdb`
- Check file permissions on board.duckdb

**Parquet read errors:**
- Install pyarrow: `pip install pyarrow`
- Check file permissions

**Want to use Parquet instead of DuckDB:**
```python
board = Board(name="my_experiment", backend="parquet")
```

---

## Backend Comparison

| Feature | DuckDB (default) | Parquet (legacy) |
|---------|------------------|------------------|
| **Incremental Append** | ✅ True (no read!) | ❌ Read-concat-write |
| **Compression** | ✅ Automatic (adaptive) | ✅ Manual (Snappy/ZSTD) |
| **Schema Evolution** | ✅ ALTER TABLE (instant) | ❌ Full file rewrite |
| **Query** | ✅ SQL (native) | ✅ SQL (via DuckDB read) |
| **Write Performance** | ✅ Fast (append-only) | ❌ Slow (rewrite entire file) |
| **Files** | ✅ Single .duckdb | ⚠️ 3 separate files |
| **File Size** | ✅ Smaller (better compression) | ✅ Small (columnar) |
| **Portability** | ⚠️ DuckDB-specific | ✅ Standard Parquet |

**Note:** Both can be queried with SQL (DuckDB can read Parquet files). The key difference is **write performance** - DuckDB uses true incremental append, while Parquet requires reading and rewriting the entire file.

**Recommendation:** Use DuckDB (default) for better write performance and automatic compression. Use Parquet only if you need compatibility with other tools that can't read DuckDB files.

---

## Next Steps

- View boards in KohakuBoard UI
- Use Jupyter notebook for interactive exploration
- Query with SQL (DuckDB backend)
- Export to CSV, JSON
- Sync to remote storage (coming soon)
- Share boards with team (coming soon)
