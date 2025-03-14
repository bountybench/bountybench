import json
import pandas as pd
import os
import sys
import datetime

def score_single_log(file_path):
    """
    Score a single log file.
    
    The score is 1 if:
      - workflow_metadata.workflow_summary has a key "success" whose value is True.
    
    Additionally, we extract the phase results from the "phase_messages" array and convert 
    each phase's "success" boolean to an integer (1 for True, 0 for False).
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON from {file_path}: {e}")
        return 0, []
    
    workflow_score = 0
    workflow_metadata = data.get("workflow_metadata", {})
    workflow_summary = workflow_metadata.get("workflow_summary", {})
    if isinstance(workflow_summary, dict) and workflow_summary.get("success", False):
        workflow_score = 1
    
    phase_messages = data.get("phase_messages", [])
    phase_scores = [1 if phase.get("success", False) else 0 for phase in phase_messages]

    return workflow_score, phase_scores

def score_directory(directory):
    """
    Score every JSON log file in the given directory.
    
    Returns a list of dictionaries where each dictionary has:
      - "log name": the file name
      - "score": the score computed using score_single_log()
    """
    records = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            file_path = os.path.join(directory, filename)
            workflow_score, phase_scores = score_single_log(file_path)
            records.append({
                "log_name": filename,
                "workflow_score": workflow_score,
                "phase_scores": phase_scores,
            })
    return records

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_dir = "log_scores"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # If input is a directory, score every log file; if a file, score that single log.
    if os.path.isdir(input_path):
        records = score_directory(input_path)
        df = pd.DataFrame(records)
        output_file = os.path.join(output_dir, f"report_{timestamp}.csv")
        df.to_csv(output_file, index=False)
        print(f"Report generated: {output_file}")
    elif os.path.isfile(input_path):
        score = score_single_log(input_path)
        df = pd.DataFrame([{"log name": os.path.basename(input_path), "score": score}])
        output_file = os.path.join(output_dir, f"report_{timestamp}.csv")
        df.to_csv(output_file, index=False)
        print(f"Report generated: {output_file}")
    else:
        print("Input path is neither a file nor a directory.")
