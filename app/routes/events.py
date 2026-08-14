from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import json
import asyncio

from app.ipc import get_host_connection, IPCUnavailable

router = APIRouter(prefix="/events", tags=["events"])

ALLOWED_EVENTS = {
    "device.connected",
    "device.disconnected",
    "fabric.transaction",
    "proof.verified",
    "proof.failed",
    "build.completed",
    "agent.started",
    "trace.completed",
}


@router.get("/stream")
async def stream_events(request: Request):
    host = get_host_connection()

    async def event_generator():
        try:
            # subscribe to all events (wildcard)
            async for env in host.subscribe("*"):
                if await request.is_disconnected():
                    break
                # filter to allowed types if needed; allow all but ensure mapping
                event_type = env.type
                # normalize dot notation: host may send DEVICE_CONNECTED etc, map to allowed
                data = json.dumps(env.model_dump())
                yield f"event: {event_type}\n"
                yield f"data: {data}\n\n"
                await asyncio.sleep(0)
        except IPCUnavailable as e:
            # stream error as SSE comment then close
            yield f"event: error\n"
            yield f"data: {json.dumps({'detail': f'Host unavailable: {str(e)}'})}\n\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })
