"""Build a fresh native-block page through actual editor input and save/reopen it."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest
from uuid import uuid4


class LayoutKitBrowser(unittest.TestCase):
    def test_build_save_and_use_grid_page(self):
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
                    dict(action=action, project_code="admin", **values),
                ),
            )["info"]

        for name in ("kit_test", "kit_target"):
            call(
                "apply",
                document=dict(name=name, title=name, blocks=[]),
                expected_revision=call("read")["revision"],
                operation_id=str(uuid4()),
            )
        root = Path(__file__).resolve().parents[1]
        output = root / ".screenshots/page-layout-kit"
        output.mkdir(parents=True, exist_ok=True)
        with (output / "browser.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [
                    shutil.which("node"),
                    "tests/page_layout_kit_browser.mjs",
                    Fixture.url,
                    str(output),
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
        saved = call("read", name="kit_test")["document"]
        self.assertEqual(saved["blocks"][0]["kind"], "grid")
        self.assertEqual(saved["blocks"][0]["columns"], 2)
        self.assertEqual(saved["blocks"][0]["children"][0]["column_span"], 2)
        self.assertEqual(saved["blocks"][0]["children"][2]["button_style"], "primary")
