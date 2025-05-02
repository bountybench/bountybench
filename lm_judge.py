import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

import get_writeups
from get_writeups import extract_huntr_reported_date, read_huntr_writeup
from prompts.prompts import LM_JUDGE_DETECT_PATCH_PROMPT
from resources.model_resource.anthropic_models.anthropic_models import AnthropicModels
from resources.model_resource.model_response import ModelResponse
from resources.utils import read_writeup


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


def extract_titles(filtered_writeups, repo_name):
    file_dir = f"html_writeups/{repo_name}"
    titles = []
    for file in filtered_writeups:
        path = file_dir + "/" + file
        writeup = Path(path).read_text(encoding="utf-8")
        soup = BeautifulSoup(writeup, "html.parser")
        title = soup.find("h1", id="title")
        titles.append(title.text.strip())
    return titles


def extract_valid_set_of_titles(bounty_name: str):
    source_dir = "bountybench"
    repo_name, bounty_number = bounty_name.split("_")
    full_repo_dir = os.path.join(source_dir, repo_name)
    writeup = read_huntr_writeup(full_repo_dir, bounty_number)
    date_str = extract_huntr_reported_date(writeup)
    print(f"bounty report date: {date_str}")
    filtered_writeups = filter_writeups_by_date(date_str, repo_name)
    titles = extract_titles(filtered_writeups, repo_name)

    return titles


def call_llm(prompt):
    judge_model = AnthropicModels()
    try:
        response = judge_model.request(
            model="anthropic/claude-3-7-sonnet-20250219",
            message=prompt,
            temperature=0.7,
            max_tokens=100,
            stop_sequences=[],
        )

        response_dict = {
            "content": response.content,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "time_taken_in_ms": response.time_taken_in_ms,
            "status_code": response.status_code,
        }

        with open("llm_response.json", "w", encoding="utf-8") as f:
            json.dump(response_dict, f, indent=2)

        return response_dict

    except Exception as e:
        print(f"LLM request failed: {e}")
        return None


def get_prompt(bounties: str, iterations: str) -> str:
    return LM_JUDGE_DETECT_PATCH_PROMPT.format(bounties=bounties, iterations=iterations)


def extract_executor_reflection_messages(json_path: Path, num_messages: int = 3):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = []
    for phase in data.get("phase_messages", []):
        for agent_msg in phase.get("agent_messages", []):
            if agent_msg.get("agent_id") == "executor_agent":
                for action in agent_msg.get("action_messages", []):
                    if isinstance(action, dict) and isinstance(
                        action.get("message"), str
                    ):
                        message = action["message"]
                        if message.strip().startswith("Reflection"):
                            messages.append(message)
    return messages[-num_messages:]


def format_titles(arr):
    return "\n".join(f"{i + 1}. {titles}" for i, titles in enumerate(arr))


def format_logs(arr):
    return "\n\n".join(f"{log}" for i, log in enumerate(arr))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "bounty_name", type=str, help="Path to a bounty, e.g., lunary_0"
    )
    parser.add_argument("log_file", type=str, help="Path to the log file to be judged")
    args = parser.parse_args()
    bounty_name = args.bounty_name
    json_file = args.log_file
    path = Path(json_file)

    titles = extract_valid_set_of_titles(str(bounty_name))
    msgs = extract_executor_reflection_messages(path)
    prompt = get_prompt(format_titles(titles), format_logs(msgs))

    result = call_llm(prompt)


if __name__ == "__main__":
    main()
