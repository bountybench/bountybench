import shutil
import tempfile
import time
import unittest
from pathlib import Path

from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig

VOLUME = {
    Path(__file__).parent.resolve() / "test_files": {"bind": "/app/", "mode": "rw"}
}
CONTAINER_NAME = "test_container"


class TestKaliEnvResource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        This method initializes the KaliEnvResource instance, starts a single container,
        creates the test file with appropriate permissions, and ensures the volume is mounted.
        """
        # Create a temporary directory

        cls.temp_dir = tempfile.mkdtemp()
        cls.test_files_dir = Path(cls.temp_dir)
        print(f"Created temporary test directory: {cls.test_files_dir}")

        cls.test_file_path = cls.test_files_dir / "test.txt"
        with open(cls.test_file_path, "w") as f:
            f.write("TEST{RANDOM_WORDS}")

        cls.VOLUME = {str(cls.test_files_dir): {"bind": "/app", "mode": "rw"}}

        cls.kali_env_resource = KaliEnvResource(
            resource_id=CONTAINER_NAME, config=KaliEnvResourceConfig(volumes=cls.VOLUME)
        )

    @classmethod
    def tearDownClass(cls):
        """
        This method is run once for the class after all tests are executed.
        It cleans up by stopping the Docker container.
        """
        cls.kali_env_resource.stop()

        # Remove the temporary directory and its contents
        shutil.rmtree(cls.temp_dir)
        print(f"Removed temporary test directory: {cls.temp_dir}")

    def test_run_simple_command(self):
        """
        Test running a simple command (e.g., `echo Hello`).
        The output should be the same as the echoed message.
        """
        command = "echo Hello"
        stdout, stderr = self.kali_env_resource.run_command(command)
        self.assertEqual(stdout.strip(), "Hello")
        self.assertEqual(stderr.strip(), "")

    def test_run_multiple_commands(self):
        """
        Test running multiple commands (e.g., `echo Hello; echo World`).
        The output should be the same as the echoed messages.
        """
        command = "echo Hello\n echo World"
        stdout, stderr = self.kali_env_resource.run_command(command)
        self.assertEqual(stdout.strip(), "Hello\nWorld")
        self.assertEqual(stderr.strip(), "")

    def test_command_with_error(self):
        """
        Test running a command that produces an error.
        The stderr should contain the error message.
        """
        command = "ls /nonexistent_directory"
        stdout, stderr = self.kali_env_resource.run_command(command)
        self.assertEqual(stdout.strip(), "")
        self.assertIn("No such file or directory", stderr)

    def test_command_with_volume(self):
        """
        Test running a command that reads a file from the volume.
        The output should be the same as the content of the file.
        """
        file_path = "/app/test.txt"
        command = f"ls -l /app && cat {file_path}"
        stdout, stderr = self.kali_env_resource.run_command(command)
        print(f"Command output: {stdout}")
        print(f"Command error: {stderr}")
        self.assertIn(r"TEST{RANDOM_WORDS}", stdout.strip())
        self.assertEqual(stderr, "")

    def test_command_with_timeout(self):
        """
        Test running a command that will take too long to complete.
        The command should be terminated due to timeout.
        """
        command = "sleep 120"
        stdout, stderr = self.kali_env_resource.run_command(command, timeout=2)
        self.assertIn("timed out after 2 seconds", stdout)
        self.assertEqual(stderr.strip(), "")

    def test_working_directory(self):
        """
        Test running a command in a specific working directory.
        """
        command = "pwd"
        workdir = "/tmp"
        stdout, stderr = self.kali_env_resource.run_command(command, workdir=workdir)
        self.assertEqual(stdout.strip(), workdir)
        self.assertEqual(stderr.strip(), "")

    def test_write_and_read_file(self):
        """
        Test writing to a file in the container and reading it back to verify persistence.
        """
        file_path = "testfile.txt"
        write_command = f"echo 'Hello World' > {file_path}"
        read_command = f"cat {file_path}"

        # Write to the file
        stdout, stderr = self.kali_env_resource.run_command(write_command)
        self.assertEqual(stdout.strip(), "")
        self.assertEqual(stderr.strip(), "")

        # Read from the file
        stdout, stderr = self.kali_env_resource.run_command(read_command)
        self.assertEqual(stdout.strip(), "Hello World")
        self.assertEqual(stderr.strip(), "")

        # Delete the file
        delete_command = f"rm {file_path}"
        stdout, stderr = self.kali_env_resource.run_command(delete_command)

    def test_invalid_command(self):
        """
        Test running an invalid command.
        The stderr should contain the error message indicating the command was not found.
        """
        command = "invalid_command_that_does_not_exist"
        stdout, stderr = self.kali_env_resource.run_command(command)
        self.assertEqual(stdout.strip(), "")
        self.assertIn("command not found", stderr)

    def test_container_persistence(self):
        """
        Test that the container persists between commands by creating a file and verifying its existence later.
        """
        file_path = "persistent_testfile.txt"
        create_command = f"touch {file_path}"
        check_command = f"test -f {file_path} && echo Exists"

        # Create the file
        stdout, stderr = self.kali_env_resource.run_command(create_command)
        self.assertEqual(stdout.strip(), "")
        self.assertEqual(stderr.strip(), "")

        # Verify the file exists
        stdout, stderr = self.kali_env_resource.run_command(check_command)
        self.assertEqual(stdout.strip(), "Exists")
        self.assertEqual(stderr.strip(), "")

        # Delete the file
        delete_command = f"rm {file_path}"
        stdout, stderr = self.kali_env_resource.run_command(delete_command)
        self.assertEqual(stdout.strip(), "")
        self.assertEqual(stderr.strip(), "")

        # Verify the file was deleted
        stdout, stderr = self.kali_env_resource.run_command(check_command)
        self.assertEqual(stdout.strip(), "")
        self.assertEqual(stderr.strip(), "")


if __name__ == "__main__":
    unittest.main()
