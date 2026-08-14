import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models import VerificationStatus, EventEnvelope
from app.ipc import IPCUnavailable
from app.auth import create_token


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _envelope_fields(body: dict):
    assert "id" in body
    assert "type" in body
    assert "timestamp" in body
    assert "source" in body
    assert "correlation_id" in body
    assert "data" in body


@pytest.mark.asyncio
async def test_tensor_cycles_is_int():
    mock_resp = EventEnvelope(
        type="TENSOR_SUBMIT_RESULT",
        source="ortho-host",
        data={"id": "job-123", "cycles": 42, "status": "queued"},
    )
    with patch("app.routes.tensor.get_host_connection") as mock_get:
        mock_host = AsyncMock()
        mock_host.send.return_value = mock_resp
        mock_get.return_value = mock_host

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post("/api/v1/tensor/jobs", json={"cycles": 42, "payload": {}})
            assert res.status_code == 200
            body = res.json()
            _envelope_fields(body)
            # cycles field is int ALWAYS
            assert isinstance(body["data"]["cycles"], int)
            assert not isinstance(body["data"]["cycles"], bool)
            assert body["data"]["cycles"] == 42
            # ensure not float
            assert isinstance(body["data"]["cycles"], int) and not isinstance(body["data"]["cycles"], float)


@pytest.mark.asyncio
async def test_verification_status_enum():
    mock_resp = EventEnvelope(
        type="PROOF_VERIFY_RESULT",
        source="ortho-host",
        data={"id": "proof-1", "status": "VERIFIED", "dependencies": []},
    )
    with patch("app.routes.proofs.get_host_connection") as mock_get:
        mock_host = AsyncMock()
        mock_host.send.return_value = mock_resp
        mock_get.return_value = mock_host

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post("/api/v1/proofs/verify", json={"artifact_id": "a1"})
            assert res.status_code == 200
            body = res.json()
            _envelope_fields(body)
            assert body["data"]["status"] in [e.value for e in VerificationStatus]
            # exactly 7 values
            assert len(list(VerificationStatus)) == 7


@pytest.mark.asyncio
async def test_hardware_reset_requires_scope():
    # token without elevated scope
    token_no_scope = create_token("user1", ["device.read"])
    token_with_scope = create_token("admin", ["device.read", "hardware.reset"])

    # mock host for success case
    mock_resp = EventEnvelope(
        type="DEVICE_RESET_RESULT", source="ortho-host", data={"id": "dev1", "status": "reset"}
    )
    with patch("app.routes.devices.get_host_connection") as mock_get:
        mock_host = AsyncMock()
        mock_host.send.return_value = mock_resp
        mock_get.return_value = mock_host

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # without elevated scope -> 403
            res = await ac.post(
                "/api/v1/devices/x/reset", headers={"Authorization": f"Bearer {token_no_scope}"}
            )
            assert res.status_code == 403

            # without token -> 401
            res2 = await ac.post("/api/v1/devices/x/reset")
            assert res2.status_code == 401

            # with elevated scope -> 200
            res3 = await ac.post(
                "/api/v1/devices/x/reset", headers={"Authorization": f"Bearer {token_with_scope}"}
            )
            assert res3.status_code == 200
            _envelope_fields(res3.json())


@pytest.mark.asyncio
async def test_events_stream_sse():
    # mock subscribe generator
    async def fake_subscribe(event_type: str):
        yield EventEnvelope(type="device.connected", source="ortho-host", data={"id": "d1"})
        yield EventEnvelope(type="fabric.transaction", source="ortho-host", data={})

    with patch("app.routes.events.get_host_connection") as mock_get:
        mock_host = MagicMock()
        mock_host.subscribe = fake_subscribe
        mock_get.return_value = mock_host

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # use stream request
            async with ac.stream("GET", "/api/v1/events/stream") as res:
                assert res.status_code == 200
                assert "text/event-stream" in res.headers.get("content-type", "")
                # read first chunk
                content = ""
                async for chunk in res.aiter_text():
                    content += chunk
                    if "data:" in content:
                        break
                assert "data:" in content
                assert "event:" in content


@pytest.mark.asyncio
async def test_envelope_fields():
    mock_resp = EventEnvelope(
        type="STATUS_RESULT", source="ortho-host", data={"ok": True, "uptime": 123}
    )
    with patch("app.routes.system.get_host_connection") as mock_get:
        mock_host = AsyncMock()
        mock_host.send.return_value = mock_resp
        mock_get.return_value = mock_host

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/system/status")
            assert res.status_code == 200
            body = res.json()
            _envelope_fields(body)
            # all responses have id type timestamp source correlation_id data
            assert isinstance(body["id"], str)
            assert isinstance(body["type"], str)
            assert isinstance(body["timestamp"], int)
            assert isinstance(body["source"], str)
            assert isinstance(body["correlation_id"], str)
            assert "data" in body


@pytest.mark.asyncio
async def test_ipc_unavailable():
    with patch("app.routes.system.get_host_connection") as mock_get:
        mock_host = AsyncMock()
        mock_host.send.side_effect = IPCUnavailable("pipe not found")
        mock_get.return_value = mock_host

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/system/status")
            assert res.status_code == 503
            # never return fake data with 200
            assert res.status_code != 200
            body = res.json()
            assert "detail" in body
            assert "Host unavailable" in body["detail"]

    # also tensor should 503
    with patch("app.routes.tensor.get_host_connection") as mock_get:
        mock_host = AsyncMock()
        mock_host.send.side_effect = IPCUnavailable("host down")
        mock_get.return_value = mock_host

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post("/api/v1/tensor/jobs", json={"cycles": 10, "payload": {}})
            assert res.status_code == 503
