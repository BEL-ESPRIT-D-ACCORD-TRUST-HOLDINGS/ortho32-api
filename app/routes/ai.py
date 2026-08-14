from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable

router = APIRouter(prefix="/ai", tags=["ai"])


def _wrap(data, type_, corr=None):
    return ResponseEnvelope(
        id=str(uuid.uuid4()),
        type=type_,
        timestamp=int(time.time() * 1000),
        source="ortho32-api",
        correlation_id=corr or str(uuid.uuid4()),
        data=data,
    )


class ConverseRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Dict[str, Any]]
    stream: bool = False


class InvokeRequest(BaseModel):
    model: Optional[str] = None
    prompt: str
    parameters: Dict[str, Any] = {}


class EmbeddingsRequest(BaseModel):
    model: Optional[str] = None
    input: Any


@router.post("/converse")
async def converse(req: ConverseRequest):
    host = get_host_connection()
    envelope = MessageEnvelope(type="INFERENCE_SUBMIT", source="ortho32-api", data={"action": "converse", **req.model_dump()})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "INFERENCE_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.post("/invoke")
async def invoke(req: InvokeRequest):
    host = get_host_connection()
    envelope = MessageEnvelope(type="INFERENCE_SUBMIT", source="ortho32-api", data={"action": "invoke", **req.model_dump()})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "INFERENCE_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/models")
async def list_models():
    host = get_host_connection()
    envelope = MessageEnvelope(type="INFERENCE_SUBMIT", source="ortho32-api", data={"action": "models.list"})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "MODELS_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/providers")
async def list_providers():
    host = get_host_connection()
    envelope = MessageEnvelope(type="INFERENCE_SUBMIT", source="ortho32-api", data={"action": "providers.list"})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "PROVIDERS_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.post("/embeddings")
async def embeddings(req: EmbeddingsRequest):
    host = get_host_connection()
    envelope = MessageEnvelope(type="INFERENCE_SUBMIT", source="ortho32-api", data={"action": "embeddings", **req.model_dump()})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "EMBEDDINGS_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/usage")
async def usage():
    host = get_host_connection()
    envelope = MessageEnvelope(type="INFERENCE_SUBMIT", source="ortho32-api", data={"action": "usage"})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "USAGE_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
