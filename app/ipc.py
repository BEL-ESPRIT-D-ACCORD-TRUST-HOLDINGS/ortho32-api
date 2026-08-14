import asyncio
import json
import socket
import os
from typing import AsyncGenerator, Optional

from app.models import MessageEnvelope, EventEnvelope

PIPE_NAME = r"\\.\pipe\ortho-host"
FALLBACK_HOST = "127.0.0.1"
FALLBACK_PORT = 7032

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
            self._socket_reader, self._socket_writer = await asyncio.wait_for(
                asyncio.open_connection(FALLBACK_HOST, FALLBACK_PORT), timeout=2.0
            )
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

            payload = envelope.model_dump_json() + "\n"
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
                obj = json.loads(raw.decode("utf-8").strip())
                return EventEnvelope(**obj)
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
                    obj = json.loads(raw.decode("utf-8").strip())
                    env = EventEnvelope(**obj)
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
                    obj = json.loads(line)
                    env = EventEnvelope(**obj)
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
