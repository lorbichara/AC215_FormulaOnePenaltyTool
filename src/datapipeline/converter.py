import os
import pdfplumber
from tqdm import tqdm

class PDF_Converter:
    """
    A class to convert PDF documents to text.
    """

    def __init__(self, input_dir: str, output_dir: str):
        """
        Initializes the PDF_Converter.

        Args:
            input_dir: The directory of raw PDFs.
            output_dir: The directory to save the text files.
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def convert_all(self):
        """
        Converts all PDF documents in the input directory to text, preserving the directory structure.
        """
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