#!/usr/bin/env python3
"""
experiment_deployer.py: Deploy experiment pods on GKE using StatefulSets and execute tasks defined in JSON configs.
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
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException
from concurrent.futures import ThreadPoolExecutor, as_completed
from kubernetes.client import V1Namespace, V1ObjectMeta, V1EphemeralContainer, V1VolumeMount, V1SecurityContext, V1Pod, V1PodSpec


def parse_config(config_path):
    """
    Read a JSON experiment config and produce a list of runner commands.
    """
    with open(config_path) as f:
        cfg = json.load(f)
    required = [
        'workflow_type', 'phase_iterations', 'use_helm',
        'model', 'max_input_tokens', 'max_output_tokens', 'tasks'
    ]
    for key in required:
        if key not in cfg:
            print(f"Missing key '{key}' in {config_path}", file=sys.stderr)
            sys.exit(1)

    workflow = cfg['workflow_type']
    phase_iter = cfg['phase_iterations']
    use_helm = cfg['use_helm']
    model = cfg['model']
    max_in = cfg['max_input_tokens']
    max_out = cfg['max_output_tokens']
    tasks = cfg['tasks']

    commands = []
    for entry in tasks:
        if '/' in entry:
            task_dir, bounty = entry.split('/', 1)
            task_dir = f"bountybench/{task_dir}"
        else:
            print(f"Invalid task entry '{entry}'", file=sys.stderr)
            sys.exit(1)
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
        commands.append(' '.join(parts))
    return commands, cfg


def load_yaml_template(template_path):
    with open(template_path) as f:
        return list(yaml.safe_load_all(f))


def generate_yaml_objects(template_objs, name):
    """
    Given loaded YAML docs (Deployment + Service), clone and patch them for a group name.
    Convert Deployment->StatefulSet.
    """
    new_objs = []
    for obj in template_objs:
        new_obj = copy.deepcopy(obj)
        kind = new_obj.get('kind')
        metadata = new_obj.setdefault('metadata', {})
        spec = new_obj.setdefault('spec', {})

        if kind == 'Deployment':
            # switch to StatefulSet
            new_obj['kind'] = 'StatefulSet'
            metadata['name'] = name
            spec['serviceName'] = name
            spec['replicas'] = 1
            sel = spec.setdefault('selector', {}).setdefault('matchLabels', {})
            sel['app'] = name
            tmpl = spec.setdefault('template', {})
            lbls = tmpl.setdefault('metadata', {}).setdefault('labels', {})
            lbls['app'] = name

        elif kind == 'Service':
            metadata['name'] = f"{name}-svc"
            sel = spec.setdefault('selector', {})
            sel['app'] = name

        new_objs.append(new_obj)
    return new_objs


def apply_yaml(objs, output_file=None, namespace="default"):
    yaml_str = yaml.safe_dump_all(objs)
    if output_file:
        with open(output_file, 'w') as f:
            f.write(yaml_str)
        print(f"Generated YAML file: {output_file}")
    result = subprocess.run([
        'kubectl', 'apply', '-n', namespace, '-f', '-'
    ], input=yaml_str, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Failed to apply Kubernetes resources: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


def sanitize_name(raw: str) -> str:
    """Convert raw string to RFC 1123-compliant name."""
    name = raw.lower()
    # replace invalid chars with hyphens
    name = re.sub(r'[^a-z0-9-]+', '-', name)
    # strip leading/trailing hyphens
    name = re.sub(r'(^-+|-+$)', '', name)
    return name


def wait_for_pod_ready(api, label, namespace='default', timeout=600):
    """
    Wait for the specific StatefulSet pod '<label>-0' to be running and ready.
    """
    pod_name = f"{label}-0"
    deadline = time.time() + timeout
    print(f"Waiting for pod named '{pod_name}' in namespace '{namespace}'...")
    while time.time() < deadline:
        try:
            pod = api.read_namespaced_pod(name=pod_name, namespace=namespace)
        except ApiException:
            # Pod not yet created or not found
            time.sleep(5)
            continue
        if pod.status.phase == 'Running':
            statuses = pod.status.container_statuses or []
            if all(s.ready for s in statuses):
                print(f"Pod {pod.metadata.name} is ready")
                return pod.metadata.name
        time.sleep(5)
    print(f"Timeout waiting for pod {pod_name}", file=sys.stderr)
    sys.exit(1)


def exec_command(api, pod_name, command, namespace='default'):
    print(f"Running '{command}' in pod {pod_name}")
    try:
        resp = stream(
            api.connect_get_namespaced_pod_exec,
            name=pod_name,
            namespace=namespace,
            command=['sh', '-c', command],
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False
        )
        return resp
    except ApiException as e:
        print(f"Exec failed: {e}", file=sys.stderr)
        return ''


def pull_image(api, pod_name, namespace):
    deadline = time.time() + 300
    print(f"Pulling image in pod {pod_name} (waiting for Docker)...")
    while time.time() < deadline:
        try:
            info = exec_command(api, pod_name, "docker info", namespace)
        except Exception as e:
            print(f"Error checking Docker in {pod_name}: {e}, retrying...", file=sys.stderr)
            time.sleep(5)
            continue
        if "Server Version:" in info:
            break
        time.sleep(5)
    else:
        raise RuntimeError(f"Docker daemon not ready in pod {pod_name} after timeout")
    return exec_command(api, pod_name, "docker pull --quiet cybench/bountyagent:latest && docker network create shared_net", namespace)


def run_tasks_ephemeral(api, pod_name, namespace, info):
    """
    Spawn ephemeral containers via kubectl patch subresource, one per task.
    """
    patch_items = []
    for entry, cmd in zip(info['meta']['tasks'], info['cmds']):
        task, bounty = entry.split('/', 1)
        parts = [info['meta']['model'], info['meta']['workflow_type'], task, bounty]
        safe = sanitize_name('-'.join(parts))
        log_name = f"{safe}-{info['timestamp']}"
        # container name <=63 chars
        short = hashlib.sha1(log_name.encode()).hexdigest()[:8]
        epi_name = f"run-{short}"

        # Command for the actual task, logging its output
        task_cmd_log = f"mkdir -p /app/logs && {cmd} > /app/logs/{log_name}.log 2>&1"

        spec = {
            "name": epi_name,
            "image": "us-west1-docker.pkg.dev/soe-ai-cyber/bountyagent/backend-image:exp",
            "envFrom": [{"secretRef": {"name": "app-secrets"}}],
            # Command is just the task now, using shared Docker socket
            "command": ["sh", "-c", task_cmd_log],
            # No longer needs privileged context just to run docker client
            # "securityContext": {"privileged": True},
            "volumeMounts": [
                # Mount the shared Docker socket volume
                {"name": "docker-sock-volume", "mountPath": "/var/run"},
                {"name": "logs", "mountPath": "/app/logs"}
            ]
        }
        patch_items.append(spec)
    # merge-patch the ephemeralContainers subresource
    patch_body = {"spec": {"ephemeralContainers": patch_items}}
    subprocess.run([
        'kubectl', 'patch', 'pod', pod_name, '-n', namespace,
        '--subresource=ephemeralcontainers',
        '-p', json.dumps(patch_body)
    ], check=True)
    print(f"Spawned {len(patch_items)} ephemeral container(s) in pod {pod_name}")


def deploy_and_wait(config_path, tmpl_objs, api, namespace, timestamp):
    raw_name = Path(config_path).stem
    group_name = sanitize_name(raw_name)
    print(f"\n=== Group: {group_name} ===")
    cmds, meta = parse_config(config_path)
    objs = generate_yaml_objects(tmpl_objs, group_name)
    apply_yaml(objs, f"{group_name}.yaml", namespace)
    pod_name = wait_for_pod_ready(api, group_name, namespace)
    return {'group_name': group_name, 'pod_name': pod_name, 'cmds': cmds, 'meta': meta, 'timestamp': timestamp}


def main():
    parser = argparse.ArgumentParser(
        description="Deploy experiments on GKE and run tasks"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--configs', nargs='+', help='JSON experiment config files'
    )
    group.add_argument(
        '--all', action='store_true', help='Use all configs in experiment-config dir'
    )
    parser.add_argument(
        '--template',
        default=str(Path(__file__).parent / 'backend_exp.yaml'),
        help='Path to Deployment+Service YAML template'
    )
    parser.add_argument(
        '--namespace', default='default', help='Kubernetes namespace'
    )
    args = parser.parse_args()

    if args.all:
        base = Path(__file__).parent / 'experiment-config'
        configs = sorted(glob.glob(str(base / 'experiment_config_*.json')))
        # exclude placeholder template files
        configs = [c for c in configs if 'template' not in Path(c).stem]
    else:
        configs = args.configs

    try:
        config.load_kube_config()
    except Exception as e:
        print(f"Could not load kubeconfig: {e}", file=sys.stderr)
        sys.exit(1)

    core_api = client.CoreV1Api()
    try:
        core_api.read_namespace(name=args.namespace)
    except ApiException as e:
        if e.status == 404:
            ns = V1Namespace(metadata=V1ObjectMeta(name=args.namespace))
            core_api.create_namespace(body=ns)
            print(f"Created namespace '{args.namespace}'")
        else:
            print(f"Error checking namespace: {e}", file=sys.stderr)
            sys.exit(1)

    # Ensure 'app-secrets' exists in namespace
    print(f"Creating/updating secret 'app-secrets' in namespace {args.namespace} from ../.env")
    try:
        sec = subprocess.run([
            'kubectl', 'create', 'secret', 'generic', 'app-secrets',
            '--from-env-file=../.env', '--dry-run=client', '-o', 'yaml',
            '-n', args.namespace
        ], text=True, capture_output=True, check=True)
        subprocess.run([
            'kubectl', 'apply', '-f', '-'
        ], input=sec.stdout, text=True, check=True)
        print("Secret 'app-secrets' created/updated")
    except subprocess.CalledProcessError as e:
        print(f"Warning: failed to create secret: {e.stderr}", file=sys.stderr)

    try:
        tmpl_objs = load_yaml_template(args.template)
    except FileNotFoundError:
        print(f"Template not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # Phase 1: deploy groups and wait for pods
    deploy_infos = []
    with ThreadPoolExecutor(max_workers=len(configs)) as deploy_executor:
        futures = {deploy_executor.submit(deploy_and_wait, cfg, tmpl_objs, core_api, args.namespace, timestamp): cfg for cfg in configs}
        for fut in as_completed(futures):
            cfg = futures[fut]
            try:
                info = fut.result()
                deploy_infos.append(info)
                print(f"Group '{info['group_name']}' deployed and pod ready")
            except Exception as e:
                print(f"Group '{Path(cfg).stem}' failed in deploy phase: {e}", file=sys.stderr)
                sys.exit(1)

    # Phase 2: pull images in parallel
    with ThreadPoolExecutor(max_workers=len(deploy_infos)) as pull_executor:
        pull_futs = {pull_executor.submit(pull_image, core_api, info['pod_name'], args.namespace): info for info in deploy_infos}
        for fut in as_completed(pull_futs):
            info = pull_futs[fut]
            try:
                fut.result()
                print(f"Pulled image in pod {info['pod_name']}")
            except Exception as e:
                print(f"Failed pulling image in {info['pod_name']}: {e}", file=sys.stderr)
                sys.exit(1)

    # Phase 3: spawn ephemeral containers for tasks
    def _spawn(info):
        run_tasks_ephemeral(core_api, info['pod_name'], args.namespace, info)

    with ThreadPoolExecutor(max_workers=len(deploy_infos)) as eph_executor:
        futures = {eph_executor.submit(_spawn, info): info for info in deploy_infos}
        for fut in as_completed(futures):
            info = futures[fut]
            try:
                fut.result()
                print(f"Tasks started as ephemeral containers in pod {info['pod_name']}")
            except Exception as e:
                print(f"Failed spawning ephemeral containers in pod {info['pod_name']}: {e}", file=sys.stderr)
                sys.exit(1)

    print("\nAll experiment groups deployed and tasks executed.")


if __name__ == '__main__':
    main()
