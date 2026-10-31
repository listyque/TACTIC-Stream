"""Resource administration, secret handling and isolated project schema upgrades."""

import json
import importlib.util
from contextlib import closing
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from pyasm.common import Config
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.database_resources import (
    database_resources_request as request,
)
from tactic_stream.server.widget_configuration import WidgetConfigConflict


class DatabaseResources(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        config = self.directory / "tactic-conf.xml"
        config.write_text(
            "<config><database><vendor>Sqlite</vendor></database></config>"
        )
        self.enterContext(
            patch.dict(
                os.environ,
                {"TACTIC_CONFIG_PATH": str(config), "TACTIC_TMP_CONFIG_PATH": ""},
            )
        )
        Config.reload_config()
        self.addCleanup(Config.reload_config)
        self.store = Store(self.directory)
        self.store.initialize(hash_password("resource-test-password"))
        self.api = Api(self.store)
        self.ticket = self.api.get_ticket("admin", "resource-test-password")
        self.enterContext(request_context(RequestContext(self.store, "admin", "admin")))
        self.api.auth.bind_security("admin", self.ticket)

    def create(self, **changes):
        loaded = request("load", "new")
        document = dict(
            loaded["document"],
            code="external",
            host="localhost",
            port="5432",
            login="studio",
        )
        document.update(changes)
        return request("save", "new", document, loaded["revision"])

    def test_crud_password_retention_conflicts_and_no_secret_journal(self):
        result = self.create(password="private-connection-password")
        self.assertTrue(result["metadata"]["hasPassword"])
        self.assertNotIn("private-connection-password", json.dumps(result))
        self.assertEqual(result["document"]["password"], "")
        changed = dict(result["document"], host="database.example")
        updated = request("save", result["identity"], changed, result["revision"])
        self.assertEqual(
            Search.get_by_code("sthpw/db_resource", "external").get_value("password"),
            "private-connection-password",
        )
        with self.assertRaises(WidgetConfigConflict):
            request("save", "external", changed, result["revision"])
        self.assertNotIn(
            "private-connection-password",
            "\n".join(
                str(row.get_data())
                for row in Search("sthpw/transaction_log").get_sobjects()
            ),
        )
        cleared = request(
            "save",
            "external",
            dict(updated["document"], clearPassword=True),
            updated["revision"],
        )
        self.assertFalse(cleared["metadata"]["hasPassword"])
        deleted = request(
            "delete",
            "external",
            expected_revision=cleared["revision"],
            confirmation="delete",
        )
        self.assertEqual(
            deleted["catalog"], [dict(identity="new", title="New resource")]
        )

    def test_validation_and_regular_user_denied(self):
        loaded = request("load", "new")
        for changes in (
            {"vendor": "Oracle"},
            {"code": "../escape"},
            {"port": "99999"},
            {"clearPassword": 1},
            {"host": "host1,host2"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                document = dict(loaded["document"], code="test", host="localhost")
                document.update(changes)
                request("save", "new", document, loaded["revision"])
        with patch(
            "tactic_stream.server.database_resources.Environment.get_security"
        ) as security:
            security.return_value.is_admin.return_value = False
            for action in (
                "list",
                "load",
                "save",
                "delete",
                "test",
                "bind",
                "upgrade",
                "unbind",
            ):
                with self.subTest(action=action), self.assertRaises(SecurityException):
                    request(action)

    @unittest.skipUnless(
        importlib.util.find_spec("httpx2"),
        "HTTP integration requires the development httpx2 package",
    )
    def test_http_contract_redacts_secrets_and_requires_confirmations(self):
        from fastapi.testclient import TestClient
        from tactic_stream.server.app import create_app

        with TestClient(create_app(self.directory, event_collector=False)) as client:
            url = "/admin/configuration/database-resources/"
            loaded = client.post(
                url + "load", json=dict(ticket=self.ticket, identity="new")
            ).json()["result"]
            document = dict(
                loaded["document"],
                code="remote",
                host="localhost",
                password="secret-connection-value",
            )
            saved = client.post(
                url + "save",
                json=dict(
                    ticket=self.ticket,
                    identity="new",
                    document=document,
                    expected_revision=loaded["revision"],
                ),
            )
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertNotIn("secret-connection-value", saved.text)
            self.api.dispatch(
                "insert",
                (
                    dict(ticket=self.ticket, project="admin"),
                    "sthpw/login",
                    dict(
                        login="viewer", password=hash_password("viewer-test-password")
                    ),
                ),
            )
            viewer = self.api.get_ticket("viewer", "viewer-test-password")
            self.assertEqual(
                client.post(url + "list", json=dict(ticket=viewer)).status_code, 403
            )
            with request_context(RequestContext(self.store, "viewer", "admin")):
                self.api.auth.bind_security("viewer", viewer)
                from pyasm.search import DbResource

                self.assertEqual(
                    DbResource.get_by_code("remote", "project_database").get_host(),
                    "localhost",
                )
                with self.assertRaises(SecurityException):
                    Search.get_by_code("sthpw/db_resource", "remote")
            value = saved.json()["result"]
            self.assertEqual(
                client.post(
                    url + "delete",
                    json=dict(
                        ticket=self.ticket,
                        identity="remote",
                        expected_revision=value["revision"],
                    ),
                ).status_code,
                400,
            )
            self.assertEqual(
                client.post(
                    url + "delete",
                    json=dict(
                        ticket=self.ticket,
                        identity="remote",
                        expected_revision=value["revision"],
                        confirmation="delete",
                    ),
                ).status_code,
                200,
            )
            self.assertEqual(
                client.post(url + "list", json=dict(ticket="expired")).status_code, 403
            )

    def test_registered_local_resource_upgrade_and_bound_delete_guard(self):
        # An existing project database, not an implicit migration or database creation.
        import sqlite3

        path = self.store.database_path("external_project")
        path.parent.mkdir(exist_ok=True)
        with closing(sqlite3.connect(path)) as db:
            from importlib.resources import files

            for statement in json.loads(
                (
                    files("tactic_stream") / "compatibility/project_schema.json"
                ).read_text()
            ).values():
                db.execute(statement)
            db.execute("CREATE TABLE project_data (id INTEGER PRIMARY KEY, value TEXT)")
            db.execute("INSERT INTO project_data(value) VALUES ('preserve me')")
            db.commit()
        auth = dict(ticket=self.ticket, project="admin")
        self.api.dispatch(
            "insert",
            (
                auth,
                "sthpw/project",
                dict(code="external_project", title="External project"),
            ),
        )
        result = self.create(vendor="Sqlite", host="", port="", login="")
        bound = request(
            "bind",
            "external",
            expected_revision=result["revision"],
            project_code="external_project",
            confirmation="bind",
        )
        with self.assertRaisesRegex(ValueError, "used by a project"):
            request(
                "delete",
                "external",
                expected_revision=bound["revision"],
                confirmation="delete",
            )
        project = Search.get_by_code("sthpw/project", "external_project")
        self.api.dispatch(
            "update", (auth, project.get_search_key(), dict(s_status="retired"))
        )
        retired = request("load", "external")
        self.assertTrue(
            next(
                row
                for row in retired["metadata"]["projects"]
                if row["code"] == "external_project"
            )["retired"]
        )
        with self.assertRaisesRegex(ValueError, "used by a project"):
            request(
                "delete",
                "external",
                expected_revision=retired["revision"],
                confirmation="delete",
            )
        self.api.dispatch("update", (auth, project.get_search_key(), dict(s_status="")))
        bound = request("load", "external")
        self.assertTrue(self.store.upgrade())
        self.assertFalse(self.store.upgrade())
        checked = request(
            "upgrade",
            "external",
            expected_revision=bound["revision"],
            database="external_project",
            confirmation="upgrade",
        )
        self.assertEqual(
            checked["metadata"]["notice"], "Database schema is already current"
        )
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(
                db.execute("SELECT value FROM project_data").fetchone(),
                ("preserve me",),
            )
            self.assertIsNotNone(
                db.execute(
                    "SELECT name FROM sqlite_master WHERE name='spt_widget_config_revision'"
                ).fetchone()
            )
        detached = request(
            "unbind",
            "external",
            expected_revision=bound["revision"],
            project_code="external_project",
            confirmation="unbind",
        )
        request(
            "delete",
            "external",
            expected_revision=detached["revision"],
            confirmation="delete",
        )


@unittest.skipUnless(
    os.environ.get("STREAM_POSTGRES_HOST"), "An isolated PostgreSQL service is required"
)
class ExternalPostgres(DatabaseResources):
    def test_separate_postgres_database_upgrade_routing_and_rollback(self):
        import psycopg
        from psycopg import sql
        from importlib.resources import files
        from concurrent.futures import ThreadPoolExecutor
        from pyasm.search import DbResource, PostgresImpl

        credentials = dict(
            host=os.environ["STREAM_POSTGRES_HOST"],
            port=os.environ.get("STREAM_POSTGRES_PORT", "5432"),
            user=os.environ.get("STREAM_POSTGRES_USER", "stream"),
            password=Path(os.environ["STREAM_POSTGRES_PASSWORD_FILE"])
            .read_text()
            .strip(),
        )
        database = "stream_external_" + uuid.uuid4().hex
        with psycopg.connect(
            dbname="postgres", autocommit=True, **credentials
        ) as maintenance:
            maintenance.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
            )
            try:
                with psycopg.connect(dbname=database, **credentials) as db:
                    for statement in json.loads(
                        (
                            files("tactic_stream") / "compatibility/project_schema.json"
                        ).read_text()
                    ).values():
                        db.execute(PostgresImpl._bootstrap_statement(statement))
                    db.execute(
                        "CREATE TABLE example_asset (id serial PRIMARY KEY, code text, name text)"
                    )
                    db.execute(
                        "INSERT INTO example_asset(code,name) VALUES ('ONE','Preserved external data')"
                    )
                result = self.create(
                    host=credentials["host"],
                    port=credentials["port"],
                    login=credentials["user"],
                    password=credentials["password"],
                )
                auth = dict(ticket=self.ticket, project="admin")
                self.api.dispatch(
                    "insert",
                    (
                        auth,
                        "sthpw/project",
                        dict(
                            code="external_project",
                            title="External project",
                            database=database,
                        ),
                    ),
                )
                latest = request("load", "external")
                bound = request(
                    "bind",
                    "external",
                    expected_revision=latest["revision"],
                    project_code="external_project",
                    confirmation="bind",
                )
                with self.assertRaises(ValueError):
                    request(
                        "upgrade",
                        "external",
                        expected_revision=bound["revision"],
                        database="postgres",
                        confirmation="upgrade",
                    )
                tested = request(
                    "test",
                    "external",
                    bound["document"],
                    bound["revision"],
                    database=database,
                )
                self.assertEqual(
                    tested["metadata"]["notice"], "Database connection succeeded"
                )
                self.assertNotIn(credentials["password"], json.dumps(tested))
                self.assertTrue(self.store.upgrade())
                self.assertFalse(self.store.upgrade())
                resource = DbResource.get_by_code("external", database)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    self.assertEqual(
                        list(
                            pool.map(
                                self.store.upgrade_project_resource,
                                [resource, resource],
                            )
                        ),
                        [False, False],
                    )
                with psycopg.connect(dbname=database, **credentials) as db:
                    self.assertEqual(
                        db.execute("SELECT name FROM example_asset").fetchone(),
                        ("Preserved external data",),
                    )
                    self.assertIsNotNone(
                        db.execute(
                            "SELECT to_regclass('spt_widget_config_revision')"
                        ).fetchone()[0]
                    )
                    db.execute("DROP TABLE spt_agent_host")
                original = PostgresImpl._upgrade_schema

                def fail_after_migration(impl, db, upgrade):
                    original(impl, db, upgrade)
                    db.execute(
                        "ALTER TABLE example_asset ADD COLUMN must_rollback text"
                    )
                    raise ValueError("deliberate failure")

                with patch.object(
                    PostgresImpl, "_upgrade_schema", fail_after_migration
                ):
                    with self.assertRaisesRegex(ValueError, "rolled back"):
                        request(
                            "upgrade",
                            "external",
                            expected_revision=bound["revision"],
                            database=database,
                            confirmation="upgrade",
                        )
                with psycopg.connect(dbname=database, **credentials) as db:
                    self.assertIsNone(
                        db.execute("SELECT to_regclass('spt_agent_host')").fetchone()[0]
                    )
                    self.assertFalse(
                        db.execute(
                            "SELECT 1 FROM information_schema.columns WHERE table_name='example_asset' AND column_name='must_rollback'"
                        ).fetchone()
                    )
                self.assertTrue(self.store.upgrade())
                self.api.dispatch(
                    "insert",
                    (
                        auth,
                        "sthpw/search_object",
                        dict(
                            code="contract/external",
                            search_type="contract/external",
                            namespace="contract",
                            database="{project}",
                            table_name="example_asset",
                            class_name="pyasm.search.SObject",
                        ),
                    ),
                )
                project_auth = dict(ticket=self.ticket, project="external_project")
                import ast

                self.assertEqual(
                    ast.literal_eval(
                        self.api.dispatch("query", (project_auth, "contract/external"))
                    )[0]["name"],
                    "Preserved external data",
                )
                self.api.dispatch(
                    "insert",
                    (
                        project_auth,
                        "contract/external",
                        dict(code="TWO", name="External write"),
                    ),
                )
                self.assertEqual(
                    len(
                        ast.literal_eval(
                            self.api.dispatch(
                                "query", (project_auth, "contract/external")
                            )
                        )
                    ),
                    2,
                )
            finally:
                # Drop only this test's exclusively created database, without FORCE.
                maintenance.execute(
                    sql.SQL("DROP DATABASE {}").format(sql.Identifier(database))
                )


if __name__ == "__main__":
    unittest.main()
