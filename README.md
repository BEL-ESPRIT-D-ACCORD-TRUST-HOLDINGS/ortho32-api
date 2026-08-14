# ortho32-api

Python 3.11+ FastAPI bridge to ORTHOHost C# service via named pipe IPC.

Port: **7032**

## Requirements

- Python 3.11+
- ORTHOHost C# service exposing `\\.\pipe\ortho-host` named pipe

## Install

```bash
pip install -e .[dev]
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7032
```

App starts `HostConnection` on lifespan startup and reconnects on pipe error without restarting the process.

## IPC

- Production (Windows): `win32pipe` via `pywin32` to `\\.\pipe\ortho-host`
  - JSON envelope per message: `{id, type, timestamp, source, correlation_id, data}`
  - `send()` writes JSON line, reads JSON response into `EventEnvelope`
  - `subscribe()` long-polls push events
- Cross-platform dev fallback: `localhost:7032` TCP socket if `pywin32` not available

All routes send `MessageEnvelope` to `HostConnection`; never call hardware/providers directly. When Host unavailable, routes return `503 ServiceUnavailable` (never fake data).

## Auth

JWT signed with `SECRET_KEY` env (default dev secret). Scopes:

- `device.read` `tensor.submit` `proof.verify` `trace.read` `fabric.inspect`
- Elevated: `hardware.reset` `marketplace.install` (checked via `require_scope()`)

Create token:

```bash
curl -X POST http://localhost:7032/api/v1/auth/session -H "Content-Type: application/json" -d '{"identity":"alice","scopes":["device.read","hardware.reset"]}'
```

## Tests

```bash
pytest
```

## OpenAPI

Auto-generated from route decorators (no manual YAML):

- Swagger UI: http://localhost:7032/docs
- ReDoc: http://localhost:7032/redoc
- JSON: http://localhost:7032/openapi.json

## Envelope Contract

All responses are `ResponseEnvelope<T>`:

```json
{
  "id": "uuid",
  "type": "RESULT_TYPE",
  "timestamp": 1710000000000,
  "source": "ortho32-api",
  "correlation_id": "uuid",
  "data": {}
}
```

`cycles` and `cycleNumber` are architectural integers (`int`, never `float`). `VerificationStatus` is enum with 7 values: `VERIFIED CROSS_VERIFIED TESTED OBSERVED ASSUMED UNVERIFIED FAILED`.
