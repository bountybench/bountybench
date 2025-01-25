import os
import shutil
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from agents.patch_agent.patch_agent import PatchAgent
from resources.init_files_resource import InitFilesResource
from resources.task_server_resource import TaskServerResource


def setup_test_repository(repo_path: str, branch: str = "master"):
    """
    Set up a test repository with an initial commit and optional branch.
    """
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
    os.makedirs(repo_path)

    subprocess.check_call(["git", "init"], cwd=repo_path)
    # Create an initial file
    with open(os.path.join(repo_path, "test_file.txt"), "w") as f:
        f.write("Initial content")
    # Add and commit the initial file
    subprocess.check_call(["git", "add", "."], cwd=repo_path)
    subprocess.check_call(["git", "commit", "-m", "Initial commit"], cwd=repo_path)

    if branch != "master":
        subprocess.check_call(["git", "checkout", "-b", branch], cwd=repo_path)


@pytest.fixture
def mock_resources():
    """Creates mock resources for init_files and task_repo with two different repositories."""
    tmp_repo_path = "tmp_repo"
    task_repo_path = "task_repo"

    # Set up separate repositories for tmp and task_repo
    setup_test_repository(tmp_repo_path)
    setup_test_repository(task_repo_path, branch="dev")

    mock_init_files = MagicMock(spec=InitFilesResource)
    mock_init_files.tmp_files_dir = tmp_repo_path
    mock_init_files.task_repo_dir = task_repo_path

    mock_task_server = MagicMock(spec=TaskServerResource)

    return mock_init_files, mock_task_server


@pytest.fixture
def patch_agent(mock_resources):
    """Initialize the PatchAgent with mock resources."""
    mock_init_files, mock_task_server = mock_resources

    def mock_get_items(resource_type):
        if resource_type == InitFilesResource:
            return [mock_init_files]
        elif resource_type == TaskServerResource:
            return [mock_task_server]
        return []

    with patch("agents.patch_agent.patch_agent.PatchAgent.__init__", return_value=None):
        agent = PatchAgent()
        agent.resource_dict = MagicMock()
        agent.resource_dict.get_items_of_resource_type.side_effect = mock_get_items
        agent.init_files = mock_init_files
        agent.task_server = mock_task_server
        agent.patch_id = 1

        agent.patch_dir = os.path.join(
            os.path.dirname(mock_init_files.task_repo_dir), "patches"
        )
        if not os.path.exists(agent.patch_dir):
            os.makedirs(agent.patch_dir)

        yield agent


def test_get_git_diff(patch_agent):
    """
    Test the get_git_diff method.
    """
    tmp_repo_path = patch_agent.init_files.tmp_files_dir

    with open(os.path.join(tmp_repo_path, "test_file.txt"), "w") as f:
        f.write("Modified content")

    diff = patch_agent.get_git_diff(tmp_repo_path)
    assert (
        "Modified content" in diff
    ), "Expected to see modified content in the git diff."


def test_create_git_patch(patch_agent):
    """
    Test the create_git_patch method, ensuring patch is created outside the task repo.
    """
    tmp_repo_path = patch_agent.init_files.tmp_files_dir
    patch_agent.patch_id = 1
    with open(os.path.join(tmp_repo_path, "test_file.txt"), "w") as f:
        f.write("Another modification")

    diff = patch_agent.get_git_diff(tmp_repo_path)
    patch_agent.create_git_patch(diff, patch_agent.patch_dir)

    patch_file_path = os.path.join(patch_agent.patch_dir, "patch_1.patch")
    assert os.path.exists(patch_file_path)


def test_create_git_commit(patch_agent):
    """
    Test the create_git_commit method in the tmp repo.
    """
    tmp_repo_path = patch_agent.init_files.tmp_files_dir
    patch_agent.patch_id = 1

    with open(os.path.join(tmp_repo_path, "test_file.txt"), "w") as f:
        f.write("New content for patch")

    diff = patch_agent.get_git_diff(tmp_repo_path)

    patch_agent.create_git_patch(diff, patch_agent.patch_dir)
    patch_agent.create_git_commit(tmp_repo_path)

    log_output = subprocess.check_output(
        ["git", "log", "--oneline"], cwd=tmp_repo_path
    ).decode("utf-8")
    print(log_output)
    assert (
        "Commit 1" in log_output
    ), "Expected the commit message to contain the patch id."

    committed_files = subprocess.check_output(
        ["git", "ls-tree", "--name-only", "-r", "HEAD"], cwd=tmp_repo_path
    ).decode("utf-8")

    assert (
        "test_file.txt" in committed_files
    ), "Expected test_file.txt to be part of the commit."

    patch_file_path = os.path.join(
        patch_agent.patch_dir, f"patch_{patch_agent.patch_id}.patch"
    )
    assert os.path.exists(patch_file_path)


def test_apply_git_patch(patch_agent):
    """
    Test the apply_git_patch method in the task repo.
    """
    tmp_repo_path = patch_agent.init_files.tmp_files_dir
    task_repo_path = patch_agent.init_files.task_repo_dir
    patch_agent.patch_id = 1

    with open(os.path.join(tmp_repo_path, "test_file.txt"), "w") as f:
        f.write("Patch content")

    diff = patch_agent.get_git_diff(tmp_repo_path)
    patch_agent.create_git_patch(diff, patch_agent.patch_dir)

    patch_agent.create_git_commit(tmp_repo_path)

    patch_file = os.path.abspath(
        os.path.join(patch_agent.patch_dir, f"patch_{patch_agent.patch_id}.patch")
    )

    subprocess.check_call(["git", "checkout", "dev"], cwd=task_repo_path)
    subprocess.check_call(
        ["git", "checkout", "--", "test_file.txt"], cwd=task_repo_path
    )

    success, message = patch_agent.apply_git_patch(patch_file, task_repo_path, "dev")

    assert success, message
    assert "Patch content" in open(os.path.join(task_repo_path, "test_file.txt")).read()


def teardown_module(module):
    """
    Clean up the test repositories after running tests.
    """
    if os.path.exists("tmp_repo"):
        shutil.rmtree("tmp_repo")
    if os.path.exists("task_repo"):
        shutil.rmtree("task_repo")
    if os.path.exists("patch_dir"):
        shutil.rmtree("patch_dir")
