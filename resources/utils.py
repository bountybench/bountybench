import asyncio
import html
import json
import select
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Union

from bs4 import BeautifulSoup

from utils.logger import get_main_logger

logger = get_main_logger(__name__)


def run_command(command, work_dir=None, verbose=True):
    """
    Runs a shell command while capturing output in real-time.

    :param command: List of command arguments.
    :param work_dir: Working directory to execute the command in.
    :param verbose: If True, prints stdout/stderr in real time.
    :return: subprocess.CompletedProcess with stdout and stderr as strings.
    """
    try:
        process = subprocess.Popen(
            command,
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        stdout_lines = []
        stderr_lines = []

        fds = [process.stdout, process.stderr]
        while process.poll() is None:
            readable, _, _ = select.select(fds, [], [], 0.1)
            for fd in readable:
                line = fd.readline()
                if line:
                    if fd == process.stdout:
                        if verbose:
                            sys.stdout.write(line)
                            sys.stdout.flush()
                        stdout_lines.append(line)
                    else:
                        if verbose:
                            sys.stderr.write(line)
                            sys.stderr.flush()
                        stderr_lines.append(line)

        # Flush remaining lines after process ends
        for fd in fds:
            for line in fd:
                if fd == process.stdout:
                    if verbose:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                    stdout_lines.append(line)
                else:
                    if verbose:
                        sys.stderr.write(line)
                        sys.stderr.flush()
                    stderr_lines.append(line)

        process.stdout.close()
        process.stderr.close()
        process.wait()

        return subprocess.CompletedProcess(
            args=command,
            returncode=process.returncode,
            stdout="".join(stdout_lines),
            stderr="".join(stderr_lines),
        )

    except PermissionError as e:
        logger.error(
            f"Command '{' '.join(command)}' failed with PermissionError {str(e)}"
        )
        if verbose:
            sys.stderr.write(f"Error executing command: {' '.join(command)}\n")
            sys.stderr.flush()
        raise

    except Exception as e:
        logger.error(f"Command '{' '.join(command)}' failed with exception: {e}")
        if hasattr(e, "stdout"):
            logger.error(f"stdout: {e.stdout}")
        if hasattr(e, "stderr"):
            logger.error(f"stderr: {e.stderr}")
        if verbose:
            sys.stderr.write(f"Error executing command: {' '.join(command)}\n")
            sys.stderr.flush()
        raise


async def run_command_async(command, work_dir=None, timeout=None, verbose=True):
    """
    Runs a shell command asynchronously while capturing output in real-time.

    :param command: List of command arguments.
    :param work_dir: Working directory to execute the command in.
    :param timeout: Optional timeout in seconds for the command to complete.
    :param verbose: If True, prints stdout/stderr in real time.
    :return: subprocess.CompletedProcess with stdout and stderr as strings.
    """
    try:
        # command needs to be in sequential format
        if isinstance(command, str):
            command = command.split()
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_lines = []
        stderr_lines = []

        # Define task to read from stdout
        async def read_stdout():
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line_str = line.decode("utf-8")
                if verbose:
                    sys.stdout.write(line_str)
                    sys.stdout.flush()
                stdout_lines.append(line_str)

        # Define task to read from stderr
        async def read_stderr():
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                line_str = line.decode("utf-8")
                if verbose:
                    sys.stderr.write(line_str)
                    sys.stderr.flush()
                stderr_lines.append(line_str)

        stdout_task = asyncio.create_task(read_stdout())
        stderr_task = asyncio.create_task(read_stderr())
        try:
            if timeout is not None:
                return_code = await asyncio.wait_for(process.wait(), timeout)
            else:
                return_code = await process.wait()

            # Run both reading tasks concurrently
            await asyncio.gather(
                stdout_task,
                stderr_task,
            )

            return subprocess.CompletedProcess(
                args=command,
                returncode=return_code,
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines),
            )
        except asyncio.TimeoutError:
            process.kill()
            stdout_task.cancel()
            stderr_task.cancel()
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

            return subprocess.CompletedProcess(
                args=command,
                returncode=-1,  # Using returncode -1 to indicate timeout
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines)
                + (f"\nCommand timed out after {timeout} seconds" if timeout else ""),
            )
        finally:
            if process and process.returncode is None:
                try:
                    process.kill()
                    await asyncio.sleep(0.1)  # Allow time for resources to be released
                except Exception:
                    pass

    except PermissionError as e:
        logger.error(f"Command '{' '.join(command)}' failed with PermissionError {e}")
        if verbose:
            sys.stderr.write(f"Error executing command: {' '.join(command)}\n")
            sys.stderr.flush()
        raise

    except Exception as e:
        logger.error(
            f"Command '{''.join(command)}' failed with return code {e.returncode}"
        )
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        sys.stderr.write(f"Error executing command: {''.join(command)}\n")
        sys.stderr.flush()
        raise


def docker_network_exists(network_name):
    """
    Checks if a Docker network exists.
    """
    logger.debug(f"Checking if Docker network '{network_name}' exists.")
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
        logger.debug(f"Docker network '{network_name}' already exists.")
    else:
        logger.debug(f"Docker network '{network_name}' does not exist.")
    return exists


def read_repo_metadata(task_dir: Path) -> dict[str, Union[str, dict]]:
    repo_metadata_file_path = task_dir / "metadata.json"
    if not repo_metadata_file_path.exists():
        logger.error("Repository metadata file not found")
        raise RuntimeError("Repository metadata file not found")

    with repo_metadata_file_path.open("r") as metadata_file:
        repo_metadata = json.load(metadata_file)

    return repo_metadata


def read_bounty_metadata(
    task_dir: Path, bounty_number: str
) -> dict[str, Union[str, dict]]:
    bounty_metadata_file_path = (
        task_dir / "bounties" / f"bounty_{bounty_number}" / "bounty_metadata.json"
    )
    if not bounty_metadata_file_path.exists():
        logger.error("Bounty metadata file not found")
        raise RuntimeError("Bounty metadata file not found")

    with bounty_metadata_file_path.open("r") as metadata_file:
        bounty_metadata = json.load(metadata_file)

    return bounty_metadata


def read_writeup(task_dir: Path, bounty_number: str) -> str:
    report_path = (
        task_dir / "bounties" / f"bounty_{bounty_number}" / "writeup" / "writeup.html"
    )
    try:
        writeup = report_path.read_text(encoding="utf-8")
        # get url from metadata
        metadata_path = (
            task_dir / "bounties" / f"bounty_{bounty_number}" / "bounty_metadata.json"
        )
        url = None

        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    url = metadata.get("bounty_link", None)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading metadata file: {e}")

        # Use the URL to determine the format
        if url:
            if "huntr" in url:
                writeup = format_huntr_writeup(writeup)
            elif "hackerone" in url:
                writeup = format_hackerone_writeup(writeup)
            else:
                raise ValueError(
                    "Only huntr and hackerone bounty reports can currently be parsed."
                )
        else:
            # Default format or error handling if URL is not available
            print("Warning: Could not determine the bounty source from metadata.")
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


def parse_shell_script(script_path: Path) -> List[str]:
    """
    Parse a shell script into individual commands.
    Args:
        script_path (Path): Path to the shell script.
    Returns:
        List[str]: A list of commands to execute.
    """
    if not script_path.is_file():
        raise FileNotFoundError(f"Shell script not found at {script_path}")

    commands = []
    with script_path.open("r") as script_file:
        for idx, line in enumerate(script_file, start=1):
            # Remove leading/trailing whitespace
            stripped_line = line.strip()

            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith("#"):
                continue

            # Add command to the list (assuming one command per line)
            commands.append(stripped_line)

    return commands


def format_huntr_writeup(writeup: str) -> str:
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


def format_hackerone_writeup(writeup: str) -> str:
    soup = BeautifulSoup(writeup, "html.parser")

    formatted_content = ["======================", "Writeup:\n"]

    # Title and report number
    title_element = soup.find(
        "div",
        class_="false report-heading__report-title spec-report-title flex items-center",
    )
    if title_element:
        title_div = title_element.find("div", class_="break-word")
        if title_div:
            formatted_content.append("Title:")
            formatted_content.append(title_div.text.strip())

    # Get report ID
    report_status = soup.find("div", class_="report-status")
    if report_status:
        report_id = report_status.find("a", class_="report-status-indicator")
        if report_id:
            formatted_content.append(report_id.text.strip())

    # Get severity
    severity_element = soup.find("span", class_="severity-label__text")
    if severity_element:
        severity_rating = severity_element.find("span", class_="spec-severity-rating")
        if severity_rating:
            formatted_content.append(f"Severity: {severity_rating.text.strip()}")

    formatted_content.append("")

    # Get the summary content
    summary = soup.find("div", class_="spec-full-summary-content")
    if summary:
        formatted_content.append("Summary:")
        # Extract paragraphs from summary
        paragraphs = summary.find_all(
            "div", class_="vertical-spacing interactive_markdown__p"
        )
        for p in paragraphs:
            formatted_content.append(html.unescape(p.text.strip()))
        formatted_content.append("")

    # Get vulnerability information
    vuln_info = soup.find("div", class_="spec-vulnerability-information")
    if vuln_info:
        formatted_content.append("Vulnerability Information:")
        # Extract paragraphs from vulnerability info
        paragraphs = vuln_info.find_all(
            "div", class_="vertical-spacing interactive_markdown__p"
        )
        for p in paragraphs:
            formatted_content.append(html.unescape(p.text.strip()))

        # Extract code blocks
        code_blocks = vuln_info.find_all(
            "div", class_="interactive-markdown__code__content"
        )
        for code in code_blocks:
            formatted_content.append("\nCode:")
            code_lines = []
            for line in code.stripped_strings:
                if not line.isdigit():  # Skip line numbers
                    code_lines.append(line)
            formatted_content.append("\n".join(code_lines))
            formatted_content.append("")

    # Get Impact section if it exists
    impact_heading = (
        vuln_info.find("h2", id="user-content-impact") if vuln_info else None
    )
    if impact_heading:
        formatted_content.append("Impact:")
        next_element = impact_heading.find_next(
            "div", class_="vertical-spacing interactive_markdown__p"
        )
        if next_element:
            formatted_content.append(html.unescape(next_element.text.strip()))

    # Get bounty information
    bounty_element = soup.find("div", class_="spec-bounty-amount-meta-item")
    if bounty_element:
        bounty_value = bounty_element.find("span", class_="spec-amount-in-currency")
        if bounty_value:
            formatted_content.append(f"\nBounty: {bounty_value.text.strip()}")

    # Get CVE ID if exists
    cve_element = soup.find("div", class_="spec-cve-id-meta-item")
    if cve_element:
        cve_link = cve_element.find("a")
        if cve_link:
            formatted_content.append(f"CVE ID: {cve_link.text.strip()}")

    formatted_content.append("======================")
    writeup = "\n".join(formatted_content)
    return writeup


def contains_setup(setup_resource_file_path: Path):
    if setup_resource_file_path.exists():
        with setup_resource_file_path.open("r") as file:
            for line in file:
                # Remove leading and trailing whitespace
                stripped_line = line.strip()

                # Skip empty lines and comments
                if stripped_line and not stripped_line.startswith("#"):
                    return True
    return False
