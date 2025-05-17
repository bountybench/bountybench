#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path


def analyze_json_file(file_path):
    """
    Analyzes a single JSON file to extract query time and total iteration time.

    Args:
        file_path (str or Path): Path to the JSON file.

    Returns:
        tuple: (query_time, iteration_time, execution_time) or None if an error occurs.
    """
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        # Extract query time from workflow_usage
        workflow_usage = data.get("workflow_usage")
        if not workflow_usage or "total_query_time_taken_in_ms" not in workflow_usage:
            print(
                f"Warning: 'total_query_time_taken_in_ms' not found in workflow_usage for {file_path}"
            )
            return None
        query_time = workflow_usage["total_query_time_taken_in_ms"]

        # Extract total iteration time from the first phase message
        phase_messages = data.get("phase_messages")
        if not isinstance(phase_messages, list) or not phase_messages:
            print(f"Warning: 'phase_messages' is not a list or is empty in {file_path}")
            return None

        first_phase = phase_messages[0]
        phase_usage = first_phase.get("phase_usage")
        if not phase_usage or "total_iteration_time_ms" not in phase_usage:
            print(
                f"Warning: 'total_iteration_time_ms' not found in phase_usage of the first phase for {file_path}"
            )
            return None
        iteration_time = phase_usage["total_iteration_time_ms"]

        if (
            query_time is None or iteration_time is None
        ):  # Should be caught by earlier checks, but as a safeguard
            print(f"Warning: Could not find required time fields in {file_path}")
            return None

        execution_time = iteration_time - query_time
        return query_time, iteration_time, execution_time

    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None
    except KeyError as e:
        print(f"Error: Missing key {e} in {file_path}")
        return None
    except IndexError:
        print(
            f"Error: 'phase_messages' list might be empty or accessed out of bounds in {file_path}"
        )
        return None
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Analyze JSON files for query and iteration times."
    )
    parser.add_argument(
        "directory_path", type=str, help="Path to the directory containing JSON files."
    )
    args = parser.parse_args()

    target_directory = Path(args.directory_path)
    if not target_directory.is_dir():
        print(f"Error: {args.directory_path} is not a valid directory.")
        return

    all_query_times = []
    all_iteration_times = []
    all_execution_times = []
    processed_files_count = 0
    failed_files_count = 0

    print(f"Scanning directory: {target_directory}\n")
    for root, _, files in os.walk(target_directory):
        for filename in files:
            if filename.endswith(".json"):
                file_path = Path(root) / filename
                # print(f"Processing {file_path}...") # Can be verbose for many files
                times = analyze_json_file(file_path)
                if times:
                    query_time, iteration_time, execution_time = times
                    all_query_times.append(query_time)
                    all_iteration_times.append(iteration_time)
                    all_execution_times.append(execution_time)
                    processed_files_count += 1
                else:
                    failed_files_count += 1

    if processed_files_count == 0:
        print("No JSON files were successfully processed or no relevant data found.")
        if failed_files_count > 0:
            print(f"{failed_files_count} files failed to process.")
        return

    # Calculate aggregates
    total_query_time = sum(all_query_times)
    total_iteration_time = sum(all_iteration_times)
    total_execution_time = sum(all_execution_times)

    avg_query_time = total_query_time / len(all_query_times) if all_query_times else 0
    avg_iteration_time = (
        total_iteration_time / len(all_iteration_times) if all_iteration_times else 0
    )
    avg_execution_time = (
        total_execution_time / len(all_execution_times) if all_execution_times else 0
    )

    print("\n--- Aggregated Results ---")
    print(
        f"Total JSON files found and attempted: {processed_files_count + failed_files_count}"
    )
    print(f"Successfully processed files: {processed_files_count}")
    print(f"Failed to process files: {failed_files_count}")

    if processed_files_count > 0:
        print("\nTotals (ms):")
        print(f"  Total Query Time: {total_query_time:.2f}")
        print(f"  Total Iteration Time: {total_iteration_time:.2f}")
        print(f"  Total Execution Time (Iteration - Query): {total_execution_time:.2f}")
        print("\nAverages (ms):")
        print(f"  Average Query Time: {avg_query_time:.2f}")
        print(f"  Average Iteration Time: {avg_iteration_time:.2f}")
        print(f"  Average Execution Time (Iteration - Query): {avg_execution_time:.2f}")


if __name__ == "__main__":
    main()
