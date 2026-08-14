from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable

router = APIRouter(prefix="/agents", tags=["agents"])


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
async def list_agents():
    host = get_host_connection()
    envelope = MessageEnvelope(type="AGENT_LIST", source="ortho32-api", data={})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "AGENT_LIST_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


class TaskRequest(BaseModel):
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    # architectural integer
    cycleNumber: int = Field(default=0, description="architectural integer: cycle number")


@router.post("/{id}/tasks")
async def create_task(id: str, req: TaskRequest):
    host = get_host_connection()
    data = req.model_dump()
    data["agent_id"] = id
    envelope = MessageEnvelope(type="AGENT_TASK_CREATE", source="ortho32-api", data=data)
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "AGENT_TASK_CREATED", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/{id}/tasks/{taskId}")
async def get_task(id: str, taskId: str):
    host = get_host_connection()
    envelope = MessageEnvelope(
        type="AGENT_TASK_GET", source="ortho32-api", data={"agent_id": id, "task_id": taskId}
    )
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "AGENT_TASK_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
