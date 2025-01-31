import os
import unittest
from pathlib import Path

from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.setup_resource import SetupResource, SetupResourceConfig
from resources.utils import read_bounty_metadata, read_repo_metadata


class TestInitFilesResource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize basic configuration
        cls.repo = "lunary"
        cls.bounty_number = "0"
        cls.task_dir = Path(f"bountybench/{cls.repo}").resolve()
        cls.files_dir = "codebase"
        cls.tmp_dir = "tmp"

        # Read metadata
        cls.repo_metadata = read_repo_metadata(str(cls.task_dir))
        cls.bounty_metadata = read_bounty_metadata(str(cls.task_dir), cls.bounty_number)

    def test_init_files_resource(cls):
        init_files_config = InitFilesResourceConfig(
            task_dir=cls.task_dir,
            files_dir_name=cls.files_dir,
            tmp_dir_name=cls.tmp_dir,
            bounty_number=cls.bounty_number,
            vulnerable_commit=cls.bounty_metadata["vulnerable_commit"],
        )

        resource = InitFilesResource("test-init", init_files_config)

        assert resource.resource_id == "test-init"
        assert resource.task_dir == os.path.abspath(cls.task_dir)
        assert os.path.exists(resource.tmp_dir)

    def test_setup_resource(cls):
        setup_repo_config = SetupResourceConfig(
            bounty_level_setup=False,
            task_dir=cls.task_dir,
        )

        repo_resource = SetupResource(cls.repo, setup_repo_config)

        assert repo_resource.resource_id == cls.repo
        assert repo_resource.bounty_level_setup is False
