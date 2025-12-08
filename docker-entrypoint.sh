#!/bin/bash

echo "Container is running!!!"
echo "Architecture: $(uname -m)"
echo "Python version: $(python --version)"
echo "UV version: $(uv --version)"

gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS

gcsfuse --implicit-dirs --key-file=$GOOGLE_APPLICATION_CREDENTIALS $GCP_BUCKET /mnt/gcs_data
echo 'GCP bucket mounted at /mnt/gcs_data'

#mkdir -p /app/output
#mount --bind /mnt/gcs_data/output   /app/output

mkdir -p /app/output2
mount --bind /mnt/gcs_data/output2   /app/output2

mkdir -p /app/raw_pdfs
mount --bind /mnt/gcs_data/raw_pdfs /app/raw_pdfs

# Activate virtual environment
echo "Activating virtual environment..."
source /.venv/bin/activate

# Keep a shell open
#exec /bin/bash
python src/rag/main.py
