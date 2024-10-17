import atexit
import logging
from typing import List, Tuple
from agents.base_agent import BaseAgent
from resources.init_files_resource import InitFilesResource
from resources.task_server_resource import TaskServerResource
from responses.command_response_interface import CommandResponseInterface
from responses.response import Response
import subprocess
import os


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatchAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__()
        # Check if there are TaskServerResource and InitFilesResource
        if InitFilesResource in self.resource_dict.resource_type_to_resources:
            self.init_files: InitFilesResource = self.resource_dict.get_items_of_resource_type(InitFilesResource)[0]
        else:
            logger.error("InitFilesResource not found in resource_dict. Terminating Patch Agent.")
            raise RuntimeError("InitFilesResource not set up. Patch agent cannot start.")
        
        if TaskServerResource in self.resource_dict.resource_type_to_resources:
            self.task_server: TaskServerResource = self.resource_dict.get_items_of_resource_type(TaskServerResource)[0]
        else:
            logger.error("TaskServerResource not found in resource_dict. Terminating Patch Agent.")
            raise RuntimeError("TaskServerResource not set up. Patch agent cannot start.")

        #TODO: Create a temporary branch for the original_files_dir on local machine
        self.create_git_branch()
        atexit.register(self.cleanup)
        self.patch_id = 1

    def run(self, responses: List[Response]) -> Response:        
        if len(responses) != 1:
            return Exception(f'Accepts only a single response, you passed in {len(responses)} responses')
        response = responses[0]
        if issubclass(response.__class__, CommandResponseInterface):
            if self.get_git_diff() != "":
                return self.execute()
            else:
                return response
        else:
            raise Exception('Response not of an interpretable type. The response type is {response.__class__} but we expect a class of CommandResponseInterface')

    def execute(self) -> Response:
        """
        This function executes the patching command
        """
        diff = self.get_git_diff()
        self.create_git_patch(diff)
        self.create_git_commit() # This will commit the changes to the tmp directory

        res, msg = self.apply_git_patch(p2) # Apply the agent patch file (p2) to the tmp branch
        res, msg = self.apply_git_patch(p1) # Apply the flag patch file (p1) to the tmp branch
        if res:
            res = self.restart_task_server_resource()
            if res:
                flag = self.run_exploit()
                if flag:
                    # Patch succeed?
                    # Maybe just send back an AnswerResponse object?
                    pass
                else:
                    # Patch failed
                    #TODO: what should we return in this case?
                    pass

            else:
                #TODO: Handle the case where the task server resource is not restarted successfully; git reset
                pass
        else:
            #TODO: Handle the case where the patch is not applied successfully i.e. merge conflicts; I think it will make sense to just set the observation field.; git reset
            pass


        raise NotImplementedError

    def get_git_diff(self) -> str:
        """
        This function returns the git diff of the changes in the task repository
        """
        try:
            diff = subprocess.check_output(['git', 'diff'], cwd=self.init_files.original_files_dir).decode('utf-8')
            return diff
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get git diff: {e}")
            return ""
    
    def create_git_patch(self, diff: str) -> None:
        """
        This function creates a patch file from the diff
        """
        try:
            with open(f"patch_{self.patch_id}.diff", "w") as patch_file:
                patch_file.write(diff)
            logger.info(f"Patch_{self.patch_id} file created successfully.")
        except Exception as e:
            logger.error(f"Failed to create git patch_{self.patch_id} file: {e}")

    def create_git_commit(self) -> None:
        """
        This function creates a git commit
        """
        try:
            subprocess.check_call(['git', 'add', '.'], cwd=self.init_files.original_files_dir)
            subprocess.check_call(['git', 'commit', '-m', f'Applied patch_{self.patch_id}'], cwd=self.init_files.original_files_dir)
            logger.info(f"Patch_{self.patch_id} committed successfully.")
            self.patch_id += 1
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create git commit: {e}")

    def create_git_branch(self) -> None:
        """
        This function creates a temporary branch on the local machine
        """
        try:
            branch_name = "temp"
            subprocess.check_call(['git', 'checkout', '-b', branch_name], cwd=self.init_files.original_files_dir)
            logger.info(f"Temporary branch '{branch_name}' created successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create temporary branch {branch_name}: {e}")
            raise RuntimeError(f"Failed to create a temporary branch {branch_name}.")
    
    def apply_git_patch(self, patch_file: str) -> Tuple[bool, str]:
        """
        This function applies the patch file to the target directory
        """
        try:
            subprocess.check_call(['git', 'apply', patch_file], cwd=self.init_files.original_files_dir)
            logger.info(f"Patch '{patch_file}' applied successfully.")
            return True, f"Patch '{patch_file}' applied successfully."
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply patch '{patch_file}': {e}")
            return False, f"Failed to apply patch '{patch_file}': {e}"

    def cleanup(self) -> None:
        """
        This function cleans up the temporary branch etc.
        """
        try:
            subprocess.check_call(['git', 'checkout', 'main'], cwd=self.init_files.original_files_dir)
            subprocess.check_call(['git', 'branch', '-D', 'temp'], cwd=self.init_files.original_files_dir)
            logger.info("Temporary branch cleaned up successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clean up temporary branch: {e}")
        
        for file in os.listdir(self.init_files.original_files_dir):
            if file.startswith("patch_") and file.endswith(".diff"):
                try:
                    os.remove(os.path.join(self.init_files.original_files_dir, file))
                    logger.info(f"Removed patch file: {file}")
                except Exception as e:
                    logger.error(f"Failed to temporary patch file '{file}': {e}")
