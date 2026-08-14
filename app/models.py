from __future__ import annotations
from enum import Enum
from typing import Generic, TypeVar, Optional, Any, List, Dict
from pydantic import BaseModel, Field
import uuid
import time

T = TypeVar("T")


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    CROSS_VERIFIED = "CROSS_VERIFIED"
    TESTED = "TESTED"
    OBSERVED = "OBSERVED"
    ASSUMED = "ASSUMED"
    UNVERIFIED = "UNVERIFIED"
    FAILED = "FAILED"


class ResponseEnvelope(BaseModel, Generic[T]):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    source: str = Field(default="ortho32-api")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: T


class MessageEnvelope(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    source: str = Field(default="ortho32-api")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: Any = Field(default_factory=dict)


class EventEnvelope(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    source: str
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: Any = Field(default_factory=dict)


class Session(BaseModel):
    id: str
    identity: str
    scopes: List[str]
    created_at: int
    expires_at: int
    token: Optional[str] = None


class AppManifest(BaseModel):
    id: str
    name: str
    version: str
    description: Optional[str] = None
    entrypoint: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


class TensorJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    status: str = Field(default="queued")
    # architectural integer - cycle count must be integer, never float
    cycles: int = Field(..., description="architectural integer: cycle count")
    payload: Optional[Dict[str, Any]] = None
    created_at: int = Field(default_factory=lambda: int(time.time() * 1000))


class TensorResult(BaseModel):
    job_id: str
    status: str
    # architectural integer
    cycles: int = Field(..., description="architectural integer: cycle count")
    result: Optional[Any] = None
    error: Optional[str] = None


class InferenceEvent(BaseModel):
    id: str
    job_id: str
    type: str
    # architectural integer
    cycleNumber: int = Field(..., description="architectural integer: cycle number")
    data: Optional[Any] = None


class BuildEvent(BaseModel):
    id: str
    build_id: str
    type: str
    message: str
    # architectural integer
    cycleNumber: int = Field(..., description="architectural integer: cycle number")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))


class ProofResult(BaseModel):
    id: str
    status: VerificationStatus
    dependencies: List[str] = Field(default_factory=list)
    details: Optional[Dict[str, Any]] = None
    verified_at: Optional[int] = None


class TraceRecord(BaseModel):
    id: str
    name: Optional[str] = None
    # architectural integer
    cycleNumber: int = Field(..., description="architectural integer: cycle number")
    cycles: int = Field(..., description="architectural integer: total cycles")
    events: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: int = Field(default_factory=lambda: int(time.time() * 1000))


class DeviceInfo(BaseModel):
    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    status: str = Field(default="disconnected")
    connected: bool = Field(default=False)
    capabilities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FabricTopology(BaseModel):
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    links: List[Dict[str, Any]] = Field(default_factory=list)
    version: Optional[str] = None


class WorkspaceSnapshot(BaseModel):
    id: str
    name: str
    path: Optional[str] = None
    active: bool = Field(default=False)
    created_at: int = Field(default_factory=lambda: int(time.time() * 1000))


class AgentTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    type: str
    status: str = Field(default="pending")
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    # architectural integer
    cycleNumber: int = Field(default=0, description="architectural integer: cycle number")
    created_at: int = Field(default_factory=lambda: int(time.time() * 1000))
