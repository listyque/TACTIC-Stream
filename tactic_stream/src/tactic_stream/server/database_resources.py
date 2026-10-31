"""Administrator-owned database connections; passwords never enter read projections."""

import hashlib
import json
import re
import sqlite3

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import DbResource, Search, SearchType
from pyasm.search.search import _context
from tactic_stream.server.widget_configuration import WidgetConfigConflict


FIELDS = {"code", "vendor", "host", "port", "login", "password", "clearPassword"}


def _records():
    search = Search("sthpw/db_resource")
    search.add_order_by("code")
    return search.get_sobjects()


def _projects():
    search = Search("sthpw/project")
    search.set_show_retired(True)
    search.add_order_by("code")
    return [
        row for row in search.get_sobjects() if row.get_code() not in ("admin", "sthpw")
    ]


def _revision(records, projects):
    # Include secrets only in the digest, so changing a password invalidates stale drafts.
    return hashlib.sha256(
        json.dumps(
            [row.get_data() for row in records + projects], sort_keys=True, default=str
        ).encode()
    ).hexdigest()


def _document(record=None):
    return dict(
        code=record.get_code() if record else "",
        **{
            key: str(record.get_value(key) or "")
            if record
            else ("PostgreSQL" if key == "vendor" else "")
            for key in ("vendor", "host", "port", "login")
        },
        password="",
        clearPassword=False,
    )


def _validate(document, existing=None):
    if not isinstance(document, dict) or set(document) != FIELDS:
        raise ValueError("Invalid database resource fields")
    if any(
        not isinstance(document[key], str)
        or len(document[key]) > 1024
        or "\x00" in document[key]
        for key in FIELDS - {"clearPassword"}
    ):
        raise ValueError("Invalid database resource fields")
    if type(document["clearPassword"]) is not bool or (
        document["clearPassword"] and document["password"]
    ):
        raise ValueError("Choose a replacement password or clear it")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", document["code"]):
        raise ValueError(
            "Resource code must contain letters, digits, underscores or hyphens"
        )
    if existing and document["code"] != existing.get_code():
        raise ValueError("Resource code cannot be changed")
    if document["vendor"] not in ("PostgreSQL", "Sqlite"):
        raise ValueError("Choose PostgreSQL or SQLite")
    if document["vendor"] == "PostgreSQL":
        if (
            not document["host"].strip()
            or any(c.isspace() for c in document["host"])
            or "," in document["host"]
        ):
            raise ValueError("Enter a single database host")
        if document["port"] and (
            not document["port"].isdigit() or not 1 <= int(document["port"]) <= 65535
        ):
            raise ValueError("Database port must be between 1 and 65535")
    elif (
        document["host"] not in ("", "localhost")
        or document["port"]
        or document["login"]
        or document["password"]
    ):
        raise ValueError(
            "SQLite resources must be local and have no connection credentials"
        )
    return {key: document[key] for key in ("code", "vendor", "host", "port", "login")}


def _connection(document, record, database):
    _validate(document, record)
    if not isinstance(database, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,128}", database
    ):
        raise ValueError(
            "Enter a database name containing letters, digits, underscores or hyphens"
        )
    password = document["password"] or (
        record.get_value("password") if record and not document["clearPassword"] else ""
    )
    return DbResource(
        database,
        host=document["host"],
        port=document["port"],
        vendor=document["vendor"],
        user=document["login"],
        password=password,
    )


def _probe(resource, project=False):
    if resource.get_vendor() == "PostgreSQL":
        import psycopg

        try:
            with resource.get_database_impl()._connect(resource) as db:
                db.execute("SET TRANSACTION READ ONLY")
                db.execute("SELECT 1")
                if project and not all(
                    db.execute(
                        "SELECT to_regclass(%s)", ("public." + name,)
                    ).fetchone()[0]
                    for name in ("spt_naming", "spt_custom_script")
                ):
                    raise ValueError(
                        "The target database must contain an existing TACTIC project schema"
                    )
        except psycopg.Error:
            raise ValueError(
                "Database connection failed. Check the host, database, user and password."
            ) from None
    else:
        store = _context.get().store
        if not store.database_path(resource.get_database()).is_file():
            raise ValueError("The SQLite database does not exist")
        with store.connection(resource) as db:
            db.execute("SELECT 1")
            if project and not all(
                db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
                ).fetchone()
                for name in ("spt_naming", "spt_custom_script")
            ):
                raise ValueError(
                    "The target database must contain an existing TACTIC project schema"
                )


def database_resources_request(
    action: str,
    identity: str = "",
    document: dict | None = None,
    expected_revision: str = "",
    database: str = "",
    project_code: str = "",
    confirmation: str = "",
) -> dict:
    security = Environment.get_security()
    if security is None or not security.is_admin():
        raise SecurityException("Database resources require administrator access")
    if action not in (
        "list",
        "load",
        "save",
        "delete",
        "test",
        "upgrade",
        "bind",
        "unbind",
    ):
        raise ValueError("Unknown database resource action")
    if any(
        not isinstance(value, str)
        for value in (identity, expected_revision, database, project_code, confirmation)
    ):
        raise ValueError("Invalid database resource request")
    records, projects = _records(), _projects()
    current_revision = _revision(records, projects)
    record = next((row for row in records if row.get_code() == identity), None)
    if identity not in ("", "new") and record is None:
        raise ValueError("Database resource no longer exists")
    referenced = any(
        row.get_value("db_resource", no_exception=True) == identity for row in projects
    )
    if (
        action in ("delete", "bind", "unbind", "upgrade")
        or action == "save"
        and record
        and referenced
    ) and confirmation != action:
        raise ValueError("Confirm this database resource operation")

    if action in ("save", "delete", "bind", "unbind"):

        class ResourceCommand(Command):
            def execute(self):
                # Serialize competing resource edits across the server workers.
                from pyasm.search import DbContainer

                sql = DbContainer.get(
                    Project.get_db_resource_by_search_type("sthpw/db_resource")
                )
                if sql.get_vendor() == "PostgreSQL":
                    sql.do_query(
                        "SELECT pg_advisory_xact_lock(hashtext('tactic-database-resources'))"
                    )
                else:
                    sql.do_update("UPDATE db_resource SET code=code WHERE 0")
                if _revision(_records(), _projects()) != expected_revision:
                    raise WidgetConfigConflict(
                        "Database resources changed. Reload before saving."
                    )
                if action == "save":
                    values = _validate(document, record)
                    if record is None and any(
                        row.get_code() == values["code"] for row in records
                    ):
                        raise ValueError("Resource code already exists")
                    item = record or SearchType.create("sthpw/db_resource")
                    for key, value in values.items():
                        item.set_value(key, value)
                    if document["password"] or document["clearPassword"]:
                        item.set_value("password", document["password"])
                    if document["vendor"] == "Sqlite":
                        item.set_value("password", "")
                    # Undo snapshots would retain connection passwords in journal XML.
                    item.commit(log_transaction=False)
                    self.info["identity"] = item.get_code()
                elif action == "delete":
                    if not record:
                        raise ValueError("Choose a saved database resource")
                    if any(
                        row.get_value("db_resource", no_exception=True) == identity
                        for row in projects
                    ):
                        raise ValueError(
                            "Resource is used by a project. Change its connection first."
                        )
                    record.delete(log=False)
                    self.info["identity"] = ""
                else:
                    project = next(
                        (row for row in projects if row.get_code() == project_code),
                        None,
                    )
                    if project is None or project.is_retired():
                        raise ValueError("Choose an active project")
                    if not record:
                        raise ValueError("Choose a saved database resource")
                    if (
                        action == "unbind"
                        and project.get_value("db_resource", no_exception=True)
                        != identity
                    ):
                        raise ValueError("Project does not use this resource")
                    resource = (
                        DbResource.get_default(project.get_database_name())
                        if action == "unbind"
                        else DbResource.get_by_code(
                            identity, project.get_database_name()
                        )
                    )
                    _probe(resource, project=True)
                    project.set_value(
                        "db_resource", "" if action == "unbind" else identity
                    )
                    project.commit()
                    self.info["identity"] = identity

        command = ResourceCommand()
        Command.execute_cmd(command)
        DbResource.clear_cache()
        return database_resources_request("load", command.info["identity"])

    notice = ""
    if action in ("test", "upgrade"):
        if expected_revision != current_revision:
            raise WidgetConfigConflict(
                "Database resources changed. Reload before continuing."
            )
        if action == "test":
            _probe(_connection(document, record, database))
            notice = "Database connection succeeded"
        else:
            if not record or not any(
                row.get_value("db_resource", no_exception=True) == identity
                and row.get_database_name() == database
                for row in projects
            ):
                raise ValueError("Choose a database bound to this resource")
            resource = DbResource.get_by_code(identity, database)
            _probe(resource)
            errors = (ValueError, sqlite3.Error)
            if resource.get_vendor() == "PostgreSQL":
                import psycopg

                errors += (psycopg.Error,)
            try:
                changed = _context.get().store.upgrade_project_resource(resource)
            except errors:
                # Driver exception strings may contain connection secrets or SQL values.
                raise ValueError(
                    "Schema update failed and was rolled back. Check database permissions and server diagnostics."
                ) from None
            notice = (
                "Database schema updated"
                if changed
                else "Database schema is already current"
            )
    if action == "list" and not identity and records:
        record = records[0]
        identity = record.get_code()
    if not identity:
        identity = "new"
    return dict(
        identity=identity,
        revision=current_revision,
        canWrite=True,
        catalog=[dict(identity=row.get_code(), title=row.get_code()) for row in records]
        + [dict(identity="new", title="New resource")],
        document=_document(record),
        metadata=dict(
            hasPassword=bool(record and record.get_value("password")),
            projects=[
                dict(
                    code=row.get_code(),
                    title=row.get_value("title") or row.get_code(),
                    database=row.get_database_name(),
                    resource=row.get_value("db_resource", no_exception=True) or "",
                    retired=row.is_retired(),
                )
                for row in projects
            ],
            notice=notice,
        ),
    )
