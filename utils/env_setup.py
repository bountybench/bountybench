import logging
from pathlib import Path
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_command(command, work_dir=None):
    """
    Runs a shell command.

    :param command: List of command arguments.
    :param work_dir: Working directory to execute the command in.
    :return: subprocess.CompletedProcess instance
    """
    try:
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
        if result.stdout:
            logger.info(result.stdout.strip())
        if result.stderr:
            logger.warning(result.stderr.strip())
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command '{' '.join(command)}' failed with exit code {e.returncode}")
        if e.stdout:
            logger.error(f"Standard Output:\n{e.stdout}")
        if e.stderr:
            logger.error(f"Standard Error:\n{e.stderr}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        logger.error(f"Command not found: {command[0]}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred while running command '{' '.join(command)}': {e}")
        sys.exit(1)

def docker_network_exists(network_name):
    """
    Checks if a Docker network exists.
    """
    logger.info(f"Checking if Docker network '{network_name}' exists.")
    result = subprocess.run(
        ["docker", "network", "ls", "--filter", f"name=^{network_name}$", "--format", "{{.Name}}"],
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