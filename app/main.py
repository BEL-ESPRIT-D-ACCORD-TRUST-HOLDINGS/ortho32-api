from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ipc import get_host_connection
from app.routes import (
    system,
    auth,
    devices,
    fabric,
    tensor,
    proofs,
    builds,
    traces,
    agents,
    apps,
    marketplace,
    workspaces,
    events,
    ai,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    host = get_host_connection()
    try:
        await host.connect()
    except Exception:
        # Host may not be available at startup; routes will return 503 until reconnect
        pass
    yield
    try:
        await host.close()
    except Exception:
        pass


app = FastAPI(
    title="ORTHO32 API",
    version="1.0.0",
    description="Python/FastAPI bridge to ORTHOHost C# service via named pipe IPC",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# JWT middleware - parses Authorization header but does not enforce; enforcement via require_scope dependencies
@app.middleware("http")
async def jwt_middleware(request: Request, call_next):
    # Allow docs/openapi without auth
    # Token verification is handled per-route via dependencies
    response = await call_next(request)
    return response


# Register all routers with prefix /api/v1
app.include_router(system.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(devices.router, prefix="/api/v1")
app.include_router(fabric.router, prefix="/api/v1")
app.include_router(tensor.router, prefix="/api/v1")
app.include_router(proofs.router, prefix="/api/v1")
app.include_router(builds.router, prefix="/api/v1")
app.include_router(traces.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(apps.router, prefix="/api/v1")
app.include_router(marketplace.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "7032"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
