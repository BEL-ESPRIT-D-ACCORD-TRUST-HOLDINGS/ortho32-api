from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable

router = APIRouter(prefix="/fabric", tags=["fabric"])


def _wrap(data, type_, corr=None):
    return ResponseEnvelope(
        id=str(uuid.uuid4()),
        type=type_,
        timestamp=int(time.time() * 1000),
        source="ortho32-api",
        correlation_id=corr or str(uuid.uuid4()),
        data=data,
    )


@router.get("/topology")
async def get_topology():
    host = get_host_connection()
    envelope = MessageEnvelope(type="FABRIC_TOPOLOGY_GET", source="ortho32-api", data={})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "FABRIC_TOPOLOGY_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/status")
async def get_status():
    host = get_host_connection()
    envelope = MessageEnvelope(type="FABRIC_STATUS_GET", source="ortho32-api", data={})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "FABRIC_STATUS_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/transactions")
async def get_transactions():
    host = get_host_connection()
    envelope = MessageEnvelope(type="FABRIC_TRANSACTIONS_GET", source="ortho32-api", data={})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "FABRIC_TRANSACTIONS_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


class FabricCommand(BaseModel):
    command: str
    args: Dict[str, Any] = {}


@router.post("/commands")
async def post_command(cmd: FabricCommand):
    host = get_host_connection()
    envelope = MessageEnvelope(type="FABRIC_COMMAND", source="ortho32-api", data=cmd.model_dump())
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "FABRIC_COMMAND_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
