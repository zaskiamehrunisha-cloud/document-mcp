# Document Ingestion Guide

## Current Status

The ingestion script has been created and all dependencies are installed, but **PostgreSQL is not running**. The system requires a PostgreSQL database with pgvector extension to store documents.

## Option 1: Start PostgreSQL with Docker (Recommended)

If you have Docker installed:

```bash
# Start PostgreSQL with pgvector
docker run -d \
  --name pgvector \
  -e POSTGRES_USER=doccontrol \
  -e POSTGRES_PASSWORD=secure_password \
  -e POSTGRES_DB=engineering_docs \
  -p 5432:5432 \
  pgvector/pgvector:0.8.3-pg18
```

Then run migrations:
```bash
python -m alembic upgrade head
```

Then ingest documents:
```bash
python scripts/ingest_documents.py "c:/Users/arisa/Downloads/ARG-E-EL-00-001_rev.1 Electrical Arrangement Layout sht.1-Layout1.pdf" --discipline ELC
```

## Option 2: Use Local PostgreSQL Installation

If you have PostgreSQL installed locally:

1. Create database:
```sql
CREATE DATABASE engineering_docs;
CREATE USER doccontrol WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE engineering_docs TO doccontrol;
```

2. Enable pgvector extension:
```sql
\c engineering_docs
CREATE EXTENSION vector;
```

3. Run migrations:
```bash
python -m alembic upgrade head
```

4. Ingest documents (same as above)

## Option 3: Use SQLite for Development/Testing

I can modify the system to use SQLite temporarily for testing the ingestion pipeline without PostgreSQL. This would allow you to:

1. Test the PDF extraction
2. Verify document parsing
3. See the structured data extracted

**Note:** SQLite doesn't support pgvector, so vector search won't work, but basic document storage and retrieval will function.

## Documents Ready for Ingestion

The following 10 engineering PDFs are ready in your Downloads folder:

1. `ARG-E-EL-00-001_rev.1 Electrical Arrangement Layout sht.1-Layout1.pdf`
2. `ARG-E-EL-00-001_rev.1 Electrical Arrangement Layout sht.2-Layout1.pdf`
3. `ARG-E-EL-00-001_rev.1 Electrical Arrangement Layout sht.3-Layout1.pdf`
4. `ARG-E-LO-00-010_Elec Lightning Arrester Layout Coverage Area_Rev.0_sht2n-Layout1.pdf`
5. `ARG-E-LO-00-009_1 Elec Grounding Layout_sht1-Layout1.pdf`
6. `ARG-E-LO-00-009_1 Elec Grounding Layout_sht2-Layout1.pdf`
7. `ARG-E-LO-00-009_1 Elec Grounding Layout_sht3-Layout1.pdf`
8. `ARG-E-LO-00-009_1 Elec Grounding Layout_sht4-Layout1.pdf`
9. `ARG-E-LO-00-006-A Cable Tray And TrenchLayout_Rev.1_sht2-Layout1.pdf`
10. `ARG-E-OD-00-001_Rev C Single Line Diagram-Model.pdf`

All are tagged with discipline: **ELC (Electrical)**

## What the Ingestion Pipeline Does

For each PDF, the system will:

1. **Extract native text** using pdfplumber/PyMuPDF
2. **Check if OCR is needed** (if < 50 chars per page)
3. **Run OCR** with PaddleOCR/Tesseract if needed (300 DPI)
4. **Parse structured data**:
   - Document number (pattern: `[A-Z]{2,4}-[A-Z]-[A-Z]{2}-\d{2}-\d{3}`)
   - Title, revision, issue status
   - Contract number
   - Revision history
   - Comment/response rows
5. **Chunk the content** (parent: 1024 tokens, child: 256 tokens)
6. **Generate embeddings** (BAAI/bge-small-en-v1.5, 384-dim)
7. **Store in PostgreSQL** with pgvector
8. **Run validation** against configured rules
9. **Forward to Document Controller** if approved

## Next Steps

Please choose an option:
- **Option 1**: Install Docker and start PostgreSQL
- **Option 2**: Use existing PostgreSQL installation
- **Option 3**: I'll create a SQLite-based version for testing

Which option would you like to proceed with?