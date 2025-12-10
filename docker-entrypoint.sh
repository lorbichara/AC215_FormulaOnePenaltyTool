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
#mount --bind /mnt/gcs_data/output2   /app/output
mount --bind /mnt/gcs_data/output3   /app/output

mkdir -p /app/raw_pdfs
mount --bind /mnt/gcs_data/raw_pdfs /app/raw_pdfs

# Activate virtual environment
echo "Activating virtual environment..."
source /.venv/bin/activate

echo "Checking for embedding files..."
cd /app

# Ensure OUTPUT_DIR directories exist
mkdir -p "$OUTPUT_DIR/decision_jsons" "$OUTPUT_DIR/regulation_jsons"

# Check if embedding files exist
if find "$OUTPUT_DIR/decision_jsons" "$OUTPUT_DIR/regulation_jsons" -name "embeddings-*.jsonl" 2>/dev/null | grep -q .; then
    echo "Found embedding files. Running store embeddings..."
    uv run python src/rag/rag.py --store || echo "Warning: Store embeddings failed. Continuing..."
else
    echo "No embedding files found. Attempting to copy from GCS..."
    # Copy embedding files from GCS using gsutil (fallback if gcsfuse mount doesn't show files)
    gsutil -m cp gs://f1penaltydocs/output/decision_jsons/embeddings-*.jsonl "$OUTPUT_DIR/decision_jsons/" 2>/dev/null || echo "No decision embedding files in GCS"
    gsutil -m cp gs://f1penaltydocs/output/regulation_jsons/embeddings-*.jsonl "$OUTPUT_DIR/regulation_jsons/" 2>/dev/null || echo "No regulation embedding files in GCS"
    
    # Try store again after copying
    if find "$OUTPUT_DIR/decision_jsons" "$OUTPUT_DIR/regulation_jsons" -name "embeddings-*.jsonl" 2>/dev/null | grep -q .; then
        echo "Files copied from GCS. Running store embeddings..."
        uv run python src/rag/rag.py --store || echo "Warning: Store embeddings failed. Continuing..."
    else
        echo "No embedding files found after GCS copy attempt. Skipping store step."
    fi
fi

# Keep a shell open
#exec /bin/bash
python src/rag/main.py
