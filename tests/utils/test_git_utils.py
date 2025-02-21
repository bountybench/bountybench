import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from utils.git_utils import (
    git_apply_patch,
    git_checkout,
    git_clean_untracked,
    git_commit,
    git_delete_branch,
    git_diff,
    git_has_changes,
    git_init_repo,
    git_reset,
    git_setup_dev_branch,
    git_submodule_update,
)


@pytest.fixture
def tmp_git_repo():
    """Create a temporary git repository for testing."""
    tmp_dir = tempfile.TemporaryDirectory()
    repo_path = Path(tmp_dir.name)
    subprocess.run(["git", "init"], cwd=repo_path)
    yield repo_path
    tmp_dir.cleanup()


def test_git_init_repo(tmp_git_repo):
    """Test git initialization in the temporary repository."""
    assert (tmp_git_repo / ".git").exists()


def test_git_commit(tmp_git_repo):
    """Check if we can commit changes."""
    (tmp_git_repo / "test_file.txt").write_text("Hello, World!")
    git_commit(tmp_git_repo, "Initial commit")
    assert (
        subprocess.run(["git", "log"], cwd=tmp_git_repo, capture_output=True).returncode
        == 0
    )


def test_git_diff(tmp_git_repo):
    """Check if git diff returns the expected difference."""
    (tmp_git_repo / "file1.txt").write_text("Hello, World!")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo)
    git_commit(tmp_git_repo, "Initial commit")

    (tmp_git_repo / "file1.txt").write_text("Hello, Git!")
    diff = git_diff(tmp_git_repo)
    assert "Hello, Git!" in diff


def test_git_checkout(tmp_git_repo):
    """Create a branch and checkout to it."""
    (tmp_git_repo / "file.txt").write_text("Hello!")
    git_commit(tmp_git_repo, "Initial commit")
    subprocess.run(["git", "checkout", "-b", "new_branch"], cwd=tmp_git_repo)

    # Assert that we are on the new_branch
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=tmp_git_repo, capture_output=True
    )
    assert current_branch.stdout.decode().strip() == "new_branch"


def test_git_reset(tmp_git_repo):
    """Check if we can reset the repository."""
    (tmp_git_repo / "file.txt").write_text("Hello!")
    git_commit(tmp_git_repo, "Initial commit")
    (tmp_git_repo / "file.txt").write_text("New content!")
    git_commit(tmp_git_repo, "Second commit")

    git_reset(tmp_git_repo)
    assert Path(tmp_git_repo / "file.txt").read_text() == "Hello!"


def test_git_clean_untracked(tmp_git_repo):
    """Test cleaning untracked files."""
    (tmp_git_repo / "temp_file.txt").write_text("Will be deleted")

    assert (tmp_git_repo / "temp_file.txt").exists()
    git_clean_untracked(tmp_git_repo)
    assert not (tmp_git_repo / "temp_file.txt").exists()


def test_git_has_changes(tmp_git_repo):
    """Check if there are changes."""
    (tmp_git_repo / "file.txt").write_text("Initial content.")
    git_commit(tmp_git_repo, "Initial commit")  # Commit initial state
    (tmp_git_repo / "file.txt").write_text("Changed content!")
    assert git_has_changes(tmp_git_repo)


def test_git_setup_dev_branch(tmp_git_repo):
    """Set up a dev branch."""
    (tmp_git_repo / "file.txt").write_text("File for dev branch.")
    git_commit(tmp_git_repo, "Initial commit")

    git_setup_dev_branch(tmp_git_repo, "master")  # Change to 'master' here
    branches = subprocess.run(
        ["git", "branch"], cwd=tmp_git_repo, capture_output=True, text=True
    ).stdout
    assert "dev" in branches


def test_git_submodule_update(tmp_git_repo):
    """Test updating submodules."""
    # Create a submodule directory and initialize it
    submodule_path = tmp_git_repo / "submodule"
    submodule_path.mkdir()

    # Initialize the submodule as a fresh Git repository
    subprocess.run(["git", "init"], cwd=submodule_path)
    (submodule_path / "README.md").write_text("Submodule readme.")
    subprocess.run(["git", "add", "README.md"], cwd=submodule_path)
    subprocess.run(
        ["git", "commit", "-m", "Initial submodule commit"], cwd=submodule_path
    )

    # Now add the submodule in the main temporary repo
    subprocess.run(["git", "submodule", "add", str(submodule_path)], cwd=tmp_git_repo)

    # Update the submodule
    git_submodule_update(tmp_git_repo)

    assert (submodule_path / "README.md").exists()


def test_git_delete_branch(tmp_git_repo):
    """Test branch deletion."""
    (tmp_git_repo / "file.txt").write_text("This will be on a new branch.")
    git_commit(tmp_git_repo, "Initial commit")

    subprocess.run(["git", "checkout", "-b", "test_branch"], cwd=tmp_git_repo)
    subprocess.run(
        ["git", "checkout", "master"], cwd=tmp_git_repo
    )  # Switch to master before deletion
    git_delete_branch(tmp_git_repo, "test_branch")

    result = subprocess.run(
        ["git", "branch"], cwd=tmp_git_repo, capture_output=True, text=True
    )
    assert "test_branch" not in result.stdout
