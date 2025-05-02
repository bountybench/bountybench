#!/usr/bin/env python3
"""
Script to clean up processed log directories.

Deletes:
- JSON/LOG pairs where the JSON indicates incompleteness.
- JSON/LOG pairs where the LOG contains a specific error string.
- Orphaned LOG files (no corresponding JSON file).

Usage: python3 cleanup_processed_logs.py <processed_log_root_dir>
"""

import os
import json
import argparse
import sys
from pathlib import Path

UNIX_ERROR_STRING = "UnixHTTPConnectionPool"

def confirm_action(prompt):
    """Helper function to get y/n confirmation."""
    while True:
        confirm = input(f'{prompt} [y/N]: ').strip().lower()
        if confirm in ('y', 'yes'):
            return True
        if confirm in ('n', 'no', ''): # Default to No
            return False
        print("Please enter 'y' or 'n'.")

def cleanup_logs(root_dir):
    logs_dir = root_dir / 'logs'
    full_logs_dir = root_dir / 'full_logs'

    if not logs_dir.is_dir() or not full_logs_dir.is_dir():
        print(f"Error: Could not find 'logs' and 'full_logs' subdirectories under '{root_dir}'.", file=sys.stderr)
        return

    to_delete_files = set() # Use a set to avoid duplicate deletion attempts
    flagged_reasons = {}
    total_json_count = 0
    successful_task_count = 0

    print(f"Scanning '{logs_dir}' for JSON files...")
    json_files_found = list(logs_dir.rglob('*.json'))
    print(f"Found {len(json_files_found)} JSON files.")
    total_json_count = len(json_files_found) # Initialize total count

    # --- Step 1 & 2: Check JSON validity and corresponding LOG errors --- 
    for json_path in json_files_found:
        relative_path = json_path.relative_to(logs_dir)
        log_path = full_logs_dir / relative_path.with_suffix('.log')
        delete_flag = False
        reason = ""

        # Check JSON completeness and success
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            workflow_summary = data.get('workflow_metadata', {}).get('workflow_summary', {})
            complete = workflow_summary.get('complete')
            success = workflow_summary.get('success') # Get the success field

            # Increment success counter if success is True
            if success is True:
                successful_task_count += 1

            if complete is False:
                delete_flag = True
                reason = "incomplete workflow"
        except json.JSONDecodeError as e:
            print(f'[WARN] Could not parse {json_path}: {e}. Flagging for deletion.', file=sys.stderr)
            delete_flag = True
            reason = f"JSON parse error: {e}"
        except Exception as e:
            print(f'[WARN] Could not read or process {json_path}: {e}. Flagging for deletion.', file=sys.stderr)
            delete_flag = True
            reason = f"read/process error: {e}"

        # Check corresponding .log file for Unix error string if not already flagged
        if not delete_flag and log_path.exists():
            try:
                with open(log_path, 'r') as f:
                    log_content = f.read()
                if UNIX_ERROR_STRING in log_content:
                    delete_flag = True
                    reason = f"log contains '{UNIX_ERROR_STRING}'"
            except Exception as e:
                print(f'[WARN] Could not read log {log_path}: {e}', file=sys.stderr)
                # Log read error doesn't automatically trigger deletion here

        # Add pair to deletion list if flagged
        if delete_flag:
            to_delete_files.add(json_path)
            flagged_reasons[json_path] = reason
            if log_path.exists():
                to_delete_files.add(log_path)
                flagged_reasons[log_path] = f"associated with invalid JSON ({reason})"

    print(f"Finished checking JSON files. {len(to_delete_files)} files flagged so far.")

    # --- Step 3: Check for Orphaned LOG files --- 
    print(f"\nScanning '{full_logs_dir}' for orphaned LOG files...")
    log_files_found = list(full_logs_dir.rglob('*.log'))
    print(f"Found {len(log_files_found)} LOG files.")
    orphaned_logs_found = 0

    for log_path in log_files_found:
        # Skip if already flagged for deletion with its JSON pair
        if log_path in to_delete_files:
            continue 

        relative_path = log_path.relative_to(full_logs_dir)
        corresponding_json_path = logs_dir / relative_path.with_suffix('.json')

        if not corresponding_json_path.exists():
            to_delete_files.add(log_path)
            flagged_reasons[log_path] = "orphaned (no corresponding JSON)"
            orphaned_logs_found += 1
    
    if orphaned_logs_found > 0:
        print(f"Flagged {orphaned_logs_found} orphaned LOG files for deletion.")
    else:
        print("No orphaned LOG files found.")

    # Log the success count
    print(f"\nTask Summary: Found {successful_task_count} successful tasks out of {total_json_count} total JSON files processed.")

    # --- Deletion Phase ---
    deleted_files = False # Keep track if any files were actually deleted
    if to_delete_files:
        print(f'\n--- {len(to_delete_files)} Files Flagged for Deletion ---')
        # Sort for consistent display
        sorted_files_to_delete = sorted(list(to_delete_files))
        for f_path in sorted_files_to_delete:
            reason = flagged_reasons.get(f_path, "Unknown")
            print(f"- {f_path} (Reason: {reason})")

        if confirm_action(f'Delete these {len(to_delete_files)} flagged files?'):
            deleted_count = 0
            failed_count = 0
            for f_path in sorted_files_to_delete:
                try:
                    os.remove(f_path)
                    print(f'[DELETED] {f_path}')
                    deleted_count += 1
                    deleted_files = True # Mark that we deleted something
                except Exception as e:
                    print(f'[ERROR] Failed to delete {f_path}: {e}', file=sys.stderr)
                    failed_count += 1
            print(f'\nDeletion summary: Deleted {deleted_count} files, Failed {failed_count} files.')
        else:
            print('\nAborted deletion. No files were deleted.')
    else:
        print('\nNo files flagged for deletion.')

    # --- Step 4: Remove Empty Directories ---
    print("\nScanning for empty directories...")
    removed_dirs_count = 0
    # Process directories bottom-up to remove child directories before parents
    for dir_path in [logs_dir, full_logs_dir]:
        # Check if the base directory still exists before walking
        if not dir_path.exists():
            continue
        for root, dirs, files in os.walk(dir_path, topdown=False):
            current_dir_path = Path(root)
            # Check if the directory is empty and is not the top-level logs/ or full_logs/ dir itself
            if not os.listdir(current_dir_path) and current_dir_path != dir_path:
                try:
                    os.rmdir(current_dir_path)
                    print(f"[REMOVED_EMPTY_DIR] {current_dir_path}")
                    removed_dirs_count += 1
                except OSError as e:
                    print(f"[ERROR] Failed to remove empty directory {current_dir_path}: {e}", file=sys.stderr)

    if removed_dirs_count > 0:
        print(f"Removed {removed_dirs_count} empty directories.")
    else:
        print("No empty directories found to remove.")


def main():
    parser = argparse.ArgumentParser(
        description='Clean up processed log directories by removing incomplete/error/orphaned files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Expects 'logs' and 'full_logs' subdirectories in the target directory. \n"
               f"Checks for incomplete JSON, logs containing '{UNIX_ERROR_STRING}', and orphaned .log files. \n"
               f"Prompts before deleting any files."
    )
    parser.add_argument('root_dir', help='Path to the root directory containing processed logs (e.g., the output of postprocess_logs.py)')
    args = parser.parse_args()

    root_path = Path(args.root_dir).resolve()

    if not root_path.is_dir():
        print(f"Error: Provided path '{root_path}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    cleanup_logs(root_path)

    print("\nCleanup finished.")

if __name__ == '__main__':
    main()
