#!/usr/bin/env python3
"""
Script to find and delete .DS_Store files in a given directory.
Usage:
    delete_ds_store_files.py <directory> [--no_dry_run]
"""
import argparse
import os
import sys


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Find and optionally delete .DS_Store files in a directory tree."
    )
    parser.add_argument("directory", help="Directory to search")
    parser.add_argument(
        "--no_dry_run",
        action="store_true",
        help="Actually delete the found .DS_Store files (default is dry run)",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    root = args.directory
    no_dry_run = args.no_dry_run

    if not os.path.isdir(root):
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    ds_store_paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename == ".DS_Store":
                ds_store_paths.append(os.path.join(dirpath, filename))

    count = len(ds_store_paths)
    if count == 0:
        print("No .DS_Store files found.")
        return

    for path in ds_store_paths:
        print(path)
        if no_dry_run:
            try:
                os.remove(path)
            except Exception as e:
                print(f"Failed to delete {path}: {e}", file=sys.stderr)

    if no_dry_run:
        print(f"Deleted {count} .DS_Store file(s).")
    else:
        print(f"Found {count} .DS_Store file(s) (dry run).")


if __name__ == "__main__":
    main()
