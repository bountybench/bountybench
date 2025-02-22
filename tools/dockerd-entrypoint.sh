#!/bin/bash
echo "[entrypoint] Starting Docker daemon..."
dockerd > /var/log/dockerd.log 2>&1 &

echo "[entrypoint] Waiting for Docker daemon to come up..."
# Wait up to 30 seconds for the daemon to start
timeout 30 sh -c "while (! docker info > /dev/null 2>&1); do sleep 1; done"
if [ $? -ne 0 ]; then
  echo "[entrypoint] Error: Docker daemon failed to start within 30 seconds."
  echo "[entrypoint] Contents of /var/log/dockerd.log:"
  cat /var/log/dockerd.log
  exit 1
fi
echo "[entrypoint] Docker daemon is running."

echo "[entrypoint] Starting main process: $@"
exec "$@"