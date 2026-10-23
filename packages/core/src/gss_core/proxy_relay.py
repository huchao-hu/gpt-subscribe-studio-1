"""Process-local TCP tunnels through a loopback HTTP proxy (Clash).

The gateway's protocol and credentials pass through unchanged. Only HTTPS
gateway TLS is terminated here, using its original hostname for verification.
Listeners are immutable so saved order URLs keep their route until shutdown.
"""
from __future__ import annotations

import asyncio
import atexit
import ssl
import threading
from urllib.parse import urlsplit


class RelayManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._loop = None
        self._thread = None
        self._servers = {}
        self._tasks = set()
        self._failures = {}

    def _start(self):
        if self._loop is not None:
            return
        ready = threading.Event()

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            ready.set()
            loop.run_forever()
            loop.close()

        self._thread = threading.Thread(target=run, name="gss-clash-relay", daemon=True)
        self._thread.start()
        ready.wait()

    def endpoint(self, host: str, port: int, scheme: str, upstream: str) -> tuple[str, int]:
        key = (host, port, scheme, upstream)
        with self._lock:
            self._start()
            if key not in self._servers:
                if len(self._servers) >= 128:
                    raise ValueError("代理转发配置过多，请重启后端释放旧连接")
                future = asyncio.run_coroutine_threadsafe(self._listen(key), self._loop)
                try:
                    self._servers[key] = future.result(timeout=5)
                except Exception:
                    future.cancel()
                    raise ValueError("无法启动本机代理转发，请检查后端运行状态") from None
            local_port = self._servers[key].sockets[0].getsockname()[1]
            return ("http" if scheme == "https" else scheme, local_port)

    async def _listen(self, key):
        return await asyncio.start_server(
            lambda reader, writer: self._relay(reader, writer, key), "127.0.0.1", 0,
        )

    async def _connect(self, key):
        host, port, scheme, upstream = key
        clash = urlsplit(upstream)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(clash.hostname, clash.port, limit=8192), 12,
            )
        except (OSError, asyncio.TimeoutError):
            raise ConnectionError("无法连接本机 Clash，请确认软件已启动且 HTTP/Mixed 端口正确") from None
        try:
            target = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
            writer.write(f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode("ascii"))
            await writer.drain()
            try:
                header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 12)
                status = header.split(b"\r\n", 1)[0].split()
                if len(status) < 2 or not status[0].startswith(b"HTTP/") or status[1] != b"200":
                    raise ValueError()
            except (ValueError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, asyncio.TimeoutError):
                raise ConnectionError("Clash 无法建立到供应商网关的连接，请检查节点、规则和网关地址") from None
            if scheme == "https":
                try:
                    context = ssl.create_default_context()
                    # Python 3.10 lacks StreamWriter.start_tls; use its underlying
                    # transport upgrade with the same verified SSLContext and SNI.
                    if hasattr(writer, "start_tls"):
                        await writer.start_tls(context, server_hostname=host, ssl_handshake_timeout=12)
                    else:
                        transport = await asyncio.get_running_loop().start_tls(
                            writer.transport, writer.transport.get_protocol(), context,
                            server_side=False, server_hostname=host, ssl_handshake_timeout=12,
                        )
                        writer._transport = transport
                except (OSError, asyncio.TimeoutError):
                    raise ConnectionError("供应商 HTTPS 代理 TLS 握手或证书校验失败") from None
            return reader, writer
        except BaseException:
            writer.close()
            raise

    async def _relay(self, client_reader, client_writer, key):
        task = asyncio.current_task()
        self._tasks.add(task)
        port = client_writer.get_extra_info("sockname")[1]
        remote_writer = None
        pumps = []
        try:
            try:
                remote_reader, remote_writer = await self._connect(key)
                self._failures.pop(port, None)
            except (OSError, ValueError) as exc:
                # Only our fixed diagnostic strings are exposed; never log requests.
                self._failures[port] = str(exc) if type(exc) is ConnectionError else "代理网关连接失败"
                return

            async def copy(reader, writer):
                while chunk := await asyncio.wait_for(reader.read(65536), 300):
                    writer.write(chunk)
                    await asyncio.wait_for(writer.drain(), 30)
                if writer.can_write_eof():
                    writer.write_eof()

            pumps = [asyncio.create_task(copy(client_reader, remote_writer)),
                     asyncio.create_task(copy(remote_reader, client_writer))]
            # A gateway can finish a response without waiting for client EOF.
            done, _ = await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
            if pumps[0] in done:
                # Client write EOF does not mean it has finished reading.
                pumps[0].result()
                await pumps[1]
        except (OSError, asyncio.TimeoutError):
            pass
        finally:
            for pump in pumps:
                pump.cancel()
            if pumps:
                await asyncio.gather(*pumps, return_exceptions=True)
            for writer in (client_writer, remote_writer):
                if writer is not None:
                    writer.close()
                    try:
                        await asyncio.wait_for(writer.wait_closed(), 2)
                    except (OSError, asyncio.TimeoutError):
                        pass
            self._tasks.discard(task)

    def failure_for(self, port: int) -> str | None:
        return self._failures.get(port)

    async def _shutdown(self):
        for server in self._servers.values():
            server.close()
            await server.wait_closed()
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def close(self):
        with self._lock:
            if self._loop is None:
                return
            try:
                asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop).result(timeout=8)
            finally:
                self._loop.call_soon_threadsafe(self._loop.stop)
                self._thread.join(timeout=3)
                self._loop = self._thread = None
                self._servers.clear()
                self._failures.clear()


relay_manager = RelayManager()
atexit.register(relay_manager.close)
