# APIs
The backend APIs interact with a **Retrieval-Augmented Generation (RAG)** architecture to process, store, and query information related to F1 penalties and regulations.

The API is served by a Uvicorn web server. The base URL will depend on the deployment environment (e.g., `http://localhost:8000` for local development).


#### **API ENDPOINT: '/'**
This endpoint provides a simple welcome message.

| Method | Endpoint | Description | Response Content Type |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Welcome message to the API. | `application/json` |

* *Example Response (Status 200):* *
```json
{
  "message": "Welcome to Formula One Penalty Analysis Tool"
}
```
#### **API ENDPOINT: '/chunk'**
This endpoint is used to manage the data processing pipeline, transforming source documents (regulations, etc.) into a searchable vector database.

| Method | Endpoint | Description | Response Content Type |
| :--- | :--- | :--- | :--- |
| 'GET' | '/chunk' | Peforms chunking and returns status string | 'text/html'|

'limit: Specifies the maximum number of documents or chunks to process`

**_Example Request:_**
```http
GET /chunk
```
**_Response Format_**
| Detail | Description |
| :--- | :--- |
| Content Type | `text/html` |
| Body | Contains the generated text response from the RAG engine. This is generally used for debugging purpose. |
| Status Code | The status code from the internal RAG process is returned directly: |

`Status Code Details:`
* 200 (OK): Query processed successfully.
* Other Codes: Indicate an error during the RAG execution (e.g., retrieval failure, LLM timeout).


#### **API ENDPOINT: '/embed'**
This endpoint is used to create numerical vector representations (embeddings) for each document chunk.

| Method | Endpoint | Description | Response Content Type |
| :--- | :--- | :--- | :--- |
| 'GET' | '/embed' | Performs embedding and returns status string | 'text/html'|

**_Example Request:_**
```html
GET /embed
```
'limit: Specifies the maximum number of documents or chunks to process`
**_Response Format_**
| Detail | Description |
| :--- | :--- |
| Content Type | `text/html` |
| Body | Contains the generated text response from the RAG engine. This is generally used for debugging purpose. |
| Status Code | The status code from the internal RAG process is returned directly: |

`Status Code Details:`
* 200 (OK): Query processed successfully.
* Other Codes: Indicate an error during the RAG execution (e.g., retrieval failure, LLM timeout).


#### **API ENDPOINT: '/store'**
This endpoint is used to store the generated embeddings into the Vector Database for retrieval.

| Method | Endpoint | Description | Response Content Type |
| :--- | :--- | :--- | :--- |
| 'GET' | '/store' | Stores embeddings in Chromadb and returns status string | 'text/html'|

**_Example Request:_**
```http
GET /store
```
**_Response Format_**
| Detail | Description |
| :--- | :--- |
| Content Type | `text/html` |
| Body | Contains the generated text response from the RAG engine. This is generally used for debugging purpose. |
| Status Code | The status code from the internal RAG process is returned directly: |

`Status Code Details:`
* 200 (OK): Query processed successfully.
* Other Codes: Indicate an error during the RAG execution (e.g., retrieval failure, LLM timeout).

#### **API ENDPOINT: /query**
This endpoint is primarily used to interact with the LLM and RAG system, retrieving relevant information and generating answers based on the processed F1 data.

| Method | Endpoint | Description | Response Content Type |
| :--- | :--- | :--- | :--- |
| 'GET' | '/query' | Sends query to RAG engine and returns status string | 'text/html'|

**Example Request:**
```http
GET /query/?prompt=What is the standard penalty for an unsafe release during a pit stop?
```

**Response Format**
| Detail | Description |
| :--- | :--- |
| Content Type | `text/html` |
| Body | Contains the generated text response from the Language Model. |
| Status Code | The status code from the internal RAG process is returned directly: |

`Status Code Details:`
* 200 (OK): Query processed successfully.
* Other Codes: Indicate an error during the RAG execution (e.g., retrieval failure, LLM timeout).


#### **API ENDPOINT: '/health'**
This endpoint is primarily for unit testing.

| Method | Endpoint | Description | Response Content Type |
| :--- | :--- | :--- | :--- |
| 'GET' | '/health' | Returns the status ""healthy" | 'text/html'|

#### Example snapshot of API backend server interface using http.
The examples produced here are based on a local instantiation of API backend server that responds to http://localhost:8000
![](reports/API_Server.png).

---