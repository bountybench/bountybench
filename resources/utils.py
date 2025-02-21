import html
import json
import os
import subprocess
import sys
from typing import List, Union

from bs4 import BeautifulSoup

from utils.logger import get_main_logger

logger = get_main_logger(__name__)


def run_command(command, work_dir=None):
    """
    Runs a shell command while capturing output in real-time.

    :param command: List of command arguments.
    :param work_dir: Working directory to execute the command in.
    :return: stdout and stderr as strings.
    """
    try:
        process = subprocess.Popen(
            command,
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Ensures line buffering for real-time output
            universal_newlines=True,
        )

        stdout_lines = []
        stderr_lines = []

        # Read output in real-time
        for stdout_line in iter(process.stdout.readline, ""):
            sys.stdout.write(stdout_line)  # Print to console immediately
            sys.stdout.flush()  # Force immediate print
            stdout_lines.append(stdout_line)  # Store in variable

        for stderr_line in iter(process.stderr.readline, ""):
            sys.stderr.write(stderr_line)  # Print errors to console immediately
            sys.stderr.flush()  # Force immediate print
            stderr_lines.append(stderr_line)  # Store in variable

        process.stdout.close()
        process.stderr.close()
        process.wait()  # Ensure process completes

        return subprocess.CompletedProcess(
            args=command,
            returncode=process.returncode,
            stdout="".join(stdout_lines),
            stderr="".join(stderr_lines),
        )

    except subprocess.CalledProcessError as e:
        logger.error(
            f"Command '{' '.join(command)}' failed with return code {e.returncode}"
        )
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        raise


def docker_network_exists(network_name):
    """
    Checks if a Docker network exists.
    """
    logger.info(f"Checking if Docker network '{network_name}' exists.")
    result = subprocess.run(
        [
            "docker",
            "network",
            "ls",
            "--filter",
            f"name=^{network_name}$",
            "--format",
            "{{.Name}}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    exists = network_name in result.stdout.splitlines()
    if exists:
        logger.info(f"Docker network '{network_name}' already exists.")
    else:
        logger.info(f"Docker network '{network_name}' does not exist.")
    return exists


def read_repo_metadata(task_dir: str) -> dict[str, Union[str, dict]]:
    repo_metadata_file_path = os.path.join(task_dir, "metadata.json")
    if not os.path.exists(repo_metadata_file_path):
        logger.error("Repository metadata file not found")
        sys.exit(1)

    with open(repo_metadata_file_path, "r") as metadata_file:
        repo_metadata = json.load(metadata_file)

    return repo_metadata


def read_bounty_metadata(
    task_dir: str, bounty_number: str
) -> dict[str, Union[str, dict]]:
    bounty_metadata_file_path = os.path.join(
        task_dir + "/bounties/bounty_" + bounty_number, "bounty_metadata.json"
    )
    if not os.path.exists(bounty_metadata_file_path):
        logger.error("Bounty metadata file not found")
        sys.exit(1)

    with open(bounty_metadata_file_path, "r") as metadata_file:
        bounty_metadata = json.load(metadata_file)

    return bounty_metadata


def read_writeup(task_dir: str, bounty_number: str) -> str:
    bounty_dir = os.path.join("bounties", f"bounty_{bounty_number}")
    report_path = os.path.join(task_dir, bounty_dir, "writeup", "writeup.html")
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            writeup = f.read()
            writeup = format_writeup(writeup)
    except FileNotFoundError:
        logger.warning(f"Writeup not found at: {report_path}")
        writeup = ""
    return writeup


def get_stdout_text(process_output: bytes) -> str:
    """
    Decode the process output from bytes to a UTF-8 string.

    Args:
        process_output (bytes): The output to decode.

    Returns:
        str: The decoded string or an error message if decoding fails.
    """
    stdout: str = ""
    if process_output is None:
        return stdout
    try:
        stdout = process_output.decode("utf-8")
        return stdout
    except UnicodeDecodeError as e:
        stdout = (
            "This failed to decode. Remember: the problem is fully solvable using UTF-8 encoding. "
            "Ignore any images (jpeg, png, etc.), videos (mp4, mpeg) etc. "
            f"Error: {str(e)}"
        )


def parse_shell_script(script_path: str) -> List[str]:
    """
    Parse a shell script into individual commands.
    Args:
        script_path (str): Path to the shell script.
    Returns:
        List[str]: A list of commands to execute.
    """
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Shell script not found at {script_path}")

    commands = []
    with open(script_path, "r") as script_file:
        for idx, line in enumerate(script_file, start=1):
            # Remove leading/trailing whitespace
            stripped_line = line.strip()

            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith("#"):
                continue

            # Add command to the list (assuming one command per line)
            commands.append(stripped_line)

    return commands


def format_writeup(writeup: str) -> str:
    soup = BeautifulSoup(writeup, "html.parser")

    formatted_content = ["======================", "Writeup:\n"]

    # Title and status
    title = soup.find("h1", id="title")
    if title:
        formatted_content.append("Title:")
        formatted_content.append(title.text.strip())
        status_span = soup.find("span", class_="mr-1 text-xs font-medium")
        if status_span:
            formatted_content.append(status_span.text.strip())
        report_date = soup.find("p", class_="ml-3 mt-1 self-center text-xs font-medium")
        if report_date:
            formatted_content.append(report_date.text.strip())
        formatted_content.append("")

    # Description and Proof of Concept
    markdown_body = soup.find("div", class_="markdown-body")
    if markdown_body:
        for child in markdown_body.children:
            if child.name == "h1":
                formatted_content.append(f"\n{child.text}:")
            elif child.name in ["p", "pre"]:
                formatted_content.append(html.unescape(child.text.strip()))
            elif child.name == "ul":
                for li in child.find_all("li"):
                    formatted_content.append(f"- {li.text.strip()}")
    formatted_content.append("======================")
    writeup = "\n".join(formatted_content)
    return writeup


def contains_setup(setup_resource_file_path):
    if os.path.exists(setup_resource_file_path):
        with open(setup_resource_file_path, "r") as file:
            for line in file:
                # Remove leading and trailing whitespace
                stripped_line = line.strip()

                # Skip empty lines and comments
                if stripped_line and not stripped_line.startswith("#"):
                    return True
    return False
