import os
import shutil
import subprocess

import pytest

from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig


@pytest.fixture
def setup_dirs():
    task_repo_dir = os.path.join(os.getcwd(), "tests", "resources", "test_files")
    tmp_dir_name = "tmp_dir_for_testing"
    tmp_dir = os.path.join(task_repo_dir, tmp_dir_name)
    original_files_dir = os.path.join(task_repo_dir, "original_files")

    if os.path.exists(task_repo_dir):
        shutil.rmtree(task_repo_dir)
    os.makedirs(original_files_dir, exist_ok=True)

    with open(os.path.join(original_files_dir, "test_file.txt"), "w") as f:
        f.write("This is a test.")

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

    if os.path.exists(task_repo_dir):
        shutil.rmtree(task_repo_dir)


@pytest.fixture
def resource(setup_dirs):
    config, tmp_dir, original_files_dir = setup_dirs
    return InitFilesResource(resource_id="test_resource", config=config)


def test_setup_repo(resource, setup_dirs):
    _, tmp_dir, _ = setup_dirs
    repo_path = os.path.join(tmp_dir, "original_files")
    git_dir = os.path.join(repo_path, ".git")

    assert os.path.exists(git_dir), "Git repository was not initialized."

    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert result.stdout.strip() == "1", "Initial commit not found."


def test_stop(resource, setup_dirs):
    _, tmp_dir, original_files_dir = setup_dirs
    repo_path = os.path.join(tmp_dir, "original_files")
    subprocess.run(["git", "checkout", "-b", "dev"], cwd=repo_path)
    resource.stop()
    assert not os.path.exists(tmp_dir)
    branch_result = subprocess.run(
        ["git", "branch"], cwd=original_files_dir, stdout=subprocess.PIPE, text=True
    )
    assert "dev" not in branch_result.stdout, "Branch 'dev' was not removed."


def test_remove_tmp(resource, setup_dirs):
    _, tmp_dir, _ = setup_dirs
    os.makedirs(os.path.join(tmp_dir, "subdir"), exist_ok=True)
    with open(os.path.join(tmp_dir, "subdir", "tempfile.txt"), "w") as f:
        f.write("Temporary file")
    assert os.path.exists(os.path.join(tmp_dir, "subdir", "tempfile.txt"))
    resource.remove_tmp()
    assert not os.path.exists(tmp_dir)


def test_safe_remove(resource, setup_dirs):
    _, tmp_dir, _ = setup_dirs
    test_file_path = os.path.join(tmp_dir, "testfile.txt")
    os.makedirs(tmp_dir, exist_ok=True)
    with open(test_file_path, "w") as f:
        f.write("This is a test file")
    resource.safe_remove(test_file_path)
    assert not os.path.exists(test_file_path)
    test_dir_path = os.path.join(tmp_dir, "testdir")
    os.makedirs(test_dir_path, exist_ok=True)
    resource.safe_remove(test_dir_path)
    assert not os.path.exists(test_dir_path)
