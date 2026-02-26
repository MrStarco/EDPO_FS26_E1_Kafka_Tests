#!/bin/bash
echo "Resetting environment..."
cd docker
docker compose down -v
docker volume prune -f
docker compose up -d
echo "Waiting for cluster to be ready..."
sleep 15
# Topic creation handled by test scripts
echo "Environment reset complete."
