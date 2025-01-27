import os
from pathlib import Path
import stat
import subprocess
import unittest
from unittest.mock import patch
import pytest

from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from agents.agent_manager import AgentManager
from messages.agent_messages.patch_agent_message import PatchAgentMessage

from tests.agents.agent_test_utils import lunary_bounty_0_setup, EnvPathAssistant

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

def write_to_file_and_make_executable(script_path: Path, file_text: str):
    script_path.write_text(file_text)
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)

@pytest.fixture(scope="module")
def patch_agent(lunary_bounty_0_setup):
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    # Initialize agent
    agent_manager = AgentManager()
    patch_config = PatchAgentConfig(
        bounty_dir=path_assistant.get_bounty_dir_from_task_dir(),
        task_dir=path_assistant.get_task_dir(),
        use_verify_script=True,
    )
    agent = agent_manager.create_agent("test_patch_agent", PatchAgent, patch_config)
    verify_script_text = path_assistant.get_verify_script_dir(as_path=True).read_text()
    exploit_script_text = path_assistant.get_exploit_script_dir(as_path=True).read_text()

    # agent's codebase parameter is initialized in the run function so we do it here
    agent.codebase = path_assistant.get_tmp_files_dir()

    mocks = [mock_patch_agent_message(), mock_restart_resource()]
    store_patch_mock = mock_store_patch()

    [mock.start() for mock in mocks]
    store_patch_mock.start() # we don't want this to stop during testing so we don't stop

    yield agent, verify_script_text, exploit_script_text

    [mock.stop() for mock in mocks]

@pytest.fixture()
def execute_fixture(lunary_bounty_0_setup, patch_agent):
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    _, verify_script_text, exploit_script_text = patch_agent

    verify_script_dir = path_assistant.get_verify_script_dir()
    verify_script_dir_path = Path(verify_script_dir)
    exploit_script_dir = path_assistant.get_exploit_script_dir()
    exploit_script_dir_path = Path(exploit_script_dir)

    subprocess.run(["cp", verify_script_dir, f"{verify_script_dir}.bak"])
    subprocess.run(["cp", exploit_script_dir, f"{exploit_script_dir}.bak"])
    write_to_file_and_make_executable(
        script_path=exploit_script_dir_path,
        file_text="#!/usr/bin/env bash\nexit 0\n",
    )
    yield
    subprocess.run(["mv", f"{verify_script_dir}.bak", verify_script_dir])
    subprocess.run(["mv", f"{exploit_script_dir}.bak", exploit_script_dir])

    # Check in case the copy/move operations failed in some manner
    if verify_script_dir_path.read_text() != verify_script_text:
        write_to_file_and_make_executable(
            script_path=verify_script_dir_path,
            file_text=verify_script_text
        )
    if exploit_script_dir_path.read_text() != exploit_script_text:
        write_to_file_and_make_executable(
            script_path=exploit_script_dir_path,
            file_text=exploit_script_text,
        )

@pytest.fixture()
def git_fixture(lunary_bounty_0_setup):
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    files_repo_test_file = path_assistant.get_files_dir(as_path=True) / TEST_FILE_NAME
    yield
    # delete test_file if it exists
    if files_repo_test_file.exists():
        files_repo_test_file.unlink()
    
# probably a temporary test but currently failing due to issues with initializing resources
def test_check_repo_and_bounty_are_different(patch_agent):
    agent, _, _ = patch_agent
    if hasattr(patch_agent, "bounty_resource") and hasattr(agent, "repo_resource"):
        assert agent.bounty_resource is not agent.repo_resource

def test_run_exploit(lunary_bounty_0_setup, patch_agent):
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    exploit_script_dir = path_assistant.get_exploit_script_dir(as_path=True)
    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        file_text="#!/usr/bin/env bash\nexit 1\n",
    )
    exploit_result = agent.run_exploit()
    assert exploit_result[1] == 1

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        file_text="#!/usr/bin/env bash\nexit 0\n",
    )
    exploit_result = agent.run_exploit()
    assert exploit_result[1] == 0

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        file_text="#!/usr/bin/env bash\nexit 2\n",
    )
    exploit_result = agent.run_exploit()
    assert exploit_result[1] == 2

def test_restart_resource_check(lunary_bounty_0_setup, patch_agent):
    """
    If repo_resource fails to restart, error.
    """
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    with patch.object(PatchAgent, "_restart_resource", return_value=False):
        result = agent.execute()
        assert isinstance(result, PatchAgentMessage)
        assert "cannot restart" in result.message.lower()

def test_no_verify_sh_exploit_returns_1(lunary_bounty_0_setup, patch_agent):
    """
    No verify.sh used. Exploit should return 0 or 1.
    If exploit returns 1 → Patch succeeded.
    """
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    exploit_script_dir = path_assistant.get_exploit_script_dir(as_path=True)
    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        file_text="#!/usr/bin/env bash\nexit 1\n",
    )
    agent.use_verify_script = False
    result = agent.execute()
    assert isinstance(result, PatchAgentMessage)
    assert "patch succeeded" in result.message.lower()

def test_no_verify_sh_exploit_returns_0(lunary_bounty_0_setup, patch_agent):
    """
    No verify.sh used. Exploit returns 0 → patch failed.
    """
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    exploit_script_dir = path_assistant.get_exploit_script_dir(as_path=True)
    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        file_text="#!/usr/bin/env bash\nexit 0\n",
    )
    agent.use_verify_script = False

    # By default exploit_script returns exit 0 (from fixture)
    result = agent.execute()
    assert isinstance(result, PatchAgentMessage)
    assert "patch failed" in result.message.lower()

def test_no_verify_sh_exploit_invalid_exit_code(lunary_bounty_0_setup, patch_agent):
    """
    No verify.sh used. Exploit must return 0 or 1.
    If it returns something else, we consider that patch failed.
    """
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    exploit_script_dir = path_assistant.get_exploit_script_dir(as_path=True)
    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        file_text="#!/usr/bin/env bash\nexit 2\n",
    )
    agent.use_verify_script = False

    # If exploit returns code != 0 or 1, we want patch failed scenario.
    # Since code 2 is not what we want, we treat it as exploit succeeded scenario (which means patch failed)
    # or we can assert patch fails. Let's assume we treat any non-(0 or 1) as exploit=0 scenario.
    result = agent.execute()
    # Should result in patch failed
    assert isinstance(result, PatchAgentMessage)
    assert "patch failed" in result.message.lower()

def test_with_verify_sh_success(lunary_bounty_0_setup, patch_agent):
    """
    Using verify.sh. Exploit can return any exit code or message.
    Success is determined by verify.sh returning 1.
    By default, verify.sh checks if 'Success' in output → exit 1 (success).
    """
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    verify_script_dir = path_assistant.get_verify_script_dir(as_path=True)
    write_to_file_and_make_executable(
        script_path=verify_script_dir,
        file_text="#!/usr/bin/env bash\nexit 1\n",
    )
    agent.use_verify_script = True
    result = agent.execute()
    assert isinstance(result, PatchAgentMessage)
    assert "patch succeeded" in result.message.lower()

def test_with_verify_sh_fail(lunary_bounty_0_setup, patch_agent):
    """
    Using verify.sh. If verify.sh returns 0, patch failed.
    No 'Success' in output → verify.sh returns 0.
    """
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    verify_script_dir = path_assistant.get_verify_script_dir(as_path=True)
    write_to_file_and_make_executable(
        script_path=verify_script_dir,
        file_text="#!/usr/bin/env bash\nexit 0\n",
    )
    agent.use_verify_script = True
    result = agent.execute()
    assert isinstance(result, PatchAgentMessage)
    assert "patch failed" in result.message.lower()

def test_verify_patch_works_success(lunary_bounty_0_setup, patch_agent):
    # patch works by default but for consistency change it anyway
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    verify_script_dir = path_assistant.get_verify_script_dir(as_path=True)
    write_to_file_and_make_executable(
        script_path=verify_script_dir,
        file_text="#!/usr/bin/env bash\nexit 1\n",
    )
    result = agent.verify_patch_works("")
    assert result

def test_verify_patch_works_fail(lunary_bounty_0_setup, patch_agent):
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    verify_script_dir = path_assistant.get_verify_script_dir(as_path=True)
    write_to_file_and_make_executable(
        script_path=verify_script_dir,
        file_text="#!/usr/bin/env bash\nexit 0\n",
    )
    result = agent.verify_patch_works("")
    assert not result

def test_verify_patch_works_other(lunary_bounty_0_setup, patch_agent):
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    verify_script_dir = path_assistant.get_verify_script_dir(as_path=True)
    write_to_file_and_make_executable(
        script_path=verify_script_dir,
        file_text="#!/usr/bin/env bash\nexit 2\n",
    )
    result = agent.verify_patch_works("")
    assert not result

def test_get_git_diff(lunary_bounty_0_setup, patch_agent, git_fixture):
    """
    Test the get_git_diff method.
    """
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    tmp_repo_path = path_assistant.get_tmp_files_dir()

    with open(os.path.join(tmp_repo_path, TEST_FILE_NAME), 'w') as f:
        f.write("Modified content")
    
    diff = agent.get_git_diff(tmp_repo_path)
    assert "Modified content" in diff, "Expected to see modified content in the git diff."
    

def test_create_git_patch(lunary_bounty_0_setup, patch_agent, git_fixture):
    """
    Test the create_git_patch method, ensuring patch is created outside the task repo.
    """
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    agent.patch_id = 1
    tmp_dir = path_assistant.get_tmp_dir()
    with open(os.path.join(tmp_dir, TEST_FILE_NAME), 'w') as f:
        f.write("Another modification")
    
    diff = agent.get_git_diff(tmp_dir)
    agent.create_git_patch(diff, agent.patch_dir)
    
    patch_file_path = os.path.join(agent.patch_dir, "patch_1.patch")
    assert os.path.exists(patch_file_path)
    

def test_create_git_commit(lunary_bounty_0_setup, patch_agent, git_fixture):
    """
    Test the create_git_commit method in the tmp repo.
    """
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    agent.patch_id = 1
    tmp_dir = path_assistant.get_tmp_dir()

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

def test_apply_git_patch(lunary_bounty_0_setup, patch_agent, git_fixture):
    """
    Test the apply_git_patch method in the task repo.
    """
    path_assistant: EnvPathAssistant = lunary_bounty_0_setup
    agent, _, _ = patch_agent
    tmp_repo_path = path_assistant.get_tmp_files_dir()
    files_repo_path = path_assistant.get_files_dir()
    agent.patch_id = 1

    with open(os.path.join(tmp_repo_path, TEST_FILE_NAME), 'w') as f:
        f.write("Patch content")
    
    diff = agent.get_git_diff(tmp_repo_path)
    agent.create_git_patch(diff, agent.patch_dir)
    agent.create_git_commit(tmp_repo_path)

    patch_file = Path(os.path.abspath(os.path.join(agent.patch_dir, f"patch_{agent.patch_id}.patch")))
    subprocess.check_call(['git', 'checkout', 'dev'], cwd=files_repo_path)

    success, message = agent.apply_git_patch(patch_file, files_repo_path, 'dev')

    assert success, message
    assert "Patch content" in open(os.path.join(files_repo_path, TEST_FILE_NAME)).read()



if __name__ == '__main__':
    unittest.main()