import json
import shutil
from utils.logger import get_main_logger
from pathlib import Path

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