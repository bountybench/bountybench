import argparse
import ast
import json
import os
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from get_writeups import (
    create_directory,
    extract_hackerone_reported_date,
    extract_huntr_reported_date,
    get_all_available_bounties,
    read_writeup,
)
from json_helper import JSONLog
from prompts.prompts import (
    LM_JUDGE_DETECT_INITIAL_PROMPT,
    LM_JUDGE_DETECT_INITIAL_PROMPT_NO_ITERATIONS,
    LM_JUDGE_DETECT_PATCH_INITIAL_PROMPT,
    LM_JUDGE_DETECT_PATCH_PROMPT,
    LM_JUDGE_DETECT_PROMPT,
)
from resources.model_resource.anthropic_models.anthropic_models import AnthropicModels
from resources.model_resource.helm_models.helm_models import HelmModels
from resources.model_resource.model_resource import ModelResourceConfig
from resources.model_resource.model_utils import truncate_input_to_max_tokens
from resources.model_resource.openai_models.openai_models import OpenAIModels
from resources.utils import format_hackerone_writeup, format_huntr_writeup


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
    file_dir = f"valid_html_writeups/{repo_name}"
    if not Path(file_dir).exists():
        print("No valid Huntr writeups,..skipping")
        return []
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


def extract_huntr_title_from_writeup(writeup):
    soup = BeautifulSoup(writeup, "html.parser")
    title_tag = soup.find("h1", id="title")
    return title_tag.text.strip() if title_tag else ""


def extract_hackerone_title_from_writeup(writeup):
    soup = BeautifulSoup(writeup, "html.parser")
    title_element = soup.find(
        "div",
        class_="false report-heading__report-title spec-report-title flex items-center",
    )
    if title_element:
        title_div = title_element.find("div", class_="break-word")
        if title_div:
            return title_div.text.strip()
    return ""


def get_date_and_title(bounty_name):
    repo_name, bounty_number = bounty_name.rsplit("_", 1)
    full_repo_dir = os.path.join("bountybench", repo_name)
    writeup, report_path = read_writeup(full_repo_dir, bounty_number)
    if not writeup:
        return None, None, None
    if writeup == "hackerone":
        writeup = report_path.read_text(encoding="utf-8")
        date_str = extract_hackerone_reported_date(writeup)
        title = extract_hackerone_title_from_writeup(writeup)
        writeup_type = "hackerone"
    else:
        date_str = extract_huntr_reported_date(writeup)
        title = extract_huntr_title_from_writeup(writeup)
        writeup_type = "huntr"
    return date_str, title, writeup_type


def extract_valid_writeups(date_str, bounty_name):
    repo_name, _ = bounty_name.rsplit("_", 1)
    filtered_files = filter_writeups_by_date(date_str, repo_name)
    if not filtered_files:
        return []
    file_dir = f"valid_html_writeups/{repo_name}"
    writeups = [
        Path(os.path.join(file_dir, file)).read_text(encoding="utf-8")
        for file in filtered_files
    ]
    return writeups


def check_submit(json_path: Path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    phase_messages = data.get("phase_messages", [])
    if phase_messages:
        phase = phase_messages[0]
        submit = phase["submit"]
        return submit
    return False


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


def get_codex_iterations(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    codex_messages = data["phase_messages"][0]["agent_messages"][1]["action_messages"]
    commands = [
        msg["message"]
        for msg in codex_messages
        if msg["resource_id"] == "function_call"
    ]
    reflection = "Reflection: " + codex_messages[-1]["message"]
    return commands[-5:] + [reflection]


def clean_log_data(data):
    cleaned_data = []
    for entry in data:
        if "text" in entry:
            cleaned_data.append(entry["text"])
        elif "input" in entry:
            cleaned_entry = {
                k: v for k, v in entry["input"].items() if k not in {"type", "id"}
            }
            cleaned_data.append(cleaned_entry)
    return cleaned_data


def parse_partial_json_list(s):
    """
    Recovers as many full JSON objects from a (possibly truncated) list string as possible.
    """
    objs = []
    brace_count = 0
    start_idx = None

    for i, char in enumerate(s):
        if char == "{":
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0 and start_idx is not None:
                obj_str = s[start_idx : i + 1]
                try:
                    obj = json.loads(obj_str)
                    objs.append(obj)
                except json.JSONDecodeError:
                    break  # stop at first failure

    return objs


def extract_content(data):
    extracted_content = []
    for action_message in data.get("action_messages", []):
        messages = action_message.get("message", [])
        if isinstance(messages, str):
            # print(messages)
            # unescaped = bytes(messages, "utf-8").decode("unicode_escape")
            messages = parse_partial_json_list(messages)
        for message in messages:
            if message.get("role") == "assistant":
                for content in message.get("content", []):
                    if (
                        content.get("type") == "text"
                        or content.get("type") == "tool_use"
                    ):
                        extracted_content.append(content)
    return extracted_content


def extract_relevant_content_from_phase(phase_data):
    relevant_content = []
    for phase in phase_data.get("phase_messages", []):
        # Check for 'agent_messages' in each phase
        for message in phase.get("agent_messages", []):
            if message.get("agent_id") == "claude_code":
                # print(message)
                relevant_content = extract_content(message)
                # print(message)
    return relevant_content


def get_claude_code_iterations(json_path: Path, num_messages: int = 5):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    iterations = extract_relevant_content_from_phase(data)
    cleaned_data = clean_log_data(iterations)
    print(format_logs(cleaned_data[-num_messages:]))
    return cleaned_data[-num_messages:]


def get_file_path(all_logs_dir, bounty_name, model_name):
    # Join the directory path
    if "claude-code" in model_name:
        # dir_path = os.path.join(all_logs_dir, "Detect_cwe_only")
        dir_path = os.path.join(all_logs_dir, bounty_name)
    elif "codex" in model_name:
        dir_path = os.path.join(all_logs_dir, bounty_name)
        dir_path = os.path.join(dir_path, "openai-o4-mini-2025-04-16")
    else:
        dir_path = os.path.join(all_logs_dir, bounty_name)
        dir_path = os.path.join(dir_path, model_name)
    # List all files in the directory
    if not Path(dir_path).exists():
        return None
    files = [
        f
        for f in os.listdir(dir_path)
        if os.path.isfile(os.path.join(dir_path, f)) and (not f.startswith("."))
    ]
    # Check if there's exactly one file in the directory
    if len(files) == 1:
        # Return the full file path
        return os.path.join(dir_path, files[0])
    else:
        print(files)
        print("There is not exactly one file in the directory.")
        return None


def extract_report_numbers(text):
    # Regular expression to extract the content after "SELECTED LIST:" until the next "##" or end of text
    numbers = re.findall(r"(?<=SELECTED LIST:)(.*?)(?=##|$)", text, re.DOTALL)
    selected_list_text = (
        numbers[0] if numbers else ""
    )  # The content after "SELECTED LIST:"

    # Split the selected list text into individual lines
    lines = selected_list_text.strip().split("\n")
    # List to store extracted numbers
    numbers_extracted = []

    for line in lines:
        # If the line contains a colon, extract the number before the colon
        if ":" in line:
            match = re.search(r"(\d+)(?=:)", line)
            if match:
                numbers_extracted.append(int(match.group(1)))
            else:
                # If no match found, fall back to extracting the number before the period
                match = re.match(r"^(\d+)\.", line)
                if match:
                    numbers_extracted.append(int(match.group(1)))
        else:
            # If there's no colon, just extract the number before the period
            match = re.match(r"^(\d+)\.", line)
            if match:
                numbers_extracted.append(int(match.group(1)))

    return numbers_extracted


def get_repo_all_bounty_titles(repo_name):
    bounty_nums = get_all_available_bounties(repo_name)
    bounties = [repo_name + "_" + num for num in bounty_nums]
    all_titles = []
    for bounty in bounties:
        _, title, writeup_type = get_date_and_title(bounty)
        all_titles.append(title)
    return all_titles


# -----------------------------
# Prompt construction helpers
# -----------------------------
def format_titles(arr):
    return "\n".join(f"{i + 1}. {title}" for i, title in enumerate(arr))


def format_logs(arr):
    return "\n\n".join(arr)


def format_writeups(report_numbers, valid_writeups, writeup_type):
    writeups = ""
    for num in report_numbers:
        writeups += f"Bounty Report # {num}\n"
        writeups += (
            format_huntr_writeup(valid_writeups[num - 1])
            if writeup_type == "huntr"
            else format_hackerone_writeup(valid_writeups[num - 1])
        )
        writeups += "\n\n"
    return writeups


def generate_script_block(script, script_type):
    script_header = (
        "git diff between the agent's patched codebase and the original codebase"
        if script_type == "patch"
        else "agent produced exploit scripts"
    )
    return (
        f"Below is the {script_header}:\n"
        f"--- BEGIN {script_type.upper()} SCRIPT ---\n{script}\n--- END {script_type.upper()} SCRIPT ---\n"
    )


def generate_prompt(bounties, iterations, prompt_type, full_log_file):
    """
    General function to generate the appropriate prompt based on the type (full or initial)
    and the type of script (patch or exploit).
    """
    if "DetectPatchWorkflow" in full_log_file:
        script = filter_patch_scripts(full_log_file)
        script_type = "patch"
    elif "DetectWorkflow" in full_log_file:
        script = filter_exploit_scripts(full_log_file)
        script_type = "exploit"
    else:
        print("Unrecognized workflow type in log file name.")
        return
    script_block = generate_script_block(script, script_type)

    if prompt_type == "full":
        if script_type == "patch":
            return LM_JUDGE_DETECT_PATCH_PROMPT.format(
                bounties=bounties, iterations=iterations, patch_script=script_block
            )
        elif script_type == "exploit":
            return LM_JUDGE_DETECT_PROMPT.format(
                bounties=bounties, iterations=iterations, exploit_script=script_block
            )
    elif prompt_type == "initial":
        if script_type == "patch":
            return LM_JUDGE_DETECT_PATCH_INITIAL_PROMPT.format(
                bounties=bounties, iterations=iterations, patch_script=script_block
            )
        elif script_type == "exploit":
            return LM_JUDGE_DETECT_INITIAL_PROMPT_NO_ITERATIONS.format(
                bounties=bounties, exploit_script=script_block
            )


def truncate_prompt(prompt, model, use_helm=False):
    config = ModelResourceConfig.create(model=model)
    prompt = truncate_input_to_max_tokens(
        max_input_tokens=config.max_input_tokens,
        model_input=prompt,
        model=model,
        use_helm=use_helm,
    )
    return prompt


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
def call_llm(prompt, model, use_helm=False):
    # Select the model based on input parameters
    if use_helm:
        judge_model = HelmModels()
    elif model.split("/")[0] == "anthropic":
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
        result = {
            "prompt": prompt,
            "content": response.content,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "time_taken_in_ms": response.time_taken_in_ms,
            "status_code": response.status_code,
        }
        return result
    except Exception as e:
        print(f"LLM request failed: {e}")
        return None


def extract_json_block_from_response(text):
    matches = re.findall(r"(\{\n.*?\n\})", text, re.DOTALL)
    # Ensure there are matches and get the last one
    if matches:
        json_block = matches[-1]
    else:
        print("No JSON block found.")
        return None
    try:
        parsed_json = json.loads(json_block.strip())
        # Check if the JSON contains the expected key
        if "bounty_title" in parsed_json:
            return parsed_json
        else:
            print("Parsed incorrect JSON.")
            return None
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
    return None


def judge(bounty_name, model, agent_model, log_file, full_log_file):
    orig_date, orig_title, writeup_type = get_date_and_title(bounty_name)
    if not orig_date or not orig_title:
        print(f"No valid original writeup for the given bounty {bounty_name}, skipping")
        return
    print(f"original bounty report date: {orig_date}")
    print(f"original bounty report title: {orig_title}")
    valid_writeups = extract_valid_writeups(orig_date, bounty_name)
    if not valid_writeups:
        return
    if writeup_type == "huntr":
        titles = [
            extract_huntr_title_from_writeup(writeup) for writeup in valid_writeups
        ]
    else:
        titles = [
            extract_hackerone_title_from_writeup(writeup) for writeup in valid_writeups
        ]
    if agent_model == "codex":
        msgs = get_codex_iterations(Path(log_file))
    elif agent_model == "claude-code":
        msgs = get_claude_code_iterations(Path(log_file))
    else:
        msgs = extract_executor_reflection_messages(Path(log_file))
    full_chat_history = []
    name = model.split("/")[-1]
    create_directory(f"./0507_judge_responses_no_CWE/{name}/{agent_model}")
    output_filename = f"0507_judge_responses_no_CWE/{name}/{agent_model}/{name}_judge_response_{agent_model}_{bounty_name}.json"
    # if Path(output_filename).exists():
    #    print(f"{output_filename} exists, skipping...")
    #    return
    formatted_logs = format_logs(msgs)
    if len(valid_writeups) > 5:
        # More than 5 reports so we would need to first just provide the list of titles
        formatted_titles = format_titles(titles)
        prompt = generate_prompt(
            formatted_titles,
            formatted_logs,
            prompt_type="initial",
            full_log_file=full_log_file,
        )
        prompt = truncate_prompt(prompt, model)

        result = call_llm(prompt, model)
        result["orig_title"] = orig_title
        content = result["content"]
        full_chat_history.append(result)
        if not "SELECTED LIST" in content:
            print("No valid initial response, terminating")
            with open(output_filename, "w") as file:
                json.dump(full_chat_history, file, indent=4)
            return
        report_numbers = extract_report_numbers(content)
        print(report_numbers)
    else:
        report_numbers = range(1, 1 + len(valid_writeups))
    # One iteration (valid_writeups <= 5)
    writeups = format_writeups(report_numbers, valid_writeups, writeup_type)
    prompt = generate_prompt(
        writeups, formatted_logs, prompt_type="full", full_log_file=full_log_file
    )
    prompt = truncate_prompt(prompt, model)
    # print(prompt)
    result = call_llm(prompt, model)
    result["orig_title"] = orig_title
    if result:
        json_block = extract_json_block_from_response(result["content"])
        if json_block:
            result["response_json"] = json_block
    full_chat_history.append(result)
    with open(output_filename, "w") as file:
        json.dump(full_chat_history, file, indent=4)

    return


# -----------------------------
# Post processing
# -----------------------------


def get_fields_from_agent_log(log_dir):
    json_log = JSONLog(log_dir)
    return (
        json_log.success,
        json_log.invariant_scores,
        json_log.invariant_message,
        json_log.invariant_pass,
        json_log.exploit_pass,
    )


# -----------------------------
# Main execution
# -----------------------------
def main():
    """
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
    """
    parser = argparse.ArgumentParser()
    # parser.add_argument("bounty_name", type=str, help="e.g., lunary_0")
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
    # bounty_name = args.bounty_name
    model = args.judge_model
    model_name = args.agent_model

    # all_logs_dir = "4.30.detect_patch/" + model_name
    all_logs_dir = "detect/" + model_name
    all_logs_dir_1 = "detect_1/" + model_name
    # all_logs_dir = "detect_cwe-only/" + model_name
    # all_logs_dir_1 = "detect_cwe-only_1/" + model_name
    all_bounties = os.listdir(all_logs_dir + "/logs")
    for bounty_name in all_bounties:
        bounty_name = "agentscope_0"
        print(bounty_name)
        if bounty_name.startswith("."):
            continue
        log_file = get_file_path(all_logs_dir + "/logs", bounty_name, model_name)
        log_file_1 = get_file_path(all_logs_dir_1 + "/logs", bounty_name, model_name)

        # print(log_file.split("/"))
        # print(log_file, log_file_1)
        # break
        # print(log_file.split("/")[-1], log_file_1.split("/")[-1])
        if log_file_1 and log_file.split("/")[-1] == log_file_1.split("/")[-1]:
            print("same log, skipped")
            continue
        if not check_submit(log_file):
            print("No submission, skipping evaluation")
            continue
        full_log_file = get_file_path(
            all_logs_dir + "/full_logs", bounty_name, model_name
        )
        # log_details = get_fields_from_agent_log(log_file)
        judge(bounty_name, model, model_name, log_file, full_log_file)
        break


if __name__ == "__main__":
    main()
