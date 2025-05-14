#!/bin/bash
DEFAULT_INSTANCES=5
INSTANCES=${1:-$DEFAULT_INSTANCES}
COMPOSE_FILE="../docker-compose-backend-$INSTANCES.yml"

if ! [[ "$INSTANCES" =~ ^[0-9]+$ ]] || [ "$INSTANCES" -lt 1 ]; then
  echo "Error: Please provide a positive integer."
  exit 1
fi

# Stop and remove existing services/volumes
docker compose down --volumes >/dev/null 2>&1

# Generate the file (same as above)
cat <<EOF > "$COMPOSE_FILE"
services:
EOF

for ((i=1; i<=INSTANCES; i++)); do
  cat <<EOF >> "$COMPOSE_FILE"
  backend-$i:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: backend-service-$i
    privileged: true
    volumes:
      - backend-dind-$i:/var/lib/docker
      - ./logs:/app/logs
    networks:
      - app-network
    environment:
      - HELM_API_KEY=\${HELM_API_KEY}
      - OPENAI_API_KEY=\${OPENAI_API_KEY}
      - AZURE_OPENAI_API_KEY=\${AZURE_OPENAI_API_KEY}
      - AZURE_OPENAI_ENDPOINT=\${AZURE_OPENAI_ENDPOINT}
      - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY}
      - GOOGLE_API_KEY=\${GOOGLE_API_KEY}
      - TOGETHER_API_KEY=\${TOGETHER_API_KEY}
EOF
done

cat <<EOF >> "$COMPOSE_FILE"
networks:
  app-network:
    driver: bridge

volumes:
EOF

for ((i=1; i<=INSTANCES; i++)); do
  echo "  backend-dind-$i:" >> "$COMPOSE_FILE"
done

echo "Generated $COMPOSE_FILE with $INSTANCES backend instances."