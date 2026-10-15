"""Finite application API mounted in TACTIC; tests inject a separate fixture backend."""
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
import hashlib
import json
import xml.etree.ElementTree as ET
import logging
import re
import secrets
import threading
import time

from .contracts import ApiError, clean_query, clean_values, fail, json_safe, project_code, search_type, text, view_name
from . import action_log
from .session import SessionStore
from .version import BUILD_VERSION
from .file_payload import FilePayload
from .csv_service import BytesPayload

LOG = logging.getLogger("tactic.vue_ui")
COOKIE = "tactic_vue_session"
MAX_JSON = 1024 * 1024
MAX_UPLOAD = 16 * 1024 * 1024


@dataclass
class Request:
    method: str
    path: str
    query: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    address: str = "127.0.0.1"
    secure: bool = False


@dataclass
class Response:
    status: int
    data: object
    headers: dict = field(default_factory=dict)


class Api:
    def __init__(self, backend, sessions=None):
        self.backend, self.sessions = backend, sessions or SessionStore()
        self.lock = threading.RLock()
        self.idempotent = {}
        self._event_limits = {}

    def handle(self, request):
        request.headers = {k.lower(): v for k, v in request.headers.items()}
        request.method = request.method.upper()
        request.path = request.path.rstrip("/") or "/"
        ref = secrets.token_hex(6)
        trace = action_log.RequestTrace(request, ref).begin()
        failure = None
        try:
            response = self.dispatch(request)
        except ApiError as exc:
            failure = exc.code
            response = Response(exc.status, {"error": {"code": exc.code, "message": exc.message, "details": exc.details, "request_id": ref}})
        except Exception as exc:
            failure = type(exc).__name__
            trace.exception(exc)
            # Never put backend tracebacks, credentials, tickets or file paths into public JSON/logs.
            LOG.error("UI request %s failed: %s", ref, type(exc).__name__)
            response = Response(500, {"error": {"code": "internal_error", "message": "Ошибка сервера. Код запроса: " + ref, "request_id": ref}})
        try:
            if not isinstance(response.data, (FilePayload, BytesPayload)):
                response.data = json_safe(response.data)
            response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-Request-ID": ref})
            return response
        finally:
            trace.finish(response.status, response.data, failure)

    def _cookie_token(self, request):
        cookie = SimpleCookie()
        try:
            cookie.load(request.headers.get("cookie", ""))
        except Exception:
            return ""
        return cookie[COOKIE].value if COOKIE in cookie else ""

    def _set_cookie(self, token, secure, clear=False):
        value = "%s=%s; HttpOnly; SameSite=Strict; Path=/api/ui/v2" % (COOKIE, token)
        if secure:
            value += "; Secure"
        value += "; Max-Age=%s" % (0 if clear else self.sessions.ttl)
        return value

    def _origin(self, request):
        if request.headers.get("x-tactic-ui") != "1":
            raise ApiError(403, "origin", "Отсутствует заголовок X-Tactic-UI")
        origin = request.headers.get("origin")
        if origin:
            parsed = urlsplit(origin)
            if parsed.scheme != ("https" if request.secure else "http") or parsed.netloc.lower() != request.headers.get("host", "").lower():
                raise ApiError(403, "origin", "Запросы с другого origin запрещены")

    def _json(self, request):
        if len(request.body) > MAX_JSON:
            raise ApiError(413, "body_too_large", "JSON-запрос слишком большой")
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
            raise ApiError(415, "content_type", "Требуется application/json")
        try:
            data = json.loads(request.body.decode("utf-8"), parse_constant=lambda _: fail("NaN/Infinity запрещены"))
        except (ValueError, UnicodeDecodeError):
            fail("Некорректный JSON")
        if not isinstance(data, dict):
            fail("Ожидается JSON-объект")
        return data

    def dispatch(self, request):
        method, path = request.method, request.path
        if method == "GET" and path == "/health":
            return Response(200, {"version": BUILD_VERSION, "mode": self.backend.mode, "api_available": True, "database_checked": False})
        if method not in ("GET", "POST", "PATCH", "DELETE"):
            raise ApiError(405, "method", "Метод не поддерживается")
        if method != "GET":
            self._origin(request)
        if path == "/upload-chunk" and method == "PATCH" and request.headers.get("content-type", "").split(";",1)[0] != "application/octet-stream":
            raise ApiError(415,"content_type","Часть файла требует application/octet-stream")
        if method == "POST" and path == "/session":
            self.sessions.login_attempt(request.address)
            data = self._json(request)
            username = text(data.get("login"), "login", 120)
            password = data.get("password")
            if not isinstance(password, str) or not password or len(password) > 4096:
                fail("Введите пароль")
            two_factor = text(data.get("two_factor", ""), "two_factor", 100, empty=True)
            with self.backend.context():
                user = self.backend.login(username, password, two_factor)
            old_token = self._cookie_token(request)
            if old_token:
                self.sessions.delete(old_token)
            token, session = self.sessions.create(user["login"], user["ticket"], user.get("site", ""),
                                                  {k: v for k, v in user.items() if k != "ticket"})
            action_log.authenticated(session)
            return Response(200, {"user": self.backend.identity(session), "csrf": session.csrf},
                            {"Set-Cookie": self._set_cookie(token, request.secure)})
        token = self._cookie_token(request)
        session = self.sessions.get(token)
        action_log.authenticated(session)
        if method != "GET":
            self.sessions.check_csrf(session, request.headers.get("x-csrf-token"))
        if path == "/session":
            if method == "DELETE":
                # Revoke our browser session, not another desktop client's TACTIC ticket.
                self.sessions.delete(token)
                return Response(200, {"logged_out": True}, {"Set-Cookie": self._set_cookie("", request.secure, clear=True)})
            if method == "GET":
                with self.backend.context(session):
                    return Response(200, {"user": self.backend.identity(session), "csrf": session.csrf})
        if method == "GET" and path == "/projects":
            with self.backend.context(session):
                return Response(200, {"items": self.backend.projects()})
        data = request.query if method == "GET" or path in ("/upload", "/upload-chunk") else self._json(request)
        project = project_code(data.get("project"))
        action_log.parameters(data)
        with self.lock, self.backend.context(session, project):
            if path == '/client-events':
                if method != 'POST':
                    raise ApiError(405, 'method', 'POST required')
                # Bounds are per authenticated login/site, not a client-provided ID.
                now = time.monotonic()
                owner = (session.login, session.site)
                if len(self._event_limits) > 1000:
                    self._event_limits = {k:v for k,v in self._event_limits.items() if v[0] > now-10}
                start, count = self._event_limits.get(owner, (now, 0))
                if start <= now-10: start, count = now, 0
                if count >= 100:
                    raise ApiError(429, 'event_rate', 'Слишком много пакетов действий интерфейса')
                self._event_limits[owner] = (start, count+1)
                return Response(200, action_log.client_events(data, session))
            if path in ('/uploads', '/upload-status', '/upload-chunk', '/upload-finish'):
                return Response(200, self.backend.upload_operation(method, path, data, request.body))
            if method == "GET" and path == "/catalog":
                return Response(200, self.backend.catalog())
            if method == "GET" and path == "/sidebar":
                return Response(200, self.backend.sidebar())
            if method == "GET" and path == "/open":
                return Response(200, self.backend.open_target(text(data.get("target"), "target", 4000)))
            if path in ('/messages', '/message-history', '/message-send', '/subscriptions', '/chats', '/chat-users', '/record-subscription'):
                return Response(200, self.backend.message_operation(method, path, data))
            if path in ("/design-catalog", "/layout-document", "/layout-preview", "/view-document", "/security-matrix", "/user-groups", "/stype-editor", "/stype-dependencies", "/stype-import", "/sidebar-editor", "/cell-editor", "/table-fill-preview", "/table-changes", "/system-config", "/license", "/context-menu", "/embedded-form", "/scripts", "/script", "/script-check", "/script-diff", "/script-run", "/configs", "/config", "/sidebar-order", "/graph", "/pipeline-positions", "/search-types", "/memberships", "/view-config", "/saved-view",
                        "/form-preview", "/tasks", "/task-generate", "/task-form", "/task-change", "/task-form-preview", "/task-hours", "/relationship", "/relation-candidates", "/history", "/record-state",
                        "/file-versions", "/snapshot-current", "/collections", "/collection-members", "/collection-change", "/relations", "/notes", "/file", "/bulk-records", "/users", "/security", "/project-create", "/project-preflight", "/ui-state", "/system"):
                try:
                    return Response(200, self.backend.config_operation(method, path, data))
                except (ET.ParseError, ValueError, TypeError) as exc:
                    raise ApiError(400, "configuration_input", "Некорректная конфигурация: " + str(exc)[:200]) from exc
            target = text(data.get("target"), "target", 4000)
            opened = self.backend.open_target(target)
            if opened["kind"] not in ("table", "form"):
                raise ApiError(400, "not_a_table", "Выбранное представление не является таблицей")
            stype, view = opened["search_type"], opened["view"]
            self.backend.active_target = opened
            spec = opened["spec"]
            if hasattr(self.backend, "check_form_binding"):
                self.backend.check_form_binding(opened, data, method, path)
            if path == '/record' and method in ('POST','PATCH') and opened.get('form_binding') is not None:
                return Response(201 if method == 'POST' else 200, self.backend.embedded_form(method, data))
            if path in ("/export-csv", "/resolved-view") and method != ("POST" if path == "/export-csv" else "GET"):
                raise ApiError(405, "method", "Метод не поддерживается для этого маршрута")
            if method == "POST" and path == "/export-csv":
                return Response(200, self.backend.export_csv(stype, spec, data))
            if method == "GET" and path == "/resolved-view":
                return Response(200, self.backend.resolved_view(data))
            if method == "GET" and path == "/view":
                return Response(200, spec)
            if method == "POST" and path == "/timeline":
                return Response(200, self.backend.timeline(stype, spec, data))
            if method == "POST" and path == "/query":
                return Response(200, self.backend.query(stype, spec, clean_query(dict(data, limit=data.get("limit", spec.get("table_options", {}).get("page_size", 50))), spec["fields"], spec.get("default_sort"))))
            if method == "GET" and path == "/form":
                return Response(200, self.backend.form(stype, data.get("key")))
            if method in ("POST", "PATCH") and path == "/record":
                prepared = (self.backend.prepare_form(stype, data.get("key"), data.get("values"))
                            if hasattr(self.backend, 'prepare_form') else self.backend.form(stype, data.get("key")))
                if prepared.get('dependency_notice'):
                    raise ApiError(400, 'form_dependency', prepared['dependency_notice'])
                spec = prepared['spec']
            if method == "POST" and path == "/record":
                if not spec["capabilities"]["create"]:
                    raise ApiError(403, "read_only", "Создание записей отключено")
                values = clean_values(data.get("values"), spec["fields"])
                return Response(201, self.backend.create(stype, values, spec))
            key = text(data.get("key"), "key", 1500)
            if method == "GET" and path == "/record":
                return Response(200, self.backend.record(stype, key, spec))
            if method == "PATCH" and path == "/record":
                if not spec["capabilities"]["update"]:
                    raise ApiError(403, "read_only", "Редактирование отключено")
                expected = text(data.get("revision"), "revision", 100)
                values = clean_values(data.get("values"), spec["fields"])
                return Response(200, self.backend.update(stype, key, values, expected, spec))
            if method == "POST" and path == "/retire":
                expected = text(data.get("revision"), "revision", 100)
                return Response(200, self.backend.retire(stype, key, expected, spec))
            if method == "GET" and path == "/snapshots":
                return Response(200, self.backend.snapshots(stype, key))
            if method == "POST" and path == "/upload":
                if len(request.body) > MAX_UPLOAD or not request.body:
                    raise ApiError(413, "upload_size", "Файл должен быть от 1 байта до 16 МиБ")
                filename = text(data.get("filename"), "filename", 180)
                if any(c in filename for c in '/\\:*?"<>|') or filename in (".", "..") or filename.endswith((".", " ")) or re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)", filename, re.I):
                    fail("Недопустимое имя файла")
                context = text(data.get("context", "publish"), "context", 100)
                if not re.fullmatch(r"[A-Za-z0-9_\-/]+", context) or ".." in context or context.startswith("/"):
                    fail("Некорректный context check-in")
                idem = text(request.headers.get("idempotency-key"), "Idempotency-Key", 100)
                fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode() + request.body).hexdigest()
                cache_key = (self.sessions._key(token), idem)
                now = time.time()
                self.idempotent = {k: v for k, v in self.idempotent.items() if v[0] > now - 3600}
                if cache_key in self.idempotent:
                    _, old, result = self.idempotent[cache_key]
                    if old != fingerprint:
                        raise ApiError(409, "idempotency", "Idempotency-Key уже использован для другого файла")
                    return Response(200, result)
                if len(self.idempotent) > 2000:
                    raise ApiError(503, "busy", "Достигнут лимит операций загрузки")
                result = self.backend.upload(stype, key, filename, request.body, context)
                self.idempotent[cache_key] = (now, fingerprint, result)
                return Response(201, result)
        raise ApiError(404, "route", "Неизвестный маршрут API")
