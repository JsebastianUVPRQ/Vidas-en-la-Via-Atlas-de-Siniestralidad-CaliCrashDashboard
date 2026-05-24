"""Print a lightweight profile of downloaded external crash datasets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_sources import RAW_EXTERNAL_DIR, selected_sources


def main() -> None:
    """Profile downloaded raw CSV files using catalog metadata."""
    parser = argparse.ArgumentParser(
        description="Profile downloaded official crash datasets.",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Source id to profile. Can be passed multiple times.",
    )
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Include optional configured sources.",
    )
    parser.add_argument(
        "--input-dir",
        default=str(RAW_EXTERNAL_DIR),
        help="Directory where raw CSV files are stored.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    for source in selected_sources(args.sources, include_optional=args.include_optional):
        path = input_dir / source.output_filename
        if not path.exists():
            print(f"{source.source_id}: missing ({path})")
            continue

        sample = pd.read_csv(
            path,
            nrows=5,
            sep=source.csv_separator,
            encoding=source.encoding,
        )
        rows = max(sum(1 for _ in path.open("rb")) - 1, 0)
        size_mb = path.stat().st_size / (1024 * 1024)
        columns = ", ".join(str(column) for column in sample.columns[:8])
        print(
            f"{source.source_id}: {rows:,} rows, {len(sample.columns)} columns, "
            f"{size_mb:.2f} MB"
        )
        print(f"  columns: {columns}")


if __name__ == "__main__":
    main()
