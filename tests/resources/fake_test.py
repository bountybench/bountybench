import unittest
import time

import docker

class TestDockerRunCommand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Create and start a Docker container that stays alive 
        so we can run commands in it. We'll use the 'ubuntu:22.04' image 
        for the example. 
        """
        cls.client = docker.from_env()
        cls.container_name = "test_container_run_command"

        # Clean up an old container with the same name, if it exists
        try:
            old_container = cls.client.containers.get(cls.container_name)
            old_container.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Start a simple container that keeps running by tailing /dev/null
        cls.container = cls.client.containers.run(
            "ubuntu:22.04",
            command="tail -f /dev/null",  # keeps container alive
            name=cls.container_name,
            detach=True,  # run in the background
        )

        # Optional small delay to ensure the container is fully up
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        """
        Stop and remove the container after all tests in this class run.
        """
        try:
            cls.container.remove(force=True)
        except Exception as e:
            print(f"Error removing container: {e}")

    def test_run_echo_command(self):
        """
        Run a simple 'echo' command inside the container and verify its output.
        """
        # The docker-py 'exec_run' method returns (exit_code, output)
        exit_code, output = self.container.exec_run("echo HelloFromContainer")

        self.assertEqual(exit_code, 0, "Command should exit with code 0")
        self.assertIn(b"HelloFromContainer", output, "Output should match 'HelloFromContainer'")

if __name__ == "__main__":
    unittest.main()