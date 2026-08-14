# ortho32-api

Canonical versioned REST + SSE gateway for ORTHO-32. All ORTHO clients (Swift desktop, Java SDK, remote HTTP, local IPC) speak this contract. No desktop internals leak through; the API sits over the ORTHO service layer and routes to Fabric only via typed operations.

- **Port:** `7032` (configurable via `PORT` / `ORTHO_API_PORT`)
- **Versioning:** URL prefix `/api/v1/*`. Breaking changes → `/api/v2`. `GET /api/v1/system/version` reports `apiVersion`.
- **Envelopes:** Every response (and every SSE `data:` frame) is `{ id, type, timestamp, source, correlation_id, data }`.

## Quick start

```bash
npm install
npm run dev      # tsx watch on :7032
npm run build && npm start
npm test
```

## Authentication & Capability Scopes

Stateless JWT capability tokens. Issue via:

```bash
curl -X POST http://localhost:7032/api/v1/auth/session \
  -H 'Content-Type: application/json' \
  -d '{"principal":"alice"}'
# => { id, type, timestamp, source, correlation_id, data: { token, scopes, expiresAt } }

curl http://localhost:7032/api/v1/devices -H "Authorization: Bearer $TOKEN"
```

Token payload: `{ sub, scopes: string[], iat, exp }` signed with `ORTHO_JWT_SECRET`.

### Scope model

Scopes are capabilities, not roles. Each route declares required scope(s); middleware returns `403 { error:forbidden, requiredScope }` when missing.

Default scopes issued to any principal:

`devices.read` `devices.connect` `fabric.read` `fabric.commands` `tensor.jobs` `proofs.*` `builds.*` `traces.*` `agents.*` `apps.*` `workspaces.*` `events.stream` `ai.*` `marketplace.read`

Elevated scopes (never in default token):

- `hardware.reset` — required for `POST /api/v1/devices/:id/reset`
- `marketplace.install` — required for `POST /api/v1/marketplace/packages/:id/install`

Requesting elevated scopes as non-privileged principal silently drops them. Privileged principals (`admin`, `system`) may request them explicitly:

```bash
curl -X POST http://localhost:7032/api/v1/auth/session \
  -d '{"principal":"admin","requestedScopes":["hardware.reset"]}'
```

Inspect: `GET /api/v1/auth/session` — Revoke: `DELETE /api/v1/auth/session`.

## Envelope

All responses and SSE events use the same envelope:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "tensor.job.created",
  "timestamp": "2026-01-01T00:00:00.000Z",
  "source": "ortho32-api",
  "correlation_id": "req-123",
  "data": { }
}
```

- `id` — server-generated UUID per envelope
- `type` — dot-notation logical type (`devices.list`, `proof.verified`, `error.forbidden`)
- `timestamp` — ISO-8601
- `source` — always `ortho32-api`
- `correlation_id` — echo of `X-Correlation-ID` / `X-Request-ID` or generated UUID; also sent as response header `x-correlation-id`
- `data` — typed payload (see `src/schemas` / OpenAPI)

Errors are also enveloped: `type: "error"` with `data: { error, code }`.

## Key contracts

### `cycles` is integer, architectural — never wall-clock

Every `cycles`, `CycleRecord.cycleNumber`, `TensorJob.cycles`, `Trace.cycles`, `FabricStatus.cycle` is `integer >=0`. Docs and Zod schemas annotate this. Clients must not treat it as `ms` or `float`.

### `VerificationStatus` — 7 disjoint values, never interchangeable

```ts
type VerificationStatus = 'VERIFIED' | 'CROSS_VERIFIED' | 'TESTED' | 'OBSERVED' | 'ASSUMED' | 'UNVERIFIED' | 'FAILED'
```

`VERIFIED` ≠ `CROSS_VERIFIED`. UI must not collapse them.

### Public schemas never expose internals

`Device` / `TensorJob` / `Trace` / `Proof` / `Workspace` / `AgentTask` are public. Fields like `BAR0`, `Win32 HANDLE`, raw FPGA pointer are forbidden in schemas, examples, and logs. See `src/schemas/index.ts`.

## Routes

| Group | Method & Path |
|-------|---------------|
| **system** | `GET /api/v1/system/status` `GET /api/v1/system/version` |
| **auth** | `POST /api/v1/auth/session` `GET /api/v1/auth/session` `DELETE /api/v1/auth/session` |
| **devices** | `GET /api/v1/devices` `GET /api/v1/devices/:id` `POST :id/connect` `POST :id/disconnect` `POST :id/reset` (elevated) |
| **fabric** | `GET /api/v1/fabric/topology` `GET /api/v1/fabric/status` `GET /api/v1/fabric/transactions` `POST /api/v1/fabric/commands` |
| **tensor** | `POST /api/v1/tensor/jobs` `GET /api/v1/tensor/jobs/:id` `GET /api/v1/tensor/jobs/:id/trace` |
| **proofs** | `POST /api/v1/proofs/verify` `GET /api/v1/proofs/:id` `GET /api/v1/proofs/:id/dependencies` |
| **builds** | `POST /api/v1/builds` `GET /api/v1/builds/:id` `GET /api/v1/builds/:id/logs` |
| **traces** | `POST /api/v1/traces/capture` `GET /api/v1/traces/:id` `POST /api/v1/traces/:id/replay` `POST /api/v1/traces/compare` |
| **agents** | `GET /api/v1/agents` `POST /api/v1/agents/:id/tasks` `GET /api/v1/agents/:id/tasks/:taskId` |
| **apps** | `GET /api/v1/apps` `POST /api/v1/apps/:id/open` |
| **marketplace** | `GET /api/v1/marketplace/packages` `GET /api/v1/marketplace/packages/:id` `POST /api/v1/marketplace/packages/:id/install` (elevated) |
| **workspaces** | `GET /api/v1/workspaces` `POST /api/v1/workspaces/:id/open` `GET /api/v1/workspaces/current` |
| **events** | `GET /api/v1/events/stream` (SSE) |
| **ai** | `POST /api/v1/ai/converse` `POST /api/v1/ai/invoke` `GET /api/v1/ai/models` `GET /api/v1/ai/providers` `POST /api/v1/ai/embeddings` `GET /api/v1/ai/usage` |

OpenAPI 3.1: `openapi/ortho-v1.yaml`

## Event Stream (SSE)

```bash
curl -N http://localhost:7032/api/v1/events/stream -H "Authorization: Bearer $TOKEN"
# event: proof.verified
# data: {"id":"...","type":"proof.verified","timestamp":"...","source":"ortho32-api","correlation_id":"...","data":{"proofId":"..."}}
```

- Content-Type `text/event-stream`, `Cache-Control: no-cache`, heartbeat comments every 15s.
- Event `event:` line is the typed name; `data:` is always an `Envelope`.
- Typed events: `device.connected` `device.disconnected` `fabric.transaction` `proof.verified` `proof.failed` `build.completed` `agent.started` `trace.completed` `security.prompt`
- Auth: same JWT. On `close` server cleans timers.

JS client:

```js
const es = new EventSource('/api/v1/events/stream', { headers: { Authorization: `Bearer ${t}` } });
es.addEventListener('proof.verified', e => {
  const env = JSON.parse(e.data); // envelope
  console.log(env.type, env.data);
});
```

## Transport modes

Both transports expose identical routes + envelopes.

- **Local IPC** (`src/transport/ipc.ts`) — for co-located desktop (Swift/Win32). Unix socket `/tmp/ortho32-api.sock` (Windows named pipe `\\.\pipe\ortho32-api`). Permission `0700`, newline-delimited JSON envelopes, same JWT. Lowest latency, no TLS, not network-reachable.
- **HTTP/2** (`src/transport/http.ts`) — for remote clients. TLS + ALPN, multiplexed, CORS, `Authorization: Bearer`. Use `HttpClient` helper for typed fetch with correlation.

Select via config: local apps prefer IPC (fall back to `http://localhost:7032`), remote agents use HTTPS.

## Versioning policy

- URL versioned: `/api/v1/*`. Minor additions are non-breaking. Breaking schema change → new major (`/api/v2`) and `apiVersion` bump in `GET /system/version`.
- `VerificationStatus` and `cycles` semantics are frozen; adding a status or changing cycles to float is a major.
- Old majors remain for at least one release. Clients should send `Accept: application/json` and handle unknown `type` gracefully.
- OpenAPI is the contract test — CI fails on drift (`npm run openapi:lint`).

## ORTHO Routing integration

This API is the Service/Intent plane gateway. Desktop routes `ortho://app/ide`, `ortho://trace/cycle/420`, `ortho://proof/rtl_deterministic` resolve to `POST /apps/:id/open`, `GET /traces/:id`, `POST /proofs/verify` etc. Workspaces store routes not UI objects; replay on login reopens via the same typed calls.
