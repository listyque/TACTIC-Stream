"""Existing item navigation and editable detail panels through real browser input."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest
from uuid import uuid4


class RecordBrowser(unittest.TestCase):
    def test_selection_drafts_save_and_lost_response(self):
        from test_transport import Transport
        from tactic_stream.server.api import Api

        class Fixture(Transport):
            pass

        Fixture.setUpClass()
        self.addCleanup(Fixture.tearDownClass)
        api = Api(Fixture.store)
        auth = dict(
            ticket=api.get_ticket("admin", "private-test-password"), project="one"
        )
        api.dispatch(
            "insert",
            (
                auth,
                "config/widget_config",
                dict(
                    search_type="contract/entity",
                    view="record_parts_edit",
                    config='<config><record_parts_edit><element name="name"/><element name="amount"/></record_parts_edit></config>',
                ),
            ),
        )

        def call(action, **values):
            return api.dispatch(
                "execute_cmd",
                (
                    auth,
                    "tactic.ui.panel.dashboard_cmd.DashboardCmd",
                    dict(action=action, project_code="one", **values),
                ),
            )["info"]

        document = dict(
            name="record_browser",
            title="Record workspace",
            blocks=[
                dict(
                    kind="row",
                    children=[
                        dict(
                            kind="items",
                            search_type="contract/entity",
                            view="continuous_example",
                            weight=4,
                            height=540,
                        ),
                        dict(
                            kind="details",
                            weight=8,
                            height=540,
                            children=[
                                dict(
                                    kind="field",
                                    title="Name",
                                    field="name",
                                    binding="selection",
                                    search_type="contract/entity",
                                ),
                                dict(
                                    kind="field",
                                    title="Progress",
                                    field="amount",
                                    format="progress",
                                    binding="selection",
                                    search_type="contract/entity",
                                ),
                                dict(
                                    kind="form",
                                    title="Edit selected record",
                                    binding="selection",
                                    search_type="contract/entity",
                                    fields=["name", "amount"],
                                    edit_view="record_parts_edit",
                                ),
                                dict(
                                    kind="action",
                                    title="Full editor",
                                    binding="selection",
                                    search_type="contract/entity",
                                    native_action="edit",
                                ),
                            ],
                        ),
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
        api.dispatch(
            "execute_cmd",
            (
                auth,
                "tactic.ui.table.CustomLayoutReadCmd",
                dict(
                    view="dashboard.record_browser",
                    detail_key="contract/entity?project=one&code=B",
                ),
            ),
        )
        root = Path(__file__).resolve().parents[1]
        output = root / ".screenshots/dashboard-records"
        output.mkdir(parents=True, exist_ok=True)
        with (output / "browser.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [
                    shutil.which("node"),
                    "tests/dashboard_record_browser.mjs",
                    Fixture.url,
                    str(output),
                    api.dispatch(
                        "get_by_search_key",
                        (auth, "contract/entity?project=one&code=A"),
                    )["name"],
                ],
                cwd=root / "frontend",
                env=dict(
                    os.environ, PLAYWRIGHT_BROWSERS_PATH=str(root / ".browser-cache")
                ),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=120,
            )
        self.assertEqual(
            result.returncode, 0, (output / "browser.log").read_text(encoding="utf-8")
        )
        row = api.dispatch(
            "get_by_search_key", (auth, "contract/entity?project=one&code=A")
        )
        self.assertEqual(row["name"], "Saved after lost reply")
        self.assertEqual(row["amount"], 37)
