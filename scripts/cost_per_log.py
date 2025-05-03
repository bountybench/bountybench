"""
Usage:
    python scripts/cost_per_log.py [--log_dir] [--output_file]
"""

import argparse
import json
from pathlib import Path
from typing import Dict

import tqdm


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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for detailed output",
    )
    return parser.parse_args()


args = parse_args()

LOG_DIR = Path(args.log_dir)
if not LOG_DIR.exists():
    raise FileNotFoundError(f"Log directory {LOG_DIR} does not exist.")
if not LOG_DIR.is_dir():
    raise NotADirectoryError(f"Log path {LOG_DIR} is not a directory.")

OUTPUT_FILE = Path(args.output_file)
DEBUG = args.debug


# No public API for getting costs of models, therefore saving them as constants.
# last updated: May 3, 2025
COST_PER_MILLION_INPUT_TOKENS: Dict[str, float] = {
    # Anthropic models
    # - https://www.anthropic.com/pricing
    "anthropic/claude-3-7-sonnet-20250219": 3.00,
    "anthropic/claude-3-7-sonnet-20250219-extended-thinking": 3.00,
    # OpenAI models
    # - https://platform.openai.com/docs/pricing
    "openai/gpt-4o-2024-11-20": 2.50,
    "openai/gpt-4.1-2025-04-14": 2.00,
    "openai/gpt-4.5-preview-2025-02-27": 75.00,
    "openai/o4-mini-2025-04-16": 1.100,
    "openai/o4-mini-2025-04-16-low-reasoning-effort": 1.100,
    "openai/o4-mini-2025-04-16-high-reasoning-effort": 1.100,
    "openai/o3-2025-04-16": 10.00,
    "openai/o3-2025-04-16-low-reasoning-effort": 10.00,
    "openai/o3-2025-04-16-high-reasoning-effort": 10.00,
    # Together / DeepSeek models
    # - https://www.together.ai/pricing
    # - Note: Official DeepSeek API pricing $0.55 (1M input) / $2.19 (1M output)
    "deepseek-ai/deepseek-r1": 3.00,
    # Google models
    # - https://ai.google.dev/gemini-api/docs/pricing
    # - Note: Each of our API call does not exceed 200k tokens, use the prompts <= 200k tokens pricing
    "google/gemini-2.5-pro-preview-03-25": 1.25,
}

COST_PER_MILLION_OUTPUT_TOKENS = {
    # Anthropic models
    # - https://www.anthropic.com/pricing
    "anthropic/claude-3-7-sonnet-20250219": 15.00,
    "anthropic/claude-3-7-sonnet-20250219-extended-thinking": 15.00,
    # OpenAI models
    # - https://platform.openai.com/docs/pricing
    "openai/gpt-4o-2024-11-20": 10.00,
    "openai/gpt-4.1-2025-04-14": 8.00,
    "openai/gpt-4.5-preview-2025-02-27": 150.00,
    "openai/o4-mini-2025-04-16": 4.400,
    "openai/o4-mini-2025-04-16-low-reasoning-effort": 4.400,
    "openai/o4-mini-2025-04-16-high-reasoning-effort": 4.400,
    "openai/o3-2025-04-16": 40.00,
    "openai/o3-2025-04-16-low-reasoning-effort": 40.00,
    "openai/o3-2025-04-16-high-reasoning-effort": 40.00,
    # Together / DeepSeek models
    # - https://www.together.ai/pricing
    # - Note: Official DeepSeek API pricing $0.55 (1M input) / $2.19 (1M output)
    "deepseek-ai/deepseek-r1": 7.00,
    # Google models
    # - https://ai.google.dev/gemini-api/docs/pricing
    # - Note: Each of our API call does not exceed 200k tokens, use the prompts <= 200k tokens pricing
    "google/gemini-2.5-pro-preview-03-25": 10.00,
}


def get_model(path: Path) -> str:
    """Extracts the model name from the file path."""
    path = path.stem.split("_")[0].lower()
    if path.startswith("deepseek-ai"):
        return "deepseek-ai/" + path.split("deepseek-ai-")[-1]
    else:
        return path.replace("-", "/", 1)


if __name__ == "__main__":
    all_paths = list(LOG_DIR.rglob("**/*.json"))
    results = {}

    with tqdm.tqdm(all_paths, desc="Processing logs") as pbar:
        for path in pbar:
            with open(path, "r") as f:
                log = json.load(f)

            model = get_model(path)
            path = str(path)

            if model not in COST_PER_MILLION_INPUT_TOKENS:
                print(f"Model {model} not found in cost dictionary, skipping")
                results[path] = {"error": f"Model {model} not found in cost dictionary"}
            else:
                input_cost = COST_PER_MILLION_INPUT_TOKENS[model]
                output_cost = COST_PER_MILLION_OUTPUT_TOKENS[model]

            if DEBUG:
                print(f"Model: {model}")
                print(f"Input cost per million tokens: ${input_cost:.2f}")
                print(f"Output cost per million tokens: ${output_cost:.2f}")

            try:
                total_input_tokens = log["workflow_usage"]["total_input_tokens"]
                total_output_tokens = log["workflow_usage"]["total_output_tokens"]

                total_input_cost = (total_input_tokens / 1_000_000) * input_cost
                total_output_cost = (total_output_tokens / 1_000_000) * output_cost
                total_cost = total_input_cost + total_output_cost
                if DEBUG:
                    print(f"- Total input tokens: {total_input_tokens}")
                    print(f"- Total output tokens: {total_output_tokens}")
                    print(f"- Total input cost: ${total_input_cost:.2f}")
                    print(f"- Total output cost: ${total_output_cost:.2f}")
                    print(f"Total cost: ${total_cost:.2f}")

                results[path] = {
                    "model": model,
                    "total_input_tokens": total_input_tokens,
                    "total_output_tokens": total_output_tokens,
                    "total_input_cost": total_input_cost,
                    "total_output_cost": total_output_cost,
                    "total_cost": total_cost,
                    "workflow_metadata": log.get("workflow_metadata", {}),
                }

            except KeyError as e:
                print(
                    f"KeyError: {e} - This log file may not have the expected structure."
                )

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Results saved to {OUTPUT_FILE}")
