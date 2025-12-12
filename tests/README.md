# Testing

### CI and Testing
This project utilizes a robust CI/CD pipeline to ensure rapid and reliable software delivery. A critical component of this pipeline is our comprehensive testing strategy.
To enable Continuous Integration and Continuous Delivery (CI/CD), we have introduced two distinct types of automated test suites:

| Test Suite Type | Purpose | Environment |
| :--- | :--- | :--- |
| **Dry-Run Testing** | Performs fundamental unit and integration testing of components. | **No Functional API** (Backend server is mocked/unnecessary) |
| **API Validation** | Queries and validates live HTTP requests, ensuring correct behavior and data formats. | **Functional RAG Backend API Server** |


#### API Endpoint Integration Tests

Ths test suite uses **`pytest`** to verify the expected behavior and responses of the core API endpoints, focusing on standard HTTP status codes, etc.
This test suite will execute standalone without a functional API backend server.

| Test Function | Description | Key Assertions |
| :--- | :--- | :--- |
| `test_root_endpoint` | Verifies the **root endpoint (`/`)** is accessible and returns the expected welcome message. | **Status Code:** `200` (OK)<br>**Response Body:** Contains a `message` key with the value `"Formula One Penalty"`. |
| `test_root_returns_json` | Checks that the **root endpoint (`/`)** correctly sets the `Content-Type` header for **JSON** data. | **Status Code:** `200` (OK)<br>**Header:** `Content-Type` contains `"application/json"`. |
| `test_invalid_route_returns_404` | Ensures that accessing a **non-existent route** correctly triggers a `404 Not Found` response. | **Status Code:** `404` (Not Found) |
| `test_method_not_allowed` | Confirms that attempting to use an **unsupported HTTP method** (like `POST`) on a `GET`-only endpoint (like `/`) returns a `405 Method Not Allowed` error. | **Status Code:** `405` (Method Not Allowed) |
| `test_method_health` | Checks the **`/health` endpoint** for basic API operational status. | **Status Code:** `200` (OK)<br>**Header:** `Content-Type` is set to `"text/html; charset=utf-8"`<br>**Response Body:** Contains the text `"healthy"`. |

**Running the integration tests**
These tests can be run using the `pytest` command from the terminal:
```bash
pytest src/tests/integration -v --tb=short
```

#### API Endpoint System Tests
This test suite contains a set of integration tests designed to verify that the backend API server is running correctly and that all major endpoints respond as expected over HTTP. These tests use pytest and make real HTTP calls to the API, ensuring end-to-end functionality.

This test suite expects a fully functional API backend server which responds to *https* requests via `localhost:9000`.
The tests will **skip** executuin if the API backend is unresponsive.

| Test Method | Endpoint | Description | Assertions |
| :--- | :--- | :--- | :--- |
| `test_root_endpoint` | `/` (GET) | Verifies the main root endpoint is accessible. | **Status code 200**. Response is **JSON**. Contains a `"message"` key with the text `"Formula One Penalty"`. |
| `test_query` | `/query` (GET) | Tests the main **LLM query endpoint**, passing a specific prompt via a query parameter. | **Status code 200**. `Content-Type` is `text/html; charset=utf-8`. |

---

**Running the system tests**
These tests can be run using the `pytest` command from the terminal:
```bash
pytest src/tests/system -v --tb=short
```

#### API Unit Tests
This test suite contains a set of unit tests designed to verify the RAG implementation in rag.py file. These tests use pytest and make real HTTP calls to the API, ensuring end-to-end functionality.

The unit test coverage has reached 67%.

There are a total of 27 functions in rag.py file.

**Functions that are directly execised from unit tests**  
 - def delete_file()  
 - def get_country_adjectives_map()  
 - def create_country_params()  
 - def extract_countries_using_demonyms()   
 - def extract_domain_entities()  
 - def extract_place_from_text()  
 - def extract_car_num_from_txt()  
 - def parse_metadata_from_text()  
 - def is_file_interesting()  

 - def create_chunks()  
 - def create_embeddings()  
 - def store_embeddings()  
 - def download_file()
 - def extract_url_and_filename()
 - def query()  

**Functions that are indirectly execised from unit tests**  
 - def get_delta_files_to_process()  
 - def find_markers()  
 - def init_globals()  
 - def chunk_file()  
 - def chunk()  
 - def find_embed_files()  
 - def generate_embeddings()  
 - def embed()  
 - def store_text_embeddings()  
 - def store()  

**The functions that are not covered by unit tests as of now**
def create_user_query():
def preprocess_query():

**Running the system tests**

These tests can be run using the `pytest` command from the terminal:
```bash
pytest tests/unit/  --cov=src/rag/rag.py
pytest tests/unit/  --cov=src/rag/rag.py --cov-report=html
```
<img src="../reports/Unit_test_run.png">


#### Example snapshot of CI/CD execution on Github repository
<img src="../reports/Gitrun.png">

---
