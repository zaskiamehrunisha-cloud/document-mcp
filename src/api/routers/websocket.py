"""WebSocket router for live upload status updates."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from src.db.models import ReferenceDocument
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections for live status updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        logger.info(f"WebSocket connected for job_id={job_id}")

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.active_connections:
            if websocket in self.active_connections[job_id]:
                self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        logger.info(f"WebSocket disconnected for job_id={job_id}")

    async def send_update(self, job_id: str, data: dict):
        if job_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(data)
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket message: {e}")
                    disconnected.append(connection)
            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn, job_id)


manager = ConnectionManager()


@router.websocket("/ws/status/{job_id}")
async def websocket_status(
    websocket: WebSocket,
    job_id: str,
):
    """
    WebSocket endpoint for live upload status updates.

    Subscribers receive real-time status updates as documents are processed.
    """
    await manager.connect(websocket, job_id)

    try:
        # Send initial status
        async with async_session_factory() as session:
            result = await session.execute(
                select(ReferenceDocument).where(ReferenceDocument.job_id == job_id)
            )
            document = result.scalar_one_or_none()

            if document:
                await websocket.send_json(
                    {
                        "type": "status_update",
                        "job_id": job_id,
                        "document_id": document.id,
                        "status": document.status,
                        "progress": 100 if document.status in ["Approved", "Rejected"] else 50,
                        "updated_at": (
                            document.updated_at.isoformat() if document.updated_at else None
                        ),
                    }
                )

        # Poll for updates until document is finalized
        last_status = None
        while True:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(ReferenceDocument).where(ReferenceDocument.job_id == job_id)
                )
                document = result.scalar_one_or_none()

                if document:
                    current_status = document.status

                    # Send update if status changed
                    if current_status != last_status:
                        await websocket.send_json(
                            {
                                "type": "status_update",
                                "job_id": job_id,
                                "document_id": document.id,
                                "status": current_status,
                                "progress": (
                                    100 if current_status in ["Approved", "Rejected"] else 50
                                ),
                                "updated_at": (
                                    document.updated_at.isoformat() if document.updated_at else None
                                ),
                            }
                        )
                        last_status = current_status

                        # Close connection if document is finalized
                        if current_status in ["Approved", "Rejected"]:
                            break

            # Wait before next poll
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for job_id={job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job_id={job_id}: {e}")
    finally:
        manager.disconnect(websocket, job_id)


async def notify_status_change(job_id: str, status: str, document_id: int | None = None):
    """
    Broadcast status change to all connected clients.

    This can be called from background tasks when document status changes.
    """
    await manager.send_update(
        job_id,
        {
            "type": "status_update",
            "job_id": job_id,
            "document_id": document_id,
            "status": status,
            "progress": 100 if status in ["Approved", "Rejected"] else 50,
        },
    )
