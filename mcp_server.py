"""
FAQ RAG - MCP Server
====================
Model Context Protocol server exposing the RAG system as an MCP tool.

Tool: ask_faq
- Input: question (required), top_k (optional, default 4)
- Output: { answer: string, sources: [string] }

Transport: stdio (client launches this as a subprocess)
"""

import os
import sys
from typing import Dict

# Import rag_core (will prompt for API key if not set in env)
# Note: For MCP, the key should be passed via env in the client config
from mcp.server.fastmcp import FastMCP
from rag_core import ask_faq_core

# --- MCP Server Setup ---
mcp = FastMCP(
    name="faq-rag",
    version="1.0.0"
)


@mcp.tool()
def ask_faq(question: str, top_k: int = 4) -> Dict[str, object]:
    """
    Answer a question using the FAQ knowledge base.
    
    Retrieves relevant information from FAQ documents and generates
    an answer with source citations.
    
    Args:
        question: The natural language question to answer (required)
        top_k: Number of document chunks to retrieve (1-10, default: 4)
    
    Returns:
        A dictionary with:
        - answer: The generated answer string
        - sources: List of source filenames cited
    """
    # Validate question
    q = (question or "").strip()
    if not q:
        raise ValueError("`question` is required and cannot be empty")
    
    # Clamp top_k to valid range
    if top_k is None or top_k <= 0 or top_k > 10:
        top_k = 4
    
    # Call the core RAG function
    result = ask_faq_core(q, top_k=top_k)
    
    return {
        "answer": result["answer"],
        "sources": result["sources"]
    }


# --- Main Entry Point ---
if __name__ == "__main__":
    # Run with stdio transport (MCP client launches this process)
    mcp.run(transport="stdio")
