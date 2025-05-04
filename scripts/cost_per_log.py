"""
Usage:
    python scripts/cost_per_log.py [--log_dir] [--output_file]
"""

import argparse
import json
import re
from pathlib import Path

import tqdm
from api_cost import (
    COST_PER_MILLION_CACHE_WRITE,
    COST_PER_MILLION_CACHED_INPUT_TOKENS,
    COST_PER_MILLION_INPUT_TOKENS,
    COST_PER_MILLION_OUTPUT_TOKENS,
)
from input_cache_helpers import INPUT_CACHE_HELPERS


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest BountyBench logs into Docent")
    parser.add_argument(
        "--log_dir",
        type=str,
        default="./logs",
        help="Directory containing BountyBench log files",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="./logs_cost_per_log.json",
        help="Directory to save the output JSON file",
    )
    return parser.parse_args()


args = parse_args()

LOG_DIR = Path(args.log_dir)
if not LOG_DIR.exists():
    raise FileNotFoundError(f"Log directory {LOG_DIR} does not exist.")
if not LOG_DIR.is_dir():
    raise NotADirectoryError(f"Log path {LOG_DIR} is not a directory.")

OUTPUT_FILE = Path(args.output_file)

USE_INPUT_CACHE = {
    "anthropic": False,
    "google": False,
    "openai": True,
    "deepseek-ai": False,
}

MILLION = 1_000_000


def get_model(path: Path) -> str:
    """
    Extracts the model name from the file path.
    """
    path = path.stem.split("_")[0].lower()
    if path.startswith("deepseek-ai"):
        return "deepseek-ai/" + path.split("deepseek-ai-")[-1]
    else:
        return path.replace("-", "/", 1)


def get_full_log_path(path: Path) -> Path:
    """
    Given a path to a log file, return the corresponding full log file path.
    """
    parts = list(path.parts)
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == "logs":
            parts[i] = "full_logs"
            break
    full_log_path = Path(*parts).with_suffix(".log")
    if full_log_path.exists():
        return full_log_path
    else:
        raise FileNotFoundError(f"Full log file not found: {full_log_path}")


def get_system_prompt(full_log: str) -> str:
    """
    Extracts the system prompt from the full log file.
    """
    pattern = re.compile(
        r"Model input \(truncated if over max tokens\):\s*\n"
        r"(.*?)"
        r"\nCommand: python3 print_file\.py\n"
        r"<END>\s*\n",
        re.DOTALL,
    )

    matches = list(pattern.finditer(full_log))
    if not matches:
        raise ValueError("No system prompt found in the full log file.")
    return matches[-1].group(1) + "\nCommand: python3 print_file.py\n<END>"


def get_num_calls(full_log: str) -> int:
    """
    Counts the number of model calls in the full log file.
    """
    pattern = re.compile(
        r"Model input \(truncated if over max tokens\):\s*\n"
        r"(?P<input>.*?)\s*\n"
        r"input_tokens:",
        re.DOTALL,
    )
    all_blocks = [m.group("input") for m in pattern.finditer(full_log)]
    return len(all_blocks)


def get_helper(model: str):
    """
    Get the correct input cache helper to use based on the model.
    """
    provider = model.split("/")[0]
    if provider not in INPUT_CACHE_HELPERS:
        raise ValueError(f"Unsupported model provider: {provider}")
    return INPUT_CACHE_HELPERS[provider]


if __name__ == "__main__":
    all_paths = list(LOG_DIR.rglob("**/*.json"))
    results = {}

    with tqdm.tqdm(all_paths, desc="Processing logs") as pbar:
        for path in pbar:
            with open(path, "r") as f:
                log = json.load(f)

            model = get_model(path)
            provider = model.split("/")[0]
            try:
                full_log_path = get_full_log_path(path)
                with open(full_log_path, "r") as f:
                    full_log = f.read()
            except Exception:
                results[str(path)] = {
                    "error": f"Full log file not found for {path}",
                }

            path = str(path)
            if model not in COST_PER_MILLION_INPUT_TOKENS:
                print(f"Model {model} not found in cost dictionary, skipping")
                results[path] = {"error": f"Model {model} not found in cost dictionary"}
                continue
            else:
                input_cost = COST_PER_MILLION_INPUT_TOKENS[model]
                cached_input_cost = COST_PER_MILLION_CACHED_INPUT_TOKENS[model]
                output_cost = COST_PER_MILLION_OUTPUT_TOKENS[model]
            try:
                total_input_tokens = log["workflow_usage"]["total_input_tokens"]
                total_output_tokens = log["workflow_usage"]["total_output_tokens"]
                if provider in USE_INPUT_CACHE and USE_INPUT_CACHE[provider]:
                    try:
                        system_prompt = get_system_prompt(full_log)
                        num_cache_hits = (
                            get_num_calls(full_log) - 1
                        )  # First call is cache write, subsequent calls are hits
                    except (ValueError, FileNotFoundError) as e:
                        print(f"[Skipping input cache calculation] for {path}: {e}")
                        continue

                    total_cached_input_tokens, _ = get_helper(model)(system_prompt)
                    total_cached_input_tokens *= num_cache_hits

                    regular_input_tokens = (
                        total_input_tokens - total_cached_input_tokens
                    )
                    total_input_cost = (regular_input_tokens / MILLION) * input_cost + (
                        total_cached_input_tokens / MILLION
                    ) * cached_input_cost

                    if model == "anthropic" or model == "google":
                        total_input_cost += (
                            total_cached_input_tokens
                            / MILLION
                            * COST_PER_MILLION_CACHE_WRITE
                        )

                else:
                    total_input_cost = (total_input_tokens / MILLION) * input_cost

                total_output_cost = (total_output_tokens / MILLION) * output_cost
                total_cost = total_input_cost + total_output_cost

                results[path] = {
                    "model": model,
                    "total_input_tokens": total_input_tokens,
                    "total_output_tokens": total_output_tokens,
                    "total_input_cost": total_input_cost,
                    "total_output_cost": total_output_cost,
                    "total_cost": total_cost,
                    "workflow_metadata": log.get("workflow_metadata", {}),
                    "use_input_cache": False,
                }
                if provider in USE_INPUT_CACHE and USE_INPUT_CACHE[provider]:
                    results[path]["use_input_cache"] = True
                    results[path][
                        "total_cached_input_tokens"
                    ] = total_cached_input_tokens

            except KeyError as e:
                print(f"[Skipping log] {path} Missing key in log data: {e}")
                results[path] = {
                    "error": f"Missing key in log data: {e}",
                }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Results saved to {OUTPUT_FILE}")
