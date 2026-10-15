"""Short-lived, in-memory browser sessions. TACTIC tickets never leave the server."""
from dataclasses import dataclass, field
import hashlib
import secrets
import threading
import time
from .contracts import ApiError


@dataclass
class Session:
    login: str
    ticket: str
    site: str
    csrf: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    expires: float = 0
    user: dict = field(default_factory=dict)


class SessionStore:
    def __init__(self, ttl=28800, max_sessions=1000):
        self.ttl, self.max_sessions = ttl, max_sessions
        self._sessions, self._attempts = {}, {}
        self._lock = threading.RLock()

    def _key(self, token):
        return hashlib.sha256((token or "").encode()).hexdigest()

    def create(self, login, ticket, site="", user=None):
        token = secrets.token_urlsafe(48)
        session = Session(login, ticket, site, expires=time.time() + self.ttl, user=user or {})
        with self._lock:
            self._sessions = {k: v for k, v in self._sessions.items() if v.expires > time.time()}
            if len(self._sessions) >= self.max_sessions:
                raise ApiError(503, "session_capacity", "Достигнут лимит сессий")
            self._sessions[self._key(token)] = session
        return token, session

    def get(self, token):
        with self._lock:
            session = self._sessions.get(self._key(token))
            if not session or session.expires <= time.time():
                self._sessions.pop(self._key(token), None)
                raise ApiError(401, "session_expired", "Войдите в систему")
            return session

    def delete(self, token):
        with self._lock:
            self._sessions.pop(self._key(token), None)

    def check_csrf(self, session, value):
        if not isinstance(value, str) or not secrets.compare_digest(session.csrf, value):
            raise ApiError(403, "csrf", "Недействительный CSRF-токен. Обновите страницу")

    def login_attempt(self, address):
        now = time.time()
        with self._lock:
            self._attempts = {k: v for k, v in self._attempts.items() if v[-1] > now - 60}
            attempts = [t for t in self._attempts.get(address, []) if t > now - 60]
            if len(attempts) >= 10:
                raise ApiError(429, "rate_limit", "Слишком много попыток входа. Повторите через минуту")
            attempts.append(now)
            self._attempts[address] = attempts
