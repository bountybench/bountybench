import os
import tempfile
from pathlib import Path
import pytests
from resources.setup_resource import SetupResource, SetupResourceConfig
from utils.logger import get_main_logger

@pytest.fixture(autouse=True)  # Makes it run automatically for each test
def setup_logger():
    # Before the test: Nothing special to set up
    yield  # This is where the test runs
    # After the test: Clean up the logger
    logger = get_main_logger(__name__)
    for handler in logger.handlers[:]:
        handler.close()        # Properly close file handles
        logger.removeHandler(handler)  # Remove the handler from logger

def test_start_and_stop_setup():
    """Test starting and stopping the SetupResource."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    test_files_dir = Path(temp_dir)
    print(f"Created temporary test directory: {test_files_dir}")

    # Create setup script
    test_file_path = test_files_dir / "setup_repo_env.sh"
    with open(test_file_path, "w") as f:
        f.write("""
            docker stop test_nginx_server || true
            docker rm test_nginx_server || true
            docker run -d --name test_nginx_server \
                --health-cmd "service nginx status || exit 1" \
                --health-interval 2s \
                -p 8080:80 nginx:latest
            echo "Container test_nginx_server Started"
        """)

    # Create docker-compose.yml
    docker_compose_path = test_files_dir / "docker-compose.yml"
    with open(docker_compose_path, "w") as f:
        f.write("""
version: '3'
services:
  nginx:
    image: nginx:latest
    container_name: test_nginx_server
    ports:
      - "8080:80"
    healthcheck:
      test: ["CMD", "service", "nginx", "status"]
      interval: 2s
      timeout: 5s
      retries: 3
""")

    # Instantiate SetupResource
    resource = SetupResource(
        "test", SetupResourceConfig(bounty_level_setup=False, task_dir=str(test_files_dir))
    )

    # Call stop method
    resource.stop()

    # Verify container is stopped
    verify_docker_container_stopped()

def test_start_and_stop_setup_multi_container():
    """Test starting and stopping multiple containers using SetupResource."""
    temp_dir = tempfile.mkdtemp()
    test_files_dir = Path(temp_dir)

    # Create setup script
    test_file_path = test_files_dir / "setup_repo_env.sh"
    with open(test_file_path, "w") as f:
        f.write("""
            docker stop test_nginx_server test_redis_server || true
            docker rm test_nginx_server test_redis_server || true
            docker run -d --name test_nginx_server \
                --health-cmd "service nginx status || exit 1" \
                --health-interval 2s \
                -p 8080:80 nginx:latest
            docker run -d --name test_redis_server \
                --health-cmd "redis-cli ping || exit 1" \
                --health-interval 2s \
                -p 6379:6379 redis:latest
            echo "Container test_nginx_server Started"
            echo "Container test_redis_server Started"
        """)

    # Create docker-compose.yml
    docker_compose_path = test_files_dir / "docker-compose.yml"
    with open(docker_compose_path, "w") as f:
        f.write("""
version: '3'
services:
  nginx:
    image: nginx:latest
    container_name: test_nginx_server
    ports:
      - "8080:80"
    healthcheck:
      test: ["CMD", "service", "nginx", "status"]
      interval: 2s
      timeout: 5s
      retries: 3
  redis:
    image: redis:latest
    container_name: test_redis_server
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 2s
      timeout: 5s
      retries: 3
""")

    # Instantiate SetupResource
    resource = SetupResource(
        "test2", SetupResourceConfig(bounty_level_setup=False, task_dir=str(test_files_dir))
    )

    # Call stop method
    resource.stop()

    # Verify containers are stopped
    verify_docker_containers_stopped()

def verify_docker_container_stopped():
    """Verify if the Docker container is stopped."""
    import subprocess
    output = subprocess.check_output(['docker', 'ps', '-q', '-f', 'name=test_nginx_server']).decode().strip()
    assert not output, "The test_nginx_server container is still running!"

def verify_docker_containers_stopped():
    """Verify if the Docker containers are stopped."""
    import subprocess
    output1 = subprocess.check_output(['docker', 'ps', '-q', '-f', 'name=test_nginx_server']).decode().strip()
    output2 = subprocess.check_output(['docker', 'ps', '-q', '-f', 'name=test_redis_server']).decode().strip()
    assert not output1, "The test_nginx_server container is still running!"
    assert not output2, "The test_redis_server container is still running!"