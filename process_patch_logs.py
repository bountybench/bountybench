#!/usr/bin/env python3
"""
Script to process log files in patch_stats directory.
1. Finds the first occurrence of "Git diff: diff" and removes all lines above it (including the line itself).
2. Finds the first occurrence of "Codebase changes detected." and removes that line and all lines below it.
Keeps track of how many files had each string and how many didn't.
"""
import glob
import os


def process_file(file_path):
    """
    Process a single file to:
    1. Find the first "Git diff: diff" and delete all lines above it and the line itself
    2. Find the first "Codebase changes detected." and delete that line and all lines below it
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        start_string = "Git diff: diff"
        end_string = "Codebase changes detected."
        start_index = None
        end_index = None

        # Find start index (Git diff)
        for i, line in enumerate(lines):
            if start_string in line:
                start_index = i
                break

        # Find end index (Codebase changes detected)
        for i, line in enumerate(lines):
            if end_string in line:
                end_index = i
                break

        # Track what was found
        found_start = start_index is not None
        found_end = end_index is not None

        # Apply the changes
        if found_start or found_end:
            if found_start and found_end and start_index < end_index:
                # Keep only lines between start_index+1 and end_index (exclusive of both)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines[start_index:end_index])
            elif found_start:
                # Only found start, keep from start_index+1 onwards
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines[start_index + 1 :])
            elif found_end:
                # Only found end, keep up to end_index (exclusive)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines[:end_index])

        return found_start, found_end
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, False


def main():
    folder_path = "/Users/thomasqin/Documents/patch_stats/"

    # Find all log files in all subdirectories
    log_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".log"):
                log_files.append(os.path.join(root, file))

    found_start_count = 0
    found_end_count = 0
    not_found_count = 0

    for file_path in log_files:
        print(f"Processing: {os.path.basename(file_path)}")
        found_start, found_end = process_file(file_path)

        if found_start and found_end:
            found_start_count += 1
            found_end_count += 1
            print(f"  Found both markers - trimmed file accordingly")
        elif found_start:
            found_start_count += 1
            print(
                f"  Found 'Git diff: diff' but not 'Codebase changes detected.' - removed lines above Git diff (including the line)"
            )
        elif found_end:
            found_end_count += 1
            print(
                f"  Found 'Codebase changes detected.' but not 'Git diff: diff' - removed line and everything below"
            )
        else:
            not_found_count += 1
            print(f"  Neither marker found - left file unchanged")

    print(f"\nProcessing complete.")
    print(f"Files with 'Git diff: diff': {found_start_count}")
    print(f"Files with 'Codebase changes detected.': {found_end_count}")
    print(f"Files with neither marker: {not_found_count}")


if __name__ == "__main__":
    main()
