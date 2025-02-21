import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

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


def git_checkout(directory_path: Path, commit: str):
    subprocess.run(
        ["git", "clean", "-fdx"],
        cwd=directory_path,
        stdout=sys.stdout,
        stderr=sys.stderr,
        check=True,
        text=True,
    )

    logger.info(f"Checking out {commit}")

    subprocess.run(
        ["git", "checkout", commit],
        cwd=directory_path,
        stdout=sys.stdout,
        stderr=sys.stderr,
        check=True,
        text=True,
    )


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
    if os.path.exists(directory_path):
        if not (directory_path / ".git").exists():
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=directory_path,
                    check=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
                # Create .gitignore if needed
                gitignore_path = directory_path / ".gitignore"
                if not gitignore_path.exists():
                    gitignore_path.write_text("*.log\n.DS_Store\n")

                logger.info(f"Initialized git repository in {directory_path}")

                subprocess.run(
                    ["git", "branch", "-m", "main"],
                    cwd=directory_path,
                    check=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
                logger.info("Branch named to main")

                # Initial commit
                subprocess.run(["git", "add", "."], cwd=directory_path)
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit"], cwd=directory_path
                )
                logger.info(f"Committed initial files in {directory_path}")
            except subprocess.CalledProcessError as e:
                logger.critical(f"Failed to set up repo: {e.stderr}")
                sys.exit(1)
        else:
            logger.warning(
                f"{directory_path} already a git repo, skipping repo initialization."
            )
    else:
        logger.critical(f"Directory does not exist: {work_dir}")
        sys.exit(1)


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


def git_setup_dev_branch(directory_path: Path, commit: Optional[str] = "main"):
    try:
        # Ensure Git repository is set up
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=directory_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )

        if result.stdout.strip() == "true":
            # Force checkout to the vulnerable commit
            logger.info(f"Forcing checkout to commit: {commit}")
            subprocess.run(
                ["git", "checkout", "-f", commit],
                cwd=directory_path,
                check=True,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

            # Check if 'dev' branch exists
            branch_exists = subprocess.run(
                ["git", "branch"], cwd=directory_path, capture_output=True, text=True
            )

            if "dev" in branch_exists.stdout:
                logger.info("Branch 'dev' exists. Deleting it...")
                subprocess.run(
                    ["git", "branch", "-D", "dev"],
                    cwd=directory_path,
                    check=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )

            # Create and switch to a new 'dev' branch
            logger.info("Creating new 'dev' branch...")
            subprocess.run(
                ["git", "checkout", "-b", "dev"],
                cwd=directory_path,
                check=True,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            logger.info(f"Created and switched to 'dev' branch in {directory_path}")

            # Verify the current commit
            current_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=directory_path,
                capture_output=True,
                text=True,
                check=True,
            )
            if current_commit.stdout.strip() == commit:
                logger.info(f"Successfully checked out to commit {commit}")
            else:
                logger.warning(
                    f"Current commit ({current_commit.stdout.strip()}) does not match the intended vulnerable commit ({commit})"
                )

        else:
            logger.error(f"Directory {directory_path} is not a valid git repository.")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to set up 'dev' branch: {e.stderr}")


def git_submodule_update(directory_path: Path):
    subprocess.run(
        ["git", "submodule", "update", "--init", "."],
        cwd=directory_path,
        stdout=sys.stdout,
        stderr=sys.stderr,
        check=True,
        text=True,
    )


def git_delete_branch(directory_path: Path, branch_name: str):
    subprocess.run(
        ["git", "branch", "-D", branch_name],
        cwd=directory_path,
        capture_output=True,
        check=False,
    )
    logger.info(f"Removed {branch_name} branch from {directory_path}")
