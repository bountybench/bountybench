import logging
import subprocess
import sys
from typing import Dict, Optional
from agents.docker_helper.docker_helper import DockerHelper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TMP_DIR = "tmp"


def setup_agent_container(repo_dir: str, name: str, volumes: Optional[Dict[str, Dict[str, str]]] = None) -> DockerHelper:
    # TODO: How to handle the requirements.sh case?
    docker_helper = DockerHelper(name=name, volumes=volumes)
    return docker_helper


def run_init_script(repo_dir: str):
    try:
        init_result = subprocess.run(
            ["./init_script.sh", TMP_DIR],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        logger.info(f"Init script stdout: {init_result.stdout}")
        logger.info(f"Init script stderr: {init_result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Init script stdout: {e.stdout}")
        logger.error(f"Init script stderr: {e.stderr}")
        sys.exit(1)


def health_check(agent_container: DockerHelper, target_hosts: str) -> None:
    hosts = target_hosts.split()
    failed_hosts = []

    for target_host in hosts:
        try:
            hostname, port = target_host.split(":")
            port = int(port)
        except ValueError:
            logger.error(
                f"Invalid target_host format: {target_host}. Expected format: hostname:port"
            )
            sys.exit(1)

        def nc_check():
            stdout, stderr = agent_container.run_command(command=f"nc -zv -w 5 {hostname} {port}", timeout=10)
            logger.info(
                f"Netcat check output: {stdout}\n {stderr}")
            if "open" in stdout:
                return True
            else:
                logger.error(f"Netcat check failed for {hostname}:{port}")
                return False

        def http_check():
            stdout, stderr = agent_container.run_command(command=f"curl -sS -o /dev/null -w \"%{{http_code}}\" {hostname}:{port}", timeout=10)
            status_code = int(stdout)
            logger.info(
                f"HTTP check output: {stdout}\n {stderr}")
            if status_code == 200:
                return True
            else:
                logger.error(f"HTTP check failed for {hostname}:{port}")
                return False

        # Perform health checks
        if not http_check() and not nc_check():
            logger.error(f"Health check failed for {hostname}:{port}")
            failed_hosts.append(target_host)

    if failed_hosts:
        logger.error(
            f"Health checks failed for the following hosts: {', '.join(failed_hosts)}"
        )
        sys.exit(1)
    else:
        logger.info("All target hosts passed the health check")
