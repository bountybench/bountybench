import os
import shutil
import subprocess
import pytest
from agents.patch_agent.patch_agent import PatchAgent
from resources.init_files_resource import InitFilesResource
from resources.task_server_resource import TaskServerResource
from unittest.mock import MagicMock, patch

def setup_test_repository(repo_path: str, branch: str = 'master'):
    """
    Set up a test repository with an initial commit and optional branch.
    """
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
    os.makedirs(repo_path)
    
    subprocess.check_call(['git', 'init'], cwd=repo_path)
    # Create an initial file
    with open(os.path.join(repo_path, 'test_file.txt'), 'w') as f:
        f.write("Initial content")
    # Add and commit the initial file
    subprocess.check_call(['git', 'add', '.'], cwd=repo_path)
    subprocess.check_call(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path)
    
    if branch != 'master':
        subprocess.check_call(['git', 'checkout', '-b', branch], cwd=repo_path)

@pytest.fixture
def mock_resources():
    """Creates mock resources for init_files and task_repo with two different repositories."""
    tmp_repo_path = "tmp_repo"
    task_repo_path = "task_repo"
    
    # Set up separate repositories for tmp and task_repo
    setup_test_repository(tmp_repo_path)
    setup_test_repository(task_repo_path, branch='dev')
    
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

    with patch('agents.patch_agent.patch_agent.PatchAgent.__init__', return_value=None):
        agent = PatchAgent()
        agent.resource_dict = MagicMock()
        agent.resource_dict.get_items_of_resource_type.side_effect = mock_get_items
        agent.init_files = mock_init_files
        agent.task_server = mock_task_server
        agent.patch_id = 1

        yield agent

def test_get_git_diff(patch_agent):
    """
    Test the get_git_diff method.
    """
    tmp_repo_path = patch_agent.init_files.tmp_files_dir

    # Modify a file in the tmp repository
    with open(os.path.join(tmp_repo_path, 'test_file.txt'), 'w') as f:
        f.write("Modified content")
    
    # Check if get_git_diff returns the expected output
    diff = patch_agent.get_git_diff(tmp_repo_path)
    assert "Modified content" in diff, "Expected to see modified content in the git diff."
    

def test_create_git_patch(patch_agent):
    """
    Test the create_git_patch method in the tmp repo.
    """
    tmp_repo_path = patch_agent.init_files.tmp_files_dir
    patch_agent.patch_id = 1

    with open(os.path.join(tmp_repo_path, 'test_file.txt'), 'w') as f:
        f.write("Another modification")
    
    diff = patch_agent.get_git_diff(tmp_repo_path)
    patch_agent.create_git_patch(diff, tmp_repo_path)
    
    patch_file_path = os.path.join(tmp_repo_path, "patch_1.patch")
    assert os.path.exists(patch_file_path), "Expected the patch file to be created in the tmp repo."
    

def test_create_git_commit(patch_agent):
    """
    Test the create_git_commit method in the tmp repo.
    """
    tmp_repo_path = patch_agent.init_files.tmp_files_dir
    patch_agent.patch_id = 1

    with open(os.path.join(tmp_repo_path, 'test_file.txt'), 'w') as f:
        f.write("New content for patch")

    diff = patch_agent.get_git_diff(tmp_repo_path)
    patch_agent.create_git_patch(diff, tmp_repo_path)
    
    patch_agent.create_git_commit(tmp_repo_path)

    log_output = subprocess.check_output(['git', 'log', '--oneline'], cwd=tmp_repo_path).decode('utf-8')
    assert "Applied patch_1" in log_output, "Expected the commit message to contain the patch id."
    
    committed_files = subprocess.check_output(['git', 'ls-tree', '--name-only', '-r', 'HEAD'], cwd=tmp_repo_path).decode('utf-8')
    assert f"patch_1.patch" in committed_files, "Expected the patch file to be part of the commit."

def test_copy_patch(patch_agent):
    """
    Test the copy_patch method to ensure the patch is copied from tmp_repo to task_repo.
    """
    tmp_repo_path = patch_agent.init_files.tmp_files_dir
    task_repo_path = patch_agent.init_files.task_repo_dir
    patch_agent.patch_id = 1

    with open(os.path.join(tmp_repo_path, 'test_file.txt'), 'w') as f:
        f.write("Patch content for copy")
    diff = patch_agent.get_git_diff(tmp_repo_path)
    patch_agent.create_git_patch(diff, tmp_repo_path)
    
    tmp_patch_path = os.path.join(tmp_repo_path, f"patch_{patch_agent.patch_id}.patch")
    task_repo_patch_path = os.path.join(task_repo_path, f"patch_{patch_agent.patch_id}.patch")

    patch_agent.copy_patch(tmp_patch_path, task_repo_patch_path)

    assert os.path.exists(task_repo_patch_path), f"Patch file should exist in the task repo at {task_repo_patch_path}."

    with open(tmp_patch_path, 'r') as tmp_patch_file, open(task_repo_patch_path, 'r') as task_repo_patch_file:
        tmp_patch_content = tmp_patch_file.read()
        task_repo_patch_content = task_repo_patch_file.read()
        assert tmp_patch_content == task_repo_patch_content

def test_apply_git_patch(patch_agent):
    """
    Test the apply_git_patch method in the task repo.
    """
    tmp_repo_path = patch_agent.init_files.tmp_files_dir
    task_repo_path = patch_agent.init_files.task_repo_dir
    patch_agent.patch_id = 1

    with open(os.path.join(tmp_repo_path, 'test_file.txt'), 'w') as f:
        f.write("Patch content")
    diff = patch_agent.get_git_diff(tmp_repo_path)
    patch_agent.create_git_patch(diff, tmp_repo_path)

    patch_agent.create_git_commit(tmp_repo_path)

    tmp_dir_patch = os.path.abspath(os.path.join(tmp_repo_path, f"patch_{patch_agent.patch_id}.patch"))
    task_repo_patch = os.path.abspath(os.path.join(task_repo_path, f"patch_{patch_agent.patch_id}.patch"))
    
    patch_agent.copy_patch(tmp_dir_patch, task_repo_patch)


    subprocess.check_call(['git', 'checkout', 'dev'], cwd=task_repo_path)
    subprocess.check_call(['git', 'checkout', '--', 'test_file.txt'], cwd=task_repo_path)
    success, message = patch_agent.apply_git_patch(f"patch_1.patch", task_repo_path, 'dev')
    
    assert success, message
    assert "Patch content" in open(os.path.join(task_repo_path, 'test_file.txt')).read()
    

def test_cleanup(patch_agent):
    """
    Test the cleanup method, ensuring that the dev branch is deleted and tmp is cleaned.
    """
    task_repo_path = patch_agent.init_files.task_repo_dir
    patch_agent.patch_id = 1

    subprocess.check_call(['git', 'checkout', 'dev'], cwd=task_repo_path)
    subprocess.check_call(['git', 'branch'], cwd=task_repo_path)

    before_clean_branches = subprocess.check_output(['git', 'branch'], cwd=task_repo_path).decode('utf-8')
    assert "dev" in before_clean_branches, "Dev branch should exist before cleanup."

    # Call cleanup
    patch_agent.cleanup()

    after_clean_branches = subprocess.check_output(['git', 'branch'], cwd=task_repo_path).decode('utf-8')
    assert "dev" not in after_clean_branches, "Dev branch should be deleted after cleanup."

    assert not os.path.exists(patch_agent.init_files.tmp_files_dir), "Tmp directory should be deleted after cleanup."


def teardown_module(module):
    """
    Clean up the test repositories after running tests.
    """
    if os.path.exists("tmp_repo"):
        shutil.rmtree("tmp_repo")
    if os.path.exists("task_repo"):
        shutil.rmtree("task_repo")
