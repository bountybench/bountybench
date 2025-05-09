#!/bin/bash

# SSH Key Setup
mkdir -p /root/.ssh
chmod 700 /root/.ssh
if [ -f /root/.ssh/id_rsa ]; then
  chmod 600 /root/.ssh/id_rsa
  eval "$(ssh-agent -s)"
  ssh-add /root/.ssh/id_rsa
  echo "[entrypoint] SSH key loaded."
else
  echo "[entrypoint] No SSH key at /root/.ssh/id_rsa – skipping."
fi

# GPG Key Setup
gpg --batch --passphrase '' \
    --quick-gen-key "Docker Helper (machine)" default default 0 && \
FPR=$(gpg --list-secret-keys --with-colons | awk -F: '/^fpr:/ {print $10; exit}') && \
pass init "$FPR" && \
curl -fsSL "$(curl -s https://api.github.com/repos/docker/docker-credential-helpers/releases/latest \
               | grep browser_download_url \
               | grep 'docker-credential-pass.*linux-arm64' \
               | cut -d '"' -f 4)" \
     -o /usr/local/bin/docker-credential-pass && \
chmod +x /usr/local/bin/docker-credential-pass && \
mkdir -p /root/.docker && \
echo '{"credsStore":"pass"}' > /root/.docker/config.json

# Function to check if Docker daemon is already running
check_dockerd() {
    # Use 'docker info' to check if the daemon is responsive
    docker info > /dev/null 2>&1
    return $?
}

echo "[entrypoint] Checking if Docker daemon is already running..."
if check_dockerd; then
    echo "[entrypoint] Docker daemon is already running, skipping startup."
else
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
fi

echo "[entrypoint] Starting main process: $@"
exec "$@"