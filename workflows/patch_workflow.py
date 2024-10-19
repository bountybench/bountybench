import argparse
from pathlib import Path

from agents.dataclasses.agent_spec import AgentConfig
from agents.patch_agent.patch_agent import PatchAgent
from agents.simple_agent.simple_agent import SimpleExecutorAgent
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.task_server_resource import TaskServerResource
from resources.utils import *
from responses.answer_response_interface import AnswerResponseInterface
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


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


def main() -> None:
    args = parse_args()

    # Create a Path object for the task repository directory
    task_repo_dir = Path(args.task_repo_dir).resolve()
    task_repo_dir = str(task_repo_dir)
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
    TaskServerResource(task_repo_dir, files_dir,
                       repo_metadata["target_host"], True)
    KaliEnvResource("KaliEnv", task_repo_dir=task_repo_dir, volumes={
                    task_repo_dir / tmp_dir: {"bind": "/app", "mode": "rw"}})
    DockerResource("DockerHelper")

    simple_agent_config: AgentConfig = AgentConfig(
        model='openai/gpt-4o-2024-05-13',
        max_output_tokens=2000,
        max_input_tokens=6000,
        max_iterations=15,
        max_response_len=3,
        use_helm=True
    )

    # TODO: copy over exploit scripts to the agent env

    simple_agent = SimpleExecutorAgent(
        simple_agent_config, task_description=bounty_metadata["patch_prompt"], answer_format=bounty_metadata["answer_format"], target_host=repo_metadata["target_host"])

    patch_agent = PatchAgent(bounty_dir=task_repo_dir + "/metadata/bounty_" + bounty_number + "bounty_metadata.json")

    simple_response = simple_agent.run([])

    for _ in range(simple_agent_config.max_iterations):
        patch_response = patch_agent.run([simple_response])
        if issubclass(patch_response.__class__, AnswerResponseInterface):
            logger.info("Patch Success!")
            break
        simple_response = simple_agent.run([patch_response])
        if issubclass(simple_response.__class__, AnswerResponseInterface):
            logger.info("Simple agent hallucinated an answer!")
            break


if __name__ == "__main__":
    main()
