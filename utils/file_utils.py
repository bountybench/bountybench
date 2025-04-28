import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from utils.logger import get_main_logger

FILE_ENCODING = "utf-8"
READ_ERROR_MESSAGE = "*** Error reading file: {error} ***"

logger = get_main_logger(__name__)


def apply_patch_to_bounty(bounty_dir: Path, task_dir: Path) -> bool:
    """
    Copy patches from bounty metadata.

    Returns:
        True if all patches were copied over successfully, False otherwise
    """
    bounty_metadata_file = bounty_dir / "bounty_metadata.json"

    # Check if metadata file exists
    if not bounty_metadata_file.exists():
        raise RuntimeError("No bounty metadata file found.")

    # Load bounty metadata
    try:
        bounty_metadata = json.loads(bounty_metadata_file.read_text())
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing bounty metadata JSON: {e}")
        return False

    # Check for patches
    if "patch" not in bounty_metadata or not bounty_metadata["patch"]:
        raise RuntimeError("Patch required for bounty. No patch found.")

    bounty_patches = bounty_metadata["patch"]
    successful_patches = 0
    failed_patches = 0

    # Copy each patch file
    for src_file_path, dest_file_path in bounty_patches.items():
        logger.info(f"Copying patch from {src_file_path} to {dest_file_path}")

        src_path = bounty_dir / src_file_path
        dest_path = task_dir / dest_file_path

        if not src_path.exists():
            logger.error(f"Patch source file not found: {src_path}")
            failed_patches += 1
            continue

        try:
            # Copy the file
            shutil.copy2(src_path, dest_path)
            logger.info(f"Successfully copied patch file to: {dest_path}")
            successful_patches += 1
        except Exception as e:
            logger.error(f"Failed to copy patch file {src_file_path}: {str(e)}")
            failed_patches += 1

    total_patches = successful_patches + failed_patches
    if total_patches > 0:
        logger.info(f"Copied {successful_patches}/{total_patches} patches")

    return failed_patches == 0


def extract_bounty_number(path: str) -> Optional[str]:
    match = re.search(r"bounty_([0-9]+)", path)
    if match:
        return match.group(1)
    return None


def print_tree(directory_path: Path):
    """
    Runs the 'tree -L 2' command on the specified directory and prints its output.

    Args:
        directory_path: The Path object representing the directory to scan.
    """
    logger.debug(f"--- Running 'tree -L 2' on {directory_path} ---")
    try:
        # Execute the tree command, limiting depth to 2 levels
        result = subprocess.run(
            ["tree", "-L", "2", str(directory_path)],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        logger.debug(result.stdout)
    except Exception as e:
        logger.error(f"An unexpected error occurred while running 'tree': {e}")


def print_file_content(file_path: Path):
    """
    Prints the content of a single file.

    Args:
        file_path: The Path object representing the file to print.
    """
    logger.debug(f"printing file: {file_path}")
    try:
        # Read and print the file content using the specified encoding
        with file_path.open("r", encoding=FILE_ENCODING) as f:
            logger.debug(f.read())
    except Exception as e:
        logger.info(f"Error printing {file_path}, Skipping. Exception: {e}")


def print_files_recursive(path_to_print: Path, ignore_path: Path | None):
    """
    Prints all files relative to path_to_print with depth 2
    """
    if ignore_path:
        logger.debug(f"--- Ignoring files within {ignore_path} ---")
    ignore_path_abs = ignore_path.resolve()

    try:
        for item in path_to_print.iterdir():
            item_abs = item.resolve()

            if ignore_path_abs and item_abs.is_relative_to(ignore_path_abs):
                continue

            if item.is_file():
                print_file_content(item)
            if item.is_dir():
                for sub_item in item.iterdir():
                    sub_item_abs = sub_item.resolve()

                    if ignore_path_abs and sub_item_abs.is_relative_to(ignore_path_abs):
                        continue

                    if sub_item.is_file():
                        print_file_content(sub_item)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
