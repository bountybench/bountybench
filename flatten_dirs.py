#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path


def flatten_json_files(directory):
    """
    Find all JSON files in the given directory (recursively),
    copy them to the root of the directory, then delete all subfolders.

    Args:
        directory (str): Path to the directory to process
    """
    directory = Path(directory).resolve()

    if not directory.is_dir():
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)

    # Find all JSON files recursively
    json_files = []
    subdirs = set()

    for root, dirs, files in os.walk(directory):
        root_path = Path(root)
        if root_path == directory:
            continue  # Skip the root directory itself

        # Keep track of subdirectories for later deletion
        subdirs.add(root_path)

        for file in files:
            if file.lower().endswith(".log"):
                source_path = root_path / file
                json_files.append(source_path)

    # Copy files to the root directory
    copied_count = 0
    skipped_count = 0

    for source_path in json_files:
        # Keep the original file name
        dest_path = directory / source_path.name

        # Check if file with same name already exists
        if dest_path.exists():
            print(f"Skipped (already exists): {source_path}")
            skipped_count += 1
            continue

        try:
            shutil.copy2(source_path, dest_path)
            print(f"Copied: {source_path} -> {dest_path}")
            copied_count += 1
        except Exception as e:
            print(f"Error copying {source_path}: {e}")

    print(f"\nCopying completed:")
    print(f"- {copied_count} JSON files copied to {directory}")
    print(f"- {skipped_count} files skipped (destination already exists)")

    # Delete all subdirectories
    # Sort in reverse order to ensure we delete deepest directories first
    deleted_count = 0
    sorted_dirs = sorted(subdirs, key=lambda x: str(x), reverse=True)

    print("\nDeleting subdirectories...")
    for subdir in sorted_dirs:
        try:
            shutil.rmtree(subdir)
            print(f"Deleted: {subdir}")
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting {subdir}: {e}")

    print(f"\nDeleted {deleted_count} subdirectories")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python flatten_dirs.py <directory>")
        sys.exit(1)

    directory = sys.argv[1]
    flatten_json_files(directory)
