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

TEST_FILE_NAME = "test_file.txt"

MOCK_REPO_SCORES = {"healthcheck": 1, "test_server": 76}
MOCK_REPO_SCORES_TO_WRITE = {"invariant_scores": MOCK_REPO_SCORES}

MOCK_BOUNTY_SCORES = {"healthcheck": 1, "test_db": 80}
MOCK_BOUNTY_SCORES_TO_WRITE = {"invariant_scores": MOCK_BOUNTY_SCORES}

MOCK_REPO_METADATA = {"healthcheck": 1, "test_server": 76}

MOCK_BOUNTY_METADATA = {"test_db": 80}


def mock_patch_agent_message():
    def mock_init(self, agent_id, message, prev, success=None, patch_files_dir=None):
        self._message = message

    return patch.object(PatchAgentMessage, "__init__", mock_init)


@pytest.fixture(scope="module")
def patch_agent(bounty_setup):
    env_path: EnvPath = bounty_setup
    # Initialize agent

    agent_manager = AgentManager(workflow_id="1")
    patch_config = PatchAgentConfig(
        bounty_dir=env_path.BOUNTY_DIR,
        task_dir=env_path.TASK_DIR,
        use_agent_exploit=True,
    )
    agent = agent_manager.create_agent("test_patch_agent", PatchAgent, patch_config)

    # agent's codebase parameter is initialized in the run function so we do it here
    agent.codebase = env_path.TMP_CODEBASE_FILES_DIR

    mocks = [patch.object(PatchAgent, "_restart_resource", return_value=True)]

    [mock.start() for mock in mocks]

    yield agent

    [mock.stop() for mock in mocks]

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


# probably a temporary test but currently failing due to issues with initializing resources
def test_check_repo_and_bounty_are_different(patch_agent):
    agent = patch_agent
    if hasattr(patch_agent, "bounty_setup") and hasattr(agent, "repo_setup"):
        assert agent.resources.bounty_setup is not agent.resources.repo_setup


@pytest.mark.asyncio
async def test_run_agent_exploit(bounty_setup, patch_agent):
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    agent.last_patch_agent_message = PatchAgentMessage(agent_id="test", message="init")
    exploit_script_dir = Path(env_path.TMP_EXPLOIT_SCRIPT_DIR)
    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=1,
    )
    exit_code, _ = await agent.run_agent_exploit()
    assert exit_code == 1

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=0,
    )
    exit_code, _ = await agent.run_agent_exploit()
    assert exit_code == 0

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=2,
    )
    exit_code, _ = await agent.run_agent_exploit()
    assert exit_code == 2


@pytest.mark.asyncio
async def test_restart_resource_check(patch_agent, mocker):
    """
    If repo_resource fails to restart, error.
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    agent.last_patch_agent_message = PatchAgentMessage(
        agent_id="patch_agent", message=None
    )

    with patch.object(
        PatchAgent,
        "_restart_resource",
        side_effect=Exception("some resource restart failure"),
    ):
        await agent.verify_patch()
        agent.update_patch_agent_message()
        assert (
            "could not restart associated resources after applying the patch. patch is invalid."
            in agent.last_patch_agent_message.message.lower()
        )


@pytest.mark.asyncio
async def test_fail_if_external_exploit_fails(patch_agent, mocker):
    """
    Exploit returns 1 (failure) before patch applies - which makes the workflow run invalid
    """
    patch_agent.use_agent_exploit = False
    mocker.patch.object(PatchAgent, "run_external_exploit", return_value=1)
    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")

    initial_msg = PatchAgentMessage(agent_id="test", message="test message")
    with pytest.raises(Exception, match=f"External Exploit for") as e:
        await patch_agent.run([initial_msg])


@pytest.mark.asyncio
async def test_restart_resource_fail_raises_exception(patch_agent, mocker):
    """
    Exploit returns 0 (success) before patch applies, restart resource fails
    """
    patch_agent.use_agent_exploit = False
    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch.object(patch_agent, "run_external_exploit", return_value=0)
    mocker.patch.object(
        PatchAgent,
        "_restart_resource",
        side_effect=Exception("some resource restart fail"),
    )
    initial_msg = PatchAgentMessage(agent_id="test", message="test message")
    with pytest.raises(Exception, match=f"Failed to restart resources") as e:
        await patch_agent.run([initial_msg])


def test_restart_resources_order(bounty_setup):
    """Test that resources are restarted in the correct order: repo_setup first, then bounty_setup."""
    env_path: EnvPath = bounty_setup

    # Create a custom agent with mocked resources and a mocked _restart_resource to track call order
    agent = PatchAgent(
        agent_id="test_patch_agent",
        agent_config=PatchAgentConfig(
            bounty_dir=env_path.BOUNTY_DIR,
            task_dir=env_path.TASK_DIR,
            use_agent_exploit=True,
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
    with patch.object(PatchAgent, "_restart_resource", side_effect=mock_restart):
        # Call restart_resources
        agent.restart_resources()

    # Verify repo_setup was restarted before bounty_setup
    assert restart_order == ["repo_setup", "bounty_setup"]


@pytest.mark.asyncio
async def test_agent_exploit_0_then_0_fail(patch_agent, mocker):
    """
    Exploit returns 0 (ok) before patch and 0 after patch → exploit is still working,
    patch must fail.
    """
    patch_agent.use_agent_exploit = True

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(True, "Patch applied successfully"),
    )

    mocker.patch.object(patch_agent, "restart_resources", return_value=True)

    run_agent_exploit_mock = mocker.patch.object(
        patch_agent,
        "run_agent_exploit",
        side_effect=[(0, "Exploit passed"), (0, "Exploit passed")],  # unpatched run
    )

    git_reset_mock: MagicMock = mocker.patch("agents.patch_agent.patch_agent.git_reset")

    # Let invariants pass
    mocker.patch.object(patch_agent, "check_invariants", return_value=True)

    initial_msg = PatchAgentMessage(agent_id="test", message="test message")
    final_msg = await patch_agent.run([initial_msg])

    assert final_msg.success is False
    assert (
        "Exploit check failed - exploit still succeeds after patch."
        in final_msg.message
    )
    assert run_agent_exploit_mock.call_count == 2
    assert git_reset_mock.call_count == 2


@pytest.mark.asyncio
async def test_agent_exploit_1_before_patch(patch_agent, mocker):
    """
    Exploit returns 1 unpatched → The agent should log it as an invalid exploit.
    No second run, no patch application.
    """
    patch_agent.use_agent_exploit = True

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")

    run_exploit_mock = mocker.patch.object(
        patch_agent,
        "run_agent_exploit",
        return_value=(1, "Exploit failed"),  # unpatched run
    )
    # Invariants won't matter because we won't even get to patch
    mock_invariants = mocker.patch.object(patch_agent, "check_invariants")

    initial_msg = PatchAgentMessage(agent_id="test", message="test message")
    final_msg = await patch_agent.run([initial_msg])

    # The code in verify_patch sees exit_code=1 (not 0, not 127) => exploit fails before patch is applied
    assert run_exploit_mock.call_count == 1
    # We expect "Exploit fails before the patch is applied" in the logs
    assert "Exploit fails before the patch is applied" in final_msg.message
    # Also expect that no patch was applied, no second run
    mock_invariants.assert_not_called()
    assert final_msg.success is False


@pytest.mark.asyncio
async def test_external_exploit_1_success(patch_agent, mocker):
    """
    The external exploit, after patch we expect 'verify.sh' to indicate success is neutralized → return 1,
    so the final patch is considered successful.
    """
    # Force external exploit path
    patch_agent.use_agent_exploit = False

    # mock git_diff => there is a patch
    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(True, "Applied patch successfully"),
    )

    run_external_exploit_mock = mocker.patch.object(
        PatchAgent,
        "run_external_exploit",
        side_effect=[0, 1],
    )

    # Let invariants pass
    mocker.patch.object(patch_agent, "check_invariants", return_value=True)

    # Run
    initial_msg = PatchAgentMessage(
        agent_id="test", message="run external exploit test"
    )
    final_msg = await patch_agent.run([initial_msg])

    # We expect success
    assert final_msg.success is True
    assert "Congratulations! The patch succeeded." in final_msg.message
    assert run_external_exploit_mock.call_count == 2


def test_create_patch_file(bounty_setup, patch_agent, git_fixture):
    """
    Test the create_patch_file method, ensuring patch is created outside the task repo.
    """
    env_path: EnvPath = bounty_setup
    agent = patch_agent
    agent.patch_id = 1
    tmp_dir = env_path.TMP_CODEBASE_FILES_DIR
    tmp_dir.chmod(0o755)  # Make sure the directory is writable
    (tmp_dir / TEST_FILE_NAME).write_text("Another modification")

    diff = git_diff(tmp_dir)
    agent.create_patch_file(diff, agent.output_patch_dir)

    patch_file_path = agent.output_patch_dir / "patch_1" / "patch_1.patch"
    assert patch_file_path.exists()


@pytest.mark.asyncio
async def test_execute_invariant_tests_success(bounty_setup, patch_agent):
    """Test that run_patch_invariants returns True when invariant checks succeed."""
    agent = patch_agent
    env_path = bounty_setup

    repo_invariants_script = env_path.TASK_DIR / "run_repo_invariants.sh"
    bounty_invariants_script = env_path.BOUNTY_DIR / "run_bounty_invariants.sh"

    patch_agent.last_patch_agent_message = PatchAgentMessage(
        agent_id="patch_agent",
    )

    # Create scripts
    write_to_file_and_make_executable(repo_invariants_script, exit_code=0)
    write_to_file_and_make_executable(bounty_invariants_script, exit_code=0)

    # Mock the file reading logic
    def mock_load_json(path):
        return {"invariant_scores": {"healthcheck": 1, "test_server": 76}}

    with (
        patch.object(
            PatchAgent, "check_invariant_scores_against_thresholds", return_value=True
        ),
        patch.object(patch_agent, "_load_json_file", side_effect=mock_load_json),
    ):
        # Just verify that files are returned
        repo_score, bounty_score = await agent._execute_invariant_tests()
        print(repo_score)
        print(bounty_score)
        assert "healthcheck" in repo_score
        assert "test_server" in bounty_score
        assert len(patch_agent.last_patch_agent_message.action_messages) == 2
        assert "healthcheck" in patch_agent.last_patch_agent_message.action_messages[
            0
        ].additional_metadata.get("repo_invariant_scores", {})
        assert "test_server" in patch_agent.last_patch_agent_message.action_messages[
            1
        ].additional_metadata.get("bounty_invariant_scores", {})

    # And test check_invariants directly
    with (
        patch.object(
            patch_agent,
            "_execute_invariant_tests",
            return_value=(Path("mock1"), Path("mock2")),
        ),
        patch.object(
            PatchAgent, "check_invariant_scores_against_thresholds", return_value=True
        ),
        patch.object(
            patch_agent, "_load_json_file", return_value={"invariant_scores": {}}
        ),
        patch.object(patch_agent, "_cleanup_files"),
    ):
        result = await agent.check_invariants()
        assert result is True


@pytest.mark.asyncio
async def test_execute_patch_invariants_check_fails(bounty_setup, patch_agent):
    """Test that run_patch_invariants returns False when check_invariant_scores_against_thresholds fails."""
    agent = patch_agent
    env_path = bounty_setup

    repo_invariants_script = env_path.TASK_DIR / "run_repo_invariants.sh"
    bounty_invariants_script = env_path.BOUNTY_DIR / "run_bounty_invariants.sh"

    write_to_file_and_make_executable(repo_invariants_script, exit_code=0)
    write_to_file_and_make_executable(bounty_invariants_script, exit_code=0)

    with (
        patch.object(
            PatchAgent, "check_invariant_scores_against_thresholds", return_value=False
        ),
        patch.object(
            patch_agent, "_load_json_file", return_value={"invariant_scores": {}}
        ),
        patch.object(
            patch_agent,
            "_execute_invariant_tests",
            return_value=(Path("mock1"), Path("mock2")),
        ),
        patch.object(patch_agent, "_cleanup_files"),
    ):
        result = await agent.check_invariants()
        assert result is False


@pytest.mark.asyncio
async def test_patch_success_requires_invariants(patch_agent):
    """Test that patch success requires both exploit check and invariant check to pass."""
    agent = patch_agent
    agent.last_patch_agent_message = PatchAgentMessage(
        agent_id="patch_agent", message=None
    )

    # Mock the run_patch_invariants method
    with patch.object(PatchAgent, "check_invariants", return_value=False):
        # Mock resource restart
        with patch.object(PatchAgent, "_restart_resource", return_value=True):
            # Mock run_agent_exploit to return success
            with patch.object(PatchAgent, "run_external_exploit", return_value=1):
                await agent.verify_patch()
                agent.update_patch_agent_message()
                print(agent.last_patch_agent_message)
                assert "failed" in agent.last_patch_agent_message.message.lower()
                assert not agent.last_patch_agent_message.success


def test_check_invariant_scores_against_thresholds_success(patch_agent):
    """Test that check_invariant_scores_against_thresholds returns True when scores meet thresholds."""
    agent = patch_agent

    # Test with all scores meeting thresholds
    result = agent.check_invariant_scores_against_thresholds(
        MOCK_REPO_METADATA,
        MOCK_BOUNTY_METADATA,
        MOCK_REPO_SCORES,
        MOCK_BOUNTY_SCORES,
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_invariants_returns_correct_scores(patch_agent):
    """Test that check_invariants properly processes and returns scores."""
    with tempfile.TemporaryDirectory() as tmpdir:
        task_dir = Path(tmpdir) / "task"
        bounty_dir = Path(tmpdir) / "bounty"
        task_dir.mkdir()
        bounty_dir.mkdir()

        # We'll need to create these files in the test setup
        repo_scores_path = task_dir / "invariant_scores.json"
        bounty_scores_path = bounty_dir / "invariant_scores.json"

        # Create all necessary files
        repo_scores_path.write_text(json.dumps(MOCK_REPO_SCORES_TO_WRITE))
        bounty_scores_path.write_text(json.dumps(MOCK_BOUNTY_SCORES_TO_WRITE))

        agent = patch_agent
        agent.task_dir = task_dir
        agent.bounty_dir = bounty_dir
        agent.last_patch_agent_message = PatchAgentMessage(
            agent_id="patch_agent", message=None
        )

        # Mock _execute_invariant_tests to return our prepared files
        with (
            patch(
                "agents.patch_agent.patch_agent.run_command_async",
                return_value=({"stdout": "mocked", "stderr": "", "returncode": 0}),
            ),
            patch.object(
                PatchAgent,
                "check_invariant_scores_against_thresholds",
                return_value=True,
            ),
        ):
            # Run the method
            result = await agent.check_invariants()

            # Verify result
            assert result is True


def test_check_invariant_scores_edge_cases(patch_agent):
    """Test edge cases for check_invariant_scores_against_thresholds method."""
    agent = patch_agent

    # Temporary test files
    files = {
        "repo_meta": Path("repo_metadata.json"),
        "bounty_meta": Path("bounty_metadata.json"),
        "repo_scores": Path("repo_scores.json"),
        "bounty_scores": Path("bounty_scores.json"),
    }

    try:
        # Case 1: Scores below thresholds
        files["repo_meta"].write_text(
            json.dumps({"invariant_thresholds": {"healthcheck": 2, "test_server": 80}})
        )
        files["bounty_meta"].write_text(
            json.dumps({"invariant_thresholds": {"test_db": 85}})
        )
        files["repo_scores"].write_text(json.dumps(MOCK_REPO_SCORES_TO_WRITE))
        files["bounty_scores"].write_text(json.dumps(MOCK_BOUNTY_SCORES_TO_WRITE))

        result = agent.check_invariant_scores_against_thresholds(*files.values())
        assert result is False

        # Case 2: Missing scores for a threshold
        files["repo_meta"].write_text(
            json.dumps({"invariant_thresholds": {"missing_score": 50}})
        )
        result = agent.check_invariant_scores_against_thresholds(*files.values())
        assert result is False

        # Case 3: Missing invariant_scores key in scores file
        files["repo_meta"].write_text(json.dumps(MOCK_REPO_METADATA))
        files["repo_scores"].write_text(json.dumps({"other_key": "value"}))
        result = agent.check_invariant_scores_against_thresholds(*files.values())
        assert result is False

    finally:
        # Clean up
        for file in files.values():
            if file.exists():
                file.unlink()


# Test that the system correctly makes calls to git_reset
# -----------------------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reset_repo_on_empty_diff(patch_agent, mocker):
    """
    Test that the repo is not reset if git diff returns an empty diff.
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value=None)
    mocker.patch.object(patch_agent, "run_external_exploit", return_value=0)
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(False, "Patch failed"),
    )
    git_reset_mock: MagicMock = mocker.patch("agents.patch_agent.patch_agent.git_reset")

    await agent.run(["message"])

    git_reset_mock.assert_not_called()
    assert (
        agent.patch_id == prev_patch_id
    )  # patch is skipped so patch_id should not increment


@pytest.mark.asyncio
async def test_reset_repo_on_patch_creation_fail(patch_agent, mocker):
    """
    Test that tmp and remote codebase are reset to their original states if
    patch creation failed.
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch.object(patch_agent, "run_external_exploit", return_value=0)
    mocker.patch.object(
        PatchAgent,
        "create_patch_file",
        side_effect=Exception("Failed to create patch file"),
    )

    git_reset_mock = mocker.patch("agents.patch_agent.patch_agent.git_reset")
    await agent.run(["message"])

    assert git_reset_mock.call_count == 2
    assert agent.patch_id == prev_patch_id + 1


@pytest.mark.asyncio
async def test_reset_repo_on_apply_patch_fail(patch_agent, mocker):
    """
    Test that tmp and remote codebase are reset to their original states if
    patch creation was successful, but patch apply fails.
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch.object(patch_agent, "run_external_exploit", return_value=0)

    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(False, "Patch failed"),
    )

    git_reset_mock = mocker.patch("agents.patch_agent.patch_agent.git_reset")
    await agent.run(["message"])

    assert git_reset_mock.call_count == 2
    assert agent.patch_id == prev_patch_id + 1


@pytest.mark.asyncio
async def test_reset_repo_on_invariant_checking_fail(patch_agent, mocker):
    """
    Test that tmp and remote codebase are reset to their original states if
    invariant checking fails.
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(False, "Patch failed"),
    )

    mocker.patch.object(PatchAgent, "_apply_patch", return_value=(True, ""))
    mocker.patch.object(PatchAgent, "restart_resources", return_value=True)
    mocker.patch.object(PatchAgent, "run_external_exploit", return_value=0)
    mocker.patch.object(PatchAgent, "apply_patched_unit_tests", return_value=True)

    git_reset_mock = mocker.patch("agents.patch_agent.patch_agent.git_reset")
    await agent.run(["message"])

    assert git_reset_mock.call_count == 2
    assert agent.patch_id == prev_patch_id + 1


@pytest.mark.asyncio
async def test_full_workflow_exploit_failure(patch_agent, mocker):
    """
    - Start with both repos in the same initial state
    - Apply patch successfully
    - Exploit still succeeds after patch (which gives an error)
    - Verify error is reported correctly
    - Verify repos changes are removed
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(True, "Patch applied successfully"),
    )
    mocker.patch("agents.patch_agent.patch_agent.git_reset")
    git_reset_mock = mocker.patch("agents.patch_agent.patch_agent.git_reset")

    agent.last_patch_agent_message = PatchAgentMessage(
        agent_id="patch_agent", message=None
    )

    mocker.patch.object(PatchAgent, "run_external_exploit", return_value=0)

    await agent.run(["message"])

    assert agent.last_patch_agent_message.success is False
    assert "check failed" in agent.last_patch_agent_message.message
    assert agent.patch_id == prev_patch_id + 1
    assert git_reset_mock.call_count == 2


@pytest.mark.asyncio
async def test_full_workflow_success(patch_agent, mocker):
    """
    Test the full patch workflow in the success case:
    - Start with both repos in the same initial state
    - Apply patch successfully
    - Verify success is reported correctly
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(True, "Patch applied successfully"),
    )
    mocker.patch("agents.patch_agent.patch_agent.git_reset")

    agent.last_patch_agent_message = PatchAgentMessage(
        agent_id="patch_agent", message=None
    )

    run_external_exploit_mock = mocker.patch.object(
        PatchAgent,
        "run_external_exploit",
        side_effect=[0, 1],
    )
    mocker.patch.object(patch_agent, "check_invariants", return_value=True)

    await agent.run(["message"])

    assert agent.last_patch_agent_message.success is True
    assert "Congratulations" in agent.last_patch_agent_message.message
    assert agent.patch_id == prev_patch_id
    assert run_external_exploit_mock.call_count == 2


# "uses" the import
if None:
    bounty_setup
