import json
import re
import csv
import sys
from pathlib import Path

CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}")

def extract_json_details(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ Error reading {file_path}: {e}")
        return None

    # Extract CVEs
    cves_found = []
    for phase in data.get("phase_messages", []):
        for agent_msg in phase.get("agent_messages", []):
            for action_msg in agent_msg.get("action_messages", []) or []:
                if isinstance(action_msg, dict):
                    msg = action_msg.get("message", "")
                    if isinstance(msg, str):
                        cves_found.extend(CVE_PATTERN.findall(msg))
    cves_found = list(set(cves_found))

    # Workflow success
    workflow_success = data.get("workflow_metadata", {}) \
                           .get("workflow_summary", {}) \
                           .get("success", "unknown")

    # Ground truth CVE
    true_cve = data.get("additional_metadata", {}) \
                   .get("bounty_metadata", {}) \
                   .get("CVE", "")

    # Did we match?
    match = "TRUE" if true_cve and true_cve in cves_found else "FALSE"

    return cves_found, workflow_success, true_cve, match

def find_bounty_and_model(file_path):
    parts = file_path.parts
    for i in range(len(parts) - 2):
        if parts[i] == "logs":
            bounty = parts[i + 1]
            model = parts[i + 2]
            return bounty, model
    return "unknown", "unknown"

def walk_and_collect_entries(root_dir):
    entries = []
    for path in Path(root_dir).rglob("*.json"):
        result = extract_json_details(path)
        if result is None:
            continue
        cves, success, true_cve, match = result
        if cves:
            bounty, model = find_bounty_and_model(path)
            entries.append((bounty, model, str(path), ";".join(sorted(cves)), success, true_cve, match))
    return entries

def write_csv(entries, output_csv_path):
    with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bounty", "model", "json_path", "cves_in_model_response", "workflow_success", "true_cve", "matched_true_cve"])
        writer.writerows(entries)

def main(root_folder, output_csv):
    entries = walk_and_collect_entries(root_folder)
    write_csv(entries, output_csv)
    print(f"✅ CSV written to: {output_csv} with {len(entries)} entries.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python extract_cves_full_report.py <input_folder> <output_csv>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
