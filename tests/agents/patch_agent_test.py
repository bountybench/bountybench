import os
from pathlib import Path
import stat
import subprocess
import unittest
from unittest.mock import patch

from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from agents.agent_manager import AgentManager
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from resources.resource_manager import ResourceManager
from resources.docker_resource import DockerResource, DockerResourceConfig
from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.setup_resource import SetupResource, SetupResourceConfig
from resources.utils import read_bounty_metadata
from workflows.utils import setup_shared_network


def mock_patch_agent_message():
    def mock_init(self, agent_id, message, prev, success=None, patch_files_dir=None):
        self._message = message

    return patch.object(PatchAgentMessage, '__init__', mock_init)

def mock_store_patch():
    def mock_s_patch(self):
        return
    return patch.object(PatchAgent, "store_patch", mock_s_patch)

def mock_restart_resource(return_value: bool = True):
    return patch.object(PatchAgent, "_restart_resource", return_value=return_value)

def write_to_file_and_make_executable(script_path: Path, file_text: str):
    script_path.write_text(file_text)
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)

class TestPatchAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Set up the environment once for the entire class. 
        This will run before any tests in the class.
        """
        # Set up the test environment - using lunary as an environment
        repo = "lunary"
        bounty_number = "0"

        files_dir_name = "codebase"
        tmp_dir_name = "tmp"
        exploit_files_dir_name = "exploit_files"

        task_dir = os.path.join("bountybench", repo)
        bounty_dir = os.path.join("bounties", "bounty_0")
        exploit_script_name, verify_script_name = "exploit.sh", "verify.sh"

        setup_shared_network()
        bounty_metadata = read_bounty_metadata(str(task_dir), bounty_number)
        vulnerable_commit = bounty_metadata['vulnerable_commit']


        print(f"task_dir: {task_dir}")
        print(f"files_dir_name: {files_dir_name}")
        print(f"tmp_dir_name: {tmp_dir_name}")

        task_dir = os.path.abspath(task_dir)
        tmp_dir = os.path.join(task_dir, tmp_dir_name)

        # Configurations
        init_config = InitFilesResourceConfig(
            task_dir=task_dir,
            files_dir_name=files_dir_name,
            tmp_dir_name=tmp_dir_name,
            bounty_number=bounty_number,
            exploit_files_dir_name=exploit_files_dir_name,
            vulnerable_commit=vulnerable_commit,
        )
        setup_config = SetupResourceConfig(
            bounty_level_setup=False,
            task_dir=task_dir,
            bounty_number=bounty_number
        )
        docker_config = DockerResourceConfig()
        patch_config = PatchAgentConfig(
            bounty_dir=bounty_dir,
            task_dir=task_dir,
            use_verify_script=True,
        )
        
        # Initialize resources and agent
        resource_manager = ResourceManager()
        agent_manager = AgentManager()

        resource_manager.register_resource("init_files", InitFilesResource, init_config)
        resource_manager.register_resource("repo_resource", SetupResource, setup_config)
        resource_manager.register_resource("docker", DockerResource, docker_config)
        resource_manager.initialize_phase_resources(0, ["init_files", "repo_resource", "docker"])

        # Make class variables for access later in setUp
        cls.agent = agent_manager.create_agent("test_patch_agent", PatchAgent, patch_config)
        cls.bounty_number = bounty_number
        cls.task_dir = task_dir
        cls.tmp_dir = tmp_dir
        cls.verify_script_dir = Path(task_dir) / bounty_dir / verify_script_name
        cls.exploit_script_dir = Path(tmp_dir) / exploit_script_name

        cls.verify_script_text = cls.verify_script_dir.read_text()
        cls.exploit_script_text = cls.exploit_script_dir.read_text()

        # These mocks are enabled for every test in this file
        cls.mocks = [mock_patch_agent_message(), mock_store_patch(), mock_restart_resource()]
        [mock.start() for mock in cls.mocks]
    
    def setUp(self):
        # Assign class-level variables to instance variables (self)
        self.agent: PatchAgent = self.__class__.agent
        self.bounty_number = self.__class__.bounty_number
        self.task_dir = self.__class__.task_dir
        self.tmp_dir = self.__class__.tmp_dir
        self.verify_script_dir = self.__class__.verify_script_dir
        self.exploit_script_dir = self.__class__.exploit_script_dir

        self.test_file_name = "test_file.txt"

        # codebase is initialized in the run function so we do it here
        self.agent.codebase = os.path.join(self.agent.init_files.tmp_dir, self.agent.init_files.files_dir_name)

        # Create backup of verify and exploit script to restore after tests
        self.verify_script_text = self.__class__.verify_script_text
        self.exploit_script_text = self.__class__.exploit_script_text
        subprocess.run(["cp", str(self.verify_script_dir), f"{str(self.verify_script_dir)}.bak"])
        subprocess.run(["cp", str(self.exploit_script_dir), f"{str(self.exploit_script_dir)}.bak"])
        write_to_file_and_make_executable(
            script_path=self.exploit_script_dir,
            file_text="#!/usr/bin/env bash\nexit 0\n",
        )

    def tearDown(self):
        # Clean up: remove the temporary exploit files from the Kali container
        subprocess.run(["mv", str(f"{str(self.verify_script_dir)}.bak"), str(self.verify_script_dir)])
        subprocess.run(["mv", str(f"{str(self.exploit_script_dir)}.bak"), str(self.exploit_script_dir)])

        # Check in case the copy/move operations failed in some manner
        if self.verify_script_dir.read_text() != self.verify_script_text:
            write_to_file_and_make_executable(
                script_path=self.verify_script_dir,
                file_text=self.verify_script_text
            )
        if self.exploit_script_dir.read_text() != self.exploit_script_text:
            write_to_file_and_make_executable(
                script_path=self.exploit_script_dir,
                file_text=self.exploit_script_text,
            )

        # delete test_file if it exists
        files_repo_test_file = Path(os.path.join(self.agent.init_files.files_dir)) / self.test_file_name
        if files_repo_test_file.exists():
            files_repo_test_file.unlink()
    
    def test_check_repo_and_bounty_are_different(self):
        if hasattr(self.agent, "bounty_resource") and hasattr(self.agent, "repo_resource"):
            self.assertIsNot(self.agent.bounty_resource, self.agent.repo_resource)
    
    def test_run_exploit(self):
        write_to_file_and_make_executable(
            script_path=self.exploit_script_dir,
            file_text="#!/usr/bin/env bash\nexit 1\n",
        )
        exploit_result = self.agent.run_exploit()
        self.assertEquals(exploit_result[1], 1)

        write_to_file_and_make_executable(
            script_path=self.exploit_script_dir,
            file_text="#!/usr/bin/env bash\nexit 0\n",
        )
        exploit_result = self.agent.run_exploit()
        self.assertEquals(exploit_result[1], 0)

        write_to_file_and_make_executable(
            script_path=self.exploit_script_dir,
            file_text="#!/usr/bin/env bash\nexit 2\n",
        )
        exploit_result = self.agent.run_exploit()
        self.assertEquals(exploit_result[1], 2)

    def test_restart_resource_check(self):
        """
        If repo_resource fails to restart, error.
        """
        with patch.object(PatchAgent, "_restart_resource", return_value=False):
            result = self.agent.execute()
            self.assertIsInstance(result, PatchAgentMessage)
            self.assertIn("cannot restart", result.message.lower())

    def test_no_verify_sh_exploit_returns_1(self):
        """
        No verify.sh used. Exploit should return 0 or 1.
        If exploit returns 1 → Patch succeeded.
        """
        write_to_file_and_make_executable(
            script_path=self.exploit_script_dir,
            file_text="#!/usr/bin/env bash\nexit 1\n",
        )
        self.agent.use_verify_script = False
        result = self.agent.execute()
        self.assertIsInstance(result, PatchAgentMessage)
        self.assertIn("patch succeeded", result.message.lower())

    def test_no_verify_sh_exploit_returns_0(self):
        """
        No verify.sh used. Exploit returns 0 → patch failed.
        """
        write_to_file_and_make_executable(
            script_path=self.exploit_script_dir,
            file_text="#!/usr/bin/env bash\nexit 0\n",
        )
        self.agent.use_verify_script = False

        # By default exploit_script returns exit 0 (from fixture)
        result = self.agent.execute()
        self.assertIsInstance(result, PatchAgentMessage)
        self.assertIn("patch failed", result.message.lower())

    def test_no_verify_sh_exploit_invalid_exit_code(self):
        """
        No verify.sh used. Exploit must return 0 or 1.
        If it returns something else, we consider that patch failed.
        """
        write_to_file_and_make_executable(
            script_path=self.exploit_script_dir,
            file_text="#!/usr/bin/env bash\nexit 2\n",
        )
        self.agent.use_verify_script = False

        # If exploit returns code != 0 or 1, we want patch failed scenario.
        # Since code 2 is not what we want, we treat it as exploit succeeded scenario (which means patch failed)
        # or we can assert patch fails. Let's assume we treat any non-(0 or 1) as exploit=0 scenario.
        result = self.agent.execute()
        # Should result in patch failed
        self.assertIsInstance(result, PatchAgentMessage)
        self.assertIn("patch failed", result.message.lower())

    def test_with_verify_sh_success(self):
        """
        Using verify.sh. Exploit can return any exit code or message.
        Success is determined by verify.sh returning 1.
        By default, verify.sh checks if 'Success' in output → exit 1 (success).
        """
        write_to_file_and_make_executable(
            script_path=self.verify_script_dir,
            file_text="#!/usr/bin/env bash\nexit 1\n",
        )
        self.agent.use_verify_script = True
        result = self.agent.execute()
        self.assertIsInstance(result, PatchAgentMessage)
        self.assertIn("patch succeeded", result.message.lower())

    def test_with_verify_sh_fail(self):
        """
        Using verify.sh. If verify.sh returns 0, patch failed.
        No 'Success' in output → verify.sh returns 0.
        """
        write_to_file_and_make_executable(
            script_path=self.verify_script_dir,
            file_text="#!/usr/bin/env bash\nexit 0\n",
        )
        self.agent.use_verify_script = True
        result = self.agent.execute()
        self.assertIsInstance(result, PatchAgentMessage)
        self.assertIn("patch failed", result.message.lower())

    def test_verify_patch_works_success(self):
        # patch works by default but for consistency change it anyway
        write_to_file_and_make_executable(
            script_path=self.verify_script_dir,
            file_text="#!/usr/bin/env bash\nexit 1\n",
        )
        result = self.agent.verify_patch_works("")
        self.assertTrue(result)

    def test_verify_patch_works_fail(self):
        write_to_file_and_make_executable(
            script_path=self.verify_script_dir,
            file_text="#!/usr/bin/env bash\nexit 0\n",
        )
        result = self.agent.verify_patch_works("")
        self.assertFalse(result)

    def test_verify_patch_works_other(self):
        write_to_file_and_make_executable(
            script_path=self.verify_script_dir,
            file_text="#!/usr/bin/env bash\nexit 2\n",
        )
        result = self.agent.verify_patch_works("")
        self.assertFalse(result)

    def test_get_git_diff(self):
        """
        Test the get_git_diff method.
        """
        tmp_repo_path = os.path.join(self.agent.init_files.tmp_dir, self.agent.init_files.files_dir_name)

        with open(os.path.join(tmp_repo_path, self.test_file_name), 'w') as f:
            f.write("Modified content")
        
        diff = self.agent.get_git_diff(tmp_repo_path)
        self.assertIn("Modified content", diff, "Expected to see modified content in the git diff.")
        

    def test_create_git_patch(self):
        """
        Test the create_git_patch method, ensuring patch is created outside the task repo.
        """
        self.agent.patch_id = 1
        with open(os.path.join(self.tmp_dir, self.test_file_name), 'w') as f:
            f.write("Another modification")
        
        diff = self.agent.get_git_diff(self.tmp_dir)
        self.agent.create_git_patch(diff, self.agent.patch_dir)
        
        patch_file_path = os.path.join(self.agent.patch_dir, "patch_1.patch")
        self.assertTrue(os.path.exists(patch_file_path))
        

    def test_create_git_commit(self):
        """
        Test the create_git_commit method in the tmp repo.
        """
        self.agent.patch_id = 1

        with open(os.path.join(self.tmp_dir, self.test_file_name), 'w') as f:
            f.write("New content for patch")
        
        diff = self.agent.get_git_diff(self.tmp_dir)
        
        self.agent.create_git_patch(diff, self.agent.patch_dir)
        self.agent.create_git_commit(self.tmp_dir)

        log_output = subprocess.check_output(['git', 'log', '--oneline'], cwd=self.tmp_dir).decode('utf-8')
        print(log_output)
        self.assertIn("Commit 1", log_output, "Expected the commit message to contain the patch id.")

        committed_files = subprocess.check_output(['git', 'ls-tree', '--name-only', '-r', 'HEAD'], cwd=self.tmp_dir).decode('utf-8')
        
        self.assertIn(self.test_file_name, committed_files, f"Expected {self.test_file_name} to be part of the commit.")
        
        patch_file_path = os.path.join(self.agent.patch_dir, f"patch_{self.agent.patch_id}.patch")
        self.assertTrue(os.path.exists(patch_file_path))

    def test_apply_git_patch(self):
        """
        Test the apply_git_patch method in the task repo.
        """
        tmp_repo_path = os.path.join(self.agent.init_files.tmp_dir, self.agent.init_files.files_dir_name)
        files_repo_path = os.path.join(self.agent.init_files.files_dir)
        self.agent.patch_id = 1

        with open(os.path.join(tmp_repo_path, self.test_file_name), 'w') as f:
            f.write("Patch content")
        
        diff = self.agent.get_git_diff(tmp_repo_path)
        self.agent.create_git_patch(diff, self.agent.patch_dir)
        self.agent.create_git_commit(tmp_repo_path)

        patch_file = Path(os.path.abspath(os.path.join(self.agent.patch_dir, f"patch_{self.agent.patch_id}.patch")))
        subprocess.check_call(['git', 'checkout', 'dev'], cwd=files_repo_path)

        success, message = self.agent.apply_git_patch(patch_file, files_repo_path, 'dev')

        self.assertTrue(success, message)
        self.assertIn("Patch content", open(os.path.join(files_repo_path, self.test_file_name)).read())



if __name__ == '__main__':
    unittest.main()