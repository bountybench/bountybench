#!/usr/bin/env python3

"""
sum_times.py: Recursively compute the time difference (in minutes) between file creation and last modification
for each file under the given directory. Print each difference and a total sum at the end.
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Sum difference in minutes between file creation and last modification times for all files under a directory."
    )
    parser.add_argument("directory", help="Directory to process")
    args = parser.parse_args()

    root_dir = args.directory
    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir!r} is not a directory", file=sys.stderr)
        sys.exit(1)

    total_minutes = 0.0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            # skip macOS metadata files
            if fname == ".DS_Store":
                continue
            filepath = os.path.join(dirpath, fname)
            try:
                st = os.stat(filepath)
                # On platforms with birth time (e.g., macOS), use st_birthtime; otherwise use ctime
                creation_time = getattr(st, "st_birthtime", st.st_ctime)
                modification_time = st.st_mtime
            except OSError as e:
                print(f"Warning: cannot access file {filepath!r}: {e}", file=sys.stderr)
                continue

            # Compute absolute difference to ensure positive duration
            diff_seconds = abs(modification_time - creation_time)
            diff_minutes = diff_seconds / 60.0
            print(f"{filepath}: {diff_minutes:.2f} minutes")
            total_minutes += diff_minutes

    print(f"Total sum: {total_minutes:.2f} minutes")


if __name__ == "__main__":
    main()
