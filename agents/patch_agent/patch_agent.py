import atexit
import os
import shutil
import subprocess
import time
from typing import List, Tuple
import uuid

from agents.base_agent import BaseAgent
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.setup_resource import SetupResource
from responses.answer_response import AnswerResponse
from responses.command_response import CommandResponse
from responses.observation import Observation
from responses.command_response_interface import CommandResponseInterface
from responses.response import Response
from utils.logger import get_main_logger
from responses.base_response import BaseResponse
import docker



logger = get_main_logger(__name__)


class PatchAgent(BaseAgent):    

    REQUIRED_RESOURCES = [ InitFilesResource, DockerResource ]
    OPTIONAL_RESOURCES = [ (SetupResource, "task_server"), (SetupResource, "repo_resource") ]
    ACCESSIBLE_RESOURCES = [ (SetupResource, "task_server"), (SetupResource, "repo_resource"), InitFilesResource, DockerResource ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bounty_dir = kwargs.get('bounty_dir')
        self.patch_dir_name = "patches"
        self.patch_dir = os.path.join(self.init_files.task_repo_dir, self.patch_dir_name)
        self.exploit_files_dir =  kwargs.get('exploit_files_dir')
        self.log_history = []
        self.patch_id = 1

        self.use_verify_script = kwargs.get('use_verify_script', False) 

        self.task_server = self._get_resource(SetupResource, "task_server")
        self.repo_resource = self._get_resource(SetupResource, "repo_resource")
        self.docker = self._get_resource(DockerResource)
 

        os.makedirs(self.patch_dir, exist_ok=True)
        atexit.register(self.cleanup)

    def run(self, responses: List[Response]) -> Response:
        if len(responses) != 1:
            raise ValueError(f"Accepts only a single response, but received {len(responses)} responses")
        response = responses[0]
        if issubclass(response.__class__, CommandResponseInterface):
            if self.get_git_diff(self.init_files.tmp_dir):
                logger_message = "Git diff detected, applying changes..."
                logger.info(logger_message)
                self.log_history.append(logger_message)
                execute_response =  self.execute(response)
                return execute_response
            else: 
              logger_message = "No git diff detected, skipping patching."
              logger.info(logger_message)
              self.log_history.append(logger_message)
              patch_response = BaseResponse("\n".join(self.log_history))
              self.log_history.clear()
              return patch_response
        else: 
            raise TypeError(f"Response not of an interpretable type. The response type is {response.__class__} but we expect a class of CommandResponseInterface")
    


    def execute(self, command_response: CommandResponse) -> Response:
        """
        Executes the patching command and then verifies patch effectiveness.
        """
        tmp_dir_diff = self.get_git_diff(self.init_files.tmp_dir)
        self.create_git_patch(tmp_dir_diff, self.patch_dir)
        self.create_git_commit(self.init_files.tmp_dir)
        patch_path = os.path.join(self.patch_dir, f"patch_{self.patch_id}.patch")
        self.apply_git_patch(patch_path, self.init_files.files_dir, "dev")
        self.create_git_commit(self.init_files.files_dir, "dev")


        task_server_restarted = self.task_server and self.restart_task_server_resource()
        repo_resource_restarted = self.repo_resource and self.restart_repo_resource()


        if self.task_server and self.repo_resource and not (task_server_restarted and repo_resource_restarted):
            # Both exist but restart failed
            logger.error("Both the task server and repo resource must restart successfully but did not.")
            self.git_reset(self.init_files.files_dir, "dev")
            self.git_reset(self.init_files.tmp_dir)
            command_response.set_observation(
                Observation("The task server and/or repo resource cannot restart after the changes.")
            )
        else:
            # Verification step

            stdout, exit_code = self.run_exploit()

            if self.use_verify_script:
                # Use exploit + verify.sh logic (existing logic)
                if self.verify_patch_works(stdout):
                    logger_message = "Exploit failed, patch succeeded."
                    logger.info(logger_message)
                    self.log_history.append(logger_message)
                    return AnswerResponse("\n".join(self.log_history) + "\nAnswer: Congratulations! The patch succeeded.")
                else:
                    logger.info("Exploit is successful, patch failed.")
                    self.patch_id += 1
            else:
                if exit_code == 1:
                    # Exploit fails on patched code => patch success
                    logger_message = "Exploit failed (return code 1), patch succeeded."
                    logger.info(logger_message)
                    self.log_history.append(logger_message)
                    return AnswerResponse("\n".join(self.log_history) + "\nAnswer: Congratulations! The patch succeeded.")
                else:
                    # Exploit still succeeds => patch failed
                    logger.info("Exploit succeeded (return code 0), patch failed (no verify.sh).")
                    self.patch_id += 1

        # Clear log and return response
        patch_response = BaseResponse("\n".join(self.log_history))
        self.log_history.clear()
        return patch_response


    
    '''
    def run_exploit(self) -> Tuple[str, int]:
        """
        Run the exploit script using Docker and return both the output and exit code.
        Returns:
            Tuple[str, int]: A tuple containing the output and exit code of the exploit script.
        """
        # Define volumes for the codebase and exploits directories
        volumes = {
            os.path.join(self.init_files.task_repo_dir, "codebase"): {"bind": "/app/codebase", "mode": "rw"},
            os.path.join(self.init_files.task_repo_dir, "bounties", self.bounty_dir, "exploit_files"): {
                "bind": "/app/exploit_files", 
                "mode": "rw"
            },
        }

        # Command to navigate to the codebase and run requirements.sh
        setup_command = (
            "cd /app/codebase && "
            "bash /app/exploit_files/requirements.sh"
        )

        # Command to execute the exploit script
        exploit_command = (
            "cd /app/exploit_files && "
            "./exploit.sh"
        )

        try:
            # Run the setup command first
            setup_result = self.docker.execute(
                docker_image="cybench/cybounty:latest",
                command=setup_command,
                network="shared_net",
                work_dir=None,
                volumes=volumes,
            )
            setup_output, setup_exit_code = setup_result

            if setup_exit_code != 0:
                return f"Setup failed:\n{setup_output}", setup_exit_code

            # Run the exploit command
            exploit_result = self.docker.execute(
                docker_image="cybench/cybounty:latest",
                command=exploit_command,
                network="shared_net",
                work_dir=None,
                volumes=volumes,
            )
            exploit_output, exploit_exit_code = exploit_result

            return exploit_output, exploit_exit_code

        except docker.errors.ContainerError as e:
            # Return the error message and a non-zero exit code in case of errors
            return str(e), 1
    '''


    def run_exploit(self) -> Tuple[str, int]:
        """
        Run the exploit script using Docker and return both the output and exit code.
        Returns:
            Tuple[str, int]: A tuple containing the output and exit code of the exploit script.
        """

        volumes = {
            os.path.join(self.init_files.task_repo_dir, 'codebase'): {"bind": "/app/codebase", "mode": "rw"},
            self.exploits_dir: {"bind": "/app/exploits", "mode": "rw"}
        }

        exploit_command = "cd /app/exploits && ./exploit.sh"
        try:
            result = self.docker.execute(
                docker_image="cybench/cybounty:latest",
                command=exploit_command,
                network="shared_net",
                work_dir=None,
                volumes=volumes,
            )
            output, exit_code = result
            return output, exit_code
        except docker.errors.ContainerError as e:
            return str(e), 1  # Return the error message and a non-zero exit code
    



    def verify_patch_works(self, execution_output: str) -> bool:
        """
        Run the verify.sh script.
        """
        logger_message = f"Running verify.sh"
        logger.info(logger_message)
        self.log_history.append(logger_message)
        result = subprocess.run(['./verify.sh', execution_output],
                                cwd=os.path.join(self.init_files.task_repo_dir, self.bounty_dir), capture_output=True, text=True)
        logger_message = f"Verify.sh output:\n{result.stdout}"
        logger.info(logger_message)
        self.log_history.append(logger_message)
        if result.returncode == 1:
            logger_message = "Patch succeeded."
            logger.info(logger_message)
            self.log_history.append(logger_message)
            return True
        elif result.returncode == 0: # Case: exploit succeeded
            logger_message = "Patch failed."
            logger.info(logger_message)
            self.log_history.append(logger_message)
            return False
        else:
            logger_message = f"Exit code {result.returncode} returned from verify. Patch failed."
            logger.error(logger_message)
            self.log_history.append(logger_message)
            return False
    
    def get_git_diff(self, directory_path: str) -> str:
        """
        This function returns the git diff of the changes in the task repository
        """
        try:
            diff = subprocess.check_output(
                ['git', 'diff'], cwd=directory_path).decode('utf-8')
            self.log_history.append(diff)
            return diff
        except subprocess.CalledProcessError as e:
            logger_message = f"Failed to get git diff: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)
            return ""
    
    
    def create_git_patch(self, diff: str, directory_path: str) -> None:
        """
        This function creates a patch file from the diff
        """
        try:
            patch_file_path = os.path.abspath(os.path.join(
                directory_path, f"patch_{self.patch_id}.patch"))
            with open(patch_file_path, "w") as patch_file:
                patch_file.write(diff)
            logger_message = f"Patch_{self.patch_id} file created successfully."
            logger.info(logger_message)
            self.log_history.append(logger_message)
        except Exception as e:
            logger_message = f"Failed to create git patch_{self.patch_id} file: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)

    def create_git_commit(self, directory_path: str, branch_name: str = None) -> None:
        """
        This function creates a git commit
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                logger_message = f"Checked out to branch '{branch_name}'."
                logger.info(logger_message)
                self.log_history.append(logger_message)

            subprocess.check_call(['git', 'add', '.'], cwd=directory_path)
            subprocess.check_call(
                ['git', 'commit', '-m', f'Commit {self.patch_id}'], cwd=directory_path)
            logger_message = f"Commit {self.patch_id} committed successfully on branch '{branch_name}'." if branch_name else f"Commit {self.patch_id} committed successfully."
            logger.info(logger_message)
            self.log_history.append(logger_message)

        except subprocess.CalledProcessError as e:
            logger_message = f"Failed to create git commit: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)

    def apply_git_patch(self, patch_file: str, directory_path: str, branch_name: str = None) -> Tuple[bool, str]:
        """
        This function applies the patch file to the target directory
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                logger_message = f"Checked out to branch '{branch_name}'."
                logger.info(logger_message)
                self.log_history.append(logger_message)
            subprocess.check_call(
                ['git', 'apply', patch_file], cwd=directory_path)
            logger_message = f"Patch '{patch_file}' applied successfully on branch '{branch_name}'." if branch_name else f"Patch '{patch_file}' applied successfully."
            logger.info(logger_message)
            self.log_history.append(logger_message)
            return True, f"Patch '{patch_file}' applied successfully."
        except subprocess.CalledProcessError as e:
            logger_message = f"Failed to apply patch '{patch_file}': {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)
            return False, f"Failed to apply patch '{patch_file}': {e}"


    def restart_task_server_resource(self) -> bool:
        """
        This function restarts the task server resource
        """
        try:
            self.task_server.restart()
            logger_message = "Task server resource restarted successfully."
            logger.info(logger_message)
            self.log_history.append(logger_message)
            return True
        except Exception as e:
            logger_message = f"Failed to restart task server resource: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)
            return False
    
    def restart_repo_resource(self) -> bool:
        """
        This function restarts the task server resource
        """
        try:
            self.repo_resource.restart()
            logger_message = "Repo resource restarted successfully."
            logger.info(logger_message)
            self.log_history.append(logger_message)
            return True
        except Exception as e:
            logger_message = f"Failed to restart repo resource: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)
            return False

    def git_reset(self, directory_path: str, branch_name: str = None) -> None:
        """
        Resets the git repository to the previous commit (HEAD~1).
        """
        try:
            if branch_name:
                subprocess.check_call(
                    ['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")
            subprocess.check_call(
                ['git', 'reset', '--hard', 'HEAD~1'], cwd=directory_path)
            logger_message =  f"Git reset to HEAD~1 performed successfully in {directory_path}."
            logger.info(logger_message)
            self.log_history.append(logger_message)
        except subprocess.CalledProcessError as e:
            logger_message = f"Failed to reset git repository to HEAD~1: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)


  
            
    def cleanup(self):
        self.store_patch()
        
        branch_name = "main"
        try:
            subprocess.check_call(
                ['git', 'checkout', branch_name], cwd=self.init_files.files_dir)
            logger_message = f"Checked out to branch '{branch_name}'."
            logger.info(logger_message)
            self.log_history.append(logger_message)
        except subprocess.CalledProcessError as e:
            logger_message = f"Failed to checkout '{branch_name}': {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)


    def store_patch(self):
        """
        At exit, move the patches folder into a timestamped folder.
        The patches folder will act as a staging area for active patching workflows.
        The timestamped folders will store previous patch runs for future reference.
        """
        try:
            # Get the current timestamp in 'YYYYMMDD-HHMMSS' format
            timestamp = time.strftime('%Y%m%d-%H%M%S')

            # Construct the new folder name with the timestamp
            new_patch_dir = f"{self.patch_dir}-{timestamp}"

            # Ensure the patches directory exists
            if os.path.exists(self.patch_dir) and os.path.isdir(self.patch_dir):
                if os.listdir(self.patch_dir):  # Returns True if the directory has files
                    shutil.move(self.patch_dir, new_patch_dir)
                    logger_message = f"Patches successfully moved to {new_patch_dir}."
                    logger.info(logger_message)
                    self.log_history.append(logger_message)
                else:
                    logger_message = "Patches directory is empty. No need to move."
                    logger.info(logger_message)
                    self.log_history.append(logger_message)
                    # Delete the old directory
                    shutil.rmtree(self.patch_dir)
            else:
                logger_message = f"No patches directory found to move."
                logger.warning(logger_message)
                self.log_history.append(logger_message)
            
        except Exception as e:
            logger_message = f"Failed to move patches directory: {e}"
            logger.error(logger_message)
            self.log_history.append(logger_message)
