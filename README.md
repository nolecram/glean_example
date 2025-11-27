# FAQ RAG System

A minimal Retrieval-Augmented Generation (RAG) prototype that answers questions from FAQ documents. Supports both **HTTP API** and **MCP Tool** interfaces.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Interfaces                             │
│  ┌──────────────────┐       ┌──────────────────┐           │
│  │   api_server.py  │       │  mcp_server.py   │           │
│  │   (FastAPI)      │       │  (MCP/stdio)     │           │
│  │   /health, /ask  │       │  ask_faq tool    │           │
│  └────────┬─────────┘       └────────┬─────────┘           │
│           │                          │                      │
│           └──────────┬───────────────┘                      │
│                      ▼                                      │
│           ┌──────────────────┐                              │
│           │   rag_core.py    │  ← Shared RAG Logic          │
│           │                  │                              │
│           │  • Chunking      │                              │
│           │  • Embeddings    │                              │
│           │  • Retrieval     │                              │
│           │  • Generation    │                              │
│           └────────┬─────────┘                              │
│                    ▼                                        │
│           ┌──────────────────┐                              │
│           │   faqs/*.md      │  ← Document Corpus           │
│           └──────────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Repository Structure

```
.
├── rag_core.py          # Core RAG implementation (shared)
├── api_server.py        # HTTP API server (FastAPI)
├── mcp_server.py        # MCP tool server (stdio transport)
├── requirements.txt     # Python dependencies
├── faqs/                # FAQ document corpus
│   ├── faq_auth.md
│   ├── faq_employee.md
│   └── faq_sso.md
├── Instructions.md      # Exercise requirements
└── README.md            # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key

### Installation

```bash
# Clone and enter the repository
cd glean_example

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."
```

### Option 1: HTTP API

```bash
# Start the server
python api_server.py

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

**Test with curl:**

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I reset my password?"}'

# With custom top_k
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the PTO policy?", "top_k": 6}'
```

**Example Response:**

```json
{
  "answer": "To reset your password, use the reset link on the login page. This information comes from the Auth FAQ (faq_auth.md).",
  "sources": ["faq_auth.md", "faq_sso.md"]
}
```

### Option 2: MCP Tool

Configure your MCP client (Claude Desktop, Cursor, etc.) to spawn the server:

**Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "faq-rag": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

**Cursor (`.cursor/mcp.json`):**

```json
{
  "servers": {
    "faq-rag": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

Once configured, you can call the `ask_faq` tool from your AI assistant.

### CLI Testing

```bash
# Quick test without starting a server
python rag_core.py

# Interactive CLI will prompt for questions
```

## ⚙️ Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | Your OpenAI API key |
| `FAQ_DIR` | `./faqs` | Directory containing FAQ markdown files |
| `EMBED_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `CHUNK_SIZE` | `200` | Target chunk size in characters |
| `TOP_K_DEFAULT` | `4` | Default number of chunks to retrieve |
| `HOST` | `0.0.0.0` | API server host (API only) |
| `PORT` | `8000` | API server port (API only) |

## 🔧 Implementation Details

### Design Decisions

1. **Shared Core (`rag_core.py`)**
   - Single implementation serves both interfaces
   - Preloads embeddings at startup for fast queries
   - Clean separation between retrieval and generation

2. **Chunking Strategy**
   - Sentence-aware splitting (~200 chars)
   - Preserves readability over strict size limits
   - Falls back to hard splits for very long sentences

3. **Embedding & Retrieval**
   - Uses `text-embedding-3-small` (cost-effective, good quality)
   - Cosine similarity with L2-normalized vectors
   - Returns top-k most similar chunks

4. **Answer Generation**
   - Low temperature (0.1) for consistent answers
   - System prompt enforces grounding and citations
   - Includes source filenames in context for citation

5. **Error Handling**
   - Fails fast on missing API key (clear error message)
   - Input validation with appropriate HTTP status codes
   - Internal errors don't leak to clients

### Trade-offs Made

| Choice | Rationale |
|--------|-----------|
| In-memory embeddings | Simple, fast for small corpus. Would need vector DB for scale. |
| Preload at startup | Slight startup delay, but zero latency on queries. |
| Sentence-aware chunking | Better context preservation vs. fixed-width splits. |
| `gpt-4o-mini` default | Good balance of quality and cost for FAQ answers. |
| No caching | Keeps implementation simple; add Redis for production. |

## 📊 API Reference

### HTTP API

#### `GET /health`

Health check endpoint.

**Response:** `200 OK`
```json
{"status": "ok"}
```

#### `POST /ask`

Ask a question to the FAQ corpus.

**Request Body:**
```json
{
  "question": "string (required, 1-1000 chars)",
  "top_k": "number (optional, 1-10, default 4)"
}
```

**Response:** `200 OK`
```json
{
  "answer": "string",
  "sources": ["filename1.md", "filename2.md"]
}
```

**Errors:**
- `400 Bad Request` — Invalid input (empty question, top_k out of range)
- `500 Internal Server Error` — Server-side error

### MCP Tool

#### `ask_faq`

Answer a question using the FAQ knowledge base.

**Parameters:**
- `question` (string, required): The question to answer
- `top_k` (number, optional): Chunks to retrieve (1-10, default 4)

**Returns:**
```json
{
  "answer": "string",
  "sources": ["filename1.md", "filename2.md"]
}
```

## 🧪 Testing Examples

### Password Reset Question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I reset my password?"}'
```

### PTO Policy Question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the unlimited PTO policy?"}'
```

### Equity Vesting Question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How does equity vesting work at TechFlow?"}'
```

### SSO Setup Question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I enable SSO for my account?"}'
```

## 📝 Adding New FAQs

1. Create a new markdown file in `faqs/`:
   ```bash
   echo "# New FAQ\n\nQ: Question?\nA: Answer." > faqs/faq_new.md
   ```

2. Restart the server (embeddings are computed at startup)

3. The new content will automatically be included in retrieval

## 🔮 Future Improvements

If this were production code, consider:

- **Vector database** (Pinecone, Weaviate) for larger corpora
- **Caching layer** (Redis) for repeated queries
- **Streaming responses** for better UX
- **Rate limiting** and authentication
- **Metrics/observability** (latency, token usage)
- **Hybrid search** (keyword + semantic)

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.