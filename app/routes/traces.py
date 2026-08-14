from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable

router = APIRouter(prefix="/traces", tags=["traces"])


def _wrap(data, type_, corr=None):
    return ResponseEnvelope(
        id=str(uuid.uuid4()),
        type=type_,
        timestamp=int(time.time() * 1000),
        source="ortho32-api",
        correlation_id=corr or str(uuid.uuid4()),
        data=data,
    )


class CaptureRequest(BaseModel):
    target: Optional[str] = None
    # architectural integer
    cycles: int = Field(..., description="architectural integer: total cycles")
    config: Dict[str, Any] = {}


class ReplayRequest(BaseModel):
    trace_id: Optional[str] = None
    config: Dict[str, Any] = {}


class CompareRequest(BaseModel):
    trace_a: str
    trace_b: str


@router.post("/capture")
async def capture_trace(req: CaptureRequest):
    host = get_host_connection()
    envelope = MessageEnvelope(type="TRACE_CAPTURE", source="ortho32-api", data=req.model_dump())
    try:
        resp = await host.send(envelope)
        data = resp.data
        if isinstance(data, dict):
            if "cycleNumber" in data:
                data["cycleNumber"] = int(data["cycleNumber"])
            if "cycles" in data:
                data["cycles"] = int(data["cycles"])
        return _wrap(data, "TRACE_CAPTURE_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/{id}")
async def get_trace(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="TRACE_GET", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        data = resp.data
        if isinstance(data, dict):
            if "cycleNumber" in data:
                data["cycleNumber"] = int(data["cycleNumber"])
            if "cycles" in data:
                data["cycles"] = int(data["cycles"])
        return _wrap(data, "TRACE_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.post("/{id}/replay")
async def replay_trace(id: str, req: ReplayRequest):
    host = get_host_connection()
    payload = req.model_dump()
    payload["id"] = id
    envelope = MessageEnvelope(type="TRACE_REPLAY", source="ortho32-api", data=payload)
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "TRACE_REPLAY_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.post("/compare")
async def compare_traces(req: CompareRequest):
    host = get_host_connection()
    envelope = MessageEnvelope(type="TRACE_COMPARE", source="ortho32-api", data=req.model_dump())
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "TRACE_COMPARE_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
