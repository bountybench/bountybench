#!/usr/bin/env python3
"""
Script to list all files in a given folder (including subfolders)
whose full path contains a specified string.
"""
import argparse
import os
import sys


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="List files whose full path contains a given string."
    )
    parser.add_argument("folder", help="Folder to search")
    parser.add_argument("string", help="String to search for in file paths")
    return parser.parse_args()


def main():
    args = parse_arguments()
    folder = args.folder
    search_str = args.string

    if not os.path.isdir(folder):
        print(f"Error: {folder} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Walk through the directory tree
    match_count = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            # Check if the search string is in the path
            if search_str in full_path:
                print(os.path.abspath(full_path))
                match_count += 1

    # Print summary of matches
    print(f"Found {match_count} matching file(s)")


if __name__ == "__main__":
    main()
