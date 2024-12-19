import os
import stat
import subprocess
import time
import pytest
from pathlib import Path
import unittest

from responses.command_response import CommandResponse
from responses.answer_response import AnswerResponse
from responses.patch_response import PatchResponse
from resources.init_files_resource import InitFilesResource
from resources.docker_resource import DockerResource
from agents.patch_agent.patch_agent import PatchAgent

@pytest.fixture
def init_files(tmp_path):
    # Setup directories used by PatchAgent
    (tmp_path / "codebase").mkdir()
    (tmp_path / "tmp").mkdir()
    class MockInitFiles:
        task_repo_dir = str(tmp_path)
        files_dir = str(tmp_path / "codebase")
        tmp_dir = str(tmp_path / "tmp")
    return MockInitFiles()

@pytest.fixture
def docker_resource():
    # Create the DockerResource
    dr = DockerResource("test_docker_resource")
    
    # Provide the resource to the test
    yield dr
    
    # Cleanup code after the test finishes
    dr.stop()

@pytest.fixture
def patch_agent(init_files, docker_resource, tmp_path):
    class MockTaskServer:
        def restart(self):
            pass

    class MockRepoResource:
        def restart(self):
            pass

    # Create exploit_files directory
    exploit_dir = tmp_path / "exploit_files"
    exploit_dir.mkdir()

    agent = PatchAgent(
        bounty_dir=str(tmp_path),
        init_files=init_files,
        docker=docker_resource,
        task_server=MockTaskServer(),
        repo_resource=MockRepoResource()
    )
    return agent

def make_executable(script_path: Path):
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)

@pytest.fixture
def exploit_script(tmp_path):
    """
    Creates a default exploit.sh script. We will override its content per test case.
    """
    script = tmp_path / "exploit_files" / "exploit.sh"
    script.write_text("#!/usr/bin/env bash\necho 'Default Exploit'\nexit 0\n")
    make_executable(script)
    return script

@pytest.fixture
def verify_script(tmp_path):
    """
    Creates a default verify.sh script. We'll override its content per test case as needed.
    """
    script = tmp_path / "verify.sh"
    # Default: check if input contains 'Success' → return 1 (success),
    # otherwise return 0 (fail).
    # Adjust logic as needed for your scenario.
    script.write_text("#!/usr/bin/env bash\nINPUT=$1\nif echo \"$INPUT\" | grep -q 'Success'; then exit 1; else exit 0; fi\n")
    make_executable(script)
    return script

def test_no_verify_sh_exploit_returns_1(patch_agent, exploit_script):
    """
    No verify.sh used. Exploit should return 0 or 1.
    If exploit returns 1 → Patch succeeded.
    """
    patch_agent.use_verify_script = False

    # Modify exploit.sh to return exit code 1
    exploit_script.write_text("#!/usr/bin/env bash\necho 'Exploit after patch'\nexit 1\n")
    make_executable(exploit_script)

    cmd_response = CommandResponse("simulate patch command")
    result = patch_agent.execute(cmd_response)
    assert isinstance(result, AnswerResponse)
    assert "patch succeeded" in result.response.lower()

def test_no_verify_sh_exploit_returns_0(patch_agent, exploit_script):
    """
    No verify.sh used. Exploit returns 0 → patch failed.
    """
    patch_agent.use_verify_script = False

    # By default exploit_script returns exit 0 (from fixture)
    cmd_response = CommandResponse("simulate patch command")
    result = patch_agent.execute(cmd_response)
    assert isinstance(result, PatchResponse)
    assert "patch failed" in result.response.lower()

def test_no_verify_sh_exploit_invalid_exit_code(patch_agent, exploit_script):
    """
    No verify.sh used. Exploit must return 0 or 1.
    If it returns something else, we consider that patch failed.
    """
    patch_agent.use_verify_script = False

    # Make exploit.sh return exit code 2, which is invalid for our scenario
    exploit_script.write_text("#!/usr/bin/env bash\necho 'Invalid code'\nexit 2\n")
    make_executable(exploit_script)

    cmd_response = CommandResponse("simulate patch command")
    # If exploit returns code != 0 or 1, we want patch failed scenario.
    # Since code 2 is not what we want, we treat it as exploit succeeded scenario (which means patch failed)
    # or we can assert patch fails. Let's assume we treat any non-(0 or 1) as exploit=0 scenario.
    result = patch_agent.execute(cmd_response)
    # Should result in patch failed
    assert isinstance(result, PatchResponse)
    assert "patch failed" in result.response.lower()

def test_with_verify_sh_success(patch_agent, exploit_script, verify_script):
    """
    Using verify.sh. Exploit can return any exit code or message.
    Success is determined by verify.sh returning 1.
    By default, verify.sh checks if 'Success' in output → exit 1 (success).
    """
    patch_agent.use_verify_script = True

    # Let exploit.sh print 'Operation Success' so verify.sh returns 1 (success).
    exploit_script.write_text("#!/usr/bin/env bash\necho 'Operation Success'\n") 
    make_executable(exploit_script)

    cmd_response = CommandResponse("simulate patch command")
    result = patch_agent.execute(cmd_response)
    assert isinstance(result, AnswerResponse)
    assert "patch succeeded" in result.response.lower()

def test_with_verify_sh_fail(patch_agent, exploit_script, verify_script):
    """
    Using verify.sh. If verify.sh returns 0, patch failed.
    No 'Success' in output → verify.sh returns 0.
    """
    patch_agent.use_verify_script = True

    # Exploit does not print 'Success', so verify.sh returns 0
    exploit_script.write_text("#!/usr/bin/env bash\necho 'Some other message'\n")
    make_executable(exploit_script)

    cmd_response = CommandResponse("simulate patch command")
    result = patch_agent.execute(cmd_response)
    assert isinstance(result, PatchResponse)
    assert "patch failed" in result.response.lower()


if __name__ == '__main__':
    unittest.main()
