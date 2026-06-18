"""
Main application entry point for DOCINTEL.
"""
from docintel.api.routes import router as api_router
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from docintel.config.settings import settings
from docintel.common.logging import get_logger
from docintel.api.routes import router as api_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("DOCINTEL application starting up")
    yield
    logger.info("DOCINTEL application shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="DOCINTEL",
        description="Engineering Document Intelligence",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix="/api")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    app.include_router(api_router)
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("docintel.main:app", host=settings.host, port=settings.port, reload=settings.debug)