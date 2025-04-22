#!/usr/bin/env python3
import argparse
import datetime
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import yaml
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream


class Status(Enum):
    """Pod status enum to prevent typos and improve readability."""

    IDLE = "idle"
    BUSY = "busy"


def load_yaml_file(file_path):
    """Load a Kubernetes YAML file."""
    try:
        with open(file_path, "r") as f:
            # Convert the generator to a list while the file is still open
            return list(yaml.safe_load_all(f))
    except FileNotFoundError:
        print(f"Error: YAML file not found at {file_path}")
        print(f"Current working directory: {os.getcwd()}")
        print("Available files in current directory:")
        for file in os.listdir("."):
            if file.endswith(".yaml"):
                print(f"  - {file}")
        sys.exit(1)


def create_deployment(apps_api, core_api, yaml_objects, replicas):
    """Create or update a deployment with specified number of replicas."""
    for obj in yaml_objects:
        if obj["kind"] == "Deployment" and obj["metadata"]["name"] == "backend":
            # Set the number of replicas
            obj["spec"]["replicas"] = replicas

            # Create the deployment
            try:
                apps_api.create_namespaced_deployment(namespace="default", body=obj)
                print(f"Deployment created with {replicas} replicas")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    print(
                        f"Deployment already exists, updating with {replicas} replicas"
                    )
                    apps_api.patch_namespaced_deployment(
                        name="backend", namespace="default", body=obj
                    )
                else:
                    print(f"Exception when creating deployment: {e}")
                    raise e

        elif obj["kind"] == "Service" and obj["metadata"]["name"] == "backend-service":
            # Create the service
            try:
                core_api.create_namespaced_service(namespace="default", body=obj)
                print("Service created")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    print("Service already exists")
                else:
                    print(f"Exception when creating service: {e}")
                    raise e


def process_pods_as_ready(
    api_instance, core_api, replicas, user_command, timestamp, executor
):
    """Watch for pods becoming ready and process them immediately."""
    print("Watching for pods to become ready...")

    w = watch.Watch()
    ready_pods = set()
    futures = {}

    for event in w.stream(
        api_instance.list_namespaced_pod,
        namespace="default",
        label_selector="app=backend",
        timeout_seconds=600,
    ):  # 10 minute timeout
        pod = event["object"]
        pod_name = pod.metadata.name

        # Check if pod is ready
        if pod.status.phase == "Running":
            container_statuses = pod.status.container_statuses
            if container_statuses and all(
                status.ready for status in container_statuses
            ):
                if pod_name not in ready_pods:
                    print(f"Pod {pod_name} is ready - starting processing immediately")
                    ready_pods.add(pod_name)

                    # Start processing this pod immediately in a separate thread
                    future = executor.submit(
                        process_pod,
                        core_api,
                        core_api,
                        pod_name,
                        user_command,
                        timestamp,
                    )
                    futures[future] = pod_name

                # If all pods are ready, break the watch
                if len(ready_pods) >= replicas:
                    print(f"All {replicas} pods are now ready and being processed")
                    w.stop()
                    break

    return futures, list(ready_pods)


def get_pod_names(api_instance):
    """Get all backend pod names."""
    pods = api_instance.list_namespaced_pod(
        namespace="default", label_selector="app=backend"
    )
    return [pod.metadata.name for pod in pods.items]


def get_pod_status(api_instance, pod_name):
    """Get the status (idle/busy) of a pod using a status file."""
    # Check if the status file exists
    try:
        # Define the status file path
        status_file = "/app/pod_status.json"

        # Try to read the status file
        result = exec_command_in_pod(api_instance, pod_name, ["cat", status_file])

        # If the command succeeded, parse the status
        try:
            status_data = json.loads(result)
            status_str = status_data.get(
                "status", Status.IDLE.value
            )  # Default to idle if status key missing
            # Convert string status to enum
            if status_str == Status.IDLE.value:
                return Status.IDLE
            elif status_str == Status.BUSY.value:
                return Status.BUSY
            else:
                print(
                    f"Warning: Unknown status '{status_str}' in pod {pod_name}, defaulting to IDLE"
                )
                return Status.IDLE
        except json.JSONDecodeError:
            print(f"Warning: Invalid status file format in pod {pod_name}")
            return Status.IDLE  # Default to idle if file format is invalid

    except Exception as e:
        # If file doesn't exist or any other error, assume the pod is idle
        print(
            f"Note: Could not read status file from pod {pod_name}, assuming idle: {e}"
        )
        return Status.IDLE


def set_pod_status(api_instance, pod_name, status):
    """Set the status (idle/busy) of a pod using a status file."""
    if not isinstance(status, Status):
        raise ValueError(f"Invalid status: {status}. Must be a Status enum value.")

    # Create status data
    status_data = {
        "status": status.value,  # Use the string value from enum
        "timestamp": datetime.datetime.now().isoformat(),
    }

    # Convert to JSON string
    status_json = json.dumps(status_data)

    # Write to status file in pod
    try:
        # First ensure the directory exists
        exec_command_in_pod(api_instance, pod_name, ["mkdir", "-p", "/app"])

        # Write the status file
        # We need to echo the JSON and redirect to the file
        cmd = ["sh", "-c", f"echo '{status_json}' > /app/pod_status.json"]
        exec_command_in_pod(api_instance, pod_name, cmd)

        print(f"Pod {pod_name} status set to: {status.name}")
        return True
    except Exception as e:
        print(f"Error setting status for pod {pod_name}: {e}")
        return False


def find_idle_pods(api_instance):
    """Find all idle backend pods."""
    pod_names = get_pod_names(api_instance)
    idle_pods = []

    for pod_name in pod_names:
        # Check if pod is Running
        pod = api_instance.read_namespaced_pod(name=pod_name, namespace="default")
        if pod.status.phase != "Running":
            continue

        # Check if all containers are ready
        container_statuses = pod.status.container_statuses
        if not container_statuses or not all(
            status.ready for status in container_statuses
        ):
            continue

        # Check the pod's status file
        status = get_pod_status(api_instance, pod_name)
        if status == Status.IDLE:
            idle_pods.append(pod_name)

    return idle_pods


def reset_pod(api_instance, pod_name):
    """Reset a pod to be reused - clear logs and set status to idle."""
    try:
        # Clean up logs directory
        exec_command_in_pod(
            api_instance, pod_name, ["sh", "-c", "rm -rf /app/logs/* || true"]
        )

        # Set status to idle
        set_pod_status(api_instance, pod_name, Status.IDLE)

        print(f"Pod {pod_name} has been reset and is ready for reuse")
        return True
    except Exception as e:
        print(f"Error resetting pod {pod_name}: {e}")
        return False


def exec_command_in_pod(api_instance, pod_name, command, namespace="default"):
    """Execute a command in a pod and return the result."""
    print(f"Executing in {pod_name}: {' '.join(command)}")

    resp = stream(
        api_instance.connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )

    return resp


def parse_command(command_str):
    """Parse a command string into a list of arguments, respecting quotes and backslashes."""
    import shlex

    # Clean up the command string
    # Remove any trailing backslashes that might cause issues
    command_str = command_str.strip()
    command_str = command_str.replace("\\", "")

    # Use shlex to parse the command, which handles quotes and escapes properly
    try:
        return shlex.split(command_str)
    except ValueError as e:
        print(f"Warning: Error parsing command: {e}. Falling back to simple split.")
        # Fall back to simple splitting if shlex fails
        return command_str.split()


def retry_with_backoff(
    func, max_retries=5, initial_backoff=5, backoff_factor=2, error_msgs_to_retry=None
):
    """
    Retry a function with exponential backoff.
    """
    import time

    retries = 0
    backoff = initial_backoff
    last_exception = None

    while retries < max_retries:
        try:
            return func()
        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()

            # Check if this is a retryable error
            should_retry = True
            if error_msgs_to_retry is not None:
                should_retry = any(
                    msg.lower() in error_msg for msg in error_msgs_to_retry
                )

            if not should_retry:
                raise e

            retries += 1
            if retries >= max_retries:
                break

            print(f"Retry attempt {retries}/{max_retries} after error: {e}")
            print(f"Waiting {backoff} seconds before retrying...")
            time.sleep(backoff)
            backoff *= backoff_factor

    # If we get here, all retries failed
    raise last_exception


def process_pod(api_instance, core_api, pod_name, user_command, timestamp):
    """Process a single pod with all required steps."""
    try:
        # Mark pod as busy before starting work
        set_pod_status(api_instance, pod_name, Status.BUSY)

        # Step 1: Pull the Docker image with retry
        print(f"Pulling Docker image in pod {pod_name}...")

        # Define retryable Docker errors
        docker_retry_errors = [
            "cannot connect to the docker daemon",
            "error during connect",
            "connection refused",
            "daemon is not running",
            "resource temporarily unavailable",
            "timeout",
            "too many open files",
            "network is unreachable",
            "unexpected EOF",
        ]

        # Define the pull function to retry
        def do_docker_pull():
            # First check if Docker daemon is running
            docker_info = exec_command_in_pod(
                api_instance,
                pod_name,
                ["docker", "info", "--format", "{{.ServerVersion}}"],
            )
            if "error" in docker_info.lower():
                raise Exception(f"Docker daemon not ready: {docker_info}")

            # If Docker daemon is running, pull the image
            return exec_command_in_pod(
                api_instance,
                pod_name,
                ["docker", "pull", "--quiet", "cybench/bountyagent:latest"],
            )

        # Retry the pull with backoff
        pull_result = retry_with_backoff(
            do_docker_pull,
            max_retries=5,
            initial_backoff=5,
            backoff_factor=2,
            error_msgs_to_retry=docker_retry_errors,
        )
        print(f"Pull result for {pod_name}: {pull_result}")

        # Step 2: Execute user command
        print(f"Executing user command in pod {pod_name}...")
        cmd_parts = parse_command(user_command)
        print(f"Parsed command: {cmd_parts}")
        cmd_result = exec_command_in_pod(api_instance, pod_name, cmd_parts)
        print(f"Command result for {pod_name}: {cmd_result}")

        # Step 3: Copy logs
        copy_logs(core_api, pod_name, timestamp)

        # Mark pod as idle after completion
        set_pod_status(api_instance, pod_name, Status.IDLE)
        return True
    except Exception as e:
        print(f"Error processing pod {pod_name}: {e}")
        # Still mark as idle on error, as the pod is no longer busy
        try:
            set_pod_status(api_instance, pod_name, Status.IDLE)
        except Exception as status_error:
            print(f"Failed to reset pod status after error: {status_error}")
        return False


def copy_logs(core_api, pod_name, timestamp):
    """Copy logs from the pod to a local directory."""
    # Create the logs directory if it doesn't exist
    log_dir = f"./logs/exp-{timestamp}/{pod_name}"
    os.makedirs(log_dir, exist_ok=True)

    # Use kubectl cp command via subprocess as the Python client doesn't support cp directly
    try:
        # Create a temp directory
        temp_dir = f"/tmp/{pod_name}-logs"
        os.makedirs(temp_dir, exist_ok=True)

        # Copy logs from pod to temp directory
        cp_cmd = ["kubectl", "cp", f"{pod_name}:/app/logs/", temp_dir]
        subprocess.run(cp_cmd, check=True)

        # Copy JSON files to the local logs directory
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".json"):
                    src_path = os.path.join(root, file)
                    dst_path = os.path.join(log_dir, file)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    subprocess.run(["cp", "-f", src_path, dst_path], check=True)

        # Clean up temp directory
        subprocess.run(["rm", "-rf", temp_dir], check=True)

        print(f"Logs from {pod_name} copied to {log_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error copying logs from {pod_name}: {e}")


def delete_deployment(api_instance, core_api):
    """Delete the backend deployment and service."""
    try:
        # Delete deployment
        api_instance.delete_namespaced_deployment(name="backend", namespace="default")
        print("Deployment deleted")

        # Delete service
        core_api.delete_namespaced_service(name="backend-service", namespace="default")
        print("Service deleted")
    except ApiException as e:
        print(f"Exception when deleting resources: {e}")


def main():
    parser = argparse.ArgumentParser(description="Kubernetes Experiment Manager")
    parser.add_argument(
        "--yaml",
        type=str,
        default="./backend_exp.yaml",
        help="Path to the YAML file for deployment",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the backend deployment and service without running the experiment",
    )
    parser.add_argument(
        "--no-reuse",
        action="store_true",
        help="Don't reuse idle pods, always create new ones",
    )
    parser.add_argument(
        "--reset-pods",
        action="store_true",
        help="Reset all existing pods to idle state without running an experiment",
    )
    args = parser.parse_args()

    # Load Kubernetes configuration
    try:
        config.load_kube_config()
    except:
        print(
            "Error loading Kubernetes config. Make sure you have proper kubeconfig setup."
        )
        sys.exit(1)

    # Create API clients
    apps_api = client.AppsV1Api()
    core_api = client.CoreV1Api()

    # If --delete flag is set, just delete the deployment and exit
    if args.delete:
        print("Deleting backend deployment and service...")
        delete_deployment(apps_api, core_api)
        print("Cleanup completed.")
        return

    # If --reset-pods flag is set, reset all pods to idle and exit
    if args.reset_pods:
        print("Resetting all pods to idle state...")
        pod_names = get_pod_names(core_api)
        if not pod_names:
            print("No pods found to reset.")
            return

        for pod_name in pod_names:
            reset_pod(core_api, pod_name)

        print(f"Reset {len(pod_names)} pods to idle state.")
        return

    # Load YAML file
    yaml_objects = load_yaml_file(args.yaml)

    # Get user input for number of replicas
    while True:
        try:
            replicas = int(input("Enter the number of replicas for the experiment: "))
            if replicas <= 0:
                print("Number of replicas must be greater than 0")
                continue
            break
        except ValueError:
            print("Please enter a valid number")

    # Get user command to execute in pods
    print("\nEnter the command to execute in each pod:")
    print("(For complex commands with quotes or backslashes, ensure proper escaping)")
    user_command = input("> ")

    # Clean up the command if needed
    user_command = user_command.strip()

    # Generate timestamp for log directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # Check for idle pods if reuse is enabled
    idle_pods = []
    if not args.no_reuse:
        print("Checking for idle pods to reuse...")
        idle_pods = find_idle_pods(core_api)
        print(f"Found {len(idle_pods)} idle pods that can be reused")

    # Calculate how many new pods we need to create
    new_pods_needed = max(0, replicas - len(idle_pods))

    # Create deployment with required number of new pods if needed
    if new_pods_needed > 0:
        print(f"Creating {new_pods_needed} new pods...")
        create_deployment(apps_api, core_api, yaml_objects, new_pods_needed)
    elif len(idle_pods) >= replicas:
        print(f"Using {replicas} existing idle pods, no new pods needed")

    # Select which idle pods to use (if we have more than needed)
    selected_idle_pods = idle_pods[:replicas]

    # Process pods as they become ready (for new pods)
    all_ready_pods = selected_idle_pods.copy()  # Start with idle pods
    futures = {}

    # If we need to wait for new pods
    if new_pods_needed > 0:
        with ThreadPoolExecutor(max_workers=replicas) as executor:
            # Process new pods as they become ready
            new_futures, new_ready_pods = process_pods_as_ready(
                core_api, core_api, new_pods_needed, user_command, timestamp, executor
            )

            # Add new pods to our tracking
            futures.update(new_futures)
            all_ready_pods.extend(new_ready_pods)

            if len(new_ready_pods) < new_pods_needed:
                print(
                    f"Warning: Only {len(new_ready_pods)} of {new_pods_needed} new pods became ready after timeout"
                )

    # Process the idle pods we're reusing (only if we have any)
    if selected_idle_pods:
        with ThreadPoolExecutor(max_workers=len(selected_idle_pods)) as executor:
            for pod_name in selected_idle_pods:
                print(f"Reusing idle pod {pod_name}")
                # Reset the pod before reusing it (clean logs, etc.)
                reset_pod(core_api, pod_name)
                # Start processing this pod in a separate thread
                future = executor.submit(
                    process_pod,
                    core_api,
                    core_api,
                    pod_name,
                    user_command,
                    timestamp,
                )
                futures[future] = pod_name

    if not all_ready_pods:
        print("No pods are ready after timeout. Exiting.")
        delete_deployment(apps_api, core_api)
        sys.exit(1)

    # Track completed and failed pods
    completed_pods = []
    failed_pods = []

    print(f"\nWaiting for all {len(futures)} pods to complete processing...")

    for future in futures:
        pod_name = futures[future]
        try:
            # Wait for the future to complete
            result = future.result()
            if result:
                print(f"✅ Processing completed successfully for pod {pod_name}")
                completed_pods.append(pod_name)
            else:
                print(f"❌ Processing failed for pod {pod_name}")
                failed_pods.append(pod_name)
        except Exception as e:
            print(f"❌ Exception processing pod {pod_name}: {e}")
            failed_pods.append(pod_name)

    # Print summary
    print(f"\nExperiment Summary:")
    print(f"- Total pods: {len(futures)}")
    print(f"- Reused pods: {len(selected_idle_pods)}")
    print(f"- New pods: {len(all_ready_pods) - len(selected_idle_pods)}")
    print(
        f"- Successful pods: {len(completed_pods)} ({', '.join(completed_pods) if completed_pods else 'None'})"
    )
    print(
        f"- Failed pods: {len(failed_pods)} ({', '.join(failed_pods) if failed_pods else 'None'})"
    )

    # Ask if user wants to delete the deployment
    delete_choice = input("Do you want to delete the deployments now? (y/n): ").lower()
    if delete_choice.startswith("y"):
        delete_deployment(apps_api, core_api)
    else:
        print(
            "Deployment not deleted. You can delete it manually later or reuse the pods for future experiments."
        )

    print(f"Experiment completed. Logs are saved in ./logs/exp-{timestamp}/")


if __name__ == "__main__":
    main()
