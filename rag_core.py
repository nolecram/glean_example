"""
RAG Core Module
===============
Shared retrieval-augmented generation logic for both API and MCP interfaces.

This module handles:
- Loading and chunking FAQ markdown files
- Creating embeddings via OpenAI
- Cosine similarity retrieval
- LLM-based answer generation with source citations
"""

import os
import json
from typing import Dict, List, Tuple
from pathlib import Path

import numpy as np
from openai import OpenAI

# --- Configuration (from environment variables) ---
FAQ_DIR = os.getenv("FAQ_DIR", str(Path(__file__).parent / "faqs"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "200"))
TOP_K_DEFAULT = int(os.getenv("TOP_K_DEFAULT", "4"))

# --- OpenAI Client Initialization ---
def _get_api_key() -> str:
    """Get API key from environment or prompt user."""
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    
    # Prompt user for key if not in environment
    import getpass
    print("\n" + "=" * 50)
    print("OpenAI API Key Required")
    print("=" * 50)
    print("Enter your API key (input is hidden):")
    key = getpass.getpass(prompt="OPENAI_API_KEY: ")
    if not key.strip():
        raise RuntimeError("API key cannot be empty")
    
    # Set it in environment for this session
    os.environ["OPENAI_API_KEY"] = key.strip()
    return key.strip()

_API_KEY = _get_api_key()
client = OpenAI(api_key=_API_KEY)

# --- Global State (populated at module load) ---
_CHUNKS: List[str] = []
_SOURCES: List[str] = []  # Source filename for each chunk
_CHUNK_EMBEDS: np.ndarray | None = None  # shape: (N, embedding_dim)


# ============================================================================
# Core Utilities
# ============================================================================

def _chunk_text(text: str, size: int = CHUNK_SIZE) -> List[str]:
    """
    Split text into fixed-size chunks of approximately `size` characters.
    
    Strategy: Split on sentence boundaries where possible, otherwise hard-split.
    This preserves readability while keeping chunks near the target size.
    """
    if not text or not text.strip():
        return []
    
    text = text.strip()
    chunks = []
    
    # Simple approach: split by sentences first, then combine/split to target size
    # Sentence delimiters: ., ?, !, newlines
    import re
    sentences = re.split(r'(?<=[.!?\n])\s+', text)
    
    current_chunk = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # If adding this sentence exceeds size and we have content, save current chunk
        if current_chunk and len(current_chunk) + len(sentence) + 1 > size:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk = current_chunk + " " + sentence if current_chunk else sentence
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Handle case where a single sentence is longer than chunk size
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= size * 1.5:  # Allow some flexibility
            final_chunks.append(chunk)
        else:
            # Hard split long chunks
            for i in range(0, len(chunk), size):
                final_chunks.append(chunk[i:i + size].strip())
    
    return [c for c in final_chunks if c]  # Filter empty


def _load_and_chunk_faqs(faq_dir: str) -> Tuple[List[str], List[str]]:
    """
    Load all *.md files from the FAQ directory, chunk each file,
    and return parallel lists of (chunks, source_filenames).
    """
    faq_path = Path(faq_dir)
    if not faq_path.exists():
        raise FileNotFoundError(f"FAQ directory not found: {faq_dir}")
    
    all_chunks: List[str] = []
    all_sources: List[str] = []
    
    md_files = sorted(faq_path.glob("*.md"))
    if not md_files:
        raise ValueError(f"No .md files found in {faq_dir}")
    
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        filename = md_file.name
        
        chunks = _chunk_text(content, CHUNK_SIZE)
        all_chunks.extend(chunks)
        all_sources.extend([filename] * len(chunks))
    
    return all_chunks, all_sources


def _embed_texts(texts: List[str]) -> np.ndarray:
    """
    Create embeddings for a list of texts using OpenAI's embedding model.
    Returns a (N, embedding_dim) numpy array of float32.
    """
    if not texts:
        return np.array([], dtype=np.float32)
    
    # OpenAI API supports batching up to 2048 inputs
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts
    )
    
    # Extract embeddings in order
    embeddings = [item.embedding for item in response.data]
    return np.array(embeddings, dtype=np.float32)


def _embed_query(query: str) -> np.ndarray:
    """
    Create an embedding for a single query string.
    Returns a (embedding_dim,) numpy vector of float32.
    """
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=[query]
    )
    return np.array(response.data[0].embedding, dtype=np.float32)


def _cosine_similarity(embeddings: np.ndarray, query_vec: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between each row in embeddings and query_vec.
    Assumes embeddings is (N, d) and query_vec is (d,).
    Returns (N,) similarity scores.
    """
    # Normalize embeddings and query
    emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9)
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    
    # Dot product gives cosine similarity for normalized vectors
    return emb_norm @ query_norm


def _generate_answer(context: str, question: str, source_files: List[str]) -> str:
    """
    Generate an answer using the LLM, grounded in the provided context.
    The answer must cite source files from the context.
    """
    # Build a clear prompt for grounded generation
    system_prompt = """You are a helpful assistant that answers questions based ONLY on the provided context.

Rules:
1. Answer the question using ONLY information from the context below.
2. If the context doesn't contain enough information, say so.
3. Always cite the source files in your answer (mention them by filename).
4. Be concise and direct.
5. If multiple sources are relevant, mention all of them."""

    user_prompt = f"""Context:
{context}

Question: {question}

Available source files: {', '.join(sorted(set(source_files)))}

Please answer the question and cite the relevant source file(s)."""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,  # Low temperature for more deterministic answers
        max_tokens=500
    )
    
    return response.choices[0].message.content.strip()


# ============================================================================
# Public API
# ============================================================================

def ask_faq_core(question: str, top_k: int = TOP_K_DEFAULT) -> Dict[str, object]:
    """
    Main entry point for the RAG system.
    
    Args:
        question: The user's natural language question
        top_k: Number of top chunks to retrieve (default: 4)
    
    Returns:
        Dict with 'answer' (str) and 'sources' (list of filenames)
    
    Raises:
        ValueError: If question is empty
    """
    q = (question or "").strip()
    if not q:
        raise ValueError("question is required")
    
    # Clamp top_k to valid range
    top_k = max(1, min(10, top_k or TOP_K_DEFAULT))
    
    # Ensure we're initialized
    if _CHUNK_EMBEDS is None or len(_CHUNKS) == 0:
        raise RuntimeError("RAG system not initialized. Embeddings not loaded.")
    
    # Embed the query
    query_emb = _embed_query(q)
    
    # Compute cosine similarity
    similarities = _cosine_similarity(_CHUNK_EMBEDS, query_emb)
    
    # Get top-k indices (highest similarity first)
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    
    # Gather context and sources
    top_sources = [_SOURCES[i] for i in top_indices]
    context_parts = [f"[From {_SOURCES[i]}]\n{_CHUNKS[i]}" for i in top_indices]
    context = "\n\n---\n\n".join(context_parts)
    
    # Generate answer
    answer = _generate_answer(context, q, top_sources)
    
    # Return distinct sources (at least 2 when available)
    distinct_sources = sorted(set(top_sources))
    
    return {
        "answer": answer,
        "sources": distinct_sources
    }


# ============================================================================
# Module Initialization
# ============================================================================

def _preload() -> None:
    """
    Load FAQs, compute embeddings, and initialize global state.
    Called automatically at module import time.
    """
    global _CHUNKS, _SOURCES, _CHUNK_EMBEDS
    
    print(f"[RAG] Loading FAQs from: {FAQ_DIR}")
    _CHUNKS, _SOURCES = _load_and_chunk_faqs(FAQ_DIR)
    print(f"[RAG] Loaded {len(_CHUNKS)} chunks from {len(set(_SOURCES))} files")
    
    print(f"[RAG] Computing embeddings with {EMBED_MODEL}...")
    _CHUNK_EMBEDS = _embed_texts(_CHUNKS)
    print(f"[RAG] Embeddings ready: shape {_CHUNK_EMBEDS.shape}")


# Auto-initialize on import
_preload()


# ============================================================================
# CLI Runner (for testing)
# ============================================================================

def main_cli():
    """Simple CLI for testing the RAG system."""
    print("\n=== FAQ RAG CLI ===")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            q = input("Question: ").strip()
            if q.lower() in ('quit', 'exit', 'q'):
                break
            if not q:
                continue
            
            result = ask_faq_core(q)
            print(f"\nAnswer: {result['answer']}")
            print(f"Sources: {', '.join(result['sources'])}\n")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main_cli()
