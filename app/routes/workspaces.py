from fastapi import APIRouter, HTTPException
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _wrap(data, type_, corr=None):
    return ResponseEnvelope(
        id=str(uuid.uuid4()),
        type=type_,
        timestamp=int(time.time() * 1000),
        source="ortho32-api",
        correlation_id=corr or str(uuid.uuid4()),
        data=data,
    )


@router.get("")
async def list_workspaces():
    host = get_host_connection()
    envelope = MessageEnvelope(type="WORKSPACE_LIST", source="ortho32-api", data={})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "WORKSPACE_LIST_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.post("/{id}/open")
async def open_workspace(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="WORKSPACE_OPEN", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "WORKSPACE_OPEN_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/current")
async def get_current():
    host = get_host_connection()
    envelope = MessageEnvelope(type="WORKSPACE_CURRENT_GET", source="ortho32-api", data={})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "WORKSPACE_CURRENT_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
