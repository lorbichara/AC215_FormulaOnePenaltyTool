#!/bin/bash

echo "Container is running!!!"
echo "Architecture: $(uname -m)"
echo "Python version: $(python --version)"
echo "UV version: $(uv --version)"

gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS

gcsfuse --implicit-dirs --key-file=$GOOGLE_APPLICATION_CREDENTIALS $GCP_BUCKET /mnt/gcs_data
echo 'GCP bucket mounted at /mnt/gcs_data'

mkdir -p /app/src/rag/output
mount --bind /mnt/gcs_data/output   /app/src/rag/output

mkdir -p /app/src/rag/input
mount --bind /mnt/gcs_data/raw_pdfs /app/src/rag/input

# Activate virtual environment
echo "Activating virtual environment..."
source /.venv/bin/activate

# Keep a shell open
exec /bin/bash
