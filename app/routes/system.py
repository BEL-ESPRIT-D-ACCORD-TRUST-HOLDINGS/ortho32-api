from fastapi import APIRouter, HTTPException
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable

router = APIRouter(prefix="/system", tags=["system"])


def _envelope(data: dict, type_: str, correlation_id: str = None) -> ResponseEnvelope:
    return ResponseEnvelope(
        id=str(uuid.uuid4()),
        type=type_,
        timestamp=int(time.time() * 1000),
        source="ortho32-api",
        correlation_id=correlation_id or str(uuid.uuid4()),
        data=data,
    )


@router.get("/status")
async def get_status():
    host = get_host_connection()
    envelope = MessageEnvelope(type="STATUS_GET", source="ortho32-api", data={})
    try:
        resp = await host.send(envelope)
        return _envelope(
            data=resp.data,
            type_="STATUS_RESULT",
            correlation_id=envelope.correlation_id,
        )
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/version")
async def get_version():
    host = get_host_connection()
    envelope = MessageEnvelope(type="VERSION_GET", source="ortho32-api", data={})
    try:
        resp = await host.send(envelope)
        return _envelope(
            data=resp.data, type_="VERSION_RESULT", correlation_id=envelope.correlation_id
        )
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
