"""Ingestion orchestrator - routes files through the extraction pipeline."""
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.ingestion.router import format_router
from src.ingestion.pdf_extractor import pdf_extractor
from src.ingestion.cad_extractor import cad_extractor
from src.ingestion.office_extractor import office_extractor
from src.ingestion.image_extractor import image_extractor
from src.parser.deterministic import DeterministicParser
from src.parser.llm_extractor import llm_extractor
from src.parser.merge import extraction_merger
from src.embeddings.chunking import ParentChildChunker
from src.embeddings.encoder import embedding_encoder
from src.common.hashing import compute_file_hash
from src.common.exceptions import IngestionError
from src.common.audit import create_ocr_audit, create_parse_audit

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """
    Orchestrates the document ingestion pipeline.
    Routes files to appropriate extractors and sequences the processing steps.
    """
    
    def __init__(self):
        """Initialize orchestrator with all extractors and processors."""
        self.parser = DeterministicParser()
        self.chunker = ParentChildChunker()
    
    async def process_document(
        self,
        file_path: Path,
        document_id: int,
        discipline: Optional[str] = None,
    ) -> dict:
        """
        Process a document through the complete ingestion pipeline.
        
        Args:
            file_path: Path to the document file
            document_id: Database ID of the document record
            discipline: Optional discipline tag (ELC/MEC/INS/SIM)
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Step 1: Compute file hash for idempotency
            file_hash = compute_file_hash(file_path)
            logger.info(f"Processing document {document_id}: {file_path.name} (hash: {file_hash[:16]}...)")
            
            # Step 2: Route to appropriate extractor
            extractor_type = format_router.route(file_path)
            
            # Step 3: Extract text and metadata
            extraction_result = self._extract_text(file_path, extractor_type)
            
            # Step 4: Parse structured data (deterministic)
            parsed_doc = self.parser.parse(
                extraction_result["text"],
                page_count=extraction_result.get("page_count"),
            )
            
            # Create parse audit
            parse_audit = create_parse_audit(
                document_id=document_id,
                file_hash=file_hash,
                model_version="deterministic-v1",
                parser_type="deterministic",
                success=True,
                extracted_fields=parsed_doc.extraction_metadata.get("fields_extracted"),
            )
            parse_audit.log()
            
            # Step 5: LLM extraction pass (augmentation)
            try:
                llm_result = await llm_extractor.extract(
                    extraction_result["text"],
                    context={"discipline": discipline, "file_type": extractor_type},
                )
                
                # Merge deterministic + LLM results
                parsed_doc = extraction_merger.merge(parsed_doc, llm_result)
                
            except Exception as e:
                logger.warning(f"LLM extraction failed, using deterministic only: {e}")
                parsed_doc.extraction_metadata["llm_error"] = str(e)
            
            # Step 6: Create parent-child chunks
            parent_chunks, child_chunks = self.chunker.chunk_document(
                extraction_result["text"],
                document_id=document_id,
            )
            
            # Step 7: Generate embeddings for child chunks
            child_texts = [chunk.content for chunk in child_chunks]
            embeddings = embedding_encoder.encode_batch(child_texts, show_progress=False)
            
            # Step 8: Prepare results for persistence
            result = {
                "document_id": document_id,
                "file_hash": file_hash,
                "extraction_method": extraction_result.get("extraction_method", "unknown"),
                "page_count": extraction_result.get("page_count", 1),
                "parsed_data": parsed_doc,
                "parent_chunks": parent_chunks,
                "child_chunks": child_chunks,
                "embeddings": embeddings,
                "low_confidence_regions": extraction_result.get("low_confidence_regions", []),
                "blocks": extraction_result.get("blocks", []),
            }
            
            logger.info(
                f"Document {document_id} processing complete: "
                f"{len(parent_chunks)} parent chunks, {len(child_chunks)} child chunks"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Document processing failed for {document_id}: {e}", exc_info=True)
            raise IngestionError(f"Document processing failed: {e}") from e
    
    def _extract_text(self, file_path: Path, extractor_type: str) -> dict:
        """
        Extract text using the appropriate extractor.
        
        Args:
            file_path: Path to file
            extractor_type: Type of extractor (pdf, cad, office, image)
            
        Returns:
            Extraction results
        """
        if extractor_type == "pdf":
            return pdf_extractor.extract(file_path)
        elif extractor_type == "cad":
            return cad_extractor.extract(file_path)
        elif extractor_type == "office":
            return office_extractor.extract(file_path)
        elif extractor_type == "image":
            return image_extractor.extract(file_path)
        else:
            raise IngestionError(f"Unknown extractor type: {extractor_type}")


# Global orchestrator instance
ingestion_orchestrator = IngestionOrchestrator()