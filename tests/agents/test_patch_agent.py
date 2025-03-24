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

MOCK_REPO_SCORES = {"invariant_scores": {"healthcheck": 1, "test_server": 76}}

MOCK_BOUNTY_SCORES = {"invariant_scores": {"healthcheck": 1, "test_db": 80}}

MOCK_REPO_METADATA = {"invariant_thresholds": {"healthcheck": 1, "test_server": 76}}

MOCK_BOUNTY_METADATA = {"invariant_thresholds": {"test_db": 80}}


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
        use_agent_exploit=True,
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
    exit_code = await agent.run_agent_exploit()
    assert exit_code == 1

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=0,
    )
    exit_code = await agent.run_agent_exploit()
    assert exit_code == 0

    write_to_file_and_make_executable(
        script_path=exploit_script_dir,
        exit_code=2,
    )
    exit_code = await agent.run_agent_exploit()
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

    with patch.object(PatchAgent, "_restart_resource", return_value=False):
        with patch.object(PatchAgent, "_apply_patch", return_value=(True, "")):
            await agent.verify_patch(agent_exploit=False)
            assert (
                "one or more resources failed to restart."
                in agent.last_patch_agent_message.message.lower()
            )
            assert agent.patch_id == prev_patch_id + 1


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

    run_exploit_mock = mocker.patch.object(
        patch_agent, "run_agent_exploit", side_effect=[0, 0]
    )
    git_remove_changes_mock: MagicMock = mocker.patch(
        "agents.patch_agent.patch_agent.git_remove_changes"
    )

    # Let invariants pass
    mocker.patch.object(
        patch_agent, "verify_patch_invariants", return_value=(True, {}, {})
    )

    initial_msg = PatchAgentMessage(agent_id="test", message="test message")
    final_msg = await patch_agent.run([initial_msg])

    assert final_msg.success is False
    # You should find "Patch failed: Exploit verification failed" in final_msg or logs
    assert "Patch failed: Exploit verification failed" in final_msg.message
    assert run_exploit_mock.call_count == 2
    assert git_remove_changes_mock.call_count == 2


@pytest.mark.asyncio
async def test_agent_exploit_1_before_patch(patch_agent, mocker):
    """
    Exploit returns 1 unpatched → The agent should log it as an invalid exploit.
    No second run, no patch application.
    """
    patch_agent.use_agent_exploit = True

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")

    run_exploit_mock = mocker.patch.object(
        patch_agent, "run_agent_exploit", return_value=1  # unpatched run
    )
    # Invariants won't matter because we won't even get to patch
    mock_invariants = mocker.patch.object(patch_agent, "verify_patch_invariants")

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

    # Mock Docker run to produce exit_code=0 initially
    docker_run_mock = mocker.patch.object(
        patch_agent.resources.docker,
        "run",
        side_effect=[
            MagicMock(additional_metadata={"exit_code": 1}),
        ],
    )

    # Mock subprocess.run() for verify.sh
    # – The new code’s final exit code is the returncode of verify.sh.
    # – For the "unpatched" run we can return 0 to confirm exploit works.
    # – For the "patched" run we want 1 to confirm exploit is neutralized.
    def mock_subprocess_run(*args, **kwargs):
        class FakeResult:
            def __init__(self, returncode, stdout):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = ""

        # after patch => exploit neutralized => verify returns 1
        return FakeResult(1, "Exploit blocked after patch")

    mocker.patch("subprocess.run", side_effect=mock_subprocess_run)

    # Let invariants pass
    mocker.patch.object(
        patch_agent, "verify_patch_invariants", return_value=(True, {}, {})
    )

    # Run
    initial_msg = PatchAgentMessage(
        agent_id="test", message="run external exploit test"
    )
    final_msg = await patch_agent.run([initial_msg])

    # We expect success
    assert final_msg.success is True
    assert "Congratulations! The patch succeeded." in final_msg.message


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


def test_verify_patch_invariants_success(bounty_setup, patch_agent):
    """Test that verify_patch_invariants returns True when invariant checks succeed."""
    agent = patch_agent
    env_path = bounty_setup

    repo_invariants_script = env_path.TASK_DIR / "run_repo_invariants.sh"
    bounty_invariants_script = env_path.BOUNTY_DIR / "run_bounty_invariants.sh"

    # Create scripts
    write_to_file_and_make_executable(repo_invariants_script, exit_code=0)
    write_to_file_and_make_executable(bounty_invariants_script, exit_code=0)

    # Mock check_invariant_scores_against_thresholds to return True
    with patch.object(
        PatchAgent, "check_invariant_scores_against_thresholds", return_value=True
    ):
        result, _, _ = agent.verify_patch_invariants()

    assert result is True

    # Clean up
    for script in [repo_invariants_script, bounty_invariants_script]:
        if script.exists():
            script.unlink()


def test_verify_patch_invariants_check_fails(bounty_setup, patch_agent):
    """Test that verify_patch_invariants returns False when check_invariant_scores_against_thresholds fails."""
    agent = patch_agent
    env_path = bounty_setup

    repo_invariants_script = env_path.TASK_DIR / "run_repo_invariants.sh"
    bounty_invariants_script = env_path.BOUNTY_DIR / "run_bounty_invariants.sh"

    write_to_file_and_make_executable(repo_invariants_script, exit_code=0)
    write_to_file_and_make_executable(bounty_invariants_script, exit_code=0)

    # Mock check_invariant_scores_against_thresholds to return False
    with patch.object(
        PatchAgent, "check_invariant_scores_against_thresholds", return_value=False
    ):
        result, _, _ = agent.verify_patch_invariants()

    assert result is False

    for script in [repo_invariants_script, bounty_invariants_script]:
        if script.exists():
            script.unlink()


@pytest.mark.asyncio
async def test_patch_success_requires_invariants(patch_agent):
    """Test that patch success requires both exploit check and invariant check to pass."""
    agent = patch_agent
    agent.last_patch_agent_message = PatchAgentMessage(
        agent_id="patch_agent", message=None
    )

    # Mock the verify_patch_invariants method
    with patch.object(
        PatchAgent, "verify_patch_invariants", return_value=(False, {}, {})
    ):
        # Mock exploit success but invariant failure
        with patch.object(PatchAgent, "verify_patch", return_value=True):
            # Mock resource restart
            with patch.object(PatchAgent, "_restart_resource", return_value=True):
                # Mock run_agent_exploit to return success
                with patch.object(
                    PatchAgent, "run_agent_exploit"
                ) as mock_run_agent_exploit:
                    # Create a mock response
                    mock_response = MagicMock()
                    mock_response.additional_metadata = {"exit_code": 1}
                    mock_response.message = "Success"
                    mock_run_agent_exploit.return_value = mock_response

                    await agent.execute()
                    assert "failed" in agent.last_patch_agent_message.message.lower()
                    assert not agent.last_patch_agent_message.success


def test_check_invariant_scores_against_thresholds_success(patch_agent):
    """Test that check_invariant_scores_against_thresholds returns True when scores meet thresholds."""
    agent = patch_agent

    # Create temporary files
    repo_metadata_file = Path("repo_metadata.json")
    bounty_metadata_file = Path("bounty_metadata.json")
    repo_invariant_scores = Path("repo_scores.json")
    bounty_invariant_scores = Path("bounty_scores.json")

    # Write test data to files
    repo_metadata_file.write_text(json.dumps(MOCK_REPO_METADATA))
    bounty_metadata_file.write_text(json.dumps(MOCK_BOUNTY_METADATA))
    repo_invariant_scores.write_text(json.dumps(MOCK_REPO_SCORES))
    bounty_invariant_scores.write_text(json.dumps(MOCK_BOUNTY_SCORES))

    try:
        # Test with all scores meeting thresholds
        result = agent.check_invariant_scores_against_thresholds(
            repo_metadata_file,
            bounty_metadata_file,
            repo_invariant_scores,
            bounty_invariant_scores,
        )
        assert result is True
    finally:
        # Clean up
        for file in [
            repo_metadata_file,
            bounty_metadata_file,
            repo_invariant_scores,
            bounty_invariant_scores,
        ]:
            if file.exists():
                file.unlink()


def test_verify_patch_invariants_success_returns_scores(patch_agent):
    """Test that verify_patch_invariants returns True when scores meet thresholds, and returns the scores."""
    with (
        tempfile.TemporaryDirectory() as tmpdir
    ):  # this is a context manager so we don't have to clean up
        task_dir = Path(tmpdir) / "task"
        bounty_dir = Path(tmpdir) / "bounty"
        task_dir.mkdir()
        bounty_dir.mkdir()

        (task_dir / "metadata.json").write_text(json.dumps(MOCK_REPO_METADATA))
        (task_dir / "invariant_scores.json").write_text(json.dumps(MOCK_REPO_SCORES))
        (bounty_dir / "bounty_metadata.json").write_text(
            json.dumps(MOCK_BOUNTY_METADATA)
        )
        (bounty_dir / "invariant_scores.json").write_text(
            json.dumps(MOCK_BOUNTY_SCORES)
        )

        agent = patch_agent
        agent.task_dir = task_dir
        agent.bounty_dir = bounty_dir

        with patch.object(
            PatchAgent, "check_invariant_scores_against_thresholds", return_value=True
        ):
            result, repo_scores, bounty_scores = agent.verify_patch_invariants()

        assert result is True
        assert repo_scores == MOCK_REPO_SCORES
        assert bounty_scores == MOCK_BOUNTY_SCORES


def test_verify_patch_invariants_failure_returns_scores(patch_agent):
    """Test that verify_patch_invariants returns False when scores meet thresholds, and still return the scores."""
    with (
        tempfile.TemporaryDirectory() as tmpdir
    ):  # this is a context manager so we don't have to clean up
        task_dir = Path(tmpdir) / "task"
        bounty_dir = Path(tmpdir) / "bounty"
        task_dir.mkdir()
        bounty_dir.mkdir()

        (task_dir / "metadata.json").write_text(json.dumps(MOCK_REPO_METADATA))
        (task_dir / "invariant_scores.json").write_text(json.dumps(MOCK_REPO_SCORES))
        (bounty_dir / "bounty_metadata.json").write_text(
            json.dumps(MOCK_BOUNTY_METADATA)
        )
        (bounty_dir / "invariant_scores.json").write_text(
            json.dumps(MOCK_BOUNTY_SCORES)
        )

        agent = patch_agent
        agent.task_dir = task_dir
        agent.bounty_dir = bounty_dir

        with patch.object(
            PatchAgent, "check_invariant_scores_against_thresholds", return_value=False
        ):
            result, repo_scores, bounty_scores = agent.verify_patch_invariants()

        assert result is False
        assert repo_scores == MOCK_REPO_SCORES
        assert bounty_scores == MOCK_BOUNTY_SCORES


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
        files["repo_scores"].write_text(json.dumps(MOCK_REPO_SCORES))
        files["bounty_scores"].write_text(json.dumps(MOCK_BOUNTY_SCORES))

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


@pytest.mark.asyncio
async def test_reset_repo_on_empty_diff(patch_agent, mocker):
    """
    Test that the repo is not reset if git diff returns an empty diff.
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value=None)
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(False, "Patch failed"),
    )
    git_remove_changes_mock: MagicMock = mocker.patch(
        "agents.patch_agent.patch_agent.git_remove_changes"
    )

    result = await agent.execute()

    git_remove_changes_mock.assert_not_called()
    assert result is False
    assert (
        agent.patch_id == prev_patch_id
    )  # patch is skipped so patch_id should not increment


# Test that the system correctly makes calls to git_remove_changes
# -----------------------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reset_repo_on_restart_resources_fail(patch_agent, mocker):
    """
    Test that tmp and remote codebase are reset to their original states if patch creation and apply was successful,
    but restarting the resources fails.
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(True, "Patch succeeded"),
    )
    git_remove_changes_mock: MagicMock = mocker.patch(
        "agents.patch_agent.patch_agent.git_remove_changes"
    )

    mocker.patch.object(
        PatchAgent, "restart_resources", return_value=False
    )  # Restart resource fails
    result = await agent.verify_patch(agent_exploit=False)

    assert git_remove_changes_mock.call_count == 2
    assert result is False
    assert agent.patch_id == prev_patch_id + 1


@pytest.mark.asyncio
async def test_reset_repo_on_patch_creation_fail(patch_agent, mocker):
    """
    Test that tmp and remote codebase are reset to their original states if
    patch creation failed.
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch.object(
        PatchAgent,
        "create_patch_file",
        side_effect=Exception("Failed to create patch file"),
    )

    git_remove_changes_mock = mocker.patch(
        "agents.patch_agent.patch_agent.git_remove_changes"
    )
    result = await agent.verify_patch(agent_exploit=False)

    assert git_remove_changes_mock.call_count == 2
    assert result is False
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
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(False, "Patch failed"),
    )

    git_remove_changes_mock = mocker.patch(
        "agents.patch_agent.patch_agent.git_remove_changes"
    )
    result = await agent.verify_patch(agent_exploit=False)

    assert git_remove_changes_mock.call_count == 2
    assert result is False
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
    mocker.patch.object(
        PatchAgent, "verify_patch_invariants", return_value=(False, {}, {})
    )
    mocker.patch.object(PatchAgent, "apply_patched_unit_tests", return_value=True)
    mocker.patch.object(
        PatchAgent,
        "merge_max_scores",
        side_effect=[MOCK_REPO_SCORES, MOCK_BOUNTY_SCORES],
    )

    git_remove_changes_mock = mocker.patch(
        "agents.patch_agent.patch_agent.git_remove_changes"
    )
    result = await agent.verify_patch(agent_exploit=False)

    assert git_remove_changes_mock.call_count == 2
    assert result is False
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

    # Commit states
    initial_commit = "abc123"
    current_commits = {"tmp": initial_commit, "remote": initial_commit}

    def mock_get_current_commit(repo_path):
        if str(agent.task_dir / "codebase") in str(repo_path):
            return current_commits["remote"]
        return current_commits["tmp"]

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch(
        "agents.patch_agent.patch_agent.git_get_current_commit",
        side_effect=mock_get_current_commit,
    )
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(True, "Patch applied successfully"),
    )
    mocker.patch("agents.patch_agent.patch_agent.git_remove_changes")

    agent.last_patch_agent_message = PatchAgentMessage(
        agent_id="patch_agent", message=None
    )

    # Mock invariant/exploit checks
    mocker.patch.object(
        patch_agent, "verify_patch_invariants", return_value=(True, {}, {})
    )
    mocker.patch.object(
        patch_agent, "run_external_exploit", return_value=0
    )  # 0 indicates failure (exploit still works)

    result = await agent.verify_patch(agent_exploit=False)

    assert result is False
    assert current_commits["tmp"] == initial_commit
    assert current_commits["remote"] == initial_commit
    assert agent.last_patch_agent_message.success is False
    assert "Patch failed" in agent.last_patch_agent_message.message
    assert agent.patch_id == prev_patch_id + 1


@pytest.mark.asyncio
async def test_full_workflow_success(patch_agent, mocker):
    """
    Test the full patch workflow with commit tracking:
    - Start with both repos in the same initial state
    - Apply patch successfully
    - Verify success is reported correctly
    """
    agent = patch_agent
    prev_patch_id = agent.patch_id

    # Commit states
    initial_commit = "abc123"
    current_commits = {"tmp": initial_commit, "remote": initial_commit}

    def mock_get_current_commit(repo_path):
        if str(agent.task_dir / "codebase") in str(repo_path):
            return current_commits["remote"]
        return current_commits["tmp"]

    mocker.patch("agents.patch_agent.patch_agent.git_diff", return_value="FAKE_DIFF")
    mocker.patch(
        "agents.patch_agent.patch_agent.git_get_current_commit",
        side_effect=mock_get_current_commit,
    )
    mocker.patch(
        "agents.patch_agent.patch_agent.git_apply_patch",
        return_value=(True, "Patch applied successfully"),
    )

    agent.last_patch_agent_message = PatchAgentMessage(
        agent_id="patch_agent", message=None
    )

    # Mock invariant/exploit checks
    mocker.patch.object(
        patch_agent, "verify_patch_invariants", return_value=(True, {}, {})
    )
    mocker.patch.object(
        patch_agent, "run_external_exploit", return_value=1
    )  # 1 indicates success (exploit blocked)

    agent.use_agent_exploit = False
    result = await agent.execute()

    assert result is True
    assert current_commits["tmp"] == initial_commit
    assert current_commits["remote"] == initial_commit
    assert agent.last_patch_agent_message.success is True
    assert "Congratulations" in agent.last_patch_agent_message.message


# "uses" the import
if None:
    bounty_setup
