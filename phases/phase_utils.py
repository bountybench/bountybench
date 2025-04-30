from pathlib import Path

from resources.bounty_setup_resource import BountySetupResourceConfig
from resources.repo_setup_resource import RepoSetupResourceConfig
from resources.resource_type import ResourceType
from resources.utils import contains_setup


def get_setup_resources(
    task_dir: Path,
    bounty_number: str,
    skip_bounty_setup: bool = False, 
) -> None:
    """
    Returns setup resources configurations if setup scripts exist.
    """
    setup_resource_list = []
    setup_repo_env_script = task_dir / "setup_repo_env.sh"
    if contains_setup(setup_repo_env_script):
        setup_resource_list.append(
            (
                ResourceType.REPO_SETUP,
                RepoSetupResourceConfig(
                    task_dir=task_dir,
                ),
            )
        )

    setup_bounty_env_script = (
        task_dir / "bounties" / f"bounty_{bounty_number}" / "setup_files" / "setup_bounty_env.sh"
    )

    if contains_setup(setup_bounty_env_script):
        setup_resource_list.append(
            (
                ResourceType.BOUNTY_SETUP,
                BountySetupResourceConfig(
                    task_dir=task_dir,
                    bounty_number=bounty_number,
                    skip_setup=skip_bounty_setup
                ),
            )
        )

    return setup_resource_list
