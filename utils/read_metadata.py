import json
import logging
import os
import sys
from typing import Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_repo_metadata(task_repo_dir: str) -> dict[str, Union[str, dict]]:
    repo_metadata_file_path = os.path.join(
        task_repo_dir, "metadata/metadata.json")
    if not os.path.exists(repo_metadata_file_path):
        logger.error("Repository metadata file not found")
        sys.exit(1)

    with open(repo_metadata_file_path, "r") as metadata_file:
        repo_metadata = json.load(metadata_file)

    return repo_metadata


def read_bounty_metadata(
    task_repo_dir: str, bounty_number: str
) -> dict[str, Union[str, dict]]:
    bounty_metadata_file_path = os.path.join(
        task_repo_dir + "/metadata/bounty_" + bounty_number, "bounty_metadata.json"
    )
    if not os.path.exists(bounty_metadata_file_path):
        logger.error("Bounty metadata file not found")
        sys.exit(1)

    with open(bounty_metadata_file_path, "r") as metadata_file:
        bounty_metadata = json.load(metadata_file)

    return bounty_metadata
