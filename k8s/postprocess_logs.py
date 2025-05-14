#!/usr/bin/env python3
"""
Script to process collected logs: delete incomplete/error logs and restructure valid ones.
Usage: python3 postprocess_logs.py --output-dir <output_path>
"""

import os
import json
import argparse
import sys
import shutil
from pathlib import Path

INPUT_LOG_DIR = Path("../collected_logs")
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

def process_logs(input_root, output_root):
    to_delete = []
    to_move = []
    valid_files_data = [] # Store data for valid files to check success later

    if not input_root.is_dir():
        print(f"Error: Input directory '{input_root}' not found.", file=sys.stderr)
        return

    print(f"Scanning '{input_root}' for log files...")
    for json_path in input_root.rglob('*.json'):
        log_path = json_path.with_suffix('.log')
        delete_flag = False
        reason = ""

        # 1. Check JSON completeness
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            complete = data.get('workflow_metadata', {}) \
                           .get('workflow_summary', {}) \
                           .get('complete')
            if complete is False: # Explicitly check for False, not just None or missing
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

        # 2. Check .log file for Unix error string if not already flagged
        if not delete_flag and log_path.exists():
            try:
                with open(log_path, 'r') as f:
                    log_content = f.read()
                if UNIX_ERROR_STRING in log_content:
                    delete_flag = True
                    reason = f"contains '{UNIX_ERROR_STRING}'"
            except Exception as e:
                print(f'[WARN] Could not read {log_path}: {e}', file=sys.stderr)
                # Decide if read error on log should flag for deletion? For now, no.

        # Categorize
        if delete_flag:
            to_delete.append({'json': json_path, 'log': log_path if log_path.exists() else None, 'reason': reason})
        else:
            # Store the parsed data if available, otherwise None
            file_data = data if 'data' in locals() and isinstance(data, dict) else None 
            to_move.append({'json': json_path, 'log': log_path if log_path.exists() else None, 'data': file_data})

    print(f"Scan complete. Found {len(to_delete)} pairs/files to delete and {len(to_move)} pairs to move.")

    # --- Deletion Phase ---
    if to_delete:
        print('\n--- Files/Pairs Flagged for Deletion ---')
        for item in to_delete:
            print(f"- {item['json']} (Reason: {item['reason']})")
            if item['log']:
                print(f"  (Associated log: {item['log']})")

        if confirm_action(f'Delete these {len(to_delete)} flagged items?'):
            deleted_count = 0
            for item in to_delete:
                try:
                    os.remove(item['json'])
                    print(f'[DELETED] {item["json"]}')
                    deleted_count += 1
                    if item['log']:
                        try:
                            os.remove(item['log'])
                            print(f'[DELETED] {item["log"]}')
                        except Exception as e:
                            print(f'[ERROR] Failed to delete log {item["log"]}: {e}', file=sys.stderr)
                except Exception as e:
                    print(f'[ERROR] Failed to delete JSON {item["json"]}: {e}', file=sys.stderr)
            print(f'Deleted {deleted_count} JSON files (and associated logs where applicable).')
        else:
            print('Aborted deletion. No files were deleted.')
    else:
        print('\nNo files flagged for deletion.')

    # --- Move Phase ---
    if to_move:
        print(f'\n--- Moving {len(to_move)} Valid Log Pairs ---')
        success_count = 0
        moved_json_count = 0
        moved_log_count = 0
        output_logs_base = output_root / 'logs'
        output_full_logs_base = output_root / 'full_logs'

        for item in to_move:
            try:
                relative_path = item['json'].relative_to(input_root)
                # Assumes path structure like date/workflow/task/model/file.json
                # We want to keep task/model/ part
                if len(relative_path.parts) > 3:
                    subpath_parts = relative_path.parts[2:-1] # Skip date, workflow, and filename
                    subpath = Path(*subpath_parts)

                    # Move JSON
                    dest_json_dir = output_logs_base / subpath
                    dest_json_path = dest_json_dir / item['json'].name
                    dest_json_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item['json']), str(dest_json_path))
                    print(f'[MOVED] {item["json"]} -> {dest_json_path}')
                    moved_json_count += 1

                    # Move LOG
                    if item.get('log'): # Check if log path exists in the item
                        dest_log_dir = output_full_logs_base / subpath
                        dest_log_path = dest_log_dir / item['log'].name
                        dest_log_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(item['log']), str(dest_log_path))
                        print(f'[MOVED] {item["log"]} -> {dest_log_path}')
                        moved_log_count += 1
                else:
                     print(f'[WARN] Skipping move for {item["json"]}: Path structure too shallow ({relative_path})', file=sys.stderr)

                # Check success status after successful move attempt
                if item.get('data'): # Check if we have parsed data for this file
                    workflow_success = item['data'].get('workflow_metadata', {}) \
                                             .get('workflow_summary', {}) \
                                             .get('success')
                    if workflow_success is True:
                        success_count += 1
                else:
                    # Cannot determine success if JSON wasn't parsed earlier (e.g., during initial read error check)
                    # We could re-parse here, but let's assume it was moved successfully as a file pair.
                    pass # Or log a warning? For now, just count files moved.

            except Exception as e:
                print(f'[ERROR] Failed to move {item.get("json")} or {item.get("log")}: {e}', file=sys.stderr)
        print(f'\nMoved {moved_json_count} JSON files and {moved_log_count} LOG files.')
        print(f'Out of {moved_json_count} moved JSON files, {success_count} reported successful workflows.')
    else:
        print('\nNo valid files found to move.')

    # --- Final Cleanup Phase ---
    if input_root.exists() and any(input_root.iterdir()): # Check if not empty
         print(f"\nSource directory '{input_root}' still contains files (likely unprocessed or failed moves).")
         if confirm_action(f"Attempt to delete the original source directory '{input_root}' and all its remaining contents?"):
             try:
                 shutil.rmtree(input_root)
                 print(f'[DELETED] Source directory {input_root}')
             except Exception as e:
                 print(f'[ERROR] Failed to delete source directory {input_root}: {e}', file=sys.stderr)
         else:
             print("Source directory cleanup aborted.")
    elif input_root.exists():
         print(f"\nSource directory '{input_root}' appears empty.")
         if confirm_action(f"Delete the empty source directory '{input_root}'?"):
             try:
                 shutil.rmtree(input_root)
                 print(f'[DELETED] Source directory {input_root}')
             except Exception as e:
                 print(f'[ERROR] Failed to delete source directory {input_root}: {e}', file=sys.stderr)
         else:
             print("Source directory cleanup aborted.")

def main():
    parser = argparse.ArgumentParser(
        description='Process collected logs: delete incomplete/error ones and restructure valid ones.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Reads from hardcoded '{INPUT_LOG_DIR}', deletes incomplete/error logs (with confirmation), \n"
               f"moves valid logs into '--output-dir'/logs and '--output-dir'/full_logs, \n"
               f"preserving the structure starting from the third directory level found within '{INPUT_LOG_DIR}'. \n"
               f"Finally, asks to clean up '{INPUT_LOG_DIR}'."
    )
    parser.add_argument('--output-dir', '-o', required=True, help='Root directory to output restructured logs into.')
    args = parser.parse_args()

    output_root = Path(args.output_dir).resolve()
    if output_root.exists() and not output_root.is_dir():
        print(f"Error: Output path '{output_root}' exists but is not a directory.", file=sys.stderr)
        sys.exit(1)

    # Ensure output base exists (but not the logs/full_logs subdirs yet)
    # output_root.mkdir(parents=True, exist_ok=True) # Let the move logic create subdirs

    process_logs(INPUT_LOG_DIR.resolve(), output_root)

    print("\nProcessing finished.")

if __name__ == '__main__':
    main()
