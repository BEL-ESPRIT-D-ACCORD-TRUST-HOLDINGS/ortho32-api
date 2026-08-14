from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable

router = APIRouter(prefix="/tensor", tags=["tensor"])


def _wrap(data, type_, corr=None):
    return ResponseEnvelope(
        id=str(uuid.uuid4()),
        type=type_,
        timestamp=int(time.time() * 1000),
        source="ortho32-api",
        correlation_id=corr or str(uuid.uuid4()),
        data=data,
    )


class TensorJobRequest(BaseModel):
    name: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    # architectural integer
    cycles: int = Field(..., description="architectural integer: cycle count")


@router.post("/jobs")
async def create_job(req: TensorJobRequest):
    host = get_host_connection()
    envelope = MessageEnvelope(
        type="TENSOR_SUBMIT",
        source="ortho32-api",
        data=req.model_dump(),
    )
    try:
        resp = await host.send(envelope)
        # Ensure cycles is int in response
        data = resp.data
        if isinstance(data, dict) and "cycles" in data:
            data["cycles"] = int(data["cycles"])
        return _wrap(data, "TENSOR_SUBMIT_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/jobs/{id}")
async def get_job(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="TENSOR_GET", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        data = resp.data
        if isinstance(data, dict) and "cycles" in data:
            data["cycles"] = int(data["cycles"])
        return _wrap(data, "TENSOR_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/jobs/{id}/trace")
async def get_job_trace(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="TENSOR_TRACE_GET", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        data = resp.data
        # Normalize cycleNumber fields to int
        if isinstance(data, dict):
            if "cycleNumber" in data:
                data["cycleNumber"] = int(data["cycleNumber"])
            if "cycles" in data:
                data["cycles"] = int(data["cycles"])
            if "events" in data and isinstance(data["events"], list):
                for ev in data["events"]:
                    if isinstance(ev, dict) and "cycleNumber" in ev:
                        ev["cycleNumber"] = int(ev["cycleNumber"])
        return _wrap(data, "TENSOR_TRACE_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
