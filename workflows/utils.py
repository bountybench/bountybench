import logging
from resources.utils import docker_network_exists, run_command

from utils.logger import logger

def setup_shared_network() -> None:
    """Setup Docker network if it does not exist."""
    network_name = "shared_net"
    if not docker_network_exists(network_name):
        logger.info(f"Creating Docker network: {network_name}")
        run_command(["docker", "network", "create", network_name])
    else:
        logger.debug(f"Docker network '{network_name}' already exists.")
