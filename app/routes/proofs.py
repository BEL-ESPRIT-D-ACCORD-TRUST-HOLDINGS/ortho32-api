from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
import uuid
import time

from app.models import MessageEnvelope, ResponseEnvelope, VerificationStatus
from app.ipc import get_host_connection, IPCUnavailable

router = APIRouter(prefix="/proofs", tags=["proofs"])


def _wrap(data, type_, corr=None):
    return ResponseEnvelope(
        id=str(uuid.uuid4()),
        type=type_,
        timestamp=int(time.time() * 1000),
        source="ortho32-api",
        correlation_id=corr or str(uuid.uuid4()),
        data=data,
    )


class VerifyRequest(BaseModel):
    artifact_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    proof: Optional[Dict[str, Any]] = None


@router.post("/verify")
async def verify_proof(req: VerifyRequest):
    host = get_host_connection()
    envelope = MessageEnvelope(type="PROOF_VERIFY", source="ortho32-api", data=req.model_dump())
    try:
        resp = await host.send(envelope)
        data = resp.data
        # Ensure status is valid VerificationStatus enum, never raw string mismatch
        if isinstance(data, dict) and "status" in data:
            try:
                status = VerificationStatus(data["status"])
                data["status"] = status.value
            except ValueError:
                raise HTTPException(status_code=502, detail=f"Invalid VerificationStatus from host: {data['status']}")
        return _wrap(data, "PROOF_VERIFY_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/{id}")
async def get_proof(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="PROOF_GET", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        data = resp.data
        if isinstance(data, dict) and "status" in data:
            try:
                VerificationStatus(data["status"])
            except ValueError:
                raise HTTPException(status_code=502, detail=f"Invalid VerificationStatus from host: {data['status']}")
        return _wrap(data, "PROOF_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")


@router.get("/{id}/dependencies")
async def get_dependencies(id: str):
    host = get_host_connection()
    envelope = MessageEnvelope(type="PROOF_DEPENDENCIES_GET", source="ortho32-api", data={"id": id})
    try:
        resp = await host.send(envelope)
        return _wrap(resp.data, "PROOF_DEPENDENCIES_RESULT", envelope.correlation_id)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
