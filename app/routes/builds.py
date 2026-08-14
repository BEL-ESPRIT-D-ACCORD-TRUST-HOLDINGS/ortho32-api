from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable

router = APIRouter(prefix="/builds", tags=["builds"])


def _wrap(data, type_, corr=None):
    return ResponseEnvelope(
        id=str(uuid.uuid4()),
        type=type_,
        timestamp=int(time.time() * 1000),
        source="ortho32-api",
        correlation_id=corr or str(uuid.uuid4()),
        data=data,
    )


class BuildRequest(BaseModel):
    project_id: Optional[str] = None
    target: Optional[str] = None
    config: Dict[str, Any] = {}


@router.post("")
async def create_build(req: BuildRequest):
    host = get_host_connection()
    # uses subprocess to run real compiler via HostConnection BUILD_RUN action (never local fake)
    envelope = MessageEnvelope(type="BUILD_RUN", source="ortho32-api", data=req.model_dump())
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "BUILD_STARTED", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/{id}")
async def get_build(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="BUILD_GET", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "BUILD_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/{id}/logs")
async def get_build_logs(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="BUILD_LOGS_GET", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "BUILD_LOGS_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
