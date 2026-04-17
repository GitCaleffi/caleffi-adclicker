"""Local HTTP proxy tunnel for authenticated upstream proxies.

Chrome connects to 127.0.0.1:LOCAL_PORT (no auth required).
This tunnel adds Proxy-Authorization and forwards all traffic
to the upstream proxy (e.g. IPRoyal geo.iproyal.com:12321).

Usage in webdriver.py:
    from local_proxy import start_local_proxy
    local_port = start_local_proxy(host, port, username, password)
    chrome_options.add_argument(f"--proxy-server=http://127.0.0.1:{local_port}")
"""

import base64
import select
import socket
import threading

from logger import logger


def _forward(src: socket.socket, dst: socket.socket, stop_event: threading.Event) -> None:
    """Forward data from src to dst until connection closes or stop_event is set."""
    try:
        while not stop_event.is_set():
            ready, _, err = select.select([src], [], [src], 1.0)
            if err:
                break
            if ready:
                data = src.recv(65536)
                if not data:
                    break
                dst.sendall(data)
    except (OSError, BrokenPipeError, ConnectionResetError):
        pass
    finally:
        stop_event.set()


def _handle_client(
    client_sock: socket.socket,
    upstream_host: str,
    upstream_port: int,
    auth_header: str,
) -> None:
    """Handle a single browser connection."""
    upstream_sock = None
    try:
        # Read request headers from browser
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = client_sock.recv(4096)
            if not chunk:
                return
            data += chunk

        first_line = data.split(b"\r\n")[0].decode("utf-8", errors="replace")
        parts = first_line.split(" ")
        if len(parts) < 2:
            return

        method = parts[0]

        # Connect to upstream proxy
        upstream_sock = socket.create_connection((upstream_host, upstream_port), timeout=20)

        if method == "CONNECT":
            # HTTPS tunnel: forward CONNECT with auth to upstream
            target = parts[1]
            connect_req = (
                f"CONNECT {target} HTTP/1.1\r\n"
                f"Host: {target}\r\n"
                f"Proxy-Authorization: Basic {auth_header}\r\n"
                f"Proxy-Connection: keep-alive\r\n"
                f"\r\n"
            )
            upstream_sock.sendall(connect_req.encode())

            # Read upstream response
            resp = b""
            while b"\r\n\r\n" not in resp:
                chunk = upstream_sock.recv(4096)
                if not chunk:
                    return
                resp += chunk

            if b"200" not in resp.split(b"\r\n")[0]:
                logger.debug(f"[LocalProxy] CONNECT to {target} failed: {resp[:80]}")
                return

            # Tell browser: tunnel is ready
            client_sock.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")

            # Bidirectional relay
            stop = threading.Event()
            t1 = threading.Thread(target=_forward, args=(client_sock, upstream_sock, stop), daemon=True)
            t2 = threading.Thread(target=_forward, args=(upstream_sock, client_sock, stop), daemon=True)
            t1.start()
            t2.start()
            stop.wait()

        else:
            # Plain HTTP: inject Proxy-Authorization header
            lines = data.split(b"\r\n")
            new_lines = []
            auth_injected = False

            for line in lines:
                if line.lower().startswith(b"proxy-authorization:"):
                    new_lines.append(f"Proxy-Authorization: Basic {auth_header}".encode())
                    auth_injected = True
                else:
                    new_lines.append(line)

            if not auth_injected:
                try:
                    empty_idx = new_lines.index(b"")
                    new_lines.insert(empty_idx, f"Proxy-Authorization: Basic {auth_header}".encode())
                except ValueError:
                    new_lines.append(f"Proxy-Authorization: Basic {auth_header}".encode())
                    new_lines.append(b"")

            upstream_sock.sendall(b"\r\n".join(new_lines))

            # Forward response back to browser
            while True:
                chunk = upstream_sock.recv(65536)
                if not chunk:
                    break
                client_sock.sendall(chunk)

    except (OSError, ConnectionResetError, BrokenPipeError, TimeoutError) as e:
        logger.debug(f"[LocalProxy] Connection error: {e}")
    except Exception as e:
        logger.debug(f"[LocalProxy] Unexpected error: {e}")
    finally:
        for s in (upstream_sock, client_sock):
            if s:
                try:
                    s.close()
                except Exception:
                    pass


def start_local_proxy(
    upstream_host: str,
    upstream_port: int,
    username: str,
    password: str,
) -> int:
    """Start a local HTTP proxy tunnel on a random free port.

    :param upstream_host: Upstream proxy host (e.g. geo.iproyal.com)
    :param upstream_port: Upstream proxy port (e.g. 12321)
    :param username: Proxy username
    :param password: Proxy password
    :returns: Local port number Chrome should connect to
    """
    auth_header = base64.b64encode(f"{username}:{password}".encode()).decode()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))  # OS assigns a free port
    local_port = server_sock.getsockname()[1]
    server_sock.listen(50)

    logger.info(f"[LocalProxy] Tunnel started: 127.0.0.1:{local_port} → {upstream_host}:{upstream_port}")

    def accept_loop() -> None:
        while True:
            try:
                client_sock, _ = server_sock.accept()
                threading.Thread(
                    target=_handle_client,
                    args=(client_sock, upstream_host, upstream_port, auth_header),
                    daemon=True,
                ).start()
            except OSError:
                break

    threading.Thread(target=accept_loop, daemon=True).start()
    return local_port
