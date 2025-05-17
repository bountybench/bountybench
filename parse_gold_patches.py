#!/usr/bin/env python3
"""
Script to parse git diffs from gold_standard_patches and generate a CSV with statistics.
For each task, it calculates:
- Lines added/removed
- Files created/deleted/modified
- Total characters in the actual changes (added/deleted lines only)
"""
import csv
import os
import re
from collections import defaultdict


def parse_gold_patch(file_path):
    """Parse a single gold standard patch file and extract statistics."""
    stats = {
        "lines_added": 0,
        "lines_removed": 0,
        "files_created": set(),
        "files_deleted": set(),
        "files_modified": set(),
        "total_chars": 0,
    }

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Calculate character count only from added and removed lines
        added_chars = 0
        removed_chars = 0

        # Find all diff sections (starting with "Diff for")
        diff_sections = (
            re.split(r"Diff for", content)[1:] if "Diff for" in content else []
        )

        if not diff_sections:
            # Try alternative pattern matching
            # Look for lines that look like diff headers (@@ -X,Y +A,B @@)
            hunk_headers = re.findall(r"@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@", content)
            if hunk_headers:
                # Process the entire file as one diff if we found hunk headers
                diff_sections = [content]

        for section in diff_sections:
            # Find the file paths in the diff header
            file_paths = re.findall(r"--- ([^\n]+)\n\+\+\+ ([^\n]+)", section)

            if file_paths:
                for old_path, new_path in file_paths:
                    # Extract file name from path (remove directory part)
                    old_file = os.path.basename(old_path)
                    new_file = os.path.basename(new_path)

                    # Determine the operation (modified, created, deleted)
                    if "/dev/null" in old_path:
                        # New file created
                        stats["files_created"].add(new_file)
                        stats["files_modified"].add(new_file)
                    elif "/dev/null" in new_path:
                        # File deleted
                        stats["files_deleted"].add(old_file)
                        stats["files_modified"].add(old_file)
                    elif old_file != new_file:
                        # File renamed
                        stats["files_deleted"].add(old_file)
                        stats["files_created"].add(new_file)
                        stats["files_modified"].add(old_file)
                        stats["files_modified"].add(new_file)
                    else:
                        # Standard modification
                        stats["files_modified"].add(old_file)

            # Find all hunk sections
            hunk_pattern = re.compile(
                r"@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@.*?\n(.*?)(?=@@ -|\Z)", re.DOTALL
            )
            hunks = hunk_pattern.findall(section)

            for hunk in hunks:
                for line in hunk.split("\n"):
                    if line.startswith("+") and not line.startswith("+++"):
                        stats["lines_added"] += 1
                        # Count characters in added line (remove the '+' prefix)
                        added_chars += len(line) - 1
                    elif line.startswith("-") and not line.startswith("---"):
                        stats["lines_removed"] += 1
                        # Count characters in removed line (remove the '-' prefix)
                        removed_chars += len(line) - 1

        # If we didn't find any files in diff headers but found lines, assume a single file was modified
        if stats["lines_added"] > 0 or stats["lines_removed"] > 0:
            if len(stats["files_modified"]) == 0:
                # Use the filename from the file path as a fallback
                task_name = os.path.basename(file_path).replace(".txt", "")
                stats["files_modified"].add(f"{task_name}_file")

        # Total characters in the patch (only from actual changes)
        stats["total_chars"] = added_chars + removed_chars

        return stats
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return stats


def main():
    base_dir = "/Users/thomasqin/Documents/final_runs/gold_standard_patches"
    output_csv = (
        "/Users/thomasqin/Documents/GitHub/cybench/bountyagent/gold_patch_stats.csv"
    )

    results = []

    # Process each file in the directory
    for file_name in sorted(os.listdir(base_dir)):
        file_path = os.path.join(base_dir, file_name)

        # Skip non-text files and hidden files
        if not file_name.endswith(".txt") or file_name.startswith("."):
            continue

        # Extract task name from filename (remove .txt extension)
        task_name = file_name.replace(".txt", "")
        print(f"Processing task: {task_name}")

        # Parse the patch
        stats = parse_gold_patch(file_path)

        # Add to results
        results.append(
            {
                "task_name": task_name,
                "model": "gold_standard",  # Use 'gold_standard' as the model name
                "lines_added": stats["lines_added"],
                "lines_removed": stats["lines_removed"],
                "files_created": len(stats["files_created"]),
                "files_deleted": len(stats["files_deleted"]),
                "files_modified": len(stats["files_modified"]),
                "total_chars": stats["total_chars"],
            }
        )

    # Write to CSV
    with open(output_csv, "w", newline="") as csvfile:
        fieldnames = [
            "task_name",
            "model",
            "lines_added",
            "lines_removed",
            "files_created",
            "files_deleted",
            "files_modified",
            "total_chars",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for result in results:
            writer.writerow(result)

    print(f"Processed {len(results)} files.")
    print(f"CSV written to {output_csv}")


if __name__ == "__main__":
    main()
