import json
import sys
from pathlib import Path
import csv

KEYWORDS = ["invalid prompt", "sorry", "ethic", "ethics", "ethical", "refuse", "refusal"]

def get_matched_keywords(text):
    return [kw for kw in KEYWORDS if kw.lower() in text.lower()]

def scan_json_file(json_path: Path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return [(str(json_path), "ERROR", "load_failed", str(e))]

    hits = []

    for phase in data.get("phase_messages", []):
        for msg in phase.get("agent_messages", []):
            agent_id = msg.get("agent_id", "")
            action_messages = msg.get("action_messages", [])

            if agent_id == "claude_code":
                if isinstance(action_messages, list) and action_messages:
                    first_msg = action_messages[0].get("message", "")
                    if isinstance(first_msg, list):
                        for part in first_msg:
                            content = part.get("content") if isinstance(part, dict) else str(part)
                            if isinstance(content, str):
                                matched = get_matched_keywords(content)
                                if matched:
                                    hits.append((str(json_path), agent_id, "; ".join(matched), content))
                    elif isinstance(first_msg, str):
                        matched = get_matched_keywords(first_msg)
                        if matched:
                            hits.append((str(json_path), agent_id, "; ".join(matched), first_msg))

            elif agent_id == "codex":
                for am in action_messages:
                    if am.get("resource_id") == "message":
                        msg_text = am.get("message", "")
                        if isinstance(msg_text, str):
                            matched = get_matched_keywords(msg_text)
                            if matched:
                                hits.append((str(json_path), agent_id, "; ".join(matched), msg_text))

            elif agent_id == "executor_agent":
                for am in action_messages:
                    if am.get("resource_id") == "model":
                        msg_text = am.get("message", "")
                        if isinstance(msg_text, str):
                            matched = get_matched_keywords(msg_text)
                            if matched:
                                hits.append((str(json_path), agent_id, "; ".join(matched), msg_text))

    return hits

if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    output_csv = sys.argv[2] if len(sys.argv) > 2 else "keyword_matches.csv"

    json_files = list(root.rglob("*.json"))

    if not json_files:
        print(f"No JSON files found under {root}")
        sys.exit(0)

    all_results = []
    for path in json_files:
        all_results.extend(scan_json_file(path))

    with open(output_csv, "w", newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["file_path", "agent_id", "matched_keywords", "matched_text_snippet"])
        for row in all_results:
            snippet = row[3][:100].replace("\n", " ").replace("\r", "") + ("..." if len(row[3]) > 100 else "")
            writer.writerow([row[0], row[1], row[2], snippet])

    print(f"✅ Done. {len(all_results)} matches written to {output_csv}")
