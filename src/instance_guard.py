"""Single-instance guard with acknowledged Qt local-socket IPC.

Windows uses a named mutex to reserve the instance atomically. Qt's local
socket channel asks the active instance to raise its window. The sender does
not claim success until the running process acknowledges the request.

The IPC sender must not run synchronously on the same thread that owns the
server's Qt event loop: the listener needs that loop to process incoming data.
"""
from __future__ import annotations

import ctypes
import getpass
import hashlib
import logging
import os
import sys
import time

from PyQt6.QtCore import QIODevice
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


log = logging.getLogger(__name__)
ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = r"Local\Rival110LiteControl_SingleInstance"


def server_name() -> str:
    # Separate each user's pipes without exposing their account names.
    identity = f'{getpass.getuser()}:{os.environ.get("USERDOMAIN", "")}:{os.environ.get("SESSIONNAME", "")}'
    token = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]
    return f'Rival110LiteControl_{token}'


def notify_existing(*, show: bool = True, timeout_ms: int = 1200,
                    name: str | None = None, attempts: int = 4) -> bool:
    """Send SHOW or PING to an already-running instance, waiting for ACK.

    Several attempts cover the window between mutex acquisition and the
    primary process beginning its Qt event loop. Returns False when there is
    no positive confirmation; callers should not pretend the UI was opened.
    """
    endpoint = name or server_name()
    payload = b'SHOW\n' if show else b'PING\n'
    for index in range(max(1, attempts)):
        sock = QLocalSocket()
        try:
            sock.connectToServer(endpoint, QIODevice.OpenModeFlag.ReadWrite)
            if not sock.waitForConnected(timeout_ms):
                continue
            if sock.write(payload) != len(payload):
                continue
            # Queued bytes can disappear quickly after flush() on Windows.
            sock.flush()
            if sock.bytesToWrite() and not sock.waitForBytesWritten(timeout_ms):
                continue

            answer = bytearray(bytes(sock.readAll()))
            until = time.monotonic() + timeout_ms / 1000.0
            while b'\n' not in answer:
                remaining = int((until - time.monotonic()) * 1000)
                if remaining <= 0 or not sock.waitForReadyRead(remaining):
                    break
                answer.extend(bytes(sock.readAll()))
            if answer.split(b'\n', 1)[0].strip() == b'OK':
                sock.disconnectFromServer()
                return True
        finally:
            sock.abort()
        if index + 1 < attempts:
            time.sleep(0.12)
    return False


class SingleInstanceGuard:
    def __init__(self, name: str | None = None):
        self._name = name or server_name()
        self._mutex_name = MUTEX_NAME if name is None else 'Local\\' + name
        self._kernel32 = None
        self._mutex = None
        self._server = None
        self._open_callback = None
        self._connections = set()
        self._buffers = {}

    def acquire(self) -> bool:
        if sys.platform == 'win32':
            self._kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            self._kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p)
            self._kernel32.CreateMutexW.restype = ctypes.c_void_p
            self._kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
            self._kernel32.CloseHandle.restype = ctypes.c_int
            handle = self._kernel32.CreateMutexW(None, 0, self._mutex_name)
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
                self._kernel32.CloseHandle(handle)
                return False
            self._mutex = handle

        self._server = QLocalServer()
        if not self._server.listen(self._name):
            # On Unix, QLocalServer can leave behind a stale filesystem socket.
            # Do not remove an endpoint that a live server acknowledges.
            if sys.platform != 'win32' and notify_existing(show=False, name=self._name):
                self.close()
                return False
            QLocalServer.removeServer(self._name)
            if not self._server.listen(self._name):
                message = self._server.errorString()
                self.close()
                raise RuntimeError(f'Could not open the single-instance IPC endpoint: {message}')
        self._server.newConnection.connect(self._accept_connections)
        return True

    def on_open(self, callback):
        self._open_callback = callback

    def _accept_connections(self):
        while self._server and self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            if sock is None:
                break
            self._connections.add(sock)
            self._buffers[sock] = b''
            sock.readyRead.connect(lambda s=sock: self._read_request(s))
            sock.disconnected.connect(lambda s=sock: self._finish_request(s))
            self._read_request(sock)

    def _read_request(self, sock):
        if sock not in self._connections:
            return
        buffer = self._buffers.get(sock, b'') + bytes(sock.readAll())
        while b'\n' in buffer:
            message, buffer = buffer.split(b'\n', 1)
            command = message.strip().upper()
            if command == b'SHOW' and self._open_callback:
                try:
                    self._open_callback()
                except Exception:
                    log.exception('Could not raise existing Rival 110 window')
                    sock.write(b'ERROR\n')
                    sock.flush()
                    continue
            elif command != b'PING':
                sock.write(b'ERROR\n')
                sock.flush()
                continue
            # The client waits for OK before it disconnects. This avoids
            # racing a disconnected sender and losing an unprocessed request.
            sock.write(b'OK\n')
            sock.flush()
        self._buffers[sock] = buffer

    def _finish_request(self, sock):
        self._read_request(sock)
        self._connections.discard(sock)
        self._buffers.pop(sock, None)
        sock.deleteLater()

    def close(self):
        if self._server is not None:
            self._server.close()
            self._server.deleteLater()
            self._server = None
        for sock in tuple(self._connections):
            sock.abort()
            sock.deleteLater()
        self._connections.clear()
        self._buffers.clear()
        if self._mutex:
            self._kernel32.CloseHandle(self._mutex)
            self._mutex = None
