import atexit
import logging
import os
import shutil
import subprocess
from typing import List, Tuple

from agents.base_agent import BaseAgent
from resources.init_files_resource import InitFilesResource
from resources.task_server_resource import TaskServerResource
from responses.command_response_interface import CommandResponseInterface
from responses.response import Response
from responses.answer_response import AnswerResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatchAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__()
        # Check if there are TaskServerResource and InitFilesResource
        if InitFilesResource in self.resource_dict.resource_type_to_resources:
            self.init_files: InitFilesResource = self.resource_dict.get_items_of_resource_type(
                InitFilesResource)[0]
        else:
            logger.error(
                "InitFilesResource not found in resource_dict. Terminating Patch Agent.")
            raise RuntimeError(
                "InitFilesResource not set up. Patch agent cannot start.")

        if TaskServerResource in self.resource_dict.resource_type_to_resources:
            self.task_server: TaskServerResource = self.resource_dict.get_items_of_resource_type(
                TaskServerResource)[0]
        else:
            logger.error(
                "TaskServerResource not found in resource_dict. Terminating Patch Agent.")
            raise RuntimeError(
                "TaskServerResource not set up. Patch agent cannot start.")

        atexit.register(self.cleanup)
        self.patch_id = 1
        self.patch_dir = os.path.join(self.init_files.task_repo_dir, "patches")
        
    def run(self, responses: List[Response]) -> Response:
        if len(responses) != 1:
            return Exception(f'Accepts only a single response, you passed in {len(responses)} responses')
        response = responses[0]
        if issubclass(response.__class__, CommandResponseInterface):
            if self.get_git_diff(self.init_files.tmp_dir) != "":
                return self.execute()
            else:
                return response
        else:
            raise Exception(
                'Response not of an interpretable type. The response type is {response.__class__} but we expect a class of CommandResponseInterface')

    def execute(self) -> Response:
        """
        This function executes the patching command
        """
        """
        diff = self.get_git_diff()
        self.create_git_patch(diff)
        self.create_git_commit() # This will commit the changes to the tmp directory

        res, msg = self.apply_git_patch(p2) # Apply the agent patch file (p2) to the tmp branch
        res, msg = self.apply_git_patch(p1) # Apply the flag patch file (p1) to the tmp branch
        """


        tmp_dir_diff = self.get_git_diff(self.init_files.tmp_dir)
        self.create_git_patch(tmp_dir_diff, self.init_files.tmp_dir)
        self.create_git_commit(self.init_files.tmp_dir)
        #TODO: Might not need the copying logic
        tmp_dir_patch = os.path.abspath(os.path.join(self.init_files.tmp_files_dir, f"patch_{self.patch_id}.patch"))
        task_repo_patch = os.path.abspath(os.path.join(self.init_files.task_repo_dir, f"patch_{self.patch_id}.patch"))
        self.copy_patch(tmp_dir_patch, task_repo_patch)
        res, msg = self.apply_git_patch(f"patch_{self.patch_id}.patch", self.init_files.task_repo_dir, "dev")


        if res:
            
            res = self.restart_task_server_resource()
            if res:
                flag = self.run_exploit()
                if flag: #patch succeeded
                    logger.info("Exploit successful. Patch succeeded.")
                    # Maybe just send back an AnswerResponse object?
                    #if we end up commiting then we want to increment the patch id
                    self.create_git_commit(self.init_files.task_repo_dir, "dev")
                    self.increment_patch_id()
                    return AnswerResponse(f"Answer: {flag}")
                else: #patch failed
                    # Patch failed
                    #TODO: what should we return in this case?
                    pass
            else:
                #TODO: Handle the case where the task server resource is not restarted successfully; git reset
                logger.error("Exploit failed after applying the patch.")
                self.git_reset(self.init_files.task_repo_dir)
        else:
            #TODO: Handle the case where the patch is not applied successfully i.e. merge conflicts; I think it will make sense to just set the observation field.; git reset
            logger.error("Failed to apply patch.")
            self.git_reset(self.init_files.task_repo_dir)


    def get_git_diff(self, directory_path: str) -> str:
        """
        This function returns the git diff of the changes in the task repository
        """
        try:
            diff = subprocess.check_output(['git', 'diff'], cwd=directory_path).decode('utf-8')
            return diff
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get git diff: {e}")
            return ""

    def create_git_patch(self, diff: str, directory_path: str) -> None:
        """
        This function creates a patch file from the diff
        """
        try:
            patch_file_path = os.path.join(directory_path, f"patch_{self.patch_id}.patch")
            with open(patch_file_path, "w") as patch_file:
                patch_file.write(diff)
            logger.info(f"Patch_{self.patch_id} file created successfully.")
        except Exception as e:
            logger.error(f"Failed to create git patch_{self.patch_id} file: {e}")

    def create_git_commit(self, directory_path: str, branch_name: str = None) -> None:
        """
        This function creates a git commit
        """
        try:
            if branch_name:
                subprocess.check_call(['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")

            patch_file = os.path.abspath(os.path.join(directory_path, f"patch_{self.patch_id}.patch"))
            subprocess.check_call(['git', 'add', patch_file], cwd=directory_path)
            subprocess.check_call(['git', 'commit', '-m', f'Applied patch_{self.patch_id}'], cwd=directory_path)
            logger.info(f"Patch_{self.patch_id} committed successfully on branch '{branch_name}'." if branch_name else f"Patch_{self.patch_id} committed successfully.")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create git commit: {e}")

    def copy_patch(self, patch_file_path: str, destination_path: str) -> None:
        """
        Copies the patch file from the tmp directory to the task repo's dev branch.
        """
        try:
            subprocess.check_call(['git', 'checkout', 'dev'], cwd=self.init_files.task_repo_dir)
            logger.info("Checked out to 'dev' branch in task repo.")
            # Copy the patch file to the task repo's dev branch
            shutil.copy(patch_file_path, destination_path)
            logger.info(f"Patch file copied to task repo dev branch: {destination_path}")
        except Exception as e:
            logger.error(f"Failed to copy patch file to dev branch: {e}")


    def apply_git_patch(self, patch_file: str, directory_path: str, branch_name: str = None) -> Tuple[bool, str]:
        """
        This function applies the patch file to the target directory
        """
        try:
            if branch_name:
                subprocess.check_call(['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")
            subprocess.check_call(['git', 'apply', patch_file], cwd=directory_path)
            logger.info(f"Patch '{patch_file}' applied successfully on branch '{branch_name}'." if branch_name else f"Patch '{patch_file}' applied successfully.")
            return True, f"Patch '{patch_file}' applied successfully."
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply patch '{patch_file}': {e}")
            return False, f"Failed to apply patch '{patch_file}': {e}"
        
    def increment_patch_id(self) -> None:
        self.patch_id += 1

    def cleanup(self) -> None:
        """
        This function cleans up the temporary branch etc.
        """
        try:
            subprocess.check_call(['git', 'checkout', 'master'], cwd=self.init_files.task_repo_dir)            
            subprocess.check_call(['git', 'branch', '-D', 'dev'], cwd=self.init_files.task_repo_dir)
            logger.info("Dev branch in task repo dir cleaned up successfully.")
            shutil.rmtree(self.init_files.tmp_files_dir)
            logger.info("Tmp directory deleted successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clean up dev branch: {e}")
        except FileNotFoundError as e:
            logger.error(f"Tmp directory not found for deletion: {e}")

    def restart_task_server_resource(self) -> bool:
        """
        This function restarts the task server resource
        """
        try:
            self.task_server.restart()
            logger.info("Task server resource restarted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to restart task server resource: {e}")
            return False
    
    def git_reset(self, directory_path: str, branch_name: str = None) -> None:
        """
        Resets the git repository to the previous commit (HEAD~1).
        """
        try:
            if branch_name: 
                subprocess.check_call(['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")
            subprocess.check_call(['git', 'reset', '--hard', 'HEAD~1'], cwd=directory_path)
            logger.info(f"Git reset to HEAD~1 performed successfully on branch '{branch_name}' in {directory_path}.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to reset git repository on branch '{branch_name}' to HEAD~1: {e}")
