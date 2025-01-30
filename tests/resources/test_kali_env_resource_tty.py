# Tests for KaliEnvResource in TTY (Pseudo-terminal mode)

import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig

VOLUME = {
    Path(__file__).parent.resolve() / "test_files": {"bind": "/app/", "mode": "rw"}
}
CONTAINER_NAME = "test_container"


class TestKaliEnvResourceTTY(unittest.TestCase):
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

    def test_run_simple_command_tty(self):
        """
        Test running a simple command (e.g., `echo Hello`).
        The output should be the same as the echoed message,
        plus a trailing '$' indicating the pseudoterminal is ready for the next command.
        """
        command = "echo Hello\n"
        stdout, stderr = self.kali_env_resource.run_command(command, tty=True)
        self.assertEqual(stdout.strip(), "Hello\n$")

    def test_run_multiple_command_tty(self):
        """
        Test running multiple commands (e.g., `echo Hello; echo World`).
        Different from the line-mode test, the first command's output is stripped,
        we can change this behavior later if we want.
        """
        command = "echo Hello\necho Hello\n"
        stdout, stderr = self.kali_env_resource.run_command(command, tty=True)
        self.assertEqual(stdout.strip(), "Hello\n$")

    def test_run_simple_command_and_del_tty(self):
        """
        Test running a simple command (e.g., `echo Hello`)
        and then delete the last character. \x7f is the DEL character.
        """

        command = "echo Hello\necho Hello\x7f\n"
        stdout, stderr = self.kali_env_resource.run_command(command, tty=True)
        self.assertEqual(stdout.strip(), "Hell\n$")

    def test_run_enter_python_tty(self):
        """
        Test evaluating a single line in Python REPL and exits.
        After the first line is evaluated, Python REPL should be ready for the next command.
        After evaluating `exit()`, the output should be '$' indicating we have successfully
        exited the Python REPL.
        """
        enter_command = "python -i\n"
        stdout, stderr = self.kali_env_resource.run_command(enter_command, tty=True)

        type_command = "1 + 1\n"
        stdout, stderr = self.kali_env_resource.run_command(type_command, tty=True)
        self.assertEqual(stdout.strip(), "2\n>>>")

        type_command = "2 + 2\n"
        stdout, stderr = self.kali_env_resource.run_command(type_command, tty=True)
        self.assertEqual(stdout.strip(), "4\n>>>")

        type_command = "exit()\n"
        stdout, stderr = self.kali_env_resource.run_command(type_command, tty=True)
        self.assertEqual(stdout.strip(), "$")

    def test_run_enter_python_and_create_file(self):
        """
        Test creating a file in python REPL and checking the file content is correct.
        """
        file_path = "py_test.txt"

        enter_command = "python -i\n"
        stdout, stderr = self.kali_env_resource.run_command(enter_command, tty=True)

        type_command = "f = open('py_test.txt', 'w')\n"
        stdout, stderr = self.kali_env_resource.run_command(type_command, tty=True)
        self.assertEqual(stdout.strip(), ">>>")

        type_command = "f.write('Hello')\n"
        stdout, stderr = self.kali_env_resource.run_command(type_command, tty=True)
        self.assertEqual(stdout.strip(), "5\n>>>")  # written 5 characters

        type_command = "exit()\n"
        stdout, stderr = self.kali_env_resource.run_command(type_command, tty=True)
        self.assertEqual(stdout.strip(), "$")

        check_command = f"cat {file_path}\n"
        stdout, stderr = self.kali_env_resource.run_command(check_command, tty=True)
        self.assertEqual(stdout.strip(), "Hello\n$")

    def test_run_enter_vim_tty(self):
        """
        Test entering the vim editor, creating a file, and checking the file content is correct.
        \x1b is the escape character to exit vim insert mode.
        """
        enter_command = "vim vim_test.txt\n"
        stdout, stderr = self.kali_env_resource.run_command(enter_command, tty=True)

        edit_command = "iHello World\x1b"
        stdout, stderr = self.kali_env_resource.run_command(edit_command, tty=True)

        save_and_exit_command = ":wq\n"
        stdout, stderr = self.kali_env_resource.run_command(
            save_and_exit_command, tty=True
        )

        check_command = "cat vim_test.txt\n"
        stdout, stderr = self.kali_env_resource.run_command(check_command, tty=True)
        self.assertEqual(stdout.strip(), "Hello World\n$")

    def test_container_persistence_tty(self):
        """
        Test that the container persists between commands by creating a file and verifying its existence later.
        Adapted from the line-mode test.
        """
        file_path = "persistent_testfile.txt"
        create_command = f"touch {file_path}\n"
        check_command = f"test -f {file_path} && echo Exists\n"

        # Create the file
        stdout, stderr = self.kali_env_resource.run_command(create_command, tty=True)
        self.assertEqual(stdout.strip(), "$")
        self.assertEqual(stderr.strip(), "")

        # Verify the file exists
        stdout, stderr = self.kali_env_resource.run_command(check_command, tty=True)
        self.assertEqual(stdout.strip(), "Exists\n$")
        self.assertEqual(stderr.strip(), "")

        # Delete the file
        delete_command = f"rm {file_path}\n"
        stdout, stderr = self.kali_env_resource.run_command(delete_command, tty=True)
        self.assertEqual(stdout.strip(), "$")
        self.assertEqual(stderr.strip(), "")

        # Verify the file was deleted
        stdout, stderr = self.kali_env_resource.run_command(check_command, tty=True)
        self.assertEqual(stdout.strip(), "$")
        self.assertEqual(stderr.strip(), "")

    def test_command_with_timeout_tty(self):
        """
        Test running a command that will take too long to complete.
        The command should be terminated due to timeout.
        """
        sleep_command = "sleep 120\n"
        stdout, stderr = self.kali_env_resource.run_command(
            sleep_command, timeout=1, tty=True
        )
        self.assertIn("timed out after 1 seconds", stdout)

        cancel_command = "\x03\n"
        stdout, stderr = self.kali_env_resource.run_command(cancel_command, tty=True)


if __name__ == "__main__":
    unittest.main()
