import atexit
import logging
from resources.resource_dict import resource_dict
from resources.base_resource import BaseResource
import subprocess
import os


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

        start_docker_path = os.path.join(self.task_repo_dir, 'start_docker.sh')

        try:
            result = subprocess.run([start_docker_path], check=True, capture_output=True, text=True)
            
            # Print the output
            logger.info("Spun up task server at {self.resource_id}. Here is output:", result.stdout)
        except subprocess.CalledProcessError as e:
            # Handle errors
            logger.info("Unable to spin up task server at {self.resource_id}. Here is error:", e.stderr)

    def stop(self) -> None:
        stop_docker_path = os.path.join(self.task_repo_dir, 'stop_docker.sh')
        try:
            result = subprocess.run([stop_docker_path], check=True, capture_output=True, text=True)
            
            logger.info("Stopping task server at {self.resource_id}. Here is output:", result.stdout)
        except subprocess.CalledProcessError as e:
            # Handle errors
            logger.info("Unable to stop task server at {self.resource_id}. Here is error:", e.stderr)

