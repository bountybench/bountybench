#!/usr/bin/env python3
"""
Script to parse git diffs from agent_patches_no_truncation logs and generate a CSV with statistics.
For each task and model, it calculates:
- Lines added/removed
- Files created/deleted/modified
- Total characters in the actual changes (added/deleted lines only)
"""
import csv
import os
import re
from collections import defaultdict


def parse_git_diff(file_path):
    """Parse a single log file and extract statistics from git diff if present."""
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

        # Check if the file contains a git diff
        diff_start = content.find("Git diff: diff --git ")
        if diff_start == -1:
            print(f"  No git diff found in {os.path.basename(file_path)}")
            return stats

        # Extract the actual diff part
        diff_content = content[diff_start:]

        # Cut off at "Submission received" or similar end marker
        end_markers = ["Submission received.", "Codebase changes detected."]
        for marker in end_markers:
            end = diff_content.find(marker)
            if end != -1:
                diff_content = diff_content[:end]
                break

        # Calculate character count only from added and removed lines
        added_chars = 0
        removed_chars = 0

        # Track all files that appear in diff headers
        file_patterns = {}  # Maps from paths to status (created, deleted, modified)

        # Find all diff sections
        # Pattern to match diff headers
        diff_headers = re.findall(r"diff --git a/(.*?) b/(.*?)\n", diff_content)

        # Process each diff header to identify file operations
        for old_path, new_path in diff_headers:
            # Extract the section for this file
            header_start = diff_content.find(f"diff --git a/{old_path} b/{new_path}")
            next_header = diff_content.find("diff --git ", header_start + 1)
            if next_header == -1:
                section = diff_content[header_start:]
            else:
                section = diff_content[header_start:next_header]

            # Check if file was created, deleted, or modified
            if "new file mode" in section:
                stats["files_created"].add(new_path)
                stats["files_modified"].add(new_path)
            elif "deleted file mode" in section:
                stats["files_deleted"].add(old_path)
                stats["files_modified"].add(old_path)
            elif old_path != new_path:
                # This is a rename
                stats["files_deleted"].add(old_path)
                stats["files_created"].add(new_path)
                stats["files_modified"].add(old_path)
                stats["files_modified"].add(new_path)
            else:
                # Standard modification
                stats["files_modified"].add(old_path)

            # Count added and removed lines in hunks and their characters
            # Find all hunks in this section
            hunk_pattern = re.compile(
                r"@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@.*?\n(.*?)(?=diff --git|\Z|@@ -)",
                re.DOTALL,
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

        # Total characters in the patch (only from actual changes)
        stats["total_chars"] = added_chars + removed_chars

        return stats
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return stats


def extract_model_name(filename):
    """Extract model name from filename (everything before the first underscore)."""
    parts = filename.split("_")

    # Handle different naming patterns
    if parts[0] == "anthropic" and parts[1] == "claude":
        # Handle anthropic-claude-* pattern
        return f"{parts[0]}-{parts[1]}"
    elif parts[0] == "google" and parts[1] == "gemini":
        # Handle google-gemini-* pattern
        return f"{parts[0]}-{parts[1]}"
    elif parts[0] == "openai" and (parts[1] == "gpt" or parts[1] == "o4"):
        # Handle openai-gpt-* or openai-o4-* pattern
        return f"{parts[0]}-{parts[1]}"
    elif parts[0] == "claude" and parts[1] == "code":
        # Handle claude-code pattern
        return f"{parts[0]}-{parts[1]}"
    else:
        # Default fallback
        return parts[0]


def main():
    base_dir = "/Users/thomasqin/Documents/final_runs/agent_patch_no_truncation"
    output_csv = (
        "/Users/thomasqin/Documents/GitHub/cybench/bountyagent/git_diff_stats.csv"
    )

    results = []

    # Walk through all task directories
    for task_dir in sorted(os.listdir(base_dir)):
        task_path = os.path.join(base_dir, task_dir)
        if not os.path.isdir(task_path) or task_dir.startswith("."):
            continue

        task_name = task_dir
        print(f"Processing task: {task_name}")

        # Process each log file in the task directory
        for log_file in os.listdir(task_path):
            if not log_file.endswith(".log"):
                continue

            file_path = os.path.join(task_path, log_file)

            # Extract model name from filename
            model = extract_model_name(log_file)
            print(f"  Processing model: {model}")

            # Parse the git diff
            stats = parse_git_diff(file_path)

            # Add to results
            results.append(
                {
                    "task_name": task_name,
                    "model": model,
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
