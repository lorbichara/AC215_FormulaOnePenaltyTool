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

# Langchain
from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
#from langchain_experimental.text_splitter import SemanticChunker

# Vertex AI
from google import genai
from google.genai import types
from google.genai.types import Content, Part, GenerationConfig, ToolConfig
from google.genai import errors

import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel, Part

# GCP related parameters
GCP_PROJECT     = os.environ["GCP_PROJECT"]
#GCP_PROJECT      = "ac215-bhargav"
GCP_LOCATION     = "us-central1"

# LLM related parameters
EMBEDDING_MODEL     = "text-embedding-004"
EMBEDDING_DIMENSION = 256

LLM_MODEL_NAME = "gemini-2.5-flash"
#LLM_MODEL_NAME = "gemini-2.5-pro"

# Data related parameters
INPUT_FOLDER     = "dataset"
OUTPUT_FOLDER    = "outputs"

# ChromaDB related parameters
CHROMADB_HOST    = "ac215-rag-chromadb"
#CHROMADB_HOST    = "localhost"
CHROMADB_PORT    = 8000
CHUNK_SIZE       = 350
COLLECTION_NAME  = "ac215-f1-collection"


# ==============================================================================
#                                CHUNK THE DATA
# ==============================================================================
def chunk():
    print("chunk()")

    # Make dataset folders
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # Read PDF files.
    pdf_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.pdf')]
    assert len(pdf_files), "No PDF files found in '{INPUT_FOLDER}'. Aborting."
    print("Number of files to process:", len(pdf_files))

    # Process PDF files
    for pdf_file in pdf_files:
        filename = os.path.splitext(pdf_file)[0]
        filepath = os.path.join(INPUT_FOLDER, pdf_file)
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
        #text_splitter = SemanticChunker(embeddings)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size)

        # Perform the splitting
        text_chunks = text_splitter.create_documents([input_text])
        text_chunks = [doc.page_content for doc in text_chunks]
        print("Number of chunks:", len(text_chunks))
        assert len(text_chunks)
        
        # Save the chunks
        data_df = pd.DataFrame(text_chunks, columns=["chunk"])
        data_df["file"] = filename
        
        jsonl_filename = os.path.join(OUTPUT_FOLDER,
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

def embed():
    print("embed()")
    
    # Get the list of chunk files
    jsonl_files = glob.glob(os.path.join(OUTPUT_FOLDER,
                                         f"chunks-*.jsonl"))
    print("Number of files to process:", len(jsonl_files))

    for jsonl_file in jsonl_files:
        print("Processing file:", jsonl_file)

        data_df = pd.read_json(jsonl_file, lines=True)

        chunks = data_df["chunk"].values
        chunks = chunks.tolist()
        data_df["embedding"] = generate_text_embeddings(chunks,
                                                        batch_size=100)
        
        # Is it necessary to sleep here?
        time.sleep(2)

        # Save embeddings into corresponding file.
        jsonl_filename = jsonl_file.replace("chunks-", "embeddings-")
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
        print(f"Inserted {total_inserted} items...")

    print(f"Finished inserting {total_inserted} items into collection '{collection.name}'")

def store():
    print("store()")

    # Clear Cache
    chromadb.api.client.SharedSystemClient.clear_system_cache()

    from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
    
    # Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # Clear out any existing items in the collection
    try:
        # Clear out any existing items in the collection
        client.delete_collection(name=COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        print(f"Collection '{COLLECTION_NAME}' did not exist. Creating new.")

    # Create a brand new collection.
    collection = client.create_collection(name=COLLECTION_NAME,
                                          metadata={"hnsw:space": "cosine"})
    print(f"Created new empty collection '{COLLECTION_NAME}'")
    print("Collection:", collection)

    # Get the list of embedding files
    jsonl_files = glob.glob(os.path.join(OUTPUT_FOLDER, f"embeddings-*.jsonl"))
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
    print("query()")

    # Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    
    # Get the collection
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print(f"Collection '{COLLECTION_NAME}' does not exist.")
        raise

    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
    
    # query = "Is the Car 30 infringement in 2024 Abu Dhabi Grand Prix a fair penalty?"
    query = input("Enter your F1 penalty-related query: ")
    print("Query:", query)
    embeddings = model.get_embeddings([query],
                                      output_dimensionality=EMBEDDING_DIMENSION)
    query_embedding = embeddings[0].values
    #print("Query embeddings:", query_embedding)

    # 4: Query based on embedding value + lexical search filter
    results = collection.query(query_embeddings=[query_embedding], n_results=10,)    
    #results = collection.query(query_texts=[query], n_results=10)
    
    context_str = "\n---\n".join(results['documents'][0])
    print("\n Retrieved Context:")
    print(context_str)

    prompt_template = f"""
    You are an expert Formula 1 steward's assistant. Based ONLY on the context below, answer the user's question.
    If the answer is not in the context, say you cannot answer based on the information provided.

    Context:
    {context_str}

    Question:
    {query}
    """

    #print("prompt template")
    #print(prompt_template)
    
    llm_model = GenerativeModel(LLM_MODEL_NAME)
    print("\n Sending prompt to the LLM...")
    try:
        response = llm_model.generate_content(prompt_template)
        print("\n\n Final answer:\n")
        print(response.text)
    except Exception as e:
        return f"An error occurred: {e}"
        
def main(args=None):
    if args.chunk:
        chunk()
    
    if args.embed:
        embed()

    if args.store:
        store()

    if args.query:
        query()
        
if __name__ == "__main__":
    # Generate the inputs arguments parser
    # if you type into the terminal '--help', it will provide the description
    parser = argparse.ArgumentParser(description="CLI")

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

    args = parser.parse_args()

    main(args)
