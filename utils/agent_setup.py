import logging
import os
import subprocess
import sys
from typing import Dict, List, Optional

from agents.docker_helper.docker_helper import DockerHelper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TMP_DIR = "tmp"


def parse_shell_script(script_path: str) -> List[str]:
    """
    Parse a shell script into individual commands.

    Args:
        script_path (str): Path to the shell script.

    Returns:
        List[str]: A list of commands to execute.
    """
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Shell script not found at {script_path}")

    commands = []
    with open(script_path, 'r') as script_file:
        for idx, line in enumerate(script_file, start=1):
            # Remove leading/trailing whitespace
            stripped_line = line.strip()

            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith("#"):
                continue

            # Add command to the list (assuming one command per line)
            commands.append(stripped_line)

    return commands


def setup_agent_container(task_repo_dir: str, name: str, volumes: Optional[Dict[str, Dict[str, str]]] = None) -> DockerHelper:
    """
    Set up a Docker container for the agent, including executing any required setup scripts.

    Args:
        task_repo_dir (str): Path to the repository directory for the task.
        name (str): Name of the Docker container.
        volumes (Optional[Dict[str, Dict[str, str]]]): Optional volume mappings for the Docker container.

    Returns:
        DockerHelper: A configured DockerHelper object for managing the container.
    """
    docker_helper = DockerHelper(name=name, volumes=volumes)
    requirements_path = f"{task_repo_dir}/metadata/requirements.sh"
    if not os.path.isfile(requirements_path):
        logger.error(f"Requirements file not found at {requirements_path}")
        sys.exit(1)

    # Parse and execute the requirements script commands
    requirement_commands = parse_shell_script(requirements_path)
    for command in requirement_commands:
        stdout, stderr = docker_helper.run_command(command)

        # Log output and error for each command
        if stdout:
            logger.info(f"Requirements.sh Output:\n{stdout}")
        if stderr:
            logger.error(f"Requirements.sh Error:\n{stderr}")
            sys.exit(1)

    return docker_helper


def run_init_script(task_repo_dir: str) -> None:
    """
    Run the initialization script for the task.

    Args:
        task_repo_dir (str): Path to the repository directory for the task.
    """
    try:
        # Execute the init_script.sh script located in the task repo directory
        init_result = subprocess.run(
            ["./init_script.sh", TMP_DIR],
            cwd=task_repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        # Log stdout and stderr output from the script
        logger.info(f"Init script stdout: {init_result.stdout}")
        logger.info(f"Init script stderr: {init_result.stderr}")
    except subprocess.CalledProcessError as e:
        # Log error details if the script execution fails
        logger.error(f"Init script stdout: {e.stdout}")
        logger.error(f"Init script stderr: {e.stderr}")
        sys.exit(1)


def health_check(agent_container: DockerHelper, target_hosts: str) -> None:
    """
    Perform health checks on the specified target hosts.

    Args:
        agent_container (DockerHelper): DockerHelper object managing the container.
        target_hosts (str): A string containing space-separated target hosts in the format hostname:port.
    """
    hosts = target_hosts.split()
    failed_hosts = []

    for target_host in hosts:
        try:
            # Split the target_host into hostname and port
            hostname, port = target_host.split(":")
            port = int(port)
        except ValueError:
            # Log error if the target_host format is invalid
            logger.error(
                f"Invalid target_host format: {target_host}. Expected format: hostname:port"
            )
            sys.exit(1)

        def nc_check():
            # Run netcat to check if the specified port is open
            stdout, stderr = agent_container.run_command(
                command=f"nc -zv -w 5 {hostname} {port}", timeout=10)
            # Log the netcat command output
            logger.info(
                f"Netcat check output: {stdout}\n {stderr}")
            if "open" in stdout:
                return True
            else:
                logger.error(f"Netcat check failed for {hostname}:{port}")
                return False

        def http_check():
            # Run curl to check if the HTTP service is responding with status code 200
            stdout, stderr = agent_container.run_command(
                command=f"curl -sS -o /dev/null -w \"%{{http_code}}\" {hostname}:{port}", timeout=10)
            status_code = int(stdout)
            # Log the HTTP check command output
            logger.info(
                f"HTTP check output: {stdout}\n {stderr}")
            if status_code == 200:
                return True
            else:
                logger.error(f"HTTP check failed for {hostname}:{port}")
                return False

        # Perform health checks: first using HTTP check, then netcat check if necessary
        if not http_check() and not nc_check():
            logger.error(f"Health check failed for {hostname}:{port}")
            failed_hosts.append(target_host)

    # Log results of health checks
    if failed_hosts:
        logger.error(
            f"Health checks failed for the following hosts: {', '.join(failed_hosts)}"
        )
        sys.exit(1)
    else:
        logger.info("All target hosts passed the health check")
