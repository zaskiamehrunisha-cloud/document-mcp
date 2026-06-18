# DOCINTEL Quick Start Guide

## Prerequisites

- Python 3.14 or higher
- Docker and Docker Compose
- NVIDIA GPU (optional, for faster LLM inference)

## Installation Steps

### 1. Environment Setup

```bash
# Navigate to project directory
cd docintel

# Create virtual environment (for development)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Minimum required:
# - DATABASE_URL (PostgreSQL connection)
# - OLLAMA_BASE_URL (local LLM endpoint)
# - REFERENCE_DOCS_DIR (path to reference PDFs)
```

### 3. Database Setup

```bash
# Install Alembic (if not already installed)
pip install alembic

# Run migrations
alembic upgrade head

# Verify pgvector extension is enabled
# Connect to PostgreSQL and run:
# CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. Pull Local Models

```bash
# Make the script executable (Linux/Mac)
chmod +x scripts/pull_models.sh

# Run the model pull script
./scripts/pull_models.sh

# Or manually pull models with Ollama:
# ollama pull llama2:7b
# ollama pull bge-large-en-v1.5
```

### 5. Start the Application

#### Option A: Docker Compose (Recommended)

```bash
# Start all services (PostgreSQL, Ollama, App)
docker-compose up -d

# Check logs
docker-compose logs -f app

# Verify health
curl http://localhost:8000/health
```

#### Option B: Local Development

```bash
# Start PostgreSQL (if not running)
# Start Ollama (if not running)
ollama serve &

# Run the application
uvicorn docintel.main:app --reload

# Or using the CLI
docintel
```

### 6. Seed Reference Documents

```bash
# Place your reference PDFs in data/reference/
# The system will automatically seed them on startup

# Or manually trigger seeding:
python scripts/seed_reference_docs.py
```

## Verification

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy"}
```

### Test MCP Tools

```bash
# MCP endpoint is available at:
# http://localhost:8000/mcp

# Use with any MCP client (e.g., Claude Desktop, Cursor)
# Configure in your MCP client settings:
# {
#   "mcpServers": {
#     "docintel": {
#       "url": "http://localhost:8000/mcp"
#     }
#   }
# }
```

### Access the Frontend

```bash
# Open in browser:
# http://localhost:8000/static/index.html

# Or serve the frontend separately:
cd frontend
python -m http.server 3000
# Then open: http://localhost:3000
```

## Usage Examples

### Example 1: Ingest a Document

```python
import httpx

async def ingest_example():
    async with httpx.AsyncClient() as client:
        with open("drawing.pdf", "rb") as f:
            response = await client.post(
                "http://localhost:8000/api/documents",
                files={"file": ("drawing.pdf", f, "application/pdf")},
                data={"discipline": "ELC"}
            )
        print(response.json())
```

### Example 2: Search Knowledge Base

```python
import httpx

async def search_example():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/search",
            json={
                "question": "What ground voltage rating is required?",
                "top_k": 5
            }
        )
        result = response.json()
        print(f"Answer: {result['answer']}")
        print(f"Confidence: {result['confidence']}")
        for citation in result['citations']:
            print(f"  - {citation['document_number']}, Page {citation['page_or_sheet']}")
```

### Example 3: Use MCP Tools

```python
from mcp import Client

async def mcp_example():
    async with Client() as client:
        # Ingest document
        result = await client.call_tool(
            "ingest_document",
            {
                "file_path": "/path/to/drawing.pdf",
                "discipline": "ELC"
            }
        )
        print(f"Ingested: {result['document_id']}")
        
        # Search knowledge base
        answer = await client.call_tool(
            "search_knowledge_base",
            {
                "question": "What is the cable tray layout?",
                "top_k": 5
            }
        )
        print(f"Answer: {answer['answer']}")
```

## Troubleshooting

### Common Issues

1. **PostgreSQL connection error**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL in .env
   - Verify pgvector extension is installed

2. **Ollama connection error**
   - Ensure Ollama is running: `ollama serve`
   - Check OLLAMA_BASE_URL in .env
   - Verify models are pulled: `ollama list`

3. **OCR not working**
   - Install Tesseract: `apt-get install tesseract-ocr` (Linux)
   - For PaddleOCR, ensure paddlepaddle is installed

4. **Import errors**
   - Activate virtual environment
   - Reinstall dependencies: `pip install -e .`

### Logs

```bash
# Application logs
docker-compose logs -f app

# PostgreSQL logs
docker-compose logs -f postgres

# Ollama logs
docker-compose logs -f ollama
```

## Next Steps

1. **Add reference documents**: Place your controlled drawings in `data/reference/`
2. **Configure validation rules**: Edit `config/validation_rules.yaml`
3. **Customize disciplines**: Edit `config/disciplines.yaml`
4. **Set up DOCON connector**: Implement `DoconConnector` for your DOCON system
5. **Configure LLM**: Choose and pull appropriate models in `config/models.yaml`

## Development

```bash
# Run tests
pytest tests/

# Lint code
ruff check src/

# Type check
mypy src/

# Format code
ruff format src/
```

## Production Deployment

See README.md for production deployment instructions with Docker Compose and Kubernetes.

## Support

For issues and questions:
- Check the documentation in README.md
- Review the action plan: `agent_action_plan (1).md`
- Examine example PDFs in the reference documents