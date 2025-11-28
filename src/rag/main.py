import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from starlette.middleware.cors import CORSMiddleware

# from rag import rag
# from . import rag as rag
import rag as rag

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
async def create_chunks(limit: int):
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
async def query_llm(prompt: str):
    ret_str, ret_val = rag.query(prompt)
    html_content = f"""
        {ret_str}
    """
    return HTMLResponse(content=html_content, status_code=ret_val)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(UVICORN_PORT), log_level="info")
