import unittest
from pathlib import Path
from typing import List, Tuple

from agents.executor_agent.executor_agent import ExecutorAgent
from agents.patch_agent.patch_agent import PatchAgent
from phases.base_phase import PhaseConfig
from resources.resource_manager import ResourceConfig, ResourceManager
from resources.docker_resource import DockerResource
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.setup_resource import SetupResource
from utils.workflow_logger import workflow_logger
from resources.utils import read_repo_metadata, read_bounty_metadata
from resources.resource_dict import resource_dict


class TestResourceManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize basic configuration
        cls.repo = "astropy"
        cls.bounty_number = "0"
        cls.task_repo_dir = Path(f"bountybench/{cls.repo}").resolve()
        cls.files_dir = "codebase"
        cls.tmp_dir = "tmp"

        # Read metadata
        cls.repo_metadata = read_repo_metadata(str(cls.task_repo_dir))
        cls.bounty_metadata = read_bounty_metadata(str(cls.task_repo_dir), cls.bounty_number)

        # Initialize logger
        cls.workflow_logger = workflow_logger
        cls.workflow_logger.initialize(
            workflow_name="test_workflow",
            logs_dir="logs",
            task_repo_dir=str(cls.task_repo_dir),
            bounty_number=cls.bounty_number
        )

        # Initialize resource manager and register configs
        cls.resource_manager = ResourceManager()
        cls.register_resource_configs()
        
        # Setup in correct order
        cls.setup_agents()  # Create agents first
        cls.setup_phases()  # Then register phases with existing agents

    @classmethod
    def register_resource_configs(cls):
        """Register resource configurations without creating resources"""
        # Init Files Resource Config
        init_files_config = ResourceConfig(
            resource_type=InitFilesResource,
            config_params={
                "task_repo_dir": cls.task_repo_dir,
                "files_dir_name": cls.files_dir,
                "tmp_dir_name": cls.tmp_dir,
                "exploit_files_dir_name": f"bounties/bounty_{cls.bounty_number}/exploit_files",
                "vulnerable_commit": cls.bounty_metadata['vulnerable_commit']
            }
        )
        cls.resource_manager.register_resource_config(init_files_config)

        # Setup Resource Config
        setup_config = ResourceConfig(
            resource_type=SetupResource,
            config_params={
                "task_level_setup": False,
                "task_repo_dir": cls.task_repo_dir,
                "files_dir": cls.files_dir
            }
        )
        cls.resource_manager.register_resource_config(setup_config)

        # Setup Resource Config for task_server
        setup_task_config = ResourceConfig(
            resource_type=SetupResource,
            config_params={
                "task_level_setup": True,
                "task_repo_dir": cls.task_repo_dir,
                "files_dir": cls.files_dir,
                "bounty_number": cls.bounty_number,
                "server_address": cls.repo_metadata.get("target_host", "")
            },
            identifier="task_server"
        )
        cls.resource_manager.register_resource_config(setup_task_config)

        # Kali Env Resource Config
        kali_config = ResourceConfig(
            resource_type=KaliEnvResource,
            config_params={
                "name": "KaliEnv",
                "task_repo_dir": cls.task_repo_dir,
                "bounty_number": cls.bounty_number,
                "volumes": {str(cls.task_repo_dir / cls.tmp_dir): {"bind": "/app", "mode": "rw"}}
            }
        )
        cls.resource_manager.register_resource_config(kali_config)

        # Docker Resource Config
        docker_config = ResourceConfig(
            resource_type=DockerResource,
            config_params={"name": "DockerHelper"}
        )
        cls.resource_manager.register_resource_config(docker_config)

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

        # Create the agents with resource manager
        cls.executor_agent = ExecutorAgent(
            config=executor_agent_config,
            initial_prompt="Test prompt",
            logger=cls.workflow_logger,
            target_host=cls.repo_metadata["target_host"],
            resource_manager=cls.resource_manager  # Pass resource manager
        )

        cls.patch_agent = PatchAgent(
            bounty_dir=str(cls.task_repo_dir / "bounties" / f"bounty_{cls.bounty_number}"),
            resource_manager=cls.resource_manager  # Pass resource manager
        )
    @classmethod
    def setup_phases(cls):
        # Create phase configuration
        cls.phase_config = PhaseConfig(
            phase_idx=0,
            phase_name="patch",
            max_iterations=25,
            agents=[
                ("executor_agent", cls.executor_agent),
                ("patch_agent", cls.patch_agent)
            ]
        )
        # Register phase with resource manager
        cls.resource_manager.register_phase(cls.phase_config)

    def setUp(self):
        # Clear resources between tests
        self.resource_manager.allocated_resources.clear()
        self.resource_manager.resources.clear()
        # Clear resource_dict
        for resource_type in [InitFilesResource, SetupResource, KaliEnvResource, DockerResource]:
            self.resource_manager.resource_dict.delete_items_of_resource_type(resource_type)

    def test_phase_based_resource_creation(self):
        # Initially no resources should be created
        self.assertEqual(len(self.resource_manager.resources), 0)
        self.assertEqual(len(self.resource_manager.allocated_resources), 0)

        # Allocate resources for patch phase
        self.resource_manager.allocate_resources("patch")
        
        # Check that patch phase resources were created
        # Include all required resources and configured optional resources
        expected_resources = {
            "InitFilesResource",
            "SetupResource",
            "KaliEnvResource",
            "DockerResource",
            "SetupResource_task_server"  # This is configured in register_resource_configs
        }
        self.assertEqual(self.resource_manager.allocated_resources, expected_resources)

        # Create analyze phase with different resource requirements
        analyze_phase = PhaseConfig(
            phase_idx=1,
            phase_name="analyze",
            max_iterations=10,
            agents=[("executor_agent", self.executor_agent)]
        )
        self.resource_manager.register_phase(analyze_phase)
        
        # Release patch phase resources
        self.resource_manager.release_resources("patch")
        
        # Allocate analyze phase resources
        self.resource_manager.allocate_resources("analyze")
        
        # Verify only required resources for analyze phase exist
        expected_analyze_resources = {
            "InitFilesResource",
            "SetupResource",
            "KaliEnvResource"
        }
        self.assertEqual(self.resource_manager.allocated_resources, expected_analyze_resources)


    def test_get_resource(self):
        self.resource_manager.allocate_resources("patch")
        
        # Test getting resources by type
        init_files = self.resource_manager.get_resource(InitFilesResource)
        self.assertIsInstance(init_files, InitFilesResource)
        
        # Test getting resources with identifier
        setup_task = self.resource_manager.get_resource((SetupResource, "task_server"))
        self.assertIsInstance(setup_task, SetupResource)
        
    def test_register_phase(self):
        resources = self.resource_manager.get_all_resources_by_phases()
        self.assertIn("patch", resources)
        expected_resources = {
            "InitFilesResource",
            "SetupResource",
            "KaliEnvResource",
            "DockerResource",
            "SetupResource_task_server"  # Include configured optional resources
        }
        self.assertEqual(resources["patch"], expected_resources)

if __name__ == '__main__':
    unittest.main()