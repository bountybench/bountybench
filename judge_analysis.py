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
    get_repo_all_bounty_titles,
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
            # print(bounty_name)
            repo_name, _ = bounty_name.rsplit("_", 1)
            all_bounty_titles = get_repo_all_bounty_titles(repo_name)
            orig_date, orig_title = get_date_and_title(bounty_name)
            valid_writeups = extract_valid_writeups(orig_date, bounty_name)
            judge_data_all[bounty_name] = data
            orig_title = orig_title

            if "response_json" not in data[-1]:
                print(f"Skipping bounty {bounty_name} due to no json extracted")
                continue
            json_resp = data[-1]["response_json"]
            json_resp["repo_titles"] = all_bounty_titles
            json_resp["num_reports"] = len(valid_writeups)
            log_file = get_file_path(all_logs_dir + "/logs", bounty_name, agent_model)
            (
                json_resp["wf_success"],
                json_resp["invariant_scores"],
                json_resp["invariant_message"],
                json_resp["invariant_pass"],
                json_resp["exploit_pass"],
            ) = get_fields_from_agent_log(log_file)
            judge_data_agg[bounty_name] = json_resp
    return judge_data_all, judge_data_agg


def detect_patch_table(judge_data_agg):
    df = pd.DataFrame.from_dict(judge_data_agg, orient="index")
    df["title_match"] = df.apply(
        lambda row: row["bounty_title"] in row["repo_titles"], axis=1
    )

    custom_order = [
        "bounty_title",
        "repo_titles",
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
        "invariant_pass",
        "exploit_pass",
    ]

    df = df[custom_order]
    return df


def detect_exploit_table(judge_data_agg):
    df = pd.DataFrame.from_dict(judge_data_agg, orient="index")
    df["title_match"] = df.apply(
        lambda row: row["bounty_title"] in row["repo_titles"], axis=1
    )

    custom_order = [
        "bounty_title",
        "repo_titles",
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
    ]

    df = df[custom_order]
    return df


def filter_df(df, submission_success=None, wf_success=None, title_match=None):
    if submission_success is not None:
        df = df[df["submission_success"] == submission_success]
    if wf_success is not None:
        df = df[df["wf_success"] == wf_success]
    if title_match is not None:
        df = df[df["title_match"] == title_match]
    return df


def filter_exploit_tables(
    df,
    judge_dir,
    logs_dir,
    judge_model,
    agent_models,
    submission_success=None,
    wf_success=None,
    title_match=None,
):
    aggregated_dfs = []

    # Loop through the agent models
    for agent_model in agent_models:
        judge_data_all, judge_data_agg = aggregated_results(
            judge_dir, logs_dir, judge_model, agent_model
        )
        df = detect_exploit_table(judge_data_agg)

        filtered_df = filter_df(
            df, submission_success, wf_success, title_match
        ).reset_index()
        filtered_df = filtered_df.rename(columns={"index": "bounty_name"})

        # Add agent model as a column
        filtered_df["agent_model"] = agent_model
        aggregated_dfs.append(filtered_df)

    final_df = pd.concat(aggregated_dfs, ignore_index=True)

    columns_to_include = [
        "agent_model",
        "bounty_name",
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
    ]

    # Exclude not-None filter columns
    if submission_success is not None:
        columns_to_include.remove("submission_success")
    if wf_success is not None:
        columns_to_include.remove("wf_success")
    if title_match is not None:
        columns_to_include.remove("title_match")

    final_df = final_df[columns_to_include]

    return final_df


def filter_patch_tables(
    df,
    judge_dir,
    logs_dir,
    judge_model,
    agent_models,
    submission_success=None,
    wf_success=None,
    title_match=None,
):
    aggregated_dfs = []

    for agent_model in agent_models:
        judge_data_all, judge_data_agg = aggregated_results(
            judge_dir, logs_dir, judge_model, agent_model
        )
        df = detect_patch_table(judge_data_agg)
        df[df["invariant_scores"].apply(lambda x: len(x) > 0)]
        filtered_df = filter_df(
            df, submission_success, wf_success, title_match
        ).reset_index()
        filtered_df = filtered_df.rename(columns={"index": "bounty_name"})

        # Add agent model as a column
        filtered_df["agent_model"] = agent_model
        aggregated_dfs.append(filtered_df)

    final_df = pd.concat(aggregated_dfs, ignore_index=True)

    columns_to_include = [
        "agent_model",
        "bounty_name",
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
        "invariant_pass",
        "exploit_pass",
    ]

    # Exclude not-None filter columns
    if submission_success is not None:
        columns_to_include.remove("submission_success")
    if wf_success is not None:
        columns_to_include.remove("wf_success")
    if title_match is not None:
        columns_to_include.remove("title_match")

    final_df = final_df[columns_to_include]

    return final_df


def get_stats(df):
    stats = {}
    stats["Total Evaluations"] = len(df)
    stats["Workflow Successes"] = len(df[df["wf_success"] == True])
    stats["Submission Successes"] = len(df[df["submission_success"] == True])
    stats["Workflow Failures"] = len(df[df["wf_success"] == False])
    stats["Submission Failures"] = len(df[df["submission_success"] == False])
    stats["Title Matches"] = len(df[df["title_match"] == True])
    stats["Title Mismatches"] = len(df[df["title_match"] == False])

    # Calculate TP, FP, TN, FN
    stats["True Positives (TP)"] = len(
        df[(df["submission_success"] == True) & (df["wf_success"] == True)]
    )
    stats["False Positives (FP)"] = len(
        df[(df["submission_success"] == False) & (df["wf_success"] == True)]
    )
    stats["False Negatives (FN)"] = len(
        df[(df["submission_success"] == True) & (df["wf_success"] == False)]
    )
    stats["True Negatives (TN)"] = len(
        df[(df["submission_success"] == False) & (df["wf_success"] == False)]
    )

    return stats


def exploit_stats(judge_dir, logs_dir, judge_model, agent_models):
    agent_stats = {}
    for agent_model in agent_models:
        print(f"Evaluating agent model : {agent_model}")
        judge_data_all, judge_data_agg = aggregated_results(
            judge_dir, logs_dir, judge_model, agent_model
        )
        df = detect_exploit_table(judge_data_agg)
        agent_stats[agent_model] = get_stats(df)
    stats_df = pd.DataFrame(agent_stats)

    # Transpose the DataFrame to have agent models as rows
    stats_df = stats_df.T
    return stats_df


def patch_stats(judge_dir, logs_dir, judge_model, agent_models):
    agent_stats = {}
    for agent_model in agent_models:
        print(f"Evaluating agent model : {agent_model}")
        judge_data_all, judge_data_agg = aggregated_results(
            judge_dir, logs_dir, judge_model, agent_model
        )
        df = detect_patch_table(judge_data_agg)
        # filter for valid submissions (successfully restarted & ran invariants (invariants don't have to pass))
        df[df["invariant_scores"].apply(lambda x: len(x) > 0)]
        agent_stats[agent_model] = get_stats(df)
    stats_df = pd.DataFrame(agent_stats)

    # Transpose the DataFrame to have agent models as rows
    stats_df = stats_df.T
    return stats_df


# Usage e.g.: python3 judge_analysis.py DetectExploit
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "wf_type",
        type=str,
        help="Type of Workflow, e.g. DetectPatch or DetectExploit",
    )
    args = parser.parse_args()
    wf_type = args.wf_type
    judge_model = "o3-2025-04-16-high-reasoning-effort"
    agent_models = [
        "google-gemini-2.5-pro-preview-03-25",
        "anthropic-claude-3-7-sonnet-20250219-extended-thinking",
        "openai-gpt-4.1-2025-04-14",
    ]
    judge_dir = "judge_responses" + wf_type
    if wf_type == "DetectPatch":
        judge_dir = "judge_responses/DetectPatch"
        logs_dir = "5-1-detect_patch_cwe_only"
    elif wf_type == "DetectExploit":
        judge_dir = "judge_responses/DetectExploit"
        logs_dir = "5-1-detect_cwe_only"
    else:
        print("Unrecognized Workflow Type. Exiting.")
        return

    if wf_type == "DetectPatch":
        stats_df = patch_stats(judge_dir, logs_dir, judge_model, agent_models)
        # Get all false positives for DetectPatch
        # filter_patch_tables(df, submission_success=False, wf_success=True, title_match=None)

    elif wf_type == "DetectExploit":
        stats_df = exploit_stats(judge_dir, logs_dir, judge_model, agent_models)
        # Get all false negatives for DetectExploit
        # filter_exploit_tables(df, submission_success=True, wf_success=False, title_match=None)

    print(stats_df)


if __name__ == "__main__":
    main()
