import shutil
import subprocess
from pathlib import Path

import pytest

from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig


@pytest.fixture
def setup_dirs():
    task_repo_dir = Path.cwd() / "tests" / "resources" / "test_files"
    tmp_dir_name = "tmp_dir_for_testing"
    tmp_dir = task_repo_dir / tmp_dir_name
    original_files_dir = task_repo_dir / "original_files"
    bounty_dir = task_repo_dir / "bounties" / "bounty_1234"
    verify_files_dir = bounty_dir / "verify_files"
    verify_file_path = verify_files_dir / "verify.sh"

    if task_repo_dir.exists():
        shutil.rmtree(task_repo_dir)

    # Create necessary directories
    original_files_dir.mkdir(parents=True, exist_ok=True)
    bounty_dir.mkdir(parents=True, exist_ok=True)
    verify_files_dir.mkdir(parents=True, exist_ok=True)

    # Create test files
    (original_files_dir / "test_file.txt").write_text("This is a test.")
    verify_file_path.write_text("#!/bin/bash\necho 'verify script'\nexit 0")
    (verify_files_dir / "helper.sh").write_text(
        "#!/bin/bash\necho 'helper script'\nexit 0"
    )

    subprocess.run(["git", "init"], cwd=original_files_dir)
    subprocess.run(["git", "add", "."], cwd=original_files_dir)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=original_files_dir)
    subprocess.run(["git", "branch", "-m", "main"], cwd=original_files_dir)

    config = InitFilesResourceConfig(
        task_dir=task_repo_dir,
        files_dir_name="original_files",
        tmp_dir=tmp_dir,
        bounty_number="1234",
        vulnerable_commit="HEAD",
        input_verify_files_dir_name="verify_files",
    )

    yield config, tmp_dir, original_files_dir, bounty_dir

    if task_repo_dir.exists():
        shutil.rmtree(task_repo_dir)


@pytest.fixture
def resource(setup_dirs):
    config, tmp_dir, original_files_dir, _ = setup_dirs  # Ignore the bounty_dir
    return InitFilesResource(resource_id="test_resource", config=config)


def test_setup_repo(resource, setup_dirs):
    _, tmp_dir, _, _ = setup_dirs
    repo_path = tmp_dir / "original_files"
    git_dir = repo_path / ".git"

    assert git_dir.exists(), "Git repository was not initialized."

    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert result.stdout.strip() == "1", "Initial commit not found."


def test_stop(resource, setup_dirs):
    _, tmp_dir, original_files_dir, _ = setup_dirs
    repo_path = tmp_dir / "original_files"
    subprocess.run(["git", "checkout", "-b", "dev"], cwd=repo_path)
    resource.stop()
    assert not tmp_dir.exists()
    branch_result = subprocess.run(
        ["git", "branch"], cwd=original_files_dir, stdout=subprocess.PIPE, text=True
    )
    assert "dev" not in branch_result.stdout, "Branch 'dev' was not removed."


def test_remove_tmp(resource, setup_dirs):
    _, tmp_dir, _, _ = setup_dirs
    (tmp_dir / "subdir").mkdir(parents=True, exist_ok=True)
    (tmp_dir / "subdir" / "tempfile.txt").write_text("Temporary file")
    assert (tmp_dir / "subdir" / "tempfile.txt").exists()
    resource.remove_tmp()
    assert not tmp_dir.exists()


def test_safe_remove(resource, setup_dirs):
    _, tmp_dir, _, _ = setup_dirs
    test_file_path = tmp_dir / "testfile.txt"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    test_file_path.write_text("This is a test file")
    resource.safe_remove(test_file_path)
    assert not test_file_path.exists()
    test_dir_path = tmp_dir / "testdir"
    test_dir_path.mkdir(parents=True, exist_ok=True)
    resource.safe_remove(test_dir_path)
    assert not test_dir_path.exists()


def test_verify_files_copy(resource, setup_dirs):
    _, tmp_dir, _, bounty_dir = setup_dirs

    # Ensure source directories and files exist
    source_verify_files_dir = bounty_dir / "verify_files"
    source_helper_file = source_verify_files_dir / "helper.sh"

    assert (
        source_verify_files_dir.exists()
    ), "Source verify_files directory does not exist"
    assert source_helper_file.exists(), "Source helper.sh file does not exist"

    # Get the actual input_verify_files_dir path from the resource
    resource_input_verify_files_dir = resource.input_verify_files_dir
    print(f"Source verify_files directory: {source_verify_files_dir}")
    print(f"Resource input_verify_files_dir: {resource_input_verify_files_dir}")
    print(f"Temp directory: {tmp_dir}")

    # Check that verify.sh was copied
    verify_file_path = tmp_dir / "verify_files" / "verify.sh"
    assert verify_file_path.exists(), "verify.sh file was not copied"
    assert (
        "verify script" in verify_file_path.read_text()
    ), "verify.sh content is incorrect"

    # Check that verify.sh was copied
    helper_file_path = tmp_dir / "verify_files" / "helper.sh"
    assert helper_file_path.exists(), "helper.sh file was not copied"
    assert (
        "helper script" in helper_file_path.read_text()
    ), "helper.sh content is incorrect"
