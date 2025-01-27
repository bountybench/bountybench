from dataclasses import dataclass
import os
from pathlib import Path
import pytest

from resources.resource_manager import ResourceManager
from resources.docker_resource import DockerResource, DockerResourceConfig
from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig
from resources.setup_resource import SetupResource, SetupResourceConfig
from resources.utils import read_bounty_metadata
from workflows.utils import setup_shared_network

environment_fixtures_count = 0
EXPLOIT_SCRIPT_NAME = "exploit.sh"
VERIFY_SCRIPT_NAME = "verify.sh"

@dataclass
class EnvPathAssistant:
    """
    This class aims to reduce confusion and manual path joins while testing.
    Assumes we are in bountyagent base folder.

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
    repo_name: str
    bounty_number: int
    tmp_dir_name: str = "tmp"
    codebase_files_dir_name: str = "codebase"
    exploit_files_dir_name: str = "exploit_files"

    def __post_init__(self):
        self.task_dir: Path = Path(os.path.abspath(os.path.join("bountybench", self.repo_name)))
        self.bounty_dir: Path = self.task_dir / "bounties" / f"bounty_{self.bounty_number}"
        self.tmp_dir = self.task_dir / self.tmp_dir_name
        self.codebase_files_dir: Path = self.task_dir / self.codebase_files_dir_name
        self.verify_script_dir: Path = self.bounty_dir / VERIFY_SCRIPT_NAME
        self.exploit_script_dir: Path = self.tmp_dir / EXPLOIT_SCRIPT_NAME
        self.exploit_files_dir: Path = self.bounty_dir / "exploit_files"

    def _subtract_paths(self, path1: Path, path2: Path):
        # Convert both paths to absolute paths for reliable comparison
        abs_path1 = path1.resolve()
        abs_path2 = path2.resolve()

        try:
            remaining_path = abs_path1.relative_to(abs_path2)
            return remaining_path
        except ValueError:
            raise ValueError(f"{path2} is not a subset of {path1}")
    
    def _return_path(self, path: Path, as_path: bool):
        return str(path) if not as_path else path

    ###############################################
    #                                             #
    #               Regular Paths                 #
    #                                             #
    ###############################################
    def get_task_dir(self, as_path=False):
        return self._return_path(self.task_dir, as_path)

    def get_bounty_dir(self, as_path=False):
        return self._return_path(self.bounty_dir, as_path)
    
    def get_tmp_dir(self, as_path=False):
        return self._return_path(self.tmp_dir, as_path)
    
    def get_tmp_dir_name(self) -> str:
        return self.tmp_dir.name
    
    def get_codebase_files_dir(self, as_path=False):
        return self._return_path(self.codebase_files_dir, as_path)

    def get_codebase_files_dir_name(self) -> str:
        return self.codebase_files_dir.name
    
    def get_files_dir(self, as_path=False):
        return self.get_codebase_files_dir(as_path)

    def get_files_dir_name(self) -> str:
        return self.get_codebase_files_dir_name()
    
    def get_tmp_codebase_files_dir(self, as_path=False):
        return self._return_path(self.tmp_dir / self.codebase_files_dir.name, as_path)

    def get_tmp_files_dir(self, as_path=False):
        return self._return_path(self.tmp_dir / self.codebase_files_dir.name, as_path)
    
    def get_verify_script_dir(self, as_path=False):
        return self._return_path(self.verify_script_dir, as_path)

    def get_exploit_script_dir(self, as_path=False):
        """
        Exploit script that the docker container runs (in tmp) 
        """
        return self._return_path(self.exploit_script_dir, as_path)

    def get_exploit_files_dir(self, as_path=False):
        """
        Exploit files folder in the bounty folder
        """
        return self._return_path(self.exploit_files_dir, as_path)
    
    def get_exploit_files_dir_name(self) -> str:
        return self.exploit_files_dir.name
    
    ###############################################
    #                                             #
    #               Compound Paths                #
    #                                             #
    ###############################################
    def get_bounty_dir_from_task_dir(self, as_path=False):
        path = self._subtract_paths(self.bounty_dir, self.task_dir)
        return self._return_path(path, as_path)

# Setup bounties and initialize needed resources for all agent tests once
def bounty_setup(repo_name: str, bounty_number: int) -> EnvPathAssistant:
    path_assistant = EnvPathAssistant(
        repo_name=repo_name,
        bounty_number=bounty_number
    )

    # The rest of the code assumes bounty_number is a str
    bounty_number = str(bounty_number)

    setup_shared_network()
    bounty_metadata = read_bounty_metadata(path_assistant.get_task_dir(), bounty_number)
    vulnerable_commit = bounty_metadata['vulnerable_commit']


    # Configurations
    init_config = InitFilesResourceConfig(
        task_dir=path_assistant.get_task_dir(),
        files_dir_name=path_assistant.get_files_dir_name(),
        tmp_dir_name=path_assistant.get_tmp_dir_name(),
        bounty_number=bounty_number,
        exploit_files_dir_name=path_assistant.get_exploit_files_dir_name(),
        vulnerable_commit=vulnerable_commit,
    )
    setup_config = SetupResourceConfig(
        bounty_level_setup=False,
        task_dir=path_assistant.get_task_dir(),
        bounty_number=bounty_number
    )
    docker_config = DockerResourceConfig()
    
    # Initialize resources and agent
    resource_manager = ResourceManager()
    resource_manager.register_resource("init_files", InitFilesResource, init_config)
    resource_manager.register_resource("repo_resource", SetupResource, setup_config)
    resource_manager.register_resource("docker", DockerResource, docker_config)
    resource_manager.initialize_phase_resources(0, ["init_files", "repo_resource", "docker"])

    return path_assistant


@pytest.fixture(scope="session")
def lunary_bounty_0_setup():
    global environment_fixtures_count
    assert environment_fixtures_count == 0, "Too many environment fixtures"
    environment_fixtures_count += 1
    repo_name = "lunary"
    bounty_number = 0
    yield bounty_setup(
        repo_name=repo_name,
        bounty_number=bounty_number,
    )
