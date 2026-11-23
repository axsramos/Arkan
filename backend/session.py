"""Sessão local efêmera, sem PIN em contratos HTTP."""

import secrets
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any


SESSION_COOKIE = "arkan_local_session"
IDLE_TIMEOUT_SECONDS = 2 * 60 * 60


class SessionError(RuntimeError):
    """Sessão local ausente, inválida ou expirada."""


@dataclass
class LocalSession:
    """Material desbloqueado mantido somente durante a sessão do processo."""

    data_key: bytes
    identity: dict[str, Any]
    last_activity: float


class LocalSessionStore:
    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._sessions: dict[str, LocalSession] = {}
        self._lock = RLock()

    def create(self, data_key: bytes, identity: dict[str, Any]) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions.clear()
            self._sessions[token] = LocalSession(data_key=data_key, identity=identity, last_activity=self._clock())
        return token

    def get(self, token: str | None, renew: bool = False) -> LocalSession:
        if not token:
            raise SessionError("Sessão local bloqueada.")
        with self._lock:
            session = self._sessions.get(token)
            if session is None or self._clock() - session.last_activity >= IDLE_TIMEOUT_SECONDS:
                self._sessions.pop(token, None)
                raise SessionError("Sessão local bloqueada.")
            if renew:
                session.last_activity = self._clock()
            return session

    def destroy(self, token: str | None = None) -> None:
        with self._lock:
            if token:
                self._sessions.pop(token, None)
            else:
                self._sessions.clear()


sessions = LocalSessionStore()
