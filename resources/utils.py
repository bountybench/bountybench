import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Union

from utils.logger import get_main_logger

logger = get_main_logger(__name__)


def run_command(command, work_dir=None):
    """
    Runs a shell command.
    :param command: List of command arguments.
    :param work_dir: Working directory to execute the command in.
    :return: subprocess.CompletedProcess instance
    """
    result = subprocess.run(
        command,
        cwd=work_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return result


def docker_network_exists(network_name):
    """
    Checks if a Docker network exists.
    """
    logger.info(f"Checking if Docker network '{network_name}' exists.")
    result = subprocess.run(
        ["docker", "network", "ls", "--filter",
            f"name=^{network_name}$", "--format", "{{.Name}}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    exists = network_name in result.stdout.splitlines()
    if exists:
        logger.info(f"Docker network '{network_name}' already exists.")
    else:
        logger.info(f"Docker network '{network_name}' does not exist.")
    return exists


def read_repo_metadata(task_repo_dir: str) -> dict[str, Union[str, dict]]:
    repo_metadata_file_path = os.path.join(
        task_repo_dir, "metadata/metadata.json")
    if not os.path.exists(repo_metadata_file_path):
        logger.error("Repository metadata file not found")
        sys.exit(1)

    with open(repo_metadata_file_path, "r") as metadata_file:
        repo_metadata = json.load(metadata_file)

    return repo_metadata


def read_bounty_metadata(
    task_repo_dir: str, bounty_number: str
) -> dict[str, Union[str, dict]]:
    bounty_metadata_file_path = os.path.join(
        task_repo_dir + "/metadata/bounty_" + bounty_number, "bounty_metadata.json"
    )
    if not os.path.exists(bounty_metadata_file_path):
        logger.error("Bounty metadata file not found")
        sys.exit(1)

    with open(bounty_metadata_file_path, "r") as metadata_file:
        bounty_metadata = json.load(metadata_file)

    return bounty_metadata

def get_stdout_text(process_output: bytes) -> str:
    """
    Decode the process output from bytes to a UTF-8 string.

    Args:
        process_output (bytes): The output to decode.

    Returns:
        str: The decoded string or an error message if decoding fails.
    """
    stdout: str = ""
    if process_output is None:
        return stdout
    try:
        stdout = process_output.decode("utf-8")
        return stdout
    except UnicodeDecodeError as e:
        stdout = (
            "This failed to decode. Remember: the problem is fully solvable using UTF-8 encoding. "
            "Ignore any images (jpeg, png, etc.), videos (mp4, mpeg) etc. "
            f"Error: {str(e)}"
        )


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

