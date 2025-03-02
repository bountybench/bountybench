import os

import yaml


def read_env_file(directory):
    env_path = os.path.join(directory, ".env")
    if not os.path.exists(env_path):
        env_path = os.path.join(directory, "env")
    env_vars = {}

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


def get_localhosts(docker_compose_path):
    try:
        with open(docker_compose_path, "r") as f:
            docker_compose = yaml.safe_load(f)

        localhosts = set()
        services = docker_compose.get("services", {})
        env_vars = read_env_file(os.path.dirname(docker_compose_path))

        for service in services.values():
            ports = service.get("ports", [])
            for port in ports:
                if isinstance(port, str):
                    parts = port.split(":")
                    if len(parts) == 2:
                        right_port = parts[1].split("/")[0]
                    elif len(parts) == 1:
                        right_port = parts[0].split("/")[0]
                    else:
                        continue

                    # Check for environment variables
                    if right_port.startswith("${") and right_port.endswith("}"):
                        var_name = right_port[2:-1]
                        if var_name in env_vars:
                            right_port = env_vars[var_name]
                        else:
                            right_port = (
                                f"${{{var_name}}}"  # Keep original if not found
                            )

                    localhosts.add(right_port)

        return sorted(localhosts)
    except Exception as e:
        print(f"Error processing {docker_compose_path}: {str(e)}")
        return []


def find_docker_compose_files(base_dir):
    for root, dirs, files in os.walk(base_dir):
        if "codebase" in dirs:
            dirs.remove("codebase")  # don't recurse into 'codebase' directory

        for file in files:
            if file in ["docker-compose.yml", "docker-compose.yaml"]:
                yield os.path.join(root, file)


def get_ports_for_directory(directory, print_names: bool = False):
    all_localhosts = []
    for docker_compose_path in find_docker_compose_files(directory):
        localhosts = get_localhosts(docker_compose_path)
        all_localhosts.extend(localhosts)

        if print_names and localhosts:
            # Get the relative path from the base directory
            rel_path = os.path.relpath(os.path.dirname(docker_compose_path), directory)
            if rel_path == ".":
                rel_path = os.path.basename(directory)
            print(f"{', '.join(localhosts)} - {rel_path}")

    return all_localhosts


def get_all_ports(print_names: bool = False):
    # Get the directory of the script file
    base_dir = "bountybench"
    ports = get_ports_for_directory(base_dir, print_names)
    print(ports)


def main():
    get_all_ports(True)


if __name__ == "__main__":
    main()
