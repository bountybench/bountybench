import asyncio
import os
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
