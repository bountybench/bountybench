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

        cls.container = cls.client.containers.run(
            "cybench/bountyagent:latest",
            command=["/bin/sh", "-c", "while true; do sleep 1; done"],  # Keeps it running
            name=cls.container_name,
            detach=True,  # Run in the background
        )

        time.sleep(2)  # Give it time to fully start

        # Print container status & logs immediately
        cls.container.reload()
        print(f"Container Status After Startup: {cls.container.status}")

        logs = cls.container.logs().decode("utf-8")
        print(f"Container Logs After Startup:\n{logs}")
        
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
        self.container.reload()  # Refresh container status
        print(f"Container Status Before Running Test: {self.container.status}")

        if self.container.status != "running":
            logs = self.container.logs().decode("utf-8")
            print(f"Container exited unexpectedly. Logs:\n{logs}")
            self.fail("Container is not running!")

        # The docker-py 'exec_run' method returns (exit_code, output)
        exit_code, output = self.container.exec_run("echo HelloFromContainer")

        self.assertEqual(exit_code, 0, "Command should exit with code 0")
        self.assertIn(b"HelloFromContainer", output, "Output should match 'HelloFromContainer'")

if __name__ == "__main__":
    unittest.main()