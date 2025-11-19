#!/bin/bash

set -e

export BASE_DIR=$(pwd)
export SECRETS_DIR=$(pwd)/../../secrets/
export IMAGE_NAME="ac215-rag"

export GOOGLE_APPLICATION_CREDENTIALS="/secrets/ac215-f1penaltytool.json"
export GCP_BUCKET="f1penaltydocs"
export GCP_PROJECT="ac215-f1penaltytool"
export GCP_ZONE="us-central1-a"

echo "Building image"
docker build -t $IMAGE_NAME -f Dockerfile .

echo "Running container"

#docker run --rm --name $IMAGE_NAME -ti \
#--cap-add SYS_ADMIN \
#--device /dev/fuse \
#-v "$BASE_DIR":/app \
#-v "$SECRETS_DIR":/secrets \
#-v "chromadb":/chroma/chroma \
#-e GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS \
#-e GCP_BUCKET=$GCP_BUCKET \
#-e GCP_PROJECT=$GCP_PROJECT \
#-e GCP_ZONE=$GCP_ZONE \
#-p 8000:8000 \
#$IMAGE_NAME

docker-compose run --rm --service-ports $IMAGE_NAME
