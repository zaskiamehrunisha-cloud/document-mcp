"""Search and Q&A router."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.api.schemas import SearchRequest, SearchResponse, AskRequest, AskResponse
from src.search.qa import qa_service
from src.common.exceptions import DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Search for documents using hybrid search (vector + full-text).
    
    Args:
        request: Search request with query and filters
        db: Database session
        
    Returns:
        Search results with ranked chunks
    """
    try:
        result = await qa_service.search(
            query=request.query,
            limit=request.limit,
            discipline=request.discipline,
            document_ids=request.document_ids,
        )
        
        # Transform to response format
        search_results = []
        for item in result["results"]:
            search_results.append({
                "chunk_id": item["chunk"]["id"],
                "content": item["chunk"]["content"],
                "document_id": item["document"]["id"],
                "document_number": item["document"].get("document_number"),
                "title": item["document"].get("title"),
                "discipline": item["document"].get("discipline"),
                "score": item["score"],
                "search_type": item["search_type"],
            })
        
        return SearchResponse(
            query=result["query"],
            results=search_results,
            total=result["total"],
        )
    
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a natural language question and get a grounded answer with citations.
    
    Args:
        request: Q&A request with question and optional filters
        db: Database session
        
    Returns:
        Answer with citations and confidence level
    """
    try:
        result = await qa_service.ask(
            query=request.query,
            discipline=request.discipline,
            document_ids=request.document_ids,
        )
        
        return AskResponse(
            answer=result["answer"],
            confidence=result["confidence"],
            citations=result["citations"],
            query=result["query"],
            context_chunks_used=result["context_chunks_used"],
        )
    
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Q&A failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Q&A failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Q&A failed: {str(e)}",
        )