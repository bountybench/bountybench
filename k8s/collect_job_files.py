#!/usr/bin/env python3
"""
collect_job_files.py: Copy generated files from completed Kubernetes Job Pods.
"""

import argparse
import subprocess
import time
from pathlib import Path
import os
import shutil
import json # Added for parsing error details
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from concurrent.futures import ThreadPoolExecutor, as_completed

def list_pods(api: client.CoreV1Api, namespace: str, label_selector: str):
    """Lists pods matching the label selector in the given namespace."""
    try:
        print(f"Listing pods in namespace '{namespace}' with selector '{label_selector}'...")
        resp = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        print(f"Found {len(resp.items)} pods.")
        return resp.items
    except ApiException as e:
        print(f"Error listing pods: {e.status} - {e.reason}", file=sys.stderr)
        try:
            # Attempt to parse and print the error body for more details
            error_body = json.loads(e.body)
            print(f"Error details: {json.dumps(error_body, indent=2)}", file=sys.stderr)
        except: # noqa (fallback for non-JSON bodies)
            print(f"Raw error body: {e.body}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred while listing pods: {e}", file=sys.stderr)
        return []

def copy_files_from_pod(namespace: str, pod_name: str, container_name: str,
                        source_paths: list[str], local_dest_base_dir: Path, pod_labels: dict):
    """
    Uses 'kubectl cp' to copy files/directories from a pod.
    Structures the output based on pod labels (group, task).
    Returns True on success, False on failure for any source path.
    """
    all_success = True

    # Determine local directory structure based on labels
    group_name = pod_labels.get('experiment-group', 'unknown-group')
    task_id = pod_labels.get('task-id', 'unknown-task')
    # Sanitize labels just in case they have problematic characters for filenames
    safe_group_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in group_name)
    safe_task_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in task_id)

    # Create a specific directory for this pod's files
    # e.g., <output_dir>/<group_name>/<task_id>/ 
    pod_local_dest = local_dest_base_dir / safe_group_name / safe_task_id
    pod_local_dest.mkdir(parents=True, exist_ok=True)

    print(f"Attempting copy from pod '{pod_name}' (Group: {group_name}, Task: {task_id}) to '{pod_local_dest}'...")

    for source_path in source_paths:
        # Construct the source specification for kubectl cp
        kube_source = f"{namespace}/{pod_name}:{source_path}"
        # Destination is the specific directory for this pod
        local_dest = pod_local_dest

        # Prepare kubectl command
        # Use -c if a specific container name is known and necessary
        cmd = [
            'kubectl', 'cp',
            # If container name is known/needed, add: '-c', container_name,
            kube_source,
            str(local_dest) # Copy *into* the pod-specific directory
        ]
        print(f"  Executing: {' '.join(cmd)}")

        try:
            # Run kubectl cp
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300, encoding='utf-8')
            print(f"    Success copying '{source_path}'.")
        except subprocess.CalledProcessError as e:
            all_success = False
            print(f"    ERROR copying '{source_path}' from pod '{pod_name}'.", file=sys.stderr)
            print(f"    Return Code: {e.returncode}", file=sys.stderr)
            stderr_lines = e.stderr.strip().splitlines() if e.stderr else []
            if stderr_lines:
                 print(f"    Stderr: {stderr_lines[0]}{'...' if len(stderr_lines) > 1 else ''}", file=sys.stderr)
                 # Check for common "No such file or directory" error
                 if "No such file or directory" in e.stderr:
                      print(f"    Hint: The path '{source_path}' might not exist in pod '{pod_name}'.", file=sys.stderr)
            else:
                 print(f"    Stderr: (empty)", file=sys.stderr)
        except subprocess.TimeoutExpired:
             all_success = False
             print(f"    ERROR: Timeout expired copying '{source_path}' from pod '{pod_name}'.", file=sys.stderr)
        except Exception as e:
            all_success = False
            print(f"    ERROR: Unexpected exception during copy from pod '{pod_name}': {e}", file=sys.stderr)

    return all_success

def main():
    parser = argparse.ArgumentParser(
        description="Copy files from completed Kubernetes Job Pods."
    )
    parser.add_argument(
        '--namespace', '-n', default='bounty-experiments',
        help='Kubernetes namespace where jobs ran (default: bounty-experiments)'
    )
    parser.add_argument(
        '--label-selector', '-l', default='app=bounty-task',
        help='Label selector to identify job pods (default: app=bounty-task)'
    )
    parser.add_argument(
        '--pod-status', default='Succeeded', choices=['Succeeded', 'Failed', 'All'],
        help='Copy files only from pods with this status (default: Succeeded)'
    )
    parser.add_argument(
        '--source-paths', nargs='+', default=['/app/logs', '/app/full_logs'],
        help='List of container paths to copy (default: /app/logs /app/full_logs)'
    )
    parser.add_argument(
        '--output-dir', '-o', default='./collected_job_files',
        help='Local directory to save the copied files (default: ./collected_job_files)'
    )
    parser.add_argument(
        '--max-workers', type=int, default=5,
        help='Max concurrent kubectl cp operations (default: 5)'
    )
    parser.add_argument(
        '--cleanup', action='store_true',
        help='Attempt to delete pods after successfully copying files.'
    )

    args = parser.parse_args()

    output_base_dir = Path(args.output_dir)
    output_base_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_base_dir.resolve()}")

    # --- Load Kubeconfig ---
    try:
        print("Loading Kubernetes configuration...")
        config.load_kube_config()
        core_api = client.CoreV1Api()
        print("Kubernetes configuration loaded successfully.")
    except Exception as e:
        print(f"Error: Could not load Kubernetes config: {e}", file=sys.stderr)
        sys.exit(1)

    # --- List Pods ---
    pods_to_process = []
    all_pods = list_pods(core_api, args.namespace, args.label_selector)

    if not all_pods:
        print("No pods found matching the selector. Exiting.")
        sys.exit(0)

    print(f"Filtering pods by status: '{args.pod_status}'...")
    for pod in all_pods:
        status = pod.status.phase
        pod_name = pod.metadata.name
        labels = pod.metadata.labels or {}

        if args.pod_status == 'All' or status == args.pod_status:
            # Get the primary container name if possible (often needed by kubectl cp)
            container_name = pod.spec.containers[0].name if pod.spec.containers else None
            if not container_name:
                 print(f"Warning: Could not determine container name for pod '{pod_name}'. Skipping copy.", file=sys.stderr)
                 continue
            pods_to_process.append((pod_name, container_name, labels))
            print(f"  Selected pod: {pod_name} (Status: {status})")
        else:
            print(f"  Skipping pod: {pod_name} (Status: {status})")


    if not pods_to_process:
        print(f"No pods found with status '{args.pod_status}'. Exiting.")
        sys.exit(0)

    print(f"\nStarting file copy process for {len(pods_to_process)} pods using up to {args.max_workers} workers...")

    # --- Copy Files in Parallel ---
    copy_success_pods = []
    copy_failed_pods = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_pod = {
            executor.submit(copy_files_from_pod, args.namespace, pod_name, container_name, args.source_paths, output_base_dir, labels): pod_name
            for pod_name, container_name, labels in pods_to_process
        }

        processed_count = 0
        total_count = len(future_to_pod)
        for future in as_completed(future_to_pod):
            processed_count += 1
            pod_name = future_to_pod[future]
            try:
                success = future.result()
                if success:
                    copy_success_pods.append(pod_name)
                    print(f"  [{processed_count}/{total_count}] Completed copy for pod: {pod_name}")
                else:
                    copy_failed_pods.append(pod_name)
                    print(f"  [{processed_count}/{total_count}] FAILED copy for pod: {pod_name}", file=sys.stderr)
            except Exception as e:
                copy_failed_pods.append(pod_name)
                print(f"  [{processed_count}/{total_count}] EXCEPTION during copy for pod {pod_name}: {e}", file=sys.stderr)

    # --- Summary ---
    print("\n--- File Copy Summary ---")
    print(f"Total Pods attempted: {len(pods_to_process)}")
    print(f"Successful copies:    {len(copy_success_pods)}")
    print(f"Failed copies:        {len(copy_failed_pods)}")
    if copy_failed_pods:
        print("  Failed pods:", ', '.join(copy_failed_pods))
        print("Check logs above for specific errors (e.g., path not found, permissions).")


    # --- Optional Cleanup ---
    if args.cleanup and copy_success_pods:
        print("\n--- Optional Cleanup ---")
        print(f"Attempting to delete {len(copy_success_pods)} pods where copy succeeded...")
        deleted_count = 0
        failed_delete_count = 0
        for pod_name in copy_success_pods:
             try:
                  print(f"  Deleting pod {pod_name}...")
                  core_api.delete_namespaced_pod(name=pod_name, namespace=args.namespace, body=client.V1DeleteOptions())
                  deleted_count += 1
                  time.sleep(0.1) # Small delay
             except ApiException as e:
                  failed_delete_count += 1
                  print(f"    Failed to delete pod {pod_name}: {e.status} - {e.reason}", file=sys.stderr)
             except Exception as e:
                  failed_delete_count += 1
                  print(f"    Unexpected error deleting pod {pod_name}: {e}", file=sys.stderr)
        print(f"Cleanup summary: Deleted {deleted_count}, Failed {failed_delete_count}")
    elif args.cleanup:
        print("\nCleanup requested, but no pods had successful copies. No pods deleted.")


if __name__ == '__main__':
    main()
