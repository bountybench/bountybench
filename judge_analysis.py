import argparse
import json
import os
import re
from pathlib import Path

import pandas as pd

from lm_judge import (
    extract_valid_writeups,
    get_date_and_title,
    get_fields_from_agent_log,
    get_file_path,
)


def aggregated_results(judge_dir, logs_dir, judge_model, agent_model):
    judge_files_path = f"./{judge_dir}/{judge_model}/{agent_model}"
    all_logs_dir = f"./{logs_dir}/{agent_model}"
    judge_file_prefix = f"{judge_model}_judge_response_{agent_model}_"
    judge_files = os.listdir(judge_files_path)
    judge_data_all = {}
    judge_data_agg = {}
    for judge_file in judge_files:
        if judge_file_prefix not in judge_file:
            continue
        file_path = os.path.join(judge_files_path, judge_file)
        with open(file_path, "r") as file:
            data = json.load(file)
            # Split on the second to last underscore
            bounty_name = judge_file.replace(judge_file_prefix, "").replace(".json", "")
            print(bounty_name)
            orig_date, orig_title = get_date_and_title(bounty_name)
            valid_writeups = extract_valid_writeups(orig_date, bounty_name)
            judge_data_all[bounty_name] = data
            orig_title = orig_title

            if "response_json" not in data[-1]:
                print(f"Skipping bounty {bounty_name} due to no json extracted")
                continue
            json_resp = data[-1]["response_json"]
            json_resp["orig_title"] = orig_title
            json_resp["num_reports"] = len(valid_writeups)
            log_file = get_file_path(all_logs_dir + "/logs", bounty_name, agent_model)
            (
                json_resp["wf_success"],
                json_resp["invariant_scores"],
                json_resp["invariant_message"],
            ) = get_fields_from_agent_log(log_file)
            judge_data_agg[bounty_name] = json_resp
    return judge_data_all, judge_data_agg


def detect_patch_table(judge_data_agg):
    df = pd.DataFrame.from_dict(judge_data_agg, orient="index")
    df["title_match"] = df["orig_title"] == df["bounty_title"]

    custom_order = [
        "orig_title",
        "bounty_title",
        "title_match",
        "num_reports",
        "identification_score",
        "patch_score",
        "localization_score",
        "justification",
        "global_comments",
        "submission_success",
        "wf_success",
        "invariant_scores",
        "invariant_message",
    ]

    df = df[custom_order]
    return df


def detect_exploit_table(judge_data_agg):
    df = pd.DataFrame.from_dict(judge_data_agg, orient="index")
    df["title_match"] = df["orig_title"] == df["bounty_title"]

    custom_order = [
        "orig_title",
        "bounty_title",
        "title_match",
        "num_reports",
        "identification_score",
        "exploit_score",
        "practicality_score",
        "impact_score",
        "justification",
        "global_comments",
        "submission_success",
        "wf_success",
        "invariant_scores",
        "invariant_message",
    ]

    df = df[custom_order]
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "judge_model",
        type=str,
        help="Name of model, e.g. anthropic/claude-3-7-sonnet-20250219",
    )
    parser.add_argument(
        "agent_model",
        type=str,
        help="Name of model, e.g. anthropic/claude-3-7-sonnet-20250219",
    )
    args = parser.parse_args()
    judge_model = args.judge_model
    agent_model = args.agent_model
    judge_dir = "judge_responses"
    logs_dir = "5-1-detect_patch_cwe_only"
    judge_data_all, judge_data_agg = aggregated_results(
        judge_dir, logs_dir, judge_model, agent_model
    )
    df = detect_patch_table(judge_data_agg)
    print(df)


if __name__ == "__main__":
    main()
