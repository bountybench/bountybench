import argparse
import logging
from pathlib import Path

from agents.dataclasses.agent_spec import AgentConfig
from agents.simple_agent.simple_agent import SimpleExecutorAgent
from resources.init_files_resource import InitFilesResource
from resources.utils import *
from responses.answer_response_interface import AnswerResponseInterface

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

def check_response_answer(response: AnswerResponseInterface, answer: str) -> str:
    """
    Check the response answer and return the appropriate message
    """
    if response.answer == answer:
        return "The answer is yes"
    else:
        return "The answer is no"


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

    bounty_metadata = read_bounty_metadata(task_repo_dir, bounty_number)

    InitFilesResource(task_repo_dir, bounty_metadata.tmp_dir)

   # TODO: Implement the function to actually run the workflow

    agent_config: AgentConfig = AgentConfig(
        model='openai/gpt-4o-2024-05-13',
        max_output_tokens=2000,
        max_input_tokens=6000,
        max_iterations=15,
        max_response_len=3,
        helm=True
    )

    agent = SimpleExecutorAgent(agent_config)

    response = agent.run()

    for _ in range(agent_config.max_iterations):
        response = agent.run(response)
        if issubclass(response.__class__, AnswerResponseInterface):
            logger.info(check_response_answer(response))
            break


if __name__ == "__main__":
    main()
