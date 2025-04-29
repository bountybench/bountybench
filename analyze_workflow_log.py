import json
import argparse
import os
import re # Import re for workflow type extraction

def analyze_log(file_path):
    """
    Analyzes the workflow log JSON file and outputs a summary dictionary.
    """
    if not os.path.exists(file_path):
        print(json.dumps({"error": f"File not found at {file_path}"}, indent=4))
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Error decoding JSON from {file_path}: {e}"}, indent=4))
        return
    except Exception as e:
        print(json.dumps({"error": f"Error reading file {file_path}: {e}"}, indent=4))
        return

    summary_data = {}

    # --- Extract Data ----
    metadata = data.get("workflow_metadata", {})
    usage = data.get("workflow_usage", {})
    phases = data.get("phase_messages", [])

    # Assume only one phase
    phase_one = phases[0] if phases else {}
    phase_one_usage = phase_one.get("phase_usage", {})
    agent_messages = phase_one.get("agent_messages", [])

    # --- Populate Dictionary --- 

    # workflow_type: Extract from workflow_name (e.g., DetectWorkflow -> detect)
    workflow_name = metadata.get('workflow_name', '')
    match = re.match(r"(Detect|Patch|Exploit)Workflow", workflow_name)
    summary_data['workflow_type'] = match.group(1).lower() if match else 'unknown'

    # task: (task_dir without 'bountybench/' + number)
    task_meta = metadata.get("task", {})
    task_dir = task_meta.get('task_dir', '').replace('bountybench/', '')
    bounty_num = task_meta.get('bounty_number', 'N/A')
    summary_data['task'] = f"{task_dir}_{bounty_num}" if task_dir else 'N/A'

    # total_iterations: Length of agent messages in phase 1
    summary_data['total_iterations'] = len(agent_messages)

    # model: Extract from the first relevant action message
    model_name = "N/A"
    for msg in agent_messages:
        action_msgs = msg.get("action_messages")
        if isinstance(action_msgs, list):
            for action_msg in action_msgs:
                if isinstance(action_msg, dict) and action_msg.get("resource_id") == "model":
                    meta = action_msg.get("additional_metadata", {})
                    model_name = meta.get("model", "N/A")
                    if model_name != "N/A":
                        break # Found the first model name
            if model_name != "N/A":
                break
    summary_data['model'] = model_name

    # model_calls: Count executor_agent messages in phase 1
    summary_data['model_calls'] = sum(1 for msg in agent_messages if msg.get("agent_id") == "executor_agent")

    # Usage stats
    summary_data['total_input_tokens'] = usage.get('total_input_tokens')
    summary_data['total_output_tokens'] = usage.get('total_output_tokens')
    summary_data['total_query_time_taken_in_ms'] = phase_one_usage.get('query_time_taken_in_ms')
    summary_data['total_iteration_time_ms'] = phase_one_usage.get('total_iteration_time_ms')

    # Status fields
    summary_data['complete'] = metadata.get('workflow_summary', {}).get('complete')
    summary_data['success'] = phase_one.get('success')
    summary_data['submit'] = phase_one.get('submit')

    # --- Workflow Specific Data --- 
    summary_data['workflow_specific_data'] = {}
    if summary_data['workflow_type'] == 'patch' and summary_data['complete']:
        # Initialize defaults
        patch_specific_data = {
            'has_changes': False, 
            'repo_invariant_check': [], 
            'repo_invariant_details': [], 
            'bounty_invariant_check': [],
            'bounty_invariant_details': [],
            'patch_check': False
        }
        # --- Get Thresholds from top-level additional_metadata ---
        top_level_add_meta = data.get("additional_metadata", {})
        repo_thresholds = top_level_add_meta.get("repo_metadata", {}).get("invariant_thresholds", {})
        bounty_metadata = top_level_add_meta.get("bounty_metadata", {})
        bounty_thresholds = bounty_metadata.get("invariant_thresholds", {})
        # --------------------------------------------------------

        # --- Process Actions from ALL Agent Messages ---
        last_verify_action = None
        last_agent_msg = agent_messages[-1] if agent_messages else {}

        # 1. has_changes check (based on last agent message actions)
        patch_specific_data['has_changes'] = bool(last_agent_msg.get("action_messages", [])) 
        
        # Iterate through messages for invariants and last verify
        for msg in agent_messages:
            action_msgs = msg.get("action_messages", [])
            if isinstance(action_msgs, list):
                for action_msg in action_msgs:
                    if isinstance(action_msg, dict):
                        # 2/3. Process Repo and Bounty Invariant Runs
                        add_meta = action_msg.get("additional_metadata", {})
                        if action_msg.get("resource_id") == "repo_invariants_subprocess" and repo_thresholds:
                            scores = add_meta.get("repo_invariant_scores", {})
                            individual_results = []
                            all_passed = True
                            details = {"scores": scores, "thresholds": repo_thresholds}
                            for inv, threshold in repo_thresholds.items():
                                score = scores.get(inv)
                                passed = score is not None and score >= threshold
                                if not passed:
                                    all_passed = False
                            patch_specific_data['repo_invariant_check'].append(all_passed)
                            patch_specific_data['repo_invariant_details'].append(details)
                            
                        elif action_msg.get("resource_id") == "bounty_invariants_subprocess" and bounty_thresholds:
                            scores = add_meta.get("bounty_invariant_scores", {})
                            individual_results = []
                            all_passed = True
                            details = {"scores": scores, "thresholds": bounty_thresholds}
                            for inv, threshold in bounty_thresholds.items():
                                score = scores.get(inv)
                                passed = score is not None and score >= threshold
                                if not passed:
                                    all_passed = False
                            patch_specific_data['bounty_invariant_check'].append(all_passed)
                            patch_specific_data['bounty_invariant_details'].append(details)
                            
                        # 4. Find last verify action for patch_check
                        if action_msg.get("additional_metadata", {}).get("command") == "./verify.sh":
                            last_verify_action = action_msg
        # -------------------------------------------------

        # 4. patch_check (based on last verify.sh run)
        if last_verify_action:
            patch_specific_data['patch_check'] = last_verify_action.get("additional_metadata", {}).get("exit_code") == 1
        else:
            pass # No action needed if no verify command was found

        summary_data['workflow_specific_data'] = patch_specific_data

    # Print the final dictionary as JSON
    print(json.dumps(summary_data, indent=4))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze workflow log JSON file and output summary dictionary.")
    parser.add_argument("log_file", help="Path to the JSON log file.")
    args = parser.parse_args()

    analyze_log(args.log_file)
