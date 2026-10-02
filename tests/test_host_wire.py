"""Host IPC wire compatibility: field mapping and Unix-socket / TCP transport against a fake ORTHOHost."""
import asyncio
import json

import pytest

from app.ipc import HostConnection, IPCUnavailable, from_host_wire, to_host_wire
from app.models import MessageEnvelope


def _host_reply(request: dict) -> dict:
    # Shape and casing taken from ortho32-host IPC/EventEnvelope.cs (System.Text.Json defaults,
    # DateTime with 7 fractional digits).
    return {
        "EventId": "evt-1",
        "CorrelationId": request["CorrelationId"],
        "EventType": "RESULT_" + request["Action"],
        "Source": "host",
        "Payload": {"echo": request["Payload"]},
        "Timestamp": "2026-10-02T22:17:40.1234567Z",
    }


async def _serve(reader, writer, seen):
    while line := await reader.readline():
        req = json.loads(line)
        seen.append(req)
        writer.write((json.dumps(_host_reply(req)) + "\n").encode())
        await writer.drain()
    writer.close()


def test_to_host_wire_maps_fields():
    env = MessageEnvelope(id="r1", type="TENSOR_SUBMIT", correlation_id="c1", data={"n": 3}, timestamp=1_700_000_000_000)
    wire = to_host_wire(env)
    assert wire["RequestId"] == "r1"
    assert wire["CorrelationId"] == "c1"
    assert wire["Action"] == "TENSOR_SUBMIT"
    assert wire["Payload"] == {"n": 3}
    assert wire["Source"] == "ortho32-api"
    assert wire["Timestamp"].startswith("2023-11-14T22:13:20")  # ISO-8601, not an integer
    assert set(wire) == {"RequestId", "CorrelationId", "Source", "Action", "Payload", "Timestamp"}


def test_from_host_wire_maps_fields_and_parses_7_digit_fraction():
    ev = from_host_wire(_host_reply({"CorrelationId": "c1", "Action": "X", "Payload": {"a": 1}}))
    assert (ev.id, ev.type, ev.source, ev.correlation_id) == ("evt-1", "RESULT_X", "host", "c1")
    assert ev.data == {"echo": {"a": 1}}
    assert ev.timestamp == 1_790_979_460_123  # 2026-10-02T22:17:40.123Z in ms


async def test_send_over_unix_socket(tmp_path, monkeypatch):
    sock = str(tmp_path / "CoreFxPipe_ortho-host")
    seen = []
    server = await asyncio.start_unix_server(lambda r, w: _serve(r, w, seen), path=sock)
    monkeypatch.setenv("ORTHO_HOST_SOCKET", sock)
    monkeypatch.delenv("ORTHO_HOST_TCP", raising=False)
    conn = HostConnection()
    try:
        ev = await conn.send(MessageEnvelope(type="PING", data={"k": "v"}))
    finally:
        await conn.close()
        server.close()
        await server.wait_closed()
    assert ev.type == "RESULT_PING"
    assert ev.data == {"echo": {"k": "v"}}
    assert seen[0]["Action"] == "PING" and "type" not in seen[0] and "data" not in seen[0]


async def test_send_over_tcp_override(monkeypatch):
    seen = []
    server = await asyncio.start_server(lambda r, w: _serve(r, w, seen), "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    monkeypatch.setenv("ORTHO_HOST_TCP", f"127.0.0.1:{port}")
    conn = HostConnection()
    try:
        ev = await conn.send(MessageEnvelope(type="PING", data={}))
    finally:
        await conn.close()
        server.close()
        await server.wait_closed()
    assert ev.type == "RESULT_PING"


async def test_missing_socket_raises_ipc_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("ORTHO_HOST_SOCKET", str(tmp_path / "absent"))
    monkeypatch.delenv("ORTHO_HOST_TCP", raising=False)
    with pytest.raises(IPCUnavailable):
        await HostConnection().send(MessageEnvelope(type="PING", data={}))
