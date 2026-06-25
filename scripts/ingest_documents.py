"""Script to ingest engineering documents into the PostgreSQL database."""
import asyncio
import sys
from pathlib import Path
from typing import List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.db.session import init_db, get_db
from src.db.models import ReferenceDocument
from src.ingestion.orchestrator import ingestion_orchestrator
from src.ingestion.router import format_router
from src.common.hashing import compute_file_hash
from src.common.constants import Discipline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def ingest_document(file_path: Path, discipline: str = None) -> dict:
    """
    Ingest a single document into the database.
    
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
        
        if not format_router.is_supported(file_path):
            return {"success": False, "error": f"Unsupported format: {file_path.suffix}"}
        
        # Compute hash for idempotency
        file_hash = compute_file_hash(file_path)
        
        # Check if already exists
        from sqlalchemy import select
        async for db in get_db():
            result = await db.execute(
                select(ReferenceDocument).where(ReferenceDocument.file_hash == file_hash)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"Document already exists: {file_path.name} (ID: {existing.id})")
                return {
                    "success": True,
                    "document_id": existing.id,
                    "status": "already_exists",
                    "message": f"Document already in database (ID: {existing.id})"
                }
            
            # Create document record
            document = ReferenceDocument(
                file_hash=file_hash,
                original_path=str(file_path),
                status="Checking",
                discipline=discipline,
            )
            db.add(document)
            await db.commit()
            await db.refresh(document)
            
            logger.info(f"Created document record: ID={document.id}, file={file_path.name}")
            
            # Process document through ingestion pipeline
            try:
                processing_result = await ingestion_orchestrator.process_document(
                    file_path=file_path,
                    document_id=document.id,
                    discipline=discipline,
                )
                
                # Update document with results
                document.status = "Approved"  # Simplified - in production, run validation
                document.document_number = processing_result["parsed_data"].document_number
                document.title = processing_result["parsed_data"].title
                document.revision = processing_result["parsed_data"].revision
                document.issue_status = processing_result["parsed_data"].issue_status
                document.contract_number = processing_result["parsed_data"].contract_number
                document.page_count = processing_result["page_count"]
                document.model_version = "deterministic-v1"
                
                await db.commit()
                await db.refresh(document)
                
                logger.info(f"Successfully processed document {document.id}: {file_path.name}")
                
                return {
                    "success": True,
                    "document_id": document.id,
                    "status": "Approved",
                    "document_number": document.document_number,
                    "title": document.title,
                    "page_count": document.page_count,
                    "chunks_created": len(processing_result["child_chunks"]),
                    "message": "Document successfully ingested"
                }
                
            except Exception as e:
                logger.error(f"Processing failed for {file_path.name}: {e}")
                document.status = "Rejected"
                await db.commit()
                
                return {
                    "success": False,
                    "document_id": document.id,
                    "status": "Rejected",
                    "error": str(e)
                }
    
    except Exception as e:
        logger.error(f"Ingestion failed for {file_path.name}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def ingest_multiple_documents(file_paths: List[Path], discipline: str = None) -> dict:
    """
    Ingest multiple documents.
    
    Args:
        file_paths: List of file paths to ingest
        discipline: Optional discipline tag
        
    Returns:
        Summary of ingestion results
    """
    # Initialize database
    await init_db()
    
    results = {
        "total": len(file_paths),
        "successful": 0,
        "failed": 0,
        "already_exists": 0,
        "documents": []
    }
    
    for file_path in file_paths:
        logger.info(f"Processing: {file_path.name}")
        result = await ingest_document(file_path, discipline)
        
        results["documents"].append({
            "file": file_path.name,
            **result
        })
        
        if result["success"]:
            if result.get("status") == "already_exists":
                results["already_exists"] += 1
            else:
                results["successful"] += 1
        else:
            results["failed"] += 1
    
    return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest engineering documents into PostgreSQL")
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
    
    logger.info(f"Ingesting {len(file_paths)} documents...")
    if args.discipline:
        logger.info(f"Discipline: {args.discipline}")
    
    # Run ingestion
    results = asyncio.run(ingest_multiple_documents(file_paths, args.discipline))
    
    # Print summary
    print("\n" + "="*80)
    print("INGESTION SUMMARY")
    print("="*80)
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