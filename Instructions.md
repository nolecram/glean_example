# Technical Screen: RAG Prototype

## Overview

Implement a minimal **Retrieval-Augmented Generation (RAG)** prototype using the provided FAQ documents. Choose **one** interface option:

| Option | Interface | Best For |
|--------|-----------|----------|
| **HTTP API** | FastAPI with `/health` and `/ask` endpoints | Testing via curl/Postman |
| **MCP Tool** | `ask_faq` tool via stdio transport | Integration with AI clients (Claude, Cursor) |

## What We're Evaluating

- **Clear reasoning** and trade-offs (simplicity over over-engineering)
- **Practicality** and correctness of your interface
- **Code quality** — readable, well-structured implementation

## Deliverables (2–3 hours suggested)

- [ ] Source code for RAG core + your chosen interface
- [ ] Brief notes if you deviated from the starter skeleton

---

## Core RAG Requirements

Both options share the same RAG logic:

| Requirement | Specification |
|------------|---------------|
| **Chunk size** | ~200 characters |
| **Retrieval** | Top-k chunks via cosine similarity (default k=4) |
| **Citations** | Answer must cite ≥2 distinct source files when available |
| **Response format** | `{ "answer": string, "sources": [filename, ...] }` |

---

## Option 1: HTTP API

### Endpoints

```
GET  /health  →  {"status": "ok"}
POST /ask     →  {"question": string, "top_k"?: number}
              ←  {"answer": string, "sources": ["file1.md", "file2.md"]}
```

### Requirements

- Input validation: non-empty question, `top_k` in range 1-10
- Status codes: `200` (success), `400` (bad input), `500` (error)
- Config via environment variables (fail fast if `OPENAI_API_KEY` missing)

---

## Option 2: MCP Tool

### Tool Schema

```yaml
name: ask_faq
inputs:
  question: string (required)
  top_k: number (optional, default 4, range 1-10)
output:
  answer: string
  sources: [string]
```

### Requirements

- Transport: stdio (client spawns server process)
- Config via environment variables (fail fast if `OPENAI_API_KEY` missing)

---

## Provided Assets

```
├── faqs/                  # Sample FAQ markdown files
│   ├── faq_auth.md
│   ├── faq_employee.md
│   └── faq_sso.md
├── rag_core.py            # Shared RAG implementation
├── api_server.py          # HTTP API wrapper
├── mcp_server.py          # MCP tool wrapper
└── requirements.txt       # Python dependencies
```

---

## Evaluation Criteria

| Criterion | What We Look For |
|-----------|-----------------|
| **Accuracy** | Relevant context retrieved, correct answers from docs |
| **Approach** | Clear design choices, appropriate simplicity |
| **Practicality** | Lightweight solution, no over-engineering |

## Notes

- Any language/stack is acceptable (Python provided for convenience)
- Optional extras (logging, retries) should be minimal and documented
- Be prepared to discuss your design decisions
