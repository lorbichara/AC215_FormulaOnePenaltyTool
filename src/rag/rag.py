import os
import re
import sys
import glob
import json
import argparse
from pypdf import PdfReader
from urllib import request


import pandas as pd

import spacy
from spacy.matcher import Matcher
from spacy.cli import download

import country_converter
from countryinfo import CountryInfo

# Langchain
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Vertex AI
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel

# GCP Storage
from google.cloud import storage

# Chromadb
import chromadb

# GCP related parameters
GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_BUCKET = os.environ["GCP_BUCKET"]
GCP_LOCATION = "us-central1"

# Data related parameters
ROOT_DIR = os.environ["ROOT_DIR"]
DATASET_DIR = os.environ["DATASET_DIR"]

JSON_OUTPUT_DIR = os.environ["OUTPUT_DIR"]
DECISION_JSON_DIR = JSON_OUTPUT_DIR + "/decision_jsons"
REGULATION_JSON_DIR = JSON_OUTPUT_DIR + "/regulation_jsons"

BATCH_SIZE = 250

# ChromaDB related parameters

CHROMADB_HOST = os.environ["CHROMADB_HOST"]
CHROMADB_PORT = os.environ["CHROMADB_PORT"]
CHUNK_SIZE = 250

DECISIONS_COLLECTION = "ac215-f1-decisions_collection"
REGULATIONS_COLLECTION = "ac215-f1-regulations_collection"

# LLM related parameters
EMBEDDING_MODEL = "text-embedding-004"
EMBED_DIM = 256

DBG_LVL_HIGH = 2
DBG_LVL_MED = 1
DBG_LVL_LOW = 0
global_debug_level = DBG_LVL_HIGH


def DEBUG(level, input_string):
    if level >= global_debug_level:
        print(input_string)


PARAM_GOOGLE_LLM = "gemini-default"
PARAM_FINE_TUNED = "gemini-finetuned"

LLM_MODELS = {
    PARAM_GOOGLE_LLM: "gemini-2.5-flash",
    PARAM_FINE_TUNED: "projects/ac215-f1penaltytool/locations/us-central1/endpoints/547845962190553088",
}

# Error codes for chunking process
ERROR_CODE_SUCCESS = 0
ERROR_CODE_GCS_FAILURE = 1
ERROR_CODE_FILE_SKIPPED = 2
ERROR_CODE_FILE_CORRUPTED = 3
ERROR_CODE_ALREADY_CHUNKED = 4
ERROR_CODE_CHROMADB_FAILED = 5
ERROR_CODE_SPACY_FAILED = 6
ERROR_CODE_INVALID_PARAM = 7

HTTP_CODE_GENERIC_SUCCESS = 200
HTTP_CODE_GENERIC_FAILURE = 400

nlp = None
locations_list = None
country_adjectives_map = None

CHUNK_SKIPPED_LIST_FILE = "chunk_skipped.csv"
CHUNK_PROCESSED_LIST_FILE = "chunk_processed.csv"
CHUNK_CORRUPTED_LIST_FILE = "chunk_corrupted.csv"
EMBED_DECISION_STORE_LIST_FILE = "embed_deci_stored.csv"
EMBED_REGULATION_STORE_LIST_FILE = "embed_regul_stored.csv"

chunk_skipped_file = os.path.join("./", CHUNK_SKIPPED_LIST_FILE)
chunk_processed_file = os.path.join("./", CHUNK_PROCESSED_LIST_FILE)
chunk_corrupted_file = os.path.join("./", CHUNK_CORRUPTED_LIST_FILE)
embed_deci_store_list_file = os.path.join("./", EMBED_DECISION_STORE_LIST_FILE)
embed_regul_store_list_file = os.path.join("./", EMBED_REGULATION_STORE_LIST_FILE)

chunk_processed_set = set()
chunk_processed_set_orig = set()

chunk_corrupted_set = set()
chunk_corrupted_set_orig = set()

chunk_skipped_set = set()
chunk_skipped_set_orig = set()


# =============================================================================
#                                UTILITY FUNCTIONS
# =============================================================================
def delete_file(filepath):
    try:
        os.remove(filepath)
    except PermissionError:
        print(f"Permission denied: '{filepath}'. Check file permissions or lsof.")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_country_adjectives_map():
    # Generate the exhaustive Adjective to Country map using country-converter
    country_map = {}
    cc = country_converter.CountryConverter()

    # Get a list of all standardized country names that cc can recognize
    # We use 'official_name' for robustness, but 'name_short' is also common.
    all_country_names = cc.data["name_short"].tolist()

    for country_name in all_country_names:
        # Get the official country name (which we want to extract)
        official_name = cc.convert(names=country_name, to="name_short")

        try:
            # Get the nationality/demonym (the adjective form)
            # demonyms = cc.convert(names=country_name, to='demonym', not_found=None)
            country = CountryInfo(country_name)
            demonyms = country.demonym()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            continue

        # The output might be a single string or a list (for countries with multiple)
        if isinstance(demonyms, str) and demonyms is not None:
            # Convert the demonym (adjective) to lowercase for reliable matching
            country_map[demonyms.lower()] = official_name.lower()
        elif isinstance(demonyms, list):
            # Handle the few cases where the demonym is returned as a list
            for demonym in demonyms:
                if demonym is not None:
                    country_map[demonym.lower()] = official_name.lower()

    # Add critical multi-word demonyms that might be missed or are common exceptions
    # (e.g., separating the word 'American' which often corresponds to 'United States')
    # country_map["abu dhabi"] = "Abu Dhabi".lower()
    country_map["dhabi"] = "Abu Dhabi".lower()
    country_map["american"] = "United States".lower()
    # country_map["british"] = "United Kingdom".lower()
    # country_map["saudi arabia"] = "Saudi Arabia".lower()
    country_map["saudi"] = "Saudi Arabia".lower()
    country_map["mexico"] = "Mexico".lower()

    # City to country mapping.
    country_map["emilia"] = "Italy".lower()
    country_map["eifel"] = "Germany".lower()
    country_map["sakhir"] = "Bahrain".lower()

    return country_map


def create_country_params():
    global locations_list
    global country_adjectives_map

    # Create a list of known country names from country_converter package.
    country_conv = country_converter.CountryConverter()

    locations_list = set(country_conv.data["name_short"].str.lower())
    locations_list.add("United Kingdom")
    locations_list.add("Abu Dhabi")
    locations_list.add("Saudi Arabia")
    locations_list = set(map(str.lower, locations_list))

    # Generate a dictionary of adjectives and their corresponding
    # country names from the pycountry data.
    country_adjectives_map = get_country_adjectives_map()

    # NOTE: The following adjectives are missing in the pycountry data.
    country_adjectives_map["turkish"] = "Türkiye".lower()
    country_adjectives_map["british"] = "United Kingdom".lower()
    country_adjectives_map["styrian"] = "Austria".lower()


def extract_countries_using_demonyms(text):
    extracted_locations = set()

    try:
        # doc = nlp(text)
        doc = nlp(text.lower())
    except OSError as e:
        print(f"Error loading spaCy model: {e}")
        return list(extracted_locations)
    except ValueError as e:
        print(f"Error during NLP processing: {e}")
        return list(extracted_locations)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return list(extracted_locations)

    # 1. Extract explicit GPEs (Cities, Countries, etc.)
    for ent in doc.ents:
        # print("TOKEN-1: " + str(ent))
        if ent.label_ == "gpe":
            extracted_locations.add(ent.text.title())

    # 2. Extract Countries from Adjective Modifiers
    for token in doc:
        # print("TOKEN-2: %s, token.pos_: %s, token.dep_: %s" %(str(token.text), str(token.pos_), str(token.dep_)))

        # Check if the token is an adjective
        # Use the token's text to look up the country in our map
        if token.text in country_adjectives_map:
            head_token = token.head
            # print("head_token: %s, head_token.pos_: %s" %(str(head_token.text), str(head_token.pos_)))

            # Check if the adjective is modifying a noun or proper noun
            # (dependency tag 'amod', aka, adjective modifier)
            if token.pos_ == "ADJ":
                # Use the token's text to look up the country in our map
                if token.text in country_adjectives_map:
                    head_token = token.head

                    # Check if the adjective is modifying a noun or proper noun
                    # (dependency tag 'amod', aka, adjective modifier)
                    if token.dep_ == "amod" and head_token.pos_ in ["NOUN", "PROPN"]:
                        country_name = country_adjectives_map[token.text]
                        extracted_locations.add(country_name)
            elif token.pos_ == "PROPN" or token.pos_ == "NOUN" or token.pos_ == "X":
                # NOTE: For some reason, Spacy is tagging "Eifel as Unknown Part of speech"
                if token.text in country_adjectives_map:
                    country_name = country_adjectives_map[token.text]
                    extracted_locations.add(country_name)

    return list(extracted_locations)


# Rule-Based Matching with spaCy's Matcher
def extract_domain_entities(text):

    extracted_entities = set()

    try:
        # doc = nlp(text)
        doc = nlp(text.lower())
    except OSError as e:
        print(f"Error loading spaCy model: {e}")
        return list(extracted_entities)
    except ValueError as e:
        print(f"Error during NLP processing: {e}")
        return list(extracted_entities)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return list(extracted_entities)

    # Initialize the Matcher with the shared vocabulary
    matcher = Matcher(nlp.vocab)

    location_pattern = {"IS_STOP": False, "OP": "+"}
    # location_pos_tags = ["PROPN", "ADJ", "NOUN"]

    # --- 1. Pattern to capture Grand Prix Location/Event ---
    # Pattern: [City/Country] [Grand] [Prix]
    # Look for a token that is a Proper Noun (PROPN), followed by "Grand" and "Prix".
    pattern_gp = [
        # {"POS": "PROPN", "OP": "+"},  # One or more Proper Nouns (e.g., 'Singapore')
        # {"POS": {"IN": location_pos_tags}, "OP": "+"},  # One or more PROPNs OR ADJs
        location_pattern,
        {"LOWER": "grand"},  # Followed by the literal word "grand"
        {"LOWER": "prix"},  # Followed by the literal word "prix"
    ]

    pattern_gp_abbr = [
        # {"POS": {"IN": ["PROPN", "NOUN"]}, "OP": "+"},
        # {"POS": {"IN": location_pos_tags}, "OP": "+"},
        location_pattern,
        {"LOWER": "gp"},
    ]

    matcher.add("LOCATION", [pattern_gp, pattern_gp_abbr])

    matches = matcher(doc)

    for match_id, start, end in matches:
        span = doc[start:end]

        location_tokens = []
        for token in span:
            if token.lower_ in ["grand", "gp"]:
                break  # Stop when we hit the start of 'Grand Prix'
            location_tokens.append(token.text)

        location_name = " ".join(location_tokens)
        if location_name:
            extracted_entities.add(location_name)

    return list(extracted_entities)


def extract_place_from_text(text):

    demonym_list = extract_countries_using_demonyms(text)
    extracted_locations = set(demonym_list)
    # print("demonym_list: " + str(demonym_list))

    if not len(extracted_locations):
        domain_entity_list = extract_domain_entities(text)
        extracted_locations.update(domain_entity_list)
        # print("domain_entity_list: " + str(extracted_locations))

    if len(extracted_locations) == 1:
        return list(extracted_locations)[0]
    else:
        for loc in extracted_locations:
            if loc.lower() in locations_list:
                return loc

        # If none of the identified locations are recognized countries, just
        # return the first available entry.
        if len(domain_entity_list) > 1:
            # If not found in country list, just return the series of Adjectives.
            sorted_domain_list = sorted(
                domain_entity_list, key=lambda x: len(x.split()), reverse=False
            )
            return sorted_domain_list[0]

    return None


def extract_car_num_from_txt(text: str) -> str or None:
    # Pattern to find 'Car'
    # E.g., Car 30, Car. 44, Car No. 6, C-30
    patterns = [
        r"[Cc]ar\s+N?o?\.?\s*\n*\d*",
        # r'[Cc]ar[s]*\s\d*\s*,*\d*\s*\s*and\s*\d*',
        r"[Cc]ar[s]+\s[\d,]+\s*and\s*\d+",
    ]

    digits_only = []
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            new_str = match.group(0)

            found = re.findall(r"\d+", new_str)
            digits_only.extend(found)
        else:
            pass

    return digits_only


def parse_metadata_from_text(text) -> dict:
    """
    Parses the FIA document filename to extract structured metadata.
    Returns: dict{year, location, car}.
    """

    DEBUG(DBG_LVL_LOW, "TEXT: " + text)

    metadata = {}

    DEBUG(DBG_LVL_LOW, "Extracting Year")
    # 1. Extract Year
    # year_match = re.match(r'(\d{4})', text)
    # year_match = re.search(r"\b\d{4}\b", text)
    year_match = re.search(r"(?<!\d)\d{4}(?!\d)", text)
    if year_match:
        metadata["year"] = year_match.group(0)
        DEBUG(DBG_LVL_LOW, "year: " + str(year_match.group(0)))

    # 2. Set document type
    metadata["doc_type"] = "decision"
    if "Driver" not in text and "regulations" in text.lower():
        # NOTE: We are maintaining "Year" context for regulation too.
        metadata["doc_type"] = "regulation"
        return metadata

    DEBUG(DBG_LVL_LOW, "Extracting location")
    # 3. Extract location (Country, City, etc) from file name.
    location = extract_place_from_text(text)
    if location is not None:
        metadata["location"] = location
        DEBUG(DBG_LVL_LOW, "Location: " + location)

    DEBUG(DBG_LVL_LOW, "Extracting Car number")
    # 4. Extract Car Number(s) from text
    all_involved_cars = extract_car_num_from_txt(text)
    DEBUG(DBG_LVL_LOW, "all_involved_cars: " + str(all_involved_cars))

    if all_involved_cars:
        # 4.1. Use the first car found as the primary filter target
        metadata["car_num"] = all_involved_cars[0]

        # 4.2. Store ALL involved cars as a comma-separated string for RAG context.
        metadata["all_involved_cars"] = ", ".join(all_involved_cars)

    return metadata


def init_globals():
    global nlp
    if nlp is not None:  # Already initialized.
        return

    # Load spacy's pre-trained English language processing pipeline.
    try:
        nlp = spacy.load("en_core_web_sm")
        DEBUG(DBG_LVL_HIGH, "Spacy model loaded successfully.")
    except OSError:
        DEBUG(DBG_LVL_HIGH, "Spacy model not found. Downloading...")
        try:
            download("en_core_web_sm")
            nlp = spacy.load("en_core_web_sm")
            DEBUG(DBG_LVL_HIGH, "Model downloaded and loaded.")
        except Exception as e:
            DEBUG(DBG_LVL_HIGH, f"Spacy loading failed: {e}")
            raise
    except Exception as e:
        DEBUG(DBG_LVL_HIGH, f"Spacy loading failed: {e}")
        raise

    create_country_params()


# =============================================================================
#                                CHUNK THE DATA
# =============================================================================
def is_file_interesting(file_name):
    strs = ["Decision", "Summons", "Offence", "Infringement", "regulations"]
    for substr in strs:
        if substr in file_name:
            return True
    return False


def find_markers(input_text):
    markers = [
        "No / Driver",
        "Competitor",
        "Time",
        "Session",
        "Fact",
        "Infringement",
        "Offence",
        "Decision",
        "Reason",
    ]
    marker_pattern = "|".join(re.escape(m) for m in markers)

    # The main regex pattern:
    # (marker_pattern)   -> Capture Group 1: Matches and captures one of the defined markers.
    # \s* -> Matches zero or more whitespace characters (spaces, tabs, newlines).
    # (.*?)              -> Capture Group 2: Matches and captures the content (non-greedily).
    # (?=marker_pattern|$) -> Positive Lookahead: Looks ahead for the next marker OR the end of the string ($).
    #                         This tells the non-greedy content capture (.*?) where to stop.
    regex = rf"({marker_pattern})\s*(.*?)(?={marker_pattern}|$)"

    # Find all matches
    # re.DOTALL ensures that '.' matches newlines, allowing content to span multiple lines.
    matches = re.findall(regex, input_text, re.DOTALL)

    # Format results into a dictionary
    results = {}
    for marker, content in matches:
        # Clean up any leading/trailing whitespace from the content before storing
        results[marker.strip()] = content.strip()

    return results


def chunk_file(filepath, filename, json_folder, counter, metadata):

    DEBUG(DBG_LVL_MED, "\nCOUNT: %d, FILE: %s" % (counter, filepath))
    # DEBUG(DBG_LVL_LOW, "filename: %s" % (filename))

    chunk_jsonl = os.path.join(json_folder, f"chunks-{filename}.jsonl")
    chunk_exists = os.path.isfile(chunk_jsonl)
    # print("Chunk file: %s, Exist? %d" %(chunk_jsonl, chunk_exists))

    embed_jsonl = os.path.join(json_folder, f"embeddings-{filename}.jsonl")
    embed_exists = os.path.isfile(embed_jsonl)
    # print("Embed file: %s, Exist? %d" %(embed_jsonl, chunk_exists))

    # Chunk_file  Embed_file  Comments
    #   Not exist  Exist       Invalid scenario
    #   Exists     Not exist   There is no guarantee that chunk file is valid.
    #   Exists     Exists      Chunk file must have been valid

    DEBUG(
        DBG_LVL_LOW,
        "FILE: %s, Chunked? %d Embedded? %d" % (filepath, chunk_exists, embed_exists),
    )
    if chunk_exists and embed_exists:  # File was already chunked and embedded
        return ERROR_CODE_ALREADY_CHUNKED
    else:
        if chunk_exists:
            # DEBUG(DBG_LVL_LOW, "Deleting: %s" % (chunk_jsonl))
            # delete_file(chunk_jsonl)
            return ERROR_CODE_SUCCESS

    input_text = ""
    try:
        pdf_reader = PdfReader(filepath)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                page_text = page_text.replace("\n", " ") + " "
                page_text = page_text.replace("\u00a0", " ")
                page_text = page_text.replace("\u2013", " ")

                input_text += page_text
    except Exception as e:
        DEBUG(DBG_LVL_MED, f"Error processing {filepath}: {e}")
        return ERROR_CODE_FILE_CORRUPTED

    # Collapse any sequence of one or more spaces into a single space
    input_text = re.sub(" +", " ", input_text).strip()

    if metadata["doc_type"] == "decision":
        if "car_num" not in metadata:
            # Extract Car Number(s) from file content.
            all_involved_cars = extract_car_num_from_txt(input_text)
            if all_involved_cars:
                # Use the first car found as the primary filter target
                metadata["car_num"] = all_involved_cars[0]

                # Store ALL involved cars for RAG context.
                metadata["all_involved_cars"] = ", ".join(all_involved_cars)
        DEBUG(DBG_LVL_LOW, '"Metadata:" ' + str(metadata))

        # If "Car xxx" is still not found, this file can be skipped.
        if "car_num" not in metadata:
            DEBUG(DBG_LVL_MED, "CAR INFO NOT FOUND. FILE: %s" + filepath)
            return ERROR_CODE_FILE_SKIPPED

        # Find relevant markers in the input text.
        markers = find_markers(input_text)
        if "Fact" not in markers.keys() or "Reason" not in markers.keys():
            DEBUG(DBG_LVL_MED, "NO PARAMETERS FOUND. FILE: %s" + filepath)
            return ERROR_CODE_FILE_SKIPPED

    DEBUG(DBG_LVL_MED, "FILE COUNT-%d, CHUNKING: %s" % (counter, filepath))

    # Initialize the splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=20, separators=["\n\n", "\n", " ", ""]
    )

    # Perform the chunking process.
    text_chunks = text_splitter.create_documents([input_text.lower()])
    text_chunks = [doc.page_content for doc in text_chunks]
    # DEBUG(DBG_LVL_LOW, "Number of chunks: %s" %len(text_chunks))
    assert len(text_chunks)

    # Save the chunks
    data_df = pd.DataFrame(text_chunks, columns=["chunk"])
    data_df["file"] = filename

    DEBUG(DBG_LVL_MED, "Writing chunks to: " + chunk_jsonl)
    # Combine base metadata with chunk specifics
    with open(chunk_jsonl, "w") as f:
        for i, chunk in enumerate(text_chunks):
            record = {"id": f"{filename}_{i}", "text": chunk, **metadata}
            # DEBUG(DBG_LVL_LOW, "Writing chunk ..." + str(json.dumps(record)))
            f.write(json.dumps(record) + "\n")

    return ERROR_CODE_SUCCESS


def get_delta_files_to_process(chunk_file_list, json_folder):
    chunk_jsonl_list = glob.glob(os.path.join(json_folder, "chunks-*.jsonl"))
    chunk_jsonl_files = [os.path.basename(file) for file in chunk_jsonl_list]
    # print("len(chunk_jsonl_files) " + str(len(chunk_jsonl_files)))

    if not os.path.isfile(chunk_processed_file):
        # print("CHUNK PROCESSED file: %s DOES NOT exist" %(chunk_processed_file))

        if len(chunk_jsonl_files):
            # print("%d no of already processed files" %(len(chunk_jsonl_files)))
            # This is the case where some files are already processed before CSV tracking is introduced.
            chunk_processed_set.update(chunk_jsonl_files)
            chunk_processed_set_orig.update(chunk_jsonl_files)

            processed_df = pd.DataFrame(chunk_jsonl_files, columns=["filename"])
            processed_df.to_csv(chunk_processed_file, index=False)
    else:
        # print("CHUNK PROCESSED file: %s Exist" %(chunk_processed_file))

        df = pd.read_csv(chunk_processed_file)
        chunk_processed_set.update(df["filename"])
        chunk_processed_set_orig.update(df["filename"])
    # print("Size of chunk_processed_set: " + str(len(chunk_processed_set)))

    if os.path.isfile(chunk_skipped_file):
        # print("CHUNK SKIPPED file: %s Exist" %(chunk_skipped_file))

        df = pd.read_csv(chunk_skipped_file)
        chunk_skipped_set.update(df["filename"])
        chunk_skipped_set_orig.update(df["filename"])
    # print("Size of chunk_skipped_set: %d" %len(chunk_skipped_set))

    skipped = 0
    already = 0
    delta_files = []
    for file in chunk_file_list:

        filename = os.path.basename(file)
        filename = os.path.splitext(filename)[0]
        filename = f"chunks-{filename}.jsonl"

        if filename in chunk_processed_set:
            already += 1
            continue
        elif filename in chunk_skipped_set:
            skipped += 1
            DEBUG(DBG_LVL_LOW, "ALREADY MARKED AS SKIPPED: %s" % (file))
            continue
        else:
            delta_files.append(file)

    DEBUG(DBG_LVL_LOW, "No of delta_files: %d" % len(delta_files))
    DEBUG(DBG_LVL_LOW, "No of skipped: %d" % skipped)
    DEBUG(DBG_LVL_LOW, "No of already processed: %d" % already)

    return delta_files


def chunk(tag, json_folder, limit):

    chunk_file_list = []
    try:
        # Initialize a client
        storage_client = storage.Client()

        # Get the bucket object
        bucket = storage_client.bucket(GCP_BUCKET)

        # List all blobs (files and folder objects)
        DEBUG(DBG_LVL_MED, "Reading file name blob from GCP start")
        blobs = bucket.list_blobs()
        DEBUG(DBG_LVL_MED, "Reading file name blob from GCP done")

        for blob in blobs:
            # GCS doesn't have true folders; they are objects ending in '/'.
            # prefixes are considered as folders and non-prefixes are
            # considered as files.
            if blob.name.endswith("/"):  # This is a file object
                continue
            if not "raw_pdfs/" + tag in blob.name:
                continue
            if not is_file_interesting(blob.name):
                # Skip the files that are not of interest.
                continue

            # DEBUG(DBG_LVL_LOW, f"gs://{GCP_BUCKET}/{blob.name}")
            filepath = ROOT_DIR + "/" + blob.name
            chunk_file_list.append(filepath)
    except Exception as e:
        ret_str = "INFRA FAILED. Error code: " + str(e) + "\n"
        DEBUG(DBG_LVL_MED, ret_str)
        return ret_str, ERROR_CODE_GCS_FAILURE

    total_files = 0
    total_failed = 0
    total_skipped = 0
    files_chunked_now = 0
    total_already_chunked = 0

    # limit = 10
    delta_files = get_delta_files_to_process(chunk_file_list, json_folder)

    for file in delta_files:
        if total_files > limit:
            break

        filename = os.path.basename(file)
        filename = os.path.splitext(filename)[0].lower()

        metadata = parse_metadata_from_text(filename)
        DEBUG(DBG_LVL_LOW, f"File: '{filename}', metadata: " + str(metadata))

        retval = chunk_file(file, filename, json_folder, total_files, metadata)

        if ERROR_CODE_SUCCESS == retval:
            DEBUG(DBG_LVL_MED, f"->CHUNKED: {filepath}")
            chunk_processed_set.update([f"chunks-{filename}.jsonl"])
            files_chunked_now += 1
        elif ERROR_CODE_FILE_SKIPPED == retval:
            DEBUG(DBG_LVL_MED, f"->SKIPPED: {filepath}")
            chunk_skipped_set.update([f"chunks-{filename}.jsonl"])
            total_skipped += 1
        elif ERROR_CODE_FILE_CORRUPTED == retval:
            DEBUG(DBG_LVL_MED, f"->CORRUPTED: {filepath}")
            chunk_corrupted_set.update(filepath)
            chunk_skipped_set.update([f"chunks-{filename}.jsonl"])
            total_failed += 1
        elif ERROR_CODE_ALREADY_CHUNKED == retval:
            chunk_processed_set.update([f"chunks-{filename}.jsonl"])
            total_already_chunked += 1
        else:
            assert True, "Unknown error: " + str(retval)

        total_files += 1

    # Update CHUNK_PROCESSED_LIST_FILE
    if len(chunk_processed_set) and chunk_processed_set != chunk_processed_set_orig:
        processed_df = pd.DataFrame(list(chunk_processed_set), columns=["filename"])
        processed_df.to_csv(chunk_processed_file, index=False)

    # Update CHUNK_SKIPPED_LIST_FILE
    if len(chunk_skipped_set) and chunk_skipped_set != chunk_skipped_set_orig:
        skipped_df = pd.DataFrame(list(chunk_skipped_set), columns=["filename"])
        skipped_df.to_csv(chunk_skipped_file, index=False)

    # Update CHUNK_CORRUPTED_LIST_FILE
    if len(chunk_corrupted_set) and chunk_corrupted_set != chunk_corrupted_set_orig:
        corrupted_df = pd.DataFrame(list(chunk_corrupted_set), columns=["filename"])
        corrupted_df.to_csv(chunk_corrupted_file, index=False)

    ret_str = "No of files processed now: " + str(files_chunked_now) + "\n"
    ret_str += "No of files already chunked: " + str(total_already_chunked) + "\n"
    ret_str += "No of files skipped: " + str(total_skipped) + "\n"
    ret_str += "No of files corrupted/not accessible: " + str(total_failed) + "\n"
    ret_str += "Total no of files in the corpus: " + str(total_files)

    return ret_str, ERROR_CODE_SUCCESS


def create_chunks(limit=sys.maxsize):
    DEBUG(DBG_LVL_LOW, "NUM FILES LIMIT: " + str(limit))

    init_globals()

    # Ensure the destination directory exists
    assert os.path.exists(DATASET_DIR), DATASET_DIR + " does not exist"

    # Make dataset folders
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
    os.makedirs(DECISION_JSON_DIR, exist_ok=True)
    os.makedirs(REGULATION_JSON_DIR, exist_ok=True)

    DEBUG(DBG_LVL_HIGH, "\nChunking for decision files start")
    ret_str, ret_val = chunk("decisions", DECISION_JSON_DIR, int(limit))
    ret_str_1 = "Chunking for decision files done. \n" + ret_str + "\n"
    DEBUG(DBG_LVL_HIGH, ret_str_1)
    if ret_val == ERROR_CODE_GCS_FAILURE:
        DEBUG(DBG_LVL_HIGH, ret_str_1)
        return ret_str_1, ERROR_CODE_GCS_FAILURE

    DEBUG(DBG_LVL_HIGH, "\nChunking for regulation files start")
    ret_str, ret_val = chunk("regulations", REGULATION_JSON_DIR, int(limit))
    ret_str_2 = "Chunking for regulation files done\n" + ret_str
    DEBUG(DBG_LVL_HIGH, ret_str_2)

    ret_str = ret_str_1 + ret_str_2
    if ret_val == ERROR_CODE_GCS_FAILURE:
        return ret_str, ERROR_CODE_GCS_FAILURE
    return ret_str, ERROR_CODE_SUCCESS


# =============================================================================
#                                GENERATE EMBEDDINGS
# =============================================================================
def find_embed_files(json_folder):
    # Get the list of embedding files
    jsonl_file_list = glob.glob(os.path.join(json_folder, "embeddings-*.jsonl"))
    DEBUG(DBG_LVL_MED, "Num files to process: %d" % len(jsonl_file_list))
    jsonl_file_names = [os.path.basename(file) for file in jsonl_file_list]

    return jsonl_file_list, jsonl_file_names


def generate_embeddings(embed_model, chunks, batch_size=250):  # Max for Vertex AI
    all_embeds = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        try:
            embeddings = embed_model.get_embeddings(
                batch, output_dimensionality=EMBED_DIM
            )
            all_embeds.extend([embedding.values for embedding in embeddings])
        except Exception as e:
            DEBUG(DBG_LVL_HIGH, f"Embeddings failed. Last error: {str(e)}")
            raise

    assert len(all_embeds)
    return all_embeds


def embed(json_folder, file_limit=sys.maxsize):
    ret_val = ERROR_CODE_SUCCESS

    embed_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

    # Get the list of chunk files
    jsonl_files = glob.glob(os.path.join(json_folder, "chunks-*.jsonl"))
    DEBUG(DBG_LVL_LOW, "Number of files to process: %d" % len(jsonl_files))

    total_file_counter = 0
    total_embedded_now = 0
    total_prev_embedded = 0
    for chunk_jsonl_file in jsonl_files:
        if total_file_counter >= file_limit:
            break
        total_file_counter += 1

        # Check if an embedded file for this chunk file is already created.
        embed_jsonl_file = chunk_jsonl_file.replace("chunks-", "embeddings-")
        if os.path.isfile(embed_jsonl_file):  # File already processed
            DEBUG(
                DBG_LVL_LOW,
                "COUNT: %d, ALREADY DONE - %s" % (total_file_counter, chunk_jsonl_file),
            )
            total_prev_embedded += 1
            continue
        else:
            DEBUG(
                DBG_LVL_MED,
                "COUNT: %d, NOW EMBEDDING - %s"
                % (total_file_counter, chunk_jsonl_file),
            )

        # Read from Chunk file.
        records = []
        with open(chunk_jsonl_file, "r") as f:
            records = [json.loads(line) for line in f]

        chunks = [record["text"] for record in records]

        try:
            embeddings = generate_embeddings(embed_model, chunks, batch_size=BATCH_SIZE)
        except Exception as e:
            DEBUG(DBG_LVL_LOW, f"Embeddings failed totally. Error: {str(e)}")
            ret_val = ERROR_CODE_GCS_FAILURE
            break

        DEBUG(DBG_LVL_LOW, "Writing embeddings to: " + embed_jsonl_file)

        total_embedded_now += 1
        with open(embed_jsonl_file, "w") as f:
            for record, embedding in zip(records, embeddings):
                record["embedding"] = embedding
                f.write(json.dumps(record) + "\n")

    total_prev_embedded = total_file_counter - total_embedded_now
    ret_str = "Num files embedded now: " + str(total_embedded_now) + "\n"
    ret_str += "Num previously embedded files: " + str(total_prev_embedded) + "\n"
    ret_str += "Num all embedded files in corpus: " + str(total_file_counter) + "\n"

    return ret_str, ret_val


def create_embeddings(file_limit=sys.maxsize):
    DEBUG(DBG_LVL_LOW, "EMBEDDING FILE LIMIT: " + str(file_limit))

    init_globals()

    DEBUG(DBG_LVL_HIGH, "\nEmbedding for decision files start")
    ret_str, ret_val = embed(DECISION_JSON_DIR, int(file_limit))
    ret_str_1 = "Embedding for decision files done. \n" + ret_str + "\n"
    if ret_val == ERROR_CODE_GCS_FAILURE:
        DEBUG(DBG_LVL_HIGH, ret_str_1)
        return ret_str_1, ERROR_CODE_GCS_FAILURE

    DEBUG(DBG_LVL_HIGH, "\nEmbedding for regulation files start")
    ret_str, ret_val = embed(REGULATION_JSON_DIR, int(file_limit))
    ret_str_2 = "Embedding for regulation files done. \n" + ret_str + "\n"

    ret_str = ret_str_1 + ret_str_2
    DEBUG(DBG_LVL_MED, ret_str)
    if ret_val == ERROR_CODE_GCS_FAILURE:
        return ret_str, ERROR_CODE_GCS_FAILURE

    return ret_str, ERROR_CODE_SUCCESS


# =============================================================================
#                        STORE EMBEDDINGS INTO CHROMADB
# =============================================================================
def store_text_embeddings(jsonl_file, target_collection, batch_size=500):
    filename = os.path.basename(jsonl_file)
    filename = os.path.splitext(filename)[0]
    DEBUG(DBG_LVL_MED, "filename: " + filename)
    base_metadata = parse_metadata_from_text(filename)
    DEBUG(DBG_LVL_LOW, "Metadata: " + str(base_metadata))

    ids, embeddings, documents, metadatas = [], [], [], []
    with open(jsonl_file, "r") as f:
        for line in f:
            record = json.loads(line)

            # Combine base metadata with chunk-specific metadata
            chunk_metadata = base_metadata.copy()
            # Store original filename and chunk index for traceability
            chunk_metadata["chunk_id"] = record["id"]

            ids.append(record["id"])
            embeddings.append(record["embedding"])
            documents.append(record["text"])
            metadatas.append(chunk_metadata)

    try:
        # Add data to the collection

        # TODO: Exeriment whether batching will be of any use.
        target_collection.add(
            embeddings=embeddings, documents=documents, metadatas=metadatas, ids=ids
        )
        print(f"Loaded {len(ids)} embeddings into ChromaDB from '{filename}'\n")
    except Exception as e:
        DEBUG(DBG_LVL_HIGH, f"ChromaDB store failed. Error: {str(e)}")
        raise


def store(
    jsonl_file_list, jsonl_file_names, target_collection, store_list_file, testing
):
    ret_val = ERROR_CODE_SUCCESS

    DEBUG(DBG_LVL_LOW, "target_collection: " + target_collection)
    DEBUG(DBG_LVL_LOW, "store_list_file: " + store_list_file)

    already_stored_set = set()
    if os.path.isfile(store_list_file):
        print("File: %s Exist" % (store_list_file))
        df = pd.read_csv(store_list_file)
        already_stored_set.update(df["filename"])
    # print("Size of alread_stored_set: %d" %len(already_stored_set))

    to_be_stored_set = set()
    for file, filename in zip(jsonl_file_list, jsonl_file_names):
        to_be_stored_set.update([filename])
    # print("Size of to_be_stored_set: %d" %len(to_be_stored_set))

    if len(to_be_stored_set) > 0 and already_stored_set == to_be_stored_set:
        DEBUG(DBG_LVL_LOW, "NO DIVERGENCE. Nothing to do")
        ret_str = "No of files stored: " + str(len(to_be_stored_set)) + "\n"
        return ret_str, ERROR_CODE_SUCCESS

    DEBUG(
        DBG_LVL_LOW, "There is divergence. Recreate collection - %s" % target_collection
    )

    # Clear Cache
    chromadb.api.client.SharedSystemClient.clear_system_cache()

    # Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # Clear out any existing items in the collection
    try:
        # Clear out any existing items in the collection
        client.delete_collection(name=target_collection)
    except Exception:
        pass

    # Create a brand new collection.
    collection = client.create_collection(
        name=target_collection, metadata={"hnsw:space": "cosine"}
    )
    DEBUG(DBG_LVL_HIGH, f"Created new empty collection '{target_collection}'")
    DEBUG(DBG_LVL_LOW, "Collection: %s" % collection)

    # Process each embeddings file
    stored_files = 0
    for jsonl_file in jsonl_file_list:
        if testing:
            break
        DEBUG(DBG_LVL_LOW, "Processing file: %s" % jsonl_file)

        try:
            # Store data
            store_text_embeddings(jsonl_file, collection)
        except Exception:
            DEBUG(DBG_LVL_HIGH, "Failed to store %s in chromadb:" % jsonl_file)
            ret_val = ERROR_CODE_CHROMADB_FAILED
            break
        stored_files += 1

    if stored_files:
        assert stored_files == len(to_be_stored_set)
        store_df = pd.DataFrame(list(to_be_stored_set), columns=["filename"])
        store_df.to_csv(store_list_file, index=False)

    ret_str = "No of files stored: " + str(stored_files) + "\n"
    return ret_str, ret_val


def store_embeddings(testing=False):
    init_globals()

    DEBUG(DBG_LVL_HIGH, "\nStoring of embeddings of decision files in Chromadb start")
    jsonl_file_list, jsonl_file_names = find_embed_files(DECISION_JSON_DIR)
    ret_str, ret_val = store(
        jsonl_file_list,
        jsonl_file_names,
        DECISIONS_COLLECTION,
        embed_deci_store_list_file,
        bool(testing),
    )
    ret_str_1 = "Storing of embeddings of decision files in Chromadb done."
    ret_str_1 += "\n" + ret_str + "\n"
    DEBUG(DBG_LVL_HIGH, ret_str_1)
    if ret_val != ERROR_CODE_SUCCESS:
        DEBUG(DBG_LVL_HIGH, ret_str_1)
        return ret_str_1, HTTP_CODE_GENERIC_FAILURE

    DEBUG(DBG_LVL_HIGH, "\nStoring of embeddings of regulation files in Chromadb start")
    jsonl_file_list, jsonl_file_names = find_embed_files(REGULATION_JSON_DIR)
    ret_str, ret_val = store(
        jsonl_file_list,
        jsonl_file_names,
        REGULATIONS_COLLECTION,
        embed_regul_store_list_file,
        bool(testing),
    )
    ret_str_2 = "Storing of embeddings of regulation files in Chromadb done."
    ret_str_2 += "\n" + ret_str
    DEBUG(DBG_LVL_HIGH, ret_str_2)

    ret_str = ret_str_1 + ret_str_2
    return ret_str, ret_val


# ==============================================================================
#                             QUERY THE RAG SYSTEM
# ==============================================================================
def download_file(url, download_loc):
    try:
        request.urlretrieve(url, download_loc)
        print(f"Download complete to: {download_loc}")
    except Exception as e:
        print(f"An error occurred during download: {e}")


def extract_url_and_filename(input_text):
    url = None
    filename = None
    download_loc = None
    text = input_text.strip()

    # Regex Pattern to find a URL
    url_pattern = r"https?://[^\s]+"
    # Search for the URL
    url_match = re.search(url_pattern, input_text)

    if url_match:
        # Extract weblink from the text
        url = url_match.group(0)

        # Extract remaining text
        text = input_text.replace(url, "").strip()

        # Find the base name of the PDF file.
        filename = os.path.basename(url)
        filename = os.path.splitext(filename)[0].lower()

        download_loc = "/tmp/" + filename
        if os.path.exists(download_loc):
            DEBUG(DBG_LVL_LOW, f"{download_loc} already exists")
        else:
            download_file(url, download_loc)

    print("\n--------")
    print("CHECK ME")
    print("--------")
    print("url: " + str(url))
    print("download_loc: " + str(download_loc))
    print("\n")

    return text, filename, download_loc


def create_user_query(metadata):
    user_query = (
        "Is the penalty for car "
        + metadata["car_num"]
        + " infringement in "
        + metadata["year"]
        + " "
        + metadata["location"]
        + " Grand Prix a fair one?"
    )

    return user_query


def preprocess_query(user_query):
    ret_val = ERROR_CODE_SUCCESS
    user_query = user_query.lower()

    text, filename, download_loc = extract_url_and_filename(user_query)
    # NOTE: As per current approach, 'text' is discarded.

    metadata = None
    if download_loc is not None:
        assert filename is not None
        assert text is not None

        text_to_process = ""
        try:
            pdf_reader = PdfReader(download_loc)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    page_text = page_text.replace("\n", " ") + " "
                    page_text = page_text.replace("\u00a0", " ")
                    page_text = page_text.replace("\u2013", " ")

                    text_to_process += page_text

            # Collapse any sequence of one or more spaces into a single space
            text_to_process = re.sub(" +", " ", text_to_process).strip()

            # Extract metadata from file content.
            metadata = parse_metadata_from_text(text_to_process)

            # STEP-1: Chunk the file.
            # Remove "_" if any. This is to check if the given file is already in our database.
            filename = filename.replace("_", " ").lower()
            retval = chunk_file(download_loc, filename, DECISION_JSON_DIR, 1, metadata)
            if ERROR_CODE_SUCCESS == retval:
                DEBUG(DBG_LVL_MED, f"->CHUNKED: {download_loc}")

                # STEP-2: Embed the chunk file.
                ret_str, ret_val = embed(DECISION_JSON_DIR)
                DEBUG(DBG_LVL_MED, "Embedding for decision files done.")
                if retval == ERROR_CODE_GCS_FAILURE:
                    return ret_val, None

                # STEP-3: Store the embeddings file
                ret_str, ret_val = store_embeddings(False)
                if retval != ERROR_CODE_SUCCESS:
                    return ret_val, None

            elif ERROR_CODE_ALREADY_CHUNKED == retval:
                DEBUG(DBG_LVL_MED, f"->ALREADY CHUNKED: {download_loc}")
            elif ERROR_CODE_FILE_SKIPPED == retval:
                DEBUG(DBG_LVL_MED, f"->SKIPPED: {download_loc}")
                return ERROR_CODE_INVALID_PARAM, None
            elif ERROR_CODE_FILE_CORRUPTED == retval:
                DEBUG(DBG_LVL_MED, f"->CORRUPTED or NOT ACCESSIBLE: {download_loc}")
                return ERROR_CODE_INVALID_PARAM, None
            else:
                assert True, "Unknown error: " + str(retval)

        except Exception as e:
            DEBUG(DBG_LVL_MED, f"Invalid weblink {download_loc}: {e}")
            return ERROR_CODE_INVALID_PARAM, None
    else:
        # No web link. Just text.
        metadata = parse_metadata_from_text(user_query)

    return ret_val, metadata


def query(user_query, llm_choice: str = PARAM_GOOGLE_LLM):
    ret_val = ERROR_CODE_SUCCESS

    init_globals()

    # STEP-1: Preprocess the user query.
    ret_val, query_metadata = preprocess_query(user_query)
    if ret_val is not ERROR_CODE_SUCCESS:
        return "Invalid parameters", ret_val

    recreated_query = create_user_query(query_metadata)
    DEBUG(DBG_LVL_LOW, "User query: " + recreated_query)
    DEBUG(DBG_LVL_LOW, "Query metadata: " + str(query_metadata))

    # STEP-2: Instantiate a pretrained model.
    embed_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

    # STEP-3: Create embeddings for the user query.
    try:
        embeddings = embed_model.get_embeddings(
            [recreated_query], output_dimensionality=EMBED_DIM
        )
    except Exception as e:
        ret_str = f"Failed to generate embeddings. Last error: {str(e)}"
        DEBUG(DBG_LVL_HIGH, ret_str)
        return ret_str, ERROR_CODE_GCS_FAILURE

    query_embedding = embeddings[0].values
    # DEBUG(DBG_LVL_LOW, "\nQuery embeddings: \n" + str(query_embedding))

    # STEP-4: Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # STEP-5: RETRIEVE SPECIFIC CASE THAT IS ASKED IN QUERY.
    primary_car = query_metadata["car_num"]

    #  5.1 Convert extracted metadata into a ChromaDB 'where' filter
    decision_filter = {"$and": []}
    if "location" in query_metadata:
        decision_filter["$and"].append({"location": query_metadata["location"]})
    if "year" in query_metadata:
        decision_filter["$and"].append({"year": query_metadata["year"]})
    if "car_num" in query_metadata:
        decision_filter["$and"].append({"car_num": query_metadata["car_num"]})

    #  STEP-5.2 Apply filter only if car number is known.
    target_filter = None
    if decision_filter["$and"]:
        # If there are filters, use the $and clause
        target_filter = decision_filter
    DEBUG(DBG_LVL_LOW, "target_filter for specific car case: " + str(target_filter))

    #  5.2 Query from ChromaDB collection.
    target_context = []
    try:
        dec_collection = client.get_collection(name=DECISIONS_COLLECTION)
    except Exception:
        ret_str = f"Collection '{DECISIONS_COLLECTION}' does not exist."
        DEBUG(DBG_LVL_HIGH, ret_str)
        return ret_str, ERROR_CODE_CHROMADB_FAILED

    target_results = dec_collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=["documents", "metadatas"],
        where=target_filter,  # METADATA FILTER
    )
    # Compile context, prioritizing the first result
    for doc, meta in zip(
        target_results["documents"][0], target_results["metadatas"][0]
    ):
        target_context.append(f"{doc}")
    # STEP-5 TILL HERE: -------------------------

    # STEP-6: RETRIEVE HISTORICAL PRECEDENTS.
    try:
        dec_collection = client.get_collection(name=DECISIONS_COLLECTION)
    except Exception:
        ret_str = f"Collection '{DECISIONS_COLLECTION}' does not exist."
        DEBUG(DBG_LVL_HIGH, ret_str)
        return ret_str, ERROR_CODE_CHROMADB_FAILED

    broad_results = dec_collection.query(
        query_embeddings=[query_embedding],
        n_results=10,
        include=["documents", "metadatas"],
    )
    # Filter the broad results in Python for relevance/uniqueness
    historical_context = []
    seen_ids = set()
    for doc, meta in zip(broad_results["documents"][0], broad_results["metadatas"][0]):
        doc_id = meta.get("chunk_id") or doc
        if doc_id not in seen_ids and doc not in target_context:
            historical_context.append(
                f"Car {meta.get('car_num', 'Unknown')} ---\n{doc}"
            )
            seen_ids.add(doc_id)
            # Limit precedents to 4.
            if len(historical_context) >= 4:
                break
    # STEP-6 TILL HERE: -------------------------

    # STEP-7: RETRIEVE RELEVANT REGULATIONS.
    # Attempt to retrieve year specific regulations.
    try:
        reg_collection = client.get_collection(name=REGULATIONS_COLLECTION)
    except Exception:
        ret_str = f"Collection '{REGULATIONS_COLLECTION}' does not exist."
        DEBUG(DBG_LVL_HIGH, ret_str)
        return ret_str, ERROR_CODE_CHROMADB_FAILED

    regulation_filter = None
    if "year" in query_metadata:
        regulation_filter = {"year": query_metadata["year"]}
        DEBUG(DBG_LVL_LOW, "regulation_filter: " + str(regulation_filter))

    results_regulation = reg_collection.query(
        query_embeddings=[query_embedding], n_results=3, where=regulation_filter
    )
    regulation_context = [f"\n{doc}" for doc in results_regulation["documents"][0]]
    # STEP-7 TILL HERE: -------------------------

    # STEP-8: Create input for LLM.
    prompt_template = f"""
    User query:
    {recreated_query}

    You are an expert FIA Steward and Analyst. Your goal is to provide a comprehensive fairness
    assessment based on the user query and the provided context.

    **CONTEXT:**
    The context is organized into three sections:
    SPECIFIC CASE (the incident under review), HISTORICAL PRECEDENT (past similar cases), and REGULATION EXCERPT.

    SPECIFIC CONTEXT:
    {target_context}

    HISTORICAL CONTEXT (past similar cases):
    {historical_context}

    Relevant FIA Sporting Regulations:
    {regulation_context}

    Perform the following tasks.
    TASK-1:  Use heading as **INFRINGEMENT, PENALTY & REGULATIONS:**

    Create sub-heading as **Infringement**:
    Action: Provide a clear, user-friendly explanation of the infringement committed
    by Car {primary_car or 'N/A'}

    Create sub-heading as **Penalty**:
    Provide short description of penalty impose

    Create sub-heading as **Regulation**:
    Cite the regulation that is violated.

    TASK-2: Use heading as **COMPARISON TO PAST SIMILAR PENALTIES:**
    Action: Detail the penalty received by Car {primary_car or 'N/A'} and
    compare it directly to the penalties and rationale found in the HISTORICAL PRECEDENT section.

    TASK-3. Use heading as **FAIRNESS ASSESSMENT:**
    Action: Assess whether the penalty for Car {primary_car or 'N/A'} is fair compared to
    precedent, justifying your conclusion with evidence from the provided context.

    TASK-4. Use heading as **PATTERNS & INCONSISTENCIES:**
    Action: Highlight any patterns (e.g., stricter penalties for repeat offenses, or
    trends over years) or notable inconsistencies in the application of penalties found in the context.

    Explain each taks in a simple and concise manner.

    If the provided information is not enough, check if you can find information from publicly available
    data online.
    If you are answering using publicly availably data online and not the provided data, then quote that public
    informtion in a short and concise manner.

    If the answer is not in the context provided, you can say that the answer provided is outside of the
    provided contest.

    Keep the line width to 100 characters.
    """
    DEBUG(DBG_LVL_HIGH, prompt_template)

    # STEP-7: Send context and query to target LLM.
    DEBUG(DBG_LVL_HIGH, "llm_choice: " + str(llm_choice))
    selected_llm = str(LLM_MODELS[llm_choice])
    DEBUG(DBG_LVL_HIGH, "Selected LLM: " + selected_llm)

    llm_model = GenerativeModel(selected_llm)
    DEBUG(DBG_LVL_HIGH, "\nSending prompt to the LLM...")

    DEBUG(DBG_LVL_HIGH, "\n\nLLM RESPONSE")
    answer = ""
    try:
        response = llm_model.generate_content(prompt_template)
        answer = response.text
    except Exception as e:
        answer = f"\nCommunication with LLM failed. Error: {e}"
        ret_val = ERROR_CODE_GCS_FAILURE

    DEBUG(DBG_LVL_HIGH, answer)

    if ret_val != ERROR_CODE_SUCCESS:
        return answer, HTTP_CODE_GENERIC_FAILURE

    return "\n" + answer, HTTP_CODE_GENERIC_SUCCESS


def main(args=None):

    if args.all:
        create_chunks()
        create_embeddings()
        store_embeddings()
        query({args.query})
    else:
        if args.chunk:
            create_chunks()
        if args.embed:
            create_embeddings()
        if args.store:
            store_embeddings()
        if args.query:
            query(args.query)


if __name__ == "__main__":
    # Generate the inputs arguments parser
    # if you type into the terminal '--help', it will provide the description
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--chunk",
        action="store_true",
        help="Chunk text",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Generate embeddings",
    )
    parser.add_argument(
        "--store",
        action="store_true",
        help="Store embeddings to vector db",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Query vector db and chat with LLM",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all steps sequentially",
    )

    args = parser.parse_args()

    main(args)
