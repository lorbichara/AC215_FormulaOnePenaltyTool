import os
import argparse
import pandas as pd
import json
import time
import glob
import hashlib
from pypdf import PdfReader
from tqdm import tqdm


# Langchain
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
DATASET_DIR            = "input"
DECISIONS_DATA_DIR     = "input/decisions"
REGULATIONS_DATA_DIR   = "input/regulations"

JSON_OUTPUT_DIR     = "output"
DECISION_JSON_DIR   = "output/decision_jsons"
REGULATION_JSON_DIR = "output/regulation_jsons"

# ChromaDB related parameters
import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings

CHROMADB_HOST   = os.environ["CHROMADB_HOST"]
CHROMADB_PORT   = os.environ["CHROMADB_PORT"]
CHROMADB_PORT    = 8000
CHUNK_SIZE       = 350

DECISIONS_COLLECTION_NAME  = "ac215-f1-decisions_collection"
REGULATIONS_COLLECTION_NAME  = "ac215-f1-regulations_collection"

# LLM related parameters
EMBEDDING_MODEL     = "text-embedding-004"
EMBEDDING_DIMENSION = 256

LLM_MODEL_NAME = "gemini-2.5-flash"
FINETUNED_MODEL_NAME = (
    "projects/ac215-f1penaltytool/locations/us-central1/endpoints/547845962190553088"
)

DEBUG_LEVEL_HIGH = 2
DEBUG_LEVEL_MED  = 1
DEBUG_LEVEL_LOW  = 0
global_debug_level = DEBUG_LEVEL_MED
def DEBUG(level, input_string):
    if level >= global_debug_level:
        print(input_string)

# ==============================================================================
#                                CHUNK THE DATA
# ==============================================================================
# Error codes for chunking process
CHUNK_RETURN_SUCCESS        = 0
CHUNK_RETURN_GCS_FAILURE    = 1
CHUNK_RETURN_FILE_CORRUPTED = 2
CHUNK_RETURN_ALREAD_CHUNKED = 3

def is_file_interesting(file_name):
    substrings = ["Decision", "Summons", "Offence", "Infringement", "regulations"]
    for substr in substrings:
        if substr in file_name:
            return True
    return False

def chunk_file(filepath, filename, json_folder, counter):
    DEBUG(DEBUG_LEVEL_LOW, "Processing file: %s, filecount-%d" %(filepath, counter))
    DEBUG(DEBUG_LEVEL_LOW, "filename: %s" %(filename))

    embeddings_jsonl = os.path.join(json_folder,
                                    f"embeddings-{filename}.jsonl")
    DEBUG(DEBUG_LEVEL_LOW, "Checking for embedding file: " + str(embeddings_jsonl))
     
    if os.path.isfile(embeddings_jsonl): # File already processed
        return CHUNK_RETURN_ALREAD_CHUNKED
    
    input_text = ""
    try:
        pdf_reader = PdfReader(filepath)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                input_text += page_text.replace('\n', ' ') + " "
    except Exception as e:
        DEBUG(DEBUG_LEVEL_MED, f"Error processing {filepath}: {e}")
        return CHUNK_RETURN_FILE_CORRUPTED

    # Init the splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE)

    # Perform the splitting
    text_chunks = None
    text_chunks = text_splitter.create_documents([input_text])
    text_chunks = [doc.page_content for doc in text_chunks]
    #print("Number of chunks:", len(text_chunks))
    assert len(text_chunks)

    # Save the chunks
    data_df = pd.DataFrame(text_chunks, columns=["chunk"])
    data_df["file"] = filename

    jsonl_filename = os.path.join(json_folder,
                                  f"chunks-{filename}.jsonl")
    
    DEBUG(DEBUG_LEVEL_LOW, "Writing chunks to: " + jsonl_filename)
    with open(jsonl_filename, "w") as json_file:
        json_file.write(data_df.to_json(orient='records', lines=True))

    return CHUNK_RETURN_SUCCESS

def chunk(tag, json_folder):

    # Make dataset folders
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
    os.makedirs(json_folder, exist_ok=True)

    # Initialize a client
    storage_client = storage.Client()

    # Ensure the destination directory exists
    assert os.path.exists(DATASET_DIR), DATASET_DIR + " does not exist"

    total_files         = 0
    files_failed        = 0
    files_chunked_now   = 0
    considering_counter = 0
    
    try:
        # Get the bucket object
        bucket = storage_client.bucket(GCP_BUCKET)

        # List all blobs (files and folder objects)
        blobs = bucket.list_blobs()

        counter = 0
        for blob in blobs:

            # GCS doesn't have true folders; they are objects ending in '/'.
            # prefixes are considered as folders and non-prefixes are considered as files.

            if not blob.name.endswith('/'): # This is a file object
                if "raw_pdfs/"+tag in blob.name:
                    # Skip the files that are not of interest.
                    if not is_file_interesting(blob.name):
                        # print(f"    -> Not interesting: {blob.name}")
                        continue
                    
                    DEBUG(DEBUG_LEVEL_LOW, f"  **[FILE]**: gs://{GCP_BUCKET}/{blob.name}")
                    considering_counter += 1
                    
                    filename = os.path.basename(blob.name)
                    filename = os.path.splitext(filename)[0]
                    ret_val = chunk_file(blob.name, filename,
                                         json_folder, considering_counter)
                    if ret_val == CHUNK_RETURN_SUCCESS:
                        DEBUG(DEBUG_LEVEL_LOW, f"    -> CHUNKED: {filename}")
                        files_chunked_now += 1
                    elif ret_val == CHUNK_RETURN_FILE_CORRUPTED:
                        DEBUG(DEBUG_LEVEL_HIGH, f"    -> CORRUPTED: {filename}")
                        files_failed += 1
                    elif ret_val == CHUNK_RETURN_ALREAD_CHUNKED:
                        DEBUG(DEBUG_LEVEL_LOW, f"    -> ALREADY CHUNKED: {filename}")
                        pass
                    
                    total_files += 1

    except Exception as e:
        ret_str = "INFRA FAILED. Error code: " + str(e) + "\n"
        return ret_str, CHUNK_RETURN_GCS_FAILURE
    
    ret_str  = "No of files corrupted: " + str(files_failed) + "\n"
    ret_str += "No of files processed now: " + str(files_chunked_now) + "\n"
    ret_str += "Total no of files in the corpus: " + str(total_files)

    return ret_str, CHUNK_RETURN_SUCCESS

def create_chunks():
    ret_str, ret_val = chunk("decisions", DECISION_JSON_DIR)
    ret_str_1 = "\nChunking for decision files done. \n" + ret_str + "\n"
    if ret_val == CHUNK_RETURN_GCS_FAILURE:
        DEBUG(DEBUG_LEVEL_HIGH, ret_str_1)
        return ret_str_1, 1
    
    ret_str, ret_val = chunk("regulations", REGULATION_JSON_DIR)
    ret_str_2 = "\nChunking for regulation files done. \n" + ret_str
    
    ret_str = ret_str_1 + ret_str_2
    DEBUG(DEBUG_LEVEL_MED, ret_str)

    if ret_val != CHUNK_RETURN_SUCCESS:
        return ret_str, 1
    
    return ret_str, 0


# ==============================================================================
#                                GENERATE EMBEDDINGS
# ==============================================================================
EMBED_RETURN_SUCCESS = 0
EMBED_GCS_FAILURE    = 1

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
            DEBUG(DEBUG_LEVEL_HIGH, f"Failed to generate embeddings. Last error: {str(e)}")
            raise

    assert len(all_embeddings)
    return all_embeddings

def embed(json_folder):

    # Get the list of chunk files
    jsonl_files = glob.glob(os.path.join(json_folder,
                                         f"chunks-*.jsonl"))
    DEBUG(DEBUG_LEVEL_LOW, "Number of files to process: %d" %len(jsonl_files))

    files_failed = 0
    file_counter = 0
    embedded_now = 0
    for jsonl_file in jsonl_files:
        file_counter += 1
        
        # Save embeddings into corresponding file.
        jsonl_filename = jsonl_file.replace("chunks-", "embeddings-")
        if os.path.isfile(jsonl_filename): # File already processed
            DEBUG(DEBUG_LEVEL_LOW, "%s - ALREADY EMBEDDED. File count: %d" %(jsonl_file, file_counter))
            continue
        else:
            DEBUG(DEBUG_LEVEL_MED, "%s - NOW EMBEDDING, File count: %d" %(jsonl_file, file_counter))
        
        data_df = pd.read_json(jsonl_file, lines=True)

        chunks = data_df["chunk"].values
        chunks = chunks.tolist()
        try:
            data_df["embedding"] = generate_text_embeddings(chunks,
                                                            batch_size=100)
        except errors.APIError as e:
            failed_files += 1
            continue
        
        embedded_now += 1

        with open(jsonl_filename, "w") as json_file:
            json_file.write(data_df.to_json(orient='records', lines=True))

    ret_str  = "No of files embedded now               : " + str(embedded_now) + "\n"
    ret_str += "No of previously embedded files        : " + str(file_counter - embedded_now) + "\n"
    ret_str += "Total no of embedded files             : " + str(file_counter) + "\n"
    ret_str += "No of files for which embeddings failed: " + str(files_failed) + "\n"
     
    return ret_str

def create_embeddings():
    ret_str = embed(DECISION_JSON_DIR)
    ret_str_1 = "\nEmbedding for decision files done. \n" + ret_str + "\n"
     
    ret_str = embed(REGULATION_JSON_DIR)
    ret_str_2 = "\nEmbedding for regulation files done. \n" + ret_str + "\n"

    ret_str = ret_str_1 + ret_str_2 
    DEBUG(DEBUG_LEVEL_MED, ret_str)

    return ret_str

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
    try:
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
    except errors.APIError as e:
        DEBUG(DEBUG_LEVEL_HIGH, f"Failed to generate embeddings. Last error: {str(e)}")


def store(json_folder, target_collection):

    # Clear Cache
    chromadb.api.client.SharedSystemClient.clear_system_cache()

    # Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # Clear out any existing items in the collection
    try:
        # Clear out any existing items in the collection
        client.delete_collection(name=target_collection)
        DEBUG(DEBUG_LEVEL_LOW, f"Deleted existing collection '{target_collection}'")
    except Exception:
        DEBUG(DEBUG_LEVEL_LOW, f"Collection '{target_collection}' did not exist. Creating new.")

    # Create a brand new collection.
    collection = client.create_collection(name=target_collection,
                                          metadata={"hnsw:space": "cosine"})
    DEBUG(DEBUG_LEVEL_HIGH, f"Created new empty collection '{target_collection}'")
    DEBUG(DEBUG_LEVEL_LOW,  "Collection: %s" %collection)

    # Get the list of embedding files
    jsonl_files = glob.glob(os.path.join(json_folder, f"embeddings-*.jsonl"))
    DEBUG(DEBUG_LEVEL_MED, "Number of files to process: %d" %len(jsonl_files))

    # Process
    files_failed = 0
    stored_files = 0
    for jsonl_file in jsonl_files:
        DEBUG(DEBUG_LEVEL_LOW, "Processing file: %s" %jsonl_file)

        data_df = pd.read_json(jsonl_file, lines=True)        
        try:
            # Store data
            store_text_embeddings(data_df, collection)
        except Exception:
            DEBUG(DEBUG_LEVEL_HIGH, "Failed to store %s in chromadb:" %jsonl_file)
            files_failed += 1
        stored_files += 1

    ret_str  = "No of files stored          : " + str(stored_files) + "\n"
    ret_str += "No of files failed to upload: " + str(files_failed) + "\n"
    return ret_str

def store_embeddings():
    ret_str = store(DECISION_JSON_DIR, DECISIONS_COLLECTION_NAME)
    ret_str_1 = "\nStoring of embeddings of decision files in chromadb done.\n" + ret_str + "\n"

    ret_str = store(REGULATION_JSON_DIR, REGULATIONS_COLLECTION_NAME)
    ret_str_2 = "\nStoring of embeddings of regulation files in chromadb done.\n" + ret_str

    ret_str = ret_str_1 + ret_str_2 
    DEBUG(DEBUG_LEVEL_MED, ret_str)
 
    return ret_str

# ==============================================================================
#                             QUERY THE RAG SYSTEM
# ==============================================================================
def query(user_query):
    # STEP-1: Instantiate a pretrained model.
    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

    # STEP-2: Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # STEP-3: Create a query.
    DEBUG(DEBUG_LEVEL_HIGH, "Query: %s" %user_query)
    embeddings = model.get_embeddings([user_query],
                                      output_dimensionality=EMBEDDING_DIMENSION)
    query_embedding = embeddings[0].values
    DEBUG(DEBUG_LEVEL_LOW, "Query embeddings: " + str(query_embedding))

    # STEP-4: Retrieve relevant regulations.
    try:
        decision_collection = client.get_collection(name=DECISIONS_COLLECTION_NAME)
    except Exception:
        DEBUG(DEBUG_LEVEL_HIGH, f"Collection '{DECISIONS_COLLECTION_NAME}' does not exist.")
        raise

    results_decision   = decision_collection.query(query_embeddings=[query_embedding],
                                                   n_results=2,)

    # STEP-5: Retrieve similar past decisions.
    try:
        regulation_collection = client.get_collection(name=REGULATIONS_COLLECTION_NAME)
    except Exception:
        DEBUG(DEBUG_LEVEL_HIGH, f"Collection '{REGULATIONS_COLLECTION_NAME}' does not exist.")
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

    Explain each task in a simple and concise manner.

    If the answer is not in the context, say you cannot answer based on the information provided.
    Keep the explanation concise and readable.
    """

    # STEP-7: Send context and query to target LLM.
    # llm_model = GenerativeModel(LLM_MODEL_NAME)
    llm_model = GenerativeModel(FINETUNED_MODEL_NAME)

    DEBUG(DEBUG_LEVEL_HIGH, "\nSending prompt to the LLM...")
    answer = ""
    try:
        response = llm_model.generate_content(prompt_template)
        answer = response.text
    except Exception as e:
        answer = f"\nAn error occurred: {e}"

    DEBUG(DEBUG_LEVEL_HIGH, answer)
    return answer

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
