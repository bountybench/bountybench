#!/usr/bin/env python3

"""
USAGE: 

python validate_logs.py [--logs-dir /path/to/logs]

"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

parser = argparse.ArgumentParser(description="Validate log files")
parser.add_argument(
    "--logs-dir",
    default="logs_dir",
    help="Directory containing logs to validate (default: logs_dir)",
)
args = parser.parse_args()

LOGS_DIR = Path(args.logs_dir)
BASE_PATH = str(Path(__file__).parent) + os.sep

VALID_MODELS = {
    "anthropic/claude-3-7-sonnet-20250219": 8192,
    "openai/gpt-4.1-2025-04-14": 8192,
    "google/gemini-2.5-pro-preview-03-25": 16384,
    "deepseek-ai/DeepSeek-R1": 16384,
    "deepseek-ai/deepseek-r1": 16384,
    "openai/o3-2025-04-16-high-reasoning-effort": 16384,
}


def validate_json_log(file_path):
    issues = []
    relative_path = file_path.replace(BASE_PATH, "")
    try:
        print(f"[DEBUG] Opening JSON file: {file_path}")
        with open(file_path, "r") as f:
            data = json.load(f)

        # Workflow should be complete
        complete_status = (
            data.get("workflow_metadata", {})
            .get("workflow_summary", {})
            .get("complete", False)
        )
        print(f"[DEBUG] Workflow Complete status: {complete_status}")
        if not complete_status:
            issues.append(f"Complete is False in {relative_path}")

        model_config = data.get("resources_used").get("model").get("config")
        model_name = model_config.get("model")

        max_output_tokens = model_config.get("max_output_tokens")

        if not model_name:
            issues.append(f"Missing model in {relative_path}")
        elif model_name not in VALID_MODELS:
            issues.append(f"Invalid model: {model_name} in {relative_path}")
        else:
            if max_output_tokens != VALID_MODELS[model_name]:
                issues.append(
                    f"max_input_tokens is {max_input_tokens}, should be {VALID_MODELS[model_name]} in {relative_path}"
                )

        # Check max_input_tokens
        max_input_tokens = model_config.get("max_input_tokens")
        if max_input_tokens != 8192:
            issues.append(
                f"max_input_tokens is {max_input_tokens}, not 8192 in {relative_path}"
            )

    except json.JSONDecodeError:
        print(f"[DEBUG] ERROR: Invalid JSON format in {file_path}")
        issues.append(f"Invalid JSON format in {relative_path}")
    except Exception as e:
        print(f"[DEBUG] ERROR: Exception while processing {file_path}: {str(e)}")
        issues.append(f"Error processing {relative_path}: {str(e)}")

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
    all_issues = []
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
                all_issues.append(
                    f"File in full_logs doesn't have .log extension: {relative_path}"
                )
            elif (
                "logs" in root
                and "full_logs" not in root
                and not file.endswith(".json")
            ):
                all_issues.append(
                    f"File in logs doesn't have .json extension: {relative_path}"
                )

            # Track JSON logs and full logs by their base names
            if file.endswith(".json"):
                base_name = os.path.splitext(file)[0]
                json_files.add(base_name)

                # Validate JSON logs
                json_issues = validate_json_log(file_path)
                all_issues.extend(json_issues)

            elif file.endswith(".log"):
                base_name = os.path.splitext(file)[0]
                log_files.add(base_name)

                # Validate full logs
                log_issues = validate_full_log(file_path)
                all_issues.extend(log_issues)

    # Check for missing corresponding logs
    for base_name in json_files:
        if base_name not in log_files:
            all_issues.append(
                f"JSON log {base_name}.json has no corresponding full log file"
            )

    for base_name in log_files:
        if base_name not in json_files:
            all_issues.append(
                f"Full log {base_name}.log has no corresponding JSON log file"
            )

    print(
        f"Processed {files_processed} files ({len(json_files)} JSON logs, {len(log_files)} full logs)"
    )

    # Print all issues
    if all_issues:
        print(f"Found {len(all_issues)} issues:")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}\n")
    else:
        print("No issues found. All logs are valid.")

    return len(all_issues)


if __name__ == "__main__":
    issue_count = validate_logs()
    sys.exit(1 if issue_count > 0 else 0)
