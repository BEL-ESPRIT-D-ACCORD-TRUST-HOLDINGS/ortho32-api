import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional

from app.models import MessageEnvelope, EventEnvelope

PIPE_NAME = r"\\.\pipe\ortho-host"
# Linux/macOS: .NET maps NamedPipeServerStream("ortho-host") to this Unix socket.
DEFAULT_HOST_SOCKET = "/tmp/CoreFxPipe_ortho-host"
# Legacy fallback, used only on platforms without Unix sockets (Windows without pywin32).
FALLBACK_HOST = "127.0.0.1"
FALLBACK_PORT = 7032


def _host_socket_path() -> str:
    return os.environ.get("ORTHO_HOST_SOCKET", DEFAULT_HOST_SOCKET)


def _host_tcp() -> str:
    """Optional "host:port" override (ORTHO_HOST_TCP). Takes priority over the Unix socket."""
    return os.environ.get("ORTHO_HOST_TCP", "")


_FRACTION = re.compile(r"(\.\d{6})\d+")


def to_host_wire(env: MessageEnvelope) -> Dict[str, Any]:
    """API envelope -> ORTHOHost MessageEnvelope (PascalCase, ISO-8601 Timestamp)."""
    ts = datetime.fromtimestamp(env.timestamp / 1000.0, tz=timezone.utc).isoformat()
    return {
        "RequestId": env.id,
        "CorrelationId": env.correlation_id,
        "Source": env.source,
        "Action": env.type,
        "Payload": env.data if env.data is not None else {},
        "Timestamp": ts,
    }


def from_host_wire(obj: Dict[str, Any]) -> EventEnvelope:
    """ORTHOHost EventEnvelope -> API envelope. .NET emits up to 7 fractional digits; trim to 6."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    ts_ms = now_ms
    raw_ts = obj.get("Timestamp")
    if isinstance(raw_ts, str):
        try:
            ts_ms = int(
                datetime.fromisoformat(_FRACTION.sub(r"\1", raw_ts).replace("Z", "+00:00")).timestamp()
                * 1000
            )
        except ValueError:
            pass
    return EventEnvelope(
        id=obj.get("EventId") or str(uuid.uuid4()),
        type=obj.get("EventType", ""),
        timestamp=ts_ms,
        source=obj.get("Source", ""),
        correlation_id=obj.get("CorrelationId", ""),
        data=obj.get("Payload", {}),
    )


def _parse_event(raw: bytes) -> EventEnvelope:
    return from_host_wire(json.loads(raw.decode("utf-8").strip()))

try:
    import win32pipe  # type: ignore
    import win32file  # type: ignore
    import pywintypes  # type: ignore

    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False


class IPCUnavailable(Exception):
    pass


class HostConnection:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._connected = False
        self._pipe_handle = None
        self._socket_reader: Optional[asyncio.StreamReader] = None
        self._socket_writer: Optional[asyncio.StreamWriter] = None
        self._use_pipe = HAS_PYWIN32

    async def connect(self):
        async with self._lock:
            if self._connected:
                return
            if self._use_pipe and HAS_PYWIN32:
                try:
                    await self._connect_pipe()
                    self._connected = True
                    return
                except Exception:
                    # fall back to socket
                    self._use_pipe = False
            try:
                await self._connect_socket()
                self._connected = True
            except Exception as e:
                self._connected = False
                raise IPCUnavailable(f"Host unavailable: {e}") from e

    async def _connect_pipe(self):
        # win32pipe is synchronous; run in thread
        def _open():
            handle = win32file.CreateFile(
                PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None,
            )
            win32pipe.SetNamedPipeHandleState(
                handle, win32pipe.PIPE_READMODE_MESSAGE, None, None
            )
            return handle

        self._pipe_handle = await asyncio.to_thread(_open)

    async def _connect_socket(self):
        try:
            tcp = _host_tcp()
            if tcp:
                host, _, port = tcp.rpartition(":")
                opener = asyncio.open_connection(host, int(port))
            elif os.name != "nt":
                opener = asyncio.open_unix_connection(_host_socket_path())
            else:
                opener = asyncio.open_connection(FALLBACK_HOST, FALLBACK_PORT)
            self._socket_reader, self._socket_writer = await asyncio.wait_for(opener, timeout=2.0)
        except Exception as e:
            raise IPCUnavailable(f"Socket connect failed: {e}") from e

    async def close(self):
        async with self._lock:
            await self._close_internal()

    async def _close_internal(self):
        self._connected = False
        if self._pipe_handle is not None:
            try:
                await asyncio.to_thread(win32file.CloseHandle, self._pipe_handle)
            except Exception:
                pass
            self._pipe_handle = None
        if self._socket_writer is not None:
            try:
                self._socket_writer.close()
                await self._socket_writer.wait_closed()
            except Exception:
                pass
            self._socket_reader = None
            self._socket_writer = None

    async def _ensure_connected(self):
        if not self._connected:
            await self.connect()

    async def send(self, envelope: MessageEnvelope) -> EventEnvelope:
        async with self._lock:
            # ensure connection
            if not self._connected:
                try:
                    if self._use_pipe and HAS_PYWIN32:
                        await self._connect_pipe()
                        self._connected = True
                    else:
                        await self._connect_socket()
                        self._connected = True
                except Exception as e:
                    self._connected = False
                    raise IPCUnavailable(f"Host unavailable: {e}") from e

            payload = json.dumps(to_host_wire(envelope)) + "\n"
            data = payload.encode("utf-8")

            try:
                if self._use_pipe and self._pipe_handle is not None:
                    raw = await self._pipe_transaction(data)
                else:
                    if self._socket_writer is None or self._socket_reader is None:
                        raise IPCUnavailable("No socket connection")
                    self._socket_writer.write(data)
                    await self._socket_writer.drain()
                    raw = await asyncio.wait_for(
                        self._socket_reader.readline(), timeout=10.0
                    )
                    if not raw:
                        raise IPCUnavailable("Host closed connection")
            except IPCUnavailable:
                await self._close_internal()
                raise
            except Exception as e:
                await self._close_internal()
                raise IPCUnavailable(f"IPC error: {e}") from e

            try:
                return _parse_event(raw)
            except Exception as e:
                raise IPCUnavailable(f"Invalid response: {e}") from e

    async def _pipe_transaction(self, data: bytes) -> bytes:
        def _transact():
            win32file.WriteFile(self._pipe_handle, data)
            # Read response - message mode
            result, resp = win32file.ReadFile(self._pipe_handle, 64 * 1024)
            return resp

        return await asyncio.to_thread(_transact)

    async def subscribe(self, event_type: str) -> AsyncGenerator[EventEnvelope, None]:
        # Long-poll push events from host
        # Sends a SUBSCRIBE envelope and yields events as they arrive
        subscribe_envelope = MessageEnvelope(
            type="SUBSCRIBE", source="ortho32-api", data={"event_type": event_type}
        )
        # initial subscribe
        try:
            await self.send(subscribe_envelope)
        except IPCUnavailable:
            # if host unavailable, just raise so caller can handle 503
            raise

        # Then continuously poll / push - for socket fallback we loop reading lines
        # For pipe, we repeatedly read
        while True:
            try:
                if self._use_pipe and self._pipe_handle is not None:

                    def _read_pipe():
                        _, data = win32file.ReadFile(self._pipe_handle, 64 * 1024)
                        return data

                    raw = await asyncio.to_thread(_read_pipe)
                    if not raw:
                        await asyncio.sleep(0.5)
                        continue
                    env = _parse_event(raw)
                    if event_type == "*" or env.type == event_type:
                        yield env
                else:
                    if self._socket_reader is None:
                        await self._ensure_connected()
                        if self._socket_reader is None:
                            raise IPCUnavailable("No connection for subscribe")
                    raw = await asyncio.wait_for(
                        self._socket_reader.readline(), timeout=30.0
                    )
                    if not raw:
                        # reconnect and resubscribe
                        await self._close_internal()
                        await self._ensure_connected()
                        await self.send(subscribe_envelope)
                        continue
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    env = _parse_event(line.encode("utf-8"))
                    if event_type == "*" or env.type == event_type:
                        yield env
            except asyncio.TimeoutError:
                # heartbeat keepalive
                try:
                    ping = MessageEnvelope(type="PING", source="ortho32-api", data={})
                    await self.send(ping)
                except Exception:
                    await self._close_internal()
                    await asyncio.sleep(1.0)
                continue
            except IPCUnavailable:
                await self._close_internal()
                # reconnect without restarting API process
                await asyncio.sleep(1.0)
                try:
                    await self._ensure_connected()
                    await self.send(subscribe_envelope)
                except Exception:
                    await asyncio.sleep(1.0)
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.5)
                continue

    async def reconnect(self):
        async with self._lock:
            await self._close_internal()
            await self.connect()


_singleton: Optional[HostConnection] = None


def get_host_connection() -> HostConnection:
    global _singleton
    if _singleton is None:
        _singleton = HostConnection()
    return _singleton
