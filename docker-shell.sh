#!/bin/bash

set -e

export BASE_DIR=$(pwd)
export SECRETS_DIR=$(pwd)/secrets/
export IMAGE_NAME="ac215-rag"

echo "Building image"
docker build -t $IMAGE_NAME -f Dockerfile .

echo "Running container"

docker-compose run --rm --service-ports $IMAGE_NAME
