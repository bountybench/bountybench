import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_command(command, work_dir=None):
    """
    Runs a shell command.
    :param command: List of command arguments.
    :param work_dir: Working directory to execute the command in.
    :return: subprocess.CompletedProcess instance
    """
    cwd_display = work_dir if work_dir else Path.cwd()
    logger.info(f"Executing command: {' '.join(command)} in {cwd_display}")
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
