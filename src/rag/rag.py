import os
import sys
import argparse
import pandas as pd
import glob
import hashlib
from pypdf import PdfReader


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

# ChromaDB related parameters

CHROMADB_HOST = os.environ["CHROMADB_HOST"]
CHROMADB_PORT = os.environ["CHROMADB_PORT"]
CHUNK_SIZE = 350

DECISIONS_COLLECTION = "ac215-f1-decisions_collection"
REGULATIONS_COLLECTION = "ac215-f1-regulations_collection"

# LLM related parameters
EMBEDDING_MODEL = "text-embedding-004"
EMBED_DIM = 256

DBG_LVL_HIGH = 2
DBG_LVL_MED = 1
DBG_LVL_LOW = 0
global_debug_level = DBG_LVL_LOW


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
ERROR_CODE_FILE_CORRUPTED = 2
ERROR_CODE_ALREADY_CHUNKED = 3
ERROR_CODE_CHROMADB_FAILED = 4

HTTP_CODE_GENERIC_SUCCESS = 200
HTTP_CODE_GENERIC_FAILURE = 400


# =============================================================================
#                                CHUNK THE DATA
# =============================================================================
def is_file_interesting(file_name):
    strs = ["Decision", "Summons", "Offence", "Infringement", "regulations"]
    for substr in strs:
        if substr in file_name:
            return True
    return False


def remove_file(filepath):
    try:
        os.remove(filepath)
    except PermissionError:
        print(f"Permission denied: '{filepath}'. Check file permissions or lsof.")
    except Exception as e:
        print(f"An error occurred: {e}")


def chunk_file(filepath, filename, json_folder, counter):
    DEBUG(DBG_LVL_LOW, "\nCOUNT: %d, FILE: %s" % (counter, filepath))
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
        if chunk_exists:  # Delete the file and recreate it
            DEBUG(DBG_LVL_LOW, "Deleting: %s" % (filepath))
            # remove_file(filepath)
            return ERROR_CODE_SUCCESS
        if embed_exists:
            assert True, "Invalid scenario"

    DEBUG(DBG_LVL_LOW, "CHUNKING: %s, FILE COUNT-%d" % (filepath, counter))
    return ERROR_CODE_SUCCESS

    input_text = ""
    try:
        pdf_reader = PdfReader(filepath)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                input_text += page_text.replace("\n", " ") + " "
    except Exception as e:
        DEBUG(DBG_LVL_MED, f"Error processing {filepath}: {e}")
        return ERROR_CODE_FILE_CORRUPTED

    # Init the splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE)

    # Perform the splitting
    text_chunks = None
    text_chunks = text_splitter.create_documents([input_text.lower()])
    text_chunks = [doc.page_content for doc in text_chunks]
    # print("Number of chunks:", len(text_chunks))
    assert len(text_chunks)

    # Save the chunks
    data_df = pd.DataFrame(text_chunks, columns=["chunk"])
    data_df["file"] = filename

    jsonl_filename = os.path.join(json_folder, f"chunks-{filename}.jsonl")
    DEBUG(DBG_LVL_LOW, "Writing chunks to: " + jsonl_filename)
    with open(jsonl_filename, "w") as json_file:
        json_file.write(data_df.to_json(orient="records", lines=True))

    return ERROR_CODE_SUCCESS


def chunk(tag, json_folder, limit):

    # Make dataset folders
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
    os.makedirs(json_folder, exist_ok=True)

    # Initialize a client
    storage_client = storage.Client()

    # Ensure the destination directory exists
    assert os.path.exists(DATASET_DIR), DATASET_DIR + " does not exist"

    total_files = 0
    files_failed = 0
    files_chunked_now = 0
    considering_counter = 0

    try:
        # Get the bucket object
        bucket = storage_client.bucket(GCP_BUCKET)

        # List all blobs (files and folder objects)
        blobs = bucket.list_blobs()

        for blob in blobs:
            if total_files >= limit:
                break

            # GCS doesn't have true folders; they are objects ending in '/'.
            # prefixes are considered as folders and non-prefixes are
            # considered as files.

            if not blob.name.endswith("/"):  # This is a file object
                if "raw_pdfs/" + tag in blob.name:
                    # Skip the files that are not of interest.
                    if not is_file_interesting(blob.name):
                        # print(f"    -> Not interesting: {blob.name}")
                        continue

                    # DEBUG(DBG_LVL_LOW, f"gs://{GCP_BUCKET}/{blob.name}")
                    considering_counter += 1

                    filename = os.path.basename(blob.name)
                    filename = os.path.splitext(filename)[0]

                    filepath = ROOT_DIR + "/" + blob.name

                    ret_val = chunk_file(
                        filepath, filename, json_folder, considering_counter
                    )
                    if ret_val == ERROR_CODE_SUCCESS:
                        DEBUG(DBG_LVL_LOW, f"->CHUNKED: {filepath}")
                        files_chunked_now += 1
                    elif ret_val == ERROR_CODE_FILE_CORRUPTED:
                        DEBUG(DBG_LVL_HIGH, f"->CORRUPTED: {filepath}")
                        files_failed += 1
                    elif ret_val == ERROR_CODE_ALREADY_CHUNKED:
                        # ALREADY CHUNKED
                        pass

                    total_files += 1
    except Exception as e:
        ret_str = "INFRA FAILED. Error code: " + str(e) + "\n"
        return ret_str, ERROR_CODE_GCS_FAILURE

    ret_str = "No of files corrupted: " + str(files_failed) + "\n"
    ret_str += "No of files processed now: " + str(files_chunked_now) + "\n"
    ret_str += "Total no of files in the corpus: " + str(total_files)

    return ret_str, ERROR_CODE_SUCCESS


def create_chunks(limit=sys.maxsize):
    DEBUG(DBG_LVL_LOW, "CHUNK LIMIT: " + str(limit))
    ret_str, ret_val = chunk("decisions", DECISION_JSON_DIR, int(limit))
    ret_str_1 = "\nChunking for decision files done. \n" + ret_str + "\n"
    if ret_val == ERROR_CODE_GCS_FAILURE:
        DEBUG(DBG_LVL_HIGH, ret_str_1)
        return ret_str_1, ERROR_CODE_GCS_FAILURE

    ret_str, ret_val = chunk("regulations", REGULATION_JSON_DIR, int(limit))
    ret_str_2 = "\nChunking for regulation files done. \n" + ret_str

    ret_str = ret_str_1 + ret_str_2
    DEBUG(DBG_LVL_MED, ret_str)
    if ret_val == ERROR_CODE_GCS_FAILURE:
        return ret_str, ERROR_CODE_GCS_FAILURE

    return ret_str, ERROR_CODE_SUCCESS


# =============================================================================
#                                GENERATE EMBEDDINGS
# =============================================================================
def generate_embeddings(chunks, batch_size=250):  # Max for Vertex AI
    all_embeds = []

    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        try:
            embeddings = model.get_embeddings(batch, output_dimensionality=EMBED_DIM)
            all_embeds.extend([embedding.values for embedding in embeddings])
        except Exception as e:
            DEBUG(DBG_LVL_HIGH, f"Embeddings failed. Last error: {str(e)}")
            raise

    assert len(all_embeds)
    return all_embeds


def embed(json_folder, limit):
    ret_val = ERROR_CODE_SUCCESS

    # Get the list of chunk files
    jsonl_files = glob.glob(os.path.join(json_folder, "chunks-*.jsonl"))
    DEBUG(DBG_LVL_LOW, "Number of files to process: %d" % len(jsonl_files))

    file_counter = 0
    embedded_now = 0
    for jsonl_file in jsonl_files:
        if file_counter >= limit:
            break
        file_counter += 1

        # Save embeddings into corresponding file.
        jsonl_filename = jsonl_file.replace("chunks-", "embeddings-")
        if os.path.isfile(jsonl_filename):  # File already processed
            DEBUG(DBG_LVL_LOW, "%s - ALREADY DONE." % jsonl_file)
            continue
        else:
            DEBUG(DBG_LVL_MED, "%s - NOW EMBEDDING" % jsonl_file)

        data_df = pd.read_json(jsonl_file, lines=True)

        chunks = data_df["chunk"].values
        chunks = chunks.tolist()
        try:
            data_df["embedding"] = generate_embeddings(chunks, batch_size=100)
        except Exception as e:
            DEBUG(DBG_LVL_LOW, f"Embeddings failed totally. Error: {str(e)}")

            ret_val = ERROR_CODE_GCS_FAILURE
            break

        embedded_now += 1
        with open(jsonl_filename, "w") as json_file:
            json_file.write(data_df.to_json(orient="records", lines=True))

    ret_str = "No of files embedded now: " + str(embedded_now) + "\n"
    prev_embedded = file_counter - embedded_now
    ret_str += "No of previously embedded files: " + str(prev_embedded) + "\n"
    ret_str += "Total no of embedded files: " + str(file_counter) + "\n"

    return ret_str, ret_val


def create_embeddings(limit=sys.maxsize):
    DEBUG(DBG_LVL_LOW, "EMBEDDING LIMIT: " + str(limit))
    ret_str, ret_val = embed(DECISION_JSON_DIR, int(limit))
    ret_str_1 = "\nEmbedding for decision files done. \n" + ret_str + "\n"
    if ret_val == ERROR_CODE_GCS_FAILURE:
        DEBUG(DBG_LVL_HIGH, ret_str_1)
        return ret_str_1, ERROR_CODE_GCS_FAILURE

    ret_str, ret_val = embed(REGULATION_JSON_DIR, int(limit))
    ret_str_2 = "\nEmbedding for regulation files done. \n" + ret_str + "\n"

    ret_str = ret_str_1 + ret_str_2
    DEBUG(DBG_LVL_MED, ret_str)
    if ret_val == ERROR_CODE_GCS_FAILURE:
        return ret_str, ERROR_CODE_GCS_FAILURE

    return ret_str, ERROR_CODE_SUCCESS


# =============================================================================
#                        STORE EMBEDDINGS INTO CHROMADB
# =============================================================================
def store_text_embeddings(df, collection, batch_size=500):

    # Generate ids
    df["id"] = df.index.astype(str)
    hashed_docs = df["file"].apply(
        lambda x: hashlib.sha256(x.encode()).hexdigest()[:16]
    )
    df["id"] = hashed_docs + "-" + df["id"]

    # Process data in batches
    total_inserted = 0
    try:
        for i in range(0, df.shape[0], batch_size):
            # Create a copy of the batch and reset the index
            batch = df.iloc[i : i + batch_size].copy().reset_index(drop=True)

            ids = batch["id"].tolist()
            documents = batch["chunk"].tolist()
            embeddings = batch["embedding"].tolist()

            collection.add(ids=ids, documents=documents, embeddings=embeddings)
            total_inserted += len(batch)
    except Exception as e:
        DEBUG(DBG_LVL_HIGH, f"DB store failed. Error: {str(e)}")
        raise


def store(json_folder, target_collection, testing):
    ret_val = ERROR_CODE_SUCCESS

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

    # Get the list of embedding files
    jsonl_files = glob.glob(os.path.join(json_folder, "embeddings-*.jsonl"))
    DEBUG(DBG_LVL_MED, "Number of files to process: %d" % len(jsonl_files))

    # Process
    stored_files = 0
    for jsonl_file in jsonl_files:
        if testing:
            break
        DEBUG(DBG_LVL_LOW, "Processing file: %s" % jsonl_file)

        data_df = pd.read_json(jsonl_file, lines=True)
        try:
            # Store data
            store_text_embeddings(data_df, collection)
        except Exception:
            DEBUG(DBG_LVL_HIGH, "Failed to store %s in chromadb:" % jsonl_file)
            ret_val = ERROR_CODE_CHROMADB_FAILED
            break
        stored_files += 1

    ret_str = "No of files stored: " + str(stored_files) + "\n"
    return ret_str, ret_val


def store_embeddings(testing=False):
    ret_str, ret_val = store(DECISION_JSON_DIR, DECISIONS_COLLECTION, bool(testing))
    ret_str_1 = "\nStoring of embeddings of decision files in chromadb done."
    ret_str_1 += "\n" + ret_str + "\n"
    if ret_val != ERROR_CODE_SUCCESS:
        DEBUG(DBG_LVL_HIGH, ret_str_1)
        return ret_str_1, HTTP_CODE_GENERIC_FAILURE

    ret_str, ret_val = store(REGULATION_JSON_DIR, REGULATIONS_COLLECTION, bool(testing))
    ret_str_2 = "\nStoring of embeddings of regulation files in chromadb done."
    ret_str_2 += "\n" + ret_str

    ret_str = ret_str_1 + ret_str_2
    DEBUG(DBG_LVL_MED, ret_str)
    return ret_str, ret_val


# ==============================================================================
#                             QUERY THE RAG SYSTEM
# ==============================================================================
def query(user_query, llm_choice: str = PARAM_GOOGLE_LLM):
    ret_val = ERROR_CODE_SUCCESS

    # STEP-1: Instantiate a pretrained model.
    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

    # STEP-2: Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # STEP-3: Create embeddings for the user query.
    DEBUG(DBG_LVL_HIGH, "Query: %s" % user_query)

    user_query = user_query.lower()
    try:
        embeddings = model.get_embeddings([user_query], output_dimensionality=EMBED_DIM)
    except Exception as e:
        ret_str = f"Failed to generate embeddings. Last error: {str(e)}"
        DEBUG(DBG_LVL_HIGH, ret_str)
        return ret_str, ERROR_CODE_GCS_FAILURE

    query_embedding = embeddings[0].values
    DEBUG(DBG_LVL_MED, "Query embeddings: " + str(query_embedding))

    # STEP-4: Retrieve similar past decisions.
    try:
        dec_collection = client.get_collection(name=DECISIONS_COLLECTION)
    except Exception:
        ret_str = f"Collection '{DECISIONS_COLLECTION}' does not exist."
        DEBUG(DBG_LVL_HIGH, ret_str)
        return ret_str, ERROR_CODE_CHROMADB_FAILED

    results_decision = dec_collection.query(
        query_embeddings=[query_embedding],
        include=["documents", "distances"],
        n_results=5,
    )

    # STEP-5: Retrieve relevant regulations.
    try:
        reg_collection = client.get_collection(name=REGULATIONS_COLLECTION)
    except Exception:
        ret_str = f"Collection '{REGULATIONS_COLLECTION}' does not exist."
        DEBUG(DBG_LVL_HIGH, ret_str)
        return ret_str, ERROR_CODE_CHROMADB_FAILED

    results_regulation = reg_collection.query(
        query_embeddings=[query_embedding],
        n_results=10,
    )

    # STEP-6: Create input for LLM.
    prompt_template = f"""
    Question:
    {user_query}

    Relevant FIA Sporting Regulations:
    {results_regulation}

    Relevant historical decisions for comparison:
    {results_decision}

    Perform symantic similarity of the user query against results_decisions and results_regulations and perform the following tasks.
    Convert text into lowercase if it provides better accuracy.

    TASKS:
    1. Provide a clear explanation of the infringement and what the regulation
       requires.
    2. Compare the penalty with past similar penalties.
    3. Assess whether the penalty is fair compared to precedent.
    4. Highlight patterns or inconsistencies.

    Explain each task in a simple and concise manner.
    Make the headings of the output of each task as CAPITAL LETTERS.

    If the answer is not in the context, say you cannot answer based on the
    information provided.
    """
    DEBUG(DBG_LVL_MED, prompt_template)

    # STEP-7: Send context and query to target LLM.
    DEBUG(DBG_LVL_HIGH, "llm_choice: " + str(llm_choice))
    selected_llm = str(LLM_MODELS[llm_choice])
    DEBUG(DBG_LVL_HIGH, "Selected LLM: " + selected_llm)

    llm_model = GenerativeModel(selected_llm)
    DEBUG(DBG_LVL_HIGH, "\nSending prompt to the LLM...")

    DEBUG(DBG_LVL_MED, "\n\nLLM RESPONSE")
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
