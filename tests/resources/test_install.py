#!/usr/bin/env python3
# To run this test, enter the following command in the root directory: 
# PYTHONPATH=. python tests/resources/test_install.py .

import os
import sys
import subprocess
import json
import re
import shutil
from pathlib import Path

from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.resource_manager import ResourceManager


# Define color codes
GREEN = "\033[1;32m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[1;36m"
RESET = "\033[0m"

# Define message prefixes
INFO = f"{CYAN}[INFO]{RESET}"
SUCCESS = f"{GREEN}[SUCCESS]{RESET}"
ERROR = f"{RED}[ERROR]{RESET}"
WARNING = f"{YELLOW}[WARNING]{RESET}"

def print_header(color, message):
    print(f"{color}========== {message} =========={RESET}")



def get_install_command(repo_dir):
    repo_metadata_file = os.path.join(repo_dir, "metadata.json")
    if not os.path.isfile(repo_metadata_file):
        print_header(RED, "ERROR")
        print(f"{ERROR} metadata.json not found at {repo_metadata_file}")
        sys.exit(1)
    
    with open(repo_metadata_file, 'r') as f:
        repo_metadata = json.load(f)
    
    install_command = repo_metadata.get('install_command')
    if not install_command:
        print("No specific install command, will use pip install -e .")
        install_command = "pip install -e ."
    return install_command



def get_vuln_commit(bounty_dir):    
    bounty_metadata_file = os.path.join(bounty_dir, "bounty_metadata.json")
    if not os.path.isfile(bounty_metadata_file):
        print_header(RED, "ERROR")
        print(f"{ERROR} bounty_metadata.json not found at {bounty_metadata_file}")
        sys.exit(1)
    
    with open(bounty_metadata_file, 'r') as f:
        bounty_metadata = json.load(f)
    
    vulnerable_commit = bounty_metadata.get('vulnerable_commit')
    if not vulnerable_commit:
        print_header(RED, "ERROR")
        print(f"{ERROR} Could not find vulnerable_commit in bounty metadata")
        sys.exit(1)

    return vulnerable_commit



def find_all_bounties(base_dir):
    bounty_dirs = []
    for root, dirs, files in os.walk(base_dir):
        path = Path(root)
        if path.match("*/bounties/bounty_*") and not path.match("*/bounties/bounty_*/*/bounty_*"):
            if re.search(r"/bounties/bounty_[0-9]+$", str(path)):
                bounty_dirs.append(str(path))
    
    bounty_dirs.sort()
    
    if not bounty_dirs:
        print_header(RED, "ERROR")
        print(f"{ERROR} No bounty directories found in {base_dir}")
        sys.exit(1)
    
    print(f"{INFO} Found {len(bounty_dirs)} bounty directories")
    for dir_path in bounty_dirs:
        print(f"{INFO} - {dir_path}")
    print()

    return bounty_dirs



def setup_kali_container(task_dir, workflow_id, bounty_num, install_command):    
    manager = ResourceManager(workflow_id=workflow_id)

    config = KaliEnvResourceConfig(
        task_dir=Path(task_dir),
        bounty_number=bounty_num,
        volumes={
            str(task_dir): {"bind": "/app", "mode": "rw"},
        },
        install_command=install_command,
        disable_cleanup=True,
    )
    
    resource_id = "kali_env"
    manager.register_resource(resource_id, KaliEnvResource, config)    
    manager._initialize_single_resource(resource_id, phase_index=0)
    kali_resource = manager.get_resource(resource_id)
    return manager, kali_resource



def is_editable_from_pip_list(pip_stdout: str, package_name: str) -> bool:
    for line in pip_stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0] != "UNKNOWN":
            print(f"{package_name} is installed in editable mode at {parts[2]}")
            return True
        elif len(parts) >= 2:
            print(f"{package_name} is installed but NOT in editable mode.")
            return False
    print(f"{package_name} is NOT installed.")
    return False



def main():
    if len(sys.argv) < 2:
        print(f"{ERROR} Please provide base directory as first argument")
        sys.exit(1)
        
    base_dir = sys.argv[1]
    
    # Create summary arrays
    successful_bounties = []
    failed_bounties = []
    skipped_bounties = []
    
    # Find all bounty directories - only match the direct bounty_X directories, not subdirectories
    print_header(CYAN, "FINDING ALL BOUNTY DIRECTORIES")
    bounty_dirs = find_all_bounties(base_dir)
    
    # Run each bounty
    total = len(bounty_dirs)
    current = 1
    
    for bounty_dir in bounty_dirs:
        print(bounty_dir)
        repo_dir = os.path.dirname(os.path.dirname(bounty_dir))
        repo_name = Path(bounty_dir).parent.parent.name
        install_command = get_install_command(repo_dir)
        vulnerable_commit = get_vuln_commit(bounty_dir)
        codebase_dir = os.path.join(repo_dir, "codebase")

        # Get bounty number
        match = re.search(r"bounty_(\d+)$", bounty_dir)
        if match:
            bounty_num = match.group(1)
            print(bounty_num) 
        else:
            print("No bounty number found")

        # Spin up Kali Container
        print_header(CYAN, "SPINNING UP KALI CONTAINER")
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        resource_id = f"kali_env_{unique_id}"
        manager, kali_env = setup_kali_container(os.path.abspath(base_dir), resource_id, bounty_num, install_command)

        is_python = kali_env._is_python_repo(codebase_dir)
        if is_python:
            print(f"{INFO} Is python project")
        else:
            print(f"{INFO} Is not a python project")

        # Checkout the vulnerable commit
        print_header(CYAN, "CHECKOUT VULNERABLE COMMIT")
        print(f"{INFO} Checking out the vulnerable commit: {vulnerable_commit}")
        
        # Check if the codebase is initialized
        check_command = f"cd {codebase_dir} && if [ ! -d .git ]; then git submodule update --init; fi"
        kali_env.run_command(check_command)

        # Checkout the vulnerable commit
        checkout_command = f"cd {codebase_dir} && git checkout {vulnerable_commit}"
        kali_env.run_command(checkout_command)        
        
        # Install the codebase
        print_header(CYAN, f"RUNNING INSTALL REPO {current}/{total}: {bounty_dir}")
        print(f"{INFO} Command: {install_command}")
        if is_python:
            stdout, stderr = kali_env.run_command(f"cd {codebase_dir} && {install_command}", timeout=600)
            pip_stdout1, pip_stderr1 = kali_env.run_command(f"cd {codebase_dir} && pip list")
            pip_stdout2, pip_stderr2 = kali_env.run_command(f"cd {codebase_dir} && python3.11 -m pip list")
            
            if is_editable_from_pip_list(pip_stdout1, repo_name) or is_editable_from_pip_list(pip_stdout2, repo_name):
                print(f"{SUCCESS} Successfully installed: {repo_name}")
                successful_bounties.append(bounty_dir)
            else:
                print(f"{ERROR} Failed to install: {repo_name}")
                failed_bounties.append(bounty_dir)
        else:
            print(f"{INFO} Skipped installing: {repo_name}")
            skipped_bounties.append(bounty_dir)
        
        current += 1
        print()

    # Print summary
    print_header(CYAN, "SUMMARY")
    print(f"{INFO} Total bounties: {total}")
    print(f"{SUCCESS} Successful bounties: {len(successful_bounties)}")
    print(f"{ERROR} Failed bounties: {len(failed_bounties)}")
    print(f"{WARNING} Skipped bounties (not python project): {len(skipped_bounties)}")
    print()
    
    if successful_bounties:
        print_header(GREEN, "SUCCESSFUL BOUNTIES")
        for bounty in successful_bounties:
            print(f"{SUCCESS} - {bounty}")
        print()
    
    if failed_bounties:
        print_header(RED, "FAILED BOUNTIES")
        for bounty in failed_bounties:
            print(f"{ERROR} - {bounty}")
        print()

    if skipped_bounties:
        print_header(YELLOW, "SKIPPED BOUNTIES")
        for bounty in skipped_bounties:
            print(f"{INFO} - {bounty}")
        print()

if __name__ == "__main__":
    main()