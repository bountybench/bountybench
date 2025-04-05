import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.agent_manager import AgentManager
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from tests.test_utils.bounty_setup_test_util import EnvPath
from tests.test_utils.bounty_setup_test_util import (
    lunary_bounty_0_setup as bounty_setup,
)
from tests.test_utils.bounty_setup_test_util import write_to_file_and_make_executable
from utils.git_utils import git_diff
from resources.base_setup_resource import SetupResourceException

TEST_FILE_NAME = "test_file.txt"

MOCK_REPO_SCORES = {"invariant_scores": {"healthcheck": 1, "test_server": 76}}

MOCK_BOUNTY_SCORES = {"invariant_scores": {"healthcheck": 1, "test_db": 80}}

MOCK_REPO_METADATA = {"invariant_thresholds": {"healthcheck": 1, "test_server": 76}}

MOCK_BOUNTY_METADATA = {"invariant_thresholds": {"test_db": 80}}


def mock_patch_agent_message():
    def mock_init(self, agent_id, message, prev, success=None, patch_files_dir=None):
        self._message = message

    return patch.object(PatchAgentMessage, "__init__", mock_init)


@pytest.fixture
def unmocked_patch_agent(bounty_setup):
    """Create a patch agent without mocking _restart_resource"""
    env_path: EnvPath = bounty_setup
    
    # Initialize agent
    agent_manager = AgentManager(workflow_id="1")
    patch_config = PatchAgentConfig(
        bounty_dir=env_path.BOUNTY_DIR,
        task_dir=env_path.TASK_DIR,
        use_agent_exploit=True,
    )
    agent = agent_manager.create_agent("test_patch_agent2", PatchAgent, patch_config)
    
    # agent's codebase parameter is initialized in the run function so we do it here
    agent.codebase = env_path.TMP_CODEBASE_FILES_DIR
    
    yield agent
    
    # revert any commits the tests made in env
    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=env_path.TASK_DIR)


@pytest.fixture(scope="module")
def execute_fixture(bounty_setup, patch_agent):
    env_path: EnvPath = bounty_setup

    env_path.TMP_CODEBASE_FILES_DIR.mkdir(parents=True, exist_ok=True)
    exploit_script_dir = env_path.TMP_EXPLOIT_SCRIPT_DIR

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=0,
    )
    yield


@pytest.fixture(scope="module")
def git_fixture(bounty_setup):
    env_path: EnvPath = bounty_setup
    files_to_delete = [
        env_path.TMP_CODEBASE_FILES_DIR / TEST_FILE_NAME,
        env_path.AGENT_PATCHES_DIR / "patch_1" / "patch_1.patch",
    ]
    yield
    # delete files if they exist
    for file in files_to_delete:
        if file.exists():
            file.unlink()


@pytest.mark.asyncio
async def test_restart_resource_with_setup_resource_exception(unmocked_patch_agent, mocker):
    """
    Test that when a resource's restart method raises a SetupResourceException,
    the exception's action_message is properly captured and used for reporting.
    """
    # Create a mock SetupResourcesMessage for the error
    mock_action_message = mocker.MagicMock()
    mock_action_message.message = "Error message from action"
    mock_action_message.exit_code = -1
    
    # Create a mock SetupResourceException with the action message
    mock_exception = SetupResourceException(
        message="Setup script not found", 
        action_message=mock_action_message
    )
    
    # Create a mock resource that raises the exception when restart is called
    mock_resource = mocker.MagicMock()
    mock_resource.resource_id = "test_resource"
    mock_resource.restart.side_effect = mock_exception
    
    # Setup the patch agent's last_action_message and last_patch_agent_message
    unmocked_patch_agent.last_action_message = None
    unmocked_patch_agent.last_patch_agent_message = PatchAgentMessage(
        agent_id="test", message=None
    )
    
    # Add logging to see what's happening
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    
    # Let's also check the _restart_resource method directly
    print("Original _restart_resource method:", unmocked_patch_agent._restart_resource)
    
    # Override the retry decorator to test the actual function
    #with patch('agents.patch_agent.patch_agent.retry', lambda *args, **kwargs: lambda f: f):
    print("After patching, _restart_resource method:", unmocked_patch_agent._restart_resource)
    
    # Explicitly check if the mocked resource raises the exception properly
    try:
        mock_resource.restart()
        assert False, "Mock resource restart() didn't raise exception"
    except Exception as e:
        print(f"Exception from mock resource: {type(e).__name__}: {e}")
        assert isinstance(e, SetupResourceException), "Expected SetupResourceException wasn't raised by mock"
    
    # Now try the actual _restart_resource method
    try:
        unmocked_patch_agent._restart_resource(mock_resource)
        pytest.fail("Expected SetupResourceException was not raised")
    except Exception as e:
        print(f"Exception from _restart_resource: {type(e).__name__}: {e}")
        # Verify it's the correct exception type
        assert isinstance(e, SetupResourceException), f"Got {type(e).__name__} instead of SetupResourceException"
        # Verify it's our mock exception
        assert e is mock_exception, "Exception is not our mock exception"
        
        # Verify the action message was added to the patch agent message's children
        assert mock_action_message in unmocked_patch_agent.last_patch_agent_message.current_children, "Action message not in patch agent message children"





# "uses" the import
if None:
    bounty_setup
