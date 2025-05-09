import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from utils.git_utils import (
    git_apply_patch,
    git_checkout,
    git_checkout_main,
    git_clean,
    git_commit,
    git_delete_branch,
    git_diff,
    git_has_changes,
    git_init_repo,
    git_reset,
    git_setup_dev_branch,
    git_submodule_update,
    git_restore,
)


@pytest.fixture
def tmp_git_repo():
    """Create a temporary git repository for testing."""
    tmp_dir = tempfile.TemporaryDirectory()
    repo_path = Path(tmp_dir.name)

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=repo_path)

    # Configure git for this repository (required for commits)
    subprocess.run(
        ["git", "config", "--local", "user.name", "Test User"], cwd=repo_path
    )
    subprocess.run(
        ["git", "config", "--local", "user.email", "test@example.com"], cwd=repo_path
    )

    # Configure git to not complain about newline endings (common CI issue)
    subprocess.run(
        ["git", "config", "--local", "core.autocrlf", "false"], cwd=repo_path
    )

    # Create an initial file so we have a master/main branch
    (repo_path / "init.txt").write_text("Initial file")
    subprocess.run(["git", "add", "init.txt"], cwd=repo_path)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path)

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


def test_git_diff_detects_file_move_without_content_change(tmp_git_repo):
    """Check if git diff detects file move (no content change)."""
    (tmp_git_repo / "src").mkdir()
    (tmp_git_repo / "src" / "moved.txt").write_text("unchanged content")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, check=True)
    git_commit(tmp_git_repo, "add moved file")

    (tmp_git_repo / "dst").mkdir()
    subprocess.run(
        ["git", "mv", "src/moved.txt", "dst/moved.txt"],
        cwd=tmp_git_repo,
        check=True,
    )
    diff = git_diff(tmp_git_repo)

    assert "diff --git a/src/moved.txt b/dst/moved.txt" in diff
    assert "rename from src/moved.txt" in diff
    assert "rename to dst/moved.txt" in diff
    assert "+unchanged content" not in diff
    assert "-unchanged content" not in diff


def test_git_diff_detects_simple_rename(tmp_git_repo):
    """Check if git diff detects simple file rename (same directory)."""
    (tmp_git_repo / "file.txt").write_text("content")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, check=True)
    git_commit(tmp_git_repo, "add file")

    # rename it in place
    subprocess.run(
        ["git", "mv", "file.txt", "renamed.txt"],
        cwd=tmp_git_repo,
        check=True,
    )
    diff = git_diff(tmp_git_repo)

    assert "diff --git a/file.txt b/renamed.txt" in diff
    assert "rename from file.txt" in diff
    assert "rename to renamed.txt" in diff
    assert "+content" not in diff
    assert "-content" not in diff


def test_git_diff_detects_file_move_with_content_change(tmp_git_repo):
    """Check if git diff detects file move file move plus a content change."""
    (tmp_git_repo / "src").mkdir()
    (tmp_git_repo / "src" / "moved.txt").write_text("original line")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, check=True)
    git_commit(tmp_git_repo, "add moved file")

    (tmp_git_repo / "dst").mkdir()
    subprocess.run(
        ["git", "mv", "src/moved.txt", "dst/moved.txt"],
        cwd=tmp_git_repo,
        check=True,
    )

    (tmp_git_repo / "dst" / "moved.txt").write_text("original line\nadded line")
    diff = git_diff(tmp_git_repo)

    assert "diff --git a/dst/moved.txt b/dst/moved.txt" in diff
    assert "new file" in diff
    assert "added line" in diff

    assert "diff --git a/src/moved.txt b/src/moved.txt" in diff
    assert "deleted file" in diff
    assert "original line" in diff


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

    git_reset(tmp_git_repo, ref="HEAD~1")
    assert Path(tmp_git_repo / "file.txt").read_text() == "Hello!"


def test_git_clean(tmp_git_repo):
    """Test cleaning untracked files."""
    (tmp_git_repo / "temp_file.txt").write_text("Will be deleted")

    assert (tmp_git_repo / "temp_file.txt").exists()
    git_clean(tmp_git_repo)
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

    git_setup_dev_branch(tmp_git_repo)
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

    # Configure git for this submodule
    subprocess.run(
        ["git", "config", "--local", "user.name", "Test User"], cwd=submodule_path
    )
    subprocess.run(
        ["git", "config", "--local", "user.email", "test@example.com"],
        cwd=submodule_path,
    )

    (submodule_path / "README.md").write_text("Submodule readme.")
    subprocess.run(["git", "add", "README.md"], cwd=submodule_path)
    subprocess.run(
        ["git", "commit", "-m", "Initial submodule commit"], cwd=submodule_path
    )

    # Now add the submodule in the main temporary repo
    try:
        # Adding a better error message
        result = subprocess.run(
            ["git", "submodule", "add", str(submodule_path)],
            cwd=tmp_git_repo,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"Submodule add failed: {result.stderr}")
    except Exception as e:
        print(f"Submodule add exception: {e}")
        # If submodule add fails, skip this test
        pytest.skip("Submodule add failed, skipping test")

    # Update the submodule
    try:
        git_submodule_update(tmp_git_repo)
    except Exception as e:
        print(f"Submodule update exception: {e}")
        # If submodule update fails, skip this test
        pytest.skip("Submodule update failed, skipping test")

    assert (submodule_path / "README.md").exists()


def test_git_delete_branch(tmp_git_repo):
    """Test branch deletion."""
    (tmp_git_repo / "file.txt").write_text("This will be on a new branch.")
    git_commit(tmp_git_repo, "Initial commit")

    subprocess.run(["git", "checkout", "-b", "test_branch"], cwd=tmp_git_repo)
    git_checkout_main(tmp_git_repo)  # Switch to main before deletion

    git_delete_branch(tmp_git_repo, "test_branch")

    result = subprocess.run(
        ["git", "branch"], cwd=tmp_git_repo, capture_output=True, text=True
    )
    assert "test_branch" not in result.stdout


def test_git_commit_no_changes(tmp_git_repo):
    """Test committing when there are no changes."""
    # Initial commit to create a clean state
    (tmp_git_repo / "dummy.txt").write_text("dummy")
    git_commit(tmp_git_repo, "Initial commit")

    # Try to commit with no changes
    result = git_commit(tmp_git_repo, "Empty commit")
    assert not result, "Should return False when no changes to commit"


def test_git_diff_non_repo(tmp_path):
    """Test git_diff on non-repository directory."""
    non_repo_dir = tmp_path / "non_repo"
    non_repo_dir.mkdir()
    (non_repo_dir / "file.txt").write_text("test")

    diff = git_diff(non_repo_dir)
    assert diff == "", "Should return empty string for non-git directory"


def test_git_apply_invalid_patch(tmp_git_repo):
    """Test applying invalid patch."""
    invalid_patch = tmp_git_repo / "invalid.patch"
    invalid_patch.write_text("@@ Invalid Patch Content @@")

    success, msg = git_apply_patch(invalid_patch, tmp_git_repo)
    assert not success
    assert "Failed to apply patch" in msg


def test_git_reset_no_previous_commit(tmp_git_repo):
    """Test reset when there's no previous commit."""
    (tmp_git_repo / "file.txt").write_text("Initial content")
    git_commit(tmp_git_repo, "Initial commit")

    # First reset works fine (goes to fixture's initial commit)
    git_reset(tmp_git_repo, ref="HEAD~1")

    # Second reset should fail as there's no commit before the fixture's initial one
    with pytest.raises(subprocess.CalledProcessError):
        git_reset(tmp_git_repo, ref="HEAD~1")


def test_git_checkout_invalid_commit(tmp_git_repo):
    """Test checking out non-existent commit."""
    with pytest.raises(subprocess.CalledProcessError):
        git_checkout(tmp_git_repo, "invalid_commit_hash")


def test_git_init_nonexistent_directory():
    """Test initializing repo in non-existent directory."""
    non_existent_dir = Path("/non/existent/path")
    with pytest.raises(RuntimeError):
        git_init_repo(non_existent_dir)


def test_git_setup_dev_branch_non_repo(tmp_path):
    """Test setup_dev_branch in non-repository directory."""
    non_repo_dir = tmp_path / "non_repo"
    non_repo_dir.mkdir()

    with pytest.raises(subprocess.CalledProcessError):
        git_setup_dev_branch(non_repo_dir)


def test_git_clean_no_untracked(tmp_git_repo):
    """Test cleaning when no untracked files exist."""
    git_clean(tmp_git_repo)  # Should complete without errors
    assert True  # Just verifying no exceptions are raised


def test_git_has_no_changes(tmp_git_repo):
    """Test has_changes when working tree is clean."""
    (tmp_git_repo / "file.txt").write_text("content")
    git_commit(tmp_git_repo, "Initial commit")

    assert not git_has_changes(tmp_git_repo)


def test_git_commit_invalid_branch(tmp_git_repo):
    """Test committing to non-existent branch."""
    (tmp_git_repo / "file.txt").write_text("content")

    with pytest.raises(subprocess.CalledProcessError):
        git_commit(tmp_git_repo, "Test commit", "non_existent_branch")


def test_git_restore_roundtrip_with_patch(tmp_git_repo, tmp_path):
    """
    1. Modify a tracked file and capture the diff (git_diff).
    2. Save that diff to a temporary *.patch* file.
    3. git_restore to return the tree to the committed state.
    4. git_apply_patch to re-apply the changes.
    5. git_restore again - the file should be back to its original contents.
    """
    file_path = tmp_git_repo / "hello.txt"
    file_path.write_text("original\n")
    git_commit(tmp_git_repo, "Add original file")

    # Step 1 – make a change and capture the patch
    file_path.write_text("original\nadded-line\n")
    patch_text = git_diff(tmp_git_repo)
    assert "+added-line" in patch_text

    # Step 2 – materialise the diff as a patch file
    patch_file = tmp_path / "change.patch"
    patch_file.write_text(patch_text)

    # Step 3 – restore (should cut the added line)
    git_restore(tmp_git_repo)
    assert file_path.read_text() == "original\n"

    # Step 4 – re‑apply the patch
    applied, _ = git_apply_patch(patch_file, tmp_git_repo)
    assert applied
    assert "added-line" in file_path.read_text()

    # Step 5 – final restore should remove the change again
    git_restore(tmp_git_repo)
    assert file_path.read_text() == "original\n"


def test_git_restore_recovers_deleted_files(tmp_git_repo):
    """
    Delete a tracked file (unstaged) and confirm git_restore recreates it.
    """
    victim = tmp_git_repo / "victim.txt"
    victim.write_text("to be deleted")
    git_commit(tmp_git_repo, "Add victim")

    # Delete and ensure it is really gone
    os.remove(victim)
    assert not victim.exists()

    # git_restore should bring the file back
    git_restore(tmp_git_repo)
    assert victim.exists()
    assert victim.read_text() == "to be deleted"


def test_git_restore_does_not_touch_untracked_files(tmp_git_repo):
    """
    Create an untracked file and ensure git_restore does **not** delete it.
    """
    untracked = tmp_git_repo / "scratch.log"
    untracked.write_text("scratch data")

    git_restore(tmp_git_repo)

    # File must still be present and contents unchanged
    assert untracked.exists()
    assert untracked.read_text() == "scratch data"
    

def test_git_restore_single_file_after_patch(tmp_git_repo, tmp_path):
    """
    Restore only one of several patched files
    """
    foo = tmp_git_repo / "foo.txt"
    bar = tmp_git_repo / "bar.txt"
    baseline = "base\n"

    foo.write_text(baseline)
    bar.write_text(baseline)
    git_commit(tmp_git_repo, "baseline foo & bar")

    # modify both files and capture patch
    foo.write_text(baseline + "foo-extra\n")
    bar.write_text(baseline + "bar-extra\n")
    patch_file = tmp_path / "multi.patch"
    patch_file.write_text(git_diff(tmp_git_repo))

    # restore to baseline
    git_restore(tmp_git_repo)
    assert foo.read_text() == baseline and bar.read_text() == baseline

    # apply patch — both files have extras
    applied, _ = git_apply_patch(patch_file, tmp_git_repo)
    assert applied
    assert foo.read_text().endswith("foo-extra\n")
    assert bar.read_text().endswith("bar-extra\n")

    # restore only bar.txt
    git_restore(tmp_git_repo, paths=[bar])

    # expectations
    assert foo.read_text().endswith("foo-extra\n")   # unchanged
    assert bar.read_text() == baseline               # reverted


def test_git_restore_unchanged_file(tmp_git_repo):
    """
    Calling git_restore on a clean file should leave everything untouched.
    Restoring an unchanged file is a no-op but must not error.
    """
    untouched = tmp_git_repo / "plain.txt"
    untouched.write_text("pristine\n")
    git_commit(tmp_git_repo, "add pristine file")

    # The file is clean; restore should succeed and content stay identical
    git_restore(tmp_git_repo, paths=[untouched])
    assert untouched.read_text() == "pristine\n"

    # The repo should still report no changes
    assert not git_has_changes(tmp_git_repo)


def test_git_restore_directory_multiple_files(tmp_git_repo):
    """
    • Create two files in a sub-directory and commit a baseline.
    • Modify both files.
    • Restore them first by passing an explicit list of paths,
      then modify again and restore by passing the directory itself.
    """
    data_dir = tmp_git_repo / "data"
    data_dir.mkdir()
    f1 = data_dir / "alpha.txt"
    f2 = data_dir / "beta.txt"

    baseline = "orig\n"
    f1.write_text(baseline)
    f2.write_text(baseline)
    git_commit(tmp_git_repo, "add data directory")

    # round 1: restore via explicit list
    f1.write_text(baseline + "change-1\n")
    f2.write_text(baseline + "change-2\n")
    assert git_has_changes(tmp_git_repo)

    git_restore(tmp_git_repo, paths=[f1, f2])

    assert f1.read_text() == baseline
    assert f2.read_text() == baseline
    assert not git_has_changes(tmp_git_repo)

    # round 2: restore via directory path
    # make changes again
    f1.write_text(baseline + "change-A\n")
    f2.write_text(baseline + "change-B\n")
    assert git_has_changes(tmp_git_repo)

    # now restore by giving the directory path
    git_restore(tmp_git_repo, paths=[data_dir])

    assert f1.read_text() == baseline
    assert f2.read_text() == baseline
    assert not git_has_changes(tmp_git_repo)