# Engineering Document Control System

A fully offline, on-premise engineering document-control knowledge base delivered as a Model Context Protocol (MCP) server with a FastAPI backend and web dashboard.

## Features

- **Multi-format Ingestion**: PDF, DWG/DXF, DOCX, XLSX, PPTX, and image files
- **OCR with Confidence Gating**: PaddleOCR/Tesseract at 300 DPI with 0.75 confidence threshold
- **Deterministic + LLM Parsing**: Regex-based extraction augmented with local LLM (Llama 3.1 8B / Qwen2.5 7B)
- **Hybrid Search**: pgvector cosine similarity + SQL full-text search
- **Grounded Q&A**: Natural-language answers with verifiable citations
- **Validation Gateway**: Configurable rules engine with JSONB rejection notes
- **Audit Trail**: Complete logging of all operations with SHA-256 hashes
- **Human-in-the-Loop**: Review queue for low-confidence OCR regions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
├─────────────────────────────────────────────────────────────┤
│  MCP Server (4 tools)  │  REST API  │  WebSocket  │  SPA   │
├─────────────────────────────────────────────────────────────┤
│  Ingestion  │  OCR  │  Parser  │  Embeddings  │  Search   │
├─────────────────────────────────────────────────────────────┤
│              SQLAlchemy 2.0 Async ORM                       │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL 18 + pgvector  │  Redis (Celery)  │  Ollama    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.14+
- PostgreSQL 18 with pgvector extension
- Redis (for Celery)
- Ollama (for local LLM)
- Docker (optional, for PostgreSQL)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/zaskiamehrunisha-cloud/document-mcp.git
cd document-mcp
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. Initialize database:
```bash
python -m alembic upgrade head
```

6. Start the application:
```bash
python src/main.py
```

### Docker Setup (Recommended)

```bash
# Start PostgreSQL with pgvector
docker run -d \
  --name pgvector \
  -e POSTGRES_USER=doccontrol \
  -e POSTGRES_PASSWORD=secure_password \
  -e POSTGRES_DB=engineering_docs \
  -p 5432:5432 \
  pgvector/pgvector:0.8.3-pg18

# Start Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Start Ollama
docker run -d --name ollama -p 11434:11434 ollama/ollama

# Pull models
docker exec -it ollama ollama pull llama3.1:8b-instruct-q4_K_M
docker exec -it ollama ollama pull qwen2.5:7b-instruct-q4_K_M
```

## Project Structure

```
├── src/
│   ├── main.py                    # Application entry point
│   ├── mcp/                       # MCP server (4 tools)
│   ├── api/                       # FastAPI REST + WebSocket
│   ├── ingestion/                 # Document extraction pipeline
│   │   ├── pdf_extractor.py       # PDF text extraction
│   │   ├── cad_extractor.py       # DWG/DXF extraction
│   │   ├── office_extractor.py    # DOCX/XLSX/PPTX extraction
│   │   └── orchestrator.py        # Pipeline orchestration
│   ├── ocr/                       # OCR engine + confidence gating
│   ├── parser/                    # Deterministic + LLM parsing
│   ├── embeddings/                # Chunking + on-device embeddings
│   ├── validation/                # Validation gateway
│   ├── search/                    # Hybrid search + Q&A
│   ├── submission/                # Document Controller client
│   ├── llm/                       # Local LLM client
│   ├── db/                        # SQLAlchemy models + session
│   ├── storage/                   # File storage
│   └── config/                    # Configuration management
├── alembic/                       # Database migrations
├── scripts/                       # Operational scripts
├── tests/                         # Test suite
├── frontend/                      # React web dashboard
├── docker/                        # Docker configuration
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project configuration
├── .env.example                   # Environment template
└── README.md                      # This file
```

## MCP Tools

The system exposes 4 MCP tools over Streamable HTTP:

1. **ingest_document** - Upload and process a document
2. **validate_document** - Run validation rules on a document
3. **search_knowledge_base** - Hybrid search across documents
4. **submit_to_docon** - Forward approved documents to Document Controller

## REST API Endpoints

- `POST /upload` - Upload document
- `GET /upload/status/{job_id}` - Check processing status
- `WS /ws/status/{job_id}` - Live status updates
- `POST /search` - Hybrid search
- `POST /ask` - Natural-language Q&A
- `GET /documents` - List approved documents
- `GET /documents/{id}` - Document details
- `GET /review/flagged` - Low-confidence regions (admin)
- `PATCH /review/{id}` - Mark region reviewed (admin)

## Web Dashboard

Three user-facing screens:
1. **Upload Document** - Drag-and-drop upload with discipline tagging
2. **Ask a Question** - Natural-language Q&A with citations
3. **Approved Documents** - Browse validated documents

## Configuration

Key environment variables (see `.env.example` for all):

```env
# Database
DB_URL=postgresql+asyncpg://doccontrol:secure_password@localhost:5432/engineering_docs

# LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M

# Embeddings
EMBED_MODEL=BAAI/bge-small-en-v1.5

# OCR
OCR_DPI=300
OCR_CONFIDENCE_THRESHOLD=0.75

# Web UI
START_WEB_UI=true
WEB_PORT=8000
```

## Document Processing Pipeline

1. **Upload** → SHA-256 hash computed for idempotency
2. **Format Router** → Dispatch to appropriate extractor
3. **Extraction** → Native text + OCR fallback if needed
4. **Confidence Gate** → Sub-0.75 blocks → review queue
5. **Parsing** → Deterministic regex + LLM JSON pass
6. **Chunking** → Parent (1024/128) + Child (256/32)
7. **Embeddings** → On-device BAAI/bge-small-en-v1.5
8. **Storage** → PostgreSQL + pgvector
9. **Validation** → Rule evaluation from database
10. **Submission** → Forward to Document Controller if approved

## Technology Stack

- **Backend**: Python 3.14, FastAPI, SQLAlchemy 2.0 async
- **MCP**: Official MCP Python SDK (FastMCP)
- **Database**: PostgreSQL 18 + pgvector 0.8.3
- **OCR**: PaddleOCR 3.6.x (primary), Tesseract 5 (fallback)
- **LLM**: Llama 3.1 8B Instruct / Qwen2.5 7B Instruct via Ollama
- **Embeddings**: sentence-transformers, BAAI/bge-small-en-v1.5
- **Queue**: Celery + Redis
- **Frontend**: React + Vite + TypeScript
- **Infrastructure**: Docker Compose

## Hard Constraints

- ✅ **Zero external API calls** - All inference runs locally
- ✅ **SQL-only persistence** - No in-memory or key-value stores
- ✅ **Offline-first** - Models pre-provisioned, no runtime downloads
- ✅ **Audit-grade** - Every operation logged with hash + model version

## Development

### Run Tests
```bash
pytest tests/ -v --cov=src
```

### Code Quality
```bash
ruff check src/
black src/
mypy src/
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## License

Proprietary - All rights reserved

## Support

For issues and questions, please use the GitHub issue tracker.

---

**Built for engineering document control in EPC/industrial capital projects.**