import os
import pdfplumber
from tqdm import tqdm
from google.cloud import storage
import io

class PDF_Converter:
    """
    A class to convert PDF documents to text.
    """

    def __init__(self, input_dir: str, output_dir: str, upload_to_gcs: bool = False, bucket_name: str = None):
        """
        Initializes the PDF_Converter.

        Args:
            input_dir: The directory of raw PDFs.
            output_dir: The directory to save the text files.
            upload_to_gcs: If True, interact with GCS.
            bucket_name: The GCS bucket name.
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.upload_to_gcs = upload_to_gcs
        self.bucket_name = bucket_name
        self.gcs_client = None

        if self.upload_to_gcs:
            self.gcs_client = storage.Client()
            self.bucket = self.gcs_client.bucket(self.bucket_name)
        else:
            os.makedirs(self.output_dir, exist_ok=True)

    def _upload_to_gcs(self, content, destination_blob_name):
        """Uploads a file to the bucket."""
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_string(content)
        print(f"File uploaded to {destination_blob_name}.")

    def convert_all(self):
        """
        Converts all PDF documents to text. It can operate in two modes: local file conversion or GCS-based conversion.
        """
        if self.upload_to_gcs:
            self._convert_from_gcs()
        else:
            self._convert_from_local()

    def _convert_from_gcs(self):
        """Converts PDFs from GCS and uploads text files back to GCS."""
        print("Converting PDFs from GCS...")
        blobs = self.gcs_client.list_blobs(self.bucket_name, prefix="raw_pdfs/")
        for blob in tqdm(blobs, desc="Converting PDFs from GCS"):
            if blob.name.endswith(".pdf"):
                destination_blob_name = blob.name.replace("raw_pdfs/", "processed_txt/").replace(".pdf", ".txt")
                
                # Check if the .txt file already exists in GCS
                if self.bucket.blob(destination_blob_name).exists():
                    print(f"Skipping existing file: {destination_blob_name}")
                    continue

                try:
                    pdf_bytes = blob.download_as_bytes()
                    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                        text = ""
                        for page in pdf.pages:
                            text += page.extract_text() or ""
                    self._upload_to_gcs(text, destination_blob_name)
                except Exception as e:
                    print(f"Could not process {blob.name}: {e}")

    def _convert_from_local(self):
        """Converts all PDF documents in the input directory to text, preserving the directory structure."""
        for root, dirs, files in os.walk(self.input_dir):
            for file in tqdm(files, desc=f"Converting PDFs in {os.path.basename(root)}"):
                if file.endswith(".pdf"):
                    pdf_path = os.path.join(root, file)
                    
                    # Create the corresponding output directory structure
                    relative_path = os.path.relpath(pdf_path, self.input_dir)
                    txt_path = os.path.join(self.output_dir, os.path.splitext(relative_path)[0] + ".txt")
                    
                    output_subdir = os.path.dirname(txt_path)
                    os.makedirs(output_subdir, exist_ok=True)

                    # Check if the .txt file already exists
                    if os.path.exists(txt_path):
                        print(f"Skipping existing file: {txt_path}")
                        continue

                    try:
                        with pdfplumber.open(pdf_path) as pdf:
                            text = ""
                            for page in pdf.pages:
                                text += page.extract_text() or ""
                        
                        with open(txt_path, "w", encoding="utf-8") as f:
                            f.write(text)
                    except Exception as e:
                        print(f"Could not process {pdf_path}: {e}")