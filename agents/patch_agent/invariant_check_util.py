import json
import shutil
from pathlib import Path
from utils.logger import get_main_logger

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

        src_path = Path(src_file_path)
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


def check_invariant_scores_against_thresholds(
    repo_metadata_file: Path,
    bounty_metadata_file: Path,
    repo_invariant_scores: Path,
    bounty_invariant_scores: Path,
) -> bool:
    """
    Check invariant scores against thresholds defined in metadata files.

    Args:
        repo_metadata_file: Repo metadata file
        bounty_metadata_file: Bounty metadata file - potentially has empty scores
        repo_invariant_scores: Repo scores file
        bounty_invariant_scores: Bounty scores file - this file may not exist
    """
    try:
        # Load scores and metadata JSON files
        repo_scores = {}
        bounty_scores = {}
        repo_metadata = {}
        bounty_metadata = {}

        if repo_invariant_scores.exists():
            repo_scores = json.loads(repo_invariant_scores.read_text())
            logger.info(f"Repo invariant scores: {repo_scores}")

        if bounty_invariant_scores.exists():
            bounty_scores = json.loads(bounty_invariant_scores.read_text())
            logger.info(f"Bounty invariant scores: {bounty_scores}")

        if repo_metadata_file.exists():
            repo_metadata = json.loads(repo_metadata_file.read_text())

        if bounty_metadata_file.exists():
            bounty_metadata = json.loads(bounty_metadata_file.read_text())

        if "invariant_thresholds" not in repo_metadata:
            logger.error("Missing invariant thresholds - failing invariant check")
            return False

        bounty_thresholds = {}
        if bounty_metadata and "invariant_thresholds" in bounty_metadata:
            bounty_thresholds = bounty_metadata["invariant_thresholds"]

        thresholds = repo_metadata.get("invariant_thresholds", {}).copy()
        thresholds.update(bounty_thresholds)

        if "invariant_scores" not in repo_scores:
            logger.error("Missing repo invariant scores - failing invariant check")
            return False

        scores = repo_scores.get("invariant_scores", {}).copy()
        if bounty_scores and "invariant_scores" in bounty_scores:
            scores.update(bounty_scores.get("invariant_scores", {}))

        errors = []
        for invariant_name, threshold in thresholds.items():
            if invariant_name not in scores:
                errors.append(f"Missing score for {invariant_name}")
                continue

            score = scores.get(invariant_name)
            if not isinstance(score, (int, float)):
                errors.append(f"Score for {invariant_name} is not a number")
                continue

            if score < threshold:
                errors.append(
                    f"{invariant_name} score ({score}) is below threshold ({threshold})"
                )

        logger.info(
            f"Found {len(errors)} errors while checking invariants: {errors}"
        )
        return len(errors) == 0

    except Exception as e:
        error_msg = f"Error checking invariants: {str(e)}"
        logger.error(error_msg)
        return False
