#!/usr/bin/env python3
"""
collect_job_files.py: Copy files from multiple job output PVCs via temporary pods.
"""

import argparse
import subprocess
import time
import sys
import random
import string
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from kubernetes import client, config
from kubernetes.client.rest import ApiException

# --- Configuration ---
COLLECTOR_POD_IMAGE = "ubuntu:22.04" # A simple image with shell access
COLLECTOR_CONTAINER_NAME = "collector-container"
DEFAULT_NAMESPACE = "test"
DEFAULT_LABEL_SELECTOR = "app=bounty-task" # Default label to find relevant PVCs
DEFAULT_OUTPUT_DIR = "../collected_logs" # Default base dir for collected files
DEFAULT_MAX_WORKERS = 5 # Default concurrency
POD_DATA_MOUNT_PATH = "/mnt/data" # Where the PVC is mounted inside the collector pod


def generate_pod_name(base="collector-pod-"):
    """Generates a unique pod name."""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{base}{suffix}"

def create_collector_pod(core_api, namespace, pod_name, pvc_name):
    """Creates the temporary collector pod mounting the specified PVC."""
    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": pod_name, "labels": {"app": "log-collector"}},
        "spec": {
            "volumes": [
                {
                    "name": "target-pvc-volume",
                    "persistentVolumeClaim": {"claimName": pvc_name},
                }
            ],
            "containers": [
                {
                    "name": COLLECTOR_CONTAINER_NAME,
                    "image": COLLECTOR_POD_IMAGE,
                    "command": ["sleep", "infinity"], # Keep container running
                    "volumeMounts": [
                        {
                            "mountPath": POD_DATA_MOUNT_PATH,
                            "name": "target-pvc-volume",
                        }
                    ],
                }
            ],
            "restartPolicy": "Never",
            # Ensure it runs on a node that can access the PVC (usually automatic for RWO)
            # If using specific node pools/selectors, might need adjustment here.
            # Add toleration for arm64 nodes
            'tolerations': [
                {
                    'key': 'kubernetes.io/arch',
                    'operator': 'Equal',
                    'value': 'arm64',
                    'effect': 'NoSchedule'
                }
            ]
        },
    }
    try:
        print(f"  Creating collector pod '{pod_name}' for PVC '{pvc_name}'...")
        core_api.create_namespaced_pod(body=pod_manifest, namespace=namespace)
        return True
    except ApiException as e:
        print(f"  ERROR creating collector pod {pod_name}: {e.reason}", file=sys.stderr)
        return False

def wait_for_pod_ready(core_api, namespace, pod_name, timeout_seconds=300):
    """Waits for the pod to reach the 'Running' state."""
    start_time = time.time()
    print(f"  Waiting for pod '{pod_name}' to be Running...")
    while time.time() - start_time < timeout_seconds:
        try:
            pod_status = core_api.read_namespaced_pod_status(pod_name, namespace)
            if pod_status.status.phase == "Running":
                # Check if container is ready (optional but good practice)
                if pod_status.status.container_statuses:
                    for cs in pod_status.status.container_statuses:
                        if cs.ready:
                            print(f"  Pod '{pod_name}' is Running and container is Ready.")
                            return True
            elif pod_status.status.phase in ["Failed", "Succeeded", "Unknown"]:
                print(f"  Pod '{pod_name}' entered unexpected phase: {pod_status.status.phase}. Aborting wait.", file=sys.stderr)
                return False
        except ApiException as e:
            if e.status == 404:
                print(f"  Pod '{pod_name}' not found (maybe deleted?). Aborting wait.", file=sys.stderr)
                return False
            else:
                 print(f"  Error checking pod status for '{pod_name}': {e.reason}. Retrying...", file=sys.stderr)
        time.sleep(5)
    print(f"  Timeout waiting for pod '{pod_name}' to become Running.", file=sys.stderr)
    return False

def run_kubectl_cp(source_path, dest_path, retries=2, delay=5):
    """Runs kubectl cp command with retries."""
    cmd = ["kubectl", "cp", source_path, str(dest_path)]
    print(f"    Executing: {' '.join(cmd)}")
    for attempt in range(retries + 1):
        try:
            # Use check=True to raise CalledProcessError on non-zero exit code
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"    Copy successful for '{source_path}'.")
            return True, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            print(f"    Attempt {attempt + 1}/{retries + 1} failed for 'kubectl cp {source_path}'. Error: {e.stderr.strip()}", file=sys.stderr)
            if attempt < retries:
                print(f"    Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"    ERROR copying '{source_path}' after {retries + 1} attempts.", file=sys.stderr)
                return False, e.stdout, e.stderr # Return last attempt's output
        except Exception as e:
            # Catch other potential errors (e.g., command not found)
            print(f"    An unexpected error occurred during kubectl cp: {e}", file=sys.stderr)
            return False, "", str(e)

def delete_pod(core_api, namespace, pod_name):
    """Deletes the specified pod."""
    try:
        print(f"  Deleting pod '{pod_name}'...")
        core_api.delete_namespaced_pod(pod_name, namespace)
        # Wait briefly for deletion to initiate?
        # time.sleep(2)
        print(f"  Pod '{pod_name}' deletion initiated.")
        return True
    except ApiException as e:
        if e.status == 404:
             print(f"  Pod '{pod_name}' already deleted.")
             return True # Already gone, counts as success
        print(f"  ERROR deleting pod '{pod_name}': {e.reason}", file=sys.stderr)
        return False

def list_pvcs(core_api, namespace, label_selector):
    """Lists PVCs in the namespace matching the label selector."""
    print(f"Listing PVCs in namespace '{namespace}' with label selector '{label_selector}'...")
    try:
        pvcs = core_api.list_namespaced_persistent_volume_claim(
            namespace=namespace,
            label_selector=label_selector
        )
        pvc_names = [pvc.metadata.name for pvc in pvcs.items]
        print(f"  Found {len(pvc_names)} PVCs matching selector.")
        return pvc_names
    except ApiException as e:
        print(f"ERROR listing PVCs: {e.reason}", file=sys.stderr)
        return []

def collect_from_single_pvc(pvc_name, namespace, core_api, output_dir):
    """Handles the full collection process for a single PVC, copying contents flat."""
    print(f"Processing PVC: {pvc_name}")
    collector_pod_name = generate_pod_name(f"collector-{pvc_name[:20]}-") # Keep name reasonable
    
    success = False
    pod_created = False
    try:
        if not create_collector_pod(core_api, namespace, collector_pod_name, pvc_name):
            raise RuntimeError("Failed to create collector pod")
        pod_created = True
        
        if not wait_for_pod_ready(core_api, namespace, collector_pod_name):
            raise RuntimeError("Collector pod did not become ready")

        print(f"  Attempting to copy files from collector pod '{collector_pod_name}' into '{output_dir}'...")
        # Define source paths inside the collector pod - use trailing /. to copy CONTENTS
        pod_logs_src = f"{namespace}/{collector_pod_name}:{POD_DATA_MOUNT_PATH}/logs/."
        pod_full_logs_src = f"{namespace}/{collector_pod_name}:{POD_DATA_MOUNT_PATH}/full_logs/."
        
        # Copy contents of 'logs' into the flat output_dir
        # Note: Using output_dir directly. Collisions WILL overwrite files.
        logs_copied, _, logs_err = run_kubectl_cp(pod_logs_src, output_dir)
        # Copy contents of 'full_logs' into the flat output_dir
        full_logs_copied, _, full_logs_err = run_kubectl_cp(pod_full_logs_src, output_dir)

        # Consider success if at least one copy worked without critical errors.
        # kubectl cp returns error if source dir doesn't exist, which might be okay.
        # A more robust check might inspect the stderr for specific non-fatal errors.
        # For now, let's require both to succeed unless the error indicates missing source.
        
        logs_success = logs_copied or ("no such file or directory" in logs_err.lower())
        full_logs_success = full_logs_copied or ("no such file or directory" in full_logs_err.lower())

        if logs_copied:
            print(f"    Successfully copied contents from 'logs' for PVC {pvc_name}.")
        elif not logs_success:
             print(f"    ERROR copying 'logs' contents for PVC {pvc_name}: {logs_err.strip()}", file=sys.stderr)

        if full_logs_copied:
            print(f"    Successfully copied contents from 'full_logs' for PVC {pvc_name}.")
        elif not full_logs_success:
             print(f"    ERROR copying 'full_logs' contents for PVC {pvc_name}: {full_logs_err.strip()}", file=sys.stderr)
        
        # Define overall success - perhaps if at least one dir existed and copied?
        # Or require strict success if dirs are expected?
        # Current logic: succeeds if both copy operations either worked OR failed because the source didn't exist.
        if logs_success and full_logs_success:
            if logs_copied or full_logs_copied:
                 print(f"  Successfully copied available log contents for PVC {pvc_name} into flat directory.")
                 success = True
            else:
                 print(f"  Neither 'logs' nor 'full_logs' directory found or copied for PVC {pvc_name}. Treating as success (no data).")
                 success = True # No data isn't necessarily a failure of the process
        else:
            print(f"  ERROR copying files for PVC {pvc_name}. Check errors above.", file=sys.stderr)
            success = False
            
    except Exception as e:
        print(f"An unexpected error occurred during collection for PVC {pvc_name}: {e}", file=sys.stderr)
        success = False
    finally:
        # --- Cleanup --- 
        if pod_created:
             delete_pod(core_api, namespace, collector_pod_name)
        else:
            print(f"Skipping cleanup for {pvc_name} as pod creation failed.")
            
    print(f"Finished processing PVC: {pvc_name} - {'SUCCESS' if success else 'FAILED'}")
    return pvc_name, success

def main():
    parser = argparse.ArgumentParser(
        description="Copies 'logs' and 'full_logs' directory contents from multiple Kubernetes PVCs "
                    "matching a label selector into a single flat local directory, using temporary collector pods."
                    " WARNING: Files with the same name from different sources will overwrite each other."
    )
    parser.add_argument(
        "--namespace", "-n",
        default=DEFAULT_NAMESPACE,
        help=f"Kubernetes namespace (default: {DEFAULT_NAMESPACE})"
    )
    parser.add_argument(
        "--label-selector", "-l",
        default=DEFAULT_LABEL_SELECTOR,
        help=f"Label selector to find target PVCs (default: '{DEFAULT_LABEL_SELECTOR}')"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Local flat directory to save all collected files (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--max-workers", "-w",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Maximum number of concurrent PVC processing workers (default: {DEFAULT_MAX_WORKERS})"
    )
    args = parser.parse_args()

    # Resolve and create base output directory
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Namespace: {args.namespace}")
    print(f"PVC Label Selector: '{args.label_selector}'")
    print(f"Output Dir: {output_dir}")
    print(f"Max Workers: {args.max_workers}")
    print("\nWARNING: Files with the same name from different sources will overwrite each other in the flat output directory!\n")

    print("Loading Kubernetes configuration...")
    try:
        config.load_kube_config()
        core_v1_api = client.CoreV1Api()
        print("Kubernetes configuration loaded successfully.")
    except Exception as e:
        print(f"Error loading Kubernetes configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # List target PVCs
    target_pvc_names = list_pvcs(core_v1_api, args.namespace, args.label_selector)
    if not target_pvc_names:
        print("No PVCs found matching the selector. Exiting.")
        sys.exit(0)

    print(f"\nStarting collection from {len(target_pvc_names)} PVCs using up to {args.max_workers} workers...")
    
    results = {}
    failed_pvcs = []
    successful_pvcs = []

    # Use ThreadPoolExecutor for concurrency
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        # Submit tasks for each PVC
        future_to_pvc = {
            executor.submit(
                collect_from_single_pvc, 
                pvc_name, 
                args.namespace, 
                core_v1_api, 
                output_dir, # Pass the single output dir
            ): pvc_name 
            for pvc_name in target_pvc_names
        }
        
        # Process completed tasks
        for future in as_completed(future_to_pvc):
            pvc_name = future_to_pvc[future]
            try:
                _pvc_name_result, success = future.result() # Get result from the worker function
                results[pvc_name] = success
                if success:
                    successful_pvcs.append(pvc_name)
                else:
                    failed_pvcs.append(pvc_name)
            except Exception as exc:
                print(f'PVC {pvc_name} generated an exception during processing: {exc}', file=sys.stderr)
                results[pvc_name] = False
                failed_pvcs.append(pvc_name)

    # --- Summary --- 
    print("\n--- Collection Summary ---")
    print(f"Processed {len(target_pvc_names)} PVCs.")
    print(f"Successfully collected from: {len(successful_pvcs)} PVCs")
    print(f"Failed to collect from:    {len(failed_pvcs)} PVCs")
    if failed_pvcs:
        print("\nFailed PVCs:")
        for pvc in failed_pvcs:
            print(f"  - {pvc}")
        print("\nCheck logs above for error details for failed PVCs.")
        sys.exit(1) # Exit with error if any failed
    else:
        print("\nCollection completed successfully for all PVCs.")
        sys.exit(0)

if __name__ == "__main__":
    main()
