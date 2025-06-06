import stat
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pytest

from resources.bounty_setup_resource import (
    BountySetupResource,
    BountySetupResourceConfig,
)
from resources.docker_resource import DockerResource, DockerResourceConfig
from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.repo_setup_resource import RepoSetupResource, RepoSetupResourceConfig
from resources.resource_manager import ResourceManager
from resources.utils import read_bounty_metadata, read_repo_metadata
from workflows.utils import setup_shared_network

EXPLOIT_SCRIPT_NAME = "exploit.sh"
VERIFY_SCRIPT_NAME = "verify.sh"


workflow_id = "1"


@dataclass
class EnvPath:
    """
    Initialize the "enum" using the following params.

    Params:
        repo_name (str): Name of repo
        bounty_number (int): Bounty number
        tmp_dir_name (str): Name of tmp folder, usually "tmp"
        codebase_files_dir_name (str): Name of codebase folder, usually "codebase"
        exploit_files_dir_name (str): Name of exploit_files folder, usually "exploit_files"

    Important Paths:
        task_dir (Path): Path to task_dir (e.g., bountytasks/lunary)
        bounty_dir (Path): Path to bounty_dir (e.g., bountytasks/lunary/bounties/bounty0)
        tmp_dir (Path): Path to created tmp dir (e.g., bountytasks/lunary/tmp)
        codebase_files_dir (Path): Path to codebase files (also called files_dir)
        verify_script_dir: Path to verify script (e.g., bountytasks/lunary/bounties/bounty0/verify.sh)
        exploit_script_dir: Path to exploit script that agent will call (e.g., {tmp_dir}/exploit.sh)
        exploit_files_dir: Path to exploit_files in bounty (not the same as exploit_script_dir)

    Conventions <-> Examples in codebase:
    - 'dir_name' <-> 'tmp'
    - 'dir' <-> usually absolute path or relative path (from pwd)
    """

    TASK_DIR: Path = Path()
    BOUNTY_DIR: Path = Path()
    TMP_DIR: Path = Path()
    CODEBASE_FILES_DIR: Path = Path()
    TMP_CODEBASE_FILES_DIR: Path = Path()
    VERIFY_SCRIPT_DIR: Path = Path()
    VERIFY_FILES_DIR: Path = Path()
    TMP_EXPLOIT_SCRIPT_DIR: Path = Path()
    EXPLOIT_FILES_DIR: Path = Path()
    AGENT_PATCHES_DIR: Path = Path()

    CODEBASE_FILES_DIR_NAME: str = ""
    EXPLOIT_FILES_DIR_NAME: str = ""
    OUTPUT_PATH_DIR_NAME: str = ""

    def __init__(
        self,
        repo_name: str,
        bounty_number: int,
        workflow_id: str = "1",
        codebase_files_dir_name: str = "codebase",
        exploit_files_dir_name: str = "exploit_files",
    ):
        """
        Initializes all paths dynamically using the provided repo_name and bounty_number.
        """

        task_dir = Path("bountytasks") / repo_name
        bounty_dir = task_dir / "bounties" / f"bounty_{bounty_number}"
        tmp_dir = (
            task_dir / "bounties" / f"bounty_{bounty_number}" / f"tmp_{workflow_id}"
        )
        codebase_files_dir = task_dir / codebase_files_dir_name
        tmp_codebase_files_dir = tmp_dir / codebase_files_dir_name
        verify_script_dir = bounty_dir / VERIFY_SCRIPT_NAME
        verify_files_dir = bounty_dir / "verify_files"
        tmp_exploit_script_dir = tmp_dir / EXPLOIT_SCRIPT_NAME
        exploit_files_dir = bounty_dir / exploit_files_dir_name
        agent_patches_dir = bounty_dir / f"agent_created_files_{workflow_id}"

        # Setting the actual value of each enum member
        self.TASK_DIR = task_dir.resolve()
        self.BOUNTY_DIR = bounty_dir
        self.TMP_DIR = tmp_dir
        self.CODEBASE_FILES_DIR = codebase_files_dir
        self.TMP_CODEBASE_FILES_DIR = tmp_codebase_files_dir
        self.VERIFY_SCRIPT_DIR = verify_script_dir
        self.VERIFY_FILES_DIR = verify_files_dir
        self.TMP_EXPLOIT_SCRIPT_DIR = tmp_exploit_script_dir
        self.EXPLOIT_FILES_DIR = exploit_files_dir
        self.AGENT_PATCHES_DIR = agent_patches_dir
        self.OUTPUT_PATH_DIR_NAME = f"agent_created_files_{workflow_id}"

        self.CODEBASE_FILES_DIR_NAME = codebase_files_dir_name
        self.EXPLOIT_FILES_DIR_NAME = exploit_files_dir_name


# Setup bounties and initialize needed resources for all agent tests once
def bounty_setup(
    repo_name: str,
    bounty_number: int,
    init_files=True,
    repo_setup=True,
    bounty_setup=True,
    kali_env_resource=True,
    docker=True,
) -> EnvPath:
    # Initialize EnvPath enum for use in tests
    env_path = EnvPath(repo_name, bounty_number)

    # The rest of the code assumes bounty_number is a str
    bounty_number = str(bounty_number)

    setup_shared_network()
    bounty_metadata = read_bounty_metadata(env_path.TASK_DIR, bounty_number)
    repo_metadata = read_repo_metadata(env_path.TASK_DIR)
    vulnerable_commit = bounty_metadata["vulnerable_commit"]

    # Initialize resources
    resources = []

    resource_manager = ResourceManager(workflow_id=workflow_id)
    if init_files:
        init_config = InitFilesResourceConfig(
            task_dir=env_path.TASK_DIR,
            files_dir_name=env_path.CODEBASE_FILES_DIR_NAME,
            tmp_dir=env_path.TMP_DIR,
            bounty_number=bounty_number,
            input_exploit_files_dir_name=env_path.EXPLOIT_FILES_DIR_NAME,
            output_agent_files_name=env_path.OUTPUT_PATH_DIR_NAME,
            vulnerable_commit=vulnerable_commit,
        )
        resources.append("init_files")
        resource_manager.register_resource("init_files", InitFilesResource, init_config)

    if repo_setup:
        repo_config = RepoSetupResourceConfig(task_dir=env_path.TASK_DIR)
        resources.append("repo_setup")
        resource_manager.register_resource("repo_setup", RepoSetupResource, repo_config)

    if bounty_setup:
        bounty_config = BountySetupResourceConfig(
            task_dir=env_path.TASK_DIR, bounty_number=bounty_number
        )
        resources.append("bounty_setup")
        resource_manager.register_resource(
            "bounty_setup", BountySetupResource, bounty_config
        )

    if kali_env_resource:
        kali_env_config = KaliEnvResourceConfig(
            task_dir=env_path.TASK_DIR,
            bounty_number=bounty_number,
            volumes={
                str(env_path.TMP_DIR.resolve()): {"bind": "/app", "mode": "rw"},
            },
            target_hosts=[repo_metadata["target_host"]],
        )
        resources.append("kali_env")
        resource_manager.register_resource("kali_env", KaliEnvResource, kali_env_config)

    if docker:
        docker_config = DockerResourceConfig()
        resources.append("docker")
        resource_manager.register_resource("docker", DockerResource, docker_config)

    resource_manager.initialize_phase_resources(0, resources)

    return env_path


@pytest.fixture(scope="session")
def lunary_bounty_0_setup():
    repo_name = "lunary"
    bounty_number = 0
    yield bounty_setup(
        repo_name=repo_name,
        bounty_number=bounty_number,
        bounty_setup=False,
    )


def write_to_file_and_make_executable(script_path: Path, exit_code: int):
    file_text = f"#!/usr/bin/env bash\nexit {exit_code}\n"
    script_path.write_text(file_text)
    current_mode = script_path.stat().st_mode
    script_path.chmod(current_mode | stat.S_IXUSR)
