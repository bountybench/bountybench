import argparse
import logging
from pathlib import Path

from agents.dataclasses.agent_spec import AgentConfig
from agents.executor_agent.executor_agent import ExecutorAgent
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.task_server_resource import TaskServerResource
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

    return parser.parse_args()

def check_response_answer(response: AnswerResponseInterface, answer: str) -> str:
    """
    Check the response answer and return the appropriate message
    """
    if response.answer == answer:
        return "You've successfully retrieved the flag!"
    else:
        return f"The flag you get is: {response.answer}. The correct flag is: {answer}"


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
    repo_metadata = read_repo_metadata(str(task_repo_dir))

    bounty_metadata = read_bounty_metadata(str(task_repo_dir), bounty_number)

    files_dir, tmp_dir = "original_files", "tmp"
    InitFilesResource(task_repo_dir, files_dir, tmp_dir)
    TaskServerResource(task_repo_dir,  files_dir,
                       repo_metadata["target_host"])
    KaliEnvResource("KaliEnv", task_repo_dir=task_repo_dir, volumes={task_repo_dir / tmp_dir: {"bind": "/app", "mode": "rw"}})

    agent_config: AgentConfig = AgentConfig(
        model='openai/gpt-4o-2024-05-13',
        max_output_tokens=2000,
        max_input_tokens=6000,
        max_iterations=15,
        max_response_len=3,
        use_helm=True
    )

    agent = ExecutorAgent(agent_config, task_description=bounty_metadata["detect_prompt_less_info"], answer_format=bounty_metadata["answer_format"], target_host=repo_metadata["target_host"])

    response = agent.run([])

    for _ in range(agent_config.max_iterations):
        response = agent.run([response])
        if issubclass(response.__class__, AnswerResponseInterface):
            logger.info(check_response_answer(response, answer=bounty_metadata["answer"]))
            break


if __name__ == "__main__":
    main()
