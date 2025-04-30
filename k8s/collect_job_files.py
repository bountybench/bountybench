#!/usr/bin/env python3
"""
collect_job_files.py: Copy files from job output PVC via a temporary pod.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from kubernetes import client, config, watch
from kubernetes.client import CoreV1Api
from kubernetes.client.rest import ApiException

# --- Configuration ---
JOB_OUTPUT_PVC_NAME = "job-output-pvc"
COLLECTOR_POD_MOUNT_PATH = "/collected_data"
COLLECTOR_POD_BASENAME = "job-file-collector"


def wait_for_pod_running(
    core_api: CoreV1Api, namespace: str, pod_name: str, timeout_seconds: int = 120
):
    """Waits for a pod to reach the Running state."""
    start_time = time.time()
    w = watch.Watch()
    try:
        for event in w.stream(
            core_api.list_namespaced_pod,
            namespace=namespace,
            field_selector=f"metadata.name={pod_name}",
            timeout_seconds=timeout_seconds,
        ):
            pod = event["object"]
            status = pod.status.phase
            print(f"  Collector pod '{pod_name}' status: {status}")
            if status == "Running":
                w.stop()
                print(f"  Collector pod '{pod_name}' is Running.")
                return True
            elif status in ["Failed", "Succeeded", "Unknown"]:
                w.stop()
                print(
                    f"  Collector pod '{pod_name}' entered terminal state {status} unexpectedly.",
                    file=sys.stderr,
                )
                # Attempt to get logs
                try:
                    logs = core_api.read_namespaced_pod_log(
                        name=pod_name, namespace=namespace
                    )
                    print(f"  Collector pod logs:\n{logs}", file=sys.stderr)
                except ApiException as log_e:
                    print(
                        f"  Could not retrieve logs for pod {pod_name}: {log_e}",
                        file=sys.stderr,
                    )
                return False

            # Check timeout inside loop
            if time.time() - start_time > timeout_seconds:
                w.stop()
                print(
                    f"  Timeout waiting for pod '{pod_name}' to become Running.",
                    file=sys.stderr,
                )
                return False
    except ApiException as e:
        # Handle potential watch errors (e.g., timeout on the watch itself)
        if e.status == 404 and "too old resource version" in str(e.body).lower():
            print(
                f"  Watch error (resource version too old), retrying check for pod {pod_name}...",
                file=sys.stderr,
            )
            # Fallback to direct read check after watch error
            try:
                pod_info = core_api.read_namespaced_pod_status(
                    name=pod_name, namespace=namespace
                )
                if pod_info.status.phase == "Running":
                    return True
            except ApiException as read_e:
                print(
                    f"  Error reading pod status after watch failed: {read_e}",
                    file=sys.stderr,
                )
        else:
            print(f"  Error watching pod '{pod_name}': {e}", file=sys.stderr)
        return False  # Treat watch errors/timeout as failure
    except Exception as e:
        print(f"  Unexpected error watching pod '{pod_name}': {e}", file=sys.stderr)
        return False

    # If loop finishes without success or explicit failure (e.g. watch timeout)
    print(
        f"  Watch ended for pod '{pod_name}' without reaching Running state within timeout.",
        file=sys.stderr,
    )
    return False


def copy_files_via_collector(
    core_api: CoreV1Api, namespace: str, logs_output_dir: Path, full_logs_output_dir: Path
):
    """Creates a temp pod, copies specific dirs from its PVC mount, then deletes it."""
    pod_name = f"{COLLECTOR_POD_BASENAME}-{int(time.time())}"
    collector_pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": pod_name, "labels": {"app": COLLECTOR_POD_BASENAME}},
        "spec": {
            "containers": [
                {
                    "name": "collector",
                    "image": "arm64v8/alpine",  # Use ARM64 Alpine image
                    "command": ["/bin/sh", "-c", "sleep 3600"],  # Keepalive
                    "volumeMounts": [
                        {
                            "name": "job-output-volume",
                            "mountPath": COLLECTOR_POD_MOUNT_PATH,
                        }
                    ],
                }
            ],
            "volumes": [
                {
                    "name": "job-output-volume",
                    "persistentVolumeClaim": {"claimName": JOB_OUTPUT_PVC_NAME},
                }
            ],
            "restartPolicy": "Never",
            "tolerations": [
                {
                    "key": "kubernetes.io/arch",
                    "operator": "Equal",
                    "value": "arm64",
                    "effect": "NoSchedule",
                }
            ],
        },
    }

    pod_created = False
    try:
        print(f"Creating collector pod '{pod_name}' in namespace '{namespace}'...")
        core_api.create_namespaced_pod(namespace=namespace, body=collector_pod_manifest)
        pod_created = True
        print(f"Waiting for collector pod '{pod_name}' to start...")
        if not wait_for_pod_running(core_api, namespace, pod_name):
            print(
                f"Collector pod '{pod_name}' did not reach Running state.",
                file=sys.stderr,
            )
            return False  # Indicate failure

        # --- Copying ---
        # Ensure output directories exist
        logs_output_dir.mkdir(parents=True, exist_ok=True)
        full_logs_output_dir.mkdir(parents=True, exist_ok=True)

        success = True  # Assume success initially

        # Define source paths within the pod and their corresponding local destinations
        copy_tasks = {
            "logs": (
                f"{namespace}/{pod_name}:{COLLECTOR_POD_MOUNT_PATH}/logs/",
                logs_output_dir,
            ),
            "full_logs": (
                f"{namespace}/{pod_name}:{COLLECTOR_POD_MOUNT_PATH}/full_logs/",
                full_logs_output_dir,
            ),
        }

        for key, (source_spec, dest_local) in copy_tasks.items():
            # Ensure trailing slash for directory contents copy
            copy_cmd = ["kubectl", "cp", source_spec, str(dest_local)]
            print(f"Executing copy command: {' '.join(copy_cmd)}")
            try:
                result = subprocess.run(
                    copy_cmd, capture_output=True, text=True, check=True, timeout=600
                )  # 10 min timeout
                print(f"  Copy successful for '{key}'.")
                if result.stdout:
                    print(f"  Stdout:\n{result.stdout}")
                if result.stderr:
                    print(
                        f"  Stderr:\n{result.stderr}", file=sys.stderr
                    )  # Log stderr even on success
            except subprocess.CalledProcessError as e:
                # Check if the error is 'No such file or directory'
                if "no such file or directory" in e.stderr.lower():
                    print(
                        f"  Warning: Source path '{source_spec}' not found in pod '{pod_name}'. Skipping copy for '{key}'."
                    )
                    # Optionally, you might want to treat this as non-fatal
                    # success = False # Uncomment if missing path should be a failure
                else:
                    print(
                        f"  ERROR copying '{key}' from collector pod '{pod_name}'.",
                        file=sys.stderr,
                    )
                    print(f"    Return Code: {e.returncode}", file=sys.stderr)
                    print(f"    Command: {' '.join(e.cmd)}", file=sys.stderr)
                    print(f"    Stderr: {e.stderr}", file=sys.stderr)
                    print(f"    Stdout: {e.stdout}", file=sys.stderr)
                    success = False  # Mark overall operation as failed
            except subprocess.TimeoutExpired as e:
                print(
                    f"  ERROR: Timeout expired copying '{key}' from collector pod '{pod_name}'.",
                    file=sys.stderr,
                )
                print(f"    Command: {' '.join(e.cmd)}", file=sys.stderr)
                success = False
            except Exception as e:
                print(
                    f"  ERROR: Unexpected error copying '{key}': {e}", file=sys.stderr
                )
                success = False

        return success  # Return overall success status

    except ApiException as e:
        print(
            f"Kubernetes API error during collector pod management: {e}",
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return False
    finally:
        # --- Cleanup ---
        if pod_created:
            try:
                print(f"Deleting collector pod '{pod_name}'...")
                core_api.delete_namespaced_pod(
                    name=pod_name, namespace=namespace, body=client.V1DeleteOptions()
                )
                print(f"Collector pod '{pod_name}' deleted.")
            except ApiException as e:
                # Log cleanup error but don't necessarily fail the whole script based on this
                print(
                    f"Warning: Failed to delete collector pod '{pod_name}'. Please delete manually. Error: {e}",
                    file=sys.stderr,
                )


# --- Main Execution Logic ---
def main():
    parser = argparse.ArgumentParser(
        description="Copy logs and full_logs from job output PVC via a temporary pod."
    )
    parser.add_argument(
        "--namespace",
        "-n",
        default="bounty-experiments",
        help="Kubernetes namespace where the PVC exists (default: bounty-experiments)",
    )
    # Removed --output-dir
    parser.add_argument(
        "--logs-dir",
        default="../logs",
        help="Local directory to save the 'logs' files (default: ../logs)",
    )
    parser.add_argument(
        "--full-logs-dir",
        default="../full_logs",
        help="Local directory to save the 'full_logs' files (default: ../full_logs)",
    )
    args = parser.parse_args()

    logs_directory = Path(args.logs_dir).resolve()
    full_logs_directory = Path(args.full_logs_dir).resolve()
    print(f"Namespace: {args.namespace}")
    print(f"Logs output directory: {logs_directory}")
    print(f"Full Logs output directory: {full_logs_directory}")

    print("Loading Kubernetes configuration...")
    try:
        config.load_kube_config()
        core_v1 = client.CoreV1Api()
        print("Kubernetes configuration loaded successfully.")
    except Exception as e:
        print(f"Error loading Kubernetes configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Execute the collection process
    overall_success = copy_files_via_collector(
        core_v1, args.namespace, logs_directory, full_logs_directory
    )

    if overall_success:
        print("\n--- File Collection Summary ---")
        print(
            f"Successfully copied files from PVC '{JOB_OUTPUT_PVC_NAME}' in namespace '{args.namespace}'"
        )
        print(f"  Logs copied to: '{logs_directory}'")
        print(f"  Full logs copied to: '{full_logs_directory}'")
    else:
        print("\n--- File Collection Summary ---")
        print(
            f"FAILED to copy one or more directories (logs, full_logs) from PVC '{JOB_OUTPUT_PVC_NAME}' in namespace '{args.namespace}'. Check errors above."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
