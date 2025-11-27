"""
FAQ RAG - HTTP API Server
=========================
FastAPI server exposing the RAG system via REST endpoints.

Endpoints:
- GET  /health  → Health check
- POST /ask     → Ask a question to the FAQ corpus
"""

import os
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import rag_core (will prompt for API key if not set)
from rag_core import ask_faq_core

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- FastAPI App ---
app = FastAPI(
    title="FAQ RAG API",
    description="Retrieval-Augmented Generation API for FAQ documents",
    version="1.0.0"
)


# --- Request/Response Models ---
class AskRequest(BaseModel):
    """Request body for POST /ask"""
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The question to ask"
    )
    top_k: Optional[int] = Field(
        default=4,
        ge=1,
        le=10,
        description="Number of chunks to retrieve (1-10)"
    )


class AskResponse(BaseModel):
    """Response body for POST /ask"""
    answer: str
    sources: list[str]


class HealthResponse(BaseModel):
    """Response body for GET /health"""
    status: str


class ErrorResponse(BaseModel):
    """Error response body"""
    detail: str


# --- Endpoints ---
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns OK if the server is running"
)
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post(
    "/ask",
    response_model=AskResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Ask a Question",
    description="Ask a natural language question and get an answer from the FAQ corpus"
)
def ask(body: AskRequest):
    """
    Process a question through the RAG pipeline.
    
    - Retrieves relevant chunks from the FAQ corpus
    - Generates an answer using an LLM
    - Returns the answer with source citations
    """
    try:
        logger.info(f"Received question: {body.question[:50]}...")
        
        result = ask_faq_core(
            question=body.question.strip(),
            top_k=body.top_k or 4
        )
        
        logger.info(f"Generated answer with {len(result['sources'])} sources")
        
        return {
            "answer": result["answer"],
            "sources": result["sources"]
        }
        
    except ValueError as e:
        # Input validation errors
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Don't leak internal errors to client
        logger.error(f"Internal error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# --- Error Handlers ---
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Catch-all exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# --- Main Entry Point ---
if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"\n🚀 Starting FAQ RAG API at http://{host}:{port}")
    print(f"📚 API docs available at http://{host}:{port}/docs\n")
    
    uvicorn.run(app, host=host, port=port)
