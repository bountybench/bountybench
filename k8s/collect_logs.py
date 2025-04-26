#!/usr/bin/env python3
"""
collect_logs.py: Fetch and archive log files from all pods in a given Kubernetes namespace.
"""
import argparse
import datetime
import os
import subprocess
from kubernetes import client, config

def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect pod logs from namespace and archive them locally and in-pod"
    )
    parser.add_argument(
        '--namespace', '-n', required=True,
        help='Kubernetes namespace to collect logs from'
    )
    parser.add_argument(
        '--output-dir', '-o', default='collected_logs',
        help='Local base directory for collected logs'
    )
    parser.add_argument(
        '--archive-path', default='/app/logs_archive',
        help='In-pod path to move logs after collection'
    )
    return parser.parse_args()


def main():
    args = parse_args()
    # timestamp for snapshot
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    # local base folder: output-dir/namespace/timestamp/
    base_local = os.path.join(args.output_dir, args.namespace, ts)
    os.makedirs(base_local, exist_ok=True)

    # load kubeconfig and list pods
    config.load_kube_config()
    core = client.CoreV1Api()
    pods = core.list_namespaced_pod(namespace=args.namespace).items

    for pod in pods:
        pod_name = pod.metadata.name
        pod_local = os.path.join(base_local, pod_name)
        os.makedirs(pod_local, exist_ok=True)

        # copy /app/logs from container 'backend'
        dest = os.path.join(pod_local, 'logs')
        os.makedirs(dest, exist_ok=True)
        cmd = [
            'kubectl', 'cp',
            f"{args.namespace}/{pod_name}:/app/logs", dest,
            '-c', 'backend', '-n', args.namespace
        ]
        print(f"Copying logs from pod {pod_name} to {dest}...")
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"ERROR copying logs from {pod_name}: {e.stderr.decode()}")
            continue

        # organize by extension
        log_dir = os.path.join(pod_local, 'logs_files')
        json_dir = os.path.join(pod_local, 'json_files')
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)
        for f in os.listdir(dest):
            src = os.path.join(dest, f)
            if f.endswith('.json'):
                os.rename(src, os.path.join(json_dir, f))
            elif f.endswith('.log'):
                os.rename(src, os.path.join(log_dir, f))

        # in-pod archive: move logs to archive-path/ts
        remote_archive = args.archive_path.rstrip('/') + '/' + ts
        archive_cmd = (
            f"mkdir -p {remote_archive} && mv /app/logs/* {remote_archive}/"
        )
        cmd2 = [
            'kubectl', 'exec', pod_name,
            '-n', args.namespace,
            '-c', 'backend', '--',
            'sh', '-c', archive_cmd
        ]
        print(f"Archiving logs inside pod {pod_name} -> {remote_archive}...")
        try:
            subprocess.run(cmd2, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"ERROR archiving logs in {pod_name}: {e.stderr.decode()}")

    print(f"\nDone. Collected logs are under {base_local}")


if __name__ == '__main__':
    main()
