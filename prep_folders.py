#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path


def create_folders_and_sort_files(base_dir):
    """
    Create the specified list of folders within the given directory
    and sort existing files into those folders based on exact folder name matching.

    Args:
        base_dir (str): Path to the directory where folders will be created
    """
    folders = [
        "agentscope_0",
        "astropy_0",
        "bentoml_0",
        "bentoml_1",
        "composio_0",
        "curl_0",
        "django_0",
        "fastapi_0",
        "gluon-cv_0",
        "gpt_academic_0",
        "gradio_0",
        "gradio_1",
        "gradio_2",
        "gunicorn_0",
        "InvokeAI_0",
        "InvokeAI_1",
        "kedro_0",
        "langchain_0",
        "langchain_1",
        "LibreChat_0",
        "LibreChat_1",
        "LibreChat_2",
        "LibreChat_3",
        "LibreChat_4",
        "lunary_0",
        "lunary_1",
        "lunary_2",
        "mlflow_0",
        "mlflow_1",
        "mlflow_2",
        "mlflow_3",
        "parse-url_0",
        "pytorch-lightning_0",
        "pytorch-lightning_1",
        "scikit-learn_0",
        "setuptools_0",
        "undici_0",
        "vllm_0",
        "yaml_0",
        "zipp_0",
    ]

    base_path = Path(base_dir).resolve()

    if not base_path.exists():
        print(f"Creating base directory: {base_path}")
        base_path.mkdir(parents=True)
    elif not base_path.is_dir():
        print(f"Error: {base_path} exists but is not a directory")
        sys.exit(1)

    # Step 1: Create folders
    created_count = 0
    for folder in folders:
        folder_path = base_path / folder

        if folder_path.exists():
            print(f"Folder already exists: {folder_path}")
            continue

        try:
            folder_path.mkdir()
            print(f"Created folder: {folder_path}")
            created_count += 1
        except Exception as e:
            print(f"Error creating folder {folder_path}: {e}")

    print(f"\nCompleted: {created_count} folders created in {base_path}")

    # Step 2: Sort existing files into folders
    moved_count = 0
    skipped_count = 0

    # Get all files in the base directory (not recursive)
    file_paths = [f for f in base_path.iterdir() if f.is_file()]
    total_files = len(file_paths)

    print(f"\nSorting {total_files} files into folders...")

    for file_path in file_paths:
        # Skip the script itself
        if file_path.name == os.path.basename(__file__):
            print(f"Skipping script file: {file_path.name}")
            continue

        # Match file to folder based on exact folder name
        matched = False
        for folder in folders:
            # Check if exact folder name is in the filename
            if folder.lower() in file_path.name.lower():
                dest_path = base_path / folder / file_path.name
                try:
                    shutil.move(file_path, dest_path)
                    print(f"Moved: {file_path.name} -> {folder}")
                    moved_count += 1
                    matched = True
                    break
                except Exception as e:
                    print(f"Error moving {file_path.name} to {folder}: {e}")

        if not matched:
            print(f"No matching folder for: {file_path.name}")
            skipped_count += 1

    print(f"\nFile sorting completed:")
    print(f"- {moved_count} files moved to folders")
    print(f"- {skipped_count} files had no matching folder")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python prep_folders.py <directory>")
        sys.exit(1)

    base_dir = sys.argv[1]
    create_folders_and_sort_files(base_dir)
