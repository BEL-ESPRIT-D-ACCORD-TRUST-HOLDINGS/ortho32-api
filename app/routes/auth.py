from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import uuid
import time

from app.auth import create_token, verify_token
from app.models import ResponseEnvelope
from app.ipc import get_host_connection, IPCUnavailable
from app.models import MessageEnvelope

router = APIRouter(prefix="/auth", tags=["auth"])


class SessionRequest(BaseModel):
    identity: str
    scopes: List[str] = []


class SessionResponse(BaseModel):
    token: str
    identity: str
    scopes: List[str]
    expires_at: int


def _wrap(data, type_, correlation_id=None):
    return ResponseEnvelope(
        id=str(uuid.uuid4()),
        type=type_,
        timestamp=int(time.time() * 1000),
        source="ortho32-api",
        correlation_id=correlation_id or str(uuid.uuid4()),
        data=data,
    )


from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth import verify_token as _verify

security = HTTPBearer(auto_error=True)


@router.post("/session", include_in_schema=True)
async def post_session(req: SessionRequest):
    allowed = {
        "device.read",
        "tensor.submit",
        "proof.verify",
        "trace.read",
        "fabric.inspect",
        "hardware.reset",
        "marketplace.install",
    }
    for s in req.scopes:
        if s not in allowed:
            raise HTTPException(status_code=400, detail=f"Unknown scope: {s}")
    host = get_host_connection()
    envelope = MessageEnvelope(type="SESSION_CREATE", source="ortho32-api", data=req.model_dump())
    try:
        await host.send(envelope)
    except IPCUnavailable:
        pass
    token = create_token(req.identity, req.scopes)
    # decode to get exp
    payload = _verify(token)
    exp = payload.get("exp")
    if isinstance(exp, int):
        expires_at = exp
    else:
        expires_at = int(time.time()) + 86400
    data = SessionResponse(token=token, identity=req.identity, scopes=req.scopes, expires_at=expires_at)
    return _wrap(data.model_dump(), "SESSION_CREATED", envelope.correlation_id)


@router.get("/session")
async def read_session(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = _verify(credentials.credentials)
    return _wrap(
        {
            "identity": payload.get("sub"),
            "scopes": payload.get("scopes", []),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
        },
        "SESSION_RESULT",
    )


@router.delete("/session")
async def delete_session(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = _verify(credentials.credentials)
    host = get_host_connection()
    envelope = MessageEnvelope(
        type="SESSION_DELETE", source="ortho32-api", data={"identity": payload.get("sub")}
    )
    try:
        await host.send(envelope)
    except IPCUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Host unavailable: {str(e)}")
    return _wrap({"deleted": True, "identity": payload.get("sub")}, "SESSION_DELETED", envelope.correlation_id)
