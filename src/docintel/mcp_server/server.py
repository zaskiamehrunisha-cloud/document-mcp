"""
MCP server for DOCINTEL.
Exposes four tools via FastMCP with streamable-HTTP transport.
"""

from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from docintel.mcp_server.tools import (
    ingest_document,
    search_knowledge_base,
    submit_to_docon,
    validate_document,
)

# Create FastMCP instance
mcp = FastMCP(
    "docintel",
    description="Engineering Document Intelligence MCP Server - Governance gateway and RAG knowledge engine",
    version="0.1.0",
)


@mcp.tool()
async def ingest_document_tool(
    file_path: str,
    discipline: str,
    metadata: dict | None = None,
) -> dict:
    """
    Ingest a document into the system.
    
    Args:
        file_path: Path to the document file
        discipline: Submitting discipline (ELC, MEC, INS, SIM, etc.)
        metadata: Optional metadata
        
    Returns:
        Ingestion result with document_id and structured_record
    """
    return await ingest_document(file_path, discipline, metadata)


@mcp.tool()
async def validate_document_tool(
    document_id: int | None = None,
    structured_record: dict | None = None,
) -> dict:
    """
    Validate a document against reference rules.
    
    Args:
        document_id: Database ID of the document (alternative to structured_record)
        structured_record: Structured record to validate (alternative to document_id)
        
    Returns:
        Validation result with conforms flag and violations
    """
    return await validate_document(document_id, structured_record)


@mcp.tool()
async def search_knowledge_base_tool(
    question: str,
    discipline: str | None = None,
    top_k: int = 5,
) -> dict:
    """
    Search the knowledge base and answer a question.
    
    Args:
        question: Natural-language engineering question
        discipline: Optional discipline filter
        top_k: Number of results to retrieve
        
    Returns:
        Answer with citations and sources
    """
    return await search_knowledge_base(question, discipline, top_k)


@mcp.tool()
async def submit_to_docon_tool(
    document_id: int,
) -> dict:
    """
    Validate and submit a document to DOCON.
    
    Args:
        document_id: Database ID of the document
        
    Returns:
        Submission result with outcome and DOCON reference if successful
    """
    return await submit_to_docon(document_id)


# Create the ASGI app for streamable HTTP
app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app):
    """
    Lifespan context manager for the MCP server.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("MCP server starting up")
    yield
    # Shutdown
    logger.info("MCP server shutting down")


# Update app with lifespan
app.router.lifespan_context = lifespan