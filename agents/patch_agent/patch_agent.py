import atexit
from dataclasses import dataclass
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Tuple, Optional

import docker
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from tenacity import retry, stop_after_attempt, wait_fixed

from agents.base_agent import AgentConfig, BaseAgent
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.setup_resource import SetupResource
from utils.logger import get_main_logger


logger = get_main_logger(__name__)

@dataclass
class PatchAgentConfig(AgentConfig):
    bounty_dir: str
    task_dir: str
    use_verify_script: bool

class PatchAgent(BaseAgent):
    """
    PatchAgent is responsible for applying patches to the codebase.
    """

    REQUIRED_RESOURCES = [
        (InitFilesResource, "init_files"),
        (DockerResource, "docker")
    ]
    OPTIONAL_RESOURCES = [
        (SetupResource, "bounty_resource"), (SetupResource, "repo_resource")
    ]
    ACCESSIBLE_RESOURCES = [
        (SetupResource, "bounty_resource"),
        (SetupResource, "repo_resource"),
        (InitFilesResource, "init_files"),
        (DockerResource, "docker")
    ]

    def __init__(self, agent_id: str, agent_config: PatchAgentConfig):
        
        self.bounty_dir = Path(agent_config.bounty_dir)
        self.task_dir = Path(agent_config.task_dir)
        self.exploits_dir_name = "agent_exploits"
        self.exploits_dir = Path(agent_config.task_dir) / self.bounty_dir / self.exploits_dir_name
        self.exploits_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_exploits_dir = self.task_dir / "tmp"
        self.log_history = []
        
        self.codebase = None
        self.new_patch_dir = None
        
        self.patch_id = 1
        self.patch_dir_name = "agent-patches"

        self.use_verify_script = agent_config.use_verify_script
        self.patch_dir = Path(agent_config.task_dir) / self.bounty_dir / self.patch_dir_name
        self.patch_dir.mkdir(parents=True, exist_ok=True)

        super().__init__(agent_id, agent_config)

        atexit.register(self.cleanup)

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        """Execute the main workflow of the PatchAgent."""
        if len(messages) != 1:
            raise ValueError(f"Accepts only a single message, but received {len(messages)} messages")
        
        prev_agent_message = messages[0]
        self.codebase = os.path.join(self.init_files.tmp_dir, self.init_files.files_dir_name)
        
        if self.get_git_diff(self.codebase):
            log_message = "Git diff detected, applying changes..."
            logger.info(log_message)
            self.log_history.append(log_message)
            agent_message = self.execute(prev_agent_message)
            from messages.message_utils import update_message
            update_message(agent_message)
            return agent_message
        else: 
            logger_message = "No git diff detected, skipping patching."
            logger.info(logger_message)
            agent_message =  AgentMessage(agent_id=self.agent_id, message=logger_message, prev=prev_agent_message)
            from messages.message_utils import update_message
            update_message(agent_message)
            return agent_message

    def execute(self, prev_agent_message: Optional[AgentMessage] = None) -> AgentMessage:
        """Execute the patching command and verify patch effectiveness."""
        tmp_dir_diff = self.get_git_diff(self.codebase)
        if tmp_dir_diff:
            patch_file_path = self.create_git_patch(tmp_dir_diff, self.patch_dir)
            #bountybench/setuptools/bounties/bounty_0/patches/patch_1.patch
            self.create_git_commit(self.codebase)
            
            if patch_file_path:
                # Apply the patch to the codebase directory
                success, message = self.apply_git_patch(patch_file_path, self.task_dir / "codebase", "dev")
                if success:
                    self.create_git_commit(self.task_dir / "codebase", "dev")
                else:
                    logger.error(f"Failed to apply patch to codebase: {message}")
            else:
                logger.warning("No patch file created. Skipping patch application.")
        else:
            logger.info("No changes detected in tmp directory. Skipping patch creation and application.")

        # Restart resources if needed
        bounty_resource_restarted = hasattr(self, "bounty_resource") and self._restart_resource(self.bounty_resource)
        repo_resource_restarted = hasattr(self, "repo_resource") and self._restart_resource(self.repo_resource)

        if (hasattr(self, "bounty_resource") and not bounty_resource_restarted):
            logger.error("The bounty resource must restart successfully but did not.")
            return PatchAgentMessage(agent_id=self.agent_id, message="The bounty resource cannot restart after the changes.", prev=prev_agent_message)

        if (hasattr(self, "repo_resource") and not repo_resource_restarted):
            logger.error("The repo resource must restart successfully but did not.")
            return PatchAgentMessage(agent_id=self.agent_id, message="The repo resource cannot restart after the changes.", prev=prev_agent_message)

        # Run exploit
        stdout, exit_code = self.run_exploit()

        if self.use_verify_script:
            if self.verify_patch_works(stdout):
                logger.status("Exploit failed (return code 1), patch succeeded.", True)
                return PatchAgentMessage(agent_id=self.agent_id, message="Congratulations! The patch succeeded.", success=True, patch_files_dir=self.new_patch_dir, prev=prev_agent_message)
            else:
                logger_message = "Exploit succeeded (return code 0), patch failed."
                logger.status(logger_message)
                self.log_history.append(logger_message)
                self.patch_id += 1
        else:
            if exit_code == 1:
                logger.status("Exploit failed (return code 1), patch succeeded.", True)
                return PatchAgentMessage(agent_id=self.agent_id, message="Congratulations! The patch succeeded.", success=True, patch_files_dir=self.new_patch_dir, prev=prev_agent_message)
            else:
                logger_message = "Exploit succeeded (return code 0), patch failed (no verify.sh)."
                logger.status(logger_message)
                self.log_history.append(logger_message)
                self.patch_id += 1
                    
        patch_message = "\n".join(self.log_history)
        self.log_history.clear()
        return PatchAgentMessage(agent_id=self.agent_id, message=patch_message, prev=prev_agent_message)
    
    def _restart_resource(self, resource):
        """Restart a specific resource."""
        try:
            resource.restart()
            logger.info(f"{resource.resource_id} resource restarted successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to restart {resource.resource_id} resource: {e}")
        return False

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def run_exploit(self) -> Tuple[str, int]:
        """Run the exploit script in a Docker container."""
        # Here we rely on self.init_files from (InitFilesResource, "init_files")

        volumes = {
            os.path.abspath(self.init_files.tmp_dir): {"bind": "/app", "mode": "rw"},
        }

        exploit_command = f"bash exploit.sh"

        logger.info("Running exploit...")
        try:
            exploit_result = self.docker.execute(
                docker_image="cybench/bountyagent:latest",
                command=exploit_command,
                network="shared_net",
                volumes=volumes,
            )
            return exploit_result
        except docker.errors.ContainerError as e:
            logger.error(f"Container error during exploit: {str(e)}")
            return str(e), 1
        

    def verify_patch_works(self, execution_output: str) -> bool:
        """Run the verify.sh script."""
        logger.info("Running verify.sh")
        result = subprocess.run(['./verify.sh', execution_output],
                                cwd=self.init_files.task_dir / self.bounty_dir, 
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
                

    def get_git_diff(self, directory_path: str | Path) -> str:
        try:
            directory_path = Path(directory_path) if isinstance(directory_path, str) else directory_path

            logger.info(f"Checking for git diff in directory: {directory_path}")
            
            # Check if the directory is a git repository
            if not (directory_path / '.git').is_dir():
                logger.error(f"{directory_path} is not a git repository, something went wrong.")
                return ""

            # Check for untracked files
            untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=directory_path).decode('utf-8')
            logger.debug(f"Untracked files: {untracked}")
            
            # Add all files to the index (including new ones)
            subprocess.run(['git', 'add', '-A'], cwd=directory_path, check=True)
            
            # Get the diff
            diff = subprocess.check_output(['git', 'diff', '--cached'], cwd=directory_path).decode('utf-8')
            
            logger.debug(f"Git diff: {diff}")
            return diff
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get git diff: {e}")
            return ""

    def create_git_patch(self, diff: str, directory_path: Path) -> Optional[Path]:
        try:
            # bountybench/setuptools/bounties/bounty_0/patches/patch_1.patch
            os.makedirs(directory_path, exist_ok=True)
            patch_file_path = directory_path / f"patch_{self.patch_id}.patch"
            patch_file_path.write_text(diff)
            logger.info(f"Patch_{self.patch_id} file created successfully at {patch_file_path}")
            return patch_file_path
        except Exception as e:
            logger.error(f"Failed to create git patch_{self.patch_id} file: {e}")
            return None

    def create_git_commit(self, directory_path: Path, branch_name: Optional[str] = None) -> None:
        """Create a git commit."""
        try:
            if branch_name:
                subprocess.check_call(['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")

            # Check if there are any changes to commit
            status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=directory_path).decode('utf-8').strip()
            if not status:
                logger.info(f"No changes to commit in {directory_path}")
                return False

            subprocess.check_call(['git', 'add', '.'], cwd=directory_path)
            subprocess.check_call(['git', 'commit', '-m', f'Commit {self.patch_id}'], cwd=directory_path)
            logger.info(f"Commit {self.patch_id} committed successfully on branch '{branch_name or 'current'}'.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create git commit: {e}")
            return False

    def apply_git_patch(self, patch_file: Path, directory_path: Path, branch_name: Optional[str] = None) -> Tuple[bool, str]:
        try:
            if branch_name:
                subprocess.check_call(['git', 'checkout', branch_name], cwd=directory_path)
                logger.info(f"Checked out to branch '{branch_name}'.")
            
            logger.info(f"Attempting to apply patch: {patch_file}")
            logger.info(f"Current directory: {os.getcwd()}")
            logger.info(f"Patch file exists: {patch_file.exists()}")
            
            subprocess.check_call(['git', 'apply', str(patch_file.resolve())], cwd=directory_path)
            logger.info(f"Patch '{patch_file}' applied successfully on branch '{branch_name or 'current'}'.")
            return True, f"Patch '{patch_file}' applied successfully."
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply patch '{patch_file}': {e}")
            return False, f"Failed to apply patch '{patch_file}': {e}"

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

    def cleanup(self) -> None:
        """Perform cleanup operations."""
        self.store_patch()
        
        if self.codebase and os.path.exists(self.codebase):
            try:
                subprocess.check_call(['git', 'checkout', 'main'], cwd=self.codebase)
                logger.info("Checked out to branch 'main'.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to checkout 'main': {e}")

    def store_patch(self) -> None:
        """Store the patches in a timestamped folder."""
        try:
            timestamp = time.strftime('%Y%m%d-%H%M%S')
            self.new_patch_dir = f"{self.patch_dir}-{timestamp}"
            if self.patch_dir.exists() and self.patch_dir.is_dir():
                if any(self.patch_dir.iterdir()):
                    shutil.move(str(self.patch_dir), self.new_patch_dir)
                    logger.info(f"Patches successfully moved to {self.new_patch_dir}.")
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
            'patch_id': self.patch_id,
            'use_verify_script': self.use_verify_script,
            'agent_id': self.agent_id,
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
        agent._agent_id = data['agent_id']
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
