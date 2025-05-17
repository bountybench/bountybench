#!/usr/bin/env python3
"""
Rename JSON files starting with '_' under paths containing 'claude-code',
replacing the leading '_' with 'claude-code'.
"""

import argparse
import os
import sys


def rename_files(base_dir):
    for dirpath, _, filenames in os.walk(base_dir):
        for filename in filenames:
            string_to_replace = "_"
            if not filename.startswith(string_to_replace) or not filename.endswith(
                ".log"
            ):
                continue
            old_path = os.path.join(dirpath, filename)
            new_filename = "claude-code_" + filename[len(string_to_replace) :]
            new_path = os.path.join(dirpath, new_filename)
            if os.path.exists(new_path):
                print(f"Skipped: target already exists: {new_path}", file=sys.stderr)
                continue
            print(f"Renaming:\n  {old_path}\n→ {new_path}")
            try:
                os.rename(old_path, new_path)
            except OSError as e:
                print(f"Error renaming {old_path} to {new_path}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Rename JSON files starting with '_' under paths containing 'claude-code', replacing the leading '_' with 'claude-code'."
    )
    parser.add_argument("base_dir", help="Base directory to search for files")
    args = parser.parse_args()
    base_dir = args.base_dir
    if not os.path.isdir(base_dir):
        print(f"Error: {base_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    rename_files(base_dir)


if __name__ == "__main__":
    main()
