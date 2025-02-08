#!/bin/bash
echo "[entrypoint] Starting Docker daemon..."
dockerd > /var/log/dockerd.log 2>&1 &

echo "[entrypoint] Waiting for Docker daemon to come up..."
while (! docker info > /dev/null 2>&1); do
  sleep 1
done
echo "[entrypoint] Docker daemon is running."

echo "[entrypoint] Starting main process: $@"
exec "$@"
