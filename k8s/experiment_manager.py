#!/usr/bin/env python3
import os
import sys
import yaml
import datetime
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream


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
    while command_str.endswith("\\"):
        command_str = command_str[:-1].strip()

    # Use shlex to parse the command, which handles quotes and escapes properly
    try:
        return shlex.split(command_str)
    except ValueError as e:
        print(f"Warning: Error parsing command: {e}. Falling back to simple split.")
        # Fall back to simple splitting if shlex fails
        return command_str.split()


def process_pod(api_instance, core_api, pod_name, user_command, timestamp):
    """Process a single pod with all required steps."""
    try:
        # Step 1: Pull the Docker image
        print(f"Pulling Docker image in pod {pod_name}...")
        pull_result = exec_command_in_pod(
            api_instance,
            pod_name,
            ["docker", "pull", "--quiet", "cybench/bountyagent:latest"],
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

        return True
    except Exception as e:
        print(f"Error processing pod {pod_name}: {e}")
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

    # Create deployment with specified replicas
    create_deployment(apps_api, core_api, yaml_objects, replicas)

    # Process pods as they become ready
    with ThreadPoolExecutor(max_workers=replicas) as executor:
        futures, ready_pods = process_pods_as_ready(
            core_api, core_api, replicas, user_command, timestamp, executor
        )

        if not ready_pods:
            print("No pods are ready after timeout. Exiting.")
            delete_deployment(apps_api, core_api)
            sys.exit(1)

        # Wait for all tasks to complete
        for future in futures:
            pod_name = futures[future]
            try:
                result = future.result()
                if result:
                    print(f"Processing completed successfully for pod {pod_name}")
                else:
                    print(f"Processing failed for pod {pod_name}")
            except Exception as e:
                print(f"Exception processing pod {pod_name}: {e}")

    # Ask if user wants to delete the deployment
    delete_choice = input("Do you want to delete the deployment now? (y/n): ").lower()
    if delete_choice.startswith("y"):
        delete_deployment(apps_api, core_api)
    else:
        print("Deployment not deleted. You can delete it manually later.")

    print(f"Experiment completed. Logs are saved in ./logs/exp-{timestamp}/")


if __name__ == "__main__":
    main()
