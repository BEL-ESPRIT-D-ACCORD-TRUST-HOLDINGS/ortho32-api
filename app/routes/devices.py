from fastapi import APIRouter, HTTPException, Depends
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable
from app.auth import require_scope

router = APIRouter(prefix="/devices", tags=["devices"])


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
async def list_devices():
    host = get_host_connection()
    envelope = MessageEnvelope(type="DEVICE_LIST", source="ortho32-api", data={})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "DEVICE_LIST_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/{id}")
async def get_device(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="DEVICE_GET", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "DEVICE_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.post("/{id}/connect")
async def connect_device(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="DEVICE_CONNECT", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "DEVICE_CONNECTED", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.post("/{id}/disconnect")
async def disconnect_device(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="DEVICE_DISCONNECT", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "DEVICE_DISCONNECTED", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.post("/{id}/reset")
async def reset_device(id: str, payload=Depends(require_scope("hardware.reset"))):
    host = get_host_connection()
    envelope = MessageEnvelope(type="DEVICE_RESET", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "DEVICE_RESET_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
