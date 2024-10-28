from typing import List

from agents.base_agent import BaseAgent
from resources.env_setup_resource import EnvSetupResource
from responses.base_response import BaseResponse
from responses.response import Response
from utils.logger import get_main_logger
import subprocess

logger = get_main_logger(__name__)


class EnvSetupAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._initialize_resources() 
        self.bug_commit = kwargs.get("bug_commit")
        self._checkout_commit()
   
    
    def _initialize_resources(self):
        try:
            self.repo_files_env = self.resource_dict.get_item_of_resource_type(EnvSetupResource)
        except KeyError as e:
            raise RuntimeError(f"{e.args[0]} has not been initiatilized. Please instantiate in the workflow.")

    def _checkout_commit(self): 
        """
        Checks out a specific commit in the repository.
        """
        if not self.bug_commit:
            raise ValueError("No bug commit specified for checkout.")
        
        try:
            # Perform git checkout
            subprocess.run(
                ["git", "checkout", self.bug_commit],
                cwd=self.repo_files_env.files_dir,
                check=True
            )
            logger.info(f"Checked out commit {self.bug_commit} in {self.repo_files_env.files_dir}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to checkout commit {self.bug_commit}: {e}")
            raise RuntimeError(f"Checkout failed for commit {self.bug_commit}")


    def run(self, responses: List[Response]) -> Response:
        resource_id = BaseResponse(self.repo_files_env.resource_id)
        return resource_id


   