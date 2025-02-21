import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from utils.logger import get_main_logger

logger = get_main_logger(__name__)


def _run_git_command(
    directory: Path,
    args: list[str],
    check: bool = True,
    capture_output: bool = False,
    log_error: bool = True,
) -> Optional[subprocess.CompletedProcess]:
    """Helper function to run git commands with consistent error handling."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=directory,
            check=check,
            capture_output=capture_output,
            text=True,
        )
        logger.debug(f"Git command succeeded: git {' '.join(args)}")
        return result
    except subprocess.CalledProcessError as e:
        if log_error:
            logger.error(f"Git command failed: git {' '.join(args)} - {e.stderr}")
        if check:
            raise
        return None


def _checkout_branch(directory: Path, branch_name: Optional[str]) -> None:
    """Helper function to checkout a branch if specified."""
    if branch_name:
        _run_git_command(directory, ["checkout", branch_name])
        logger.info(f"Checked out to branch '{branch_name}'.")


def git_commit(
    directory_path: str | Path, commit_info: str, branch_name: Optional[str] = None
) -> bool:
    """Create a git commit in the specified branch."""
    try:
        directory = Path(directory_path)
        _checkout_branch(directory, branch_name)

        # Check repository status
        status_result = _run_git_command(
            directory, ["status", "--porcelain"], capture_output=True
        )
        if not status_result.stdout.strip():
            logger.info(f"No changes to commit in {directory}")
            return False

        _run_git_command(directory, ["add", "."])
        _run_git_command(directory, ["commit", "-m", f"Commit {commit_info}"])
        logger.info(f"Commit {commit_info} created successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create commit: {e}")
        return False


def git_reset(directory_path: str | Path, branch_name: Optional[str] = None) -> None:
    """Reset repository to previous commit."""
    try:
        directory = Path(directory_path)
        _checkout_branch(directory, branch_name)
        _run_git_command(directory, ["reset", "--hard", "HEAD~1"])
        logger.info(f"Reset successful in {directory}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to reset repository: {e}")


def git_checkout(directory_path: str | Path, commit: str) -> None:
    """Checkout a specific commit and clean repository."""
    directory = Path(directory_path)
    _run_git_command(directory, ["clean", "-fdx"])
    logger.info(f"Checking out {commit}")
    _run_git_command(directory, ["checkout", commit])


def git_checkout_main(directory_path: str | Path) -> None:
    """Checkout main branch."""
    git_checkout(directory_path, "main")


def git_clean_untracked(directory_path: str | Path) -> None:
    """Clean untracked files from repository."""
    directory = Path(directory_path)
    _run_git_command(directory, ["clean", "-fd"])


def git_init_repo(directory_path: str | Path) -> None:
    """Initialize git repository if it doesn't exist."""
    directory = Path(directory_path)
    if not directory.exists():
        logger.critical(f"Directory does not exist: {directory}")
        sys.exit(1)

    if (directory / ".git").exists():
        logger.warning(f"Repository already exists in {directory}")
        return

    try:
        _run_git_command(directory, ["init"])
        _run_git_command(directory, ["branch", "-m", "main"])

        # Create basic .gitignore
        gitignore = directory / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*.log\n.DS_Store\n")

        # Initial commit
        _run_git_command(directory, ["add", "."])
        _run_git_command(directory, ["commit", "-m", "Initial commit"])
        logger.info(f"Initialized repository in {directory}")
    except subprocess.CalledProcessError as e:
        logger.critical(f"Failed to initialize repository: {e}")
        raise


def git_commit_changes(directory_path: str | Path) -> None:
    """Commit all changes in the repository."""
    directory = Path(directory_path)
    try:
        _run_git_command(directory, ["add", "."])
        _run_git_command(
            directory,
            ["commit", "-m", f'Update files at {time.strftime("%Y-%m-%d %H:%M:%S")}'],
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to commit changes: {e}")


def git_has_changes(directory_path: str | Path) -> bool:
    """Check if repository has uncommitted changes."""
    directory = Path(directory_path)
    try:
        result = _run_git_command(
            directory, ["status", "--porcelain"], capture_output=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        logger.error("Failed to check repository status")
        return True


def git_submodule_update(directory_path: str | Path) -> None:
    """Update git submodules."""
    directory = Path(directory_path)
    _run_git_command(directory, ["submodule", "update", "--init", "."])


def git_delete_branch(directory_path: str | Path, branch_name: str) -> None:
    """Delete a git branch."""
    directory = Path(directory_path)
    _run_git_command(directory, ["branch", "-D", branch_name], check=False)
    logger.info(f"Deleted branch {branch_name} in {directory}")


def git_diff(directory_path: str | Path) -> str:
    """Get git diff of the repository."""
    try:
        directory = Path(directory_path)
        logger.info(f"Checking for git diff in directory: {directory}")

        if not (directory / ".git").is_dir():
            logger.error(f"{directory} is not a git repository")
            return ""

        # Clean cached pycache files
        _run_git_command(
            directory,
            ["rm", "--cached", "-r", "__pycache__"],
            check=False,
            log_error=False,
        )
        _run_git_command(
            directory, ["rm", "--cached", "*.pyc"], check=False, log_error=False
        )

        # Check untracked files
        untracked_result = _run_git_command(
            directory,
            ["ls-files", "--others", "--exclude-standard"],
            capture_output=True,
        )
        logger.debug(
            f"Untracked files: {untracked_result.stdout if untracked_result else ''}"
        )

        # Stage all changes
        _run_git_command(directory, ["add", "-A"])

        # Get staged diff
        diff_result = _run_git_command(
            directory, ["diff", "--cached"], capture_output=True
        )
        diff = diff_result.stdout if diff_result else ""
        logger.debug(f"Git diff: {diff}")
        return diff
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get git diff: {e}")
        return ""


def git_apply_patch(
    patch_file: Path, directory_path: str | Path, branch_name: Optional[str] = None
) -> Tuple[bool, str]:
    """Apply a git patch to the repository."""
    try:
        directory = Path(directory_path)
        _checkout_branch(directory, branch_name)
        _run_git_command(directory, ["apply", str(patch_file.resolve())])
        msg = f"Applied patch {patch_file.name} successfully"
        logger.info(msg)
        return True, msg
    except subprocess.CalledProcessError as e:
        msg = f"Failed to apply patch {patch_file.name}: {e}"
        logger.error(msg)
        return False, msg


def git_setup_dev_branch(directory_path: str | Path, commit: str = "main") -> None:
    """Set up dev branch from specified commit."""
    directory = Path(directory_path)
    try:
        # Verify valid repository
        result = _run_git_command(
            directory, ["rev-parse", "--is-inside-work-tree"], capture_output=True
        )
        if result.stdout.strip() != "true":
            raise ValueError(f"Not a git repository: {directory}")

        # Checkout base commit
        _run_git_command(directory, ["checkout", "-f", commit])

        # Delete existing dev branch
        branches = _run_git_command(directory, ["branch"], capture_output=True)
        if "dev" in branches.stdout:
            _run_git_command(directory, ["branch", "-D", "dev"])

        # Create new dev branch
        _run_git_command(directory, ["checkout", "-b", "dev"])
        logger.info(f"Created dev branch in {directory}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to setup dev branch: {e}")
