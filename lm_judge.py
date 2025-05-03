import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from get_writeups import extract_huntr_reported_date, read_huntr_writeup
from prompts.prompts import LM_JUDGE_DETECT_PATCH_PROMPT, LM_JUDGE_DETECT_PROMPT
from resources.model_resource.anthropic_models.anthropic_models import AnthropicModels
from resources.model_resource.openai_models.openai_models import OpenAIModels


# -----------------------------
# Log filtering utilities
# -----------------------------
def remove_log_headers(line):
    pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \w+ +\[.*\]"
    return re.sub(pattern, "", line).strip()


def filter_logs(lines, start_pattern, end_pattern):
    capture = False
    filtered_lines = []
    start_pattern = (
        re.compile(start_pattern) if isinstance(start_pattern, str) else start_pattern
    )
    end_pattern = (
        re.compile(end_pattern) if isinstance(end_pattern, str) else end_pattern
    )

    for line in lines:
        if not capture and start_pattern.search(line):
            capture = True
        if end_pattern.search(line):
            capture = False
            break
        if capture:
            filtered_lines.append(remove_log_headers(line))
    return filtered_lines


# -----------------------------
# Data extraction functions
# -----------------------------
def filter_writeups_by_date(report_date_str, repo_name):
    original_date = datetime.strptime(report_date_str, "%m_%d_%Y")
    file_dir = f"html_writeups/{repo_name}"
    all_files = os.listdir(file_dir)
    return [
        file
        for file in all_files
        if file.startswith("report_")
        and file.endswith(".html")
        and re.search(r"\d{2}_\d{2}_\d{4}", file)
        and datetime.strptime(re.search(r"\d{2}_\d{2}_\d{4}", file).group(), "%m_%d_%Y")
        >= original_date
    ]


def extract_titles(writeups, repo_name):
    file_dir = f"html_writeups/{repo_name}"
    return [
        BeautifulSoup(
            Path(os.path.join(file_dir, file)).read_text(encoding="utf-8"),
            "html.parser",
        )
        .find("h1", id="title")
        .text.strip()
        for file in writeups
    ]


def extract_valid_set_of_titles(bounty_name):
    repo_name, bounty_number = bounty_name.split("_")
    full_repo_dir = os.path.join("bountybench", repo_name)
    writeup = read_huntr_writeup(full_repo_dir, bounty_number)
    date_str = extract_huntr_reported_date(writeup)
    print(f"bounty report date: {date_str}")
    return extract_titles(filter_writeups_by_date(date_str, repo_name), repo_name)


def extract_executor_reflection_messages(json_path: Path, num_messages: int = 3):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    messages = []
    for phase in data.get("phase_messages", []):
        submit = phase["submit"]
        for agent_msg in phase.get("agent_messages", []):
            if agent_msg.get("agent_id") == "executor_agent":
                for action in agent_msg.get("action_messages", []):
                    if isinstance(action, dict) and isinstance(
                        action.get("message"), str
                    ):
                        message = action["message"]
                        if message.strip().startswith("Reflection"):
                            messages.append(message)
    return messages[-num_messages:], submit


# -----------------------------
# Prompt construction helpers
# -----------------------------
def format_titles(arr):
    return "\n".join(f"{i + 1}. {title}" for i, title in enumerate(arr))


def format_logs(arr):
    return "\n\n".join(arr)


def get_patch_prompt(bounties, iterations, script):
    script_block = (
        (
            f"Below is the git diff between the agent's patched codebase and the original codebase:\n"
            f"--- BEGIN PATCH SCRIPT ---\n{script}\n--- END PATCH SCRIPT ---\n"
        )
        if script
        else ""
    )
    return LM_JUDGE_DETECT_PATCH_PROMPT.format(
        bounties=bounties, iterations=iterations, patch_script=script_block
    )


def get_exploit_prompt(bounties, iterations, script):
    script_block = (
        (
            f"Below are the agent produced exploit scripts:\n"
            f"--- BEGIN EXPLOIT SCRIPT ---\n{script}\n--- END EXPLOIT SCRIPT ---\n"
        )
        if script
        else ""
    )
    return LM_JUDGE_DETECT_PROMPT.format(
        bounties=bounties, iterations=iterations, exploit_script=script_block
    )


# -----------------------------
# Script filtering
# -----------------------------
def filter_exploit_scripts(log_file):
    with open(log_file, "r") as file:
        return "\n".join(
            filter_logs(
                file.readlines(),
                r"printing file: bountybench/.*/exploit_files/.*",
                r"printing file: bountybench/.*/.gitignore",
            )
        )


def filter_patch_scripts(log_file):
    with open(log_file, "r") as file:
        logs = filter_logs(
            file.readlines(),
            "Checking for git diff in directory",
            "Submission received.",
        )
    return "\n".join(filter_logs(logs, "Git diff: diff ", "Submission received."))


# -----------------------------
# LLM interaction
# -----------------------------
def call_llm(prompt, model, path):
    if model.split("/")[0] == "anthropic":
        judge_model = AnthropicModels()
    elif model.split("/")[0] == "openai":
        judge_model = OpenAIModels()
    else:
        print("ERROR: Invalid model")
        return None
    try:
        response = judge_model.request(
            model=model,
            message=prompt,
            temperature=0.7,
            max_tokens=4096,
            stop_sequences=[],
        )
        output_filename = f"{model.split('/')[-1]}_judge_response_{path.name}"
        print("Judge response saved to:", output_filename)
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "prompt": prompt,
                    "content": response.content,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "time_taken_in_ms": response.time_taken_in_ms,
                    "status_code": response.status_code,
                },
                f,
                indent=2,
            )
        return response
    except Exception as e:
        print(f"LLM request failed: {e}")
        return None


def extract_json_block_from_response(text):
    match = re.search(r"\{.*?\}\s*(?=###|$)", text, re.DOTALL)
    if not match:
        print("No JSON block found.")
        return None
    try:
        return json.loads(match.group(0).strip())
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        return None


# -----------------------------
# Main execution
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bounty_name", type=str, help="e.g., lunary_0")
    parser.add_argument(
        "model",
        type=str,
        help="Name of model, e.g. anthropic/claude-3-7-sonnet-20250219",
    )
    parser.add_argument("log_file", type=str, help="Path to the log file")
    parser.add_argument("full_log_file", type=str, help="Path to full execution log")
    args = parser.parse_args()

    titles = extract_valid_set_of_titles(args.bounty_name)
    msgs, submit = extract_executor_reflection_messages(Path(args.log_file))
    formatted_titles = format_titles(titles)
    formatted_logs = format_logs(msgs)

    if "DetectPatchWorkflow" in args.full_log_file:
        script = filter_patch_scripts(args.full_log_file) if submit else ""
        prompt = get_patch_prompt(formatted_titles, formatted_logs, script)
    elif "DetectWorkflow" in args.full_log_file:
        script = filter_exploit_scripts(args.full_log_file) if submit else ""
        prompt = get_exploit_prompt(formatted_titles, formatted_logs, script)
    else:
        print("Unrecognized workflow type in log file name.")
        return

    result = call_llm(prompt, args.model, Path(args.log_file))
    if result and hasattr(result, "content"):
        parsed = extract_json_block_from_response(result.content)
        print(parsed)


if __name__ == "__main__":
    main()
