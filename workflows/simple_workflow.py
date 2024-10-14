import argparse
import logging
from pathlib import Path

from resources.utils import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the task")
    parser.add_argument(
        "--task_repo_dir", type=str, help="The directory of the task repo"
    )
    parser.add_argument(
        "--bounty_number",
        type=str,
        help="The bounty for the given task; not used in detect_all",
    )
    parser.add_argument(
        "--task_mode",
        type=str,
        help="The mode to use for the agent",
        choices=["patch", "exploit", "detect_less_info",
                 "detect_some_info", "detect_all"],
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Create a Path object for the task repository directory
    task_repo_dir = Path(args.task_repo_dir).resolve()
    bounty_number = str(args.bounty_number)

    network_name = "shared_net"

    # Check if the network exists
    if not docker_network_exists(network_name):
        logger.info(f"Creating Docker network: {network_name}")
        run_command(["docker", "network", "create", network_name])

    # Read metadata
    repo_metadata = read_repo_metadata(task_repo_dir)

    bounty_metadata = read_bounty_metadata(
        task_repo_dir, bounty_number)

   # TODO: Implement the function to actually run the workflow


if __name__ == "__main__":
    main()
