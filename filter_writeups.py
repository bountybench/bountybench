import argparse
import os
import re
from datetime import datetime

import get_writeups
from get_writeups import extract_huntr_reported_date, read_huntr_writeup


# Get all writeups within a repo that are reported on or after the specified date
def filter_writeups_by_date(report_date_str, repo_name):
    # Parse the original date string into a datetime object
    original_date = datetime.strptime(report_date_str, "%m_%d_%Y")

    file_dir = f"html_writeups/{repo_name}"
    all_files = os.listdir(file_dir)

    filtered_files = []

    for file in all_files:
        # Check if the file matches the pattern 'report_x_mm_dd_yyyy.html'
        if file.startswith("report_") and file.endswith(".html"):
            try:
                match = re.search(r"(\d{2}_\d{2}_\d{4})", file)
                if match:
                    date_str = match.group(1)  # Extract the date part
                    file_date = datetime.strptime(date_str, "%m_%d_%Y")

                    if file_date >= original_date:
                        filtered_files.append(file)
            except ValueError:
                continue

    return filtered_files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "bounty_name", type=str, help="Path to a bounty, e.g., lunary_0"
    )
    source_dir = "bountybench"

    args = parser.parse_args()
    bounty_name = args.bounty_name
    repo_name, bounty_number = bounty_name.split("_")
    full_repo_dir = os.path.join(source_dir, repo_name)
    writeup = read_huntr_writeup(full_repo_dir, bounty_number)
    date_str = extract_huntr_reported_date(writeup)
    print(f"bounty report date: {date_str}")
    filtered_writeups = filter_writeups_by_date(date_str, repo_name)
    print(filtered_writeups)


if __name__ == "__main__":
    main()
