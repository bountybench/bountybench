import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from utils.logger import get_main_logger

logger = get_main_logger(__name__)


def git_diff(directory_path: str | Path) -> str:
    try:
        directory_path = (
            Path(directory_path) if isinstance(directory_path, str) else directory_path
        )

        logger.info(f"Checking for git diff in directory: {directory_path}")

        # Check if the directory is a git repository
        if not (directory_path / ".git").is_dir():
            logger.error(
                f"{directory_path} is not a git repository, something went wrong."
            )
            return ""

        subprocess.run(
            ["git", "rm", "--cached", "-r", "__pycache__"],
            cwd=directory_path,
            check=False,
        )
        subprocess.run(
            ["git", "rm", "--cached", "*.pyc"], cwd=directory_path, check=False
        )
        # Check for untracked files
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"], cwd=directory_path
        ).decode("utf-8")
        logger.debug(f"Untracked files: {untracked}")

        # Add all files to the index (including new ones)
        subprocess.run(["git", "add", "-A"], cwd=directory_path, check=True)

        # Get the diff
        diff = subprocess.check_output(
            ["git", "diff", "--cached"], cwd=directory_path
        ).decode("utf-8")

        logger.debug(f"Git diff: {diff}")
        return diff
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get git diff: {e}")
        return ""


def git_commit(
    directory_path: Path, commit_info: str, branch_name: Optional[str] = None
) -> None:
    """Create a git commit."""
    try:
        if branch_name:
            subprocess.check_call(["git", "checkout", branch_name], cwd=directory_path)
            logger.info(f"Checked out to branch '{branch_name}'.")

        # Check if there are any changes to commit
        status = (
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=directory_path
            )
            .decode("utf-8")
            .strip()
        )
        if not status:
            logger.info(f"No changes to commit in {directory_path}")
            return False

        subprocess.check_call(["git", "add", "."], cwd=directory_path)
        subprocess.check_call(
            ["git", "commit", "-m", f"Commit {commit_info}"], cwd=directory_path
        )
        logger.info(
            f"Commit {commit_info} committed successfully on branch '{branch_name or 'current'}'."
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create git commit: {e}")
        return False


def git_reset(directory_path: Path, branch_name: Optional[str] = None) -> None:
    """Reset the git repository to the previous commit (HEAD~1)."""
    try:
        if branch_name:
            subprocess.check_call(["git", "checkout", branch_name], cwd=directory_path)
            logger.info(f"Checked out to branch '{branch_name}'.")
        subprocess.check_call(["git", "reset", "--hard", "HEAD~1"], cwd=directory_path)
        logger.info(f"Git reset to HEAD~1 performed successfully in {directory_path}.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to reset git repository to HEAD~1: {e}")


def git_checkout_main(directory_path: Path):
    try:
        subprocess.check_call(["git", "checkout", "main"], cwd=directory_path)
        logger.info("Checked out to branch 'main'.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to checkout 'main': {e}")


def git_clean_untracked(directory_path: Path):
    """Clean untracked files using git clean"""
    try:
        subprocess.run(
            ["git", "--git-dir=.git", "--work-tree=.", "clean", "-fd"],
            cwd=directory_path,
            check=True,
        )
    except subprocess.CalledProcessError:
        logger.error("Failed to clean untracked files")


def git_init_repo(directory_path: Path):
    """Initialize git repo in exploits directory if it doesn't exist"""
    if not (directory_path / ".git").exists():
        subprocess.run(["git", "init"], cwd=directory_path, check=True)
        # Create .gitignore if needed
        gitignore_path = directory_path / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("*.log\n.DS_Store\n")
        # Initial commit
        subprocess.run(["git", "add", "."], cwd=directory_path)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=directory_path)


def git_commit_changes(directory_path: Path):
    """Commit any changes in the exploits directory"""
    try:
        subprocess.run(
            ["git", f"--git-dir=.git", f"--work-tree=.", "add", "."],
            cwd=directory_path,
        )
        subprocess.run(
            [
                "git",
                f"--git-dir=.git",
                f"--work-tree=.",
                "commit",
                "-m",
                f'Update exploit files at {time.strftime("%Y-%m-%d %H:%M:%S")}',
            ],
            cwd=directory_path,
        )
    except subprocess.CalledProcessError:
        logger.error("Failed to commit changes")


def git_has_changes(directory_path: Path) -> bool:
    """Check if there are any changes in the exploits directory"""
    try:
        result = subprocess.run(
            ["git", f"--git-dir=.git", f"--work-tree=.", "status", "--porcelain"],
            cwd=directory_path,
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        logger.error("Failed to check git status")
        return True


################
# GIT PATCHING #
################


def git_apply_patch(
    patch_file: Path, directory_path: Path, branch_name: Optional[str] = None
) -> Tuple[bool, str]:
    try:
        if branch_name:
            subprocess.check_call(["git", "checkout", branch_name], cwd=directory_path)
            logger.info(f"Checked out to branch '{branch_name}'.")

        logger.info(f"Attempting to apply patch: {patch_file}")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f"Patch file exists: {patch_file.exists()}")

        subprocess.check_call(
            ["git", "apply", str(patch_file.resolve())], cwd=directory_path
        )
        logger.info(
            f"Patch '{patch_file}' applied successfully on branch '{branch_name or 'current'}'."
        )
        return True, f"Patch '{patch_file}' applied successfully."
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to apply patch '{patch_file}': {e}")
        return False, f"Failed to apply patch '{patch_file}': {e}"
