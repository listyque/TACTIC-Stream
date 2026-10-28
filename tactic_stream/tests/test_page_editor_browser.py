"""Actual web editor and DashboardCmd persistence on a private SQLite fixture."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest
from uuid import uuid4


class PageEditorBrowser(unittest.TestCase):
    def test_canvas_and_save(self):
        from test_transport import Transport
        from tactic_stream.server.api import Api

        class Fixture(Transport):
            pass

        Fixture.setUpClass()
        self.addCleanup(Fixture.tearDownClass)
        api = Api(Fixture.store)
        auth = dict(
            ticket=api.get_ticket("admin", "private-test-password"), project="admin"
        )

        def call(action, **values):
            return api.dispatch(
                "execute_cmd",
                (
                    auth,
                    "tactic.ui.panel.dashboard_cmd.DashboardCmd",
                    dict(action=action, project_code=auth["project"], **values),
                ),
            )["info"]

        for name in ("review", "review_two"):
            document = dict(
                name=name,
                title=name,
                blocks=[
                    dict(
                        kind="column",
                        height=240,
                        children=[
                            dict(kind="text", text="Project status", height=60),
                            dict(kind="text", text="Next step", height=60),
                        ],
                    )
                ],
            )
            call(
                "apply",
                document=document,
                expected_revision=call("read")["revision"],
                operation_id=str(uuid4()),
            )
        root = Path(__file__).resolve().parents[1]
        auth["project"] = "one"
        detail_document = dict(
            name="detail_preview",
            title="Detail preview",
            blocks=[
                dict(
                    kind="row",
                    children=[
                        dict(
                            kind="items",
                            search_type="contract/entity",
                            view="continuous_example",
                            height=400,
                            filters=[dict(column="code", value="A")],
                        ),
                        dict(
                            kind="details",
                            children=[
                                dict(
                                    kind="column",
                                    search_type="contract/entity",
                                    children=[
                                        dict(kind="text", title="Code", field="code")
                                    ],
                                )
                            ],
                        ),
                    ],
                )
            ],
        )
        call(
            "apply",
            document=detail_document,
            expected_revision=call("read")["revision"],
            operation_id=str(uuid4()),
        )
        output = root / ".screenshots/page-editor-browser"
        output.mkdir(parents=True, exist_ok=True)
        log = output / "browser.log"
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(
                [
                    shutil.which("node"),
                    "tests/page_editor_browser.mjs",
                    Fixture.url,
                    str(output),
                ],
                cwd=root / "frontend",
                env=dict(
                    os.environ, PLAYWRIGHT_BROWSERS_PATH=str(root / ".browser-cache")
                ),
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, log.read_text(encoding="utf-8"))
        from xmlrpc.client import ServerProxy

        with ServerProxy(
            Fixture.url + "/tactic/default/Api/", allow_none=True
        ) as proxy:
            current = dict(
                ticket=proxy.get_ticket("admin", "private-test-password"),
                project="admin",
            )
            state = proxy.execute_cmd(
                current,
                "tactic.ui.panel.dashboard_cmd.DashboardCmd",
                dict(action="read", project_code="admin", name="review"),
            )["info"]
        children = state["document"]["blocks"][0]["children"]
        self.assertEqual(
            [row["text"] for row in children], ["Project status", "Next step"]
        )
        self.assertLess(children[1]['offset_y'], 0)
        text = children[0]
        self.assertEqual(text["height"], 90)
        self.assertEqual(text["padding"], [12, 0, 0, 0])
