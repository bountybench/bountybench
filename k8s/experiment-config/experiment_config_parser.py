import argparse
import json
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate runner.py commands from config JSON"
    )
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        with open(args.config, "r") as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)

    required = [
        "workflow_type",
        "phase_iterations",
        "use_helm",
        "model",
        "max_input_tokens",
        "max_output_tokens",
        "tasks",
    ]
    for k in required:
        if k not in cfg:
            print(f"Missing key '{k}' in config", file=sys.stderr)
            sys.exit(1)

    workflow = cfg["workflow_type"]
    phase_iter = cfg["phase_iterations"]
    use_helm = cfg["use_helm"]
    model = cfg["model"]
    max_in = cfg["max_input_tokens"]
    max_out = cfg["max_output_tokens"]
    tasks = cfg["tasks"]

    commands = []
    for entry in tasks:
        if "/" in entry:
            task_dir, bounty = entry.split("/", 1)
            # prefix with bountybench
            task_dir = f"bountybench/{task_dir}"
        else:
            print(
                f"Invalid task entry '{entry}', expected 'task_dir/bounty_number'",
                file=sys.stderr,
            )
            sys.exit(1)
        parts = [
            "python",
            "-m",
            "workflows.runner",
            "--workflow-type",
            workflow,
            "--phase_iterations",
            str(phase_iter),
        ]
        if use_helm:
            parts.append("--use_helm")
        parts.extend(
            [
                "--model",
                model,
                "--max_input_tokens",
                str(max_in),
                "--max_output_tokens",
                str(max_out),
                "--task_dir",
                task_dir,
                "--bounty_number",
                bounty,
            ]
        )
        commands.append(" ".join(parts))

    for cmd in commands:
        print(cmd)


if __name__ == "__main__":  # noqa: C901
    main()
