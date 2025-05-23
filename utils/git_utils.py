import shutil
import subprocess
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
    text: bool = True,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> Optional[subprocess.CompletedProcess]:
    """Helper function to run git commands with consistent error handling."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=directory,
            check=True,
            capture_output=capture_output,
            text=text,
            encoding=encoding if text else None,
            errors=errors if text else None,
        )
        logger.debug(f"Git command succeeded: git {' '.join(args)}", stacklevel=2)
        return result
    except subprocess.CalledProcessError as e:
        logger.warning(
            f"Git command failed: git {' '.join(args)} - {str(e)}", stacklevel=2
        )
        raise


def _checkout_branch(directory: Path, branch_name: Optional[str]) -> None:
    """Helper function to checkout a branch if specified."""
    if branch_name:
        _run_git_command(directory, ["checkout", branch_name])
        logger.debug(f"Checked out to branch '{branch_name}'.")


def _get_main_branch(directory_path: PathLike) -> str:
    """Determine if repository uses 'main' or 'master' as default branch."""
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
        return "main"
    elif "master" in branches:
        return "master"
    else:
        raise ValueError("Neither 'main' nor 'master' branch found in the repository.")


def git_commit(
    directory_path: PathLike,
    commit_message: Optional[Union[str, int, float]] = None,
    branch_name: Optional[str] = None,
    subfolder_to_commit: Optional[PathLike] = None,
) -> bool:
    """
    Create a git commit with all changes in the repository.

    Args:
        directory_path: Path to the git repository
        commit_message: Custom commit message (uses timestamp if None)
        branch_name: Optional branch to checkout before committing

    Returns:
        bool: True if commit was created, False if no changes to commit
    """
    directory = Path(directory_path)

    # Check if directory is within a git repo (either directly or as a subdirectory)
    try:
        # Run git status to check if we're in a git repository
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=directory,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError:
        logger.warning(f"No git repository exists at or above {directory}")
        return False

    try:
        # Checkout branch if specified
        if branch_name:
            _checkout_branch(directory, branch_name)

        # Stage changes
        if subfolder_to_commit:
            relative_path = str(subfolder_to_commit.relative_to(directory))
            _run_git_command(directory, ["add", relative_path])
        else:
            _run_git_command(directory, ["add", "."])

        # Check repository status
        if not git_has_changes(directory):
            logger.debug(f"No changes to commit in {directory}")
            return False

        # Use timestamp if no message provided
        if commit_message is None:
            commit_message = f'Update files at {time.strftime("%Y-%m-%d %H:%M:%S")}'
        else:
            commit_message = str(commit_message)

        # Create the commit
        _run_git_command(directory, ["commit", "-m", commit_message])
        logger.debug(f"Commit '{commit_message}' created successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create commit: {e.stderr}")
        raise


def git_reset(
    directory_path: PathLike,
    ref: str = "HEAD",
    branch_name: Optional[str] = None,
    clean: bool = True,
) -> None:
    """
    Reset repository to a specific commit reference, discarding all changes.

    Args:
        directory_path: Path to the git repository
        ref: Git reference to reset to (default: "HEAD")
            Use "HEAD" for current commit
            Use "HEAD~1" for previous commit
            Use "HEAD~n" to go back n commits
            Can also use any commit hash or branch name
        branch_name: Optional branch to checkout before resetting
        clean: Whether to also clean untracked files
    """
    try:
        directory = Path(directory_path)
        _checkout_branch(directory, branch_name)

        # Reset to the specified reference
        _run_git_command(directory, ["reset", "--hard", ref])
        logger.debug(f"Reset to {ref} in {directory}")

        # Clean untracked files if requested
        if clean:
            _run_git_command(directory, ["clean", "-fd"])
            logger.debug(f"Cleaned untracked files in {directory}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to reset repository: {e.stderr}")
        raise


def git_checkout(
    directory_path: PathLike, target: str, force: bool = False, clean: bool = True
) -> None:
    """
    Checkout a specific commit or branch with options to clean and force.

    Args:
        directory_path: Path to the git repository
        target: Branch name, commit hash, or reference to checkout
        force: Whether to force checkout (discard local changes)
        clean: Whether to clean untracked files before checkout
    """
    directory = Path(directory_path)
    logger.debug(f"Checking out {target}")

    cmd = ["checkout"]
    if force:
        cmd.append("--force")
    cmd.append(target)

    try:
        # Clean first if requested
        if clean:
            _run_git_command(directory, ["clean", "-fdx"])

        _run_git_command(directory, cmd)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to checkout {target}: {e.stderr}")
        raise


def git_checkout_main(
    directory_path: PathLike, force: bool = False, clean: bool = True
) -> None:
    """
    Checkout main or master branch with optional cleaning.

    Args:
        directory_path: Path to the git repository
        force: Whether to force checkout (discard local changes)
        clean: Whether to clean untracked files before checkout
    """
    git_checkout(
        directory_path, _get_main_branch(directory_path), force=force, clean=clean
    )


def git_has_changes(directory_path: PathLike, check_all: bool = True) -> bool:
    """
    Check if repository has uncommitted changes.

    Args:
        directory_path: Path to the git repository
        check_all: Whether to check changes in the whole git folder

    Returns:
        bool: True if uncommitted changes exist, False otherwise
    """
    directory = Path(directory_path)
    try:
        arg = ["status", "--porcelain"]
        if not check_all:
            arg.append(".")
        result = _run_git_command(directory, arg, capture_output=True)
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        logger.error("Failed to check repository status")
        return True  # Assume changes exist if command fails


def git_clean(directory_path: PathLike, remove_ignored: bool = False) -> None:
    """
    Clean untracked files from repository with options.

    Args:
        directory_path: Path to the git repository
        remove_ignored: Whether to also remove files ignored by .gitignore
    """
    directory = Path(directory_path)

    flags = "-fd"
    if remove_ignored:
        flags += "x"
    cmd = ["clean", flags]

    _run_git_command(directory, cmd)
    logger.debug(f"Cleaned untracked files in {directory}")


def git_restore(
    directory_path: PathLike,
    paths: Optional[list[PathLike]] = None,
    staged: bool = True,
    worktree: bool = True,
) -> None:
    """
    Restore tracked paths to their HEAD state.

    Args:
        directory_path: Repo root.
        paths: List of files/dirs to restore.  None ⇒ whole repo.
        staged: Also reset the index.
        worktree: Also reset the working tree.
    """
    directory = Path(directory_path)
    cmd = ["restore"]
    if staged:
        cmd.append("--staged")
    if worktree:
        cmd.append("--worktree")

    if paths:
        cmd.extend(str(Path(p).relative_to(directory)) for p in paths)
    else:
        cmd.append(".")  # fallback: every tracked file

    _run_git_command(directory, cmd)
    logger.debug(f"Restored {paths or 'entire repo'} in {directory}")


def git_add(
    directory_path: PathLike,
    all_changes: bool = True,
    paths: Optional[list[PathLike]] = None,
) -> None:
    """
    Stage changes in the repo.

    Args:
        directory_path: Path to the git repository.
        all_changes: If True, runs `git add -A` (new, modified, and deleted files).
        paths: If all_changes is False, a list of specific files or dirs to stage.
    """
    directory = Path(directory_path)

    if all_changes:
        args = ["add", "-A"]
    elif paths:
        # make paths relative to the repo root
        rels = [str(Path(p).relative_to(directory)) for p in paths]
        args = ["add", *rels]
    else:
        # default to staging everything in the CWD
        args = ["add", "."]

    _run_git_command(directory, args)
    logger.debug(
        f"Staged {'all changes' if all_changes else paths or ['.']} in {directory}"
    )


def git_init_repo(directory_path: PathLike, ignore_dirs: list[str] = None) -> None:
    """Initialize git repository if it doesn't exist."""
    directory = Path(directory_path)

    # Validate directory exists
    if not directory.exists():
        logger.critical(f"Directory does not exist: {directory}")
        raise RuntimeError(f"Directory does not exist: {directory}")

    # Exit if already a git repo
    if (directory / ".git").exists():
        logger.warning(f"Repository already exists in {directory}")
        return

    try:
        # Initialize repo and set main branch
        _run_git_command(directory, ["init"])
        _run_git_command(directory, ["branch", "-m", "main"])

        # Create basic .gitignore
        gitignore = directory / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*.log\n.DS_Store\n")
            gitignore.write_text("\n# Node.js dependencies\nnode_modules/\n")

        # If ignore_dirs list is provided, append each entry to .gitignore if not already present
        if ignore_dirs:
            current_content = gitignore.read_text() if gitignore.exists() else ""
            with gitignore.open("a") as f:
                for ignore_dir in ignore_dirs:
                    if ignore_dir not in current_content:
                        f.write(f"{ignore_dir}\n")

        # Initial commit
        _run_git_command(directory, ["add", "."])
        _run_git_command(directory, ["commit", "-q", "-m", "Initial commit"])
        logger.debug(f"Initialized repository in {directory}")
    except subprocess.CalledProcessError as e:
        logger.critical(f"Failed to initialize repository: {e}")
        raise


def git_submodule_update(directory_path: PathLike) -> None:
    """Update git submodules."""
    directory = Path(directory_path)
    _run_git_command(directory, ["submodule", "update", "--init", "."])
    logger.debug(f"Updated submodules in {directory}")


def git_delete_branch(directory_path: PathLike, branch_name: str) -> None:
    """Delete a git branch if it exists."""
    directory = Path(directory_path)

    # Check if the branch exists
    result = _run_git_command(
        directory, ["branch", "--list", branch_name], capture_output=True
    )

    # Only attempt deletion if branch exists
    if branch_name in result.stdout.strip():
        _run_git_command(directory, ["branch", "-D", branch_name])
        logger.debug(f"Deleted branch {branch_name} in {directory}")
    else:
        logger.debug(
            f"Branch {branch_name} does not exist in {directory}, skipping deletion."
        )


def git_diff(directory_path: PathLike, exclude_binary: Optional[bool] = True) -> str:
    """Get git diff of the repository"""
    try:
        directory = Path(directory_path)
        logger.debug(f"Checking for git diff in directory: {directory}")

        # Validate git repository
        if not (directory / ".git").is_dir():
            logger.error(f"{directory} is not a git repository")
            return ""

        # Stage all changes
        _run_git_command(directory, ["add", "-A"])

        if exclude_binary:
            # 1) detect content‐changed files via numstat
            numstat_result = _run_git_command(
                directory,
                [
                    "diff",
                    "--cached",
                    "--numstat",
                ],
                capture_output=True,
                errors="replace",
            )

            content_changed_files = {
                parts[2]
                for line in numstat_result.stdout.splitlines()
                if (parts := line.split("\t")) and parts[0] != "-" and parts[1] != "-"
            }

            # 2) detect pure renames via name-status
            name_status_result = _run_git_command(
                directory,
                ["diff", "--cached", "--name-status"],
                capture_output=True,
                errors="replace",
            )

            rename_files = {
                path
                for line in name_status_result.stdout.splitlines()
                if (parts := line.split("\t"))
                and parts[0].startswith("R")
                and len(parts) >= 3
                for path in (parts[1], parts[2])
            }

            files_to_diff = content_changed_files.union(rename_files)

            if not files_to_diff:
                logger.debug("No non-binary files changed")
                return ""

            args = ["diff", "--cached", "--", *files_to_diff]
        else:
            args = ["diff", "--cached"]

        # Get staged diff
        diff_result = _run_git_command(
            directory,
            args,
            capture_output=True,
            errors="replace",
        )

        diff = diff_result.stdout if diff_result else ""
        logger.debug(f"Git diff: {diff}")
        return diff
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get git diff: {e}")
        return ""


def git_apply_patch(
    patch_file: PathLike,
    directory_path: PathLike,
    branch_name: Optional[str] = None,
    methods: Optional[list[str]] = None,
) -> Tuple[bool, str]:
    """
    Apply a git patch to the repository with multiple fallback methods.

    Args:
        patch_file: Path to the patch file
        directory_path: Path to the git repository
        branch_name: Optional branch to checkout before applying patch
        methods: List of methods to try, in order ('standard', '3way', 'reject', 'unix')
                 Defaults to trying all methods in that order

    Returns:
        Tuple[bool, str]: Success status and message
    """
    directory = Path(directory_path)
    patch_path = Path(patch_file)
    _checkout_branch(directory, branch_name)

    # Default methods to try if not specified
    if methods is None:
        methods = ["standard", "3way", "reject", "unix"]

    # Method definitions
    method_commands = {
        "standard": (["apply", str(patch_path.resolve())], "standard git apply"),
        "3way": (["apply", "--3way", str(patch_path.resolve())], "git apply --3way"),
        "reject": (
            ["apply", "--reject", str(patch_path.resolve())],
            "git apply --reject (may be partial)",
        ),
    }

    # Try git methods first
    for method in methods:
        if method == "unix":
            # Unix patch method handled separately
            continue

        if method not in method_commands:
            logger.warning(f"Unknown patch method: {method}, skipping")
            continue

        args, method_name = method_commands[method]
        try:
            _run_git_command(directory, args)
            msg = f"Applied patch successfully with {method_name}."
            logger.debug(msg)
            return True, msg
        except subprocess.CalledProcessError:
            logger.debug(
                f"{method_name} failed for {patch_path.name}, trying next method..."
            )

    # Fall back to Unix patch command if specified and previous methods failed
    if "unix" in methods:
        try:
            subprocess.run(
                ["patch", "-p1", "-i", str(patch_path.resolve())],
                cwd=directory,
                check=True,
                capture_output=True,
                text=True,
            )
            msg = "Applied patch successfully with Unix patch command."
            logger.debug(msg)
            return True, msg
        except subprocess.CalledProcessError as e:
            # Unix method failed
            logger.debug(f"Unix patch method failed: {e}")

    # All methods failed
    msg = "Failed to apply patch."
    logger.error(msg)
    return False, msg


def git_setup_dev_branch(
    directory_path: PathLike, commit: Optional[str] = None
) -> None:
    """Set up dev branch from specified commit or main branch."""
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

        # Delete existing dev branch if it exists
        branches_output = _run_git_command(
            directory, ["branch"], capture_output=True
        ).stdout
        branch_names = [
            line.lstrip("* ").strip() for line in branches_output.splitlines()
        ]
        if "dev" in branch_names:
            _run_git_command(directory, ["branch", "-D", "dev"])

        # Create new dev branch
        _run_git_command(directory, ["checkout", "-b", "dev"])
        logger.debug(f"Created dev branch in {directory} from {commit}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to setup dev branch: {e}")
        raise


def git_get_current_commit(directory_path: PathLike) -> Optional[str]:
    """Get the current commit hash of the repository."""
    try:
        directory = Path(directory_path)

        # Validate git repository
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


def git_get_codebase_version(directory: Optional[Path] = None) -> Optional[str]:
    """Get the current git commit short hash as a version identifier."""
    if not directory:
        directory = Path.cwd()

    # Validate git repository
    if not (directory / ".git").exists():
        logger.error(f"{directory} is not a git repository")
        return None

    try:
        # Get the current short commit hash
        result = _run_git_command(
            directory, ["rev-parse", "--short", "HEAD"], capture_output=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting git version: {e}")
        return None


def create_git_ignore_function(ignore_git):
    """Create a custom ignore function for shutil.copytree."""

    def custom_ignore(src, names):
        if ignore_git:
            return [n for n in names if n == ".git" or n.startswith(".git")]
        return []

    return custom_ignore


def prepare_git_directory(dest_git_path):
    """Prepare the destination .git directory by removing existing one if needed."""
    if dest_git_path.exists():
        if dest_git_path.is_file():
            dest_git_path.unlink()
        else:  # is_dir
            shutil.rmtree(dest_git_path)


def initialize_git_repository(destination):
    """Initialize a new Git repository at the destination."""
    subprocess.run(
        ["git", "init"],
        cwd=str(destination),
        check=True,
        capture_output=True,
    )
    logger.debug(f"Initialized new Git repository at {destination}")


def delete_git_branches(destination, exclude_branches=None):
    """Delete Git branches in the repository.

    Args:
        destination: Path to the Git repository
        exclude_branches: List of branch names to exclude from deletion (default: None)

    Returns:
        List of successfully deleted branch names
    """
    if exclude_branches is None:
        exclude_branches = []

    deleted_branches = []

    # Get all branches
    result = subprocess.run(
        ["git", "branch"],
        cwd=str(destination),
        check=True,
        capture_output=True,
        text=True,
    )

    # Parse branch names
    branches = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("*"):
            # Skip the current HEAD which is likely (no branch)
            continue
        branch_name = line.strip()
        if branch_name not in exclude_branches:
            branches.append(branch_name)

    # Delete branches
    for branch in branches:
        try:
            # Force delete the branch
            subprocess.run(
                ["git", "branch", "-D", branch],
                cwd=str(destination),
                check=True,
                capture_output=True,
            )
            logger.debug(f"Deleted branch {branch} from repository in {destination}")
            deleted_branches.append(branch)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to delete branch {branch}: {e}")

    return deleted_branches


def cleanup_git_branches(destination):
    """Clean up all branches and make the current detached HEAD the new main branch.

    This function:
    1. Identifies all existing branches
    2. Creates a new main branch from the current HEAD
    3. Deletes all other branches completely

    Args:
        destination: Path to the Git repository
    """
    try:
        # Delete all branches except main
        deleted_branches = delete_git_branches(destination, exclude_branches=[])
        if deleted_branches:
            logger.debug(f"Deleted branches: {', '.join(deleted_branches)}")

        # Create a new main branch from the current HEAD
        subprocess.run(
            ["git", "checkout", "-b", "main"],
            cwd=str(destination),
            check=True,
            capture_output=True,
        )
        logger.debug(f"Created new main branch from detached HEAD in {destination}")

        # Delete all branches except main
        deleted_branches = delete_git_branches(destination, exclude_branches=[])
        if deleted_branches:
            logger.debug(f"Deleted branches: {', '.join(deleted_branches)}")

        # Garbage collect to ensure deleted branches are completely removed
        subprocess.run(
            ["git", "gc", "--prune=now", "--aggressive"],
            cwd=str(destination),
            check=True,
            capture_output=True,
        )
        logger.debug(f"Completed garbage collection in {destination}")

        # Final step: Explicitly checkout to the main branch to ensure we're on it
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=str(destination),
            check=True,
            capture_output=True,
        )
        logger.debug(f"Checked out to main branch in {destination}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error cleaning up Git branches: {e}")
