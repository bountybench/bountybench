import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import pytest

from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from agents.agent_manager import AgentManager
from messages.agent_messages.patch_agent_message import PatchAgentMessage

from tests.agents.agent_test_utils import lunary_bounty_0_setup as bounty_setup, EnvPath, write_to_file_and_make_executable

TEST_FILE_NAME = "test_file.txt"

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

@pytest.fixture(scope="module")
def patch_agent(bounty_setup):
    env_path: EnvPath = bounty_setup
    # Initialize agent
    agent_manager = AgentManager()
    patch_config = PatchAgentConfig(
        bounty_dir=env_path.BOUNTY_DIR_FROM_TASK_DIR,
        task_dir=env_path.TASK_DIR,
        use_verify_script=True,
    )
    agent = agent_manager.create_agent("test_patch_agent", PatchAgent, patch_config)
    verify_script_text = Path(env_path.VERIFY_SCRIPT_DIR).read_text()
    exploit_script_text = Path(env_path.TMP_EXPLOIT_SCRIPT_DIR).read_text()

    # agent's codebase parameter is initialized in the run function so we do it here
    agent.codebase = env_path.TMP_DIR

    mocks = [mock_patch_agent_message(), mock_restart_resource()]
    store_patch_mock = mock_store_patch()

    [mock.start() for mock in mocks]
    store_patch_mock.start() # we don't want this to stop during testing so we don't stop

    yield agent

    [mock.stop() for mock in mocks]

    # revert any commits the tests made in env
    subprocess.run(
        ["git", "reset", "--hard", "origin/main"],
        cwd=env_path.TASK_DIR
    )

@pytest.fixture(scope="module")
def execute_fixture(bounty_setup, patch_agent):
    env_path: EnvPath = bounty_setup

    exploit_script_dir = env_path.TMP_EXPLOIT_SCRIPT_DIR
    exploit_script_dir_path = Path(exploit_script_dir)

    write_to_file_and_make_executable(
        script_path=exploit_script_dir_path,
        exit_code=0,
    )
    yield

@pytest.fixture(scope="module")
def git_fixture(bounty_setup):
    env_path: EnvPath = bounty_setup
    files_to_delete = [
        Path(env_path.CODEBASE_FILES_DIR) / TEST_FILE_NAME,
        Path(env_path.AGENT_PATCHES_DIR) / "patch_1.patch",
    ]
    yield
    # delete files if they exist
    for file in files_to_delete:
        if file.exists():
            file.unlink()
    
    
# probably a temporary test but currently failing due to issues with initializing resources
def test_check_repo_and_bounty_are_different(patch_agent):
    agent = patch_agent
    if hasattr(patch_agent, "bounty_resource") and hasattr(agent, "repo_resource"):
        assert agent.bounty_resource is not agent.repo_resource

def test_run_exploit(bounty_setup, patch_agent):
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    exploit_script_dir = Path(env_path.TMP_EXPLOIT_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=1,
    )
    exploit_result = agent.run_exploit()
    assert exploit_result[1] == 1

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=0,
    )
    exploit_result = agent.run_exploit()
    assert exploit_result[1] == 0

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=2,
    )
    exploit_result = agent.run_exploit()
    assert exploit_result[1] == 2

def test_restart_resource_check(patch_agent):
    """
    If repo_resource fails to restart, error.
    """
    agent = patch_agent
    with patch.object(PatchAgent, "_restart_resource", return_value=False):
        result = agent.execute()
        assert isinstance(result, PatchAgentMessage)
        assert "cannot restart" in result.message.lower()

def test_no_verify_sh_exploit_returns_1(bounty_setup, patch_agent, execute_fixture):
    """
    No verify.sh used. Exploit should return 0 or 1.
    If exploit returns 1 → Patch succeeded.
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    exploit_script_dir = Path(env_path.TMP_EXPLOIT_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=1,
    )
    agent.use_verify_script = False
    result = agent.execute()
    assert isinstance(result, PatchAgentMessage)
    assert "patch succeeded" in result.message.lower()

def test_no_verify_sh_exploit_returns_0(bounty_setup, patch_agent, execute_fixture):
    """
    No verify.sh used. Exploit returns 0 → patch failed.
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    exploit_script_dir = Path(env_path.TMP_EXPLOIT_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=0,
    )
    agent.use_verify_script = False

    # By default exploit_script returns exit 0 (from fixture)
    result = agent.execute()
    assert isinstance(result, PatchAgentMessage)
    assert "patch failed" in result.message.lower()

def test_no_verify_sh_exploit_invalid_exit_code(bounty_setup, patch_agent, execute_fixture):
    """
    No verify.sh used. Exploit must return 0 or 1.
    If it returns something else, we consider that patch failed.
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    exploit_script_dir = Path(env_path.TMP_EXPLOIT_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=2,
    )
    agent.use_verify_script = False

    # If exploit returns code != 0 or 1, we want patch failed scenario.
    # Since code 2 is not what we want, we treat it as exploit succeeded scenario (which means patch failed)
    # or we can assert patch fails. Let's assume we treat any non-(0 or 1) as exploit=0 scenario.
    result = agent.execute()
    # Should result in patch failed
    assert isinstance(result, PatchAgentMessage)
    assert "patch failed" in result.message.lower()

def test_with_verify_sh_success(bounty_setup, patch_agent, execute_fixture):
    """
    Using verify.sh. Exploit can return any exit code or message.
    Success is determined by verify.sh returning 1.
    By default, verify.sh checks if 'Success' in output → exit 1 (success).
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    verify_script_dir = Path(env_path.VERIFY_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=verify_script_dir,
        exit_code=1,
    )
    agent.use_verify_script = True
    result = agent.execute()
    assert isinstance(result, PatchAgentMessage)
    assert "patch succeeded" in result.message.lower()

def test_with_verify_sh_fail(bounty_setup, patch_agent):
    """
    Using verify.sh. If verify.sh returns 0, patch failed.
    No 'Success' in output → verify.sh returns 0.
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    verify_script_dir = Path(env_path.VERIFY_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=verify_script_dir,
        exit_code=0,
    )
    agent.use_verify_script = True
    result = agent.execute()
    assert isinstance(result, PatchAgentMessage)
    assert "patch failed" in result.message.lower()

def test_verify_patch_works_success(bounty_setup, patch_agent):
    # patch works by default but for consistency change it anyway
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    verify_script_dir = Path(env_path.VERIFY_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=verify_script_dir,
        exit_code=1,
    )
    result = agent.verify_patch_works("")
    assert result

def test_verify_patch_works_fail(bounty_setup, patch_agent):
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    verify_script_dir = Path(env_path.VERIFY_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=verify_script_dir,
        exit_code=0,
    )
    result = agent.verify_patch_works("")
    assert not result

def test_verify_patch_works_other(bounty_setup, patch_agent):
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    verify_script_dir = Path(env_path.VERIFY_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=verify_script_dir,
        exit_code=2,
    )
    result = agent.verify_patch_works("")
    assert not result

def test_get_git_diff(bounty_setup, patch_agent, git_fixture):
    """
    Test the get_git_diff method.
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    tmp_repo_path = env_path.TMP_CODEBASE_FILES_DIR

    with open(os.path.join(tmp_repo_path, TEST_FILE_NAME), 'w') as f:
        f.write("Modified content")
    
    diff = agent.get_git_diff(tmp_repo_path)
    assert "Modified content" in diff, "Expected to see modified content in the git diff."
    

def test_create_git_patch(bounty_setup, patch_agent, git_fixture):
    """
    Test the create_git_patch method, ensuring patch is created outside the task repo.
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    agent.patch_id = 1
    tmp_dir = env_path.TMP_DIR
    with open(os.path.join(tmp_dir, TEST_FILE_NAME), 'w') as f:
        f.write("Another modification")
    
    diff = agent.get_git_diff(tmp_dir)
    agent.create_git_patch(diff, agent.patch_dir)
    
    patch_file_path = os.path.join(agent.patch_dir, "patch_1.patch")
    assert os.path.exists(patch_file_path)
    

def test_create_git_commit(bounty_setup, patch_agent, git_fixture):
    """
    Test the create_git_commit method in the tmp repo.
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    agent.patch_id = 1
    tmp_dir = env_path.TMP_DIR

    with open(os.path.join(tmp_dir, TEST_FILE_NAME), 'w') as f:
        f.write("New content for patch")
    
    diff = agent.get_git_diff(tmp_dir)
    
    agent.create_git_patch(diff, agent.patch_dir)
    agent.create_git_commit(tmp_dir)

    log_output = subprocess.check_output(['git', 'log', '--oneline'], cwd=tmp_dir).decode('utf-8')
    print(log_output)
    assert "Commit 1" in log_output, "Expected the commit message to contain the patch id."

    committed_files = subprocess.check_output(['git', 'ls-tree', '--name-only', '-r', 'HEAD'], cwd=tmp_dir).decode('utf-8')
    
    assert TEST_FILE_NAME in committed_files, f"Expected {TEST_FILE_NAME} to be part of the commit."
    
    patch_file_path = os.path.join(agent.patch_dir, f"patch_{agent.patch_id}.patch")
    assert os.path.exists(patch_file_path)

def test_apply_git_patch(bounty_setup, patch_agent, git_fixture):
    """
    Test the apply_git_patch method in the task repo.
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    tmp_repo_path = env_path.TMP_CODEBASE_FILES_DIR
    files_repo_path = env_path.CODEBASE_FILES_DIR
    agent.patch_id = 1

    with open(os.path.join(tmp_repo_path, TEST_FILE_NAME), 'w') as f:
        f.write("test_apply_git_patch")
    
    diff = agent.get_git_diff(tmp_repo_path)
    agent.create_git_patch(diff, agent.patch_dir)
    agent.create_git_commit(tmp_repo_path)

    patch_file = Path(os.path.abspath(os.path.join(agent.patch_dir, f"patch_{agent.patch_id}.patch")))
    subprocess.check_call(['git', 'checkout', 'dev'], cwd=files_repo_path)

    success, message = agent.apply_git_patch(patch_file, files_repo_path, 'dev')

    assert success, message
    assert "test_apply_git_patch" in open(os.path.join(files_repo_path, TEST_FILE_NAME)).read()



if __name__ == '__main__':
    unittest.main()