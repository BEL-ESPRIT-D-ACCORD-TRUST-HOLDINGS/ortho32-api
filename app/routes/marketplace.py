from fastapi import APIRouter, HTTPException, Depends
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable
from app.auth import require_scope

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def _wrap(data, type_, corr=None):
    return ResponseEnvelope(
        id=str(uuid.uuid4()),
        type=type_,
        timestamp=int(time.time() * 1000),
        source="ortho32-api",
        correlation_id=corr or str(uuid.uuid4()),
        data=data,
    )


@router.get("/packages")
async def list_packages():
    host = get_host_connection()
    envelope = MessageEnvelope(type="MARKETPLACE_LIST", source="ortho32-api", data={})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "MARKETPLACE_LIST_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/packages/{id}")
async def get_package(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="MARKETPLACE_GET", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "MARKETPLACE_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.post("/packages/{id}/install")
async def install_package(id: str, payload=Depends(require_scope("marketplace.install"))):
    host = get_host_connection()
    envelope = MessageEnvelope(type="MARKETPLACE_INSTALL", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "MARKETPLACE_INSTALL_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
