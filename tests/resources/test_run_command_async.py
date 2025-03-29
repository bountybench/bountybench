import asyncio
import os
import sys
import tempfile
import time

import pytest

from resources.utils import run_command_async


@pytest.mark.asyncio
async def test_run_command_async():
    # Test with a simple command
    result = await run_command_async(["echo", "Hello World"])
    assert result.returncode == 0
    assert "Hello World" in result.stdout

    # Test with a command that produces stderr
    result = await run_command_async(["ls", "/nonexistent_directory"])
    assert result.returncode != 0
    assert "No such file or directory" in result.stderr

    # Test with a directory
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Run ls in that directory
        result = await run_command_async(["ls"], work_dir=temp_dir)
        assert result.returncode == 0
        assert "test.txt" in result.stdout

    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, "test_script.sh")
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\nsleep 1\necho Done\n")
        os.chmod(script_path, 0o755)

        result = await run_command_async([script_path])
        assert result.returncode == 0
        assert "Done" in result.stdout


@pytest.mark.asyncio
async def test_concurrent_commands():
    start_time = time.time()

    # Create two tasks that each sleep for 1 second
    # If they run sequentially, this would take 2 seconds
    # If concurrent, should take just over 1 second
    task1 = run_command_async(["sleep", "1"])
    task2 = run_command_async(["sleep", "1"])

    # Wait for both to complete
    results = await asyncio.gather(task1, task2)

    elapsed = time.time() - start_time

    # Should take just over 1 second if concurrent
    assert elapsed < 1.5, f"Commands did not run concurrently (took {elapsed} seconds)"
    assert results[0].returncode == 0
    assert results[1].returncode == 0


@pytest.mark.asyncio
async def test_output_streaming():
    """Test that output is streamed in real-time rather than buffered."""

    # Create a temporary script that outputs lines with deliberate delays
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, "incremental_output.sh")
        with open(script_path, "w") as f:
            f.write(
                """#!/bin/bash
echo "Line 1"
sleep 0.5
echo "Line 2"
sleep 0.5
echo "Line 3" >&2
sleep 0.5
echo "Line 4"
sleep 0.5
echo "Line 5" >&2
"""
            )
        os.chmod(script_path, 0o755)

        # Capture timing of output arrival
        output_times = []
        original_stdout_write = sys.stdout.write
        original_stderr_write = sys.stderr.write

        def stdout_monitor(text):
            """Capture when output arrives at stdout."""
            output_times.append((time.time(), "stdout", text.strip()))
            return original_stdout_write(text)

        def stderr_monitor(text):
            """Capture when output arrives at stderr."""
            output_times.append((time.time(), "stderr", text.strip()))
            return original_stderr_write(text)

        # Patch stdout/stderr to monitor when output arrives
        sys.stdout.write = stdout_monitor
        sys.stderr.write = stderr_monitor

        start_time = time.time()

        try:
            # Run the script, which should produce output with delay between lines
            result = await run_command_async([script_path])

            # Restore stdout/stderr
            sys.stdout.write = original_stdout_write
            sys.stderr.write = original_stderr_write

            # Verify the command completed correctly
            assert result.returncode == 0
            assert "Line 1" in result.stdout
            assert "Line 2" in result.stdout
            assert "Line 4" in result.stdout
            assert "Line 3" in result.stderr
            assert "Line 5" in result.stderr

            # Analyze timing to confirm streaming behavior
            # First, filter out empty lines
            actual_outputs = [item for item in output_times if item[2]]

            # Verify we have at least 5 output events
            assert (
                len(actual_outputs) >= 5
            ), f"Expected at least 5 output events, got {len(actual_outputs)}"

            # Calculate time differences between first and last outputs
            time_span = actual_outputs[-1][0] - actual_outputs[0][0]

            # If output is streamed, time_span should be close to 2 seconds (4 sleep periods)
            # If buffered, it would be close to 0
            assert (
                time_span >= 1.5
            ), f"Output appeared too quickly ({time_span}s), suggesting it was buffered, not streamed"

            # Print actual output timing for debugging
            print("\nOutput timing (seconds since start, stream, content):")
            for timestamp, stream, content in actual_outputs:
                print(f"{timestamp - start_time:.3f}s - {stream}: {content}")

        finally:
            # Make sure we restore stdout/stderr even if the test fails
            sys.stdout.write = original_stdout_write
            sys.stderr.write = original_stderr_write
