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
    agent.last_detect_agent_message = DetectAgentMessage(
        agent_id="test", message="init"
    )
    exploit_script_dir = Path(env_path.TMP_EXPLOIT_SCRIPT_DIR)

    # Set up mocks
    mock_run_exploit = MagicMock()
    mock_action_message = MagicMock()
    mock_action_message.additional_metadata = {"exit_code": 1}
    mock_action_message.message = "exploit output"
    mock_run_exploit.return_value = mock_action_message

    with patch.object(agent, "run_exploit", mock_run_exploit):
        # Test exploit failure
        mock_action_message.additional_metadata = {"exit_code": 1}
        detect_message = DetectAgentMessage(agent_id="test", message="test")
        exit_code = await agent.run_agent_exploit(detect_message)
        assert exit_code == 1

        # Test exploit success
        mock_action_message.additional_metadata = {"exit_code": 0}
        exit_code = await agent.run_agent_exploit(detect_message)
        assert exit_code == 0


@pytest.mark.asyncio
async def test_restart_resource_check(detect_agent, mocker):
    """
    If repo_resource fails to restart, error.
    """
    agent = detect_agent

    with patch.object(
        DetectAgent,
        "_restart_resource",
        side_effect=Exception("some resource restart failure"),
    ):
        success = agent.restart_resources()
        assert not success


def test_restart_resources_order(bounty_setup):
    """Test that resources are restarted in the correct order: repo_setup first, then bounty_setup."""
    env_path: EnvPath = bounty_setup

    # Create a custom agent with mocked resources and a mocked _restart_resource to track call order
    agent = DetectAgent(
        agent_id="test_detect_agent",
        agent_config=DetectAgentConfig(
            bounty_dir=env_path.BOUNTY_DIR,
            task_dir=env_path.TASK_DIR,
            tmp_dir=env_path.TMP_DIR,
            submit=False,
        ),
    )

    # Create mock attributes to simulate resource existence
    restart_order = []

    def mock_restart(resource):
        restart_order.append(resource.resource_id)
        return True

    # Add mock resources to the agent
    agent.resources.repo_setup = MagicMock()
    agent.resources.repo_setup.resource_id = "repo_setup"
    agent.resources.bounty_setup = MagicMock()
    agent.resources.bounty_setup.resource_id = "bounty_setup"

    # Override the _restart_resource method to track call order
    with patch.object(DetectAgent, "_restart_resource", side_effect=mock_restart):
        # Call restart_resources
        agent.restart_resources()

    # Verify repo_setup was restarted before bounty_setup
    assert restart_order == ["repo_setup", "bounty_setup"]


@pytest.mark.asyncio
async def test_skip_no_exploit(detect_agent, mocker):
    """Test that the agent skips if no exploit.sh exists"""
    agent = detect_agent

    # Mock that exploit.sh doesn't exist
    mocker.patch.object(Path, "exists", return_value=False)

    # Run the agent
    init_msg = ExecutorAgentMessage(
        agent_id="executor", message="test", submission=False
    )
    final_msg = await agent.run([init_msg])

    # Verify the result
    assert "No exploit.sh found." in final_msg.message
    assert "Skipping" in final_msg.message


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
    assert "No changes to exploit files detected." in final_msg.message
    assert "Skipping" in final_msg.message


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

    # Mock git_clean to avoid side effects
    mocker.patch("agents.detect_agent.detect_agent.git_clean")

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

    # Mock reset_bounty_resource_work_dir to avoid side effects
    mocker.patch.object(detect_agent, "reset_bounty_resource_work_dir")

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

    # Mock reset_bounty_resource_work_dir to avoid side effects
    mocker.patch.object(detect_agent, "reset_bounty_resource_work_dir")

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


def test_setup_patched_bounty_env(detect_agent, mocker):
    """Test that setup_patched_bounty_env updates the work_dir and calls restart_resources"""
    # Mock checkout_different_commit to avoid side effects
    mocker.patch.object(detect_agent, "checkout_different_commit")

    # Mock get_bounty_dir_path to return a Path
    bounty_dir = Path("/mocked/bounty/path")
    mocker.patch.object(detect_agent, "get_bounty_dir_path", return_value=bounty_dir)

    # Mock apply_patch_to_bounty to return True
    mocker.patch("utils.file_utils.apply_patch_to_bounty", return_value=True)

    # Mock Path.exists to return True
    mocker.patch.object(Path, "exists", return_value=True)

    # Mock ResourceType.BOUNTY_SETUP bound check
    mocker.patch.object(detect_agent.resources, "has_bound", return_value=True)

    # Create a mock bounty_setup resource
    mock_bounty_setup = MagicMock()
    detect_agent.resources.bounty_setup = mock_bounty_setup

    # Create a spy on restart_resources
    restart_spy = mocker.spy(detect_agent, "restart_resources")

    # Call the method
    detect_agent.setup_patched_bounty_env("1")

    # Verify that update_work_dir was called on the bounty_setup resource with the correct path
    expected_path = bounty_dir / SETUP_FILES_DIR
    mock_bounty_setup.update_work_dir.assert_called_once_with(expected_path)

    # Verify that restart_resources was called
    restart_spy.assert_called_once()
