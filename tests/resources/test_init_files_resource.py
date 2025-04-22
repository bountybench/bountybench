import os
import shutil
import subprocess
from pathlib import Path

import pytest

from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from utils.git_utils import (
    cleanup_git_branches,
    create_git_ignore_function,
    initialize_git_repository,
    prepare_git_directory,
)


@pytest.fixture
def setup_dirs():
    task_repo_dir = Path.cwd() / "tests" / "resources" / "test_files"
    tmp_dir_name = "tmp_dir_for_testing"
    tmp_dir = task_repo_dir / tmp_dir_name
    original_files_dir = task_repo_dir / "original_files"
    bounty_dir = task_repo_dir / "bounties" / "bounty_1234"
    verify_files_dir = bounty_dir / "verify_files"
    verify_file_path = verify_files_dir / "verify.sh"
    exploit_files_dir = bounty_dir / "exploit_files"
    exploit_file_path = exploit_files_dir / "exploit.sh"

    if task_repo_dir.exists():
        shutil.rmtree(task_repo_dir)

    # Create necessary directories
    original_files_dir.mkdir(parents=True, exist_ok=True)
    bounty_dir.mkdir(parents=True, exist_ok=True)
    verify_files_dir.mkdir(parents=True, exist_ok=True)
    exploit_files_dir.mkdir(parents=True, exist_ok=True)

    # Create test files
    (original_files_dir / "test_file.txt").write_text("This is a test.")
    verify_file_path.write_text("#!/bin/bash\necho 'verify script'\nexit 0")
    (verify_files_dir / "helper.sh").write_text(
        "#!/bin/bash\necho 'helper script'\nexit 0"
    )

    exploit_script = """#!/bin/bash
IS_CI_RUN=$1
HOSTNAME1='localhost'
HOSTNAME2='localhost'

if [ "$IS_CI_RUN" = true ]; then
    HOSTNAME1='server-name1'
    HOSTNAME2='server-name2'
fi

pip install -e ./codebase

python3 solver.py $HOSTNAME1 $HOSTNAME2
"""

    exploit_file_path.write_text(exploit_script)
    (exploit_files_dir / "solver.py").write_text("print('hello')")

    subprocess.run(["git", "init"], cwd=original_files_dir)
    subprocess.run(["git", "add", "."], cwd=original_files_dir)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=original_files_dir)
    subprocess.run(["git", "branch", "-m", "main"], cwd=original_files_dir)

    # Default to no exploit_files copying
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


@pytest.fixture
def setup_git_repos():
    """Setup Git repositories for testing, including a main repo and a submodule."""
    test_dir = Path.cwd() / "tests" / "resources" / "git_test_files"

    # Clean up any existing test directories
    if test_dir.exists():
        shutil.rmtree(test_dir)

    # Create test directory structure
    test_dir.mkdir(parents=True, exist_ok=True)
    main_repo = test_dir / "main_repo"
    submodule_repo = test_dir / "submodule_repo"
    destination = test_dir / "destination"

    # Create main repository
    main_repo.mkdir()
    (main_repo / "main_file.txt").write_text("Content in main repo")

    # Initialize main repository
    subprocess.run(["git", "init"], cwd=main_repo, check=True)

    # Create an .env file
    with open(main_repo / ".env", "w") as f:
        f.write(f"ENV_ID=11111")

    subprocess.run(["git", "add", "."], cwd=main_repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=main_repo, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=main_repo, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit in main repo"],
        cwd=main_repo,
        check=True,
    )
    subprocess.run(["git", "branch", "-m", "main"], cwd=main_repo, check=True)

    # Create another branch in main repo
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=main_repo, check=True)
    (main_repo / "feature_file.txt").write_text("Content in feature branch")

    subprocess.run(["git", "add", "."], cwd=main_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Commit in feature branch"], cwd=main_repo, check=True
    )
    subprocess.run(["git", "checkout", "main"], cwd=main_repo, check=True)

    # Create submodule repository
    submodule_repo.mkdir()
    (submodule_repo / "submodule_file.txt").write_text("Content in submodule")

    # Initialize submodule repository
    subprocess.run(["git", "init"], cwd=submodule_repo, check=True)
    subprocess.run(["git", "add", "."], cwd=submodule_repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=submodule_repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=submodule_repo, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit in submodule"],
        cwd=submodule_repo,
        check=True,
    )
    subprocess.run(["git", "branch", "-m", "main"], cwd=submodule_repo, check=True)

    # Instead of using git submodule add (which can be problematic in tests),
    # manually create a submodule-like structure
    sub_dir = main_repo / "sub"
    sub_dir.mkdir(exist_ok=True)

    # Copy files from submodule repo to the sub directory
    for item in submodule_repo.iterdir():
        if item.name != ".git":
            if item.is_file():
                shutil.copy2(item, sub_dir / item.name)
            else:
                shutil.copytree(item, sub_dir / item.name, dirs_exist_ok=True)

    # Create a .git file that points to the submodule repo's .git directory
    with open(sub_dir / ".git", "w") as f:
        f.write(f"gitdir: {os.path.relpath(submodule_repo / '.git', sub_dir)}")

    # Add and commit the submodule
    subprocess.run(["git", "add", "sub"], cwd=main_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add submodule-like structure"],
        cwd=main_repo,
        check=True,
    )

    # Create destination directory
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir()

    yield main_repo, submodule_repo, destination

    # Clean up
    if test_dir.exists():
        shutil.rmtree(test_dir)


def test_create_git_ignore_function():
    """Test the create_git_ignore_function utility."""
    # Test with ignore_git=True
    ignore_func = create_git_ignore_function(True)
    names = [".git", ".gitignore", "file.txt", ".gitattributes"]
    ignored = ignore_func("/some/path", names)
    assert ".git" in ignored
    assert ".gitattributes" in ignored
    assert "file.txt" not in ignored

    # Test with ignore_git=False
    ignore_func = create_git_ignore_function(False)
    ignored = ignore_func("/some/path", names)
    assert len(ignored) == 0


def test_prepare_git_directory(tmp_path):
    """Test the prepare_git_directory utility."""
    # Test with non-existent directory
    git_dir = tmp_path / ".git"
    prepare_git_directory(git_dir)
    assert not git_dir.exists()

    # Test with existing file
    git_dir.write_text("gitdir: /path/to/repo")
    assert git_dir.is_file()
    prepare_git_directory(git_dir)
    assert not git_dir.exists()

    # Test with existing directory
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\n\tbare = false")
    assert git_dir.is_dir()
    prepare_git_directory(git_dir)
    assert not git_dir.exists()


def test_initialize_git_repository(tmp_path):
    """Test the initialize_git_repository utility."""
    initialize_git_repository(tmp_path)
    git_dir = tmp_path / ".git"
    assert git_dir.exists()
    assert git_dir.is_dir()

    # Check that basic Git files were created
    assert (git_dir / "HEAD").exists()
    assert (git_dir / "config").exists()


def test_copy_files_with_git(resource, setup_git_repos):
    """Test copying files with Git repositories."""
    main_repo, _, destination = setup_git_repos

    # Copy the repository with Git data
    resource.copy_files(main_repo, destination, ignore_git=False)

    # Check that files were copied
    assert (destination / "main_file.txt").exists()
    assert (destination / "sub").exists()
    assert (destination / "sub" / "submodule_file.txt").exists()

    # Check that .git directory exists and is a directory (not a file)
    git_dir = destination / ".git"
    assert git_dir.exists()
    assert git_dir.is_dir()

    # Verify Git functionality in the copied repository
    result = subprocess.run(
        ["git", "status"],
        cwd=destination,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "On branch main" in result.stdout

    # Verify that only main branch exists
    branch_result = subprocess.run(
        ["git", "branch"],
        cwd=destination,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "* main" in branch_result.stdout
    assert "feature" not in branch_result.stdout


def test_copy_files_with_skip(resource, setup_git_repos):
    """Test copying files with Git repositories."""
    main_repo, _, destination = setup_git_repos
    # Copy the repository with Git data
    resource.copy_files(
        main_repo, destination, ignore_git=False, skip_hidden_files=True
    )
    # Check that files were copied
    assert not (destination / ".env").exists()


def test_copy_files_no_skip(resource, setup_git_repos):
    """Test copying files with Git repositories."""
    main_repo, _, destination = setup_git_repos
    assert (main_repo / ".env").exists()
    # Copy the repository with Git data
    resource.copy_files(main_repo, destination, ignore_git=False)
    # Check that files were copied
    assert (destination / ".env").exists()


def test_cleanup_git_branches(setup_git_repos):
    """Test the cleanup_git_branches function."""
    main_repo, _, destination = setup_git_repos

    # Copy the repository structure without Git data
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(main_repo, destination, ignore=shutil.ignore_patterns(".git"))

    # Initialize a new Git repository
    initialize_git_repository(destination)

    # Create multiple branches
    subprocess.run(["git", "add", "."], cwd=destination, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=destination, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=destination, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=destination, check=True
    )

    # Create feature branch
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=destination, check=True)
    (destination / "feature_file.txt").write_text("Feature content")
    subprocess.run(["git", "add", "."], cwd=destination, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Feature commit"], cwd=destination, check=True
    )

    # Create another branch
    subprocess.run(["git", "checkout", "-b", "dev"], cwd=destination, check=True)

    # Verify we have multiple branches
    branch_result = subprocess.run(
        ["git", "branch"],
        cwd=destination,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "feature" in branch_result.stdout
    assert "* dev" in branch_result.stdout

    # Run cleanup_git_branches
    cleanup_git_branches(destination)

    # Verify only main branch exists now
    branch_result = subprocess.run(
        ["git", "branch"],
        cwd=destination,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "* main" in branch_result.stdout
    assert "feature" not in branch_result.stdout
    assert "dev" not in branch_result.stdout


def test_handle_git_submodule(resource, setup_git_repos):
    """Test handling of Git submodules."""
    main_repo, _, destination = setup_git_repos

    # Get the submodule .git file
    submodule_git_file = main_repo / "sub" / ".git"
    assert submodule_git_file.exists()
    assert submodule_git_file.is_file()

    # Create a destination for the submodule
    sub_destination = destination / "sub"
    sub_destination.mkdir(parents=True)

    # Copy the submodule directory
    resource.copy_files(main_repo / "sub", sub_destination, ignore_git=False)

    # Verify the submodule was converted to a standalone Git repository
    git_dir = sub_destination / ".git"
    assert git_dir.exists()
    assert git_dir.is_dir()

    # Verify Git functionality in the copied submodule
    result = subprocess.run(
        ["git", "status"],
        cwd=sub_destination,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "On branch main" in result.stdout


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

    # Check that helper.sh was copied
    helper_file_path = tmp_dir / "verify_files" / "helper.sh"
    assert helper_file_path.exists(), "helper.sh file was not copied"
    assert (
        "helper script" in helper_file_path.read_text()
    ), "helper.sh content is incorrect"


def test_verify_files_not_copied_by_default(setup_dirs):
    """Test that verify_files directory is not copied if not specified in config."""
    config, tmp_dir, original_files_dir, bounty_dir = setup_dirs

    # Create a modified config without verify_files_dir_name
    config_without_verify = InitFilesResourceConfig(
        task_dir=config.task_dir,
        files_dir_name=config.files_dir_name,
        tmp_dir=config.tmp_dir,
        bounty_number=config.bounty_number,
        vulnerable_commit=config.vulnerable_commit,
        # Explicitly not setting input_verify_files_dir_name
    )

    # Create a new resource with the modified config
    resource = InitFilesResource(
        resource_id="test_resource_no_verify", config=config_without_verify
    )

    # Verify that verify_files is None in the resource
    assert (
        resource.input_verify_files_dir is None
    ), "input_verify_files_dir should be None when not specified"

    # Check that verify files were not copied
    verify_files_dir_in_tmp = tmp_dir / "verify_files"
    assert (
        not verify_files_dir_in_tmp.exists()
    ), "verify_files directory should not be copied when not specified in config"

    # Manually remove resource for cleanup
    resource.stop()


def test_exploit_files_no_copy_default(resource, setup_dirs):
    """Test that exploit_files directory is not copied if not specified in config."""
    config, tmp_dir, _, _ = setup_dirs

    # Verify that exploit_files is None in the resource
    assert (
        resource.input_exploit_files_dir is None
    ), "input_exploit_files_dir should be None when not specified"

    # Check that exploit.sh file is not copied
    tmp_dir_exploit_files_dir = tmp_dir / "exploit_files"
    exploit_script_in_tmp = tmp_dir_exploit_files_dir / "exploit.sh"
    assert (
        not exploit_script_in_tmp.exists()
    ), "exploit.sh should not be copied when not specified in config"

    # Manually remove resource for cleanup
    resource.stop()


def test_exploit_files_copy(setup_dirs):
    """Test that exploit_files directory is copied if specified in config."""
    config, tmp_dir, _, bounty_dir = setup_dirs

    # Create a modified config with exploit_files_dir_name
    config_with_exploit = InitFilesResourceConfig(
        task_dir=config.task_dir,
        files_dir_name=config.files_dir_name,
        tmp_dir=config.tmp_dir,
        bounty_number=config.bounty_number,
        vulnerable_commit=config.vulnerable_commit,
        input_exploit_files_dir_name="exploit_files",
    )

    # Create a new resource with the modified config
    resource = InitFilesResource(
        resource_id="test_resource_with_exploit", config=config_with_exploit
    )

    # Ensure source directories and files exist
    source_exploit_files_dir = bounty_dir / "exploit_files"
    source_helper_file = source_exploit_files_dir / "solver.py"

    assert (
        source_exploit_files_dir.exists()
    ), "Source exploit_files directory does not exist"
    assert source_helper_file.exists(), "Source solver.py file does not exist"

    # Get the actual input_exploit_files_dir path from the resource
    resource_input_exploit_files_dir = resource.input_exploit_files_dir
    print(f"Source exploit_files directory: {source_exploit_files_dir}")
    print(f"Resource input_exploit_files_dir: {resource_input_exploit_files_dir}")
    # Check that exploit.sh was copied
    tmp_dir_exploit_files_dir = (
        tmp_dir / config_with_exploit.input_exploit_files_dir_name
    )
    exploit_file_path = tmp_dir_exploit_files_dir / "exploit.sh"
    assert exploit_file_path.exists(), "exploit.sh file was not copied"
    processed_exploit_script = exploit_file_path.read_text()
    expected_processed_script = """#!/bin/bash
HOSTNAME1='server-name1'
HOSTNAME2='server-name2'

pip install -e ./codebase

python3 solver.py $HOSTNAME1 $HOSTNAME2"""
    print(processed_exploit_script)
    print(expected_processed_script)
    assert (
        processed_exploit_script == expected_processed_script
    ), "exploit.sh processed script mismatch"

    # Check that helper script solver.py was copied
    helper_file_path = tmp_dir_exploit_files_dir / "solver.py"
    assert helper_file_path.exists(), "solver.py file was not copied"
    assert "hello" in helper_file_path.read_text(), "solver.py content is incorrect"
