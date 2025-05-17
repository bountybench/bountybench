#!/usr/bin/env python3
"""
Recursively search for a string in all files under a given directory,
printing 10 lines of context above and below each match, and
reporting which files contain the string.
"""
import os
import sys

CONTEXT_LINES = 20


def find_in_file(filepath, search_str, context=CONTEXT_LINES):
    try:
        with open(filepath, "r", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return []
    matches = []
    for idx, line in enumerate(lines):
        if search_str in line:
            start = max(0, idx - context)
            end = min(len(lines) - 1, idx + context)
            snippet = lines[start : end + 1]
            matches.append((idx, start, snippet))
    return matches


def main():
    if len(sys.argv) != 3:
        sys.stderr.write(f"Usage: {sys.argv[0]} <directory> <search_string>\n")
        sys.exit(2)
    root_dir, search_str = sys.argv[1], sys.argv[2]
    if not os.path.isdir(root_dir):
        sys.stderr.write(f"Error: '{root_dir}' is not a directory.\n")
        sys.exit(1)

    # Track occurrences per file and global total
    found_counts = []  # list of tuples (file_path, count)
    total_count = 0
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            path = os.path.join(dirpath, name)
            matches = find_in_file(path, search_str)
            if matches:
                count = len(matches)
                found_counts.append((path, count))
                total_count += count
                # print each match with context
                for idx, start, snippet in matches:
                    print(f"File: {path}, Line: {idx + 1}")
                    for offset, text in enumerate(snippet, start=start + 1):
                        print(f"{offset}: {text.rstrip()}")
                    print("-" * 80)

    if found_counts:
        # print summary of occurrences per file and total
        print("\nOccurrences per file:")
        for path, count in found_counts:
            print(f"{path}: {count}")
        print(f"\nTotal occurrences: {total_count}")
        sys.exit(0)
    else:
        print("No occurrences found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
