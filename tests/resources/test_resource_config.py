from pathlib import Path

import pytest

from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.repo_setup_resource import RepoSetupResource, RepoSetupResourceConfig


# Fixture to set up common test data
@pytest.fixture
def test_config():
    return {
        "repo": "lunary",
        "bounty_number": "0",
        "task_dir": Path("bountytasks/lunary").resolve(),
        "files_dir": "codebase",
        "tmp_dir": Path("bountytasks/lunary/bounties/bounty_0/tmp_1"),
    }


def test_init_files_resource(test_config):
    init_files_config = InitFilesResourceConfig(
        task_dir=test_config["task_dir"],
        files_dir_name=test_config["files_dir"],
        tmp_dir=test_config["tmp_dir"],
        bounty_number=test_config["bounty_number"],
    )
    resource = InitFilesResource("test-init", init_files_config)

    assert resource.resource_id == "test-init"
    assert Path(resource.task_dir) == test_config["task_dir"]
    assert Path(resource.tmp_dir).exists()


def test_setup_resource(test_config):
    setup_repo_config = RepoSetupResourceConfig(
        task_dir=test_config["task_dir"],
    )
    repo_resource = RepoSetupResource(test_config["repo"], setup_repo_config)

    assert repo_resource.resource_id == test_config["repo"]
