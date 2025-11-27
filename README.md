# FAQ RAG System

A minimal **Retrieval-Augmented Generation (RAG)** prototype that answers questions from FAQ documents. Built for the Glean technical screen exercise.

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
│   ├── faq_auth.md      # Authentication & password FAQs
│   ├── faq_employee.md  # HR & benefits FAQs
│   └── faq_sso.md       # SSO setup FAQs
└── README.md            # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (3.11 recommended for MCP support)
- **OpenAI API key** with billing enabled

### Installation

```bash
# Clone and enter the repository
git clone <repo-url>
cd glean_example

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### API Key Configuration

The system supports **two methods** for providing your OpenAI API key:

| Method | How to Use | Best For |
|--------|------------|----------|
| **Environment Variable** | `export OPENAI_API_KEY="sk-..."` | Production, CI/CD |
| **Interactive Prompt** | Just run the script—it will ask securely | Local testing, demos |

> **Security Note:** The interactive prompt uses `getpass` so your key is never visible on screen or in shell history.

---

## 🧪 Testing Guide

### Method 1: CLI (Quickest Test)

The fastest way to verify the RAG system works:

```bash
source .venv/bin/activate
python rag_core.py
```

You'll see:
```
==================================================
OpenAI API Key Required
==================================================
Enter your API key (input is hidden):
OPENAI_API_KEY: [paste your key here - it won't show]

[RAG] Loading FAQs from: /path/to/faqs
[RAG] Loaded 6 chunks from 3 files
[RAG] Computing embeddings with text-embedding-3-small...
[RAG] Embeddings ready: shape (6, 1536)

=== FAQ RAG CLI ===
Type 'quit' to exit.

Question: 
```

**Example questions to try:**
- `How do I reset my password?`
- `What is the vesting schedule?`
- `How do I enable SSO?`

---

### Method 2: HTTP API

#### Start the Server

```bash
source .venv/bin/activate
python api_server.py
```

Enter your API key when prompted. You'll see:
```
🚀 Starting FAQ RAG API at http://0.0.0.0:8000
📚 API docs available at http://0.0.0.0:8000/docs
```

#### Test with curl (in a separate terminal)

**Health Check:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

**Ask a Question:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I reset my password?"}'
```

**Example Response:**
```json
{
  "answer": "To reset your password, click the \"Forgot Password\" link on the login page. You'll receive an email with a secure reset link that expires in 24 hours. This information is from the authentication FAQ (faq_auth.md).",
  "sources": ["faq_auth.md", "faq_sso.md"]
}
```

**Ask with Custom top_k:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the vesting schedule?", "top_k": 3}'
```

#### Test with Swagger UI

Open http://localhost:8000/docs in your browser for an interactive API explorer.

---

### Method 3: MCP Tool (for AI Clients)

Configure your MCP client to spawn the server:

**Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):**
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

---

## ⚙️ Configuration

All settings are via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(prompted)* | Your OpenAI API key |
| `FAQ_DIR` | `./faqs` | Directory containing FAQ markdown files |
| `EMBED_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI chat model for answer generation |
| `CHUNK_SIZE` | `200` | Target chunk size in characters |
| `TOP_K_DEFAULT` | `4` | Default number of chunks to retrieve |
| `HOST` | `0.0.0.0` | API server host |
| `PORT` | `8000` | API server port |

---

## 🔧 Technical Design

### Why These Choices?

| Decision | Rationale |
|----------|-----------|
| **Python 3.11** | Required for MCP package (needs 3.10+); best async performance |
| **Single `rag_core.py`** | DRY principle—both interfaces share identical RAG logic |
| **Interactive API key prompt** | Secure for demos (uses `getpass`, hidden input, not in shell history) |
| **In-memory embeddings** | Appropriate for small FAQ corpus; preloaded at startup for fast queries |
| **Sentence-aware chunking** | Preserves semantic coherence vs. naive fixed-width splits |
| **`text-embedding-3-small`** | Best price/performance ratio; 1536 dimensions |
| **`gpt-4o-mini`** | Strong quality at low cost; ideal for FAQ-style answers |
| **Cosine similarity** | Industry standard for embedding comparison; L2-normalized vectors |

### How It Works

1. **Startup:** Load all `.md` files from `faqs/`, chunk into ~200 char segments, compute embeddings
2. **Query:** Embed the question, compute cosine similarity against all chunks
3. **Retrieve:** Select top-k most similar chunks (default: 4)
4. **Generate:** Pass context + question to LLM with citation instructions
5. **Return:** Answer string + list of distinct source filenames

### Trade-offs

| Choice | Trade-off |
|--------|-----------|
| In-memory embeddings | Fast queries, but won't scale to millions of docs (would need vector DB) |
| Preload at startup | ~2s startup delay, but zero latency on queries |
| Low temperature (0.1) | Consistent answers, but less creative responses |
| No caching | Simple implementation; add Redis for production |

---

## 📊 API Reference

### HTTP Endpoints

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/health` | GET | — | `{"status": "ok"}` |
| `/ask` | POST | `{"question": str, "top_k"?: 1-10}` | `{"answer": str, "sources": [str]}` |

**Status Codes:**
- `200` — Success
- `400` — Bad request (empty question, invalid top_k)
- `500` — Internal server error

### MCP Tool

| Tool | Parameters | Returns |
|------|------------|---------|
| `ask_faq` | `question` (str, required), `top_k` (int, optional 1-10) | `{"answer": str, "sources": [str]}` |

---

## ✅ Exercise Compliance

This implementation satisfies all requirements from the Glean technical screen exercise.

### Core RAG Requirements ✓

| Requirement | Implementation |
|-------------|----------------|
| Chunk size ~200 chars | `CHUNK_SIZE = 200` with sentence-aware splitting |
| Top-k cosine similarity | L2-normalized embeddings, configurable k (default 4) |
| Cite ≥2 sources | Returns all distinct sources; LLM prompt enforces citations |
| Response format | Exactly `{"answer": string, "sources": [string]}` |

### HTTP API Requirements ✓

| Requirement | Implementation |
|-------------|----------------|
| `GET /health` → `{"status":"ok"}` | ✅ Implemented |
| `POST /ask` with validation | ✅ Pydantic: 1-1000 chars, top_k 1-10 |
| Status codes 200/400/500 | ✅ Proper HTTP semantics |
| Config via environment | ✅ All settings from env vars |

### MCP Tool Requirements ✓

| Requirement | Implementation |
|-------------|----------------|
| Tool name: `ask_faq` | ✅ `@mcp.tool()` decorator |
| Stdio transport | ✅ `mcp.run(transport="stdio")` |
| Schema with optional top_k | ✅ Default 4, range 1-10 |

### Deviations from Skeleton

1. **Both interfaces implemented** — Exercise required one; we provided both to demonstrate shared-core architecture
2. **Interactive API key prompt** — Added secure `getpass` prompt for convenient demos without exposing keys
3. **Upgraded models** — Using `text-embedding-3-small` and `gpt-4o-mini` (better price/performance)
4. **Sentence-aware chunking** — Preserves semantic coherence vs. fixed splits

---

## 📝 Adding New FAQs

```bash
# 1. Add a new markdown file
echo "# New FAQ Topic

Q: How do I do X?
A: You do X by doing Y.
" > faqs/faq_newtopic.md

# 2. Restart the server (embeddings recompute at startup)
python api_server.py
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
