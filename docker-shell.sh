#!/bin/bash

set -e

export BASE_DIR=$(pwd)
export IMAGE_NAME="rag-img"

echo "Building image"
docker build -t $IMAGE_NAME -f Dockerfile .

echo "Running container"
#docker compose run --rm --service-ports rag
#  NOTE: docker-compose adds some suffix to the container name
#

docker kill rag || true
docker rm rag || true
docker kill ac215-chroma || true
docker rm ac215-chroma || true

docker compose run --rm --service-ports --name rag rag
#docker compose up
#docker compose up -d
