#!/usr/bin/env python3

"""
USAGE: 

python validate_logs.py [--logs-dir /path/to/logs]

"""
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from json_log import JSONLog
from script_constants import VALID_MODELS

# Global dictionaries to track token usage by model
model_input_tokens = defaultdict(int)
model_output_tokens = defaultdict(int)

# Lists to track different log statuses
successes = []  # Logs with success status

parser = argparse.ArgumentParser(description="Validate log files")
parser.add_argument(
    "--logs-dir",
    default="logs",
    help="Directory containing logs to validate (default: logs_dir)",
)
args = parser.parse_args()

LOGS_DIR = Path(args.logs_dir)
BASE_PATH = str(Path(__file__).parent) + os.sep


def validate_json_log(file_path):
    print(f"[DEBUG] Opening JSON file: {file_path}")

    # Use JSONLog to validate the file
    json_log = JSONLog(file_path)
    issues = json_log.identify_issues()

    if json_log.success:
        successes.append(json_log)

    # Only track tokens if the model name exists and token values are present
    if json_log.model_name:
        input_tokens = json_log.total_input_tokens or 0
        output_tokens = json_log.total_output_tokens or 0
        model_input_tokens[json_log.model_name] += input_tokens
        model_output_tokens[json_log.model_name] += output_tokens

    print(f"[DEBUG] Finished processing {file_path} and found {len(issues)} issues")
    return issues


def validate_full_log(file_path):
    issues = []
    relative_path = file_path.replace(BASE_PATH, "")
    try:
        with open(file_path, "r") as f:
            content = f.read()

        # Check if workflow was run via docker
        if "/app/full_logs/" not in content:
            issues.append(f"Missing /app/full_logs/ path in {relative_path}")

        # Check if log ended early
        if "Phase 0 completed:" not in content:
            issues.append(f"Missing 'Phase 0 completed:' in {relative_path}")

        # Check if DEBUG logs appear
        if "DEBUG" not in content:
            issues.append(f"Missing DEBUG logs in {relative_path}")

        # Check for submit mode
        if "FinalSubmissionCommand" not in content:
            issues.append(f"Missing FinalSubmissionCommand in {relative_path}")

    except Exception as e:
        issues.append(f"Error processing {relative_path}: {str(e)}")

    return issues


def validate_logs():
    issues_by_file = defaultdict(list)
    files_processed = 0
    json_files = set()  # Store base filenames (without .json) of JSON log files
    log_files = set()  # Store base filenames (without .log) of full log files
    print(f"Looking for logs in {LOGS_DIR}")

    # First pass: collect all files and validate them
    for root, _, files in os.walk(LOGS_DIR):
        for file in files:
            if file == ".DS_Store":
                continue
            files_processed += 1

            file_path = os.path.join(root, file)
            relative_path = file_path.replace(BASE_PATH, "")

            # Check file extension based on directory
            if "full_logs" in root and not file.endswith(".log"):
                issues_by_file[relative_path].append(
                    f"File in full_logs doesn't have .log extension"
                )
            elif (
                "logs" in root
                and "full_logs" not in root
                and not file.endswith(".json")
            ):
                issues_by_file[relative_path].append(
                    f"File in logs doesn't have .json extension"
                )

            # Track JSON logs and full logs by their base names
            if file.endswith(".json"):
                base_name = os.path.splitext(file)[0]
                json_files.add(base_name)

                # Validate JSON logs
                json_issues = validate_json_log(file_path)
                if json_issues:
                    issues_by_file[relative_path].extend(json_issues)

            elif file.endswith(".log"):
                base_name = os.path.splitext(file)[0]
                log_files.add(base_name)

                # Validate full logs
                log_issues = validate_full_log(file_path)
                if log_issues:
                    issues_by_file[relative_path].extend(log_issues)

    # Check for missing corresponding logs
    for base_name in json_files:
        if base_name not in log_files:
            relative_path = f"{base_name}.json"
            issues_by_file[relative_path].append(f"No corresponding full log file")

    for base_name in log_files:
        if base_name not in json_files:
            relative_path = f"{base_name}.log"
            issues_by_file[relative_path].append(f"No corresponding JSON log file")

    # Remove entries with empty issue lists
    issues_by_file = {k: v for k, v in issues_by_file.items() if v}

    # Count total issues
    total_issues = sum(len(issues) for issues in issues_by_file.values())

    print(
        f"Processed {files_processed} files ({len(json_files)} JSON logs, {len(log_files)} full logs)"
    )

    # Print issues by file
    if issues_by_file:
        print(
            f"Found {len(issues_by_file)} files with issues ({total_issues} total issues):"
        )
        for i, (file_path, issues) in enumerate(sorted(issues_by_file.items()), 1):
            print(f"\n{i}. File: {file_path}")
            print(f"   Issues: {len(issues)}")
            for j, issue in enumerate(issues, 1):
                print(f"      {j}. {issue}")
    else:
        print("No issues found. All logs are valid.")

    print(f"Successes: {len(successes)}")
    for i, success in enumerate(successes, 1):
        # Use name property of Path object
        relative_path = success.filepath.name
        print(
            f"{i}. Task: {success.task_name}, \nModel: {success.model_name} \n{relative_path}"
        )

    # Print token usage by model
    if model_input_tokens or model_output_tokens:
        print("\n=== Token Usage by Model ===")
        print(
            f"{'Model':<50} {'Input Tokens':>15} {'Output Tokens':>15} {'Total Tokens':>15}"
        )
        print("-" * 100)

        for model in sorted(
            set(model_input_tokens.keys()) | set(model_output_tokens.keys())
        ):
            input_count = model_input_tokens[model]
            output_count = model_output_tokens[model]
            total = input_count + output_count
            print(f"{model:<50} {input_count:>15,} {output_count:>15,} {total:>15,}")

        # Print totals
        total_input = sum(model_input_tokens.values())
        total_output = sum(model_output_tokens.values())
        total_tokens = total_input + total_output
        print("-" * 100)
        print(
            f"{'TOTAL':<50} {total_input:>15,} {total_output:>15,} {total_tokens:>15,}"
        )

    return len(issues_by_file)


if __name__ == "__main__":
    issue_count = validate_logs()
    sys.exit(1 if issue_count > 0 else 0)
