import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.agent_manager import AgentManager
from agents.detect_agent.detect_agent import (
    SETUP_FILES_DIR,
    DetectAgent,
    DetectAgentConfig,
)
from messages.agent_messages.detect_agent_message import DetectAgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from tests.test_utils.bounty_setup_test_util import EnvPath
from tests.test_utils.bounty_setup_test_util import (
    lunary_bounty_0_setup as bounty_setup,
)
from tests.test_utils.bounty_setup_test_util import write_to_file_and_make_executable
from utils.file_utils import apply_patch_to_bounty


def mock_detect_agent_message():
    def mock_init(self, agent_id, message, prev, success=None):
        self._message = message

    return patch.object(DetectAgentMessage, "__init__", mock_init)


@pytest.fixture(scope="module")
def detect_agent(bounty_setup):
    env_path: EnvPath = bounty_setup
    # Initialize agent

    agent_manager = AgentManager(workflow_id="1")
    detect_config = DetectAgentConfig(
        bounty_dir=env_path.BOUNTY_DIR,
        task_dir=env_path.TASK_DIR,
        tmp_dir=env_path.TMP_DIR,
        submit=False,
    )
    agent = agent_manager.create_agent("test_detect_agent", DetectAgent, detect_config)

    mocks = [patch.object(DetectAgent, "_restart_resource", return_value=True)]

    [mock.start() for mock in mocks]

    yield agent

    [mock.stop() for mock in mocks]

    # revert any commits the tests made in env
    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=env_path.TASK_DIR)


@pytest.fixture(scope="module")
def execute_fixture(bounty_setup, detect_agent):
    env_path: EnvPath = bounty_setup

    env_path.TMP_DIR.mkdir(parents=True, exist_ok=True)
    exploit_script_dir = env_path.TMP_EXPLOIT_SCRIPT_DIR

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=0,
    )
    yield


@pytest.mark.asyncio
async def test_run_agent_exploit(bounty_setup, detect_agent):
    env_path: EnvPath = bounty_setup
    agent = detect_agent

    # Create a message
    detect_message = DetectAgentMessage(agent_id="test", message="test")

    # Set up an async mock for run_exploit
    mock_action_message = MagicMock()
    mock_action_message.additional_metadata = {"exit_code": 1}
    mock_action_message.message = "exploit output"

    # Need an async mock that can be awaited
    async def mock_run_exploit():
        return mock_action_message

    # Patch the run_exploit method
    with patch.object(agent, "run_exploit", mock_run_exploit):
        # Set up restart_resources to avoid side effects
        mocker = MagicMock()
        mocker.patch.object(agent, "restart_resources", return_value=True)

        # Test exploit failure
        mock_action_message.additional_metadata = {"exit_code": 1}
        exit_code = await agent.run_agent_exploit(detect_message)
        assert exit_code == 1

        # Test exploit success
        mock_action_message.additional_metadata = {"exit_code": 0}
        exit_code = await agent.run_agent_exploit(detect_message)
        assert exit_code == 0


def test_restart_resource_check(detect_agent, mocker):
    """
    Test that restart_resources returns False when _restart_resource returns False
    """
    agent = detect_agent

    # Mock _restart_resource to return False instead of raising an exception
    mocker.patch.object(detect_agent, "_restart_resource", return_value=False)

    # Call the method
    success = agent.restart_resources()

    # Verify the result
    assert not success


@pytest.mark.asyncio
async def test_skip_no_exploit(detect_agent, mocker):
    """Test that the agent skips if no exploit.sh exists"""
    agent = detect_agent

    # Mock that exploit.sh doesn't exist
    mocker.patch.object(Path, "exists", return_value=False)
    with patch("agents.detect_agent.detect_agent.git_has_changes", return_value=True):
        # Run the agent
        init_msg = ExecutorAgentMessage(
            agent_id="executor", message="test", submission=False
        )
        final_msg = await agent.run([init_msg])

        # Verify the result
        assert "No exploit.sh found." in final_msg.message


@pytest.mark.asyncio
async def test_no_changes_detected(detect_agent, mocker):
    """Test that the agent skips if no changes to exploit files detected"""
    agent = detect_agent

    # Mock that exploit.sh exists but no git changes
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("agents.detect_agent.detect_agent.git_has_changes", return_value=False)

    # Run the agent
    init_msg = ExecutorAgentMessage(
        agent_id="executor", message="test", submission=False
    )
    final_msg = await agent.run([init_msg])

    # Verify the result
    assert "No file changes detected" in final_msg.message


@pytest.mark.asyncio
async def test_waiting_for_submission(detect_agent, mocker):
    """Test that when submit=True but prev_agent_message.submission=False, we get 'Waiting for the submission...'"""
    # Override submit flag on existing agent
    mocker.patch.object(detect_agent, "submit", True)

    # Create message with submission=False
    init_msg = ExecutorAgentMessage(
        agent_id="executor", message="test", submission=False
    )

    # Run the agent
    final_msg = await detect_agent.run([init_msg])

    # Verify the result
    assert "Waiting for the submission..." in final_msg.message


@pytest.mark.asyncio
async def test_received_submission(detect_agent, mocker):
    """Test that when submit=True and prev_agent_message.submission=True, we check for exploit"""
    # Override submit flag on existing agent
    mocker.patch.object(detect_agent, "submit", True)

    # Mock that exploit.sh exists
    mocker.patch.object(Path, "exists", return_value=True)

    # Mock run_agent_exploit to return success (0)
    mocker.patch.object(detect_agent, "run_agent_exploit", return_value=0)

    # Mock score_agent_exploit to return True
    mocker.patch.object(detect_agent, "score_agent_exploit", return_value=True)

    # Create message with submission=True
    init_msg = ExecutorAgentMessage(
        agent_id="executor", message="test", submission=True
    )
    with patch("agents.detect_agent.detect_agent.git_has_changes", return_value=True):
        with patch("agents.detect_agent.detect_agent.git_commit", return_value=True):
            # Run the agent
            final_msg = await detect_agent.run([init_msg])

    # Verify the result
    assert final_msg.success is True


@pytest.mark.asyncio
async def test_exploit_failure(detect_agent, mocker):
    """Test that when run_agent_exploit returns 1, we get 'Exploit failed with exit code' message"""
    # Mock that exploit.sh exists
    mocker.patch.object(Path, "exists", return_value=True)

    # Mock git_has_changes to return True so we run the exploit
    mocker.patch("agents.detect_agent.detect_agent.git_has_changes", return_value=True)

    # Mock git_commit to avoid side effects
    mocker.patch("agents.detect_agent.detect_agent.git_commit")

    # Mock git_reset to avoid side effects
    mocker.patch("agents.detect_agent.detect_agent.git_reset")

    # Mock run_agent_exploit to return failure (1)
    mocker.patch.object(detect_agent, "run_agent_exploit", return_value=1)

    # Run the agent with a simple message
    init_msg = ExecutorAgentMessage(
        agent_id="executor", message="test", submission=False
    )

    # Run the agent
    final_msg = await detect_agent.run([init_msg])

    # Verify the result
    assert "Exploit failed with exit code 1" in final_msg.message


@pytest.mark.asyncio
async def test_score_agent_exploit_all_success(detect_agent, mocker):
    """Test score_agent_exploit returns False when all patches result in exploit success (exit code 0)"""
    # Mock the compatible patches to return 3 items
    mocker.patch.object(
        detect_agent, "get_compatible_patches", return_value=["0", "1", "2"]
    )

    # Mock setup_patched_bounty_env to avoid side effects
    mocker.patch.object(detect_agent, "setup_patched_bounty_env")

    # Mock run_agent_exploit to always return 0 (success)
    mocker.patch.object(detect_agent, "run_agent_exploit", return_value=0)

    # Create message
    detect_message = DetectAgentMessage(agent_id="test", message="test")

    # Run the method
    result = await detect_agent.score_agent_exploit(detect_message)

    # Verify result
    # If all exploits succeed (exit code 0), total_failures should be 0
    # The function should return (total_failures == 1), which is False
    assert result is False


@pytest.mark.asyncio
async def test_score_agent_exploit_one_failure(detect_agent, mocker):
    """Test score_agent_exploit returns True when exactly one patch results in exploit failure"""
    # Mock the compatible patches to return 3 items
    mocker.patch.object(
        detect_agent, "get_compatible_patches", return_value=["0", "1", "2"]
    )

    # Mock setup_patched_bounty_env to avoid side effects
    mocker.patch.object(detect_agent, "setup_patched_bounty_env")

    # Mock run_agent_exploit to return 0 for first two patches and 1 for the third
    mocker.patch.object(detect_agent, "run_agent_exploit", side_effect=[0, 0, 1])

    # Create message
    detect_message = DetectAgentMessage(agent_id="test", message="test")

    # Run the method
    result = await detect_agent.score_agent_exploit(detect_message)

    # Verify result
    # If exactly one exploit fails (exit code 1), total_failures should be 1
    # The function should return (total_failures == 1), which is True
    assert result is True
