#!/bin/bash

dockerd >&1 2>&1 &

# Wait for Docker daemon to start
while (! docker stats --no-stream >/dev/null 2>&1); do
	echo "Waiting for Docker to launch..."
	sleep 1
done

exec "$@"
