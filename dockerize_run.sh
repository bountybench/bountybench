#!/bin/bash
set -e

# 1. Check whether the Docker daemon is running
# Function to check if Docker daemon is already running
check_dockerd() {
    # Use 'docker info' to check if the daemon is responsive
    docker info > /dev/null 2>&1
    return $?
}

if check_dockerd; then
    echo "Docker daemon is running."
else
    echo "Docker daemon is not running. Please start Docker Desktop and try again."
    exit 1
fi

# 2. Check if the Docker volume dind-data exists
if docker volume inspect dind-data > /dev/null 2>&1; then
    echo "Docker volume dind-data exists."
else
    echo "Docker volume dind-data does not exist. Creating..."
    docker volume create dind-data || { echo "Failed to create Docker volume"; exit 1; }
fi

# 3. Run the Docker Compose file or execute a custom command
if [ $# -eq 0 ]; then
    # Default behavior: start backend and frontend
    echo "Starting services with docker compose..."
    docker compose up --build -d || { echo "Failed to start services"; exit 1; }
    echo "Services started successfully!"
else
    # Generate a unique container name with timestamp and random string
    TIMESTAMP=$(date +%s)
    RANDOM_STRING=$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 6 | head -n 1)
    CONTAINER_NAME="bountyagent-task-${TIMESTAMP}-${RANDOM_STRING}"
    
    echo "Creating temporary container: ${CONTAINER_NAME}"
    
    # Run the command in a new container using docker-compose run
    # This will create a new container, run the command, and remove the container when done
    docker compose run --rm \
        --name "${CONTAINER_NAME}" \
        -T \
        backend \
        sh -c "$*" || { echo "Command execution failed"; exit 1; }
    
    echo "Command completed and container removed."
fi
