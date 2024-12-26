import unittest
from pathlib import Path
from typing import List, Tuple

from agents.executor_agent.executor_agent import ExecutorAgent
from agents.patch_agent.patch_agent import PatchAgent
from phases.base_phase import PhaseConfig
from resources.resource_manager import ResourceManager
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.setup_resource import SetupResource
from utils.workflow_logger import workflow_logger
from resources.utils import read_repo_metadata, read_bounty_metadata

class TestResourceManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = "astropy"
        cls.bounty_number = "0"
        cls.task_repo_dir = Path(f"bountybench/{cls.repo}").resolve()
        cls.files_dir = "codebase"
        cls.tmp_dir = "tmp"

        cls.repo_metadata = read_repo_metadata(str(cls.task_repo_dir))
        cls.bounty_metadata = read_bounty_metadata(str(cls.task_repo_dir), cls.bounty_number)

        cls.workflow_logger = workflow_logger
        cls.workflow_logger.initialize(
            workflow_name="test_workflow",
            logs_dir="logs",
            task_repo_dir=str(cls.task_repo_dir),
            bounty_number=cls.bounty_number
        )

        cls.resource_manager = ResourceManager()
        cls.setup_resources()
        cls.setup_agents()
        cls.setup_phases()
    

    @classmethod
    def setup_resources(cls):
        cls.init_files_resource = InitFilesResource(
            task_repo_dir=cls.task_repo_dir,
            files_dir_name=cls.files_dir,
            tmp_dir_name=cls.tmp_dir,
            exploit_files_dir_name=f"bounties/bounty_{cls.bounty_number}/exploit_files",
            vulnerable_commit=cls.bounty_metadata['vulnerable_commit']
        )
        cls.resource_manager.add_resource(cls.init_files_resource)

        cls.setup_resource = SetupResource(
            task_level_setup=False,
            task_repo_dir=cls.task_repo_dir,
            files_dir=cls.files_dir
        )
        cls.resource_manager.add_resource(cls.setup_resource)

        cls.kali_env_resource = KaliEnvResource(
            "KaliEnv",
            task_repo_dir=cls.task_repo_dir,
            bounty_number=cls.bounty_number,
            volumes={str(cls.task_repo_dir / cls.tmp_dir): {"bind": "/app", "mode": "rw"}}
        )
        cls.resource_manager.add_resource(cls.kali_env_resource)

        cls.docker_resource = DockerResource("DockerHelper")
        cls.resource_manager.add_resource(cls.docker_resource)

    @classmethod
    def setup_agents(cls):
        executor_agent_config = {
            'model': 'openai/o3-mini-2024-12-17',
            'max_output_tokens': 25000,
            'max_input_tokens': 25000,
            'max_iterations': 25,
            'max_iterations_stored_in_memory': 3,
            'use_helm': False
        }

        cls.executor_agent = ExecutorAgent(
            config=executor_agent_config,
            initial_prompt="Test prompt",
            logger=cls.workflow_logger,
            target_host=cls.repo_metadata["target_host"]
        )

        cls.patch_agent = PatchAgent(bounty_dir=str(cls.task_repo_dir / "bounties" / f"bounty_{cls.bounty_number}"))

    @classmethod
    def setup_phases(cls):
        cls.phase_config = PhaseConfig(
            phase_idx=0,
            phase_name="patch",
            max_iterations=25,
            agents=[
                ("executor_agent", cls.executor_agent),
                ("patch_agent", cls.patch_agent)
            ]
        )
        cls.resource_manager.register_phase(cls.phase_config)

    def setUp(self):
        # Clear allocated resources before each test
        self.resource_manager.allocated_resources.clear()

    def test_register_phase(self):
        resources = self.resource_manager.get_all_resources_by_phases()
        self.assertIn("patch", resources)
        expected_resources = {
            "InitFilesResource",
            "SetupResource",
            "KaliEnvResource",
            "DockerResource"
        }
        self.assertEqual(resources["patch"], expected_resources)

    def test_allocate_resources(self):
        self.resource_manager.allocate_resources("patch")
        
        expected_resources = {
            "InitFilesResource",
            "SetupResource",
            "KaliEnvResource",
            "DockerResource"
        }
        
        self.assertEqual(self.resource_manager.allocated_resources, expected_resources)


    def test_release_resources(self):
        self.resource_manager.allocate_resources("patch")
        initial_resource_count = len(self.resource_manager.allocated_resources)
        self.resource_manager.release_resources("patch")
        self.assertEqual(len(self.resource_manager.allocated_resources), 0)

    def test_get_resource(self):
        self.resource_manager.allocate_resources("patch")
        for resource_name in ["InitFilesResource", "SetupResource", "KaliEnvResource", "DockerResource"]:
            resource = self.resource_manager.get_resource(resource_name)
            self.assertIsNotNone(resource)


    def test_multiple_phases(self):
        # Create a second phase with different resource requirements
        phase2_config = PhaseConfig(
            phase_idx=1,
            phase_name="analyze",
            max_iterations=10,
            agents=[("executor_agent", self.executor_agent)]  # This phase only uses ExecutorAgent
        )
        self.resource_manager.register_phase(phase2_config)

        # Allocate resources for the first phase
        self.resource_manager.allocate_resources("patch")
        
        # Allocate resources for the second phase
        self.resource_manager.allocate_resources("analyze")
        
        # Release resources for the first phase
        self.resource_manager.release_resources("patch")
        
        # Check that resources needed by the second phase are still allocated
        self.assertIn("InitFilesResource", self.resource_manager.allocated_resources)
        self.assertIn("SetupResource", self.resource_manager.allocated_resources)
        self.assertIn("KaliEnvResource", self.resource_manager.allocated_resources)
        
        # DockerResource should be released as it's not needed by the second phase
        self.assertNotIn("DockerResource", self.resource_manager.allocated_resources)
        
        # Release resources for the second phase
        self.resource_manager.release_resources("analyze")
        
        # All resources should be released now
        self.assertEqual(len(self.resource_manager.allocated_resources), 0)

if __name__ == '__main__':
    unittest.main()