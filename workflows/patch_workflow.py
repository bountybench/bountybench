import argparse
import json
import os
import sys
import sys
from pathlib import Path

from agents.dataclasses.agent_spec import AgentConfig
from agents.patch_agent.patch_agent import PatchAgent
from agents.executor_agent.prompt import PATCH_PROMPT, STOP_TOKEN
from agents.executor_agent.executor_agent import ExecutorAgent
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.setup_resource import SetupResource
from resources.utils import *
from responses.answer_response_interface import AnswerResponseInterface
from utils.logger import get_main_logger
from utils.workflow_logger import WorkflowLogger, workflow_logger

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
    task_repo_dir_str = str(task_repo_dir.name)  # Use only the directory name
    bounty_number = str(args.bounty_number)

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    executor_agent_config: AgentConfig = AgentConfig(
        model='openai/gpt-4o-2024-05-13',
        max_output_tokens=2000,
        max_input_tokens=6000,
        max_iterations=15,
        max_response_len=3,
        use_helm=True
    )

    # Initialize workflow logger
    workflow_logger.initialize(
        workflow_name="patch",
        logs_dir=str(logs_dir),
        task_repo_dir=str(args.task_repo_dir),
        bounty_number=bounty_number,
        model_config=executor_agent_config.__dict__
    )
    # Initialize our new workflow logger
    workflow_logger = WorkflowLogger(
        workflow_name="patch",
        logs_dir=str(logs_dir),
        task_repo_dir=str(args.task_repo_dir),
        bounty_number=bounty_number,
        model_config=executor_agent_config.__dict__
    )

    network_name = "shared_net"

    # Check if the network exists
    if not docker_network_exists(network_name):
        logger.info(f"Creating Docker network: {network_name}")
        run_command(["docker", "network", "create", network_name])

    # Read metadata
    repo_metadata = read_repo_metadata(str(task_repo_dir))
    bounty_metadata = read_bounty_metadata(str(task_repo_dir), bounty_number)

    if not bounty_metadata['patch']:
        print(f"Patching not available for {task_repo_dir_str}.")
        sys.exit()  # Exit the script


    vulnerable_commit=bounty_metadata['vulnerable_commit']
    
    
    run_command(["git", "checkout", vulnerable_commit], str(task_repo_dir) + "/codebase")

    vulnerable_files = []
    for _, value in bounty_metadata['patch'].items(): 
        relative_path = os.path.relpath(value, start="codebase")

        full_path = os.path.join(str(task_repo_dir), value)
        if os.path.exists(full_path):
            vulnerable_files.append(relative_path)
    
    run_command(["git", "checkout", "main"], str(task_repo_dir) + "/codebase")


    vulnerable_files_formatted = ", ".join(f"`{file}`" for file in vulnerable_files)


    exploit_description = f"""
    {bounty_metadata["exploit_prompt"]} 
    The path to the vulnerable file(s) is {vulnerable_files_formatted}. 
    """


    patch_prompt = PATCH_PROMPT.format(
        task_description=exploit_description,
        stop_token=STOP_TOKEN,
        target_host=repo_metadata["target_host"],
    )


    files_dir, tmp_dir = "codebase", "tmp"

    # Relative to task_repo_dir
    exploit_files_dir = os.path.join("bounties", f"bounty_{bounty_number}", "exploit_files")



    workflow_logger.add_resource("InitFilesResource")
    InitFilesResource(task_repo_dir=task_repo_dir, files_dir_name=files_dir, tmp_dir_name=tmp_dir, exploit_files_dir_name=exploit_files_dir, vulnerable_commit=vulnerable_commit)
    if os.path.exists(str(task_repo_dir) + "/setup_repo_env.sh"): 
        SetupResource(task_level_setup=False, task_repo_dir=task_repo_dir, files_dir=files_dir)
    if repo_metadata["target_host"]: 
        SetupResource(task_level_setup=True, task_repo_dir=task_repo_dir, files_dir=files_dir, bounty_number=bounty_number, server_address=repo_metadata["target_host"])

    KaliEnvResource("KaliEnv", task_repo_dir=task_repo_dir, bounty_number=bounty_number, volumes={
                    os.path.join(task_repo_dir, tmp_dir): {"bind": "/app", "mode": "rw"}})
    DockerResource("DockerHelper")
    
    # Add workflow metadata
    workflow_logger.add_metadata("vulnerable_files", vulnerable_files)
    workflow_logger.add_metadata("exploit_description", exploit_description)
    workflow_logger.add_metadata("repo_metadata", repo_metadata)
    workflow_logger.add_metadata("bounty_metadata", bounty_metadata)

    executor_agent = ExecutorAgent(
        config=executor_agent_config, initial_prompt=patch_prompt, logger=workflow_logger, target_host=repo_metadata["target_host"])

    patch_agent = PatchAgent(bounty_dir=os.path.join("bounties", f"bounty_{bounty_number}"))

    prev_response = None

    for iteration in range(executor_agent_config.max_iterations):
        with workflow_logger.iteration(iteration + 1) as iteration_ctx:
            # Execute the executor agent
            with iteration_ctx.interaction("executor_agent", prev_response if iteration > 0 else None) as interaction:
                simple_response = executor_agent.run([] if iteration == 0 else [prev_response])
                interaction.set_output(simple_response)

            # If simple agent hallucinates, stop
            if issubclass(simple_response.__class__, AnswerResponseInterface):
                workflow_logger.finalize("completed_with_hallucination")
                logger.info("Simple agent hallucinated an answer!")
                break

            # Execute the patch agent
            with iteration_ctx.interaction("patch_agent", simple_response) as interaction:
                patch_response = patch_agent.run([simple_response])
                interaction.set_output(patch_response)

            # If patch is successful, stop
            if issubclass(patch_response.__class__, AnswerResponseInterface):
                workflow_logger.finalize("completed_success")
                logger.info("Patch Success!")
                break

            prev_response = simple_response

    # If we reached max iterations without success
    if iteration == executor_agent_config.max_iterations - 1:
        workflow_logger.finalize("completed_max_iterations")

if __name__ == "__main__":
    main()