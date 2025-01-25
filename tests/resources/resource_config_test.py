import os
import unittest
from pathlib import Path

from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.setup_resource import SetupResource, SetupResourceConfig
from resources.utils import read_bounty_metadata, read_repo_metadata
from utils.workflow_logger import workflow_logger


class TestInitFilesResource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize basic configuration
        cls.repo = "lunary"
        cls.bounty_number = "0"
        cls.task_repo_dir = Path(f"bountybench/{cls.repo}").resolve()
        cls.files_dir = "codebase"
        cls.tmp_dir = "tmp"

        # Read metadata
        cls.repo_metadata = read_repo_metadata(str(cls.task_repo_dir))
        cls.bounty_metadata = read_bounty_metadata(
            str(cls.task_repo_dir), cls.bounty_number
        )

        cls.workflow_logger = workflow_logger
        cls.workflow_logger.initialize(
            workflow_name="test_workflow",
            logs_dir="logs",
            task_repo_dir=str(cls.task_repo_dir),
            bounty_number=cls.bounty_number,
        )

    def test_init_files_resource(cls):
        init_files_config = InitFilesResourceConfig(
            task_repo_dir=cls.task_repo_dir,
            files_dir_name=cls.files_dir,
            tmp_dir_name=cls.tmp_dir,
            vulnerable_commit=cls.bounty_metadata["vulnerable_commit"],
        )

        resource = InitFilesResource("test-init", init_files_config)

        assert resource.resource_id == "test-init"
        assert resource.task_repo_dir == os.path.abspath(cls.task_repo_dir)
        assert os.path.exists(resource.tmp_dir)

    def test_setup_resource(cls):

        setup_repo_config = SetupResourceConfig(
            task_level_setup=False,
            task_repo_dir=cls.task_repo_dir,
            files_dir=cls.files_dir,
        )

        setup_task_config = SetupResourceConfig(
            task_level_setup=True,
            task_repo_dir=cls.task_repo_dir,
            files_dir=cls.files_dir,
            bounty_number=cls.bounty_number,
            server_address=cls.repo_metadata["target_host"],
        )

        task_resource_id = cls.repo_metadata["target_host"]

        repo_resource = SetupResource(cls.repo, setup_repo_config)
        task_resource = SetupResource(task_resource_id, setup_task_config)

        assert repo_resource.resource_id == cls.repo
        assert repo_resource.task_level_setup is False
        assert repo_resource.host_name == None
        assert repo_resource.port_number == None

        assert task_resource.resource_id == task_resource_id
        assert task_resource.task_level_setup is True
        assert task_resource.host_name == "lunary-app"
        assert task_resource.port_number == "3333"
