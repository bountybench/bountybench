from typing import Optional


def truncate_script_output(
    stdout: str, stderr: Optional[str] = "", max_length: int = 5000
) -> str:
    """
    Truncate script output to enforce max_length, keeping the most recent output

    Args:
        stdout: Standard output from script
        stderr: Standard error from script (optional)
        max_length: Maximum total length of the combined output

    Returns:
        Truncated combined output string
    """
    stdout = stdout.strip()
    stderr = stderr.strip()

    total_length = len(stdout) + len(stderr)
    truncation_indicator = "\n...TRUNCATED...\n"
    indicator_length = len(truncation_indicator)

    if total_length <= max_length:
        if stderr:
            return f"{stdout}\n\nSTDERR:\n{stderr}"
        return stdout

    if not stdout:
        truncated_stderr = (
            f"{truncation_indicator}{stderr[-(max_length - indicator_length):]}"
        )
        return f"STDERR:{truncated_stderr}"

    if not stderr:
        truncated_stdout = (
            f"{truncation_indicator}{stdout[-(max_length - indicator_length):]}"
        )
        return truncated_stdout

    stderr_prefix = "\n\nSTDERR:\n"

    if len(stderr) < max_length * 0.5:
        stderr_space = len(stderr)
        stdout_space = max_length - stderr_space
    elif len(stdout) < max_length * 0.5:
        stdout_space = len(stdout)
        stderr_space = max_length - stdout_space
    else:
        stdout_space = max_length // 2
        stderr_space = max_length - stdout_space

    truncated_stdout = stdout[-int(stdout_space) :]
    truncated_stderr = stderr[-int(stderr_space) :]

    return (
        f"{truncation_indicator}{truncated_stdout}{stderr_prefix}{truncated_stderr}"
    )
