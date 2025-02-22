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

    if task_repo_dir.exists():
        shutil.rmtree(task_repo_dir)
    original_files_dir.mkdir(parents=True, exist_ok=True)

    (original_files_dir / "test_file.txt").write_text("This is a test.")

    subprocess.run(["git", "init"], cwd=original_files_dir)
    subprocess.run(["git", "add", "."], cwd=original_files_dir)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=original_files_dir)
    subprocess.run(["git", "branch", "-m", "main"], cwd=original_files_dir)

    config = InitFilesResourceConfig(
        task_dir=task_repo_dir,
        files_dir_name="original_files",
        tmp_dir_name=tmp_dir_name,
        bounty_number="1234",
        vulnerable_commit="HEAD",
    )

    yield config, tmp_dir, original_files_dir

    if task_repo_dir.exists():
        shutil.rmtree(task_repo_dir)


@pytest.fixture
def resource(setup_dirs):
    config, tmp_dir, original_files_dir = setup_dirs
    return InitFilesResource(resource_id="test_resource", config=config)


def test_setup_repo(resource, setup_dirs):
    _, tmp_dir, _ = setup_dirs
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
    _, tmp_dir, original_files_dir = setup_dirs
    repo_path = tmp_dir / "original_files"
    subprocess.run(["git", "checkout", "-b", "dev"], cwd=repo_path)
    resource.stop()
    assert not tmp_dir.exists()
    branch_result = subprocess.run(
        ["git", "branch"], cwd=original_files_dir, stdout=subprocess.PIPE, text=True
    )
    assert "dev" not in branch_result.stdout, "Branch 'dev' was not removed."


def test_remove_tmp(resource, setup_dirs):
    _, tmp_dir, _ = setup_dirs
    (tmp_dir / "subdir").mkdir(parents=True, exist_ok=True)
    (tmp_dir / "subdir" / "tempfile.txt").write_text("Temporary file")
    assert (tmp_dir / "subdir" / "tempfile.txt").exists()
    resource.remove_tmp()
    assert not tmp_dir.exists()


def test_safe_remove(resource, setup_dirs):
    _, tmp_dir, _ = setup_dirs
    test_file_path = tmp_dir / "testfile.txt"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    test_file_path.write_text("This is a test file")
    resource.safe_remove(test_file_path)
    assert not test_file_path.exists()
    test_dir_path = tmp_dir / "testdir"
    test_dir_path.mkdir(parents=True, exist_ok=True)
    resource.safe_remove(test_dir_path)
    assert not test_dir_path.exists()
