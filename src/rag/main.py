import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware

import rag as rag


PARAM_GOOGLE_LLM = "gemini-default"
PARAM_FINE_TUNED = "gemini-finetuned"


UVICORN_PORT = os.environ["UVICORN_PORT"]

# Setup FastAPI app
app = FastAPI(title="API Server", description="API Server", version="v1")

# Enable CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes
@app.get("/")
async def get_index():
    return {"message": "Welcome to Formula One Penalty Analysis Tool"}


@app.get("/health")
async def health_check():
    ret_str = "healthy"
    html_content = f"""
        {ret_str}
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/chunk/")
async def create_chunks(limit: int = sys.maxsize):
    ret_str, ret_val = rag.create_chunks(limit)
    html_content = f"""
        {ret_str}
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/embed/")
async def create_embeddings(limit: int):
    ret_str, ret_val = rag.create_embeddings(limit)
    html_content = f"""
        {ret_str}
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/store/")
async def store_embeddings(testing: bool):
    ret_str, ret_val = rag.store_embeddings(testing)
    html_content = f"""
        {ret_str}
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/query/")
async def query_llm(prompt: str, llm_choice: str = PARAM_GOOGLE_LLM):

    ret_str, ret_val = rag.query(prompt, llm_choice)

    if ret_val == rag.HTTP_CODE_GENERIC_SUCCESS:
        return JSONResponse(content={"response": ret_str}, status_code=ret_val)
    else:
        http_status = ret_val if ret_val >= 400 else 500
        return JSONResponse(content={"error": ret_str}, status_code=http_status)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(UVICORN_PORT), log_level="info")
