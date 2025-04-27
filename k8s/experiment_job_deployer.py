#!/usr/bin/env python3
"""
experiment_job_deployer.py: Deploy experiment tasks as Kubernetes Jobs.
"""

import argparse
import glob
import json
import sys
import time
import copy
from pathlib import Path
import subprocess
import datetime
import re
import hashlib
import yaml
from kubernetes import client, config
from kubernetes.client import CoreV1Api
from kubernetes.client.rest import ApiException
from concurrent.futures import ThreadPoolExecutor, as_completed
import shlex

# --- Configuration Parsing (adapted from original script) ---
def parse_config(config_path):
    """
    Read a JSON experiment config and produce a list of runner commands.
    Also extracts metadata needed for job naming/labeling.
    """
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return None, None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in {config_path}: {e}", file=sys.stderr)
        return None, None

    required = [
        'workflow_type', 'phase_iterations', 'use_helm',
        'model', 'max_input_tokens', 'max_output_tokens', 'tasks'
    ]
    for key in required:
        if key not in cfg:
            print(f"Missing key '{key}' in {config_path}", file=sys.stderr)
            return None, None # Indicate failure

    workflow = cfg['workflow_type']
    phase_iter = cfg['phase_iterations']
    use_helm = cfg['use_helm']
    model = cfg['model']
    max_in = cfg['max_input_tokens']
    max_out = cfg['max_output_tokens']
    tasks = cfg['tasks']

    if not isinstance(tasks, list):
        print(f"Error: 'tasks' key in {config_path} must be a list.", file=sys.stderr)
        return None, None

    commands = []
    task_details = [] # Store structured task info
    for entry in tasks:
        if not isinstance(entry, str) or '/' not in entry:
            print(f"Invalid task entry format '{entry}' in {config_path}. Expected 'task_dir/bounty_number'.", file=sys.stderr)
            # Optionally continue and skip this entry, or fail the whole config
            continue # Skip invalid entry

        task_dir_part, bounty = entry.split('/', 1)
        task_dir = f"bountybench/{task_dir_part}"
        task_details.append({'full_entry': entry, 'task_dir_part': task_dir_part, 'bounty': bounty})

        parts = [
            'python', '-m', 'workflows.runner',
            '--workflow-type', workflow,
            '--phase_iterations', str(phase_iter)
        ]
        if use_helm:
            parts.append('--use_helm')
        parts.extend([
            '--model', model,
            '--max_input_tokens', str(max_in),
            '--max_output_tokens', str(max_out),
            '--task_dir', task_dir,
            '--bounty_number', bounty
        ])
        # Log command output within the container to stdout/stderr for `kubectl logs`
        command_str = ' '.join(parts)
        # Example: Add logging redirection if needed, but Job logs capture stdout/stderr by default
        # command_str = f"{' '.join(parts)} > /proc/1/fd/1 2>/proc/1/fd/2"
        commands.append(command_str)


    metadata = {
        'workflow_type': workflow,
        'model': model,
        'tasks': task_details # Use the structured details
    }
    return commands, metadata

# --- Kubernetes Utilities ---

def sanitize_name(raw: str) -> str:
    """Convert raw string to RFC 1123-compliant name (lowercase, alphanumeric, hyphen)."""
    name = raw.lower()
    name = re.sub(r'[^a-z0-9-]+', '-', name) # Replace invalid chars
    name = re.sub(r'-+', '-', name)         # Collapse multiple hyphens
    name = re.sub(r'(^-+|-+$)', '', name)     # Strip leading/trailing hyphens
    # Max length for K8s names is 253, but labels/etc. are often 63.
    # Job names can be longer, but keep it reasonable. Let's use 63 for safety with derived names.
    return name[:63]

def load_yaml_template(template_path):
    """Loads a single YAML document from a file."""
    try:
        with open(template_path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML template {template_path}: {e}", file=sys.stderr)
        sys.exit(1)

def ensure_namespace(api: client.CoreV1Api, namespace: str):
    """Creates namespace if it doesn't exist."""
    try:
        api.read_namespace(name=namespace)
        print(f"Namespace '{namespace}' already exists.")
    except ApiException as e:
        if e.status == 404:
            print(f"Namespace '{namespace}' not found. Creating...")
            ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
            api.create_namespace(body=ns)
            print(f"Created namespace '{namespace}'")
            # Add a small delay to allow namespace propagation if needed
            time.sleep(2)
        else:
            print(f"Error checking namespace '{namespace}': {e.status} - {e.reason}", file=sys.stderr)
            try:
                error_body = json.loads(e.body)
                print(f"Error details: {json.dumps(error_body, indent=2)}", file=sys.stderr)
            except: # noqa
                 print(f"Raw error body: {e.body}", file=sys.stderr)
            raise # Re-raise other errors

def ensure_secret(namespace: str, env_file: str = '../.env'):
    """Creates or updates the 'app-secrets' secret from an env file using kubectl apply."""
    env_path = Path(env_file)
    if not env_path.is_file():
        print(f"Warning: Environment file '{env_file}' not found. Secret 'app-secrets' might be missing or outdated.", file=sys.stderr)
        # Depending on requirements, you might want to exit here:
        # sys.exit(f"Error: Required environment file '{env_file}' not found.")
        return # Or just continue, assuming secret might exist or is not strictly needed

    print(f"Creating/updating secret 'app-secrets' in namespace '{namespace}' from '{env_file}' using kubectl apply")
    try:
        # Generate the secret YAML using --dry-run=client
        cmd_dry_run = [
            'kubectl', 'create', 'secret', 'generic', 'app-secrets',
            f'--from-env-file={env_file}', '--dry-run=client', '-o', 'yaml',
            '-n', namespace
        ]
        proc_dry_run = subprocess.run(cmd_dry_run, text=True, capture_output=True, check=True, encoding='utf-8')
        secret_yaml = proc_dry_run.stdout

        # Apply the generated YAML
        cmd_apply = ['kubectl', 'apply', '-f', '-', '-n', namespace]
        proc_apply = subprocess.run(cmd_apply, input=secret_yaml, text=True, capture_output=True, check=True, encoding='utf-8')

        print(f"Secret 'app-secrets' apply status: {proc_apply.stdout.strip()}")

    except subprocess.CalledProcessError as e:
        print(f"Error creating/updating secret 'app-secrets':", file=sys.stderr)
        print(f"  Command: {' '.join(e.cmd)}", file=sys.stderr)
        print(f"  Return Code: {e.returncode}", file=sys.stderr)
        print(f"  Stderr: {e.stderr.strip() if e.stderr else 'N/A'}", file=sys.stderr)
        # Decide if this is fatal
        sys.exit(1) # Exit if secret cannot be applied


def create_job(batch_api: client.BatchV1Api, job_template: dict, namespace: str,
               group_name: str, task_detail: dict, command: str, timestamp: str):
    """Creates a single Kubernetes Job for a specific task."""
    job_manifest = copy.deepcopy(job_template)

    # Generate a unique, descriptive, and valid name
    # Format: {group}-{task_dir}-{bounty}-{timestamp-short}
    task_id_part = sanitize_name(f"{task_detail['task_dir_part']}-{task_detail['bounty']}")
    ts_short = timestamp.split('-')[-1] # Get H M S part
    job_name = sanitize_name(f"{group_name}-{task_id_part}-{ts_short}")
    # Ensure final name doesn't exceed limits (already handled by sanitize_name)

    # --- Patch Metadata ---
    job_manifest['metadata']['name'] = job_name
    job_manifest['metadata']['namespace'] = namespace
    # Ensure labels dictionary exists
    job_manifest['metadata'].setdefault('labels', {})
    job_manifest['metadata']['labels']['app'] = 'bounty-task' # Consistent app label
    job_manifest['metadata']['labels']['experiment-group'] = group_name
    job_manifest['metadata']['labels']['task-id'] = task_id_part
    # Add full task entry as a label (sanitized) if useful for filtering
    job_manifest['metadata']['labels']['task-full'] = sanitize_name(task_detail['full_entry'])

    # --- Patch Pod Spec ---
    pod_template = job_manifest['spec']['template']
    # Ensure pod metadata and labels dictionaries exist
    pod_template.setdefault('metadata', {}).setdefault('labels', {})
    # Ensure pod labels match job labels for potential selection/management
    pod_template['metadata']['labels']['app'] = 'bounty-task'
    pod_template['metadata']['labels']['experiment-group'] = group_name
    pod_template['metadata']['labels']['task-id'] = task_id_part
    pod_template['metadata']['labels']['job-name'] = job_name # Link pod to job name via label

    # --- Patch Container Spec ---
    if not pod_template['spec'].get('containers'):
         print(f"Error: Job template {job_template.get('metadata',{}).get('name','unnamed')} has no containers defined in spec.template.spec.containers", file=sys.stderr)
         return None # Cannot proceed

    container = pod_template['spec']['containers'][0] # Assuming one container definition in template
    container['name'] = f"runner-{task_id_part}" # Unique container name within pod
    # Set the actual command to run via sh -c
    container['command'] = ["/bin/sh", "-c"] # Override template command

    # Join the original command list into a shell-safe string *for logging only*
    joined_task_command_for_echo = shlex.join([command])
    # Create the command string for direct execution by joining with spaces
    raw_task_command_for_exec = " ".join([command])

    # Define the wrapper script
    # Note the {{ and }} to escape curly braces for the f-string itself
    wrapper_script = f"""
set -e # Exit immediately if a command exits with a non-zero status.

echo "[wrapper] Starting Docker daemon..."
dockerd > /var/log/dockerd.log 2>&1 &
dockerd_pid=$!

echo "[wrapper] Waiting for Docker daemon to become ready..."
max_wait=45 # Increased wait time slightly
current_wait=0
while ! docker info > /dev/null 2>&1; do
    if [ $current_wait -ge $max_wait ]; then
        echo "[wrapper] Docker daemon failed to start within ${{max_wait}} seconds." >&2 
        echo "[wrapper] dockerd logs:" >&2
        cat /var/log/dockerd.log >&2
        # Attempt to kill the lingering dockerd process if it exists
        if kill -0 $dockerd_pid > /dev/null 2>&1; then
            kill $dockerd_pid
            wait $dockerd_pid # Wait for it to actually exit
        fi
        exit 1
    fi
    echo "[wrapper] Waiting for Docker daemon... (${{current_wait}}s / ${{max_wait}}s)"
    sleep 1
    current_wait=$((current_wait + 1))
done

echo "[wrapper] Docker daemon is ready."

echo "[wrapper] Executing original command (logged safely): {joined_task_command_for_echo}"
# Use exec with the raw space-joined command string
exec {raw_task_command_for_exec}
"""
    # Set the *single* argument (the wrapper script)
    container["args"] = [wrapper_script]

    try:
        print(f"Creating Job: {job_name} (Group: {group_name}, Task: {task_detail['full_entry']}) ...")
        api_response = batch_api.create_namespaced_job(body=job_manifest, namespace=namespace)
        created_job_name = api_response.metadata.name
        # Short delay to avoid overwhelming the API server if creating many jobs rapidly
        time.sleep(0.1)
        return created_job_name
    except ApiException as e:
        print(f"Failed to create Job '{job_name}': {e.status} - {e.reason}", file=sys.stderr)
        try:
            error_body = json.loads(e.body)
            print(f"Error details: {json.dumps(error_body, indent=2)}", file=sys.stderr)
        except: # noqa
            print(f"Raw error body: {e.body}", file=sys.stderr)
        return None # Indicate failure

# --- PVC Configuration ---
JOB_OUTPUT_PVC_NAME = "job-output-pvc"
JOB_OUTPUT_MOUNT_PATH = "/output"

def ensure_pvc_exists(core_api: CoreV1Api, namespace: str, pvc_name: str):
    """Checks if a PVC exists, creates it if not."""
    pvc_manifest = {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {"name": pvc_name},
        "spec": {
            "accessModes": ["ReadWriteOnce"],
            "resources": {"requests": {"storage": "4Gi"}}, # Min size for hyperdisk-balanced
            # Add storageClassName here if needed for your cluster
            "storageClassName": "standard-arm", 
        },
    }
    try:
        core_api.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=namespace)
        print(f"PersistentVolumeClaim '{pvc_name}' already exists in namespace '{namespace}'.")
    except ApiException as e:
        if e.status == 404:
            print(f"PersistentVolumeClaim '{pvc_name}' not found in namespace '{namespace}'. Creating...")
            try:
                core_api.create_namespaced_persistent_volume_claim(namespace=namespace, body=pvc_manifest)
                print(f"PersistentVolumeClaim '{pvc_name}' created successfully.")
                # Add a small delay to allow PVC to bind potentially?
                time.sleep(5) 
            except ApiException as create_e:
                print(f"Error creating PersistentVolumeClaim '{pvc_name}': {create_e}", file=sys.stderr)
                raise # Re-raise the creation error
        else:
            print(f"Error checking PersistentVolumeClaim '{pvc_name}': {e}", file=sys.stderr)
            raise # Re-raise other API errors

# --- Main Execution Logic ---
def main():
    parser = argparse.ArgumentParser(
        description="Deploy experiment tasks as Kubernetes Jobs"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--configs', nargs='+', help='Path(s) to JSON experiment config file(s)'
    )
    group.add_argument(
        '--all', action='store_true', help='Use all experiment_config_*.json files in ./experiment-config/'
    )
    parser.add_argument(
        '--template', default=str(Path(__file__).parent / 'backend_job_template.yaml'),
        help='Path to the Job YAML template (default: ./backend_job_template.yaml)'
    )
    parser.add_argument(
        '--namespace', default='bounty-experiments', help='Kubernetes namespace for jobs (default: bounty-experiments)'
    )
    parser.add_argument(
        '--env-file', default='../.env', help='Path to the .env file for app-secrets (default: ../.env)'
    )
    parser.add_argument(
        '--max-workers', type=int, default=10, help='Max concurrent K8s Job creation requests (default: 10)'
    )
    parser.add_argument(
        '--job-prefix', default='exp', help='Prefix for job names (default: exp)'
    )

    args = parser.parse_args()

    if args.all:
        # Assume experiment-config is relative to this script's parent dir
        base = Path(__file__).resolve().parent / 'experiment-config'
        if not base.is_dir():
             print(f"Error: --all specified, but directory not found: {base}", file=sys.stderr)
             sys.exit(1)
        config_paths = sorted(base.glob('experiment_config_*.json'))
        # Exclude templates if necessary (adjust pattern if needed)
        config_paths = [p for p in config_paths if 'template' not in p.stem]
        if not config_paths:
             print(f"Error: --all specified, but no matching config files found in {base}", file=sys.stderr)
             sys.exit(1)
        print(f"Found {len(config_paths)} config files in {base}")
    else:
        config_paths = [Path(p) for p in args.configs]
        # Basic validation if paths exist
        for p in config_paths:
            if not p.is_file():
                print(f"Error: Specified config file not found: {p}", file=sys.stderr)
                sys.exit(1)

    # --- Load Kubeconfig ---
    try:
        print("Loading Kubernetes configuration...")
        config.load_kube_config()
        core_api = client.CoreV1Api()
        batch_api = client.BatchV1Api()
        print("Kubernetes configuration loaded successfully.")
    except Exception as e:
        print(f"Error: Could not load Kubernetes config: {e}", file=sys.stderr)
        print("Ensure your KUBECONFIG environment variable is set or ~/.kube/config is valid.", file=sys.stderr)
        sys.exit(1)

    # --- Prepare Namespace and Secrets ---
    try:
        ensure_namespace(core_api, args.namespace)
        ensure_secret(args.namespace, args.env_file)
    except Exception as e:
         print(f"Failed during namespace/secret preparation: {e}", file=sys.stderr)
         sys.exit(1) # Exit if basic setup fails

    # Ensure the output PVC exists
    try:
        ensure_pvc_exists(core_api, args.namespace, JOB_OUTPUT_PVC_NAME)
    except ApiException:
        print(f"Failed to ensure PVC '{JOB_OUTPUT_PVC_NAME}' exists. Exiting.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during PVC check/creation: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Load Job Template ---
    job_template = load_yaml_template(args.template)

    # --- Generate Timestamp ---
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # --- Process Configs and Create Job Submission Tasks ---
    job_submission_tasks = []
    for config_path in config_paths:
        print(f"\nProcessing config: {config_path.name}")
        commands, metadata = parse_config(config_path)

        if commands is None or metadata is None:
             print(f"Skipping config {config_path.name} due to parsing errors.")
             continue # Skip to next config file

        if not commands:
            print(f"No valid tasks found or generated for {config_path.name}. Skipping.")
            continue

        # Use the config file stem (without extension) combined with prefix as group name
        raw_group_name = f"{args.job_prefix}-{config_path.stem.replace('experiment_config_', '')}"
        group_name = sanitize_name(raw_group_name)

        print(f"Experiment Group: {group_name} ({len(commands)} tasks planned)")

        # Create a list of tuples: (batch_api, job_template, namespace, group_name, task_detail, command, timestamp)
        for task_detail, command in zip(metadata['tasks'], commands):
             job_submission_tasks.append(
                 (batch_api, job_template, args.namespace, group_name, task_detail, command, timestamp)
             )

    if not job_submission_tasks:
        print("No valid jobs to create after processing all configs. Exiting.")
        sys.exit(0)

    print(f"\nPrepared {len(job_submission_tasks)} tasks across {len(config_paths)} config file(s). Total Jobs to create: {len(job_submission_tasks)}")
    print(f"Submitting Kubernetes Jobs to namespace '{args.namespace}' using up to {args.max_workers} parallel requests...")

    # --- Submit Jobs in Parallel ---
    created_jobs = []
    failed_jobs = 0
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        # Submit tasks: executor.submit(function, *args)
        future_to_task = {
            executor.submit(create_job, *task_args): task_args
            for task_args in job_submission_tasks
        }

        processed_count = 0
        total_count = len(future_to_task)
        for future in as_completed(future_to_task):
            processed_count += 1
            task_args = future_to_task[future]
            group, task_detail, command = task_args[3], task_args[4], task_args[5] # Extract info for logging
            try:
                job_name = future.result()
                if job_name:
                    created_jobs.append(job_name)
                    # Print progress less frequently if many jobs
                    if total_count < 50 or processed_count % 10 == 0:
                         print(f"  [{processed_count}/{total_count}] Created job: {job_name}")
                else:
                    failed_jobs += 1
                    print(f"  [{processed_count}/{total_count}] FAILED creation for task: {task_detail['full_entry']} (Group: {group})", file=sys.stderr)

            except Exception as e:
                failed_jobs += 1
                print(f"  [{processed_count}/{total_count}] EXCEPTION during creation for task: {task_detail['full_entry']} (Group: {group})", file=sys.stderr)
                print(f"    Error: {e}", file=sys.stderr)
                # import traceback
                # traceback.print_exc()

    # --- Summary ---
    print("\n--- Job Submission Summary ---")
    print(f"Total Tasks Processed: {len(job_submission_tasks)}")
    print(f"Successfully Created:  {len(created_jobs)} Jobs")
    if failed_jobs > 0:
        print(f"Failed Attempts:       {failed_jobs}")
        print("\nPlease check the logs above and Kubernetes events for failure details (e.g., `kubectl get events -n <namespace>`).")
    else:
        print("All planned jobs submitted successfully.")

    print(f"\nMonitor job status in namespace '{args.namespace}' using:")
    print(f"  kubectl get jobs -n {args.namespace} -w")
    print(f"  kubectl get pods -n {args.namespace} -l app=bounty-task")
    print("\nTo view logs for a specific job's pod (find pod name first):")
    print(f"  kubectl logs -n {args.namespace} <pod-name>")


if __name__ == '__main__':
    main()
