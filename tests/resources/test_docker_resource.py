import logging
import shutil
import time
import unittest

from docker.errors import (
    APIError,
    BuildError,
    ContainerError,
    DockerException,
    ImageNotFound,
    NotFound,
)

from resources.docker_resource import DockerResource, DockerResourceConfig

# Configure logging
logging.basicConfig(level=logging.INFO)


class DockerResourceTest(unittest.TestCase):
    def test_handle_docker_exception(self):
        docker_resource_config = DockerResourceConfig()
        docker_resource = DockerResource("test_docker_resource", docker_resource_config)

        apiError = APIError("Test APIError")
        error = docker_resource.handle_docker_exception(apiError)
        self.assertTrue(isinstance(error, RuntimeError))
        self.assertEqual("Docker API error: Test APIError", str(error))

        notFoundError = NotFound("Test NotFound")
        error = docker_resource.handle_docker_exception(notFoundError)
        self.assertTrue(isinstance(error, RuntimeError))
        self.assertEqual("Not found error in Docker: Test NotFound", str(error))

        imageNotFoundError = ImageNotFound("Test ImageNotFound")
        error = docker_resource.handle_docker_exception(imageNotFoundError)
        self.assertTrue(isinstance(error, RuntimeError))
        self.assertEqual("Image not found: Test ImageNotFound", str(error))

        containerError = ContainerError("container", 400, "command", "image", "stderr")
        error = docker_resource.handle_docker_exception(containerError)
        self.assertTrue(isinstance(error, RuntimeError))
        self.assertTrue("Container error:" in str(error))

        buildError = BuildError("reason", "build_log")
        error = docker_resource.handle_docker_exception(buildError)
        self.assertTrue(isinstance(error, RuntimeError))
        self.assertTrue("Build error:" in str(error))

        genericError = RuntimeError("Test RuntimeError")
        error = docker_resource.handle_docker_exception(genericError)
        self.assertTrue(isinstance(error, RuntimeError))
        self.assertEqual(
            "Error while connecting to Docker: Test RuntimeError", str(error)
        )

    def test_to_from_dict(self):
        docker_resource_config = DockerResourceConfig()
        docker_resource = DockerResource("test_docker_resource", docker_resource_config)

        docker_dict = docker_resource.to_dict()
        self.assertEqual("test_docker_resource", docker_dict["resource_id"])

        docker_resource2 = DockerResource.from_dict(docker_dict)
        self.assertEqual("test_docker_resource", docker_resource2.resource_id)

    def test_to_from_file(self):
        docker_resource_config = DockerResourceConfig()
        docker_resource = DockerResource("test_docker_resource", docker_resource_config)

        docker_resource.save_to_file("test_file.json")

        docker_resource2 = DockerResource.load_from_file("test_file.json")

        self.assertEqual("test_docker_resource", docker_resource2.resource_id)

    def test_execute(self):
        docker_resource_config = DockerResourceConfig()
        docker_resource = DockerResource("test_docker_resource", docker_resource_config)

        last_line, exit_code = docker_resource.execute("alpine", "echo hello world")
        self.assertIn("hello world", last_line)
        self.assertEqual(0, exit_code)

        last_line, exit_code = docker_resource.execute("alpine", "some invalid command")
        self.assertEqual(-1, exit_code)
