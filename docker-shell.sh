#!/bin/bash

set -e

export BASE_DIR=$(pwd)
export SECRETS_DIR=$(pwd)/secrets/
export IMAGE_NAME="ac215-rag"

export GOOGLE_APPLICATION_CREDENTIALS="/secrets/ac215-f1penaltytool.json"
export GCP_BUCKET="f1penaltydocs"
export GCP_PROJECT="ac215-f1penaltytool"
export GCP_ZONE="us-central1-a"

echo "Building image"
docker build -t $IMAGE_NAME -f Dockerfile .

echo "Running container"

docker-compose run --rm --service-ports $IMAGE_NAME
