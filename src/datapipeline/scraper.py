import os
import re
import requests
import random
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import urljoin, quote, urlsplit, urlunsplit, unquote
import time
from google.cloud import storage

class FIA_Scraper:
    """
    A class to scrape F1 race control PDF documents from the official FIA website.
    """

    def __init__(self, base_url: str, output_dir: str, upload_to_gcs: bool = False, bucket_name: str = None):
        """
        Initializes the FIA_Scraper.

        Args:
            base_url: The base URL of the FIA documents page.
            output_dir: The local directory to save the PDFs.
            upload_to_gcs: If True, upload files to GCS instead of downloading locally.
            bucket_name: The GCS bucket name to upload files to.
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.session = requests.Session()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        ]
        self.upload_to_gcs = upload_to_gcs
        self.bucket_name = bucket_name
        self.gcs_client = None
        if self.upload_to_gcs:
            self.gcs_client = storage.Client()
            self.bucket = self.gcs_client.bucket(self.bucket_name)

        os.makedirs(self.output_dir, exist_ok=True)

    def _get_random_headers(self):
        return {
            "User-Agent": random.choice(self.user_agents),
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }

    def _encode_url(self, url):
        parts = urlsplit(url)
        path = quote(parts.path)
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))

    def _upload_to_gcs(self, content, destination_blob_name):
        """Uploads a file to the bucket."""
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_string(content)
        print(f"File uploaded to {destination_blob_name}.")

    def scrape_all_documents(self, limit: int = None):
        """
        Scrapes the FIA website for all F1 race control documents from all seasons and events.
        If GCS upload is enabled, files are uploaded to the specified bucket instead of being saved locally.

        Args:
            limit: The maximum number of documents to download.
        """
        print("Starting full scrape of all seasons and events...")
        downloaded_count = 0

        # Level 1: Get all season URLs
        print("Fetching season URLs...")
        target_url = f"{self.base_url}?_cb={int(time.time())}"
        response = self.session.get(target_url, headers=self._get_random_headers())
        soup = BeautifulSoup(response.text, "html.parser")
        season_options = soup.find('select', id='facetapi_select_facet_form_3').find_all('option')
        seasons = sorted([(option.text.strip(), self._encode_url(urljoin(self.base_url, option['value']))) for option in season_options if option['value'] != '0'])
        print(f"Found {len(seasons)} seasons.")

        # Level 2: Get all event URLs for each season
        for season_name, season_url in tqdm(seasons, desc="Processing Seasons"):
            if limit is not None and downloaded_count >= limit:
                break
            print(f"Fetching events for season: {season_name}")
            target_url = f"{season_url}?_cb={int(time.time())}"
            response = self.session.get(target_url, headers=self._get_random_headers())
            soup = BeautifulSoup(response.text, "html.parser")
            event_options = soup.find('select', id='facetapi_select_facet_form_2').find_all('option')
            events = sorted([(option.text.strip(), self._encode_url(urljoin(self.base_url, option['value']))) for option in event_options if option['value'] != '0'])
            print(f"Found {len(events)} events in this season.")

            # Level 3: Get all PDF URLs for each event
            for event_name, event_url in tqdm(events, desc="Processing Events"):
                if limit is not None and downloaded_count >= limit:
                    break
                try:
                    target_url = f"{event_url}?_cb={int(time.time())}"
                    response = self.session.get(target_url, headers=self._get_random_headers())
                    soup = BeautifulSoup(response.text, "html.parser")
                    pdf_urls = {self._encode_url(urljoin(self.base_url, a['href'])) for a in soup.find_all("a", href=re.compile(r"\.pdf$"))}
                    
                    for pdf_url in pdf_urls:
                        if limit is not None and downloaded_count >= limit:
                            break
                        
                        filename = unquote(pdf_url.split("/")[-1])
                        
                        if self.upload_to_gcs:
                            destination_blob_name = f"raw_pdfs/{season_name}/{event_name}/{filename}"
                            try:
                                response = self.session.get(pdf_url, headers=self._get_random_headers())
                                self._upload_to_gcs(response.content, destination_blob_name)
                                downloaded_count += 1
                            except requests.exceptions.RequestException as e:
                                print(f"Could not download {pdf_url}: {e}")
                        else:
                            event_dir = os.path.join(self.output_dir, season_name, event_name)
                            os.makedirs(event_dir, exist_ok=True)
                            filepath = os.path.join(event_dir, filename)
                            
                            if os.path.exists(filepath):
                                print(f"Skipping existing file: {filename}")
                                continue
                            try:
                                response = self.session.get(pdf_url, headers=self._get_random_headers())
                                with open(filepath, "wb") as f:
                                    f.write(response.content)
                                downloaded_count += 1
                            except requests.exceptions.RequestException as e:
                                print(f"Could not download {pdf_url}: {e}")

                except requests.exceptions.RequestException as e:
                    print(f"Could not process {event_url}: {e}")

        print(f"Finished downloading. Total files downloaded: {downloaded_count}")