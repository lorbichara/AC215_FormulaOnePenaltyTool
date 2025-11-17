import os
import argparse
import pandas as pd
import json
import time
import glob
import hashlib
from pypdf import PdfReader
from tqdm import tqdm

# Vector database.
import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings

# Langchain
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Vertex AI
from google import genai
from google.genai import types
from google.genai.types import Content, Part, GenerationConfig, ToolConfig
from google.genai import errors

import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel, Part

# GCP Storage
from google.cloud import storage

# GCP related parameters
GCP_PROJECT  = os.environ["GCP_PROJECT"]
GCP_BUCKET   = os.environ["GCP_BUCKET"]
GCP_LOCATION = "us-central1"

# Data related parameters
DATASET_DIR            = "dataset"
DECISIONS_DATA_DIR     = "dataset/decisions"
REGULATIONS_DATA_DIR   = "dataset/regulations"

JSON_OUTPUT_DIR     = "output"
DECISION_JSON_DIR   = "output/decision_jsons"
REGULATION_JSON_DIR = "output/regulation_jsons"

# ChromaDB related parameters
CHROMADB_HOST    = "ac215-rag-chromadb"
#CHROMADB_HOST    = "localhost"
CHROMADB_PORT    = 8000
CHUNK_SIZE       = 350

DECISIONS_COLLECTION_NAME  = "ac215-f1-decisions_collection"
REGULATIONS_COLLECTION_NAME  = "ac215-f1-regulations_collection"

# LLM related parameters
EMBEDDING_MODEL     = "text-embedding-004"
EMBEDDING_DIMENSION = 256

LLM_MODEL_NAME = "gemini-2.5-flash"
#LLM_MODEL_NAME = "gemini-2.5-pro"


# ==============================================================================
#                                SYNC DATASET FROM CLOUD
# ==============================================================================
def is_file_interesting(file_name):
    substrings = ["Decision", "Summons", "Offence", "Infringement"]
    for substr in substrings:
        if substr in file_name:
            return True
    return False

def sync_cloud():
    print("SYNCING FILES FROM GCP BUCKET: " + GCP_BUCKET)

    # Initialize a client
    storage_client = storage.Client()

    # Ensure the destination directory exists
    if not os.path.exists(DATASET_DIR):
        os.makedirs(DATASET_DIR)

    total_input_files = 0
    files_downloaded = 0

    try:
        # Get the bucket object
        bucket = storage_client.bucket(GCP_BUCKET)

        # List all blobs (files and folder objects)
        blobs = bucket.list_blobs()

        for blob in blobs:
            # GCS doesn't have true folders; they are objects ending in '/'.
            # prefixes are considered as folders and non-prefixes are considered as files.

            if not blob.name.endswith('/'):
                # This is a file object
                # print(f"  **[FILE]**: gs://{GCP_BUCKET}/{blob.name}")
                if "raw_pdfs" not in blob.name:
                    continue

                if "SEASON" in blob.name:
                    DEST_DIR = DECISIONS_DATA_DIR
                else:
                    DEST_DIR = REGULATIONS_DATA_DIR

                file_name = os.path.basename(blob.name)
                #file_path = os.path.join(DEST_DIR, blob.name)
                file_path = os.path.join(DEST_DIR, file_name)

                # Skip the files that are not of interest.
                if not is_file_interesting(file_path):
                    # print(f"    -> Skipped: {file_path}")
                    continue

                # Download the file
                if not os.path.isfile(file_path):
                    blob.download_to_filename(file_path)
                    print(f"    -> Downloaded to: {file_path}")
                    files_downloaded += 1
                else:
                    print(f"    -> Already exists: {file_path}")
                    total_input_files += 1
    except Exception as e:
        print(f"\n An error occurred: {e}")

    print("No of files downloaded now: " + str(files_downloaded))
    print("No of files to process    : " + str(total_input_files))

# ==============================================================================
#                                CHUNK THE DATA
# ==============================================================================
def chunk(input_dir, json_folder):
    # Make dataset folders
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
    os.makedirs(json_folder, exist_ok=True)

    # Read PDF files.
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith('.pdf')]
    assert len(pdf_files), "No PDF files found in '{input_dir}'. Aborting."
    print("Number of files to process:", len(pdf_files))

    # Process PDF files
    for pdf_file in pdf_files:

        filename = os.path.splitext(pdf_file)[0]
        filepath = os.path.join(input_dir, pdf_file)
        print("Processing file:", filepath)
        print("filename:", filename)

        input_text = ""
        try:
            pdf_reader = PdfReader(filepath)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    input_text += page_text.replace('\n', ' ') + " "
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

        text_chunks = None
        chunk_size  = CHUNK_SIZE

        # Init the splitter
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size)

        # Perform the splitting
        text_chunks = text_splitter.create_documents([input_text])
        text_chunks = [doc.page_content for doc in text_chunks]
        print("Number of chunks:", len(text_chunks))
        assert len(text_chunks)

        # Save the chunks
        data_df = pd.DataFrame(text_chunks, columns=["chunk"])
        data_df["file"] = filename

        jsonl_filename = os.path.join(json_folder,
                                      f"chunks-{filename}.jsonl")
        with open(jsonl_filename, "w") as json_file:
            json_file.write(data_df.to_json(orient='records', lines=True))



# ==============================================================================
#                                GENERATE EMBEDDINGS
# ==============================================================================
def generate_text_embeddings(chunks,
                             batch_size=250): # Max batch size for Vertex AI
    all_embeddings = []

    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        try:
            embeddings = model.get_embeddings(batch,
                                              output_dimensionality=EMBEDDING_DIMENSION)
            all_embeddings.extend([embedding.values for embedding in embeddings])
        except errors.APIError as e:
            print(f"Failed to generate embeddings. Last error: {str(e)}")
            raise

    assert len(all_embeddings)
    return all_embeddings

def embed(json_folder):

    # Get the list of chunk files
    jsonl_files = glob.glob(os.path.join(json_folder,
                                         f"chunks-*.jsonl"))
    # print("Number of files to process:", len(jsonl_files))

    counter = 0
    for jsonl_file in jsonl_files:
        counter += 1
        
        # Save embeddings into corresponding file.
        jsonl_filename = jsonl_file.replace("chunks-", "embeddings-")
        if os.path.isfile(jsonl_filename): # File already processed
            continue
        else:
            print("Processing file: %s, file count: %d" %(jsonl_file, counter))

        data_df = pd.read_json(jsonl_file, lines=True)

        chunks = data_df["chunk"].values
        chunks = chunks.tolist()
        data_df["embedding"] = generate_text_embeddings(chunks,
                                                        batch_size=100)

        with open(jsonl_filename, "w") as json_file:
            json_file.write(data_df.to_json(orient='records', lines=True))

# ==============================================================================
#                        STORE EMBEDDINGS INTO CHROMADB
# ==============================================================================
def store_text_embeddings(df, collection, batch_size=500):

    # Generate ids
    df["id"] = df.index.astype(str)
    hashed_docs = df["file"].apply(
        lambda x: hashlib.sha256(x.encode()).hexdigest()[:16])
    df["id"] = hashed_docs + "-" + df["id"]

    # Process data in batches
    total_inserted = 0
    for i in range(0, df.shape[0], batch_size):
        # Create a copy of the batch and reset the index
        batch = df.iloc[i:i+batch_size].copy().reset_index(drop=True)

        ids        = batch["id"].tolist()
        documents  = batch["chunk"].tolist()
        embeddings = batch["embedding"].tolist()

        collection.add(ids=ids,
                       documents=documents,
                       embeddings=embeddings)
        total_inserted += len(batch)
        #print(f"Inserted {total_inserted} items...")

    #print(f"Finished inserting {total_inserted} items into collection '{collection.name}'")

def store(json_folder, target_collection):

    # Clear Cache
    chromadb.api.client.SharedSystemClient.clear_system_cache()

    # Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # Clear out any existing items in the collection
    try:
        # Clear out any existing items in the collection
        client.delete_collection(name=target_collection)
        print(f"Deleted existing collection '{target_collection}'")
    except Exception:
        print(f"Collection '{target_collection}' did not exist. Creating new.")

    # Create a brand new collection.
    collection = client.create_collection(name=target_collection,
                                          metadata={"hnsw:space": "cosine"})
    print(f"Created new empty collection '{target_collection}'")
    # print("Collection:", collection)

    # Get the list of embedding files
    jsonl_files = glob.glob(os.path.join(json_folder, f"embeddings-*.jsonl"))
    print("Number of files to process:", len(jsonl_files))

    # Process
    for jsonl_file in jsonl_files:
        print("Processing file:", jsonl_file)

        data_df = pd.read_json(jsonl_file, lines=True)
        
        # Store data
        store_text_embeddings(data_df, collection)

# ==============================================================================
#                             QUERY THE RAG SYSTEM
# ==============================================================================
def query():
    # STEP-1: Instantiate a pretrained model.
    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

    # STEP-2: Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # STEP-3: Create a query.
    user_query = "Is the Car 30 infringement in 2024 Abu Dhabi Grand Prix a fair penalty?"
    # query = input("Enter your F1 penalty-related query: ")
    print("Query:", user_query)
    embeddings = model.get_embeddings([user_query],
                                      output_dimensionality=EMBEDDING_DIMENSION)
    query_embedding = embeddings[0].values
    #print("Query embeddings:", query_embedding)

    # STEP-4: Retrieve relevant regulations.
    try:
        decision_collection = client.get_collection(name=DECISIONS_COLLECTION_NAME)
    except Exception:
        print(f"Collection '{DECISIONS_COLLECTION_NAME}' does not exist.")
        raise

    results_decision   = decision_collection.query(query_embeddings=[query_embedding],
                                                   n_results=2,)

    # STEP-5: Retrieve similar past decisions.
    try:
        regulation_collection = client.get_collection(name=REGULATIONS_COLLECTION_NAME)
    except Exception:
        print(f"Collection '{REGULATIONS_COLLECTION_NAME}' does not exist.")
        raise

    results_regulation = regulation_collection.query(query_embeddings=[query_embedding],
                                                     n_results=10,)

    # STEP-6: Create input for LLM.
    prompt_template = f"""
    Question:
    {user_query}

    Relevant FIA Sporting Regulations:
    {results_decision}

    Relevant historical decisions for comparison:
    {results_regulation}

    TASKS:
    1. Provide a clear explanation of the infringement and what the regulation requires.
    2. Compare the penalty with past similar penalties.
    3. Assess whether the penalty is fair compared to precedent.
    4. Highlight patterns or inconsistencies.

    If the answer is not in the context, say you cannot answer based on the information provided.
    Keep the explanation concise and readable.
    """

    # STEP-7: Send context and query to target LLM.
    llm_model = GenerativeModel(LLM_MODEL_NAME)
    print("\n Sending prompt to the LLM...")
    try:
        response = llm_model.generate_content(prompt_template)
        print("\n\n Final answer:\n")
        print(response.text)
    except Exception as e:
        print(f"An error occurred: {e}")

def main(args=None):

    if args.all:
        sync_cloud()
        
        chunk(DECISIONS_DATA_DIR, DECISION_JSON_DIR)
        chunk(REGULATIONS_DATA_DIR, REGULATION_JSON_DIR)
        
        embed(DECISION_JSON_DIR)
        embed(REGULATION_JSON_DIR)
        
        store(DECISION_JSON_DIR, DECISIONS_COLLECTION_NAME)
        store(REGULATION_JSON_DIR, REGULATIONS_COLLECTION_NAME)

        query()
    else:
        if args.sync:
            sync_cloud()
        if args.chunk:
            chunk(DECISIONS_DATA_DIR, DECISION_JSON_DIR)
            chunk(REGULATIONS_DATA_DIR, REGULATION_JSON_DIR)
        if args.embed:
            embed(DECISION_JSON_DIR)
            embed(REGULATION_JSON_DIR)
        if args.store:
            store(DECISION_JSON_DIR, DECISIONS_COLLECTION_NAME)
            store(REGULATION_JSON_DIR, REGULATIONS_COLLECTION_NAME)
        if args.query:
            query()

if __name__ == "__main__":
    # Generate the inputs arguments parser
    # if you type into the terminal '--help', it will provide the description
    parser = argparse.ArgumentParser(description="CLI")

    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync local dataset with cloud",
    )
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
        action="store_true",
        help="Query vector db and chat with LLM",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all steps sequentially",
    )

    args = parser.parse_args()

    main(args)
