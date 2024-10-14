import atexit
import logging
from resources.resource_dict import resource_dict
from resources.base_resource import BaseResource
import subprocess
import os

from resources.utils import run_command


# Configure logging
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)



class TaskServerResource(BaseResource):
    """Task Server Resource"""

    def __init__(self, task_repo_dir: str, server_address: str) -> None:
        self.resource_id = server_address 
        self.task_repo_dir = task_repo_dir
        self.start()

        resource_dict[self.resource_id] = self
        atexit.register(self.stop)
    
    def start(self) -> None:
        try:
            result = run_command(
                command=["./start_docker.sh"],
                work_dir=str(self.task_repo_dir),
            )
            
            # Print the output
            # logger.info(f"Spun up task server at {self.resource_id}. Here is output:", result.stdout)
        except Exception as e:
            # Handle errors
            logger.info(f"Unable to spin up task server at {self.resource_id}.")

    def stop(self) -> None:
        try:
            result = run_command(
                command=["./stop_docker.sh"],
                work_dir=str(self.task_repo_dir),
            )
            # Print the output
            logger.info(f"Stop task server at {self.resource_id}.")
        except Exception as e:
            # Handle errors
            logger.info(f"Unable to stop task server at {self.resource_id}. Here is error:", e.stderr)

