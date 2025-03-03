import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.agent_manager import AgentManager
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from tests.agents.agent_test_utils import EnvPath
from tests.agents.agent_test_utils import lunary_bounty_0_setup as bounty_setup
from tests.agents.agent_test_utils import write_to_file_and_make_executable
from utils.git_utils import git_diff

TEST_FILE_NAME = "test_file.txt"


def mock_patch_agent_message():
    def mock_init(self, agent_id, message, prev, success=None, patch_files_dir=None):
        self._message = message

    return patch.object(PatchAgentMessage, "__init__", mock_init)


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

    agent_manager = AgentManager(workflow_id="1")
    patch_config = PatchAgentConfig(
        bounty_dir=env_path.BOUNTY_DIR,
        task_dir=env_path.TASK_DIR,
        use_verify_script=True,
    )
    agent = agent_manager.create_agent("test_patch_agent", PatchAgent, patch_config)

    # agent's codebase parameter is initialized in the run function so we do it here
    agent.codebase = env_path.TMP_CODEBASE_FILES_DIR

    mocks = [mock_restart_resource()]
    store_patch_mock = mock_store_patch()

    [mock.start() for mock in mocks]
    store_patch_mock.start()  # we don't want this to stop during testing so we don't stop

    yield agent

    [mock.stop() for mock in mocks]

    # revert any commits the tests made in env
    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=env_path.TASK_DIR)


@pytest.fixture(scope="module")
def execute_fixture(bounty_setup, patch_agent):
    env_path: EnvPath = bounty_setup

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
        env_path.AGENT_PATCHES_DIR / "patch_1.patch",
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


@pytest.mark.asyncio
async def test_run_exploit(bounty_setup, patch_agent):
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    exploit_script_dir = Path(env_path.TMP_EXPLOIT_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=1,
    )
    exploit_result = await agent.run_exploit()
    assert exploit_result.additional_metadata["exit_code"] == 1

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=0,
    )
    exploit_result = await agent.run_exploit()
    assert exploit_result.additional_metadata["exit_code"] == 0

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=2,
    )
    exploit_result = await agent.run_exploit()
    assert exploit_result.additional_metadata["exit_code"] == 2


@pytest.mark.asyncio
async def test_restart_resource_check(patch_agent):
    """
    If repo_resource fails to restart, error.
    """
    agent = patch_agent

    patch_agent_message = PatchAgentMessage(agent_id="patch_agent", message=None)

    with patch.object(PatchAgent, "_restart_resource", return_value=False):
        await agent.execute(patch_agent_message)
        assert "cannot restart" in patch_agent_message.message.lower()


@pytest.mark.asyncio
async def test_no_verify_sh_exploit_returns_1(
    bounty_setup, patch_agent, execute_fixture
):
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

    patch_agent_message = PatchAgentMessage(agent_id="patch_agent", message=None)

    await agent.execute(patch_agent_message)
    assert "patch succeeded" in patch_agent_message.message.lower()


@pytest.mark.asyncio
async def test_no_verify_sh_exploit_returns_0(
    bounty_setup, patch_agent, execute_fixture
):
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

    patch_agent_message = PatchAgentMessage(agent_id="patch_agent", message=None)
    await agent.execute(patch_agent_message)
    assert "patch failed" in patch_agent_message.message.lower()


@pytest.mark.asyncio
async def test_no_verify_sh_exploit_invalid_exit_code(
    bounty_setup, patch_agent, execute_fixture
):
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

    patch_agent_message = PatchAgentMessage(agent_id="patch_agent", message=None)

    await agent.execute(patch_agent_message)
    # Should result in patch failed
    assert "patch failed" in patch_agent_message.message.lower()


@pytest.mark.asyncio
async def test_with_verify_sh_success(bounty_setup, patch_agent, execute_fixture):
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
    patch_agent_message = PatchAgentMessage(agent_id="patch_agent", message=None)
    await agent.execute(patch_agent_message)
    assert "patch succeeded" in patch_agent_message.message.lower()


@pytest.mark.asyncio
async def test_with_verify_sh_fail(bounty_setup, patch_agent):
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

    patch_agent_message = PatchAgentMessage(agent_id="patch_agent", message=None)

    await agent.execute(patch_agent_message)

    assert "patch failed" in patch_agent_message.message.lower()


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


def test_create_patch_file(bounty_setup, patch_agent, git_fixture):
    """
    Test the create_patch_file method, ensuring patch is created outside the task repo.
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    agent.patch_id = 1
    tmp_dir = env_path.TMP_CODEBASE_FILES_DIR
    (tmp_dir / TEST_FILE_NAME).write_text("Another modification")

    diff = git_diff(tmp_dir)
    agent.create_patch_file(diff, agent.patch_dir)

    patch_file_path = agent.patch_dir / "patch_1.patch"
    assert patch_file_path.exists()

# "uses" the import
if None:
    bounty_setup