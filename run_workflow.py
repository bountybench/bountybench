import argparse
from pathlib import Path
from agents.docker_helper.agent_setup import *
from utils.env_setup import docker_network_exists, run_command
from utils.read_metadata import *

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
    # Should we handle task_mode here or should we handle it in the workflow?
    parser.add_argument(
        "--task_mode",
        type=str,
        help="The mode to use for the agent",
        choices=["patch", "exploit", "detect_less_info", "detect_some_info", "detect_all"],
    )

    return parser.parse_args()

def main() -> None:
    args = parse_args()

    # Create a Path object for the task repository directory
    task_repo_dir = Path(args.task_repo_dir).resolve()
    print(task_repo_dir)
    

    image_name = "cybench/cybounty:latest"
    network_name = "shared_net"

    # Pull the Docker image
    logger.info(f"Pulling Docker image: {image_name}")
    run_command(["docker", "pull", image_name])

    # Check if the network exists
    if not docker_network_exists(network_name):
        logger.info(f"Creating Docker network: {network_name}")
        run_command(["docker", "network", "create", network_name])
    
    start_docker_script = task_repo_dir / "start_docker.sh"
    if start_docker_script.is_file():
        run_command(
            command=["./start_docker.sh"],
            work_dir=str(task_repo_dir),
        )
    else:
        logger.info("No start_docker.sh script found in the task repo.")
    

    # Read metadata
    repo_metadata = read_repo_metadata(args.task_repo_dir)

    bounty_metadata = read_bounty_metadata(
        args.task_repo_dir, args.bounty_number)

   # TODO: Implement the function to actually run the workflow

    stop_docker_script = task_repo_dir / "stop_docker.sh"
    if stop_docker_script.is_file():
        run_command(
            command=["./stop_docker.sh"],
            work_dir=str(task_repo_dir)
        )
    else:
        logger.info("No stop_docker.sh script found in the task repo.")

if __name__ == "__main__":
    main()