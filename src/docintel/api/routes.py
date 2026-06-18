"""FastAPI routers for the DOCINTEL pipeline."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from docintel.ingestion.pipeline import get_pipeline

router = APIRouter(prefix="/api/v1", tags=["pipeline"])


class IngestRequest(BaseModel):
    file_path: str
    discipline: str
    metadata: dict | None = None


class ValidateRequest(BaseModel):
    structured_record: dict


class SearchRequest(BaseModel):
    question: str
    discipline: str | None = None
    top_k: int = 5


class SubmitRequest(BaseModel):
    document_id: int


@router.post("/ingest")
async def ingest_document(request: IngestRequest):
    """Ingest a document through the full pipeline."""
    pipeline = get_pipeline()
    result = await pipeline.ingest(
        file_path=request.file_path,
        discipline=request.discipline,
        metadata=request.metadata,
    )
    return result


@router.post("/validate")
async def validate_document(request: ValidateRequest):
    """Validate a structured record against rules."""
    pipeline = get_pipeline()
    result = await pipeline.validate(request.structured_record)
    return result


@router.post("/pipeline/run")
async def run_full_pipeline(request: IngestRequest):
    """Run the full pipeline: ingest → validate → submit."""
    pipeline = get_pipeline()
    result = await pipeline.validate_and_submit(
        file_path=request.file_path,
        discipline=request.discipline,
        metadata=request.metadata,
    )
    return result


@router.post("/search")
async def search_knowledge_base(request: SearchRequest):
    """Search the knowledge base."""
    from docintel.retrieval.qa import get_qa

    qa = get_qa()
    result = await qa.answer_question(
        question=request.question,
        top_k=request.top_k,
        discipline=request.discipline,
    )
    return result


@router.post("/submit")
async def submit_to_docon(request: SubmitRequest):
    """Submit a validated document to DOCON."""
    from docintel.docon.gateway import get_docon_gateway

    gateway = get_docon_gateway()
    # Simplified - would need proper document loading
    return {
        "document_id": request.document_id,
        "outcome": "not_implemented",
        "message": "DOCON submission requires document loading from database",
    }