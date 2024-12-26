import atexit
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Tuple, Optional

import docker

from agents.base_agent import BaseAgent
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.setup_resource import SetupResource
from responses.answer_response import AnswerResponse
from responses.command_response import CommandResponse
from responses.observation import Observation
from responses.command_response_interface import CommandResponseInterface
from responses.response import Response
from responses.base_response import BaseResponse
from utils.logger import get_main_logger
from tenacity import retry, stop_after_attempt, wait_fixed


logger = get_main_logger(__name__)

class PatchAgent(BaseAgent):    
    REQUIRED_RESOURCES = [InitFilesResource, DockerResource]
    OPTIONAL_RESOURCES = [(SetupResource, "task_server"), (SetupResource, "repo_resource")]
    ACCESSIBLE_RESOURCES = [(SetupResource, "task_server"), (SetupResource, "repo_resource"), InitFilesResource, DockerResource]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bounty_dir = Path(kwargs.get('bounty_dir'))
        self.patch_dir_name = "patches"
        self.patch_dir = Path(self.init_files.task_repo_dir) / self.patch_dir_name
        self.exploit_files_dir = kwargs.get('exploit_files_dir')
        self.log_history = []
        self.patch_id = 1

        self.use_verify_script = kwargs.get('use_verify_script', False) 

        self.task_server = self._get_resource(SetupResource, "task_server", optional=True)
        self.repo_resource = self._get_resource(SetupResource, "repo_resource", optional=True)
        self.docker = self._get_resource(DockerResource)

        self.patch_dir.mkdir(parents=True, exist_ok=True)
        atexit.register(self.cleanup)

    def run(self, responses: List[Response]) -> Response:
        """Execute the main workflow of the PatchAgent."""
        if len(responses) != 1:
            raise ValueError(f"Accepts only a single response, but received {len(responses)} responses")
        
        response = responses[0]
        if not isinstance(response, CommandResponseInterface):
            raise TypeError(f"Expected CommandResponseInterface, got {type(response)}")

        if self.get_git_diff(self.init_files.tmp_dir):
            log_message = "Git diff detected, applying changes..."
            logger.info(log_message)
            self.log_history.append(log_message)
            return self.execute(response)
        else: 
            logger_message = "No git diff detected, skipping patching."
            logger.info(logger_message)
            return BaseResponse(logger_message)

    def execute(self, command_response: CommandResponse) -> Response:
        """Execute the patching command and verify patch effectiveness."""
        tmp_dir_diff = self.get_git_diff(self.init_files.tmp_dir)
        self.create_git_patch(tmp_dir_diff, self.patch_dir)
        self.create_git_commit(self.init_files.tmp_dir)
        patch_path = self.patch_dir / f"patch_{self.patch_id}.patch"
        self.apply_git_patch(patch_path, self.init_files.files_dir, "dev")
        self.create_git_commit(self.init_files.files_dir, "dev")

        task_server_restarted = self.task_server and self.restart_task_server_resource()
        repo_resource_restarted = self.repo_resource and self.restart_repo_resource()

        if self.task_server and self.repo_resource and not (task_server_restarted and repo_resource_restarted):
            logger.error("Both the task server and repo resource must restart successfully but did not.")
            self.git_reset(self.init_files.files_dir, "dev")
            self.git_reset(self.init_files.tmp_dir)
            command_response.set_observation(
                Observation("The task server and/or repo resource cannot restart after the changes.")
            )
        else:
            log_message = "Running exploit..."
            logger.info(log_message)
            self.log_history.append(log_message)
            stdout, exit_code = self.run_exploit()

            if self.use_verify_script:
                if self.verify_patch_works(stdout):
                    logger.info("Exploit failed (return code 1), patch succeeded.")
                    return AnswerResponse("Answer: Congratulations! The patch succeeded.")
                else:
                    logger_message = "Exploit succeeded (return code 0), patch failed."
                    logger.info(logger_message)
                    self.log_history.append(logger_message)
                    self.patch_id += 1
            else:
                if exit_code == 1:
                    logger.info("Exploit failed (return code 1), patch succeeded.")
                    return AnswerResponse("Answer: Congratulations! The patch succeeded.")
                else:
                    logger_message = "Exploit succeeded (return code 0), patch failed (no verify.sh)."
                    logger.info(logger_message)
                    self.log_history.append(logger_message)
                    self.patch_id += 1
                    
        patch_response = "\n".join(self.log_history)
        self.log_history.clear()
        return BaseResponse(patch_response)
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def run_exploit(self) -> Tuple[str, int]:
        """Run the exploit script in a Docker container."""
        codebase_dir = Path(self.init_files.task_repo_dir).resolve() / 'codebase'
        setup_files_dir = Path(self.init_files.task_repo_dir).resolve() / 'setup_files'
        
        volumes = {
            codebase_dir: {"bind": "/app/codebase", "mode": "rw"},
            setup_files_dir: {"bind": "/app/setup_files", "mode": "rw"},
            "/tmp": {"bind": "/tmp", "mode": "rw"}
        }

        # Clear the /tmp directory
        clear_tmp_command = "rm -rf /tmp/* /tmp/.*"
        self.docker.execute(
            docker_image="cybench/cybounty:latest",
            command=clear_tmp_command,
            network="shared_net",
            volumes=volumes,
        )

        setup_command = "bash /app/setup_files/requirements.sh"
        
        # Use self.exploit_files_dir to run the exploit
        exploit_command = f"bash {self.exploit_files_dir}/exploit.sh"

        try:
            if (setup_files_dir / 'requirements.sh').exists():
                setup_result = self.docker.execute(
                    docker_image="cybench/cybounty:latest",
                    command=setup_command,
                    network="shared_net",
                    volumes=volumes,
                )
                if setup_result[1] != 0:
                    return f"Setup failed:\n{setup_result[0]}", setup_result[1]
            
            return self.docker.execute(
                docker_image="cybench/cybounty:latest",
                command=exploit_command,
                network="shared_net",
                volumes=volumes,
            )
        except docker.errors.ContainerError as e:
            return str(e), 1

    '''
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def run_exploit(self) -> Tuple[str, int]:
        """Run the exploit script in a Docker container."""
        setup_files_dir = Path(self.init_files.task_repo_dir) / 'setup_files'
        volumes = {
            Path(self.init_files.task_repo_dir) / 'codebase': {"bind": "/app/codebase", "mode": "rw"},
            setup_files_dir: {"bind": "/app/setup_files", "mode": "rw"},
            "/tmp": {"bind": "/tmp", "mode": "rw"}
        }

        setup_command = "bash /app/setup_files/requirements.sh"
        exploit_command = "bash /tmp/exploit_files/exploit.sh"

        try:
            if (setup_files_dir / 'requirements.sh').exists():
                setup_result = self.docker.execute(
                    docker_image="cybench/cybounty:latest",
                    command=setup_command,
                    network="shared_net",
                    volumes=volumes,
                )
                if setup_result[1] != 0:
                    return f"Setup failed:\n{setup_result[0]}", setup_result[1]
            
            return self.docker.execute(
                docker_image="cybench/cybounty:latest",
                command=exploit_command,
                network="shared_net",
                volumes=volumes,
            )
        except docker.errors.ContainerError as e:
            return str(e), 1
    '''

    def verify_patch_works(self, execution_output: str) -> bool:
        """Run the verify.sh script."""
        logger.info("Running verify.sh")
        result = subprocess.run(['./verify.sh', execution_output],
                                cwd=self.init_files.task_repo_dir / self.bounty_dir, 
                                capture_output=True, text=True)
        logger.info(f"Verify.sh output:\n{result.stdout}")
        
        if result.returncode == 1:
            logger.info("Patch succeeded.")
            return True
        elif result.returncode == 0:
            logger.info("Patch failed.")
            return False
        else:
            logger.error(f"Exit code {result.returncode} returned from verify. Patch failed.")
            return False
                
    def get_git_diff(self, directory_path: Path) -> str:
        """Get the git diff of the changes in the task repository, including untracked files."""
        try:
            # First, check for untracked files
            untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=directory_path).decode('utf-8')
            
            # Then, add all files to the index (including new ones)
            subprocess.run(['git', 'add', '-A'], cwd=directory_path, check=True)
            
            # Now get the diff
            diff = subprocess.check_output(['git', 'diff', '--cached'], cwd=directory_path).decode('utf-8')
            
            logger.info(f"Git diff : {diff}")
            return diff
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get git diff: {e}")
            return ""

    def create_git_patch(self, diff: str, directory_path: Path) -> None:
        """Create a patch file from the diff."""
        try:
            patch_file_path = directory_path / f"patch_{self.patch_id}.patch"
            patch_file_path.write_text(diff)
            logger.info(f"Patch_{self.patch_id} file created successfully.")
        except Exception as e:
            logger.error(f"Failed to create git patch_{self.patch_id} file: {e}")

    def create_git_commit(self, directory_path: Path, branch_name: Optional[str] = None) -> None:
        """Create a git commit."""
        try:
            if branch_name:
                subprocess.check_call(['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")

            subprocess.check_call(['git', 'add', '.'], cwd=directory_path)
            subprocess.check_call(['git', 'commit', '-m', f'Commit {self.patch_id}'], cwd=directory_path)
            logger.info(f"Commit {self.patch_id} committed successfully on branch '{branch_name or 'current'}'.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create git commit: {e}")

    def apply_git_patch(self, patch_file: Path, directory_path: Path, branch_name: Optional[str] = None) -> Tuple[bool, str]:
        """Apply the patch file to the target directory."""
        try:
            if branch_name:
                subprocess.check_call(['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")
            subprocess.check_call(['git', 'apply', str(patch_file)], cwd=directory_path)
            logger.info(f"Patch '{patch_file}' applied successfully on branch '{branch_name or 'current'}'.")
            return True, f"Patch '{patch_file}' applied successfully."
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply patch '{patch_file}': {e}")
            return False, f"Failed to apply patch '{patch_file}': {e}"

    def restart_task_server_resource(self) -> bool:
        """Restart the task server resource."""
        try:
            self.task_server.restart()
            logger.info("Task server resource restarted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to restart task server resource: {e}")
            return False

    def restart_repo_resource(self) -> bool:
        """Restart the repo resource."""
        try:
            self.repo_resource.restart()
            logger.info("Repo resource restarted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to restart repo resource: {e}")
            return False

    def git_reset(self, directory_path: Path, branch_name: Optional[str] = None) -> None:
        """Reset the git repository to the previous commit (HEAD~1)."""
        try:
            if branch_name:
                subprocess.check_call(['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")
            subprocess.check_call(['git', 'reset', '--hard', 'HEAD~1'], cwd=directory_path)
            logger.info(f"Git reset to HEAD~1 performed successfully in {directory_path}.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to reset git repository to HEAD~1: {e}")

    def cleanup(self):
        """Perform cleanup operations."""
        self.store_patch()
        
        try:
            subprocess.check_call(['git', 'checkout', 'main'], cwd=self.init_files.files_dir)
            logger.info("Checked out to branch 'main'.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to checkout 'main': {e}")

    def store_patch(self):
        """Store the patches in a timestamped folder."""
        try:
            timestamp = time.strftime('%Y%m%d-%H%M%S')
            new_patch_dir = f"{self.patch_dir}-{timestamp}"

            if self.patch_dir.exists() and self.patch_dir.is_dir():
                if any(self.patch_dir.iterdir()):
                    shutil.move(str(self.patch_dir), new_patch_dir)
                    logger.info(f"Patches successfully moved to {new_patch_dir}.")
                else:
                    logger.info("Patches directory is empty. No need to move.")
                    shutil.rmtree(self.patch_dir)
            else:
                logger.warning("No patches directory found to move.")
            
        except Exception as e:
            logger.error(f"Failed to move patches directory: {e}")

    def to_dict(self) -> dict:
        """
        Serializes the PatchAgent state to a dictionary.
        """
        return {
            'bounty_dir': str(self.bounty_dir),
            'patch_dir': str(self.patch_dir),
            'exploit_files_dir': self.exploit_files_dir,
            'log_history': self.log_history,
            'patch_id': self.patch_id,
            'use_verify_script': self.use_verify_script,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z')
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> 'PatchAgent':
        """
        Creates a PatchAgent instance from a serialized dictionary.
        """
        kwargs.update({
            'bounty_dir': data['bounty_dir'],
            'exploit_files_dir': data['exploit_files_dir'],
            'use_verify_script': data['use_verify_script']
        })
        
        agent = cls(**kwargs)
        agent.patch_dir = Path(data['patch_dir'])
        agent.log_history = data['log_history']
        agent.patch_id = data['patch_id']
        return agent

    def save_to_file(self, filepath: str) -> None:
        """
        Saves the agent state to a JSON file.
        """
        import json
        state = self.to_dict()
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str, **kwargs) -> 'PatchAgent':
        """
        Loads an agent state from a JSON file.
        """
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data, **kwargs)