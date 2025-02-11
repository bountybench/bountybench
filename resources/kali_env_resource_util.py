import atexit
import os
import sys
import time
import select
from typing import Dict, Optional, Tuple
import time
import re
from typing import Callable, Optional, Any, Type


import docker
from docker.models.containers import Container

from resources.utils import get_stdout_text
import os

TIMEOUT_PER_COMMAND = 120
MAX_RETRIES = 3
RETRY_DELAY = 5

class KaliEnvResourceUtil:
    @staticmethod
    def wait_for_container(container, timeout=10,initial_delay=0.1):
        """Waits for the container to enter 'running' state."""
        start_time = time.time()
        delay = initial_delay

        while time.time() - start_time < timeout:
            container.reload()  # Refresh container status
            if container.status == "running":
                return True
            #exponential backoff
            delay = min(delay * 2, 1.0)
            time.sleep(delay)
        return False
    
    @staticmethod
    def handle_container_start_failure(container: Container, logger=None):
        logs = container.logs().decode("utf-8")
        logger.error(f"Container failed to start. Logs:\n{logs}")
        raise RuntimeError("Container failed to reach running state.")  
    
    @staticmethod 
    def handle_start_error(error: Exception, attempt: int,logger=None):
        if isinstance(error, docker.errors.APIError):
            error_type = "Docker API error"
        else:
            error_type = "Unexpected error"

        logger.error(f"{error_type} while starting container: {error}")
    
        if attempt < MAX_RETRIES - 1:
            logger.info(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
        else:
            logger.critical("Failed to start Docker container after maximum retries.")
            raise DockerContainerStartError(f"{error_type}: {str(error)}") from error

    @staticmethod
    def verify_container_removal(client, name: str, logger=None):
        delay=0.1
        for _ in range(5):
            try:
                client.containers.get(name)
                # Exponential backoff with a cap for more efficiency 
                delay = min(delay * 2, 1.0)
                time.sleep(delay)
            except docker.errors.NotFound:
                logger.debug(f"Confirmed container '{name}' is removed.")
                break
        else:
            logger.warning(f"Container '{name}' still exists post-removal.")

    @staticmethod
    def parse_target_host(target_host: str, logger=None) -> Tuple[str, int]:
        """
        Parse the target host string into hostname and port.

        Args:
            target_host (str): The target host in the format hostname:port.

        Returns:
            Tuple[str, int]: A tuple containing the hostname and port as an integer.
        """
        try:
            hostname, port = target_host.split(":")
            return hostname, int(port)
        except ValueError:
            logger.error(
                f"Invalid target_host format: {target_host}. Expected format: hostname:port")
            sys.exit(1)

    @staticmethod
    def print_docker_log(container: Container, timeout=120) -> None:
        print("Monitoring container startup...")
        start_time = time.time()

        for log in container.logs(stream=True, follow=True):
            print(log.decode('utf-8').strip())

            container.reload()
            if container.status == "running":
                break
        
            if time.time() - start_time > timeout:
                print("Timeout reached while monitoring container startup")
                break

    @staticmethod
    def safe_execute(func, operation_name,logger=None):
        """Safely execute a function and log any errors."""
        try:
            func()
        except Exception as e:
            logger.error(f"Error during {operation_name}: {e}")

    @staticmethod
    def count_trailing_new_lines(input_str: str) -> int:
        input_str = input_str.rstrip(' ')
        return len(input_str) - len(input_str.rstrip('\n'))
    
    def process_tty_output(self, output: bytes, command: str) -> str:
        if not output:
            return f"No output received for {30} seconds."
        stdout_text = get_stdout_text(output)
        return self.clean_command_output(stdout_text, command)
    
    def clean_command_output(self, raw_output: str, command_str: str) -> str:
        """
        Cleans the raw bash output to remove initialization strings and the echoed command.
        Also removes echoed multiline outputs for commands like `cat << EOF`.
        """
        import re

        # Use a regex to remove ANSI escape sequences
        cleaned_output = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', raw_output)
        # Remove patterns like \r followed by digits, a comma, and more digits
        cleaned_output = re.sub(r'\r\d+,\s*\d*', '', cleaned_output)
        # Remove sequences like \r8, \r08, etc.
        cleaned_output = re.sub(r'\r\d*', '', cleaned_output)
        # Replace standalone carriage returns (\r) with nothing
        cleaned_output = cleaned_output.replace('\r', '')
        cleaned_output = cleaned_output.replace('\n\n$', '\n$')

        if self.is_single_control_character(command_str):
            command_str = self.control_char_to_text(command_str)

        # Escape command_str for regex safety
        command_pattern = re.escape(command_str.strip())

        # Use regex to find the command and split the output after the match
        match = re.search(f"^{command_pattern}.*$", cleaned_output, re.MULTILINE)
        if not match:
            return cleaned_output.strip()  # If no match, return the original stripped output

        # Get everything after the command match
        start_index = match.end()
        cleaned_output = cleaned_output[start_index:].strip()

        return cleaned_output

    def is_single_control_character(self,s):
        s = s.strip()
        s = s.encode('utf-8').decode('unicode_escape')
        if len(s) != 1:
            return False
        return ord(s) < 32 or ord(s) == 127

    def control_char_to_text(self,char: str) -> str:
        if ord(char) == 127:  # Special case for DEL
            return '^?'
        return f"^{chr(ord(char) + 64)}"

class DockerContainerStartError(Exception):
    """Custom exception for Docker container start failures."""
    pass