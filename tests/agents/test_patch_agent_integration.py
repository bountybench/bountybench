import os
import shutil
import time
from pathlib import Path

import pytest

from agents.agent_manager import AgentManager
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from tests.test_utils.bounty_setup_test_util import EnvPath
from tests.test_utils.bounty_setup_test_util import (
    lunary_bounty_0_setup as bounty_setup,
)
from tests.test_utils.lunary_bounty_0_scripts import (
    LUNARY_BOUNTY_0_AGENT_EXPLOIT_FAILING,
    LUNARY_BOUNTY_0_AGENT_EXPLOIT_VALID,
    LUNARY_BOUNTY_0_PATCH_FAIL,
    LUNARY_BOUNTY_0_PATCH_RESOURCE_RESTART_FAIL,
    LUNARY_BOUNTY_0_PATCH_VALID_P1,
    LUNARY_BOUNTY_0_PATCH_VALID_P2,
    LUNARY_BOUNTY_0_VERIFY_PYTHON_SCRIPT,
)
from utils.git_utils import git_diff, git_reset


# Helpers
def create_codebase_change(env_path: EnvPath, filename, content):
    """
    Writes content to a specific file in the tmp codebase used by the agent.
    """
    test_file: Path = env_path.TMP_CODEBASE_FILES_DIR / filename
    test_file.write_text(content)
    print(f"Created code change in {test_file}")

    # Verify the file was created
    if not test_file.exists():
        print(f"WARNING: Failed to create {test_file}")

    # Verify git will detect the change
    diff = git_diff(env_path.TMP_CODEBASE_FILES_DIR)
    if not diff:
        print(f"WARNING: No git diff detected after creating {test_file}")
    else:
        print(f"Git diff detected change in {test_file}")


def create_detect_git_diff(env_path: EnvPath):
    """
    Creates a code change that will be detected by git diff.
    """
    create_codebase_change(env_path, "temp.txt", "This is a test change.")


def create_exploit(env_path: EnvPath, filename, content):
    """
    Creates an exploit-related file in the tmp directory used by the agent.
    """
    file_path: Path = env_path.TMP_DIR / filename
    file_path.write_text(content)
    print(f"Created {filename} in {env_path.TMP_DIR}")
    return file_path


def reset_environment(env_path: EnvPath):
    """
    Resets the integration test environment to a clean state.
    """
    print("Resetting integration test environment...")
    # Reset git repositories
    if env_path.TMP_CODEBASE_FILES_DIR.exists():
        git_reset(env_path.TMP_CODEBASE_FILES_DIR)

    # Remove the exploit.sh file if it exists
    exploit_path = env_path.TMP_DIR / "exploit.sh"
    if exploit_path.exists():
        os.unlink(exploit_path)

    # Clean any patch files
    for patch_dir in env_path.AGENT_PATCHES_DIR.glob("patch_*"):
        if patch_dir.exists() and patch_dir.is_dir():
            shutil.rmtree(patch_dir)
            print(f"Removed patch directory: {patch_dir}")


async def test_scenario_0_no_git_diff(
    agent: PatchAgent, initial_msg: PatchAgentMessage, env_path: EnvPath
):
    """
    Scenario 0: No git diff detected, agent should skip patching.
    """
    reset_environment(env_path)

    result: PatchAgentMessage = await agent.run([initial_msg])
    print(f"SCENARIO 0 RESULT: success={result.success}")
    print(f"SCENARIO 0 MESSAGE: {result.message}")

    assert not result.success
    assert "no git diff detected" in result.message.lower()
    return result


async def test_scenario_1_no_exploit_file(
    agent: PatchAgent, initial_msg: PatchAgentMessage, env_path: EnvPath
):
    """
    Scenario 1: Git diff detected but no exploit.sh file present.
    """
    reset_environment(env_path)
    create_detect_git_diff(env_path)

    result = await agent.run([initial_msg])
    print(f"SCENARIO 1 RESULT: success={result.success}")
    print(f"SCENARIO 1 MESSAGE: {result.message}")

    assert not result.success
    assert "exploit.sh not found" in result.message.lower()
    return result


async def test_scenario_2_failing_exploit(
    agent: PatchAgent, initial_msg: PatchAgentMessage, env_path: EnvPath
):
    """
    Scenario 2: Agent provides exploit.sh but it fails before patch.
    """
    reset_environment(env_path)
    create_detect_git_diff(env_path)
    create_exploit(env_path, "exploit.sh", LUNARY_BOUNTY_0_AGENT_EXPLOIT_FAILING)

    result = await agent.run([initial_msg])
    print(f"SCENARIO 2 RESULT: success={result.success}")
    print(f"SCENARIO 2 MESSAGE: {result.message}")

    assert not result.success
    assert "exploit fails before the patch is applied" in result.message.lower()
    return result


async def test_scenario_3_resource_restart_fails(
    agent: PatchAgent, initial_msg: PatchAgentMessage, env_path: EnvPath
):
    """
    Scenario 3: Exploit succeeds before patch, but resource restart fails with patch.
    """
    reset_environment(env_path)
    create_exploit(env_path, "exploit.sh", LUNARY_BOUNTY_0_AGENT_EXPLOIT_VALID)
    create_exploit(env_path, "verify_state.py", LUNARY_BOUNTY_0_VERIFY_PYTHON_SCRIPT)
    create_codebase_change(
        env_path,
        "packages/backend/src/utils/db.ts",
        LUNARY_BOUNTY_0_PATCH_RESOURCE_RESTART_FAIL,
    )

    result = await agent.run([initial_msg])
    print(f"SCENARIO 3 RESULT: success={result.success}")
    print(f"SCENARIO 3 MESSAGE: {result.message}")

    assert not result.success
    assert "exploit succeeds" in result.message.lower()
    assert "patch is invalid" in result.message.lower()
    return result


async def test_scenario_4_patch_fails(
    agent: PatchAgent, initial_msg: PatchAgentMessage, env_path: EnvPath
):
    """
    Scenario 4: Exploit succeeds before patch, patch applied, but exploit still succeeds after patch.
    """
    reset_environment(env_path)
    create_exploit(env_path, "exploit.sh", LUNARY_BOUNTY_0_AGENT_EXPLOIT_VALID)
    create_exploit(env_path, "verify_state.py", LUNARY_BOUNTY_0_VERIFY_PYTHON_SCRIPT)
    create_codebase_change(
        env_path,
        "packages/backend/src/utils/authorization.ts",
        LUNARY_BOUNTY_0_PATCH_FAIL,
    )

    result = await agent.run([initial_msg])
    print(f"SCENARIO 4 RESULT: success={result.success}")
    print(f"SCENARIO 4 MESSAGE: {result.message}")

    assert not result.success
    assert "successfully restarted associated resources" in result.message.lower()
    assert "exploit check failed" in result.message.lower()
    return result


async def test_scenario_5_happy_path(
    agent: PatchAgent, initial_msg: PatchAgentMessage, env_path: EnvPath
):
    """
    Scenario 5: Happy path - patch successfully fixes the vulnerability.
    """
    reset_environment(env_path)
    create_exploit(env_path, "exploit.sh", LUNARY_BOUNTY_0_AGENT_EXPLOIT_VALID)
    create_exploit(env_path, "verify_state.py", LUNARY_BOUNTY_0_VERIFY_PYTHON_SCRIPT)
    create_codebase_change(
        env_path,
        "packages/backend/src/utils/authorization.ts",
        LUNARY_BOUNTY_0_PATCH_VALID_P1,
    )
    create_codebase_change(
        env_path,
        "packages/backend/src/api/v1/projects/index.ts",
        LUNARY_BOUNTY_0_PATCH_VALID_P2,
    )

    result = await agent.run([initial_msg])
    print(f"SCENARIO 5 RESULT: success={result.success}")
    print(f"SCENARIO 5 MESSAGE: {result.message}")

    assert result.success
    assert "successfully restarted associated resources" in result.message.lower()
    assert "exploit check passed" in result.message.lower()
    return result


@pytest.mark.asyncio
async def test_patch_agent_multi_scenario_integration(bounty_setup):
    """
    Integration test that runs a single patch agent through multiple scenarios.
    This test uses real exploits and resources with no mocking.
    """
    # Environment setup
    env_path: EnvPath = bounty_setup

    # Agent setup
    initial_msg = PatchAgentMessage(agent_id="test_patch_agent", message="Test message")

    agent_manager = AgentManager(workflow_id="1")
    config = PatchAgentConfig(
        bounty_dir=env_path.BOUNTY_DIR,
        task_dir=env_path.TASK_DIR,
        use_agent_exploit=True,
        resource_restart_retry_attempts=1,
    )
    agent = agent_manager.create_agent("test_patch_agent", PatchAgent, config)

    print("\nTest environment paths:")
    print(f"TASK_DIR: {env_path.TASK_DIR}")
    print(f"BOUNTY_DIR: {env_path.BOUNTY_DIR}")
    print(f"TMP_DIR: {env_path.TMP_DIR}")
    print(f"TMP_EXPLOIT_SCRIPT_DIR: {env_path.TMP_EXPLOIT_SCRIPT_DIR}")
    print(f"AGENT_PATCHES_DIR: {env_path.AGENT_PATCHES_DIR}")

    # Currently running sequentially, but can duplicate/remove any calls as needed
    await test_scenario_0_no_git_diff(agent, initial_msg, env_path)
    await test_scenario_1_no_exploit_file(agent, initial_msg, env_path)
    await test_scenario_2_failing_exploit(agent, initial_msg, env_path)
    await test_scenario_3_resource_restart_fails(agent, initial_msg, env_path)
    await test_scenario_4_patch_fails(agent, initial_msg, env_path)
    await test_scenario_5_happy_path(agent, initial_msg, env_path)
