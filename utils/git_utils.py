import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple, Union

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

PathLike = Union[Path, str]


def _run_git_command(
    directory: Path,
    args: list[str],
    capture_output: bool = False,
    text: bool = True,  # Added parameter to control text conversion
    encoding: str = "utf-8",  # Added parameter to specify encoding
    errors: str = "replace",  # Added parameter to handle encoding errors
) -> Optional[subprocess.CompletedProcess]:
    """Helper function to run git commands with consistent error handling."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=directory,
            check=True,
            capture_output=capture_output,
            text=text,  # Use the parameter instead of hardcoding
            encoding=encoding if text else None,  # Only use encoding if text=True
            errors=errors if text else None,  # Only use errors if text=True
        )
        logger.debug(f"Git command succeeded: git {' '.join(args)}")
        return result
    except subprocess.CalledProcessError as e:
        logger.warning(f"Git command failed: git {' '.join(args)} - {str(e)}")
        raise


def _checkout_branch(directory: Path, branch_name: Optional[str]) -> None:
    """Helper function to checkout a branch if specified."""
    if branch_name:
        _run_git_command(directory, ["checkout", branch_name])
        logger.info(f"Checked out to branch '{branch_name}'.")


def git_commit(
    directory_path: PathLike, commit_info: str, branch_name: Optional[str] = None
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
        raise


def git_reset(directory_path: PathLike, branch_name: Optional[str] = None) -> None:
    """Reset repository to previous commit."""
    try:
        directory = Path(directory_path)
        _checkout_branch(directory, branch_name)
        _run_git_command(directory, ["reset", "--hard", "HEAD~1"])
        logger.info(f"Reset successful in {directory}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to reset repository: {e}")
        raise


def git_remove_changes(directory_path: PathLike) -> None:
    try:
        directory = Path(directory_path)
        _run_git_command(directory, ["reset", "--hard", "HEAD"])
        _run_git_command(directory, ["clean", "-fd"])
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to remove changes in repository: {e}")
        raise


def git_checkout(directory_path: PathLike, commit: str, force=False) -> None:
    """Checkout a specific commit and clean repository."""
    directory = Path(directory_path)
    logger.info(f"Checking out {commit}")
    if force:
        _run_git_command(directory, ["checkout", "--force", commit])
    else:
        _run_git_command(directory, ["clean", "-fdx"])
        _run_git_command(directory, ["checkout", commit])


def _get_main_branch(directory_path: PathLike):
    directory = Path(directory_path)

    # Get list of branches
    result = _run_git_command(directory, ["branch", "--list"], capture_output=True)
    branches = [
        branch.strip().lstrip("*").strip()
        for branch in result.stdout.split("\n")
        if branch.strip()
    ]

    # Check for 'main' or 'master'
    if "main" in branches:
        branch_name = "main"
    elif "master" in branches:
        branch_name = "master"
    else:
        raise ValueError("Neither 'main' nor 'master' branch found in the repository.")

    return branch_name


def git_checkout_main(directory_path: PathLike, force=False) -> None:
    """
    Checkout main or master branch.
    """
    git_checkout(directory_path, _get_main_branch(directory_path), force)


def git_clean_untracked(directory_path: PathLike) -> None:
    """Clean untracked files from repository."""
    directory = Path(directory_path)
    _run_git_command(directory, ["clean", "-fd"])


def git_init_repo(directory_path: PathLike, ignore_dirs: list[str] = None) -> None:
    """Initialize git repository if it doesn't exist."""
    directory = Path(directory_path)
    if not directory.exists():
        logger.critical(f"Directory does not exist: {directory}")
        raise RuntimeError(f"Directory does not exist: {directory}")

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

        # If ignore_dirs list is provided, append each entry to .gitignore if not already present
        if ignore_dirs:
            current_content = gitignore.read_text() if gitignore.exists() else ""
            with gitignore.open("a") as f:
                for ignore_dir in ignore_dirs:
                    if ignore_dir not in current_content:
                        f.write(f"{ignore_dir}\n")

        # Initial commit
        _run_git_command(directory, ["add", "."])
        _run_git_command(directory, ["commit", "-m", "Initial commit"])
        logger.info(f"Initialized repository in {directory}")
    except subprocess.CalledProcessError as e:
        logger.critical(f"Failed to initialize repository: {e}")
        raise


def git_commit_changes(directory_path: PathLike) -> None:
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
        raise


def git_has_changes(directory_path: PathLike) -> bool:
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


def git_submodule_update(directory_path: PathLike) -> None:
    """Update git submodules."""
    directory = Path(directory_path)
    _run_git_command(directory, ["submodule", "update", "--init", "."])


def git_delete_branch(directory_path: PathLike, branch_name: str) -> None:
    """Delete a git branch if it exists."""
    directory = Path(directory_path)

    # Check if the branch exists
    result = _run_git_command(
        directory, ["branch", "--list", branch_name], capture_output=True
    )
    branches = result.stdout.strip() if result else ""
    branch_exists = branch_name in branches

    if branch_exists:
        _run_git_command(directory, ["branch", "-D", branch_name])
        logger.info(f"Deleted branch {branch_name} in {directory}")
    else:
        logger.info(
            f"Branch {branch_name} does not exist in {directory}, skipping deletion."
        )


def git_diff(directory_path: PathLike) -> str:
    """Get git diff of the repository."""
    try:
        directory = Path(directory_path)
        logger.info(f"Checking for git diff in directory: {directory}")

        if not (directory / ".git").is_dir():
            logger.error(f"{directory} is not a git repository")
            return ""

        # Check if __pycache__ exists and clean it if it does
        pycache_dir = directory / "__pycache__"
        if pycache_dir.is_dir():
            _run_git_command(directory, ["rm", "--cached", "-r", "__pycache__"])
            logger.info(f"Removed cached __pycache__ in {directory}")

        # Clean .pyc files, use a safe approach in case there are no .pyc files
        try:
            _run_git_command(directory, ["rm", "--cached", "*.pyc"])
            logger.info("Removed cached .pyc files")
        except subprocess.CalledProcessError:
            logger.info(
                "No .pyc files to remove or encountered an error, handled gracefully."
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

        # Get staged diff - using specific encoding parameters to handle non-UTF-8 content
        diff_result = _run_git_command(
            directory,
            [
                "diff",
                "--cached",
                "--text",
            ],  # Added --text flag to help with binary files
            capture_output=True,
            errors="replace",  # Replace invalid characters instead of failing
        )
        diff = diff_result.stdout if diff_result else ""
        logger.debug(f"Git diff: {diff}")
        return diff
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get git diff: {e}")
        return ""


def git_apply_patch(
    patch_file: PathLike, directory_path: PathLike, branch_name: Optional[str] = None
) -> Tuple[bool, str]:
    """Apply a git patch to the repository with multiple fallback methods."""
    directory = Path(directory_path)
    patch_path = Path(patch_file)
    _checkout_branch(directory, branch_name)

    # Method 1: Standard git apply
    try:
        _run_git_command(directory, ["apply", str(patch_path.resolve())])
        msg = f"Applied patch {patch_path.name} successfully with standard git apply"
        logger.info(msg)
        return True, msg
    except subprocess.CalledProcessError:
        logger.info(
            f"Standard git apply failed for {patch_path.name}, trying alternative methods..."
        )

    # Method 2: Git apply with --3way option
    try:
        _run_git_command(directory, ["apply", "--3way", str(patch_path.resolve())])
        msg = f"Applied patch {patch_path.name} successfully with git apply --3way"
        logger.info(msg)
        return True, msg
    except subprocess.CalledProcessError:
        logger.info(
            f"Git apply --3way failed for {patch_path.name}, trying next method..."
        )

    # Method 3: Git apply with --reject option (allows partial application)
    try:
        _run_git_command(directory, ["apply", "--reject", str(patch_path.resolve())])
        msg = (
            f"Applied patch {patch_path.name} with git apply --reject (may be partial)"
        )
        logger.info(msg)
        return True, msg
    except subprocess.CalledProcessError:
        logger.info(
            f"Git apply --reject failed for {patch_path.name}, trying next method..."
        )

    # Method 4: Use Unix patch command as last resort
    try:
        result = subprocess.run(
            ["patch", "-p1", "-i", str(patch_path.resolve())],
            cwd=directory,
            check=True,
            capture_output=True,
            text=True,
        )
        msg = f"Applied patch {patch_path.name} successfully with Unix patch command"
        logger.info(msg)
        return True, msg
    except subprocess.CalledProcessError as e:
        # All methods failed
        msg = f"Failed to apply patch {patch_path.name} with all methods: {e}"
        logger.error(msg)
        return False, msg


def git_setup_dev_branch(
    directory_path: PathLike, commit: Optional[str] = None
) -> None:
    """Set up dev branch from specified commit."""
    directory = Path(directory_path)
    if not commit:
        commit = _get_main_branch(directory_path)

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
        raise


def git_get_current_commit(directory_path: PathLike) -> Optional[str]:
    """
    Get the current commit hash of the repository.

    Args:
        directory_path: Path to the git repository

    Returns:
        Optional[str]: The current commit hash if successful, None otherwise
    """
    try:
        directory = Path(directory_path)

        if not (directory / ".git").exists():
            logger.error(f"{directory} is not a git repository")
            return None

        result = _run_git_command(directory, ["rev-parse", "HEAD"], capture_output=True)

        commit_hash = result.stdout.strip()
        logger.debug(f"Current commit hash: {commit_hash}")
        return commit_hash

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get current commit hash: {e}")
        return None


def git_get_codebase_version() -> Optional[str]:
    """
    Get the current git commit hash as a version identifier.
    Returns the short commit hash or None if not in a git repository.
    """
    directory = Path.cwd()

    if not (directory / ".git").exists():
        logger.error(f"{directory} is not a git repository")
        return None

    try:
        # Get the current commit hash (short version)
        import subprocess

        version = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=directory,
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )

        return version
    except subprocess.SubprocessError as e:
        logger.error(f"Error getting git version: {e}")
        return None
