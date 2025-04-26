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

import yaml
from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException
from concurrent.futures import ThreadPoolExecutor, as_completed
from kubernetes.client import V1Namespace, V1ObjectMeta


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
    selector = f"app={label}"
    deadline = time.time() + timeout
    print(f"Waiting for pod with label '{selector}'...")
    while time.time() < deadline:
        pods = api.list_namespaced_pod(
            namespace=namespace, label_selector=selector
        ).items
        if pods:
            pod = pods[0]
            if pod.status.phase == 'Running':
                statuses = pod.status.container_statuses or []
                if all(s.ready for s in statuses):
                    print(f"Pod {pod.metadata.name} is ready")
                    return pod.metadata.name
        time.sleep(5)
    print(f"Timeout waiting for pod ready for '{label}'", file=sys.stderr)
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


def process_group(config_path, tmpl_objs, core_api, namespace, timestamp):
    """Deploy one experiment group and run its commands in parallel."""
    raw_name = Path(config_path).stem
    group_name = sanitize_name(raw_name)
    print(f"\n=== Group: {group_name} ===")
    cmds, meta = parse_config(config_path)
    objs = generate_yaml_objects(tmpl_objs, group_name)
    apply_yaml(objs, f"{group_name}.yaml", namespace)
    pod_name = wait_for_pod_ready(core_api, group_name, namespace)
    # Detach each command inside the pod, logging via nohup to container's /app/logs/<fname>
    with ThreadPoolExecutor(max_workers=len(cmds)) as execer:
        future_to_fname = {}
        for entry, cmd in zip(meta['tasks'], cmds):
            task, bounty = entry.split('/', 1)
            # build a safe filename: sanitize each component
            parts = [meta['model'], meta['workflow_type'], task, bounty]
            safe_parts = [sanitize_name(p) for p in parts]
            fname = '-'.join(safe_parts + [timestamp]) + '.log'
            # ensure logs directory exists and start background process
            wrapped = f"mkdir -p /app/logs && nohup {cmd} > /app/logs/{fname} 2>&1 &"
            fut = execer.submit(exec_command, core_api, pod_name, wrapped, namespace)
            future_to_fname[fut] = fname
        for fut in as_completed(future_to_fname):
            fname = future_to_fname[fut]
            try:
                fut.result()
                print(f"Started background job; logs at /app/logs/{fname}")
            except Exception as e:
                print(f"Failed to start job for {fname}: {e}", file=sys.stderr)
    return group_name


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

    try:
        tmpl_objs = load_yaml_template(args.template)
    except FileNotFoundError:
        print(f"Template not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # Process all configuration groups in parallel
    with ThreadPoolExecutor(max_workers=len(configs)) as group_executor:
        future_map = {group_executor.submit(process_group, cfg, tmpl_objs, core_api, args.namespace, timestamp): cfg for cfg in configs}
        for fut in as_completed(future_map):
            cfg = future_map[fut]
            try:
                grp = fut.result()
                print(f"Group '{grp}' completed")
            except Exception as e:
                print(f"Group '{Path(cfg).stem}' failed: {e}", file=sys.stderr)

    print("\nAll experiment groups deployed and tasks executed.")


if __name__ == '__main__':
    main()
