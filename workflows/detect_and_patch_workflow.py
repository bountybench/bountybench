import argparse
import json
import os
from pathlib import Path
import shutil
import uuid

from agents.dataclasses.agent_spec import AgentConfig
from agents.patch_agent.patch_agent import PatchAgent
from agents.executor_agent.prompt import DETECT_AND_PATCH_PROMPT, STOP_TOKEN
from agents.executor_agent.executor_agent import ExecutorAgent
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.setup_resource import SetupResource
from resources.utils import *
from responses.answer_response_interface import AnswerResponseInterface
from utils.logger import get_main_logger
from resources.resource_dict import resource_dict

logger = get_main_logger(__name__)

# Function to save JSON log
def save_run_log(run_data, filename):
    with open(filename, 'w') as f:
        json.dump(run_data, f, indent=4)

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
        "--vuln_info",
        action="store_true",
        help="Share the CWE of the vulnerability in the prompt",
        default=False,
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()

    # Create a Path object for the task repository directory
    task_repo_dir = Path(args.task_repo_dir).resolve()
    task_repo_dir_str = str(task_repo_dir.name)  # Use only the directory name
    bounty_number = str(args.bounty_number)

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    executor_agent_config: AgentConfig = AgentConfig(
        model='openai/gpt-4o-2024-05-13',
        max_output_tokens=2000,
        max_input_tokens=6000,
        max_iterations=7,
        max_response_len=3,
        use_helm=True
    )
    
    # Replace slashes with underscores in the model name
    model_name_safe = executor_agent_config.model.replace("/", "_")
    file_id = uuid.uuid4()
    log_filename = logs_dir / f"patch_{task_repo_dir_str}_{bounty_number}_{model_name_safe}_{file_id}.json"

    network_name = "shared_net"

    # Check if the network exists
    if not docker_network_exists(network_name):
        logger.info(f"Creating Docker network: {network_name}")
        run_command(["docker", "network", "create", network_name])

    # Read metadata
    repo_metadata = read_repo_metadata(str(task_repo_dir))
    bounty_metadata = read_bounty_metadata(str(task_repo_dir), bounty_number)

    vuln_information=bounty_metadata["exploit_prompt"]
    detect_prompt = DETECT_AND_PATCH_PROMPT.format(
            additional_information=vuln_information,
            stop_token=STOP_TOKEN,
            target_host=repo_metadata["target_host"],
        )
    
    print(detect_prompt)
    print("==========================")

    files_dir, tmp_dir = "codebase", "tmp"

    # Relative to task_repo_dir

    InitFilesResource(task_repo_dir=task_repo_dir, files_dir_name=files_dir, tmp_dir_name=tmp_dir, exploit_files_dir_name=None, vulnerable_commit=bounty_metadata['vulnerable_commit'])
    if os.path.exists(str(task_repo_dir) + "/setup_repo_env.sh"): 
        SetupResource(task_level_setup=False, task_repo_dir=task_repo_dir, files_dir=files_dir)
    if repo_metadata["target_host"]: 
        SetupResource(task_level_setup=True, task_repo_dir=task_repo_dir, files_dir=files_dir, bounty_number=bounty_number, server_address=repo_metadata["target_host"])

    KaliEnvResource("KaliEnv", task_repo_dir=task_repo_dir, bounty_number=bounty_number, volumes={
                    os.path.join(task_repo_dir, tmp_dir): {"bind": "/app", "mode": "rw"}})
    DockerResource("DockerHelper")



    executor_agent_config: AgentConfig = AgentConfig(
        model='openai/gpt-4o-2024-05-13',
        max_output_tokens=2000,
        max_input_tokens=6000,
        max_iterations=15,
        max_response_len=3,
        use_helm=True
    )

    executor_agent = ExecutorAgent(
        executor_agent_config, initial_prompt=detect_prompt)

    bounty_dir=os.path.join("bounties", f"bounty_{bounty_number}")
    exploit_files_dir = os.path.join(bounty_dir, "exploit_files")
    patch_agent = PatchAgent(bounty_dir=bounty_dir, exploit_files_dir)

    # Initialize the log for all iterations
    run_log = {
        "iterations": []
    }

    simple_response = executor_agent.run([])

    

    for iteration in range(executor_agent_config.max_iterations):
        run_data = {}
        run_data["iteration"] = iteration + 1
        if run_data["iteration"] == 1: 
            run_data["executor_agent_input"] = executor_agent.prompt 
        else: 
            run_data["executor_agent_input"] = simple_response.response

        patch_response = patch_agent.run([simple_response])

        run_data["patch_agent_output"] = patch_response.response
        run_log["iterations"].append(run_data)

        if issubclass(patch_response.__class__, AnswerResponseInterface):
            logger.info("Patch Success!")
            break

        simple_response = executor_agent.run([simple_response])

        # If simple agent hallucinates, log and stop
        if issubclass(simple_response.__class__, AnswerResponseInterface):
            logger.info("Simple agent hallucinated an answer!")
            break

    save_run_log(run_log, log_filename)

    


if __name__ == "__main__":
    main()