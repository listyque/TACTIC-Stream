"""Adapter for the public TACTIC 5.0 source API; mounted INSIDE its CherryPy process.

This development fork is deliberately admin-only. Ordinary-user field/object policies and arbitrary
legacy action handlers have NOT been validated and are not claimed as supported.
All mutating operations go through the existing TacticServerStub / Command API.
"""
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qs
import contextvars
import os
import re
import tempfile
import threading

from .contracts import ApiError, json_safe, revision, safe_field



class TacticBackend:
    mode = "tactic"
    _request_lock = threading.RLock()  # only new UI; not a DB lock against legacy clients

    def __init__(self, config=None):
        config = config or {}
        self.allow_writes = (config.get("allow_writes", False) is True)
        self.allow_uploads = (config.get("allow_uploads", False) is True) and self.allow_writes
        self.allow_script_execution = config.get('allow_script_execution',False) is True and self.allow_writes
        self.site = str(config.get("site", ""))
        self._upload_settings = config.get("resumable_uploads", {})
        self._state = contextvars.ContextVar("tactic_vue_request")

    @contextmanager
    def context(self, session=None, project=None):
        from pyasm.common import Container, Environment
        from pyasm.security import TacticInit, XmlRpcInit, Site
        from pyasm.search import DbContainer
        from pyasm.biz import Project
        from pyasm.web import WebContainer
        from pyasm.web.cherrypy30_adapter import CherryPyAdapter
        from tactic_client_lib import TacticServerStub
        with self._request_lock:
            token = None
            try:
                TacticInit()
                selected_site = session.site if session else self.site
                if selected_site:
                    Site.set_site(selected_site)
                WebContainer.set_web(CherryPyAdapter())
                if session:
                    try:
                        XmlRpcInit(session.ticket, site=session.site)
                    except Exception as exc:
                        raise ApiError(401, "tactic_session_expired", "Сессия TACTIC истекла. Войдите повторно") from exc
                    if not Environment.get_security().is_admin():
                        raise ApiError(403, "admin_only", "На этой стадии native UI доступен администраторам TACTIC")
                if project:
                    project_obj = Project.get_by_code(project)
                    if not project_obj:
                        raise ApiError(403, "project_denied", "Проект недоступен")
                    Project.set_project(project)
                else:
                    Project.set_project("admin")
                stub = TacticServerStub(setup=False, protocol="local")
                stub.set_server("local")
                stub.set_project(project or "admin")
                if session:
                    stub.set_ticket(session.ticket)
                # Original commands call TacticServerStub.get(); give them this same authorized project/ticket.
                TacticServerStub.set(stub)
                token = self._state.set({"stub": stub, "project": project, "session": session})
                yield
                DbContainer.commit_thread_sql()
            except Exception as exc:
                DbContainer.abort_thread_sql(force=True)
                from pyasm.common import UserException
                if isinstance(exc, UserException):
                    raise ApiError(400, "tactic_validation", str(exc)[:500]) from exc
                raise
            finally:
                if token is not None:
                    self._state.reset(token)
                DbContainer.release_thread_sql()
                Container.create()

    def login(self, username, password, two_factor=""):
        from pyasm.common import Environment
        security = Environment.get_security()
        try:
            security.login_user(username, password, two_factor_code=two_factor or None)
        except Exception as exc:
            raise ApiError(401, "invalid_credentials", "Неверный логин, пароль или код подтверждения") from exc
        if not security.is_logged_in() or not security.is_admin():
            raise ApiError(403, "admin_only", "Native UI пока включён только для администраторов TACTIC")
        ticket = security.get_ticket_key()
        if not ticket:
            raise ApiError(401, "invalid_credentials", "TACTIC не выдал ticket")
        canonical = Environment.get_user_name()
        return {"login": canonical, "display_name": canonical, "ticket": ticket, "site": self.site}

    def identity(self, session):
        return {"login": session.login, "display_name": session.user.get("display_name", session.login),
                "mode": self.mode, "site": session.site, "admin_only": True, "allow_writes": self.allow_writes, "allow_uploads": self.allow_uploads}




    def _stub(self):
        return self._state.get()["stub"]

    def _project(self):
        return self._state.get()["project"]



    def _scope_filters(self, stype):
        if stype.startswith("sthpw/"):
            columns = self._stub().get_column_info(stype)
            if "project_code" not in columns:
                raise ApiError(501, "project_scope", "Нельзя безопасно ограничить системную таблицу проектом")
            return [("project_code", self._project())]
        return []

    @staticmethod
    def _like(value):
        # Literal keyword semantics, not arbitrary SQL wildcard expressions.
        return str(value).replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")




    def _row(self, row, spec):
        values = {f["name"]: json_safe(row.get(f["name"])) for f in spec["fields"] if not f.get('write_only')}
        key = row.get("__search_key__")
        if not key:
            raise ApiError(501, "missing_search_key", "TACTIC вернул запись без __search_key__")
        return {"key": key, "values": values, "revision": revision(values)}


    def _write(self, callback):
        if not self.allow_writes:
            raise ApiError(403, "read_only", "Запись отключена в config.json")
        from pyasm.command import Command
        class NativeUiCommand(Command):
            def get_title(self):
                return "TACTIC native configuration UI"
            def execute(self):
                self.result = callback()
        cmd = NativeUiCommand()
        Command.execute_cmd(cmd)
        return cmd.result



    def retire(self, stype, key, expected, spec):
        if not spec["capabilities"]["retire"]:
            raise ApiError(403, "read_only", "Архивирование недоступно")
        self.update(stype, key, {"s_status": "retired"}, expected, spec)
        return {"retired": True}

    def snapshots(self, stype, key):
        self._load(stype, key)
        rows = self._stub().query("sthpw/snapshot", parent_key=key, filters=self._scope_filters("sthpw/snapshot"),
                                  order_bys=["version desc"], limit=100)
        fields = ("code", "context", "version", "description", "timestamp", "login")
        return {"items": [{k: json_safe(r.get(k)) for k in fields} for r in rows], "can_upload": self.allow_uploads,
                "notice": "Показаны до 100 snapshot. Скачивание/превью файлов в live-адаптере ещё не перенесено."}

    def upload(self, stype, key, filename, content, context):
        if not self.allow_uploads:
            raise ApiError(403, "uploads_disabled", "Check-in отключён; включите allow_uploads на тестовой копии")
        self._load(stype, key)
        from pyasm.common import Environment
        root = Path(Environment.get_tmp_dir()) / "vue_checkin"
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="upload_", dir=str(root)) as temporary:
            path = Path(temporary) / filename
            path.write_bytes(content)
            result = self._write(lambda: self._stub().simple_checkin(key, context, str(path),
                                  description="Vue: " + filename, mode="copy", create_icon=False))
        return {"snapshot": json_safe(result), "filename": filename}
