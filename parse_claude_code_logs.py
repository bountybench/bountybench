#!/usr/bin/env python3
"""
Script to parse Claude code logs and output a CSV file.
"""
import argparse
import csv
import json
import os
import sys


def parse_log_file(path):
    """Parse a single JSON log file and extract relevant fields."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to parse JSON file {path}: {e}", file=sys.stderr)
        return None
    rec = {}
    # Workflow metadata
    wm = data.get("workflow_metadata", {})
    rec["workflow_name"] = wm.get("workflow_name")
    rec["workflow_id"] = data.get("workflow_id")
    wsum = wm.get("workflow_summary", {})
    rec["complete"] = wsum.get("complete")
    rec["success"] = wsum.get("success")
    task = wm.get("task", {})
    rec["task_dir"] = task.get("task_dir")
    rec["bounty_number"] = task.get("bounty_number")
    # Derived task_name
    if rec["task_dir"] is not None and rec["bounty_number"] is not None:
        rec["task_name"] = f"{rec['task_dir']}_{rec['bounty_number']}"
    else:
        rec["task_name"] = None
    # Phase summaries
    phase_msgs = data.get("phase_messages", [])
    summaries = []
    for p in phase_msgs:
        ps = p.get("phase_summary")
        if ps is not None:
            summaries.append(ps)
    rec["phase_summary"] = ";".join(summaries)
    # Bounty metadata
    add_meta = data.get("additional_metadata", {})
    bmeta = add_meta.get("bounty_metadata", {})
    rec["severity"] = bmeta.get("severity")
    rec["disclosure_bounty"] = bmeta.get("disclosure_bounty")
    rec["patch_bounty"] = bmeta.get("patch_bounty")
    # Commits
    rec["bountyagent_commit"] = data.get("codebase_version")
    rec["bountybench_commit"] = data.get("task_codebase_version")
    # Initialize invariant fields
    rec["invariant_scores"] = None
    rec["invariant_message"] = None
    # Extract invariant message and scores from patch_agent
    for phase in phase_msgs:
        for agent_msg in phase.get("agent_messages", []):
            if agent_msg.get("agent_id") == "patch_agent":
                msg_text = agent_msg.get("message") or ""
                if "Hidden tests" in msg_text:
                    rec["invariant_message"] = msg_text
                    for action in agent_msg.get("action_messages", []):
                        if action.get("resource_id") == "repo_invariants_subprocess":
                            scores = action.get("additional_metadata", {}).get(
                                "repo_invariant_scores"
                            )
                            if scores is not None:
                                rec["invariant_scores"] = scores
                                break
                    break
        if rec["invariant_message"] is not None:
            break
    # Determine exploit blocked based on invariant message
    inv_msg = rec.get("invariant_message") or ""
    rec["invariant_pass"] = "Hidden tests passed" in inv_msg
    wf = rec.get("workflow_name")
    exploit_pass = False
    if inv_msg and wf in ("PatchWorkflow", "patch_workflow"):
        exploit_pass = "Exploit check passed" in inv_msg
    elif inv_msg and wf in ("DetectPatchWorkflow", "detect_patch_workflow"):
        exploit_pass = any(
            sub in inv_msg
            for sub in (
                "1 exploits fail out of",
                "2 exploits fail out of",
                "3 exploits fail out of",
            )
        )
    rec["exploit_blocked"] = exploit_pass
    return rec


def main():
    parser = argparse.ArgumentParser(
        description="Parse Claude code logs and output CSV."
    )
    parser.add_argument("dirs", nargs="+", help="Log directories to parse")
    parser.add_argument(
        "-o",
        "--output",
        default="parsed_logs.csv",
        help="Output CSV file (default: parsed_logs.csv)",
    )
    args = parser.parse_args()
    rows = []
    for d in args.dirs:
        if not os.path.isdir(d):
            print(f"Warning: {d} is not a directory, skipping.", file=sys.stderr)
            continue
        for root, _, files in os.walk(d):
            for fname in files:
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(root, fname)
                rec = parse_log_file(path)
                if rec is not None:
                    rec["log_file"] = path
                    rows.append(rec)
    if not rows:
        print("No log records parsed.", file=sys.stderr)
        sys.exit(1)
    # Write to CSV
    fieldnames = [
        "log_file",
        "workflow_name",
        "workflow_id",
        "complete",
        "success",
        "task_dir",
        "bounty_number",
        "task_name",
        "phase_summary",
        "severity",
        "disclosure_bounty",
        "patch_bounty",
        "bountyagent_commit",
        "bountybench_commit",
        "invariant_scores",
        "exploit_blocked",
    ]
    with open(args.output, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rec in rows:
            # Serialize invariant_scores dict to JSON string
            inv = rec.get("invariant_scores")
            rec_str = json.dumps(inv) if inv is not None else ""
            # Prepare row with only the specified fields
            row = {}
            for field in fieldnames:
                if field == "invariant_scores":
                    row[field] = rec_str
                else:
                    row[field] = rec.get(field)
            writer.writerow(row)
    print(f"Wrote {len(rows)} records to {args.output}")


if __name__ == "__main__":
    main()
