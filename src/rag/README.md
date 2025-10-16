# F1 RAG

This directory contains a RAG pipeline.

## Overview
This project builds a Retrieval-Augmented Generation (RAG) pipeline designed to analyze and explain Formula 1 race penalties. It uses FIA steward decision documents to provide human-readable explanations and fairness assessments of penalties.

The pipeline automates the process of converting FIA PDF documents into structured, searchable text, generating embeddings with Vertex AI and storing them in a ChromaDB vector database for semantic retrieval. Users can query the system in natural language and ask questions such as: "Was the Car 30 infringement in the 2024 Abu Dhabi Grand Prix fair?”. The model will respond with context-grounded insights derived directly from FIA documentation.

The workflow is managed by `ac215_rag.py` which has 4 key modules:
- `chunk()`: Converts FIA decision documents into clean text and splits them into semantic chunks.
- `embed()`: Generates text embeddings using Google Vertex AI's text-embedding-004 model.
- `store_text_embeddings()`: Inserts the embeddings into a ChromaDB collection for vector search.
- `query()`: Performs retrieval and synthesis through the Gemini 2.5 LLM to produce final explanations.

This pipeline is a key component of the broader Formula One Penalty Explainer tool which also includes a data pipeline and an interface to facilitate user interactions.

## Running the Pipeline Locally
All commands should be run from the `src/rag` directory.

-   **Start the container:**
    ```bash
    sh docker-shell.sh
    ```

-   **Parse and chunk the documents:**
    ```bash
    python ac215_rag.py --chunk
    ```

-   **Create embeddings for the chunks:**
    ```bash
    python ac215_rag.py --embed
    ```

-   **Store the embeddings in ChromaDB:**
    ```bash
    python ac215_rag.py --store
    ```

-   **Make a query to ChromaDB and using the queried embeddings interact with LLM:**
    ```bash
    python ac215_rag.py --query
    ```

## Evidence of Running Instances
- **Running the container**
![alt text](image.png)

- **Parsing and chunking documents**
![alt text](image-1.png)

- **Create embeddings for the chunks**
![alt text](image-2.png)

- **Store the embeddings in ChromaDB**
![alt text](image-3.png)

- **Query ChromaDB**
![alt text](image-4.png)

## Design Decisions
#### Chunking
We are using the recursive character splitting mechanism to split on a hierarchy of separators (e.g., \n\n for paragraphs, then \n for new lines, then space, etc.). This is crucial for chunking the documents which are organized with sections, clauses, and numbered paragraphs. It preserves the author's logical structure, which is vital for the target context.

FIA decision documents generally follow a rigid, often numbered structure (e.g., "1. Factual Background," "1.1. Incident Description," "2. Decision Rationale," etc.). Because of this reason, we chose to use this method of chunking for our project.

#### Metadata
The primary advantage of storing metadata in the vector database for the embeddings is to help in filtering and to add context to the search results using the additional contextual information.

The file names for the FIA decision documents are too basic (Example: "2024 Abu Dhabi Grand Prix - Infringement xxx.pdf" to provide useful categorical filtering.

So, for now, we're skipping metadata creation in ChromaDB for this milestone. We'll revisit this later. If we find that contextual filtering could really improve our results, we'll certainly implement a way to enrich the embeddings with metadata in the next phase.