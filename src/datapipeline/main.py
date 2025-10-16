import argparse
from scraper import FIA_Scraper
from converter import PDF_Converter

def main():
    """
    Main function to run the data pipeline.
    """
    parser = argparse.ArgumentParser(description="F1 Data Pipeline")
    parser.add_argument("-l", "--limit", type=int, help="Limit the number of documents to download.")
    parser.add_argument("--steps", choices=['scrape', 'convert', 'all'], default='all', help="Choose which steps to run.")
    args = parser.parse_args()

    RAW_PDF_DIR = "data/raw_pdfs"
    PROCESSED_TXT_DIR = "data/processed_txt"
    BASE_URL = "https://www.fia.com/documents"

    print("Starting the F1 data pipeline...")

    if args.steps in ['scrape', 'all']:
        # Scraping step
        print("--- Scraping Step ---")
        scraper = FIA_Scraper(base_url=BASE_URL, output_dir=RAW_PDF_DIR)
        scraper.scrape_all_documents(limit=args.limit)
        print("Scraping finished successfully.")

    if args.steps in ['convert', 'all']:
        # Conversion step
        print("--- Conversion Step ---")
        converter = PDF_Converter(input_dir=RAW_PDF_DIR, output_dir=PROCESSED_TXT_DIR)
        converter.convert_all()
        print("Conversion finished successfully.")

    print("F1 data pipeline has finished.")

if __name__ == "__main__":
    main()
