#!/usr/bin/env python3
"""
Flexible dataset generator for testing.

Usage:
    python scripts/generate_test_dataset.py --rows 1000 --cols 20 --format csv --output test.csv
    python scripts/generate_test_dataset.py --rows 1000000 --cols 30 --format parquet --output huge.parquet
"""

import argparse
import csv
import json
import random
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# Word list for generating text
WORDS = [
    "the",
    "quick",
    "brown",
    "fox",
    "jumps",
    "over",
    "lazy",
    "dog",
    "machine",
    "learning",
    "artificial",
    "intelligence",
    "neural",
    "network",
    "data",
    "science",
    "python",
    "javascript",
    "algorithm",
    "optimization",
    "performance",
    "scalability",
    "database",
    "cloud",
    "api",
    "framework",
    "security",
    "encryption",
]


def generate_value(col_type: str, row_id: int):
    """Generate a value based on column type."""
    if col_type == "id":
        return row_id
    elif col_type == "int":
        return random.randint(0, 1000000)
    elif col_type == "float":
        return round(random.uniform(0, 1000), 2)
    elif col_type == "bool":
        return random.choice([True, False])
    elif col_type == "date":
        days_ago = random.randint(0, 3650)
        return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    elif col_type == "datetime":
        days_ago = random.randint(0, 365)
        return (datetime.now() - timedelta(days=days_ago)).isoformat() + "Z"
    elif col_type == "short_text":
        # 1-3 words
        return " ".join(random.choices(WORDS, k=random.randint(1, 3)))
    elif col_type == "text":
        # 5-20 words
        return " ".join(random.choices(WORDS, k=random.randint(5, 20)))
    elif col_type == "long_text":
        # 20-100 words
        return " ".join(random.choices(WORDS, k=random.randint(20, 100)))
    elif col_type == "very_long_text":
        # 100-300 words
        return " ".join(random.choices(WORDS, k=random.randint(100, 300)))
    else:
        return f"value_{row_id}"


def generate_column_schema(num_cols: int) -> list[dict]:
    """Generate column schema with meaningful names."""
    # Predefined meaningful column names with types
    predefined_columns = [
        {"name": "id", "type": "id"},
        {"name": "user_id", "type": "int"},
        {"name": "age", "type": "int"},
        {"name": "score", "type": "float"},
        {"name": "rating", "type": "float"},
        {"name": "is_active", "type": "bool"},
        {"name": "is_verified", "type": "bool"},
        {"name": "created_at", "type": "datetime"},
        {"name": "updated_at", "type": "datetime"},
        {"name": "birth_date", "type": "date"},
        {"name": "username", "type": "short_text"},
        {"name": "email", "type": "short_text"},
        {"name": "name", "type": "short_text"},
        {"name": "title", "type": "text"},
        {"name": "description", "type": "text"},
        {"name": "category", "type": "short_text"},
        {"name": "status", "type": "short_text"},
        {"name": "comment", "type": "long_text"},
        {"name": "review", "type": "long_text"},
        {"name": "content", "type": "very_long_text"},
        {"name": "price", "type": "float"},
        {"name": "quantity", "type": "int"},
        {"name": "views", "type": "int"},
        {"name": "likes", "type": "int"},
        {"name": "tags", "type": "text"},
        {"name": "metadata", "type": "text"},
        {"name": "notes", "type": "long_text"},
        {"name": "address", "type": "text"},
        {"name": "city", "type": "short_text"},
        {"name": "country", "type": "short_text"},
    ]

    columns = []

    # Use predefined columns first
    for i in range(min(num_cols, len(predefined_columns))):
        columns.append(predefined_columns[i])

    # If we need more columns, generate with numbered suffix
    if num_cols > len(predefined_columns):
        type_distribution = {
            "int": 0.2,
            "float": 0.15,
            "bool": 0.1,
            "date": 0.1,
            "short_text": 0.15,
            "text": 0.15,
            "long_text": 0.1,
            "very_long_text": 0.05,
        }

        types = list(type_distribution.keys())
        weights = list(type_distribution.values())

        for i in range(len(predefined_columns), num_cols):
            col_type = random.choices(types, weights=weights)[0]
            columns.append({"name": f"field_{i}_{col_type}", "type": col_type})

    return columns


def generate_csv(output_path: Path, num_rows: int, num_cols: int):
    """Generate CSV file."""
    print(f"Generating CSV: {num_rows:,} rows × {num_cols} columns")

    schema = generate_column_schema(num_cols)
    fieldnames = [col["name"] for col in schema]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        batch_size = 10000
        for batch_start in range(0, num_rows, batch_size):
            batch_end = min(batch_start + batch_size, num_rows)
            # Print progress every 5 batches (every 50k rows)
            if batch_start % (batch_size * 5) == 0:
                print(f"  Writing rows {batch_start:,} to {batch_end:,}...")

            for row_id in range(batch_start, batch_end):
                row = {
                    col["name"]: generate_value(col["type"], row_id) for col in schema
                }
                writer.writerow(row)

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  [OK] Created {output_path} ({size_mb:.1f} MB)")


def generate_jsonl(output_path: Path, num_rows: int, num_cols: int):
    """Generate JSONL file."""
    print(f"Generating JSONL: {num_rows:,} rows × {num_cols} columns")

    schema = generate_column_schema(num_cols)

    with open(output_path, "w", encoding="utf-8") as f:
        batch_size = 10000
        for batch_start in range(0, num_rows, batch_size):
            batch_end = min(batch_start + batch_size, num_rows)
            # Print progress every 5 batches (every 50k rows)
            if batch_start % (batch_size * 5) == 0:
                print(f"  Writing rows {batch_start:,} to {batch_end:,}...")

            for row_id in range(batch_start, batch_end):
                row = {
                    col["name"]: generate_value(col["type"], row_id) for col in schema
                }
                f.write(json.dumps(row) + "\n")

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  [OK] Created {output_path} ({size_mb:.1f} MB)")


def generate_parquet(output_path: Path, num_rows: int, num_cols: int):
    """Generate Parquet file."""
    print(f"Generating Parquet: {num_rows:,} rows × {num_cols} columns")

    schema = generate_column_schema(num_cols)

    # Generate in batches to avoid memory issues
    batch_size = 50000
    writer = None
    arrow_schema = None

    for batch_start in range(0, num_rows, batch_size):
        batch_end = min(batch_start + batch_size, num_rows)
        # Print progress every 100k rows (every 2 batches of 50k)
        if batch_start % 100000 == 0:
            progress_end = min(batch_start + 100000, num_rows)
            print(f"  Processing rows {batch_start:,} to {progress_end:,}...")

        # Generate batch data
        data = []
        for row_id in range(batch_start, batch_end):
            row = {col["name"]: generate_value(col["type"], row_id) for col in schema}
            data.append(row)

        # Convert to PyArrow table
        table = pa.Table.from_pylist(data)

        # Initialize writer on first batch
        if writer is None:
            arrow_schema = table.schema
            writer = pq.ParquetWriter(
                output_path, arrow_schema, compression="snappy", use_dictionary=True
            )

        # Write batch
        writer.write_table(table)

    # Close writer
    if writer:
        writer.close()

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  [OK] Created {output_path} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate test datasets with configurable size and format"
    )
    parser.add_argument(
        "--rows", type=int, required=True, help="Number of rows to generate"
    )
    parser.add_argument(
        "--cols", type=int, required=True, help="Number of columns to generate"
    )
    parser.add_argument(
        "--format",
        type=str,
        required=True,
        choices=["csv", "jsonl", "parquet"],
        help="Output format",
    )
    parser.add_argument("--output", type=str, required=True, help="Output file path")

    args = parser.parse_args()

    output_path = Path(args.output)

    # Validate
    if args.rows <= 0:
        print("Error: rows must be positive")
        return

    if args.cols <= 0:
        print("Error: cols must be positive")
        return

    # Generate
    print("=" * 60)
    print(f"Dataset Generator")
    print(f"  Rows: {args.rows:,}")
    print(f"  Columns: {args.cols}")
    print(f"  Format: {args.format}")
    print(f"  Output: {output_path}")
    print("=" * 60)

    if args.format == "csv":
        generate_csv(output_path, args.rows, args.cols)
    elif args.format == "jsonl":
        generate_jsonl(output_path, args.rows, args.cols)
    elif args.format == "parquet":
        generate_parquet(output_path, args.rows, args.cols)

    print("=" * 60)
    print("[SUCCESS] Dataset generated!")


if __name__ == "__main__":
    main()
