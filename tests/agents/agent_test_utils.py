from collections import defaultdict
from dataclasses import dataclass
import os
import stat
from pathlib import Path
import pytest

from resources.resource_manager import ResourceManager
from resources.docker_resource import DockerResource, DockerResourceConfig
from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.setup_resource import SetupResource, SetupResourceConfig
from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.utils import read_bounty_metadata, read_repo_metadata
from workflows.utils import setup_shared_network

EXPLOIT_SCRIPT_NAME = "exploit.sh"
VERIFY_SCRIPT_NAME = "verify.sh"

def _subtract_paths(path1: Path, path2: Path):
    # Convert both paths to absolute paths for reliable comparison
    abs_path1 = path1.resolve()
    abs_path2 = path2.resolve()

    try:
        remaining_path = abs_path1.relative_to(abs_path2)
        return remaining_path
    except ValueError:
        raise ValueError(f"{path2} is not a subset of {path1}")
@dataclass
class EnvPath():
    """
    Initialize the "enum" using the following params.

    Params:
        repo_name (str): Name of repo
        bounty_number (int): Bounty number
        tmp_dir_name (str): Name of tmp folder, usually "tmp"
        codebase_files_dir_name (str): Name of codebase folder, usually "codebase"
        exploit_files_dir_name (str): Name of exploit_files folder, usually "exploit_files"

    Important Paths:
        task_dir (Path): Path to task_dir (e.g., bountybench/lunary)
        bounty_dir (Path): Path to bounty_dir (e.g., bountybench/lunary/bounties/bounty0)
        tmp_dir (Path): Path to created tmp dir (e.g., bountybench/lunary/tmp)
        codebase_files_dir (Path): Path to codebase files (also called files_dir)
        verify_script_dir: Path to verify script (e.g., bountybench/lunary/bounties/bounty0/verify.sh)
        exploit_script_dir: Path to exploit script that agent will call (e.g., {tmp_dir}/exploit.sh)
        exploit_files_dir: Path to exploit_files in bounty (not the same as exploit_script_dir)

    Conventions <-> Examples in codebase:
    - 'dir_name' <-> 'tmp'
    - 'dir' <-> usually absolute path or relative path (from pwd) 
    """
    TASK_DIR = ""
    BOUNTY_DIR = ""
    TMP_DIR = ""
    CODEBASE_FILES_DIR = ""
    TMP_CODEBASE_FILES_DIR = ""
    VERIFY_SCRIPT_DIR = ""
    TMP_EXPLOIT_SCRIPT_DIR = ""
    EXPLOIT_FILES_DIR = ""
    AGENT_PATCHES_DIR = ""

    BOUNTY_DIR_FROM_TASK_DIR = ""

    TMP_DIR_NAME = ""
    CODEBASE_FILES_DIR_NAME = ""
    EXPLOIT_FILES_DIR_NAME = ""

    def __init__(
        cls,
        repo_name: str,
        bounty_number: int,
        tmp_dir_name: str = "tmp",
        codebase_files_dir_name: str = "codebase",
        exploit_files_dir_name: str = "exploit_files",
    ):
        """
        Initializes all paths dynamically using the provided repo_name and bounty_number.
        """
        task_dir = Path(os.path.abspath(os.path.join("bountybench", repo_name)))
        bounty_dir = task_dir / "bounties" / f"bounty_{bounty_number}"
        tmp_dir = task_dir / tmp_dir_name
        codebase_files_dir = task_dir / codebase_files_dir_name
        tmp_codebase_files_dir = tmp_dir / codebase_files_dir_name
        verify_script_dir = bounty_dir / VERIFY_SCRIPT_NAME
        tmp_exploit_script_dir = tmp_dir / EXPLOIT_SCRIPT_NAME
        exploit_files_dir = bounty_dir / exploit_files_dir_name
        agent_patches_dir = bounty_dir / "agent-patches"

        bounty_dir_from_task_dir = _subtract_paths(bounty_dir, task_dir)

        # Setting the actual value of each enum member
        cls.TASK_DIR = str(task_dir)
        cls.BOUNTY_DIR = str(bounty_dir)
        cls.TMP_DIR = str(tmp_dir)
        cls.CODEBASE_FILES_DIR = str(codebase_files_dir)
        cls.TMP_CODEBASE_FILES_DIR = str(tmp_codebase_files_dir)
        cls.VERIFY_SCRIPT_DIR = str(verify_script_dir)
        cls.TMP_EXPLOIT_SCRIPT_DIR = str(tmp_exploit_script_dir)
        cls.EXPLOIT_FILES_DIR = str(exploit_files_dir)
        cls.AGENT_PATCHES_DIR = str(agent_patches_dir)

        cls.BOUNTY_DIR_FROM_TASK_DIR = str(bounty_dir_from_task_dir)

        cls.TMP_DIR_NAME = tmp_dir_name
        cls.CODEBASE_FILES_DIR_NAME = codebase_files_dir_name
        cls.EXPLOIT_FILES_DIR_NAME = exploit_files_dir_name

# Setup bounties and initialize needed resources for all agent tests once
def bounty_setup(
        repo_name: str,
        bounty_number: int,
        init_files=True,
        repo_resource=True,
        bounty_resource=True,
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
    vulnerable_commit = bounty_metadata['vulnerable_commit']


    # Initialize resources 
    resources = []

    resource_manager = ResourceManager(workflow_id="1")
    if init_files:
        init_config = InitFilesResourceConfig(
            task_dir=env_path.TASK_DIR,
            files_dir_name=env_path.CODEBASE_FILES_DIR_NAME,
            tmp_dir_name=env_path.TMP_DIR_NAME,
            bounty_number=bounty_number,
            exploit_files_dir_name=env_path.EXPLOIT_FILES_DIR_NAME,
            vulnerable_commit=vulnerable_commit,
        )
        resources.append("init_files")
        resource_manager.register_resource("init_files", InitFilesResource, init_config)
    
    if repo_resource:
        repo_config = SetupResourceConfig(
            bounty_level_setup=False,
            task_dir=env_path.TASK_DIR,
            bounty_number=bounty_number
        )
        resources.append("repo_resource")
        resource_manager.register_resource("repo_resource", SetupResource, repo_config)
    
    if bounty_resource:
        bounty_config = SetupResourceConfig(
            bounty_level_setup=True,
            task_dir=env_path.TASK_DIR,
            bounty_number=bounty_number
        )
        resources.append("bounty_resource")
        resource_manager.register_resource("bounty_resource", SetupResource, bounty_config)
    
    if kali_env_resource:
        kali_env_config = KaliEnvResourceConfig(
            task_dir=env_path.TASK_DIR,
            bounty_number=bounty_number,
            volumes= {
                os.path.abspath(env_path.TMP_DIR): {"bind": "/app", "mode": "rw"},
            }, 
            target_host= repo_metadata["target_host"],
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
        bounty_resource=False,
    )


def write_to_file_and_make_executable(script_path: Path, exit_code: int):
    file_text = f"#!/usr/bin/env bash\nexit {exit_code}\n"
    script_path.write_text(file_text)
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
