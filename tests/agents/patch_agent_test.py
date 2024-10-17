import os
import shutil
import subprocess
import pytest
from agents.patch_agent.patch_agent import PatchAgent
from resources.init_files_resource import InitFilesResource
from resources.task_server_resource import TaskServerResource
from unittest.mock import MagicMock, patch



def setup_test_repository(repo_path: str):
    """
    Set up a test repository for unit tests.
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

@pytest.fixture
def mock_resources():
    """Creates mock resources."""
    repo_path = "test_repo"
    setup_test_repository(repo_path)
    
    mock_init_files = MagicMock(spec=InitFilesResource)
    mock_init_files.original_files_dir = repo_path

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
        
        # Mock the create_git_branch method to avoid actual git operations
        agent.create_git_branch = MagicMock()
        
        yield agent


def test_get_git_diff(patch_agent):
    """
    Test the get_git_diff method.
    """
    repo_path = patch_agent.init_files.original_files_dir
    print(repo_path)

    # Modify a file in the repository
    
    with open(os.path.join(repo_path, 'test_file.txt'), 'w') as f:
        f.write("Modified content")
    
    # Check if get_git_diff returns the expected output
    diff = patch_agent.get_git_diff()
    #print(diff)
    assert "Modified content" in diff, "Expected to see modified content in the git diff."
    

def test_create_git_patch(patch_agent):
    """
    Test the create_git_patch method.
    """
    repo_path = patch_agent.init_files.original_files_dir
    patch_agent.patch_id = 1

    with open(os.path.join(repo_path, 'test_file.txt'), 'w') as f:
        f.write("Another modification")
    
    diff = patch_agent.get_git_diff()
    patch_agent.create_git_patch(diff)
    
    assert os.path.exists("patch_1.diff"), "Expected patch_1.diff file to be created."
    
    os.remove("patch_1.diff")


def test_create_git_commit(patch_agent):
    """
    Test the create_git_commit method.
    """
    repo_path = patch_agent.init_files.original_files_dir

    patch_agent.patch_id = 1

    # Modify a file in the repository
    with open(os.path.join(repo_path, 'test_file.txt'), 'w') as f:
        f.write("Committed change")
    
    # Create a commit
    patch_agent.create_git_commit()
    
    # Check the log to see if the commit was successful
    log_output = subprocess.check_output(['git', 'log', '--oneline'], cwd=repo_path).decode('utf-8')
    assert "Applied patch_1" in log_output


def teardown_module(module):
    """
    Clean up the test repository after running tests.
    """
    if os.path.exists("test_repo"):
        shutil.rmtree("test_repo")
    if os.path.exists("patch_1.diff"):
        os.remove("patch_1.diff")
