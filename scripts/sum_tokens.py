#!/usr/bin/env python3
"""
Sum token fields in JSON log(s).

Usage:
  python sum_tokens.py [path]

If path is a file, sums tokens in that JSON log.
If path is a directory, recursively processes all .json files under it.
Default path is logs.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# Fields to sum (look for embedded usage blocks)
TARGET_KEYS = [
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
]
PATTERNS = {k: re.compile(rf'"{k}"\s*:\s*(\d+)') for k in TARGET_KEYS}

# Cost rates per token (dollars per token)
COST_RATES = {
    "input_tokens": 3.0 / 1_000_000,
    "cache_creation_input_tokens": 3.75 / 1_000_000,
    "cache_read_input_tokens": 0.30 / 1_000_000,
    "output_tokens": 15.0 / 1_000_000,
}


def find_and_sum(obj, sums):
    """Recursively find TARGET_KEYS in obj (including embedded text) and accumulate their values in sums."""
    # If string, search for embedded JSON-like patterns
    if isinstance(obj, str):
        for key, pattern in PATTERNS.items():
            for m in pattern.findall(obj):
                try:
                    sums[key] += int(m)
                except (ValueError, TypeError):
                    pass
    # If dict, check for numeric values under target keys and recurse
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in sums:
                try:
                    sums[k] += int(v)
                except (ValueError, TypeError):
                    pass
            find_and_sum(v, sums)
    # If list, recurse into items
    elif isinstance(obj, list):
        for item in obj:
            find_and_sum(item, sums)


def main():
    parser = argparse.ArgumentParser(description="Sum token fields in JSON log(s).")
    parser.add_argument(
        "path",
        nargs="?",
        default="logs",
        help="Path to JSON log file or directory (default: logs)",
    )
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Error: path {path} does not exist.", file=sys.stderr)
        sys.exit(1)

    # Collect JSON files to process
    files = []
    if path.is_file():
        files = [path]
    elif path.is_dir():
        for root, _, filenames in os.walk(path):
            for name in filenames:
                if name.lower().endswith(".json"):
                    files.append(Path(root) / name)
        if not files:
            print(f"No JSON files found in directory {path}.", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error: path {path} is not a file or directory.", file=sys.stderr)
        sys.exit(1)

    # Initialize sums
    global_sums = {k: 0 for k in TARGET_KEYS}
    results = []

    # Process each file
    for file in sorted(files):
        try:
            with file.open("r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading JSON from {file}: {e}", file=sys.stderr)
            continue

        sums = {k: 0 for k in TARGET_KEYS}
        find_and_sum(data, sums)
        # Accumulate into global sums
        for k in TARGET_KEYS:
            global_sums[k] += sums[k]
        results.append((file, sums))

    # Output per-file results with token sums and cost breakdown
    if results:
        for file, sums in results:
            print(f"File: {file}")
            for k in TARGET_KEYS:
                print(f"  {k}: {sums[k]}")
            # Per-file totals and cost
            file_total = sum(sums.values())
            print(f"  Total tokens: {file_total}")
            print("  Cost breakdown:")
            file_cost = 0.0
            for k in TARGET_KEYS:
                rate = COST_RATES.get(k, 0)
                cost = sums[k] * rate
                file_cost += cost
                print(f"    {k}: ${cost:.2f}")
            print(f"  Total cost: ${file_cost:.2f}\n")
    # Print global totals
    print("Global sums:")
    for k in TARGET_KEYS:
        print(f"  {k}: {global_sums[k]}")

    total = sum(global_sums.values())
    print(f"TOTAL tokens: {total}")
    # Print estimated cost
    print("\nEstimated cost ($):")
    total_cost = 0.0
    for k in TARGET_KEYS:
        rate = COST_RATES.get(k, 0)
        cost = global_sums[k] * rate
        total_cost += cost
        print(f"  {k}: ${cost:.2f}")
    print(f"Total cost: ${total_cost:.2f}")


if __name__ == "__main__":
    main()
