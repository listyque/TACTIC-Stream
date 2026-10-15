"""Private local SQLite transport sessions shared by a single native cluster.

Not a replacement for TACTIC tickets or its application database. A session only
holds a reference to the original ticket, which XmlRpcInit validates per request.
The supervisor creates a fresh store per cluster run. Never use this on NFS/SMB.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import secrets
import sqlite3
import time
from .session import Session, SessionStore
from .contracts import ApiError


class SharedSessionStore(SessionStore):
    def __init__(self, path, ttl=28800, max_sessions=1000):
        self.path = Path(path).resolve()
        self.ttl, self.max_sessions = ttl, max_sessions
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS sessions (
                    digest TEXT PRIMARY KEY, login TEXT NOT NULL, ticket TEXT NOT NULL,
                    site TEXT NOT NULL, csrf TEXT NOT NULL, expires REAL NOT NULL,
                    user_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS attempts (address TEXT NOT NULL, at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS attempts_at ON attempts(at);
                CREATE INDEX IF NOT EXISTS attempts_address ON attempts(address);
            ''')
        # On Windows inherit the private data-dir ACL; chmod is not an ACL API.
        self.path.chmod(0o600)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(str(self.path), timeout=15)
        db.execute('PRAGMA busy_timeout=15000')
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, login, ticket, site='', user=None):
        token = secrets.token_urlsafe(48)
        session = Session(login, ticket, site, expires=time.time()+self.ttl, user=user or {})
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM sessions WHERE expires <= ?', (time.time(),))
            if db.execute('SELECT count(*) FROM sessions').fetchone()[0] >= self.max_sessions:
                raise ApiError(503, 'session_capacity', 'Достигнут лимит сессий')
            db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?)',
                       (self._key(token), login, ticket, site, session.csrf, session.expires,
                        json.dumps(session.user, ensure_ascii=False, allow_nan=False)))
        return token, session

    def get(self, token):
        with self._connect() as db:
            row = db.execute('SELECT login,ticket,site,csrf,expires,user_json FROM sessions WHERE digest=?',
                             (self._key(token),)).fetchone()
        if not row or row[4] <= time.time():
            raise ApiError(401, 'session_expired', 'Войдите в систему')
        return Session(row[0], row[1], row[2], csrf=row[3], expires=row[4], user=json.loads(row[5]))

    def delete(self, token):
        with self._connect() as db:
            db.execute('DELETE FROM sessions WHERE digest=?', (self._key(token),))

    def login_attempt(self, address):
        now = time.time()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM attempts WHERE at <= ?', (now-60,))
            if db.execute('SELECT count(*) FROM attempts WHERE address=?', (address,)).fetchone()[0] >= 10:
                raise ApiError(429, 'rate_limit', 'Слишком много попыток входа. Повторите через минуту')
            db.execute('INSERT INTO attempts VALUES (?,?)', (address, now))
