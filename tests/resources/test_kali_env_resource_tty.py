import shutil
import tempfile
from pathlib import Path

import pytest

from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig

VOLUME = {
    Path(__file__).parent.resolve() / "test_files": {"bind": "/app/", "mode": "rw"}
}
CONTAINER_NAME = "test_container"


@pytest.fixture(scope="class")
def kali_env_resource():
    temp_dir = tempfile.mkdtemp()
    test_files_dir = Path(temp_dir)
    print(f"Created temporary test directory: {test_files_dir}")

    test_file_path = test_files_dir / "test.txt"
    with open(test_file_path, "w") as f:
        f.write("TEST{RANDOM_WORDS}")

    volume = {str(test_files_dir): {"bind": "/app", "mode": "rw"}}

    resource = KaliEnvResource(
        resource_id=CONTAINER_NAME, config=KaliEnvResourceConfig(volumes=volume)
    )
    yield resource
    resource.stop()
    shutil.rmtree(temp_dir)
    print(f"Removed temporary test directory: {temp_dir}")


def test_run_simple_command_tty(kali_env_resource):
    command = "echo Hello\n"
    stdout, _ = kali_env_resource.run_command(command, tty=True)
    assert stdout.strip() == "Hello\n$"


def test_run_multiple_command_tty(kali_env_resource):
    command = "echo Hello\necho Hello\n"
    stdout, _ = kali_env_resource.run_command(command, tty=True)
    assert stdout.strip() == "Hello\n$"


def test_run_simple_command_and_del_tty(kali_env_resource):
    command = "echo Hello\necho Hello\x7f\n"
    stdout, _ = kali_env_resource.run_command(command, tty=True)
    assert stdout.strip() == "Hell\n$"


def test_run_enter_python_tty(kali_env_resource):
    kali_env_resource.run_command("python -i\n", tty=True)
    stdout, _ = kali_env_resource.run_command("1 + 1\n", tty=True)
    assert stdout.strip() == "2\n>>>"
    stdout, _ = kali_env_resource.run_command("2 + 2\n", tty=True)
    assert stdout.strip() == "4\n>>>"
    stdout, _ = kali_env_resource.run_command("exit()\n", tty=True)
    assert stdout.strip() == "$"


def test_run_enter_python_and_create_file(kali_env_resource):
    file_path = "py_test.txt"
    kali_env_resource.run_command("python -i\n", tty=True)
    kali_env_resource.run_command("f = open('py_test.txt', 'w')\n", tty=True)
    stdout, _ = kali_env_resource.run_command("f.write('Hello')\n", tty=True)
    assert stdout.strip() == "5\n>>>"
    kali_env_resource.run_command("exit()\n", tty=True)
    stdout, _ = kali_env_resource.run_command(f"cat {file_path}\n", tty=True)
    assert stdout.strip() == "Hello\n$"


def test_container_persistence_tty(kali_env_resource):
    file_path = "persistent_testfile.txt"
    kali_env_resource.run_command(f"touch {file_path}\n", tty=True)
    stdout, _ = kali_env_resource.run_command(
        f"test -f {file_path} && echo Exists\n", tty=True
    )
    assert stdout.strip() == "Exists\n$"
    kali_env_resource.run_command(f"rm {file_path}\n", tty=True)
    stdout, _ = kali_env_resource.run_command(
        f"test -f {file_path} && echo Exists\n", tty=True
    )
    assert stdout.strip() == "$"


def test_command_with_timeout_tty(kali_env_resource):
    stdout, _ = kali_env_resource.run_command("sleep 120\n", timeout=1, tty=True)
    assert "timed out after 1 seconds" in stdout
    kali_env_resource.run_command("\x03\n", tty=True)
