import os
import shutil
import time
from pathlib import Path

import pytest

from agents.agent_manager import AgentManager
from agents.patch_agent.patch_agent import PatchAgent, PatchAgentConfig
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from tests.test_utils.bounty_setup_test_util import (
    LUNARY_BOUNTY_0_EXPLOIT_FAILING,
    LUNARY_BOUNTY_0_EXPLOIT_VALID,
    LUNARY_BOUNTY_0_PATCH_FAIL,
    LUNARY_BOUNTY_0_PATCH_RESOURCE_RESTART_FAIL,
    LUNARY_BOUNTY_0_PATCH_VALID,
    LUNARY_BOUNTY_0_VERIFY_VALID,
    EnvPath,
)
from tests.test_utils.bounty_setup_test_util import (
    lunary_bounty_0_setup as bounty_setup,
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
    file_path: Path = env_path.TMP_DIR / filename
    file_path.write_text(content)
    print(f"Created {filename} in {env_path.TMP_DIR}")
    return file_path


def reset_environment(env_path: EnvPath):
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


@pytest.mark.asyncio
async def test_patch_agent_multi_scenario_integration(bounty_setup):
    """
    Integration test that runs a single patch agent through multiple iterations.
    This test uses real exploits and resources with no mocking.
    """
    # Env setup
    env_path: EnvPath = bounty_setup

    # Agent setup
    initial_msg = PatchAgentMessage(agent_id="test_patch_agent", message="Test message")

    agent_manager = AgentManager(workflow_id="1")
    config = PatchAgentConfig(
        bounty_dir=env_path.BOUNTY_DIR,
        task_dir=env_path.TASK_DIR,
        use_agent_exploit=True,
    )
    agent = agent_manager.create_agent("test_patch_agent", PatchAgent, config)

    print("\nTest environment paths:")
    print(f"TASK_DIR: {env_path.TASK_DIR}")
    print(f"BOUNTY_DIR: {env_path.BOUNTY_DIR}")
    print(f"TMP_DIR: {env_path.TMP_DIR}")
    print(f"TMP_EXPLOIT_SCRIPT_DIR: {env_path.TMP_EXPLOIT_SCRIPT_DIR}")
    print(f"AGENT_PATCHES_DIR: {env_path.AGENT_PATCHES_DIR}")

    # Iteration 0: No git diff detected, skip patching
    result_0 = await agent.run([initial_msg])
    print(f"SCENARIO 0 RESULT: success={result_0.success}")
    print(f"SCENARIO 0 MESSAGE: {result_0.message}")
    assert not result_0.success
    assert "no git diff detected" in result_0.message.lower()

    # Iteration 1: No exploit.sh file
    # - resources/init_files_resource.py:229 copies all files, including exploit.sh to tmp
    # - we will first remove the exploit.sh file to simulate the scenario
    reset_environment(env_path)
    create_detect_git_diff(env_path)

    result_1 = await agent.run([initial_msg])
    print(f"SCENARIO 1 RESULT: success={result_1.success}")
    print(f"SCENARIO 1 MESSAGE: {result_1.message}")
    assert not result_1.success
    assert "exploit.sh not found" in result_1.message.lower()

    # Iteration 2: Agent provides exploit.sh
    # - fail before patch
    reset_environment(env_path)
    create_detect_git_diff(env_path)

    create_exploit(env_path, "exploit.sh", LUNARY_BOUNTY_0_EXPLOIT_FAILING)
    result_2 = await agent.run([initial_msg])
    print(f"SCENARIO 2 RESULT: success={result_2.success}")
    print(f"SCENARIO 2 MESSAGE: {result_2.message}")
    assert not result_2.success
    assert "exploit fails before the patch is applied" in result_2.message.lower()

    # Iteration 3: Agent provides exploit.sh
    # - succeeds before patch; restart resource fails with patch
    # - exploit.sh can be mocked by our own version in bountybench
    reset_environment(env_path)
    create_detect_git_diff(env_path)

    create_exploit(env_path, "exploit.sh", LUNARY_BOUNTY_0_EXPLOIT_VALID)
    create_codebase_change(
        env_path,
        "packages/backend/src/utils/db.ts",
        LUNARY_BOUNTY_0_PATCH_RESOURCE_RESTART_FAIL,
    )
    result_3 = await agent.run([initial_msg])
    print(f"SCENARIO 3 RESULT: success={result_3.success}")
    print(f"SCENARIO 3 MESSAGE: {result_3.message}")

    assert not result_3.success
    assert "exploit succeeds" in result_3.message.lower()
    assert "patch is invalid" in result_3.message.lower()

    # Iteration 4: Agent provides exploit.sh
    # - succeeds before patch; patch applied; still succeeds after patch (patch fails)
    reset_environment(env_path)
    create_detect_git_diff(env_path)

    create_exploit(env_path, "exploit.sh", LUNARY_BOUNTY_0_EXPLOIT_VALID)
    create_codebase_change(
        env_path,
        "packages/backend/src/utils/authorization.ts",
        LUNARY_BOUNTY_0_PATCH_FAIL,
    )

    result_4 = await agent.run([initial_msg])
    print(f"SCENARIO 4 RESULT: success={result_4.success}")
    print(f"SCENARIO 4 MESSAGE: {result_4.message}")
    assert not result_4.success

    assert "successfully restarted associated resources" in result_4.message.lower()
    assert "exploit check failed" in result_4.message.lower()

    # Iteration 5: Happy path
    reset_environment(env_path)
    create_detect_git_diff(env_path)
    create_exploit(env_path, "exploit.sh", LUNARY_BOUNTY_0_EXPLOIT_VALID)
    create_codebase_change(
        env_path,
        "packages/backend/src/utils/authorization.ts",
        LUNARY_BOUNTY_0_PATCH_VALID,
    )
    result_5 = await agent.run([initial_msg])
    print(f"SCENARIO 5 RESULT: success={result_5.success}")
    print(f"SCENARIO 5 MESSAGE: {result_5.message}")
    assert result_5.success

    assert "successfully restarted associated resources" in result_5.message.lower()
    assert "exploit check succeeded" in result_5.message.lower()
