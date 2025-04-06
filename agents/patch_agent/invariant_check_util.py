from pathlib import Path
from utils.logger import get_main_logger
import json
import shutil
from typing import List, Optional

logger = get_main_logger(__name__)


def apply_patched_unit_tests(bounty_dir: Path, task_dir: Path) -> bool:
    """
    Apply unit test patches from bounty metadata.

    Returns:
        bool: True if all patches were applied successfully, False otherwise
    """
    logger.info("Checking for unit test patches to apply...")

    bounty_metadata_file = bounty_dir / "bounty_metadata.json"
    bounty_metadata = {}
    bounty_unit_tests = {}

    # Load bounty metadata
    if not bounty_metadata_file.exists():
        logger.info("No bounty metadata file found.")
        return False

    try:
        bounty_metadata = json.loads(bounty_metadata_file.read_text())
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing bounty metadata JSON: {e}")
        return False

    # Check for unit test patches
    if "unit_test_patch" not in bounty_metadata:
        logger.info("No unit test patches defined in metadata. Skipping.")
        return False

    bounty_unit_tests = bounty_metadata["unit_test_patch"]
    if not bounty_unit_tests:
        logger.info("Unit test patches dictionary is empty. Skipping.")
        return False

    successful_patches = 0
    failed_patches = 0

    for src_file_path, dest_file_path in bounty_unit_tests.items():
        logger.info(
            f"Applying unit test patch from {src_file_path} to {dest_file_path}"
        )

        src_path = bounty_dir / src_file_path

        dest_path = task_dir / dest_file_path

        if not src_path.exists():
            logger.error(f"Unit test source file not found: {src_path}")
            failed_patches += 1
            continue

        try:
            # Copy the file
            shutil.copy2(src_path, dest_path)
            logger.info(f"Successfully copied unit test file to: {dest_path}")
            successful_patches += 1

        except Exception as e:
            logger.error(f"Failed to copy unit test file {src_file_path}: {str(e)}")
            failed_patches += 1

    total_patches = successful_patches + failed_patches
    if total_patches > 0:
        logger.info(
            f"Applied {successful_patches}/{total_patches} unit test patches"
        )

    return failed_patches == 0

def cleanup_files(file_paths: List[Path]) -> None:
    """Delete files if they exist."""
    for path in file_paths:
        if path.exists():
            path.unlink()
            logger.info(f"Removed {path.name}")

def load_json_file(file_path: Path) -> dict:
    """Load a JSON file or return an empty dict if it doesn't exist."""
    if file_path.exists():
        try:
            with open(file_path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error parsing JSON from {file_path}")
    return {}
