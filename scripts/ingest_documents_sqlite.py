"""Script to ingest engineering documents into SQLite database (no PostgreSQL required)."""
import asyncio
import sys
from pathlib import Path
from typing import List
import sqlite3
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.pdf_extractor import PDFExtractor
from src.parser.deterministic import DeterministicParser
from src.common.hashing import compute_file_hash
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# Database file path
DB_PATH = Path(__file__).parent.parent / "data" / "engineering_docs.db"


def init_sqlite_db():
    """Initialize SQLite database with required tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS reference_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_number TEXT,
            title TEXT,
            revision TEXT,
            issue_status TEXT,
            contract_number TEXT,
            discipline TEXT,
            page_count INTEGER,
            file_hash TEXT UNIQUE NOT NULL,
            original_path TEXT NOT NULL,
            status TEXT DEFAULT 'Checking',
            job_id TEXT,
            model_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS revision_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            rev TEXT,
            date TEXT,
            description TEXT,
            prepared_by TEXT,
            checked_by TEXT,
            approved_by TEXT,
            FOREIGN KEY (document_id) REFERENCES reference_documents(id)
        );
        
        CREATE TABLE IF NOT EXISTS comments_response (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            seq INTEGER,
            client_comment TEXT,
            contractor_response TEXT,
            FOREIGN KEY (document_id) REFERENCES reference_documents(id)
        );
        
        CREATE TABLE IF NOT EXISTS equipment_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            tag TEXT,
            rating TEXT,
            voltage TEXT,
            phase TEXT,
            frequency TEXT,
            power TEXT,
            sheet TEXT,
            FOREIGN KEY (document_id) REFERENCES reference_documents(id)
        );
        
        CREATE TABLE IF NOT EXISTS drawing_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            sheet_no TEXT,
            sheet_title TEXT,
            drawing_number TEXT,
            FOREIGN KEY (document_id) REFERENCES reference_documents(id)
        );
        
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            parent_id INTEGER,
            level TEXT,
            content TEXT NOT NULL,
            token_count INTEGER,
            embedding TEXT,
            tsv TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES reference_documents(id),
            FOREIGN KEY (parent_id) REFERENCES document_chunks(id)
        );
        
        CREATE TABLE IF NOT EXISTS low_confidence_regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            page INTEGER,
            bbox TEXT,
            text TEXT,
            confidence REAL,
            reviewed BOOLEAN DEFAULT 0,
            reviewed_by TEXT,
            reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES reference_documents(id)
        );
        
        CREATE TABLE IF NOT EXISTS qa_query_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            answer TEXT,
            confidence_level TEXT,
            cited_document_ids TEXT,
            retrieved_chunk_ids TEXT,
            model_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_doc_hash ON reference_documents(file_hash);
        CREATE INDEX IF NOT EXISTS idx_doc_number ON reference_documents(document_number);
        CREATE INDEX IF NOT EXISTS idx_doc_discipline ON reference_documents(discipline);
        CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);
    """)
    
    conn.commit()
    conn.close()
    
    logger.info(f"SQLite database initialized at: {DB_PATH}")


def ingest_document(file_path: Path, discipline: str = None) -> dict:
    """
    Ingest a single document into SQLite database.
    
    Args:
        file_path: Path to the document file
        discipline: Optional discipline tag (ELC/MEC/INS/SIM)
        
    Returns:
        Dictionary with ingestion results
    """
    try:
        # Validate file
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        if file_path.suffix.lower() != ".pdf":
            return {"success": False, "error": f"Only PDF files supported: {file_path.suffix}"}
        
        # Compute hash for idempotency
        file_hash = compute_file_hash(file_path)
        
        # Check if already exists
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, status FROM reference_documents WHERE file_hash = ?", (file_hash,))
        existing = cursor.fetchone()
        
        if existing:
            doc_id, status = existing
            logger.info(f"Document already exists: {file_path.name} (ID: {doc_id})")
            conn.close()
            return {
                "success": True,
                "document_id": doc_id,
                "status": status,
                "message": f"Document already in database (ID: {doc_id})"
            }
        
        # Extract text from PDF
        logger.info(f"Extracting text from: {file_path.name}")
        extractor = PDFExtractor()
        extraction_result = extractor.extract(file_path)
        
        # Parse structured data
        logger.info(f"Parsing structured data from: {file_path.name}")
        parser = DeterministicParser()
        parsed_data = parser.parse(extraction_result["text"])
        
        # Create document record
        cursor.execute("""
            INSERT INTO reference_documents 
            (file_hash, original_path, status, discipline, page_count, model_version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            file_hash,
            str(file_path),
            "Approved",  # Simplified - skip validation for now
            discipline,
            extraction_result["page_count"],
            "deterministic-v1"
        ))
        
        document_id = cursor.lastrowid
        
        # Update with parsed data
        cursor.execute("""
            UPDATE reference_documents 
            SET document_number = ?, title = ?, revision = ?, issue_status = ?,
                contract_number = ?, updated_at = ?
            WHERE id = ?
        """, (
            parsed_data.document_number,
            parsed_data.title,
            parsed_data.revision,
            parsed_data.issue_status,
            parsed_data.contract_number,
            datetime.utcnow().isoformat(),
            document_id
        ))
        
        # Store revision history
        if parsed_data.revision_history:
            for rev in parsed_data.revision_history:
                cursor.execute("""
                    INSERT INTO revision_history (document_id, rev, date, description, prepared_by, checked_by, approved_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    document_id,
                    rev.get("revision"),
                    rev.get("date"),
                    rev.get("description"),
                    rev.get("prepared_by"),
                    rev.get("checked_by"),
                    rev.get("approved_by")
                ))
        
        # Store comments/response
        if parsed_data.comments:
            for i, comment in enumerate(parsed_data.comments, 1):
                cursor.execute("""
                    INSERT INTO comments_response (document_id, seq, client_comment, contractor_response)
                    VALUES (?, ?, ?, ?)
                """, (
                    document_id,
                    i,
                    comment.get("client_comment"),
                    comment.get("contractor_response")
                ))
        
        # Store equipment ratings
        if parsed_data.equipment_ratings:
            for rating in parsed_data.equipment_ratings:
                cursor.execute("""
                    INSERT INTO equipment_ratings 
                    (document_id, tag, rating, voltage, phase, frequency, power, sheet)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document_id,
                    rating.get("tag"),
                    rating.get("rating"),
                    rating.get("voltage"),
                    rating.get("phase"),
                    rating.get("frequency"),
                    rating.get("power"),
                    rating.get("sheet")
                ))
        
        # Store drawing index
        if parsed_data.drawing_index:
            for idx in parsed_data.drawing_index:
                cursor.execute("""
                    INSERT INTO drawing_index (document_id, sheet_no, sheet_title, drawing_number)
                    VALUES (?, ?, ?, ?)
                """, (
                    document_id,
                    idx.get("sheet_no"),
                    idx.get("sheet_title"),
                    idx.get("drawing_number")
                ))
        
        # Store low confidence regions
        if extraction_result["low_confidence_regions"]:
            for region in extraction_result["low_confidence_regions"]:
                cursor.execute("""
                    INSERT INTO low_confidence_regions 
                    (document_id, page, bbox, text, confidence)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    document_id,
                    region.page,
                    json.dumps(region.bbox),
                    region.text,
                    region.confidence
                ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✓ Successfully ingested: {file_path.name} (ID: {document_id})")
        
        return {
            "success": True,
            "document_id": document_id,
            "status": "Approved",
            "document_number": parsed_data.document_number,
            "title": parsed_data.title,
            "page_count": extraction_result["page_count"],
            "message": "Document successfully ingested"
        }
    
    except Exception as e:
        logger.error(f"✗ Ingestion failed for {file_path.name}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def ingest_multiple_documents(file_paths: List[Path], discipline: str = None) -> dict:
    """
    Ingest multiple documents.
    
    Args:
        file_paths: List of file paths to ingest
        discipline: Optional discipline tag
        
    Returns:
        Summary of ingestion results
    """
    # Initialize database
    init_sqlite_db()
    
    results = {
        "total": len(file_paths),
        "successful": 0,
        "failed": 0,
        "already_exists": 0,
        "documents": []
    }
    
    for file_path in file_paths:
        logger.info(f"Processing: {file_path.name}")
        result = ingest_document(file_path, discipline)
        
        results["documents"].append({
            "file": file_path.name,
            **result
        })
        
        if result["success"]:
            if result.get("status") in ["Approved", "already_exists"]:
                if result.get("status") == "already_exists":
                    results["already_exists"] += 1
                else:
                    results["successful"] += 1
            else:
                results["failed"] += 1
        else:
            results["failed"] += 1
    
    return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest engineering documents into SQLite")
    parser.add_argument("files", nargs="+", help="PDF files to ingest")
    parser.add_argument("--discipline", choices=["ELC", "MEC", "INS", "SIM"], help="Discipline tag")
    parser.add_argument("--directory", help="Directory containing PDF files")
    
    args = parser.parse_args()
    
    # Determine files to process
    if args.directory:
        directory = Path(args.directory)
        file_paths = [f for f in directory.glob("*.pdf") if f.is_file()]
    else:
        file_paths = [Path(f) for f in args.files]
    
    if not file_paths:
        logger.error("No files to process")
        sys.exit(1)
    
    logger.info(f"Ingesting {len(file_paths)} documents into SQLite...")
    if args.discipline:
        logger.info(f"Discipline: {args.discipline}")
    
    # Run ingestion
    results = ingest_multiple_documents(file_paths, args.discipline)
    
    # Print summary
    print("\n" + "="*80)
    print("INGESTION SUMMARY (SQLite)")
    print("="*80)
    print(f"Database: {DB_PATH}")
    print(f"Total files:      {results['total']}")
    print(f"Successful:       {results['successful']}")
    print(f"Already exists:   {results['already_exists']}")
    print(f"Failed:           {results['failed']}")
    print("="*80)
    
    # Print details
    print("\nDOCUMENT DETAILS:")
    print("-"*80)
    for doc in results["documents"]:
        status_icon = "✓" if doc["success"] else "✗"
        print(f"{status_icon} {doc['file']}")
        if doc["success"]:
            print(f"  ID: {doc.get('document_id', 'N/A')}")
            print(f"  Status: {doc.get('status', 'N/A')}")
            if doc.get('document_number'):
                print(f"  Doc #: {doc['document_number']}")
            if doc.get('title'):
                print(f"  Title: {doc['title']}")
            if doc.get('page_count'):
                print(f"  Pages: {doc['page_count']}")
        else:
            print(f"  Error: {doc.get('error', 'Unknown error')}")
        print()
    
    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()